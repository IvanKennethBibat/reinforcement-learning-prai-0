"""The overworld: a village with roads out to three slimes, in any order.

To change the level, run ``python -m ui.editor`` or edit ``ui/assets/level.txt``,
which holds one character per 16px tile:

    .  grass      ,  dirt path      _  flagstone     ~  crimson carpet
    #  wall            T  tree           b  bush          r  mossy rock
    c  pillar          w  water          =  plank bridge  o  well
    R  roof            D  door           W  lit window    l  lantern
    S  start           H  hall gate      1 2 3 B  foes
    e  sheep           p  lattice fence  g  veg patch     v  flower bed
"""
from functools import cache
import math
import random
from collections import deque

import numpy as np

import pygame

from ui.arena import BAYER, dither_pick
from ui.bouncer import Bouncer
from ui.encounters import ENCOUNTERS
from ui.font import draw_text
from ui.palette import (
    BERRY, BONE, CLOTH, COBBLE, DANGER, DIRT, EAR, EMBER, FOREST_FLOOR, FUR, GOLD, GRASS,
    INK, LATTICE, LEAVES, MOSS_INK, PAVING, PETALS, ROOF, SKY, STEEL, STONE, TRUNK, WALL_TOP, WATER,
    WHITE, WOOD,
)
from ui.buildings import load_building
from ui.props import FIGURE_PAD, figure_canvas, prop_images
from ui.sheep import FEET_Y, Sheep
from ui.sprites import ASSETS, load_sheet

TILE = 16
VIEW = (320, 180)
SPEED = 60  # exactly one pixel per step, so scrolling never stutters
TRIGGER_RADIUS = 30
ALERT_TIME = 0.55
IDLE_DELAY = 0.35     # how long the cat stands still before its idle loop starts
IDLE_TAIL = (0, 1, 2, 1, 0, -1, -2, -1)
IDLE_NOD = (0, 0, 0, 1, 1, 1, 0, 0)
IDLE_BLINK = 6
SIT_DELAY = 4.0       # how long the cat stands before it sits down
SIT_TAIL = (0, 0, 1, 1, 0, 0, -1, -1)
SIT_BLINK = 4
GLOW_RADIUS = 30
FIGURE_SIZE = (20, 26)
SMOKE_PUFFS = 7
SMOKE_LIFE = 4.5      # seconds for a puff to rise and fade
SMOKE_RISE = 40

LEVEL_FILE = ASSETS / "level.txt"
LEVEL = LEVEL_FILE.read_text().split()
SOLID = set("#TbrcHwRDWolp")
WALLS = "#RDW"
GRASSY = ".brlepgv"
MAX_FRAY = 10
# What each block of roof tiles becomes, in map order (left to right, top to bottom).
# Each name needs ui/assets/buildings/<name>.png and .json.
VILLAGE = ("bakery", "bookstore", "coffee", "home")
PLACED_PROPS = {"b": "bush", "r": "rock"}

# Which foes must fall before each gate opens.
GATES = {"H": {"1", "2", "3"}}


def find_tiles(chars):
    return {
        char: (x, y)
        for y, row in enumerate(LEVEL) for x, char in enumerate(row)
        if char in chars
    }


def tile_center(tile):
    return (tile[0] * TILE + TILE / 2, tile[1] * TILE + TILE / 2)


def reachable(open_gates="", blocked=()):
    """Every tile you can walk to from the start."""
    start = find_tiles("S")["S"]
    seen, queue = {start}, deque([start])
    while queue:
        x, y = queue.popleft()
        for nxt in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if not (0 <= nxt[1] < len(LEVEL) and 0 <= nxt[0] < len(LEVEL[0])):
                continue
            char = LEVEL[nxt[1]][nxt[0]]
            if nxt not in seen and nxt not in blocked and (char not in SOLID or char in open_gates):
                seen.add(nxt)
                queue.append(nxt)
    return seen


def level_problems():
    """What would stop the level from loading or being finished."""
    if len({len(row) for row in LEVEL}) != 1:
        return ["ROWS DIFFER IN LENGTH"]
    text = "".join(LEVEL)
    problems = [f"NEED EXACTLY ONE {char}" for char in "S123B" if text.count(char) != 1]
    problems += [f"NO GATE {gate} ON THE MAP" for gate in GATES if gate not in text]
    if problems:
        return problems

    spots = find_tiles("123B")
    walkable = reachable()
    problems = [f"CANNOT REACH {ENCOUNTERS[key].name}" for key in "123" if spots[key] not in walkable]
    if spots["B"] in walkable:
        problems.append("THE BOSS IS NOT BEHIND THE GATE")
    elif spots["B"] not in reachable("".join(GATES)):
        problems.append("CANNOT REACH THE BOSS")
    return problems


def _paint_ground(surf, char, x, y, rng):
    px, py = x * TILE, y * TILE
    if char in "123B":  # foes stand on whatever surrounds them
        char = LEVEL[y][min(x + 1, len(LEVEL[y]) - 1)]
    if char == "w":
        _paint_water(surf, px, py, rng)
    elif char == "=":
        _paint_bridge(surf, px, py)
    elif char in ",SH":
        pygame.draw.rect(surf, DIRT[1], (px, py, TILE, TILE))
    elif char == "T":
        pygame.draw.rect(surf, FOREST_FLOOR, (px, py, TILE, TILE))
    elif char in GRASSY:
        _paint_grass(surf, px, py, rng)
    elif char == "~":
        pygame.draw.rect(surf, CLOTH[1], (px, py, TILE, TILE))
        pygame.draw.line(surf, CLOTH[2], (px, py + 7), (px + TILE, py + 7))
        pygame.draw.line(surf, GOLD, (px + 7, py + 3), (px + 7, py + 3))
    else:  # stone floor: grass here, with cobbles laid over it by _lay_cobbles
        pygame.draw.rect(surf, GRASS[1], (px, py, TILE, TILE))
        for _ in range(3):
            surf.set_at((px + rng.randrange(TILE), py + rng.randrange(TILE)), GRASS[0])


def _paint_grass(surf, px, py, rng):
    """Flat grass, with the odd tuft and flower so the eye has somewhere to rest."""
    pygame.draw.rect(surf, GRASS[1], (px, py, TILE, TILE))
    if rng.random() < 0.35:
        x, y = px + rng.randrange(2, TILE - 3), py + rng.randrange(3, TILE)
        for dx, height in ((-1, 2), (0, 3), (1, 2)):
            pygame.draw.line(surf, GRASS[0], (x + dx, y), (x + dx, y - height))
    if rng.random() < 0.12:
        x, y = px + rng.randrange(2, TILE - 2), py + rng.randrange(2, TILE - 2)
        color = rng.choice(PETALS)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            surf.set_at((x + dx, y + dy), color)
        surf.set_at((x, y), GOLD)


def _paint_water(surf, px, py, rng):
    pygame.draw.rect(surf, WATER[1], (px, py, TILE, TILE))
    for _ in range(4):
        x, y = px + rng.randrange(TILE - 5), py + rng.randrange(TILE)
        pygame.draw.line(surf, WATER[0], (x, y), (x + rng.randrange(3, 6), y))
    for _ in range(2):
        x, y = px + rng.randrange(TILE - 5), py + rng.randrange(TILE)
        pygame.draw.line(surf, WATER[2], (x, y), (x + rng.randrange(2, 4), y))


