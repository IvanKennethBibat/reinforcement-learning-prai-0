"""Status plates and the command panel."""
import pygame

from battle.engine import MAX_HP, MAX_MANA, MOVES, TURN_LIMIT, Move, mana_cost
from ui.font import CHAR_WIDTH, draw_text, wrap
from ui.palette import BONE, DANGER, EMBER, GOLD, INK, SKY, SPIRIT, STEEL, STONE, WHITE

PANEL = pygame.Rect(2, 140, 316, 38)
COMMAND_COLUMNS = (10, 104)
COMMAND_WIDTHS = (94, 58)
COMMAND_TOP = PANEL.y + 5
COMMAND_ROW = 11
DETAIL_X = 164
DETAIL_CHARS = (PANEL.right - DETAIL_X - 6) // CHAR_WIDTH

# Pipkin's names for the moves. The engine and the foes keep the plain ones.
MOVE_NAMES = {
    Move.ATTACK: "ATTACK",
    Move.FIREBOLT: "SWIPE",
    Move.HONE: "SHARPEN CLAWS",
    Move.HEAL: "HEAL",
    Move.DEFEND: "BLOCK",
}

MOVE_DETAILS = {
    Move.ATTACK: f"A quick pounce. Up to {MOVES[Move.ATTACK].max_damage} damage.",
    Move.FIREBOLT: f"Rake with your claws. Up to {MOVES[Move.FIREBOLT].max_damage} damage.",
    Move.HONE: "Your next Attack or Swipe deals double damage.",
    Move.HEAL: f"Potion. Restore {MOVES[Move.HEAL].heal} HP before blows land.",
    Move.DEFEND: f"Halve damage taken and gain {MOVES[Move.DEFEND].mana_gain} mana.",
}


def command_rect(move: Move) -> pygame.Rect:
    column, row = int(move) % 2, int(move) // 2
    return pygame.Rect(COMMAND_COLUMNS[column] - 6, COMMAND_TOP + row * COMMAND_ROW - 2, COMMAND_WIDTHS[column], COMMAND_ROW)


def _frame(surf, rect):
    pygame.draw.rect(surf, SKY[0], rect)
    pygame.draw.rect(surf, INK, rect.inflate(2, 2), 1)
    pygame.draw.rect(surf, STONE[3], rect, 1)
    pygame.draw.rect(surf, STONE[0], rect.inflate(-2, -2), 1)
    for x, y in (rect.topleft, (rect.right - 3, rect.top), (rect.left, rect.bottom - 3), (rect.right - 3, rect.bottom - 3)):
        pygame.draw.rect(surf, GOLD, (x, y, 3, 3))


def _bar(surf, x, y, width, value, trail, maximum, color, light):
    pygame.draw.rect(surf, INK, (x - 1, y - 1, width + 2, 6))
    pygame.draw.rect(surf, STONE[0], (x, y, width, 4))
    trail_width = round(width * trail / maximum)
    fill_width = round(width * value / maximum)
    if trail_width > fill_width:
        pygame.draw.rect(surf, WHITE, (x, y, trail_width, 4))
    if fill_width:
        pygame.draw.rect(surf, color, (x, y, fill_width, 4))
        pygame.draw.rect(surf, light, (x, y, fill_width, 1))


def draw_plate(surf, fighter, x):
    rect = pygame.Rect(x, 3, 112, 31)
    _frame(surf, rect)
    draw_text(surf, fighter.name, (rect.x + 6, rect.y + 5), BONE, shadow=INK)
    if fighter.shown_honed:
        draw_text(surf, "HONED", (rect.right - 36, rect.y + 5), GOLD, shadow=INK)

    hp = max(0, round(fighter.shown_hp))
    low = hp <= MAX_HP * 0.3
    _bar(surf, rect.x + 20, rect.y + 15, 68, fighter.shown_hp, fighter.trail_hp, MAX_HP,
         DANGER[1] if low else SPIRIT[1], DANGER[2] if low else SPIRIT[2])
    _bar(surf, rect.x + 20, rect.y + 23, 68, fighter.shown_mana, fighter.shown_mana, MAX_MANA, SKY[3], SKY[4])
    draw_text(surf, "HP", (rect.x + 6, rect.y + 14), STEEL[2])
    draw_text(surf, "MP", (rect.x + 6, rect.y + 22), STEEL[2])
    draw_text(surf, str(hp), (rect.x + 91, rect.y + 14), WHITE)
    draw_text(surf, str(round(fighter.shown_mana)), (rect.x + 91, rect.y + 22), WHITE)


def draw_turn(surf, turn):
    draw_text(surf, f"TURN {min(turn, TURN_LIMIT)}/{TURN_LIMIT}", (160, 6), BONE, shadow=INK, center=True)


def draw_panel(surf, selected, legal, log, accepting, player):
    _frame(surf, PANEL)
    pygame.draw.line(surf, STONE[1], (DETAIL_X - 6, PANEL.y + 4), (DETAIL_X - 6, PANEL.bottom - 5))

    for move in Move:
        rect = command_rect(move)
        x, y = rect.x + 6, rect.y + 2
        available = move in legal
        chosen = accepting and move == selected
        color = WHITE if chosen else BONE if available and accepting else STONE[2]
        if chosen:
            pygame.draw.polygon(surf, EMBER[2], [(x - 6, y), (x - 6, y + 6), (x - 3, y + 3)])
        draw_text(surf, MOVE_NAMES[move], (x, y), color)
        cost = mana_cost(player, move)
        if cost:
            draw_text(surf, str(cost), (rect.right - 2 - len(str(cost)) * CHAR_WIDTH, y), SPIRIT[1] if available and accepting else STONE[2])
        if move == Move.HEAL:
            draw_text(surf, f"x{player.heal_potions}", (rect.right - 2 - 2 * CHAR_WIDTH, y), GOLD if available and accepting else STONE[2])

    if accepting:
        lines = wrap(MOVE_DETAILS[selected], DETAIL_CHARS)
        if selected not in legal:
            lines = ["None left." if selected == Move.HEAL else "Not enough mana."]
    else:
        lines = log[-3:]
    for i, line in enumerate(lines[:3]):
        draw_text(surf, line, (DETAIL_X, PANEL.y + 6 + i * 10), BONE)


def draw_banner(surf, title, color, subtitle):
    band = pygame.Surface((320, 44), pygame.SRCALPHA)
    band.fill((*INK, 200))
    surf.blit(band, (0, 38))
    pygame.draw.line(surf, GOLD, (0, 38), (320, 38))
    pygame.draw.line(surf, GOLD, (0, 81), (320, 81))
    draw_text(surf, title, (160, 45), color, scale=3, shadow=INK, center=True)
    draw_text(surf, subtitle, (160, 70), BONE, center=True)
