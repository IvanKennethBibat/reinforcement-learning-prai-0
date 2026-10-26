import numpy as np
from battle.env import BattleEnv
from agents.q_learning import QLearningAgent
from battle.engine import Outcome
from battle.bots import scripted_bot

def train(opponent_bot, episodes = 20000, seed =0, eps_start = 1.0, eps_end = 0.05, decay_frac = 0.8):
    rng = np.random.default_rng(seed)
    env = BattleEnv(opponent_bot)
    agent = QLearningAgent(rng=rng)
    eps_step = (eps_start - eps_end) / (decay_frac * episodes)

    returns, outcomes = [], []

    for ep in range(episodes):
        # Epsilon decay from eps_start to eps_end
        agent.epsilon = max(eps_end, eps_start - ep * eps_step)

        # Seed once, env RNG advances each episode
        s, info = env.reset(seed=seed if ep == 0 else None)

        G, terminated = 0.0, False

        while not terminated:
            a = agent.act(s, info["action_mask"])

            s2, r, terminated, _, info = env.step(a)

            agent.update(s, a, r, s2, info["action_mask"], terminated)
            G += r
            s = s2

        returns.append(G)
        outcomes.append(info["outcome"])
    return agent, returns, outcomes


def evaluate(agent, opponent_bot, n=1000, seed=10000):
    env = BattleEnv(opponent_bot)
    counts = {Outcome.WIN: 0, Outcome.LOSS: 0, Outcome.DRAW: 0}
    for ep in range(n):
        s, info = env.reset(seed=seed if ep == 0 else None)
        terminated = False
        while not terminated:
            a = agent.act(s, info["action_mask"], greedy=True)
            s, _, terminated, _, info = env.step(a)
            # no update here: why?
        counts[info["outcome"]] += 1
    return {k: v / n for k, v in counts.items()}


if __name__ == "__main__":
    for frac in (0.2,0.5,0.8):
        agent, returns, outcomes = train(scripted_bot, seed=0, decay_frac = frac)
        print(f"--- decay_frac {frac} ---")
        for start in range(0, len(outcomes), 2000):
            block = outcomes[start:start + 2000]
            wins = sum(o == Outcome.WIN for o in block)
            print(f"eps {start:>6}: win rate {wins / len(block):.1%}")
            print(evaluate(agent, scripted_bot))