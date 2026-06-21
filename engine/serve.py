#!/usr/bin/env python3
# kx3-criativos-service — microserviço de geração (host VPS).
# POST /gerar : briefing -> engine(HTML) -> PNG(Chromium) + Canva editável(Connect) -> devolve.
# GET  /health
#
# Deps: fastapi uvicorn requests playwright (chromium já instalado).
# Run:  uvicorn serve:app --host 0.0.0.0 --port 8095
#
# Segredos lidos do host (nunca no código): /root/.kx3_gh_token (PAT GitHub),
# token do Canva via helper /root/kx3_canva_token.sh.
import os, base64, json, uuid, subprocess, tempfile, shutil, time
from typing import Optional
import requests
import numpy as np
from PIL import Image, ImageDraw
from fastapi import FastAPI
from pydantic import BaseModel
import gerador as g

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
REPO = "gfurtado07/kx3-poc"
GH_TOKEN = open("/root/.kx3_gh_token").read().strip()

app = FastAPI(title="kx3-criativos-service")


class GerarReq(BaseModel):
    tipo: str
    arquetipo: str
    briefing: dict
    cutout_b64: Optional[str] = None
    ia_b64: Optional[str] = None
    want_png: bool = True
    want_canva: bool = True
    title: Optional[str] = None


