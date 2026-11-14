import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from agents.opponent_pool import TierPolicy
from battle.engine import Move, Outcome
from ui.arena import HEIGHT, WIDTH
from ui.debug import battle_lines, dda_lines
from ui.encounters import ENCOUNTERS
from ui.game import Game

STEP = 1 / 30


def key(game, code):
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=code, mod=0))


def start_fight(game, foe="1"):
    game._begin_fight(foe)
    return game.battle


def end_fight(game, outcome, button=pygame.K_RETURN):
    game.battle.outcome = outcome
    key(game, button)


def test_slimes_are_played_by_the_trained_agent_at_the_dda_tier():
    game = Game(seed=0)
    assert game.pool is not None, "train first: python -m experiments.train_pool"
    battle = start_fight(game)
    assert isinstance(battle.opponent, TierPolicy)
    assert battle.opponent.tier == game.director.tier


def test_the_boss_plays_one_tier_harder_but_never_past_the_top():
    game = Game(seed=0)
    assert start_fight(game, "B").opponent.tier == game.director.tier + 1
    game.director.tier = len(game.pool) - 1
    assert start_fight(game, "B").opponent.tier == len(game.pool) - 1


def test_each_fight_is_recorded_once_from_the_players_side():
    game = Game(seed=0)
    start_fight(game)
    end_fight(game, Outcome.WIN)
    assert list(game.director.history) == [1.0]


def test_rematch_records_the_result_and_starts_a_fresh_fight():
    game = Game(seed=0)
    first = start_fight(game, "2")
    end_fight(game, Outcome.WIN, pygame.K_r)
    assert game.battle is not first and game.battle.encounter is ENCOUNTERS["2"]
    assert game.battle.player.battler.hp == 100 and game.director.fights == 1
    assert "2" in game.world.defeated, "a win before a rematch still opens the gate"


def test_a_winning_streak_makes_the_next_slime_harder():
    game = Game(seed=0)
    start = game.director.tier
    for _ in range(6):
        start_fight(game)
        end_fight(game, Outcome.WIN, pygame.K_r)
    assert game.director.tier > start
    assert game.battle.opponent.tier == game.director.tier


def test_without_a_trained_pool_the_game_falls_back_to_the_bots():
    game = Game(seed=0, pool=None)
    assert start_fight(game).opponent is ENCOUNTERS["1"].policy
    end_fight(game, Outcome.LOSS)


def test_f1_toggles_the_debug_overlay_in_battle_and_on_the_map():
    game = Game(seed=0)
    surf = pygame.Surface((WIDTH, HEIGHT))
    key(game, pygame.K_F1)
    assert game.debug
    game.draw(surf)
    battle = start_fight(game)
    assert battle.debug
    battle.choose(Move.ATTACK)
    for _ in range(5):
        game.update(STEP)
        game.draw(surf)
    key(game, pygame.K_F1)
    assert not game.debug and not battle.debug


def test_overlay_explains_the_npcs_last_decision():
    game = Game(seed=0)
    battle = start_fight(game)
    battle.choose(Move.ATTACK)
    lines = [text for text, _ in battle_lines(battle.opponent, game.director)]
    picked = battle.opponent.last_move.name
    assert any(text.startswith(f"PICKED {picked}") for text in lines)
    assert sum(text.split()[0] in Move.__members__ for text in lines) == len(Move)
    assert any("RANDOM MOVES" in text for text in lines)  # the game's current tier rule
    highlighted = [text for text, on in battle_lines(battle.opponent, game.director) if on]
    assert highlighted and highlighted[0].startswith(picked)


def test_dda_lines_show_tier_score_and_target():
    game = Game(seed=0)
    assert dda_lines(game.director)[1].startswith("SCORE -")
    game.director.record(Outcome.WIN)
    text = " ".join(dda_lines(game.director))
    assert "TIER" in text and "SCORE 1.00 (1/10)" in text and "TARGET 0.40-0.60" in text
