"""
entities.py - Spielobjekte als pygame.sprite.Sprite (ECS-naher Ansatz).

Profi-Systeme:
  * Vektor-Physik: Vector2 fuer pos / vel / acc, Schwerkraft, Reibung, Momentum.
  * Delta-Time: alle Bewegungen * dt (Framerate-unabhaengig).
  * FSM: Player-Animation ueber Zustaende IDLE / RUN / JUMP / FALL.
  * Sprite-Gruppen: alle Entities erben von Sprite (image + rect + hitbox).
"""

import math
import random
import pygame

import settings as cfg
# Vector2 + Sprite/Group ueber die Kompatibilitaetsschicht (Desktop: echtes
# pygame.sprite/pygame.Vector2; Browser/pygbag: schlanker Fallback).
from compat import Vector2, Sprite


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def hitbox_collide(a, b):
    """Kollisions-Callback fuer sprite-Gruppen: nutzt faire Hitboxen."""
    return a.hitbox.colliderect(b.hitbox)


def draw_shadow(surface, center_x, width, scale=1.0):
    w = max(8, int(width * scale))
    h = max(4, int(w * 0.32))
    shadow = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, cfg.SHADOW_COLOR, (0, 0, w, h))
    surface.blit(shadow, (center_x - w // 2, cfg.GROUND_Y - h // 2 + 4))


# ==========================================================================
# Player (Aiva) - Vektor-Physik + FSM
# ==========================================================================
class Player(Sprite):
    IDLE, RUN, JUMP, FALL = "IDLE", "RUN", "JUMP", "FALL"

    def __init__(self, assets):
        super().__init__()
        self.assets = assets
        self.anim = assets.player_anim

        # --- Vektor-Kinematik ---
        self.pos = Vector2(cfg.PLAYER_START_X, cfg.GROUND_Y - cfg.PLAYER_HEIGHT)
        self.vel = Vector2(0, 0)
        self.acc = Vector2(0, 0)
        self.on_ground = True
        self.jump_held = False
        self.world_moving = True        # im Lauf: Boden -> RUN statt IDLE

        # Komfort-Timer (faires Sprung-Gefuehl)
        self.coyote_timer = 0.0
        self.jump_buffer_timer = 0.0

        # --- FSM / Animation ---
        self.state = self.RUN
        self.anim_timer = 0.0
        # Lauf-Tempo der Animation (wird vom Spiel ans Welttempo angepasst)
        self.run_fps = cfg.SCROLL_SPEED / cfg.RUN_STRIDE_PX

        self.image = self.anim[self.RUN][0]
        self.rect = self.image.get_rect(topleft=self.pos)

    # --------------------------------------------------------- Hitbox
    @property
    def hitbox(self):
        return self.rect.inflate(-2 * cfg.HITBOX_INSET_X, -2 * cfg.HITBOX_INSET_Y)

    # --------------------------------------------------------- Sprung
    def jump(self):
        """Springt sofort (am Boden ODER innerhalb der Coyote-Zeit).
        Sonst wird der Sprung kurz vorgemerkt (Jump-Buffer)."""
        if self.on_ground or self.coyote_timer > 0:
            self._do_jump()
            return True
        self.jump_buffer_timer = cfg.JUMP_BUFFER_TIME
        return False

    def _do_jump(self):
        running = self.vel.x > 60            # nimmt gerade Anlauf?
        self.vel.y = cfg.JUMP_SPEED + (cfg.MOMENTUM_JUMP_BONUS if running else 0)
        self.on_ground = False
        self.coyote_timer = 0.0
        self.jump_held = True

    def release_jump(self):
        self.jump_held = False
        if self.vel.y < 0:
            self.vel.y *= cfg.JUMP_CUT_MULTIPLIER

    # --------------------------------------------------------- Update
    def update(self, dt, inp):
        """dt in Sekunden. inp ist ein InputState (left/right/jump)."""
        # 1) horizontale Beschleunigung aus Input
        self.acc.x = 0.0
        if inp.left:
            self.acc.x -= cfg.PLAYER_ACCEL
        if inp.right:
            self.acc.x += cfg.PLAYER_ACCEL
        self.vel.x += self.acc.x * dt

        # 2) Reibung (exponentiell -> framerate-unabhaengig)
        friction = cfg.GROUND_FRICTION if self.on_ground else cfg.AIR_FRICTION
        self.vel.x *= friction ** dt
        self.vel.x = _clamp(self.vel.x, -cfg.MAX_RUN_SPEED, cfg.MAX_RUN_SPEED)

        # 3) Schwerkraft (schnelleres Fallen fuer knackiges Gefuehl)
        g = cfg.GRAVITY * (cfg.FALL_MULTIPLIER if self.vel.y > 0 else 1.0)
        self.vel.y += g * dt
        if self.vel.y > cfg.MAX_FALL_SPEED:
            self.vel.y = cfg.MAX_FALL_SPEED

        # 4) Integration (Position aus Geschwindigkeit)
        self.pos.x += self.vel.x * dt
        self.pos.y += self.vel.y * dt

        landed = self._resolve_bounds(dt)

        # Komfort-Timer aktualisieren
        if self.on_ground:
            self.coyote_timer = cfg.COYOTE_TIME       # am Boden: Coyote auffrischen
        else:
            self.coyote_timer = max(0.0, self.coyote_timer - dt)
        self.jump_buffer_timer = max(0.0, self.jump_buffer_timer - dt)
        # Vorgemerkten Sprung bei der Landung ausloesen
        if landed and self.jump_buffer_timer > 0:
            self._do_jump()
            self.jump_buffer_timer = 0.0

        self._update_state()
        self._animate(dt)

        self.rect = self.image.get_rect(topleft=(round(self.pos.x), round(self.pos.y)))
        return landed

    def _resolve_bounds(self, dt):
        w, h = cfg.PLAYER_WIDTH, cfg.PLAYER_HEIGHT
        # horizontale Grenzen (in der Luft weiter dank Momentum)
        right_bound = cfg.PLAYER_MAX_X + cfg.MOMENTUM_MAX_X_EXTEND
        if self.pos.x < cfg.PLAYER_MIN_X:
            self.pos.x = cfg.PLAYER_MIN_X
            self.vel.x = max(self.vel.x, 0)
        if self.pos.x + w > right_bound:
            self.pos.x = right_bound - w
            self.vel.x = min(self.vel.x, 0)
        # am Boden sanft ins linke Drittel zurueckgleiten
        if self.on_ground and (self.pos.x + w) > cfg.PLAYER_MAX_X:
            self.pos.x = max(cfg.PLAYER_MAX_X - w, self.pos.x - cfg.MAX_RUN_SPEED * dt)

        # Boden-Kollision
        landed = False
        if self.pos.y + h >= cfg.GROUND_Y:
            self.pos.y = cfg.GROUND_Y - h
            if not self.on_ground:
                landed = True
            self.vel.y = 0.0
            self.on_ground = True
        else:
            self.on_ground = False
        return landed

    def _update_state(self):
        """FSM: Zustand aus der Physik ableiten."""
        if not self.on_ground:
            new = self.JUMP if self.vel.y < 0 else self.FALL
        else:
            new = self.RUN if self.world_moving or abs(self.vel.x) > 30 else self.IDLE
        if new != self.state:
            self.state = new
            self.anim_timer = 0.0

    def _animate(self, dt):
        frames = self.anim[self.state]
        if len(frames) > 1:
            # RUN: Tempo an die Welt gekoppelt (Beine passen zum Boden)
            fps = self.run_fps if self.state == self.RUN else cfg.ANIM_FPS_IDLE
            self.anim_timer += dt
            idx = int(self.anim_timer * fps) % len(frames)
        else:
            idx = 0
        self.image = frames[idx]

    # --------------------------------------------------------- Draw-Helfer
    def draw_shadow(self, surface):
        height_above = cfg.GROUND_Y - self.rect.bottom
        scale = max(0.45, 1.0 - height_above / 320)
        draw_shadow(surface, self.rect.centerx, self.rect.width, scale)


# ==========================================================================
# ScrollSprite - Basis fuer alles, was nach links scrollt
# ==========================================================================
class ScrollSprite(Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.pos = Vector2(x, y)

    def scroll(self, dt, scroll_speed):
        self.pos.x -= scroll_speed * dt
        self.rect.x = round(self.pos.x)
        if self.rect.right < -20:
            self.kill()


# ==========================================================================
# Obstacle
# ==========================================================================
class Obstacle(ScrollSprite):
    def __init__(self, x, image=None):
        if image:
            w, h = image.get_size()
        else:
            w = random.randint(cfg.OBSTACLE_MIN_W, cfg.OBSTACLE_MAX_W)
            h = random.randint(cfg.OBSTACLE_MIN_H, cfg.OBSTACLE_MAX_H)
        # Basisklasse zuerst (Web-pygame setzt sonst self.image zurueck)
        super().__init__(x, cfg.GROUND_Y - h)
        self.image = image if image else self._make_placeholder(w, h)
        self.rect = self.image.get_rect(topleft=(x, cfg.GROUND_Y - h))

    @staticmethod
    def _make_placeholder(w, h):
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        if random.random() < 0.5:
            # --- Felsen (grau, mit Schattierung) ---
            base = (120, 120, 130)
            pygame.draw.ellipse(surf, (90, 90, 100), (0, h - int(h * 0.85), w, int(h * 0.85)))
            pygame.draw.ellipse(surf, base, (2, h - int(h * 0.80), w - 4, int(h * 0.80)))
            pygame.draw.ellipse(surf, (160, 160, 170),
                                (int(w * 0.18), h - int(h * 0.7), int(w * 0.45), int(h * 0.4)))
        else:
            # --- Busch (gruen, mehrere Kugeln) ---
            dark, mid, light = (40, 110, 50), (60, 150, 70), (90, 190, 100)
            pygame.draw.ellipse(surf, dark, (0, h - int(h * 0.55), w, int(h * 0.55)))
            for (cx, cy, r, col) in (
                (int(w * 0.30), int(h * 0.55), int(w * 0.30), mid),
                (int(w * 0.70), int(h * 0.55), int(w * 0.30), mid),
                (int(w * 0.50), int(h * 0.35), int(w * 0.32), light)):
                pygame.draw.circle(surf, col, (cx, cy), r)
        return surf

    @property
    def hitbox(self):
        return self.rect.inflate(-2 * cfg.OBSTACLE_HITBOX_INSET_X,
                                 -2 * cfg.OBSTACLE_HITBOX_INSET_Y)

    def update(self, dt, scroll_speed):
        self.scroll(dt, scroll_speed)

    def draw_shadow(self, surface):
        draw_shadow(surface, self.rect.centerx, self.rect.width)


# ==========================================================================
# Chew (Kaustange)
# ==========================================================================
class Chew(ScrollSprite):
    def __init__(self, x, assets):
        # Sorte wuerfeln: angel (selten) -> epic -> standard
        r = random.random()
        if r < cfg.CHEW_ANGEL_CHANCE:
            self.kind = "angel"
            self.points = cfg.CHEW_ANGEL_POINTS
        elif r < cfg.CHEW_ANGEL_CHANCE + cfg.CHEW_EPIC_CHANCE:
            self.kind = "epic"
            self.points = cfg.CHEW_EPIC_POINTS
        else:
            self.kind = "standard"
            self.points = cfg.CHEW_STANDARD_POINTS
        self.epic = (self.kind == "epic")    # Rueckwaerts-Kompatibilitaet

        if random.random() < 0.5:
            base_y = cfg.GROUND_Y - cfg.CHEW_SIZE - 8
        else:
            base_y = cfg.GROUND_Y - cfg.CHEW_SIZE - random.randint(70, 140)
        # WICHTIG: Basisklasse ZUERST initialisieren (im Web-pygame setzt
        # Sprite.__init__ self.image zurueck) - danach erst das Bild setzen.
        super().__init__(x, base_y)
        self.base_y = base_y
        self.bob_phase = random.uniform(0, math.tau)

        img = {"epic": assets.chew_epic, "standard": assets.chew,
               "angel": getattr(assets, "chew_angel", None)}[self.kind]
        self.image = img if img else self._make_placeholder()
        self.rect = self.image.get_rect(topleft=(x, base_y))

    @staticmethod
    def _disc(surf, cx, cy, r, color, alpha):
        """Weicher Farbkreis mit Alpha ueber eine Temp-Surface (web-sicher,
        statt eine RGBA-Farbe direkt an pygame.draw zu geben)."""
        g = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(g, (color[0], color[1], color[2], alpha), (r + 1, r + 1), r)
        surf.blit(g, (cx - r - 1, cy - r - 1))

    def _make_placeholder(self):
        size = cfg.CHEW_SIZE
        surf = pygame.Surface((size + 22, size + 22), pygame.SRCALPHA)
        cx = cy = surf.get_width() // 2

        if self.kind == "epic":
            color = cfg.CHEW_EPIC_COLOR
            self._disc(surf, cx, cy, size // 2 + 8, cfg.CHEW_EPIC_COLOR, 70)
        elif self.kind == "angel":
            color = cfg.CHEW_ANGEL_COLOR
            self._disc(surf, cx, cy, size // 2 + 9, cfg.CHEW_ANGEL_GLOW, 90)
        else:
            color = cfg.CHEW_COLOR

        # Knochen (ohne border_radius -> web-sicher)
        pygame.draw.rect(surf, color, (cx - 15, cy - 5, 30, 10))
        for ex in (cx - 15, cx + 15):
            pygame.draw.circle(surf, color, (ex, cy - 5), 6)
            pygame.draw.circle(surf, color, (ex, cy + 5), 6)

        if self.kind == "angel":
            pygame.draw.ellipse(surf, cfg.CHEW_ANGEL_GLOW, (cx - 12, cy - 20, 24, 9), 3)
        return surf

    @property
    def hitbox(self):
        return self.rect.inflate(-10, -10)

    def update(self, dt, scroll_speed):
        self.pos.x -= scroll_speed * dt
        self.bob_phase += 4.0 * dt
        self.rect.x = round(self.pos.x)
        self.rect.y = round(self.base_y + math.sin(self.bob_phase) * 4)
        if self.rect.right < -20:
            self.kill()


# ==========================================================================
# Portal (Level-Wechsel) - mit pulsierendem, neu gerendertem Image
# ==========================================================================
class Portal(ScrollSprite):
    def __init__(self, x, assets):
        self.static_img = assets.portal
        super().__init__(x, cfg.GROUND_Y - cfg.PORTAL_HEIGHT)
        self.phase = 0.0
        self.used = False
        self.image = pygame.Surface((cfg.PORTAL_WIDTH + 40, cfg.PORTAL_HEIGHT + 40),
                                    pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.rect.midbottom = (round(x), cfg.GROUND_Y)
        self._render()

    @property
    def hitbox(self):
        return self.rect.inflate(-50, -30)

    @property
    def glow_center(self):
        return self.rect.center

    def _render(self):
        self.image.fill((0, 0, 0, 0))
        if self.static_img:
            r = self.static_img.get_rect(center=(self.image.get_width() // 2,
                                                 self.image.get_height() // 2))
            self.image.blit(self.static_img, r)
            return
        cx = self.image.get_width() // 2
        cy = self.image.get_height() // 2
        pulse = (math.sin(self.phase) + 1) * 0.5
        # weicher Glow ueber Temp-Surface (web-sicher statt RGBA-Direkt-Draw)
        w, h = self.image.get_width(), self.image.get_height()
        glow = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (cfg.PORTAL_COLOR_A[0], cfg.PORTAL_COLOR_A[1],
                                   cfg.PORTAL_COLOR_A[2], 60), (0, 0, w, h))
        self.image.blit(glow, (0, 0))
        for i, col in enumerate((cfg.PORTAL_COLOR_A, cfg.PORTAL_COLOR_B, (255, 255, 255))):
            rw = int(cfg.PORTAL_WIDTH * (0.9 - i * 0.22) * (0.92 + 0.08 * pulse))
            rh = int(cfg.PORTAL_HEIGHT * (0.9 - i * 0.22) * (0.92 + 0.08 * pulse))
            pygame.draw.ellipse(self.image, col, (cx - rw // 2, cy - rh // 2, rw, rh),
                                width=max(2, 5 - i))

    def update(self, dt, scroll_speed):
        self.pos.x -= scroll_speed * dt
        self.phase += 5.0 * dt
        self.rect.x = round(self.pos.x)
        if not self.static_img:
            self._render()
        if self.rect.right < -20:
            self.kill()
