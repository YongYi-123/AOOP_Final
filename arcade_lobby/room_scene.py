"""BaseRoomScene: everything the three hub rooms (HOME, ARCADE FLOOR, PRIZE
PLAZA) have in common, and the RoomHub that connects them.

A room scene owns what is specific to its place: its props and machines,
background art, cats, doorways and the hints it shows. The shared player,
wallet HUD and ambience belong to the RoomHub, so walking through a door never
creates a second player or touches the PlayerProfile (tokens, tickets,
inventory, daily progress and the save file are the one `game.profile`). Only
the active room is updated and drawn: the SceneManager keeps just that room on
the stack, and the others sit frozen in the hub with their cats, machine
animations and decorations exactly as they were left.

Paying for a game: choosing PLAY charges the machine's play_cost through
machine.start_play(), which returns a PlaySession. When the minigame is popped
the room settles that session with the minigame's reward - once. (To plug in a
real minigame see scenes.py.)
"""
from dataclasses import dataclass

import pygame

from cat_colony import CatColony
from chance_scene import ChanceGameScene
from daily_ui import TaskPanel
from inventory_ui import InventoryUI
from item_registry import FREE_PLAY_COUPON
from machine import ArcadeMachine
from rewards import RewardService
from room import room_walls
from scene_base import BaseScene
from scenes import create_minigame_scene
from settings import (ARRIVAL_GRACE, CATS, Col, DEBUG_COUPON_KEY, DEBUG_NEXT_DAY_KEY,
                      DEBUG_RESET_TASKS_KEY, DEBUG_STICKER_KEY, DEBUG_TOKEN_KEY,
                      DEBUG_TOKENS, ENTRY_INSET, EXIT_DEPTH, INTERACT_FLASH,
                      INTERACT_KEYS, INVENTORY_KEY, MOVE_KEYS, PLAYER_START,
                      ROOM_IDS, SIDE_DOOR_H, SIDE_DOOR_Y, START_ROOM,
                      TRANSITION_TIME, VIEW_W)
from stations import Station
from ui import DialogueBox, InstructionBox, Notice, PromptBubble, RoomTitle

PLAY, PLAY_LOCKED, CANCEL = "PLAY", "PLAY  [LOCKED]", "CANCEL"
COUPON_INPUT_DELAY = 0.3     # seconds the coupon question ignores keys

DOOR_Y_MID = SIDE_DOOR_Y + SIDE_DOOR_H // 2 + 2


@dataclass(frozen=True)
class RoomExit:
    """A doorway: walking into the `side` edge of the room leads to room
    `target`, where the player appears at that room's `entry`."""
    side: str       # "left" or "right"
    target: str     # a room id
    entry: str      # "left" or "right": the doorway the player arrives through

    @property
    def trigger(self):
        """Canvas area that counts as 'through the door'."""
        x = 0 if self.side == "left" else VIEW_W - EXIT_DEPTH
        return pygame.Rect(x, SIDE_DOOR_Y, EXIT_DEPTH, SIDE_DOOR_H)

    @property
    def zone(self):
        """The floor in front of the door, which cats keep clear of."""
        x = 0 if self.side == "left" else VIEW_W - 60
        return pygame.Rect(x, SIDE_DOOR_Y - 4, 60, SIDE_DOOR_H + 8)


# where a player arriving through each door stands, and which way they face
ENTRIES = {
    "left": ((ENTRY_INSET, DOOR_Y_MID), "right"),
    "right": ((VIEW_W - ENTRY_INSET, DOOR_Y_MID), "left"),
    "spawn": (PLAYER_START, "up"),
}


