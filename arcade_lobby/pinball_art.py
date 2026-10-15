"""Pixel art for LUCKY CAT PINBALL (drawing helpers only; no game state).

The table is drawn 1:1 from the physics geometry in pinball.py at TABLE_POS on the 400 x 300
canvas, so what you see is exactly what the ball hits. build_* make the static layers once;
draw_* paint the moving parts each frame.
"""
import math

import pygame

import pinball as pb
from gfx import scale_color, shade

TABLE_POS = (130, 36)       # canvas position of the table's top-left corner
TX, TY = TABLE_POS
CABINET = pygame.Rect(8, 4, 384, 292)
CX = TX + int(pb.W / 2)

NAVY, VIOLET, VIOLET_DARK = (14, 10, 44), (58, 40, 130), (30, 20, 78)
CYAN = (80, 240, 255)
PINK = (255, 120, 200)
GOLD = (255, 206, 84)
FELT_TOP, FELT_BOT = (22, 12, 58), (40, 22, 96)
BALL = (236, 244, 255)


def P(x, y):
    """Table coordinates -> canvas pixels."""
    return TX + int(round(x)), TY + int(round(y))


def _outline():
    pts = [(a[0], a[1]) for a, _ in pb._arc()] + [pb._arc()[-1][1]]
    return pts + [(pb.W, pb.H), (0.0, pb.H)]


# ------------------------------------------------------------------ small sprites
def star(surf, x, y, r, color):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    pygame.draw.polygon(surf, color, pts)


def fish(surf, x, y, color, flip=False):
    """A 9 x 5 pixel-art fish."""
    d = -1 if flip else 1                                                   # the tail is on the right unless flipped
    pygame.draw.ellipse(surf, color, (x - 4, y - 2, 7, 5))
    pygame.draw.polygon(surf, color, [(x + 3 * d, y), (x + 5 * d, y - 2), (x + 5 * d, y + 2)])
    surf.set_at((x - 2 * d, y - 1), (20, 10, 40))


def cat_face(surf, cx, cy, lucky=False, t=0.0):
    """The lucky-cat centrepiece: pink ears, a round face, whiskers; the eyes are happy arcs in Lucky Cat Mode."""
    face = (255, 236, 214) if lucky else (190, 170, 214)
    pygame.draw.polygon(surf, PINK, [(cx - 12, cy - 4), (cx - 9, cy - 13), (cx - 3, cy - 8)])
    pygame.draw.polygon(surf, PINK, [(cx + 12, cy - 4), (cx + 9, cy - 13), (cx + 3, cy - 8)])
    pygame.draw.ellipse(surf, face, (cx - 12, cy - 9, 24, 19))
    pygame.draw.ellipse(surf, shade(face, -0.25), (cx - 12, cy - 9, 24, 19), 1)
    eye = (255, 190, 60) if lucky else (40, 24, 70)
    if lucky:
        for ex in (cx - 6, cx + 5):
            pygame.draw.arc(surf, eye, (ex - 2, cy - 4, 5, 5), 0.2, math.pi - 0.2, 1)
    else:
        blink = int(t * 1.3) % 7 == 0 and (t * 1.3) % 1 < 0.15
        for ex in (cx - 5, cx + 5):
            surf.fill(eye, (ex - 1, cy - 2 + (1 if blink else 0), 2, 1 if blink else 3))
    surf.set_at((cx, cy + 2), PINK)
    surf.fill((120, 60, 120), (cx - 1, cy + 3, 3, 1))
    for dy in (1, 3):
        pygame.draw.line(surf, shade(face, -0.35), (cx - 10, cy + dy), (cx - 15, cy + dy - 1))
        pygame.draw.line(surf, shade(face, -0.35), (cx + 10, cy + dy), (cx + 15, cy + dy - 1))
    if lucky:                                                              # the raised, waving lucky paw
        paw = (cx + 15, cy - 10 + int(math.sin(t * 9) * 2))
        pygame.draw.ellipse(surf, face, (paw[0] - 3, paw[1] - 3, 6, 7))
        surf.set_at((paw[0], paw[1]), PINK)


