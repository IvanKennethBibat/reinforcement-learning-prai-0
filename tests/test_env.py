import pytest
from battle.env import BattleEnv, hp_bucket, mana_bucket, encode_state, N_STATES
from battle.engine import Battler, Move, Outcome, TURN_LIMIT
from battle.bots import scripted_bot

@pytest.mark.parametrize("hp, expected", [
    (0, 0), (25, 0), (26, 1), (50, 1), (51, 2), (75, 2), (76, 3), (100, 3)
])
def test_hp_bucket(hp, expected):
    assert hp_bucket(hp) == expected

@pytest.mark.parametrize("mana, expected", [
    (0, 0), (4, 0), (5, 1), (9, 1), (10,2), (14, 2), (15, 3), (29, 3), (30, 3)
])
def test_mana_bucket(mana, expected):
    assert mana_bucket(mana) == expected

def test_encode_state_in_range():
    state = encode_state(Battler(), Battler(), None)
    assert 0 <= state < N_STATES

def test_encode_state_honed_changes_state():
    plain = encode_state(Battler(honed = False), Battler(honed = True), None)

    honed = encode_state(Battler(honed=True), Battler(), None)

    assert plain != honed

def test_episode_terminates():
    env = BattleEnv(scripted_bot)
    obs, info = env.reset(seed=0)
    terminated = False

    for _ in range(TURN_LIMIT + 1):
        action = 0

        obs, r, terminated, _, info = env.step(action)

        assert 0 <= obs < N_STATES

        if terminated:
            break
    assert terminated and info["outcome"] is not None

def defend_bot(me, opp, rng):
    return Move.DEFEND


def test_heal_gives_positive_shaping():
    env = BattleEnv(defend_bot)
    env.reset(seed=0)
    env.npc.hp = 50

    _, r, terminated, _, _ = env.step(Move.HEAL)

    # 50 vs 100 -> 70 vs 100: 0.95 * -0.30 - (-0.50). The old damage-only reward gave 0 here.
    assert not terminated
    assert r == pytest.approx(0.215)


def test_timeout_while_ahead_is_penalised():
    env = BattleEnv(defend_bot)
    env.reset(seed=0)
    env.npc.hp, env.opp.hp = 80, 50
    env.turn = TURN_LIMIT - 1

    _, r, terminated, _, info = env.step(Move.DEFEND)

    # A timeout pays back the 0.30 lead, so running down the clock while ahead earns nothing overall.
    assert terminated and info["outcome"] == Outcome.DRAW
    assert r == pytest.approx(-0.30)
