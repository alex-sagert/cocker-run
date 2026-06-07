"""
settings.py - Zentrale Konfiguration fuer "Cocker Run".

WICHTIG (Refactor): Alle Bewegungs-/Physikwerte sind jetzt in
*Einheiten pro Sekunde* angegeben, weil die Engine Delta-Time (dt) nutzt:
    Geschwindigkeit -> px / Sekunde
    Beschleunigung  -> px / Sekunde^2
So laeuft das Spiel bei 60 FPS exakt gleich schnell wie bei 144 FPS.
"""

# ==========================================================================
# Fenster
# ==========================================================================
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 540
FPS = 60                          # Ziel-FPS (dt sorgt fuer Unabhaengigkeit)
TITLE = "Cocker Run - Aiva"

# Sicherheits-Cap fuer dt (z.B. wenn der Browser-Tab kurz einfriert),
# damit Objekte nicht durch Waende "tunneln".
MAX_DT = 1 / 30

# ==========================================================================
# Boden
# ==========================================================================
GROUND_HEIGHT = 90
GROUND_Y = SCREEN_HEIGHT - GROUND_HEIGHT

# ==========================================================================
# Spieler (Aiva)
# ==========================================================================
PLAYER_WIDTH = 96          # groesser -> schaerfer & besser sichtbar
PLAYER_HEIGHT = 80
PLAYER_START_X = 140
PLAYER_MIN_X = 40
PLAYER_MAX_X = SCREEN_WIDTH // 3

# Faire (grosszuegige) Hitbox des Spielers -> man stirbt nicht so leicht
HITBOX_INSET_X = 24
HITBOX_INSET_Y = 18

# ==========================================================================
# >>> PHYSIK-STELLSCHRAUBEN (Vektor-Kinematik) <<<
# Hier justierst du das Game Feel. Alles in px/s bzw. px/s^2.
# ==========================================================================
GRAVITY = 3600.0                  # Schwerkraft-Beschleunigung (px/s^2)
FALL_MULTIPLIER = 1.35            # >1 = schnelleres Fallen (weniger floaty)
JUMP_SPEED = -1010.0             # Absprung-Geschwindigkeit (px/s, negativ=hoch)
JUMP_CUT_MULTIPLIER = 0.45        # Loslassen -> Aufstieg kappen (kleiner Hopser)
MAX_FALL_SPEED = 1400.0          # maximale Fallgeschwindigkeit (px/s)

# Komfort-Features fuer ein faires Sprung-Gefuehl (wie in Profi-Plattformern):
COYOTE_TIME = 0.10                # noch springen, kurz nachdem man die Kante verlassen hat
JUMP_BUFFER_TIME = 0.12           # Sprung "vormerken", wenn kurz vor der Landung gedrueckt

# Horizontale Bewegung mit Beschleunigung + Reibung (echtes Momentum):
PLAYER_ACCEL = 6500.0            # Input-Beschleunigung (px/s^2)
MAX_RUN_SPEED = 520.0            # max. horizontale Geschwindigkeit (px/s)
# Reibung = pro Sekunde verbleibender Geschwindigkeits-Anteil (0..1).
# Klein  -> griffig/viel Reibung;  nahe 1 -> rutschig/viel Momentum.
GROUND_FRICTION = 0.00050         # am Boden: bremst zugig ab
AIR_FRICTION = 0.25               # in der Luft: Momentum bleibt lange erhalten
MOMENTUM_JUMP_BONUS = -150.0     # Anlauf -> etwas hoeher (px/s, negativ)
MOMENTUM_MAX_X_EXTEND = 140       # wie weit Aiva im Sprung nach rechts darf

# ==========================================================================
# Side-Scrolling & Score
# ==========================================================================
SCROLL_SPEED = 320.0              # Basis-Welttempo (px/s); * Level-Faktor (etwas entspannter)
SCORE_PER_SECOND = 18.0           # Distanz-Punkte pro Sekunde
# Lauf-Animation an das Tempo koppeln: alle X Welt-Pixel ein neues Lauf-Bild.
# Kleiner = schnellere Beinbewegung. So passen Beine & Boden zusammen.
RUN_STRIDE_PX = 26.0

# ==========================================================================
# Animation (Frames pro Sekunde je Zustand)
# ==========================================================================
ANIM_FPS_RUN = 14.0
ANIM_FPS_IDLE = 4.0
EAR_WIGGLE_SPEED = 9.0            # nur Platzhalter-Hund (rad/s)
EAR_WIGGLE_AMP = 22

# ==========================================================================
# Hindernisse  (kleiner & fairer)
# ==========================================================================
OBSTACLE_MIN_W = 26
OBSTACLE_MAX_W = 44
OBSTACLE_MIN_H = 28
OBSTACLE_MAX_H = 56               # bleibt locker springbar
# Eigene (kleine) Hitbox-Einrueckung fuer Hindernisse -> fairer
OBSTACLE_HITBOX_INSET_X = 7
OBSTACLE_HITBOX_INSET_Y = 6

# ==========================================================================
# Kaustangen (Items)
# ==========================================================================
CHEW_STANDARD_POINTS = 50
CHEW_EPIC_POINTS = 250
CHEW_EPIC_CHANCE = 0.18
CHEW_SPAWN_GAP_MIN = 220
CHEW_SPAWN_GAP_MAX = 480
CHEW_SIZE = 42

# --- Engels-Kaustange (Schutzhuelle / Smash-Modus) ---
CHEW_ANGEL_CHANCE = 0.07          # seltener als die epische
CHEW_ANGEL_POINTS = 100
SHIELD_IFRAME = 0.8               # kurze Unverwundbarkeit nach Schild-Verlust (s)
SMASH_TIME = 5.0                  # Dauer des Smash-/Stern-Modus (s)
SMASH_POINTS = 25                 # Bonuspunkte pro zertruemmertem Hindernis

