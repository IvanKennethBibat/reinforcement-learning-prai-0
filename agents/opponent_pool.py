"""A ladder of NPC opponents of rising strength, built from one trained Q-table.

Each tier plays the greedy Q-learning policy, but makes a random legal move with
probability `epsilon`. Tier 0 is fully random (easiest) and the last tier never
errs (hardest). Probing showed this gives a steady rise in difficulty against
every simulated player, unlike saved training checkpoints, whose difficulty
varies by opponent and by seed.
"""
import numpy as np

from battle.engine import Move, legal_moves
from battle.env import encode_state

# Chance of a random move at each tier, from easiest to hardest.
TIER_EPSILONS = (1.0, 0.8, 0.6, 0.4, 0.2, 0.0)


class OpponentPool:
    def __init__(self, q, epsilons=TIER_EPSILONS):
        self.q = q
        self.epsilons = tuple(epsilons)

    @classmethod
    def load(cls, path, epsilons=TIER_EPSILONS):
        return cls(np.load(path), epsilons)

    def __len__(self):
        return len(self.epsilons)

    def act(self, tier, state, mask, rng):
        """The tier's choice from the legal moves in `mask`."""
        legal = np.flatnonzero(mask)
        if rng.random() < self.epsilons[tier]:
            return int(rng.choice(legal))
        return int(legal[np.argmax(self.q[state][legal])])

    def q_values(self, state):
        return self.q[state]

    def policy(self, tier):
        return TierPolicy(self, tier)


class TierPolicy:
    """Plays one tier in the game, with the same call shape as the bots.

    Call observe() with the player's move after each turn, since the agent's state
    includes the opponent's last move.
    """

    def __init__(self, pool, tier):
        self.pool, self.tier = pool, tier
        self.opp_last = None
        self.last_state = None

    def observe(self, opponent_move):
        self.opp_last = opponent_move

    def __call__(self, me, opp, rng):
        self.last_state = encode_state(me, opp, self.opp_last)
        mask = np.zeros(len(Move), dtype=np.int8)
        mask[legal_moves(me)] = 1
        return Move(self.pool.act(self.tier, self.last_state, mask, rng))