# ------------------------------------------------------------------ static layers
def build_background():
    from settings import VIEW_H, VIEW_W
    bg = pygame.Surface((VIEW_W, VIEW_H))
    for y in range(VIEW_H):
        k = y / VIEW_H
        bg.fill((int(10 + 12 * k), int(6 + 6 * k), int(30 + 28 * k)), (0, y, VIEW_W, 1))
    for x in range(-VIEW_H, VIEW_W, 28):
        pygame.draw.line(bg, (20, 14, 52), (x, 0), (x + VIEW_H, VIEW_H))
    return bg


def build_cabinet():
    """The casing round the table, the cat-ear header and the side panels' backing."""
    from settings import VIEW_H, VIEW_W
    s = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
    cab = CABINET
    pygame.draw.rect(s, VIOLET_DARK, cab, border_radius=7)
    pygame.draw.rect(s, NAVY, cab.inflate(-8, -8), border_radius=6)
    pygame.draw.rect(s, CYAN, cab, 1, border_radius=7)
    pygame.draw.rect(s, scale_color(CYAN, 0.45), cab.inflate(-4, -4), 1, border_radius=6)
    for ex in (cab.left + 52, cab.right - 52):                              # the pink cat ears of the header
        pygame.draw.polygon(s, PINK, [(ex - 15, cab.top + 5), (ex, cab.top - 4), (ex + 15, cab.top + 5)])
        pygame.draw.polygon(s, (120, 40, 110), [(ex - 7, cab.top + 5), (ex, cab.top), (ex + 7, cab.top + 5)])
    for box in (pygame.Rect(16, 40, 106, 232), pygame.Rect(278, 40, 106, 232)):     # side panels
        pygame.draw.rect(s, (10, 8, 34), box, border_radius=4)
        pygame.draw.rect(s, scale_color(CYAN, 0.5), box, 1, border_radius=4)
    glass = pygame.Rect(TX - 5, TY - 5, int(pb.W) + 10, int(pb.H) + 10)
    pygame.draw.rect(s, (8, 6, 28), glass, border_radius=8)
    pygame.draw.rect(s, scale_color(CYAN, 0.6), glass, 1, border_radius=8)
    return s


def build_table():
    """The playfield: felt, decals and every wall, rail, post and slot, drawn from the physics geometry."""
    W, H = int(pb.W), int(pb.H)
    t = pygame.Surface((W, H), pygame.SRCALPHA)
    felt = pygame.Surface((W, H))
    for y in range(H):
        k = y / H
        felt.fill(tuple(int(a + (b - a) * k) for a, b in zip(FELT_TOP, FELT_BOT)), (0, y, W, 1))
    for x in range(8, W, 14):                                               # a faint dotted grid
        for y in range(8, H, 14):
            felt.set_at((x, y), (60, 40, 130))
    mask = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), _outline())
    felt.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    t.blit(felt, (0, 0))
    lane = pygame.Surface((W - int(pb.LANE_X), H), pygame.SRCALPHA)         # the darker plunger lane
    lane.fill((8, 6, 30, 130))
    t.blit(lane, (int(pb.LANE_X), 0))
    for x, y, r, c in ((20, 70, 4, GOLD), (104, 66, 4, GOLD), (28, 168, 3, (255, 236, 150)), (94, 168, 3, (255, 236, 150)),
                       (61, 78, 3, (255, 236, 150)), (10, 108, 3, (255, 236, 150))):
        star(t, x, y, r, scale_color(c, 0.75))
    fish(t, 45, 176, (230, 170, 60))
    fish(t, 77, 176, (230, 170, 60), flip=True)
    fish(t, 61, 180, (255, 214, 90))
    # outlane drains
    for x0, x1 in ((0, 10), (int(pb.LANE_X) - 10, int(pb.LANE_X))):
        for y in range(160, int(pb.H), 8):
            t.fill((120, 30, 70), (x0 + 3, y, 4, 2))
    # walls, rails and the gate
    for a, b in pb.WALLS:
        _rail(t, a, b, 1.5)
    pygame.draw.line(t, PINK, pb.GATE[0], pb.GATE[1], 2)
    pygame.draw.line(t, (255, 220, 240), (pb.GATE[0][0], pb.GATE[0][1] - 1), (pb.GATE[1][0], pb.GATE[1][1] - 1))
    for px, py in pb.POSTS:
        pygame.draw.circle(t, (10, 6, 30), (int(px), int(py)), int(pb.POST_R) + 2)
        pygame.draw.circle(t, GOLD, (int(px), int(py)), int(pb.POST_R) + 1)
        t.set_at((int(px) - 1, int(py) - 1), (255, 255, 230))
    for x, y, w, h in pb.LANES:                                             # the rollover slots
        pygame.draw.rect(t, (14, 8, 44), (x, y, w, h), border_radius=2)
        pygame.draw.rect(t, scale_color(CYAN, 0.55), (x, y, w, h), 1, border_radius=2)
    # scoop
    sx, sy = int(pb.SCOOP[0]), int(pb.SCOOP[1])
    pygame.draw.circle(t, (10, 6, 30), (sx, sy), 8)
    pygame.draw.circle(t, GOLD, (sx, sy), 8, 1)
    pygame.draw.circle(t, (2, 0, 10), (sx, sy), 5)
    return t


