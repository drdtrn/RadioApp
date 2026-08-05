from radio_tui import __main__
from radio_tui.config import Config


class _FakeApp:
    def __init__(self):
        self.return_code = 0
        self.ran = False

    def run(self):
        self.ran = True


def _stub_config(monkeypatch, mpv_binary="mpv"):
    """Isolate main() from whatever config.toml happens to exist on this machine."""
    monkeypatch.setattr(
        __main__.config_module, "load_config", lambda path: Config(mpv_binary=mpv_binary)
    )


def test_main_runs_app_and_returns_zero_when_mpv_installed(monkeypatch):
    _stub_config(monkeypatch)
    monkeypatch.setattr(__main__.MPVController, "is_installed", staticmethod(lambda mpv_binary="mpv": True))
    fake_app = _FakeApp()
    monkeypatch.setattr(__main__, "RadioApp", lambda: fake_app)

    exit_code = __main__.main()

    assert fake_app.ran is True
    assert exit_code == 0


def test_main_returns_app_return_code(monkeypatch):
    _stub_config(monkeypatch)
    monkeypatch.setattr(__main__.MPVController, "is_installed", staticmethod(lambda mpv_binary="mpv": True))
    fake_app = _FakeApp()
    fake_app.return_code = 1
    monkeypatch.setattr(__main__, "RadioApp", lambda: fake_app)

    assert __main__.main() == 1


def test_main_returns_one_when_mpv_missing(monkeypatch, capsys):
    _stub_config(monkeypatch)
    monkeypatch.setattr(__main__.MPVController, "is_installed", staticmethod(lambda mpv_binary="mpv": False))

    exit_code = __main__.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "mpv" in captured.err.lower()


def test_main_checks_is_installed_against_configured_mpv_binary(monkeypatch):
    """A custom mpv_binary in config.toml must be what gets validated, not the
    hardcoded default — this is what regressed in the original bug."""
    _stub_config(monkeypatch, mpv_binary="/opt/custom/mpv")
    received = {}

    def fake_is_installed(mpv_binary="mpv"):
        received["binary"] = mpv_binary
        return True

    monkeypatch.setattr(__main__.MPVController, "is_installed", staticmethod(fake_is_installed))
    fake_app = _FakeApp()
    monkeypatch.setattr(__main__, "RadioApp", lambda: fake_app)

    exit_code = __main__.main()

    assert received["binary"] == "/opt/custom/mpv"
    assert exit_code == 0


def test_main_reports_configured_binary_when_missing(monkeypatch, capsys):
    _stub_config(monkeypatch, mpv_binary="/opt/custom/mpv")
    monkeypatch.setattr(
        __main__.MPVController, "is_installed", staticmethod(lambda mpv_binary="mpv": False)
    )

    exit_code = __main__.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "/opt/custom/mpv" in captured.err
