from dataclasses import dataclass
from enum import IntEnum

MAX_HP =100
MAX_MANA = 30
DEFEND_MULTIPLIER = 0.5
HONE_MULTIPLIER = 2
TURN_LIMIT = 30
ROLL_MIN = 85
ROLL_MAX = 100

class Move(IntEnum):
    ATTACK = 0
    FIREBOLT = 1
    HONE = 2
    HEAL = 3
    DEFEND = 4


@dataclass(frozen=True)
class MoveStats:
    mana_cost: int
    mana_gain: int = 0
    max_damage: int = 0
    heal: int = 0

MOVES = {
    Move.ATTACK: MoveStats(mana_cost=0, max_damage=12),
    Move.FIREBOLT: MoveStats(mana_cost = 10, max_damage = 25),
    Move.HONE: MoveStats(mana_cost=5),
    Move.HEAL: MoveStats(mana_cost=8, heal=20),
    Move.DEFEND:  MoveStats(mana_cost=0, mana_gain=5)
}