import shutil
from pathlib import Path

from radio_tui.mpv_controller import MPVController

FAKE_MPV_PATH = Path(__file__).parent / "fixtures" / "fake_mpv.py"


def test_is_installed_reflects_shutil_which(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert MPVController.is_installed() is False

    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/mpv")
    assert MPVController.is_installed() is True


def test_controller_drives_fake_mpv_over_ipc():
    controller = MPVController(mpv_binary=str(FAKE_MPV_PATH))
    controller.start()
    try:
        controller.play("http://example.invalid/stream")
        assert controller.get_now_playing() == "Fake Song Title"
        assert controller.toggle_pause() is True
        assert controller.toggle_pause() is False
        controller.set_volume(150)  # should clamp to 100, must not raise
    finally:
        controller.quit()
