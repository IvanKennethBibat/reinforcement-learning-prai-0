"""The battle screen: runs a fight on the real engine and animates each turn.

The engine resolves a turn instantly, so ``choose`` calls ``resolve_turn`` and
then plays the returned results back as a timed script. Scripts are generators:
each ``yield`` hands back control until the next frame and receives the frame's
elapsed time.
"""
import math

import numpy as np
import pygame

from battle.bots import scripted_bot
from battle.engine import (
    Battler, Move, Outcome, battle_over, legal_moves, resolve_turn,
)
from ui import hud
from ui.arena import HEIGHT, WIDTH, Arena
from ui.characters import CANVAS, ROOT
from ui.effects import SHOTS, Effects, draw_ward
from ui.encounters import ENCOUNTERS
from ui.palette import BONE, DANGER, EMBER, GOLD, INK, SPIRIT, WHITE
from ui.sprites import load_sheet

HEAL_POTIONS = 3

# What the log says for Pipkin's moves. Each foe's lines are in ui/encounters.py.
PIPKIN_LINES = {
    Move.ATTACK: "strikes!",
    Move.FIREBOLT: "swipes!",
    Move.HONE: "sharpens claws.",
    Move.HEAL: "heals.",
    Move.DEFEND: "blocks.",
}

BANNERS = {
    Outcome.WIN: ("VICTORY", GOLD),
    Outcome.LOSS: ("DEFEAT", DANGER[1]),
    Outcome.DRAW: ("DRAW", BONE),
}


