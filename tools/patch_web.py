"""
tools/patch_web.py - Nachbearbeitung des pygbag-Web-Builds (build/web/index.html).

pygbag 0.9.3 erzeugt eine index.html mit zwei Problemen, die wir hier fixen:

  1) BrowserFS: die CDN-Datei browserfs.min.js fehlt (404) -> wir laden sie
     stattdessen von jsdelivr. Ohne BrowserFS startet das Spiel nicht
     ("PyMain: BrowserFS not found").

  2) devicePixelRatio: bei nicht-ganzzahligem DPR (z.B. 1.5 bei Windows-
     150%-Skalierung) dimensioniert pygbag den Canvas auf 1x1 -> grauer
     Bildschirm. Wir erzwingen DPR=1, bevor pygbag startet.

Aufruf nach dem Build:
    python tools/bake_sprites.py        # (einmalig / bei Sprite-Aenderung)
    pygbag --build main.py
    python tools/patch_web.py
"""

import os
import sys

INDEX = os.path.join("build", "web", "index.html")

BROWSERFS_BROKEN = "https://pygame-web.github.io/cdn/0.9.3//browserfs.min.js"
BROWSERFS_FIX = "https://cdn.jsdelivr.net/npm/browserfs@1.4.3/dist/browserfs.min.js"
DPR_OVERRIDE = ('<script>Object.defineProperty(window,"devicePixelRatio",'
                '{get:function(){return 1;}});</script>')


def main():
    if not os.path.exists(INDEX):
        print(f"FEHLER: {INDEX} nicht gefunden. Erst 'pygbag --build main.py' ausfuehren.")
        sys.exit(1)

    html = open(INDEX, encoding="utf-8").read()
    changed = []

    # 1) BrowserFS auf jsdelivr umbiegen (auch Variante mit einfachem Slash)
    for broken in (BROWSERFS_BROKEN, BROWSERFS_BROKEN.replace("0.9.3//", "0.9.3/")):
        if broken in html:
            html = html.replace(broken, BROWSERFS_FIX)
            changed.append("BrowserFS -> jsdelivr")
            break

    # 2) devicePixelRatio=1 erzwingen (nur einmal, vor dem pythons.js-Script)
    head = html.split("pythons.js")[0]
    if "devicePixelRatio" not in head:
        html = html.replace('<html lang="en-us">',
                             '<html lang="en-us">' + DPR_OVERRIDE, 1)
        changed.append("devicePixelRatio=1")

    open(INDEX, "w", encoding="utf-8").write(html)
    if changed:
        print("Web-Build gepatcht:", ", ".join(changed))
    else:
        print("Keine Aenderung noetig (schon gepatcht).")


if __name__ == "__main__":
    main()
