import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import math

import pygame
import pytest

from battle.engine import Outcome
from ui.arena import HEIGHT, WIDTH
from ui.bouncer import LEASH, REST, SQUASHED, STRETCHED
from ui.encounters import ENCOUNTERS
from ui.game import Game
from ui.sprites import load_sheet
from ui.overworld import (
    GATES, LEVEL, SIT_DELAY, TILE, TRIGGER_RADIUS, VIEW, _cottage_prop, chimney_spots, find_cottages,
)
from ui.overworld import Overworld, find_tiles, level_problems, reachable

STEP = 1 / 30


def test_level_is_rectangular():
    assert len({len(row) for row in LEVEL}) == 1


def test_shipped_level_has_no_problems():
    assert level_problems() == []


def test_slimes_are_open_from_the_start_and_only_the_boss_is_locked_away():
    spots = find_tiles("123B")
    open_tiles = reachable("")
    assert all(spots[key] in open_tiles for key in "123")
    assert spots["B"] not in open_tiles
    assert spots["B"] in reachable("H")


@pytest.mark.parametrize("road", [
    [(21, 26), (21, 27)],  # west road out of the hamlet
    [(44, 25), (44, 26)],  # east bridge
    [(31, 35), (32, 35)],  # south road
])
def test_every_slime_survives_any_one_road_being_cut(road):
    # Back paths mean the map loops, so no single road is the only way in.
    spots = find_tiles("123")
    open_tiles = reachable("", blocked=road)
    assert all(spot in open_tiles for spot in spots.values())


def test_gate_keys_name_real_foes():
    assert set().union(*GATES.values()) <= set(ENCOUNTERS)


def test_names_fit_the_status_plate():
    assert all(len(foe.name) <= 11 for foe in ENCOUNTERS.values())


def test_walls_stop_the_player():
    world = Overworld()
    for _ in range(600):
        world.update(STEP, (-1, 0))
    assert world.pos[0] > TILE


def test_closed_gate_stops_the_player_until_opened():
    world = Overworld()
    world.foes = {}
    for _ in range(600):
        world.update(STEP, (0, -1))
    gate_y = find_tiles("H")["H"][1]
    assert world.pos[1] > (gate_y + 1) * TILE
    assert "LOCKED" in world.message

    world.defeated.update(GATES["H"])
    for _ in range(300):
        world.update(STEP, (0, -1))
    assert world.pos[1] < gate_y * TILE


def test_the_cat_idles_only_after_standing_still():
    world = Overworld()
    world.foes = {}
    walking = load_sheet("cat_walk").frames[world.facing]
    world.update(STEP, (0, -1))
    assert world.idle_time == 0 and any(world._cat_frame() is frame for frame in walking)

    for _ in range(30):
        world.update(STEP, (0, 0))
    idling = load_sheet("cat_idle").frames[world.facing]
    assert any(world._cat_frame() is frame for frame in idling)

    world.update(STEP, (1, 0))
    assert world.idle_time == 0


def test_the_cat_sits_after_a_few_seconds_and_stands_when_moved():
    world = Overworld()
    world.foes = {}
    for _ in range(int(SIT_DELAY / STEP) + 20):
        world.update(STEP, (0, 0))
    sitting = load_sheet("cat_sit").frames[world.facing]
    assert any(world._cat_frame() is frame for frame in sitting)

    world.update(STEP, (0, -1))
    walking = load_sheet("cat_walk").frames[world.facing]
    assert any(world._cat_frame() is frame for frame in walking)


@pytest.mark.parametrize("facing", ["down", "up", "side"])
def test_idle_loop_actually_moves(facing):
    frames = load_sheet("cat_idle").frames[facing]
    pictures = {pygame.image.tobytes(frame, "RGBA") for frame in frames}
    assert len(frames) == 8 and len(pictures) >= 4


def test_the_map_has_a_flock_that_stands_on_open_ground():
    world = Overworld()
    assert len(world.sheep) >= 6
    assert not any(world._blocked(*sheep.pos) for sheep in world.sheep)


def test_sheep_graze_walk_and_hop_but_never_enter_anything_solid():
    world = Overworld()
    world.pos = [-999.0, -999.0]
    seen = set()
    for _ in range(int(120 / STEP)):
        for sheep in world.sheep:
            sheep.update(STEP, world.pos, world._blocked)
            seen.add(sheep.state)
            assert not world._blocked(*sheep.pos)
            assert sheep.frame() is not None
    assert seen == {"graze", "walk", "hop"}


def test_sheep_stay_near_home():
    world = Overworld()
    world.pos = [-999.0, -999.0]
    for _ in range(int(120 / STEP)):
        for sheep in world.sheep:
            sheep.update(STEP, world.pos, world._blocked)
    assert all(math.dist(sheep.pos, sheep.home) < 200 for sheep in world.sheep)


def test_a_sheep_hops_away_from_the_cat():
    world = Overworld()
    sheep = world.sheep[0]
    cat = [sheep.pos[0] - 10, sheep.pos[1]]
    sheep.update(STEP, cat, lambda x, y: False)
    assert sheep.state == "hop" and sheep.heading[0] > 0
    start = sheep.pos[0]
    for _ in range(6):
        sheep.update(STEP, [-999.0, -999.0], lambda x, y: False)
    assert sheep.pos[0] > start and sheep.lift > 0


def test_sheep_never_start_a_fight():
    world = Overworld()
    world.foes = {}
    world.pos = list(world.sheep[0].pos)
    for _ in range(90):
        assert world.update(STEP, (0, 0)) is None
    assert world.alert is None


def test_every_block_of_roof_tiles_becomes_a_cottage():
    cottages = find_cottages()
    assert len(cottages) == 4
    for x, y, width, rows, wall in cottages:
        assert rows == 3 and "D" in wall and len(wall) == width


