"""Asset discovery and loading utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pygame

from .settings import IMAGE_EXTENSIONS, PROJECT_ROOT, SOUNDS_DIR

ROLE_MATCHERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("player_bullet", ("player", "bullet")),
    ("enemy_bullet", ("enemy", "bullet")),
    ("half_heart", ("half", "heart")),
    ("start_menu", ("start", "menu")),
    ("game_over", ("game", "over")),
    ("background", ("background",)),
    ("stars", ("stars",)),
    ("asteroid", ("asteroid",)),
    ("explosion", ("explosion",)),
    ("boss", ("boss",)),
    ("coin", ("coin",)),
    ("enemy", ("enemy",)),
    ("player", ("player",)),
    ("heart", ("heart",)),
)

SOUND_MATCHERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("fire", ("fire",)),
    ("game_over", ("game", "over")),
    ("select", ("plane", "change")),
)


def infer_asset_role(filename: str) -> str | None:
    """Infer the semantic role of an asset based on its filename."""

    normalized = Path(filename).stem.lower().replace("-", "_").replace(" ", "_")
    tokens = tuple(token for token in normalized.split("_") if token)

    for role, required_tokens in ROLE_MATCHERS:
        if all(token in tokens or token in normalized for token in required_tokens):
            return role
    return None


def infer_sound_role(filename: str) -> str | None:
    """Infer a sound role from its filename."""

    normalized = Path(filename).stem.lower().replace("-", "_").replace(" ", "_")
    tokens = tuple(token for token in normalized.split("_") if token)

    for role, required_tokens in SOUND_MATCHERS:
        if all(token in tokens or token in normalized for token in required_tokens):
            return role
    return None


@dataclass(frozen=True, slots=True)
class AssetManifest:
    """Resolved asset files available in the project."""

    images: dict[str, Path]
    sounds: dict[str, Path]

    @classmethod
    def from_project_root(cls, root: Path = PROJECT_ROOT) -> "AssetManifest":
        images: dict[str, Path] = {}
        for path in sorted(root.iterdir()):
            if path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            role = infer_asset_role(path.name)
            if role and role not in images:
                images[role] = path

        sounds: dict[str, Path] = {}
        if SOUNDS_DIR.exists():
            for path in sorted(SOUNDS_DIR.iterdir()):
                if not path.is_file():
                    continue
                role = infer_sound_role(path.name)
                if role and role not in sounds:
                    sounds[role] = path

        return cls(images=images, sounds=sounds)


class SoundBank:
    """Small wrapper around pygame sounds with graceful fallbacks."""

    def __init__(self, sound_paths: dict[str, Path]) -> None:
        self.enabled = pygame.mixer.get_init() is not None
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        if not self.enabled:
            return

        for role, path in sound_paths.items():
            try:
                self._sounds[role] = pygame.mixer.Sound(path.as_posix())
            except pygame.error:
                continue

        if "fire" in self._sounds:
            self._sounds["fire"].set_volume(0.2)
        if "game_over" in self._sounds:
            self._sounds["game_over"].set_volume(0.45)
        if "select" in self._sounds:
            self._sounds["select"].set_volume(0.18)

    def play(self, role: str) -> None:
        sound = self._sounds.get(role)
        if sound is not None:
            sound.play()


class AssetLibrary:
    """Loads and caches surfaces derived from project assets."""

    def __init__(self, manifest: AssetManifest) -> None:
        self.available_roles = frozenset(manifest.images)
        self._base_surfaces: dict[str, pygame.Surface] = {}
        self._cache: dict[tuple[str, tuple[int, int], bool, int], pygame.Surface] = {}

        for role, path in manifest.images.items():
            self._base_surfaces[role] = pygame.image.load(path.as_posix()).convert_alpha()

        if "heart" in self._base_surfaces and "empty_heart" not in self._base_surfaces:
            self._base_surfaces["empty_heart"] = self._make_empty_heart(self._base_surfaces["heart"])

        self.sounds = SoundBank(manifest.sounds)

    def has(self, role: str) -> bool:
        return role in self._base_surfaces

    def image(
        self,
        role: str,
        size: tuple[int, int] | None = None,
        *,
        cover: bool = False,
        rotation: int = 0,
    ) -> pygame.Surface:
        """Return a cached surface variant for a given role."""

        if role not in self._base_surfaces:
            raise KeyError(f"Missing asset role: {role}")

        base = self._base_surfaces[role]
        if size is None and rotation == 0 and not cover:
            return base

        target_size = size or base.get_size()
        cache_key = (role, target_size, cover, rotation)
        if cache_key in self._cache:
            return self._cache[cache_key]

        if cover:
            surface = self._scale_cover(base, target_size)
        else:
            surface = pygame.transform.scale(base, target_size)

        if rotation:
            surface = pygame.transform.rotate(surface, rotation)

        self._cache[cache_key] = surface
        return surface

    @staticmethod
    def _scale_cover(surface: pygame.Surface, size: tuple[int, int]) -> pygame.Surface:
        src_width, src_height = surface.get_size()
        dst_width, dst_height = size
        scale = max(dst_width / src_width, dst_height / src_height)
        scaled_size = (
            max(1, round(src_width * scale)),
            max(1, round(src_height * scale)),
        )
        scaled = pygame.transform.scale(surface, scaled_size)
        result = pygame.Surface(size, pygame.SRCALPHA)
        rect = scaled.get_rect(center=(dst_width // 2, dst_height // 2))
        result.blit(scaled, rect)
        return result

    @staticmethod
    def _make_empty_heart(full_heart: pygame.Surface) -> pygame.Surface:
        empty = full_heart.copy()
        empty.fill((65, 80, 104, 165), special_flags=pygame.BLEND_RGBA_MULT)
        veil = pygame.Surface(empty.get_size(), pygame.SRCALPHA)
        veil.fill((28, 33, 50, 110))
        empty.blit(veil, (0, 0))
        return empty
