"""The cat and the slimes, drawn from poses. This is the source of the battle sprites.

Each character has a ``draw_*`` function that paints one frame from a ``Pose``.
The game doesn't call these directly: ``ui.bake_sprites`` renders them to sheets.
All face right here; the battle screen flips the foe to face left.
"""
from dataclasses import dataclass
import math

import pygame

from ui.palette import CLOTH, DANGER, EAR, EMBER, FUR, GOLD, INK, TIDE_SLIME, WHITE

CANVAS = (136, 112)
ROOT = (46, 104)  # where the feet touch the ground on the canvas
CAT_SWAY = 3.0  # speed of the tail and scarf, radians per second
SLIME_SWAY = 2.4  # speed of the idle wobble, radians per second


@dataclass(frozen=True)
class Pose:
    x: float = 0.0        # body offset, forward is positive
    y: float = 0.0        # body offset, down is positive
    lean: float = 0.0     # how far the shoulders sit ahead of the hips
    crouch: float = 0.0   # how far the hips drop
    stride: float = 5.0   # distance of each foot from the centre
    arm: float = 0.5      # weapon arm, radians forward from hanging straight down
    off_arm: float = -0.2 # other arm, same convention
    weapon: float = 0.5   # weapon, radians forward from pointing straight up
    glow: float = 0.0     # eye and weapon intensity, 0 to 1


# For the cat, `arm` is the foreleg and `weapon` raises the tail.
CAT_POSES = {
    "idle": Pose(arm=0.08, off_arm=-0.05),
    "windup": Pose(x=-4, lean=-3, crouch=7, arm=0.1, off_arm=0.0, weapon=0.5),
    "strike": Pose(x=8, lean=7, crouch=2, arm=1.6, off_arm=0.9, weapon=-0.4),
    "cast": Pose(lean=1, arm=0.1, off_arm=0.0, weapon=0.7, glow=1),
    "hone": Pose(crouch=3, arm=1.5, off_arm=0.0, weapon=0.3, glow=1),
    "heal": Pose(crouch=2, arm=0.2, off_arm=0.3, weapon=0.2, glow=0.6),
    "defend": Pose(x=-2, lean=-2, crouch=6, arm=0.1, off_arm=0.0, weapon=-0.2),
    "hurt": Pose(x=-3, lean=-5, crouch=3, arm=0.6, off_arm=0.6, weapon=-0.1),
    "ko": Pose(x=4, lean=6, crouch=16, arm=1.2, off_arm=1.1, weapon=-0.5),
}

# For slimes, `crouch` squashes the body and `lean` shears it towards the foe.
SLIME_POSES = {
    "idle": Pose(),
    "windup": Pose(x=-3, lean=-5, crouch=9),
    "strike": Pose(x=9, lean=10, crouch=-3),
    "cast": Pose(crouch=-5, glow=1),
    "hone": Pose(crouch=5, glow=1),
    "heal": Pose(crouch=-3, glow=0.6),
    "defend": Pose(x=-2, crouch=8),
    "hurt": Pose(x=-6, lean=-7, crouch=5),
    "ko": Pose(crouch=16),
}