class BaseRoomScene(BaseScene):
    room_id = None
    ambience_mix = {}           # ambience layer -> volume while this room is on screen
    exits = ()                  # RoomExit doorways
    cat_spots = {}              # cat id -> places it likes (first = home); only cats of this room
    hint_rows = None            # rows for the controls box (see ui.InstructionBox)

    def __init__(self, game, hub):
        super().__init__(game)
        self.hub = hub
        self.style = hub.style              # one shared ArcadeStyle ...
        self.theme = self.style.theme_for(self.room_id)     # ... with this room's own accents
        self.player = hub.player            # one player for the whole hub
        self.hud = hub.hud
        self.machines = self.build_machines()
        for m in self.machines:
            m.soft_glow = self.style.soft_machines
        self.props = self.build_props()     # furniture and stations
        self.walls = room_walls([e.side for e in self.exits])
        self.solids = []
        self.rebuild_solids()
        self.renderer = self.build_renderer()
        self.keep_clear_areas = [e.zone for e in self.exits]
        roster = [data for data in CATS if data.get("room", "home") == self.room_id]
        self.cats = CatColony(roster, self)
        # everything the player can walk up to and press E on
        self.interactables = self.machines + [p for p in self.props if isinstance(p, Station)]

        self.held = []          # movement keys currently held, in press order
        self.dialogue = None
        self.activating = None  # (target, time left) while the E-flash plays
        self.popup = None       # the daily login bonus (HOME)
        self.panel = None       # TaskPanel while the daily board is open (HOME)
        self.inventory_ui = None    # InventoryUI while the bag is open
        self._day_timer = 0.0
        self._ready_tasks = 0
        self.nearby = None
        self.nearby_cat = None
        self.prompt = PromptBubble()
        self.instructions = InstructionBox(self.hint_rows)
        self.notice = Notice()
        self.title = RoomTitle(self.theme.name, self.theme.title, self.theme.title_glow)
        self.active_play = None  # (PlaySession, minigame scene) while a paid game runs
        self.leaving = False     # a doorway was entered: no more input until the swap
        self.arrival_grace = 0.0
        self.time = 0.0

    @property
    def profile(self):
        return self.game.profile

    # ------------------------------------------------------------ building (hooks)
    def build_machines(self):
        return []

    def build_props(self):
        return []

    def build_renderer(self):
        raise NotImplementedError

    def rebuild_solids(self):
        """Recompute collision in place (cats hold a reference to the list)."""
        self.solids[:] = (self.walls + [p.footprint for p in self.props if p.solid]
                          + [m.footprint for m in self.machines])

    def on_room_enter(self):
        """Hook: the player just walked in (or the game started here)."""

    def on_new_day(self):
        """Hook: the calendar date changed while the game was open."""

    def update_room(self, dt):
        """Hook: per-frame work specific to this room."""

    def draw_room_overlay(self, surf):
        """Hook: draw this room's own extras over the lit scene."""

    # ------------------------------------------------------------ scene lifecycle
    def on_enter(self):
        entry = self.hub.take_arrival() or "spawn"
        pos, facing = ENTRIES[entry]
        self._close_transients()
        self.player.x, self.player.y = float(pos[0]), float(pos[1])
        self.player.facing = facing
        self.player.stop()
        self.leaving = False
        self.arrival_grace = ARRIVAL_GRACE
        self.hud.clear_effects()
        self.hub.ambience.set_mix(self.ambience_mix)
        self.cats.resume()
        self.held = self._keys_down()
        self._ready_tasks = len(self.profile.claimable_tasks)
        self.title.show(delay=TRANSITION_TIME)
        self.profile.sync_daily_tasks()
        self.on_room_enter()

    def on_exit(self):
        """Leaving the room: close anything open and let the cats settle."""
        self._close_transients()
        self.cats.pause()
        self.title.clear()

    def on_resume(self):
        # Key-ups may have happened inside the minigame; start clean.
        self._close_transients()
        self.hub.ambience.resume()
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

    def _close_transients(self):
        """Close dialogue, panels and the E-flash, drop held keys and stop the
        player: nothing half-open survives a room change or a minigame."""
        self.held.clear()
        self.activating = None
        self.dialogue = None
        self.panel = None
        self.popup = None
        self.inventory_ui = None
        self.notice.clear()
        self.player.stop()
        for thing in self.interactables:
            thing.highlight = False
            thing.flash_time = 0.0
        self.nearby = self.nearby_cat = None

    @staticmethod
    def _keys_down():
        """Movement keys physically held right now, so walking carries on
        through a doorway instead of stopping dead."""
        try:
            pressed = pygame.key.get_pressed()
            return [k for k in MOVE_KEYS if pressed[k]]
        except (pygame.error, IndexError):
            return []

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

    # ------------------------------------------------------------ daily clock
    def _check_new_day(self):
        """The calendar date may have changed while the game stayed open (or
        while a minigame ran): roll the tasks, and let the room react."""
        self.profile.sync_daily_tasks()
        self.on_new_day()

    def _watch_tasks(self):
        """A one-line, non-blocking hint when a challenge becomes claimable."""
        ready = len(self.profile.claimable_tasks)
        if ready > self._ready_tasks and not self.notice.visible:
            where = "AT THE DAILY BOARD" if self.room_id == "home" else "AT THE BOARD IN HOME"
            self.notice.show("CHALLENGE COMPLETE", [(f"CLAIM IT {where}", Col.YELLOW)], Col.CYAN)
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
        if event.type != pygame.KEYDOWN or self.activating or self.leaving:
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

    # ------------------------------------------------------------ machines
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

    def _pause_for_minigame(self):
        self.notice.clear()
        self.hub.ambience.pause()
        self.cats.pause()       # cats stay put; they settle down until we're back

    def open_chance_game(self, game_cls):
        """Walk into a Lucky Corner game. Nothing is charged here: the game
        itself charges when its round starts."""
        if self.active_play is not None or self.game.scenes.transitioning:
            return
        self._pause_for_minigame()
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
        self._pause_for_minigame()
        self.game.scenes.push(scene)

    def open_task_panel(self):
        self.panel = TaskPanel(self.profile)

    # ------------------------------------------------------------ doorways
    def _check_exits(self):
        if self.arrival_grace > 0 or self.leaving or self.active_play is not None:
            return
        feet = self.player.feet
        for door in self.exits:
            if feet.colliderect(door.trigger):
                self.leaving = self.hub.travel(self, door)
                if self.leaving:
                    self.held.clear()
                return

    # ------------------------------------------------------------ update
    def _direction(self):
        dx = dy = 0
        for key in self.held:
            vx, vy = MOVE_KEYS[key]
            dx, dy = dx + vx, dy + vy
        return max(-1, min(1, dx)), max(-1, min(1, dy))

    def update(self, dt):
        self.time += dt
        self.arrival_grace = max(0.0, self.arrival_grace - dt)
        self.renderer.update(dt)
        for prop in self.props:
            prop.update(dt)
        for m in self.machines:
            m.update(dt)
        self.update_room(dt)

        if self.activating:
            target, left = self.activating
            left -= dt
            self.activating = (target, left)
            if left <= 0:
                self.activating = None
                self._open_target(target)

        busy = (self.dialogue is not None or self.activating is not None
                or self.popup is not None or self.panel is not None
                or self.inventory_ui is not None or self.leaving)
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
        self.title.update(dt)
        solids = self.solids + self.cats.blockers(self.player)
        self.player.update(dt, (0, 0) if busy else self._direction(), solids)
        self.cats.update(dt, self.player, busy)
        self._check_exits()

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
                self.on_popup_closed(self.popup)
                self.popup = None
        if self.panel:
            self.panel.update(dt)
            if self.panel.closed:
                self.panel = None
        if self.inventory_ui:
            self.inventory_ui.update(dt)
            if self.inventory_ui.closed:
                self.inventory_ui = None

    def on_popup_closed(self, popup):
        """Hook: the popup finished (claimed, or put off with ESC)."""

    def _find_nearby(self):
        feet = self.player.feet
        close = [m for m in self.interactables if m.zone.colliderect(feet)]
        return min(close, key=lambda m: abs(m.rect.centerx - self.player.x), default=None)

    # ------------------------------------------------------------ draw
    def drawables(self):
        return self.props + self.machines

    def draw(self, surf):
        self.renderer.draw_background(surf)
        self.draw_under_sprites(surf)
        things = self.drawables() + [self.player] + self.cats.drawables()
        things.sort(key=lambda t: t.sort_y)
        for thing in things:
            thing.draw_under(surf)
        for thing in things:
            thing.draw(surf)
        self.renderer.draw_lighting(surf)
        for prop in self.props:
            prop.draw_glow(surf)
        self.renderer.draw_overlay(surf)
        self.draw_room_overlay(surf)
        for m in self.machines:
            m.draw_glow(surf)
        self.cats.draw_overlay(surf)

        self.prompt.draw(surf, self.time)
        self.instructions.draw(surf)
        self.hud.draw(surf)
        self.notice.draw(surf)
        self.title.draw(surf)
        if self.dialogue:
            self.dialogue.draw(surf)
        if self.panel:
            self.panel.draw(surf)
        if self.inventory_ui:
            self.inventory_ui.draw(surf)
        if self.popup:
            self.popup.draw(surf)

    def draw_under_sprites(self, surf):
        """Hook: flat things drawn on the floor/wall, below every sprite."""


