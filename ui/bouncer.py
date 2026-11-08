"""How slimes get around the map: short hops near home, with a squash each side."""
import math
import random

HOP_TIME = 0.38
HOP_SPEED = 34
HOP_HEIGHT = 9
SQUASH_TIME = 0.14   # how long it crouches before a hop and after landing
LEASH = 36           # how far a slime strays from home

# Columns of a slime's walk sheet.
REST, SQUASHED, STRETCHED = 0, 1, 2


class Bouncer:
    def __init__(self, spot, seed):
        self.rng = random.Random(seed)
        self.pos = list(spot)
        self.home = tuple(spot)
        self.heading = (0.0, 0.0)
        self.hop_time = None  # seconds into the current hop, or None when grounded
        self.rest = self.rng.uniform(0.2, 2.0)
        self.landed = SQUASH_TIME  # seconds since it last touched down

    @property
    def lift(self):
        if self.hop_time is None:
            return 0
        return round(math.sin(self.hop_time / HOP_TIME * math.pi) * HOP_HEIGHT)

    @property
    def frame(self):
        if self.hop_time is not None:
            return STRETCHED
        if self.rest < SQUASH_TIME or self.landed < SQUASH_TIME:
            return SQUASHED
        return REST

    def _leap(self):
        if math.dist(self.pos, self.home) > LEASH * 0.6:
            angle = math.atan2(self.home[1] - self.pos[1], self.home[0] - self.pos[0])
            angle += self.rng.uniform(-0.5, 0.5)
        else:
            angle = self.rng.uniform(0, math.tau)
        self.heading = (math.cos(angle), math.sin(angle))
        self.hop_time = 0.0

    def update(self, dt, blocked):
        if self.hop_time is None:
            self.landed += dt
            self.rest -= dt
            if self.rest <= 0:
                self._leap()
            return

        self.hop_time += dt
        x = self.pos[0] + self.heading[0] * HOP_SPEED * dt
        y = self.pos[1] + self.heading[1] * HOP_SPEED * dt
        if not blocked(x, y) and math.dist((x, y), self.home) <= LEASH:
            self.pos = [x, y]
        if self.hop_time >= HOP_TIME:
            self.hop_time = None
            self.landed = 0.0
            self.rest = self.rng.uniform(0.5, 2.2)
