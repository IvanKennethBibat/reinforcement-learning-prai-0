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


def test_the_boss_plays_at_the_dda_tier_like_every_slime():
    game = Game(seed=0)
    for tier in (0, len(game.pool) - 1):
        game.director.tier = tier
        assert start_fight(game, "B").opponent.tier == tier


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


def overlay(battle, game):
    return battle_lines(battle.opponent, game.director, battle.foe.battler, battle.player.battler)


def test_overlay_shows_the_odds_of_the_foes_next_move_before_the_first_turn():
    game = Game(seed=0)
    battle = start_fight(game)
    rows = overlay(battle, game)
    move_rows = [text for text, _ in rows if text.split()[0] in Move.__members__]
    assert len(move_rows) == len(Move)
    odds = [int(text.split()[-1].rstrip("%")) for text in move_rows if text.endswith("%")]
    assert abs(sum(odds) - 100) <= len(odds), "the chances of the legal moves add up to 100%"
    assert any(text.startswith("TIER 3/5 RANDOM 0.40") for text, _ in rows)
    assert rows[-1][0] == "LAST: NONE YET"


def test_overlay_highlights_the_best_move_and_reports_last_turn():
    game = Game(seed=0)
    battle = start_fight(game)
    battle.choose(Move.ATTACK)
    rows = overlay(battle, game)
    state, mask = battle.opponent.upcoming(battle.foe.battler, battle.player.battler)
    q = game.pool.q_values(state)
    best = max((m for m in Move if mask[m]), key=lambda m: q[m])
    highlighted = [text for text, on in rows if on]
    assert len(highlighted) == 1 and highlighted[0].startswith(best.name)
    expected = round((1 - 0.4 + 0.4 / mask.sum()) * 100)  # tier 3: epsilon 0.4
    assert highlighted[0].endswith(f"{expected}%")
    how = "RANDOM" if battle.opponent.last_deviated else "BEST"
    assert rows[-1][0] == f"LAST: {battle.opponent.last_move.name} ({how})"


def test_overlay_rows_fit_the_panel():
    from ui.font import CHAR_WIDTH, GLYPHS
    game = Game(seed=0)
    for tier in range(len(game.pool)):
        game.director.tier = tier
        battle = start_fight(game)
        battle.choose(Move.DEFEND)
        for text, _ in overlay(battle, game):
            assert set(text) <= set(GLYPHS)
            room = 164 - 8 - (32 if text.split()[0] in Move.__members__ else 0)  # move rows also hold a bar
            assert len(text) * CHAR_WIDTH <= room, text
    assert len("LAST: FIREBOLT (RANDOM)") * CHAR_WIDTH <= 164 - 8, "the longest last-turn line"


def test_dda_lines_show_tier_score_and_target():
    game = Game(seed=0)
    assert dda_lines(game.director)[1].startswith("SCORE -")
    game.director.record(Outcome.WIN)
    text = " ".join(dda_lines(game.director))
    assert "TIER" in text and "SCORE 1.00 (1/10)" in text and "TARGET 0.40-0.60" in text


def test_a_tier_change_is_announced_once_at_the_start_of_the_next_fight():
    game = Game(seed=0)
    assert start_fight(game).notice is None, "no change yet, so no notice"
    game.director.tier += 1
    battle = start_fight(game)
    assert battle.notice.startswith("DIFFICULTY UP") and battle.showing_notice
    assert start_fight(game).notice is None, "announced once, not every fight"
    game.director.tier -= 2
    assert start_fight(game).notice.startswith("DIFFICULTY DOWN")


def test_the_difficulty_notice_fits_the_screen_and_clears_when_play_starts():
    from ui.font import CHAR_WIDTH, GLYPHS
    game = Game(seed=0)
    game.director.tier += 1
    battle = start_fight(game)
    assert set(battle.notice) <= set(GLYPHS) and len(battle.notice) * CHAR_WIDTH <= WIDTH - 8
    battle.choose(Move.DEFEND)
    assert not battle.showing_notice


def test_dda_badge_shows_the_win_rate_and_fits_between_the_plates():
    from ui import hud
    from ui.font import CHAR_WIDTH, GLYPHS
    game = Game(seed=0)
    assert hud.dda_score_text(game.director) == "WIN RATE -"
    for outcome in (Outcome.WIN, Outcome.LOSS, Outcome.WIN, Outcome.WIN):
        game.director.record(outcome)
    text = hud.dda_score_text(game.director)
    assert text == "WIN RATE 0.75" and set(text) <= set(GLYPHS)
    assert len(text) * CHAR_WIDTH <= 84, "the gap between the two status plates is 84 px"


def test_dda_badge_says_how_often_foes_play_at_random():
    from ui import hud
    from ui.font import CHAR_WIDTH, GLYPHS
    game = Game(seed=0)
    battle = start_fight(game)
    assert battle.randomness == 0.4 and hud.dda_random_text(battle.randomness) == "RANDOM 40%"
    for level in game.pool.levels:
        text = hud.dda_random_text(level)
        assert set(text) <= set(GLYPHS) and len(text) * CHAR_WIDTH <= 84
    assert hud.NOTICE_Y >= 16 + 18 + 7, "the notice sits below the badge's third line"


def test_dda_badge_is_drawn_on_the_map_and_in_battle():
    game = Game(seed=0)
    surf = pygame.Surface((WIDTH, HEIGHT))
    game.draw(surf)
    start_fight(game).draw(surf)
    game.director = None
    game.draw(surf)  # no pool: no badge, and no crash
