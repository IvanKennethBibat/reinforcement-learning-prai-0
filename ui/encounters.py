"""Who you fight: three slimes in any order, then VESPER in the Great Hall.

Each foe is a slime in its own colour, driven by one of the bots.
"""
from dataclasses import dataclass
from functools import partial
from typing import Callable

from battle.bots import expert_bot, random_bot, scripted_bot
from battle.engine import Move
from ui.characters import draw_slime
from ui.palette import EMBER_SLIME, MOSS_SLIME, TIDE_SLIME, VESPER_SLIME


# What the log says for each foe's moves. A name and its line must fit 24 characters.
MOSS_LINES = {
    Move.ATTACK: "squelches!",
    Move.FIREBOLT: "spits spores!",
    Move.HONE: "soaks up sun.",
    Move.HEAL: "regrows.",
    Move.DEFEND: "goes mossy.",
}
TIDE_LINES = {
    Move.ATTACK: "splashes!",
    Move.FIREBOLT: "sprays water!",
    Move.HONE: "swells up.",
    Move.HEAL: "flows back.",
    Move.DEFEND: "turns to ice.",
}
EMBER_LINES = {
    Move.ATTACK: "scorches!",
    Move.FIREBOLT: "spits lava!",
    Move.HONE: "heats up.",
    Move.HEAL: "rekindles.",
    Move.DEFEND: "hardens.",
}
VESPER_LINES = {
    Move.ATTACK: "crushes down!",
    Move.FIREBOLT: "flings royal goo!",
    Move.HONE: "gathers power.",
    Move.HEAL: "absorbs slime.",
    Move.DEFEND: "puffs up.",
}


@dataclass(frozen=True)
class Encounter:
    name: str
    policy: Callable
    lines: dict
    body: tuple = TIDE_SLIME
    shot: str = "water"  # a key of ui.effects.SHOTS
    is_boss: bool = False

    @property
    def sprite(self):
        return self.name.lower().replace(" ", "_")

    @property
    def draw(self):
        return partial(draw_slime, body=self.body, size=1.2 if self.is_boss else 1.0, crown=self.is_boss)


# Keys match the digits and letters placed on the level map.
ENCOUNTERS = {
    "1": Encounter("MOSS SLIME", random_bot, MOSS_LINES, body=MOSS_SLIME, shot="spores"),
    "2": Encounter("TIDE SLIME", scripted_bot, TIDE_LINES, body=TIDE_SLIME, shot="water"),
    "3": Encounter("EMBER SLIME", expert_bot, EMBER_LINES, body=EMBER_SLIME, shot="lava"),
    # In the game every foe is played by the trained agent; these bots are the fallback.
    "B": Encounter("VESPER", expert_bot, VESPER_LINES, body=VESPER_SLIME, shot="royal", is_boss=True),
}
