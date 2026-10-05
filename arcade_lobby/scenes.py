"""The arcade room scene, the placeholder minigame scene and the registry
that maps machines to their minigame scenes.

To plug in a real minigame, write a MinigameScene subclass (minigame.py) whose
constructor takes (game, machine), register it in MINIGAME_SCENES under the
machine id, override get_reward() with its scoring, and call
`self.game.scenes.pop()` when the player quits.

Paying for a game: choosing PLAY charges the machine's play_cost through
machine.start_play(), which returns a PlaySession. When the minigame is popped
the room settles that session with the minigame's reward - once.
"""
import math

import pygame

from ambience import AmbienceManager
from cat_colony import CatColony
from chance_scene import ChanceGameScene
from daily_ui import DailyBonusPopup, TaskPanel
from inventory_ui import InventoryUI
from item_registry import FREE_PLAY_COUPON
from rewards import RewardService
from font import LINE_H, get_font
from gfx import lerp_color, scale_color, shade
from hud import CurrencyHUD
from lofi_room import LofiRoom
from machine import ArcadeMachine
from minigame import MinigameScene
from player import Player
from retro_racer_scene import RetroRacerScene
from room import Room
from scene_base import BaseScene
from settings import (BACK_KEYS, BACKGROUND_STYLE, CATS, Col, DEBUG_NEXT_DAY_KEY,
                      DEBUG_COUPON_KEY, DEBUG_RESET_TASKS_KEY, DEBUG_STICKER_KEY,
                      DEBUG_TOKEN_KEY, DEBUG_TOKENS, INTERACT_FLASH,
                      INTERACT_KEYS, INVENTORY_KEY, MACHINES, MOVE_KEYS,
                      PLAYER_START, VIEW_H, VIEW_W)
from stations import Station, build_stations
from ui import (DialogueBox, InstructionBox, Notice, PromptBubble, draw_text,
                neon_panel, wrap_text)


# Background style name -> room class (see settings.BACKGROUND_STYLES)
ROOM_STYLES = {"lofi": LofiRoom, "neon": Room}

PLAY, PLAY_LOCKED, CANCEL = "PLAY", "PLAY  [LOCKED]", "CANCEL"
COUPON_INPUT_DELAY = 0.3     # seconds the coupon question ignores keys