def _paint_bridge(surf, px, py):
    pygame.draw.rect(surf, WOOD[0], (px, py, TILE, TILE))
    for i in range(0, TILE, 4):
        pygame.draw.line(surf, WOOD[1], (px + i, py), (px + i, py + TILE))
        pygame.draw.line(surf, INK, (px + i + 3, py), (px + i + 3, py + TILE))


def _paint_roof(surf, x, y):
    px, py = x * TILE, y * TILE
    pygame.draw.rect(surf, ROOF[0], (px, py, TILE, TILE))
    for row, top in enumerate(range(0, TILE, 4)):
        pygame.draw.line(surf, INK, (px, py + top + 3), (px + TILE, py + top + 3))
        pygame.draw.line(surf, ROOF[1], (px, py + top), (px + TILE, py + top))
        for i in range(row % 2 * 3, TILE, 6):
            pygame.draw.line(surf, INK, (px + i, py + top), (px + i, py + top + 3))
    if LEVEL[y - 1][x] != "R":
        pygame.draw.line(surf, STONE[3], (px, py), (px + TILE, py))


def _paint_door(surf, px, py):
    pygame.draw.rect(surf, INK, (px + 3, py + 2, 10, 14))
    pygame.draw.rect(surf, WOOD[1], (px + 4, py + 3, 8, 13))
    pygame.draw.line(surf, INK, (px + 8, py + 3), (px + 8, py + 15))
    surf.set_at((px + 10, py + 9), GOLD)


def _paint_window(surf, px, py):
    pygame.draw.rect(surf, INK, (px + 4, py + 3, 8, 9))
    pygame.draw.rect(surf, EMBER[2], (px + 5, py + 4, 6, 7))
    pygame.draw.rect(surf, EMBER[3], (px + 5, py + 4, 3, 3))
    pygame.draw.line(surf, INK, (px + 8, py + 4), (px + 8, py + 10))
    pygame.draw.line(surf, INK, (px + 5, py + 7), (px + 10, py + 7))


def _is_wall(x, y):
    return not (0 <= y < len(LEVEL) and 0 <= x < len(LEVEL[0])) or LEVEL[y][x] in WALLS


def _moss(surf, rng, px, py, count, top_only=False):
    """Little clumps of moss, mostly along the top edge of the stone."""
    for _ in range(count):
        x = px + rng.randrange(TILE - 2)
        y = py + (rng.randrange(3) if top_only else rng.randrange(TILE - 2))
        for dx, dy in ((0, 0), (1, 0), (0, 1), (rng.choice((-1, 2)), 0)):
            if rng.random() < 0.85:
                surf.set_at((x + dx, y + dy), rng.choice((GRASS[0], LEAVES[1], LEAVES[2])))


