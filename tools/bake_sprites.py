"""
tools/bake_sprites.py - Einmaliges "Backen" der Aiva-Sprites.

Schneidet die Hunde-Frames aus dem Sprite-Sheet, stellt den Hintergrund
per Flood-Fill frei und speichert sie als fertige, transparente PNGs unter
assets/baked/. Vorteile:
    - Web (pygbag) laedt fertige PNGs -> kein langsames Per-Pixel-Freistellen
      im Browser zur Laufzeit.
    - Reproduzierbar: Koordinaten/Toleranz kommen aus settings.py.

Aufruf (einmalig bzw. nach Koordinaten-Aenderung):
    python tools/bake_sprites.py
"""

import os
import sys
import pygame

# settings/assets aus dem Projekt-Root importierbar machen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import settings as cfg
from assets import extract_sprite, free_sprite, find_sprite_sheet

BAKED_DIR = os.path.join(cfg.ASSET_DIR, "baked")


def bake():
    pygame.init()
    pygame.display.set_mode((8, 8))   # noetig fuer convert_alpha

    sheet_path = find_sprite_sheet()
    if not sheet_path:
        print("FEHLER: kein Sprite-Sheet gefunden (Datei beginnt mit 'e').")
        return
    sheet = pygame.image.load(sheet_path).convert_alpha()
    os.makedirs(BAKED_DIR, exist_ok=True)

    def save(coords, name, canvas):
        """Schneidet aus, stellt frei, croppt auf die Hunde-Kontur,
        skaliert seitenverhaeltnis-erhaltend und richtet am Boden aus.
        Ergebnis: konsistente, unverzerrte, vollstaendige Sprites."""
        cw, ch = canvas
        spr = extract_sprite(sheet, *coords)
        if spr is None:
            print("  uebersprungen (Bereich ungueltig):", name)
            return
        spr = free_sprite(spr, cfg.FREE_SPRITE_TOLERANCE)

        # Nur KLEINE Streupixel entfernen, aber alle groesseren Teile des
        # Hundes behalten (Kopf/Koerper/Beine koennen nach dem Freistellen
        # getrennte Inseln sein). -> sauber ohne den Hund zu zerstoeren.
        try:
            m = pygame.mask.from_surface(spr, 40)
            comps = m.connected_components(minimum=60)   # Inseln >= 60 px
            if comps:
                keepmask = comps[0]
                for c in comps[1:]:
                    keepmask.draw(c, (0, 0))             # Vereinigung
                keep = keepmask.to_surface(setcolor=(255, 255, 255, 255),
                                           unsetcolor=(0, 0, 0, 0))
                spr.blit(keep, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        except Exception as e:
            print("  (Despeckle uebersprungen:", e, ")")

        # auf die tatsaechliche (nicht-transparente) Kontur zuschneiden
        bbox = spr.get_bounding_rect(min_alpha=12)
        if bbox.width < 4 or bbox.height < 4:
            print("  WARN leere Kontur:", name)
            return
        spr = spr.subsurface(bbox).copy()

        # seitenverhaeltnis-erhaltend in die Canvas einpassen (kleiner Rand)
        pad = 4
        max_w, max_h = cw - 2 * pad, ch - 2 * pad
        scale = min(max_w / spr.get_width(), max_h / spr.get_height())
        new_size = (max(1, round(spr.get_width() * scale)),
                    max(1, round(spr.get_height() * scale)))
        spr = pygame.transform.smoothscale(spr, new_size)

        # auf transparente Canvas: horizontal zentriert, am BODEN ausgerichtet
        out_surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
        x = (cw - new_size[0]) // 2
        y = ch - pad - new_size[1]
        out_surf.blit(spr, (x, y))

        out = os.path.join(BAKED_DIR, name)
        pygame.image.save(out_surf, out)
        print(f"  gebacken: {out}  (Kontur {bbox.width}x{bbox.height})")

    size = (cfg.PLAYER_WIDTH, cfg.PLAYER_HEIGHT)
    for i, coords in enumerate(cfg.SHEET_SLICES.get("run", [])):
        save(coords, f"aiva_run_{i}.png", size)
    save(cfg.SHEET_SLICES["jump"], "aiva_jump.png", size)

    print("Fertig. Baked-Sprites liegen in:", BAKED_DIR)


if __name__ == "__main__":
    bake()
