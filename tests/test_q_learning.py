import numpy as np
from agents.q_learning import QLearningAgent
from battle.engine import Move
import pytest 


def test_act_never_returns_masked_move():
    agent = QLearningAgent(epsilon = 1.0, rng= np.random.default_rng(0))

    mask = np.array([1,0,1,0,1], dtype = np.int8)

    for _ in range(100):
        a = agent.act(0, mask)
        assert mask[a] == 1


def test_greedy_ignores_masked_best():
    agent = QLearningAgent(epsilon = 1.0, rng= np.random.default_rng(0))

    agent.q[0] = [0.2, 0.9, 0.1, 0.5, 0.3]

    mask = np.array([1,0,1,0,1], dtype = np.int8)

    a = agent.act(0,mask,greedy=True)
    assert a == Move.DEFEND


def test_terminal_update_moves_to_reward():
    agent = QLearningAgent(alpha = 0.1)
    agent.update(0,0,1.0,5,np.ones(5, dtype=np.int8), terminated = True)

    assert agent.q[0,0] == pytest.approx(0.1)

def test_save_load_round_trip(tmp_path):
    agent = QLearningAgent()
    agent.q[0] = [0.2, 0.9, 0.1, 0.5, 0.3]
    path = tmp_path / "q.npy"
    agent.save(path)
    clone = QLearningAgent.load(path)
    assert np.array_equal(agent.q, clone.q)