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

The game is single-player: one HubPlayer (body, held keys, nearby thing,
prompt) plays for the one profile of the session. The room holds a single modal
(dialogue / panel / bag / popup) at a time and only the player's keys drive it.
`self.players` is the session's list of that one body (kept list-shaped so the
rooms, the story and the cats share one call path).

World state vs player-specific state (what a room may show):

  GLOBAL WORLD STATE - neutral
    daily board sprite (generic terminal), machine score plates, HOME's
    decorations, cats, props.
  PLAYER-SPECIFIC INTERACTION STATE - always the profile that is playing
    wallet HUD, bag, daily panel, machine dialogue / coupon prompts,
    prize counter text, Lucky Corner rounds, daily bonus popups, rewards.

Paying for a game: choosing PLAY charges the machine's play_cost through
machine.start_play(), which returns a PlaySession. When the minigame is popped
the room settles that session with the minigame's reward - once. (To plug in a
real minigame see scenes.py.)
"""
from dataclasses import dataclass

import pygame

from cat_colony import CatColony
from chance_scene import ChanceGameScene
from coin_pusher_scene import CoinPusherScene
from pinball_scene import PinballScene
from neon21_scene import Neon21Scene
from daily_ui import TaskPanel
from inventory_ui import InventoryUI
from novelty import use_item
from novelty_fx import NoveltyFX
from vending_ui import VendingScene
from staff_ui import MaintenanceScene
from item_registry import FREE_PLAY_COUPON
from local_session import GameEvent, MachineInteraction
from machine import ArcadeMachine
from rewards import RewardService
from miao_meow import MiaoMeow
from room import room_walls
from scene_base import BaseScene
from scenes import create_minigame_scene
from settings import (ARRIVAL_GRACE, CATS, Col, DEBUG_COUPON_KEY, DEBUG_NEXT_DAY_KEY,
                      DEBUG_RESET_TASKS_KEY, DEBUG_STICKER_KEY, DEBUG_TOKEN_KEY,
                      DEBUG_TOKENS, ENTRY_INSET, EXIT_DEPTH, INTERACT_FLASH,
                      PLAYER_START, ROOM_IDS, SIDE_DOOR_H, SIDE_DOOR_Y, START_ROOM,
                      TRANSITION_TIME, VIEW_W)
from stations import Station
from ui import DialogueBox, InstructionBox, Notice, RoomTitle, selection_brackets

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


def facing_toward(player, rect):
    """The facing (down / up / left / right) that looks from `player` at `rect`."""
    dx, dy = rect.centerx - player.x, rect.centery - (player.y - 8)
    if abs(dx) > abs(dy) * 1.5:
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"


class BaseRoomScene(BaseScene):
    room_id = None
    ambience_mix = {}           # ambience layer -> volume while this room is on screen
    exits = ()                  # RoomExit doorways
    cat_spots = {}              # cat id -> places it likes (first = home); only cats of this room
    hint_rows = None            # rows for the controls box (see ui.InstructionBox)
    resume_notice = None        # (title, lines, color) to show when a minigame scene closes
    edit_mode = False           # decoration mode: draw only the room itself (no prompts, HUD or tags)

    def __init__(self, game, hub):
        super().__init__(game)
        self.hub = hub
        self.style = hub.style              # one shared ArcadeStyle ...
        self.theme = self.style.theme_for(self.room_id)     # ... with this room's own accents
        self.session = hub.session          # who is playing (the one player)
        self.players = hub.avatars          # their body (a list of one): shared by the whole hub
        self.huds = hub.huds
        self.hud = hub.hud                  # the wallet readout
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
        # (Miao Meow is not in this fixed list: she moves, and is only there while she is in the room; see _candidates)
        self.interactables = self.machines + [p for p in self.props if isinstance(p, Station) and not isinstance(p, MiaoMeow)]

        self.dialogue = None
        self.popup = None       # the daily login bonus (HOME)
        self.panel = None       # TaskPanel while the daily board is open (HOME)
        self.inventory_ui = None    # InventoryUI while the bag is open
        self.novelty_fx = NoveltyFX()   # shows put on by used novelty items
        self._modal_owner = None    # the HubPlayer who opened the open modal
        self.acting_player = None   # the HubPlayer whose press is being carried out (for stations)
        self._day_timer = 0.0
        self._ready = {id(p): len(p.profile.claimable_tasks) for p in self.players}
        self.instructions = InstructionBox(self.build_hint_rows())
        self.notice = Notice()
        self.title = RoomTitle(self.theme.name, self.theme.title, self.theme.title_glow,
                               subtitle=self.title_subtitle())
        self.active_play = None  # (PlaySession, minigame scene) while a paid game runs
        self.interaction = None  # the MachineInteraction last started (who initiated it)
        self.leaving = False     # a doorway was entered: no more input until the swap
        self.arrival_grace = 0.0
        self.time = 0.0

    # ------------------------------------------------------------ players
    @property
    def player(self):
        """The player's body."""
        return self.players[0]

    @property
    def profile(self):
        """The primary player's profile (HOME's owner)."""
        return self.game.profile

    # The player's interaction state, under short names.
    held = property(lambda self: self.player.held,
                    lambda self, v: setattr(self.player, "held", v))
    nearby = property(lambda self: self.player.nearby,
                      lambda self, v: setattr(self.player, "nearby", v))
    nearby_cat = property(lambda self: self.player.nearby_cat,
                          lambda self, v: setattr(self.player, "nearby_cat", v))
    activating = property(lambda self: self.player.activating,
                          lambda self, v: setattr(self.player, "activating", v))
    prompt = property(lambda self: self.player.prompt)

    action_hint = "INTERACT"        # what the use key does in this room

    def title_subtitle(self):
        """Hook: a quiet line under the room name (HOME names its owner)."""
        return None

    def build_hint_rows(self):
        """The controls box: the room's own rows."""
        return self.hint_rows

    def _owner_tag(self, player):
        """A header for the player's panels: None (the panels then show no owner line)."""
        return None

    def _actor(self, player=None):
        """The player an action belongs to: the one named, else the one whose
        press is being carried out, else the player."""
        return player or self.acting_player or self.player

    @property
    def music_duck(self):
        """The music level the story wants right now (the opening muffles it); None leaves it alone. Read by Game.duck_for."""
        return self.hub.story.music_duck

    @property
    def modal(self):
        return self.popup or self.panel or self.inventory_ui or self.dialogue or self.hub.story.modal

    @property
    def modal_owner(self):
        """Who the open modal belongs to (None if nothing is open)."""
        if self.modal is None:
            return None
        return self.player

    def _own_modal(self, player):
        self._modal_owner = player

    def _emit(self, event_type, player, **kw):
        """Send a personal event, owned by `player`, to that player's profile."""
        local = self.session.player_for_avatar(player)
        self.session.dispatch(GameEvent(event_type, local.player_id, **kw))

    # ------------------------------------------------------------ building (hooks)
    def build_machines(self):
        return []

    def build_props(self):
        return []

    def make_miao(self):
        """Miao Meow as this room sees her (a Station: it draws her only while she is here). A room's build_props adds it."""
        self.miao = MiaoMeow(self.hub.story.brain, self.room_id)
        return self.miao

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
        for p in self.players:
            p.x, p.y = float(pos[0]), float(pos[1])
            p.facing = facing
            p.stop()
        self.leaving = False
        self.arrival_grace = ARRIVAL_GRACE
        for hud in self.huds:
            hud.clear_effects()
        self.hub.ambience.set_mix(self.ambience_mix)
        self.cats.resume()
        for p in self.players:
            p.held = p.controls.held_now()
        self._ready = {id(p): len(p.profile.claimable_tasks) for p in self.players}
        self.title.show(delay=TRANSITION_TIME)
        for profile in self.session.profiles:
            profile.sync_daily_tasks()
        self.hub.story.on_room_enter(self)
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
        for hud in self.huds:
            hud.clear_effects()
        self._end_play(ran=True)
        self._check_new_day()
        if self.resume_notice:              # e.g. NEON 21 settled a hand you walked out of
            self.notice.show(*self.resume_notice)
            self.resume_notice = None

    def on_quit(self):
        # Closing the window mid-game still pays out what was played; if the
        # wipe into the game had not finished yet, the tokens are refunded.
        if self.active_play is not None:
            _, scene = self.active_play
            self._end_play(ran=scene in self.game.scenes.stack)

    def _close_transients(self):
        """Close dialogue, panels and the E-flash, drop held keys and stop the
        players: nothing half-open survives a room change or a minigame."""
        self.dialogue = None
        self.panel = None
        self.popup = None
        self.inventory_ui = None
        self.novelty_fx.clear()
        self.notice.clear()
        for p in self.players:
            p.held.clear()
            p.activating = None
            p.nearby = p.nearby_cat = None
            p.stop_action()
            p.stop()
        for thing in self.interactables:
            thing.highlight = False
            thing.flash_time = 0.0

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
        results = scene.get_result()
        profile = self.player.profile
        pr = (results.for_profile(profile.profile_id) if profile.profile_id is not None
              else next(iter(results.player_results[:1]), None))
        paid = session.settle_result(pr) if pr is not None else session.settle(None)
        if paid is None:
            return
        self.play_sound("ticket")
        self.notice.show("GAME COMPLETE", [(f"+{paid.reward.tickets} TICKETS", Col.YELLOW)], Col.GREEN)

    # ------------------------------------------------------------ daily clock
    def _check_new_day(self):
        """The calendar date may have changed while the game stayed open (or
        while a minigame ran): roll everyone's tasks, and let the room react."""
        for profile in self.session.profiles:
            profile.sync_daily_tasks()
        self.on_new_day()

    def _watch_tasks(self):
        """A one-line, non-blocking hint when a challenge becomes claimable."""
        for p in self.players:
            ready = len(p.profile.claimable_tasks)
            if ready > self._ready.get(id(p), 0) and not self.notice.visible:
                where = "AT THE DAILY BOARD" if self.room_id == "home" else "AT THE BOARD IN HOME"
                lines = [(f"CLAIM IT {where}", Col.YELLOW)]
                self.notice.show("CHALLENGE COMPLETE", lines, Col.CYAN)
            self._ready[id(p)] = ready

    # ------------------------------------------------------------ input
    def handle_event(self, event):
        if event.type == pygame.WINDOWFOCUSLOST:
            for p in self.players:
                p.held.clear()
        elif event.type == pygame.KEYUP:
            for p in self.players:
                if event.key in p.held:
                    p.held.remove(event.key)

        modal = self.modal
        if modal:
            if event.type == pygame.KEYDOWN:
                modal.handle_event(event)
            else:
                modal.handle_event(event)
            return
        if event.type != pygame.KEYDOWN or self.leaving:
            return
        if self.hub.story.locked:                       # the opening plays: only the dialogue (a modal) answers keys
            self.hub.story.handle_locked_event(event)
            return
        if self.game.debug and self._debug_key(event.key):
            return
        if event.key == pygame.K_q:                     # the Quest Log (Q belongs to no player's controls)
            self.hub.story.toggle_log(self)
            return
        if event.key == pygame.K_TAB:                   # fold / open the quest drawer (TAB is only a window key elsewhere)
            self.hub.story.toggle_tracker(self)
            return
        local, action = self.session.input.route(event)
        if local is None:
            return
        player, key = local.avatar, event.key
        if player.activating:
            return
        if action == "menu":
            self.inventory_ui = InventoryUI(local.profile.inventory, self._owner_tag(player),
                                            player.look.accent, use_keys=local.controls.item,
                                            on_use=lambda item_id, p=player: self.use_novelty(item_id, p))
            self._own_modal(player)
            player.held.clear()
        elif action in ("up", "down", "left", "right") and key not in player.held:
            player.held.append(key)
        elif action == "emote":
            self._emote(player)
        elif action == "interact" and player.sitting:
            player.stop_action()                    # E on the seat stands up (and does nothing else)
        elif action == "interact" and player.nearby:
            if isinstance(player.nearby, ArcadeMachine):
                self._emit("machine_visited", player, key=player.nearby.id)
            player.nearby.activate()
            player.activating = (player.nearby, INTERACT_FLASH)
            player.play_action("press", facing_toward(player, player.nearby.rect))
        elif action == "interact" and player.nearby_cat:
            if self.cats.interact(player.nearby_cat, player):
                self._emit("cat_petted", player)
                player.play_action("pet", facing_toward(player, player.nearby_cat.feet), emote="heart")   # (the cat answers)

    def _emote(self, player):
        """T / '/': wave, then celebrate on the next press. Never while a window is open or
        while the player is already doing something (sitting, E-flash)."""
        if player.activating or player.sitting:
            return
        pose = "cheer" if player.action == "wave" else "wave"
        player.play_action(pose, "down")
        self.play_sound("emote")

    def sit_player(self, seat):
        """A SEAT was used: the acting player sits on it unless somebody else already does."""
        player = self._actor()
        if any(p is not player and p.sitting and p.seat == seat.seat_pos for p in self.players):
            self.notice.show("SEAT TAKEN", [], Col.YELLOW)
            return
        player.sit(seat.seat_pos, "down", seat.sort_y)
        self.play_sound("sit")

    def play_sound(self, name):
        audio = getattr(self.game, "audio", None)
        if audio is not None:
            audio.play(name)

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
    def open_dialogue(self, machine, player=None):
        # Opening (and cancelling) the dialogue is free: tokens are only taken
        # in _start_game, after PLAY is confirmed. Everything shown and later
        # charged belongs to the player who pressed the key.
        player = self._actor(player)
        profile = player.profile
        local = self.session.player_for_avatar(player)
        self.interaction = MachineInteraction(machine, local)
        affordable = machine.can_play(profile)      # tokens, or a coupon
        coupons = profile.inventory.get_quantity(FREE_PLAY_COUPON)
        details = [(f"COST: {machine.cost_label}", Col.YELLOW),
                   (f"TOKENS: {profile.tokens}", Col.TEXT_MUTED if affordable else Col.MAGENTA)]
        if coupons:
            details.append((f"FREE PLAY COUPONS: {coupons}", Col.GREEN))
        self.dialogue = DialogueBox(
            machine.name, machine.description, [PLAY if affordable else PLAY_LOCKED, CANCEL],
            on_choice=lambda choice: self._on_choice(machine, choice, player),
            accent=machine.accent, glow=machine.neon,
            details=details, locked=() if affordable else (0,))
        self._own_modal(player)

    def _on_choice(self, machine, choice, player=None):
        player = self._actor(player)
        self.dialogue = None
        if choice not in (PLAY, PLAY_LOCKED):
            return
        if machine.can_use_coupon(player.profile):
            self._ask_coupon(machine, player)
        else:
            self._after_payment_choice(machine, player)

    def _ask_coupon(self, machine, player=None):
        """PLAY was confirmed and the player owns a coupon: YES uses one
        (no tokens), NO pays tokens as usual, ESC cancels. The box ignores
        keys for a moment so a mashed PLAY cannot answer it by accident."""
        player = self._actor(player)
        count = player.profile.inventory.get_quantity(FREE_PLAY_COUPON)
        self.dialogue = DialogueBox(
            "COUPON", "USE FREE PLAY COUPON?", ["YES", "NO"],
            on_choice=lambda choice: self._on_coupon_choice(machine, choice, player),
            accent=Col.GREEN, glow=machine.neon,
            details=[(f"YOU HAVE: {count}", Col.GREEN),
                     (f"NO PAYS {machine.cost_label}", Col.TEXT_MUTED)],
            input_delay=COUPON_INPUT_DELAY)
        self._own_modal(player)

    def _on_coupon_choice(self, machine, choice, player=None):
        player = self._actor(player)
        self.dialogue = None
        if choice == "YES":
            self._after_payment_choice(machine, player, use_coupon=True)
        elif choice == "NO":
            self._after_payment_choice(machine, player)

    def _after_payment_choice(self, machine, player, use_coupon=False):
        self._start_game(machine, use_coupon, player)

    def _open_target(self, target, player=None):
        """The E-flash finished: open whatever `player` used. If somebody
        else's window is already open, this press is dropped."""
        player = self._actor(player)
        if self.modal is not None:
            return
        self.acting_player = player
        try:
            if isinstance(target, ArcadeMachine):
                if hasattr(self.game, "audio"):
                    self.game.audio.play("machine")
                self.open_dialogue(target, player)
            else:
                target.interact(self)
        finally:
            self.acting_player = None

    def _pause_for_minigame(self):
        self.notice.clear()
        self.hub.ambience.pause()
        self.cats.pause()       # cats stay put; they settle down until we're back

    def open_chance_game(self, game_cls, player=None):
        """Walk into a Lucky Corner game. Nothing is charged here: the game
        itself charges (the player who walked in) when its round starts."""
        if self.active_play is not None or self.game.scenes.transitioning:
            return
        player = self._actor(player)
        self._pause_for_minigame()
        self.game.scenes.push(ChanceGameScene(self.game, game_cls,
                                              self.session.player_for_avatar(player)))

    def open_neon21(self, player=None):
        """Walk up to the NEON 21 table. Nothing is charged here: the wager is
        taken (from the player who walked up) when they press DEAL."""
        if self.active_play is not None or self.game.scenes.transitioning:
            return
        player = self._actor(player)
        self._pause_for_minigame()
        self.game.scenes.push(Neon21Scene(self.game, self.session.player_for_avatar(player)))

    def open_coin_pusher(self, player=None):
        """Walk up to NEON COIN PUSHER. Nothing is charged here: Tokens are only taken, one
        per coin, from the player who walked up when they press DROP."""
        if self.active_play is not None or self.game.scenes.transitioning:
            return
        player = self._actor(player)
        self._pause_for_minigame()
        self.game.scenes.push(CoinPusherScene(self.game, self.session.player_for_avatar(player)))

    def open_pinball(self, player=None):
        """Walk up to LUCKY CAT PINBALL. Nothing is charged here: the Token is only taken, from the
        player who walked up, when they press START inside the machine."""
        if self.active_play is not None or self.game.scenes.transitioning:
            return
        player = self._actor(player)
        self._pause_for_minigame()
        self.game.scenes.push(PinballScene(self.game, self.session.player_for_avatar(player)))

    def _start_game(self, machine, use_coupon=False, player=None):
        # A paid game is already starting/running, or a wipe is in progress
        # (SceneManager would drop the push): never charge in those states.
        if self.active_play is not None or self.game.scenes.transitioning:
            return
        player = self._actor(player)
        profile = player.profile
        if use_coupon and not machine.can_use_coupon(profile):
            self.notice.show("NO COUPON LEFT", [("NOTHING WAS CHARGED", Col.TEXT_MUTED)], Col.MAGENTA)
            return
        if not use_coupon and not machine.can_afford(profile):
            self.notice.show("NOT ENOUGH TOKENS", [
                (f"NEED: {machine.play_cost}", Col.YELLOW),
                (f"YOU HAVE: {profile.tokens}", Col.TEXT_MUTED)], Col.MAGENTA)
            return
        scene = create_minigame_scene(self.game, machine)   # built before charging
        local = self.session.player_for_avatar(player)
        if hasattr(scene, "attach_players"):
            scene.attach_players([local])
        else:
            scene.participants = [profile]
        session = machine.start_play(profile, use_coupon)
        if session is None:
            return
        self.play_sound("token")                # the token drops in
        self.interaction = MachineInteraction(machine, local)
        self.active_play = (session, scene)
        self._pause_for_minigame()
        self.game.scenes.push(scene)

    def open_vending(self, player=None):
        """Walk up to the NEON VEND-O-MATIC. Opening is free; each purchase charges the player who opened it."""
        if self.active_play is not None or self.game.scenes.transitioning:
            return
        player = self._actor(player)
        self.notice.clear()
        self.game.scenes.push(VendingScene(self.game, self.session.player_for_avatar(player)))

    def open_maintenance(self, player=None):
        """The BROKEN CAT-CADE's fake maintenance screen, owned by the player who pressed the use key."""
        if self.active_play is not None or self.game.scenes.transitioning or self.game.scenes.current is not self:
            return
        player = self._actor(player)
        self.notice.clear()
        self.game.scenes.push(MaintenanceScene(self.game, self.session.player_for_avatar(player), room=self))

    def use_novelty(self, item_id, player=None):
        """USE from the bag: one copy leaves that player's inventory and a harmless show plays on their avatar."""
        player = self._actor(player)
        result = use_item(player.profile, item_id)
        if result.success:
            self.play_sound(result.sound)
            self.novelty_fx.start(player, result)
        return result

    def open_task_panel(self, player=None):
        player = self._actor(player)
        self.panel = TaskPanel(player.profile, self._owner_tag(player), player.look.accent)
        self._own_modal(player)

    # ------------------------------------------------------------ doorways
    def _check_exits(self):
        """A door fires when the player stands in it."""
        if self.arrival_grace > 0 or self.leaving or self.active_play is not None:
            return
        for door in self.exits:
            if any(p.feet.colliderect(door.trigger) for p in self.players):
                self.leaving = self.hub.travel(self, door)
                if self.leaving:
                    for p in self.players:
                        p.held.clear()
                return

    # ------------------------------------------------------------ update
    def _is_busy(self, player):
        """Is this player held still by a window of theirs, the E-flash or a room change?"""
        return (self.leaving or player.activating is not None or self.modal_owner is player
                or self.hub.story.locked)

    def update(self, dt):
        self.time += dt
        self.arrival_grace = max(0.0, self.arrival_grace - dt)
        self.hub.story.update(dt, self)
        self.renderer.update(dt)
        for prop in self.props:
            prop.update(dt)
        for m in self.machines:
            m.update(dt)
        self.update_room(dt)

        for p in self.players:
            if p.activating:
                target, left = p.activating
                left -= dt
                p.activating = (target, left)
                if left <= 0:
                    p.activating = None
                    self._open_target(target, p)

        busy = (self.modal is not None or any(p.activating is not None for p in self.players)
                or self.leaving)
        if self.dialogue:
            self.dialogue.update(dt)
        self._update_modals(dt)
        self._day_timer += dt
        if self._day_timer >= 1.0:
            self._day_timer = 0.0
            self._check_new_day()
        self._watch_tasks()
        for hud in self.huds:
            hud.update(dt)
        self.notice.update(dt)
        self.title.update(dt)
        for p in self.players:
            direction = (0, 0) if self._is_busy(p) else p.direction
            p.update(dt, direction, self.solids + self.cats.blockers(p) + self.hub.story.blockers(self, p))
            if p.footstep:                      # a foot just came down
                p.footstep = False
                self.play_sound("footstep")
        self.cats.update(dt, self.players, busy)
        self.novelty_fx.update(dt)
        self._check_exits()

        # Machines win over cats when both are in reach.
        for p in self.players:
            held_still = self._is_busy(p)
            p.nearby = None if held_still or p.sitting else self._find_nearby(p)
            p.nearby_cat = None if held_still or p.nearby or p.sitting else self.cats.find_nearby(p)
        for m in self.interactables:
            m.highlight = any(p.nearby is m for p in self.players)
        for p in self.players:
            target = p.nearby or p.nearby_cat
            anchor = (int(p.x), int(p.y) - 22) if target else None
            label = p.nearby.prompt_label if p.nearby else p.nearby_cat and p.nearby_cat.personality.prompt
            p.prompt.update(dt, anchor, label)

    def _update_modals(self, dt):
        if self.popup:
            self.popup.update(dt)
            if self.popup.done:
                popup, self.popup = self.popup, None
                self.on_popup_closed(popup)
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

    def _find_nearby(self, player=None):
        player = player or self.player
        feet = player.feet
        close = [m for m in self._candidates() if m.zone.colliderect(feet)]
        return min(close, key=lambda m: abs(m.rect.centerx - player.x), default=None)

    def _candidates(self):
        """Everything the player could press E on right now: the fixed machines and stations, plus Miao Meow while she is here."""
        miao = getattr(self, "miao", None)
        return self.interactables + [miao] if miao is not None and miao.present else self.interactables

    SIGN_BAND = 12      # the marquee strip across the top of every cabinet / station sprite

    def prompt_avoid_rects(self):
        """Screen areas an interaction prompt must not cover: the marquee of every
        machine, station and idle cabinet in the room, plus any prop that names itself a sign
        (`sign_rect`). Shared by every room, so no cabinet needs its own offset."""
        rects = [pygame.Rect(t.rect.x, t.rect.y, t.rect.w, min(self.SIGN_BAND, t.rect.h))
                 for t in self.machines + self.props if getattr(t, "rect", None) is not None]   # incl. idle SOON cabinets
        rects += [pygame.Rect(p.sign_rect) for p in self.props if getattr(p, "sign_rect", None)]
        rects += self.hub.story.avoid_rects(self)
        return rects

    # ------------------------------------------------------------ draw
    def drawables(self):
        return self.props + self.machines

    def draw(self, surf):
        self.renderer.draw_background(surf)
        self.draw_under_sprites(surf)
        things = self.drawables() + self.players + self.cats.drawables()
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
        self.novelty_fx.draw(surf)
        if self.edit_mode:
            return

        story = self.hub.story
        story.draw_world(surf, self)
        if not story.hides_hud:
            avoid = self.prompt_avoid_rects()
            for p in self.players:
                if p.nearby is not None and p.prompt.alpha > 0:        # which machine is selected
                    selection_brackets(surf, p.nearby.rect, Col.YELLOW, self.time)
                mine = [p.nearby.rect] if p.nearby is not None else []   # keep the selected machine visible too
                used = p.prompt.draw(surf, self.time, avoid + mine, below_first=p.nearby is not None)
                if used is not None:
                    avoid.append(used.inflate(2, 2))
            self.instructions.draw(surf)
            for hud in self.huds:
                hud.draw(surf)
            story.draw_hud(surf, self)
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
        story.draw_front(surf, self)

    def draw_under_sprites(self, surf):
        """Hook: flat things drawn on the floor/wall, below every sprite."""


