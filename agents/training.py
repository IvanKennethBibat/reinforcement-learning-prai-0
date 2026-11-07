import numpy as np
from battle.env import BattleEnv
from agents.q_learning import QLearningAgent
from battle.engine import Outcome
from battle.bots import scripted_bot


def train(opponent_bot, episodes = 20000, seed =0, eps_start = 1.0, eps_end = 0.05, decay_frac = 0.8,
          on_episode = None):
    """Train a Q-learning agent.

    opponent_bot can be one bot, or a list of bots to pick from at random each
    episode, which stops the agent overfitting to a single opponent.
    on_episode(ep, agent) is called after every episode, e.g. to save checkpoints.
    """
    rng = np.random.default_rng(seed)
    pool = list(opponent_bot) if isinstance(opponent_bot, (list, tuple)) else [opponent_bot]
    env = BattleEnv(pool[0])
    agent = QLearningAgent(rng=rng)
    eps_step = (eps_start - eps_end) / (decay_frac * episodes)

    returns, outcomes = [], []

    for ep in range(episodes):
        # Epsilon decay from eps_start to eps_end
        agent.epsilon = max(eps_end, eps_start - ep * eps_step)

        if len(pool) > 1:
            env.opponent_bot = pool[rng.integers(len(pool))]

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
        if on_episode is not None:
            on_episode(ep + 1, agent)
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
