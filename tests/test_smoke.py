from __future__ import annotations

from game import __version__
from game.assets import infer_asset_role
from game.settings import DIFFICULTIES, FPS, WINDOW_HEIGHT, WINDOW_WIDTH
from game.ui import heart_states_for_health


def test_project_imports() -> None:
    assert __version__ == "0.1.0"


def test_default_window_settings() -> None:
    assert WINDOW_WIDTH > 0
    assert WINDOW_HEIGHT > 0
    assert FPS > 0


def test_difficulties_increase_pressure() -> None:
    easy = DIFFICULTIES["easy"]
    medium = DIFFICULTIES["medium"]
    hard = DIFFICULTIES["hard"]

    assert easy.spawn_interval > medium.spawn_interval > hard.spawn_interval
    assert easy.enemy_speed < medium.enemy_speed < hard.enemy_speed
    assert easy.aggression < medium.aggression < hard.aggression


def test_asset_role_inference_matches_project_names() -> None:
    assert infer_asset_role("PlayerShip.png") == "player"
    assert infer_asset_role("EnemyBullet.png") == "enemy_bullet"
    assert infer_asset_role("HalfHeart.png") == "half_heart"
    assert infer_asset_role("mystery_asset.png") is None


def test_half_hearts_degrade_into_empty_slots() -> None:
    assert heart_states_for_health(6, 6) == ["heart", "heart", "heart"]
    assert heart_states_for_health(5, 6) == ["heart", "heart", "half_heart"]
    assert heart_states_for_health(1, 6) == ["half_heart", "empty_heart", "empty_heart"]
    assert heart_states_for_health(0, 6) == ["empty_heart", "empty_heart", "empty_heart"]


def test_headless_run_one_frame(monkeypatch) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")

    from game.main import run

    run(max_frames=1)
