import pytest
from battle.env import BattleEnv, hp_bucket, mana_bucket, encode_state, N_STATES
from battle.engine import Battler, TURN_LIMIT
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