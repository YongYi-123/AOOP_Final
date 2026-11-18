"""Helpers that play TRIAL 02 the way a person does: real key events fed to the real Game, one frame at a time.

Walking reuses golden_age_testing.Driver (a breadth-first route over the hall's own collision boxes, arrow keys held along
it). The registration wheels are turned with the arrow keys, and the fights are played by a small keyboard bot on NEON
BRAWL's real input path (arrow keys held, J / K / I tapped) - or, with real=False, by the same bot driving the bout's
rules directly, which is much faster for long suites.
"""
import unbeaten_record as T
import unbeaten_ui as UI
from golden_age_testing import DT, Driver, K, key_down, key_up
from neon_brawl.data import ATTACKS
from unbeaten_bout import TournamentBoutScene
from unbeaten_scene import TournamentHallScene

__all__ = ("HallDriver", "DT", "K", "key_down", "key_up")


def bot_move(bout, style="smart", clock=0.0):
    """What the bot does this frame: (direction, action or None). style "smart" dodges windups and uses heavies on a
    guard; "mash" stands in line and presses J; "idle" does nothing at all (to lose a round on purpose)."""
    p, o = bout.player, bout.opponent
    if style == "idle" or o is None or not o.alive:
        return (0, 0), None
    dx, dy = o.x - p.x, o.y - p.y
    if style == "smart" and o.swing is not None and o.swing.age < ATTACKS[o.swing.name].windup \
            and abs(dx) < ATTACKS[o.swing.name].reach + 25 and p.dodge_cooldown <= 0 and p.ready:
        return (0, 0), "dodge"
    if abs(dy) > 5:
        return (0, 1 if dy > 0 else -1), None
    if abs(dx) > 34:
        return (1 if dx > 0 else -1, 0), None
    facing = 1 if dx > 0 else -1
    if p.facing != facing and p.ready:
        return (facing, 0), None
    if style == "smart" and (o.state == "guard" or clock % 1.5 < 0.35):
        return (0, 0), "heavy"
    return (0, 0), "light"


ARROWS = {(1, 0): K.K_RIGHT, (-1, 0): K.K_LEFT, (0, 1): K.K_DOWN, (0, -1): K.K_UP}
ACTION_KEYS = {"light": K.K_j, "heavy": K.K_k, "dodge": K.K_i}


