"""Large scenery that stands on the map: pines, flowering bushes and mossy rocks.

Props aren't tied to the tile grid. Each has a ground position, and the overworld
draws them in depth order with the characters, so you can walk behind them.
"""
from functools import cache
import random

import pygame

from ui.palette import BERRY, DEEP_PINE, GRASS, MOSS_INK, PETALS, PINE, ROCK, TRUNK


FIGURE_PAD = 2


def _outline(surf, color):
    silhouette = pygame.mask.from_surface(surf).to_surface(setcolor=(*color, 255), unsetcolor=(0, 0, 0, 0))
    framed = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for offset in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        framed.blit(silhouette, offset)
    framed.blit(surf, (0, 0))
    return framed


def figure_canvas(size):
    """A canvas with a clear border, so outlines never get cut off at its edge.

    Returns (canvas, area): draw on `area` using coordinates inside `size`, then
    outline and show `canvas`, which is FIGURE_PAD bigger on every side.
    """
    canvas = pygame.Surface((size[0] + FIGURE_PAD * 2, size[1] + FIGURE_PAD * 2), pygame.SRCALPHA)
    return canvas, canvas.subsurface((FIGURE_PAD, FIGURE_PAD, *size))


def make_pine(rng, ramp, width, height):
    """A tall spruce: layered boughs that sweep out and droop into needle tips.

    `ramp` runs from shadow to highlight (five steps). Light comes from the upper
    left, and each tier sits in the shadow of the one above it.
    """
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    cx = width / 2
    base = height - 2
    canopy_top, canopy_bottom = 1, height - 11
    span = canopy_bottom - canopy_top

    # Trunk with a little root flare, bark lit on the left.
    for y in range(canopy_bottom - 6, base + 1):
        flare = 1 if y >= base - 1 else 0
        for x in range(int(cx) - 2 - flare, int(cx) + 3 + flare):
            side = x - cx
            surf.set_at((x, y), TRUNK[2] if side < -1 else TRUNK[1] if side < 1 else TRUNK[0])
        if rng.random() < 0.4:
            surf.set_at((int(cx) + rng.randint(-1, 1), y), TRUNK[0])

    # Tier boundaries: short tiers at the top, longer towards the bottom.
    tiers = max(5, span // 7)
    edges = [canopy_top + round(span * (i / tiers) ** 0.85) for i in range(tiers + 1)]
    for tier in range(tiers):
        top, bottom = edges[tier], edges[tier + 1]
        jag_left, jag_right = rng.uniform(-1.5, 2.5), rng.uniform(-1.5, 2.5)
        spread = rng.uniform(0.82, 1.12)   # some boughs reach further than others
        lean = rng.choice((-1, 0, 0, 1))   # and sit a pixel off centre
        for y in range(top, bottom + 1):
            t = (y - canopy_top) / span
            f = (y - top) / max(1, bottom - top)        # 0 at the tier's top, 1 at its lip
            half = min(width / 2 - 2, (width / 2 - 2) * (0.1 + 0.9 * t ** 0.9) * (0.5 + 0.5 * f ** 1.4) * spread)
            left = int(cx + lean - half - jag_left * f - rng.randint(0, 1))
            right = int(cx + lean + half + jag_right * f + rng.randint(0, 1))
            for x in range(max(0, left), min(width, right + 1)):
                side = (x - cx) / max(1.0, half)
                if f < 0.3 and tier:
                    color = ramp[0] if side > -0.5 else ramp[1]   # shade under the bough above
                elif side > 0.4:
                    color = ramp[0] if rng.random() < 0.55 else ramp[1]
                elif side > -0.3:
                    color = ramp[1] if rng.random() < 0.7 else ramp[2]
                else:
                    color = ramp[2] if rng.random() < 0.75 else ramp[3]
                surf.set_at((x, y), color)

        # Needle tips hanging from the lip of the bough.
        lip_half = min(width / 2 - 2, (width / 2 - 2) * (0.1 + 0.9 * ((bottom - canopy_top) / span) ** 0.9) * spread)
        for x in range(int(cx + lean - lip_half), int(cx + lean + lip_half) + 1, 2):
            if 0 <= x < width and rng.random() < 0.75:
                side = (x - cx) / max(1.0, lip_half)
                drop = rng.randint(1, 4 if abs(side) > 0.5 else 2)
                color = ramp[2] if side < -0.2 else ramp[1] if side < 0.3 else ramp[0]
                pygame.draw.line(surf, color, (x, bottom), (x, min(base, bottom + drop)))

        # Bright needle strokes on the sunlit upper side of the bough.
        for _ in range(int(lip_half * 0.9) + 1):
            x = int(cx - rng.uniform(0.1, 0.95) * lip_half)
            y = top + int((bottom - top) * rng.uniform(0.35, 0.9))
            if 0 < x < width - 2 and surf.get_at((x, y)).a:
                surf.set_at((x, y), ramp[3])
                surf.set_at((x - 1, y + 1), ramp[3])
                if rng.random() < 0.35:
                    surf.set_at((x + 1, y - 1), ramp[4])
    for y in range(canopy_top, canopy_top + 3):  # the leader at the very top
        surf.set_at((int(cx), y), ramp[2])

    # A tuft of grass and a couple of flowers at the foot.
    for _ in range(9):
        x = int(cx) + rng.randint(-6, 6)
        pygame.draw.line(surf, rng.choice(GRASS[:3]), (x, base), (x + rng.randint(-1, 1), base - rng.randint(1, 3)))
    for _ in range(2):
        surf.set_at((int(cx) + rng.choice((-5, -4, 4, 5)), base - 1), rng.choice((BERRY[1], PETALS[0])))
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


@cache
def prop_images():
    rng = random.Random(17)
    return {
        "small_pine": [make_pine(rng, PINE, rng.randint(24, 28), rng.randint(38, 44)) for _ in range(5)],
        "pine": [make_pine(rng, PINE, rng.randint(28, 34), rng.randint(50, 60)) for _ in range(6)],
        "deep_pine": [make_pine(rng, DEEP_PINE, rng.randint(30, 36), rng.randint(54, 64)) for _ in range(5)],
        "bush": [make_bush(rng) for _ in range(4)],
        "rock": [make_rock(rng) for _ in range(3)],
    }
