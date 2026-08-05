from radio_tui import __main__


class _FakeApp:
    def __init__(self):
        self.return_code = 0
        self.ran = False

    def run(self):
        self.ran = True


def test_main_runs_app_and_returns_zero_when_mpv_installed(monkeypatch):
    monkeypatch.setattr(__main__.MPVController, "is_installed", staticmethod(lambda mpv_binary="mpv": True))
    fake_app = _FakeApp()
    monkeypatch.setattr(__main__, "RadioApp", lambda: fake_app)

    exit_code = __main__.main()

    assert fake_app.ran is True
    assert exit_code == 0


def test_main_returns_app_return_code(monkeypatch):
    monkeypatch.setattr(__main__.MPVController, "is_installed", staticmethod(lambda mpv_binary="mpv": True))
    fake_app = _FakeApp()
    fake_app.return_code = 1
    monkeypatch.setattr(__main__, "RadioApp", lambda: fake_app)

    assert __main__.main() == 1


def test_main_returns_one_when_mpv_missing(monkeypatch, capsys):
    monkeypatch.setattr(__main__.MPVController, "is_installed", staticmethod(lambda mpv_binary="mpv": False))

    exit_code = __main__.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "mpv" in captured.err.lower()
