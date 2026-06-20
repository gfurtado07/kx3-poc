// ---------------------------------------------------------------------------
// Motor de Criativos KX3 — Template Engine (flyer de divulgação)
// Transforma um briefing + foto (data-URI) em HTML self-contained, com
// ARQUÉTIPOS de layout variados. Cada arquétipo é um layout distinto, mas
// todos travados nos tokens de marca KX3. É o "diretor de arte" do motor B.
//
// Uso:  node gerador.js   (lê ./foto.png, gera ./a.html e ./b.html do KRC5050)
// Em produção: o workflow chama montar(briefing, arquetipo) com os dados reais.
// ---------------------------------------------------------------------------

const KX3 = { preto: "#0e1116", laranja: "#FF6600", prata: "#A7A9AC", branco: "#ffffff", escuro: "#161b22" };
const FONT_TITULO = '"Arial Black", Impact, "Haettenschweiler", sans-serif';
const FONT_TEXTO = "Arial, Helvetica, sans-serif";

// envelopa o conteúdo numa página self-contained de 1080x1350 (4:5)
function page(inner) {
  return `<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><style>
*{margin:0;padding:0;box-sizing:border-box}
.page{position:relative;width:1080px;height:1350px;background:${KX3.preto};font-family:${FONT_TEXTO};overflow:hidden}
.t{font-family:${FONT_TITULO};font-weight:900}
</style></head><body><div class="page" data-document-role="page" data-label="Flyer KX3">${inner}</div></body></html>`;
}

function cap(s) { return (s || "").toString(); }

// ---------- ARQUÉTIPO A — Hero central ----------
function arqA(d) {
  const bullets = d.bullets.slice(0, 6);
  const cols = bullets.map((b, i) => {
    const x = i < 3 ? 74 : 580, y = 905 + (i % 3) * 80;
    return `<div style="position:absolute;left:${x - 22}px;top:${y + 5}px;width:9px;height:9px;border-radius:50%;background:${KX3.laranja}"></div>
<div style="position:absolute;left:${x}px;top:${y - 8}px;font-size:25px;color:#fff;font-weight:700">${cap(b.t)}</div>
<div style="position:absolute;left:${x}px;top:${y + 25}px;font-size:19px;color:${KX3.prata}">${cap(b.d)}</div>`;
  }).join("");
  return page(`
<div style="position:absolute;left:0;top:0;width:14px;height:1350px;background:${KX3.laranja}"></div>
<div class="t" style="position:absolute;left:70px;top:60px;font-size:64px;color:#fff;letter-spacing:1px">KX<span style="color:${KX3.laranja}">3</span></div>
<div style="position:absolute;left:74px;top:152px;background:${KX3.laranja};color:#1a0f00;font-weight:700;font-size:20px;letter-spacing:2px;padding:8px 18px;border-radius:5px">${cap(d.categoria)}</div>
<div class="t" style="position:absolute;left:68px;top:206px;font-size:118px;color:#fff;letter-spacing:-2px;line-height:1">${cap(d.sku)}</div>
<div style="position:absolute;left:74px;top:350px;font-size:25px;color:${KX3.prata}">${cap(d.sub)}</div>
<img style="position:absolute;left:215px;top:420px;width:650px;height:430px;object-fit:contain" src="${d.img}">
${cols}
<div style="position:absolute;left:70px;top:1175px;width:940px;height:92px;background:${KX3.laranja};border-radius:10px"></div>
<div style="position:absolute;left:96px;top:1196px;width:890px;font-size:24px;color:#1a0f00;font-weight:700;line-height:1.35">${cap(d.promo)}</div>
<div style="position:absolute;left:74px;top:1300px;font-size:22px;color:${KX3.prata};font-weight:700">${cap(d.handle)}</div>
<div style="position:absolute;right:74px;top:1300px;font-size:22px;color:${KX3.laranja};font-weight:700">${cap(d.site)}</div>`);
}

