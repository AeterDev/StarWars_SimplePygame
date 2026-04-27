"""Gameplay entity models."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random

import pygame

from .assets import AssetLibrary
from .settings import MAX_HEALTH_HALVES, PLAYER_FIRE_COOLDOWN, PLAYER_INVULNERABILITY, PLAYER_SPEED


@dataclass(slots=True)
class Projectile:
    """A moving projectile fired by the player or an enemy."""

    position: pygame.Vector2
    velocity: pygame.Vector2
    owner: str
    sprite_role: str
    radius: float
    size: tuple[int, int]
    ttl: float = 4.0
    active: bool = True

    def update(self, dt: float) -> None:
        self.position += self.velocity * dt
        self.ttl -= dt
        if self.ttl <= 0.0:
            self.active = False

    def collides_with(self, other_position: pygame.Vector2, other_radius: float) -> bool:
        limit = self.radius + other_radius
        return self.position.distance_squared_to(other_position) <= limit * limit

    def draw(self, surface: pygame.Surface, assets: AssetLibrary, offset: pygame.Vector2) -> None:
        center = self.position + offset
        glow_color = (117, 243, 255) if self.owner == "player" else (255, 130, 108)
        glow_rect = pygame.Rect(0, 0, self.size[0] + 12, self.size[1] + 12)
        glow_rect.center = (round(center.x), round(center.y))
        pygame.draw.ellipse(surface, (*glow_color, 64), glow_rect)

        angle = 90 if abs(self.velocity.y) >= abs(self.velocity.x) else 0
        sprite = assets.image(self.sprite_role, self.size, rotation=angle)
        rect = sprite.get_rect(center=(round(center.x), round(center.y)))
        surface.blit(sprite, rect)


@dataclass(slots=True)
class Explosion:
    """Short-lived explosion effect."""

    position: pygame.Vector2
    duration: float = 0.45
    age: float = 0.0

    def update(self, dt: float) -> bool:
        self.age += dt
        return self.age < self.duration

    def draw(self, surface: pygame.Surface, assets: AssetLibrary, offset: pygame.Vector2) -> None:
        progress = min(1.0, self.age / self.duration)
        size = round(42 + 78 * progress)
        sprite = assets.image("explosion", (size, size))
        if progress > 0:
            sprite = sprite.copy()
            sprite.set_alpha(max(0, round(255 * (1.0 - progress))))
        rect = sprite.get_rect(center=(round(self.position.x + offset.x), round(self.position.y + offset.y)))
        surface.blit(sprite, rect)


@dataclass(slots=True)
class Player:
    """The player's spaceship."""

    position: pygame.Vector2
    speed: float = PLAYER_SPEED
    max_health_halves: int = MAX_HEALTH_HALVES
    health_halves: int = MAX_HEALTH_HALVES
    fire_cooldown: float = 0.0
    invulnerability_timer: float = 0.0
    shoot_flash: float = 0.0
    radius: float = 27.0

    def update(
        self,
        dt: float,
        move_vector: pygame.Vector2,
        pointer_target: pygame.Vector2 | None,
        arena: pygame.Rect,
    ) -> None:
        velocity = pygame.Vector2()
        if move_vector.length_squared() > 0:
            velocity = move_vector.normalize() * self.speed

        if pointer_target is not None and move_vector.length_squared() == 0:
            delta = pointer_target - self.position
            if delta.length_squared() > 36:
                velocity = delta.normalize() * min(self.speed, max(120.0, delta.length() * 5.5))

        self.position += velocity * dt
        self.position.x = max(arena.left + 42, min(arena.right - 42, self.position.x))
        self.position.y = max(arena.top + 52, min(arena.bottom - 42, self.position.y))

        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)
        self.invulnerability_timer = max(0.0, self.invulnerability_timer - dt)
        self.shoot_flash = max(0.0, self.shoot_flash - dt * 3.5)

    def can_shoot(self) -> bool:
        return self.fire_cooldown <= 0.0

    def shoot(self) -> Projectile:
        self.fire_cooldown = PLAYER_FIRE_COOLDOWN
        self.shoot_flash = 1.0
        return Projectile(
            position=self.position + pygame.Vector2(0, -42),
            velocity=pygame.Vector2(0, -640),
            owner="player",
            sprite_role="player_bullet",
            radius=11.0,
            size=(18, 44),
        )

    def take_damage(self) -> bool:
        if self.invulnerability_timer > 0:
            return False

        self.health_halves = max(0, self.health_halves - 1)
        self.invulnerability_timer = PLAYER_INVULNERABILITY
        return True

    def is_destroyed(self) -> bool:
        return self.health_halves <= 0

    def draw(self, surface: pygame.Surface, assets: AssetLibrary, offset: pygame.Vector2) -> None:
        flash_scale = 1.0 + (0.06 * self.shoot_flash)
        sprite = assets.image("player", (round(94 * flash_scale), round(94 * flash_scale)))
        if self.invulnerability_timer > 0 and int(self.invulnerability_timer * 14) % 2 == 0:
            sprite = sprite.copy()
            sprite.set_alpha(150)

        rect = sprite.get_rect(center=(round(self.position.x + offset.x), round(self.position.y + offset.y)))
        surface.blit(sprite, rect)


