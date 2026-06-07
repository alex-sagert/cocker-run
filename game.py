"""
game.py - Spiel-Orchestrierung mit moderner, skalierbarer Architektur.

Profi-Systeme:
  * Delta-Time-Loop (async, pygbag-/Web-tauglich)
  * pygame.sprite.Group fuer obstacles / items / portals (schnelle Kollision)
  * Touch-Steuerung (On-Screen-Buttons) + Tastatur parallel
  * Level-/Portal-Logik, Parallax, Partikel, HUD, Game-Over/Ranking
"""

import asyncio
import math
import random
import pygame

import settings as cfg
from assets import AssetManager
from background import ParallaxBackground
from particles import ParticleSystem
from entities import Player, Obstacle, Chew, Portal, hitbox_collide
from compat import Group, spritecollide
import highscores


class InputState:
    """Aktueller Bewegungs-Input (aus Tastatur ODER Touch)."""
    __slots__ = ("left", "right")

    def __init__(self):
        self.left = False
        self.right = False


class TouchControls:
    """On-Screen-Buttons fuer Handy/Browser: Links, Rechts, Springen."""

    def __init__(self):
        r = cfg.TOUCH_BTN_RADIUS
        m = cfg.TOUCH_BTN_MARGIN
        y = cfg.SCREEN_HEIGHT - m - r
        self.left_c = (m + r, y)
        self.right_c = (m + r * 3 + 24, y)
        self.jump_c = (cfg.SCREEN_WIDTH - m - r, y)
        self.r = r

    def _in(self, center, p):
        return (center[0] - p[0]) ** 2 + (center[1] - p[1]) ** 2 <= self.r ** 2

    def buttons_for(self, points):
        """Welche Buttons sind durch die aktiven Pointer (Touch/Maus) gedrueckt?"""
        left = right = jump = False
        for p in points:
            if self._in(self.left_c, p):
                left = True
            elif self._in(self.right_c, p):
                right = True
            elif self._in(self.jump_c, p):
                jump = True
        return left, right, jump

    def draw(self, surface):
        overlay = pygame.Surface((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT), pygame.SRCALPHA)
        a = cfg.TOUCH_BTN_ALPHA
        for center, sym in ((self.left_c, "left"), (self.right_c, "right"),
                            (self.jump_c, "up")):
            pygame.draw.circle(overlay, (255, 255, 255, a), center, self.r)
            pygame.draw.circle(overlay, (255, 255, 255, a + 60), center, self.r, 3)
            cx, cy = center
            s = 16
            if sym == "left":
                pts = [(cx + s, cy - s), (cx + s, cy + s), (cx - s, cy)]
            elif sym == "right":
                pts = [(cx - s, cy - s), (cx - s, cy + s), (cx + s, cy)]
            else:  # up
                pts = [(cx - s, cy + s), (cx + s, cy + s), (cx, cy - s)]
            pygame.draw.polygon(overlay, (40, 40, 40, 210), pts)
        surface.blit(overlay, (0, 0))


