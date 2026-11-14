import gymnasium as gym
import numpy as np
from battle.engine import Battler, Move, Outcome, legal_moves, resolve_turn, battle_over

# The state encoding lives in battle.state; these names stay importable from here.
from battle.state import N_STATES, STATE_DIMS, encode_state, hp_bucket, mana_bucket  # noqa: F401

# must equal the gamma of the agent.
GAMMA = 0.95

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

        self._phi_before = 0.01 * (self.npc.hp - self.opp.hp)

        results = resolve_turn(self.npc, self.opp, npc_move, opp_move, self.np_random)
        self.turn += 1
        self.opp_last = opp_move

        outcome = battle_over(self.npc, self.opp, self.turn)
        reward = self._reward(results, outcome)
        terminated = outcome is not None

        return self._obs(), reward, terminated, False, {"action_mask": self.action_mask(), "outcome": outcome}

    def _reward(self, results: dict, outcome) -> float:
        # Potential-based shaping (Ng, Harada and Russell, 1999):
        #   reward = terminal + GAMMA * phi(s') - phi(s), where phi is the NPC's HP lead / 100.
        # It rewards any turn that improves the NPC's position (damage, heals, blocks), and
        # phi(terminal) = 0 pays the lead back when the fight ends, so the discounted shaping
        # sums to zero over a fight and the best policy is the same as with win/loss alone.
        # A timeout while ahead is therefore worth nothing, so stalling doesn't pay.
        # Keep the order of operations: it makes training reproduce the saved Q-tables exactly.
        terminal = {Outcome.WIN: 1.0, Outcome.LOSS: -1.0, Outcome.DRAW: 0.0}.get(outcome, 0.0)
        phi_after = 0.0 if outcome is not None else 0.01 * (self.npc.hp - self.opp.hp)
        return terminal + GAMMA * phi_after - self._phi_before