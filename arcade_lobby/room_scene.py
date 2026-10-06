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

Two local players share the one screen and the one active room. Each player has
their own HubPlayer (body, held keys, nearby thing, prompt), profile, HUD and
bag; the room holds a single modal (dialogue / panel / bag / popup) at a time,
owned by the player who opened it, and only that player's keys drive it. A room
change needs everybody at the same exit.

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
from local_session import GameEvent, MachineInteraction
from machine import ArcadeMachine
from rewards import RewardService
from room import room_walls
from font import get_font
from scene_base import BaseScene
from scenes import create_minigame_scene, minigame_definition
from settings import (ARRIVAL_GRACE, CATS, Col, DEBUG_COUPON_KEY, DEBUG_NEXT_DAY_KEY,
                      DEBUG_RESET_TASKS_KEY, DEBUG_STICKER_KEY, DEBUG_TOKEN_KEY,
                      DEBUG_TOKENS, ENTRY_INSET, EXIT_DEPTH, INTERACT_FLASH,
                      PLAYER_START, ROOM_IDS, SIDE_DOOR_H, SIDE_DOOR_Y, START_ROOM,
                      TRANSITION_TIME, VIEW_W)
from stations import Station
from ui import (DialogueBox, InstructionBox, Notice, RoomTitle, draw_text, neon_panel)

