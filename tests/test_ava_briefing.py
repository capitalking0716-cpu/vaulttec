"""Ava's briefing — she reads briefing.md before every answer.

The loader returns "" when the file is missing or unreadable and
never raises. ask() and brief() both carry the briefing text.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import vaulttec.ava.briefing as briefing_mod
from vaulttec.ava import Ava, load_briefing


def test_load_briefing_reads_the_file():
    text = load_briefing()
    assert text
    assert "wide-6" in text
    # Status and strategy only — no key material, no account numbers.
    assert "sk-" not in text
    assert "AVA_API_KEY = " not in text


def test_load_briefing_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(briefing_mod, "briefing_path",
                        lambda: tmp_path / "no-such-briefing.md")
    assert load_briefing() == ""


def test_load_briefing_empty_when_unreadable(tmp_path, monkeypatch):
    bad = tmp_path / "briefing.md"
    bad.write_bytes(b"\xff\xfe\x00bad bytes")
    monkeypatch.setattr(briefing_mod, "briefing_path", lambda: bad)
    assert load_briefing() == ""


def test_ask_carries_briefing_offline(tmp_path, monkeypatch):
    import vaulttec.ava.lessons as lessons_mod

    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    monkeypatch.delenv("AVA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    note = tmp_path / "briefing.md"
    note.write_text("TEST BRIEFING MARKER — wide-6 is the lead.", encoding="utf-8")
    monkeypatch.setattr(briefing_mod, "briefing_path", lambda: note)
    ava = Ava()
    ctx = {"portfolio": {"cash": 100.0, "value": 100.0, "pnl": 0.0},
           "open_trades": [], "signals": []}
    answer = ava.ask("What is the plan?", ctx)
    assert "TEST BRIEFING MARKER" in answer
    assert "offline mode" in answer
    assert "never place trades" in answer


def test_brief_carries_briefing(tmp_path, monkeypatch):
    import vaulttec.ava.lessons as lessons_mod

    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    note = tmp_path / "briefing.md"
    note.write_text("TEST BRIEFING MARKER — wide-6 is the lead.", encoding="utf-8")
    monkeypatch.setattr(briefing_mod, "briefing_path", lambda: note)
    ava = Ava()
    ctx = {"portfolio": {"cash": 100.0, "value": 100.0, "pnl": 0.0},
           "open_trades": []}
    assert "TEST BRIEFING MARKER" in ava.brief(ctx)
    assert "I'm Ava" in ava.brief(ctx)


def test_ask_and_brief_work_with_no_briefing_file(tmp_path, monkeypatch):
    import vaulttec.ava.lessons as lessons_mod

    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    monkeypatch.delenv("AVA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(briefing_mod, "briefing_path",
                        lambda: tmp_path / "no-such-briefing.md")
    ava = Ava()
    ctx = {"portfolio": {"cash": 100.0, "value": 100.0, "pnl": 0.0},
           "open_trades": [], "signals": []}
    assert "offline mode" in ava.ask("What is the plan?", ctx)
    assert "I'm Ava" in ava.brief(ctx)
