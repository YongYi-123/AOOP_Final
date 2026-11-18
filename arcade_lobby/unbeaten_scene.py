"""TRIAL 02 - THE UNBEATEN RECORD: the Tournament Hall (a walkable room full of people, the registration puzzle, the three
rounds on NEON BRAWL and the ending).

Entered from the Legacy Terminal (legacy_terminal.TRIAL_SCENES["trial_02"]), so only through the real secret interface and
only when quests.trial_status says so (Chapter 01 complete, the lifetime earnings milestone reached). It borrows the
player's body from the hub and gives it back where it stood; the wallet is never touched (the fights are not machines).

The night, as the player lives it:
    the opening ......... MEMORY RECONSTRUCTION LOADED, Miao Meow amazed (once; later visits just show the title)
    the hall ............ fifteen people to talk to, a dozen things to look at; some mention the arcade's founder
    THE MISSING ENTRY ... poster + ticket (lost and found) + ledger -> the entry code at the registration terminal
    three rounds ........ the host on the stage starts each one (unbeaten_bout); a loss just offers the round again
    the ending .......... celebration, then the systems misbehave, CORE: "One more game?", Memory Fragment 02

Saved as it happens (QuestManager.save_trial_progress): registration, rounds won, stories heard, documents read. The
story hears GameEvent("secret_trial_done", key="trial_02") once, at the end; the checkpoints are then cleared so a replay
is a fresh night.
"""
import math
import random

import pygame

import golden_age_art as GA
import golden_age_ui as GU
import unbeaten_art as A
import unbeaten_content as C
import unbeaten_record as T
import unbeaten_ui as UI
from golden_age_scene import Companion, Spot as _Spot
from gfx import soft_shadow
from local_session import GameEvent
from miao_meow import point_clear
from scene_base import BaseScene
from settings import Col, VIEW_H, VIEW_W
from story_dialogue import Line, SPEAKERS, Speaker, StoryDialogue, framed_portrait, register_speaker
from ui import Notice, draw_text
from unbeaten_bout import TournamentBoutScene


class Spot(_Spot):
    """golden_age_scene's Spot, plus `extra` zones: a big board can be used from its side as well as its front."""

    def __init__(self, key, label, rect, zone, act, anchor=None, extra=()):
        super().__init__(key, label, rect, zone, act, anchor)
        self.extra = [pygame.Rect(z) for z in extra]


def zones_of(spot):
    return [spot.zone] + list(getattr(spot, "extra", ()))

put = A.put

LOW_ON_SCREEN = 212
MIAO_SPOTS = ((60, 182), (112, 176), (156, 160), (246, 160), (300, 166), (356, 178), (200, 206), (140, 210),
              (262, 214), (206, 238), (280, 240), (372, 262), (44, 278), (120, 280))
LEAVE_LANE = 176                    # the crowd walks home along this line, to the door
WALK_SPEED = 30.0
CONFETTI_MAX = 160


def _speaker_key(key):
    return f"T2_{key}"


# ------------------------------------------------------------------ the people in the hall
class Person:
    """Someone in the crowd: stands, sits, cheers, plays a cabinet or strolls a short loop; turns to whoever talks to them.
    Drawn with the hub's own character sprite in their own colours."""

    def __init__(self, key, spec):
        self.key = key
        self.spec = spec
        self.name = spec["name"]
        self.home = tuple(spec["pos"])
        self.x, self.y = float(self.home[0]), float(self.home[1])
        self.facing = self.home_facing = spec.get("facing", "down")
        self.pose = spec.get("pose", "idle")
        self.route = tuple(spec.get("route") or ())
        self.leg = 1 if self.route else 0
        self.pause = 0.0
        look = spec["look"]
        self.look = A.person_look(key, look["shirt"], look["hair"], C.SKINS[look.get("skin", "peach")], look.get("hair_style", "short"),
                                  look.get("eyes", "dot"))
        self.sheet = A.person_sheet(self.look, spec.get("outfit"))
        self.time = random.Random(key).uniform(0, 6)
        self.walking = False
        self.cheer = 0.0                    # seconds of cheering asked for by the scene
        self.frozen = False
        self.talking = False
        self.leaving = None                 # waypoints to the door once the night is over
        self.gone = False
        self.talks = 0
        self.heard = {}                     # phase key -> conversations had in it (this visit)

    @property
    def seated(self):
        return self.pose == "sit" and self.leaving is None

    @property
    def solid(self):
        if self.gone or self.seated:
            return None
        return pygame.Rect(int(self.x) - 5, int(self.y) - 4, 10, 5)

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 7, int(self.y) - 20, 14, 21)

    @property
    def zone(self):
        z = self.spec.get("zone")
        return pygame.Rect(z) if z else pygame.Rect(int(self.x) - 15, int(self.y) - 14, 30, 26)

    def look_at(self, x, y):
        dx, dy = x - self.x, y - self.y
        self.facing = ("right" if dx > 0 else "left") if abs(dx) > abs(dy) else ("down" if dy > 0 else "up")

    def update(self, dt, blocked):
        if self.frozen or self.gone:
            return
        self.time += dt
        self.cheer = max(0.0, self.cheer - dt)
        self.walking = False
        if self.talking:
            return
        if self.leaving:
            self._walk(dt, self.leaving[0], lambda: self.leaving.pop(0))
            if not self.leaving:
                self.gone = True
            return
        if self.route:
            if self.pause > 0:
                self.pause -= dt
                return
            target = self.route[self.leg]
            if blocked(self, target):
                return
            self._walk(dt, target, self._next_leg)
        else:
            self.facing = self.home_facing

    def _next_leg(self):
        self.leg = (self.leg + 1) % len(self.route)
        self.pause = 1.4

    def _walk(self, dt, target, arrived):
        dx, dy = target[0] - self.x, target[1] - self.y
        d = math.hypot(dx, dy)
        if d < 1.0:
            self.x, self.y = float(target[0]), float(target[1])
            arrived()
            return
        step = min(d, WALK_SPEED * dt * (1.3 if self.leaving else 1.0))
        self.x += dx / d * step
        self.y += dy / d * step
        self.walking = True
        self.facing = ("right" if dx > 0 else "left") if abs(dx) >= abs(dy) else ("down" if dy > 0 else "up")

    def leave(self, obstacles=()):
        """Go home: get up, find a clear column down (or up) to the lane, walk along it and out of the door."""
        if self.leaving is not None or self.gone:
            return
        self.pose = "idle" if self.pose == "sit" else self.pose
        self.route = ()
        lane = LEAVE_LANE + (sum(map(ord, self.key)) % 5 - 2) * 4
        y = self.y + (10 if self.pose == "idle" and self.spec.get("pose") == "sit" else 0)
        path = [(self.x, y)] if y != self.y else []
        clear = lambda a, b: not any(r.inflate(4, 4).clipline(a, b) for r in obstacles)
        for cx in (self.x, 160, 240, 140, 290, 200):
            if clear((self.x, y), (cx, y)) and clear((cx, y), (cx, lane)):
                if cx != self.x:
                    path.append((cx, y))
                path.append((cx, lane))
                break
        path.append((A.START[0] - 30, lane))
        self.leaving = path

    def frame(self):
        f = self.facing
        sheet = self.sheet[f]
        t = self.time
        if self.walking:
            return sheet["walk"][int(t / 0.15) % 4]
        if self.frozen:
            return sheet["idle"][0]
        if self.cheer > 0 or (self.pose == "cheer" and t % 4.5 < 1.3 and not self.talking):
            return sheet["cheer"][int(t / 0.16) % 2]
        if self.talking:
            return sheet["idle"][int(t / 0.4) % 8]
        if self.pose == "press":
            return sheet["press"][int(t / 0.22) % 2]
        if self.pose == "sit":
            return sheet["sit"][int(t / 0.6) % 2]
        if self.pose == "wave" and t % 6 < 1.0:
            return sheet["wave"][int(t / 0.17) % 2]
        return sheet["idle"][int(t / 0.4) % 8]

    def portrait(self, mood=None, context=None):
        face = getattr(self, "_face", None)
        if face is None:
            face = self._face = framed_portrait(self.sheet["down"]["idle"][0], 2, self.spec.get("accent", Col.CYAN))
        return face

    def draw(self, surf):
        if self.gone:
            return
        img = self.frame()
        if not self.seated:
            surf.blit(soft_shadow(12, 4, 90), (int(self.x) - 6, int(self.y) - 2))
        surf.blit(img, img.get_rect(midbottom=(int(self.x), int(self.y) + 1)))


