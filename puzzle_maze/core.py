"""Deterministic, renderer-independent movement and tile collision."""
from dataclasses import dataclass, field
from puzzle_maze.weapons import BasicSword, Weapon

@dataclass
class Player:
    x: int
    y: int
    facing: tuple = (0, 1)
    moving: bool = False
    hp: int = 5
    max_hp: int = 5
    invulnerable: float = 0
    attack_cooldown: float = 0
    attack_flash: float = 0
    weapon: Weapon = field(default_factory=BasicSword)
    attack_facing: tuple = (0,1)

@dataclass
class TileMap:
    rows: list[str]

    def walkable(self, x, y):
        return 0 <= y < len(self.rows) and 0 <= x < len(self.rows[0]) and self.rows[y][x] not in '#~Ov'

class CollisionManager:
    def __init__(self, tilemap):
        self.tilemap = tilemap

    def can_enter(self, x, y):
        return self.tilemap.walkable(x, y)

    def move(self, player, dx, dy):
        player.facing = (dx, dy)
        player.moving = self.can_enter(player.x + dx, player.y + dy)
        if player.moving:
            player.x += dx
            player.y += dy
        return player.moving

@dataclass
class Camera:
    x: float = 0
    y: float = 0

    def follow(self, player, width, height, viewport=(320, 208), tile=16):
        self.x = max(0, min(player.x * tile - viewport[0] / 2, width * tile - viewport[0]))
        self.y = max(0, min(player.y * tile - viewport[1] / 2, height * tile - viewport[1]))
