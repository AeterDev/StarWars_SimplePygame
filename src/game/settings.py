"""Game settings and constants."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

WINDOW_WIDTH = 960
WINDOW_HEIGHT = 540
WINDOW_TITLE = "Star Wars Pixel Arcade"
FPS = 60

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOUNDS_DIR = PROJECT_ROOT / "sounds"
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")

BACKGROUND_COLOR = (7, 11, 24)
PANEL_COLOR = (17, 27, 51)
PANEL_BORDER = (92, 195, 255)
TEXT_COLOR = (235, 247, 255)
TEXT_SHADOW = (10, 12, 22)
ACCENT_COLOR = (255, 210, 67)
DANGER_COLOR = (255, 102, 102)
SUCCESS_COLOR = (110, 255, 186)
MUTED_COLOR = (132, 166, 204)
BLACK = (0, 0, 0)

PLAYER_SPEED = 320.0
PLAYER_FIRE_COOLDOWN = 0.18
PLAYER_INVULNERABILITY = 0.8
MAX_HEALTH_HALVES = 6
COIN_INTERVAL_SECONDS = 2.0

MENU_BUTTON_SIZE = (260, 58)
OVERLAY_BUTTON_SIZE = (220, 52)
BUTTON_SPACING = 74

DifficultyName = Literal["easy", "medium", "hard"]


@dataclass(frozen=True, slots=True)
class DifficultyConfig:
    """Difficulty tuning knobs for the arcade session."""

    key: DifficultyName
    label: str
    enemy_speed: float
    asteroid_speed: float
    spawn_interval: float
    asteroid_interval: float
    enemy_fire_interval: float
    aggression: float
    boss_unlock_time: float
    boss_cadence: float


DIFFICULTIES: dict[DifficultyName, DifficultyConfig] = {
    "easy": DifficultyConfig(
        key="easy",
        label="EASY",
        enemy_speed=185.0,
        asteroid_speed=125.0,
        spawn_interval=1.45,
        asteroid_interval=2.2,
        enemy_fire_interval=2.4,
        aggression=0.35,
        boss_unlock_time=42.0,
        boss_cadence=28.0,
    ),
    "medium": DifficultyConfig(
        key="medium",
        label="MEDIUM",
        enemy_speed=225.0,
        asteroid_speed=155.0,
        spawn_interval=1.0,
        asteroid_interval=1.55,
        enemy_fire_interval=1.8,
        aggression=0.58,
        boss_unlock_time=30.0,
        boss_cadence=24.0,
    ),
    "hard": DifficultyConfig(
        key="hard",
        label="HARD",
        enemy_speed=275.0,
        asteroid_speed=195.0,
        spawn_interval=0.72,
        asteroid_interval=1.15,
        enemy_fire_interval=1.18,
        aggression=0.82,
        boss_unlock_time=18.0,
        boss_cadence=20.0,
    ),
}
