"""HOME / LOUNGE: the calm, personal centre room and the default spawn.

It holds the daily board, the daily login bonus, the cats (most of them),
cozy furniture and the decoration slots. The look is the soft purple / warm
blue lofi corner: rain on the window, fairy lights, lamp light.
"""
import pygame

from backdrop import (AmbientAnimator, BackgroundRenderer, DustMotes,
                      LightingOverlay, NeonLight, RainWindow, Scanlines,
                      StringLights)
from daily_ui import DailyBonusPopup
from decorations import (CAT_BED, NEON_SIGN, PLANT, RUG, TABLE_DECOR, WALL_POSTER,
                         DecorationSlot, HomeDecorationManager, default_catalog)
from gfx import radial_glow, scale_color
from lofi_props import (CoffeeTable, FloorLamp, Speaker, make_beanbag, make_couch)
from room import Prop
from room_art import WALL_STRIP_Y, HubBackdrop
from room_scene import BaseRoomScene, RoomExit
from settings import FLOOR_TOP, Col, Lofi, VIEW_H, VIEW_W, WALL_SIDE
from stations import build_daily_board

WINDOW = pygame.Rect(24, 7, 38, 31)

# Where decorations can go (see decorations.py). Flat things give their
# top-left; plants, table items and cat beds give the point they stand on.
HOME_SLOTS = (
    DecorationSlot("poster_left", WALL_POSTER, (222, 8), (30, 38), "poster_cassette"),
    DecorationSlot("poster_right", WALL_POSTER, (256, 8), (30, 38), "poster_vinyl"),
    DecorationSlot("rug", RUG, (118, 76), (106, 58), "rug_lounge"),
    DecorationSlot("table_decor", TABLE_DECOR, (190, 102), (14, 14), "table_cactus", sort_bias=20),
    DecorationSlot("plant_back", PLANT, (366, 76), (26, 44), "plant_monstera", foot=(14, 6), solid=True),
    DecorationSlot("plant_front", PLANT, (40, 168), (26, 44), "plant_bushy", foot=(12, 6), solid=True),
    DecorationSlot("neon_sign", NEON_SIGN, (171, 14), (30, 26), "neon_note"),
    DecorationSlot("cat_bed_left", CAT_BED, (80, 244), (30, 20), "bed_round"),
    DecorationSlot("cat_bed_right", CAT_BED, (322, 246), (30, 20), "bed_round"),
)


