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


def publish_html(html: str) -> str:
    """Publica o HTML no GitHub (Contents API) e devolve a URL raw (Canva importa por URL .html)."""
    path = "gen/%s.html" % uuid.uuid4().hex
    r = requests.put(
        "https://api.github.com/repos/%s/contents/%s" % (REPO, path),
        headers={"Authorization": "token %s" % GH_TOKEN, "Accept": "application/vnd.github+json"},
        json={"message": "criativo gen", "content": base64.b64encode(html.encode("utf-8")).decode()},
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
        out = {"tipo": req.tipo, "arquetipo": req.arquetipo}
        if req.want_png:
            out["png_b64"] = base64.b64encode(render_png(html)).decode()
        if req.want_canva:
            url = publish_html(html)
            out["html_url"] = url
            out["canva"] = canva_import(url, req.title or ("KX3 %s %s" % (d.get("sku", ""), req.arquetipo)))
        return out
    finally:
        for p in tmp:
            try:
                os.unlink(p)
            except OSError:
                pass
