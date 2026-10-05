"""LOFI ARCADE room style: a calm late-night arcade with rain on the window,
fairy lights, soft neon, a lounge corner and a little cafe counter.

Same collision/drawable API as room.Room, but the background is assembled
from the cached layers and ambient effects in backdrop.py."""
import pygame

from backdrop import (AmbientAnimator, ArcadeBackdrop, BackgroundRenderer,
                      DustMotes, LightingOverlay, NeonLight, RainWindow,
                      Scanlines, StringLights, neon_tube)
from font import get_font
from gfx import glow_line, neon_rect_glow, radial_glow, scale_color
from lofi_props import (CafeCounter, CoffeeTable, FloorLamp, Speaker,
                        make_beanbag, make_couch, make_stool, make_tall_plant)
from room import ClawMachine, Prop, Room, make_gumball, make_plant, make_vending, room_walls
from settings import (DOOR_W, DOOR_X, FLOOR_BOTTOM, FLOOR_TOP, Lofi, VIEW_H,
                      VIEW_W, WALL_SIDE)

WINDOW = pygame.Rect(24, 7, 38, 31)
RUG = pygame.Rect(28, 166, 106, 58)
RUNNER = pygame.Rect(DOOR_X + 6, 124, DOOR_W - 12, FLOOR_BOTTOM - 124 - 16)
WALL_STRIP_Y = 46
SCONCES = (118, 178)
SIGN_POS = (112, 9)


