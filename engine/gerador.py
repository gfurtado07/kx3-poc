#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# Motor de Criativos KX3 — ENGINE consolidado (assets PIL + composição HTML)
# ---------------------------------------------------------------------------
# Une, num só módulo:
#   1) Tokens de marca KX3 (Constituição Visual).
#   2) Geração de ASSETS com profundidade (PIL): medalhões de spec, selo
#      starburst de oferta, faixa de preço trabalhada, logo oficial e a
#      composição "lifestyle" (produto real sobre cena de carro).
#   3) ARQUÉTIPOS aprovados, dirigidos por um BRIEFING (dict):
#        - flyer  / A  -> hero central + 6 cards de spec
#        - flyer  / C  -> macro + 3 medalhões
#        - post   / lifestyle -> imagem lifestyle full-bleed + headline
#        - promo  / faixa     -> selo starburst + faixa de preço
#
# Saída: HTML self-contained (1080x1350, tudo em data-URI) pronto pra hospedar
# e importar no Canva como design EDITÁVEL (textos/preços = camadas).
#
# A logo é SEMPRE a oficial (LOGO_ORIGINAL.png) — nunca recriar "KX3" em texto.
#
# Uso direto:  python3 gerador.py   -> gera os 4 arquétipos do KRC5050 em ./out
# Em produção: o orquestrador chama montar(briefing, tipo, arquetipo, assets).
# ---------------------------------------------------------------------------

import base64, math, os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import numpy as np

# ---- Tokens de marca (não-negociáveis) ----
PRETO = "#0e1116"; LAR = "#FF6600"; PRATA = "#A7A9AC"; ESC = "#161b22"
LAR_RGB = (255, 102, 0); LAR_D = (199, 71, 0); LAR_L = (255, 150, 54)
D1 = (34, 42, 57); D0 = (11, 14, 19); BORD = (48, 58, 74)
FONT_T = '"Arial Black", Impact, sans-serif'
HERE = os.path.dirname(os.path.abspath(__file__))
def _find_logo():
    cands = [os.environ.get("KX3_LOGO"), os.path.join(HERE, "..", "..", "LOGO_ORIGINAL.png"), os.path.join(HERE, "LOGO_ORIGINAL.png")]
    for p in cands:
        if p and os.path.exists(p):
            return os.path.normpath(p)
    return os.path.normpath(cands[1])
LOGO_SRC = _find_logo()

# ===========================================================================
# Helpers de imagem (PIL)
# ===========================================================================
def _uri(img, mime="image/png"):
    b = BytesIO(); img.save(b, "PNG"); return "data:%s;base64,%s" % (mime, base64.b64encode(b.getvalue()).decode())

def _uri_file(path, mime="image/png"):
    return "data:%s;base64,%s" % (mime, base64.b64encode(open(path, "rb").read()).decode())

def _radial(size, inner, outer, cx, cy, R, mask_circle=True):
    w, h = size; yy, xx = np.mgrid[0:h, 0:w]; d = np.sqrt((xx-cx)**2+(yy-cy)**2)/R; t = np.clip(d, 0, 1)
    arr = np.zeros((h, w, 4), np.uint8)
    for i in range(3): arr[:, :, i] = (inner[i]*(1-t)+outer[i]*t).astype(np.uint8)
    if mask_circle:
        a = np.clip((R-np.sqrt((xx-cx)**2+(yy-cy)**2))*1.5+0.5, 0, 1)*255; arr[:, :, 3] = a.astype(np.uint8)
    else:
        arr[:, :, 3] = 255
    return Image.fromarray(arr, "RGBA")

def _shadow(mask, blur, alpha, off=(0, 10)):
    a = mask.split()[3].point(lambda p: int(p*alpha/255)); blk = Image.new("RGBA", mask.size, (0, 0, 0, 255)); blk.putalpha(a)
    sh = Image.new("RGBA", mask.size, (0, 0, 0, 0)); sh.paste(blk, off, blk); return sh.filter(ImageFilter.GaussianBlur(blur))

# ---- ícones de linha (para os medalhões) ----
def _ic_wifi(d, cx, cy):
    for r, wd in [(34, 7), (23, 6), (13, 5)]: d.arc([cx-r, cy-r, cx+r, cy+r], 215, 325, fill=(255, 255, 255, 235), width=wd)
    d.ellipse([cx-5, cy+18, cx+5, cy+28], fill=LAR_L)
