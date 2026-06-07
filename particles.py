"""
particles.py - Delta-Time-basiertes Partikel-System.

Alle Geschwindigkeiten in px/s, Lebensdauer in Sekunden -> framerate-unabhaengig.
Effekte: Staub (Sprung/Landung), Funken (Items), Portal-Gluehen, Epic-Burst.
"""

import math
import random
import pygame


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life",
                 "color", "radius", "gravity", "shrink")

    def __init__(self, x, y, vx, vy, life, color, radius, gravity=0.0, shrink=True):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.radius = radius
        self.gravity = gravity
        self.shrink = shrink

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        self.life -= dt

    @property
    def dead(self):
        return self.life <= 0

    def draw(self, surface):
        t = max(0.0, self.life / self.max_life)
        r = self.radius * t if self.shrink else self.radius
        if r < 1:
            return
        alpha = int(255 * t)
        size = int(r * 2)
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), (int(r), int(r)), int(r))
        surface.blit(surf, (self.x - r, self.y - r))


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if not p.dead]

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)

    def clear(self):
        self.particles.clear()

    # ------------------------------------------------------------- Effekte
    def emit_dust(self, x, y, amount=10):
        for _ in range(amount):
            self.particles.append(Particle(
                x + random.uniform(-8, 8), y,
                vx=random.uniform(-150, 150), vy=random.uniform(-120, -12),
                life=random.uniform(0.28, 0.48), color=(200, 180, 150),
                radius=random.uniform(3, 6), gravity=720))

    def emit_sparkle(self, x, y, color=(255, 240, 180), amount=14):
        for _ in range(amount):
            a = random.uniform(0, math.tau)
            sp = random.uniform(120, 360)
            self.particles.append(Particle(
                x, y, vx=math.cos(a) * sp, vy=math.sin(a) * sp,
                life=random.uniform(0.38, 0.68), color=color,
                radius=random.uniform(2, 5), gravity=900))

    def emit_epic(self, x, y, amount=30):
        palette = [(120, 230, 255), (255, 245, 180), (255, 255, 255), (180, 150, 255)]
        for _ in range(amount):
            a = random.uniform(0, math.tau)
            sp = random.uniform(180, 540)
            self.particles.append(Particle(
                x, y, vx=math.cos(a) * sp, vy=math.sin(a) * sp,
                life=random.uniform(0.5, 0.9), color=random.choice(palette),
                radius=random.uniform(3, 7), gravity=600))

    def emit_portal_glow(self, x, y, color=(150, 120, 255), amount=2):
        for _ in range(amount):
            self.particles.append(Particle(
                x + random.uniform(-26, 26), y + random.uniform(-44, 44),
                vx=random.uniform(-24, 24), vy=random.uniform(-96, -24),
                life=random.uniform(0.4, 0.75), color=color,
                radius=random.uniform(2, 5), gravity=-60))
