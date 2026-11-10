"""Ava's clips — her dancing, her sexy moments, and her jutsus.

Clips live in ``assets/clips/`` as plain ``.mp4`` files (binary, so
they are never pushed to GitHub — they are saved to the PC by hand,
like the logo and the avatar). Adding more later is the whole point:
drop a new ``.mp4`` into that folder and it shows up automatically —
no code change, no redeploy of the list. A file whose name is not in
``KNOWN_CLIPS`` still appears, labelled from its file name.

Two kinds:
- ``sexy`` — her playful, flirty clips (dance, wink, walk).
- ``jutsu`` — her Naruto-style jutsus (fireball, Rasengan, Chidori,
  Shadow Clone, Water Dragon). She normally chills; a random clip is
  her showing off.
"""
from __future__ import annotations

import random
from pathlib import Path

KNOWN_CLIPS: dict[str, dict[str, str]] = {
    "sexy-dance.mp4": {"label": "💃 Sexy dance", "kind": "sexy"},
    "sexy-wink.mp4": {"label": "😉 Wink & kiss", "kind": "sexy"},
    "sexy-walk.mp4": {"label": "🔥 Slow walk", "kind": "sexy"},
    "fireball.mp4": {"label": "🔥 Fireball Jutsu", "kind": "jutsu"},
    "rasengan.mp4": {"label": "🌀 Rasengan", "kind": "jutsu"},
    "chidori.mp4": {"label": "⚡ Chidori", "kind": "jutsu"},
    "shadow-clone.mp4": {"label": "👥 Shadow Clone Jutsu", "kind": "jutsu"},
    "water-dragon.mp4": {"label": "🐉 Water Dragon Jutsu", "kind": "jutsu"},
}


def clips_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "assets" / "clips"


def list_clips(kind: str | None = None) -> list[dict]:
    """Every clip file found, with label + kind. Sorted by name so the
    list is stable. Unknown files get a label from their file name."""
    clips = []
    folder = clips_dir()
    if not folder.exists():
        return []
    for path in sorted(folder.glob("*.mp4")):
        info = KNOWN_CLIPS.get(path.name, {
            "label": path.stem.replace("-", " ").replace("_", " ").title(),
            "kind": "clip",
        })
        if kind is None or info["kind"] == kind:
            clips.append({"file": str(path), "name": path.name, **info})
    return clips


def random_clip(kind: str | None = None) -> dict | None:
    """One random clip — how Ava surprises you. None when no clips
    are saved yet."""
    clips = list_clips(kind)
    return random.choice(clips) if clips else None
