"""Does an agent trained on one bot cope with the others? ``python -m experiments.generalisation``

Trains a specialist against each bot, and the generalist against a random mix,
over seeds 0-2, then scores every agent against every bot.
Saves results/generalisation.csv.
"""
import csv

import numpy as np

from agents.training import train
from experiments.train_pool import BOTS, EPISODES, RESULTS, SEEDS, greedy, npc_score

GAMES = 1000


def main():
    trainers = {f"{name} only": bot for name, bot in BOTS.items()}
    trainers["mixed"] = list(BOTS.values())
    rows = []
    for label, opponents in trainers.items():
        scores = []
        for seed in SEEDS:
            agent, _, _ = train(opponents, episodes=EPISODES, seed=seed)
            scores.append([npc_score(greedy(agent), bot, GAMES, 7) for bot in BOTS.values()])
        scores = np.array(scores)
        rows.append([label, *[f"{m:.3f} ± {s:.3f}" for m, s in zip(scores.mean(0), scores.std(0))],
                     f"{scores.min():.3f}"])
        print(label, rows[-1][1:])
    with open(RESULTS / "generalisation.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["trained_against", *[f"vs_{name}" for name in BOTS], "worst_case"])
        writer.writerows(rows)


if __name__ == "__main__":
    main()
