"""TRIAL 01 - THE GOLDEN AGE: the scene (a walkable room, its lighting, the interactions and the way out).

Entered from the vending machine's Legacy Terminal (legacy_terminal.TRIAL_SCENES["trial_01"]), so it can only be reached
through the real secret interface. It borrows the player's body (HubPlayer) from the hub and puts it back exactly where it
stood when the scene closes, so the player's profile, tickets, tokens and quest progress are never touched on the way in
or out. The rules live in golden_age.py, the pictures in golden_age_art.py and the pop-up screens in golden_age_ui.py; the
dialogue box is the existing story_dialogue.StoryDialogue.

The only thing the story ever hears is the end: GameEvent("secret_trial_done", key="trial_01"), sent once, when the
computer's archive has been restored. Leaving halfway sends nothing; the run (what has been done in the room) stays with
the hub while the game is open, so coming back carries on, and is thrown away when the trial is completed, so a replay
starts in the dark again. The Memory Fragment is granted by the story on the first completion only.
"""
import math
import random

import pygame

import golden_age as G
import golden_age_art as A
import golden_age_content as C
import golden_age_ui as UI
from gfx import soft_shadow
from local_session import GameEvent
from miao_meow import WALK_LEGS, WALK_STEP, facing_frame, miao_frame, point_clear, segment_clear
from scene_base import BaseScene
from settings import Col, PLAYER_SPEED, VIEW_H, VIEW_W
from story_dialogue import Line, Speaker, SPEAKERS, StoryDialogue, register_speaker
from ui import Notice, draw_text

if "SYSTEM" not in SPEAKERS:
    register_speaker("SYSTEM", Speaker("SYSTEM", Col.GREEN, None, blip="vend_select"))

START = (64, 214)                       # just inside the door, looking into the room
DOOR_ZONE = pygame.Rect(20, 196, 34, 30)
LOW_ON_SCREEN = 212                     # speakers lower than this: the dialogue box goes to the top
AMBIENT_DARK, AMBIENT_LIT = (104, 112, 166), (244, 222, 186)
POWER_FADE = 2.6                        # seconds the lamps take to come up
MUSIC_DARK, MUSIC_LIT = 0.35, 0.95

# (x, y) places Miao Meow likes: open floor, clear of every prompt area (a test checks that)
MIAO_SPOTS = ((70, 170), (120, 160), (232, 158), (126, 232), (216, 248), (270, 176), (320, 168), (110, 262), (290, 262), (232, 262))


class Spot:
    """Something the player can walk up to and press E on."""

    def __init__(self, key, label, rect, zone, act, anchor=None):
        self.key = key
        self.label = label                      # str, or callable() -> str
        self.rect = pygame.Rect(rect)           # where it is drawn (the prompt keeps this visible)
        self.zone = pygame.Rect(zone)           # stand here to use it
        self.act = act
        self.anchor = anchor or self.zone.center              # (the nearest prompt area centre wins when two overlap)

    @property
    def prompt(self):
        return self.label() if callable(self.label) else self.label


class Companion:
    """Miao Meow in the room: she keeps near the player, always on open floor and never in front of something you can use.
    She is also a Spot ("TALK": a hint, only when asked)."""
    SPEED = 40.0

    def __init__(self, pos=(84, 226)):
        self.x, self.y = float(pos[0]), float(pos[1])
        self.side = "right"
        self.target = None
        self.walking = False
        self.time = 0.0
        self.think = 0.0

    @property
    def zone(self):
        return pygame.Rect(int(self.x) - 14, int(self.y) - 16, 28, 24)

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 10, int(self.y) - 16, 20, 17)

    def update(self, dt, player, solids, spots):
        self.time += dt
        self.think -= dt
        px, py = player
        dist = math.hypot(px - self.x, py - self.y)
        if self.think <= 0 and (self.target is None or dist < 20 or dist > 120):
            self.think = 0.8
            options = [s for s in spots if 26 <= math.hypot(s[0] - px, s[1] - py) <= 120 and segment_clear((self.x, self.y), s, solids)]
            if not options:
                options = [s for s in spots if segment_clear((self.x, self.y), s, solids)]
            if options:
                best = min(options, key=lambda s: math.hypot(s[0] - px, s[1] - py))
                if self.target != best and (self.target is None or math.hypot(self.x - px, self.y - py) < 20
                                            or math.hypot(self.target[0] - px, self.target[1] - py) > 130):
                    self.target = best
        self.walking = False
        if self.target is not None:
            dx, dy = self.target[0] - self.x, self.target[1] - self.y
            d = math.hypot(dx, dy)
            if d > 1.5:
                step = min(d, self.SPEED * dt)
                self.x += dx / d * step
                self.y += dy / d * step
                self.walking = True
                if abs(dx) > 1:
                    self.side = "left" if dx < 0 else "right"
            else:
                self.target = None
        if not self.walking:
            self.side = "left" if px < self.x else "right"

    def image(self, level):
        if self.walking:
            i = int(self.time / WALK_STEP) % 4
            frame = miao_frame("stand", "open", tail=(0, 1, 2, 1)[i], legs=WALK_LEGS[i], level=level)
        else:
            eyes = "sleepy" if int(self.time / 3) % 5 == 4 else "open"
            frame = miao_frame("sit", eyes, tail=int(self.time * 1.2) % 3 == 1, level=level)
        return facing_frame(frame, self.side)


