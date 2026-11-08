"""How the agent sees a battle: a handful of coarse features packed into one number.

Kept apart from the Gymnasium environment so the game can use it without
loading Gymnasium.
"""
import numpy as np

from battle.engine import Battler, Move

#These buckets shrink values into a few coarse levels, keeping the Q-table small for learning.
def hp_bucket(hp:int) -> int:
    if hp <= 25:
        return 0
    elif hp <= 50:
        return 1
    elif hp <= 75:
        return 2
    else:
        return 3


def mana_bucket(mana:int) -> int:
    if mana <= 4:
        return 0
    elif mana <= 9:
        return 1
    elif mana <= 14:
        return 2
    else:
        return 3


# 2 x 4 HP buckets, 2 x 4 Mana Buckets, Opponent's last possible move (+ no move), 2 Honed status
STATE_DIMS = (4, 4, 4, 4, 6, 2)
N_STATES = int(np.prod(STATE_DIMS))   # 3072


def encode_state(me: Battler, opp: Battler, opp_last: Move | None) -> int:
    last = 0 if opp_last is None else int(opp_last) + 1

    features = (
        hp_bucket(me.hp),
        mana_bucket(me.mana),
        hp_bucket(opp.hp),
        mana_bucket(opp.mana),
        last,
        int(me.honed)
    )
    return int(np.ravel_multi_index(features, STATE_DIMS))


def decode_state(state: int) -> dict:
    """The features behind a state number, for debugging and plots."""
    my_hp, my_mana, opp_hp, opp_mana, last, honed = np.unravel_index(state, STATE_DIMS)
    return {
        "my_hp": int(my_hp), "my_mana": int(my_mana),
        "opp_hp": int(opp_hp), "opp_mana": int(opp_mana),
        "opp_last": None if last == 0 else Move(int(last) - 1),
        "honed": bool(honed),
    }
