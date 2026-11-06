"""Render the code-drawn characters to sprite sheets: ``python -m ui.bake_sprites``.

This overwrites every sheet in ``ui/assets``, including any hand edits, so commit
those first and only re-bake the art you mean to replace.
"""
import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from ui.characters import (
    CAT_POSES, CAT_SWAY, SLIME_POSES, SLIME_SWAY, draw_cat,
)
from ui.encounters import ENCOUNTERS
from ui.overworld import (
    IDLE_TAIL, SIT_TAIL, draw_idle, draw_map_slime, draw_sit, draw_sit_down, draw_walker,
)
from ui.palette import SHEEP_FACES
from ui.sheep import FRAMES, VIEWS, draw_sheep
from ui.sprites import save_sheet

SWAY_FRAMES = 8
WALK_FRAMES = 4
IDLE_FRAME_TIME = 0.24
SIT_DOWN_FRAME_TIME = 0.14
SIT_FRAME_TIME = 0.36


def bake_fighter(name, draw, poses, sway):
    period = 2 * math.pi / sway
    rows, tips = {}, {}
    for pose_name, pose in poses.items():
        drawn = [draw(pose, period * i / SWAY_FRAMES) for i in range(SWAY_FRAMES)]
        rows[pose_name] = [image for image, _ in drawn]
        tips[pose_name] = [[round(tip[0], 1), round(tip[1], 1)] for _, tip in drawn]
    save_sheet(name, rows, period / SWAY_FRAMES, tips)


def main():
    pygame.init()
    bake_fighter("cat", draw_cat, CAT_POSES, CAT_SWAY)
    save_sheet("cat_walk", {
        facing: [draw_walker(facing, step) for step in range(WALK_FRAMES)]
        for facing in ("down", "up", "side")
    })
    save_sheet("cat_idle", {
        facing: [draw_idle(facing, frame) for frame in range(len(IDLE_TAIL))]
        for facing in ("down", "up", "side")
    }, IDLE_FRAME_TIME)
    save_sheet("cat_sit_down", {
        facing: [draw_sit_down(facing, frame) for frame in range(2)]
        for facing in ("down", "up", "side")
    }, SIT_DOWN_FRAME_TIME)
    save_sheet("cat_sit", {
        facing: [draw_sit(facing, frame) for frame in range(len(SIT_TAIL))]
        for facing in ("down", "up", "side")
    }, SIT_FRAME_TIME)
    for name, face in SHEEP_FACES.items():
        save_sheet(f"sheep_{name}", {
            view: [draw_sheep(view, frame, face) for frame in range(FRAMES)] for view in VIEWS
        })
    for foe in ENCOUNTERS.values():
        bake_fighter(foe.sprite, foe.draw, SLIME_POSES, SLIME_SWAY)
        save_sheet(f"{foe.sprite}_walk", {
            "down": [draw_map_slime(foe.body, squash, foe.is_boss) for squash in (0, 1)],
        })
    pygame.quit()


if __name__ == "__main__":
    main()
