"""Short-lived visual effects: particles, slashes, wards and damage numbers."""
from dataclasses import dataclass
import math
import random
from typing import Callable

import pygame

from ui.font import draw_text
from ui.palette import EMBER, GOLD, INK, SPIRIT


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    color: tuple
    gravity: float = 0.0
    size: int = 1


@dataclass
class Floater:
    text: str
    x: float
    y: float
    color: tuple
    scale: int = 1
    age: float = 0.0


@dataclass
class Slash:
    x: float
    y: float
    facing: int
    age: float = 0.0


def _draw_spores(surf, pos, radius, colors, facing, time):
    """A soft cloud of round spores, each drifting on its own little orbit."""
    x, y = pos
    for i in range(9):
        angle = i * 2.4 + time * (2 + i % 3)
        reach = radius * (0.3 + (i % 4) * 0.32)
        spot = (x + math.cos(angle) * reach, y + math.sin(angle) * reach * 0.8)
        size = 1 + (i % 3)
        pygame.draw.circle(surf, INK, spot, size + 1)
        pygame.draw.circle(surf, colors[2 if i % 2 else 1], spot, size)


def _draw_water(surf, pos, radius, colors, facing, time):
    """A jet of teardrops, each pointing back along the way it came."""
    x, y = pos
    for i, scale in enumerate((1.0, 0.7, 0.5, 0.35)):
        size = max(1.5, radius * 0.72 * scale)
        cx = x - facing * i * radius * 1.5
        cy = y + math.sin(time * 30 + i) * i * 0.6
        tail = (cx - facing * size * 2.6, cy)
        top, bottom = (cx, cy - size), (cx, cy + size)
        pygame.draw.polygon(surf, INK, [(tail[0] - facing, tail[1]), (top[0], top[1] - 1), (bottom[0], bottom[1] + 1)])
        pygame.draw.circle(surf, INK, (cx, cy), size + 1)
        pygame.draw.polygon(surf, colors[1], [tail, top, bottom])
        pygame.draw.circle(surf, colors[1], (cx, cy), size)
        pygame.draw.circle(surf, colors[2], (cx + facing * size * 0.3, cy - size * 0.3), max(1, size * 0.4))


def _draw_lava(surf, pos, radius, colors, facing, time):
    """A rough molten lump: dark crust cracked open over a bright core."""
    x, y = pos
    points = []
    for i in range(9):
        angle = i * math.tau / 9 + time * 5
        reach = radius * (1.05 + 0.3 * math.sin(i * 2.7 + time * 9))
        points.append((x + math.cos(angle) * reach, y + math.sin(angle) * reach))
    pygame.draw.polygon(surf, INK, [(px + (px > x) - (px < x), py + (py > y) - (py < y)) for px, py in points])
    pygame.draw.polygon(surf, colors[0], points)
    pygame.draw.circle(surf, colors[1], (x, y), radius * 0.7)
    pygame.draw.circle(surf, colors[2], (x - 1, y - 1), radius * 0.4)
    for i in range(3):
        angle = i * 2.1 + time * 5
        tip = (x + math.cos(angle) * radius, y + math.sin(angle) * radius)
        pygame.draw.line(surf, colors[2], (x, y), tip)


def _draw_royal(surf, pos, radius, colors, facing, time):
    """A big wobbling blob of goo with gold sparkles circling it."""
    x, y = pos
    wobble = math.sin(time * 26) * radius * 0.25
    width, height = radius * 2.3 + wobble, radius * 2.3 - wobble
    for offset, size in ((radius + 5, radius * 0.5), (radius + 12, radius * 0.32), (radius + 18, radius * 0.2)):
        drop = (x - facing * offset, y + 1 + math.sin(time * 19 + offset) * 2)
        pygame.draw.circle(surf, INK, drop, size + 1)
        pygame.draw.circle(surf, colors[1], drop, size)
    body = pygame.Rect(0, 0, width, height)
    body.center = (x, y)
    pygame.draw.ellipse(surf, INK, body.inflate(2, 2))
    pygame.draw.ellipse(surf, colors[0], body)
    pygame.draw.ellipse(surf, colors[1], body.inflate(-2, -2))
    pygame.draw.ellipse(surf, colors[2], (body.x + 2, body.y + 2, width * 0.45, height * 0.35))
    for i in range(3):
        angle = i * math.tau / 3 + time * 7
        sx, sy = x + math.cos(angle) * (radius + 6), y + math.sin(angle) * (radius + 4)
        pygame.draw.line(surf, GOLD, (sx - 2, sy), (sx + 2, sy))
        pygame.draw.line(surf, GOLD, (sx, sy - 2), (sx, sy + 2))


@dataclass(frozen=True)
class Shot:
    """How a slime's ranged attack looks and flies."""
    draw: Callable
    flight: float       # seconds in the air
    arc: float = 0.0    # how high it lobs, in pixels
    sway: float = 0.0   # how far it wanders from side to side
    size: float = 1.0
    spray: int = 2      # particles shed each frame
    spray_gravity: float = 90
    splash: int = 40    # particles on impact
    splash_speed: float = 90


