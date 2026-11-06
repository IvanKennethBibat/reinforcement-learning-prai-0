"""A 5x7 bitmap font, so text stays crisp at the game's low resolution."""
from functools import cache

import pygame

CHAR_WIDTH = 6
LINE_HEIGHT = 9

# One byte per column, lowest bit at the top.
GLYPHS = {
    "0": "3E 51 49 45 3E", "1": "00 42 7F 40 00", "2": "42 61 51 49 46", "3": "21 41 45 4B 31",
    "4": "18 14 12 7F 10", "5": "27 45 45 45 39", "6": "3C 4A 49 49 30", "7": "01 71 09 05 03",
    "8": "36 49 49 49 36", "9": "06 49 49 29 1E",
    "A": "7E 11 11 11 7E", "B": "7F 49 49 49 36", "C": "3E 41 41 41 22", "D": "7F 41 41 22 1C",
    "E": "7F 49 49 49 41", "F": "7F 09 09 09 01", "G": "3E 41 49 49 7A", "H": "7F 08 08 08 7F",
    "I": "00 41 7F 41 00", "J": "20 40 41 3F 01", "K": "7F 08 14 22 41", "L": "7F 40 40 40 40",
    "M": "7F 02 0C 02 7F", "N": "7F 04 08 10 7F", "O": "3E 41 41 41 3E", "P": "7F 09 09 09 06",
    "Q": "3E 41 51 21 5E", "R": "7F 09 19 29 46", "S": "46 49 49 49 31", "T": "01 01 7F 01 01",
    "U": "3F 40 40 40 3F", "V": "1F 20 40 20 1F", "W": "3F 40 38 40 3F", "X": "63 14 08 14 63",
    "Y": "07 08 70 08 07", "Z": "61 51 49 45 43",
    " ": "00 00 00 00 00", ".": "00 60 60 00 00", ",": "00 50 30 00 00", ":": "00 36 36 00 00",
    "!": "00 00 5F 00 00", "?": "02 01 51 09 06", "/": "20 10 08 04 02", "-": "08 08 08 08 08",
    "+": "08 08 3E 08 08", "'": "00 05 03 00 00", "(": "00 1C 22 41 00", ")": "00 41 22 1C 00",
}


@cache
def render_text(text: str, color: tuple, scale: int = 1) -> pygame.Surface:
    surf = pygame.Surface((max(1, len(text) * CHAR_WIDTH), 7), pygame.SRCALPHA)
    for index, char in enumerate(text.upper()):
        columns = GLYPHS.get(char, GLYPHS[" "]).split()
        for x, column in enumerate(columns):
            bits = int(column, 16)
            for y in range(7):
                if bits >> y & 1:
                    surf.set_at((index * CHAR_WIDTH + x, y), color)
    return pygame.transform.scale_by(surf, scale) if scale > 1 else surf


def draw_text(surf, text, pos, color, scale=1, shadow=None, center=False):
    image = render_text(text, tuple(color), scale)
    x, y = pos
    if center:
        x -= image.get_width() // 2
    if shadow:
        surf.blit(render_text(text, tuple(shadow), scale), (x + scale, y + scale))
    surf.blit(image, (x, y))


def wrap(text: str, max_chars: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > max_chars:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + [line] if line else lines
