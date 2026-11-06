"""Paint the level with the mouse: ``python -m ui.editor``.

Left mouse paints, right mouse picks up the tile under the cursor, and the arrow
keys or WASD scroll. Ctrl+S saves, Ctrl+Z undoes, G toggles the grid, Esc quits.
"""
import pygame

from ui.font import draw_text
from ui.overworld import (
    LEVEL, LEVEL_FILE, SOLID, TILE, build_map, build_props, find_tiles, level_problems,
    paint_tile, visible_props,
)
from ui.palette import BONE, EMBER, GOLD, INK, SKY, STONE, WHITE
from ui.props import prop_images

WINDOW = (480, 270)
VIEW_HEIGHT = 226
PALETTE_Y = 229
SWATCH = 18
SCROLL_SPEED = 240

TILE_NAMES = {
    ".": "GRASS", ",": "DIRT PATH", "_": "FLAGSTONE", "~": "CLOTH CARPET",
    "w": "WATER", "=": "PLANK BRIDGE", "#": "WALL", "R": "ROOF", "D": "DOOR",
    "W": "LIT WINDOW", "T": "TREE", "b": "BUSH", "r": "MOSSY ROCK",
    "c": "PILLAR", "o": "WELL", "l": "LANTERN", "H": "HALL GATE",
    "p": "PICKET FENCE", "g": "VEG PATCH", "v": "FLOWER BED",
    "e": "SHEEP", "S": "START", "1": "MOSS SLIME", "2": "TIDE SLIME", "3": "EMBER SLIME", "B": "VESPER",
}
UNIQUE = "S123B"   # exactly one of each: placing one moves it
SWATCH_PROPS = {"T": "pine", "b": "bush", "r": "rock"}
MARKERS = "SHe123B"  # invisible in the art, so the editor labels them


def _draw_marker(surf, char, x, y):
    pygame.draw.rect(surf, INK, (x + 3, y + 3, 10, 10))
    pygame.draw.rect(surf, GOLD, (x + 3, y + 3, 10, 10), 1)
    draw_text(surf, char, (x + 5, y + 5), WHITE)