class ArcadeRoomScene(BaseScene):
    def __init__(self, game, style=BACKGROUND_STYLE):
        super().__init__(game)
        self.machines = [ArcadeMachine(data) for data in MACHINES]
        self.stations = build_stations(game.profile)
        self.room = ROOM_STYLES[style](self.machines, self.stations)
        # everything the player can walk up to and press E on
        self.interactables = self.machines + [s for s in self.stations if isinstance(s, Station)]
        self.player = Player(PLAYER_START)
        self.cats = CatColony(CATS, self.room)
        self.ambience = AmbienceManager()
        self.ambience.start()
        self.held = []          # movement keys currently held, in press order
        self.dialogue = None
        self.activating = None  # (target, time left) while the E-flash plays
        self.popup = None       # DailyBonusPopup while the login bonus is offered
        self.panel = None       # TaskPanel while the daily board is open
        self.inventory_ui = None    # InventoryUI while the bag is open
        self._declined_day = None   # the day the player pressed ESC on the bonus
        self._day_timer = 0.0
        self._ready_tasks = 0
        self.nearby = None
        self.nearby_cat = None
        self.prompt = PromptBubble()
        self.instructions = InstructionBox()
        self.hud = CurrencyHUD(game.profile)
        self.notice = Notice()
        self.active_play = None  # (PlaySession, minigame scene) while a paid game runs
        self.time = 0.0
        self.profile.record_login()
        self._ready_tasks = len(self.profile.claimable_tasks)
        self._offer_daily_bonus()

    @property
    def profile(self):
        return self.game.profile

    def on_resume(self):
        # Key-ups may have happened inside the minigame; start clean.
        self.held.clear()
        self.activating = None
        self.dialogue = None
        self.panel = None
        self.inventory_ui = None
        self.player.stop()
        self.ambience.resume()
        self.cats.resume()
        self.hud.clear_effects()
        self._end_play(ran=True)
        self._check_new_day()

    def on_quit(self):
        # Closing the window mid-game still pays out what was played; if the
        # wipe into the game had not finished yet, the tokens are refunded.
        if self.active_play is not None:
            _, scene = self.active_play
            self._end_play(ran=scene in self.game.scenes.stack)

    def _end_play(self, ran):
        """Settle (or refund) the paid minigame that just closed. active_play
        is cleared first and a PlaySession ends only once, so this can never
        pay or refund twice for one token."""
        if self.active_play is None:
            return
        session, scene = self.active_play
        self.active_play = None
        if not ran or scene.failed:
            if session.refund():
                unit = "TOKEN" if session.cost == 1 else "TOKENS"
                back = "COUPON RETURNED" if session.coupon else f"+{session.cost} {unit} REFUNDED"
                self.notice.show("GAME UNAVAILABLE", [(back, Col.YELLOW)], Col.MAGENTA)
            return
        result = session.settle(scene.get_reward())
        if result is not None:
            self.notice.show("GAME COMPLETE", [(f"+{result.tickets_earned} TICKETS", Col.YELLOW)],
                             Col.GREEN)

    # ------------------------------------------------------------ daily bonus
    def _offer_daily_bonus(self):
        """Show the DAILY BONUS popup if today's reward is unclaimed. Not
        again today once the player has put it off with ESC."""
        today = self.profile.clock.today()
        status = self.profile.daily_status(today)
        if self.popup is None and status.can_claim and self._declined_day != today:
            self.popup = DailyBonusPopup(status.day, status.tokens, self._claim_daily_bonus)

    def _claim_daily_bonus(self):
        self.profile.claim_daily_reward()      # the profile refuses a second claim

    def _check_new_day(self):
        """The calendar date may have changed while the arcade stayed open (or
        while a minigame ran): roll the tasks and offer the new bonus."""
        self.profile.sync_daily_tasks()
        self._offer_daily_bonus()

    def open_task_panel(self):
        self.panel = TaskPanel(self.profile)

    def _watch_tasks(self):
        """A one-line, non-blocking hint when a challenge becomes claimable."""
        ready = len(self.profile.claimable_tasks)
        if ready > self._ready_tasks and not self.notice.visible:
            self.notice.show("CHALLENGE COMPLETE", [("CLAIM IT AT THE DAILY BOARD", Col.YELLOW)],
                             Col.CYAN)
        self._ready_tasks = ready

    # ------------------------------------------------------------ input
    def handle_event(self, event):
        if event.type == pygame.WINDOWFOCUSLOST:
            self.held.clear()
        elif event.type == pygame.KEYUP and event.key in self.held:
            self.held.remove(event.key)

        modal = self.popup or self.panel or self.inventory_ui or self.dialogue
        if modal:
            modal.handle_event(event)
            return
        if event.type != pygame.KEYDOWN or self.activating:
            return
        if self.game.debug and self._debug_key(event.key):
            return
        if event.key == INVENTORY_KEY:
            self.inventory_ui = InventoryUI(self.profile.inventory)
            self.held.clear()
        elif event.key in MOVE_KEYS and event.key not in self.held:
            self.held.append(event.key)
        elif event.key in INTERACT_KEYS and self.nearby:
            if isinstance(self.nearby, ArcadeMachine):
                self.profile.record_machine_visit(self.nearby.id)
            self.nearby.activate()
            self.activating = (self.nearby, INTERACT_FLASH)
        elif event.key in INTERACT_KEYS and self.nearby_cat:
            if self.cats.interact(self.nearby_cat):
                self.profile.record_cat_petted()

    def _debug_key(self, key):
        """Debug-build helpers. Returns True if `key` was one of them."""
        if key == DEBUG_TOKEN_KEY:
            self.profile.add_tokens(DEBUG_TOKENS, "DEBUG")
        elif key == DEBUG_NEXT_DAY_KEY:
            self.profile.clock.advance_days(1)
            self._check_new_day()
        elif key == DEBUG_RESET_TASKS_KEY:
            self.profile.reset_daily_tasks()
        elif key == DEBUG_STICKER_KEY:
            RewardService.grant_item(self.profile, "cat_sticker")
        elif key == DEBUG_COUPON_KEY:
            RewardService.grant_item(self.profile, "free_play_coupon")
        else:
            return False
        return True

    def open_dialogue(self, machine):
        # Opening (and cancelling) the dialogue is free: tokens are only taken
        # in _start_game, after PLAY is confirmed.
        affordable = machine.can_play(self.profile)      # tokens, or a coupon
        coupons = self.profile.inventory.get_quantity(FREE_PLAY_COUPON)
        details = [(f"COST: {machine.cost_label}", Col.YELLOW),
                   (f"TOKENS: {self.profile.tokens}", Col.TEXT_MUTED if affordable else Col.MAGENTA)]
        if coupons:
            details.append((f"FREE PLAY COUPONS: {coupons}", Col.GREEN))
        self.dialogue = DialogueBox(
            machine.name, machine.description, [PLAY if affordable else PLAY_LOCKED, CANCEL],
            on_choice=lambda choice: self._on_choice(machine, choice),
            accent=machine.accent, glow=machine.neon,
            details=details, locked=() if affordable else (0,))

    def _on_choice(self, machine, choice):
        self.dialogue = None
        if choice not in (PLAY, PLAY_LOCKED):
            return
        if machine.can_use_coupon(self.profile):
            self._ask_coupon(machine)
        else:
            self._start_game(machine)

    def _ask_coupon(self, machine):
        """PLAY was confirmed and the player owns a coupon: YES uses one
        (no tokens), NO pays tokens as usual, ESC cancels. The box ignores
        keys for a moment so a mashed PLAY cannot answer it by accident."""
        count = self.profile.inventory.get_quantity(FREE_PLAY_COUPON)
        self.dialogue = DialogueBox(
            "COUPON", "USE FREE PLAY COUPON?", ["YES", "NO"],
            on_choice=lambda choice: self._on_coupon_choice(machine, choice),
            accent=Col.GREEN, glow=machine.neon,
            details=[(f"YOU HAVE: {count}", Col.GREEN),
                     (f"NO PAYS {machine.cost_label}", Col.TEXT_MUTED)],
            input_delay=COUPON_INPUT_DELAY)

    def _on_coupon_choice(self, machine, choice):
        self.dialogue = None
        if choice == "YES":
            self._start_game(machine, use_coupon=True)
        elif choice == "NO":
            self._start_game(machine)

    def _open_target(self, target):
        """The E-flash finished: open whatever the player used."""
        if isinstance(target, ArcadeMachine):
            self.open_dialogue(target)
        else:
            target.interact(self)

    def open_chance_game(self, game_cls):
        """Walk into a Lucky Corner game. Nothing is charged here: the game
        itself charges when its round starts."""
        if self.active_play is not None or self.game.scenes.transitioning:
            return
        self.notice.clear()
        self.ambience.pause()
        self.cats.pause()
        self.game.scenes.push(ChanceGameScene(self.game, game_cls))

    def _start_game(self, machine, use_coupon=False):
        # A paid game is already starting/running, or a wipe is in progress
        # (SceneManager would drop the push): never charge in those states.
        if self.active_play is not None or self.game.scenes.transitioning:
            return
        if use_coupon and not machine.can_use_coupon(self.profile):
            self.notice.show("NO COUPON LEFT", [("NOTHING WAS CHARGED", Col.TEXT_MUTED)], Col.MAGENTA)
            return
        if not use_coupon and not machine.can_afford(self.profile):
            self.notice.show("NOT ENOUGH TOKENS", [
                (f"NEED: {machine.play_cost}", Col.YELLOW),
                (f"YOU HAVE: {self.profile.tokens}", Col.TEXT_MUTED)], Col.MAGENTA)
            return
        scene = create_minigame_scene(self.game, machine)   # built before charging
        session = machine.start_play(self.profile, use_coupon)
        if session is None:
            return
        self.active_play = (session, scene)
        self.notice.clear()
        self.ambience.pause()
        self.cats.pause()       # cats stay in the hub; they settle down until we're back
        self.game.scenes.push(scene)

    def _direction(self):
        dx = dy = 0
        for key in self.held:
            vx, vy = MOVE_KEYS[key]
            dx, dy = dx + vx, dy + vy
        return max(-1, min(1, dx)), max(-1, min(1, dy))

    # ------------------------------------------------------------ update
    def update(self, dt):
        self.time += dt
        self.room.update(dt)
        for m in self.machines:
            m.update(dt)

        if self.activating:
            target, left = self.activating
            left -= dt
            self.activating = (target, left)
            if left <= 0:
                self.activating = None
                self._open_target(target)

        busy = (self.dialogue is not None or self.activating is not None
                or self.popup is not None or self.panel is not None
                or self.inventory_ui is not None)
        if self.dialogue:
            self.dialogue.update(dt)
        self._update_modals(dt)
        self._day_timer += dt
        if self._day_timer >= 1.0:
            self._day_timer = 0.0
            self._check_new_day()
        self._watch_tasks()
        self.hud.update(dt)
        self.notice.update(dt)
        solids = self.room.solids + self.cats.blockers(self.player)
        self.player.update(dt, (0, 0) if busy else self._direction(), solids)
        self.cats.update(dt, self.player, busy)

        # Machines win over cats when both are in reach.
        self.nearby = None if busy else self._find_nearby()
        self.nearby_cat = None if busy or self.nearby else self.cats.find_nearby(self.player)
        for m in self.interactables:
            m.highlight = m is self.nearby
        target = self.nearby or self.nearby_cat
        anchor = (int(self.player.x), int(self.player.y) - 22) if target else None
        label = self.nearby.prompt_label if self.nearby else self.nearby_cat and self.nearby_cat.personality.prompt
        self.prompt.update(dt, anchor, label)

    def _update_modals(self, dt):
        if self.popup:
            self.popup.update(dt)
            if self.popup.done:
                if self.popup.dismissed:
                    self._declined_day = self.profile.clock.today()
                self.popup = None
        if self.panel:
            self.panel.update(dt)
            if self.panel.closed:
                self.panel = None
        if self.inventory_ui:
            self.inventory_ui.update(dt)
            if self.inventory_ui.closed:
                self.inventory_ui = None

    def _find_nearby(self):
        feet = self.player.feet
        close = [m for m in self.interactables if m.zone.colliderect(feet)]
        return min(close, key=lambda m: abs(m.rect.centerx - self.player.x), default=None)

    # ------------------------------------------------------------ draw
    def draw(self, surf):
        self.room.draw_background(surf)
        things = self.room.drawables() + [self.player] + self.cats.drawables()
        things.sort(key=lambda t: t.sort_y)
        for thing in things:
            thing.draw_under(surf)
        for thing in things:
            thing.draw(surf)
        self.room.draw_lighting(surf)
        for m in self.machines:
            m.draw_glow(surf)
        self.cats.draw_overlay(surf)

        self.prompt.draw(surf, self.time)
        self.instructions.draw(surf)
        self.hud.draw(surf)
        self.notice.draw(surf)
        if self.dialogue:
            self.dialogue.draw(surf)
        if self.panel:
            self.panel.draw(surf)
        if self.inventory_ui:
            self.inventory_ui.draw(surf)
        if self.popup:
            self.popup.draw(surf)