class Script:
    """A cutscene: ("say", lines) waits for the dialogue box, ("wait", seconds), ("do", fn)."""

    def __init__(self, steps):
        self.steps = list(steps)
        self.index = -1
        self.timer = 0.0
        self.done = False
        self.waiting_for_dialogue = False

    def update(self, dt, scene):
        while not self.done:
            if self.waiting_for_dialogue:
                if scene.dialogue is not None:
                    return
                self.waiting_for_dialogue = False
            if self.timer > 0:
                self.timer -= dt
                dt = 0.0
                if self.timer > 0:
                    return
            self.index += 1
            if self.index >= len(self.steps):
                self.done = True
                return
            kind, arg = self.steps[self.index]
            if kind == "say":
                scene.say(arg)
                self.waiting_for_dialogue = True
            elif kind == "wait":
                self.timer = arg
            else:
                arg()


class Effects:
    """What the ending does to the hall (all off at first)."""

    def __init__(self):
        self.screen = None              # forced big-screen mode (None: follows the night)
        self.cabinet_on = False         # the unplugged machine wakes up
        self.board_glitch = 0.0         # seconds of leaderboard / screen glitch left
        self.wobble = 0.0               # seconds of distorted music left
        self.exit_flicker = False
        self.locked = False
        self.freeze_all = False
        self.fade = 0.0                 # 0..1 to black
        self.fade_to = 0.0
        self.final = 0                  # lines of the final card shown
        self.messages = []              # [(text, age)]
        self.party = False