def test_cottages_get_a_different_look_and_stay_solid():
    pictures = {
        pygame.image.tobytes(_cottage_prop(*c, index=i)[3], "RGBA") for i, c in enumerate(find_cottages())
    }
    assert len(pictures) == len(find_cottages())
    world = Overworld()
    x, y, width, rows, _ = find_cottages()[0]
    assert world._solid((x + 1) * TILE, (y + 1) * TILE)


def test_every_cottage_has_a_garden_and_the_level_still_works():
    text = "".join(LEVEL)
    assert all(tile in text for tile in "pgv")
    for x, y, width, rows, wall in find_cottages():
        below = LEVEL[y + rows][x:x + width]
        assert "v" in below, "flowers along the front of each cottage"
        door = x + wall.index("D")
        assert LEVEL[y + rows][door] == ",", "a clear path out of each door"
    assert level_problems() == []


def test_smoke_rises_from_each_chimney_and_stays_on_top():
    spots = chimney_spots()
    assert len(spots) == len(find_cottages())
    world = Overworld()
    world.pos = [spots[0][0], spots[0][1] + 50.0]
    before = pygame.Surface(VIEW)
    after = pygame.Surface(VIEW)
    world.draw(before)
    world.time += 1.3
    world.draw(after)
    assert pygame.image.tobytes(before, "RGB") != pygame.image.tobytes(after, "RGB")


def run_slimes(world, seconds=120):
    world.pos = [-999.0, -999.0]
    for _ in range(int(seconds / STEP)):
        for key, bouncer in world.bouncers.items():
            bouncer.update(STEP, world._blocked)
            yield key, bouncer


def test_slimes_bounce_away_from_home_but_stay_on_a_short_leash():
    world = Overworld()
    moved = set()
    for key, bouncer in run_slimes(world):
        assert not world._blocked(*bouncer.pos)
        assert math.dist(bouncer.pos, bouncer.home) <= LEASH
        if bouncer.pos != list(bouncer.home):
            moved.add(key)
    assert moved == set(ENCOUNTERS)


def test_a_hop_rises_and_shows_each_frame():
    bouncer = Overworld().bouncers["1"]
    frames, lifts = set(), set()
    for _ in range(int(20 / STEP)):
        bouncer.update(STEP, lambda x, y: False)
        frames.add(bouncer.frame)
        lifts.add(bouncer.lift)
    assert frames == {REST, SQUASHED, STRETCHED}
    assert max(lifts) >= 6 and min(lifts) == 0


def test_a_slime_can_never_reach_the_start():
    world = Overworld()
    for spot in (bouncer.home for bouncer in world.bouncers.values()):
        assert math.dist(spot, world.start) > LEASH + TRIGGER_RADIUS


def test_slimes_hold_still_during_an_alert_and_after_defeat():
    world = Overworld()
    world.defeated.add("2")
    resting_at = list(world.foes["2"])
    world.pos = list(world.foes["1"])
    world.update(STEP, (0, 0))
    frozen = list(world.foes["1"])
    assert world.alert == "1"
    for _ in range(10):
        world.update(STEP, (0, 0))
    assert world.foes["1"] == frozen and world.foes["2"] == resting_at


def test_a_moving_slime_still_starts_a_fight():
    world = Overworld()
    for _ in range(int(10 / STEP)):
        world.bouncers["1"].update(STEP, world._blocked)
    world.foes["1"] = world.bouncers["1"].pos
    world.pos = list(world.foes["1"])
    world.update(STEP, (0, 0))
    assert world.alert == "1"


def test_proximity_starts_a_fight_after_the_alert():
    world = Overworld()
    world.pos = list(world.foes["1"])
    assert world.update(STEP, (0, 0)) is None
    assert world.alert == "1"
    key = None
    for _ in range(30):
        key = key or world.update(STEP, (0, 0))
    assert key == "1"


def test_defeated_foes_do_not_trigger_again():
    world = Overworld()
    world.defeated.add("1")
    world.pos = list(world.foes["1"])
    world.update(STEP, (0, 0))
    assert world.alert is None


def test_losing_returns_to_the_checkpoint_outside_foe_range():
    world = Overworld()
    world.pos = list(world.foes["1"])
    world.update(STEP, (0, 0))
    world.resolve_fight("1", won=False)
    assert tuple(world.pos) == world.checkpoint
    world.update(STEP, (0, 0))
    assert world.alert is None


def finish_fight(game, surf, outcome):
    game.battle.outcome = outcome
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    while game.battle or game.wipe is not None:
        game.update(STEP)
        game.draw(surf)


def enter_fight(game, surf, key):
    game.world.pos = list(game.world.foes[key])
    while game.battle is None or game.wipe is not None:
        game.update(STEP)
        game.draw(surf)


@pytest.mark.parametrize("outcome", [Outcome.LOSS, Outcome.DRAW])
def test_only_a_win_counts_as_beating_a_foe(outcome):
    surf = pygame.Surface((WIDTH, HEIGHT))
    game = Game(seed=0)
    enter_fight(game, surf, "1")
    finish_fight(game, surf, outcome)
    assert "1" not in game.world.defeated


@pytest.mark.parametrize("order", ["123", "321", "213"])
def test_campaign_reaches_the_ending_in_any_order(order):
    surf = pygame.Surface((WIDTH, HEIGHT))
    game = Game(seed=0)
    for key in (*order, "B"):
        enter_fight(game, surf, key)
        assert game.battle.foe.name == ENCOUNTERS[key].name
        assert game.battle.foe.battler.hp == 100 and game.battle.player.battler.hp == 100
        finish_fight(game, surf, Outcome.WIN)
    assert game.finished
