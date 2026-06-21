#!/usr/bin/env python3
# Driver de teste do engine no servidor — gera os arquétipos do KRC5050.
# Uso: python3 driver.py            (gera flyer A/C, post, promo em ./out)
#      python3 driver.py <tipo> <arq> <out.html>   (gera 1, lendo briefing.json)
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gerador as g

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
BRIEF = {
    "sku": "KRC5050", "categoria": "CENTRAL MULTIMÍDIA ANDROID",
    "nome": "Central Multimídia", "destaque": "Android 9″ · 4/64GB",
    "sub": "KRC5050 · Padrão 2-DIN · CarPlay sem fio",
    "cutout_path": os.path.join(ASSETS, "produto_cut.png"),
    "ia_lifestyle_path": os.path.join(ASSETS, "ia_lifestyle.jpg"),
    "bullets": [
        {"t": "CarPlay & Android Auto", "d": "sem fio, conecta sozinho"},
        {"t": "Octacore + 4GB RAM", "d": "64GB de memória"},
        {"t": "Câmera de Ré + Frontal Temporizada", "d": "* aceita câmeras Full HD"},
        {"t": "Bluetooth 5.2 · Wi-Fi · GPS", "d": "conectividade total"},
        {"t": "DSP com Corte de Frequência", "d": "HPF / LPF"},
        {"t": "Tela 9″ Full HD", "d": "capacitiva, sensível ao toque"},
    ],
    "selos": [
        {"icon": "wifi", "big": "Sem fio", "small": "CarPlay & Android Auto"},
        {"icon": "chip", "big": "4/64GB", "small": "Octacore"},
        {"icon": "screen", "big": "9″ Full HD", "small": "tela capacitiva"},
    ],
    "promo_text": "Octacore e 4GB de RAM: muito mais fluidez que aparelhos quad-core ou 2GB de memória.",
    "headline_post": ["Sua jornada,", "mais conectada."],
    "sub_post": "Central Multimídia KRC5050 · CarPlay & Android Auto sem fio",
    "cta_post": "Saiba mais no link da bio",
    "promo": {"selo": "OFERTA", "desc": "-23%", "de": "De R$ 1.299", "por": "por R$ 999",
              "cond": "12x de R$ 96 sem juros · à vista R$ 899 no Pix",
              "validade": "Válido até 30/06/2026 ou enquanto durar o estoque.",
              "cta": "Peça já pelo WhatsApp"},
    "handle": "@kx3acessorios", "site": "www.kx3.com.br",
    "hx": 206, "hw": 668, "hh": 475,
}

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"); os.makedirs(out, exist_ok=True)
    jobs = [("flyer", "A", "flyer_A.html"), ("flyer", "C", "flyer_C.html"),
            ("post", "lifestyle", "post.html"), ("promo", "faixa", "promo.html")]
    for tipo, arq, fn in jobs:
        open(os.path.join(out, fn), "w", encoding="utf-8").write(g.montar(BRIEF, tipo, arq))
        print("html", fn)