# ------------------------------------------------------------------ the scene
class TournamentHallScene(BaseScene):
    music_id = "lobby"                  # the arcade's own floor theme: the same arcade, in its best year
    own_audio = False

    def __init__(self, game, owner):
        super().__init__(game)
        self.owner = owner
        self.hub = game.hub
        self.manager = self.hub.story.manager
        self.avatar = owner.avatar
        self.controls = owner.controls
        self.replay = self.manager.trial_done(T.TRIAL_ID)
        self.run = T.TournamentRun.from_dict(self.manager.trial_progress(T.TRIAL_ID))
        self.time = 0.0
        self.panel = None
        self.panel_then = None
        self.dialogue = None
        self.intro_dialogue = None
        self.script = None
        self.notice = Notice(center=(VIEW_W // 2, 62))
        self.bubble = GU.HintBubble()
        self.timers = []
        self.leaving = False
        self.completed_here = False
        self.fx = Effects()
        self.confetti = []
        self.celebrate = 0.0            # seconds of between-round celebration left (big screen shows WINNER)
        self.selection = getattr(self.hub, "trial02_fighter", 0)
        self.tutorial_seen = getattr(self.hub, "trial02_tutorial", False)
        self.pending = None             # a bout's outcome, acted on when the hall is back on screen
        self.looks = {}                 # thing -> times looked at (this visit)
        self.draft = T.BracketDraft()   # THE BROKEN BRACKET as the player left it (this visit)
        self.case = T.TrophyCase()      # THE CHAMPION'S TROPHY as the player left it (this visit)
        self.evidence_return = None     # a puzzle panel waiting while the evidence file is open (TAB inside it)
        self.hint_asks = {}             # puzzle -> times Miao Meow was asked about it (her hints grow clearer)
        self.bouts = 0
        self._saved = None
        self._ambience = None
        self._near = None
        self._bracket_called = self.run.bracket
        self.last_notice = None
        self.build()
        self.companion = Companion((60, 186))
        self._register_speakers()

    # ------------------------------------------------------------ building the hall
    def build(self):
        walls = [pygame.Rect(0, 0, VIEW_W, A.WALL_SOLID), pygame.Rect(0, 0, A.SIDE, VIEW_H),
                 pygame.Rect(VIEW_W - A.SIDE, 0, A.SIDE, VIEW_H), pygame.Rect(0, A.FLOOR_BOTTOM, VIEW_W, VIEW_H - A.FLOOR_BOTTOM)]
        self.walls = walls
        self.furniture = [pygame.Rect(solid) for _, solid in A.FURNITURE.values() if solid]
        self.fixed_solids = walls + self.furniture
        self.people = {key: Person(key, spec) for key, spec in C.PEOPLE.items()}
        self.spots = {sp.key: sp for sp in self.spot_defs()}
        self.static = self._static_layer()
        self._refresh_solids()

    def _refresh_solids(self):
        self.solids = self.fixed_solids + [p.solid for p in self.people.values() if p.solid is not None]

    def spot_defs(self):
        S, ins = Spot, "INSPECT"
        look = self.look
        cab = lambda i: A.FURNITURE[f"cab_{i}"][0]
        spots = [
            S("terminal", "USE TERMINAL", A.TERMINAL, (6, 102, 22, 12), self.use_terminal),
            S("ledger", ins, (A.LEDGER_POS[0], A.LEDGER_POS[1], 22, 8), (44, 102, 28, 12), lambda: self.read("ledger")),
            S("clock", ins, A.CLOCK, (31, 102, 10, 12), lambda: look("clock")),     # (right under it, clear of the ledger)
            S("lost_found", ins, A.FURNITURE["lost_found"][0], (28, 118, 18, 16), self.use_lost_found),
            S("poster", ins, A.POSTER, (76, 80, 34, 14), lambda: self.read("poster")),
            S("leaderboard", ins, A.LEADERBOARD, (288, 80, 30, 14), lambda: self.read("leaderboard")),
            S("trophy_shelf", ins, A.TROPHY_SHELF, (372, 102, 18, 12), self.use_trophies),
            S("schedule", ins, A.FURNITURE["schedule"][0], (338, 138, 26, 12), self.use_schedule),
            S("bracket_board", ins, A.FURNITURE["bracket_board"][0], (262, 256, 32, 10), self.use_bracket,
              extra=[(294, 250, 12, 30), (262, 277, 32, 11)]),                # (its right side, and the front below it)                                    # (or from its right-hand side)
            S("final_cabinet", ins, (124, 58, 22, 36), (122, 100, 36, 12), self.use_final_cabinet),
            S("bench_left", ins, A.FURNITURE["bench_left"][0], (124, 141, 28, 10), lambda: look("bench_left")),
            S("bench_right", ins, A.FURNITURE["bench_right"][0], (284, 141, 24, 10), lambda: look("bench_right")),
            S("snack_bar", ins, A.FURNITURE["snack_bar"][0], (298, 232, 20, 12), lambda: look("snack_bar")),
            S("magazines", ins, A.FURNITURE["magazines"][0], (158, 252, 26, 12), lambda: look("magazines"),
              extra=[(158, 277, 26, 11)]),                                    # (or from the front, below it)
            S("photo_board", ins, A.FURNITURE["photo_board"][0], (230, 256, 30, 10), self.use_photos,
              extra=[(218, 250, 12, 30), (230, 277, 31, 11)]),                # (its left side, and the front below it)                                    # (or from its left-hand side)
            S("door", "LEAVE HALL", A.DOOR, A.DOOR_ZONE, self.ask_leave),
        ]
        for i in range(4):
            spots.append(S(f"cab_{i}", ins, cab(i), (cab(i)[0], 231, 22, 12), (lambda i=i: self.use_cabinet(i))))
        return spots

    def _static_layer(self):
        s = A.hall_shell().copy()
        for img, pos in ((A.poster(), A.POSTER.topleft), (A.trophy_shelf(), A.TROPHY_SHELF.topleft), (A.door(), A.DOOR.topleft),
                         (A.banner((150, 40, 60)), (112, 4)), (A.banner((40, 70, 150)), (275, 4))):
            put(s, img, *pos)
        # REGISTRATION over the desk
        draw_text(s, "REGISTRATION", (40, 26), A.NEON_CYAN, anchor="midtop")
        draw_text(s, "PRIZES", (356, 56), A.NEON_PINK, anchor="midtop")
        for rect in self.furniture:
            if rect.w > 30:
                s.blit(soft_shadow(rect.w + 8, 8, 70), (rect.x - 4, rect.bottom - 5))
        return s

    def _register_speakers(self):
        for key, person in self.people.items():
            register_speaker(_speaker_key(key), Speaker(person.name, person.spec.get("accent", Col.CYAN), person.portrait))
        if "CORE" not in SPEAKERS:
            register_speaker("CORE", Speaker("CORE", (255, 70, 110), None, blip="glitch"))

    # ------------------------------------------------------------ lifecycle
    def on_enter(self):
        av = self.avatar
        self._saved = (av.x, av.y, av.facing)
        self._ambience = dict(getattr(self.hub.ambience, "mix", {}))
        self.hub.ambience.set_mix({})
        av.x, av.y = float(A.START[0]), float(A.START[1])
        av.facing = "right"
        av.held = list(self.controls.held_now())
        av.stop()
        if not self.manager.state.get("flags", {}).get(T.INTRO_FLAG):
            self.later(0.7, self.play_intro)
        else:
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
        """Back from a fight: the host has something to say about it."""
        self.avatar.held.clear()
        self.avatar.stop()
        pending, self.pending = self.pending, None
        if pending is None:
            return
        outcome, number = pending
        if outcome == "won":
            self.celebrate_round(number)              # (after the final: the hall is free until the ceremony)
        elif outcome == "lost":
            self.later(0.4, lambda: self.say(C.HOST["lost"]))
        else:
            self.later(0.4, lambda: self.say(C.HOST["forfeit"]))

    def on_quit(self):
        self.avatar.held.clear()

    # ------------------------------------------------------------ helpers
    def play(self, name, volume=1.0):
        audio = getattr(self.game, "audio", None)
        if audio is not None:
            audio.play(name, volume) if volume != 1.0 else audio.play(name)

    def later(self, seconds, fn):
        self.timers.append([seconds, fn])

    def save_run(self):
        self.manager.save_trial_progress(T.TRIAL_ID, self.run.to_dict())

    @property
    def captures_text(self):
        return False

    @property
    def music_duck(self):
        fx = self.fx
        if fx.freeze_all:
            return 0.15 * (1.0 - fx.fade)
        if fx.wobble > 0:
            return 0.3 + 0.55 * abs(math.sin(self.time * 17)) * (0.6 + 0.4 * math.sin(self.time * 5))
        level = 1.0 - 0.85 * fx.fade
        return level

    @property
    def modal(self):
        return self.dialogue or self.panel

    @property
    def in_cutscene(self):
        return self.script is not None and not self.script.done

    @property
    def locked(self):
        return self.dialogue is not None or self.panel is not None or self.leaving or self.in_cutscene

    def say(self, lines, on_done=None):
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
        self.last_notice = title
        self.notice.show(title, [(t, Col.TEXT) for t in lines], color)

    def announce_start(self):
        self.tell(C.TITLE, [C.objective(self.run)], Col.YELLOW)

    # ------------------------------------------------------------ the opening
    def play_intro(self):
        def finish():
            self.manager.handle(T.INTRO_FLAG)
            self.later(0.3, self.announce_start)
        self.intro_dialogue = self.say(C.OPENING, on_done=finish)

    def _skip_intro(self):
        self.dialogue = self.intro_dialogue = None
        self.manager.handle(T.INTRO_FLAG)
        self.later(0.3, self.announce_start)

    # ------------------------------------------------------------ talking to people
    def talk_to(self, person):
        if person.key == "host":
            self.talk_to_host()
            return
        lines = self.lines_for(person)
        person.talking = True
        person.look_at(self.avatar.x, self.avatar.y)
        person.talks += 1

        key, conv = self.conversation(person)
        founder = conv.get("kevin") and person.heard.get(key, 0) == 1
        clue = conv.get("clue")
        told = bool(clue) and tuple(lines[-len(clue):]) == tuple(clue)

        def done():
            person.talking = False
            person.facing = person.home_facing
            changed = founder and self.run.hear_kevin(person.key)
            if told and self.run.hear_clue(f"{person.key}:{key}"):         # (into the evidence file)
                changed = True
            if changed:
                self.save_run()
        self.say(lines, on_done=done)

    def conversation(self, person):
        """(phase key, conversation) for `person` at this point of the night: the saved phase, and in phase 0 the
        "0+" one once the player has a badge (when the person has one)."""
        talk, phase = person.spec["talk"], self.run.phase
        key = "0+" if phase == 0 and self.run.registered and "0+" in talk else phase
        return key, talk[key]

    def lines_for(self, person):
        """What `person` says now, and count it. Only this phase's lines: the first conversation (with whatever they
        know that this phase's puzzle needs), then their other lines in turn, the clue among them so it can be asked for
        again. A founder's story already heard (on an earlier visit) is not told twice."""
        key, conv = self.conversation(person)
        n = person.heard.get(key, 0)
        if n == 0 and key == 0 and conv.get("kevin") and person.key in self.run.kevin:
            n = 1
        person.heard[key] = n + 1
        clue = conv.get("clue")
        if n == 0:
            return conv["first"] + (clue or ())
        pool = tuple(conv["again"]) + ((clue,) if clue else ())
        return pool[(n - 1) % len(pool)] if pool else conv["first"]

    def talk_to_host(self):
        host = self.people["host"]
        host.talks += 1
        run = self.run
        if not run.registered:
            self.say(C.HOST["unregistered"] if host.talks == 1 else C.HOST["unregistered_again"])
            return
        if run.finished:
            self.say(C.HOST["ceremony"], on_done=self.offer_ceremony)
            return
        rnd = run.next_round
        if rnd is None:
            return
        stage = run.stage
        if stage == "bracket":
            self.say(C.HOST["bracket"], on_done=lambda: self.show_evidence("slips"))
        elif stage == "trophies":
            self.say(C.HOST["key_missing"])
        elif stage == "key":
            self.say(C.HOST["key_found"])
        else:
            self.say(C.HOST["offer"][rnd.number], on_done=lambda: self.offer_round(rnd))

    def offer_ceremony(self):
        self.open_panel(UI.ConfirmPanel("THE TROPHY CEREMONY", ["THE NIGHT ENDS WITH THE CEREMONY.", "SAY GOODBYE TO EVERYONE FIRST?"],
                                        "START IT", "NOT YET", default_yes=True))
        self.panel.ceremony = True

    def offer_round(self, rnd):
        self.open_panel(UI.ConfirmPanel(f"ROUND {rnd.number:02d}  {rnd.stage}",
                                        [f"VS {rnd.title}.  DIFFICULTY: {rnd.difficulty}",
                                         "LOSE AND YOU CAN TRY THIS ROUND AGAIN."], "FIGHT!", "NOT YET", default_yes=True))
        self.panel.round = rnd

    def start_round(self, rnd):
        self.bouts += 1
        tutorial = not self.tutorial_seen
        self.tutorial_seen = self.hub.trial02_tutorial = True
        self.play("machine")
        self.game.scenes.push(TournamentBoutScene(self.game, rnd, self.bout_over, self.selection, tutorial))

    def bout_over(self, outcome, rnd, selection):
        """Called by the bout as it closes. The checkpoint is saved now; the hall reacts when it is back (on_resume)."""
        self.selection = self.hub.trial02_fighter = selection
        if outcome == "won":
            if self.run.win(rnd.number):
                self.save_run()
        elif outcome == "lost":
            self.run.lose(rnd.number)
        self.pending = (outcome, rnd.number)

    def celebrate_round(self, number):
        """Between rounds: confetti, the crowd on its feet, WINNER on the big screen, then the host."""
        self.celebrate = 4.0
        self.play("win")
        self.burst(70)
        for p in self.people.values():
            if p.key not in ("clerk", "attendant") and not p.gone:
                p.cheer = 2.6
        self.later(1.2, lambda: self.say(C.HOST["won"][number]))

    def talk_to_miao(self):
        """Miao Meow: her realisation once enough people have talked about the founder (once); the first time in
        each phase, what she makes of the night so far; otherwise a hint (asked for, never pushed)."""
        if self.realization_waiting:
            self.say(C.REALIZATION, on_done=lambda: self.manager.handle(T.REALIZED_FLAG))
            return
        phase = self.run.phase
        if phase not in self.run.chats:
            self.run.chats.append(phase)
            self.save_run()
            self.say(C.MIAO_CHAT[phase])
            return
        stage = self.run.stage
        asked = self.hint_asks.get(stage, 0)
        tip = T.hint(self.run, asked)
        if tip != T.SLIPS_FIRST:                       # (pointing at the referee's slips is not one of the tiers)
            self.hint_asks[stage] = asked + 1
        self.bubble.show(tip)

    @property
    def realization_waiting(self):
        return self.run.realization_ready and not self.manager.state.get("flags", {}).get(T.REALIZED_FLAG)

    # ------------------------------------------------------------ the evidence file
    def evidence(self):
        """What can be read again ([TAB]): everything found so far, saved with the run, in the order it turns up."""
        run = self.run
        found = set(run.seen) | ({"slips", "bracket"} if run.bracket else set())
        return [k for k in T.EVIDENCE if k in found]

    WHEN = {1: "AFTER ROUND 01", 2: "AFTER ROUND 02"}

    def testimonies(self):
        """(tag, name, when) for every clue heard, in the order heard (only ones that still exist)."""
        out = []
        for tag in self.run.heard:
            found = self._clue(tag)
            if found is not None:
                out.append((tag, found[0]["name"], self.WHEN.get(found[1], "")))
        return out

    @staticmethod
    def _clue(tag):
        """(person spec, phase, clue lines) for a "person:phase" tag, or None if there is no such clue."""
        key, _, phase = tag.partition(":")
        spec = C.PEOPLE.get(key)
        phase = int(phase) if phase.isdigit() else phase
        conv = spec.get("talk", {}).get(phase) if spec else None
        if not conv or not conv.get("clue"):
            return None
        return spec, phase, conv["clue"]

    def open_evidence(self, at=None):
        items = self.evidence()
        panel = self.open_panel(UI.EvidencePanel(items, self.testimonies(), self.play))
        if at in items:
            panel.index = items.index(at)
        elif at is not None and at.startswith("said:"):
            tags = [t for t, _, _ in panel.said]
            if at[5:] in tags:
                panel.tab, panel.index = 1, tags.index(at[5:])
                panel.top = max(0, panel.index - panel.ROWS + 1)

    def show_said(self, tag):
        spec, phase, clue = self._clue(tag)
        self.open_panel(UI.SaidPanel(spec["name"], self.WHEN.get(phase, ""), [t for _, t, _ in clue], self.play))
        self.panel_then = lambda: self.open_evidence("said:" + tag)

    def back_to_puzzle(self):
        """The evidence file was opened from inside a puzzle: that puzzle again, exactly as it was left."""
        panel, self.evidence_return = self.evidence_return, None
        panel.closed, panel.result = False, None
        self.open_panel(panel)

    def show_evidence(self, kind, back=False):
        """Open one piece of evidence (and remember it was found). `back`: return to the evidence file afterwards."""
        if self.run.look_at(kind):
            self.save_run()
        if kind == "photos":
            self.open_panel(UI.PhotoPanel(self.play))
        elif kind == "bracket":
            if self.run.bracket:
                self.draft.slots.update(T.BRACKET_ANSWER)
                self.draft.winners = set(T.BRACKET_WINNERS)
            self.open_panel(UI.BracketPanel(self.run, self.draft, self.play))
        else:
            self.open_panel(UI.DocumentPanel(kind, self.play))
        if back:
            self.panel_then = lambda: self.open_evidence(kind)

    # ------------------------------------------------------------ looking at things
    def look(self, key, then=None):
        info = C.LOOKS[key]
        n = self.looks.get(key, 0)
        self.looks[key] = n + 1
        again = info.get("again", ())
        lines = info["lines"] if n == 0 or not again else again[(n - 1) % len(again)]
        if key == "cab_2" and n == 0:
            self.later(0.6, lambda: setattr(self, "_continue_flash", 2.2))
        self.say(lines, on_done=then)

    def read(self, doc):
        """A document: a line or two the first time, then the page itself."""
        first = self.looks.get(doc, 0) == 0
        if self.run.look_at(doc):
            self.save_run()
        open_doc = lambda: self.open_panel(UI.DocumentPanel(doc, self.play))
        if first and doc in C.LOOKS:
            self.look(doc, then=open_doc)
        else:
            self.looks[doc] = self.looks.get(doc, 0) + 1
            open_doc()

    def use_lost_found(self):
        first = self.looks.get("lost_found", 0) == 0
        if self.run.look_at("ticket"):
            self.save_run()
        open_doc = lambda: self.open_panel(UI.DocumentPanel("ticket", self.play))
        if first:
            self.look("lost_found", then=open_doc)
        else:
            open_doc()

    def use_cabinet(self, i):
        key = f"cab_{i}"
        if i == A.OFF_CABINET and self.looks.get(key, 0) >= 1:
            self.looks[key] += 1
            self.open_panel(UI.DocumentPanel("notes", self.play))
            return
        self.look(key)

    # ---- PUZZLE 02: THE BROKEN BRACKET
    def use_bracket(self):
        if self.run.rounds_won == 0 or not self.run.registered:
            self.look("bracket_board")
            return
        first = self.looks.get("bracket_broken", 0) == 0 and not self.run.bracket
        open_board = lambda: self.open_panel(UI.BracketPanel(self.run, self.draft, self.play))
        if self.run.bracket:
            self.draft.slots.update(T.BRACKET_ANSWER)                  # (the solved board, to look at again)
            self.draft.winners = set(T.BRACKET_WINNERS)
        if self.run.look_at("bracket"):
            self.save_run()
        if first:
            self.look("bracket_broken", then=open_board)
        else:
            open_board()

    def bracket_fixed(self):
        """The board adds up: saved, the host calls the semifinal."""
        self.save_run()
        self.play("win")
        self.burst(30)
        self.later(0.4, lambda: self.say(C.HOST["bracket_done"]))

    # ---- PUZZLE 03: THE CHAMPION'S TROPHY
    def use_photos(self):
        open_wall = lambda: self.show_evidence("photos")
        if self.looks.get("photo_board", 0) == 0:
            self.look("photo_board", then=open_wall)
        else:
            open_wall()

    def use_schedule(self):
        if self.run.rounds_won < 2 and not self.run.trophies:
            self.look("schedule")
            return
        open_note = lambda: self.show_evidence("champ_note")
        if self.looks.get("schedule_note", 0) == 0:
            self.look("schedule_note", then=open_note)
        else:
            open_note()

    def use_trophies(self):
        run = self.run
        if run.trophies:
            self.look("trophy_open")
        elif run.stage == "trophies":
            open_case = lambda: self.open_panel(UI.TrophyPanel(self.case, self.play))
            if self.looks.get("trophy_first", 0) == 0:
                self.look("trophy_first", then=open_case)
            else:
                open_case()
        else:
            self.look("trophy_shelf")

    def key_found(self):
        if not self.run.take_key(self.case):
            return
        self.save_run()
        self.play("equip")
        self.say(C.LOOKS["key_taken"]["lines"], on_done=lambda: self.tell("ITEM RECEIVED", [T.KEY_NAME], Col.YELLOW))

    def use_final_cabinet(self):
        run = self.run
        if run.key_used:
            self.look("final_ready")
        elif run.trophies:
            self.insert_key()
        else:
            self.say(C.LOOKS["final_cabinet"]["lines"] + C.LOOKS["final_locked"]["lines"])

    def insert_key(self):
        """The stage key goes in: the championship stage powers up, and the leaderboard flickers for a moment."""
        if not self.run.use_key():
            return
        self.save_run()
        self.play("power_on")
        self.fx.board_glitch = 0.6
        self.message(T.ANOMALY, life=4.0)
        self.say(C.LOOKS["final_cabinet"]["lines"] + C.LOOKS["final_insert"]["lines"],
                 on_done=lambda: self.later(0.3, lambda: self.say(C.HOST["key_used"])))

    def use_terminal(self):
        if self.run.registered:
            self.say(C.LOOKS["terminal_done"]["lines"])
            return
        self.open_panel(UI.TerminalPanel(self.run, self.play))

    def registered(self):
        """THE MISSING ENTRY is solved: the clerk welcomes the player and hands over the badge."""
        self.save_run()
        clerk = self.people["clerk"]
        clerk.look_at(self.avatar.x, self.avatar.y)
        self.play("equip")

        def done():
            clerk.facing = clerk.home_facing
            self.tell("ITEM RECEIVED", [T.BADGE_NAME, "TOURNAMENT PARTICIPATION OPEN"], Col.YELLOW)
        self.say(C.REGISTERED, on_done=done)

    def ask_leave(self):
        self.open_panel(UI.ConfirmPanel("LEAVE THE HALL?", ["YOUR TOURNAMENT PROGRESS IS SAVED.", "YOU CAN COME BACK ANY TIME."],
                                        "LEAVE", "STAY"))

    def leave(self):
        if self.leaving:
            return
        self.leaving = True
        self.stop_walking()
        self.game.scenes.pop()

    # ------------------------------------------------------------ panels reporting back
    def _panel_done(self):
        panel, self.panel = self.panel, None
        result = panel.result
        after, self.panel_then = self.panel_then, None
        if result == "evidence" and isinstance(panel, (UI.BracketPanel, UI.TrophyPanel, UI.TerminalPanel)):
            self.evidence_return = panel                   # (TAB inside a puzzle: it waits while the file is open)
            self.open_evidence()
        elif isinstance(panel, UI.TerminalPanel):
            if result == "registered" or (self.run.registered and not getattr(self, "_badge_given", False)):
                self._badge_given = True
                self.registered()
        elif isinstance(panel, UI.BracketPanel):
            if self.run.bracket and not getattr(self, "_bracket_called", False):
                self._bracket_called = True
                self.bracket_fixed()
        elif isinstance(panel, UI.EvidencePanel):
            if result is not None and result in T.EVIDENCE:
                self.show_evidence(result, back=True)
            elif isinstance(result, str) and result.startswith("said:"):
                self.show_said(result[5:])
            elif getattr(self, "evidence_return", None) is not None:
                self.back_to_puzzle()
        elif isinstance(panel, UI.TrophyPanel):
            if result == "key":
                self.key_found()
        elif isinstance(panel, UI.CompletePanel):
            if result == "return":
                self.leave()
            else:
                self.fresh_night()
        elif isinstance(panel, UI.ConfirmPanel):
            rnd = getattr(panel, "round", None)
            if getattr(panel, "ceremony", False):
                if result == "yes":
                    self.start_ending()
            elif rnd is not None:
                if result == "yes":
                    self.start_round(rnd)
            elif result == "yes":
                self.leave()
        if after is not None and self.panel is None and self.dialogue is None:
            after()

    # ------------------------------------------------------------ the ending
    def start_ending(self):
        if self.in_cutscene or self.completed_here:
            return
        fx = self.fx
        fx.messages.clear()
        people = self.people
        crowd = [p for k, p in people.items() if k not in C.STAFF]

        def celebrate():
            fx.screen, fx.party = "complete", True
            self.burst(120)
            self.play("win")
            for p in people.values():
                p.cheer = 30.0 if p.key not in ("clerk", "attendant") else 6.0
            host = people["host"]
            host.pose = "wave"

        def goodbye():
            fx.party = False
            for p in people.values():
                p.cheer = 0.0
            for p in crowd:
                p.leave(self.furniture)

        def cabinet_wakes():
            fx.cabinet_on = True
            self.play("crt_boot")
            self.message(C.SYSTEM_MESSAGES[0])

        def board_glitch():
            fx.board_glitch = 2.4
            fx.wobble = 1.8
            self.play("glitch")

        def extension():
            fx.exit_flicker = True
            self.message(C.SYSTEM_MESSAGES[1])

        def lock():
            fx.locked = True
            self.play("drawer_open")
            self.message(C.SYSTEM_MESSAGES[2])

        def freeze_crowd(on):
            for p in crowd:
                p.frozen = on
            if on:
                self.play("glitch", 0.6)

        def freeze_all():
            fx.freeze_all = True
            for p in people.values():
                p.frozen = True
            self.play("glitch")

        def final_card():
            fx.final = 1
            self.play("trial_complete")

        steps = [("do", celebrate), ("wait", 1.0), ("say", C.ENDING_CHEER), ("wait", 1.4), ("say", C.ENDING_GOODBYE),
                 ("do", goodbye), ("wait", 1.6), ("do", cabinet_wakes), ("wait", 1.3), ("do", board_glitch), ("wait", 1.4),
                 ("do", extension), ("wait", 1.2), ("do", lock), ("wait", 0.9), ("do", lambda: freeze_crowd(True)),
                 ("wait", 1.3), ("do", lambda: freeze_crowd(False)), ("wait", 0.9), ("say", C.ENDING_FLICKER),
                 ("wait", 0.6), ("say", C.ENDING_FINAL),
                 ("say", C.CORE_LINE), ("do", freeze_all), ("wait", 1.0), ("do", lambda: setattr(fx, "fade_to", 1.0)),
                 ("wait", 1.5), ("do", final_card), ("wait", 1.4), ("do", lambda: setattr(fx, "final", 2)), ("wait", 2.0),
                 ("do", self.complete)]
        self.script = Script(steps)
        self.stop_walking()

    def message(self, text, life=None):
        self.fx.messages.append([text, 0.0, life])
        self.play("vend_select")

    def complete(self):
        """The one place the trial is recorded: TRIAL 02 COMPLETE and Memory Fragment 02, on the FIRST completion only.
        The night's checkpoints are cleared so that a replay starts at the desk again."""
        first = not self.manager.trial_done(T.TRIAL_ID)
        if first:
            self.game.session.dispatch(GameEvent("secret_trial_done", self.owner.player_id, key=T.TRIAL_ID))
        self.completed_here = True
        self.run = T.TournamentRun()
        self.manager.save_trial_progress(T.TRIAL_ID, {})
        self.open_panel(UI.CompletePanel(first))

    def fresh_night(self):
        """STAY IN THE HALL after the ending: the memory starts over, the doors unlocked, everyone back in place."""
        self.fx = Effects()
        self.confetti.clear()
        self.draft, self.case, self.hint_asks = T.BracketDraft(), T.TrophyCase(), {}
        self.evidence_return = None
        self._bracket_called = False
        self.script = None
        self.completed_here = False
        self.replay = True
        self.looks.clear()
        self.people = {key: Person(key, spec) for key, spec in C.PEOPLE.items()}
        self._register_speakers()
        self._refresh_solids()
        self.later(0.4, self.announce_start)

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
            if event.key == pygame.K_ESCAPE and d is self.intro_dialogue:
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
        if self.leaving or self.in_cutscene:
            return
        key = event.key
        if key == pygame.K_ESCAPE:
            self.ask_leave()
        elif key == pygame.K_TAB:
            self.open_evidence()
        elif key in self.controls.move:
            if key not in av.held:
                av.held.append(key)
        elif self.controls.action_for(key) == "interact":
            spot = self.nearby
            if spot is not None:
                spot.act()

    # ------------------------------------------------------------ who is in reach
    def person_spots(self):
        out = []
        for p in self.people.values():
            if p.gone or p.leaving:
                continue
            out.append(Spot("npc_" + p.key, "TALK", p.rect, p.zone, (lambda p=p: self.talk_to(p)), anchor=p.zone.center))
        return out

    @property
    def companion_spot(self):
        c = self.companion
        return Spot("miao", "TALK", c.rect, c.zone, self.talk_to_miao, anchor=c.rect.center)

    @property
    def nearby(self):
        return self.spot_at(self.avatar.x, self.avatar.y)

    def spot_at(self, x, y):
        feet = pygame.Rect(int(x) - 5, int(y) - 5, 10, 5)
        found = [sp for sp in list(self.spots.values()) + self.person_spots() if any(z.colliderect(feet) for z in zones_of(sp))]
        if found:
            return min(found, key=lambda sp: min(math.hypot(z.centerx - x, z.centery - y) for z in zones_of(sp)
                                                 if z.colliderect(feet)) if getattr(sp, "extra", None)
                       else math.hypot(sp.anchor[0] - x, sp.anchor[1] - y))
        miao = self.companion_spot
        return miao if miao.zone.colliderect(feet) else None

    def blocked(self, person, target):
        """A stroller waits rather than walk into the player (or anyone else)."""
        ahead = pygame.Rect(int(person.x) - 6, int(person.y) - 6, 12, 8)
        dx, dy = target[0] - person.x, target[1] - person.y
        d = math.hypot(dx, dy) or 1
        ahead.move_ip(int(dx / d * 6), int(dy / d * 6))
        av = self.avatar
        if math.hypot(av.x - person.x, av.y - person.y) < 34:            # somebody wants a word: stop and wait
            return True
        return ahead.colliderect(pygame.Rect(int(av.x) - 5, int(av.y) - 5, 10, 5))

    # ------------------------------------------------------------ update
    def update(self, dt):
        self.time += dt
        for t in list(self.timers):
            t[0] -= dt
            if t[0] <= 0:
                self.timers.remove(t)
                t[1]()
        fx = self.fx
        if self.script is not None and not self.script.done:
            self.script.update(dt, self)
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
        for p in self.people.values():
            p.update(dt, self.blocked)
        self._refresh_solids()
        if not fx.freeze_all:
            self.companion.update(dt, (av.x, av.y), self.solids, self.miao_spots)
        self.bubble.update(dt)
        self.notice.update(dt)
        self.celebrate = max(0.0, self.celebrate - dt)
        self._continue_flash = max(0.0, getattr(self, "_continue_flash", 0.0) - dt)
        fx.board_glitch = max(0.0, fx.board_glitch - dt)
        fx.wobble = max(0.0, fx.wobble - dt)
        fx.fade += (fx.fade_to - fx.fade) * min(1.0, dt * 2.2)
        if abs(fx.fade - fx.fade_to) < 0.01:
            fx.fade = fx.fade_to
        for m in fx.messages:
            m[1] += dt
        self._update_confetti(dt)
        near = None if self.locked else self.nearby
        av.prompt.update(dt, (int(av.x), int(av.y) - 22) if near else None, near.prompt if near else None)
        self._near = near

    @property
    def miao_spots(self):
        cached = getattr(self, "_spots_ok", None)
        if cached is None:
            zones = [z.inflate(8, 8) for sp in self.spots.values() for z in zones_of(sp)] + [p.zone.inflate(4, 4) for p in self.people.values()]
            cached = self._spots_ok = [pt for pt in MIAO_SPOTS
                                       if point_clear(pt[0], pt[1], self.fixed_solids, 2) and all(not z.collidepoint(pt) for z in zones)]
        return cached

    # ---- confetti
    def burst(self, n):
        rng = random.Random(int(self.time * 1000))
        colors = A.confetti_colors()
        for _ in range(n):
            if len(self.confetti) >= CONFETTI_MAX:
                break
            self.confetti.append([rng.uniform(20, 380), rng.uniform(-40, 10), rng.uniform(-12, 12), rng.uniform(18, 46),
                                  rng.uniform(0, 6.28), rng.choice(colors), rng.uniform(3.5, 7.0)])

    def _update_confetti(self, dt):
        if self.fx.freeze_all:
            return
        if self.fx.party and len(self.confetti) < CONFETTI_MAX - 6 and int(self.time * 10) != int((self.time - dt) * 10):
            self.burst(4)
        alive = []
        for c in self.confetti:
            c[0] += (c[2] + math.sin(self.time * 3 + c[4]) * 10) * dt
            c[1] += c[3] * dt
            c[6] -= dt
            if c[6] > 0 and c[1] < A.FLOOR_BOTTOM:
                alive.append(c)
        self.confetti = alive

    # ------------------------------------------------------------ drawing
    def screen_mode(self):
        fx = self.fx
        if fx.screen:
            return fx.screen
        if self.celebrate > 0:
            return "win"
        stage = self.run.stage
        if stage == "bracket":
            return "bracket"
        if stage in ("trophies", "key"):
            return "offline"
        return "round" if self.run.registered and self.run.next_round else "title"

    def draw(self, surf):
        fx = self.fx
        t = self.time
        surf.blit(self.static, (0, 0))
        self._draw_wall(surf, t)
        for _, draw in sorted(self._things(), key=lambda it: it[0]):
            draw(surf)
        self._lighting(surf)
        self._emissive(surf, t)
        for x, y, _, _, ph, color, life in self.confetti:
            w = 2 if int(t * 8 + ph * 3) % 2 else 1
            surf.fill(color, (int(x), int(y), w, 3 - w))
        surf.blit(GA.vignette(), (0, 0))
        if fx.freeze_all:
            gray = pygame.transform.grayscale(surf)
            gray.set_alpha(150)
            surf.blit(gray, (0, 0))
            for y in range(0, VIEW_H, 3):
                surf.fill((10, 30, 40), (0, y, VIEW_W, 1), special_flags=pygame.BLEND_RGB_ADD)
        self._messages(surf)
        self._hud(surf)
        near = self._near
        if near is not None and not self.locked:
            self.avatar.prompt.draw(surf, t, [near.rect], below_first=True)
        elif self.avatar.prompt.alpha > 0:
            self.avatar.prompt.draw(surf, t)
        if self.bubble.visible and self.panel is None and self.dialogue is None:
            self.bubble.draw(surf, (self.companion.rect.centerx, self.companion.rect.top - 2))
        self.notice.draw(surf)
        if fx.fade > 0:
            black = pygame.Surface((VIEW_W, VIEW_H))
            black.set_alpha(int(255 * fx.fade))
            surf.blit(black, (0, 0))
        for i, line in enumerate(C.FINAL_CARD[:fx.final]):
            draw_text(surf, line, (VIEW_W // 2, 128 + i * 20), (255, 230, 170) if i == 0 else (180, 230, 255), 1, "midtop",
                      glow=(80, 50, 20))
        if self.panel is not None:
            self.panel.draw(surf)
        if self.dialogue is not None:
            self.dialogue.draw(surf)

    def _draw_wall(self, surf, t):
        fx = self.fx
        put(surf, A.wall_clock(51 - int(t / 20) % 4), *A.CLOCK.topleft)
        put(surf, A.leaderboard(t, fx.board_glitch + (1 if int(t * 10) % 53 == 0 else 0)), *A.LEADERBOARD.topleft)
        self._screen_img = A.stage_screen(t, self.screen_mode(), (self.run.next_round or T.ROUNDS[-1]).number, fx.board_glitch)
        surf.blit(self._screen_img, A.SCREEN.topleft)
        lit = 1.0
        if fx.exit_flicker:
            lit = 1.0 if random.Random(int(t * 14)).random() > 0.45 else 0.15
        put(surf, A.exit_sign(lit, fx.locked), *A.EXIT_SIGN.topleft)
        if fx.locked:
            put(surf, A.padlock(), A.DOOR.x + 3, A.DOOR.y + 22)
        A.string_lights(surf, t, fx.party or self.celebrate > 0)

    def _things(self):
        F = A.FURNITURE
        t = self.time
        fx = self.fx
        cab_colors = ((60, 110, 200), (200, 70, 120), (90, 90, 110), (230, 150, 60))

        def cab(i):
            def draw(s):
                x, y = F[f"cab_{i}"][0][:2]
                off = i == A.OFF_CABINET
                flash = getattr(self, "_continue_flash", 0) > 0
                on = (not off) or fx.cabinet_on or flash
                screen = "continue" if off and (fx.cabinet_on or flash) else "attract"
                put(s, A.cabinet(cab_colors[i], screen, on, t, off and fx.cabinet_on), x, y)
                if off and not fx.cabinet_on:
                    put(s, A.out_of_order_sign(), x + 2, y + 22)
                    s.fill((230, 230, 200), (x + 20, y + 26, 4, 6))        # the log taped to its side
            return draw
        things = [
            (60.0, lambda s: put(s, A.stage(), *F["stage"][0][:2])),
            (60.4, lambda s: put(s, A.trophy(), *A.TROPHY)),
            (60.5, lambda s: [put(s, A.cabinet((120, 60, 180) if i else (60, 160, 200), "attract", True, t + i), x, y)
                              for i, (x, y) in enumerate(A.STAGE_CABS)]),
            (61.0, lambda s: A.stage_bulbs(s, t, fx.party or self.celebrate > 0)),
            (86.0, lambda s: put(s, A.counter(64, 24, (150, 96, 56), (110, 60, 40)), *F["reg_counter"][0][:2])),
            (86.2, lambda s: put(s, A.terminal("green" if self.run.registered else "red"), *A.TERMINAL.topleft)),
            (86.2, lambda s: put(s, A.ledger_book(), *A.LEDGER_POS)),
            (86.0, lambda s: put(s, A.counter(72, 24, (150, 96, 56), (80, 40, 70), "PRIZE COUNTER", A.NEON_PINK), *F["prize_counter"][0][:2])),
            (122.0, lambda s: put(s, A.lost_found(), *F["lost_found"][0][:2])),
            (131.0, lambda s: put(s, A.bench(60), *F["bench_left"][0][:2])),
            (131.0, lambda s: put(s, A.bench(60), *F["bench_right"][0][:2])),
            (130.0, lambda s: put(s, A.schedule_board(), *F["schedule"][0][:2])),
            (214.0, lambda s: (put(s, A.snack_bar(), *F["snack_bar"][0][:2]), put(s, A.popcorn(), 304, 198),
                               put(s, A.soda_cups(), 360, 204))),
            (268.0, lambda s: put(s, A.magazine_rack(), *F["magazines"][0][:2])),
            (270.0, lambda s: put(s, A.photo_board(), *F["photo_board"][0][:2])),
            (270.0, lambda s: put(s, A.bracket_board(self.run.stage == "bracket"), *F["bracket_board"][0][:2])),
            (60.6, self._draw_keyhole),
            (self.avatar.sort_y, self._draw_avatar),
            (self.companion.y, self._draw_companion),
        ]
        for i in range(4):
            things.append((216.0, cab(i)))
        for p in self.people.values():
            things.append((p.y + (0.5 if p.seated else 0), p.draw))
        return things

    def _draw_keyhole(self, surf):
        x, y = A.STAGE_CABS[0]
        lit = self.run.key_used
        surf.fill((255, 214, 90) if lit else (40, 30, 20), (x + 10, y + 27, 2, 3))
        if lit and int(self.time * 2) % 2:
            surf.fill((255, 250, 200), (x + 10, y + 26, 2, 1))

    def _draw_avatar(self, surf):
        self.avatar.draw_under(surf)
        self.avatar.draw(surf)

    def _draw_companion(self, surf):
        c = self.companion
        surf.blit(soft_shadow(14, 5, 100), (int(c.x) - 7, int(c.y) - 3))
        img = c.image(5)
        surf.blit(img, (int(c.x) - img.get_width() // 2, int(c.y) - img.get_height() + 1))
        if self.realization_waiting and not self.locked and int(self.time * 1.2) % 3 != 2:
            x, y = int(c.x), int(c.y) - 24
            surf.fill((250, 240, 214), (x - 6, y, 13, 6))
            for k in range(3):
                surf.fill((70, 44, 30), (x - 4 + k * 4, y + 2, 2, 2))

    def _lighting(self, surf):
        fx = self.fx
        lay = pygame.Surface((VIEW_W, VIEW_H))
        lay.fill((214, 188, 176) if not fx.freeze_all else (160, 170, 190))
        add = lambda r, color, level, pos, sq=1.0: lay.blit(GA.tinted_light(r, color, level, sq), GA.tinted_light(r, color, level, sq).get_rect(center=pos),
                                                           special_flags=pygame.BLEND_RGB_ADD)
        t = self.time
        party = fx.party or self.celebrate > 0
        add(96, (90, 70, 40), 1.0, (200, 84), 0.6)                         # the stage spotlight pool
        add(60, (60, 50, 90), 0.9, (200, 30), 0.6)                          # the big screen
        if party:
            for k in range(3):
                x = 200 + int(math.sin(t * 1.4 + k * 2.1) * 150)
                add(40, ((120, 40, 80), (40, 90, 120), (120, 100, 30))[k], 1.0, (x, 150 + k * 40), 0.6)
        for i in range(4):
            x = A.FURNITURE[f"cab_{i}"][0][0] + 11
            on = i != A.OFF_CABINET or fx.cabinet_on
            if on:
                add(20, (40, 50, 90) if i != A.OFF_CABINET else (30, 90, 70), 1.0, (x, 206))
        add(26, (90, 20, 20), 0.8 if not fx.exit_flicker else (0.8 if int(t * 14) % 3 else 0.1), A.EXIT_SIGN.center)
        add(40, (80, 60, 30), 0.9, (340, 216), 0.6)
        add(40, (70, 40, 60), 0.9, (354, 90), 0.6)
        add(34, (40, 70, 80), 0.9, (40, 92), 0.6)
        surf.blit(lay, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

    def _emissive(self, surf, t):
        """The lights that make their own light, redrawn bright over the lighting."""
        fx = self.fx
        surf.blit(self._screen_img, A.SCREEN.topleft)
        A.string_lights(surf, t, fx.party or self.celebrate > 0)
        A.stage_bulbs(surf, t, fx.party or self.celebrate > 0)
        if not fx.exit_flicker or random.Random(int(t * 14)).random() > 0.45:
            put(surf, A.exit_sign(1.0, fx.locked), *A.EXIT_SIGN.topleft)
        surf.fill(A.NEON_PINK, (0, 3, VIEW_W, 1))

    def _messages(self, surf):
        y = 72
        for text, age, life in self.fx.messages:
            shown = text[:int(age * 28)]
            if not shown or (life is not None and age > life):
                continue
            w = 8 + len(text) * 6
            box = pygame.Surface((w, 12), pygame.SRCALPHA)
            box.fill((0, 20, 10, 200))
            surf.blit(box, (VIEW_W - w - 10, y - 2))
            draw_text(surf, shown, (VIEW_W - w - 6, y), (110, 255, 170))
            y += 14

    def _hud(self, surf):
        if self.panel is not None or self.dialogue is not None or self.in_cutscene:
            return
        y = A.FLOOR_BOTTOM + 2
        x = 12
        if self.run.has_badge:
            put(surf, A.badge_icon(), x, y - 2)
            draw_text(surf, "BADGE", (x + 16, y + 1), (255, 214, 120))
            x += 56
        if self.run.registered:
            draw_text(surf, "ROUNDS", (x, y + 1), (200, 190, 230))
            for i in range(len(T.ROUNDS)):
                won = i < self.run.rounds_won
                r = pygame.Rect(x + 42 + i * 9, y + 1, 6, 6)
                pygame.draw.rect(surf, (255, 214, 90) if won else (90, 70, 100), r, 0 if won else 1)
            x += 72
        if self.run.trophies and not self.run.key_used:
            put(surf, A.key_icon(), x, y)
            draw_text(surf, "STAGE KEY", (x + 20, y + 1), (255, 214, 120))
        draw_text(surf, "[TAB] EVIDENCE  [ESC] LEAVE", (VIEW_W - 12, y + 1), (214, 180, 130), anchor="topright")
