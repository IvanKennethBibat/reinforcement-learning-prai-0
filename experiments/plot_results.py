"""Draw the report figures from results/: ``python -m experiments.plot_results``.

  results/learning_curves.png   NPC score during training, mean and range over seeds
  results/dda_adaptation.png    rolling player score and tier, with and without DDA
"""
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from agents.dda import TARGET_BAND, WINDOW
from agents.opponent_pool import TIER_EPSILONS

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


if __name__ == "__main__":
    learning_curves()
    dda_adaptation()
    print("saved results/learning_curves.png and results/dda_adaptation.png")
