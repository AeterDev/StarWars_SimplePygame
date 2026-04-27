from game import __version__
from game.settings import FPS, WINDOW_HEIGHT, WINDOW_WIDTH


def test_project_imports() -> None:
    assert __version__ == "0.1.0"


def test_default_window_settings() -> None:
    assert WINDOW_WIDTH > 0
    assert WINDOW_HEIGHT > 0
    assert FPS > 0

