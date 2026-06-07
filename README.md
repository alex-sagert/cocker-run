# 🐶 Cocker Run – Aiva

Ein 2.5D-Endless-Runner in **Python / Pygame** mit dem Englisch Cocker Spaniel
**Aiva**. Sammle Kaustangen 🦴, weiche Hindernissen aus, springe durch Portale
in neue Level – und jage den höchsten Rang (S/A/B/C/D)!

Läuft **nativ am Desktop** und **im Browser** (WebAssembly via `pygbag`) –
inklusive **Touch-Steuerung fürs Handy**.

---

## 🎮 Steuerung
| | Desktop | Handy / Browser |
|---|---|---|
| Springen (variabel) | Pfeil **↑** | **▲**-Button |
| Bewegen | Pfeil **←/→** | **◀ ▶**-Buttons |
| Neustart (Game Over) | Leertaste / Enter | Bildschirm tippen |

*Tipp:* Pfeil **rechts halten beim Absprung** = Anlauf-Sprung (höher & weiter, dank Momentum).

---

## 🏗️ Architektur (modular)
| Datei | Verantwortung |
|------|----------------|
| `main.py` | async Einstiegspunkt (Desktop **und** Web) |
| `settings.py` | Konfiguration; **Physik in px/s**, Sprite-Sheet-Koordinaten |
| `assets.py` | Sprite-Sheet-Slicing, Freistellen, baked PNGs, FSM-Frames |
| `particles.py` | Delta-Time-Partikelsystem |
| `background.py` | 3-Ebenen-Parallax mit Paletten-Übergang |
| `entities.py` | `Player` (Vector2 + FSM), `Obstacle`/`Chew`/`Portal` (Sprites) |
| `game.py` | async Game-Loop, dt, Touch-Input, Level-/Portal-Logik |
| `tools/bake_sprites.py` | Sprites einmalig freistellen → `assets/baked/` |

**Profi-Systeme:** Vektor-Physik (`pygame.math.Vector2`, Reibung, Momentum),
Delta-Time (framerate-unabhängig), Finite State Machine (IDLE/RUN/JUMP/FALL),
`pygame.sprite.Group` für performante Kollision.

---

## ▶️ Lokal starten (Desktop)
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows PowerShell
pip install -r requirements.txt
python main.py
```

---

## 🌐 Web-Version bauen & im Browser testen
```bash
pip install pygbag
pygbag main.py        # startet lokalen Testserver: http://localhost:8000
# oder nur bauen (Ausgabe in build/web/):
pygbag --build main.py
```
Öffne `http://localhost:8000` im Browser. Beim ersten Mal dauert das Laden
etwas (WebAssembly-Runtime).

---

## 🚀 Auf GitHub Pages veröffentlichen (→ Link für WhatsApp)
1. Repository auf GitHub anlegen und Code pushen (Branch `main`).
2. **Settings → Pages → Build and deployment → Source: „GitHub Actions"**.
3. Der enthaltene Workflow `.github/workflows/deploy.yml` baut das Spiel
   automatisch mit `pygbag` und veröffentlicht es.
4. Nach dem Durchlauf findest du den Link unter **Settings → Pages**
   (Form: `https://<dein-name>.github.io/<repo>/`).
5. **Diesen Link per WhatsApp verschicken** – deine Freundin öffnet ihn am
   Handy, kein Download, Touch-Steuerung inklusive. 🎉

---

## 🎛️ Game Feel justieren (`settings.py`)
- **Sprung:** `JUMP_SPEED` (Höhe), `JUMP_CUT_MULTIPLIER` (Tipp = kleiner Hopser),
  `GRAVITY`, `FALL_MULTIPLIER`.
- **Momentum/Reibung:** `PLAYER_ACCEL`, `MAX_RUN_SPEED`,
  `GROUND_FRICTION` / `AIR_FRICTION` (näher an 1 = mehr Momentum),
  `MOMENTUM_JUMP_BONUS`, `MOMENTUM_MAX_X_EXTEND`.
- **Tempo/Level:** `SCROLL_SPEED`, `LEVELS[*]["speed_mult"]`, `obstacle_gap`.

## 🖼️ Eigene Sprites
Koordinaten im `SHEET_SLICES`-Dict in `settings.py` (Hilfe: `assets/SHEET_grid.png`).
Nach Änderungen Sprites neu backen:
```bash
python tools/bake_sprites.py
```
Weitere Kategorien aus dem Sheet aktivieren: `SHEET_USE = {"player","obstacles","chews","portal"}`.