def _ic_chip(d, cx, cy):
    s = 30; d.rounded_rectangle([cx-s, cy-s, cx+s, cy+s], radius=9, outline=(255, 255, 255, 235), width=7)
    d.rounded_rectangle([cx-12, cy-12, cx+12, cy+12], radius=4, outline=LAR_L, width=5)
    for i in (-14, 0, 14):
        d.line([cx+i, cy-s-12, cx+i, cy-s], fill=(255, 255, 255, 220), width=5); d.line([cx+i, cy+s, cx+i, cy+s+12], fill=(255, 255, 255, 220), width=5)
        d.line([cx-s-12, cy+i, cx-s, cy+i], fill=(255, 255, 255, 220), width=5); d.line([cx+s, cy+i, cx+s+12, cy+i], fill=(255, 255, 255, 220), width=5)
def _ic_screen(d, cx, cy):
    d.rounded_rectangle([cx-38, cy-26, cx+38, cy+22], radius=8, outline=(255, 255, 255, 235), width=7)
    d.line([cx-30, cy+20, cx-30, cy-18], fill=LAR_L, width=4); d.line([cx-16, cy+34, cx+16, cy+34], fill=(255, 255, 255, 220), width=7)
def _ic_sound(d, cx, cy):
    d.polygon([(cx-28, cy-9), (cx-12, cy-9), (cx+2, cy-24), (cx+2, cy+24), (cx-12, cy+9), (cx-28, cy+9)], outline=(255, 255, 255, 235), width=6)
    for r, wd in [(16, 5), (27, 5)]:
        d.arc([cx+2-r, cy-r, cx+2+r, cy+r], -50, 50, fill=LAR_L, width=wd)
def _ic_cam(d, cx, cy):
    d.rounded_rectangle([cx-34, cy-18, cx+34, cy+24], radius=9, outline=(255, 255, 255, 235), width=6)
    d.rectangle([cx-24, cy-28, cx-4, cy-18], outline=(255, 255, 255, 235), width=5)
    d.ellipse([cx-13, cy-7, cx+13, cy+19], outline=LAR_L, width=5)
def _ic_gps(d, cx, cy):
    d.ellipse([cx-20, cy-30, cx+20, cy+10], outline=(255, 255, 255, 235), width=6)
    d.polygon([(cx-12, cy+1), (cx+12, cy+1), (cx, cy+34)], fill=(255, 255, 255, 235))
    d.ellipse([cx-7, cy-17, cx+7, cy-3], fill=LAR_L)
def _ic_bolt(d, cx, cy):
    d.polygon([(cx+8, cy-34), (cx-18, cy+5), (cx-2, cy+5), (cx-8, cy+34), (cx+18, cy-7), (cx+2, cy-7)], fill=(255, 255, 255, 235))
def _ic_star(d, cx, cy):
    p = []
    for i in range(10):
        a = math.pi*i/5 - math.pi/2
        r = 31 if i % 2 == 0 else 13
        p.append((cx+r*math.cos(a), cy+r*math.sin(a)))
    d.polygon(p, outline=(255, 255, 255, 235), width=5)
_ICONS = {"wifi": _ic_wifi, "chip": _ic_chip, "screen": _ic_screen,
          "sound": _ic_sound, "cam": _ic_cam, "gps": _ic_gps, "bolt": _ic_bolt, "star": _ic_star}

# ===========================================================================
# Builders de ASSET (retornam PIL.Image RGBA)
# ===========================================================================
def asset_medalhao(icon="wifi"):
    W, H = 300, 360; cx, cy = 150, 150; R = 130; img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    mask = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(mask).ellipse([cx-R, cy-R, cx+R, cy+R], fill=(0, 0, 0, 255))
    img.alpha_composite(_shadow(mask, 18, 150, (0, 16))); img.alpha_composite(_radial((W, H), D1, D0, cx-30, cy-40, R+30))
    dr = ImageDraw.Draw(img); dr.ellipse([cx-R, cy-R, cx+R, cy+R], outline=BORD, width=3)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(glow).arc([cx-R+10, cy-R+10, cx+R-10, cy+R-10], 200, 340, fill=LAR_RGB, width=16)
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(7))); dr.arc([cx-R+10, cy-R+10, cx+R-10, cy+R-10], 200, 340, fill=LAR_RGB, width=9)
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(gl).ellipse([cx-95, cy-118, cx+25, cy-18], fill=(255, 255, 255, 46))
    img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(22))); _ICONS.get(icon, _ic_wifi)(dr, cx, cy-66)
    return img

