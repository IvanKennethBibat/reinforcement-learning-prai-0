"""Sprite sheets: the art the game actually shows.

Each sheet is a PNG in ``ui/assets`` plus a JSON file of the same name. Rows are
poses or facings, and columns are the frames of that row's loop. Edit a PNG in
any pixel editor and the game picks it up, as long as the grid stays the same.
"""
from dataclasses import dataclass
from functools import cache
import json
from pathlib import Path

import pygame

ASSETS = Path(__file__).parent / "assets"


@dataclass(frozen=True)
class Sheet:
    frames: dict       # row name -> list of surfaces, one per column
    tips: dict         # row name -> list of (x, y) weapon tips, empty for walkers
    frame_time: float  # seconds each column stays on screen

    def column_at(self, time):
        columns = len(next(iter(self.frames.values())))
        return int(time / self.frame_time) % columns


def save_sheet(name, rows, frame_time=0.0, tips=None):
    """Write `rows`, a dict of row name -> list of equally sized surfaces."""
    width, height = next(iter(rows.values()))[0].get_size()
    columns = len(next(iter(rows.values())))
    sheet = pygame.Surface((width * columns, height * len(rows)), pygame.SRCALPHA)
    for y, frames in enumerate(rows.values()):
        for x, frame in enumerate(frames):
            sheet.blit(frame, (x * width, y * height))

    ASSETS.mkdir(exist_ok=True)
    pygame.image.save(sheet, ASSETS / f"{name}.png")
    meta = {
        "frame": [width, height],
        "rows": list(rows),
        "columns": columns,
        "frame_time": frame_time,
        "tips": tips or {},
    }
    (ASSETS / f"{name}.json").write_text(json.dumps(meta, indent=1) + "\n")


@cache
def load_sheet(name):
    meta = json.loads((ASSETS / f"{name}.json").read_text())
    image = pygame.image.load(ASSETS / f"{name}.png")
    width, height = meta["frame"]
    frames = {
        row: [image.subsurface((x * width, y * height, width, height)) for x in range(meta["columns"])]
        for y, row in enumerate(meta["rows"])
    }
    tips = {row: [tuple(tip) for tip in points] for row, points in meta["tips"].items()}
    return Sheet(frames, tips, meta["frame_time"])
