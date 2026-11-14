from pathlib import Path

from core.models import CrawlerConfig


def test_bundled_extension_is_discovered() -> None:
    config = CrawlerConfig(search_prompt="test")

    paths = config.get_extension_paths()

    assert any(path.endswith("i-still-dont-care-about-cookies") for path in paths)
    assert all((Path(path) / "manifest.json").is_file() for path in paths)


def test_browser_args_include_extension_flags() -> None:
    config = CrawlerConfig(search_prompt="test")

    args = config.to_browser_args()["args"]

    assert any(arg.startswith("--load-extension=") for arg in args)
    assert any(arg.startswith("--disable-extensions-except=") for arg in args)


def test_explicit_profile_path_wins(monkeypatch) -> None:
    monkeypatch.setenv("CHROME_PROFILE_PATH", "/tmp/from-env")

    config = CrawlerConfig(chrome_profile_path="/tmp/explicit")

    assert config.chrome_profile_path == "/tmp/explicit"


def test_profile_path_can_come_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("CHROME_PROFILE_PATH", "/tmp/from-env")

    config = CrawlerConfig()

    assert config.chrome_profile_path == "/tmp/from-env"


def test_default_profile_path_is_inside_core(monkeypatch) -> None:
    monkeypatch.delenv("CHROME_PROFILE_PATH", raising=False)

    config = CrawlerConfig()

    assert config.chrome_profile_path.endswith("core/Chrome_Profile")
