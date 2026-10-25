import gymnasium as gym
import numpy as np
from battle.engine import Battler, Move, Outcome, legal_moves, resolve_turn, battle_over

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


class BattleEnv(gym.Env):
    def __init__(self, opponent_bot):
        self.opponent_bot = opponent_bot
        
        # 5 moves
        self.action_space = gym.spaces.Discrete(len(Move))

        # 3072 possible states, 
        self.observation_space = gym.spaces.Discrete(N_STATES)

    # Resets the stage at the start of every battle
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        self.npc, self.opp = Battler(), Battler()

        self.turn = 0
        self.opp_last = None

        return self._obs(), {"action_mask": self.action_mask()}


    # Internal, encodes battle into a state number
    def _obs(self) -> int:
        return encode_state(self.npc, self.opp, self.opp_last)


    # The 5 moves the NPC can currently afford to make.
    def action_mask(self) -> np.ndarray:
        mask = np.zeros(len(Move), dtype = np.int8)
        for move in legal_moves(self.npc):
            mask[move] = 1

        return mask

    def step(self, action:int):
        npc_move = Move(action)
        opp_move = self.opponent_bot(self.opp, self.npc, self.np_random)

        results = resolve_turn(self.npc, self.opp, npc_move, opp_move, self.np_random)
        self.turn += 1
        self.opp_last = opp_move

        outcome = battle_over(self.npc, self.opp, self.turn)
        reward = self._reward(results, outcome)
        terminated = outcome is not None

        return self._obs(), reward, terminated, False, {"action_mask": self.action_mask(), "outcome": outcome}

    def _reward(self, results: dict, outcome) -> float:
        if outcome == Outcome.WIN:
            return 1.0
        if outcome == Outcome.LOSS:
            return -1.0
        if outcome == Outcome.DRAW:
            return 0.0
        return 0.01 * (results["damage_to_b"] - results["damage_to_a"])