def asset_burst():
    W = H = 340; cx = cy = 170; Ro = 158; Ri = 126; n = 18; pts = []
    for i in range(n*2):
        ang = math.pi*i/n - math.pi/2; r = Ro if i % 2 == 0 else Ri; pts.append((cx+r*math.cos(ang), cy+r*math.sin(ang)))
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); mask = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(mask).polygon(pts, fill=(0, 0, 0, 255))
    img.alpha_composite(_shadow(mask, 16, 160, (0, 12)))
    fill = _radial((W, H), LAR_L, LAR_D, cx-26, cy-30, Ro+26, mask_circle=False); star = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(star).polygon(pts, fill=(255, 255, 255, 255)); img.paste(fill, (0, 0), star)
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(gl).ellipse([cx-86, cy-104, cx+30, cy-6], fill=(255, 255, 255, 66)); img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(20)))
    return img

def asset_pricepanel():
    W, H = 940, 250; img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); rr = [10, 18, W-10, H-22]
    mask = Image.new("L", (W, H), 0); ImageDraw.Draw(mask).rounded_rectangle(rr, radius=20, fill=255)
    img.alpha_composite(_shadow(Image.merge("RGBA", [mask]*4), 16, 150, (0, 14)))
    grad = np.zeros((H, W, 4), np.uint8); ty = np.linspace(0, 1, H)
    for i in range(3): grad[:, :, i] = (np.array(LAR_L[i])*(1-ty)+np.array(LAR_D[i])*ty)[:, None].astype(np.uint8)
    grad[:, :, 3] = 255; panel = Image.fromarray(grad, "RGBA"); m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).rounded_rectangle(rr, radius=20, fill=255); img.paste(panel, (0, 0), m)
    dr = ImageDraw.Draw(img); dr.rounded_rectangle(rr, radius=20, outline=(255, 190, 120, 180), width=2); dr.line([rr[0]+18, rr[1]+4, rr[2]-18, rr[1]+4], fill=(255, 255, 255, 90), width=3)
    return img

def asset_logo(w=680):
    lg = Image.open(LOGO_SRC).convert("RGBA"); h = round(lg.height*w/lg.width); return lg.resize((w, h), Image.LANCZOS)

def asset_lifestyle(ia_path, cut_path):
    """Compõe o produto real (recorte) como herói sobre a cena lifestyle desfocada."""
    bg = Image.open(ia_path).convert("RGB").resize((1080, 1350), Image.LANCZOS).filter(ImageFilter.GaussianBlur(4))
    bg = ImageEnhance.Brightness(bg).enhance(0.72); bg = ImageEnhance.Color(bg).enhance(1.05); bg = bg.convert("RGBA")
    halo = Image.new("RGBA", (1080, 1350), (0, 0, 0, 0)); ImageDraw.Draw(halo).ellipse([220, 500, 860, 1140], fill=(150, 170, 200, 70)); bg.alpha_composite(halo.filter(ImageFilter.GaussianBlur(140)))
    prod = Image.open(cut_path).convert("RGBA"); pw = 880; ph = round(prod.height*pw/prod.width); prod = prod.resize((pw, ph), Image.LANCZOS); px = (1080-pw)//2; py = 566
    pa = prod.split()[3]; blk = Image.new("RGBA", prod.size, (0, 0, 0, 0)); blk.putalpha(pa.point(lambda v: int(v*0.5)))
    sh = Image.new("RGBA", (1080, 1350), (0, 0, 0, 0)); sh.paste(blk, (px, py+28), blk); bg.alpha_composite(sh.filter(ImageFilter.GaussianBlur(26))); bg.alpha_composite(prod, (px, py))
    return bg.convert("RGB")

# ===========================================================================
# Composição HTML
# ===========================================================================
def _page(inner, label):
    return ('<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><style>'
            '*{margin:0;padding:0;box-sizing:border-box}.t{font-family:' + FONT_T + ';font-weight:900}'
            '.page{position:relative;width:1080px;height:1350px;background:' + PRETO + ';font-family:Arial,Helvetica,sans-serif;overflow:hidden}'
            '</style></head><body><div class="page" data-document-role="page" data-label="' + label + '">' + inner + '</div></body></html>')

