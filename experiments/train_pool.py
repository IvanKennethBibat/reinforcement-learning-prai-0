"""Train the NPC for the opponent pool, over several seeds.

Run from the repo root: ``python -m experiments.train_pool``. Saves, per seed:
  checkpoints/npc_seed{seed}.npy     the trained Q-table
  results/learning_curves.npz        greedy score against each bot during training
  results/baselines.csv              trained agent vs the bots, all as the NPC
  results/tier_ladder.csv            player score against each tier of the pool
"""
import csv
from pathlib import Path

import numpy as np

from agents.opponent_pool import TIER_EPSILONS, OpponentPool
from agents.q_learning import QLearningAgent
from agents.training import train
from battle.bots import expert_bot, random_bot, scripted_bot
from battle.engine import Battler, Move, Outcome, battle_over, resolve_turn
from battle.env import BattleEnv

SEEDS = (0, 1, 2)
EPISODES = 40000
EVAL_EVERY = 2000
EVAL_GAMES = 300
LADDER_GAMES = 600
BOTS = {"random": random_bot, "scripted": scripted_bot, "expert": expert_bot}
ROOT = Path(__file__).resolve().parent.parent
CHECKPOINTS, RESULTS = ROOT / "checkpoints", ROOT / "results"


def npc_score(choose, player_bot, games, seed):
    """Share of games the NPC wins against `player_bot` (draws count half).

    `choose(state, mask, rng)` picks the NPC's move.
    """
    rng = np.random.default_rng(seed)
    env = BattleEnv(player_bot)
    total = 0.0
    for game in range(games):
        state, info = env.reset(seed=seed if game == 0 else None)
        done = False
        while not done:
            state, _, done, _, info = env.step(choose(state, info["action_mask"], rng))
        total += {Outcome.WIN: 1.0, Outcome.DRAW: 0.5, Outcome.LOSS: 0.0}[info["outcome"]]
    return total / games


def bot_as_npc_score(npc_bot, player_bot, games, seed):
    """The same measure for a hand-written bot playing the NPC."""
    rng = np.random.default_rng(seed)
    total = 0.0
    for _ in range(games):
        npc, player, turn = Battler(), Battler(), 0
        while (outcome := battle_over(npc, player, turn)) is None:
            resolve_turn(npc, player, npc_bot(npc, player, rng), player_bot(player, npc, rng), rng)
            turn += 1
        total += {Outcome.WIN: 1.0, Outcome.DRAW: 0.5, Outcome.LOSS: 0.0}[outcome]
    return total / games


def greedy(agent):
    return lambda state, mask, rng: agent.act(state, mask, greedy=True)


def main():
    CHECKPOINTS.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    curves = {"episodes": np.arange(EVAL_EVERY, EPISODES + 1, EVAL_EVERY)}

    for seed in SEEDS:
        scores = {name: [] for name in BOTS}

        def checkpoint(episode, agent):
            if episode % EVAL_EVERY == 0:
                for name, bot in BOTS.items():
                    scores[name].append(npc_score(greedy(agent), bot, EVAL_GAMES, seed=50_000 + episode))

        agent, _, _ = train(list(BOTS.values()), episodes=EPISODES, seed=seed, on_episode=checkpoint)
        agent.save(CHECKPOINTS / f"npc_seed{seed}.npy")
        for name in BOTS:
            curves[f"seed{seed}_{name}"] = np.array(scores[name])
        print(f"seed {seed}: final NPC score " + ", ".join(f"{n} {s[-1]:.2f}" for n, s in scores.items()))
    np.savez(RESULTS / "learning_curves.npz", **curves)

    with open(RESULTS / "baselines.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["npc", "seed", *[f"vs_{name}" for name in BOTS]])
        for npc_name, npc_bot in BOTS.items():
            writer.writerow([f"{npc_name}_bot", "-", *[f"{bot_as_npc_score(npc_bot, bot, 2000, 7):.3f}" for bot in BOTS.values()]])
        for seed in SEEDS:
            agent = QLearningAgent.load(CHECKPOINTS / f"npc_seed{seed}.npy")
            writer.writerow(["q_learning", seed, *[f"{npc_score(greedy(agent), bot, 2000, 7):.3f}" for bot in BOTS.values()]])

    with open(RESULTS / "tier_ladder.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["seed", "tier", "epsilon", *[f"player_{name}" for name in BOTS]])
        for seed in SEEDS:
            pool = OpponentPool.load(CHECKPOINTS / f"npc_seed{seed}.npy")
            for tier, epsilon in enumerate(TIER_EPSILONS):
                choose = lambda state, mask, rng, tier=tier: pool.act(tier, state, mask, rng)
                row = [1 - npc_score(choose, bot, LADDER_GAMES, 99) for bot in BOTS.values()]
                writer.writerow([seed, tier, epsilon, *[f"{score:.3f}" for score in row]])
    print("saved checkpoints/ and results/")


if __name__ == "__main__":
    main()
