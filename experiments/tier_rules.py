"""Compare ways of weakening the agent for easier tiers: ``python -m experiments.tier_rules``

For each rule (random moves, rank-based slips, Q tolerance) and each seed's Q-table:
  - difficulty: the player's score against every tier, for three simulated players
  - believability: regret (best legal Q minus chosen Q) and how often the tier
    plays its worst legal move, over the NPC's decisions in those games
  - DDA: share of fights with the rolling score in the target band
Saves results/tier_rules.csv, results/tier_rules_dda.csv and results/tier_rules.png.
"""
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from agents.dda import TARGET_BAND, WINDOW
from agents.opponent_pool import RULES, OpponentPool
from battle.engine import Outcome
from battle.env import BattleEnv
from experiments.dda_simulation import PLAYERS, POOL_SEEDS, RUNS, run
from experiments.plot_results import BAND, INK, INK_SOFT, SERIES, SURFACE, style

ROOT = Path(__file__).resolve().parent.parent
GAMES = 400
RULE_TITLES = {"epsilon": "random moves (current)", "rank": "rank-based slips", "tolerance": "Q tolerance"}


def ladder_row(pool, tier, seed):
    """Player scores against one tier, plus how sensible the tier's moves were."""
    rng = np.random.default_rng(seed)
    scores, regrets, worst, choices = [], [], 0, 0
    for player in PLAYERS.values():
        env = BattleEnv(player)
        total = 0.0
        for game in range(GAMES):
            state, info = env.reset(seed=seed if game == 0 else None)
            done = False
            while not done:
                mask = info["action_mask"]
                move, _ = pool.decide(tier, state, mask, rng)
                legal = np.flatnonzero(mask)
                values = pool.q[state][legal]
                regrets.append(values.max() - pool.q[state][move])
                if len(legal) >= 3:
                    choices += 1
                    worst += move == legal[np.argmin(values)]
                state, _, done, _, info = env.step(move)
            total += {Outcome.LOSS: 1.0, Outcome.DRAW: 0.5, Outcome.WIN: 0.0}[info["outcome"]]
        scores.append(total / GAMES)
    return scores, float(np.mean(regrets)), worst / max(1, choices)


def main():
    ladder, dda = [], []
    for rule in RULES:
        for seed in POOL_SEEDS:
            pool = OpponentPool.load(ROOT / "checkpoints" / f"npc_seed{seed}.npy", rule=rule)
            for tier, level in enumerate(pool.levels):
                scores, regret, worst = ladder_row(pool, tier, 99)
                ladder.append([rule, seed, tier, level, *[f"{s:.3f}" for s in scores], f"{regret:.4f}", f"{worst:.3f}"])
        print(f"{rule}: ladder done")
        for name, bot in PLAYERS.items():
            rolling = []
            for seed in POOL_SEEDS:
                pool = OpponentPool.load(ROOT / "checkpoints" / f"npc_seed{seed}.npy", rule=rule)
                rolling += [run(pool, bot, 1000 * seed + r, True)[1] for r in range(RUNS)]
            settled = np.array(rolling)[:, WINDOW * 2:]
            in_band = np.mean((settled >= TARGET_BAND[0]) & (settled <= TARGET_BAND[1]))
            dda.append([rule, name, f"{settled.mean():.3f}", f"{in_band:.3f}"])
            print(f"  DDA {name}: mean {settled.mean():.3f}, in band {in_band:.0%}")

    with open(ROOT / "results" / "tier_rules.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["rule", "seed", "tier", "level", *[f"player_{n.split()[0]}" for n in PLAYERS],
                         "mean_regret", "worst_move_rate"])
        writer.writerows(ladder)
    with open(ROOT / "results" / "tier_rules_dda.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["rule", "player", "mean_score_after_20", "share_in_band_after_20"])
        writer.writerows(dda)
    plot(ladder)


def plot(ladder):
    rows = np.array(ladder, dtype=object)
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 4.0), dpi=200, facecolor=SURFACE, sharex=True,
                             gridspec_kw={"height_ratios": (2, 1)})
    for col, rule in enumerate(RULES):
        top, bottom = axes[0, col], axes[1, col]
        style(top)
        style(bottom)
        top.axhspan(*TARGET_BAND, color=BAND, zorder=0)
        mine = rows[rows[:, 0] == rule]
        tiers = sorted({int(t) for t in mine[:, 2]})
        for p, (name, color) in enumerate(zip(PLAYERS, SERIES)):
            mean = [np.mean([float(r[4 + p]) for r in mine if int(r[2]) == t]) for t in tiers]
            top.plot(tiers, mean, color=color, linewidth=2, marker="o", markersize=3, label=name.split()[0])
        worst = [np.mean([float(r[8]) for r in mine if int(r[2]) == t]) for t in tiers]
        bottom.plot(tiers, worst, color=INK_SOFT, linewidth=2, marker="o", markersize=3)
        top.set_title(RULE_TITLES[rule], color=INK, fontsize=9, loc="left")
        top.set_ylim(0, 1)
        bottom.set_ylim(0, 0.6)
        bottom.set_xticks(tiers)
        bottom.set_xlabel("tier (0 easiest)", color=INK_SOFT, fontsize=8)
        if col == 0:
            top.set_ylabel("player score", color=INK_SOFT, fontsize=8)
            bottom.set_ylabel("worst-move\nrate", color=INK_SOFT, fontsize=8)
    axes[0, 2].legend(frameon=False, fontsize=7, loc="upper right", labelcolor=INK, title="simulated player",
                      title_fontsize=7)
    fig.suptitle("How each tier rule trades difficulty range against sensible play (mean of 3 seeds)",
                 color=INK, fontsize=10, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(ROOT / "results" / "tier_rules.png", facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    main()
