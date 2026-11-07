"""Ties the overworld and battles together, with a dithered wipe between them."""
from functools import cache
from pathlib import Path

import numpy as np
import pygame

from agents.dda import DifficultyDirector
from agents.opponent_pool import OpponentPool
from battle.engine import Outcome
from ui import debug, hud
from ui.arena import BAYER, HEIGHT, WIDTH, Arena
from ui.battle_screen import BattleScreen
from ui.encounters import ENCOUNTERS
from ui.overworld import Overworld
from ui.palette import GOLD, INK
from ui.sprites import ASSETS, load_sheet

WIPE_TIME = 0.35


@cache
def _wipe_mask(level):
    """A full-screen ink pattern covering `level` of the 16 dither cells."""
    cell = pygame.Surface((4, 4), pygame.SRCALPHA)
    for y in range(4):
        for x in range(4):
            if BAYER[y][x] < level:
                cell.set_at((x, y), (*INK, 255))
    mask = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for y in range(0, HEIGHT, 4):
        for x in range(0, WIDTH, 4):
            mask.blit(cell, (x, y))
    return mask


def _prepare():
    """Do the slow first-time work now, so nothing hitches during play."""
    Arena()
    for path in ASSETS.glob("*.png"):
        load_sheet(path.stem)
    for level in range(17):
        _wipe_mask(level)


NPC_TABLE = Path(__file__).resolve().parent.parent / "checkpoints" / "npc_seed0.npy"


def load_pool():
    """The trained opponent pool, or None if no Q-table has been trained yet."""
    try:
        return OpponentPool.load(NPC_TABLE)
    except FileNotFoundError:
        return None


class Game:
    def __init__(self, seed=None, pool="trained"):
        self.rng = np.random.default_rng(seed)
        self.pool = load_pool() if pool == "trained" else pool
        # One director for the whole session, so difficulty follows the player across fights.
        self.director = DifficultyDirector(len(self.pool)) if self.pool else None
        self.debug = False
        _prepare()
        self.new_game()

    def new_game(self):
        self.world = Overworld()
        self.battle = None
        self.fight = None
        self.finished = False
        self.wipe = None  # seconds into a wipe, while one is running
        self.wipe_action = None

    def _start_wipe(self, action):
        self.wipe, self.wipe_action = 0.0, action

    def npc_for(self, foe):
        """The trained agent at the DDA's tier, or the foe's own bot without a pool.

        The boss plays one tier above the rest.
        """
        if self.pool is None:
            return foe.policy
        tier = min(len(self.pool) - 1, self.director.tier + (1 if foe.is_boss else 0))
        return self.pool.policy(tier)

    def _begin_fight(self, key):
        foe = ENCOUNTERS[key]
        self.fight = key
        self.battle = BattleScreen(
            opponent=self.npc_for(foe),
            seed=int(self.rng.integers(2**31)),
            encounter=foe,
            on_finish=self._fight_over,
            on_rematch=self._rematch,
            director=self.director,
        )
        self.battle.debug = self.debug

    def _record(self, outcome):
        if self.director is not None:
            self.director.record(outcome)

    def _fight_over(self, outcome):
        self._record(outcome)
        self._start_wipe(lambda: self._leave_fight(outcome))

    def _rematch(self, outcome):
        self._record(outcome)
        if outcome == Outcome.WIN:
            self.world.defeated.add(self.fight)
        self._begin_fight(self.fight)

    def _leave_fight(self, outcome):
        key, won = self.fight, outcome == Outcome.WIN
        self.world.resolve_fight(key, won)
        self.battle = self.fight = None
        self.finished = ENCOUNTERS[key].is_boss and key in self.world.defeated

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            self.debug = not self.debug
            if self.battle:
                self.battle.debug = self.debug
            return
        if self.wipe is not None:
            return
        if self.battle:
            self.battle.handle_event(event)
        elif self.finished and event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.new_game()
    def update(self, dt, move=(0, 0)):
        if self.wipe is not None:
            before = self.wipe
            self.wipe += dt
            if before < WIPE_TIME <= self.wipe:
                self.wipe_action()
            if self.wipe >= WIPE_TIME * 2:
                self.wipe = None
            return

        if self.battle:
            self.battle.update(dt)
        elif not self.finished:
            key = self.world.update(dt, move)
            if key is not None:
                self._start_wipe(lambda: self._begin_fight(key))

    def draw(self, surf):
        if self.battle:
            self.battle.draw(surf)
        else:
            self.world.draw(surf)
            if self.finished:
                hud.draw_banner(surf, "HOORAY!", GOLD, "THE VALLEY IS SAFE. PRESS ENTER")
            if self.debug:
                debug.draw_world_overlay(surf, self.director)
        if self.wipe is not None:
            k = 1 - abs(self.wipe / WIPE_TIME - 1)
            surf.blit(_wipe_mask(round(max(0.0, k) * 16)), (0, 0))
