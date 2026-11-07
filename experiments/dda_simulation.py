"""Does DDA keep simulated players in the target band? ``python -m experiments.dda_simulation``

Three bots stand in for players of different skill. Each plays a run of fights
against the opponent pool, once with DDA choosing the tier and once at a fixed
middle tier, over several seeds and with each seed's trained Q-table.
Saves results/dda_runs.npz and results/dda_summary.csv.
"""
import csv
from pathlib import Path

import numpy as np

from agents.dda import WINDOW, DifficultyDirector, player_outcome
from agents.opponent_pool import OpponentPool
from battle.bots import expert_bot, random_bot, scripted_bot
from battle.env import BattleEnv

PLAYERS = {"novice (random)": random_bot, "intermediate (scripted)": scripted_bot, "skilled (expert)": expert_bot}
FIGHTS = 80
RUNS = 10           # seeds per player
POOL_SEEDS = (0, 1, 2)
ROOT = Path(__file__).resolve().parent.parent


def play_fight(pool, tier, env, rng):
    state, info = env.reset()
    done = False
    while not done:
        state, _, done, _, info = env.step(pool.act(tier, state, info["action_mask"], rng))
    return player_outcome(info["outcome"])


def run(pool, player_bot, seed, adaptive):
    rng = np.random.default_rng(seed)
    env = BattleEnv(player_bot)
    env.reset(seed=seed)
    director = DifficultyDirector(len(pool))
    tiers, rolling = [], []
    for _ in range(FIGHTS):
        tiers.append(director.tier)
        outcome = play_fight(pool, director.tier, env, rng)
        if adaptive:
            director.record(outcome)
        else:
            director.history.append({"win": 1.0, "draw": 0.5, "loss": 0.0}[outcome.value])
        rolling.append(director.score)
    return np.array(tiers), np.array(rolling, dtype=float)


def main():
    out = {}
    rows = []
    for name, bot in PLAYERS.items():
        for mode in ("dda", "fixed"):
            tiers, rolling = [], []
            for pool_seed in POOL_SEEDS:
                pool = OpponentPool.load(ROOT / "checkpoints" / f"npc_seed{pool_seed}.npy")
                for run_seed in range(RUNS):
                    t, r = run(pool, bot, 1000 * pool_seed + run_seed, mode == "dda")
                    tiers.append(t)
                    rolling.append(r)
            tiers, rolling = np.array(tiers), np.array(rolling)
            key = f"{name.split()[0]}_{mode}"
            out[f"{key}_tiers"], out[f"{key}_rolling"] = tiers, rolling
            settled = rolling[:, WINDOW * 2:]  # after the first 20 fights
            rows.append([
                name, mode, len(rolling),
                f"{settled.mean():.3f}",
                f"{np.mean((settled >= 0.4) & (settled <= 0.6)):.3f}",
                f"{np.mean(np.abs(settled - 0.5)):.3f}",
                f"{tiers[:, -1].mean():.2f}",
            ])
    np.savez(ROOT / "results" / "dda_runs.npz", fights=np.arange(1, FIGHTS + 1), **out)
    with open(ROOT / "results" / "dda_summary.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["player", "mode", "runs", "mean_score_after_20", "share_in_band_after_20",
                         "mean_distance_from_0.5", "final_tier_mean"])
        writer.writerows(rows)
    for row in rows:
        print(" | ".join(str(x) for x in row))


if __name__ == "__main__":
    main()
