import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

import ui.buildings as buildings
from ui.overworld import TILE, VILLAGE, _building, chimney_spots, find_cottages


@pytest.mark.parametrize("kind", VILLAGE)
def test_every_building_type_has_art_and_sensible_settings(kind):
    art = buildings.load_building(kind)
    width, height = art.image.get_size()
    assert 0 <= art.anchor[0] < width and 0 < art.anchor[1] <= height
    if art.chimney is not None:
        assert 0 <= art.chimney[0] < width and 0 <= art.chimney[1] < height


def test_a_building_stands_on_its_tiles_by_its_anchor():
    x, y, width, rows, wall = find_cottages()[0]
    (ground_y, left, top, image), _ = _building(x, y, width, rows, wall, index=0)
    art = buildings.load_building(VILLAGE[0])
    assert ground_y == (y + rows) * TILE
    assert (left + art.anchor[0], top + art.anchor[1]) == (x * TILE, ground_y)


def test_smoke_comes_from_each_chimney():
    spots = chimney_spots()
    kinds = [VILLAGE[i % len(VILLAGE)] for i in range(len(find_cottages()))]
    with_chimneys = [kind for kind in kinds if buildings.load_building(kind).chimney is not None]
    assert len(spots) == len(with_chimneys)


@pytest.fixture
def art_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(buildings, "BUILDINGS_DIR", tmp_path)
    buildings.load_building.cache_clear()
    yield tmp_path
    buildings.load_building.cache_clear()


def test_new_art_is_picked_up_and_can_be_scaled(art_folder):
    pygame.image.save(pygame.Surface((30, 20), pygame.SRCALPHA), art_folder / "tower.png")
    (art_folder / "tower.json").write_text(json.dumps({"anchor": [3, 20], "chimney": None, "scale": 2}))
    art = buildings.load_building("tower")
    assert art.image.get_size() == (60, 40) and art.anchor == (6, 40) and art.chimney is None


def test_art_without_settings_stands_on_its_bottom_left_corner(art_folder):
    pygame.image.save(pygame.Surface((30, 20), pygame.SRCALPHA), art_folder / "hut.png")
    art = buildings.load_building("hut")
    assert art.anchor == (0, 20) and art.chimney is None


def test_missing_art_says_which_file_to_add(art_folder):
    with pytest.raises(FileNotFoundError, match="castle.png"):
        buildings.load_building("castle")