class HomeBackdrop(HubBackdrop):
    """Window sill, personal shelves and warm wall sconces."""
    SCONCES = (100, 214)

    def paint_room(self, surf):
        t = self.theme
        # window sill with a tiny cactus (the window itself is animated)
        surf.fill((70, 56, 108), (WINDOW.x - 2, WINDOW.bottom, WINDOW.w + 4, 2))
        surf.fill((40, 32, 70), (WINDOW.x - 1, WINDOW.bottom + 2, WINDOW.w + 2, 1))
        surf.fill(Lofi.TERRACOTTA, (WINDOW.right - 8, WINDOW.bottom - 3, 4, 3))
        surf.fill(Lofi.LEAF, (WINDOW.right - 7, WINDOW.bottom - 7, 2, 4))
        self.add_light(radial_glow(22, (10, 18, 36), bands=4, squash=0.8),
                       (WINDOW.centerx - 22, WINDOW.centery - 18))
        self._shelves(surf, pygame.Rect(78, 12, 62, 4), pygame.Rect(78, 30, 62, 4))
        for x in self.SCONCES:
            surf.fill((70, 56, 96), (x - 3, 38, 7, 1))
            pygame.draw.polygon(surf, (255, 204, 140), [(x - 3, 39), (x + 3, 39), (x + 2, 42), (x - 2, 42)])
            surf.fill((255, 236, 200), (x - 2, 39, 5, 1))
            self.add_light(radial_glow(14, (60, 38, 16), bands=4, squash=1.4), (x - 14, 40 - 20))

    @staticmethod
    def _shelves(surf, top, low):
        """Two wall shelves with books, a mug, a plant and a photo frame."""
        for shelf in (top, low):
            surf.fill(Lofi.WOOD, shelf)
            surf.fill(Lofi.WOOD_HI, (shelf.x, shelf.y, shelf.w, 1))
            surf.fill(Lofi.WOOD_DARK, (shelf.x + 2, shelf.bottom, shelf.w - 4, 1))
        books = ((70, 100, 190), (226, 130, 170), (240, 200, 110), (110, 190, 160), (150, 110, 220))
        x = top.x + 3
        for i, c in enumerate(books):
            h = 9 + (i * 5) % 4
            surf.fill(c, (x, top.y - h, 3, h))
            surf.fill(scale_color(c, 0.6), (x + 2, top.y - h, 1, h))
            x += 4
        surf.fill((236, 228, 244), (top.x + 30, top.y - 5, 4, 5))            # mug
        surf.fill((120, 72, 52), (top.x + 30, top.y - 5, 4, 1))
        surf.fill(Lofi.TERRACOTTA, (top.x + 44, top.y - 4, 5, 4))            # little plant
        surf.fill(Lofi.LEAF, (top.x + 45, top.y - 9, 3, 5))
        surf.fill(Lofi.LEAF_LIGHT, (top.x + 44, top.y - 8, 1, 2))
        surf.fill((150, 128, 206), (low.x + 4, low.y - 11, 12, 11))          # photo frame
        surf.fill((46, 56, 106), (low.x + 5, low.y - 10, 10, 9))
        surf.fill((255, 170, 215), (low.x + 8, low.y - 7, 4, 3))
        for i in range(4):                                                    # books lying down
            surf.fill(books[(i + 2) % 5], (low.x + 24, low.y - 3 - i * 3, 14, 3))
        surf.fill(Lofi.WARM, (low.x + 46, low.y - 4, 3, 4))                   # trinket