class HallDriver(Driver):
    """Drives a Game whose top scene is the Tournament Hall (or a bout pushed over it)."""

    @property
    def hall(self):
        for s in reversed(self.game.scenes.stack):
            if isinstance(s, TournamentHallScene):
                return s
        return None

    def walk_to(self, spot_key, limit=1500):
        """As golden_age_testing's, but people (and Miao) move: if the target walked off, route again (a few times)."""
        for attempt in range(5):
            try:
                return super().walk_to(spot_key, limit)
            except AssertionError:
                if attempt == 4:
                    raise
                self.frames(20)

    def talk(self, key, presses=40):
        """Walk to a person (or a thing) and press E, then read the conversation to the end."""
        self.use(key if key in self.hall.spots or key == "miao" else "npc_" + key)
        self.talk_through(presses)

    # ------------------------------------------------------------ THE MISSING ENTRY
    def read_documents(self):
        for spot in ("poster", "lost_found", "ledger"):
            self.use(spot)
            self.talk_through()
            assert isinstance(self.scene.panel, UI.DocumentPanel), self.scene.panel
            self.tap(K.K_e)
            self.frames(6)

    def enter_code(self, code):
        """At the open terminal: turn the three wheels with the arrow keys to `code`, then press E."""
        panel = self.scene.panel
        assert isinstance(panel, UI.TerminalPanel), panel
        wheels = panel.wheels
        target = [T.LETTERS.index(code[0]), T.TENS.index(int(code[1])), T.UNITS.index(int(code[2]))]
        for i, want in enumerate(target):
            while wheels.cursor != i:
                self.tap(K.K_RIGHT)
            n = len(wheels.choices[i])
            steps = (want - wheels.values[i]) % n
            for _ in range(steps):
                self.tap(K.K_DOWN)
        self.tap(K.K_e)
        self.frames(4)
        return panel.reply

    def register(self, code=T.ANSWER):
        self.use("terminal")
        reply = self.enter_code(code)
        if reply and reply[0] == "ok":
            self.tap(K.K_e)                     # CONTINUE: the clerk and the badge
            self.frames(10)
            self.talk_through()
            self.seconds(0.5)
        return reply

    # ------------------------------------------------------------ the rounds
    def start_round(self):
        """Talk to the host, read the offer, choose FIGHT!. Returns the bout scene once it is on screen."""
        self.use("npc_host")
        self.talk_through()
        assert isinstance(self.scene.panel, UI.ConfirmPanel), self.scene.panel
        self.tap(K.K_e)
        self.frames(40)
        assert isinstance(self.scene, TournamentBoutScene), self.scene
        return self.scene

    def fight(self, style="smart", real=True, limit=180.0, character=0):
        """In a bout scene: pick the fighter (A/D from REX), skip the controls card, fight until the result card."""
        bout_scene = self.scene
        assert isinstance(bout_scene, TournamentBoutScene)
        if bout_scene.brawl.screen == "select":
            while bout_scene.brawl.selection != character:
                self.tap(K.K_d)
            self.tap(K.K_RETURN)
        if bout_scene.brawl.screen == "tutorial":
            self.tap(K.K_RETURN)
        self.seconds(2.6)                                   # ROUND 01 ... FIGHT!
        held = set()
        t = 0.0
        while bout_scene.result is None and t < limit:
            bout = bout_scene.bout
            if real:
                direction, action = bot_move(bout, style, t) if bout.state == "playing" else ((0, 0), None)
                want = {ARROWS[(direction[0], 0)]} if direction[0] else set()
                if direction[1]:
                    want.add(ARROWS[(0, direction[1])])
                events = [key_up(k) for k in held - want] + [key_down(k) for k in want - held]
                held = want
                if action:
                    events += [key_down(ACTION_KEYS[action]), key_up(ACTION_KEYS[action])]
                self.frames(1, events)
            else:
                direction, action = bot_move(bout, style, t) if bout.state == "playing" else ((0, 0), None)
                if action:
                    bout.player.act(action)
                bout.update(DT, direction)
                bout_scene.update(0.0)
                self.clock += DT
            t += DT
        if held:
            self.frames(1, [key_up(k) for k in held])
        self.seconds(0.7)
        return bout_scene.result

    def finish_bout(self, retry=False):
        """On the result card: ENTER (a win goes back to the stage; a loss RETRY or BACK TO THE HALL)."""
        bout_scene = self.scene
        if bout_scene.result == "lost" and not retry:
            self.tap(K.K_RIGHT)
        self.tap(K.K_RETURN)
        self.frames(40)

    def win_round(self, style="smart", real=True):
        self.start_round()
        result = self.fight(style, real)
        assert result == "won", result
        self.finish_bout()
        self.seconds(2.0)
        self.talk_through()
        self.seconds(0.5)
        return result

    # ------------------------------------------------------------ the ending
    def start_ceremony(self):
        """After the final: talk to the host and say START IT (the ending begins)."""
        self.use("npc_host")
        self.talk_through()
        assert isinstance(self.scene.panel, UI.ConfirmPanel) and getattr(self.scene.panel, "ceremony", False), self.scene.panel
        self.tap(K.K_e)
        self.frames(4)

    def watch_ending(self, limit=60.0):
        """Start the ceremony if it has not started, then press E through the ending until the finish card is up."""
        if self.hall.script is None and self.hall.run.finished:
            self.start_ceremony()
        t = 0.0
        while not isinstance(self.scene.panel, UI.CompletePanel) and t < limit:
            if self.scene.dialogue is not None and self.scene.dialogue.done_typing:
                self.tap(K.K_e)
                t += 2 * DT
            else:
                self.frames(1)
                t += DT
        assert isinstance(self.scene.panel, UI.CompletePanel), "no finish card"

    # ------------------------------------------------------------ PUZZLE 02: THE BROKEN BRACKET
    def open_bracket(self):
        self.use("bracket_board")
        if self.scene.dialogue is not None:
            self.talk_through()
        assert isinstance(self.scene.panel, UI.BracketPanel), self.scene.panel
        return self.scene.panel

    def fill_bracket(self, slots=None, winners=None, check=True):
        """On the open board, with the arrow keys: put `slots` ({slot: name}) in and mark `winners`, then CHECK."""
        panel = self.scene.panel
        slots = dict(T.BRACKET_ANSWER if slots is None else slots)
        winners = set(T.BRACKET_WINNERS if winners is None else winners)
        for slot in T.BRACKET_SLOTS:                           # empty the board first (so no name is held elsewhere)
            self._row(panel, T.BRACKET_SLOTS.index(slot))
            for _ in range(len(T.BRACKET_POOL) + 2):
                if panel.draft.slots[slot] is None:
                    break
                self.tap(K.K_RIGHT)
        for slot in T.BRACKET_SLOTS:
            self._row(panel, T.BRACKET_SLOTS.index(slot))
            for _ in range(len(T.BRACKET_POOL) + 2):
                if panel.draft.slots[slot] == slots.get(slot):
                    break
                self.tap(K.K_RIGHT)
            if slot in winners:
                self.tap(K.K_e)
        if check:
            self._row(panel, 6)
            self.tap(K.K_e)
        return panel.reply

    def _row(self, panel, row):
        while panel.row != row:
            self.tap(K.K_DOWN if panel.row < row else K.K_UP)

    def fix_bracket(self):
        self.open_bracket()
        reply = self.fill_bracket()
        assert reply == "ok", reply
        self.tap(K.K_e)                                         # DONE
        self.seconds(0.8)
        self.talk_through()                                     # the host calls the semifinal
        self.seconds(0.3)

    # ------------------------------------------------------------ PUZZLE 03: THE CHAMPION'S TROPHY
    def open_trophies(self):
        self.use("trophy_shelf")
        if self.scene.dialogue is not None:
            self.talk_through()
        assert isinstance(self.scene.panel, UI.TrophyPanel), self.scene.panel
        return self.scene.panel

    def arrange_trophies(self, order=T.TROPHY_ANSWER, facings=(0, 0, 0), pull=True):
        """With the keys: lift and swap trophies into `order`, turn each to `facings`, pull the lever."""
        panel = self.scene.panel
        case = panel.case
        for i, kind in enumerate(order):
            j = case.order.index(kind)
            if j != i:
                self._cursor(case, j)
                self.tap(K.K_e)
                self._cursor(case, i)
                self.tap(K.K_e)
        for i, want in enumerate(facings):
            self._cursor(case, i)
            while case.slots[i][1] != want:
                self.tap(K.K_DOWN)
        if pull:
            self._cursor(case, 3)
            self.tap(K.K_e)
        return case.open

    def _cursor(self, case, i):
        while case.cursor != i:
            self.tap(K.K_RIGHT)

    def get_stage_key(self):
        self.open_trophies()
        assert self.arrange_trophies()
        self.seconds(1.0)
        self.tap(K.K_e)                                         # take the key
        self.frames(6)
        self.talk_through()
        self.seconds(0.3)

    def insert_key(self):
        self.use("final_cabinet")
        self.talk_through()
        self.seconds(0.6)
        self.talk_through()                                     # the host: THE STAGE IS LIVE
        self.seconds(0.3)

    def play_through(self, real=True):
        self.read_documents()
        self.register()
        self.win_round(real=real)
        self.fix_bracket()
        self.win_round(real=real)
        self.get_stage_key()
        self.insert_key()
        self.win_round(real=real)
        self.watch_ending()
