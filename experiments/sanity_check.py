import numpy as np
from collections import Counter
from battle.engine import Battler, Outcome, Move,legal_moves, resolve_turn, battle_over

def play_one(rng) -> Outcome:
    a, b = Battler(), Battler()
    turn = 0
    while True:
        move_a = Move(rng.choice(legal_moves(a)))
        move_b = Move(rng.choice(legal_moves(b)))
        resolve_turn(a,b, move_a, move_b, rng)
        turn += 1
        result = battle_over(a,b,turn)
        if result is not None:
            return result

rng = np.random.default_rng(0)
print(Counter(play_one(rng) for _ in range(1000)))