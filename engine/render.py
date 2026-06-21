#!/usr/bin/env python3
# Renderiza HTML(s) self-contained em PNG 1080x1350 com Chromium headless (Playwright).
# Uso: python3 render.py arquivo1.html [arquivo2.html ...]  -> gera .png ao lado
import sys, os
from playwright.sync_api import sync_playwright

def render(files):
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox", "--disable-gpu"])
        for f in files:
            f = os.path.abspath(f)
            pg = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
            pg.goto("file://" + f)
            pg.wait_for_timeout(500)
            out = f[:-5] + ".png" if f.endswith(".html") else f + ".png"
            pg.screenshot(path=out, clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
            pg.close()
            print("png", os.path.basename(out))
        b.close()

if __name__ == "__main__":
    render(sys.argv[1:])
