import numpy as np
from collections import Counter
from battle.engine import MOVES, Battler, Outcome, Move,legal_moves, resolve_turn, battle_over

def random_bot(me: Battler, opp: Battler, rng) -> Move:
    return Move(rng.choice(legal_moves(me)))

def scripted_bot(me: Battler, opp: Battler, rng) -> Move:
    if Move.HEAL in legal_moves(me) and me.hp <= 30:
        return Move.HEAL
    elif Move.FIREBOLT in legal_moves(me):
        return Move.FIREBOLT
    return Move.ATTACK

def expert_bot(me: Battler, opp: Battler, rng) -> Move:
    if me.honed and Move.FIREBOLT in legal_moves(me):
        return Move.FIREBOLT
    elif opp.honed:
        return Move.DEFEND
    elif me.hp <= 33 and Move.HEAL in legal_moves(me):
        return Move.HEAL
    elif me.mana >= 15:
        return Move.HONE
    return Move.FIREBOLT if Move.FIREBOLT in legal_moves(me) else Move.ATTACK