def _rail(t, a, b, r):
    pygame.draw.line(t, (8, 6, 30), a, b, int(r * 2) + 3)
    pygame.draw.line(t, CYAN, a, b, int(r * 2) + 1)
    pygame.draw.line(t, (225, 255, 255), (a[0], a[1] - 1), (b[0], b[1] - 1))


# ------------------------------------------------------------------ moving parts
def draw_bumper(surf, i, flash, lucky, t):
    x, y = P(*pb.BUMPERS[i])
    r = int(pb.BUMPER_R)
    glow_on = flash > 0 or lucky
    if lucky:
        k = 0.5 + 0.5 * math.sin(t * 8 + i)
        halo = pygame.Surface((r * 2 + 12, r * 2 + 12), pygame.SRCALPHA)
        pygame.draw.circle(halo, (255, 214, 90, int(70 + 60 * k)), halo.get_rect().center, r + 5)
        surf.blit(halo, halo.get_rect(center=(x, y)))
    base = (255, 214, 90) if lucky else PINK
    pygame.draw.circle(surf, (10, 6, 30), (x, y), r + 1)
    pygame.draw.circle(surf, scale_color(base, 0.55), (x, y), r)
    grow = 2 if flash > 0.08 else 0
    pygame.draw.circle(surf, base if glow_on else scale_color(base, 0.8), (x, y), r - 2 + grow)
    pygame.draw.circle(surf, (255, 250, 255) if flash > 0 else shade(base, 0.35), (x, y), max(2, r - 5 + grow))
    pygame.draw.circle(surf, scale_color(base, 0.5), (x, y), r, 1)
    # a tiny cat-ear mark so each bumper is a little cat head
    for ex in (-1, 1):
        pygame.draw.polygon(surf, base, [(x + ex * 3, y - r + 1), (x + ex * 5, y - r - 3), (x + ex * 7, y - r + 2)])
    surf.set_at((x - 3, y - 3), (255, 255, 255))


