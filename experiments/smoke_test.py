import numpy as np
from collections import Counter
from battle.engine import Battler, Outcome, Move,legal_moves, resolve_turn, battle_over
from battle.env import BattleEnv
from battle.bots import scripted_bot

env = BattleEnv(scripted_bot)
obs, info = env.reset(seed=0)
done = False
while not done:
    action = env.np_random.choice(np.flatnonzero(info["action_mask"]))
    obs, r, done, _, info = env.step(action)
    print(obs, r, info["outcome"])