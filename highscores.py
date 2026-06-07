"""
highscores.py - Persistente Top-10-Bestenliste.

Speichert die besten Laeufe in einer JSON-Datei. Robust gegen fehlende/kaputte
Datei und gegen schreibgeschuetzte Umgebungen (z.B. Browser/pygbag) - dort
bleibt die Liste wenigstens fuer die Sitzung erhalten.
"""

import json
import datetime

import settings as cfg


def load():
    """Liest die Bestenliste (Liste aus {'score': int, 'date': str})."""
    try:
        with open(cfg.HIGHSCORE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        cleaned = []
        for e in data:
            try:
                cleaned.append({"score": int(e["score"]), "date": str(e.get("date", ""))})
            except (KeyError, ValueError, TypeError):
                continue
        cleaned.sort(key=lambda e: e["score"], reverse=True)
        return cleaned[: cfg.HIGHSCORE_MAX]
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def save(entries):
    """Schreibt die Bestenliste (bestes-zuerst, max. HIGHSCORE_MAX)."""
    try:
        with open(cfg.HIGHSCORE_FILE, "w", encoding="utf-8") as f:
            json.dump(entries[: cfg.HIGHSCORE_MAX], f, indent=2)
    except OSError:
        pass  # z.B. im Browser nicht schreibbar -> kein Absturz


def add(score):
    """Fuegt einen Score ein. Gibt (liste, platz_index) zurueck.
    platz_index ist der 0-basierte Rang des neuen Eintrags oder None,
    wenn er nicht in die Top 10 kam."""
    entries = load()
    new_entry = {"score": int(score),
                 "date": datetime.date.today().isoformat()}
    entries.append(new_entry)
    entries.sort(key=lambda e: e["score"], reverse=True)
    entries = entries[: cfg.HIGHSCORE_MAX]
    save(entries)

    placed = None
    for i, e in enumerate(entries):
        if e is new_entry:
            placed = i
            break
    return entries, placed


def is_highscore(score):
    """True, wenn der Score in die Top 10 kaeme."""
    entries = load()
    if len(entries) < cfg.HIGHSCORE_MAX:
        return True
    return score > min(e["score"] for e in entries)
