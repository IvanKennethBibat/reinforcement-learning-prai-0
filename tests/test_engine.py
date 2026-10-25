from battle.engine import MOVES, TURN_LIMIT, Move, Battler, Outcome, legal_moves, calc_damage, battle_over
import numpy as np


def test_firebolt_costs_10_mana():
    assert MOVES[Move.FIREBOLT].mana_cost == 10


def test_legal_moves_with_6_mana():
    battler = Battler(mana=6)

    assert legal_moves(battler) == [Move.ATTACK, Move.HONE, Move.DEFEND]


def test_legal_moves_with_max_mana():
    battler = Battler(mana=30)

    assert legal_moves(battler) == [Move.ATTACK, Move.FIREBOLT, Move.HONE, Move.HEAL, Move.DEFEND]


def test_battler_honed_doubles_damage():
    attacker = Battler(honed=True)
    defender = Battler()
    rng = np.random.default_rng(0)

    damage = calc_damage(attacker, defender, Move.ATTACK, rng)
    assert 20 <= damage <= 24


def test_battler_unhoned_does_normal_damage():
    attacker = Battler(honed=False)
    defender = Battler()
    rng = np.random.default_rng(0)

    damage = calc_damage(attacker, defender, Move.ATTACK, rng)
    assert 10 <= damage <= 12


def test_battle_over_a_ko_is_loss():
    assert battle_over(Battler(hp=0), Battler(), turn=1) == Outcome.LOSS

def test_battle_over_b_ko_is_win():
    assert battle_over(Battler(), Battler(hp=0), turn=1) == Outcome.WIN

def test_battle_over_both_ko_is_draw():
    assert battle_over(Battler(hp=0), Battler(hp=0), turn=1) == Outcome.DRAW

def test_battle_over_turn_limit_is_draw():
    assert battle_over(Battler(), Battler(), turn=TURN_LIMIT) == Outcome.DRAW

def test_battle_over_both_not_ko():
    assert battle_over(Battler(hp=5), Battler(hp=67), turn=5) == None