def _limb(surf, start, end, width, color, light=None):
    pygame.draw.line(surf, color, start, end, width)
    pygame.draw.circle(surf, color, end, max(1, width // 2))
    if light:
        pygame.draw.line(surf, light, (start[0], start[1] - 1), (end[0], end[1] - 1))


def _reach(origin, angle, length):
    """A point `length` away from origin; angle 0 is down, forward is positive."""
    return (origin[0] + math.sin(angle) * length, origin[1] + math.cos(angle) * length)


def _blade_tip(origin, angle, length):
    """As _reach, but angle 0 is straight up."""
    return (origin[0] + math.sin(angle) * length, origin[1] - math.cos(angle) * length)


def _outlined(surf):
    """Wrap the figure in a one-pixel ink outline."""
    silhouette = pygame.mask.from_surface(surf).to_surface(setcolor=(*INK, 255), unsetcolor=(0, 0, 0, 0))
    framed = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for offset in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        framed.blit(silhouette, offset)
    framed.blit(surf, (0, 0))
    return framed


def draw_cat(pose: Pose, time: float = 0.0):
    """PIPKIN: a small black cat in a teal scarf, who casts through the tail."""
    surf = pygame.Surface(CANVAS, pygame.SRCALPHA)
    root_x, root_y = ROOT[0] + pose.x, ROOT[1] + pose.y
    swish = math.sin(time * CAT_SWAY)
    phase = time * CAT_SWAY / math.tau % 1
    breath = 1 if phase < 0.5 else 0
    blink = 0.6 <= phase < 0.7

    hip = (root_x - 7 + pose.lean * 0.3, root_y - 13 + pose.crouch * 0.6)
    chest = (root_x + 4 + pose.lean * 0.8, root_y - 25 + pose.crouch)
    head = (chest[0] + 5 + pose.lean * 0.5, chest[1] - 15 + pose.crouch * 0.2 + breath)
    shoulder = (chest[0] + 3, chest[1] + 3)

    # Tail: three bending segments, curling up behind the body.
    base = (hip[0] - 9, hip[1] + 8)
    bend = -0.9 + pose.weapon + swish * 0.12
    mid = _blade_tip(base, bend, 13)
    upper = _blade_tip(mid, bend + 0.45, 12)
    tip = _blade_tip(upper, bend + 1.0, 10)
    pygame.draw.line(surf, FUR[0], base, mid, 5)
    pygame.draw.line(surf, FUR[0], mid, upper, 4)
    pygame.draw.line(surf, FUR[1], upper, tip, 3)
    pygame.draw.circle(surf, FUR[0], mid, 2)
    pygame.draw.circle(surf, FUR[0], upper, 2)
    if pose.glow > 0.3:
        pygame.draw.circle(surf, EMBER[2], tip, 3)
        pygame.draw.circle(surf, EMBER[3], tip, 1)

    # Far foreleg.
    far_shoulder = (shoulder[0] - 4, shoulder[1])
    elbow = _reach(far_shoulder, pose.off_arm, 11)
    paw = _reach(elbow, pose.off_arm + 0.1, 10)
    _limb(surf, far_shoulder, elbow, 6, FUR[0])
    _limb(surf, elbow, paw, 5, FUR[0])

    # Haunch and body.
    pygame.draw.ellipse(surf, FUR[0], (hip[0] - 13, hip[1] - 11, 25, 24))
    pygame.draw.polygon(surf, FUR[0], [
        (hip[0] - 9, hip[1] - 8), (chest[0] - 7, chest[1] - 4), (chest[0] + 8, chest[1] - 2),
        (chest[0] + 8, chest[1] + 11), (hip[0] + 9, hip[1] + 11),
    ])
    pygame.draw.line(surf, FUR[1], (hip[0] - 7, hip[1] - 9), (chest[0] - 6, chest[1] - 3), 2)
    pygame.draw.arc(surf, FUR[2], (hip[0] - 11, hip[1] - 9, 20, 18), 1.0, 2.6)
    pygame.draw.rect(surf, FUR[1], (hip[0] - 4, root_y - 3, 13, 3))

    # Near foreleg.
    elbow = _reach(shoulder, pose.arm, 11)
    paw = _reach(elbow, pose.arm + 0.1, 11)
    _limb(surf, shoulder, elbow, 7, FUR[0], FUR[1])
    _limb(surf, elbow, paw, 6, FUR[0], FUR[1])
    pygame.draw.circle(surf, FUR[1], paw, 3)

    # Scarf: knotted at the throat, the end streaming behind.
    pygame.draw.polygon(surf, CLOTH[1], [
        (chest[0] - 8, chest[1] - 6), (chest[0] + 9, chest[1] - 5),
        (chest[0] + 10, chest[1] + 1), (chest[0] - 8, chest[1] + 1),
    ])
    pygame.draw.line(surf, CLOTH[2], (chest[0] - 7, chest[1] - 5), (chest[0] + 8, chest[1] - 4))
    tail_y = chest[1] - 2 + swish * 2
    pygame.draw.polygon(surf, CLOTH[0], [
        (chest[0] - 7, chest[1] - 4), (chest[0] - 7, chest[1] + 1),
        (chest[0] - 18, tail_y + 5), (chest[0] - 21, tail_y - 1),
    ])
    pygame.draw.circle(surf, GOLD, (chest[0] + 7, chest[1] - 1), 2)

    # Head: wide cheeks, rounded ears and big amber eyes.
    for side, inner in ((-1, FUR[1]), (1, EAR)):
        ear = head[0] + side * 7
        pygame.draw.polygon(surf, FUR[0], [(ear - 6, head[1] - 5), (ear + side * 2, head[1] - 19), (ear + 6, head[1] - 5)])
        pygame.draw.polygon(surf, inner, [(ear - 3, head[1] - 7), (ear + side * 2, head[1] - 15), (ear + 3, head[1] - 7)])
    pygame.draw.ellipse(surf, FUR[0], (head[0] - 13, head[1] - 10, 26, 21))
    pygame.draw.arc(surf, FUR[2], (head[0] - 11, head[1] - 9, 20, 16), 1.2, 2.5)

    if pose.crouch >= 12 or (blink and not pose.glow):  # knocked out or blinking: eyes shut
        pygame.draw.line(surf, FUR[2], (head[0] - 5, head[1]), (head[0] - 1, head[1] + 1))
        pygame.draw.line(surf, FUR[2], (head[0] + 4, head[1] + 1), (head[0] + 8, head[1]))
    else:
        iris = EMBER[3] if pose.glow > 0.3 else EMBER[2]
        for eye_x in (int(head[0]) - 5, int(head[0]) + 4):
            eye_y = int(head[1]) - 3
            pygame.draw.rect(surf, iris, (eye_x, eye_y + 1, 5, 3))
            pygame.draw.line(surf, iris, (eye_x + 1, eye_y), (eye_x + 3, eye_y))
            pygame.draw.line(surf, iris, (eye_x + 1, eye_y + 4), (eye_x + 3, eye_y + 4))
            pygame.draw.rect(surf, INK, (eye_x + 2, eye_y + 1, 2, 3))
            surf.set_at((eye_x + 2, eye_y + 1), WHITE)
    pygame.draw.polygon(surf, EAR, [(head[0] + 1, head[1] + 3), (head[0] + 4, head[1] + 3), (head[0] + 2, head[1] + 5)])
    for dy in (2, 5):
        pygame.draw.line(surf, FUR[2], (head[0] + 10, head[1] + 3), (head[0] + 17, head[1] + dy))
        pygame.draw.line(surf, FUR[2], (head[0] - 9, head[1] + 3), (head[0] - 15, head[1] + dy))

    return _outlined(surf), tip


def draw_slime(pose: Pose, time: float = 0.0, body=TIDE_SLIME, size=1.0, crown=False):
    """A soft dome of jelly with a darker heart. Squashes and stretches to move."""
    surf = pygame.Surface(CANVAS, pygame.SRCALPHA)
    wobble = math.sin(time * SLIME_SWAY) * 1.5
    base = ROOT[1] + pose.y
    cx = ROOT[0] + pose.x
    half = 25 * size + pose.crouch * 0.7 + wobble
    height = max(8, 40 * size - pose.crouch * 1.5 - wobble * 1.4)

    def dome(inset, squeeze=1.0, lift=0):
        points = []
        for i in range(25):
            angle = math.pi * i / 24
            rise = math.sin(angle) ** 0.75
            points.append((
                cx + math.cos(angle) * (half - inset) + pose.lean * rise,
                base - lift - rise * (height - inset) * squeeze,
            ))
        points += [(cx - half + inset + 4, base - lift + 1), (cx + half - inset - 4, base - lift + 1)]
        return points

    pygame.draw.polygon(surf, body[0], dome(0))
    pygame.draw.polygon(surf, body[2], dome(2))
    pygame.draw.polygon(surf, body[1], dome(7, squeeze=0.72, lift=1))

    # Light on the upper-left shoulder, plus a wet glint.
    rim = dome(3)[10:21]
    pygame.draw.lines(surf, body[3], False, rim, 2)
    glint = dome(8)[16]
    pygame.draw.rect(surf, WHITE, (glint[0], glint[1], 4, 2))
    surf.set_at((int(glint[0]) + 6, int(glint[1]) + 3), WHITE)

    top_x = cx + pose.lean
    face_y = base - height * 0.46
    face_x = cx + pose.lean * 0.6 + half * 0.26
    if pose.crouch >= 14:  # defeated: eyes shut
        for eye_x in (face_x - 7, face_x + 7):
            pygame.draw.line(surf, INK, (eye_x - 3, face_y), (eye_x + 3, face_y), 2)
    else:
        for eye_x in (face_x - 7, face_x + 7):
            pygame.draw.rect(surf, INK, (eye_x - 2, face_y - 4, 5, 8))
            color = EMBER[3] if pose.glow > 0.3 else WHITE
            pygame.draw.rect(surf, color, (eye_x - 1, face_y - 3, 2, 2))
        pygame.draw.lines(surf, INK, False, [(face_x - 2, face_y + 6), (face_x, face_y + 7), (face_x + 2, face_y + 6)])

    tip = (top_x, base - height - 3)
    if crown:
        crown_y = base - height + 2
        points = [(top_x - 11, crown_y), (top_x - 13, crown_y - 11), (top_x - 6, crown_y - 5), (top_x, crown_y - 14),
                  (top_x + 6, crown_y - 5), (top_x + 13, crown_y - 11), (top_x + 11, crown_y)]
        pygame.draw.polygon(surf, GOLD, points)
        pygame.draw.line(surf, EMBER[3], (top_x - 10, crown_y - 2), (top_x + 10, crown_y - 2))
        pygame.draw.rect(surf, DANGER[1], (top_x - 1, crown_y - 7, 3, 3))
        tip = (top_x, crown_y - 16)
    return _outlined(surf), tip
