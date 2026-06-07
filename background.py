"""
background.py - 2.5D-Parallax-Hintergrund mit mehreren Tiefen-Ebenen.

Ebenen (von hinten nach vorne):
    1) Himmel-Verlauf (statisch, mit Dunst/Depth-of-Field)
    2) Ferne Berge        - sehr langsam
    3) Wolken             - langsam
    4) Huegel (Mittelgrund) - mittel
    5) Boden (Gameplay-Ebene)
    6) Vordergrund-Gras   - schneller als der Boden (vor den Entities!)

Beim Level-Wechsel faehrt die Farbpalette weich in die Zielpalette.
"""

import math
import random
import pygame

import settings as cfg


def _lerp(a, b, t):
    return a + (b - a) * t


def _lerp_color(c1, c2, t):
    return tuple(int(_lerp(c1[i], c2[i], t)) for i in range(3))


class ParallaxBackground:
    # relative Geschwindigkeiten der Ebenen (Faktor auf scroll_speed)
    SPEED_FAR = 0.15
    SPEED_CLOUD = 0.25
    SPEED_HILL = 0.45
    SPEED_GROUND = 1.0
    SPEED_FOREGROUND = 1.35

    def __init__(self, palette):
        self.cur = dict(palette)
        self.target = dict(palette)
        self.transition = 1.0           # 1.0 = fertig

        # Scroll-Offsets je Ebene
        self.off_far = 0.0
        self.off_cloud = 0.0
        self.off_hill = 0.0
        self.off_ground = 0.0
        self.off_fore = 0.0

        # feste Zufalls-Layouts (einmalig, damit es nicht flackert)
        rnd = random.Random(42)
        self.mountains = [(rnd.randint(0, cfg.SCREEN_WIDTH), rnd.randint(70, 130))
                          for _ in range(6)]
        self.clouds = [(rnd.randint(0, cfg.SCREEN_WIDTH), rnd.randint(40, 150))
                       for _ in range(4)]
        self.grass_blades = [rnd.randint(0, cfg.SCREEN_WIDTH) for _ in range(40)]

        self._sky = None
        self._rebuild_sky()

    # ---------------------------------------------------------- Palette
    def set_palette(self, palette):
        """Startet einen weichen Uebergang zur neuen Level-Palette."""
        self.cur = dict(self._current_palette())   # von aktuellem Stand aus
        self.target = dict(palette)
        self.transition = 0.0

    def _current_palette(self):
        """Aktuell sichtbare (ggf. interpolierte) Palette."""
        keys = ("sky_top", "sky_bottom", "far", "hill",
                "ground", "ground_edge", "grass")
        t = self.transition
        return {k: _lerp_color(self.cur[k], self.target[k], t) for k in keys}

    def _rebuild_sky(self):
        pal = self._current_palette()
        sky = pygame.Surface((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
        top, bottom = pal["sky_top"], pal["sky_bottom"]
        for y in range(cfg.GROUND_Y):
            t = y / cfg.GROUND_Y
            pygame.draw.line(sky, _lerp_color(top, bottom, t),
                             (0, y), (cfg.SCREEN_WIDTH, y))
        self._sky = sky

    # ---------------------------------------------------------- Update
    def update(self, dt, scroll_speed):
        # scroll_speed in px/s -> mit dt multiplizieren (framerate-unabhaengig)
        w = cfg.SCREEN_WIDTH
        self.off_far = (self.off_far + scroll_speed * self.SPEED_FAR * dt) % w
        self.off_cloud = (self.off_cloud + scroll_speed * self.SPEED_CLOUD * dt) % (w + 200)
        self.off_hill = (self.off_hill + scroll_speed * self.SPEED_HILL * dt) % w
        self.off_ground = (self.off_ground + scroll_speed * self.SPEED_GROUND * dt) % 48
        self.off_fore = (self.off_fore + scroll_speed * self.SPEED_FOREGROUND * dt) % 40

        if self.transition < 1.0:
            self.transition = min(1.0, self.transition + dt / cfg.PORTAL_TRANSITION_TIME)
            self._rebuild_sky()           # Himmel waehrend Uebergang neu faerben

    # ---------------------------------------------------------- Draw (hinten)
    def draw_back(self, surface):
        pal = self._current_palette()
        surface.blit(self._sky, (0, 0))

        # 2) ferne Berge (Depth of Field: Richtung Himmel aufgehellt)
        far = _lerp_color(pal["far"], pal["sky_bottom"], 0.35)
        for mx, mh in self.mountains:
            x = (mx - self.off_far) % cfg.SCREEN_WIDTH
            self._triangle(surface, far, x, mh)
            self._triangle(surface, far, x - cfg.SCREEN_WIDTH, mh)

        # 3) Wolken
        for cx, cy in self.clouds:
            x = (cx - self.off_cloud) % (cfg.SCREEN_WIDTH + 200) - 100
            self._cloud(surface, x, cy)

        # 4) Huegel (Mittelgrund)
        for base in (0, cfg.SCREEN_WIDTH):
            x = base - self.off_hill
            pygame.draw.ellipse(surface, pal["hill"], (x, cfg.GROUND_Y - 70, 460, 180))
            pygame.draw.ellipse(surface, pal["hill"], (x + 300, cfg.GROUND_Y - 46, 380, 130))

        # 5) Boden
        pygame.draw.rect(surface, pal["ground"],
                         (0, cfg.GROUND_Y, cfg.SCREEN_WIDTH, cfg.GROUND_HEIGHT))
        pygame.draw.rect(surface, pal["ground_edge"],
                         (0, cfg.GROUND_Y, cfg.SCREEN_WIDTH, 7))
        pygame.draw.rect(surface, cfg.DIRT_COLOR,
                         (0, cfg.GROUND_Y + 20, cfg.SCREEN_WIDTH, cfg.GROUND_HEIGHT - 20))
        # scrollende Bodenmarkierungen
        for x in range(-48, cfg.SCREEN_WIDTH + 48, 48):
            gx = x - int(self.off_ground)
            pygame.draw.line(surface, pal["ground_edge"],
                             (gx, cfg.GROUND_Y + 12), (gx + 10, cfg.GROUND_Y + 12), 3)

    # ---------------------------------------------------------- Draw (vorne)
    def draw_foreground(self, surface):
        """Vordergrund-Gras VOR den Entities -> verstaerkt die Tiefe."""
        pal = self._current_palette()
        for bx in self.grass_blades:
            x = (bx - self.off_fore) % cfg.SCREEN_WIDTH
            h = 14 + (bx % 10)
            pygame.draw.line(surface, pal["grass"],
                             (x, cfg.SCREEN_HEIGHT), (x - 3, cfg.SCREEN_HEIGHT - h), 3)
            pygame.draw.line(surface, pal["grass"],
                             (x + 3, cfg.SCREEN_HEIGHT), (x + 5, cfg.SCREEN_HEIGHT - h + 3), 3)

    # ---------------------------------------------------------- Helfer
    @staticmethod
    def _triangle(surface, color, x, h):
        base_y = cfg.GROUND_Y
        pygame.draw.polygon(surface, color,
                            [(x, base_y), (x + 110, base_y - h), (x + 220, base_y)])

    @staticmethod
    def _cloud(surface, x, y):
        x = int(x)
        c = cfg.CLOUD_COLOR
        pygame.draw.circle(surface, c, (x, y), 26)
        pygame.draw.circle(surface, c, (x + 30, y + 8), 22)
        pygame.draw.circle(surface, c, (x - 28, y + 10), 20)
        pygame.draw.rect(surface, c, (x - 28, y + 8, 60, 18))
