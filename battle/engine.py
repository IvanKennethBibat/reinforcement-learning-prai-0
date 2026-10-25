from dataclasses import dataclass
from enum import IntEnum, StrEnum
import math

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

class Outcome(StrEnum):
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"

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

@dataclass
class Battler:
    hp: int = MAX_HP
    mana: int = MAX_MANA
    defending: bool= False
    honed: bool = False

    @property
    def is_ko(self) -> bool:
        return self.hp <= 0


def legal_moves(battler: Battler) -> list[Move]:
    moves = []

    for move in Move:
        if MOVES[move].mana_cost <= battler.mana:
            moves.append(move)
    return moves


def calc_damage(attacker, defender, move, rng) -> int:
    honed = HONE_MULTIPLIER if attacker.honed else 1
    defending = DEFEND_MULTIPLIER if defender.defending else 1
    
    damage = math.floor(MOVES[move].max_damage * honed * rng.integers(ROLL_MIN, ROLL_MAX + 1)/100 * defending)

    return damage


def battle_over(a: Battler, b: Battler, turn: int) -> Outcome | None:
    if a.is_ko:
        return Outcome.DRAW if b.is_ko else Outcome.LOSS
    elif b.is_ko:
        return Outcome.DRAW if a.is_ko else Outcome.WIN
    elif turn >= TURN_LIMIT:
        return Outcome.DRAW
    else:
        return None


def resolve_turn(a: Battler, b: Battler, move_a: Move, move_b: Move, rng) -> dict:

    # 1. Pay Mana costs for both moves
    a.mana -= MOVES[move_a].mana_cost
    b.mana -= MOVES[move_b].mana_cost

    # 2. Set defending flags (Defend has priority)
    a.defending, b.defending = (move_a == Move.DEFEND), (move_b == Move.DEFEND)

    # 3. Heal (the other priority move)
    previous_hp_a, previous_hp_b = a.hp, b.hp
    a.hp, b.hp = min(MAX_HP, a.hp + MOVES[move_a].heal), min(MAX_HP, b.hp + MOVES[move_b].heal)
    healed_a = a.hp - previous_hp_a
    healed_b = b.hp - previous_hp_b

    # 4. Work out damage each side deals:
    #    max_damage × (hone?) × roll × (target defending?), rounded down
    previous_hp_a, previous_hp_b = a.hp, b.hp
    damage_to_b = calc_damage(a, b, move_a, rng)
    damage_to_a = calc_damage(b, a, move_b, rng)

    # 5. Apply both damages at the same time (HP can't go below 0)
    a.hp = max(0, a.hp - damage_to_a)
    b.hp = max(0, b.hp - damage_to_b)

    hp_lost_a, hp_lost_b = previous_hp_a - a.hp, previous_hp_b - b.hp
    
    # 6. Mana Gain (Defend's other effect, capped at MAX_MANA)
    a.mana, b.mana = min(MAX_MANA, a.mana + MOVES[move_a].mana_gain), min(MAX_MANA, b.mana + MOVES[move_b].mana_gain)

    # 7. Update honed flags for next turn.
    a.honed = move_a == Move.HONE
    b.honed = move_b == Move.HONE

    # 8. Reset defending flags
    a.defending, b.defending = False, False

    # 9. Record what happened in results
    results = {
        "move_a": move_a,
        "move_b": move_b,
        "damage_to_a": hp_lost_a,
        "damage_to_b": hp_lost_b,
        "healed_a": healed_a,
        "healed_b": healed_b    
    }

    return results