def _paint_wall(surf, x, y, rng):
    """Weathered stone: the mossy top of a wall, or its face where it meets the ground."""
    px, py = x * TILE, y * TILE
    if _is_wall(x, y + 1):
        # Looking down on top of the wall: big worn slabs with moss in the cracks.
        pygame.draw.rect(surf, WALL_TOP[0], (px, py, TILE, TILE))
        for row, top in enumerate(range(0, TILE, 8)):
            for left in range(-4 * (row % 2), TILE, 8):
                slab = pygame.Rect(px + max(0, left), py + top, min(TILE, left + 8) - max(0, left) - 1, 7)
                if slab.width > 0:
                    pygame.draw.rect(surf, WALL_TOP[1], slab)
                    pygame.draw.line(surf, WALL_TOP[2], slab.topleft, (slab.right - 1, slab.top))
        _moss(surf, rng, px, py, rng.randint(1, 3))
        if not _is_wall(x, y - 1):
            pygame.draw.line(surf, MOSS_INK, (px, py), (px + TILE - 1, py))
        if not _is_wall(x - 1, y):
            pygame.draw.line(surf, MOSS_INK, (px, py), (px, py + TILE - 1))
        if not _is_wall(x + 1, y):
            pygame.draw.line(surf, MOSS_INK, (px + TILE - 1, py), (px + TILE - 1, py + TILE - 1))
        return

    # The face of the wall: courses of outlined blocks, moss dripping from the top.
    pygame.draw.rect(surf, COBBLE[0], (px, py, TILE, TILE))
    for row, top in enumerate(range(0, TILE - 2, 4)):
        left = -rng.randint(0, 5) if row % 2 else 0
        while left < TILE:
            width = rng.randint(5, 8)
            block = pygame.Rect(px + max(0, left), py + top, min(TILE, left + width) - max(0, left) - 1, 3)
            if block.width > 0:
                pygame.draw.rect(surf, rng.choice((COBBLE[1], COBBLE[2], COBBLE[2])), block)
                pygame.draw.line(surf, COBBLE[3], block.topleft, (block.right - 1, block.top))
            left += width
    _moss(surf, rng, px, py, rng.randint(1, 3), top_only=True)
    if rng.random() < 0.18:  # a trailing vine
        vx = px + rng.randrange(2, TILE - 2)
        for vy in range(py, py + rng.randint(6, 12)):
            surf.set_at((vx + (vy // 3) % 2, vy), TRUNK[0])
            if vy % 3 == 0:
                surf.set_at((vx + 1 - (vy // 3) % 2 * 2, vy), LEAVES[2])
    if not _is_wall(x, y - 1):
        pygame.draw.line(surf, MOSS_INK, (px, py), (px + TILE - 1, py))
    pygame.draw.rect(surf, MOSS_INK, (px, py + TILE - 2, TILE, 2))


def _is_fence(x, y):
    return 0 <= y < len(LEVEL) and 0 <= x < len(LEVEL[0]) and LEVEL[y][x] == "p"


FENCE_BOTTOM = 13           # the lattice's lower rail, from the top of the tile
FENCE_POST = (5, 6)         # left edge and width of a centred post or rail, ink included


def _fence_panel(surf, px, py, columns):
    """The lattice face with its scalloped top, across the given tile columns."""
    bottom = py + FENCE_BOTTOM
    for i in columns:
        top = py + 6 - round(3 * math.sin(math.pi * (i + 0.5) / TILE))
        for j in range(top + 2, bottom):
            u, v = i + j, i - j
            if u % 5 in (0, 1) or v % 5 in (0, 1):
                shade = LATTICE[2] if u % 5 == 0 and v % 5 not in (0, 1) else LATTICE[1]
                surf.set_at((px + i, j), shade)
        surf.set_at((px + i, top - 1), MOSS_INK)
        surf.set_at((px + i, top), LATTICE[2])
        surf.set_at((px + i, top + 1), LATTICE[1])
        surf.set_at((px + i, bottom), LATTICE[1])
        surf.set_at((px + i, bottom + 1), LATTICE[0])
        surf.set_at((px + i, bottom + 2), MOSS_INK)


def _fence_post(surf, left, py, width=5):
    """A square post standing the full height of the fence, with a cap."""
    bottom = py + FENCE_BOTTOM
    pygame.draw.rect(surf, MOSS_INK, (left - 1, py + 1, width, bottom - py + 3))
    pygame.draw.rect(surf, LATTICE[1], (left, py + 2, width - 2, bottom - py + 1))
    pygame.draw.line(surf, LATTICE[2], (left, py + 2), (left, bottom))
    pygame.draw.line(surf, LATTICE[0], (left + width - 3, py + 3), (left + width - 3, bottom + 1))
    pygame.draw.line(surf, LATTICE[2], (left, py + 1), (left + width - 3, py + 1))


def _fence_rail(surf, px, top, end):
    """A fence seen edge on: a slim rail, as it runs up or down the screen."""
    left, width = FENCE_POST
    pygame.draw.rect(surf, MOSS_INK, (px + left, top, width, end - top + 1))
    pygame.draw.rect(surf, LATTICE[1], (px + left + 1, top, width - 2, end - top + 1))
    pygame.draw.line(surf, LATTICE[2], (px + left + 1, top), (px + left + 1, end))
    for j in range(top + 2, end, 4):
        pygame.draw.line(surf, LATTICE[0], (px + left + 2, j), (px + left + width - 2, j))


def _paint_fence(surf, x, y):
    """A dark wood lattice fence that joins up with the fence tiles around it.

    Runs left to right show the lattice face on, runs up and down are seen edge on,
    and where the two meet a single post takes the corner so neither cuts into the other.
    """
    px, py = x * TILE, y * TILE
    left, right = _is_fence(x - 1, y), _is_fence(x + 1, y)
    up, down = _is_fence(x, y - 1), _is_fence(x, y + 1)
    across, along = left or right, up or down
    post_left = px + FENCE_POST[0] + 1

    if along and not across:
        top = py if up else py + 2
        end = py + TILE - 1 if down else py + 14
        _fence_rail(surf, px, top, end)
        if not up or not down:  # a cap where the run ends
            cap = top if not up else end - 2
            pygame.draw.rect(surf, MOSS_INK, (px + 4, cap - 1, 8, 4))
            pygame.draw.rect(surf, LATTICE[2], (px + 5, cap, 6, 2))
        return

    if not along:
        _fence_panel(surf, px, py, range(TILE))
        if not left:
            _fence_post(surf, px, py)
        if not right:
            _fence_post(surf, px + TILE - 3, py)
        return

    # A corner, T or crossing: the rail behind, then the panel, then the post, then the rail in front.
    if up:
        _fence_rail(surf, px, py, py + 4)
    columns = [i for i in range(TILE) if (left and i < post_left - px) or (right and i > post_left - px + 2)]
    _fence_panel(surf, px, py, columns)
    _fence_post(surf, post_left, py, width=FENCE_POST[1])  # as wide as the rail it meets
    if down:
        _fence_rail(surf, px, py + FENCE_BOTTOM + 3, py + TILE - 1)


def _paint_veg_patch(surf, px, py, rng):
    """Tilled soil with a row of cabbages, carrots or pumpkins."""
    pygame.draw.rect(surf, DIRT[0], (px + 1, py + 1, 14, 14))
    pygame.draw.line(surf, TRUNK[1], (px + 1, py + 6), (px + 14, py + 6))
    pygame.draw.line(surf, TRUNK[1], (px + 1, py + 11), (px + 14, py + 11))
    crop = rng.choice(("cabbage", "carrot", "pumpkin"))
    for row, y in enumerate((py + 4, py + 10)):
        for x in range(px + 3 + row, px + 14, 5):
            if crop == "cabbage":
                pygame.draw.circle(surf, LEAVES[1], (x, y), 2)
                surf.set_at((x - 1, y - 1), LEAVES[3])
            elif crop == "carrot":
                pygame.draw.line(surf, BERRY[2], (x, y), (x, y + 2))
                pygame.draw.line(surf, GRASS[2], (x - 1, y - 2), (x, y - 1))
                pygame.draw.line(surf, GRASS[2], (x + 1, y - 2), (x, y - 1))
            else:
                pygame.draw.circle(surf, BERRY[0], (x, y + 1), 2)
                surf.set_at((x - 1, y), BERRY[1])
                surf.set_at((x, y - 2), LEAVES[1])


def _paint_flower_bed(surf, px, py, rng):
    """A tight clump of leaves and bright blooms."""
    pygame.draw.rect(surf, LEAVES[1], (px + 1, py + 6, 14, 9))
    for _ in range(7):
        x, y = px + rng.randrange(1, 14), py + rng.randrange(6, 14)
        surf.set_at((x, y), LEAVES[3])
    colors = (*PETALS, EMBER[2], DANGER[2])
    for _ in range(9):
        x, y = px + rng.randrange(2, 14), py + rng.randrange(3, 13)
        color = rng.choice(colors)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            surf.set_at((x + dx, y + dy), color)
        surf.set_at((x, y), GOLD)


def _paint_prop(surf, char, x, y, rng):
    px, py = x * TILE, y * TILE
    if char == "p":
        _paint_fence(surf, x, y)
    elif char == "g":
        _paint_veg_patch(surf, px, py, rng)
    elif char == "v":
        _paint_flower_bed(surf, px, py, rng)
    elif char == "o":  # well
        pygame.draw.ellipse(surf, INK, (px, py + 3, 16, 13))
        pygame.draw.ellipse(surf, STONE[2], (px + 1, py + 3, 14, 11))
        pygame.draw.ellipse(surf, SKY[0], (px + 4, py + 5, 8, 6))
        pygame.draw.line(surf, STONE[4], (px + 3, py + 4), (px + 12, py + 4))
    elif char == "l":  # lantern post
        pygame.draw.ellipse(surf, INK, (px + 4, py + 12, 8, 4))
        pygame.draw.line(surf, INK, (px + 8, py + 14), (px + 8, py + 5), 2)
        pygame.draw.rect(surf, INK, (px + 5, py + 1, 7, 6))
        pygame.draw.rect(surf, EMBER[2], (px + 6, py + 2, 5, 4))
        pygame.draw.rect(surf, EMBER[3], (px + 7, py + 3, 2, 2))
    elif char == "c":  # pillar
        pygame.draw.ellipse(surf, INK, (px + 1, py + 10, 14, 6))
        pygame.draw.rect(surf, STONE[2], (px + 3, py + 1, 10, 13))
        pygame.draw.rect(surf, STONE[4], (px + 4, py + 1, 2, 13))
        pygame.draw.rect(surf, STONE[1], (px + 10, py + 1, 3, 13))
        pygame.draw.rect(surf, STONE[3], (px + 2, py, 12, 2))


def _paint_lantern_glow(surf):
    """Pools of warm light, dithered in once every tile has been painted."""
    for x, y in ((x, y) for y, row in enumerate(LEVEL) for x, char in enumerate(row) if char == "l"):
        cx, cy = x * TILE + 8, y * TILE + 4
        for py in range(cy - GLOW_RADIUS, cy + GLOW_RADIUS):
            for px in range(cx - GLOW_RADIUS, cx + GLOW_RADIUS):
                if not (0 <= px < surf.get_width() and 0 <= py < surf.get_height()):
                    continue
                strength = 1 - math.dist((px, py), (cx, cy)) / GLOW_RADIUS
                if (BAYER[py % 4][px % 4] + 0.5) / 16 < strength * 0.5:
                    base = surf.get_at((px, py))
                    surf.set_at((px, py), tuple((base[i] + GOLD[i]) // 2 for i in range(3)))


def paint_tile(surf, char, x, y):
    # Seeded by position, so editing one tile leaves the detail on the others alone.
    rng = random.Random(y * 1000 + x)
    if char == "R":
        _paint_roof(surf, x, y)
    elif char in WALLS:
        _paint_wall(surf, x, y, rng)
        if char == "D":
            _paint_door(surf, x * TILE, y * TILE)
        elif char == "W":
            _paint_window(surf, x * TILE, y * TILE)
    else:
        _paint_ground(surf, char, x, y, rng)
        _paint_prop(surf, char, x, y, rng)


def _fray_edges(surf):
    """Eat into paths, water and stone with wobbling grass, so no edge follows the grid."""
    width, height = surf.get_size()
    pixels = pygame.surfarray.pixels3d(surf)
    tiles = np.array([list(row) for row in LEVEL]).T
    grown = lambda mask: np.repeat(np.repeat(mask, TILE, axis=0), TILE, axis=1)

    def distance_from(chars):
        """How far each pixel is from the nearest of these tiles, up to MAX_FRAY."""
        near = grown(np.isin(tiles, list(chars)))
        distance = np.full((width, height), MAX_FRAY, np.int16)
        for step in range(MAX_FRAY):
            distance[near & (distance == MAX_FRAY)] = step
            grown_out = near.copy()
            grown_out[1:] |= near[:-1]
            grown_out[:-1] |= near[1:]
            grown_out[:, 1:] |= near[:, :-1]
            grown_out[:, :-1] |= near[:, 1:]
            near = grown_out
        return distance

    x, y = np.meshgrid(np.arange(width), np.arange(height), indexing="ij")
    wobble = np.sin(x / 9 + np.sin(y / 13) * 2) + np.sin(y / 7 + np.sin(x / 17) * 2) + 0.5 * np.sin((x + y) / 3.3)
    wobble = (wobble + 2.5) / 5

    to_grass = distance_from(GRASSY)
    to_ground = distance_from(GRASSY + "T")
    speckle = np.sin(x * 12.9898 + y * 78.233) * 43758.5453 % 1

    forest = grown(tiles == "T")
    pixels[forest & (to_grass < 2 + wobble * 7)] = GRASS[1]

    for chars, inset, spread in ((",SH", 3, 5), ("w", 1, 4)):
        region = grown(np.isin(tiles, list(chars)))
        edge = inset + wobble * spread
        pixels[region & (to_ground < edge)] = GRASS[1]
        if chars == ",SH":
            pixels[region & (to_ground >= edge) & (to_ground < edge + 1)] = DIRT[0]
            pixels[region & (to_ground >= edge + 1) & (speckle > 0.985)] = DIRT[2]
    del pixels


STONE_FLOOR = "_co"   # tiles with a cobbled floor; foes take the floor of the tile beside them
COBBLE_FADE = 16      # pixels over which cobbles thin out towards the edge of a floor
STRAY_REACH = 10      # how far loose cobbles scatter onto the grass beyond


def _distance_to(mask, limit):
    """For every pixel, how many steps to the nearest True pixel, capped at `limit`."""
    distance = np.full(mask.shape, limit, np.int16)
    near = mask.copy()
    for step in range(limit):
        distance[near & (distance == limit)] = step
        grown = near.copy()
        grown[1:] |= near[:-1]
        grown[:-1] |= near[1:]
        grown[:, 1:] |= near[:, :-1]
        grown[:, :-1] |= near[:, 1:]
        near = grown
    return distance


def _floor_tiles():
    """Which tiles are cobbled, counting a foe as standing on the floor beside it."""
    def ground(x, y):
        char = LEVEL[y][x]
        return LEVEL[y][min(x + 1, len(LEVEL[y]) - 1)] if char in "123B" else char
    return np.array([[ground(x, y) in STONE_FLOOR for y in range(len(LEVEL))] for x in range(len(LEVEL[0]))])


STONE_SPACING = 11    # rough width of one cobble, in pixels


def _nearest_seeds(width, height, rng):
    """Scatter one seed per cell of a jittered grid; each pixel finds its two nearest.

    The pixels nearest each seed make one irregular stone (a Voronoi cell), and the gap
    between the nearest and second-nearest distance says how close a pixel is to a seam.
    """
    cols, rows = width // STONE_SPACING + 2, height // STONE_SPACING + 2
    jitter = np.array([[(rng.uniform(1, STONE_SPACING - 1), rng.uniform(1, STONE_SPACING - 1))
                        for _ in range(rows)] for _ in range(cols)])
    seeds_x = (np.arange(cols)[:, None] - 1) * STONE_SPACING + jitter[..., 0]
    seeds_y = (np.arange(rows)[None, :] - 1) * STONE_SPACING + jitter[..., 1]
    px, py = np.meshgrid(np.arange(width), np.arange(height), indexing="ij")
    cell_x, cell_y = px // STONE_SPACING + 1, py // STONE_SPACING + 1
    first = np.full(px.shape, 1e9)
    second = np.full(px.shape, 1e9)
    owner = np.zeros(px.shape + (2,), np.int32)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            cx = np.clip(cell_x + dx, 0, cols - 1)
            cy = np.clip(cell_y + dy, 0, rows - 1)
            sx, sy = seeds_x[cx, cy], seeds_y[cx, cy]
            dist = np.hypot((px - sx) * 0.85, py - sy)   # a little wider than tall
            closer = dist < first
            second = np.where(closer, first, np.minimum(second, dist))
            first = np.where(closer, dist, first)
            owner[closer] = np.stack([cx, cy], axis=-1)[closer]
    return seeds_x, seeds_y, owner, second - first, px, py


def _lay_cobbles(surf):
    """Pave stone floors with irregular, mottled cobbles that break up into the grass.

    Deep inside a floor the stones pack tight over dark grout. Towards the edge the
    seams widen into grass with the odd flower, stones drop out, and a few loose ones
    scatter onto the meadow beyond, so a floor fades out instead of stopping dead.
    """
    grown = lambda mask: np.repeat(np.repeat(mask, TILE, axis=0), TILE, axis=1)
    tiles = np.array([list(row) for row in LEVEL]).T
    floor = grown(_floor_tiles())
    inside = _distance_to(~floor, COBBLE_FADE)          # how deep into the floor
    outside = _distance_to(floor, STRAY_REACH)          # how far out onto the grass
    grassy = grown(np.isin(tiles, list(GRASSY)))
    allowed = floor | (grassy & (outside < STRAY_REACH))
    width, height = surf.get_size()
    rng = random.Random(77)
    seeds_x, seeds_y, owner, seam, px, py = _nearest_seeds(width, height, rng)

    # Decide which stones are laid: nearly all deep inside, fewer towards the edge.
    cols, rows = seeds_x.shape
    kept = np.zeros((cols, rows), bool)
    tone = np.zeros((cols, rows))
    for cx in range(cols):
        for cy in range(rows):
            sx, sy = int(seeds_x[cx, cy]), int(seeds_y[cx, cy])
            if not (0 <= sx < width and 0 <= sy < height):
                continue
            if floor[sx, sy]:
                chance = 0.35 + 0.65 * min(1.0, inside[sx, sy] / COBBLE_FADE) ** 1.5
            elif grassy[sx, sy] and outside[sx, sy] < STRAY_REACH:
                chance = 0.35 * (1 - outside[sx, sy] / STRAY_REACH)
                # a loose stone needs open grass all round it
                reach = STONE_SPACING // 2 + 1
                if not all(0 <= sx + ox < width and 0 <= sy + oy < height and allowed[sx + ox, sy + oy]
                           for ox, oy in ((-reach, 0), (reach, 0), (0, -reach), (0, reach))):
                    continue
            else:
                continue
            kept[cx, cy] = rng.random() < chance
            tone[cx, cy] = rng.uniform(-0.12, 0.12)

    ox, oy = owner[..., 0], owner[..., 1]
    deep = floor & (inside >= 9 + _wobble(px, py) * 10)    # where the seams are dark grout
    seam_width = np.where(deep, 0.8, 2.4 + 3.0 * (1 - np.minimum(inside, COBBLE_FADE) / COBBLE_FADE))
    stone = kept[ox, oy] & allowed & (seam >= seam_width)

    # Mottled face: lit from the top left, with chunky 2x2 speckle like weathered rock.
    rel_x = (px - seeds_x[ox, oy]) / STONE_SPACING
    rel_y = (py - seeds_y[ox, oy]) / STONE_SPACING
    speckle = np.random.default_rng(3).uniform(-0.28, 0.28, (width // 2 + 1, height // 2 + 1))
    light = 1.0 - 1.6 * np.hypot(rel_x + 0.12, rel_y + 0.15) + speckle[px // 2, py // 2] + tone[ox, oy]
    rim = seam < seam_width + 1.4                          # the stone's outline
    shade = np.digitize(light, (0.25, 0.55, 0.85))        # 0 dark .. 3 bright

    pixels = pygame.surfarray.pixels3d(surf)
    pixels[deep & ~stone] = PAVING[0]
    for level in range(4):
        pixels[stone & ~rim & (shade == level)] = PAVING[level + 1]
    # Rims: bright on the lit top-left edges, dark everywhere else.
    lit = stone & rim & (rel_x + rel_y < -0.25) & ~deep
    pixels[stone & rim] = PAVING[0]
    pixels[lit] = PAVING[3]
    del pixels

    # Moss creeping over the odd stone, and little flowers in the grassy seams.
    for cx in range(cols):
        for cy in range(rows):
            if not kept[cx, cy] or rng.random() > 0.2:
                continue
            sx, sy = int(seeds_x[cx, cy]), int(seeds_y[cx, cy]) - 3
            for _ in range(rng.randint(2, 4)):
                x, y = sx + rng.randint(-3, 3), sy + rng.randint(-1, 1)
                if 0 <= x < width and 0 <= y < height and stone[x, y]:
                    surf.set_at((x, y), rng.choice((GRASS[2], GRASS[3], LEAVES[1])))
    gaps = np.argwhere(allowed & ~stone & ~deep & (inside < COBBLE_FADE) & (seam < 1.4)
                       & kept[ox, oy] & (inside > 0))
    for index in rng.sample(range(len(gaps)), min(len(gaps), len(gaps) // 90)):
        x, y = gaps[index]
        petal = rng.choice((PETALS[0], PETALS[2], PETALS[2]))
        for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
            surf.set_at((x + dx, y + dy), petal)
        surf.set_at((x, y), PETALS[1])


def _wobble(px, py):
    """Smooth 0..1 noise that keeps the grout boundary from following the tile grid."""
    return (np.sin(px / 7 + np.sin(py / 11) * 2) + np.sin(py / 6 + np.sin(px / 13) * 2) + 2) / 4


BLADE_TILE = 64  # size of the repeating patch of grass blades


@cache
def _blade_patch():
    """A seamless patch of grass blades: colours, and where a blade is drawn."""
    rng = random.Random(5)
    colors = np.zeros((BLADE_TILE, BLADE_TILE, 3), np.uint8)
    drawn = np.zeros((BLADE_TILE, BLADE_TILE), bool)
    for _ in range(BLADE_TILE * BLADE_TILE // 7):
        x, y = rng.randrange(BLADE_TILE), rng.randrange(BLADE_TILE)
        light = rng.random() < 0.3
        lean = rng.choice((-1, 0, 0, 1))
        height = rng.randint(2, 4)
        for step in range(height):
            px, py = (x + (lean if step == height - 1 else 0)) % BLADE_TILE, (y - step) % BLADE_TILE
            if light:
                color = GRASS[3] if step == height - 1 else GRASS[2]
            else:
                color = GRASS[2] if step == height - 1 and rng.random() < 0.35 else GRASS[0]
            colors[px, py] = color
            drawn[px, py] = True
    return colors, drawn


def _grow_grass(surf):
    """Cover plain grass with blades, so the meadow has texture instead of a flat fill."""
    width, height = surf.get_size()
    colors, drawn = _blade_patch()
    reps = (width // BLADE_TILE + 1, height // BLADE_TILE + 1)
    colors = np.tile(colors, (*reps, 1))[:width, :height]
    drawn = np.tile(drawn, reps)[:width, :height]
    pixels = pygame.surfarray.pixels3d(surf)
    plain = np.all(pixels == GRASS[1], axis=2)
    pixels[plain & drawn] = colors[plain & drawn]
    del pixels


@cache
def build_map():
    surf = pygame.Surface((len(LEVEL[0]) * TILE, len(LEVEL) * TILE))
    for y, row in enumerate(LEVEL):
        for x, char in enumerate(row):
            paint_tile(surf, char, x, y)
    _fray_edges(surf)
    _lay_cobbles(surf)
    _grow_grass(surf)
    # Pillars and wells stand on the cobbles, so draw them again on top.
    for y, row in enumerate(LEVEL):
        for x, char in enumerate(row):
            if char in "co":
                _paint_prop(surf, char, x, y, random.Random(y * 1000 + x))
    _paint_lantern_glow(surf)
    return surf


def _clear_distance(x, y, limit=3):
    """How many tiles from here to the nearest open ground, up to `limit`."""
    for radius in range(1, limit + 1):
        for ny in range(max(0, y - radius), min(len(LEVEL), y + radius + 1)):
            for nx in range(max(0, x - radius), min(len(LEVEL[0]), x + radius + 1)):
                if LEVEL[ny][nx] != "T":
                    return radius
    return limit + 1


def find_cottages():
    """Each block of roof tiles with its front wall, as (x, y, width, rows, wall row)."""
    cottages = []
    for y, row in enumerate(LEVEL):
        for x, char in enumerate(row):
            above = LEVEL[y - 1][x] if y else ""
            beside = row[x - 1] if x else ""
            if char != "R" or above == "R" or beside == "R":
                continue
            width = 0
            while x + width < len(row) and row[x + width] == "R":
                width += 1
            bottom = y
            while bottom + 1 < len(LEVEL) and LEVEL[bottom + 1][x] == "R":
                bottom += 1
            wall = LEVEL[bottom + 1][x:x + width] if bottom + 1 < len(LEVEL) else ""
            if len(wall) == width and all(c in WALLS for c in wall):
                cottages.append((x, y, width, bottom + 2 - y, wall))
    return cottages


def chimney_spots():
    """Where smoke leaves each building with a chimney, in map pixels."""
    spots = []
    for index, cottage in enumerate(find_cottages()):
        (_, left, top, _), chimney = _building(*cottage, index=index)
        if chimney is not None:
            spots.append((left + chimney[0], top + chimney[1]))
    return spots


@cache
def _smoke_puff(radius, strength):
    """A soft round puff; `strength` 0 to 4 sets how solid it looks."""
    size = radius * 2 + 1
    puff = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(puff, (*STEEL[2], 70 + strength * 45), (radius, radius), radius)
    pygame.draw.circle(puff, (*WHITE, 60 + strength * 45), (radius - 1, radius - 1), max(1, radius - 1))
    return puff


def _cottage_prop(x, y, width, rows, wall, index=0):
    return _building(x, y, width, rows, wall, index)[0]


def _building(x, y, width, rows, wall, index=0):
    """A building prop for one block of roof tiles, and its chimney top within the image.

    Buildings take turns from VILLAGE in map order. Each one's art is an image in
    ui/assets/buildings, placed so its anchor pixel sits on the block's bottom-left corner.
    """
    art = load_building(VILLAGE[index % len(VILLAGE)])
    ground_y = (y + rows) * TILE
    left, top = x * TILE - art.anchor[0], ground_y - art.anchor[1]
    return (ground_y, left, top, art.image), art.chimney


@cache
def build_props():
    """Every standing prop as (ground y, left, top, image), nearest last."""
    images = prop_images()
    props = []
    for y, row in enumerate(LEVEL):
        for x, char in enumerate(row):
            rng = random.Random(y * 1000 + x + 7)
            if char in PLACED_PROPS:
                image = rng.choice(images[PLACED_PROPS[char]])
                ground_x, ground_y = x * TILE + 8, y * TILE + 14
                props.append((ground_y, ground_x - image.get_width() // 2, ground_y - image.get_height(), image))
            if char != "T":
                continue
            clear = _clear_distance(x, y)
            roll = rng.random()
            if clear == 1 and roll < 0.2:
                kind = "bush"
            elif clear == 1 and roll < 0.28:
                kind = "rock"
            elif clear == 1 and roll > 0.72:
                continue  # gaps along the treeline let the forest floor show
            elif clear == 1:
                kind = "small_pine"
            elif clear >= 3:
                kind = "deep_pine"
            else:
                kind = "pine"
            image = rng.choice(images[kind])
            ground_x = x * TILE + 8 + rng.randint(-5, 5)
            ground_y = y * TILE + 14 + rng.randint(-4, 2)
            props.append((ground_y, ground_x - image.get_width() // 2, ground_y - image.get_height(), image))
    props += [_cottage_prop(*cottage, index=i) for i, cottage in enumerate(find_cottages())]
    props.sort(key=lambda prop: prop[0])
    return props


def visible_props(camera, size):
    left, top = camera
    return [
        prop for prop in build_props()
        if prop[1] < left + size[0] and prop[1] + prop[3].get_width() > left
        and prop[2] < top + size[1] and prop[0] > top
    ]


def _build_vignette():
    shade = pygame.Surface(VIEW, pygame.SRCALPHA)
    for y in range(VIEW[1]):
        for x in range(VIEW[0]):
            edge = math.hypot((x - 160) / 170, (y - 90) / 105)
            if edge > 1.05 and (BAYER[y % 4][x % 4] + 0.5) / 16 < (edge - 1.05) * 1.2:
                shade.set_at((x, y), (*INK, 255))
    return shade


def _draw_ears(surf, left, right, top, inner):
    for ear in (left, right):
        pygame.draw.polygon(surf, FUR[0], [(ear - 2, top + 5), (ear, top), (ear + 2, top + 5)])
        if inner:
            surf.set_at((ear, top + 3), EAR)


def _draw_cat_side(surf, step, tail=0, nod=0, blink=False):
    """Body stretched out low on four legs. Diagonal pairs swing together."""
    near = (0, 1, 0, -1)[step % 4]
    bob = step % 2
    pygame.draw.line(surf, FUR[0], (3, 17 + bob), (1, 12 + bob), 2)
    pygame.draw.line(surf, FUR[0], (1, 12 + bob), (2 + tail, 8 + bob - near), 2)
    for x, swing in ((5, -near * 2), (14, near * 2)):      # far legs, a shade lighter
        pygame.draw.rect(surf, FUR[1], (x + swing, 20, 2, 4))
    pygame.draw.ellipse(surf, FUR[0], (2, 14 + bob, 15, 7))
    pygame.draw.line(surf, FUR[1], (5, 15 + bob), (12, 15 + bob))
    for x, swing in ((3, near * 2), (12, -near * 2)):      # near legs
        pygame.draw.rect(surf, FUR[0], (x + swing, 20, 2, 4))

    pygame.draw.rect(surf, CLOTH[1], (11, 14 + bob, 3, 5))
    pygame.draw.line(surf, CLOTH[2], (11, 14 + bob), (11, 18 + bob))
    pygame.draw.circle(surf, FUR[0], (15, 13 + bob + nod), 4)
    _draw_ears(surf, 13, 17, 6 + bob + nod, True)
    if not blink:
        surf.set_at((16, 12 + bob + nod), EMBER[2])
        surf.set_at((16, 13 + bob + nod), EMBER[1])
    surf.set_at((18, 14 + bob + nod), EAR)


def _draw_cat_front(surf, step, tail=0, nod=0, blink=False):
    """Walking towards the camera: a small head over slim shoulders and forepaws."""
    near = (0, 1, 0, -1)[step % 4]
    pygame.draw.line(surf, FUR[0], (13, 19), (16 + tail, 14 + near), 2)
    pygame.draw.ellipse(surf, FUR[0], (6, 15, 8, 8))
    for x, lift in ((6, max(0, near)), (12, max(0, -near))):
        pygame.draw.rect(surf, FUR[0], (x, 20, 2, 4 - lift))
        pygame.draw.line(surf, FUR[1], (x, 23 - lift), (x + 1, 23 - lift))
    pygame.draw.rect(surf, CLOTH[1], (7, 17, 6, 2))
    pygame.draw.line(surf, CLOTH[2], (7, 17), (12, 17))
    pygame.draw.circle(surf, FUR[0], (10, 13 + nod), 4)
    _draw_ears(surf, 7, 13, 7 + nod, True)
    if not blink:
        for x in (8, 11):
            surf.set_at((x, 13 + nod), EMBER[2])
            surf.set_at((x, 14 + nod), EMBER[1])
    surf.set_at((10, 15 + nod), EAR)


def _draw_cat_back(surf, step, tail=0, nod=0, blink=False):
    """Walking away: a slim rump and raised tail, the ears just peeking over."""
    near = (0, 1, 0, -1)[step % 4]
    pygame.draw.circle(surf, FUR[0], (10, 12 + nod), 3)
    _draw_ears(surf, 8, 12, 7 + nod, False)
    for x, lift in ((6, max(0, near)), (12, max(0, -near))):
        pygame.draw.rect(surf, FUR[0], (x, 20, 2, 4 - lift))
    pygame.draw.ellipse(surf, FUR[0], (5, 14, 10, 9))
    pygame.draw.line(surf, FUR[1], (7, 16), (9, 15))
    pygame.draw.line(surf, FUR[1], (11, 18), (15, 15 + near), 2)
    pygame.draw.line(surf, FUR[1], (15, 15 + near), (16 + tail, 10 + near), 2)


def _draw_cat_sit_side(surf, tail=0, nod=0, blink=False):
    """Haunches down, chest up, tail curled along the ground."""
    pygame.draw.line(surf, FUR[1], (7, 22), (2, 22), 2)
    pygame.draw.line(surf, FUR[1], (2, 22), (1 + tail, 16), 2)
    pygame.draw.ellipse(surf, FUR[0], (6, 15, 9, 9))
    pygame.draw.polygon(surf, FUR[0], [(9, 16), (11, 11 + nod), (15, 11 + nod), (15, 23), (9, 23)])
    pygame.draw.line(surf, FUR[1], (7, 18), (10, 14 + nod))
    pygame.draw.rect(surf, FUR[1], (13, 17, 2, 7))
    pygame.draw.rect(surf, CLOTH[1], (10, 12 + nod, 5, 2))
    pygame.draw.line(surf, CLOTH[2], (10, 12 + nod), (14, 12 + nod))
    pygame.draw.circle(surf, FUR[0], (14, 8 + nod), 4)
    _draw_ears(surf, 12, 16, 1 + nod, True)
    if not blink:
        surf.set_at((15, 7 + nod), EMBER[2])
        surf.set_at((15, 8 + nod), EMBER[1])
    surf.set_at((17, 9 + nod), EAR)


def _draw_cat_sit_front(surf, tail=0, nod=0, blink=False):
    """Forepaws together, haunches showing either side, tail round to the right."""
    pygame.draw.line(surf, FUR[0], (13, 22), (17, 22), 2)
    pygame.draw.line(surf, FUR[0], (17, 22), (17 + tail, 18), 2)
    pygame.draw.ellipse(surf, FUR[0], (4, 16, 12, 8))
    pygame.draw.polygon(surf, FUR[0], [(7, 11 + nod), (13, 11 + nod), (13, 23), (7, 23)])
    pygame.draw.line(surf, FUR[1], (10, 17), (10, 23))
    pygame.draw.rect(surf, CLOTH[1], (7, 13 + nod, 6, 2))
    pygame.draw.line(surf, CLOTH[2], (7, 13 + nod), (12, 13 + nod))
    pygame.draw.circle(surf, FUR[0], (10, 9 + nod), 4)
    _draw_ears(surf, 7, 13, 3 + nod, True)
    if not blink:
        for x in (8, 11):
            surf.set_at((x, 9 + nod), EMBER[2])
            surf.set_at((x, 10 + nod), EMBER[1])
    surf.set_at((10, 11 + nod), EAR)


def _draw_cat_sit_back(surf, tail=0, nod=0, blink=False):
    """A pear shape from behind, with the tail lying out to one side."""
    pygame.draw.polygon(surf, FUR[0], [(7, 11 + nod), (13, 11 + nod), (14, 18), (6, 18)])
    pygame.draw.ellipse(surf, FUR[0], (4, 15, 12, 9))
    pygame.draw.circle(surf, FUR[0], (10, 9 + nod), 3)
    _draw_ears(surf, 8, 12, 4 + nod, False)
    pygame.draw.rect(surf, CLOTH[1], (7, 12 + nod, 6, 1))
    pygame.draw.line(surf, FUR[1], (7, 17), (9, 15))
    pygame.draw.line(surf, FUR[1], (11, 22), (16, 22), 2)
    pygame.draw.line(surf, FUR[1], (16, 22), (17 + tail, 18), 2)


CAT_VIEWS = {"side": _draw_cat_side, "down": _draw_cat_front, "up": _draw_cat_back}
CAT_SIT_VIEWS = {"side": _draw_cat_sit_side, "down": _draw_cat_sit_front, "up": _draw_cat_sit_back}


def _outline(surf):
    silhouette = pygame.mask.from_surface(surf).to_surface(setcolor=(*INK, 255), unsetcolor=(0, 0, 0, 0))
    framed = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for offset in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        framed.blit(silhouette, offset)
    framed.blit(surf, (0, 0))
    return framed


def draw_walker(facing, step):
    """The cat on the map. Facing is 'down', 'up' or 'side' (side looks right)."""
    canvas, surf = figure_canvas(FIGURE_SIZE)
    CAT_VIEWS[facing](surf, step)
    return _outline(canvas)


def draw_idle(facing, frame):
    """The cat standing still: the tail swishes, the head nods, and it blinks once."""
    canvas, surf = figure_canvas(FIGURE_SIZE)
    CAT_VIEWS[facing](
        surf, 0,
        tail=IDLE_TAIL[frame], nod=IDLE_NOD[frame], blink=frame == IDLE_BLINK,
    )
    return _outline(canvas)


def draw_sit(facing, frame):
    """The cat sitting: a slow tail flick and an unhurried blink."""
    canvas, surf = figure_canvas(FIGURE_SIZE)
    CAT_SIT_VIEWS[facing](surf, tail=SIT_TAIL[frame], blink=frame == SIT_BLINK)
    return _outline(canvas)


def draw_sit_down(facing, frame):
    """The two steps from standing to sitting: hips dip, then settle."""
    canvas, surf = figure_canvas(FIGURE_SIZE)
    if frame == 0:
        CAT_VIEWS[facing](surf, 0, nod=1)
    else:
        CAT_SIT_VIEWS[facing](surf, nod=2)
    return _outline(canvas)


def draw_map_slime(body, squash, crown=False):
    """A slime on the map, bouncing between two heights."""
    canvas, surf = figure_canvas(FIGURE_SIZE)
    top = 12 + squash
    pygame.draw.ellipse(surf, body[0], (2 - squash, top, 16 + squash * 2, 25 - top + 6))
    pygame.draw.ellipse(surf, body[2], (3 - squash, top + 1, 14 + squash * 2, 25 - top + 4))
    pygame.draw.ellipse(surf, body[1], (6, top + 6, 8, 25 - top))
    pygame.draw.line(surf, body[3], (5, top + 3), (8, top + 1))
    pygame.draw.rect(surf, (0, 0, 0, 0), (0, 25, 20, 2))
    pygame.draw.rect(surf, INK, (7, top + 5, 2, 3))
    pygame.draw.rect(surf, INK, (12, top + 5, 2, 3))
    if crown:
        pygame.draw.polygon(surf, GOLD, [(6, top + 1), (6, top - 5), (8, top - 2), (10, top - 6), (12, top - 2), (14, top - 5), (14, top + 1)])
    return _outline(canvas)


class Overworld:
    def __init__(self):
        self.map = build_map()
        self.vignette = _build_vignette()
        self.size = self.map.get_size()
        tiles = find_tiles("S123B")
        self.start = tile_center(tiles["S"])
        self.bouncers = {key: Bouncer(tile_center(tiles[key]), ord(key)) for key in ENCOUNTERS}
        self.foes = {key: bouncer.pos for key, bouncer in self.bouncers.items()}
        self.gate_tiles = {
            key: [(x, y) for y, row in enumerate(LEVEL) for x, char in enumerate(row) if char == key]
            for key in GATES
        }
        self.sheep = [
            Sheep(tile_center((x, y)), y * 1000 + x)
            for y, row in enumerate(LEVEL) for x, char in enumerate(row) if char == "e"
        ]
        self.chimneys = chimney_spots()
        self.defeated = set()
        self.pos = list(self.start)
        self.checkpoint = self.start
        self.facing, self.flip = "up", False
        self.walked = 0.0
        self.idle_time = 0.0  # seconds since the cat last moved
        self.time = 0.0
        self.alert = None     # key of the foe that has spotted the player
        self.alert_time = 0.0
        self.message = "fight three slimes to enter the great hall..."

    def gate_open(self, gate):
        return GATES[gate] <= self.defeated

    @property
    def slimes_left(self):
        return len(GATES["H"] - self.defeated)

    def _solid(self, x, y):
        tx, ty = int(x // TILE), int(y // TILE)
        if not (0 <= ty < len(LEVEL) and 0 <= tx < len(LEVEL[0])):
            return True
        char = LEVEL[ty][tx]
        if char in GATES:
            return not self.gate_open(char)
        return char in SOLID

    def _blocked(self, x, y):
        return any(self._solid(x + dx, y + dy) for dx in (-5, 5) for dy in (-3, 3))

    def _move(self, dx, dy):
        if not self._blocked(self.pos[0] + dx, self.pos[1]):
            self.pos[0] += dx
        if not self._blocked(self.pos[0], self.pos[1] + dy):
            self.pos[1] += dy

    def update(self, dt, move):
        """Advance the world. Returns a foe's key once a fight should start."""
        self.time += dt
        self.idle_time = 0.0 if any(move) and self.alert is None else self.idle_time + dt
        for sheep in self.sheep:
            sheep.update(dt, self.pos, self._blocked)
        for key in self.foes:
            if key not in self.defeated and self.alert is None:
                self.bouncers[key].update(dt, self._blocked)
                self.foes[key] = self.bouncers[key].pos
        if self.alert is not None:
            self.alert_time += dt
            return self.alert if self.alert_time >= ALERT_TIME else None

        dx, dy = move
        if dx or dy:
            # Whole pixels on each axis, even on diagonals: normalising to ~0.7 px
            # per step makes the rounded position advance unevenly and judder.
            step = SPEED * dt
            self._move(dx * step, dy * step)
            self.walked += SPEED * dt
            if dy:
                self.facing = "up" if dy < 0 else "down"
            if dx:
                self.facing, self.flip = "side", dx < 0

        ahead = LEVEL[int((self.pos[1] - 8) // TILE)][int(self.pos[0] // TILE)]
        if ahead in GATES and not self.gate_open(ahead):
            self.message = f"THE GATE IS LOCKED. SLIMES LEFT: {self.slimes_left}"

        for key, spot in self.foes.items():
            if key not in self.defeated and math.dist(self.pos, spot) < TRIGGER_RADIUS:
                self.alert, self.alert_time = key, 0.0
                break
        return None

    def resolve_fight(self, key, won):
        self.alert = None
        if won:
            self.defeated.add(key)
            self.checkpoint = tuple(self.pos)
            left = self.slimes_left
            self.message = f"GOOD WORK! SLIMES LEFT: {left}" if left else "THE GREAT HALL IS OPEN!"
        else:
            self.pos = list(self.checkpoint)
            self.message = "PIPKIN SHAKES IT OFF."

    def _camera(self):
        x = min(max(self.pos[0] - VIEW[0] / 2, 0), self.size[0] - VIEW[0])
        y = min(max(self.pos[1] - VIEW[1] / 2, 0), self.size[1] - VIEW[1])
        return int(x), int(y)

    def _draw_gates(self, surf, camera):
        for gate, tiles in self.gate_tiles.items():
            if self.gate_open(gate):
                continue
            for tx, ty in tiles:
                x, y = tx * TILE - camera[0], ty * TILE - camera[1]
                pygame.draw.rect(surf, INK, (x, y, TILE, TILE))
                for i in range(1, TILE, 4):
                    pygame.draw.line(surf, STEEL[1], (x + i, y), (x + i, y + TILE))
                pygame.draw.line(surf, STEEL[2], (x, y + 5), (x + TILE, y + 5), 2)
            lock = (tiles[0][0] * TILE + TILE - camera[0], tiles[0][1] * TILE + 6 - camera[1])
            pygame.draw.circle(surf, DANGER[1] if int(self.time * 3) % 2 else EMBER[2], lock, 3)

    def _cat_frame(self):
        sitting = self.idle_time - SIT_DELAY
        if sitting >= 0:
            settle = load_sheet("cat_sit_down")
            step = int(sitting / settle.frame_time)
            if step < 2:
                return settle.frames[self.facing][step]
            sheet = load_sheet("cat_sit")
            return sheet.frames[self.facing][sheet.column_at(sitting)]
        if self.idle_time >= IDLE_DELAY:
            sheet = load_sheet("cat_idle")
            return sheet.frames[self.facing][sheet.column_at(self.idle_time)]
        frames = load_sheet("cat_walk").frames[self.facing]
        return frames[int(self.walked / 7) % len(frames)]

    def _draw_sheep(self, surf, sheep, camera):
        x, y = int(sheep.pos[0]) - camera[0], int(sheep.pos[1]) - camera[1]
        if not (-24 < x < VIEW[0] + 24 and -24 < y < VIEW[1] + 24):
            return
        shadow = pygame.Surface((18, 6), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (*INK, 120), shadow.get_rect())
        surf.blit(shadow, (x - 9, y - 2))
        image = sheep.frame()
        if sheep.flip and sheep.facing == "side":
            image = pygame.transform.flip(image, True, False)
        surf.blit(image, (x - 12 - FIGURE_PAD, y - FEET_Y - FIGURE_PAD - sheep.lift))

    def _draw_smoke(self, surf, camera):
        for index, (x, y) in enumerate(self.chimneys):
            for puff in range(SMOKE_PUFFS):
                k = (self.time / SMOKE_LIFE + puff / SMOKE_PUFFS + index * 0.13) % 1
                drift = math.sin(k * 5 + puff * 2 + index) * (1 + k * 5) + k * 7
                radius = 2 + int(k * 5)
                image = _smoke_puff(radius, int((1 - k) * 4))
                surf.blit(image, (x + drift - radius - camera[0], y - k * SMOKE_RISE - radius - camera[1]))

    def _draw_prop(self, surf, prop, camera):
        _, left, top, image = prop
        surf.blit(image, (left - camera[0], top - camera[1]))

    def _draw_figure(self, surf, image, center, camera, lift=0):
        x, y = int(center[0]) - camera[0], int(center[1]) - camera[1]
        shadow = pygame.Surface((16, 6), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (*INK, 150), shadow.get_rect())
        surf.blit(shadow, (x - 8, y))
        surf.blit(image, (x - 10 - FIGURE_PAD, y - 22 - FIGURE_PAD - lift))

    def draw(self, surf):
        camera = self._camera()
        surf.blit(self.map, (0, 0), (*camera, *VIEW))
        self._draw_gates(surf, camera)

        figures = [(self.pos[1], None, self.pos)]
        figures += [(spot[1], key, spot) for key, spot in self.foes.items() if key not in self.defeated]
        figures += [(sheep.pos[1], sheep, sheep.pos) for sheep in self.sheep]
        figures.sort(key=lambda item: item[0])
        props = visible_props(camera, VIEW)
        for ground_y, key, spot in figures:
            while props and props[0][0] <= ground_y:
                self._draw_prop(surf, props.pop(0), camera)
            if isinstance(key, Sheep):
                self._draw_sheep(surf, key, camera)
                continue
            lift = 0
            if key is None:
                image = self._cat_frame()
                if self.flip:
                    image = pygame.transform.flip(image, True, False)
            else:
                bouncer = self.bouncers[key]
                image = load_sheet(f"{ENCOUNTERS[key].sprite}_walk").frames["down"][bouncer.frame]
                lift = bouncer.lift
            self._draw_figure(surf, image, spot, camera, lift)
        for prop in props:
            self._draw_prop(surf, prop, camera)
        self._draw_smoke(surf, camera)

        if self.alert is not None:
            x, y = self.foes[self.alert]
            draw_text(surf, "!", (int(x) - camera[0] - 5, int(y) - camera[1] - 42), EMBER[3], scale=2, shadow=INK)

        surf.blit(self.vignette, (0, 0))
        draw_text(surf, self.message, (8, 168), BONE, shadow=INK)
        draw_text(surf, f"FOES {len(self.defeated)}/{len(ENCOUNTERS)}", (312 - 48, 6), BONE, shadow=INK)
