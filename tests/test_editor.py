import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from ui.editor import MARKERS, TILE_NAMES, UNIQUE, VIEW_HEIGHT, WINDOW, Editor
from ui.font import GLYPHS
from ui.overworld import LEVEL, LEVEL_FILE, TILE, build_map, find_tiles, level_problems


@pytest.fixture
def editor(tmp_path):
    original = list(LEVEL)
    path = tmp_path / "level.txt"
    yield Editor(path)
    LEVEL[:] = original
    build_map.cache_clear()


def screen_pos(editor, tile):
    return (tile[0] * TILE + 8 - editor.camera[0], tile[1] * TILE + 8 - editor.camera[1])


def click(editor, tile, button=1):
    pos = screen_pos(editor, tile)
    editor.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=button))
    editor.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=button))


def key(editor, code, mod=0):
    editor.handle_event(pygame.event.Event(pygame.KEYDOWN, key=code, mod=mod))


def nearby_grass(editor):
    start = find_tiles("S")["S"]
    return next(
        (x, y) for y in range(start[1] - 4, start[1] + 4) for x in range(start[0] - 6, start[0] + 6)
        if LEVEL[y][x] == "." and editor.tile_at(screen_pos(editor, (x, y)))
    )


def test_every_tile_in_the_game_is_on_the_palette():
    assert set("".join(LEVEL)) <= set(TILE_NAMES)
    assert set(UNIQUE) <= set(MARKERS) <= set(TILE_NAMES)
    assert set("".join(TILE_NAMES.values())) <= set(GLYPHS)


def test_palette_fits_the_window_above_the_edge(editor):
    assert editor.swatch_rect(len(TILE_NAMES) - 1).right <= WINDOW[0]
    assert editor.swatch_rect(0).top >= VIEW_HEIGHT


def test_painting_changes_the_tile_and_undo_restores_it(editor):
    tile = nearby_grass(editor)
    editor.selected = "w"
    click(editor, tile)
    assert LEVEL[tile[1]][tile[0]] == "w" and editor.unsaved
    key(editor, pygame.K_z, pygame.KMOD_CTRL)
    assert LEVEL[tile[1]][tile[0]] == "."


def test_a_fast_drag_leaves_no_gaps_and_undoes_as_one_stroke(editor):
    x, y = nearby_grass(editor)
    before = list(LEVEL)
    editor.selected = ","
    editor.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=screen_pos(editor, (x, y)), button=1))
    editor.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=screen_pos(editor, (x + 3, y)), rel=(0, 0), buttons=(1, 0, 0)))
    editor.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=screen_pos(editor, (x + 3, y)), button=1))
    assert LEVEL[y][x:x + 4] == ",,,,"
    key(editor, pygame.K_z, pygame.KMOD_CTRL)
    assert LEVEL == before


def test_right_click_picks_a_tile(editor):
    tile = nearby_grass(editor)
    editor.selected = "w"
    click(editor, tile, button=3)
    assert editor.selected == "."


def test_placing_a_unique_marker_moves_it(editor):
    old = find_tiles("S")["S"]
    tile = nearby_grass(editor)
    editor.selected = "S"
    click(editor, tile)
    assert "".join(LEVEL).count("S") == 1
    assert find_tiles("S")["S"] == tile and LEVEL[old[1]][old[0]] != "S"


def test_markers_cannot_be_painted_over(editor):
    tile = find_tiles("S")["S"]
    editor.selected = "T"
    click(editor, tile)
    assert LEVEL[tile[1]][tile[0]] == "S"


def test_save_writes_a_level_that_loads_back(editor):
    tile = nearby_grass(editor)
    editor.selected = "t"
    click(editor, tile)
    assert editor.save() and not editor.unsaved
    assert editor.path.read_text().split() == LEVEL


def test_save_refuses_a_level_that_cannot_be_finished(editor):
    x, y = find_tiles("H")["H"]
    for gate_x in (x - 1, x):
        LEVEL[y] = LEVEL[y][:gate_x] + "#" + LEVEL[y][gate_x + 1:]
    assert level_problems()
    assert not editor.save()
    assert "NOT SAVED" in editor.message and not editor.path.exists()


def test_quitting_with_unsaved_changes_asks_first(editor):
    editor.unsaved = True
    key(editor, pygame.K_ESCAPE)
    assert editor.running
    key(editor, pygame.K_ESCAPE)
    assert not editor.running


def test_tests_leave_the_real_level_alone(editor):
    assert editor.path != LEVEL_FILE
