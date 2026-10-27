import numpy as np
from battle.env import BattleEnv
from agents.q_learning import QLearningAgent
from battle.engine import Outcome
from battle.bots import scripted_bot
from agents.training import train, evaluate

if __name__ == "__main__":
    for frac in (0.2,0.5,0.8):
        agent, returns, outcomes = train(scripted_bot, seed=0, decay_frac = frac)
        print(f"--- decay_frac {frac} ---")
        for start in range(0, len(outcomes), 2000):
            block = outcomes[start:start + 2000]
            wins = sum(o == Outcome.WIN for o in block)
            print(f"eps {start:>6}: win rate {wins / len(block):.1%}")
            print(evaluate(agent, scripted_bot))