class Fighter:
    def __init__(self, name, battler, sheet, feet, facing, lines):
        self.name = name
        self.battler = battler
        self.sheet = sheet
        self.lines = lines
        self.feet = feet
        self.facing = facing
        self.time = 0.0
        self.offset = [0.0, 0.0]
        self.flash = 0.0
        self.warding = False
        self.tip = feet
        self.pose = "idle"
        self.set_pose("idle", 0)
        self.shown_hp = self.trail_hp = self.target_hp = battler.hp
        self.shown_mana = battler.mana
        self.shown_honed = False

    @property
    def chest(self):
        return (self.feet[0] + self.offset[0], self.feet[1] + self.offset[1] - 28)

    def set_pose(self, name, blend=0.1):
        self.pose_from, self.pose_to = self.pose, name
        self.blend, self.blend_time = 0.0, blend
        self.progress = 0.0 if blend else 1.0

    def update(self, dt):
        self.time += dt
        self.flash = max(0.0, self.flash - dt)
        self.blend = min(self.blend_time, self.blend + dt)
        self.progress = self.blend / self.blend_time if self.blend_time else 1.0
        # Sprites can't blend, so swap to the new pose halfway through.
        self.pose = self.pose_to if self.progress >= 0.5 else self.pose_from

        self.shown_hp += (self.target_hp - self.shown_hp) * min(1.0, dt * 9)
        if self.trail_hp > self.shown_hp:
            self.trail_hp = max(self.shown_hp, self.trail_hp - 34 * dt)
        else:
            self.trail_hp = self.shown_hp
        self.shown_mana += (self.battler.mana - self.shown_mana) * min(1.0, dt * 9)

    def draw(self, surf):
        x = self.feet[0] + self.offset[0]
        y = self.feet[1] + self.offset[1]

        shadow = pygame.Surface((44, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (*INK, 150), shadow.get_rect())
        surf.blit(shadow, (x - 22, y - 5))

        column = self.sheet.column_at(self.time)
        image = self.sheet.frames[self.pose][column]
        # The sprite swaps at once, but effects following the tip still glide.
        start = self.sheet.tips[self.pose_from][column]
        end = self.sheet.tips[self.pose_to][column]
        tip = pygame.Vector2(start).lerp(end, self.progress)
        root_x = ROOT[0]
        if self.facing < 0:
            image = pygame.transform.flip(image, True, False)
            root_x = CANVAS[0] - ROOT[0]
            tip = (CANVAS[0] - tip[0], tip[1])
        if self.flash > 0 and int(self.flash * 30) % 2 == 0:
            image = pygame.mask.from_surface(image).to_surface(setcolor=WHITE, unsetcolor=(0, 0, 0, 0))
        left, top = x - root_x, y - ROOT[1]
        surf.blit(image, (left, top))
        self.tip = (left + tip[0], top + tip[1])

        if self.warding:
            draw_ward(surf, self.chest, self.facing, self.time)


class BattleScreen:
    def __init__(self, opponent=scripted_bot, seed=None, encounter=ENCOUNTERS["B"], on_finish=None):
        self.opponent = opponent
        self.encounter = encounter
        self.goo = encounter.body[1:]
        self.on_finish = on_finish
        self.arena = Arena()
        self.rng = np.random.default_rng(seed)
        self.world = pygame.Surface((WIDTH, HEIGHT))
        self.reset()

    def reset(self):
        self.player = Fighter(
            "PIPKIN",
            Battler(heal_potions=HEAL_POTIONS),
            load_sheet("cat"), (72, 130), 1, PIPKIN_LINES,
        )
        self.foe = Fighter(
            self.encounter.name, Battler(), load_sheet(self.encounter.sprite), (246, 110), -1, self.encounter.lines,
        )
        self.effects = Effects()
        self.turn = 0
        self.selected = Move.ATTACK
        self.outcome = None
        self.script = None
        self.shake = 0.0
        self.log = []

    @property
    def accepting(self):
        return self.script is None and self.outcome is None

    def choose(self, move):
        if not self.accepting or move not in legal_moves(self.player.battler):
            return
        foe_move = self.opponent(self.foe.battler, self.player.battler, self.rng)
        was_honed = self.player.battler.honed, self.foe.battler.honed
        results = resolve_turn(self.player.battler, self.foe.battler, move, foe_move, self.rng)
        self.turn += 1
        self.log = []
        self.script = self._play_turn(results, was_honed)
        next(self.script)

    def handle_event(self, event):
        if self.outcome is not None:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.on_finish:
                    self.on_finish(self.outcome)
                else:
                    self.reset()
            return
        if not self.accepting:
            return
        if event.type == pygame.KEYDOWN:
            steps = {pygame.K_LEFT: -1, pygame.K_a: -1, pygame.K_RIGHT: 1, pygame.K_d: 1,
                     pygame.K_UP: -2, pygame.K_w: -2, pygame.K_DOWN: 2, pygame.K_s: 2}
            if event.key in steps:
                index = int(self.selected) + steps[event.key]
                if 0 <= index < len(Move):
                    self.selected = Move(index)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.choose(self.selected)
            elif pygame.K_1 <= event.key < pygame.K_1 + len(Move):
                self.selected = Move(event.key - pygame.K_1)
                self.choose(self.selected)
        elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            for move in Move:
                if hud.command_rect(move).collidepoint(event.pos):
                    self.selected = move
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self.choose(move)

    def update(self, dt):
        self.arena.update(dt)
        self.player.update(dt)
        self.foe.update(dt)
        self.effects.update(dt)
        self.shake = max(0.0, self.shake - dt * 14)
        for fighter in (self.player, self.foe):
            if fighter.shown_honed:
                self.effects.trail(fighter.tip, (GOLD, EMBER[3]))
        if self.script is not None:
            try:
                self.script.send(dt)
            except StopIteration:
                self.script = None
                self.outcome = battle_over(self.player.battler, self.foe.battler, self.turn)

    def draw(self, surf):
        world = self.world
        self.arena.draw_back(world)
        self.foe.draw(world)
        self.player.draw(world)
        self.effects.draw(world)
        self.arena.draw_front(world)
        self.effects.draw_floaters(world)

        jolt = int(self.shake) * (1 if int(self.arena.time * 40) % 2 else -1)
        surf.fill(INK)
        surf.blit(world, (jolt, 0))

        hud.draw_plate(surf, self.player, 3)
        hud.draw_plate(surf, self.foe, WIDTH - 115)
        hud.draw_turn(surf, self.turn + 1 if self.accepting else self.turn)
        hud.draw_panel(surf, self.selected, legal_moves(self.player.battler), self.log, self.accepting,
                       self.player.battler)
        if self.outcome is not None:
            title, color = BANNERS[self.outcome]
            subtitle = "PRESS ENTER TO CONTINUE" if self.on_finish else "PRESS ENTER TO FIGHT AGAIN"
            hud.draw_banner(surf, title, color, subtitle)

    # Turn playback. Order follows the engine: Defend, then Heal, then the rest.

    def _say(self, fighter, move):
        self.log.append(f"{fighter.name} {fighter.lines[move]}")

    def _wait(self, seconds):
        elapsed = 0.0
        while elapsed < seconds:
            elapsed += yield

    def _tween_offset(self, fighter, target, seconds):
        start = list(fighter.offset)
        elapsed = 0.0
        while elapsed < seconds:
            elapsed += yield
            k = min(1.0, elapsed / seconds)
            fighter.offset = [start[0] + (target[0] - start[0]) * k, start[1] + (target[1] - start[1]) * k]

    def _play_turn(self, results, was_honed):
        player, foe = self.player, self.foe
        sides = [
            (player, foe, results["move_a"], results["healed_a"], results["damage_to_b"], was_honed[0]),
            (foe, player, results["move_b"], results["healed_b"], results["damage_to_a"], was_honed[1]),
        ]

        defenders = [side[0] for side in sides if side[2] == Move.DEFEND]
        for fighter in defenders:
            fighter.set_pose("defend")
            fighter.warding = True
            self._say(fighter, Move.DEFEND)
        if defenders:
            yield from self._wait(0.4)

        healers = [side for side in sides if side[2] == Move.HEAL]
        for fighter, _, _, healed, _, _ in healers:
            fighter.set_pose("heal", 0.15)
            fighter.target_hp += healed
            self.effects.rise(fighter.chest, SPIRIT)
            self.effects.floater(f"+{healed}", fighter.chest, SPIRIT[2])
            self._say(fighter, Move.HEAL)
        if healers:
            yield from self._wait(0.7)
            for fighter, *_ in healers:
                fighter.set_pose("idle", 0.15)

        for fighter, target, move, _, damage, honed in sides:
            if move == Move.HONE:
                yield from self._play_hone(fighter)
            elif move == Move.ATTACK:
                yield from self._play_attack(fighter, target, damage, honed, move)
            elif move == Move.FIREBOLT:
                if fighter is player:
                    yield from self._play_attack(fighter, target, damage, honed, move)
                else:
                    yield from self._play_shot(fighter, target, damage, honed)

        for fighter in (player, foe):
            fighter.warding = False
            fighter.shown_honed = fighter.battler.honed
            fighter.set_pose("ko" if fighter.battler.is_ko else "idle", 0.3)
        yield from self._wait(0.35)

    def _play_hone(self, fighter):
        self._say(fighter, Move.HONE)
        fighter.set_pose("hone", 0.15)
        yield from self._wait(0.15)
        self.effects.rise(fighter.tip, (GOLD, EMBER[3], WHITE), count=16, spread=4)
        yield from self._wait(0.5)
        fighter.set_pose("idle", 0.15)

    def _play_attack(self, fighter, target, damage, honed, move):
        self._say(fighter, move)
        reach = (
            target.feet[0] - fighter.feet[0] - fighter.facing * 44,
            target.feet[1] - fighter.feet[1],
        )
        fighter.set_pose("windup", 0.12)
        yield from self._wait(0.16)
        yield from self._tween_offset(fighter, reach, 0.14)
        fighter.set_pose("strike", 0.06)
        yield from self._wait(0.06)
        self.effects.slash(target.chest, -target.facing)
        self._land_hit(target, damage, honed, (BONE, WHITE, DANGER[1]))
        yield from self._wait(0.24)
        fighter.set_pose("idle", 0.15)
        yield from self._tween_offset(fighter, (0, 0), 0.16)
        self._settle(target)

    def _play_shot(self, fighter, target, damage, honed):
        self._say(fighter, Move.FIREBOLT)
        shot = SHOTS[self.encounter.shot]
        fighter.set_pose("cast", 0.16)
        yield from self._wait(0.26)
        start, end = fighter.tip, target.chest
        radius = (9 if honed else 6) * shot.size
        elapsed = 0.0
        while elapsed < shot.flight:
            elapsed += yield
            k = min(1.0, elapsed / shot.flight)
            head = (
                start[0] + (end[0] - start[0]) * k,
                start[1] + (end[1] - start[1]) * k
                - math.sin(k * math.pi) * shot.arc + math.sin(k * math.tau * 1.5) * shot.sway,
            )
            self.effects.bolt = (head, radius, self.goo, fighter.facing, shot)
            self.effects.burst(head, self.goo, count=shot.spray, speed=18, gravity=shot.spray_gravity)
        self.effects.bolt = None
        self.effects.burst(end, self.goo, count=shot.splash, speed=shot.splash_speed)
        self._land_hit(target, damage, honed, self.goo)
        yield from self._wait(0.26)
        fighter.set_pose("idle", 0.15)
        self._settle(target)

    def _land_hit(self, target, damage, honed, colors):
        target.target_hp -= damage
        target.flash = 0.2
        target.set_pose("hurt", 0.05)
        self.shake = 5 if honed else 3
        self.effects.burst(target.chest, colors, count=12)
        self.effects.floater(str(damage), target.chest, GOLD if honed else WHITE, 2 if honed else 1)

    def _settle(self, target):
        target.set_pose("defend" if target.warding else "idle", 0.15)