class GoldenAgeScene(BaseScene):
    music_id = "golden_age"
    own_audio = False

    def __init__(self, game, owner):
        super().__init__(game)
        self.owner = owner
        self.hub = game.hub
        self.manager = self.hub.story.manager
        self.avatar = owner.avatar
        self.controls = owner.controls
        run = getattr(self.hub, "trial01_run", None)
        if run is None or run.computer_done:
            run = self.hub.trial01_run = G.TrialRun()
        self.run = run
        if self.manager.state.get("flags", {}).get(G.BREAKOUT_FLAG):
            run.breakout_cleared = True                          # HAPPY BREAKOUT was cleared once: it stays cleared
        self.time = 0.0
        self.panel = None
        self.dialogue = None
        self.notice = Notice(center=(VIEW_W // 2, 62))
        self.bubble = UI.HintBubble()
        self.timers = []                        # [seconds left, callable]
        self.intro_dialogue = None
        self.leaving = False
        self.completed_here = False
        self._saved = None
        self._ambience = None
        self.power_t = None                     # seconds since the power came on in front of the player (None: not animating)
        self.light = 1.0 if run.power else 0.0
        self.flicker = 0.0
        self.shown_state = "off"
        rng = random.Random(1990)
        self.dust = [[rng.uniform(24, 376), rng.uniform(80, 276), rng.uniform(-3, 3), rng.uniform(-2, 1), rng.uniform(0, 6.28),
                      rng.choice((70, 110, 150))] for _ in range(30)]
        self.build_room()
        self.companion = Companion()

    # ------------------------------------------------------------ the room
    def build_room(self):
        walls = [pygame.Rect(0, 0, VIEW_W, A.WALL_SOLID_BOTTOM), pygame.Rect(0, 0, A.SIDE, VIEW_H),
                 pygame.Rect(VIEW_W - A.SIDE, 0, A.SIDE, VIEW_H), pygame.Rect(0, A.FLOOR_BOTTOM, VIEW_W, VIEW_H - A.FLOOR_BOTTOM)]
        self.walls = walls
        self.spots = {sp.key: sp for sp in self.spot_defs()}
        furniture = [pygame.Rect(26, 86, 64, 30), pygame.Rect(92, 96, 28, 12), pygame.Rect(226, 86, 124, 26),
                     pygame.Rect(350, 86, 30, 22), pygame.Rect(148, 180, 56, 12), pygame.Rect(352, 204, 16, 8),
                     pygame.Rect(28, 252, 30, 14), pygame.Rect(300, 220, 28, 10), pygame.Rect(352, 252, 16, 8)]
        self.furniture = furniture
        self.solids = walls + furniture
        self.static = self._static_layer()

    def spot_defs(self):
        """Everything the player can inspect. Every ordinary thing and every clue says the same word on its prompt (INSPECT):
        only looking tells which is which. rect: where it is drawn; zone: the floor to stand on."""
        S = Spot
        ins = "INSPECT"
        life = self.use_life
        return [
            S("power_box", ins, (196, 50, 18, 24), (194, 88, 24, 22), self.use_power_box),
            S("window", ins, (172, 10, 54, 40), (168, 88, 26, 22), lambda: life("window")),
            S("bookshelf", ins, (122, 20, 46, 66), (122, 88, 44, 22), self.use_bookshelf),
            S("bedside_lamp", ins, (93, 70, 14, 20), (92, 112, 13, 24), self.use_bedside_lamp),
            S("alarm_clock", ins, (108, 77, 13, 13), (105, 112, 17, 24), lambda: life("alarm_clock")),
            S("plushie", ins, (44, 62, 19, 19), (46, 118, 44, 24), lambda: life("plushie")),
            S("photo_frame", ins, (4, 116, 12, 16), (20, 112, 24, 22), lambda: life("photo_frame")),
            S("poster", ins, (4, 140, 12, 32), (20, 136, 26, 34), lambda: life("poster")),
            S("door", "LEAVE ROOM", (0, 200, 20, 54), DOOR_ZONE, self.ask_leave),
            S("cartridges", ins, (28, 244, 32, 26), (50, 226, 40, 24), lambda: life("cartridges")),
            S("noodle_cup", ins, (152, 159, 14, 15), (146, 192, 22, 22), lambda: life("noodle_cup")),
            S("cookie_jar", ins, (172, 157, 14, 17), (168, 192, 18, 22), lambda: life("cookie_jar")),
            S("coffee_mug", ins, (190, 163, 12, 11), (186, 192, 22, 22), lambda: life("coffee_mug")),
            S("homework", ins, (216, 196, 34, 20), (208, 186, 42, 36), lambda: life("homework")),
            S("textbook", ins, (258, 230, 22, 14), (248, 216, 44, 28), lambda: life("textbook")),
            S("plant", ins, (352, 186, 16, 26), (334, 210, 38, 12), lambda: life("plant")),
            S("trash_bin", ins, (352, 238, 16, 21), (332, 226, 40, 26), lambda: life("trash_bin")),
            S("phone", ins, (232, 70, 24, 15), (224, 112, 26, 24), self.use_phone),
            S("desk", ins, (226, 72, 124, 40), (250, 112, 18, 24), lambda: life("desk")),
            S("computer", ins, (270, 48, 36, 34), (268, 112, 32, 24), self.use_computer),
            S("desk_lamp", ins, (314, 58, 14, 20), (300, 112, 14, 24), self.use_desk_lamp),
            S("drawer", ins, (302, 92, 46, 20), (314, 112, 34, 24), self.use_drawer),
            S("cabinet", ins, (350, 58, 30, 50), (350, 112, 30, 26), self.use_cabinet),
        ]

    def _static_layer(self):
        """The room as it never changes: shell, rug, wall dressing, soft shadows and the furniture that has no states."""
        s = A.room_shell().copy()
        s.blit(A.rug(), (138, 148))
        for sprite, pos in ((A.window(), (172, 10)), (A.corkboard(), (296, 14)), (A.poster("quest"), (36, 14)),
                            (A.poster("arcade"), (64, 18)), (A.poster("pilot"), (246, 14)), (A.wall_clock(), (140, 6)),
                            (A.trophy_shelf(), (340, 30)), (A.door(), (0, 200)), (A.side_frame(), (4, 116)),
                            (A.side_poster(), (4, 140)), (A.bookshelf(), (122, 20)), (A.power_box(), (196, 50)),
                            (A.homework(), (216, 196)), (A.textbook(), (258, 230))):
            A.put(s, sprite, *pos)
        A.draw_string_lights(s)
        for rect in self.furniture:                       # a soft shadow on the floor under everything solid
            sh = soft_shadow(rect.w + 10, 9, 90)
            s.blit(sh, (rect.x - 5, rect.bottom - 6))
        return s

    # ------------------------------------------------------------ scene lifecycle
    def on_enter(self):
        av = self.avatar
        self._saved = (av.x, av.y, av.facing)
        self._ambience = dict(getattr(self.hub.ambience, "mix", {}))
        self.hub.ambience.set_mix({})
        av.x, av.y = float(START[0]), float(START[1])
        av.facing = "right"
        av.held = list(self.controls.held_now())
        av.stop()
        if not self.run.intro_played and not self.manager.state.get("flags", {}).get(G.INTRO_FLAG):
            self.later(0.7, self.play_intro)
        else:
            self.run.intro_played = True
            self.later(0.5, self.announce_start)

    def on_exit(self):
        av = self.avatar
        if self._saved:
            av.x, av.y, av.facing = self._saved
        av.held.clear()
        av.stop()
        av.nearby = av.nearby_cat = None
        av.activating = None
        av.prompt.alpha = 0.0
        self.hub.ambience.set_mix(self._ambience or {})

    def on_resume(self):
        self.avatar.held.clear()

    # ------------------------------------------------------------ helpers
    def play(self, name, volume=1.0):
        audio = getattr(self.game, "audio", None)
        if audio is not None:
            audio.play(name, volume) if volume != 1.0 else audio.play(name)

    def later(self, seconds, fn):
        self.timers.append([seconds, fn])

    @property
    def captures_text(self):
        return bool(self.panel is not None and self.panel.captures_text)

    @property
    def music_duck(self):
        return MUSIC_DARK + (MUSIC_LIT - MUSIC_DARK) * self.light

    @property
    def modal(self):
        return self.dialogue or self.panel

    @property
    def locked(self):
        waking = self.power_t is not None and self.power_t < 1.4        # the lights are coming on: nothing else starts yet
        return self.dialogue is not None or self.panel is not None or self.leaving or waking

    def say(self, lines, on_done=None):
        """Open the story's dialogue box. `lines`: golden_age tuples (speaker, text, mood)."""
        low = max(self.avatar.y, self.companion.y) > LOW_ON_SCREEN
        self.dialogue = StoryDialogue([Line(*row) for row in lines], {"players": [self.avatar]}, on_done=on_done,
                                      play_sound=self.play, top=low)
        self.stop_walking()
        self.bubble.clear()
        self.notice.clear()
        return self.dialogue

    def stop_walking(self):
        self.avatar.held.clear()
        self.avatar.stop()

    def open_panel(self, panel):
        self.panel = panel
        self.stop_walking()
        self.bubble.clear()
        self.notice.clear()
        return panel

    def tell(self, title, lines=(), color=Col.CYAN):
        """A short, non-blocking card at the top of the room."""
        self.notice.show(title, [(t, Col.TEXT) for t in lines], color)

    def announce_start(self):
        """Coming back into the room (the first visit says the same things in its opening): the title, and nothing else."""
        self.tell("TRIAL 01 - THE GOLDEN AGE", ["Explore the room."], Col.YELLOW)

    # ------------------------------------------------------------ the opening
    def play_intro(self):
        self.run.intro_played = True
        done = self._intro_done

        def finish():
            self.manager.handle(G.INTRO_FLAG)
            done()
        self.intro_dialogue = self.say(G.OPENING, on_done=finish)

    def _intro_done(self):
        self.run.intro_played = True

    # ------------------------------------------------------------ interactions
    def use_power_box(self):
        if self.run.power:
            self.tell("POWER BOX", [C.POWER_BOX_DONE], Col.GREEN)
            return
        self.open_panel(UI.CircuitPanel(self.run.circuit, self.play))

    def use_phone(self):
        if not self.run.power:
            self.tell("TELEPHONE", [C.PHONE_DEAD], Col.CYAN)
            self.play("cancel")
            return
        self.open_panel(UI.PhonePanel(on_start=self._phone_started, play=self.play, has_chart=lambda: "chart" in self.run.clues))

    def _phone_started(self):
        self.run.play_phone()

    def use_drawer(self):
        first = not self.run.drawer_opened
        if first:
            self.play("drawer_open")
        self.run.open_drawer()
        pages = UI.paper_pages("paper") + UI.paper_pages("chart")
        self.open_panel(UI.PagedPanel(pages, self.play, finish_label="CLOSE DRAWER"))
        self.panel_then = (lambda: self.tell("CLUES ADDED", ["SEE NOTES [TAB]"], Col.CYAN)) if first else None

    def use_cabinet(self):
        if not self.run.power:
            self.tell("FILE CABINET", [C.CABINET_DEAD], Col.CYAN)
            self.play("cancel")
            return
        if self.run.cabinet_open:
            self.open_panel(UI.PagedPanel(UI.paper_pages("note"), self.play, finish_label="PUT IT BACK"))
            return
        self.open_panel(UI.KeypadPanel(self.run.try_cabinet, self.play))

    def use_bookshelf(self):
        """The shelf opens a browser of books. Nothing is handed over by the shelf: the books are read one by one."""
        self.open_panel(UI.BookshelfPanel(self.run.shelf()))

    def use_life(self, key):
        """An ordinary thing in the room: a few words (a different line each visit), sometimes something to read. It never
        changes any progress."""
        info = C.LIFE[key]
        reader = info.get("reader")
        if reader and key in self.run.inspected:                     # read again: straight to the pages
            self.run.inspect(key)
            self.open_reader(reader)
            return
        if key == "plushie":
            self.run.see_plushie()
        lines = self.run.inspect(key)
        self.say(lines, on_done=(lambda: self.open_reader(reader)) if reader else None)

    def open_reader(self, tag):
        self.open_panel(UI.PagedPanel(UI.paper_pages(tag), self.play, finish_label="CLOSE", tag=tag))

    def use_bedside_lamp(self):
        self.say(C.BEDSIDE_ON if self.run.power else C.BEDSIDE_OFF)

    def use_desk_lamp(self):
        self.say(C.LAMP_ON if self.run.power else C.LAMP_OFF)

    def use_computer(self):
        state = self.run.computer_state()
        if state == "dark":
            self.tell("COMPUTER", [C.COMPUTER_DEAD], Col.CYAN)
            self.play("cancel")
        elif state == "standby":
            self.tell("COMPUTER", [C.COMPUTER_STANDBY], Col.CYAN)
        elif state == "done":
            self.say((("SYSTEM", "PLAYER_000 / SYSTEM ADMINISTRATOR ACCESS", "normal"),))
        else:
            self.open_panel(UI.ComputerPanel(self.play, cleared=self.run.breakout_cleared, on_clear=self._breakout_cleared))

    def _breakout_cleared(self):
        """HAPPY BREAKOUT.EXE was cleared: the locked files open, now and in any later visit."""
        self.run.clear_breakout()
        self.manager.handle(G.BREAKOUT_FLAG)

    def ask_leave(self):
        self.open_panel(UI.ConfirmPanel("LEAVE THE ROOM?", ["YOU CAN COME BACK ANY TIME.", "WHAT YOU DID HERE IS KEPT WHILE THE GAME IS OPEN."],
                                        "LEAVE", "STAY"))

    def talk_to_miao(self):
        """Talking to Miao is the only way to get a hint, and the only one: she never offers."""
        self.give_hint()

    def give_hint(self):
        """Miao Meow's next hint for where things stand (vague first, then the area, then a clearer direction), in a little
        bubble. Never a window, never the password."""
        self.bubble.show(self.run.hint())

    def leave(self):
        if self.leaving:
            return
        self.leaving = True
        self.stop_walking()
        self.game.scenes.pop()

    # ------------------------------------------------------------ panels reporting back
    panel_then = None

    def _panel_done(self):
        panel, self.panel = self.panel, None
        result = panel.result
        after, self.panel_then = self.panel_then, None
        if isinstance(panel, UI.CircuitPanel):
            if result == "solved":
                self.power_on()
        elif isinstance(panel, UI.KeypadPanel):
            if result == "open":
                self.play("drawer_open")
                self.open_panel(UI.PagedPanel(UI.paper_pages("note"), self.play, finish_label="KEEP THE NOTE"))
                self.panel_then = lambda: self.tell("CLUE ADDED", ["THE OLD NOTE"], Col.CYAN)
        elif isinstance(panel, UI.PhonePanel):
            if result == "note":
                self.open_panel(UI.PagedPanel(UI.paper_pages("chart"), self.play, finish_label="BACK TO THE PHONE"))
                self.panel_then = self.use_phone
        elif isinstance(panel, UI.BookshelfPanel):
            if isinstance(result, tuple) and result[0] == "book":
                self._take_book(result[1])
        elif isinstance(panel, UI.PagedPanel):
            if result == "finished" and panel.tag == C.NOTEBOOK_KEY:
                self._journal_read()
        elif isinstance(panel, UI.ComputerPanel):
            if result == "done":
                self._computer_done()
        elif isinstance(panel, UI.NotesPanel):
            if isinstance(result, tuple) and result[0] == "clue":
                self._read_clue(result[1])
        elif isinstance(panel, UI.ConfirmPanel):
            if result == "yes":
                self.leave()
        elif isinstance(panel, UI.CompletePanel):
            if result == "return":
                self.leave()
        if after is not None and self.panel is None and self.dialogue is None:
            after()

    def _take_book(self, key):
        self.run.open_book(key)
        tag = C.NOTEBOOK_KEY if key == C.NOTEBOOK_KEY else key
        pages = UI.paper_pages("journal" if key == C.NOTEBOOK_KEY else key)
        self.open_panel(UI.PagedPanel(pages, self.play, finish_label="CLOSE BOOK", tag=tag))
        self.panel_then = self.use_bookshelf                       # back to the shelf (unless the notebook's ending takes over)

    def _read_clue(self, key):
        pages = UI.paper_pages(key)
        self.open_panel(UI.PagedPanel(pages, self.play, finish_label="BACK TO NOTES", tag=C.NOTEBOOK_KEY if key == "journal" else key))
        self.panel_then = self.open_notes

    def open_notes(self):
        self.open_panel(UI.NotesPanel(self.run))

    def power_on(self):
        """The fuse board is solved: the whole room wakes up. The state changes now; the lights follow the clock."""
        if not self.run.restore_power():
            return
        self.power_t = 0.0
        self.flicker = 0.0
        self.play("power_on")
        self.later(0.5, lambda: self.play("phone_blip"))
        self.later(1.0, lambda: self.say(G.POWER_RESTORED))

    def _journal_read(self):
        if not self.run.finish_journal():
            return
        self.say(G.JOURNAL_REACTION, on_done=self._disk_found)

    def _disk_found(self):
        self.play("equip")
        self.say(G.DISK_FOUND, on_done=lambda: self.tell("ITEM FOUND", ["OLD BOOT DISK"], Col.YELLOW))

    def _computer_done(self):
        if not self.run.finish_computer():
            return
        self.say(G.COMPUTER_AFTER, on_done=self.complete)

    def complete(self):
        """The one place the trial is recorded. The story keeps TRIAL_01 = COMPLETE and Memory Fragment 01 on the FIRST
        completion only; a replay shows the card again but grants nothing."""
        first = not self.manager.trial_done(G.TRIAL_ID)
        if first:
            self.game.session.dispatch(GameEvent("secret_trial_done", self.owner.player_id, key=G.TRIAL_ID))
        self.completed_here = True
        self.hub.trial01_run = None             # the next visit starts from the dark room
        self.play("trial_complete")
        self.open_panel(UI.CompletePanel(first))

    # ------------------------------------------------------------ input
    def handle_event(self, event):
        av = self.avatar
        if event.type == pygame.WINDOWFOCUSLOST:
            av.held.clear()
            return
        if event.type == pygame.KEYUP:
            if event.key in av.held:
                av.held.remove(event.key)
            if self.panel is not None:
                self.panel.handle_event(event)
            return
        if event.type != pygame.KEYDOWN:
            return
        if self.dialogue is not None:
            d = self.dialogue
            if event.key == pygame.K_ESCAPE and d is self.intro_dialogue:          # ESC skips the opening
                self._skip_intro()
                return
            d.handle_event(event)
            if d.closed and self.dialogue is d:
                self.dialogue = None
            return
        if self.panel is not None:
            self.panel.handle_event(event)
            if self.panel.closed:
                self._panel_done()
            return
        if self.leaving:
            return
        key = event.key
        if key == pygame.K_ESCAPE:
            self.ask_leave()
        elif key in (pygame.K_TAB, pygame.K_n):
            self.open_notes()
        elif key in self.controls.move:
            if key not in av.held:
                av.held.append(key)
        elif self.controls.action_for(key) == "interact":
            spot = self.nearby
            if spot is not None:
                spot.act()

    def _skip_intro(self):
        self.dialogue = self.intro_dialogue = None
        self.manager.handle(G.INTRO_FLAG)
        self._intro_done()

    # ------------------------------------------------------------ who is in reach
    @property
    def companion_spot(self):
        sp = getattr(self, "_miao_spot", None)
        if sp is None:
            sp = self._miao_spot = Spot("miao", "TALK", self.companion.rect, self.companion.zone, self.talk_to_miao)
        sp.rect, sp.zone, sp.anchor = self.companion.rect, self.companion.zone, self.companion.rect.center
        return sp

    @property
    def nearby(self):
        return self.spot_at(self.avatar.x, self.avatar.y)

    def spot_at(self, x, y):
        """The thing E would use for feet standing at (x, y): the nearest of the places whose prompt area the feet touch (Miao only
        when nothing else is in reach)."""
        feet = pygame.Rect(int(x) - 5, int(y) - 5, 10, 5)
        found = [sp for sp in self.spots.values() if sp.zone.colliderect(feet)]
        if found:                                           # something to use beats a chat: Miao never takes E away from a puzzle
            return min(found, key=lambda sp: math.hypot(sp.anchor[0] - x, sp.anchor[1] - y))
        miao = self.companion_spot
        return miao if miao.zone.colliderect(feet) else None

    # ------------------------------------------------------------ update
    def update(self, dt):
        self.time += dt
        for t in list(self.timers):
            t[0] -= dt
            if t[0] <= 0:
                self.timers.remove(t)
                t[1]()
        self._update_light(dt)
        av = self.avatar
        if self.dialogue is not None:
            self.dialogue.update(dt)
        elif self.panel is not None:
            self.panel.update(dt)
            if self.panel.closed:
                self._panel_done()
        if self.locked:
            av.update(dt, (0, 0), self.solids)
        else:
            av.update(dt, self.controls.direction(av.held), self.solids)
        if av.footstep:
            av.footstep = False
            self.play("footstep")
        self.companion.update(dt, (av.x, av.y), self.solids, self.miao_spots)
        self.bubble.update(dt)
        self.notice.update(dt)
        near = None if self.locked else self.nearby
        av.prompt.update(dt, (int(av.x), int(av.y) - 22) if near else None, near.prompt if near else None)
        self._near = near
        for m in self.dust:
            m[0] += m[2] * dt + math.sin(self.time * 0.6 + m[4]) * 0.15
            m[1] += m[3] * dt
            if not (24 < m[0] < 376 and 78 < m[1] < 278):
                m[0], m[1] = random.uniform(30, 370), random.uniform(120, 270)

    @property
    def miao_spots(self):
        cached = getattr(self, "_spots_ok", None)
        if cached is None:
            zones = [sp.zone.inflate(8, 8) for sp in self.spots.values()]
            cached = self._spots_ok = [p for p in MIAO_SPOTS
                                       if point_clear(p[0], p[1], self.solids, 2) and all(not z.collidepoint(p) for z in zones)]
        return cached

    def _update_light(self, dt):
        if self.power_t is not None:
            self.power_t += dt
            self.light = max(0.0, min(1.0, (self.power_t - 0.2) / POWER_FADE))
            self.flicker = max(0.0, 1.0 - abs(self.power_t - 0.9) / 0.5)
            if self.power_t > POWER_FADE + 0.6:
                self.power_t = None
        elif self.run.power:
            self.light = 1.0
        else:
            self.light = 0.0

    # ------------------------------------------------------------ drawing
    def draw(self, surf):
        surf.blit(self.static, (0, 0))
        items = self._sorted_things()
        for _, draw in sorted(items, key=lambda it: it[0]):
            draw(surf)
        self._lighting(surf)
        self._emissive(surf)
        self._dust(surf)
        surf.blit(A.vignette(), (0, 0))
        self._hud(surf)
        near = getattr(self, "_near", None)
        if near is not None:
            self.avatar.prompt.draw(surf, self.time, [near.rect], below_first=True)
        elif self.avatar.prompt.alpha > 0:
            self.avatar.prompt.draw(surf, self.time)
        if self.bubble.visible and self.panel is None and self.dialogue is None:
            self.bubble.draw(surf, (self.companion.rect.centerx, self.companion.rect.top - 2))
        self.notice.draw(surf)
        if self.panel is not None:
            self.panel.draw(surf)
        if self.dialogue is not None:
            self.dialogue.draw(surf)

    def _computer_look(self):
        if self.run.computer_done:
            return "on"
        return "standby" if self.run.power else "off"

    def _sorted_things(self):
        run = self.run
        av = self.avatar
        lamps_on = self.light > 0.5
        playing = isinstance(self.panel, UI.PhonePanel) and self.panel.lit
        things = [
            (116.0, lambda s: A.put(s, A.bed(), 26, 54)),
            (116.4, lambda s: A.put(s, A.plushie(), 44, 62)),
            (108.0, lambda s: A.put(s, A.bedside_table(), 92, 82)),
            (108.2, lambda s: A.put(s, A.small_lamp(lamps_on), 93, 70)),
            (108.2, lambda s: A.put(s, A.alarm_clock(), 108, 77)),
            (112.0, lambda s: A.put(s, A.desk(), 226, 72)),
            (112.1, lambda s: A.put(s, A.phone(playing), 232, 70)),
            (112.1, lambda s: A.put(s, A.keyboard(), 272, 84)),
            (112.2, lambda s: A.put(s, A.crt(self._computer_look()), 270, 48)),
            (112.1, lambda s: A.put(s, A.small_lamp(lamps_on), 314, 58)),
            (108.0, lambda s: A.put(s, A.cabinet(), 350, 58)),
            (194.0, lambda s: A.put(s, A.low_table(), 146, 166)),
            (194.1, lambda s: A.put(s, A.noodle_cup(), 152, 159)),
            (194.1, lambda s: A.put(s, A.cookie_jar(), 172, 157)),
            (194.1, lambda s: A.put(s, A.coffee_mug(), 190, 163)),
            (212.0, lambda s: A.put(s, A.plant(), 352, 186)),
            (266.0, lambda s: A.put(s, A.game_boxes(), 28, 244)),
            (230.0, lambda s: A.put(s, A.pouf(), 300, 212)),
            (260.0, lambda s: A.put(s, A.trash_bin(), 352, 238)),
            (-1.0, self._draw_dim_bulbs),
            (av.sort_y, self._draw_avatar),
            (self.companion.y, self._draw_companion),
        ]
        return things

    def _draw_dim_bulbs(self, surf):
        for bx, by in A.string_light_positions():
            surf.blit(A.bulb(False), (bx - 2, by - 3))

    def _draw_avatar(self, surf):
        self.avatar.draw_under(surf)
        self.avatar.draw(surf)

    def _draw_companion(self, surf):
        c = self.companion
        surf.blit(soft_shadow(14, 5, 100), (int(c.x) - 7, int(c.y) - 3))
        img = c.image(int(2 + 4 * self.light))
        surf.blit(img, (int(c.x) - img.get_width() // 2, int(c.y) - img.get_height() + 1))

    # ---- light
    def _lighting(self, surf):
        L = self.light
        k = L * L * (3 - 2 * L)                              # an ease for the ambient swell
        ambient = tuple(int(a + (b - a) * k) for a, b in zip(AMBIENT_DARK, AMBIENT_LIT))
        lay = pygame.Surface((VIEW_W, VIEW_H))
        lay.fill(ambient)
        # moonlight through the window: a pale patch on the floor with the sash bars in it (fades as the lamps come up)
        moon = 1.0 - k * 0.85
        if moon > 0.02:
            patch = pygame.Surface((VIEW_W // 4, VIEW_H // 4))
            col = tuple(int(c * moon) for c in (46, 56, 96))
            pygame.draw.polygon(patch, col, [(44, 29), (56, 29), (64, 49), (35, 49)])
            bar = tuple(int(c * 0.25) for c in col)
            pygame.draw.line(patch, bar, (50, 29), (49, 49))
            pygame.draw.line(patch, bar, (39, 39), (60, 39))
            patch = pygame.transform.smoothscale(patch, (VIEW_W, VIEW_H))            # a soft edge: the moonlight is not a stencil
            lay.blit(patch, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            glow = A.tinted_light(40, (70, 84, 140), moon * 0.7, 0.9)
            lay.blit(glow, glow.get_rect(center=(199, 56)), special_flags=pygame.BLEND_RGB_ADD)
        if L > 0:
            for (cx, cy, r, color, sq, amount) in ((200, 168, 176, (120, 82, 40), 0.7, k),
                                                   (100, 74, 44, (200, 140, 70), 1.0, self._ramp(0.25, 0.55)),
                                                   (321, 68, 54, (210, 150, 76), 1.0, self._ramp(0.4, 0.7)),
                                                   (60, 150, 60, (70, 46, 24), 0.8, k)):
                img = A.tinted_light(r, color, amount, sq)
                lay.blit(img, img.get_rect(center=(cx, cy)), special_flags=pygame.BLEND_RGB_ADD)
            for i, (bx, by) in enumerate(A.string_light_positions()):
                amount = self._ramp(0.15 + i * 0.09, 0.35 + i * 0.09)
                img = A.tinted_light(20, (255, 190, 100), amount * 0.9)
                lay.blit(img, img.get_rect(center=(bx, by + 6)), special_flags=pygame.BLEND_RGB_ADD)
        # the power box's little light, the CRT's standby glow
        led = self._led_colour()
        if led:
            img = A.tinted_light(14, led, 0.9)
            lay.blit(img, img.get_rect(center=(209, 55)), special_flags=pygame.BLEND_RGB_ADD)
        if self.run.power:
            glow = (30, 70, 56)
            amount = 0.55 + 0.45 * (1.0 if self.flicker <= 0 else (0.3 + 0.7 * abs(math.sin(self.time * 40))))
            if self.run.computer_done:
                glow, amount = (40, 120, 90), 1.0
            img = A.tinted_light(26, glow, amount, 0.9)
            lay.blit(img, img.get_rect(center=(288, 66)), special_flags=pygame.BLEND_RGB_ADD)
        surf.blit(lay, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

    def _ramp(self, a, b):
        """0..1 as `light` goes from a to b (a lamp that comes on part-way through the swell)."""
        return max(0.0, min(1.0, (self.light - a) / (b - a)))

    def _led_colour(self):
        if self.run.power:
            return (40, 160, 70)
        return (170, 60, 30) if int(self.time * 1.6) % 2 == 0 else (50, 18, 10)

    def _emissive(self, surf):
        """Things that make their own light are drawn again over the lighting, so they stay bright in the dark."""
        led = self._led_colour()
        surf.fill(tuple(min(255, int(c * 1.5)) for c in led), (208, 54, 2, 2))
        L = self.light
        if L > 0:
            for i, (bx, by) in enumerate(A.string_light_positions()):
                amount = self._ramp(0.15 + i * 0.09, 0.35 + i * 0.09)
                if amount > 0.5:
                    surf.blit(A.bulb(True), (bx - 2, by - 3))
            if self._ramp(0.25, 0.55) > 0.5:
                A.put(surf, A.small_lamp(True), 93, 70)
            if self._ramp(0.4, 0.7) > 0.5:
                A.put(surf, A.small_lamp(True), 314, 58)
        if self.run.power:                                  # the CRT's glass, a little brighter than the lamp light
            sx, sy = 270 + 5, 48 + 5
            tone = (62, 120, 96) if not self.run.computer_done else (90, 255, 190)
            flick = 1.0 if self.flicker <= 0 else (0.35 + 0.65 * abs(math.sin(self.time * 40)))
            tone = tuple(int(c * flick) for c in tone)
            surf.fill(tone, (sx + 1, sy + 1, 26, 16))
            surf.blit(A.scanlines((26, 16), 70), (sx + 1, sy + 1))
            if self.run.computer_done:
                draw_text(surf, "P_000", (sx + 3, sy + 5), (8, 40, 28))
            else:
                surf.fill((40, 160, 120), (sx + 4, sy + 12, 6, 2) if int(self.time * 2) % 2 == 0 else (0, 0, 0, 0))

    def _dust(self, surf):
        lit = self.light
        for x, y, _, _, ph, a in self.dust:
            alpha = int(a * (0.55 + 0.45 * math.sin(self.time * 1.3 + ph)) * (0.55 + 0.45 * lit))
            col = (255, 232, 180) if lit > 0.4 else (200, 214, 255)
            dot = pygame.Surface((2, 1), pygame.SRCALPHA)
            dot.fill((*col, max(0, alpha)))
            surf.blit(dot, (int(x), int(y)))

    def _hud(self, surf):
        if self.panel is not None or self.dialogue is not None:
            return
        y = A.FLOOR_BOTTOM + 5
        draw_text(surf, "[TAB] NOTES", (VIEW_W - 26, y + 2), (214, 180, 130), anchor="topright")
