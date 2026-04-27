"""User interface helpers and widgets."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from .assets import AssetLibrary
from .settings import (
    ACCENT_COLOR,
    DANGER_COLOR,
    MUTED_COLOR,
    PANEL_BORDER,
    PANEL_COLOR,
    SUCCESS_COLOR,
    TEXT_COLOR,
    TEXT_SHADOW,
)


@dataclass(frozen=True, slots=True)
class UIFonts:
    """Fonts used across the game."""

    title: pygame.font.Font
    subtitle: pygame.font.Font
    menu: pygame.font.Font
    hud: pygame.font.Font
    small: pygame.font.Font


def build_fonts() -> UIFonts:
    return UIFonts(
        title=pygame.font.Font(None, 68),
        subtitle=pygame.font.Font(None, 32),
        menu=pygame.font.Font(None, 40),
        hud=pygame.font.Font(None, 28),
        small=pygame.font.Font(None, 22),
    )


def draw_arcade_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    position: tuple[int, int],
    *,
    color: tuple[int, int, int] = TEXT_COLOR,
    shadow_color: tuple[int, int, int] = TEXT_SHADOW,
    glow_color: tuple[int, int, int] | None = None,
    align: str = "center",
) -> pygame.Rect:
    """Render chunky arcade text with a shadow and optional glow."""

    if glow_color:
        glow = font.render(text, False, glow_color)
        glow.set_alpha(95)
        for delta in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            glow_rect = glow.get_rect()
            setattr(glow_rect, align, (position[0] + delta[0], position[1] + delta[1]))
            surface.blit(glow, glow_rect)

    shadow = font.render(text, False, shadow_color)
    shadow_rect = shadow.get_rect()
    setattr(shadow_rect, align, (position[0] + 3, position[1] + 3))
    surface.blit(shadow, shadow_rect)

    label = font.render(text, False, color)
    rect = label.get_rect()
    setattr(rect, align, position)
    surface.blit(label, rect)
    return rect


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    fill: tuple[int, int, int] = PANEL_COLOR,
    border: tuple[int, int, int] = PANEL_BORDER,
    glow_alpha: int = 0,
) -> None:
    """Draw a pixel-ish panel with a subtle glow."""

    if glow_alpha:
        glow_surface = pygame.Surface((rect.width + 18, rect.height + 18), pygame.SRCALPHA)
        pygame.draw.rect(
            glow_surface,
            (*border, glow_alpha),
            glow_surface.get_rect(),
            border_radius=10,
        )
        surface.blit(glow_surface, (rect.x - 9, rect.y - 9))

    pygame.draw.rect(surface, fill, rect, border_radius=6)
    pygame.draw.rect(surface, border, rect, width=3, border_radius=6)


@dataclass(slots=True)
class Button:
    """Interactive menu button."""

    label: str
    action: str
    center: tuple[int, int]
    size: tuple[int, int]
    hover_t: float = 0.0
    press_t: float = 0.0

    def update(self, dt: float, *, hovered: bool, pressed: bool, selected: bool) -> None:
        hover_target = 1.0 if hovered or selected else 0.0
        press_target = 1.0 if pressed and hovered else 0.0
        self.hover_t += (hover_target - self.hover_t) * min(1.0, dt * 10.0)
        self.press_t += (press_target - self.press_t) * min(1.0, dt * 16.0)

    def rect(self) -> pygame.Rect:
        scale = 1.0 + (0.05 * self.hover_t) - (0.03 * self.press_t)
        width = round(self.size[0] * scale)
        height = round(self.size[1] * scale)
        rect = pygame.Rect(0, 0, width, height)
        rect.center = self.center
        return rect

    def contains(self, position: tuple[float, float]) -> bool:
        return self.rect().collidepoint(position)

    def draw(self, surface: pygame.Surface, fonts: UIFonts, *, selected: bool) -> None:
        rect = self.rect()
        accent = SUCCESS_COLOR if self.action == "easy" else PANEL_BORDER
        if self.action == "hard":
            accent = DANGER_COLOR
        elif self.action == "medium":
            accent = ACCENT_COLOR
        elif self.action in {"exit", "menu"}:
            accent = MUTED_COLOR

        if selected and self.hover_t < 0.6:
            accent = ACCENT_COLOR

        draw_panel(surface, rect, fill=PANEL_COLOR, border=accent, glow_alpha=70 + round(self.hover_t * 80))
        draw_arcade_text(
            surface,
            fonts.menu,
            self.label,
            rect.center,
            color=TEXT_COLOR,
            glow_color=accent,
        )


def heart_states_for_health(health_halves: int, max_health_halves: int) -> list[str]:
    """Return the heart fill state per heart slot."""

    states: list[str] = []
    remaining = max(0, health_halves)
    slots = max_health_halves // 2
    for _ in range(slots):
        if remaining >= 2:
            states.append("heart")
        elif remaining == 1:
            states.append("half_heart")
        else:
            states.append("empty_heart")
        remaining = max(0, remaining - 2)
    return states


def create_scanline_overlay(size: tuple[int, int]) -> pygame.Surface:
    overlay = pygame.Surface(size, pygame.SRCALPHA)
    for y_position in range(0, size[1], 4):
        pygame.draw.line(overlay, (0, 0, 0, 20), (0, y_position), (size[0], y_position))
    return overlay


def draw_hud(
    surface: pygame.Surface,
    assets: AssetLibrary,
    fonts: UIFonts,
    *,
    health_halves: int,
    max_health_halves: int,
    coins: int,
    coin_pulse: float,
    score: int,
    difficulty_label: str,
    boss_health_ratio: float | None,
) -> None:
    """Draw health, coins, score, and boss information."""

    draw_panel(surface, pygame.Rect(18, 16, 252, 68), glow_alpha=55)
    draw_panel(surface, pygame.Rect(surface.get_width() - 236, 16, 218, 68), glow_alpha=55)

    x_position = 34
    for role in heart_states_for_health(health_halves, max_health_halves):
        if assets.has(role):
            heart = assets.image(role, (34, 34))
            surface.blit(heart, (x_position, 33))
        x_position += 40

    coin_scale = 1.0 + (coin_pulse * 0.18)
    coin_size = round(34 * coin_scale)
    coin = assets.image("coin", (coin_size, coin_size))
    coin_rect = coin.get_rect(midleft=(surface.get_width() - 214, 50))
    surface.blit(coin, coin_rect)

    draw_arcade_text(
        surface,
        fonts.hud,
        f"x {coins}",
        (surface.get_width() - 152, 50),
        align="midleft",
        color=ACCENT_COLOR,
        glow_color=(255, 223, 110),
    )
    draw_arcade_text(
        surface,
        fonts.small,
        f"SCORE {score}",
        (surface.get_width() - 126, 31),
        align="midleft",
        color=TEXT_COLOR,
    )
    draw_arcade_text(
        surface,
        fonts.small,
        difficulty_label,
        (136, 24),
        align="midleft",
        color=MUTED_COLOR,
    )

    if boss_health_ratio is not None:
        bar_rect = pygame.Rect(surface.get_width() // 2 - 170, 16, 340, 20)
        draw_panel(surface, bar_rect, fill=(21, 18, 34), border=DANGER_COLOR, glow_alpha=55)
        fill_rect = bar_rect.inflate(-8, -8)
        fill_rect.width = max(8, round(fill_rect.width * boss_health_ratio))
        pygame.draw.rect(surface, DANGER_COLOR, fill_rect, border_radius=4)
        draw_arcade_text(
            surface,
            fonts.small,
            "BOSS",
            (surface.get_width() // 2, 48),
            color=DANGER_COLOR,
            glow_color=(255, 145, 145),
        )