PLAY, PLAY_LOCKED, CANCEL = "PLAY", "PLAY  [LOCKED]", "CANCEL"
ONE_PLAYER, TWO_PLAYERS, TWO_PLAYERS_LOCKED = "1 PLAYER", "2 PLAYERS", "2 PLAYERS  [P2 NEEDS TOKENS]"
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
# With two players they arrive side by side, not on the same pixel (one player: no offset).
ARRIVAL_SPREAD = {
    "left": ((0, -9), (0, 9)),
    "right": ((0, -9), (0, 9)),
    "spawn": ((-10, 0), (10, 0)),
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
        self.session = hub.session          # who is playing (1 or 2 local players)
        self.players = hub.avatars          # their bodies: shared by the whole hub
        self.huds = hub.huds
        self.hud = hub.hud                  # P1's wallet readout
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

        self.dialogue = None
        self.popup = None       # the daily login bonus (HOME)
        self.panel = None       # TaskPanel while the daily board is open (HOME)
        self.inventory_ui = None    # InventoryUI while the bag is open
        self._modal_owner = None    # the HubPlayer who opened the open modal
        self.acting_player = None   # the HubPlayer whose press is being carried out (for stations)
        self._day_timer = 0.0
        self._ready = {id(p): len(p.profile.claimable_tasks) for p in self.players}
        self.waiting = None     # (waiting players, missing players) at an exit
        self._labels = {}
        self.instructions = InstructionBox(self.build_hint_rows())
        self.notice = Notice()
        self.title = RoomTitle(self.theme.name, self.theme.title, self.theme.title_glow)
        self.active_play = None  # (PlaySession, minigame scene) while a paid game runs
        self.active_plays = []   # [(HubPlayer, PlaySession)]: one per participant of that game
        self.interaction = None  # the MachineInteraction last started (who initiated it)
        self.leaving = False     # a doorway was entered: no more input until the swap
        self.arrival_grace = 0.0
        self.time = 0.0

    # ------------------------------------------------------------ players
    @property
    def player(self):
        """The primary (P1) body - the only one in a one-player session."""
        return self.players[0]

    @property
    def profile(self):
        """The primary player's profile (HOME's owner)."""
        return self.game.profile

    @property
    def two_player(self):
        return len(self.players) > 1

    # P1's interaction state, under the names a one-player room always had.
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

    def build_hint_rows(self):
        """The controls box: the room's own rows for one player, a compact
        P1 / P2 key list for two."""
        if not self.two_player:
            return self.hint_rows
        rows = []
        for p in self.session:
            c = p.controls
            rows.append([(f"{p.label}:", p.avatar.look.accent),
                         (f"{c.move_hint} {c.interact_hint} {c.inventory_hint}", Col.TEXT)])
        rows.append([("USE KEY:", Col.TEXT), (self.action_hint, Col.YELLOW)])
        return rows

    def _owner_tag(self, player):
        """'P2 ALICE' for the header of that player's panels; None when playing alone."""
        local = self.session.player_for_avatar(player)
        return local.tag if local and self.two_player else None

    def _actor(self, player=None):
        """The player an action belongs to: the one named, else the one whose
        press is being carried out, else P1."""
        return player or self.acting_player or self.player

    @property
    def modal(self):
        return self.popup or self.panel or self.inventory_ui or self.dialogue

    @property
    def modal_owner(self):
        """Who the open modal belongs to (None if nothing is open)."""
        if self.modal is None:
            return None
        return self._modal_owner if self._modal_owner in self.players else self.player

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
        spread = ARRIVAL_SPREAD[entry] if self.two_player else None
        for i, p in enumerate(self.players):
            dx, dy = spread[i] if spread else (0, 0)
            p.x, p.y = float(pos[0] + dx), float(pos[1] + dy)
            p.facing = facing
            p.stop()
            p.show_tag()
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
        self.waiting = None
        self.notice.clear()
        for p in self.players:
            p.held.clear()
            p.activating = None
            p.nearby = p.nearby_cat = None
            p.stop()
        for thing in self.interactables:
            thing.highlight = False
            thing.flash_time = 0.0

    @staticmethod
    def _keys_down(controls=None):
        """Movement keys physically held right now, so walking carries on
        through a doorway instead of stopping dead."""
        from controls import SOLO_CONTROLS
        return (controls or SOLO_CONTROLS).held_now()

    def _end_play(self, ran):
        """Settle (or refund) the paid minigame that just closed. active_play
        is cleared first and a PlaySession ends only once, so this can never
        pay or refund twice for one token. Every participant is settled
        against their own session and their own result."""
        if self.active_play is None:
            return
        session, scene = self.active_play
        plays = self.active_plays or [(self.player, session)]
        self.active_play, self.active_plays = None, []
        if not ran or scene.failed:
            refunded = [(p, s) for p, s in plays if s.refund()]
            if refunded:
                _, first = refunded[0]
                unit = "TOKEN" if first.cost == 1 else "TOKENS"
                back = "COUPON RETURNED" if first.coupon else f"+{first.cost} {unit} REFUNDED"
                self.notice.show("GAME UNAVAILABLE", [(back, Col.YELLOW)], Col.MAGENTA)
            return
        results = scene.get_result()
        lines = []
        for index, (player, sess) in enumerate(plays):
            profile = player.profile
            pr = (results.for_profile(profile.profile_id) if profile.profile_id is not None
                  else next(iter(results.player_results[index:index + 1]), None))
            paid = sess.settle_result(pr) if pr is not None else sess.settle(None)
            if paid is not None:
                tickets = paid.reward.tickets
                lines.append((f"{player.label} +{tickets} TICKETS" if player.label
                              else f"+{tickets} TICKETS", Col.YELLOW))
        if lines:
            self.notice.show("GAME COMPLETE", lines, Col.GREEN)

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
                if self.two_player:
                    lines.insert(0, (self._owner_tag(p), p.look.accent))
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
                owner = self.session.player_for_avatar(self.modal_owner)
                if self.session.allows(owner, event.key):
                    modal.handle_event(event)
                else:
                    self._key_during_modal(event.key)
            else:
                modal.handle_event(event)
            return
        if event.type != pygame.KEYDOWN or self.leaving:
            return
        if self.game.debug and self._debug_key(event.key):
            return
        local = self.session.player_for_key(event.key)
        if local is None:
            return
        player, key, controls = local.avatar, event.key, local.controls
        if player.activating:
            return
        if key in controls.inventory:
            self.inventory_ui = InventoryUI(local.profile.inventory, self._owner_tag(player),
                                            player.look.accent)
            self._own_modal(player)
            player.held.clear()
        elif key in controls.move and key not in player.held:
            player.held.append(key)
        elif key in controls.interact and player.nearby:
            if isinstance(player.nearby, ArcadeMachine):
                self._emit("machine_visited", player, key=player.nearby.id)
            player.nearby.activate()
            player.activating = (player.nearby, INTERACT_FLASH)
        elif key in controls.interact and player.nearby_cat:
            if self.cats.interact(player.nearby_cat, player):
                self._emit("cat_petted", player)

    def _key_during_modal(self, key):
        """A key of the player who does NOT own the open modal: they can keep
        walking, but cannot open anything else until it closes."""
        local = self.session.player_for_key(key)
        if local is None or self.leaving:
            return
        player = local.avatar
        if key in local.controls.move:
            if key not in player.held:
                player.held.append(key)
        elif not self.notice.visible:
            owner = self.session.player_for_avatar(self.modal_owner)
            self.notice.show(f"{local.label} WAIT", [(f"{owner.label} IS BUSY", Col.TEXT_MUTED)],
                             Col.MAGENTA)

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
        if self.two_player:
            details.insert(0, (local.tag, player.look.accent))
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

    def _other_players(self, player):
        return [p for p in self.players if p is not player]

    def _after_payment_choice(self, machine, player, use_coupon=False):
        """How the starter pays is settled. With two people here and a game
        that takes two, ask how many play; otherwise the starter plays."""
        if self.two_player and minigame_definition(machine.game_id).supports(2):
            self._ask_players(machine, player, use_coupon)
        else:
            self._start_game(machine, use_coupon, player)

    def _ask_players(self, machine, player, use_coupon):
        """PLAYERS: 1 PLAYER / 2 PLAYERS. The second player pays their own
        tokens, so that option is locked while they cannot."""
        other = self._other_players(player)[0]
        can_join = machine.can_afford(other.profile)
        self.dialogue = DialogueBox(
            "PLAYERS", "HOW MANY ARE PLAYING?",
            [ONE_PLAYER, TWO_PLAYERS if can_join else TWO_PLAYERS_LOCKED],
            on_choice=lambda choice: self._on_players_choice(machine, choice, player, use_coupon),
            accent=machine.accent, glow=machine.neon,
            details=[(f"{other.label} PAYS {machine.cost_label}", Col.TEXT_MUTED)],
            locked=() if can_join else (1,))
        self._own_modal(player)

    def _on_players_choice(self, machine, choice, player, use_coupon):
        self.dialogue = None
        if choice == ONE_PLAYER:
            self._start_game(machine, use_coupon, player)
        elif choice == TWO_PLAYERS:
            self._start_game(machine, use_coupon, player, participants=self.players)
        elif choice == TWO_PLAYERS_LOCKED:
            other = self._other_players(player)[0]
            self.notice.show("NOT ENOUGH TOKENS", [(f"{other.label} NEEDS {machine.play_cost}", Col.YELLOW),
                                                   ("NOTHING WAS CHARGED", Col.TEXT_MUTED)], Col.MAGENTA)

    def _open_target(self, target, player=None):
        """The E-flash finished: open whatever `player` used. If somebody
        else's window is already open, this press is dropped."""
        player = self._actor(player)
        if self.modal is not None:
            return
        self.acting_player = player
        try:
            if isinstance(target, ArcadeMachine):
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

    def _start_game(self, machine, use_coupon=False, player=None, participants=None):
        # A paid game is already starting/running, or a wipe is in progress
        # (SceneManager would drop the push): never charge in those states.
        if self.active_play is not None or self.game.scenes.transitioning:
            return
        player = self._actor(player)
        profile = player.profile
        group = [player] + [p for p in (participants or ()) if p is not player]
        if use_coupon and not machine.can_use_coupon(profile):
            self.notice.show("NO COUPON LEFT", [("NOTHING WAS CHARGED", Col.TEXT_MUTED)], Col.MAGENTA)
            return
        if not use_coupon and not machine.can_afford(profile):
            self.notice.show("NOT ENOUGH TOKENS", [
                (f"NEED: {machine.play_cost}", Col.YELLOW),
                (f"YOU HAVE: {profile.tokens}", Col.TEXT_MUTED)], Col.MAGENTA)
            return
        for other in group[1:]:                 # everybody must be able to pay before anybody does
            if not machine.can_afford(other.profile):
                self.notice.show("NOT ENOUGH TOKENS", [
                    (f"{other.label} NEEDS {machine.play_cost}", Col.YELLOW),
                    ("NOTHING WAS CHARGED", Col.TEXT_MUTED)], Col.MAGENTA)
                return
        scene = create_minigame_scene(self.game, machine)   # built before charging
        scene.participants = [p.profile for p in group]
        session = machine.start_play(profile, use_coupon)
        if session is None:
            return
        plays = [(player, session)]
        for other in group[1:]:
            plays.append((other, machine.start_play(other.profile)))
        self.interaction = MachineInteraction(machine, self.session.player_for_avatar(player))
        self.active_play = (session, scene)
        self.active_plays = plays
        self._pause_for_minigame()
        self.game.scenes.push(scene)

    def open_task_panel(self, player=None):
        player = self._actor(player)
        self.panel = TaskPanel(player.profile, self._owner_tag(player), player.look.accent)
        self._own_modal(player)

    # ------------------------------------------------------------ doorways
    def _check_exits(self):
        """A door fires when somebody stands in it and everybody is at it; with
        two players the first one waits ('WAITING FOR PLAYER 2')."""
        self.waiting = None
        if self.arrival_grace > 0 or self.leaving or self.active_play is not None:
            return
        for door in self.exits:
            at_door = [p for p in self.players if p.feet.colliderect(door.trigger)]
            if not at_door:
                continue
            near = [p for p in self.players if p.feet.colliderect(door.zone)]
            if len(near) == len(self.players):
                self.leaving = self.hub.travel(self, door)
                if self.leaving:
                    for p in self.players:
                        p.held.clear()
                return
            self.waiting = (at_door, [p for p in self.players if p not in near])
            return

    @property
    def waiting_text(self):
        """'WAITING FOR PLAYER 2' while somebody stands in a doorway alone."""
        if not self.waiting:
            return None
        return "WAITING FOR " + " AND ".join(f"PLAYER {p.number}" for p in self.waiting[1])

    # ------------------------------------------------------------ update
    def _direction(self):
        return self.player.direction

    def _is_busy(self, player):
        """Is this player held still by a window of theirs, the E-flash or a room change?"""
        return self.leaving or player.activating is not None or self.modal_owner is player

    def update(self, dt):
        self.time += dt
        self.arrival_grace = max(0.0, self.arrival_grace - dt)
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
            p.update(dt, direction, self.solids + self.cats.blockers(p))
        self.cats.update(dt, self.players, busy)
        self._check_exits()

        # Machines win over cats when both are in reach.
        for p in self.players:
            held_still = self._is_busy(p)
            p.nearby = None if held_still else self._find_nearby(p)
            p.nearby_cat = None if held_still or p.nearby else self.cats.find_nearby(p)
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
        close = [m for m in self.interactables if m.zone.colliderect(feet)]
        return min(close, key=lambda m: abs(m.rect.centerx - player.x), default=None)

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

        for p in self.players:
            p.prompt.draw(surf, self.time)
            p.draw_tag(surf)
        self._draw_waiting(surf)
        self.instructions.draw(surf)
        for hud in self.huds:
            hud.draw(surf)
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

    def _draw_waiting(self, surf):
        text = self.waiting_text
        if not text:
            return
        label = self._labels.get(text)
        if label is None:
            w = get_font().size(text)[0] + 12
            label = pygame.Surface((w, 15), pygame.SRCALPHA)
            label.blit(neon_panel(w, 15, Col.YELLOW, None, 235), (0, 0))
            draw_text(label, text, (6, 4), Col.YELLOW)
            self._labels[text] = label
        waiting = self.waiting[0][0]
        rect = label.get_rect(midbottom=(int(waiting.x), int(waiting.y) - 26))
        rect.clamp_ip(pygame.Rect(2, 2, VIEW_W - 4, 400))
        if int(self.time * 3) % 3:          # a slow blink
            surf.blit(label, rect)

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
        self.session = game.session         # one or two LocalPlayers
        self.avatars = self.session.avatars
        self.player = self.avatars[0]       # P1 (the only player in a one-player session)
        if self.session.player_count == 1:
            self.huds = [CurrencyHUD(self.session.primary.profile)]
        else:                               # one wallet readout per player, labelled
            self.huds = [CurrencyHUD(p.profile, p.tag, p.avatar.look.accent, slot=i)
                         for i, p in enumerate(self.session)]
        self.hud = self.huds[0]
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
