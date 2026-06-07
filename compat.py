"""
compat.py - Plattform-Kompatibilitaet (Desktop nativ <-> Browser/pygbag).

Problem: pygbag 0.9.3 laedt die pygame-Submodule `pygame.sprite` und
`pygame.math` NICHT automatisch und behandelt ein explizites
`import pygame.sprite` faelschlich als zu installierendes PyPI-Paket (404).
Die Kern-Module (draw, display, font, transform, image, ...) sind dagegen da.

Loesung: Wir verwenden die echten pygame-Klassen, WENN verfuegbar (Desktop),
und fallen sonst auf API-identische, schlanke Eigenimplementierungen zurueck
(Browser). Der restliche Code bleibt unveraendert und nutzt einfach:

    from compat import Vector2, Sprite, Group, spritecollide
"""

import pygame


# ==========================================================================
# Vector2  (bevorzugt pygame.Vector2)
# ==========================================================================
def _resolve_vector2():
    V = getattr(pygame, "Vector2", None)
    if V is not None:
        return V

    class Vector2:
        """Minimaler 2D-Vektor (Fallback). Deckt genau ab, was das Spiel nutzt:
        Komponenten x/y, Arithmetik, Skalierung, length()."""
        __slots__ = ("x", "y")

        def __init__(self, x=0.0, y=0.0):
            if hasattr(x, "__len__"):
                x, y = x[0], x[1]
            self.x = float(x)
            self.y = float(y)

        def __iter__(self):
            yield self.x
            yield self.y

        def __getitem__(self, i):
            return (self.x, self.y)[i]

        def __add__(self, o):
            return Vector2(self.x + o[0], self.y + o[1])

        def __sub__(self, o):
            return Vector2(self.x - o[0], self.y - o[1])

        def __mul__(self, s):
            return Vector2(self.x * s, self.y * s)

        __rmul__ = __mul__

        def length(self):
            return (self.x * self.x + self.y * self.y) ** 0.5

        def __repr__(self):
            return f"Vector2({self.x}, {self.y})"

    return Vector2


Vector2 = _resolve_vector2()


# ==========================================================================
# Sprite / Group / spritecollide  (bevorzugt pygame.sprite)
# ==========================================================================
def _resolve_sprite():
    spr = getattr(pygame, "sprite", None)
    if spr is not None and hasattr(spr, "Sprite"):
        return spr.Sprite, spr.Group, spr.spritecollide

    # --- Fallback: schlanke, API-kompatible Eigenimplementierung ---
    class Sprite:
        def __init__(self, *groups):
            self._groups = []
            for g in groups:
                g.add(self)

        def add(self, *groups):
            for g in groups:
                g.add(self)

        def kill(self):
            for g in list(self._groups):
                g.remove(self)
            self._groups.clear()

        def alive(self):
            return bool(self._groups)

        def update(self, *args, **kwargs):
            pass

    class Group:
        def __init__(self, *sprites):
            self._sprites = []
            for s in sprites:
                self.add(s)

        def add(self, *sprites):
            for s in sprites:
                if s not in self._sprites:
                    self._sprites.append(s)
                    s._groups.append(self)

        def remove(self, *sprites):
            for s in sprites:
                if s in self._sprites:
                    self._sprites.remove(s)
                if self in s._groups:
                    s._groups.remove(self)

        def sprites(self):
            return list(self._sprites)

        def update(self, *args, **kwargs):
            for s in list(self._sprites):
                s.update(*args, **kwargs)

        def draw(self, surface):
            for s in self._sprites:
                surface.blit(s.image, s.rect)

        def empty(self):
            for s in list(self._sprites):
                self.remove(s)

        def __iter__(self):
            return iter(list(self._sprites))

        def __len__(self):
            return len(self._sprites)

    def spritecollide(sprite, group, dokill, collided=None):
        if collided is None:
            hits = [s for s in group if sprite.rect.colliderect(s.rect)]
        else:
            hits = [s for s in group if collided(sprite, s)]
        if dokill:
            for s in hits:
                s.kill()
        return hits

    return Sprite, Group, spritecollide


Sprite, Group, spritecollide = _resolve_sprite()
