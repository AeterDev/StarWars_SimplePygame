"""Core gameplay state and update loop."""

from __future__ import annotations

from dataclasses import dataclass, field
import random

import pygame

from .assets import AssetLibrary
from .entities import Enemy, Explosion, Player, Projectile
from .settings import COIN_INTERVAL_SECONDS, DifficultyConfig, WINDOW_HEIGHT, WINDOW_WIDTH
from .ui import UIFonts, draw_hud


@dataclass(slots=True)
class ControlState:
    """Per-frame control input."""

    move_vector: pygame.Vector2
    shooting: bool
    pointer_target: pygame.Vector2 | None = None


@dataclass(slots=True)
class GameSession:
    """Live gameplay session for one difficulty."""

    difficulty: DifficultyConfig
    assets: AssetLibrary
    arena: pygame.Rect = field(default_factory=lambda: pygame.Rect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT))
    player: Player = field(init=False)
    projectiles: list[Projectile] = field(default_factory=list)
    enemies: list[Enemy] = field(default_factory=list)
    explosions: list[Explosion] = field(default_factory=list)
    elapsed: float = 0.0
    coins: int = 0
    score: int = 0
    coin_timer: float = 0.0
    enemy_spawn_timer: float = field(init=False)
    asteroid_spawn_timer: float = field(init=False)
    next_boss_at: float = field(init=False)
    coin_pulse: float = 0.0
    screen_shake: float = 0.0
    game_over: bool = False

    def __post_init__(self) -> None:
        self.player = Player(pygame.Vector2(self.arena.centerx, self.arena.bottom - 80))
        self.enemy_spawn_timer = self.difficulty.spawn_interval
        self.asteroid_spawn_timer = self.difficulty.asteroid_interval
        self.next_boss_at = self.difficulty.boss_unlock_time

    def update(self, dt: float, controls: ControlState) -> None:
        self.elapsed += dt
        self.coin_pulse = max(0.0, self.coin_pulse - dt * 2.8)
        self.screen_shake = max(0.0, self.screen_shake - dt * 18.0)

        if self.game_over:
            self._update_effects(dt)
            return

        self.coin_timer += dt
        while self.coin_timer >= COIN_INTERVAL_SECONDS:
            self.coin_timer -= COIN_INTERVAL_SECONDS
            self.coins += 1
            self.coin_pulse = 1.0

        self.player.update(dt, controls.move_vector, controls.pointer_target, self.arena)

        if controls.shooting and self.player.can_shoot():
            self.projectiles.append(self.player.shoot())
            self.assets.sounds.play("fire")

        self._spawn_enemies(dt)
        self._update_enemies(dt)
        self._update_projectiles(dt)
        self._resolve_collisions()
        self._cleanup_entities()
        self._update_effects(dt)

        if self.player.is_destroyed():
            self.game_over = True
            self.assets.sounds.play("game_over")

    def draw(self, surface: pygame.Surface, fonts: UIFonts) -> None:
        offset = self._screen_offset()

        for enemy in self.enemies:
            enemy.draw(surface, self.assets, offset)
        for projectile in self.projectiles:
            projectile.draw(surface, self.assets, offset)
        for explosion in self.explosions:
            explosion.draw(surface, self.assets, offset)
        self.player.draw(surface, self.assets, offset)

        draw_hud(
            surface,
            self.assets,
            fonts,
            health_halves=self.player.health_halves,
            max_health_halves=self.player.max_health_halves,
            coins=self.coins,
            coin_pulse=self.coin_pulse,
            score=self.score,
            difficulty_label=self.difficulty.label,
            boss_health_ratio=self.boss_health_ratio(),
        )

    def boss_health_ratio(self) -> float | None:
        for enemy in self.enemies:
            if enemy.kind == "boss":
                return max(0.0, enemy.hp / 12)
        return None

    def _screen_offset(self) -> pygame.Vector2:
        if self.screen_shake <= 0.0:
            return pygame.Vector2()
        strength = self.screen_shake * 0.8
        return pygame.Vector2(random.uniform(-strength, strength), random.uniform(-strength, strength))

    def _spawn_enemies(self, dt: float) -> None:
        scale_factor = 1.0 + min(0.55, self.elapsed / 75.0)
        self.enemy_spawn_timer -= dt
        if self.enemy_spawn_timer <= 0.0:
            x_position = random.uniform(70, self.arena.width - 70)
            self.enemies.append(
                Enemy.fighter(
                    x_position=x_position,
                    base_speed=self.difficulty.enemy_speed * scale_factor,
                    fire_interval=max(0.72, self.difficulty.enemy_fire_interval / scale_factor),
                    aggression=min(1.0, self.difficulty.aggression + (self.elapsed / 140.0)),
                )
            )
            self.enemy_spawn_timer = max(0.42, self.difficulty.spawn_interval / scale_factor)

        if self.assets.has("asteroid"):
            self.asteroid_spawn_timer -= dt
            if self.asteroid_spawn_timer <= 0.0:
                x_position = random.uniform(70, self.arena.width - 70)
                self.enemies.append(
                    Enemy.asteroid(
                        x_position=x_position,
                        base_speed=self.difficulty.asteroid_speed * scale_factor,
                    )
                )
                self.asteroid_spawn_timer = max(0.8, self.difficulty.asteroid_interval / scale_factor)

        boss_present = any(enemy.kind == "boss" for enemy in self.enemies)
        if self.assets.has("boss") and not boss_present and self.elapsed >= self.next_boss_at:
            self.enemies.append(
                Enemy.boss(
                    arena=self.arena,
                    fire_interval=self.difficulty.enemy_fire_interval,
                    aggression=self.difficulty.aggression,
                )
            )
            self.next_boss_at += self.difficulty.boss_cadence

    def _update_enemies(self, dt: float) -> None:
        spawned_projectiles: list[Projectile] = []
        for enemy in self.enemies:
            spawned_projectiles.extend(
                enemy.update(
                    dt,
                    player_position=self.player.position,
                    arena=self.arena,
                    bullet_speed=310.0 + (self.elapsed * 1.6),
                )
            )
        self.projectiles.extend(spawned_projectiles)

    def _update_projectiles(self, dt: float) -> None:
        for projectile in self.projectiles:
            projectile.update(dt)
            if not self.arena.inflate(180, 180).collidepoint(projectile.position):
                projectile.active = False

    def _resolve_collisions(self) -> None:
        for projectile in self.projectiles:
            if not projectile.active:
                continue

            if projectile.owner == "player":
                for enemy in self.enemies:
                    if enemy.hp <= 0:
                        continue
                    if projectile.collides_with(enemy.position, enemy.radius):
                        projectile.active = False
                        if enemy.take_hit():
                            self._destroy_enemy(enemy)
                        break
            else:
                if projectile.collides_with(self.player.position, self.player.radius):
                    projectile.active = False
                    if self.player.take_damage():
                        self.coin_pulse = 0.0
                        self.screen_shake = 9.0

        for enemy in self.enemies:
            if enemy.hp <= 0:
                continue
            limit = enemy.radius + self.player.radius
            if enemy.position.distance_squared_to(self.player.position) <= limit * limit:
                if self.player.take_damage():
                    self.screen_shake = 11.0
                enemy.hp = 0
                self.explosions.append(Explosion(enemy.position.copy()))

    def _destroy_enemy(self, enemy: Enemy) -> None:
        enemy.hp = 0
        self.score += enemy.reward
        self.explosions.append(Explosion(enemy.position.copy()))
        self.screen_shake = max(self.screen_shake, 4.5 if enemy.kind != "boss" else 9.5)

    def _cleanup_entities(self) -> None:
        self.projectiles = [projectile for projectile in self.projectiles if projectile.active]
        self.enemies = [
            enemy
            for enemy in self.enemies
            if enemy.hp > 0 and not enemy.off_screen(self.arena)
        ]

    def _update_effects(self, dt: float) -> None:
        self.explosions = [explosion for explosion in self.explosions if explosion.update(dt)]