SHOTS = {
    "spores": Shot(_draw_spores, flight=0.55, sway=9, size=1.2, spray=1, spray_gravity=-12, splash=30, splash_speed=45),
    "water": Shot(_draw_water, flight=0.2, size=0.9, spray=3, spray_gravity=200, splash=48, splash_speed=120),
    "lava": Shot(_draw_lava, flight=0.42, arc=46, spray=3, spray_gravity=130, splash=36, splash_speed=100),
    "royal": Shot(_draw_royal, flight=0.36, size=1.2, spray=2, spray_gravity=40, splash=56, splash_speed=105),
}


class Effects:
    FLOATER_LIFE = 1.0
    SLASH_LIFE = 0.2

    def __init__(self):
        self.particles: list[Particle] = []
        self.floaters: list[Floater] = []
        self.slashes: list[Slash] = []
        self.bolt = None  # (position, radius, colours, facing, Shot) in flight
        self.shot_time = 0.0
        self.rng = random.Random()

    def burst(self, pos, colors, count=18, speed=60, gravity=90):
        for _ in range(count):
            angle = self.rng.uniform(0, math.tau)
            pace = self.rng.uniform(speed * 0.3, speed)
            self.particles.append(Particle(
                pos[0], pos[1], math.cos(angle) * pace, math.sin(angle) * pace,
                self.rng.uniform(0.2, 0.55), self.rng.choice(colors), gravity,
                self.rng.choice((1, 1, 2)),
            ))

    def rise(self, pos, colors, count=14, spread=14):
        for _ in range(count):
            self.particles.append(Particle(
                pos[0] + self.rng.uniform(-spread, spread), pos[1] + self.rng.uniform(-6, 18),
                self.rng.uniform(-3, 3), self.rng.uniform(-34, -14),
                self.rng.uniform(0.5, 1.0), self.rng.choice(colors),
            ))

    def trail(self, pos, colors):
        self.particles.append(Particle(
            pos[0] + self.rng.uniform(-1, 1), pos[1] + self.rng.uniform(-2, 2),
            self.rng.uniform(-8, 8), self.rng.uniform(-14, 2),
            self.rng.uniform(0.12, 0.3), self.rng.choice(colors),
        ))

    def slash(self, pos, facing):
        self.slashes.append(Slash(pos[0], pos[1], facing))

    def floater(self, text, pos, color, scale=1):
        self.floaters.append(Floater(text, pos[0], pos[1], color, scale))

    def update(self, dt):
        self.shot_time += dt
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += p.gravity * dt
            p.life -= dt
        self.particles = [p for p in self.particles if p.life > 0]
        for f in self.floaters:
            f.age += dt
        self.floaters = [f for f in self.floaters if f.age < self.FLOATER_LIFE]
        for s in self.slashes:
            s.age += dt
        self.slashes = [s for s in self.slashes if s.age < self.SLASH_LIFE]

    def draw(self, surf):
        for s in self.slashes:
            self._draw_slash(surf, s)
        for p in self.particles:
            pygame.draw.rect(surf, p.color, (int(p.x), int(p.y), p.size, p.size))
        if self.bolt:
            pos, radius, colors, facing, shot = self.bolt
            shot.draw(surf, pos, radius, colors, facing, self.shot_time)

    def draw_floaters(self, surf):
        for f in self.floaters:
            pop = min(1.0, f.age / 0.15)
            y = f.y - 8 * pop - f.age * 8
            draw_text(surf, f.text, (int(f.x), int(y)), f.color, f.scale, INK, center=True)

    def _draw_slash(self, surf, slash):
        """A crescent that sweeps downward and thins out as it fades."""
        k = slash.age / self.SLASH_LIFE
        thickness = max(1.0, 7 * (1 - k))
        outer, inner = [], []
        for i in range(11):
            angle = -1.2 + 2.4 * i / 10
            radius = 20 + 4 * k
            bulge = thickness * math.cos(angle * 1.3)
            outer.append((slash.x + slash.facing * math.cos(angle) * radius, slash.y + math.sin(angle) * radius))
            inner.append((slash.x + slash.facing * math.cos(angle) * (radius - bulge), slash.y + math.sin(angle) * (radius - bulge)))
        pygame.draw.polygon(surf, EMBER[3] if k < 0.5 else EMBER[1], outer + inner[::-1])


def draw_ward(surf, center, facing, time):
    """A shimmering arc of warding light in front of a defending fighter."""
    cx, cy = center
    for i in range(29):
        angle = -1.25 + 2.5 * i / 28
        wobble = math.sin(time * 9 + i * 0.7)
        x = cx + facing * math.cos(angle) * (24 + wobble)
        y = cy + math.sin(angle) * 34
        pygame.draw.rect(surf, SPIRIT[2] if wobble > 0.2 else SPIRIT[1], (int(x), int(y), 2, 2))
        if i % 2:
            inner = cx + facing * math.cos(angle) * (20 + wobble)
            surf.set_at((int(inner), int(y)), SPIRIT[0])