class MinigamePlaceholderScene(MinigameScene):
    """Stand-in for a machine's minigame: a synthwave-style title card in the
    machine's own neon colours. ESC returns to the arcade (and pays the
    temporary flat reward from MinigameScene.get_reward)."""
    HORIZON = 132

    def __init__(self, game, machine):
        super().__init__(game, machine)
        self.time = 0.0
        neon, accent = machine.neon, machine.accent
        self.grid_color = scale_color(neon, 0.8)
        self.background = self._build_background(neon, accent)

        font = get_font()
        self.title = font.render_glow(machine.name, shade(accent, 0.6), neon, scale=3)
        self.panel = neon_panel(236, 108, accent, neon, 245).copy()
        draw_text(self.panel, "PROTOTYPE MINIGAME SCREEN", (10, 10), shade(accent, 0.4),
                  glow=scale_color(neon, 0.5))
        self.panel.fill(scale_color(accent, 0.6), (10, 21, 216, 1))
        y = 28
        for line in wrap_text(machine.description, 216):
            draw_text(self.panel, line, (10, y), Col.TEXT_MUTED)
            y += LINE_H
        draw_text(self.panel, "REAL GAME COMING SOON!", (10, y + 6), Col.TEXT)
        self.esc = font.render_glow("PRESS ESC TO RETURN TO ARCADE", Col.YELLOW,
                                    scale_color(Col.YELLOW, 0.35))
        self.cabinet = pygame.Surface((38, 64), pygame.SRCALPHA)
        self.cabinet_big = pygame.Surface((76, 128), pygame.SRCALPHA)

    def _build_background(self, neon, accent):
        bg = pygame.Surface((VIEW_W, VIEW_H))
        top, bottom = (8, 4, 20), scale_color(neon, 0.35)
        for y in range(self.HORIZON):                       # banded sky
            k = (y // 8 * 8) / self.HORIZON
            bg.fill(lerp_color(top, bottom, k), (0, y, VIEW_W, 1))
        sun_c = (VIEW_W // 2, self.HORIZON)
        for r, c in ((46, scale_color(neon, 0.8)), (40, accent), (30, shade(accent, 0.4))):
            pygame.draw.circle(bg, c, sun_c, r, draw_top_left=True, draw_top_right=True)
        for i, y in enumerate(range(self.HORIZON - 26, self.HORIZON, 6)):  # sun stripes
            bg.fill(lerp_color(top, bottom, y / self.HORIZON), (0, y, VIEW_W, 1 + i // 2))
        bg.fill((6, 3, 16), (0, self.HORIZON, VIEW_W, VIEW_H - self.HORIZON))
        bg.fill(accent, (0, self.HORIZON, VIEW_W, 1))
        for sx, sy in ((30, 20), (80, 50), (140, 14), (260, 30), (330, 60), (370, 18), (220, 70)):
            bg.fill(Col.TEXT, (sx, sy, 1, 1))
        return bg

    def handle_event(self, event):
        # SceneManager ignores input during the wipe, so ESC pops only once.
        if event.type == pygame.KEYDOWN and event.key in BACK_KEYS:
            self.game.scenes.pop()

    def update(self, dt):
        self.time += dt
        self.machine.update(dt)

    def draw(self, surf):
        surf.blit(self.background, (0, 0))
        self._draw_grid(surf)

        bob = int(math.sin(self.time * 2.2) * 2)
        surf.blit(self.title, self.title.get_rect(midtop=(VIEW_W // 2, 20 + bob)))

        # cabinet preview, redrawn into reusable surfaces (no per-frame allocs)
        self.cabinet.fill((0, 0, 0, 0))
        self.machine.draw_at(self.cabinet, (1, 1))
        pygame.transform.scale(self.cabinet, self.cabinet_big.get_size(), self.cabinet_big)
        surf.blit(self.cabinet_big, (34, 132 - bob))

        surf.blit(self.panel, (136, 146))
        if int(self.time * 2.5) % 2 == 0:
            surf.blit(self.esc, self.esc.get_rect(midbottom=(136 + 118, 146 + 100)))

    def _draw_grid(self, surf):
        h0, depth = self.HORIZON, VIEW_H - self.HORIZON
        cx = VIEW_W // 2
        for x in range(-VIEW_W, VIEW_W * 2, 40):
            pygame.draw.line(surf, self.grid_color, (cx + (x - cx) * 0.08, h0), (x, VIEW_H))
        phase = (self.time * 0.8) % 1.0
        for k in range(12):
            d = (k + phase) / 12
            y = h0 + int(depth * d * d)
            surf.fill(self.grid_color, (0, y, VIEW_W, 1))


# Machine id -> scene class. Anything not listed uses the placeholder, so real
# minigames can be dropped in one at a time.
MINIGAME_SCENES = {"retro_racer": RetroRacerScene}


def create_minigame_scene(game, machine):
    scene_cls = MINIGAME_SCENES.get(machine.id, MinigamePlaceholderScene)
    return scene_cls(game, machine)