def cap(s): return "" if s is None else str(s)
def _logo(uri, x, y, w=230): return '<img src="%s" style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx">' % (uri, x, y, w, round(w*0.329))

# ---------- FLYER / A — hero central + 6 cards ----------
def flyer_A(d, A):
    cards = ""
    for i, b in enumerate(d["bullets"][:6]):
        x = 70 if i < 3 else 552; y = 895 + (i % 3)*92
        cards += ('<div style="position:absolute;left:%dpx;top:%dpx;width:466px;height:80px;background:%s;border-left:4px solid %s;border-radius:10px"></div>'
                  '<div style="position:absolute;left:%dpx;top:%dpx;width:432px;font-size:21px;color:#fff;font-weight:700">%s</div>'
                  '<div style="position:absolute;left:%dpx;top:%dpx;width:432px;font-size:17px;color:%s">%s</div>') % (x, y, ESC, LAR, x+22, y+13, cap(b["t"]), x+22, y+47, PRATA, cap(b["d"]))
    return _page(
        '<div style="position:absolute;left:0;top:0;width:14px;height:1350px;background:%s"></div>' % LAR +
        '<div style="position:absolute;left:360px;top:430px;width:360px;height:360px;border-radius:50%;background:radial-gradient(circle,rgba(150,170,200,.22),rgba(14,17,22,0) 68%)"></div>' +
        _logo(A["logo"], 70, 58) +
        '<div style="position:absolute;left:74px;top:150px;background:%s;color:#1a0f00;font-weight:700;font-size:19px;letter-spacing:2px;padding:7px 16px;border-radius:5px">%s</div>' % (LAR, cap(d["categoria"])) +
        '<div class="t" style="position:absolute;left:68px;top:196px;font-size:78px;color:#fff;line-height:1">%s</div>' % cap(d["nome"]) +
        '<div class="t" style="position:absolute;left:68px;top:278px;font-size:70px;color:%s;line-height:1">%s</div>' % (LAR, cap(d["destaque"])) +
        '<div style="position:absolute;left:74px;top:370px;font-size:26px;color:%s">%s</div>' % (PRATA, cap(d["sub"])) +
        '<img style="position:absolute;left:%dpx;top:406px;width:%dpx;height:%dpx;object-fit:contain" src="%s">' % (d.get("hx", 206), d.get("hw", 668), d.get("hh", 475), A["cutout"]) +
        cards +
        '<div style="position:absolute;left:70px;top:1180px;width:940px;height:88px;background:%s;border-radius:10px"></div>' % LAR +
        '<div style="position:absolute;left:96px;top:1200px;width:890px;font-size:23px;color:#1a0f00;font-weight:700;line-height:1.35">%s</div>' % cap(d["promo_text"]) +
        '<div style="position:absolute;left:74px;top:1300px;font-size:22px;color:%s;font-weight:700">%s</div>' % (PRATA, cap(d["handle"])) +
        '<div style="position:absolute;right:74px;top:1300px;font-size:22px;color:%s;font-weight:700">%s</div>' % (LAR, cap(d["site"])),
        "Flyer A")

