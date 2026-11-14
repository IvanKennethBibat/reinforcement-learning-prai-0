"""The F1 debug overlay: what the NPC sees, what it thinks of each move, and DDA.

Text-building is kept separate from drawing so tests can check what it says.
"""
import pygame

from agents.dda import TARGET_BAND
from battle.engine import Move
from battle.state import decode_state
from ui.font import draw_text
from ui.palette import BONE, GOLD, INK, SPIRIT, STONE

LINE = 9
RULE_LABELS = {"epsilon": "RANDOM MOVES", "rank": "SLIP CHANCE", "tolerance": "Q TOLERANCE"}
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


def battle_lines(policy, director):
    """Rows of (text, highlight) for the battle overlay."""
    rows = [(line, False) for line in dda_lines(director)[:2]]
    if getattr(policy, "last_state", None) is None:
        name = getattr(policy, "__name__", "AGENT").replace("_", " ").upper()
        rows.append((f"NPC: {name}" if not hasattr(policy, "pool") else "NPC: WAITING", False))
        return rows

    pool, state = policy.pool, policy.last_state
    rows.insert(1, (f"{RULE_LABELS[pool.rule]} {pool.levels[policy.tier]:.2f}", False))
    seen = decode_state(state)
    last = seen["opp_last"].name if seen["opp_last"] is not None else "NONE"
    rows.append((f"SLIME HP{seen['my_hp']} MP{seen['my_mana']} HONED {'Y' if seen['honed'] else 'N'}", False))
    rows.append((f"CAT HP{seen['opp_hp']} MP{seen['opp_mana']} LAST {last}", False))
    q = pool.q_values(state)
    for move in Move:
        legal = bool(policy.last_mask[move])
        value = f"{q[move]:+.2f}" if legal else "  --"
        rows.append((f"{move.name:<9}{value}", move == policy.last_move))
    rows.append((f"PICKED {policy.last_move.name} ({'SLIP' if policy.last_deviated else 'BEST'})", False))
    return rows


def _panel(surf, rect):
    shade = pygame.Surface(rect.size, pygame.SRCALPHA)
    shade.fill((*INK, 215))
    surf.blit(shade, rect.topleft)
    pygame.draw.rect(surf, STONE[2], rect, 1)


def draw_battle_overlay(surf, policy, director):
    rows = battle_lines(policy, director)
    rect = pygame.Rect(84, 36, 152, len(rows) * LINE + 4)
    _panel(surf, rect)
    q_rows = [i for i, (text, _) in enumerate(rows) if text.split()[0] in Move.__members__]
    values = {}
    if q_rows:
        q, mask = policy.pool.q_values(policy.last_state), policy.last_mask
        legal = [q[m] for m in Move if mask[m]]
        low, high = min(legal), max(legal)
        values = {m: (q[m] - low) / (high - low) if high > low else 1.0 for m in Move if mask[m]}
    for i, (text, highlight) in enumerate(rows):
        y = rect.y + 3 + i * LINE
        draw_text(surf, text, (rect.x + 4, y), GOLD if highlight else BONE)
        name = text.split()[0]
        if i in q_rows and Move[name] in values:
            width = max(1, round(values[Move[name]] * BAR))
            pygame.draw.rect(surf, GOLD if highlight else SPIRIT[1], (rect.right - BAR - 4, y + 1, width, 5))


def draw_world_overlay(surf, director):
    rows = dda_lines(director)
    rect = pygame.Rect(4, 4, 114, len(rows) * LINE + 6)
    _panel(surf, rect)
    for i, text in enumerate(rows):
        draw_text(surf, text, (rect.x + 4, rect.y + 4 + i * LINE), BONE)
