"""Ava clips + brain test — clips auto-appear from the folder, and her
brain reports honestly whether a thinking model is connected."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.ava import Ava
from vaulttec.ava import clips as clips_mod


def test_clips_found_and_random(tmp_path, monkeypatch):
    folder = tmp_path / "assets" / "clips"
    folder.mkdir(parents=True)
    (folder / "fireball.mp4").write_bytes(b"fake")
    (folder / "sexy-dance.mp4").write_bytes(b"fake")
    (folder / "brand-new-move.mp4").write_bytes(b"fake")
    monkeypatch.setattr(clips_mod, "clips_dir", lambda: folder)
    all_clips = clips_mod.list_clips()
    assert len(all_clips) == 3
    assert [c["label"] for c in all_clips if c["kind"] == "jutsu"] == ["🔥 Fireball Jutsu"]
    # Unknown file still appears, labelled from its name — more later works.
    assert any(c["label"] == "Brand New Move" for c in all_clips)
    assert clips_mod.random_clip() is not None
    assert clips_mod.random_clip(kind="sexy")["name"] == "sexy-dance.mp4"
    assert clips_mod.random_clip(kind="nope") is None


def test_clips_empty_when_folder_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(clips_mod, "clips_dir", lambda: tmp_path / "nope")
    assert clips_mod.list_clips() == []
    assert clips_mod.random_clip() is None


def test_brain_status_offline_without_key(monkeypatch):
    monkeypatch.delenv("AVA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AVA_BASE_URL", raising=False)
    ava = Ava()
    status = ava.brain_status()
    assert status["online"] is False
    assert "offline" in status["status"]
    assert "AVA_API_KEY" in status["status"]


def test_brain_status_names_gemini(monkeypatch):
    monkeypatch.setenv("AVA_API_KEY", "test-key")
    monkeypatch.setenv("AVA_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    monkeypatch.setenv("AVA_MODEL", "gemini-2.5-flash")
    ava = Ava()
    status = ava.brain_status()
    assert status["online"] is True
    assert status["provider"] == "Google Gemini (free)"
    assert status["model"] == "gemini-2.5-flash"