class RoomHub:
    """The three connected rooms and what they share: the players' bodies, the
    currency HUDs and the ambience. Rooms are built the first time they are
    visited and then kept, so each one is exactly as it was left."""

    def __init__(self, game, style):
        from ambience import AmbienceManager
        from hud import CurrencyHUD
        self.game = game
        self.style = style                  # shared by all three rooms
        self.session = game.session         # the LocalSession: the one player
        self.avatars = self.session.avatars
        self.player = self.avatars[0]
        self.hud = CurrencyHUD(self.session.primary.profile)      # the wallet readout
        self.huds = [self.hud]
        self.ambience = AmbienceManager()
        self.ambience.start()
        from story import StoryDirector         # (imported here: the story layer imports the room modules' helpers)
        self.story = StoryDirector(self)
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

    def start(self, room_id=START_ROOM, replace=False):
        """Put the players in a room (game start). Without a wipe, as the
        first scene; or `replace=True` to swap out the menu on top of the stack."""
        self._arrival = "spawn"
        if replace:
            self.game.scenes.replace(self.room(room_id))
        else:
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
        """The doorway the players are arriving through (once), or None."""
        arrival, self._arrival = self._arrival, None
        return arrival

    def close(self):
        self.story.close()
        for hud in self.huds:
            hud.close()


def room_registry():
    """room id -> room scene class. Imported here because the room modules
    import this one."""
    from arcade_floor import ArcadeFloorScene
    from home_room import HomeRoomScene
    from prize_plaza import PrizePlazaScene
    return {"home": HomeRoomScene, "arcade_floor": ArcadeFloorScene,
            "prize_plaza": PrizePlazaScene}
