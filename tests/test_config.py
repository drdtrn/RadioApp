from radio_tui.config import Config, load_config, save_config


def test_load_config_returns_defaults_when_file_missing(tmp_path):
    config = load_config(tmp_path / "missing.toml")
    assert config == Config()


def test_save_and_load_round_trip(tmp_path):
    config_path = tmp_path / "config.toml"
    original = Config(volume=42, last_tab="SA", mpv_binary="/usr/bin/mpv")

    save_config(config_path, original)
    loaded = load_config(config_path)

    assert loaded == original


def test_load_config_fills_missing_keys_with_defaults(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('volume = 33\n')

    loaded = load_config(config_path)

    assert loaded == Config(volume=33, last_tab="XK", mpv_binary="mpv")