# ------------------------------------------------------------ static layers
class LofiArcadeBackdrop(ArcadeBackdrop):
    """Paints the static lofi room: tiled floor, rug, papered walls with a
    wainscot, posters, sconces and the doorway."""

    def paint_floor(self, surf):
        surf.fill(Lofi.NIGHT)
        tile = 16
        for y in range(FLOOR_TOP, FLOOR_BOTTOM, tile):
            for x in range(WALL_SIDE, VIEW_W - WALL_SIDE, tile):
                i, j = (x - WALL_SIDE) // tile, (y - FLOOR_TOP) // tile
                surf.fill(Lofi.TILE_B if (i + j) % 2 else Lofi.TILE_A, (x, y, tile, tile))
                surf.fill(Lofi.GROUT, (x, y, tile, 1))
                surf.fill(Lofi.GROUT, (x, y, 1, tile))
                if (i * 3 + j) % 5 == 0:                          # faint sheen
                    surf.fill(Lofi.TILE_SHINE, (x + 2, y + 2, 3, 1))
                    surf.fill(Lofi.TILE_SHINE, (x + 2, y + 3, 1, 1))
        self._paint_rug(surf, RUG)
        self._paint_runner(surf, RUNNER)

        shadow = pygame.Surface((VIEW_W, 8), pygame.SRCALPHA)   # under the back wall
        for i, a in enumerate((110, 80, 55, 35, 20, 10)):
            shadow.fill((0, 0, 0, a), (0, i, VIEW_W, 1))
        surf.blit(shadow, (0, FLOOR_TOP))

        mat = pygame.Rect(DOOR_X + 4, FLOOR_BOTTOM - 14, DOOR_W - 8, 12)
        surf.fill((44, 34, 62), mat)
        pygame.draw.rect(surf, (80, 64, 104), mat, 1)
        for x in range(mat.x + 4, mat.right - 4, 4):
            surf.fill((56, 44, 78), (x, mat.y + 3, 2, mat.h - 6))

    @staticmethod
    def _paint_rug(surf, r):
        base, border, trim, motif = (60, 40, 84), (88, 58, 112), (150, 96, 146), (96, 66, 126)
        surf.fill(base, r.inflate(0, -2))
        surf.fill(base, r.inflate(-2, 0))
        pygame.draw.rect(surf, border, r.inflate(-4, -4), 2)
        pygame.draw.rect(surf, trim, r.inflate(-10, -10), 1)
        for y in range(r.y + 12, r.bottom - 10, 8):              # little diamonds
            for x in range(r.x + 12 + (y // 8 % 2) * 6, r.right - 12, 12):
                pygame.draw.polygon(surf, motif, [(x, y - 2), (x + 2, y), (x, y + 2), (x - 2, y)])
        for y in range(r.y + 3, r.bottom - 3, 2):                # fringe
            surf.fill((150, 132, 170), (r.x - 2, y, 2, 1))
            surf.fill((150, 132, 170), (r.right, y, 2, 1))

    @staticmethod
    def _paint_runner(surf, r):
        """Long runner rug leading from the door toward the machines."""
        surf.fill((30, 30, 64), r)
        surf.fill((40, 40, 84), r.inflate(-4, -4))
        for x in (r.x + 3, r.right - 4):
            surf.fill((110, 70, 130), (x, r.y + 3, 1, r.h - 6))
        for y in range(r.y + 8, r.bottom - 6, 10):
            surf.fill((56, 56, 106), (r.centerx - 2, y, 4, 1))
            surf.fill((56, 56, 106), (r.centerx - 1, y - 1, 2, 3))
        for x in range(r.x + 1, r.right - 1, 2):              # fringe
            surf.fill((130, 120, 160), (x, r.y - 2, 1, 2))
            surf.fill((130, 120, 160), (x, r.bottom, 1, 2))

    def paint_walls(self, surf):
        # back wall: wallpaper, chair rail, wainscot, baseboard
        surf.fill(Lofi.WALL, (0, 0, VIEW_W, FLOOR_TOP))
        for x in range(0, VIEW_W, 12):
            surf.fill(Lofi.WALL_STRIPE, (x, 4, 2, WALL_STRIP_Y - 4))
        for y in range(8, WALL_STRIP_Y - 2, 8):
            for x in range(6 + (y // 8 % 2) * 6, VIEW_W, 12):
                surf.fill(Lofi.WALL_DOT, (x, y, 1, 1))
        surf.fill(Lofi.CEILING, (0, 0, VIEW_W, 3))
        surf.fill(scale_color(Lofi.PURPLE, 0.35), (0, 3, VIEW_W, 1))
        surf.fill(Lofi.RAIL, (0, WALL_STRIP_Y - 1, VIEW_W, 3))
        surf.fill(Lofi.RAIL_HI, (0, WALL_STRIP_Y - 1, VIEW_W, 1))
        surf.fill(Lofi.WAINSCOT, (0, WALL_STRIP_Y + 2, VIEW_W, FLOOR_TOP - WALL_STRIP_Y - 6))
        for x in range(0, VIEW_W, 20):
            surf.fill(Lofi.WAINSCOT_LINE, (x, WALL_STRIP_Y + 4, 1, 10))
            surf.fill(Lofi.WAINSCOT_HI, (x + 1, WALL_STRIP_Y + 4, 1, 10))
        surf.fill(Lofi.BASEBOARD, (0, FLOOR_TOP - 4, VIEW_W, 4))
        surf.fill(Lofi.RAIL, (0, FLOOR_TOP - 4, VIEW_W, 1))

        # side walls
        for x in (0, VIEW_W - WALL_SIDE):
            surf.fill(Lofi.SIDE_WALL, (x, 0, WALL_SIDE, VIEW_H))
            surf.fill(Lofi.SIDE_WALL_HI, (x + 3, 0, WALL_SIDE - 6, VIEW_H))
        for x in (WALL_SIDE - 1, VIEW_W - WALL_SIDE):
            surf.fill(scale_color(Lofi.PURPLE, 0.45), (x, FLOOR_TOP, 1, FLOOR_BOTTOM - FLOOR_TOP))

        # bottom wall with the doorway
        surf.fill((10, 8, 22), (DOOR_X, FLOOR_BOTTOM, DOOR_W, VIEW_H - FLOOR_BOTTOM))
        for x0, x1 in ((0, DOOR_X), (DOOR_X + DOOR_W, VIEW_W)):
            surf.fill(Lofi.SIDE_WALL, (x0, FLOOR_BOTTOM, x1 - x0, VIEW_H - FLOOR_BOTTOM))
            surf.fill(Lofi.SIDE_WALL_HI, (x0, FLOOR_BOTTOM + 3, x1 - x0, VIEW_H - FLOOR_BOTTOM - 6))
            surf.fill(scale_color(Lofi.PURPLE, 0.45), (x0, FLOOR_BOTTOM, x1 - x0, 1))
        for x in (DOOR_X - 2, DOOR_X + DOOR_W):
            surf.fill((10, 8, 22), (x, FLOOR_BOTTOM, 2, VIEW_H - FLOOR_BOTTOM))

    def paint_decor(self, surf):
        self.add_light(glow_line(VIEW_W, Lofi.CYAN, spread=3, strength=0.18), (-3, 1))  # ceiling edge
        # window sill with a tiny cactus (the window itself is animated)
        surf.fill((70, 56, 108), (WINDOW.x - 2, WINDOW.bottom, WINDOW.w + 4, 2))
        surf.fill((40, 32, 70), (WINDOW.x - 1, WINDOW.bottom + 2, WINDOW.w + 2, 1))
        surf.fill(Lofi.TERRACOTTA, (WINDOW.right - 8, WINDOW.bottom - 3, 4, 3))
        surf.fill(Lofi.LEAF, (WINDOW.right - 7, WINDOW.bottom - 7, 2, 4))
        surf.fill(Lofi.LEAF_LIGHT, (WINDOW.right - 8, WINDOW.bottom - 6, 1, 2))
        self.add_light(radial_glow(22, (10, 18, 36), bands=4, squash=0.8),
                       (WINDOW.centerx - 22, WINDOW.centery - 18))

        self._cassette_poster(surf, pygame.Rect(250, 7, 26, 20))
        self._vinyl_poster(surf, pygame.Rect(330, 6, 24, 34))
        self._cat_poster(surf, pygame.Rect(230, 9, 14, 18))

        for x in SCONCES:                                    # warm wall sconces
            surf.fill((70, 56, 96), (x - 3, 36, 7, 1))
            pygame.draw.polygon(surf, (255, 204, 140), [(x - 3, 37), (x + 3, 37), (x + 2, 40), (x - 2, 40)])
            surf.fill((255, 236, 200), (x - 2, 37, 5, 1))
            self.add_light(radial_glow(14, (60, 38, 16), bands=4, squash=1.4), (x - 14, 38 - 20))

        exit_sign = get_font().render_glow("EXIT", (170, 240, 190), (40, 110, 70))
        self.exit_pos = (DOOR_X + DOOR_W + 6, FLOOR_BOTTOM + 5)
        surf.fill((8, 18, 14), pygame.Rect(self.exit_pos, exit_sign.get_size()).inflate(4, 2))
        surf.blit(exit_sign, self.exit_pos)

    @staticmethod
    def _frame(surf, r, border, fill):
        surf.fill(border, r.inflate(2, 2))
        surf.fill(fill, r)

    def _cassette_poster(self, surf, r):
        self._frame(surf, r, (150, 128, 206), (46, 56, 106))
        surf.fill((70, 70, 130), (r.x, r.bottom - 6, r.w, 6))      # sunset stripe
        surf.fill((150, 84, 140), (r.x, r.bottom - 4, r.w, 2))
        c = pygame.Rect(r.x + 4, r.y + 3, 18, 11)
        surf.fill(Lofi.CREAM, c)
        surf.fill((226, 130, 170), (c.x + 2, c.y + 1, c.w - 4, 3))
        surf.fill((60, 46, 70), (c.x + 4, c.y + 6, c.w - 8, 3))
        for rx in (c.x + 5, c.x + 12):
            surf.fill((24, 20, 34), (rx, c.y + 6, 2, 2))
            surf.fill((200, 190, 210), (rx, c.y + 6, 1, 1))
        surf.fill((180, 160, 140), (c.x + 5, c.bottom - 1, 8, 1))

    def _vinyl_poster(self, surf, r):
        self._frame(surf, r, Lofi.MAGENTA, (42, 28, 74))
        cx, cy = r.centerx, r.y + 12
        pygame.draw.circle(surf, (14, 12, 24), (cx, cy), 9)
        for rad in (7, 5):
            pygame.draw.circle(surf, (38, 34, 58), (cx, cy), rad, 1)
        pygame.draw.circle(surf, Lofi.MAGENTA, (cx, cy), 3)
        surf.fill((255, 220, 240), (cx, cy, 1, 1))
        surf.fill((90, 86, 120), (cx - 6, cy - 5, 2, 1))           # shine
        surf.blit(get_font().render("LOFI", Lofi.PINK), (r.x + 1, r.bottom - 9))

    def _cat_poster(self, surf, r):
        self._frame(surf, r, (110, 180, 200), (34, 22, 60))
        cx, cy = r.centerx, r.centery + 2
        col = (246, 164, 86)
        pygame.draw.circle(surf, col, (cx, cy), 5)
        pygame.draw.polygon(surf, col, [(cx - 5, cy - 1), (cx - 4, cy - 7), (cx - 1, cy - 4)])
        pygame.draw.polygon(surf, col, [(cx + 4, cy - 1), (cx + 3, cy - 7), (cx, cy - 4)])
        surf.fill((34, 22, 60), (cx - 3, cy, 2, 1))                 # sleepy eyes
        surf.fill((34, 22, 60), (cx + 1, cy, 2, 1))
        for sx, sy in ((2, 2), (11, 3)):
            surf.fill(Lofi.WARM, (r.x + sx, r.y + sy, 1, 1))


# ------------------------------------------------------------------ lights
def _music_note_shape():
    s = pygame.Surface((11, 16), pygame.SRCALPHA)
    c = (255, 255, 255)
    s.fill(c, (7, 0, 1, 12))
    for i in range(4):
        s.fill(c, (8 + i // 2, 1 + i, 1, 1))
    pygame.draw.ellipse(s, c, (2, 10, 6, 5), 1)
    return s


def _open_sign_shape():
    font = get_font()
    s = pygame.Surface((30, 13), pygame.SRCALPHA)
    pygame.draw.rect(s, (255, 150, 200), s.get_rect(), 1, border_radius=3)
    s.blit(font.render("OPEN", (255, 214, 160)), (4, 3))
    return s


def build_lights():
    """The room's neon lights, as (light, layer) pairs."""
    font = get_font()
    arcade = font.render_glow("ARCADE", (255, 200, 236), (196, 84, 168), scale=2)
    note = neon_tube(_music_note_shape(), (210, 248, 255), (90, 190, 215))
    strip = pygame.Surface((VIEW_W - 2 * WALL_SIDE, 1), pygame.SRCALPHA)
    strip.fill((196, 160, 255))
    return [
        (NeonLight(strip, (WALL_SIDE, WALL_STRIP_Y), Lofi.PURPLE, spread=5,
                   strength=0.4, speed=0.45, depth=0.3), "wall"),
        (NeonLight(arcade, SIGN_POS, Lofi.MAGENTA, spread=8, strength=0.55, speed=0.6,
                   depth=0.18, flicker=(11.0, ((9.6, 9.7, 0.4), (9.8, 9.95, 0.5)))), "overlay"),
        (NeonLight(_open_sign_shape(), (292, 11), Lofi.AMBER, spread=6, strength=0.5,
                   speed=0.9, depth=0.15, phase=1.3,
                   flicker=(17.0, ((5.0, 5.12, 0.35), (5.3, 5.4, 0.5)))), "overlay"),
        (NeonLight(note, (358, 10), Lofi.CYAN, spread=6, strength=0.5, speed=0.7,
                   depth=0.25, phase=2.2), "overlay"),
    ]


# --------------------------------------------------------------------- room
class LofiRoom(Room):
    """Chill late-night arcade. Collision and drawable API match Room."""
    # cat id -> places it likes to wander to and nap at (first = home)
    cat_spots = {
        **Room.cat_spots,
        "miso": ((318, 226), (286, 236), (250, 200)),     # by the cafe stools
        "mochi": ((60, 216), (112, 222)),                 # napping on the lounge rug
    }

    def __init__(self, machines):
        self.machines = machines
        for m in machines:
            m.soft_glow = True
        self.props = self._build_props()
        self.walls = room_walls()
        self.solids = (self.walls + [p.footprint for p in self.props]
                       + [m.footprint for m in machines])

        animator = AmbientAnimator()
        # nothing stands in front of the window, so it can glow on the overlay
        animator.add(RainWindow(WINDOW), "overlay")
        for light, layer in build_lights():
            animator.add(light, layer)
        animator.add(StringLights(WALL_SIDE, VIEW_W - WALL_SIDE, 2, span=60, sag=4), "overlay")
        animator.add(DustMotes((30, 70, 340, 200), count=20), "overlay")
        animator.add(Scanlines((VIEW_W, VIEW_H)), "overlay")

        lighting = LightingOverlay(
            (VIEW_W, VIEW_H), edge=(70, 62, 120), center=(212, 204, 242),
            pools=[((200, 190), 130, (14, 8, 26), 0.8),       # soft purple fill
                   ((32, 162), 56, (44, 26, 10), 0.75),       # floor lamp
                   ((80, 200), 50, (20, 12, 20), 0.6),        # lounge
                   ((334, 196), 40, (36, 22, 10), 0.6),       # cafe counter
                   ((43, 76), 34, (8, 18, 36), 0.5),          # window light on floor
                   ((200, 290), 30, (10, 26, 18), 0.6)])      # exit sign
        self.renderer = BackgroundRenderer(LofiArcadeBackdrop((VIEW_W, VIEW_H)), animator, lighting)
        self.time = 0.0

    def _build_props(self):
        stool = make_stool()
        vend_glow = neon_rect_glow(30, 58, Lofi.CYAN, 6, 0.22)
        return [
            Prop(make_plant(Lofi.TERRACOTTA, Lofi.TERRACOTTA_HI), (22, 40), (24, FLOOR_TOP, 14, 4)),
            Prop(make_plant(Lofi.TERRACOTTA, Lofi.TERRACOTTA_HI), (360, 40), (362, FLOOR_TOP, 14, 4)),
            Prop(make_vending(), (248, 32), (249, FLOOR_TOP, 30, 26), vend_glow, (243, 27)),
            ClawMachine((288, 30), glow_strength=0.25),
            # lounge corner
            FloorLamp((22, 112)),
            Prop(make_couch(), (36, 140), (37, 152, 58, 16)),
            Speaker((98, 140)),
            CoffeeTable((50, 186)),
            Prop(make_beanbag(), (96, 190), (97, 198, 20, 8)),
            Prop(make_tall_plant(), (22, 214), (24, 242, 16, 8)),
            # cafe counter + stools
            CafeCounter((294, 162)),
            Prop(stool, (300, 206), (301, 214, 12, 5)),
            Prop(stool, (328, 206), (329, 214, 12, 5)),
            Prop(stool, (356, 206), (357, 214, 12, 5)),
            # near the door
            Prop(make_gumball(), (236, 252), (237, 268, 12, 6)),
            Prop(make_plant(Lofi.TERRACOTTA, Lofi.TERRACOTTA_HI), (356, 248), (359, 264, 13, 10)),
        ]

    # ------------------------------------------------------------ per frame
    def update(self, dt):
        self.time += dt
        self.renderer.update(dt)
        for prop in self.props:
            prop.update(dt)

    def draw_background(self, surf):
        self.renderer.draw_background(surf)

    def draw_lighting(self, surf):
        self.renderer.draw_lighting(surf)
        for prop in self.props:
            prop.draw_glow(surf)
        self.renderer.draw_overlay(surf)
