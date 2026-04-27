"""Application entry point."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from .assets import AssetLibrary, AssetManifest
from .gameplay import ControlState, GameSession
from .settings import (
    ACCENT_COLOR,
    BACKGROUND_COLOR,
    BLACK,
    BUTTON_SPACING,
    DIFFICULTIES,
    FPS,
    MENU_BUTTON_SIZE,
    MUTED_COLOR,
    OVERLAY_BUTTON_SIZE,
    PANEL_COLOR,
    TEXT_COLOR,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from .ui import Button, build_fonts, create_scanline_overlay, draw_arcade_text, draw_panel


@dataclass(slots=True)
class PointerState:
    """Pointer interaction state shared across menu overlays."""

    position: tuple[float, float]
    is_down: bool = False
    touch_active: bool = False


class ArcadeShooterApp:
    """Main application controller with menu, gameplay, and overlays."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.assets = AssetLibrary(AssetManifest.from_project_root())
        self.fonts = build_fonts()
        self.scanlines = create_scanline_overlay(screen.get_size())
        self.pointer = PointerState(position=(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
        self.scene = "menu"
        self.transition_alpha = 255.0
        self.elapsed = 0.0
        self.selected_indices = {"menu": 0, "paused": 0, "game_over": 0}
        self.session: GameSession | None = None
        self.menu_buttons = self._build_buttons(
            (("EASY", "easy"), ("MEDIUM", "medium"), ("HARD", "hard"), ("EXIT", "exit")),
            center_y=WINDOW_HEIGHT // 2 + 28,
            size=MENU_BUTTON_SIZE,
        )
        self.pause_buttons = self._build_buttons(
            (("RESUME", "resume"), ("RESTART", "restart"), ("MENU", "menu")),
            center_y=WINDOW_HEIGHT // 2 + 18,
            size=OVERLAY_BUTTON_SIZE,
        )
        self.game_over_buttons = self._build_buttons(
            (("RETRY", "restart"), ("MENU", "menu")),
            center_y=WINDOW_HEIGHT // 2 + 110,
            size=OVERLAY_BUTTON_SIZE,
        )

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            return False

        if event.type == pygame.MOUSEMOTION:
            self.pointer.position = event.pos

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.pointer.position = event.pos
            self.pointer.is_down = True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.pointer.position = event.pos
            self.pointer.is_down = False
            self._activate_hovered_button()

        if event.type == pygame.FINGERDOWN:
            self.pointer.touch_active = True
            self.pointer.is_down = True
            self.pointer.position = self._finger_position(event)

        if event.type == pygame.FINGERMOTION:
            self.pointer.position = self._finger_position(event)

        if event.type == pygame.FINGERUP:
            self.pointer.position = self._finger_position(event)
            self.pointer.is_down = False
            self.pointer.touch_active = False
            self._activate_hovered_button()

        if event.type == pygame.KEYDOWN:
            if self.scene == "menu":
                return self._handle_menu_key(event.key)
            if self.scene == "playing" and event.key == pygame.K_ESCAPE:
                self.scene = "paused"
                self.transition_alpha = 180.0
            elif self.scene == "paused":
                return self._handle_pause_key(event.key)
            elif self.scene == "game_over":
                return self._handle_game_over_key(event.key)

        return True

    def update(self, dt: float) -> bool:
        self.elapsed += dt
        self.transition_alpha = max(0.0, self.transition_alpha - dt * 420.0)

        if self.scene == "playing" and self.session is not None:
            self.session.update(dt, self._controls())
            if self.session.game_over:
                self.scene = "game_over"
                self.selected_indices["game_over"] = 0
                self.transition_alpha = 220.0

        self._update_buttons(dt)
        return True

    def draw(self) -> None:
        if self.scene == "menu":
            self._draw_background(primary="start_menu", secondary="stars", speed=24.0)
            self._draw_menu()
        else:
            self._draw_background(primary="background", secondary="stars", speed=56.0)
            if self.session is not None:
                self.session.draw(self.screen, self.fonts)
            if self.scene == "paused":
                self._draw_pause_overlay()
            elif self.scene == "game_over":
                self._draw_game_over_overlay()

        self.screen.blit(self.scanlines, (0, 0))

        if self.transition_alpha > 0:
            fade = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            fade.fill((0, 0, 0, round(self.transition_alpha)))
            self.screen.blit(fade, (0, 0))

    def _draw_background(self, *, primary: str, secondary: str, speed: float) -> None:
        if self.assets.has(primary):
            background = self.assets.image(primary, self.screen.get_size(), cover=True)
            self.screen.blit(background, (0, 0))
        else:
            self.screen.fill(BACKGROUND_COLOR)

        if self.assets.has(secondary):
            stars = self.assets.image(secondary, self.screen.get_size(), cover=True)
            offset = round((self.elapsed * speed) % self.screen.get_height())
            self.screen.blit(stars, (0, offset - self.screen.get_height()))
            self.screen.blit(stars, (0, offset))

        veil = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        veil.fill((6, 12, 28, 90))
        self.screen.blit(veil, (0, 0))

    def _draw_menu(self) -> None:
        title_y = 90
        draw_arcade_text(
            self.screen,
            self.fonts.title,
            "STAR WARS",
            (WINDOW_WIDTH // 2, title_y),
            color=TEXT_COLOR,
            glow_color=ACCENT_COLOR,
        )
        draw_arcade_text(
            self.screen,
            self.fonts.subtitle,
            "PIXEL ARCADE SHOOTER",
            (WINDOW_WIDTH // 2, title_y + 42),
            color=ACCENT_COLOR,
        )
        draw_arcade_text(
            self.screen,
            self.fonts.small,
            "SELECT DIFFICULTY",
            (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 72),
            color=MUTED_COLOR,
        )

        for index, button in enumerate(self.menu_buttons):
            button.draw(self.screen, self.fonts, selected=index == self.selected_indices["menu"])

        draw_arcade_text(
            self.screen,
            self.fonts.small,
            "Arrow Keys / Enter or Click | Move: WASD / Arrows | Shoot: Space / Hold Mouse / Touch",
            (WINDOW_WIDTH // 2, WINDOW_HEIGHT - 26),
            color=MUTED_COLOR,
        )

    def _draw_pause_overlay(self) -> None:
        shade = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 158))
        self.screen.blit(shade, (0, 0))
        panel = pygame.Rect(WINDOW_WIDTH // 2 - 180, WINDOW_HEIGHT // 2 - 108, 360, 244)
        draw_panel(self.screen, panel, fill=PANEL_COLOR, glow_alpha=95)
        draw_arcade_text(
            self.screen,
            self.fonts.title,
            "PAUSED",
            (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 76),
            color=TEXT_COLOR,
            glow_color=ACCENT_COLOR,
        )
        for index, button in enumerate(self.pause_buttons):
            button.draw(self.screen, self.fonts, selected=index == self.selected_indices["paused"])

    def _draw_game_over_overlay(self) -> None:
        shade = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        shade.fill((12, 0, 4, 186))
        self.screen.blit(shade, (0, 0))
        banner = self.assets.image("game_over", (420, 148)) if self.assets.has("game_over") else None
        if banner is not None:
            banner_rect = banner.get_rect(center=(WINDOW_WIDTH // 2, 116))
            self.screen.blit(banner, banner_rect)
        else:
            draw_arcade_text(
                self.screen,
                self.fonts.title,
                "GAME OVER",
                (WINDOW_WIDTH // 2, 108),
                color=(255, 130, 130),
                glow_color=(255, 88, 88),
            )

        if self.session is not None:
            draw_arcade_text(
                self.screen,
                self.fonts.subtitle,
                f"SCORE {self.session.score}    COINS {self.session.coins}",
                (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 8),
                color=TEXT_COLOR,
            )

        for index, button in enumerate(self.game_over_buttons):
            button.draw(self.screen, self.fonts, selected=index == self.selected_indices["game_over"])

    def _build_buttons(
        self,
        entries: tuple[tuple[str, str], ...],
        *,
        center_y: int,
        size: tuple[int, int],
    ) -> list[Button]:
        buttons: list[Button] = []
        first_y = center_y - ((len(entries) - 1) * BUTTON_SPACING) // 2
        for index, (label, action) in enumerate(entries):
            buttons.append(
                Button(
                    label=label,
                    action=action,
                    center=(WINDOW_WIDTH // 2, first_y + index * BUTTON_SPACING),
                    size=size,
                )
            )
        return buttons

    def _controls(self) -> ControlState:
        pressed = pygame.key.get_pressed()
        move_vector = pygame.Vector2(
            float(pressed[pygame.K_d] or pressed[pygame.K_RIGHT])
            - float(pressed[pygame.K_a] or pressed[pygame.K_LEFT]),
            float(pressed[pygame.K_s] or pressed[pygame.K_DOWN])
            - float(pressed[pygame.K_w] or pressed[pygame.K_UP]),
        )

        mouse_shooting = pygame.mouse.get_pressed()[0]
        shooting = bool(pressed[pygame.K_SPACE] or mouse_shooting or self.pointer.touch_active)
        pointer_target = None
        if mouse_shooting or self.pointer.touch_active:
            pointer_target = pygame.Vector2(*self.pointer.position)

        return ControlState(move_vector=move_vector, shooting=shooting, pointer_target=pointer_target)

    def _handle_menu_key(self, key: int) -> bool:
        if key == pygame.K_ESCAPE:
            return False
        if key in (pygame.K_UP, pygame.K_w):
            self.selected_indices["menu"] = (self.selected_indices["menu"] - 1) % len(self.menu_buttons)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.selected_indices["menu"] = (self.selected_indices["menu"] + 1) % len(self.menu_buttons)
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            self._activate_button(self.menu_buttons[self.selected_indices["menu"]].action)
        return True

    def _handle_pause_key(self, key: int) -> bool:
        if key == pygame.K_ESCAPE:
            self.scene = "playing"
            self.transition_alpha = 120.0
            return True
        if key in (pygame.K_UP, pygame.K_w):
            self.selected_indices["paused"] = (self.selected_indices["paused"] - 1) % len(self.pause_buttons)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.selected_indices["paused"] = (self.selected_indices["paused"] + 1) % len(self.pause_buttons)
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            self._activate_button(self.pause_buttons[self.selected_indices["paused"]].action)
        return True

    def _handle_game_over_key(self, key: int) -> bool:
        if key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a):
            self.selected_indices["game_over"] = (self.selected_indices["game_over"] - 1) % len(self.game_over_buttons)
        elif key in (pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT, pygame.K_d):
            self.selected_indices["game_over"] = (self.selected_indices["game_over"] + 1) % len(self.game_over_buttons)
        elif key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
            self._activate_button(self.game_over_buttons[self.selected_indices["game_over"]].action)
        elif key == pygame.K_m:
            self._activate_button("menu")
        return True

    def _update_buttons(self, dt: float) -> None:
        active_buttons = self._active_buttons()
        if active_buttons is None:
            return

        hovered_index = None
        for index, button in enumerate(active_buttons):
            if button.contains(self.pointer.position):
                hovered_index = index
                break

        if hovered_index is not None:
            self.selected_indices[self.scene] = hovered_index

        for index, button in enumerate(active_buttons):
            button.update(
                dt,
                hovered=index == hovered_index,
                pressed=self.pointer.is_down,
                selected=index == self.selected_indices[self.scene],
            )

    def _active_buttons(self) -> list[Button] | None:
        if self.scene == "menu":
            return self.menu_buttons
        if self.scene == "paused":
            return self.pause_buttons
        if self.scene == "game_over":
            return self.game_over_buttons
        return None

    def _activate_hovered_button(self) -> None:
        active_buttons = self._active_buttons()
        if active_buttons is None:
            return

        for index, button in enumerate(active_buttons):
            if button.contains(self.pointer.position):
                self.selected_indices[self.scene] = index
                self._activate_button(button.action)
                break

    def _activate_button(self, action: str) -> None:
        if action in DIFFICULTIES:
            self._start_session(action)
            return

        if action == "exit":
            raise SystemExit

        if action == "resume":
            self.scene = "playing"
            self.transition_alpha = 120.0
            return

        if action == "restart" and self.session is not None:
            self._start_session(self.session.difficulty.key)
            return

        if action == "menu":
            self.scene = "menu"
            self.transition_alpha = 180.0
            self.assets.sounds.play("select")

    def _start_session(self, action: str) -> None:
        difficulty = DIFFICULTIES[action]
        self.session = GameSession(difficulty=difficulty, assets=self.assets)
        self.scene = "playing"
        self.transition_alpha = 255.0
        self.assets.sounds.play("select")

    def _finger_position(self, event: pygame.event.Event) -> tuple[float, float]:
        return (event.x * WINDOW_WIDTH, event.y * WINDOW_HEIGHT)


def run(max_frames: int | None = None) -> None:
    """Run the main game loop."""

    pygame.init()
    try:
        try:
            pygame.mixer.init()
        except pygame.error:
            pass

        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE)
        clock = pygame.time.Clock()
        app = ArcadeShooterApp(screen)

        frame_count = 0
        running = True
        while running:
            try:
                for event in pygame.event.get():
                    running = app.handle_event(event)
                    if not running:
                        break

                if not running:
                    break

                dt = clock.tick(FPS) / 1000.0
                running = app.update(dt)
                screen.fill(BLACK)
                app.draw()
                pygame.display.flip()
                frame_count += 1
                if max_frames is not None and frame_count >= max_frames:
                    break
            except SystemExit:
                break
    finally:
        pygame.quit()


if __name__ == "__main__":
    run()
