"""
Cocker Run - Ein 2.5D Jump 'n' Run mit dem Englisch Cocker Spaniel "Aiva".

Profi-Architektur (Refactor):
    settings.py    - Konfiguration (Physik in px/s) + Sprite-Sheet-Koordinaten
    assets.py      - Sprite-Sheet-Slicing, Freistellen, baked PNGs, FSM-Frames
    particles.py   - Delta-Time-Partikel
    background.py  - 3-Ebenen-Parallax
    entities.py    - Player (Vector2 + FSM), Obstacle/Chew/Portal (Sprite-Gruppen)
    game.py        - async Game-Loop, dt, Touch-Steuerung, Level-/Portal-Logik
    tools/         - bake_sprites.py (Sprites einmalig freistellen)

Steuerung:
    Desktop:  Pfeil OBEN = Sprung (variabel), Pfeil LINKS/RECHTS = Bewegung
    Handy:    On-Screen-Buttons (Links / Rechts / Springen)
    Portal beruehren -> naechstes Level
    Tippen / LEERTASTE -> Neustart (Game Over)

Start (Desktop):  python main.py
Web-Build:        pygbag .     (siehe README.md)

Der Einstieg ist async -> identischer Code laeuft nativ UND im Browser (pygbag).
"""

import asyncio
import pygame          # WICHTIG: damit pygbag pygame als Abhaengigkeit erkennt/buendelt
from game import main

if __name__ == "__main__":
    asyncio.run(main())
