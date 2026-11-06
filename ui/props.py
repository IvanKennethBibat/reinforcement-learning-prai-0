"""Large scenery that stands on the map: pines, flowering bushes and mossy rocks.

Props aren't tied to the tile grid. Each has a ground position, and the overworld
draws them in depth order with the characters, so you can walk behind them.
"""
from functools import cache
import random

import pygame

from ui.palette import (
    BERRY, BRICK, DEEP_PINE, EMBER, GOLD, GRASS, LEAVES, MOSS_INK, PETALS, PINE, PLASTER,
    ROCK, STEEL, STONE, TRUNK, WOOD,
)


def _outline(surf, color):
    silhouette = pygame.mask.from_surface(surf).to_surface(setcolor=(*color, 255), unsetcolor=(0, 0, 0, 0))
    framed = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for offset in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        framed.blit(silhouette, offset)
    framed.blit(surf, (0, 0))
    return framed


def make_pine(rng, ramp, width, height):
    """Stacked boughs that droop into jagged tips, lit from the upper left."""
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    cx = width // 2
    trunk_top = height - 9
    pygame.draw.rect(surf, TRUNK[0], (cx - 2, trunk_top, 5, 8))
    pygame.draw.rect(surf, TRUNK[1], (cx - 2, trunk_top, 2, 8))

    tiers = max(4, height // 10)
    for tier in range(tiers):
        k = tier / (tiers - 1)                       # 0 at the bottom, 1 at the top
        bottom = int(trunk_top + 1 - k * (height - 20))
        top = bottom - int(15 - k * 4)
        half = (width / 2 - 2) * (1 - k * 0.82)
        for y in range(max(0, top), bottom):
            t = (y - top) / max(1, bottom - top)
            reach = half * t ** 0.85 + 1
            left, right = int(cx - reach - rng.randint(0, 1)), int(cx + reach + rng.randint(0, 1))
            for x in range(left, right + 1):
                if 0 <= x < width:
                    side = (x - cx) / max(1.0, reach)
                    color = ramp[0] if side > 0.3 else ramp[1] if side > -0.35 else ramp[2]
                    surf.set_at((x, y), color)
        # Drooping tips along the lower edge of the bough.
        for x in range(int(cx - half), int(cx + half) + 1, 3):
            drop = rng.randint(1, 3)
            side = (x - cx) / max(1.0, half)
            color = ramp[0] if side > 0.2 else ramp[1]
            if 0 <= x < width:
                pygame.draw.line(surf, color, (x, bottom - 1), (x, min(height - 1, bottom + drop)))
        # Clusters of light on the sunny side.
        for _ in range(int(half) + 2):
            x = int(cx - rng.uniform(0.15, 1.0) * half)
            y = bottom - rng.randint(1, 4)
            if 0 <= x < width - 1 and 0 <= y < height and surf.get_at((x, y)).a:
                pygame.draw.line(surf, ramp[3], (x, y), (x + rng.randint(0, 2), y))
    return _outline(surf, MOSS_INK)


def make_bush(rng, width=30, height=20):
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    blobs = []
    for _ in range(9):
        x = rng.randint(6, width - 7)
        arch = 1 - abs(x - width / 2) / (width / 2)
        blobs.append((x, int(height - 5 - rng.uniform(0, 9) * arch), rng.randint(4, 6)))
    for x, y, r in sorted(blobs, key=lambda blob: blob[1]):
        pygame.draw.circle(surf, PINE[0], (x, y), r)
        pygame.draw.circle(surf, PINE[1], (x - 1, y - 1), r - 1)
        pygame.draw.circle(surf, PINE[2], (x - 2, y - 2), max(1, r - 3))
    for _ in range(26):
        x, y = rng.randrange(2, width - 2), rng.randrange(1, height - 3)
        if surf.get_at((x, y)).a:
            color = rng.choice(BERRY)
            surf.set_at((x, y), color)
            if rng.random() < 0.5:
                surf.set_at((x + 1, y), color)
    return _outline(surf, MOSS_INK)


def make_rock(rng, width=24, height=20):
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    points = [(2, height - 3), (3, 9), (8, 3), (15, 2), (width - 4, 7), (width - 2, height - 3)]
    pygame.draw.polygon(surf, ROCK[0], points)
    pygame.draw.polygon(surf, ROCK[1], [(3, 10), (8, 4), (15, 3), (17, 9), (12, height - 5), (5, height - 4)])
    pygame.draw.polygon(surf, ROCK[2], [(5, 9), (9, 5), (14, 4), (13, 8), (8, 11)])
    pygame.draw.line(surf, ROCK[0], (12, 8), (9, height - 5))
    for _ in range(16):  # moss creeping over the top
        x, y = rng.randrange(3, width - 3), rng.randrange(2, 12)
        if surf.get_at((x, y)).a:
            pygame.draw.line(surf, rng.choice(GRASS[1:]), (x, y), (x + rng.randint(0, 2), y))
    return _outline(surf, MOSS_INK)


EAVE = 5          # how far the roof overhangs each wall
WALL_HEIGHT = 30
COTTAGE_RISE = 14  # how far a cottage stands above its footprint on the map
CHIMNEY_FROM_RIGHT = 21  # the middle of the chimney, from the sprite's right edge


def _draw_window(surf, x, y, shutter):
    """A lit window with a cross frame, shutters and a box of flowers."""
    pygame.draw.rect(surf, WOOD[0], (x - 1, y - 1, 12, 13))
    pygame.draw.rect(surf, EMBER[2], (x, y, 10, 11))
    pygame.draw.rect(surf, EMBER[3], (x, y, 5, 5))
    pygame.draw.line(surf, WOOD[0], (x + 5, y), (x + 5, y + 10))
    pygame.draw.line(surf, WOOD[0], (x, y + 5), (x + 9, y + 5))
    for side in (x - 5, x + 11):
        pygame.draw.rect(surf, shutter[0], (side, y - 1, 4, 13))
        pygame.draw.rect(surf, shutter[1], (side + 1, y, 2, 11))
        for line in (y + 3, y + 7):
            pygame.draw.line(surf, shutter[0], (side + 1, line), (side + 2, line))
    pygame.draw.rect(surf, WOOD[0], (x - 2, y + 12, 14, 4))
    pygame.draw.line(surf, WOOD[1], (x - 1, y + 13), (x + 10, y + 13))
    for i in range(7):
        fx = x - 1 + i * 2
        surf.set_at((fx, y + 11), GRASS[0])
        surf.set_at((fx, y + 10), PETALS[i % 3])


def _draw_door(surf, x, bottom):
    """A plank door in a stone arch, with a step in front."""
    top = bottom - 22
    pygame.draw.rect(surf, STONE[1], (x - 2, top + 2, 18, 20))
    pygame.draw.circle(surf, STONE[1], (x + 7, top + 4), 9)
    pygame.draw.rect(surf, WOOD[0], (x, top + 3, 14, 19))
    pygame.draw.circle(surf, WOOD[0], (x + 7, top + 4), 7)
    pygame.draw.rect(surf, WOOD[1], (x + 1, top + 4, 12, 18))
    for line in (x + 4, x + 7, x + 10):
        pygame.draw.line(surf, WOOD[0], (line, top + 2), (line, bottom - 1))
    pygame.draw.line(surf, STEEL[1], (x + 1, top + 9), (x + 12, top + 9))
    pygame.draw.line(surf, STEEL[1], (x + 1, top + 16), (x + 12, top + 16))
    pygame.draw.rect(surf, GOLD, (x + 11, top + 12, 2, 2))
    pygame.draw.rect(surf, STONE[3], (x - 3, bottom - 2, 20, 2))
    pygame.draw.line(surf, STONE[4], (x - 3, bottom - 2), (x + 16, bottom - 2))


def _draw_timbers(surf, left, right, top, bottom):
    pygame.draw.rect(surf, WOOD[0], (left, top, right - left, 3))
    pygame.draw.line(surf, WOOD[1], (left, top), (right - 1, top))
    pygame.draw.rect(surf, WOOD[0], (left, bottom - 2, right - left, 2))
    for x in (left, right - 3):
        pygame.draw.rect(surf, WOOD[0], (x, top, 3, bottom - top))
        pygame.draw.line(surf, WOOD[1], (x, top), (x, bottom - 1))


def _draw_foundation(surf, rng, left, right, bottom):
    pygame.draw.rect(surf, STONE[1], (left, bottom - 7, right - left, 7))
    for row, y in enumerate((bottom - 7, bottom - 4)):
        x = left + row * 3
        while x < right - 2:
            width = rng.randint(4, 8)
            color = rng.choice(STONE[2:4])
            pygame.draw.rect(surf, color, (x, y, min(width, right - x) - 1, 2))
            x += width


def _draw_roof(surf, rng, width, roof_top, eave_y, colors):
    """A pitched roof of staggered shingles, some a touch lighter or darker."""
    inset = 12
    points = [(0, eave_y), (width, eave_y), (width - inset, roof_top), (inset, roof_top)]
    pygame.draw.polygon(surf, colors[1], points)
    for row, y in enumerate(range(roof_top, eave_y, 4)):
        k = (y - roof_top) / (eave_y - roof_top)
        left = int(inset * (1 - k))
        right = width - left
        pygame.draw.line(surf, colors[0], (left, y + 3), (right - 1, y + 3))
        for x in range(left + (row % 2) * 3, right, 6):
            pygame.draw.line(surf, colors[0], (x, y), (x, y + 3))
            roll = rng.random()
            if roll < 0.28:
                pygame.draw.line(surf, colors[2], (x + 1, y), (min(x + 4, right - 1), y))
            elif roll < 0.38:
                pygame.draw.rect(surf, colors[0], (x + 1, y, 3, 3))
    pygame.draw.rect(surf, colors[0], (inset - 1, roof_top - 2, width - inset * 2 + 2, 3))
    pygame.draw.line(surf, colors[2], (inset, roof_top - 2), (width - inset, roof_top - 2))
    pygame.draw.line(surf, colors[2], (0, eave_y - 1), (inset, roof_top))
    pygame.draw.rect(surf, colors[0], (0, eave_y, width, 2))


def _draw_chimney(surf, x, roof_top):
    bottom = roof_top + 12
    pygame.draw.rect(surf, BRICK[1], (x, 2, 10, bottom - 2))
    for row, y in enumerate(range(3, bottom, 3)):
        pygame.draw.line(surf, BRICK[0], (x, y), (x + 9, y))
        for bx in range(x + (row % 2) * 2, x + 10, 4):
            surf.set_at((bx, y + 1), BRICK[0])
    pygame.draw.line(surf, BRICK[2], (x, 2), (x, bottom - 1))
    pygame.draw.rect(surf, STONE[2], (x - 1, 0, 12, 3))
    pygame.draw.line(surf, STONE[4], (x - 1, 0), (x + 10, 0))


def _draw_dormer(surf, x, y, colors):
    """A small gabled window poking out of the roof."""
    pygame.draw.rect(surf, PLASTER[1], (x, y + 5, 14, 10))
    pygame.draw.rect(surf, WOOD[0], (x + 3, y + 7, 8, 7))
    pygame.draw.rect(surf, EMBER[2], (x + 4, y + 8, 6, 5))
    pygame.draw.line(surf, WOOD[0], (x + 7, y + 8), (x + 7, y + 12))
    pygame.draw.polygon(surf, colors[1], [(x - 3, y + 7), (x + 7, y - 2), (x + 17, y + 7)])
    pygame.draw.line(surf, colors[2], (x - 3, y + 7), (x + 7, y - 2))
    pygame.draw.line(surf, colors[0], (x + 7, y - 2), (x + 17, y + 7))
    pygame.draw.line(surf, colors[0], (x - 3, y + 7), (x + 17, y + 7))


def _draw_ivy(surf, rng, x, bottom, height):
    for _ in range(height * 2):
        y = bottom - int(rng.random() ** 1.6 * height)
        leaf_x = x + rng.randint(-3, 4)
        surf.set_at((leaf_x, y), rng.choice(GRASS[:3]))
        surf.set_at((leaf_x + 1, y), LEAVES[1])


def make_cottage(seed, width, height, door_x, window_xs, colors):
    """A whole cottage for a footprint `width` by `height` pixels.

    `door_x` and `window_xs` are the left edges of those tiles on the front wall,
    measured from the footprint's left edge. `colors` is one of COTTAGE_ROOFS.
    """
    rng = random.Random(seed)
    total = width + EAVE * 2
    tall = height + COTTAGE_RISE
    surf = pygame.Surface((total, tall), pygame.SRCALPHA)

    wall_top = tall - WALL_HEIGHT
    left, right = EAVE, EAVE + width
    roof_top = 10

    _draw_chimney(surf, total - CHIMNEY_FROM_RIGHT - 5, roof_top)
    pygame.draw.rect(surf, PLASTER[1], (left, wall_top, width, WALL_HEIGHT))
    for _ in range(width):
        surf.set_at((rng.randrange(left, right), rng.randrange(wall_top, tall)), rng.choice((PLASTER[0], PLASTER[2])))
    _draw_timbers(surf, left, right, wall_top, tall)
    _draw_foundation(surf, rng, left, right, tall)
    _draw_roof(surf, rng, total, roof_top, wall_top, colors)
    pygame.draw.rect(surf, PLASTER[0], (left, wall_top + 2, width, 2))  # shade under the eave

    for x in window_xs:
        _draw_window(surf, left + x + 3, wall_top + 6, colors)
    if door_x is not None:
        _draw_door(surf, left + door_x + 1, tall)
    _draw_dormer(surf, total // 2 - 7, roof_top + 5, colors)
    _draw_ivy(surf, rng, left + 2, tall - 2, 24)
    return _outline(surf, MOSS_INK)


@cache
def prop_images():
    rng = random.Random(17)
    return {
        "small_pine": [make_pine(rng, PINE, rng.randint(26, 30), rng.randint(32, 38)) for _ in range(5)],
        "pine": [make_pine(rng, PINE, rng.randint(32, 38), rng.randint(42, 50)) for _ in range(6)],
        "deep_pine": [make_pine(rng, DEEP_PINE, rng.randint(34, 40), rng.randint(44, 54)) for _ in range(5)],
        "bush": [make_bush(rng) for _ in range(4)],
        "rock": [make_rock(rng) for _ in range(3)],
    }
