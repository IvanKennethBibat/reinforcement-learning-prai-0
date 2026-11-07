"""Dynamic difficulty adjustment: keep the player winning 40-60% of fights.

Indicator: the player's score over their last 10 fights (win 1, draw 0.5, loss 0).
Target: that score inside TARGET_BAND.
Mechanism: move one tier up the opponent pool when the player is winning too
often, and one down when they are losing too often. It waits for a few fights
before the first change, and between changes, so one lucky fight can't swing it.
"""
from collections import deque

from battle.engine import Outcome

WINDOW = 10
TARGET_BAND = (0.4, 0.6)
MIN_FIGHTS = 5     # fights before the first adjustment
COOLDOWN = 3       # fights between adjustments

PLAYER_SCORE = {Outcome.WIN: 1.0, Outcome.DRAW: 0.5, Outcome.LOSS: 0.0}


def player_outcome(npc_outcome):
    """Flip an outcome seen from the NPC's side to the player's side."""
    return {Outcome.WIN: Outcome.LOSS, Outcome.LOSS: Outcome.WIN, Outcome.DRAW: Outcome.DRAW}[npc_outcome]


class DifficultyDirector:
    def __init__(self, tiers, start=None, window=WINDOW, band=TARGET_BAND,
                 min_fights=MIN_FIGHTS, cooldown=COOLDOWN):
        self.tiers = tiers
        self.tier = tiers // 2 if start is None else start
        self.band = band
        self.min_fights = min_fights
        self.cooldown = cooldown
        self.history = deque(maxlen=window)
        self.since_change = 0
        self.fights = 0
        self.changes = []  # (fight number, old tier, new tier, score at the time)

    @property
    def score(self):
        """The player's score over the window, or None before any fights."""
        if not self.history:
            return None
        return sum(self.history) / len(self.history)

    @property
    def in_band(self):
        return self.score is not None and self.band[0] <= self.score <= self.band[1]

    def record(self, outcome):
        """Log a fight from the player's side, and return the tier for the next one."""
        self.history.append(PLAYER_SCORE[outcome])
        self.since_change += 1
        self.fights += 1
        if len(self.history) < self.min_fights or self.since_change < self.cooldown:
            return self.tier

        old = self.tier
        if self.score > self.band[1]:
            self.tier = min(self.tiers - 1, self.tier + 1)
        elif self.score < self.band[0]:
            self.tier = max(0, self.tier - 1)
        if self.tier != old:
            self.since_change = 0
            self.changes.append((self.fights, old, self.tier, self.score))
        return self.tier
