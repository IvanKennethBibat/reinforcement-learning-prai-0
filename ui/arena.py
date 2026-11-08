"""The hilltop where fights happen, under a tall summer sky.

The sky and the land are painted once. ``Arena`` slides clouds between the two
and drifts petals over everything each frame.
"""
from functools import cache
import math
import random

import pygame

from ui.palette import (
    GRASS, HILLS, LEAVES, PETALS, SKY, WHITE,
)

WIDTH, HEIGHT = 320, 180
HORIZON = 84          # where the far hills meet the meadow
FLOOR_BOTTOM = 138    # the command panel covers everything below this

BAYER = [
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
]


def dither_pick(ramp, value, x, y):
    """Pick from a dark-to-light ramp, dithering between neighbouring colours."""
    scaled = max(0.0, min(0.999, value)) * (len(ramp) - 1)
    low = int(scaled)
    threshold = (BAYER[y % 4][x % 4] + 0.5) / 16
    return ramp[min(len(ramp) - 1, low + (scaled - low > threshold))]


def _paint_sky(surf):
    for y in range(HORIZON + 6):
        for x in range(WIDTH):
            surf.set_at((x, y), dither_pick(SKY[1:], y / (HORIZON + 6) * 0.95, x, y))


def _cloud(rng, width, height):
    """A towering cumulus: sunlit puffs on top of a soft blue-shaded base."""
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    puffs = []
    for _ in range(width // 5):
        k = rng.random()
        radius = int((0.35 + 0.65 * math.sin(k * math.pi)) * height * rng.uniform(0.22, 0.38))
        x = int(width * (0.1 + 0.8 * k))
        y = int(height - radius - rng.uniform(0, height * 0.5) * math.sin(k * math.pi))
        puffs.append((x, y, max(3, radius)))
    for x, y, radius in sorted(puffs, key=lambda puff: puff[1]):
        pygame.draw.circle(surf, SKY[3], (x, y), radius)
        pygame.draw.circle(surf, WHITE, (x - radius // 4, y - radius // 4), int(radius * 0.8))
    for y in range(height):
        for x in range(width):
            pixel = surf.get_at((x, y))
            if pixel.a and (BAYER[y % 4][x % 4] + 0.5) / 16 < (y / height - 0.55) * 2.2:
                surf.set_at((x, y), (*SKY[3], 255))
    return surf


def _paint_mountains(surf):
    rng = random.Random(21)
    ridge = [(0, HORIZON + 6)]
    for x in range(0, WIDTH + 12, 12):
        height = 58 + 12 * math.sin(x / 47) + 7 * math.sin(x / 19 + 1) + rng.randint(-2, 2)
        ridge.append((x, height))
    ridge.append((WIDTH, HORIZON + 6))
    pygame.draw.polygon(surf, HILLS[0], ridge)


def _hill_height(x, base, size, phase):
    return base + size * math.sin(x / 61 + phase) + size * 0.4 * math.sin(x / 23 + phase * 2)


def _paint_hills(surf):
    rng = random.Random(8)
    for color, base, size, phase in ((HILLS[1], 72, 5, 0.4), (HILLS[2], 79, 4, 2.1)):
        for x in range(WIDTH):
            top = int(_hill_height(x, base, size, phase))
            pygame.draw.line(surf, color, (x, top), (x, HORIZON + 8))
        # Round clumps of trees sitting along the ridge.
        for _ in range(14):
            x = rng.randrange(WIDTH)
            y = int(_hill_height(x, base, size, phase))
            radius = rng.randint(3, 6)
            pygame.draw.circle(surf, LEAVES[0], (x, y), radius)
            pygame.draw.circle(surf, LEAVES[1], (x - 1, y - 1), radius - 1)
            pygame.draw.circle(surf, LEAVES[2], (x - 2, y - 2), max(1, radius - 3))


def _paint_meadow(surf):
    rng = random.Random(5)
    for y in range(HORIZON, HEIGHT):
        depth = (y - HORIZON) / (HEIGHT - HORIZON)
        for x in range(WIDTH):
            # A wide pool of sunlight falling across the middle of the meadow.
            sun = max(0.0, 1 - abs(x - 170 + y * 0.4) / 190) * 0.4
            roll = 0.05 * math.sin(x / 37 + y / 11)
            surf.set_at((x, y), dither_pick(GRASS, 0.2 + sun + roll + depth * 0.1, x, y))

    # Blades of grass and wildflowers, larger towards the viewer.
    for _ in range(420):
        x, y = rng.randrange(WIDTH), rng.randrange(HORIZON + 2, HEIGHT)
        height = 1 + int((y - HORIZON) / 26)
        pygame.draw.line(surf, rng.choice((GRASS[0], GRASS[3])), (x, y), (x + rng.randint(-1, 1), y - height))
    for _ in range(130):
        x, y = rng.randrange(WIDTH), rng.randrange(HORIZON + 3, HEIGHT)
        color = rng.choice(PETALS)
        surf.set_at((x, y), color)
        if y > HORIZON + 26:
            surf.set_at((x + 1, y), color)
            surf.set_at((x, y - 1), color)


@cache
def build_sky():
    surf = pygame.Surface((WIDTH, HEIGHT))
    _paint_sky(surf)
    return surf


@cache
def build_land():
    surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    _paint_mountains(surf)
    _paint_hills(surf)
    _paint_meadow(surf)
    return surf


@cache
def build_clouds():
    rng = random.Random(14)
    return _cloud(rng, 150, 62), _cloud(rng, 96, 34), _cloud(rng, 70, 24)


class Arena:
    def __init__(self):
        self.sky = build_sky()
        self.land = build_land()
        self.time = 0.0
        self.rng = random.Random(3)
        # (image, x, y, speed): the big near clouds drift a little faster.
        big, medium, small = build_clouds()
        self.clouds = [[big, 18.0, 2, 1.6], [medium, 196.0, 24, 1.0], [small, 120.0, 44, 0.6]]
        self.petals = [
            [self.rng.uniform(0, WIDTH), self.rng.uniform(30, FLOOR_BOTTOM), self.rng.uniform(6, 16), self.rng.choice(PETALS)]
            for _ in range(22)
        ]

    def update(self, dt):
        self.time += dt
        for cloud in self.clouds:
            cloud[1] += cloud[3] * dt
            if cloud[1] > WIDTH:
                cloud[1] = -cloud[0].get_width()
        for petal in self.petals:
            petal[0] += petal[2] * dt
            petal[1] += math.sin(self.time * 2 + petal[2]) * 6 * dt
            if petal[0] > WIDTH:
                petal[0], petal[1] = -4.0, self.rng.uniform(30, FLOOR_BOTTOM)

    def draw_back(self, surf):
        surf.blit(self.sky, (0, 0))
        for image, x, y, _ in self.clouds:
            surf.blit(image, (int(x), y))
        surf.blit(self.land, (0, 0))

    def draw_front(self, surf):
        for x, y, _, color in self.petals:
            surf.set_at((int(x) % WIDTH, int(y)), color)
