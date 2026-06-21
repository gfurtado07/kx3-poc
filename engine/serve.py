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
import os, base64, uuid, subprocess, tempfile, shutil, time
from typing import Optional
import requests
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


# ---- mapeamento de briefing livre -> estruturado (via Clawdbot / Claude CLI) ----
MAPPER_PROMPT = """Voce e o copywriter senior do Motor de Criativos da KX3 Acessorios Automotivos (acessorios automotivos premium; cores laranja/prata/preto; tom premium, tecnico e direto, sem exagero; portugues impecavel; numeros e termos tecnicos EXATOS; NUNCA invente specs).

A partir do BRIEFING abaixo, devolva APENAS um JSON (sem markdown, sem comentarios, sem texto antes/depois) com EXATAMENTE estas chaves preenchidas para ESTE produto:
{
 "sku": "primeiro SKU",
 "categoria": "categoria curta em CAIXA ALTA",
 "nome": "nome forte e curto do produto (linha grande)",
 "destaque": "1 atributo ancora curto (vira a linha laranja)",
 "sub": "SKU · atributo · atributo",
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
tipo: %(tipo)s
nome_produto: %(nome)s
skus: %(skus)s
briefing_tecnico: %(tec)s
briefing_comercial: %(com)s
inputs_especificos: %(inp)s

Responda APENAS o JSON."""


def claude_cli(prompt: str) -> str:
    pf = os.path.join(tempfile.gettempdir(), "mapper_%s.txt" % uuid.uuid4().hex)
    open(pf, "w", encoding="utf-8").write(prompt)
    os.chmod(pf, 0o644)
    try:
        r = subprocess.run(
            ["runuser", "-u", "openclaw", "--", "bash", "-lc",
             'HOME=/home/openclaw claude -p "$(cat %s)" --output-format text' % pf],
            capture_output=True, text=True, timeout=150)
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
    pr = MAPPER_PROMPT % {
        "tipo": criativo.get("tipo", ""),
        "nome": criativo.get("nome_produto", ""),
        "skus": ", ".join(criativo.get("skus", []) or []),
        "tec": _j.dumps(criativo.get("briefing_tecnico"), ensure_ascii=False),
        "com": criativo.get("briefing_comercial") or "",
        "inp": _j.dumps(criativo.get("inputs_especificos") or {}, ensure_ascii=False),
    }
    d = _extract_json(claude_cli(pr))
    d.setdefault("handle", "@kx3acessorios")
    d.setdefault("site", "www.kx3.com.br")
    d.setdefault("sku", (criativo.get("skus") or [""])[0])
    for k, v in (("hx", 206), ("hw", 668), ("hh", 475)):
        d.setdefault(k, v)
    return d


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


@app.post("/gerar")
def gerar(req: GerarReq):
    d = dict(req.briefing)
    tmp = []
    try:
        if req.cutout_b64:
            d["cutout_path"] = _tmp_write(req.cutout_b64, ".png"); tmp.append(d["cutout_path"])
        else:
            d.setdefault("cutout_path", os.path.join(ASSETS, "produto_cut.png"))
        if req.tipo == "post":
            if req.ia_b64:
                d["ia_lifestyle_path"] = _tmp_write(req.ia_b64, ".jpg"); tmp.append(d["ia_lifestyle_path"])
            else:
                d.setdefault("ia_lifestyle_path", os.path.join(ASSETS, "ia_lifestyle.jpg"))
        html = g.montar(d, req.tipo, req.arquetipo)
        uid = uuid.uuid4().hex
        out = {"tipo": req.tipo, "arquetipo": req.arquetipo}
        if req.want_png:
            out["png_url"] = gh_put("gen/%s.png" % uid, render_png(html), "criativo png")
        if req.want_canva:
            out["html_url"] = gh_put("gen/%s.html" % uid, html.encode("utf-8"), "criativo html")
            out["canva"] = canva_import(out["html_url"], req.title or ("KX3 %s %s" % (d.get("sku", ""), req.arquetipo)))
        return out
    finally:
        for p in tmp:
            try:
                os.unlink(p)
            except OSError:
                pass
