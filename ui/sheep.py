"""Passive sheep: they graze, wander and hop, and bounce away from the cat.

The art is drawn here and baked by ``ui.bake_sprites``. Each ``Sheep`` only picks
which frame to show, so the game itself just reads the sheets.
"""
import math
import random

import pygame

from ui.palette import INK, MOSS_INK, SHEEP_FACES, WOOL
from ui.props import _outline, figure_canvas
from ui.sprites import load_sheet

SIZE = (24, 24)
FEET_Y = 21
VIEWS = ("down", "up", "side", "graze_down", "graze_side")
FRAMES = 4

WALK_SPEED = 15
HOP_SPEED = 34
HOP_TIME = 0.42
HOP_HEIGHT = 7
LEASH = 80           # how far a sheep strays from where it started
SCARE_RADIUS = 26
TURN_TIME = 0.5      # how long it waits before spooking again


def _wool(surf, puffs):
    for x, y, r in puffs:
        pygame.draw.circle(surf, WOOL[0], (x, y + 1), r)
    for x, y, r in puffs:
        pygame.draw.circle(surf, WOOL[1], (x, y), r)
    for x, y, r in puffs:
        pygame.draw.circle(surf, WOOL[2], (x - 1, y - 1), max(1, r - 2))


def _side(surf, frame, face, grazing):
    skin, shade = face
    step = (0, 1, 0, -1)[frame]
    bob = 0 if grazing else frame % 2
    for x, swing in ((6, step), (9, -step), (14, step), (17, -step)):
        pygame.draw.rect(surf, shade, (x + (0 if grazing else swing), 18, 2, 4))
    _wool(surf, [(7, 12 + bob, 5), (11, 10 + bob, 6), (15, 12 + bob, 5), (10, 14 + bob, 4), (14, 14 + bob, 4)])
    head_y = 17 + (frame % 2) if grazing else 9 + bob
    pygame.draw.ellipse(surf, skin, (16, head_y - 3, 7, 6))
    pygame.draw.rect(surf, shade, (16, head_y - 4, 2, 2))  # ear
    surf.set_at((20, head_y - 1), INK)
    if grazing:
        surf.set_at((22, head_y + 2), shade)


def _front(surf, frame, face, grazing):
    skin, shade = face
    step = (0, 1, 0, -1)[frame]
    for x, lift in ((8, max(0, step)), (14, max(0, -step))):
        pygame.draw.rect(surf, shade, (x, 18, 2, 4 - (0 if grazing else lift)))
    _wool(surf, [(12, 12, 7), (7, 10, 4), (17, 10, 4), (7, 14, 4), (17, 14, 4), (12, 7, 4)])
    top = 13 + (frame % 2) if grazing else 8
    pygame.draw.rect(surf, shade, (6, top + 1, 3, 2))
    pygame.draw.rect(surf, shade, (15, top + 1, 3, 2))
    pygame.draw.ellipse(surf, skin, (9, top, 6, 8))
    if not grazing:
        surf.set_at((10, top + 3), INK)
        surf.set_at((13, top + 3), INK)
    surf.set_at((11, top + 6), shade)
    surf.set_at((12, top + 6), shade)


def _back(surf, frame, face):
    skin, shade = face
    step = (0, 1, 0, -1)[frame]
    for x, lift in ((8, max(0, step)), (14, max(0, -step))):
        pygame.draw.rect(surf, shade, (x, 18, 2, 4 - lift))
    pygame.draw.rect(surf, shade, (6, 7, 2, 2))
    pygame.draw.rect(surf, shade, (16, 7, 2, 2))
    _wool(surf, [(12, 12, 7), (7, 10, 4), (17, 10, 4), (7, 14, 4), (17, 14, 4), (12, 7, 4)])
    pygame.draw.circle(surf, WOOL[2], (12, 16), 2)


