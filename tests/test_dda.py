import numpy as np
import pytest

from agents.dda import COOLDOWN, MIN_FIGHTS, DifficultyDirector, player_outcome
from agents.opponent_pool import TIER_EPSILONS, OpponentPool
from battle.engine import Battler, Move, Outcome
from battle.env import N_STATES

W, L, D = Outcome.WIN, Outcome.LOSS, Outcome.DRAW


def test_score_counts_wins_draws_and_losses_from_the_players_side():
    director = DifficultyDirector(6)
    for outcome in (W, D, L, W):
        director.record(outcome)
    assert director.score == pytest.approx(2.5 / 4)
    assert player_outcome(Outcome.WIN) == L and player_outcome(Outcome.DRAW) == D


def test_nothing_changes_before_enough_fights():
    director = DifficultyDirector(6, start=3)
    for _ in range(MIN_FIGHTS - 1):
        assert director.record(W) == 3


def test_a_winning_player_gets_a_harder_tier_and_a_losing_one_an_easier_tier():
    winning, losing = DifficultyDirector(6, start=3), DifficultyDirector(6, start=3)
    for _ in range(MIN_FIGHTS):
        winning.record(W)
        losing.record(L)
    assert winning.tier == 4 and losing.tier == 2


def test_inside_the_band_the_tier_holds_steady():
    director = DifficultyDirector(6, start=3)
    for outcome in [W, L] * 20:
        director.record(outcome)
    assert director.tier == 3 and director.changes == []


def test_cooldown_spaces_out_changes_and_tiers_stay_in_range():
    director = DifficultyDirector(6, start=3)
    for _ in range(40):
        director.record(L)
    fights = [fight for fight, *_ in director.changes]
    assert director.tier == 0
    assert all(later - earlier >= COOLDOWN for earlier, later in zip(fights, fights[1:]))


def test_tier_zero_plays_at_random_and_the_top_tier_plays_greedy():
    q = np.zeros((N_STATES, len(Move)))
    q[0] = [0, 0, 5, 0, 0]
    pool = OpponentPool(q)
    rng = np.random.default_rng(0)
    mask = np.ones(len(Move), dtype=np.int8)
    assert TIER_EPSILONS[0] == 1.0 and TIER_EPSILONS[-1] == 0.0
    assert {pool.act(len(pool) - 1, 0, mask, rng) for _ in range(50)} == {Move.HONE}
    assert len({pool.act(0, 0, mask, rng) for _ in range(200)}) == len(Move)


def test_every_tier_only_picks_legal_moves():
    pool = OpponentPool(np.random.default_rng(1).normal(size=(N_STATES, len(Move))))
    rng = np.random.default_rng(2)
    mask = np.array([1, 0, 0, 1, 1], dtype=np.int8)
    for tier in range(len(pool)):
        assert all(mask[pool.act(tier, 7, mask, rng)] for _ in range(100))


def test_tier_policy_plays_like_a_bot_and_tracks_the_players_last_move():
    pool = OpponentPool(np.random.default_rng(3).normal(size=(N_STATES, len(Move))))
    policy = pool.policy(len(pool) - 1)
    rng = np.random.default_rng(0)
    first = policy(Battler(), Battler(), rng)
    assert isinstance(first, Move)
    before = policy.last_state
    policy.observe(Move.FIREBOLT)
    policy(Battler(), Battler(), rng)
    assert policy.last_state != before
