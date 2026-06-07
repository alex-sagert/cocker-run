"""
assets.py - Asset-Management: Sprite-Sheet-Slicing + Laden mit Fallback.

Kernstueck ist extract_sprite(): schneidet ein Einzelbild aus dem grossen
Sprite-Sheet. Der AssetManager nutzt die Koordinaten aus settings.SHEET_SLICES
und faellt automatisch auf gezeichnete Platzhalter zurueck, wenn etwas fehlt.
"""

import os
from collections import deque
import pygame

import settings as cfg

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".jfif", ".webp", ".bmp")


def free_sprite(surface, tolerance=68):
    """Macht den zusammenhaengenden Hintergrund transparent.

    Flood-Fill von allen Raendern aus: alle Pixel, die der Hintergrundfarbe
    (Mittel der vier Ecken) innerhalb der Toleranz aehneln und mit dem Rand
    verbunden sind, werden transparent. Das Motiv in der Mitte bleibt erhalten.
    Ideal fuer Konzeptkunst mit (relativ) einheitlichem Hintergrund.
    """
    surf = surface.copy()
    surf.lock()
    w, h = surf.get_size()
    corners = [surf.get_at(c)[:3] for c in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
    ref = tuple(sum(c[i] for c in corners) // 4 for i in range(3))
    thresh = tolerance * 3

    def is_bg(c):
        return abs(c[0] - ref[0]) + abs(c[1] - ref[1]) + abs(c[2] - ref[2]) <= thresh

    visited = set()
    dq = deque()
    border = [(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)] + \
             [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)]
    for s in border:
        if s not in visited and is_bg(surf.get_at(s)[:3]):
            visited.add(s)
            dq.append(s)
    while dq:
        x, y = dq.popleft()
        surf.set_at((x, y), (0, 0, 0, 0))
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                if is_bg(surf.get_at((nx, ny))[:3]):
                    visited.add((nx, ny))
                    dq.append((nx, ny))
    surf.unlock()
    return surf


# ==========================================================================
# Slicing-Utility
# ==========================================================================
def extract_sprite(sheet, x, y, width, height, scale_to=None):
    """Schneidet ein (x, y, width, height)-Rechteck aus dem Sheet.

    Args:
        sheet:    geladenes pygame.Surface (das gesamte Sprite-Sheet)
        x, y:     linke obere Ecke des Ausschnitts im Sheet (Pixel)
        width,height: Groesse des Ausschnitts (Pixel)
        scale_to: optionales (w, h), auf das das Sprite skaliert wird

    Returns:
        pygame.Surface (mit Transparenz) - oder None bei ungueltigem Bereich.
    """
    sheet_w, sheet_h = sheet.get_size()
    # Schutz: Bereich muss innerhalb des Sheets liegen
    if x < 0 or y < 0 or x + width > sheet_w or y + height > sheet_h:
        return None

    sprite = pygame.Surface((width, height), pygame.SRCALPHA)
    sprite.blit(sheet, (0, 0), pygame.Rect(x, y, width, height))
    if scale_to:
        sprite = pygame.transform.smoothscale(sprite, scale_to)
    return sprite


def find_sprite_sheet():
    """Findet die Sheet-Datei: entweder die in settings konfigurierte,
    oder automatisch die erste Bilddatei in assets/, deren Name mit 'e'
    beginnt (so wie deine Sheet-Datei)."""
    # 1) explizit konfiguriert?
    if cfg.SPRITE_SHEET_FILE:
        path = os.path.join(cfg.ASSET_DIR, cfg.SPRITE_SHEET_FILE)
        return path if os.path.exists(path) else None

    # 2) Auto-Erkennung: Datei beginnt mit 'e'/'E'
    search_dirs = [cfg.ASSET_DIR, "."]
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if name.lower().startswith("e") and name.lower().endswith(IMAGE_EXTS):
                return os.path.join(d, name)
    return None


def load_image(filename, size=None):
    """Laedt ein einzelnes Bild aus assets/ (oder None bei Fehlen)."""
    if not filename:
        return None
    path = os.path.join(cfg.ASSET_DIR, filename)
    if not os.path.exists(path):
        return None
    try:
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.smoothscale(img, size)
        return img
    except pygame.error:
        return None


# ==========================================================================
# AssetManager
# ==========================================================================
def _load_baked(name, size):
    """Laedt ein bereits freigestelltes PNG aus assets/baked/."""
    path = os.path.join(cfg.BAKED_DIR, name)
    if not os.path.exists(path):
        return None
    try:
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.smoothscale(img, size)
        return img
    except pygame.error:
        return None


class AssetManager:
    """Laedt & sliced alle Grafiken. Stellt die Spieler-Animation als
    Dict pro FSM-Zustand bereit. Reihenfolge: baked PNG -> Sheet -> Platzhalter."""

    def __init__(self):
        self.sheet = self._load_sheet()
        self.run_frames = []
        self.jump_frame = None
        self.obstacle_images = []
        self.portal = None
        self.chew = None
        self.chew_epic = None
        self.logo = load_image(cfg.LOGO_FILE)

        if self.sheet:
            self._slice_sheet()
        self._load_player_animation()

    def _load_sheet(self):
        path = find_sprite_sheet()
        if not path:
            return None
        try:
            return pygame.image.load(path).convert_alpha()
        except pygame.error:
            return None

    # ------------------------------------------------------ Spieler-Animation
    def _load_player_animation(self):
        """Fuellt self.run_frames + self.jump_frame.
        1) gebackene PNGs (Web-schnell)  2) Sheet-Slicing  3) Platzhalter."""
        size = (cfg.PLAYER_WIDTH, cfg.PLAYER_HEIGHT)

        # 1) baked PNGs bevorzugen
        baked_run = []
        i = 0
        while True:
            spr = _load_baked(f"aiva_run_{i}.png", size)
            if spr is None:
                break
            baked_run.append(spr)
            i += 1
        if baked_run:
            self.run_frames = baked_run
            self.jump_frame = _load_baked("aiva_jump.png", size) or baked_run[0]

        # 2) Falls keine baked-Frames: ggf. aus Sheet (in _slice_sheet gefuellt)
        # 3) Platzhalter, falls weiterhin leer
        if not self.run_frames:
            self.run_frames = [self._placeholder_dog(i) for i in range(4)]
        if self.jump_frame is None:
            self.jump_frame = self._placeholder_dog(0, jumping=True)

        # FSM-Zustaende -> Frame-Listen
        self.player_anim = {
            "IDLE": [self.run_frames[0]],
            "RUN": self.run_frames,
            "JUMP": [self.jump_frame],
            "FALL": [self.jump_frame],
        }

    def _placeholder_dog(self, frame, jumping=False):
        """Einfacher gezeichneter Hund als Fallback-Surface (eine Pose)."""
        surf = pygame.Surface((cfg.PLAYER_WIDTH, cfg.PLAYER_HEIGHT), pygame.SRCALPHA)
        w, h = surf.get_size()
        cy = h // 2
        leg = (frame % 2) * 6 - 3
        pygame.draw.line(surf, cfg.DOG_EAR, (8, cy + 2), (0, cy + 6), 8)            # Schwanz
        pygame.draw.ellipse(surf, cfg.DOG_BODY, (8, cy - 12, w - 28, 32))          # Koerper
        pygame.draw.ellipse(surf, cfg.DOG_BELLY, (14, cy + 2, w - 38, 16))
        pygame.draw.line(surf, cfg.DOG_DARK, (24, h - 16), (24 + leg, h - 2), 7)
        pygame.draw.line(surf, cfg.DOG_DARK, (w - 28, h - 16), (w - 28 - leg, h - 2), 7)
        pygame.draw.circle(surf, cfg.DOG_BODY, (w - 18, cy - 8), 16)               # Kopf
        pygame.draw.ellipse(surf, cfg.DOG_BELLY, (w - 16, cy - 6, 17, 12))
        pygame.draw.circle(surf, cfg.DOG_NOSE, (w - 2, cy), 3)
        ear_y = cy - 22 if jumping else cy - 14
        pygame.draw.ellipse(surf, cfg.DOG_EAR, (w - 30, ear_y, 16, 30))            # Ohr
        return surf

    def _extract(self, coords, scale_to=None, scale_h=None):
        """Schneidet aus, stellt optional frei und skaliert.

        scale_to: feste (w, h)-Zielgroesse.
        scale_h:  nur Zielhoehe; Breite folgt dem Seitenverhaeltnis.
        Freistellen passiert VOR dem Skalieren (genauer)."""
        if not coords:
            return None
        spr = extract_sprite(self.sheet, *coords)   # roh, ohne Skalierung
        if spr is None:
            return None
        if cfg.FREE_SPRITE_BG:
            spr = free_sprite(spr, cfg.FREE_SPRITE_TOLERANCE)
        if scale_h:
            w, h = spr.get_size()
            scale_to = (max(1, int(w * scale_h / h)), scale_h)
        if scale_to:
            spr = pygame.transform.smoothscale(spr, scale_to)
        return spr

    def _slice(self, key, scale_to=None, scale_h=None):
        return self._extract(cfg.SHEET_SLICES.get(key), scale_to=scale_to, scale_h=scale_h)

    def _slice_sheet(self):
        use = cfg.SHEET_USE

        # Hund: Lauf-Frames + Sprung
        if "player" in use:
            for coords in cfg.SHEET_SLICES.get("run", []):
                spr = self._extract(coords, scale_to=(cfg.PLAYER_WIDTH, cfg.PLAYER_HEIGHT))
                if spr:
                    self.run_frames.append(spr)
            self.jump_frame = self._slice("jump", (cfg.PLAYER_WIDTH, cfg.PLAYER_HEIGHT))

        # Hindernisse (Hoehe fixiert, Breite proportional -> keine Verzerrung)
        if "obstacles" in use:
            for key in ("obstacle_plant", "obstacle_ruin"):
                spr = self._slice(key, scale_h=cfg.OBSTACLE_MAX_H)
                if spr:
                    self.obstacle_images.append(spr)

        # Portal
        if "portal" in use:
            self.portal = self._slice("portal", (cfg.PORTAL_WIDTH, cfg.PORTAL_HEIGHT))

        # Kaustangen
        if "chews" in use:
            self.chew = self._slice("chew", (cfg.CHEW_SIZE, cfg.CHEW_SIZE))
            self.chew_epic = self._slice("chew_epic", (cfg.CHEW_SIZE, cfg.CHEW_SIZE))