def draw_targets(surf, world, t, font):
    for i, (a, b) in enumerate(pb.TARGETS):
        x0, y0 = P(*a)
        x1, y1 = P(*b)
        lit = world.targets[i]
        flash = world.target_flash[i] > 0 or (world.cat_flash > 0 and int(t * 12) % 2 == 0)
        body = pygame.Rect(x0 - 5, y0, 5, y1 - y0)
        col = (255, 250, 200) if flash else GOLD if lit else (110, 70, 190)
        pygame.draw.rect(surf, (10, 6, 30), body.inflate(2, 2), border_radius=1)
        pygame.draw.rect(surf, col, body, border_radius=1)
        if lit:
            pygame.draw.rect(surf, scale_color(GOLD, 0.5), body.inflate(4, 4), 1, border_radius=2)
        img = font.render(pb.TARGET_LETTERS[i], GOLD if lit else (190, 170, 255))
        surf.blit(img, img.get_rect(midright=(x0 - 8, (y0 + y1) // 2)))


def draw_lanes(surf, world, t):
    for i, (x, y, w, h) in enumerate(pb.LANES):
        px, py = P(x, y)
        if world.lanes[i]:
            pygame.draw.rect(surf, (255, 236, 150), (px + 1, py + 1, w - 2, h - 2), border_radius=1)
            star(surf, px + w // 2, py + h // 2, 4, (255, 150, 60))
        else:
            tri = [(px + 3, py + 4), (px + w - 3, py + 4), (px + w // 2, py + h - 3)]
            pygame.draw.polygon(surf, (70, 90, 170), tri)


def draw_flipper(surf, f, lucky):
    px, py = P(*f.pivot)
    tx, ty = f.tip()
    tx, ty = TX + tx, TY + ty
    dx, dy = tx - px, ty - py
    ln = math.hypot(dx, dy) or 1
    nx, ny = -dy / ln, dx / ln
    r0, r1 = 4.2, 2.6
    poly = [(px + nx * r0, py + ny * r0), (tx + nx * r1, ty + ny * r1), (tx - nx * r1, ty - ny * r1), (px - nx * r0, py - ny * r0)]
    body = (255, 214, 90) if lucky else PINK
    glow = f.raised > 0.5
    pygame.draw.polygon(surf, (10, 6, 30), [(x + (1 if x > px else -1), y) for x, y in poly])
    pygame.draw.polygon(surf, body if not glow else shade(body, 0.25), poly)
    pygame.draw.circle(surf, body, (int(tx), int(ty)), int(r1))
    pygame.draw.circle(surf, body, (px, py), int(r0))
    pygame.draw.line(surf, (255, 255, 255), (px + nx * 2, py + ny * 2), (tx + nx * 1, ty + ny * 1))
    pygame.draw.circle(surf, (60, 20, 90), (px, py), 1)
    if glow:
        pygame.draw.line(surf, CYAN, (px - nx * 4, py - ny * 4), (tx - nx * 3, ty - ny * 3))


def draw_plunger(surf, world):
    x = TX + int(pb.PLUNGER_REST[0])
    top = TY + int(pb.H) - 6 + int(world.pull * 7)
    for y in range(top + 1, TY + int(pb.H) + 8, 2):                         # the spring
        surf.fill(CYAN if (y // 2) % 2 else (40, 140, 170), (x - 3, y, 6, 1))
    pygame.draw.rect(surf, PINK, (x - 5, top - 1, 10, 3), border_radius=1)
    surf.fill((255, 230, 245), (x - 4, top - 1, 8, 1))
    pygame.draw.rect(surf, (10, 6, 30), (x - 1, top + 2, 2, 4))


def draw_ball(surf, bx, by, trail, lucky):
    for i, (x, y) in enumerate(trail):
        k = (i + 1) / (len(trail) + 1)
        c = scale_color((255, 214, 90) if lucky else CYAN, 0.18 + 0.45 * k)
        pygame.draw.circle(surf, c, P(x, y), max(1, int(pb.R * k * 0.8)))
    x, y = P(bx, by)
    pygame.draw.circle(surf, (10, 6, 30), (x, y), int(pb.R) + 1)
    pygame.draw.circle(surf, BALL, (x, y), int(pb.R))
    pygame.draw.circle(surf, (150, 170, 220), (x + 1, y + 1), int(pb.R) - 1, 1)
    surf.set_at((x - 1, y - 1), (255, 255, 255))
    surf.set_at((x - 2, y - 1), (255, 255, 255))


def draw_scoop(surf, world, t):
    x, y = P(*pb.SCOOP)
    if world.scoop_lit:
        k = 0.5 + 0.5 * math.sin(t * 7)
        pygame.draw.circle(surf, scale_color(GOLD, 0.55 + 0.4 * k), (x, y), 8, 1)
        pygame.draw.circle(surf, scale_color(GOLD, 0.4 + 0.4 * k), (x, y), 10, 1)
    if world.captured > 0:
        pygame.draw.circle(surf, (255, 250, 220), (x, y), 3)