// ---------- ARQUÉTIPO B — Split vertical (foto à esquerda, specs em faixa) ----------
function arqB(d) {
  const bullets = d.bullets.slice(0, 6);
  const list = bullets.map((b, i) => {
    const y = 250 + i * 132;
    return `<div style="position:absolute;left:632px;top:${y}px;width:9px;height:9px;border-radius:50%;background:#1a0f00"></div>
<div style="position:absolute;left:656px;top:${y - 9}px;width:360px;font-size:23px;color:#1a0f00;font-weight:700">${cap(b.t)}</div>
<div style="position:absolute;left:656px;top:${y + 22}px;width:360px;font-size:17px;color:#3a2200">${cap(b.d)}</div>`;
  }).join("");
  return page(`
<div style="position:absolute;left:0;top:0;width:610px;height:1350px;background:${KX3.escuro}"></div>
<div style="position:absolute;left:610px;top:0;width:470px;height:1350px;background:${KX3.laranja}"></div>
<div class="t" style="position:absolute;left:60px;top:54px;font-size:56px;color:#fff;letter-spacing:1px;z-index:2">KX<span style="color:${KX3.laranja}">3</span></div>
<img style="position:absolute;left:20px;top:240px;width:570px;height:560px;object-fit:contain" src="${d.img}">
<div style="position:absolute;left:60px;top:150px;font-size:18px;color:${KX3.laranja};font-weight:700;letter-spacing:2px">${cap(d.categoria)}</div>
<div class="t" style="position:absolute;left:56px;top:880px;font-size:120px;color:#fff;letter-spacing:-2px;line-height:.95">${cap(d.sku)}</div>
<div style="position:absolute;left:60px;top:1030px;width:520px;font-size:24px;color:${KX3.prata};line-height:1.4">${cap(d.sub)}</div>
<div style="position:absolute;left:60px;top:1180px;width:520px;font-size:21px;color:#fff;font-weight:700;border-left:4px solid ${KX3.laranja};padding-left:16px;line-height:1.35">${cap(d.promo)}</div>
<div style="position:absolute;left:656px;top:150px;font-size:30px;color:#1a0f00;font-weight:900;font-family:${FONT_TITULO}">DESTAQUES</div>
${list}
<div style="position:absolute;left:656px;top:1255px;font-size:20px;color:#1a0f00;font-weight:700">${cap(d.handle)}</div>
<div style="position:absolute;left:656px;top:1285px;font-size:20px;color:#1a0f00;font-weight:700">${cap(d.site)}</div>`);
}

const ARQ = { a: arqA, b: arqB };
function montar(briefing, arquetipo) { return (ARQ[arquetipo] || arqA)(briefing); }
module.exports = { montar, ARQ };

// ----- execução direta: gera os arquétipos do KRC5050 com a foto local -----
if (require.main === module) {
  const fs = require("fs");
  const b64 = fs.readFileSync("foto.png").toString("base64");
  const d = {
    sku: "KRC5050",
    categoria: "CENTRAL MULTIMÍDIA ANDROID",
    sub: 'Multimídia Android 2-DIN · Tela 9" Full HD · CarPlay sem fio',
    img: `data:image/png;base64,${b64}`,
    bullets: [
      { t: "CarPlay & Android Auto", d: "sem fio, conecta sozinho" },
      { t: "Octacore + 4GB RAM", d: "64GB de memória" },
      { t: "Câmera ré + frontal", d: "Full HD" },
      { t: "Bluetooth 5.2 · Wi-Fi · GPS", d: "conectividade total" },
      { t: "4×52W · EQ 32 bandas", d: "áudio Dolby Digital" },
      { t: 'Tela 9" Full HD', d: "capacitiva, sensível ao toque" }
    ],
    promo: "Octacore e 4GB de RAM: muito mais fluidez que aparelhos quad-core ou 2GB de memória.",
    handle: "@kx3acessorios",
    site: "www.kx3.com.br"
  };
  for (const a of Object.keys(ARQ)) {
    fs.writeFileSync(`${a}.html`, montar(d, a));
    console.log(`gerado ${a}.html (${fs.statSync(`${a}.html`).size} bytes)`);
  }
}
