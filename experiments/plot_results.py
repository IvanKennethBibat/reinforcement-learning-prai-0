"""Draw the report figures from results/: ``python -m experiments.plot_results``.

  results/learning_curves.png   NPC score during training, mean and range over seeds
  results/dda_adaptation.png    rolling player score and tier, with and without DDA
  results/q_policy_map.png      the greedy move in each situation, from the game's Q-table
"""
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from agents.dda import TARGET_BAND, WINDOW
from agents.opponent_pool import TIER_EPSILONS
from battle.engine import Battler, Move, legal_moves
from battle.state import STATE_DIMS

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

# Validated categorical order (blue, orange, aqua); text stays in ink, never series colour.
SERIES = ("#2a78d6", "#eb6834", "#1baf7a")
SURFACE, INK, INK_SOFT, GRID, BAND = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#ecebe7"
OPPONENTS = ("random", "scripted", "expert")


def style(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_SOFT, labelsize=8)


def learning_curves():
    data = np.load(RESULTS / "learning_curves.npz")
    episodes = data["episodes"]
    with open(RESULTS / "baselines.csv") as f:
        expert_row = next(row for row in csv.DictReader(f) if row["npc"] == "expert_bot")

    fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=200, facecolor=SURFACE)
    style(ax)
    for name, color in zip(OPPONENTS, SERIES):
        runs = np.array([data[key] for key in data.files if key.endswith(f"_{name}")])
        mean = runs.mean(axis=0)
        ax.fill_between(episodes, runs.min(axis=0), runs.max(axis=0), color=color, alpha=0.15, linewidth=0)
        ax.plot(episodes, mean, color=color, linewidth=2, label=f"vs {name} bot")
        ax.text(episodes[-1] * 1.015, mean[-1], f"vs {name}", color=INK, fontsize=8, va="center")
        baseline = float(expert_row[f"vs_{name}"])
        ax.axhline(baseline, color=color, linewidth=1, alpha=0.55)
    ax.text(episodes[0], float(expert_row["vs_expert"]) - 0.06,
            "thin lines: expert bot in the NPC's place (baseline)", color=INK_SOFT, fontsize=7)
    ax.set_xlim(0, episodes[-1] * 1.13)
    ax.set_ylim(0, 1.04)
    ax.set_xlabel("training episodes", color=INK_SOFT, fontsize=9)
    ax.set_ylabel("NPC score (win 1, draw 0.5)", color=INK_SOFT, fontsize=9)
    ax.set_title("Greedy NPC score while training against a mix of bots\n"
                 f"mean of {len(runs)} seeds, shaded: range across seeds", color=INK, fontsize=10, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="lower right", labelcolor=INK)
    fig.tight_layout()
    fig.savefig(RESULTS / "learning_curves.png", facecolor=SURFACE)
    plt.close(fig)


def dda_adaptation():
    data = np.load(RESULTS / "dda_runs.npz")
    fights = data["fights"]
    players = (("novice", "Novice (random bot)"), ("intermediate", "Intermediate (scripted)"),
               ("skilled", "Skilled (expert bot)"))
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 4.2), dpi=200, facecolor=SURFACE, sharex=True,
                             gridspec_kw={"height_ratios": (2, 1)})
    for col, (key, title) in enumerate(players):
        top, bottom = axes[0, col], axes[1, col]
        style(top)
        style(bottom)
        top.axhspan(*TARGET_BAND, color=BAND, zorder=0)
        for mode, color, label in (("dda", SERIES[0], "DDA"), ("fixed", SERIES[1], "fixed tier")):
            rolling = data[f"{key}_{mode}_rolling"]
            q25, q75 = np.nanpercentile(rolling, (25, 75), axis=0)
            top.fill_between(fights, q25, q75, color=color, alpha=0.15, linewidth=0)
            mean = np.nanmean(rolling, axis=0)
            top.plot(fights, mean, color=color, linewidth=2, label=label)
            top.text(fights[-1] + 2, mean[-1], label, color=INK, fontsize=7, va="center")
            tiers = data[f"{key}_{mode}_tiers"].mean(axis=0)
            bottom.plot(fights, tiers, color=color, linewidth=2)
        top.set_title(title, color=INK, fontsize=9, loc="left")
        top.set_ylim(0, 1)
        top.set_xlim(1, fights[-1] + 22)
        bottom.set_ylim(-0.3, len(TIER_EPSILONS) - 0.7)
        bottom.set_yticks(range(len(TIER_EPSILONS)))
        bottom.set_xlabel("fight", color=INK_SOFT, fontsize=8)
        bottom.set_xticks([1, 20, 40, 60, fights[-1]])
        if col == 0:
            top.set_ylabel(f"player score,\nlast {WINDOW} fights", color=INK_SOFT, fontsize=8)
            bottom.set_ylabel("tier (0 easiest)", color=INK_SOFT, fontsize=8)
            top.text(3, TARGET_BAND[1] + 0.02, "target 40–60%", color=INK_SOFT, fontsize=7)
    runs = data["novice_dda_rolling"].shape[0]
    fig.suptitle(f"DDA keeps simulated players near the target band (mean of {runs} runs; shaded: middle 50%)",
                 color=INK, fontsize=10, x=0.01, ha="left")
    axes[0, 2].legend(frameon=False, fontsize=7, loc="lower right", labelcolor=INK)
    fig.tight_layout()
    fig.savefig(RESULTS / "dda_adaptation.png", facecolor=SURFACE)
    plt.close(fig)


