import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from battle.engine import Move, Outcome, legal_moves
from ui.arena import HEIGHT, WIDTH
from ui.battle_screen import BattleScreen
from ui.characters import CANVAS, CAT_POSES, SLIME_POSES, draw_cat, draw_slime
from ui.encounters import ENCOUNTERS
from ui.effects import SHOTS
from ui.font import GLYPHS, wrap
from ui.battle_screen import HEAL_POTIONS, PIPKIN_LINES
from ui.hud import DETAIL_CHARS, MOVE_DETAILS, MOVE_NAMES, command_rect
from ui.sprites import ASSETS, load_sheet

STEP = 1 / 30


def run_until_ready(screen, surf):
    while screen.script is not None:
        screen.update(STEP)
        screen.draw(surf)


def play_fight(moves, seed):
    screen = BattleScreen(seed=seed)
    surf = pygame.Surface((WIDTH, HEIGHT))
    turn = 0
    while screen.outcome is None:
        legal = legal_moves(screen.player.battler)
        move = moves[turn % len(moves)]
        screen.choose(move if move in legal else Move.ATTACK)
        run_until_ready(screen, surf)
        turn += 1
    return screen


@pytest.mark.parametrize("seed", range(5))
def test_full_fight_plays_to_an_outcome(seed):
    screen = play_fight(list(Move), seed)
    assert isinstance(screen.outcome, Outcome)


@pytest.mark.parametrize("seed", range(5))
def test_displayed_hp_matches_the_engine_after_each_fight(seed):
    screen = play_fight([Move.FIREBOLT, Move.HEAL, Move.HONE, Move.ATTACK, Move.DEFEND], seed)
    assert screen.player.target_hp == screen.player.battler.hp
    assert screen.foe.target_hp == screen.foe.battler.hp


def finish_turn(screen, surf):
    while screen.script is not None:
        screen.update(STEP)
        screen.draw(surf)


def test_pipkin_runs_out_of_heals_but_keeps_full_mana():
    screen = BattleScreen(seed=0)
    surf = pygame.Surface((WIDTH, HEIGHT))
    for _ in range(HEAL_POTIONS):
        screen.choose(Move.HEAL)
        finish_turn(screen, surf)
    assert screen.player.battler.heal_potions == 0 and screen.player.battler.mana == 30

    screen.choose(Move.HEAL)
    assert screen.turn == HEAL_POTIONS and screen.script is None


def test_pipkin_swipes_while_foes_keep_their_own_words():
    screen = BattleScreen(seed=0)
    surf = pygame.Surface((WIDTH, HEIGHT))
    screen.choose(Move.FIREBOLT)
    finish_turn(screen, surf)
    assert any("PIPKIN swipes" in line for line in screen.log)


@pytest.mark.parametrize("key", list(ENCOUNTERS))
def test_every_slime_has_its_own_lines_that_fit_the_log(key):
    foe = ENCOUNTERS[key]
    assert set(foe.lines) == set(Move)
    for move, line in foe.lines.items():
        assert len(foe.name) + 1 + len(line) <= DETAIL_CHARS
        assert set(line.upper()) <= set(GLYPHS)
        others = [other.lines[move] for other in ENCOUNTERS.values() if other is not foe]
        assert line not in others and line != PIPKIN_LINES[move]


def test_pipkins_lines_fit_the_log():
    assert set(PIPKIN_LINES) == set(Move)
    assert all(len("PIPKIN ") + len(line) <= DETAIL_CHARS for line in PIPKIN_LINES.values())


def test_every_slime_has_a_shot_of_its_own():
    used = [foe.shot for foe in ENCOUNTERS.values()]
    assert sorted(used) == sorted(SHOTS)


