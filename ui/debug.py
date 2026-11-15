"""The F1 debug overlay: what the NPC sees, what it thinks of each move, how likely it is
to play each one at the current DDA tier, and DDA.

Text-building is kept separate from drawing so tests can check what it says.
"""
import pygame

from agents.dda import TARGET_BAND
from battle.engine import Move
from battle.state import decode_state
from ui.font import draw_text
from ui.palette import BONE, GOLD, INK, SPIRIT, STONE

LINE = 9
RULE_LABELS = {"epsilon": "RANDOM", "rank": "SLIP", "tolerance": "Q TOL"}
BAR = 30


def dda_lines(director):
    if director is None:
        return ["DDA OFF"]
    score = "-" if director.score is None else f"{director.score:.2f}"
    return [
        f"DDA TIER {director.tier}/{director.tiers - 1}",
        f"SCORE {score} ({len(director.history)}/{director.history.maxlen})",
        f"TARGET {TARGET_BAND[0]:.2f}-{TARGET_BAND[1]:.2f}",
    ]


def battle_lines(policy, director, me, opp):
    """Rows of (text, highlight) for the battle overlay.

    The rows explain the foe's NEXT decision: the state it will see, the Q-value of each legal
    move, and the exact chance it plays each one at the current DDA tier (highlighted: its best
    move). The last row says what it did last turn and whether that move was its best or random.
    `me` is the foe's battler and `opp` the player's.
    """
    if not hasattr(policy, "pool"):
        name = getattr(policy, "__name__", "AGENT").replace("_", " ").upper()
        return [(line, False) for line in dda_lines(director)[:2]] + [(f"NPC: {name}", False)]

    pool = policy.pool
    state, mask = policy.upcoming(me, opp)
    q, chances = pool.q_values(state), pool.probabilities(policy.tier, state, mask)
    best = max((m for m in Move if mask[m]), key=lambda m: q[m])
    seen = decode_state(state)
    last = seen["opp_last"].name if seen["opp_last"] is not None else "NONE"
    rows = [
        (f"TIER {policy.tier}/{len(pool) - 1} {RULE_LABELS[pool.rule]} {pool.levels[policy.tier]:.2f}", False),
        (f"SLIME HP{seen['my_hp']} MP{seen['my_mana']} HONED {'Y' if seen['honed'] else 'N'}", False),
        (f"CAT HP{seen['opp_hp']} MP{seen['opp_mana']} LAST {last}", False),
        (f"{'NEXT':<9}{'Q':>5} {'ODDS':>4}", False),
    ]
    for move in Move:
        if mask[move]:
            rows.append((f"{move.name:<9}{q[move]:+.2f} {round(chances[move] * 100):>3}%", move == best))
        else:
            rows.append((f"{move.name:<9}{'--':>5} {'--':>4}", False))
    if policy.last_move is None:
        rows.append(("LAST: NONE YET", False))
    else:
        how = ("RANDOM" if pool.rule == "epsilon" else "SLIP") if policy.last_deviated else "BEST"
        rows.append((f"LAST: {policy.last_move.name} ({how})", False))
    return rows


def _panel(surf, rect):
    shade = pygame.Surface(rect.size, pygame.SRCALPHA)
    shade.fill((*INK, 215))
    surf.blit(shade, rect.topleft)
    pygame.draw.rect(surf, STONE[2], rect, 1)


def draw_battle_overlay(surf, policy, director, me, opp):
    rows = battle_lines(policy, director, me, opp)
    rect = pygame.Rect(78, 44, 164, len(rows) * LINE + 4)
    _panel(surf, rect)
    chances = {}
    if hasattr(policy, "pool"):
        state, mask = policy.upcoming(me, opp)
        odds = policy.pool.probabilities(policy.tier, state, mask)
        chances = {m: odds[m] for m in Move if mask[m]}
    for i, (text, highlight) in enumerate(rows):
        y = rect.y + 3 + i * LINE
        draw_text(surf, text, (rect.x + 4, y), GOLD if highlight else BONE)
        name = text.split()[0]
        if name in Move.__members__ and Move[name] in chances:
            width = round(chances[Move[name]] * BAR)
            if width:
                pygame.draw.rect(surf, GOLD if highlight else SPIRIT[1], (rect.right - BAR - 4, y + 1, width, 5))


def draw_world_overlay(surf, director):
    rows = dda_lines(director)
    rect = pygame.Rect(4, 4, 114, len(rows) * LINE + 6)
    _panel(surf, rect)
    for i, text in enumerate(rows):
        draw_text(surf, text, (rect.x + 4, rect.y + 4 + i * LINE), BONE)