# One validated colour per move, in a fixed order, with a text label on every cell.
MOVE_COLORS = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4")
MOVE_LABELS = {Move.ATTACK: "ATK", Move.FIREBOLT: "BOLT", Move.HONE: "HONE", Move.HEAL: "HEAL", Move.DEFEND: "DEF"}
MANA_EXAMPLES = (2, 7, 12, 25)  # one mana value inside each of the four mana buckets


def _ink_for(hex_color):
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return INK if 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.45 else "#ffffff"


def policy_map(seed=0):
    """The greedy move in each HP pairing, one panel per slime mana level.

    Each cell averages the Q-values of every state the agent visited in that
    situation (over the cat's mana, its last move and the slime's hone status),
    so it shows what was learned rather than untouched zeros. Cells never
    visited are greyed out.
    """
    q = np.load(ROOT / "checkpoints" / f"npc_seed{seed}.npy")
    visited = np.any(q != 0, axis=1)
    fig, axes = plt.subplots(1, 4, figsize=(7.2, 2.6), dpi=200, facecolor=SURFACE, sharey=True)
    for panel, (ax, mana) in enumerate(zip(axes, MANA_EXAMPLES)):
        ax.set_facecolor(SURFACE)
        legal = legal_moves(Battler(mana=mana))
        for my_hp in range(4):
            for cat_hp in range(4):
                states = [
                    np.ravel_multi_index((my_hp, panel, cat_hp, cat_mana, last, honed), STATE_DIMS)
                    for cat_mana in range(4) for last in range(STATE_DIMS[4]) for honed in range(2)
                ]
                seen = [s for s in states if visited[s]]
                cell = (cat_hp + 0.04, my_hp + 0.04)
                if not seen:
                    ax.add_patch(plt.Rectangle(cell, 0.92, 0.92, color=GRID, linewidth=0))
                    ax.text(cat_hp + 0.5, my_hp + 0.5, "unseen", ha="center", va="center", fontsize=5.5, color=INK_SOFT)
                    continue
                mean = q[seen].mean(axis=0)
                ranked = sorted(legal, key=lambda move: mean[move], reverse=True)
                best = ranked[0]
                margin = mean[best] - mean[ranked[1]] if len(ranked) > 1 else 0.0
                color = MOVE_COLORS[best]
                ink = _ink_for(color)
                ax.add_patch(plt.Rectangle(cell, 0.92, 0.92, color=color, linewidth=0))
                ax.text(cat_hp + 0.5, my_hp + 0.6, MOVE_LABELS[best], ha="center", va="center", fontsize=7,
                        color=ink, fontweight="bold")
                ax.text(cat_hp + 0.5, my_hp + 0.3, f"+{margin:.2f}", ha="center", va="center", fontsize=5.5, color=ink)
        ax.set_xlim(0, 4)
        ax.set_ylim(0, 4)
        ax.set_xticks([0.5, 1.5, 2.5, 3.5], ["0-25", "26-50", "51-75", "76+"], fontsize=6, color=INK_SOFT)
        ax.set_yticks([0.5, 1.5, 2.5, 3.5], ["0-25", "26-50", "51-75", "76+"], fontsize=6, color=INK_SOFT)
        ax.tick_params(length=0)
        for side in ax.spines.values():
            side.set_visible(False)
        ax.set_title(f"slime mana {('0-4', '5-9', '10-14', '15+')[panel]}", color=INK, fontsize=8, loc="left")
        ax.set_xlabel("cat HP", color=INK_SOFT, fontsize=7)
    axes[0].set_ylabel("slime HP", color=INK_SOFT, fontsize=7)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in MOVE_COLORS]
    fig.legend(handles, [f"{MOVE_LABELS[m]} = {m.name.lower()}" for m in Move], loc="lower center", ncol=5,
               frameon=False, fontsize=7, labelcolor=INK)
    fig.suptitle(f"Learned greedy move by situation (seed {seed}, {visited.mean():.0%} of states visited)\n"
                 "averaged over visited states; small number: Q-value lead over the next best legal move",
                 color=INK, fontsize=8.5, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.1, 1, 0.97))
    fig.savefig(RESULTS / "q_policy_map.png", facecolor=SURFACE)
    plt.close(fig)
    return visited.mean()


if __name__ == "__main__":
    learning_curves()
    dda_adaptation()
    policy_map()
    print("saved results/learning_curves.png, dda_adaptation.png and q_policy_map.png")
