"""Play the game: ``python -m ui``."""
import asyncio
import statistics
import time
from collections import deque

import pygame

from ui.arena import HEIGHT, WIDTH
from ui.game import Game

STEP = 1 / 60         # the game always advances in steps of this size
MAX_FRAME = 0.1       # after a long pause, don't try to catch up


COMMON_RATES = (30, 50, 60, 75, 90, 100, 120, 144, 165, 240)


def _settle_rate(gap):
    """The refresh rate a typical frame gap points at, snapped to a common screen rate."""
    rate = 1 / gap
    nearest = min(COMMON_RATES, key=lambda common: abs(common - rate))
    return nearest if abs(nearest - rate) < nearest * 0.1 else rate


class FixedStep:
    """Turns uneven frame times into a whole number of equal game steps.

    Equal steps mean Pipkin moves the same number of pixels every frame, on any
    monitor, which is what keeps scrolling smooth.

    Each frame counts as exactly one refresh of the screen. The OS often reports
    flips unevenly (one returns at once, the next waits two refreshes) even though
    the screen shows every frame on time, and trusting those times makes the game
    hold some frames for one refresh and others for three. Real time is still
    tracked, and when it drifts more than 1.5 refreshes away, because frames really
    were dropped or the game was paused, the difference is made up in whole refreshes.
    The refresh rate is measured from the last second or so of frames, so it also works in a browser.
    """

    def __init__(self, refresh_rate=60):
        self.refresh = 1 / (refresh_rate or 60)
        self.lag = 0.0                    # real time minus the time the game has counted
        self.banked = STEP / 4            # start between steps, away from the rounding edge
        self.recent = deque(maxlen=60)

    def steps_for(self, frame_time):
        frame_time = min(frame_time, MAX_FRAME)
        self.recent.append(frame_time)
        if len(self.recent) == self.recent.maxlen:
            typical = statistics.fmean(self.recent)
            if typical > 0:
                self.refresh = 1 / _settle_rate(typical)
        shown = self.refresh
        self.lag += frame_time - shown
        if abs(self.lag) > 1.5 * self.refresh:
            shown = max(0.0, shown + round(self.lag / self.refresh) * self.refresh)
            self.lag -= shown - self.refresh
        self.banked += shown
        steps = int(self.banked / STEP + 1e-9)
        self.banked -= steps * STEP
        return steps


def refresh_rate():
    """The screen's refresh rate in hertz, or 60 when it can't be read (e.g. in a browser)."""
    try:
        return pygame.display.get_current_refresh_rate() or 60
    except (AttributeError, pygame.error):
        return 60


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
    stepper = FixedStep(refresh_rate())
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
