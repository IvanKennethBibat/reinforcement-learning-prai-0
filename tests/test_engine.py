from battle.engine import MOVES, Move, Battler, legal_moves

def test_firebolt_costs_10_mana():
    assert MOVES[Move.FIREBOLT].mana_cost == 10

def test_legal_moves_with_6_mana():
    battler = Battler(mana=6)

    assert legal_moves(battler) == [Move.ATTACK, Move.HONE, Move.DEFEND]

def test_legal_moves_with_max_mana():
    battler = Battler(mana=30)

    assert legal_moves(battler) == [Move.ATTACK, Move.FIREBOLT, Move.HONE, Move.HEAL, Move.DEFEND]