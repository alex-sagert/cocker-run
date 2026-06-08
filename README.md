# 🐶 Cocker Run

### ▶️ [Jetzt im Browser spielen](https://alex-sagert.github.io/cocker-run/)
*Direkt am Desktop oder Smartphone – ohne Installation.*

Ein 2.5D-Endless-Runner in **Python / Pygame** mit dem Englisch Cocker Spaniel
**Aiva**. Sammle Kaustangen 🦴, weiche Hindernissen aus, springe durch Portale
in neue Level – und jage den höchsten Rang (S/A/B/C/D)!

Läuft **nativ am Desktop** und **im Browser** (WebAssembly via `pygbag`) –
inklusive **Touch-Steuerung** für Smartphones.

---

## 🎮 Steuerung
| | Desktop | Touch / Mobil |
|---|---|---|
| Springen (variabel) | Pfeil **↑** | **▲**-Button |
| Bewegen | Pfeil **←/→** | **◀ ▶**-Buttons |
| Neustart (Game Over) | Leertaste / Enter | Bildschirm tippen |

*Tipp:* Pfeil **rechts halten beim Absprung** = Anlauf-Sprung (höher & weiter, dank Momentum).

### Power-ups (Kaustangen)
- **Standard** 🦴 – Punkte
- **Episch** ✨ – viele Punkte + Speed-Boost
- **Engels-Kaustange** 😇 – Schutzhülle; ein Hindernis-Treffer wird überlebt und
  das Hindernis zertrümmert. Eine zweite aktiviert den **Smash-Modus** (kurz
  unverwundbar, pflügt durch Hindernisse).

---

## ▶️ Lokal starten (Desktop)
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows PowerShell
pip install -r requirements.txt
python main.py
```

---

## 🌐 Im Browser spielen (WebAssembly)
Build erzeugen und lokal testen:
```bash
pip install pygbag
pygbag main.py            # lokaler Testserver: http://localhost:8000
pygbag --build main.py    # nur bauen -> Ausgabe in build/web/
python tools/patch_web.py # Web-Fixes anwenden (siehe unten)
```

> **Hinweis:** `tools/patch_web.py` korrigiert zwei bekannte Eigenheiten von
> pygbag 0.9.3 in `build/web/index.html`:
> 1. lädt `browserfs.min.js` von einem funktionierenden CDN (jsDelivr),
> 2. erzwingt `devicePixelRatio = 1` (sonst bleibt der Canvas bei nicht-
>    ganzzahliger Display-Skalierung leer).

---

## 🚀 Veröffentlichen / auf dem Smartphone spielen
Der Inhalt von `build/web/` ist eine statische Website und kann überall
gehostet werden. Auf einem echten Host (nicht `localhost`) lädt die Pygame-
Laufzeit automatisch von der öffentlichen CDN.

**Option A – GitHub Pages (automatisch):**
Repository pushen, dann *Settings → Pages → Source: „GitHub Actions"*.
Der Workflow in `.github/workflows/deploy.yml` baut, patcht und veröffentlicht
automatisch. Der Link hat die Form `https://<name>.github.io/<repo>/`.

**Option B – itch.io / Netlify:**
`build/web/` (gepatcht) als ZIP hochladen bzw. den Ordner ablegen, fertigen
Link öffnen.

Auf dem Smartphone den Link im Browser öffnen und über *„Zum Startbildschirm
hinzufügen"* wie eine App ablegen.

---

## 🏗️ Architektur (modular)
| Datei | Verantwortung |
|------|----------------|
| `main.py` | async Einstiegspunkt (Desktop **und** Web) |
| `settings.py` | Konfiguration; Physik in px/s, Sprite-Sheet-Koordinaten |
| `assets.py` | Sprite-Sheet-Slicing, Freistellen, baked PNGs, FSM-Frames |
| `compat.py` | Plattform-Layer (echtes `pygame.sprite`/`Vector2` ↔ Fallback fürs Web) |
| `particles.py` | Delta-Time-Partikelsystem |
| `background.py` | 3-Ebenen-Parallax mit Paletten-Übergang |
| `entities.py` | `Player` (Vector2 + FSM), `Obstacle`/`Chew`/`Portal` (Sprites) |
| `highscores.py` | persistente Top-10-Bestenliste |
| `game.py` | async Game-Loop, dt, Touch-Input, Level-/Portal-Logik |
| `tools/bake_sprites.py` | Sprites einmalig freistellen → `assets/baked/` |
| `tools/patch_web.py` | Web-Build nachbearbeiten (siehe oben) |

**Kernsysteme:** Vektor-Physik (`pygame.math.Vector2`, Reibung, Momentum,
Coyote-Time, Jump-Buffer), Delta-Time (framerate-unabhängig), Finite State
Machine (IDLE/RUN/JUMP/FALL), `pygame.sprite`-Gruppen für Kollision.

---

## 🎛️ Game Feel justieren (`settings.py`)
- **Sprung:** `JUMP_SPEED`, `JUMP_CUT_MULTIPLIER`, `GRAVITY`, `FALL_MULTIPLIER`
- **Momentum/Reibung:** `PLAYER_ACCEL`, `GROUND_FRICTION` / `AIR_FRICTION`
- **Tempo/Level:** `SCROLL_SPEED`, `LEVELS[*]["speed_mult"]`, `obstacle_gap`
- **Power-ups:** `CHEW_ANGEL_CHANCE`, `SMASH_TIME`, `SHIELD_IFRAME`

## 🖼️ Eigene Sprites
Koordinaten im `SHEET_SLICES`-Dict in `settings.py`. Nach Änderungen neu backen:
```bash
python tools/bake_sprites.py
```