@pytest.mark.parametrize("key", list(ENCOUNTERS))
def test_a_slime_fires_its_shot_in_its_own_colour_with_its_own_line(key):
    foe = ENCOUNTERS[key]
    screen = BattleScreen(opponent=lambda *_: Move.FIREBOLT, seed=0, encounter=foe)
    surf = pygame.Surface((WIDTH, HEIGHT))
    screen.choose(Move.DEFEND)
    shots = []
    while screen.script is not None:
        screen.update(STEP)
        screen.draw(surf)
        if screen.effects.bolt:
            shots.append(screen.effects.bolt)
    assert shots and all(shot[2] == foe.body[1:] and shot[4] is SHOTS[foe.shot] for shot in shots)
    assert f"{foe.name} {foe.lines[Move.FIREBOLT]}" in screen.log


def test_ko_ends_the_fight_with_no_second_chance():
    screen = BattleScreen(opponent=lambda *_: Move.FIREBOLT, seed=0)
    surf = pygame.Surface((WIDTH, HEIGHT))
    screen.player.battler.hp = screen.player.target_hp = 1
    screen.choose(Move.DEFEND)
    finish_turn(screen, surf)
    assert screen.outcome == Outcome.LOSS and screen.player.pose_to == "ko"


def test_command_labels_fit_their_buttons():
    for move in Move:
        rect = command_rect(move)
        assert 6 + len(MOVE_NAMES[move]) * 6 + 6 <= rect.width


def test_illegal_move_is_ignored():
    screen = BattleScreen(seed=0)
    screen.player.battler.mana = 0
    screen.choose(Move.FIREBOLT)
    assert screen.turn == 0 and screen.script is None


def test_input_is_ignored_while_a_turn_plays():
    screen = BattleScreen(seed=0)
    screen.choose(Move.ATTACK)
    screen.choose(Move.ATTACK)
    assert screen.turn == 1


@pytest.mark.parametrize("draw, poses", [(draw_cat, CAT_POSES), (draw_slime, SLIME_POSES), (ENCOUNTERS["B"].draw, SLIME_POSES)])
def test_poses_stay_inside_the_canvas(draw, poses):
    for pose in poses.values():
        image, _ = draw(pose, 1.0)
        assert image.get_size() == CANVAS
        bounds = image.get_bounding_rect()
        assert bounds.top > 0 and bounds.left > 0 and bounds.right < CANVAS[0]


@pytest.mark.parametrize("name", ["cat", *(foe.sprite for foe in ENCOUNTERS.values())])
def test_battle_sheets_have_every_pose_at_canvas_size(name):
    sheet = load_sheet(name)
    assert set(sheet.frames) == set(CAT_POSES) == set(sheet.tips)
    for pose, frames in sheet.frames.items():
        assert len(frames) == len(sheet.tips[pose])
        assert all(frame.get_size() == CANVAS and frame.get_bounding_rect().width for frame in frames)


@pytest.mark.parametrize("name, rows", [
    ("cat_walk", {"down", "up", "side"}),
    *((f"{foe.sprite}_walk", {"down"}) for foe in ENCOUNTERS.values()),
])
def test_walk_sheets_have_every_facing(name, rows):
    assert set(load_sheet(name).frames) == rows


@pytest.mark.parametrize("path", sorted(ASSETS.glob("*.png")), ids=lambda path: path.stem)
def test_no_sprite_touches_the_edge_of_its_frame(path):
    for row, frames in load_sheet(path.stem).frames.items():
        for column, frame in enumerate(frames):
            bounds = frame.get_bounding_rect()
            width, height = frame.get_size()
            inside = bounds.left > 0 and bounds.top > 0 and bounds.right < width and bounds.bottom < height
            assert inside, f"{path.stem} {row} {column}: {bounds} in {width}x{height}"


def test_every_move_has_a_description_and_a_distinct_button():
    assert set(MOVE_DETAILS) == set(MOVE_NAMES) == set(Move)
    rects = [command_rect(move) for move in Move]
    assert all(not a.colliderect(b) for i, a in enumerate(rects) for b in rects[i + 1:])


def test_font_covers_all_move_text():
    text = "".join(MOVE_DETAILS.values()).upper()
    assert set(text) <= set(GLYPHS)
    assert all(len(line) <= 25 for line in wrap(text, 25))
