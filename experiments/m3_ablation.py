"""Ablation of the three M3 issues (2026-11-14). Run from the repo root:
    uv run python -m experiments.m3_ablation <variant>
variants: base, mana5 (cost-aligned mana buckets), clock (late-fight flag), pbrs (potential-based shaping incl. heals), all

Results are in results/m3_ablation.json (produced at commit 2288774). "base" is the old reward,
0.01 x damage traded per turn, written out here; "pbrs" is the potential-based reward that
BattleEnv._reward now uses, so the pbrs run reproduces checkpoints/npc_seed*.npy exactly.
"""
import sys, json
import numpy as np
from agents.q_learning import QLearningAgent
from battle.engine import Move, Outcome, TURN_LIMIT
from battle.env import BattleEnv
from battle.state import hp_bucket, mana_bucket
from experiments.train_pool import BOTS, EPISODES, SEEDS

V = sys.argv[1]
MANA5 = V in ("mana5", "all"); CLOCK = V in ("clock", "all"); PBRS = V in ("pbrs", "all")
LATE = TURN_LIMIT - 6

def mana5(m):  # thresholds at the move costs: 5 Hone, 8 Heal, 10 Firebolt, 15 Hone+Firebolt
    return 0 if m < 5 else 1 if m < 8 else 2 if m < 10 else 3 if m < 15 else 4

MB = mana5 if MANA5 else mana_bucket
DIMS = (4, 5 if MANA5 else 4, 4, 5 if MANA5 else 4, 6, 2) + ((2,) if CLOCK else ())
N = int(np.prod(DIMS))

class Env(BattleEnv):
    def _obs(self):
        f = (hp_bucket(self.npc.hp), MB(self.npc.mana), hp_bucket(self.opp.hp), MB(self.opp.mana),
             0 if self.opp_last is None else int(self.opp_last) + 1, int(self.npc.honed))
        if CLOCK:
            f += (int(self.turn >= LATE),)
        return int(np.ravel_multi_index(f, DIMS))
    def _phi(self):
        return 0.01 * (self.npc.hp - self.opp.hp)
    def step(self, action):
        self._prev = self._phi()
        return super().step(action)
    def _reward(self, results, outcome):
        if not PBRS:
            if outcome is not None:  # the old reward: win/loss/draw, else damage traded
                return {Outcome.WIN: 1.0, Outcome.LOSS: -1.0, Outcome.DRAW: 0.0}[outcome]
            return 0.01 * (results["damage_to_b"] - results["damage_to_a"])
        terminal = {Outcome.WIN: 1.0, Outcome.LOSS: -1.0, Outcome.DRAW: 0.0}.get(outcome, 0.0)
        nxt = 0.0 if outcome is not None else self._phi()
        return terminal + 0.95 * nxt - self._prev

def train(seed):  # mirrors agents.training.train
    rng = np.random.default_rng(seed); pool = list(BOTS.values()); env = Env(pool[0])
    agent = QLearningAgent(rng=rng); agent.q = np.zeros((N, len(Move)))
    step = (1.0 - 0.05) / (0.8 * EPISODES)
    for ep in range(EPISODES):
        agent.epsilon = max(0.05, 1.0 - ep * step)
        env.opponent_bot = pool[rng.integers(len(pool))]
        s, info = env.reset(seed=seed if ep == 0 else None); done = False
        while not done:
            a = agent.act(s, info["action_mask"]); s2, r, done, _, info = env.step(a)
            agent.update(s, a, r, s2, info["action_mask"], done); s = s2
    return agent

def evaluate(agent, bot, games=1000, seed=7):
    env = Env(bot); score = timeouts = ahead = 0
    for g in range(games):
        s, info = env.reset(seed=seed if g == 0 else None); done = False
        while not done:
            s, _, done, _, info = env.step(agent.act(s, info["action_mask"], greedy=True))
        score += {Outcome.WIN: 1, Outcome.DRAW: .5, Outcome.LOSS: 0}[info["outcome"]]
        if info["outcome"] == Outcome.DRAW and not (env.npc.is_ko or env.opp.is_ko):
            timeouts += 1; ahead += env.npc.hp > env.opp.hp
    return score / games, timeouts / games, ahead / games

out = {"states": N, "visited": [], "res": {}}
for seed in SEEDS:
    agent = train(seed)
    if V == "pbrs":
        out["reproduces_checkpoint"] = out.get("reproduces_checkpoint", True) and bool(np.array_equal(agent.q, np.load(f"checkpoints/npc_seed{seed}.npy")))
    out["visited"].append(float(np.mean(np.any(agent.q != 0, axis=1))))
    for name, bot in BOTS.items():
        out["res"].setdefault(name, []).append(evaluate(agent, bot))
print(json.dumps({V: out}))