class Editor:
    def __init__(self, path=LEVEL_FILE):
        self.path = path
        self.camera = [0.0, 0.0]
        self.selected = "."
        self.show_grid = False
        self.painting = False
        self.last_tile = None
        self.undo_stack = []
        self.unsaved = False
        self.confirm_quit = False
        self.running = True
        self.message = "CTRL+S SAVE  CTRL+Z UNDO  G GRID  RIGHT CLICK PICKS"
        self.swatches = self._build_swatches()
        self._rebuild()
        self._center_on(find_tiles("S")["S"])

    def _build_swatches(self):
        swatches = {}
        for char in TILE_NAMES:
            surf = pygame.Surface((TILE, TILE))
            paint_tile(surf, char, 0, 0)
            if char in MARKERS:
                _draw_marker(surf, char, 0, 0)
            if char in SWATCH_PROPS:
                prop = prop_images()[SWATCH_PROPS[char]][0]
                surf.blit(pygame.transform.scale(prop, (TILE - 2, TILE - 2)), (1, 1))
            swatches[char] = surf
        return swatches

    def _rebuild(self):
        build_map.cache_clear()
        build_props.cache_clear()
        self.map = build_map()

    def _center_on(self, tile):
        self.camera = [tile[0] * TILE - WINDOW[0] / 2, tile[1] * TILE - VIEW_HEIGHT / 2]
        self._clamp_camera()

    def _clamp_camera(self):
        self.camera[0] = min(max(self.camera[0], 0), self.map.get_width() - WINDOW[0])
        self.camera[1] = min(max(self.camera[1], 0), self.map.get_height() - VIEW_HEIGHT)

    def tile_at(self, pos):
        if pos[1] >= VIEW_HEIGHT:
            return None
        x = int((pos[0] + self.camera[0]) // TILE)
        y = int((pos[1] + self.camera[1]) // TILE)
        return (x, y) if 0 <= y < len(LEVEL) and 0 <= x < len(LEVEL[0]) else None

    def swatch_rect(self, index):
        return pygame.Rect(6 + index * SWATCH, PALETTE_Y, TILE + 2, TILE + 2)

    # Editing

    def _write(self, x, y, char):
        LEVEL[y] = LEVEL[y][:x] + char + LEVEL[y][x + 1:]
        # Walls, roofs and foes look at their neighbours, so those repaint too.
        for ny in range(max(0, y - 1), min(len(LEVEL), y + 2)):
            for nx in range(max(0, x - 1), min(len(LEVEL[0]), x + 2)):
                paint_tile(self.map, LEVEL[ny][nx], nx, ny)

    def _ground_near(self, x, y):
        row = LEVEL[y]
        beside = [row[i] for i in (x - 1, x + 1) if 0 <= i < len(row)]
        return next((char for char in beside if char not in SOLID and char not in UNIQUE), ".")

    def set_tile(self, x, y, char):
        current = LEVEL[y][x]
        if current == char:
            return
        if current in UNIQUE:
            self.message = f"{TILE_NAMES[current]} IS HERE. PICK IT UP TO MOVE IT."
            return
        if char in UNIQUE:
            old_x, old_y = find_tiles(char)[char]
            self._write(old_x, old_y, self._ground_near(old_x, old_y))
        self._write(x, y, char)
        self.unsaved = True

    def _paint_line(self, start, end):
        steps = max(abs(end[0] - start[0]), abs(end[1] - start[1]), 1)
        for i in range(steps + 1):
            x = round(start[0] + (end[0] - start[0]) * i / steps)
            y = round(start[1] + (end[1] - start[1]) * i / steps)
            self.set_tile(x, y, self.selected)

    def undo(self):
        if not self.undo_stack:
            self.message = "NOTHING TO UNDO."
            return
        LEVEL[:] = self.undo_stack.pop()
        self._rebuild()
        self.unsaved = True
        self.message = "UNDONE."

    def save(self):
        problems = level_problems()
        if problems:
            self.message = f"NOT SAVED: {problems[0]}"
            return False
        self.path.write_text("\n".join(LEVEL) + "\n")
        self.unsaved = False
        self.message = "SAVED."
        return True

    # Input

    def _click_palette(self, pos):
        for index, char in enumerate(TILE_NAMES):
            if self.swatch_rect(index).collidepoint(pos):
                self.selected = char

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.request_quit()
        elif event.type == pygame.KEYDOWN:
            self._handle_key(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            tile = self.tile_at(event.pos)
            if event.button == 1 and tile is None:
                self._click_palette(event.pos)
            elif event.button == 1:
                self.undo_stack.append(list(LEVEL))
                self.painting, self.last_tile = True, tile
                self.set_tile(*tile, self.selected)
            elif event.button == 3 and tile is not None:
                self.selected = LEVEL[tile[1]][tile[0]]
        elif event.type == pygame.MOUSEMOTION and self.painting:
            tile = self.tile_at(event.pos)
            if tile is not None:
                self._paint_line(self.last_tile, tile)
                self.last_tile = tile
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.painting:
            self.painting = False
            self._rebuild()  # brings back the lantern glow

    def _handle_key(self, event):
        ctrl = event.mod & (pygame.KMOD_CTRL | pygame.KMOD_META)
        if event.key == pygame.K_ESCAPE:
            self.request_quit()
            return
        self.confirm_quit = False
        if ctrl and event.key == pygame.K_s:
            self.save()
        elif ctrl and event.key == pygame.K_z:
            self.undo()
        elif event.key == pygame.K_g:
            self.show_grid = not self.show_grid

    def request_quit(self):
        if self.unsaved and not self.confirm_quit:
            self.confirm_quit = True
            self.message = "UNSAVED CHANGES. PRESS ESC AGAIN TO QUIT."
        else:
            self.running = False

    def update(self, dt, scroll):
        self.camera[0] += scroll[0] * SCROLL_SPEED * dt
        self.camera[1] += scroll[1] * SCROLL_SPEED * dt
        self._clamp_camera()

    # Drawing

    def draw(self, surf, mouse=None):
        surf.fill(SKY[0])
        left, top = int(self.camera[0]), int(self.camera[1])
        surf.blit(self.map, (0, 0), (left, top, WINDOW[0], VIEW_HEIGHT))
        for _, x, y, image in visible_props((left, top), (WINDOW[0], VIEW_HEIGHT)):
            surf.blit(image, (x - left, y - top))
        pygame.draw.rect(surf, INK, (0, VIEW_HEIGHT, WINDOW[0], WINDOW[1] - VIEW_HEIGHT))

        for y, row in enumerate(LEVEL):
            for x, char in enumerate(row):
                if char in MARKERS:
                    _draw_marker(surf, char, x * TILE - left, y * TILE - top)
        if self.show_grid:
            for x in range(-left % TILE, WINDOW[0], TILE):
                pygame.draw.line(surf, STONE[1], (x, 0), (x, VIEW_HEIGHT - 1))
            for y in range(-top % TILE, VIEW_HEIGHT, TILE):
                pygame.draw.line(surf, STONE[1], (0, y), (WINDOW[0] - 1, y))

        hovered = self.tile_at(mouse) if mouse else None
        if hovered:
            pygame.draw.rect(surf, WHITE, (hovered[0] * TILE - left, hovered[1] * TILE - top, TILE, TILE), 1)

        pygame.draw.rect(surf, INK, (0, VIEW_HEIGHT, WINDOW[0], WINDOW[1] - VIEW_HEIGHT))
        for index, char in enumerate(TILE_NAMES):
            rect = self.swatch_rect(index)
            surf.blit(self.swatches[char], (rect.x + 1, rect.y + 1))
            pygame.draw.rect(surf, EMBER[3] if char == self.selected else STONE[1], rect, 1)

        place = f"  ({hovered[0]},{hovered[1]})" if hovered else ""
        star = "  UNSAVED" if self.unsaved else ""
        draw_text(surf, f"{TILE_NAMES[self.selected]}{place}{star}", (6, PALETTE_Y + 21), GOLD)
        draw_text(surf, self.message, (6, PALETTE_Y + 31), BONE)


def read_scroll():
    keys = pygame.key.get_pressed()
    if pygame.key.get_mods() & (pygame.KMOD_CTRL | pygame.KMOD_META):
        return (0, 0)
    return (
        (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a]),
        (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w]),
    )


def main():
    pygame.init()
    pygame.display.set_caption("Pipkin's Meadow: Level Editor")
    window = pygame.display.set_mode(WINDOW, pygame.SCALED | pygame.RESIZABLE)
    clock = pygame.time.Clock()
    editor = Editor()
    while editor.running:
        dt = clock.tick(60) / 1000
        for event in pygame.event.get():
            editor.handle_event(event)
        editor.update(dt, read_scroll())
        editor.draw(window, pygame.mouse.get_pos())
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