@dataclass(slots=True)
class Enemy:
    """Enemy ship, asteroid, or boss."""

    kind: str
    position: pygame.Vector2
    velocity: pygame.Vector2
    sprite_role: str
    size: tuple[int, int]
    radius: float
    hp: int
    reward: int
    fire_interval: float
    fire_timer: float
    aggression: float
    phase: float
    age: float = 0.0

    @classmethod
    def fighter(cls, x_position: float, base_speed: float, fire_interval: float, aggression: float) -> "Enemy":
        return cls(
            kind="fighter",
            position=pygame.Vector2(x_position, -70),
            velocity=pygame.Vector2(random.uniform(-35, 35), base_speed),
            sprite_role="enemy",
            size=(88, 88),
            radius=28.0,
            hp=1,
            reward=12,
            fire_interval=fire_interval,
            fire_timer=random.uniform(fire_interval * 0.45, fire_interval * 1.2),
            aggression=aggression,
            phase=random.uniform(0, math.tau),
        )

    @classmethod
    def asteroid(cls, x_position: float, base_speed: float) -> "Enemy":
        return cls(
            kind="asteroid",
            position=pygame.Vector2(x_position, -82),
            velocity=pygame.Vector2(random.uniform(-65, 65), base_speed),
            sprite_role="asteroid",
            size=(86, 86),
            radius=30.0,
            hp=1,
            reward=6,
            fire_interval=0.0,
            fire_timer=0.0,
            aggression=0.0,
            phase=random.uniform(0, math.tau),
        )

    @classmethod
    def boss(cls, arena: pygame.Rect, fire_interval: float, aggression: float) -> "Enemy":
        return cls(
            kind="boss",
            position=pygame.Vector2(arena.centerx, -120),
            velocity=pygame.Vector2(0, 125),
            sprite_role="boss",
            size=(176, 142),
            radius=56.0,
            hp=12,
            reward=160,
            fire_interval=max(0.75, fire_interval * 0.8),
            fire_timer=1.0,
            aggression=aggression,
            phase=random.uniform(0, math.tau),
        )

    def update(
        self,
        dt: float,
        player_position: pygame.Vector2,
        arena: pygame.Rect,
        bullet_speed: float,
    ) -> list[Projectile]:
        bullets: list[Projectile] = []
        self.age += dt

        if self.kind == "fighter":
            tracking = max(-1.0, min(1.0, (player_position.x - self.position.x) / arena.width))
            self.velocity.x = (tracking * 210 * self.aggression) + math.sin(self.age * 2.5 + self.phase) * 40
            self.position += self.velocity * dt
            self.fire_timer -= dt
            if self.position.y > 40 and self.fire_timer <= 0:
                aim = player_position - self.position
                if aim.length_squared() == 0:
                    aim = pygame.Vector2(0, 1)
                bullet_velocity = aim.normalize() * bullet_speed
                bullet_velocity.y = max(bullet_velocity.y, bullet_speed * 0.74)
                bullets.append(self._bullet(bullet_velocity))
                self.fire_timer = random.uniform(self.fire_interval * 0.9, self.fire_interval * 1.25)

        elif self.kind == "asteroid":
            sway = math.sin(self.age * 1.7 + self.phase) * 22
            self.position += pygame.Vector2(self.velocity.x + sway, self.velocity.y) * dt

        elif self.kind == "boss":
            if self.position.y < 120:
                self.position.y += self.velocity.y * dt
            else:
                self.position.x += math.sin(self.age * 1.4 + self.phase) * 92 * dt
                self.position.x = max(arena.left + 110, min(arena.right - 110, self.position.x))

            self.fire_timer -= dt
            if self.fire_timer <= 0:
                for spread in (-0.35, 0.0, 0.35):
                    bullet_velocity = pygame.Vector2(spread * bullet_speed, bullet_speed)
                    bullets.append(self._bullet(bullet_velocity))
                self.fire_timer = self.fire_interval

        return bullets

    def take_hit(self, damage: int = 1) -> bool:
        self.hp -= damage
        return self.hp <= 0

    def off_screen(self, arena: pygame.Rect) -> bool:
        margin = 120
        return (
            self.position.y > arena.bottom + margin
            or self.position.x < arena.left - margin
            or self.position.x > arena.right + margin
        )

    def draw(self, surface: pygame.Surface, assets: AssetLibrary, offset: pygame.Vector2) -> None:
        sprite = assets.image(self.sprite_role, self.size)
        if self.kind == "asteroid":
            rotation = round(math.sin(self.age * 2.8 + self.phase) * 16)
            sprite = assets.image(self.sprite_role, self.size, rotation=rotation)
        rect = sprite.get_rect(center=(round(self.position.x + offset.x), round(self.position.y + offset.y)))
        surface.blit(sprite, rect)

    def _bullet(self, velocity: pygame.Vector2) -> Projectile:
        return Projectile(
            position=self.position + pygame.Vector2(0, self.size[1] * 0.26),
            velocity=velocity,
            owner="enemy",
            sprite_role="enemy_bullet",
            radius=10.0,
            size=(18, 38),
        )
