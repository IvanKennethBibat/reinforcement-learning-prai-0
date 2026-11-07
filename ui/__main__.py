"""Play the game: ``python -m ui``."""
import asyncio
import time

import pygame

from ui.arena import HEIGHT, WIDTH
from ui.game import Game

STEP = 1 / 60         # the game always advances in steps of this size
SNAP = 0.002          # frames this close to one step count as exactly one
MAX_FRAME = 0.1       # after a long pause, don't try to catch up


class FixedStep:
    """Turns uneven frame times into a whole number of equal game steps.

    Equal steps mean Pipkin moves the same number of pixels every frame, on any
    monitor, which is what keeps scrolling smooth.
    """

    def __init__(self):
        self.banked = 0.0

    def steps_for(self, frame_time):
        frame_time = min(frame_time, MAX_FRAME)
        if abs(frame_time - STEP) < SNAP:
            frame_time = STEP
        self.banked += frame_time
        steps = int(self.banked / STEP + 1e-9)
        self.banked -= steps * STEP
        return steps


def read_movement():
    keys = pygame.key.get_pressed()
    return (
        (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a]),
        (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w]),
    )


def open_window():
    flags = pygame.SCALED | pygame.RESIZABLE
    try:
        return pygame.display.set_mode((WIDTH, HEIGHT), flags, vsync=1)
    except pygame.error:  # not every display can do vsync
        return pygame.display.set_mode((WIDTH, HEIGHT), flags)


async def main():
    pygame.init()
    pygame.display.set_caption("Pipkin's Meadow")
    window = open_window()
    game = Game()
    stepper = FixedStep()
    last = time.perf_counter()

    running = True
    while running:
        now = time.perf_counter()
        frame_time, last = now - last, now
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            else:
                game.handle_event(event)
        movement = read_movement()
        for _ in range(stepper.steps_for(frame_time)):
            game.update(STEP, movement)
        game.draw(window)
        pygame.display.flip()
        await asyncio.sleep(0)  # hands control back to the browser; harmless on desktop
    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