def render_png(html: str) -> bytes:
    d = tempfile.mkdtemp()
    try:
        hp = os.path.join(d, "x.html")
        open(hp, "w", encoding="utf-8").write(html)
        subprocess.check_call(["python3", os.path.join(HERE, "render.py"), hp],
                              stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        return open(hp[:-5] + ".png", "rb").read()
    finally:
        shutil.rmtree(d, ignore_errors=True)


def gh_put(path: str, content: bytes, msg: str) -> str:
    """Publica bytes no GitHub (Contents API) e devolve a URL raw."""
    r = requests.put(
        "https://api.github.com/repos/%s/contents/%s" % (REPO, path),
        headers={"Authorization": "token %s" % GH_TOKEN, "Accept": "application/vnd.github+json"},
        json={"message": msg, "content": base64.b64encode(content).decode()},
        timeout=30,
    )
    r.raise_for_status()
    return "https://raw.githubusercontent.com/%s/main/%s" % (REPO, path)


def canva_token() -> str:
    return subprocess.check_output(["/root/kx3_canva_token.sh"]).decode().strip()


def canva_import(url: str, title: str) -> dict:
    at = canva_token()
    H = {"Authorization": "Bearer %s" % at}
    j = requests.post("https://api.canva.com/rest/v1/url-imports",
                      headers={**H, "Content-Type": "application/json"},
                      json={"title": title, "url": url}, timeout=30).json()
    jid = j.get("job", {}).get("id")
    if not jid:
        return {"error": "no job id", "raw": str(j)[:200]}
    for _ in range(20):
        time.sleep(2)
        s = requests.get("https://api.canva.com/rest/v1/url-imports/%s" % jid, headers=H, timeout=15).json()
        st = s.get("job", {}).get("status")
        if st == "success":
            d = s["job"]["result"]["designs"][0]
            return {"design_id": d["id"], "edit_url": d["urls"]["edit_url"], "view_url": d["urls"].get("view_url")}
        if st == "failed":
            return {"error": s.get("job", {}).get("error", "failed")}
    return {"error": "timeout"}


# ---- tratamento de foto (kx3-imgservice: rembg) ----
IMG_SVC = "http://127.0.0.1:8088"
IMG_TOKEN = "kx3img_Hs7Lp2Qw9Xz4Rt6Yb3Nf"


CARPLAY_PATH = os.path.join(ASSETS, "carplay.png")
TELA_PROMPT = """Olhe a imagem PNG em [[IMG]] (recorte de um produto automotivo, fundo transparente).
Se for uma CENTRAL MULTIMIDIA / MP5 / aparelho com DISPLAY retangular, devolva APENAS JSON com os 4 cantos da AREA DE TELA (somente o display que acende, SEM a moldura/bezel preta ao redor e SEM a coluna de botoes lateral), em pixels (origem no canto superior esquerdo, numeros inteiros):
{"tela": true, "tl":[x,y], "tr":[x,y], "br":[x,y], "bl":[x,y]}
Se NAO houver display (sensor, soleira, cabo, modulo, antena, etc.), devolva {"tela": false}.
Responda so o JSON."""


def _find_coeffs(dst, src):
    A = []
    for (xo, yo), (xi, yi) in zip(dst, src):
        A.append([xi, yi, 1, 0, 0, 0, -xo * xi, -xo * yi])
        A.append([0, 0, 0, xi, yi, 1, -yo * xi, -yo * yi])
    B = np.array([c for p in dst for c in p], dtype=float)
    return np.linalg.solve(np.array(A, dtype=float), B).tolist()


def compor_tela_carplay(cutout_path):
    """Clawdbot localiza o display; se for multimídia, encaixa a tela CarPlay real (warp PIL)."""
    if not os.path.exists(CARPLAY_PATH):
        return None
    rp = os.path.join(tempfile.gettempdir(), uuid.uuid4().hex + "_ask.png")
    shutil.copy(cutout_path, rp); os.chmod(rp, 0o644)
    try:
        info = _extract_json(claude_cli(TELA_PROMPT.replace("[[IMG]]", rp), allow_read=True, timeout=120))
    except Exception:
        info = {"tela": False}
    finally:
        try:
            os.unlink(rp)
        except OSError:
            pass
    if not info.get("tela"):
        return None
    try:
        quad = [(int(info[k][0]), int(info[k][1])) for k in ("tl", "tr", "br", "bl")]
    except Exception:
        return None
    cut = Image.open(cutout_path).convert("RGBA"); W, H = cut.size
    cp = Image.open(CARPLAY_PATH).convert("RGBA"); w, h = cp.size
    coeffs = _find_coeffs(quad, [(0, 0), (w, 0), (w, h), (0, h)])
    warped = cp.transform((W, H), Image.PERSPECTIVE, coeffs, Image.BICUBIC)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon(quad, fill=255)
    cut.paste(warped, (0, 0), mask)
    out = os.path.join(tempfile.gettempdir(), uuid.uuid4().hex + "_tela.png")
    cut.save(out)
    return out


def tratar_foto(foto_url: str) -> str:
    """Baixa a foto, remove o fundo (rembg) e, se for multimídia, compõe a tela CarPlay ligada."""
    raw = requests.get(foto_url, timeout=60).content
    r = requests.post(IMG_SVC + "/removebg",
                      headers={"Authorization": "Bearer " + IMG_TOKEN},
                      json={"image_base64": base64.b64encode(raw).decode()}, timeout=120).json()
    if not r.get("success"):
        raise RuntimeError("removebg: " + str(r.get("error"))[:120])
    p = os.path.join(tempfile.gettempdir(), uuid.uuid4().hex + "_cut.png")
    open(p, "wb").write(base64.b64decode(r["image_base64"]))
    try:
        p2 = compor_tela_carplay(p)
        if p2:
            try:
                os.unlink(p)
            except OSError:
                pass
            return p2
    except Exception:
        pass
    return p


# ---- mapeamento de briefing livre -> estruturado (via Clawdbot / Claude CLI) ----
MAPPER_PROMPT = """Voce e o copywriter senior do Motor de Criativos da KX3 Acessorios Automotivos (acessorios automotivos premium; cores laranja/prata/preto; tom premium, tecnico e direto, sem exagero; portugues impecavel; numeros e termos tecnicos EXATOS; NUNCA invente specs).

A partir do BRIEFING abaixo, devolva APENAS um JSON (sem markdown, sem comentarios, sem texto antes/depois) com EXATAMENTE estas chaves preenchidas para ESTE produto:
{
 "sku": "primeiro SKU",
 "categoria": "categoria curta em CAIXA ALTA",
 "nome": "titulo CURTO e forte, MAXIMO 16 caracteres, 1-2 palavras (ex.: Sensor de Re, Central Android, Som 4 Canais) — NAO use o nome completo aqui",
 "destaque": "1 atributo ancora curto, MAXIMO 22 caracteres (vira a linha laranja)",
 "sub": "SKU · atributo · atributo (curto, uma linha)",
 "bullets": [{"t":"beneficio curto","d":"spec/detalhe curto"} (EXATAMENTE 6)],
 "selos": [{"icon":"um de: wifi chip screen sound cam gps bolt star","big":"2-3 palavras","small":"detalhe curto"} (EXATAMENTE 3)],
 "promo_text": "1 frase de fechamento (diferencial + ganho)",
 "headline_post": ["linha1 curtissima","linha2 curtissima"],
 "sub_post": "1 linha de apoio",
 "cta_post": "Saiba mais no link da bio",
 "promo": {"selo":"OFERTA","desc":"-XX% ou vazio","de":"De R$ X ou vazio","por":"por R$ Y ou vazio","cond":"condicao ou vazio","validade":"validade ou vazio","cta":"Peca ja pelo WhatsApp"}
}
Regras: use SO informacao do briefing; se faltar dado de promocao, deixe string vazia; se faltar spec para 6 bullets, reaproveite atributos reais de formas diferentes, NUNCA invente numero; escolha o icon mais coerente com cada selo.

BRIEFING:
tipo: [[TIPO]]
nome_produto: [[NOME]]
skus: [[SKUS]]
briefing_tecnico: [[TEC]]
briefing_comercial: [[COM]]
inputs_especificos: [[INP]]

Responda APENAS o JSON."""


def claude_cli(prompt: str, allow_read: bool = False, timeout: int = 150) -> str:
    pf = os.path.join(tempfile.gettempdir(), "cl_%s.txt" % uuid.uuid4().hex)
    open(pf, "w", encoding="utf-8").write(prompt)
    os.chmod(pf, 0o644)
    flags = "--allowedTools Read " if allow_read else ""
    try:
        r = subprocess.run(
            ["runuser", "-u", "openclaw", "--", "bash", "-lc",
             'HOME=/home/openclaw claude -p "$(cat %s)" %s--output-format text' % (pf, flags)],
            capture_output=True, text=True, timeout=timeout)
        return r.stdout or ""
    finally:
        try:
            os.unlink(pf)
        except OSError:
            pass


def _extract_json(txt: str):
    import re
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise ValueError("sem JSON na resposta: " + txt[:160])
    return json.loads(m.group(0))


def mapear_briefing(criativo: dict) -> dict:
    import json as _j
    pr = (MAPPER_PROMPT
          .replace("[[TIPO]]", str(criativo.get("tipo", "")))
          .replace("[[NOME]]", str(criativo.get("nome_produto", "")))
          .replace("[[SKUS]]", ", ".join(criativo.get("skus", []) or []))
          .replace("[[TEC]]", _j.dumps(criativo.get("briefing_tecnico"), ensure_ascii=False))
          .replace("[[COM]]", str(criativo.get("briefing_comercial") or ""))
          .replace("[[INP]]", _j.dumps(criativo.get("inputs_especificos") or {}, ensure_ascii=False)))
    d = _extract_json(claude_cli(pr))
    d.setdefault("handle", "@kx3acessorios")
    d.setdefault("site", "www.kx3.com.br")
    d.setdefault("sku", (criativo.get("skus") or [""])[0])
    for k, v in (("hx", 206), ("hw", 668), ("hh", 475)):
        d.setdefault(k, v)
    return d


# ---- Revisores de IA (Fase 3) — Clawdbot ----
REV_COPY_PROMPT = """Voce e revisor ortografico e tecnico da KX3. Revise SOMENTE a escrita dos textos no JSON abaixo: corrija portugues, acentuacao e termos tecnicos. NAO mude o sentido, NAO invente, NAO altere numeros nem a estrutura/chaves. Devolva APENAS o JSON corrigido, mesmas chaves.
JSON:
[[JSON]]
Responda so o JSON."""

REV_ARTE_PROMPT = """Voce e diretor de arte senior da KX3 Acessorios Automotivos revisando um criativo (arquetipo [[ARQ]]). Leia e analise a imagem em [[IMG]].
Cheque pela regua KX3:
1. NENHUM texto cortado, sobreposto, estourando a margem ou ilegivel.
2. Identidade: cores laranja/prata/preto, logo KX3 visivel com respiro.
3. Produto e o heroi, nitido e bem posicionado.
4. Hierarquia clara, com respiro; nada espremido nem poluido.
5. Portugues correto.
Calibracao da nota (seja JUSTO, nao severo a toa): 95-100 = pronto pra publicar, sem nenhum problema real; 90-94 = bom, so ajuste cosmetico; 80-89 = problema visivel; <80 = erro grave (texto cortado, marca errada). Uma arte limpa, legivel e fiel a marca DEVE receber 95+.
Devolva APENAS JSON: {"aprovado": true|false, "score": 0-100, "problemas": ["curto"], "correcao": {"campo_do_briefing": "novo valor"}}.
Em "correcao" inclua SO ajustes de TEXTO do briefing que resolvam problemas de layout (ex.: encurtar "nome" ou "destaque" se cortou; encurtar um bullet longo). Se estiver bom: aprovado=true, problemas=[], correcao={}.
Responda so o JSON."""


def revisar_copy(briefing: dict) -> dict:
    try:
        d = _extract_json(claude_cli(REV_COPY_PROMPT.replace("[[JSON]]", json.dumps(briefing, ensure_ascii=False))))
        for k in ("hx", "hw", "hh", "handle", "site", "sku"):
            if k in briefing:
                d[k] = briefing[k]
        if not d.get("bullets") or not d.get("selos"):
            return briefing
        return d
    except Exception:
        return briefing


def revisar_arte(img_path: str, arq: str) -> dict:
    try:
        return _extract_json(claude_cli(
            REV_ARTE_PROMPT.replace("[[ARQ]]", arq).replace("[[IMG]]", img_path),
            allow_read=True, timeout=120))
    except Exception as e:
        return {"aprovado": True, "score": None, "problemas": [], "correcao": {}, "_erro": str(e)[:120]}


class PrepararReq(BaseModel):
    criativo: dict


@app.post("/preparar")
def preparar(req: PrepararReq):
    return {"briefing": mapear_briefing(req.criativo)}


def _tmp_write(b64: str, suffix: str) -> str:
    p = os.path.join(tempfile.gettempdir(), uuid.uuid4().hex + suffix)
    open(p, "wb").write(base64.b64decode(b64))
    return p


@app.get("/health")
def health():
    return {"ok": True, "service": "kx3-criativos"}


def _setup_assets(d, tipo, cutout_b64=None, ia_b64=None):
    tmp = []
    if cutout_b64:
        d["cutout_path"] = _tmp_write(cutout_b64, ".png"); tmp.append(d["cutout_path"])
    else:
        d.setdefault("cutout_path", os.path.join(ASSETS, "produto_cut.png"))
    if tipo == "post":
        if ia_b64:
            d["ia_lifestyle_path"] = _tmp_write(ia_b64, ".jpg"); tmp.append(d["ia_lifestyle_path"])
        else:
            d.setdefault("ia_lifestyle_path", os.path.join(ASSETS, "ia_lifestyle.jpg"))
    return tmp


def _compose(d, tipo, arq, want_png=True, want_canva=True, title=None):
    html = g.montar(d, tipo, arq)
    uid = uuid.uuid4().hex
    out = {"tipo": tipo, "arquetipo": arq}
    if want_png:
        out["png_url"] = gh_put("gen/%s.png" % uid, render_png(html), "criativo png")
    if want_canva:
        out["html_url"] = gh_put("gen/%s.html" % uid, html.encode("utf-8"), "criativo html")
        out["canva"] = canva_import(out["html_url"], title or ("KX3 %s %s" % (d.get("sku", ""), arq)))
    return out


MIN_SCORE = int(os.environ.get("KX3_MIN_SCORE", "95"))   # nota mínima p/ pré-aprovação
MAX_TRIES = int(os.environ.get("KX3_MAX_TRIES", "4"))     # teto RÍGIDO de tentativas (protege orçamento)


def _gerar_variacao(d, tipo, arq, title):
    """Compõe → renderiza (local, custo zero) → revisa por visão → auto-corrige até
    score >= MIN_SCORE ou esgotar MAX_TRIES; publica a MELHOR tentativa, marcada se não bateu a meta."""
    best = None
    tentativas = 0
    for attempt in range(MAX_TRIES):
        tentativas = attempt + 1
        html = g.montar(d, tipo, arq)
        png = render_png(html)
        rp = os.path.join(tempfile.gettempdir(), "rev_%s.png" % uuid.uuid4().hex)
        open(rp, "wb").write(png); os.chmod(rp, 0o644)
        try:
            rev = revisar_arte(rp, arq)
        finally:
            try:
                os.unlink(rp)
            except OSError:
                pass
        score = rev.get("score")
        sc = score if isinstance(score, (int, float)) else -1
        cand = {"score": score, "sc": sc, "html": html, "png": png, "problemas": rev.get("problemas") or []}
        if best is None or sc > best["sc"]:
            best = cand
        if score is None or sc >= MIN_SCORE:   # bateu a meta OU revisão indisponível (fail-open)
            best = cand
            break
        cor = rev.get("correcao") or {}
        if not cor or attempt == MAX_TRIES - 1:
            break
        for k, v in cor.items():               # aplica correção (só texto escalar) e re-renderiza
            if k in d and isinstance(v, (str, int, float)):
                d[k] = v
    score = best["score"]
    aprovado_ia = isinstance(score, (int, float)) and score >= MIN_SCORE
    uid = uuid.uuid4().hex
    out = {"tipo": tipo, "arquetipo": arq, "score": score, "problemas": best["problemas"],
           "tentativas": tentativas, "aprovado_ia": aprovado_ia, "min_score": MIN_SCORE}
    out["png_url"] = gh_put("gen/%s.png" % uid, best["png"], "criativo png")
    out["html_url"] = gh_put("gen/%s.html" % uid, best["html"].encode("utf-8"), "criativo html")
    out["canva"] = canva_import(out["html_url"], title or ("KX3 %s %s" % (d.get("sku", ""), arq)))
    return out


@app.post("/gerar")
def gerar(req: GerarReq):
    d = dict(req.briefing)
    tmp = _setup_assets(d, req.tipo, req.cutout_b64, req.ia_b64)
    try:
        return _compose(d, req.tipo, req.arquetipo, req.want_png, req.want_canva, req.title)
    finally:
        for p in tmp:
            try:
                os.unlink(p)
            except OSError:
                pass


# tipo do criativo -> arquétipos do engine (2-3 variações)
TIPO_ARQ = {
    "flyer_divulgacao": [("flyer", "A"), ("flyer", "C")],
    "post_instagram": [("post", "lifestyle")],
    "flyer_promocao": [("promo", "faixa")],
    "flyer_campanha": [("flyer", "A")],
}


class GerarCriativoReq(BaseModel):
    criativo: dict
    foto_url: Optional[str] = None
    cutout_b64: Optional[str] = None
    ia_b64: Optional[str] = None


@app.post("/gerar_criativo")
def gerar_criativo(req: GerarCriativoReq):
    """Mapeia o briefing livre (Clawdbot) e gera todas as variações do tipo."""
    c = req.criativo
    briefing = revisar_copy(mapear_briefing(c))  # mapeia + revisor ortográfico
    jobs = TIPO_ARQ.get(c.get("tipo"), [("flyer", "A")])
    cutpath = None
    if req.foto_url:
        try:
            cutpath = tratar_foto(req.foto_url)
        except Exception:
            cutpath = None
    variacoes = []
    for i, (t, a) in enumerate(jobs):
        d = dict(briefing)
        if cutpath:
            d["cutout_path"] = cutpath
        tmp = _setup_assets(d, t, req.cutout_b64, req.ia_b64)
        try:
            o = _gerar_variacao(d, t, a, "KX3 %s %s" % (c.get("nome_produto") or d.get("sku", ""), a))
            cv = o.get("canva") or {}
            variacoes.append({"idx": i, "arquetipo": t + "/" + a, "png": o.get("png_url"), "thumb": o.get("png_url"),
                              "edit_url": cv.get("edit_url"), "view_url": cv.get("view_url"), "canva_design_id": cv.get("design_id"),
                              "score": o.get("score"), "problemas": o.get("problemas"),
                              "aprovado_ia": o.get("aprovado_ia"), "tentativas": o.get("tentativas"), "min_score": o.get("min_score")})
        except Exception as e:
            variacoes.append({"idx": i, "arquetipo": t + "/" + a, "erro": str(e)[:200]})
        finally:
            for p in tmp:
                try:
                    os.unlink(p)
                except OSError:
                    pass
    if cutpath:
        try:
            os.unlink(cutpath)
        except OSError:
            pass
    return {"briefing": briefing, "variacoes": variacoes}
