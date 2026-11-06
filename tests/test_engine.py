from battle.engine import (
    MOVES, TURN_LIMIT, Move, Battler, Outcome, legal_moves, calc_damage, battle_over, resolve_turn,
)
from battle.env import N_STATES, BattleEnv
from battle.bots import scripted_bot
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


def test_heal_potions_replace_the_mana_cost_and_run_out():
    drinker = Battler(hp=50, mana=0, heal_potions=2)
    foe = Battler()
    rng = np.random.default_rng(0)

    assert Move.HEAL in legal_moves(drinker)
    resolve_turn(drinker, foe, Move.HEAL, Move.DEFEND, rng)
    assert drinker.heal_potions == 1 and drinker.hp == 70 and drinker.mana == 0

    resolve_turn(drinker, foe, Move.HEAL, Move.DEFEND, rng)
    assert drinker.heal_potions == 0
    assert Move.HEAL not in legal_moves(Battler(heal_potions=0))


def test_battlers_without_potions_pay_mana_to_heal():
    healer = Battler(hp=50)

    resolve_turn(healer, Battler(), Move.HEAL, Move.DEFEND, np.random.default_rng(0))
    assert healer.mana == 30 - MOVES[Move.HEAL].mana_cost and healer.heal_potions is None


def test_a_ko_ends_the_fight():
    faller = Battler(hp=1)
    foe = Battler()

    resolve_turn(faller, foe, Move.DEFEND, Move.FIREBOLT, np.random.default_rng(0))
    assert battle_over(faller, foe, 1) == Outcome.LOSS


def test_rl_setup_keeps_its_five_moves_and_mana_heal():
    env = BattleEnv(scripted_bot)
    env.reset(seed=0)

    assert len(Move) == 5 and env.action_space.n == 5 and N_STATES == 3072
    assert env.npc.heal_potions is None and env.opp.heal_potions is None
