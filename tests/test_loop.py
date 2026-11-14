import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from ui.__main__ import MAX_FRAME, STEP, FixedStep
from ui.game import Game, _wipe_mask
from ui.overworld import SPEED, TILE


def test_a_steady_60hz_screen_gets_exactly_one_step_every_frame():
    stepper = FixedStep()
    assert [stepper.steps_for(STEP) for _ in range(600)] == [1] * 600


def test_millisecond_rounding_does_not_cause_uneven_steps():
    stepper = FixedStep()
    frames = [0.016, 0.017, 0.017] * 200
    assert [stepper.steps_for(frame) for frame in frames] == [1] * 600


@pytest.mark.parametrize("hertz, steps_in_a_second", [(30, 60), (120, 60), (144, 60)])
def test_game_speed_is_the_same_on_any_screen(hertz, steps_in_a_second):
    stepper = FixedStep()
    assert sum(stepper.steps_for(1 / hertz) for _ in range(hertz)) == pytest.approx(steps_in_a_second, abs=1)


def test_a_jittery_120hz_screen_steps_on_exactly_every_other_refresh():
    stepper = FixedStep(120)
    jitter = [1 / 120 + wobble for wobble in (0.0009, -0.0011, 0.0004, -0.0007, 0.001, -0.0005)] * 50
    steps = [stepper.steps_for(frame) for frame in jitter]
    assert steps == [0, 1] * 150 or steps == [1, 0] * 150


def test_flips_that_return_unevenly_still_step_evenly():
    # macOS often returns one flip at once and makes the next wait two refreshes.
    stepper = FixedStep(120)
    frames = ([1 / 120] * 7 + [0.0003, 2 / 120]) * 40
    steps = [stepper.steps_for(frame) for frame in frames]
    assert steps in ([0, 1] * 180, [1, 0] * 180)


def test_the_refresh_rate_is_measured_when_the_screen_reports_it_wrong():
    stepper = FixedStep(60)
    for _ in range(60):
        stepper.steps_for(1 / 144)
    assert stepper.refresh == pytest.approx(1 / 144)


def test_a_long_pause_does_not_fast_forward_the_game():
    assert FixedStep().steps_for(5.0) == round(MAX_FRAME / STEP)


def test_walking_moves_exactly_one_pixel_every_step():
    assert SPEED * STEP == 1
    world = Game(seed=0).world
    world.foes = {}
    world.pos = [20 * TILE + 8.0, 26 * TILE + 8.0]
    camera, moves = world._camera()[0], []
    for _ in range(200):
        world.update(STEP, (1, 0))
        moves.append(world._camera()[0] - camera)
        camera = world._camera()[0]
    moving = [step for step in moves if step]
    assert len(moving) > 100 and set(moving) == {1}


def test_wipe_mask_matches_its_dither_level():
    assert _wipe_mask(0).get_bounding_rect().width == 0
    full = pygame.mask.from_surface(_wipe_mask(16))
    assert full.count() == 320 * 180
    assert pygame.mask.from_surface(_wipe_mask(8)).count() == 320 * 180 // 2
