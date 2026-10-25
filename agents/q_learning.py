import numpy as np
from battle.engine import Move
from battle.env import N_STATES

class QLearningAgent:
    def __init__(self, alpha = 0.1, gamma = 0.95, epsilon = 1.0, rng = None):
        self.q = np.zeros((N_STATES, len(Move)))
        self.alpha, self.gamma, self.epsilon = alpha, gamma, epsilon
        self.rng = rng or np.random.default_rng()

    def act(self, state: int, mask: np.ndarray, greedy = False) -> int:
        legal = np.flatnonzero(mask)

        if not greedy and self.rng.random() < self.epsilon:
            return int(self.rng.choice(legal))

        values = np.where(mask == 1, self.q[state], -np.inf)

        return int(np.argmax(values))

    def update(self, s, a, r, s_next, next_mask, terminated):
        if terminated:
            target = r
        else:
            best_next = np.max(self.q[s_next][next_mask == 1])
            target = r + self.gamma * best_next

        self.q[s,a] += self.alpha * (target - self.q[s,a])