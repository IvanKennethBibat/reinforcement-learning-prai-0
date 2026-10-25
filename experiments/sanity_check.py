import numpy as np
from collections import Counter
from battle.engine import Battler, Outcome, Move,legal_moves, resolve_turn, battle_over
from battle.bots import random_bot, scripted_bot, expert_bot

def play_one(bot_a, bot_b, rng) -> Outcome:
    a, b = Battler(), Battler()
    turn = 0
    while True:
        move_a = bot_a(a,b,rng)
        move_b = bot_b(b,a,rng)
        resolve_turn(a,b, move_a, move_b, rng)
        turn += 1
        result = battle_over(a,b,turn)
        if result is not None:
            return result

matchups = [
    (expert_bot, scripted_bot),
    (expert_bot, random_bot),
    (scripted_bot, random_bot),
    (random_bot, random_bot),
]
rng = np.random.default_rng(0)
for bot_a, bot_b in matchups:
    results = Counter(play_one(bot_a, bot_b, rng) for _ in range(1000))
    print(f"{bot_a.__name__} vs {bot_b.__name__}: {dict(results)}")