# ---------- FLYER / C — macro + 3 medalhões ----------
def flyer_C(d, A):
    mc = ""; xs = [70, 390, 710]; my = 812
    for (uri, selo), mx in zip(A["selos"], xs):
        mc += ('<img src="%s" style="position:absolute;left:%dpx;top:%dpx;width:300px;height:360px">'
               '<div class="t" style="position:absolute;left:%dpx;top:%dpx;width:240px;text-align:center;font-size:31px;color:#fff">%s</div>'
               '<div style="position:absolute;left:%dpx;top:%dpx;width:240px;text-align:center;font-size:15px;color:%s">%s</div>') % (uri, mx, my, mx+30, my+126, cap(selo["big"]), mx+30, my+172, PRATA, cap(selo["small"]))
    return _page(
        '<div style="position:absolute;left:0;top:0;width:14px;height:1350px;background:%s"></div>' % LAR +
        '<div style="position:absolute;left:360px;top:320px;width:380px;height:380px;border-radius:50%;background:radial-gradient(circle,rgba(150,170,200,.22),rgba(14,17,22,0) 68%)"></div>' +
        _logo(A["logo"], 70, 58) +
        '<div style="position:absolute;left:74px;top:150px;background:%s;color:#1a0f00;font-weight:700;font-size:19px;letter-spacing:2px;padding:7px 16px;border-radius:5px">%s</div>' % (LAR, cap(d["categoria"])) +
        '<div class="t" style="position:absolute;left:68px;top:198px;font-size:64px;color:#fff;line-height:1">%s</div>' % cap(d["sku"]) +
        '<div style="position:absolute;left:74px;top:272px;font-size:25px;color:%s">%s</div>' % (PRATA, cap(d["sub"])) +
        '<img src="%s" style="position:absolute;left:230px;top:336px;width:620px;height:446px;object-fit:contain">' % A["cutout"] +
        mc +
        '<div style="position:absolute;left:70px;top:1196px;width:940px;height:86px;background:%s;border-radius:10px"></div>' % LAR +
        '<div style="position:absolute;left:96px;top:1216px;width:890px;font-size:22px;color:#1a0f00;font-weight:700;line-height:1.32">%s</div>' % cap(d["promo_text"]) +
        '<div style="position:absolute;left:74px;top:1308px;font-size:21px;color:%s;font-weight:700">%s</div>' % (PRATA, cap(d["handle"])) +
        '<div style="position:absolute;right:74px;top:1308px;font-size:21px;color:%s;font-weight:700">%s</div>' % (LAR, cap(d["site"])),
        "Flyer C")

# ---------- POST / lifestyle ----------
def post_lifestyle(d, A):
    h = d["headline_post"]
    return _page(
        '<img src="%s" style="position:absolute;left:0;top:0;width:1080px;height:1350px;object-fit:cover">' % A["postbg"] +
        '<div style="position:absolute;left:0;top:0;width:1080px;height:470px;background:linear-gradient(180deg,rgba(14,17,22,.92),rgba(14,17,22,.4) 50%,rgba(14,17,22,0))"></div>' +
        '<div style="position:absolute;left:0;top:1070px;width:1080px;height:280px;background:linear-gradient(0deg,rgba(14,17,22,.92),rgba(14,17,22,0))"></div>' +
        _logo(A["logo"], 70, 56, 220) +
        '<div class="t" style="position:absolute;left:70px;top:170px;font-size:80px;color:#fff;line-height:1.02">%s</div>' % cap(h[0]) +
        '<div class="t" style="position:absolute;left:70px;top:258px;font-size:80px;color:%s;line-height:1.02">%s</div>' % (LAR, cap(h[1] if len(h) > 1 else "")) +
        '<div style="position:absolute;left:74px;top:366px;font-size:25px;color:#e8eaed;font-weight:700">%s</div>' % cap(d["sub_post"]) +
        '<div style="position:absolute;left:70px;top:1216px;background:%s;color:#1a0f00;font-weight:700;font-size:22px;padding:13px 28px;border-radius:30px">%s</div>' % (LAR, cap(d["cta_post"])) +
        '<div style="position:absolute;right:74px;top:1228px;font-size:22px;color:#fff;font-weight:700">%s</div>' % cap(d["handle"]),
        "Post IG lifestyle")

# ---------- PROMO / faixa ----------
def promo_faixa(d, A):
    p = d["promo"]
    return _page(
        '<div style="position:absolute;left:0;top:0;width:14px;height:1350px;background:%s"></div>' % LAR +
        _logo(A["logo"], 70, 52) +
        '<div style="position:absolute;left:74px;top:150px;font-size:25px;color:%s">%s</div>' % (PRATA, cap(d["sub"])) +
        '<img src="%s" style="position:absolute;left:715px;top:40px;width:300px;height:300px">' % A["burst"] +
        '<div class="t" style="position:absolute;left:715px;top:148px;width:300px;text-align:center;font-size:30px;color:#fff;letter-spacing:2px">%s</div>' % cap(p["selo"]) +
        '<div class="t" style="position:absolute;left:715px;top:186px;width:300px;text-align:center;font-size:74px;color:#fff;line-height:1">%s</div>' % cap(p["desc"]) +
        '<div style="position:absolute;left:300px;top:300px;width:480px;height:420px;border-radius:50%;background:radial-gradient(circle,rgba(150,170,200,.20),rgba(14,17,22,0) 68%)"></div>' +
        '<img src="%s" style="position:absolute;left:210px;top:300px;width:660px;height:475px;object-fit:contain">' % A["cutout"] +
        '<img src="%s" style="position:absolute;left:70px;top:808px;width:940px;height:250px">' % A["panel"] +
        '<div style="position:absolute;left:118px;top:846px;font-size:30px;color:#3a1500;font-weight:700;text-decoration:line-through;opacity:.8">%s</div>' % cap(p["de"]) +
        '<div class="t" style="position:absolute;left:116px;top:882px;font-size:92px;color:#1a0f00;line-height:1">%s</div>' % cap(p["por"]) +
        '<div style="position:absolute;left:120px;top:1000px;font-size:25px;color:#2a1200;font-weight:700">%s</div>' % cap(p["cond"]) +
        '<div style="position:absolute;left:70px;top:1090px;font-size:22px;color:%s">%s</div>' % (PRATA, cap(p["validade"])) +
        '<div style="position:absolute;left:70px;top:1142px;background:#1faa46;color:#fff;font-weight:700;font-size:26px;padding:18px 34px;border-radius:34px">%s</div>' % cap(p["cta"]) +
        '<div style="position:absolute;right:74px;top:1160px;font-size:21px;color:%s;font-weight:700">%s</div>' % (PRATA, cap(d["site"])),
        "Promo faixa")