class HomeRoomScene(BaseRoomScene):
    room_id = "home"
    ambience_mix = {"rain": 0.25, "machine_hum": 0.04, "arcade_buzz": 0.03}
    exits = (RoomExit("left", "arcade_floor", "right"),
             RoomExit("right", "prize_plaza", "left"))
    cat_spots = {
        "miso": ((322, 236), (286, 222), (250, 174)),     # by the right cat bed
        "mochi": ((80, 234), (112, 214)),                 # napping on the left cat bed
        "luna": ((50, 112), (366, 150), (350, 180)),      # quiet corners
        "bean": ((262, 132), (214, 160), (150, 200)),     # wandering the lounge
    }
    hint_rows = (
        [("MOVE: WASD", Col.TEXT)],
        [("E :", Col.TEXT), ("INTERACT", Col.YELLOW)],
        [("I :", Col.TEXT), ("BAG", Col.YELLOW)],
    )

    def __init__(self, game, hub):
        self._declined = {}         # player -> the day they pressed ESC on their bonus
        super().__init__(game, hub)
        for profile in self.session.profiles:       # each profile's own login, separately
            profile.record_login()
        self._ready = {id(p): len(p.profile.claimable_tasks) for p in self.players}

    def title_subtitle(self):
        """P1 owns HOME; with two players the room says whose it is."""
        return f"{self.session.primary.name}'S HOME" if len(self.session) > 1 else None

    def guest_note(self, player):
        return "GUEST" if len(self.session) > 1 and player is not self.player else ""

    # ------------------------------------------------------------ building
    def build_props(self):
        self.decorations = HomeDecorationManager(self.profile, HOME_SLOTS, default_catalog())
        self.decorations.on_change = self._decorations_changed
        board = build_daily_board(self.profile, (300, 26))
        self.furniture = [
            FloorLamp((26, 64)),
            Prop(make_couch(), (150, 38), (151, 50, 58, 16)),
            CoffeeTable((166, 94)),
            Prop(make_beanbag(), (234, 102), (235, 110, 20, 8)),
            Speaker((96, 92)),
            board,
        ]
        return self.furniture + self.decorations.props

    def _decorations_changed(self):
        """A decoration was swapped: pick up its new props and collision."""
        self.props = self.furniture + self.decorations.props
        self.rebuild_solids()

    def build_renderer(self):
        style, t = self.style, self.theme
        backdrop = HomeBackdrop((VIEW_W, VIEW_H), t, {"left": ("ARCADE", Col.CYAN),
                                                      "right": ("PRIZES", Col.YELLOW)}, style)
        animator = AmbientAnimator()
        strip = pygame.Surface((VIEW_W - 2 * WALL_SIDE, 1), pygame.SRCALPHA)
        strip.fill((196, 160, 255))
        animator.add(RainWindow(WINDOW), "overlay")
        animator.add(NeonLight(strip, (WALL_SIDE, WALL_STRIP_Y), t.accent_a, spread=5,
                               strength=style.strength(0.4), speed=0.45, depth=0.3), "wall")
        # small cyan and magenta accents low on the wall: neon, but kept quiet
        for x, w, color, phase in ((30, 110, Lofi.CYAN, 0.0), (262, 108, t.accent_b, 1.7)):
            tube = pygame.Surface((w, 1), pygame.SRCALPHA)
            tube.fill(scale_color(color, 1.0))
            animator.add(NeonLight(tube, (x, FLOOR_TOP - 3), color, spread=3,
                                   strength=style.strength(0.22), speed=0.5, depth=0.35,
                                   phase=phase), "wall")
        animator.add(StringLights(WALL_SIDE, VIEW_W - WALL_SIDE, 2, span=60, sag=4), "overlay")
        animator.add(DustMotes((30, 70, 340, 200), count=16), "overlay")
        animator.add(Scanlines((VIEW_W, VIEW_H), alpha=style.scanline_alpha(10)), "overlay")
        pools = [((200, 190), 140, (14, 8, 28), 0.8),         # soft purple fill
                 ((32, 100), 50, (44, 26, 10), 0.75),         # floor lamp
                 ((180, 110), 80, (22, 12, 24), 0.6),         # lounge rug
                 ((80, 244), 36, (30, 18, 10), 0.6),          # cat bed
                 ((322, 246), 36, (30, 18, 10), 0.6),
                 ((43, 76), 34, (8, 18, 36), 0.5)]            # window light on the floor
        lighting = LightingOverlay((VIEW_W, VIEW_H), edge=t.light_edge, center=t.light_center,
                                   pools=[(pos, r, style.light(c), sq) for pos, r, c, sq in pools])
        return BackgroundRenderer(backdrop, animator, lighting)

    # ------------------------------------------------------------ per frame
    def update_room(self, dt):
        self.decorations.update(dt)

    def draw_under_sprites(self, surf):
        self.decorations.draw_flat(surf)

    def draw_room_overlay(self, surf):
        self.decorations.draw_neon(surf)

    # ------------------------------------------------------------ daily login
    def on_room_enter(self):
        self._offer_daily_bonus()

    def on_new_day(self):
        self._offer_daily_bonus()

    def _offer_daily_bonus(self):
        """Show the DAILY BONUS popup of the first player whose reward is
        unclaimed (the next player's follows once it closes). Not again today
        once a player has put theirs off with ESC. A profile refuses a second
        claim, so re-offering can never pay twice - and a bonus is only ever
        claimed into the profile it was offered to."""
        if self.popup is not None:
            return
        for player in self.players:
            profile = player.profile
            today = profile.clock.today()
            status = profile.daily_status(today)
            if status.can_claim and self._declined.get(player) != today:
                self.popup = DailyBonusPopup(status.day, status.bundle.lines(),
                                             profile.claim_daily_reward, owner=self._owner_tag(player))
                self.popup.player = player
                self._own_modal(player)
                return

    def on_popup_closed(self, popup):
        player = getattr(popup, "player", self.player)
        if popup.dismissed:
            self._declined[player] = player.profile.clock.today()
        self._offer_daily_bonus()