def draw_sheep(view, frame, face):
    canvas, surf = figure_canvas(SIZE)
    if view == "up":
        _back(surf, frame, face)
    elif view.endswith("side"):
        _side(surf, frame, face, view.startswith("graze"))
    else:
        _front(surf, frame, face, view.startswith("graze"))
    return _outline(canvas, MOSS_INK)


class Sheep:
    def __init__(self, spot, seed):
        self.rng = random.Random(seed)
        self.pos = list(spot)
        self.home = spot
        self.sheet_name = f"sheep_{self.rng.choice(list(SHEEP_FACES))}"
        self.facing, self.flip = self.rng.choice(("down", "side")), self.rng.random() < 0.5
        self.state = "graze"
        self.heading = (0.0, 0.0)
        self.timer = self.rng.uniform(0.5, 3.0)
        self.hops_left = 0
        self.hop_time = 0.0
        self.walked = 0.0
        self.time = self.rng.uniform(0, 5)
        self.calm = 0.0  # seconds until it can be spooked again

    @property
    def lift(self):
        if self.state != "hop":
            return 0
        return round(math.sin(self.hop_time / HOP_TIME * math.pi) * HOP_HEIGHT)

    def _face(self, dx, dy):
        if abs(dx) >= abs(dy):
            self.facing, self.flip = "side", dx < 0
        else:
            self.facing = "up" if dy < 0 else "down"

    def _set_heading(self, angle):
        self.heading = (math.cos(angle), math.sin(angle))
        self._face(*self.heading)

    def _pick_heading(self):
        away = math.dist(self.pos, self.home)
        if away > LEASH:
            self._set_heading(math.atan2(self.home[1] - self.pos[1], self.home[0] - self.pos[0]))
        else:
            self._set_heading(self.rng.uniform(0, math.tau))

    def _graze(self):
        self.state = "graze"
        self.timer = self.rng.uniform(2.0, 5.0)
        if self.facing == "up":
            self.facing = "down"

    def _start_hops(self, count):
        self.state = "hop"
        self.hops_left = count
        self.hop_time = 0.0

    def _next_state(self):
        roll = self.rng.random()
        if roll < 0.45:
            self._graze()
        elif roll < 0.8:
            self.state = "walk"
            self.timer = self.rng.uniform(1.0, 3.0)
            self._pick_heading()
        else:
            self._pick_heading()
            self._start_hops(self.rng.randint(1, 3))

    def _move(self, speed, dt, blocked):
        x = self.pos[0] + self.heading[0] * speed * dt
        y = self.pos[1] + self.heading[1] * speed * dt
        if blocked(x, y):
            return False
        self.pos = [x, y]
        return True

    def update(self, dt, cat, blocked):
        self.time += dt
        self.calm = max(0.0, self.calm - dt)
        if self.calm == 0 and self.state != "hop" and math.dist(self.pos, cat) < SCARE_RADIUS:
            self._set_heading(math.atan2(self.pos[1] - cat[1], self.pos[0] - cat[0]))
            self._start_hops(2)
            self.calm = TURN_TIME

        if self.state == "hop":
            self.hop_time += dt
            self._move(HOP_SPEED, dt, blocked)
            if self.hop_time >= HOP_TIME:
                self.hop_time = 0.0
                self.hops_left -= 1
                if self.hops_left <= 0:
                    self._graze()
        elif self.state == "walk":
            self.timer -= dt
            self.walked += WALK_SPEED * dt
            if not self._move(WALK_SPEED, dt, blocked):
                self._graze()
            elif self.timer <= 0:
                self._next_state()
        else:
            self.timer -= dt
            if self.timer <= 0:
                self._next_state()

    def frame(self):
        sheet = load_sheet(self.sheet_name)
        if self.state == "graze":
            return sheet.frames[f"graze_{self.facing}"][int(self.time * 3) % FRAMES]
        if self.state == "hop":
            return sheet.frames[self.facing][1]
        return sheet.frames[self.facing][int(self.walked / 4) % FRAMES]
