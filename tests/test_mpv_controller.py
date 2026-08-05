import shutil
import time
from pathlib import Path

import pytest

from radio_tui.mpv_controller import IPC_TIMEOUT_SECONDS, MPVController

FAKE_MPV_PATH = Path(__file__).parent / "fixtures" / "fake_mpv.py"
HANGING_MPV_PATH = Path(__file__).parent / "fixtures" / "hanging_mpv.py"
HANGING_RESPONSE_MPV_PATH = Path(__file__).parent / "fixtures" / "hanging_response_mpv.py"
EXITING_MPV_PATH = Path(__file__).parent / "fixtures" / "exiting_mpv.py"


def _force_kill(controller: MPVController) -> None:
    """Tear down a controller without going through quit() (which itself does
    an IPC round trip that would time out against an unresponsive fixture)."""
    if controller._process is not None:
        controller._process.terminate()
        controller._process.wait(timeout=2)
    if controller._socket_dir is not None:
        shutil.rmtree(controller._socket_dir, ignore_errors=True)


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


def test_start_cleans_up_on_connect_timeout():
    controller = MPVController(mpv_binary=str(HANGING_MPV_PATH))
    with pytest.raises(ConnectionError):
        controller.start()

    assert controller._process.poll() is not None
    assert Path(controller._socket_dir).exists() is False


def test_start_cleans_up_when_process_exits_immediately():
    controller = MPVController(mpv_binary=str(EXITING_MPV_PATH))
    with pytest.raises(ConnectionError):
        controller.start()

    assert controller._process.poll() is not None
    assert Path(controller._socket_dir).exists() is False


def test_get_now_playing_times_out_instead_of_hanging_forever():
    """If mpv accepts the IPC connection but stops responding, get_now_playing()
    must return None within the IPC timeout window rather than blocking the
    caller (the UI thread, in practice) forever."""
    controller = MPVController(mpv_binary=str(HANGING_RESPONSE_MPV_PATH))
    controller.start()
    try:
        start = time.monotonic()
        assert controller.get_now_playing() is None
        elapsed = time.monotonic() - start

        assert elapsed < IPC_TIMEOUT_SECONDS + 2.0
    finally:
        _force_kill(controller)


def test_had_playback_error_reports_true_after_unresponsive_mpv():
    """A get_now_playing() timeout should be surfaced by had_playback_error()
    (once), so RadioApp._poll_now_playing marks the station unavailable via
    its existing error-handling path instead of silently doing nothing."""
    controller = MPVController(mpv_binary=str(HANGING_RESPONSE_MPV_PATH))
    controller.start()
    try:
        assert controller.get_now_playing() is None

        assert controller.had_playback_error() is True
        # The flag is consumed by the first check; it should not repeat-fire.
        assert controller.had_playback_error() is False
    finally:
        _force_kill(controller)


def test_quit_does_not_raise_when_mpv_is_unresponsive():
    """quit() sends a 'quit' IPC command and awaits a reply. Against an mpv
    that has wedged (accepted the connection, never responds), that call now
    times out (same IPC timeout as get_now_playing()) instead of hanging
    forever -- but quit() must swallow that timeout (like it already
    swallows ConnectionError for an mpv that's already gone) and still tear
    down the subprocess/socket dir, rather than raising out of
    RadioApp.action_quit()."""
    controller = MPVController(mpv_binary=str(HANGING_RESPONSE_MPV_PATH))
    controller.start()

    start = time.monotonic()
    controller.quit()  # must not raise
    elapsed = time.monotonic() - start

    assert elapsed < IPC_TIMEOUT_SECONDS + 2.0
    assert controller._process.poll() is not None
    assert Path(controller._socket_dir).exists() is False