class Game:
    STATE_PLAYING = "playing"
    STATE_GAME_OVER = "game_over"

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
        pygame.display.set_caption(cfg.TITLE)
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont("Arial", 22)
        self.mid_font = pygame.font.SysFont("Arial", 30, bold=True)
        self.big_font = pygame.font.SysFont("Arial", 56, bold=True)
        self.rank_font = pygame.font.SysFont("Arial", 120, bold=True)

        self.assets = AssetManager()
        self.touch = TouchControls()
        self.input = InputState()

        # aktive Pointer (Touch-Finger + Maus) -> Position
        self.pointers = {}
        self.prev_jump = False

        self.running = True
        self.reset()

    # ---------------------------------------------------------- Setup
    def reset(self):
        self.state = self.STATE_PLAYING
        self.level_index = 0
        self.level = cfg.LEVELS[0]

        self.player = Player(self.assets)
        self.obstacles = Group()
        self.items = Group()
        self.portals = Group()
        self.particles = ParticleSystem()
        self.background = ParallaxBackground(self.level)

        self.score = 0.0
        self.chew_points = 0
        self.floats = []                 # schwebende "+50"-Punkte-Texte

        self.boost_timer = 0.0
        self.flash_timer = 0.0
        self.banner_timer = 0.0

        # Schutzhuelle / Smash-Modus (Engels-Kaustange)
        self.shield = False
        self.smash_timer = 0.0
        self.invuln_timer = 0.0
        self._aura_phase = 0.0

        self.hs_entries = []             # Top-10 (bei Game Over gefuellt)
        self.hs_index = None             # eigener Platz in der Liste

        self._reset_spawn_timers()
        self.dist_to_portal = random.randint(cfg.PORTAL_GAP_MIN, cfg.PORTAL_GAP_MAX)

        self.final_score = 0
        self.final_rank = "D"

    def _reset_spawn_timers(self):
        lo, hi = self.level["obstacle_gap"]
        self.dist_to_obstacle = random.randint(lo, hi)
        self.dist_to_chew = random.randint(cfg.CHEW_SPAWN_GAP_MIN, cfg.CHEW_SPAWN_GAP_MAX)

    # ---------------------------------------------------------- Score/Level
    @property
    def total_score(self):
        return int(self.score) + self.chew_points

    def _rank_for(self, score):
        for name, threshold in cfg.RANK_THRESHOLDS:
            if score >= threshold:
                return name
        return cfg.RANK_THRESHOLDS[-1][0]

    @property
    def current_scroll_speed(self):
        speed = cfg.SCROLL_SPEED * self.level["speed_mult"]
        if self.boost_timer > 0:
            speed *= cfg.EPIC_BOOST_MULT
        return speed

    def _enter_next_level(self, portal):
        portal.used = True
        portal.kill()
        self.level_index = min(self.level_index + 1, len(cfg.LEVELS) - 1)
        self.level = cfg.LEVELS[self.level_index]
        self.background.set_palette(self.level)
        self._reset_spawn_timers()
        for o in list(self.obstacles):
            if o.rect.left <= cfg.SCREEN_WIDTH:
                o.kill()
        self.banner_timer = cfg.LEVEL_BANNER_TIME
        self.flash_timer = cfg.EPIC_FLASH_TIME
        cx, cy = portal.glow_center
        self.particles.emit_epic(cx, cy, amount=40)

    # ---------------------------------------------------------- Spawning
    @staticmethod
    def _conflict(a_rect, b_rect):
        """Ueberlappen sich zwei Objekte horizontal (mit etwas Puffer)?"""
        gap = a_rect.width // 2 + b_rect.width // 2 + 14
        return abs(a_rect.centerx - b_rect.centerx) < gap

    def _lift_chew_above(self, chew, obs):
        """Hebt eine Kaustange ueber ein Hindernis (so ist sie nie versteckt
        und per Sprung einsammelbar)."""
        lift_to = obs.rect.top - cfg.CHEW_SIZE - 46
        if chew.base_y > lift_to:
            chew.base_y = lift_to
            chew.rect.y = round(lift_to)

    def _maybe_spawn(self, dist):
        self.dist_to_obstacle -= dist
        if self.dist_to_obstacle <= 0:
            img = random.choice(self.assets.obstacle_images) if self.assets.obstacle_images else None
            obs = Obstacle(cfg.SCREEN_WIDTH + 20, img)
            self.obstacles.add(obs)
            # bereits gespawnte Knochen ggf. ueber das neue Hindernis heben
            for c in self.items:
                if self._conflict(c.rect, obs.rect):
                    self._lift_chew_above(c, obs)
            lo, hi = self.level["obstacle_gap"]
            self.dist_to_obstacle = random.randint(lo, hi)

        self.dist_to_chew -= dist
        if self.dist_to_chew <= 0:
            chew = Chew(cfg.SCREEN_WIDTH + 20, self.assets)
            # neuen Knochen ueber nahe Hindernisse heben (nicht im Hindernis!)
            for o in self.obstacles:
                if self._conflict(chew.rect, o.rect):
                    self._lift_chew_above(chew, o)
            self.items.add(chew)
            self.dist_to_chew = random.randint(cfg.CHEW_SPAWN_GAP_MIN, cfg.CHEW_SPAWN_GAP_MAX)

        self.dist_to_portal -= dist
        if self.dist_to_portal <= 0 and len(self.portals) == 0:
            self.portals.add(Portal(cfg.SCREEN_WIDTH + 40, self.assets))
            self.dist_to_portal = random.randint(cfg.PORTAL_GAP_MIN, cfg.PORTAL_GAP_MAX)

    # ---------------------------------------------------------- Input
    def _do_jump(self):
        if self.state == self.STATE_PLAYING and self.player.jump():
            self.particles.emit_dust(self.player.rect.centerx, cfg.GROUND_Y, amount=10)

    def _do_release(self):
        if self.state == self.STATE_PLAYING:
            self.player.release_jump()

    def _set_pointer(self, pid, x, y):
        self.pointers[pid] = (x, y)
        if self.state == self.STATE_GAME_OVER:
            self.reset()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_UP:
                    self._do_jump()
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    if self.state == self.STATE_GAME_OVER:
                        self.reset()
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_UP:
                    self._do_release()
            # ---- Touch / Maus (pygbag liefert beides) ----
            elif event.type == pygame.FINGERDOWN:
                self._set_pointer(("f", event.finger_id),
                                  event.x * cfg.SCREEN_WIDTH, event.y * cfg.SCREEN_HEIGHT)
            elif event.type == pygame.FINGERMOTION:
                if ("f", event.finger_id) in self.pointers:
                    self.pointers[("f", event.finger_id)] = (
                        event.x * cfg.SCREEN_WIDTH, event.y * cfg.SCREEN_HEIGHT)
            elif event.type == pygame.FINGERUP:
                self.pointers.pop(("f", event.finger_id), None)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._set_pointer("mouse", *event.pos)
            elif event.type == pygame.MOUSEMOTION and "mouse" in self.pointers:
                self.pointers["mouse"] = event.pos
            elif event.type == pygame.MOUSEBUTTONUP:
                self.pointers.pop("mouse", None)

    def _gather_input(self):
        keys = pygame.key.get_pressed()
        tl, tr, tj = self.touch.buttons_for(self.pointers.values())
        self.input.left = keys[pygame.K_LEFT] or tl
        self.input.right = keys[pygame.K_RIGHT] or tr
        # Touch-Sprung als Flanke (Tastatur-Sprung laeuft ueber Events)
        if tj and not self.prev_jump:
            self._do_jump()
        elif not tj and self.prev_jump:
            self._do_release()
        self.prev_jump = tj

    # ---------------------------------------------------------- Update
    # ---------------------------------------------------------- Punkte-Popups
    def _add_float(self, x, y, text, color):
        self.floats.append({"x": x, "y": float(y), "text": text,
                            "color": color, "life": 0.9, "max": 0.9})

    def _update_floats(self, dt):
        for f in self.floats:
            f["y"] -= 40 * dt            # steigt nach oben
            f["life"] -= dt
        self.floats = [f for f in self.floats if f["life"] > 0]

    def update(self, dt):
        self.particles.update(dt)
        self._update_floats(dt)
        self.flash_timer = max(0.0, self.flash_timer - dt)
        self.banner_timer = max(0.0, self.banner_timer - dt)

        self._gather_input()

        if self.state != self.STATE_PLAYING:
            return

        scroll = self.current_scroll_speed
        if self.boost_timer > 0:
            self.boost_timer = max(0.0, self.boost_timer - dt)
        self.smash_timer = max(0.0, self.smash_timer - dt)
        self.invuln_timer = max(0.0, self.invuln_timer - dt)
        self._aura_phase += dt
        dist = scroll * dt                       # zurueckgelegte Welt-Distanz

        # Lauf-Animation ans Welttempo koppeln (Beine passen zum Boden)
        self.player.run_fps = scroll / cfg.RUN_STRIDE_PX
        self.player.world_moving = True
        landed = self.player.update(dt, self.input)
        if landed:
            self.particles.emit_dust(self.player.rect.centerx, cfg.GROUND_Y, amount=8)

        self.background.update(dt, scroll)
        self._maybe_spawn(dist)
        self.obstacles.update(dt, scroll)
        self.items.update(dt, scroll)
        self.portals.update(dt, scroll)
        for p in self.portals:
            cx, cy = p.glow_center
            self.particles.emit_portal_glow(cx, cy)

        self.score += cfg.SCORE_PER_SECOND * dt

        # --- Kollisionen ueber Sprite-Gruppen ---
        collected = spritecollide(self.player, self.items, True,
                                  collided=hitbox_collide)
        for chew in collected:
            self.chew_points += chew.points
            if chew.kind == "angel":
                self._collect_angel(chew)
            elif chew.kind == "epic":
                self.boost_timer = cfg.EPIC_BOOST_TIME
                self.flash_timer = cfg.EPIC_FLASH_TIME
                self.particles.emit_epic(chew.rect.centerx, chew.rect.centery)
                self._add_float(chew.rect.centerx, chew.rect.top,
                                f"+{chew.points}", (120, 230, 255))
            else:
                self.particles.emit_sparkle(chew.rect.centerx, chew.rect.centery)
                self._add_float(chew.rect.centerx, chew.rect.top,
                                f"+{chew.points}", (255, 240, 170))

        portal_hits = spritecollide(self.player, self.portals, False,
                                    collided=hitbox_collide)
        for portal in portal_hits:
            if not portal.used:
                self._enter_next_level(portal)
                break

        hit = spritecollide(self.player, self.obstacles, False,
                            collided=hitbox_collide)
        if hit:
            if self.smash_timer > 0:
                for o in hit:
                    self._smash(o)                    # Stern-Modus: durchpfluegen
            elif self.shield:
                self.shield = False                   # Huelle zerbricht...
                self.invuln_timer = cfg.SHIELD_IFRAME
                self.flash_timer = max(self.flash_timer, 0.25)
                for o in hit:
                    self._smash(o)                    # ...und zertruemmert das Hindernis
            elif self.invuln_timer > 0:
                pass                                   # noch kurz unverwundbar
            else:
                self._game_over()

    def _game_over(self):
        self.state = self.STATE_GAME_OVER
        self.final_score = self.total_score
        self.final_rank = self._rank_for(self.final_score)
        self.particles.emit_dust(self.player.rect.centerx, cfg.GROUND_Y, amount=16)
        # in die Top-10-Bestenliste eintragen
        self.hs_entries, self.hs_index = highscores.add(self.final_score)

    def _collect_angel(self, chew):
        """Engels-Kaustange: erste = Schutzhuelle, zweite = Smash-/Stern-Modus."""
        self.flash_timer = cfg.EPIC_FLASH_TIME
        self.particles.emit_epic(chew.rect.centerx, chew.rect.centery, amount=36)
        if self.shield or self.smash_timer > 0:
            self.smash_timer = cfg.SMASH_TIME
            self.shield = False
            self._add_float(chew.rect.centerx, chew.rect.top, "SMASH-MODUS!", cfg.SMASH_COLOR)
        else:
            self.shield = True
            self._add_float(chew.rect.centerx, chew.rect.top, "SCHUTZ!", cfg.SHIELD_COLOR)

    def _smash(self, obs):
        """Zertruemmert ein Hindernis (Schutzhuelle/Smash) statt Game Over."""
        cx, cy = obs.rect.center
        obs.kill()
        self.chew_points += cfg.SMASH_POINTS
        self.particles.emit_dust(cx, cy, amount=14)
        self.particles.emit_sparkle(cx, cy, (215, 215, 225), amount=10)
        self._add_float(cx, obs.rect.top, f"+{cfg.SMASH_POINTS}", (255, 230, 160))

    # ---------------------------------------------------------- Draw
    def draw(self):
        s = self.screen
        self.background.draw_back(s)

        self.player.draw_shadow(s)
        for o in self.obstacles:
            o.draw_shadow(s)

        self.portals.draw(s)
        self.items.draw(s)
        self.obstacles.draw(s)
        self._draw_player_aura(s)
        s.blit(self.player.image, self.player.rect)

        self.particles.draw(s)
        self._draw_floats(s)
        self.background.draw_foreground(s)

        self._draw_flash(s)
        if self.state == self.STATE_PLAYING:
            self._draw_hud(s)
            if cfg.TOUCH_CONTROLS:
                self.touch.draw(s)
        self._draw_banner(s)
        if self.state == self.STATE_GAME_OVER:
            self._draw_game_over(s)

        pygame.display.flip()

    def _draw_player_aura(self, s):
        """Leuchtende Schutzhuelle (blau) bzw. pulsierende Smash-Aura (gold)."""
        if not (self.shield or self.smash_timer > 0):
            return
        p = self.player.rect
        cx, cy = p.center
        base_r = max(p.width, p.height) // 2 + 12
        pulse = (math.sin(self._aura_phase * 7) + 1) * 0.5
        if self.smash_timer > 0:
            col, alpha, rr = cfg.SMASH_COLOR, int(120 + 90 * pulse), base_r + int(6 * pulse)
        else:
            col, alpha, rr = cfg.SHIELD_COLOR, int(70 + 45 * pulse), base_r
        surf = pygame.Surface((rr * 2 + 6, rr * 2 + 6), pygame.SRCALPHA)
        c = rr + 3
        pygame.draw.circle(surf, (*col, alpha // 2), (c, c), rr)
        pygame.draw.circle(surf, (*col, min(255, alpha + 90)), (c, c), rr, 3)
        s.blit(surf, (cx - c, cy - c))

    def _draw_flash(self, s):
        if self.flash_timer <= 0:
            return
        alpha = int(120 * (self.flash_timer / cfg.EPIC_FLASH_TIME))
        flash = pygame.Surface((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT), pygame.SRCALPHA)
        flash.fill((255, 240, 160, alpha))
        s.blit(flash, (0, 0))

    def _draw_hud(self, s):
        total = self.total_score
        label = self.font.render("Score", True, cfg.TEXT_LIGHT)
        s.blit(label, (cfg.SCREEN_WIDTH // 2 - label.get_width() // 2, 6))
        num = self.big_font.render(str(total), True, cfg.TEXT_LIGHT)
        shadow = self.big_font.render(str(total), True, (0, 0, 0))
        s.blit(shadow, (cfg.SCREEN_WIDTH // 2 - num.get_width() // 2 + 2, 28))
        s.blit(num, (cfg.SCREEN_WIDTH // 2 - num.get_width() // 2, 26))
        lvl = self.font.render(f"Level {self.level_index + 1}: {self.level['name']}",
                               True, cfg.TEXT_LIGHT)
        s.blit(lvl, (16, 14))
        if self.boost_timer > 0:
            boost = self.font.render("SPEED BOOST!", True, (90, 220, 255))
            s.blit(boost, (cfg.SCREEN_WIDTH // 2 - boost.get_width() // 2, 92))
        if self.smash_timer > 0:
            t = self.font.render(f"SMASH-MODUS!  {self.smash_timer:.0f}s",
                                 True, cfg.SMASH_COLOR)
            s.blit(t, (cfg.SCREEN_WIDTH // 2 - t.get_width() // 2, 116))
        elif self.shield:
            t = self.font.render("SCHUTZHUELLE AKTIV", True, cfg.SHIELD_COLOR)
            s.blit(t, (cfg.SCREEN_WIDTH // 2 - t.get_width() // 2, 116))

    def _draw_banner(self, s):
        if self.banner_timer <= 0:
            return
        t = self.banner_timer / cfg.LEVEL_BANNER_TIME
        alpha = int(255 * min(1.0, t * 2))
        text = self.big_font.render(f"LEVEL {self.level_index + 1}", True, (255, 230, 150))
        sub = self.mid_font.render(self.level["name"], True, cfg.TEXT_LIGHT)
        text.set_alpha(alpha)
        sub.set_alpha(alpha)
        s.blit(text, (cfg.SCREEN_WIDTH // 2 - text.get_width() // 2, 150))
        s.blit(sub, (cfg.SCREEN_WIDTH // 2 - sub.get_width() // 2, 220))

    def _draw_floats(self, s):
        for f in self.floats:
            t = max(0.0, f["life"] / f["max"])
            surf = self.mid_font.render(f["text"], True, f["color"])
            surf.set_alpha(int(255 * t))
            s.blit(surf, (int(f["x"] - surf.get_width() // 2), int(f["y"])))

    def _center(self, s, surf, cx, y):
        s.blit(surf, (int(cx - surf.get_width() // 2), int(y)))

    def _draw_game_over(self, s):
        overlay = pygame.Surface((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(cfg.OVERLAY_COLOR)
        s.blit(overlay, (0, 0))
        muted = (150, 152, 170)

        # Titel
        self._center(s, self.big_font.render("GAME OVER", True, (255, 90, 90)),
                     cfg.SCREEN_WIDTH // 2, 22)

        # ---------- linke Spalte: dein Ergebnis ----------
        lx = 250
        self._center(s, self.font.render("DEIN ERGEBNIS", True, muted), lx, 110)
        rank_col = cfg.RANK_COLORS.get(self.final_rank, (255, 255, 255))
        self._center(s, self.rank_font.render(self.final_rank, True, rank_col), lx, 150)
        self._center(s, self.font.render("RANG", True, muted), lx, 285)
        self._center(s, self.mid_font.render(f"Score: {self.final_score}", True,
                                             cfg.TEXT_LIGHT), lx, 330)

        # ---------- rechte Spalte: Top 10 ----------
        rx = 560
        self._center(s, self.mid_font.render("TOP 10  -  BESTENLISTE", True,
                                             (255, 215, 0)), rx + 150, 104)
        y = 150
        if not self.hs_entries:
            s.blit(self.font.render("- noch keine Eintraege -", True, muted), (rx, y))
        for i, e in enumerate(self.hs_entries):
            me = (i == self.hs_index)
            col = (255, 215, 0) if me else cfg.TEXT_LIGHT
            row = f"{i + 1:>2}.  {e['score']:>6}   {e['date']}"
            if me:
                row += "   <- DU"
            s.blit(self.font.render(row, True, col), (rx, y))
            y += 29

        # Neustart-Hinweis
        self._center(s, self.font.render("Tippen / LEERTASTE = Neustart", True,
                                         cfg.TEXT_LIGHT), cfg.SCREEN_WIDTH // 2, 500)

    # ---------------------------------------------------------- Loop (async)
    async def run(self):
        """Async Game-Loop -> noetig fuer pygbag (Browser/WebAssembly)."""
        while self.running:
            dt = min(self.clock.tick(cfg.FPS) / 1000.0, cfg.MAX_DT)
            self.handle_events()
            self.update(dt)
            self.draw()
            await asyncio.sleep(0)         # gibt die Kontrolle an den Browser zurueck
        pygame.quit()


async def main():
    await Game().run()
