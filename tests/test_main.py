from radio_tui.__main__ import main


def test_main_prints_version_and_returns_zero(capsys):
    exit_code = main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "radio-tui" in captured.out
