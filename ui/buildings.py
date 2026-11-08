"""Village buildings, loaded from images in ui/assets/buildings/.

Each building type (see VILLAGE in ui.overworld) has two files:

  <kind>.png    the building, with a transparent background
  <kind>.json   where it sits and smokes:
      "anchor":  [x, y] the pixel in the image that sits on the bottom-left corner
                 of the building's tiles on the map (the left end of the front wall,
                 where it meets the ground)
      "chimney": [x, y] where smoke rises, or null for no smoke
      "scale":   optional whole number to enlarge art drawn at a smaller pixel size

Only the building's map tiles are solid, so an image can be wider or taller than
its footprint. Paint the footprint in the editor to match the art.
"""
from dataclasses import dataclass
from functools import cache
import json

import pygame

from ui.sprites import ASSETS

BUILDINGS_DIR = ASSETS / "buildings"


@dataclass(frozen=True)
class BuildingArt:
    image: pygame.Surface
    anchor: tuple        # pixel of the image on the footprint's bottom-left corner
    chimney: tuple | None


@cache
def load_building(kind):
    image_path, meta_path = BUILDINGS_DIR / f"{kind}.png", BUILDINGS_DIR / f"{kind}.json"
    if not image_path.exists():
        raise FileNotFoundError(f"no art for the {kind!r} building: add {image_path} and {meta_path.name}")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    image = pygame.image.load(image_path)
    scale = int(meta.get("scale", 1))
    if scale != 1:
        image = pygame.transform.scale(image, (image.get_width() * scale, image.get_height() * scale))
    anchor = tuple(v * scale for v in meta.get("anchor", (0, image.get_height() // scale)))
    chimney = meta.get("chimney")
    return BuildingArt(image, anchor, tuple(v * scale for v in chimney) if chimney else None)