EPIC_BOOST_TIME = 1.5             # Sekunden Speed-Boost
EPIC_BOOST_MULT = 1.6
EPIC_FLASH_TIME = 0.5             # Sekunden Screen-Flash
EPIC_PARTICLES = 30

# ==========================================================================
# Portal & Level
# ==========================================================================
PORTAL_WIDTH = 80
PORTAL_HEIGHT = 110
PORTAL_GAP_MIN = 1500
PORTAL_GAP_MAX = 2400
PORTAL_TRANSITION_TIME = 0.75     # Sekunden Paletten-Uebergang
LEVEL_BANNER_TIME = 2.0           # Sekunden "LEVEL X"-Banner

LEVELS = [
    {
        "name": "Sunny Meadow",
        "sky_top": (120, 195, 235), "sky_bottom": (190, 230, 246),
        "far": (165, 185, 210), "hill": (130, 190, 120),
        "ground": (95, 159, 53), "ground_edge": (70, 130, 40),
        "grass": (60, 120, 40),
        "speed_mult": 1.00, "obstacle_gap": (460, 780),
    },
    {
        "name": "Twilight Ruins",
        "sky_top": (55, 38, 92), "sky_bottom": (196, 96, 120),
        "far": (78, 66, 108), "hill": (92, 78, 120),
        "ground": (74, 86, 78), "ground_edge": (52, 64, 58),
        "grass": (60, 80, 70),
        "speed_mult": 1.25, "obstacle_gap": (400, 680),
    },
    {
        "name": "Aurora Night",
        "sky_top": (12, 18, 48), "sky_bottom": (28, 96, 120),
        "far": (40, 70, 110), "hill": (30, 70, 90),
        "ground": (40, 60, 80), "ground_edge": (30, 46, 62),
        "grass": (40, 70, 80),
        "speed_mult": 1.45, "obstacle_gap": (360, 600),
    },
]

# ==========================================================================
# Highscore (Top 10) - wird in einer Datei gespeichert
# ==========================================================================
HIGHSCORE_FILE = "highscores.json"
HIGHSCORE_MAX = 10

# ==========================================================================
# Ranking
# ==========================================================================
RANK_THRESHOLDS = [("S", 3000), ("A", 1900), ("B", 1100), ("C", 500), ("D", 0)]
RANK_COLORS = {
    "S": (255, 215, 0), "A": (120, 230, 255), "B": (150, 255, 150),
    "C": (255, 200, 120), "D": (220, 220, 220),
}

# ==========================================================================
# Touch-Steuerung (fuers Handy / Browser)
# ==========================================================================
TOUCH_CONTROLS = True             # On-Screen-Buttons anzeigen
TOUCH_BTN_RADIUS = 46
TOUCH_BTN_MARGIN = 28
TOUCH_BTN_ALPHA = 110
# Button-Zentren werden in game.py aus diesen Werten berechnet.

# ==========================================================================
# ASSETS
# ==========================================================================
ASSET_DIR = "assets"
BAKED_DIR = "assets/baked"        # fertige, freigestellte PNGs (Web-freundlich)

SPRITE_SHEET_FILE = None          # None = Auto-Erkennung (Datei beginnt mit 'e')
LOGO_FILE = "logo.png"            # web-freundliches PNG (aus dem Portraet gebacken)

FREE_SPRITE_BG = True
FREE_SPRITE_TOLERANCE = 68
SHEET_USE = {"player"}            # "player","obstacles","chews","portal"

SHEET_SLICES = {
    # Per Farberkennung praezise auf die 4 Hunde der oberen Reihe zentriert
    # (grosszuegige Box innerhalb des Rahmens; bake_sprites.py schneidet dann
    #  exakt auf die Hunde-Kontur zu und richtet am Boden aus).
    "run": [
        (85,  108, 120, 132),
        (222, 108, 120, 132),
        (357, 110, 120, 132),
        (490, 102, 122, 134),
    ],
    "jump": (263, 274, 150, 164),
    "obstacle_plant": (196, 556, 140, 128),
    "obstacle_ruin":  (352, 556, 150, 128),
    "portal": (48, 548, 135, 140),
    "chew":      (58, 752, 196, 134),
    "chew_epic": (515, 556, 135, 120),
}

# ==========================================================================
# Farben (UI / Platzhalter)
# ==========================================================================
TEXT_LIGHT = (255, 255, 255)
TEXT_DARK = (25, 25, 30)
OVERLAY_COLOR = (0, 0, 0, 165)
CLOUD_COLOR = (255, 255, 255)
DIRT_COLOR = (120, 80, 40)

DOG_BODY = (226, 172, 84)
DOG_BELLY = (242, 205, 135)
DOG_EAR = (198, 138, 58)
DOG_DARK = (150, 100, 40)
DOG_NOSE = (40, 30, 25)

OBSTACLE_COLOR = (90, 70, 60)
CHEW_COLOR = (235, 205, 150)
CHEW_EPIC_COLOR = (90, 220, 255)
CHEW_ANGEL_COLOR = (255, 250, 235)       # weiss-golden glaenzend
CHEW_ANGEL_GLOW = (255, 215, 90)
SHIELD_COLOR = (120, 220, 255)           # Schutzhuellen-Blase
SMASH_COLOR = (255, 210, 80)             # Smash-/Stern-Aura
PORTAL_COLOR_A = (150, 90, 240)
PORTAL_COLOR_B = (90, 200, 255)

SHADOW_COLOR = (0, 0, 0, 90)
