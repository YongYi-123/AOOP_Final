"""Original 64px chibi cels. Rounded pixel contours, not scaled legacy bodies.

Every pose shares a (32, 59) ground anchor. The larger heads are presentation
only: combat still uses the original world-space lanes and body separation.
"""
import math
import pygame
from .data import ROSTER, ATTACKS
from .outfits import outfit_for, BOSS_NAMES

INK = (19, 20, 43)
WHITE = (239, 250, 250)
SKIN = (246, 194, 155)
SHADE = (211, 137, 132)


def mix(a, b, weight=.5):
    return tuple(round(x*(1-weight)+y*weight) for x, y in zip(a, b))


def fighter_cel(name, state, frame, outfit=0):
    s = pygame.Surface((64, 64), pygame.SRCALPHA)
    frame %= 8
    boss = name in BOSS_NAMES
    heavy = name in ('BRUNO', 'bruiser', 'shield', 'security', 'RELAY', 'NULL')
    fast = name in ('NOVA', 'runner', 'duelist', 'cyber', 'assassin')
    clothing = None if name in ROSTER or boss else outfit_for(name, outfit)
    color = (ROSTER[name].color if name in ROSTER else
             {'WARDEN': (169, 73, 103), 'RELAY': (103, 174, 196), 'NULL': (145, 108, 206)}[name] if boss else clothing.color)
    trim = clothing.trim if clothing else (255, 203, 110) if name in ('BRUNO', 'WARDEN') else (163, 250, 245) if name != 'NULL' else (255, 159, 219)
    dark = mix(color, INK, .58)
    pale = mix(color, WHITE, .5)
    walking = state in ('walk', 'approach', 'positioning')
    cycle = (0, 1, 2, 1, 0, -1, -2, -1)[frame]
    bob = (0, 0, -1, 0, 0, 0, -1, 0)[frame] if walking else (0, 0, 0, 0, 1, 1, 0, 0)[frame]
    lean = cycle//2 if walking and fast else 0
    stride = cycle*(2 if fast else 1) if walking else 0
    attack = state in ATTACKS
    extension = (0, -2, 10, 15, 13, 7, 2, 0)[frame] if attack else 0
    if attack:
        lean = (-2, -3, 2, 4, 3, 2, 1, 0)[frame]
        bob = (1, 2, 0, -1, 0, 1, 0, 0)[frame]
    if state == 'airborne':
        stride = (0, -1, -3, -3, -2, 0, 1, 0)[frame]; bob = 0
    if state == 'dodge':
        lean = (1, 3, 4, 4, 3, 2, 1, 0)[frame]; bob = (2, 4, 5, 5, 4, 3, 1, 0)[frame]
        stride = 3
    if state == 'hurt':
        lean = (-4, -5, -4, -3, -2, -1, 0, 0)[frame]; bob = 2 if frame < 3 else 1
    fallen = state in ('knockdown', 'defeated')
    if fallen: lean, bob = -2, 0
    cx = 31+lean
    width = 12 if heavy else 10 if boss else 8 if fast else 9
    head_w = 26 if heavy else 24
    head_x, head_y = cx-head_w//2, 12+bob

    def box(c, x, y, w, h):
        pygame.draw.rect(s, c, (round(x), round(y), w, h))

    def roundbox(c, rect, radius=3, outline=True):
        rect = pygame.Rect(*(round(v) for v in rect))
        pygame.draw.rect(s, INK if outline else c, rect, border_radius=radius)
        if outline:
            pygame.draw.rect(s, c, rect.inflate(-2, -2), border_radius=max(1, radius-1))

    def poly(c, points): pygame.draw.polygon(s, c, points)

    def limb(points, c, width=5):
        points = [(round(x), round(y)) for x, y in points]
        pygame.draw.lines(s, INK, False, points, width+2)
        pygame.draw.lines(s, c, False, points, width)
        for point in (points[0], points[-1]):
            pygame.draw.circle(s, INK, point, (width+2)//2)
            pygame.draw.circle(s, c, point, width//2)

    # Back silhouettes: courier scarf, ponytails, coat tails and backpacks.
    if name in ('NOVA', 'runner', 'assassin'):
        tail_y = 26+bob+(cycle//2 if walking else 0)
        poly(INK, [(cx-8, tail_y), (cx-22, tail_y+2), (cx-20, tail_y+8), (cx-7, tail_y+5)])
        poly(color, [(cx-9, tail_y+1), (cx-20, tail_y+3), (cx-18, tail_y+6), (cx-8, tail_y+4)])
        box(trim, cx-20, tail_y+3, 4, 1)
    if name in ('WARDEN', 'NULL') or clothing and clothing.style == 'coat':
        poly(INK, [(cx-10, 36+bob), (cx+10, 36+bob), (cx+15, 54), (cx+2, 53), (cx, 48), (cx-5, 54), (cx-15, 52)])
        poly(dark, [(cx-9, 37+bob), (cx+9, 37+bob), (cx+12, 52), (cx+3, 51), (cx, 46), (cx-6, 52), (cx-12, 50)])
    if clothing and clothing.style == 'courier':
        roundbox(dark, (cx-width-7, 32+bob, 10, 16)); box(trim, cx-width-5, 35+bob, 4, 3)

    # Short bent legs and rounded sneakers, anchored at y=59.
    for back, foot_x in ((True, 25+stride), (False, 38-stride)):
        hip = cx-4 if back else cx+5
        limb([(hip, 46+bob), (foot_x, 51), (foot_x, 55)], (49, 54, 86) if back else (70, 75, 112), 5 if not heavy else 7)
        roundbox(dark if back else color, (foot_x-5, 53, 12 if heavy else 11, 6), 2)
        box(trim, foot_x-3, 57, 8 if heavy else 7, 1)
    # Rear arm is behind jacket; separate elbows prevent a rectangular torso.
    limb([(cx-width, 37+bob), (cx-width-4, 42+bob), (cx-width-1, 46+bob)], dark, 6 if heavy else 4)
    roundbox(color, (cx-width-2, 33+bob, width*2+4, 17), 5)
    box(dark, cx-width+1, 40+bob, 4, 6)
    box(trim, cx, 36+bob, 2, 11)
    box(INK, cx-width+1, 47+bob, width*2-2, 2)
    box(trim, cx-1, 47+bob, 4, 2)

    # Body-specific clothing, rather than the old body's coordinate overlays.
    style = clothing.style if clothing else 'nova' if name == 'NOVA' else 'worker' if name == 'BRUNO' else 'jacket'
    if style in ('worker', 'vest', 'military'):
        roundbox((61, 73, 99), (cx-width+2, 38+bob, width*2-4, 10), 2)
        for x in (cx-6, cx+5): box(trim, x, 34+bob, 2, 11)
        box(pale, cx-3, 41+bob, 6, 3)
    elif style in ('armor', 'tech') or name in ('RELAY', 'NULL', 'security', 'cyber'):
        for x in (cx-width-3, cx+width-3): roundbox(pale, (x, 33+bob, 8, 7), 3)
        roundbox(dark, (cx-6, 38+bob, 13, 8), 3)
        if name == 'NULL':
            poly(trim, [(cx, 38+bob), (cx+4, 42+bob), (cx, 46+bob), (cx-4, 42+bob)])
            box(WHITE, cx-1, 41+bob, 2, 2)
        else: box(trim, cx-3, 40+bob, 7, 2)
    elif style == 'track':
        for x in (cx-width+2, cx+width-3): box(trim, x, 35+bob, 2, 11)
    elif style in ('leather', 'denim', 'jacket'):
        for sign in (-1, 1):
            poly(pale, [(cx+sign*3, 34+bob), (cx+sign*8, 36+bob), (cx+sign*5, 40+bob)])
        box(trim, cx+4, 42+bob, 3, 2)
    elif style == 'nova':
        poly(WHITE, [(cx-7, 35+bob), (cx+7, 35+bob), (cx+3, 39+bob), (cx-2, 38+bob)])
        box((255, 157, 194), cx-7, 40+bob, 3, 3)
    if name == 'WARDEN':
        for sign in (-1, 1):
            poly(trim, [(cx+sign*3, 34+bob), (cx+sign*10, 35+bob), (cx+sign*6, 41+bob)])
        box(trim, cx+5, 44+bob, 3, 3)

    # Large softly stepped head with cheek shading and visible two-eye expression.
    if style == 'hood' or name in ('assassin', 'NULL'):
        roundbox(dark, (head_x-2, head_y-3, head_w+4, 27), 7)
    face_color = (187, 219, 226) if name in ('RELAY', 'NULL', 'echo') else SKIN
    roundbox(face_color, (head_x, head_y, head_w, 23), 7)
    box(SHADE if face_color == SKIN else dark, head_x+2, head_y+15, 2, 4)
    box(mix(face_color, WHITE, .4), head_x+5, head_y+4, 4, 2)
    # Every family has a different hair contour or helmet, independent of palette.
    if name == 'NOVA':
        poly(INK, [(head_x, head_y+9), (head_x-2, head_y+3), (head_x+4, head_y-3), (head_x+14, head_y-4), (head_x+22, head_y), (head_x+25, head_y+10), (head_x+18, head_y+7), (head_x+14, head_y+3), (head_x+9, head_y+10)])
        poly(color, [(head_x+1, head_y+7), (head_x, head_y+3), (head_x+5, head_y-2), (head_x+14, head_y-2), (head_x+21, head_y+1), (head_x+23, head_y+7), (head_x+18, head_y+5), (head_x+14, head_y+1), (head_x+9, head_y+8)])
        box(pale, head_x+5, head_y, 7, 2)
        roundbox(dark, (head_x-5, head_y+7, 7, 10), 3)
        box(trim, head_x-4, head_y+10, 4, 3)
        box((255, 158, 195), head_x+19, head_y+7, 4, 2)
    elif name in ('BRUNO', 'bruiser') or style == 'worker':
        roundbox(color, (head_x, head_y-3, head_w, 10), 5)
        roundbox(trim, (head_x-2, head_y+4, head_w+4, 4), 2)
        box(pale, cx-2, head_y-2, 3, 6)
    elif name in ('RELAY', 'security') or style == 'armor':
        roundbox(dark, (head_x-1, head_y-2, head_w+2, 12), 5)
        for x in (head_x-3, head_x+head_w-2): roundbox(pale, (x, head_y+5, 6, 12), 2)
        box(trim, head_x+5, head_y+5, head_w-10, 2)
        if name == 'RELAY':
            limb([(cx-5, head_y), (cx-7, head_y-6)], pale, 2)
            roundbox(trim, (cx-10, head_y-9, 6, 5), 2)
    elif name == 'NULL':
        for sign in (-1, 1):
            poly(INK, [(cx+sign*5, head_y), (cx+sign*15, head_y-8), (cx+sign*14, head_y+8)])
            poly(color, [(cx+sign*8, head_y), (cx+sign*14, head_y-5), (cx+sign*12, head_y+6)])
            box(trim, cx+sign*11-1, head_y-1, 2, 3)
        roundbox(dark, (head_x+2, head_y+1, head_w-4, 7), 3)
    elif name == 'WARDEN':
        roundbox((255, 218, 155), (head_x-1, head_y-5, head_w+1, 13), 5)
        roundbox((255, 236, 191), (cx, head_y-8, 13, 8), 3)
        box((197, 140, 114), head_x+3, head_y+4, 6, 2)
    elif fast:
        roundbox(dark, (head_x-1, head_y-2, head_w, 9), 4)
        poly(color, [(head_x+3, head_y+5), (head_x+5, head_y-5), (head_x+11, head_y-2), (head_x+17, head_y-6), (head_x+22, head_y+5)])
        box(trim, head_x, head_y+7, head_w, 2)
    else:
        hair = (78, 55, 81) if name != 'REX' else (93, 49, 81)
        for x, y, r in ((head_x+5, head_y+2, 6), (cx, head_y, 7), (head_x+head_w-5, head_y+2, 6)):
            pygame.draw.circle(s, INK, (x, y), r+1); pygame.draw.circle(s, hair, (x, y), r)
        if style == 'hood': roundbox(color, (head_x-3, head_y-4, 8, 20), 4)
        if style == 'denim': box(trim, head_x+1, head_y+7, 4, 3)
        if style == 'military': roundbox(color, (head_x-2, head_y-4, head_w+4, 7), 3)
    # Squeezed hit eyes / drowsy defeat / alert windup. No frightening faces.
    eye_y = head_y+12
    for x in (cx-5, cx+4):
        if state in ('hurt', 'knockdown', 'defeated'):
            pygame.draw.lines(s, INK, False, [(x-1, eye_y), (x+1, eye_y+2), (x-1, eye_y+4)], 1)
        elif frame == 7 and not attack and state not in ('intro', 'phase', 'guard'):
            box(INK, x-1, eye_y+2, 4, 1)
        else:
            roundbox(WHITE, (x-1, eye_y-1, 5, 6), 2, False)
            box(INK, x+1, eye_y, 2, 4)
            box(WHITE, x+1, eye_y, 1, 1)
    for x in (cx-9, cx+8): box((244, 144, 163), x, eye_y+5, 3, 1)
    if state in ('intro', 'phase') or attack and frame < 2:
        roundbox(INK, (cx+1, eye_y+6, 3, 3), 1, False)
    else:
        pygame.draw.lines(s, INK, False, [(cx, eye_y+7), (cx+2, eye_y+8), (cx+4, eye_y+7)], 1)

    # Front arm changes its whole articulation; heavy attacks no longer grow a third arm.
    hand_x, hand_y = cx+width+4+extension, 43+bob
    if attack and state in ('heavy', 'smash', 'slam', 'bash'):
        hand_x = cx+(8, 5, 15, 18, 15, 12, 10, 9)[frame]
        hand_y = (30, 23, 20, 18, 24, 32, 39, 42)[frame]+bob
    if state == 'special':
        hand_x = cx+(10, 7, 16, 19, 18, 14, 11, 10)[frame]
        hand_y = (37, 34, 30, 31, 35, 38, 40, 42)[frame]+bob
    if state == 'victory': hand_x, hand_y = cx+15, 10+bob
    hand_x = min(58, hand_x)
    elbow = (cx+width+3, 38+bob) if extension > 0 else (cx+width+4, 40+bob)
    limb([(cx+width-1, 36+bob), elbow, (hand_x, hand_y)], color, 6 if heavy else 4)
    roundbox(trim if heavy or boss else face_color, (hand_x-3, hand_y-3, 7 if heavy else 6, 7 if heavy else 6), 3)
    if attack and state in ('combo3', 'air', 'sweep') and 2 <= frame <= 4:
        limb([(cx+3, 46), (cx+12, 46), (55, 43)], (70, 75, 112), 6)
        roundbox(color, (51, 40, 11, 7), 3)
        box(trim, 54, 45, 6, 1)
    if name in ('shield', 'security'):
        roundbox(dark, (cx-18, 34+bob, 13, 21), 5)
        roundbox(pale, (cx-16, 37+bob, 9, 14), 3)
        box(trim, cx-14, 41+bob, 5, 3)
    if name in ('ranged', 'sniper', 'echo'):
        roundbox(dark, (hand_x-5, hand_y-4, 11 if name == 'sniper' else 8, 6), 2)
        box(trim, min(60, hand_x+3), hand_y-3, 2, 2)
    if name in ('duelist', 'assassin'):
        pygame.draw.line(s, INK, (hand_x, hand_y), (min(61, hand_x+4), max(3, hand_y-13)), 3)
        pygame.draw.line(s, pale, (hand_x, hand_y-1), (min(61, hand_x+4), max(3, hand_y-13)), 1)
    if fallen:
        # Rotate the cropped body, then anchor its bottom. No off-canvas floor clipping.
        body = s.subsurface(s.get_bounding_rect()).copy()
        angle = (20, 40, 65, 83, 90, 90, 90, 90)[frame]
        body = pygame.transform.rotate(body, angle)
        if body.get_width() > 60 or body.get_height() > 58:
            factor = min(60/body.get_width(), 58/body.get_height())
            body = pygame.transform.scale(body, (int(body.get_width()*factor), int(body.get_height()*factor)))
        s.fill((0, 0, 0, 0))
        s.blit(body, ((64-body.get_width())//2, 59-body.get_height()-(2 if frame in (2, 3) else 0)))
    return s