# ===========================================================================
# Orquestração
# ===========================================================================
ARQ = {"flyer": {"A": flyer_A, "C": flyer_C}, "post": {"lifestyle": post_lifestyle}, "promo": {"faixa": promo_faixa}}

def montar(briefing, tipo, arquetipo):
    """Gera os assets necessários e devolve o HTML self-contained do arquétipo."""
    A = {"logo": _uri(asset_logo())}
    cut = briefing.get("cutout_path")
    if cut: A["cutout"] = _uri_file(cut)
    if tipo == "flyer" and arquetipo == "C":
        icons_default = ["wifi", "chip", "screen"]
        A["selos"] = [(_uri(asset_medalhao(s.get("icon", icons_default[i % 3]))), s) for i, s in enumerate(briefing["selos"][:3])]
    if tipo == "promo":
        A["burst"] = _uri(asset_burst()); A["panel"] = _uri(asset_pricepanel())
    if tipo == "post":
        A["postbg"] = _uri(asset_lifestyle(briefing["ia_lifestyle_path"], cut))
    fn = ARQ.get(tipo, {}).get(arquetipo)
    if not fn: raise ValueError("arquétipo desconhecido: %s/%s" % (tipo, arquetipo))
    return fn(briefing, A)

# ===========================================================================
# Execução direta: gera os 4 arquétipos do KRC5050
# ===========================================================================
if __name__ == "__main__":
    import argparse, json
    _ap = argparse.ArgumentParser(description="Motor de Criativos KX3")
    _ap.add_argument("--briefing", help="JSON com o briefing (inclui cutout_path e ia_lifestyle_path)")
    _ap.add_argument("--tipo"); _ap.add_argument("--arq"); _ap.add_argument("--out")
    _a, _ = _ap.parse_known_args()
    if _a.briefing:
        _d = json.load(open(_a.briefing, encoding="utf-8"))
        open(_a.out, "w", encoding="utf-8").write(montar(_d, _a.tipo, _a.arq))
        print("ok", _a.out); raise SystemExit(0)
    POC = os.path.normpath(os.path.join(HERE, "..", "poc"))
    d = {
        "sku": "KRC5050", "categoria": "CENTRAL MULTIMÍDIA ANDROID",
        "nome": "Central Multimídia", "destaque": "Android 9″ · 4/64GB",
        "sub": "KRC5050 · Padrão 2-DIN · CarPlay sem fio",
        "cutout_path": os.path.join(POC, "produto_cut.png"),
        "ia_lifestyle_path": os.path.join(POC, "ia_lifestyle.jpg"),
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
        # flyer A: o produto vem com a tela já composta; herói menor centralizado
        "hx": 206, "hw": 668, "hh": 475,
    }
    out = os.path.join(HERE, "out"); os.makedirs(out, exist_ok=True)
    jobs = [("flyer", "A", "flyer_A.html"), ("flyer", "C", "flyer_C.html"),
            ("post", "lifestyle", "post.html"), ("promo", "faixa", "promo.html")]
    for tipo, arq, fn in jobs:
        html = montar(d, tipo, arq)
        open(os.path.join(out, fn), "w").write(html)
        print("gerado %s (%d KB)" % (fn, round(len(html)/1024)))
