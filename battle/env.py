import gymnasium as gym
import numpy as np
from battle.engine import Battler, Move, Outcome, legal_moves, resolve_turn, battle_over

# The state encoding lives in battle.state; these names stay importable from here.
from battle.state import N_STATES, STATE_DIMS, encode_state, hp_bucket, mana_bucket  # noqa: F401


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