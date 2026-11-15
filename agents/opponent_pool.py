"""A ladder of NPC opponents of rising strength, built from one trained Q-table.

Every tier plays the trained agent, weakened in one of three ways (the "rule"):

  epsilon    with probability `level`, play any legal move at random
  rank       with probability `level`, play one of the agent's lesser moves,
             favouring its second best (challenge-sensitive action selection)
  tolerance  play any legal move whose Q-value is within `level` of the best

Tier 0 is the easiest and the last tier is the plain greedy agent. Probing showed
training checkpoints don't make a steady ladder, so all tiers share one Q-table.
"""
import numpy as np

from battle.engine import Move, legal_moves
from battle.state import encode_state

RULES = ("epsilon", "rank", "tolerance")
TIER_LEVELS = {
    "epsilon": (1.0, 0.8, 0.6, 0.4, 0.2, 0.0),
    "rank": (1.0, 0.8, 0.6, 0.4, 0.2, 0.0),
    "tolerance": (0.5, 0.3, 0.2, 0.1, 0.05, 0.0),
}
TIER_EPSILONS = TIER_LEVELS["epsilon"]
# When a rank tier slips, how likely it is to pick the 2nd, 3rd, 4th and 5th best move.
RANK_WEIGHTS = (0.55, 0.25, 0.15, 0.05)


class OpponentPool:
    def __init__(self, q, levels=None, rule="epsilon"):
        if rule not in RULES:
            raise ValueError(f"unknown tier rule {rule!r}")
        self.q = q
        self.rule = rule
        self.levels = tuple(TIER_LEVELS[rule] if levels is None else levels)

    @classmethod
    def load(cls, path, levels=None, rule="epsilon"):
        return cls(np.load(path), levels, rule)

    @property
    def epsilons(self):
        return self.levels

    def __len__(self):
        return len(self.levels)

    def act(self, tier, state, mask, rng):
        """The tier's choice from the legal moves in `mask`."""
        return self.decide(tier, state, mask, rng)[0]

    def decide(self, tier, state, mask, rng):
        """As act(), but also says whether the tier stepped away from the greedy choice."""
        legal = np.flatnonzero(mask)
        values = self.q[state][legal]
        best = int(legal[np.argmax(values)])
        level = self.levels[tier]
        if self.rule == "epsilon":
            if rng.random() < level:
                return int(rng.choice(legal)), True
        elif self.rule == "rank":
            if len(legal) > 1 and rng.random() < level:
                lesser = legal[np.argsort(-values, kind="stable")][1:]
                weights = np.array(RANK_WEIGHTS[:len(lesser)])
                return int(rng.choice(lesser, p=weights / weights.sum())), True
        else:
            close = legal[values >= values.max() - level]
            choice = int(rng.choice(close)) if len(close) > 1 else best
            return choice, choice != best
        return best, False

    def probabilities(self, tier, state, mask):
        """The exact chance of each move under decide(), for the F1 overlay. Illegal moves get 0.

        epsilon:   best move (1 - level) + level / n, every other legal move level / n
        rank:      best move 1 - level, the rest share level by RANK_WEIGHTS
        tolerance: equal chances for every move within `level` of the best Q-value
        """
        legal = np.flatnonzero(mask)
        values = self.q[state][legal]
        best = int(legal[np.argmax(values)])
        level = self.levels[tier]
        chances = np.zeros(len(mask))
        if self.rule == "epsilon":
            chances[legal] = level / len(legal)
            chances[best] += 1 - level
        elif self.rule == "rank" and len(legal) > 1:
            lesser = legal[np.argsort(-values, kind="stable")][1:]
            weights = np.array(RANK_WEIGHTS[:len(lesser)])
            chances[lesser] = level * weights / weights.sum()
            chances[best] = 1 - level
        elif self.rule == "tolerance":
            close = legal[values >= values.max() - level]
            chances[close] = 1 / len(close)
        else:
            chances[best] = 1.0
        return chances

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
        self.last_mask = None
        self.last_move = None
        self.last_deviated = False

    def observe(self, opponent_move):
        self.opp_last = opponent_move

    def upcoming(self, me, opp):
        """The state and legal-move mask this tier will decide from next turn, without deciding."""
        mask = np.zeros(len(Move), dtype=np.int8)
        mask[legal_moves(me)] = 1
        return encode_state(me, opp, self.opp_last), mask

    def __call__(self, me, opp, rng):
        self.last_state = encode_state(me, opp, self.opp_last)
        self.last_mask = np.zeros(len(Move), dtype=np.int8)
        self.last_mask[legal_moves(me)] = 1
        move, self.last_deviated = self.pool.decide(self.tier, self.last_state, self.last_mask, rng)
        self.last_move = Move(move)
        return self.last_move