class RoomHub:
    """The three connected rooms and what they share: the player, the
    currency HUD and the ambience. Rooms are built the first time they are
    visited and then kept, so each one is exactly as it was left."""

    def __init__(self, game, style):
        from ambience import AmbienceManager
        from hud import CurrencyHUD
        from player import Player
        self.game = game
        self.style = style                  # shared by all three rooms
        self.player = Player(PLAYER_START)
        self.hud = CurrencyHUD(game.profile)
        self.ambience = AmbienceManager()
        self.ambience.start()
        self._rooms = {}
        self._arrival = None
        self.registry = room_registry()

    # ------------------------------------------------------------ rooms
    @property
    def built_rooms(self):
        return dict(self._rooms)

    def room(self, room_id):
        if room_id not in ROOM_IDS:
            raise KeyError(f"unknown room {room_id!r}")
        if room_id not in self._rooms:
            self._rooms[room_id] = self.registry[room_id](self.game, self)
        return self._rooms[room_id]

    def start(self, room_id=START_ROOM):
        """Put the player in a room without a wipe (game start)."""
        self._arrival = "spawn"
        self.game.scenes.push(self.room(room_id), fade=False)

    def travel(self, source, door):
        """Walk through `door` of `source`. Refused while a wipe is running, a
        paid game is in flight, or `source` is not the room on screen - so a
        doorway can never fire twice."""
        scenes = self.game.scenes
        if (scenes.transitioning or scenes.current is not source
                or source.active_play is not None):
            return False
        self._arrival = door.entry
        if not scenes.replace(self.room(door.target)):
            self._arrival = None
            return False
        return True

    def take_arrival(self):
        """The doorway the player is arriving through (once), or None."""
        arrival, self._arrival = self._arrival, None
        return arrival

    def close(self):
        self.hud.close()


def room_registry():
    """room id -> room scene class. Imported here because the room modules
    import this one."""
    from arcade_floor import ArcadeFloorScene
    from home_room import HomeRoomScene
    from prize_plaza import PrizePlazaScene
    return {"home": HomeRoomScene, "arcade_floor": ArcadeFloorScene,
            "prize_plaza": PrizePlazaScene}
