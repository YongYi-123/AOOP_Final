"""CHAPTER 02, THE FORGOTTEN GAMES: the hint cards in the capsule machines, the three hidden clues (NEON CAT MAZE's
corridor, STARFALL ASSAULT's quiet signal, CAT VOLLEYBALL's old ticket) by both routes, Miao Meow's one-time talk,
Mochi's maintenance record and its answer, and the Golden Cat in NEON CLAW that awards Secret Item 02.

    python3 -m unittest test_forgotten_games
"""
import itertools
import os
import random
import re
import shutil
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from game import Game  # noqa: E402  (first: it puts the project root, and so the minigame packages, on sys.path)
import claw_machine as cm  # noqa: E402
import forgotten_games as fg  # noqa: E402
import mochi_chat as C  # noqa: E402
import quests as Q  # noqa: E402
from capsule import CAPSULE_MACHINES, CAT, RETRO, CapsuleService  # noqa: E402
from capsule_exchange import REDEEMABLE  # noqa: E402
from capsule_ui import CapsuleScene  # noqa: E402
from cat_maze_scene import CatMazeScene  # noqa: E402
from claw_scene import ClawScene  # noqa: E402
from galaxy_defender_scene import GalaxyDefenderScene  # noqa: E402
from item_registry import COLLECTIBLE, ITEM_REGISTRY  # noqa: E402
from local_session import GameEvent, LocalSession  # noqa: E402
from claw_lock import ClawLockScene  # noqa: E402
from maintenance_note import MaintenanceNoteScene  # noqa: E402
from mochi_chat import MochiChatScene  # noqa: E402
from pixel_volleyball_scene import PixelVolleyballScene  # noqa: E402
from player_profile import PlayerProfile, ProfileStore  # noqa: E402
from quests import CH2_CLUE_FLAGS, CH2_CLUES, CH2_TRIES_NEEDED, QuestManager  # noqa: E402
from room_testing import goto_room  # noqa: E402

from galaxy_defender import quiet_signal  # noqa: E402
from galaxy_defender.game import GalaxyGame, Screen as GScreen  # noqa: E402
from neon_cat_maze import corridor  # noqa: E402
from neon_cat_maze.game import CatMazeGame, Screen as MScreen  # noqa: E402
from neon_cat_maze.model import Run as MazeRun  # noqa: E402
from pixel_volleyball import old_ticket  # noqa: E402
from pixel_volleyball.game import VolleyGame  # noqa: E402
from pixel_volleyball.model import MatchState, VolleyInput  # noqa: E402

pygame.init()
DT = 1 / 60
K = pygame
EARLY = ["grand_tour", "meet_the_locals", "arcade_explorer", "earn_some_rewards"]
CARDS = tuple(fg.HINT_CARDS.values())


def story(chapter2=True, clues=(), solved=False, hint_told=False, item=False):
    """A saved story at the start of Chapter 01 (chapter2=False) or of Chapter 02 (Trial 01 complete)."""
    flags = {"vending_secret": True, "tour_home": True, "tour_arcade": True, "met_mochi": True}
    stats = {}
    if chapter2:
        stats = {"secret_items": [Q.SECRET_ITEM_RETRO_RACER], "secret_trials": ["trial_01"]}
        flags.update({Q.MIAO_REVERSE_ROAD: True, Q.MOCHI_ARCADE_STORY: True, "memory_fragment_01": True})
    for clue in clues:
        flags[CH2_CLUE_FLAGS[clue]] = True
    if solved:
        flags[Q.CH2_RIDDLE_SOLVED] = True
    if hint_told:
        flags[Q.MIAO_CH2_HINT] = True
    if item:
        stats.setdefault("secret_items", []).append(Q.SECRET_ITEM_CLAW)
    return {"opening_done": True, "completed": list(EARLY), "flags": flags, "stats": stats}


def profile(pid="fg", tickets=0, tokens=0, **kw):
    p = PlayerProfile(profile_id=pid, display_name=pid.upper(), tokens=tokens, tickets=tickets)
    p.set_story(story(**kw))
    return p


def key(k, unicode=""):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=unicode)


class Picks:
    """An rng stand-in for capsule pulls: choices() takes the first prize that is not a hint card (or a card if forced)."""

    def __init__(self, want_card=False):
        self.want_card = want_card
        self.pools = []

    def choices(self, pool, weights=None):
        self.pools.append([p.item_id for p in pool])
        cards = [p for p in pool if p.item_id in CARDS]
        if self.want_card and cards:
            return [cards[0]]
        return [next((p for p in pool if p.item_id not in CARDS), pool[0])]


class FixedRoll(random.Random):
    """A claw rng whose grab roll is fixed (random() -> value); everything else is seeded."""

    def __init__(self, value):
        super().__init__(3)
        self.value = value

    def random(self):
        return self.value


def play_claw(g, target_x):
    """One full attempt with the claw dropped straight over `target_x`."""
    assert g.start()
    g.x = float(target_x)
    g.drop()
    for _ in range(4000):
        g.update(DT)
        if g.phase == cm.IDLE:
            break
    return g.attempt


# ===================================================================== the symbols and the lock's combination
def mentions(text, word):
    """Is `word` in `text` as a whole word (so STARFALL is not STAR)?"""
    return re.search(r"\b" + word + r"\b", text.upper()) is not None


class SymbolTests(unittest.TestCase):
    def test_the_combination_is_star_moon_paw_in_numbered_order(self):
        self.assertEqual(fg.COMBINATION, ("STAR", "MOON", "PAW"))
        self.assertEqual(fg.LOCK_SLOTS, ("I", "II", "III"))
        self.assertEqual([(c, n, sym) for c, n, sym, _ in Q.CH2_SYMBOLS],
                         [("maze", "I", "STAR"), ("galaxy", "II", "MOON"), ("volley", "III", "PAW")])
        # each game's own symbol and numeral are the ones the lock and the Quest Log use
        self.assertEqual((corridor.SYMBOL, corridor.NUMERAL), ("STAR", "I"))
        self.assertEqual((quiet_signal.SYMBOL, quiet_signal.NUMERAL), ("MOON", "II"))
        self.assertEqual((old_ticket.SYMBOL, old_ticket.NUMERAL), ("PAW", "III"))

    def test_the_games_draw_the_same_pixels_as_the_lock(self):
        from symbol_art import SYMBOL_PIXELS
        self.assertEqual(SYMBOL_PIXELS["STAR"], corridor.STAR_PIXELS)
        self.assertEqual(SYMBOL_PIXELS["MOON"], quiet_signal.MOON_PIXELS)
        self.assertEqual(SYMBOL_PIXELS["PAW"], old_ticket.PAW_PIXELS)
        patterns = [SYMBOL_PIXELS[name] for name in fg.LOCK_CHOICES]
        self.assertEqual(len(set(patterns)), len(patterns))                  # every mark looks different
        for numeral, rows in ((1, corridor.NUMERAL_PIXELS), (2, quiet_signal.NUMERAL_PIXELS),
                              (3, old_ticket.NUMERAL_PIXELS)):
            self.assertEqual(sum(1 for ch in rows[2] if ch == "#"), numeral)   # I, II, III: one, two, three strokes

    def test_the_lock_offers_decoys(self):
        from symbol_art import SYMBOL_PIXELS
        self.assertTrue(set(fg.COMBINATION) <= set(fg.LOCK_CHOICES))
        decoys = set(fg.LOCK_CHOICES) - set(fg.COMBINATION)
        self.assertGreaterEqual(len(decoys), 4)
        self.assertTrue(set(fg.LOCK_CHOICES) <= set(SYMBOL_PIXELS))

    def test_only_star_moon_paw_in_that_order_opens_it(self):
        self.assertTrue(fg.is_combination(("STAR", "MOON", "PAW")))
        for marks in itertools.permutations(fg.COMBINATION):
            if marks != fg.COMBINATION:
                self.assertFalse(fg.is_combination(marks), marks)
        for marks in (("STAR", "MOON", "HEART"), ("PAW", "PAW", "PAW"), ("STAR", "MOON"), ("STAR", "MOON", "PAW", "KEY"),
                      (None, "MOON", "PAW"), ()):
            self.assertFalse(fg.is_combination(marks), marks)

    def test_no_text_ever_names_a_symbol_or_the_answer(self):
        lines = [l.text for l in fg.MIAO_HINT_LINES + fg.RECORD_INTRO] + list(fg.RECORD_LINES)
        lines += list(fg.WRONG_LINES) + [fg.UNSET_LINE, fg.RIGHT_LINE]
        lines += [ITEM_REGISTRY.get(c).description for c in CARDS] + [ITEM_REGISTRY.get(c).name for c in CARDS]
        lines += [q.objective for q in Q.QUESTS if q.chapter == 2] + [h for q in Q.QUESTS if q.chapter == 2 for h in q.hints]
        lines += [l.text for l in C.HINT_LINES + C.RACE_LINES]
        for text in lines:
            for word in ("STAR", "MOON", "PAW"):
                self.assertFalse(mentions(text, word), (word, text))

    def test_miao_says_exactly_the_requested_lines(self):
        self.assertEqual([l.text for l in fg.MIAO_HINT_LINES], [
            "Hey! Mochi was acting kinda weird earlier!",
            "She said she found something interesting at the Prize Counter.",
            "But when I asked her what it was, she just smiled!",
            "You should go talk to her!"])
        self.assertEqual({l.speaker for l in fg.MIAO_HINT_LINES}, {"MIAO MEOW"})

    def test_all_new_text_is_english_and_drawable(self):
        from font import _GLYPHS
        allowed = set(_GLYPHS) | {" "}
        texts = [l.text for l in fg.MIAO_HINT_LINES + fg.RECORD_INTRO] + list(fg.RECORD_LINES)
        texts += [fg.RECORD_TITLE, fg.RIGHT_LINE, fg.SOLVED_LINE, fg.UNSET_LINE, fg.UNUSUAL] + list(fg.WRONG_LINES)
        texts += list(fg.LOCK_PLATE) + ["PRIZE LOCK", "THE OLD LOCK IS STIFF. TURN THE WHEELS", "THE PRIZE LOCK IS OPEN"]
        texts += [old_ticket.HEADER] + list(fg.LOCK_CHOICES) + list(fg.LOCK_SLOTS)
        texts += [game for _, _, _, game in Q.CH2_SYMBOLS]
        texts += ["CHAPTER 02  THE FORGOTTEN GAMES", "RECOVERED SYMBOLS", "RIGHT: RECOVERED SYMBOLS",
                  "SYMBOLS YOU FIND ARE KEPT HERE.", "SECRET ITEM 02 FOUND", "NOT FOUND YET", "???"]
        for item in CARDS + ("claw_golden_cat",):
            d = ITEM_REGISTRY.get(item)
            texts += [d.name, d.description, d.use_hint]
        for text in texts:
            self.assertTrue(text.isascii(), text)
            for ch in text.upper():
                self.assertIn(ch, allowed, text)

    def test_the_record_fits_its_paper_one_line_each(self):
        from font import get_font
        from maintenance_note import PAPER
        self.assertLessEqual(19 + len(fg.RECORD_LINES) * 11, PAPER.h - 2)
        for line in fg.RECORD_LINES:
            self.assertLessEqual(get_font().size(line)[0], PAPER.w - 14, line)

    def test_kevin_is_never_named(self):
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(here)
        files = [os.path.join(here, f) for f in ("forgotten_games.py", "maintenance_note.py", "claw_lock.py", "symbol_art.py")] + [
            os.path.join(root, "neon_cat_maze", "corridor.py"), os.path.join(root, "galaxy_defender", "quiet_signal.py"),
            os.path.join(root, "pixel_volleyball", "old_ticket.py")]
        for path in files:
            with open(path, encoding="utf-8") as f:
                self.assertNotIn("kevin", f.read().lower(), path)


# ===================================================================== the story state
class StoryStateTests(unittest.TestCase):
    def manager(self, **kw):
        self.p = profile(**kw)
        return QuestManager(LocalSession(self.p))

    def test_nothing_of_chapter_two_is_recorded_before_trial_01(self):
        m = self.manager(chapter2=False)
        self.assertFalse(m.chapter_two_open)
        for clue in CH2_CLUES:
            m.handle(Q.CLUE_FOUND_EVENT, clue)
            m.handle(Q.CLUE_TRY_EVENT, clue)
        m.handle(Q.MIAO_CH2_HINT)
        m.handle(Q.CH2_RIDDLE_SOLVED)
        self.assertEqual(m.clues_found, 0)
        self.assertEqual([m.clue_tries(c) for c in CH2_CLUES], [0, 0, 0])
        self.assertFalse(m.riddle_solved)
        self.assertFalse(m.state["flags"].get(Q.MIAO_CH2_HINT))
        self.assertFalse(m.golden_cat_wanted)

    def test_trial_01_alone_without_the_reverse_gear_does_not_open_it(self):
        m = self.manager(chapter2=False)
        m.handle("secret_trial_done", "trial_01")        # (refused anyway: Chapter 01's item is missing)
        self.assertFalse(m.chapter_two_open)

    def test_clues_and_tries_are_recorded_in_chapter_two(self):
        m = self.manager()
        self.assertTrue(m.chapter_two_open)
        m.handle(Q.CLUE_TRY_EVENT, "maze")
        m.handle(Q.CLUE_TRY_EVENT, "maze")
        self.assertEqual(m.clue_tries("maze"), 2)
        m.handle(Q.CLUE_FOUND_EVENT, "maze")
        m.handle(Q.CLUE_TRY_EVENT, "maze")                # a found clue stops counting
        self.assertTrue(m.clue_found("maze"))
        self.assertEqual(m.clue_tries("maze"), 2)
        m.handle(Q.CLUE_FOUND_EVENT, "nowhere")           # unknown clues are ignored
        self.assertEqual(m.clues_found, 1)

    def test_the_persistence_route_opens_after_enough_tries(self):
        m = self.manager()
        for clue in CH2_CLUES:
            for i in range(CH2_TRIES_NEEDED[clue]):
                self.assertFalse(m.clue_route_open(clue), (clue, i))
                m.handle(Q.CLUE_TRY_EVENT, clue)
            self.assertTrue(m.clue_route_open(clue))
            self.assertFalse(m.clue_found(clue))           # the route only makes it appear: finding it is still to do

    def test_the_chosen_thresholds(self):
        self.assertEqual(corridor.ACE_LEVELS_CLEARED, 3)                  # COMPLETE level 3
        self.assertEqual(quiet_signal.ACE_WAVES_CLEARED, 10)              # CLEAR wave 10 (the second mothership)
        self.assertFalse(hasattr(old_ticket, "ACE_POINTS"))               # beat Sandra (a won match)
        self.assertEqual(CH2_TRIES_NEEDED, {"maze": 12, "galaxy": 12, "volley": 12})
        self.assertEqual((corridor.TRY_MIN_SCORE, quiet_signal.TRY_MIN_SCORE, old_ticket.TRY_MIN_POINTS), (600, 250, 1))

    def test_an_ace_route_is_kept_and_never_awards_the_symbol(self):
        m = self.manager()
        self.assertFalse(m.clue_route_open("galaxy"))
        m.handle(Q.CLUE_ROUTE_EVENT, "galaxy")
        self.assertTrue(m.clue_route_open("galaxy") and m.clue_due("galaxy"))
        self.assertEqual(m.clue_route("galaxy"), "ace")
        self.assertFalse(m.clue_found("galaxy"))                         # still to be found in the game
        self.assertEqual(m.clues_found, 0)
        m.handle(Q.CLUE_FOUND_EVENT, "galaxy")
        self.assertTrue(m.clue_route_open("galaxy"))
        self.assertFalse(m.clue_due("galaxy"))                           # found: the encounter stops coming

    def test_an_ace_route_survives_a_reload(self):
        m = self.manager()
        m.handle(Q.CLUE_ROUTE_EVENT, "maze")
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        path = os.path.join(folder, "p.json")
        ProfileStore(path).save(self.p)
        m2 = QuestManager(LocalSession(ProfileStore(path).load()))
        self.assertTrue(m2.clue_due("maze"))
        self.assertEqual(m2.clue_route("maze"), "ace")
        self.assertFalse(m2.clue_found("maze"))

    def test_no_route_is_kept_before_chapter_two(self):
        m = self.manager(chapter2=False)
        for clue in CH2_CLUES:
            m.handle(Q.CLUE_ROUTE_EVENT, clue)
        self.assertFalse(any(k.startswith("ch2_route") for k in self.p.story.get("flags", {})))

    def test_persistence_is_cumulative_across_sessions_and_a_win_does_not_reset_it(self):
        m = self.manager()
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        path = os.path.join(folder, "p.json")
        profile_now = self.p
        for session in range(3):                                          # three play sessions of four tries each
            for _ in range(4):
                m.handle(Q.CLUE_TRY_EVENT, "volley")
            ProfileStore(path).save(profile_now)
            profile_now = ProfileStore(path).load()
            m = QuestManager(LocalSession(profile_now))
            self.assertEqual(m.clue_tries("volley"), 4 * (session + 1))
        self.assertTrue(m.clue_route_open("volley"))
        self.assertEqual(m.clue_route("volley"), "persistence")

    def test_the_hint_and_the_record_wait_for_all_three(self):
        m = self.manager(clues=("maze", "galaxy"))
        self.assertFalse(m.miao_ch2_hint_due)
        m.handle(Q.CH2_RIDDLE_SOLVED)
        self.assertFalse(m.riddle_solved)
        m.handle(Q.CLUE_FOUND_EVENT, "volley")
        self.assertTrue(m.all_clues_found)
        self.assertTrue(m.miao_ch2_hint_due)
        m.handle(Q.MIAO_CH2_HINT)
        self.assertFalse(m.miao_ch2_hint_due)
        m.handle(Q.CH2_RIDDLE_SOLVED)
        self.assertTrue(m.riddle_solved and m.golden_cat_wanted)
        self.assertFalse(m.has_secret_item(Q.SECRET_ITEM_CLAW))      # the answer alone awards nothing

    def test_progress_persists_across_saves(self):
        m = self.manager()
        m.handle(Q.CLUE_FOUND_EVENT, "galaxy")
        m.handle(Q.CLUE_TRY_EVENT, "volley")
        m.set_card_pity(3)
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        path = os.path.join(folder, "p.json")
        ProfileStore(path).save(self.p)
        loaded = ProfileStore(path).load()
        m2 = QuestManager(LocalSession(loaded))
        self.assertTrue(m2.clue_found("galaxy"))
        self.assertFalse(m2.clue_found("maze"))
        self.assertEqual(m2.clue_tries("volley"), 1)
        self.assertEqual(m2.card_pity, 3)

    def test_symbol_iii_before_i_keeps_the_fixed_order(self):
        m = self.manager()
        self.assertEqual(m.recovered_symbols(), [("I", None, None), ("II", None, None), ("III", None, None)])
        m.handle(Q.CLUE_FOUND_EVENT, "volley")                       # III first
        self.assertEqual(m.recovered_symbols(), [("I", None, None), ("II", None, None),
                                                 ("III", "PAW", "CAT VOLLEYBALL")])
        m.handle(Q.CLUE_FOUND_EVENT, "maze")                         # then I
        self.assertEqual(m.recovered_symbols(), [("I", "STAR", "NEON CAT MAZE"), ("II", None, None),
                                                 ("III", "PAW", "CAT VOLLEYBALL")])
        self.assertEqual(m.clues_found, 2)
        self.assertEqual(self.p.story["stats"][Q.CH2_SYMBOLS_FOUND],
                         {"III": {"symbol": "PAW", "game": "CAT VOLLEYBALL"},
                          "I": {"symbol": "STAR", "game": "NEON CAT MAZE"}})

    def test_a_duplicate_discovery_does_not_count_twice(self):
        m = self.manager()
        fired = []
        m.on_change(fired.append)
        m.handle(Q.CLUE_FOUND_EVENT, "galaxy")
        m.handle(Q.CLUE_FOUND_EVENT, "galaxy")
        m.handle(Q.CLUE_FOUND_EVENT, "galaxy")
        self.assertEqual(m.clues_found, 1)
        self.assertEqual(fired.count("progress"), 1)                   # the tracker's count moved once
        self.assertEqual(list(self.p.story["stats"][Q.CH2_SYMBOLS_FOUND]), ["II"])

    def test_no_symbol_is_recorded_before_chapter_two(self):
        m = self.manager(chapter2=False)
        for clue in CH2_CLUES:
            m.handle(Q.CLUE_FOUND_EVENT, clue)
        self.assertEqual([s for _, s, _ in m.recovered_symbols()], [None, None, None])
        self.assertNotIn(Q.CH2_SYMBOLS_FOUND, self.p.story.get("stats", {}))

    def test_recovered_symbols_survive_save_and_load(self):
        m = self.manager()
        m.handle(Q.CLUE_FOUND_EVENT, "volley")
        m.handle(Q.CLUE_FOUND_EVENT, "galaxy")
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        path = os.path.join(folder, "p.json")
        ProfileStore(path).save(self.p)
        m2 = QuestManager(LocalSession(ProfileStore(path).load()))
        self.assertEqual(m2.recovered_symbols(), [("I", None, None), ("II", "MOON", "STARFALL ASSAULT"),
                                                  ("III", "PAW", "CAT VOLLEYBALL")])
        m2.handle(Q.CLUE_FOUND_EVENT, "maze")
        self.assertEqual(m2.clues_found, 3)
        self.assertFalse(m2.riddle_solved)                            # all three found: the lock is NOT opened for you

    def test_damaged_counters_read_as_zero(self):
        p = profile()
        data = p.story
        data["stats"][Q.CH2_TRIES] = {"maze": "lots", "galaxy": -4, "volley": True}
        data["stats"][Q.CH2_CARD_PITY] = "x"
        p.set_story(data)
        m = QuestManager(LocalSession(p))
        self.assertEqual([m.clue_tries(c) for c in CH2_CLUES], [0, 0, 0])
        self.assertEqual(m.card_pity, 0)

    def test_another_profile_keeps_its_own_story(self):
        a, b = profile("aa"), profile("bb")
        m = QuestManager(LocalSession(a))
        m.handle(Q.CLUE_FOUND_EVENT, "maze")
        self.assertTrue(a.story["flags"].get(CH2_CLUE_FLAGS["maze"]))
        self.assertFalse(b.story["flags"].get(CH2_CLUE_FLAGS["maze"]))


# ===================================================================== the hint cards
class HintCardTests(unittest.TestCase):
    def service(self, chapter2=True, rng=None, tickets=100000):
        self.p = profile(tickets=tickets, chapter2=chapter2)
        self.m = QuestManager(LocalSession(self.p))
        return CapsuleService(self.p, rng=rng or random.Random(4), bonus=fg.HintCardDraw(self.m))

    def test_cards_are_single_copy_collectibles_outside_the_machines_own_lists(self):
        for card in CARDS:
            d = ITEM_REGISTRY.get(card)
            self.assertEqual(d.category, COLLECTIBLE)
            self.assertFalse(d.stackable)
            for spec in CAPSULE_MACHINES.values():
                self.assertNotIn(card, [p.item_id for p in spec.prizes])
            self.assertNotIn(card, REDEEMABLE)                    # never on the Capsule Exchange

    def test_no_card_before_trial_01(self):
        svc = self.service(chapter2=False)
        self.assertEqual(svc.extras(CAT), [])
        for _ in range(150):
            for kind in (CAT, RETRO):
                self.assertNotIn(svc.pull(kind).item_id, CARDS)
        self.assertEqual(self.m.card_pity, 0)

    def test_cards_come_from_ordinary_pulls_of_both_machines(self):
        for kind in (CAT, RETRO):
            svc = self.service()
            self.assertEqual({p.item_id for p in svc.extras(kind)}, set(CARDS))
            got = [svc.pull(kind).item_id for _ in range(200)]
            self.assertEqual(set(CARDS) & set(got), set(CARDS), kind)
            self.assertEqual(sum(1 for i in got if i in CARDS), 3)          # each exactly once: no duplicates
            self.assertTrue(all(self.p.inventory.get_quantity(c) == 1 for c in CARDS))

    def test_a_card_pull_costs_the_normal_price_and_says_new(self):
        svc = self.service(rng=Picks(want_card=True), tickets=100)
        r = svc.pull(CAT)
        self.assertTrue(r.success)
        self.assertIn(r.item_id, CARDS)
        self.assertEqual((r.cost, self.p.tickets, r.duplicate, r.message), (15, 85, False, "NEW!"))

    def test_pity_gives_a_missing_card_after_four_misses(self):
        rng = Picks()
        svc = self.service(rng=rng)
        for i in range(fg.CARD_PITY_AFTER):
            self.assertNotIn(svc.pull(CAT).item_id, CARDS)
            self.assertEqual(self.m.card_pity, i + 1)
        r = svc.pull(CAT)                                             # the rng still "wants" no card: pity decides
        self.assertIn(r.item_id, CARDS)
        self.assertTrue(set(rng.pools[-1]) <= set(CARDS))
        self.assertEqual(self.m.card_pity, 0)

    def test_every_card_is_reached_within_fifteen_pulls_even_with_bad_luck(self):
        svc = self.service(rng=Picks())
        for _ in range(3 * (fg.CARD_PITY_AFTER + 1)):
            svc.pull(RETRO)
        self.assertTrue(all(self.p.inventory.has_item(c) for c in CARDS))

    def test_once_all_three_are_owned_the_machine_is_ordinary_again(self):
        svc = self.service()
        for c in CARDS:
            self.p.inventory.add_item(c)
        self.m.set_card_pity(2)
        self.assertEqual(svc.extras(CAT), [])
        for _ in range(40):
            self.assertNotIn(svc.pull(CAT).item_id, CARDS)
        self.assertEqual(self.m.card_pity, 2)                          # (no longer counted)

    def test_no_more_cards_once_the_golden_cat_is_won(self):
        svc = self.service()
        svc.profile.inventory.add_item(CARDS[0])
        m = svc.bonus.manager
        m.handle(Q.CLUE_FOUND_EVENT, "maze")
        m.state["stats"].setdefault("secret_items", []).append(Q.SECRET_ITEM_CLAW)
        self.assertTrue(m.has_secret_item(Q.SECRET_ITEM_CLAW))
        self.assertEqual(svc.bonus.missing(svc.profile), [])
        m.set_card_pity(9)
        self.assertFalse(svc.bonus.forced(svc, CAT))
        for _ in range(30):
            self.assertNotIn(svc.pull(CAT).item_id, CARDS[1:])
        self.assertTrue(svc.profile.inventory.has_item(CARDS[0]))     # (a card already owned is kept)

    def test_a_pull_with_the_bonus_is_still_one_save(self):
        svc = self.service(rng=Picks())
        saves = []
        self.p.subscribe_save(lambda: saves.append(1))
        svc.pull(CAT)
        self.assertEqual(len(saves), 1)

    def test_cards_are_rereadable_in_the_bag(self):
        for clue, card in fg.HINT_CARDS.items():
            d = ITEM_REGISTRY.get(card)
            self.assertTrue(d.description and d.use_hint)
        texts = " ".join(ITEM_REGISTRY.get(c).description for c in CARDS).upper()
        for route in ("CLEAR LEVEL 3", "CLEAR WAVE 10", "BEAT SANDRA", "KEEP COMING BACK"):
            self.assertIn(route, texts)

    def test_the_capsule_screen_uses_the_bonus_only_in_chapter_two(self):
        for chapter2 in (False, True):
            p = profile(tickets=500, chapter2=chapter2)
            game = Game(session=LocalSession(p))
            self.addCleanup(game.quit)
            scene = CapsuleScene(game, game.session.primary, CAT)
            ids = [d.id for d in scene.rows]
            self.assertEqual(set(CARDS) <= set(ids), chapter2)


# ===================================================================== the three clues: the games themselves
class MazeCorridorTests(unittest.TestCase):
    def walk(self, run, direction, steps=240):
        for _ in range(steps):
            run.steer(direction)
            run.update(DT)

    def ready_run(self):
        run = MazeRun(random.Random(1))
        run.phase, run.invulnerable = "run", 99.0
        for robot in run.robots:
            robot.release_in = 999.0
        return run

    def test_every_layout_has_a_solid_corner_wall_with_floor_behind_the_gate(self):
        from neon_cat_maze.mazes import MAZES
        for maze in MAZES:
            self.assertIn(corridor.GATE, maze.walls, maze.name)
            self.assertTrue(maze.is_open(corridor.ENTRANCE), maze.name)
            self.assertIn(corridor.ENTRANCE, maze.corners, maze.name)            # an optional corner, off the main paths

    def test_the_cat_must_push_into_the_crack_then_walks_to_the_end(self):
        run = self.ready_run()
        run.cat.place(corridor.ENTRANCE)
        self.walk(run, (-1, 0))
        self.assertEqual(run.cat.nearest_tile(), corridor.ENTRANCE)       # walled up: no way through
        run.open_corridor()
        self.assertFalse(run.corridor.revealed)                            # only a hairline crack so far
        self.assertEqual([e.name for e in run.take_events() if "corridor" in e.name], [])   # and nothing announced it
        self.walk(run, (-1, 0))
        self.assertTrue(run.corridor.revealed)
        self.assertEqual(run.cat.nearest_tile(), (-1, 1))
        self.walk(run, (0, 1))
        self.assertEqual(run.cat.nearest_tile(), corridor.END)
        self.assertTrue(run.corridor_found)
        names = [e.name for e in run.take_events()]
        self.assertEqual((names.count("corridor_revealed"), names.count("corridor_found")), (1, 1))

    def test_robots_never_enter_it(self):
        run = self.ready_run()
        run.open_corridor()
        run.cat.place(corridor.END)
        for robot in run.robots:
            robot.release_in = 0.0
        for _ in range(60 * 30):
            run.invulnerable = 99.0
            run.update(DT)
            for robot in run.robots:
                self.assertTrue(run.maze.is_open(robot.nearest_tile()))

    def game(self, enabled=True, ready=False):
        g = CatMazeGame(seed=2)
        g.secret_enabled, g.secret_ready = enabled, ready
        g.new_run()
        return g

    def clear_level(self, g):
        level = g.run.level
        g.run.fish.clear()                                            # eat everything: level clear
        g.run.phase, g.run.phase_time = "run", 0.0
        for _ in range(60 * 6):
            g.update(DT)
            if g.run.level == level + 1 and g.run.phase in ("ready", "run"):
                break
        g.update(DT)

    def test_off_by_default_and_when_disabled_even_after_three_clears(self):
        self.assertFalse(CatMazeGame().secret_enabled)
        g = self.game(enabled=False)
        g.run.levels_cleared = 3
        g.update(DT)
        self.assertIsNone(g.run.corridor)
        self.assertEqual(g.pop_secret_events(), [])

    def test_ace_route_needs_level_three_completed_not_reached(self):
        g = self.game()
        g.update(DT)
        self.clear_level(g)
        self.clear_level(g)
        self.assertEqual(g.run.level, 3)                                  # level 3 REACHED ...
        self.assertIsNone(g.run.corridor)                                 # ... is not enough
        self.assertEqual(g.pop_secret_events(), [])
        self.clear_level(g)                                               # level 3 COMPLETED
        self.assertEqual(g.run.levels_cleared, 3)
        self.assertEqual(g.pop_secret_events(), ["unlocked"])
        self.assertIsNotNone(g.run.corridor)                              # there from level 4 on in this run ...
        self.assertFalse(g.run.corridor.revealed)                         # ... still to be found
        self.assertFalse(g.run.corridor_found)
        self.clear_level(g)
        self.assertEqual(g.pop_secret_events(), [])                       # reported once

    def test_a_route_earned_before_opens_it_from_level_one(self):
        g = self.game(ready=True)
        g.update(DT)
        self.assertIsNotNone(g.run.corridor)
        self.assertFalse(g.run.corridor.revealed)

    def test_the_ace_route_is_not_reported_again_once_kept(self):
        g = self.game(ready=True)
        g.run.levels_cleared = 3
        g.update(DT)
        self.assertEqual(g.pop_secret_events(), [])

    def test_a_real_game_over_is_reported_as_a_try_once(self):
        g = self.game()
        g.run.score, g.run.lives = corridor.TRY_MIN_SCORE, 0
        g.run.phase, g.run.phase_time = "dying", 99.0
        for _ in range(10):
            g.update(DT)
        self.assertEqual(g.pop_secret_events(), ["try"])
        for _ in range(10):
            g.update(DT)
        self.assertEqual(g.pop_secret_events(), [])

    def test_a_short_run_is_not_a_try(self):
        g = self.game()
        g.run.score, g.run.lives = corridor.TRY_MIN_SCORE - 10, 0
        g.run.phase, g.run.phase_time = "dying", 99.0
        for _ in range(10):
            g.update(DT)
        self.assertEqual(g.pop_secret_events(), [])

    def test_a_restart_or_a_quit_is_not_a_try(self):
        g = self.game()
        g.run.score = corridor.TRY_MIN_SCORE * 3
        g.pause()
        g.act("down")
        g.act("confirm")                                                  # PAUSED > RESTART
        g.update(DT)
        g.run.score = corridor.TRY_MIN_SCORE * 3
        g.leave()                                                         # RETURN TO LOBBY mid-run
        g.update(DT)
        self.assertEqual(g.pop_secret_events(), [])

    def test_the_star_i_lights_up_only_when_the_cat_reaches_the_end(self):
        g = self.game(ready=True)
        g.update(DT)
        run = g.run
        run.phase, run.invulnerable = "run", 99.0
        plaque = g.renderer.plaque_rect()
        tip = (plaque.x + 2 + 4, plaque.y + 3)                            # the star's tip
        surf = pygame.Surface((400, 300))
        run.corridor.revealed = True
        g.draw(surf)
        dim = surf.get_at(tip)[:3]
        self.assertFalse(g.renderer.corridor_mark(run))
        run.cat.place(corridor.END)
        g.update(DT)
        self.assertEqual(g.pop_secret_events(), ["found"])
        self.assertTrue(run.corridor.found)
        self.assertTrue(g.renderer.corridor_mark(run))                    # big STAR I in the strip below the maze
        g.draw(surf)
        lit = surf.get_at(tip)[:3]
        self.assertGreater(lit[0], 180)                                    # gold now ...
        self.assertLess(dim[0], 100)                                       # ... dusty before

    def test_before_it_is_found_only_a_faint_crack_shows(self):
        from neon_cat_maze.rendering import OX, OY, TILE
        g = self.game(ready=True)
        g.update(DT)
        surf = pygame.Surface((400, 300))
        g.draw(surf)
        hidden = surf.get_at((OX - TILE + 8, OY + 3 * TILE + 8))[:3]      # a passage tile, still unseen
        g.run.corridor.revealed = True
        g.draw(surf)
        self.assertNotEqual(surf.get_at((OX - TILE + 8, OY + 3 * TILE + 8))[:3], hidden)


class GalaxySignalTests(unittest.TestCase):
    def game(self, enabled=True, ready=False):
        g = GalaxyGame(rng=random.Random(5))
        g.secret_enabled, g.secret_ready = enabled, ready
        g.new_run()
        return g

    def tune(self, g, frames=60 * 12):
        for _ in range(frames):
            if g.run.signal is not None:
                g.run.x = min(max(g.run.signal.x, 11), 389)
            g.update(DT)
            if g.run.signal_received:
                return True
        return False

    def calm(self, g, wave):
        """Jump to the calm before `wave` (every earlier wave counted as cleared)."""
        g.run.enemies.clear()
        g.run.boss = None
        g.run.wave, g.run.waves_cleared, g.run.banner = wave, wave - 1, 2.0
        g.update(DT)

    def test_off_by_default_and_when_disabled(self):
        self.assertFalse(GalaxyGame().secret_enabled)
        g = self.game(enabled=False)
        self.calm(g, 11)
        self.assertIsNone(g.run.signal)
        self.assertEqual(g.pop_secret_events(), [])

    def test_ace_route_needs_wave_ten_cleared(self):
        g = self.game()
        g.update(DT)
        self.assertIsNone(g.run.signal)                                   # the calm before wave 1: no ship by skill
        self.calm(g, 10)                                                  # wave 10 (the second mothership) REACHED
        self.assertIsNone(g.run.signal)
        self.assertEqual(g.pop_secret_events(), [])
        self.calm(g, 11)                                                  # wave 10 CLEARED
        self.assertEqual(g.pop_secret_events(), ["unlocked"])
        self.assertIsNotNone(g.run.signal)

    def test_it_returns_every_calm_until_tuned_in_and_the_wave_always_comes(self):
        g = self.game(ready=True)
        g.update(DT)
        for wave in (1, 2, 3):
            if wave > 1:
                self.calm(g, wave)
            self.assertIsNotNone(g.run.signal, wave)
            g.run.x = 11 if g.run.signal.dir > 0 else 389                 # stay away from the beam
            for _ in range(60 * 20):                                      # it crosses and leaves (never stops) ...
                g.run.x = 11 if (g.run.signal is None or g.run.signal.x > 200) else 389
                g.update(DT)
                if not g.run.banner_active:
                    break
            self.assertFalse(g.run.banner_active, wave)                   # ... and the wave starts after it: no soft-lock
            self.assertFalse(g.run.signal_received)
        self.calm(g, 4)
        self.assertTrue(self.tune(g))
        self.assertEqual(g.pop_secret_events(), ["found"])
        for _ in range(60 * 20):                                          # it shows its hologram until it has left
            g.update(DT)
            if g.run.signal is None:
                break
        self.calm(g, 5)
        self.assertIsNone(g.run.signal)                                   # tuned in: it does not come back this run

    def test_a_later_game_brings_it_back(self):
        g = self.game(ready=True)
        g.update(DT)
        g.run._end("hp")                                                  # missed it: game over
        g.update(DT)
        g.new_run()
        g.update(DT)
        self.assertIsNotNone(g.run.signal)

    def test_the_wave_waits_and_tuning_in_is_the_discovery(self):
        g = self.game(ready=True)
        g.update(DT)
        banner = g.run.banner
        self.assertTrue(self.tune(g))
        self.assertEqual(g.run.wave, 1)
        self.assertEqual(g.run.banner, banner)                         # held while the ship crosses
        self.assertEqual(g.pop_secret_events(), ["found"])
        self.assertTrue(g.run.signal.projecting)                       # the MOON II hologram above the ship
        g.draw(pygame.Surface((400, 300)))

    def test_no_hologram_before_tuning_in(self):
        g = self.game(ready=True)
        g.update(DT)
        self.assertIsNotNone(g.run.signal)
        self.assertFalse(g.run.signal.projecting)

    def test_it_is_not_hostile_and_cannot_be_shot(self):
        g = self.game(ready=True)
        g.update(DT)
        hp, score = g.run.hp, g.run.score
        for _ in range(60 * 4):
            g.run.x = g.run.signal.x if g.run.signal else g.run.x
            g.update(DT, fire=True)
        self.assertEqual((g.run.hp, g.run.score), (hp, score))
        self.assertFalse(g.run.enemy_bolts)

    def test_a_real_game_over_is_reported_as_a_try(self):
        g = self.game()
        g.run.score = quiet_signal.TRY_MIN_SCORE
        g.run._end("hp")
        g.update(DT)
        self.assertEqual(g.pop_secret_events(), ["try"])
        g2 = self.game()
        g2.run.score = quiet_signal.TRY_MIN_SCORE - 1
        g2.run._end("hp")
        g2.update(DT)
        self.assertEqual(g2.pop_secret_events(), [])

    def test_a_restart_or_a_quit_is_not_a_try(self):
        g = self.game()
        g.run.score = quiet_signal.TRY_MIN_SCORE * 3
        g.pause()
        g.act("down")
        g.act("confirm")                                                  # PAUSED > RESTART
        g.update(DT)
        g.run.score = quiet_signal.TRY_MIN_SCORE * 3
        g.leave()
        g.update(DT)
        self.assertEqual(g.pop_secret_events(), [])


class VolleyTicketTests(unittest.TestCase):
    def game(self, enabled=True, ready=False):
        g = VolleyGame()
        g.secret_enabled, g.secret_ready = enabled, ready
        g.match.start()
        return g

    def finish(self, g, mine, sandra, winner):
        g.match.points = [mine, sandra]
        g.match.award_point(winner)
        self.assertEqual(g.match.state, MatchState.FINISHED)
        g.update(DT)

    def play_ticket(self, g, seconds=None):
        for _ in range(int((seconds or old_ticket.TOTAL_SECONDS + 0.2) / DT)):
            g.update(DT)

    def test_off_by_default_and_when_disabled(self):
        self.assertFalse(VolleyGame().secret_enabled)
        g = self.game(enabled=False)
        self.finish(g, 4, 0, 0)
        self.assertIsNone(g.ticket)
        self.assertEqual(g.pop_secret_events(), [])

    def test_never_during_a_match_even_when_due(self):
        g = self.game(ready=True)
        for points in ([0, 0], [3, 2], [4, 4]):
            g.match.points = list(points)
            g.update(DT)
            self.assertIsNone(g.ticket)

    def test_ace_route_beating_sandra(self):
        g = self.game()
        self.finish(g, 4, 3, 0)                                          # 5:3, a win
        self.assertEqual(g.pop_secret_events(), ["unlocked"])
        self.assertIsNotNone(g.ticket)                                   # its scene starts right after the winning point

    def test_after_a_due_route_it_comes_after_a_lost_match_too(self):
        g = self.game(ready=True)
        self.finish(g, 0, 4, 1)
        self.assertIsNotNone(g.ticket)

    def test_the_ticket_scene_is_short_then_the_result_card(self):
        self.assertLessEqual(old_ticket.TOTAL_SECONDS, 3.0)
        g = self.game(ready=True)
        self.finish(g, 2, 4, 1)
        score = list(g.match.points)
        self.assertTrue(g.ticket_playing)
        g.confirm()                                                      # no rematch in the middle of it
        self.assertEqual(g.match.state, MatchState.FINISHED)
        self.play_ticket(g, old_ticket.FLY_SECONDS + 0.05)
        self.assertTrue(g.ticket.found)                                  # it reached the cat's paws: the discovery
        self.assertEqual(g.pop_secret_events(), ["try", "found"])
        self.assertTrue(g.ticket_playing)                                # still held up large ...
        self.play_ticket(g)
        self.assertFalse(g.ticket_playing)                               # ... then pinned, and the result card is back
        self.assertEqual(g.ticket.phase, "pinned")
        self.assertEqual(g.match.points, score)                          # nothing of the match changed
        surf = pygame.Surface((400, 300))
        g.draw(surf)
        # the pinned stub over the stands shows its PAW print (ink on paper) and the III beside it
        paw = next((x, y) for y, row in enumerate(old_ticket.PAW_PIXELS) for x, ch in enumerate(row) if ch == "#")
        px, py = old_ticket.PAW_AT
        nx, ny = old_ticket.NUMERAL_AT
        self.assertEqual(surf.get_at((26 + px + paw[0] * 2, 50 + py + paw[1] * 2))[:3], (110, 80, 50))
        self.assertEqual(surf.get_at((26 + nx, 50 + ny))[:3], (110, 80, 50))
        g.confirm()                                                      # and a rematch works as usual
        self.assertEqual(g.match.state, MatchState.PLAYING)

    def test_every_phase_draws(self):
        g = self.game(ready=True)
        self.finish(g, 4, 1, 0)
        surf = pygame.Surface((400, 300))
        seen = set()
        for _ in range(int((old_ticket.TOTAL_SECONDS + 0.3) / DT)):
            g.update(DT)
            seen.add(g.ticket.phase)
            g.draw(surf)
        self.assertEqual(seen, {"fly", "show", "settle", "pinned"})

    def test_leaving_before_it_arrives_brings_it_back_after_the_next_match(self):
        g = self.game(ready=True)
        self.finish(g, 1, 4, 1)
        self.assertFalse(g.ticket.found)
        g2 = VolleyGame()                                                # (left the machine: a new game later)
        g2.secret_enabled, g2.secret_ready = True, True
        g2.match.start()
        g2.match.points = [0, 4]
        g2.match.award_point(1)
        g2.update(DT)
        self.assertIsNotNone(g2.ticket)

    def test_found_once_never_again(self):
        g = self.game(ready=True)
        g.secret_found = True
        self.finish(g, 4, 0, 0)
        self.assertIsNone(g.ticket)

    def test_a_lost_match_with_a_point_is_a_try_and_a_win_is_not(self):
        g = self.game()
        self.finish(g, old_ticket.TRY_MIN_POINTS, 4, 1)
        self.assertEqual(g.pop_secret_events(), ["try"])
        g = self.game()
        self.finish(g, 4, 0, 0)
        self.assertNotIn("try", g.pop_secret_events())
        g = self.game()
        self.finish(g, 0, 4, 1)                                          # a 0 point loss is not a real try
        self.assertEqual(g.pop_secret_events(), [])

    def test_a_restarted_match_is_not_a_try(self):  # (BACKSPACE before the final point)
        g = self.game()
        g.match.points = [3, 4]
        g.update(DT)
        g.restart()                                                      # BACKSPACE RESTART before the end
        g.update(DT)
        self.assertEqual(g.pop_secret_events(), [])


# ===================================================================== the hub: games, Miao, Mochi, the claw
class HubBase(unittest.TestCase):
    story_kw = {}

    def setUp(self):
        self.p = profile(tokens=40, tickets=200, **self.story_kw)
        self.p.claim_daily_reward()                                  # (no daily bonus card over the rooms)
        self.other = profile("bob")
        self.game = Game(session=LocalSession(self.p))
        self.addCleanup(self.game.quit)
        self.story = self.game.hub.story
        self.m = self.story.manager

    def frames(self, n=1, events=()):
        for i in range(n):
            self.game.step(list(events) if i == 0 else [], DT)

    def start_machine(self, machine_id, cls):
        room = goto_room(self.game, "arcade_floor")
        machine = next(m for m in room.machines if m.id == machine_id)
        room._start_game(machine, player=room.players[0])
        self.frames(30)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, cls)
        return room, scene


class MinigameLinkTests(HubBase):
    def test_before_chapter_two_the_games_have_no_secret(self):
        self.p.set_story(story(chapter2=False))
        self.m = QuestManager(LocalSession(self.p))
        self.game.hub.story.manager.close()
        self.game.hub.story.manager = self.m
        for machine_id, cls, attr in (("puzzle_drop", CatMazeScene, "cat_maze"),
                                      ("galaxy_defender", GalaxyDefenderScene, "galaxy"),
                                      ("pixel_volleyball", PixelVolleyballScene, "volley")):
            room, scene = self.start_machine(machine_id, cls)
            self.frames(2)
            self.assertFalse(getattr(scene, attr).secret_enabled, machine_id)
            getattr(scene, attr).secret_events.append("found")       # even a stray report records nothing
            self.frames(2)
            scene.leaving = True
            self.game.scenes.pop()
            self.frames(40)
        self.assertEqual(self.m.clues_found, 0)

    def test_the_maze_reports_its_corridor_to_the_story(self):
        room, scene = self.start_machine("puzzle_drop", CatMazeScene)
        self.frames(1, [key(K.K_RETURN)])
        self.assertTrue(scene.cat_maze.secret_enabled)
        self.assertFalse(scene.cat_maze.secret_ready)
        run = scene.cat_maze.run
        run.open_corridor()
        run.cat.place(corridor.END)
        run.phase, run.invulnerable = "run", 99.0
        self.frames(3)
        self.assertTrue(self.m.clue_found("maze"))
        self.assertTrue(self.p.story["flags"][CH2_CLUE_FLAGS["maze"]])
        self.assertFalse(self.other.story["flags"].get(CH2_CLUE_FLAGS["maze"]))     # single player: Bob untouched

    def test_galaxy_tries_count_up_to_the_persistence_route(self):
        room, scene = self.start_machine("galaxy_defender", GalaxyDefenderScene)
        for i in range(CH2_TRIES_NEEDED["galaxy"]):
            self.frames(1, [key(K.K_RETURN)])                        # START / RETRY
            self.assertEqual(scene.galaxy.screen, GScreen.PLAYING)
            self.assertFalse(scene.galaxy.secret_ready)
            scene.galaxy.run.score = quiet_signal.TRY_MIN_SCORE
            scene.galaxy.run._end("hp")
            self.frames(2)
            self.assertEqual(self.m.clue_tries("galaxy"), i + 1)
        self.frames(1, [key(K.K_RETURN)])
        self.frames(2)
        self.assertTrue(scene.galaxy.secret_ready)
        self.assertIsNotNone(scene.galaxy.run.signal)               # it crosses before wave 1 now
        run = scene.galaxy.run
        for _ in range(60 * 12):
            if run.signal is not None:
                run.x = min(max(run.signal.x, 11), 389)
            self.frames(1)
            if self.m.clue_found("galaxy"):
                break
        self.assertTrue(self.m.clue_found("galaxy"))

    def test_volleyball_ace_route_records_the_ticket(self):
        room, scene = self.start_machine("pixel_volleyball", PixelVolleyballScene)
        self.frames(1, [key(K.K_e)])
        volley = scene.volley
        self.assertEqual(volley.match.state, MatchState.PLAYING)
        volley.match.points = [4, 2]
        volley.match.award_point(0)                                    # the winning point
        self.frames(3)
        self.assertTrue(self.m.clue_route_open("volley"))              # the win is kept ...
        self.assertTrue(volley.ticket_playing)                         # ... and the ticket scene plays
        self.frames(int(old_ticket.TOTAL_SECONDS / DT) + 10)
        self.assertTrue(self.m.clue_found("volley"))
        self.assertFalse(volley.ticket_playing)

    def test_an_ace_route_survives_leaving_the_game(self):
        room, scene = self.start_machine("puzzle_drop", CatMazeScene)
        self.frames(1, [key(K.K_RETURN)])
        scene.cat_maze.run.levels_cleared = 3                         # level 3 completed in this run
        self.frames(3)
        self.assertTrue(self.m.clue_route_open("maze"))
        scene.leaving = True
        self.game.scenes.pop()
        self.frames(40)
        room, scene = self.start_machine("puzzle_drop", CatMazeScene)  # a new game, later
        self.frames(1, [key(K.K_RETURN)])
        self.frames(3)
        self.assertTrue(scene.cat_maze.secret_ready)
        self.assertIsNotNone(scene.cat_maze.run.corridor)              # there from level 1, still to be found
        self.assertFalse(scene.cat_maze.run.corridor.revealed)
        self.assertFalse(self.m.clue_found("maze"))

    def test_a_found_secret_is_not_offered_again(self):
        self.m.handle(Q.CLUE_FOUND_EVENT, "galaxy")
        room, scene = self.start_machine("galaxy_defender", GalaxyDefenderScene)
        self.frames(1, [key(K.K_RETURN)])
        self.frames(3)
        self.assertFalse(scene.galaxy.secret_ready)
        self.assertIsNone(scene.galaxy.run.signal)


class MiaoHintTests(HubBase):
    story_kw = {"clues": ("maze", "galaxy", "volley")}

    def back_in(self, room_id="home", wait=120):
        room = goto_room(self.game, room_id)
        self.frames(5)
        room.popup = None                                           # (the daily bonus card: the talk waits for it)
        self.frames(wait)
        return room

    def read_to_end(self):
        for _ in range(40):
            if self.story.dialogue is None:
                return
            self.frames(1, [key(K.K_e)])
            self.frames(2)

    def test_it_plays_once_when_back_in_the_hub(self):
        self.back_in()
        self.assertIsNotNone(self.story.dialogue)
        self.assertEqual([l.text for l in self.story.dialogue.lines], [l.text for l in fg.MIAO_HINT_LINES])
        self.read_to_end()
        self.assertIsNone(self.story.dialogue)
        self.assertTrue(self.m.state["flags"].get(Q.MIAO_CH2_HINT))
        self.assertTrue(self.p.story["flags"].get(Q.MIAO_CH2_HINT))
        for room_id in ("arcade_floor", "prize_plaza", "home"):
            self.back_in(room_id)
            self.assertIsNone(self.story.dialogue, room_id)

    def test_a_talk_cut_short_is_told_again(self):
        self.back_in()
        self.assertIsNotNone(self.story.dialogue)
        self.story.dialogue.closed = True                            # (closed some other way, not read to the end)
        self.frames(2)
        self.assertFalse(self.m.state["flags"].get(Q.MIAO_CH2_HINT))
        self.back_in("arcade_floor")
        self.assertIsNotNone(self.story.dialogue)


class MiaoHintGateTests(HubBase):
    story_kw = {"clues": ("maze", "galaxy")}

    def test_two_clues_are_not_enough(self):
        room = goto_room(self.game, "home")
        self.frames(5)
        room.popup = None
        self.frames(200)
        self.assertIsNone(self.story.dialogue)
        self.m.handle(Q.CLUE_FOUND_EVENT, "volley")
        self.frames(120)
        self.assertIsNotNone(self.story.dialogue)


class MochiRecordTests(HubBase):
    story_kw = {"clues": ("maze", "galaxy", "volley"), "hint_told": True}

    def chat(self):
        scene = MochiChatScene(self.game, self.game.session.primary)
        self.game.scenes.push(scene)
        self.frames(30)
        return scene

    def open_record(self):
        chat = self.chat()
        keys = [k for _l, k in chat.options]
        self.assertIn("unusual", keys)
        chat.start("unusual")
        for _ in range(30):
            if chat.talk is None:
                break
            chat.talk.handle_event(key(K.K_e))
            chat.talk.handle_event(key(K.K_e))
        self.frames(40)
        note = self.game.scenes.current
        self.assertIsInstance(note, MaintenanceNoteScene)
        return note

    def test_the_option_needs_all_three_clues(self):
        self.assertEqual(C.chat_options("found", C.has_record(self.m))[-1], (fg.UNUSUAL, "unusual"))
        p = profile("two", clues=("maze", "volley"))
        m2 = QuestManager(LocalSession(p))
        self.assertFalse(C.has_record(m2))
        self.assertNotIn("unusual", [k for _l, k in C.chat_options(m2.mochi_story_stage, C.has_record(m2))])
        p3 = profile("pre", chapter2=False, clues=("maze", "galaxy", "volley"))
        m3 = QuestManager(LocalSession(p3))
        self.assertFalse(C.has_record(m3))                             # (stray flags before Chapter 02: still no)

    def test_mochi_points_to_the_claw_machine_and_the_record_has_no_lock(self):
        self.assertTrue(any("claw machine" in l.text.lower() for l in fg.RECORD_INTRO))
        note = self.open_record()
        self.assertFalse(hasattr(note, "wheels"))                      # read only: the lock is on the claw machine
        note.draw(pygame.Surface((400, 300)))
        self.frames(1, [key(K.K_ESCAPE)])
        self.frames(30)
        self.assertNotIsInstance(self.game.scenes.current, MaintenanceNoteScene)
        self.assertFalse(self.m.riddle_solved)


class ClawLockTests(HubBase):
    story_kw = {"clues": ("maze", "galaxy", "volley"), "hint_told": True}

    def claw(self):
        room = goto_room(self.game, "prize_plaza")
        room.popup = None
        scene = ClawScene(self.game, self.game.session.primary)
        self.game.scenes.push(scene)
        self.frames(40)
        self.assertIs(self.game.scenes.current, scene)
        return scene

    def open_lock(self):
        claw = self.claw()
        self.assertTrue(claw.lock_waiting)
        self.assertIn("PRIZE LOCK", [what for _k, what in claw.controls_lines()])
        self.frames(1, [key(K.K_w)])
        self.frames(30)
        lock = self.game.scenes.current
        self.assertIsInstance(lock, ClawLockScene)
        return claw, lock

    def set_lock(self, lock, marks):
        """Turn the wheels with real key presses (LEFT/RIGHT picks a wheel, DOWN turns it) to `marks`, then press E."""
        for i, mark in enumerate(marks):
            while lock.cursor != i:
                self.frames(1, [key(K.K_RIGHT)])
            for _ in range(len(fg.LOCK_CHOICES) + 1):
                if lock.marks[i] == mark:
                    break
                self.frames(1, [key(K.K_DOWN)])
            self.assertEqual(lock.marks[i], mark)
        self.frames(1, [key(K.K_e)])
        self.frames(1)

    def test_the_lock_starts_empty_even_with_all_three_recovered(self):
        claw, lock = self.open_lock()
        self.assertTrue(lock.can_answer)
        self.assertEqual(lock.marks, [None, None, None])               # nothing filled in from the Quest Log
        self.assertFalse(self.m.riddle_solved)
        self.frames(1, [key(K.K_e)])
        self.assertEqual(lock.reply, fg.UNSET_LINE)
        self.assertFalse(self.m.riddle_solved)
        lock.draw(pygame.Surface((400, 300)))

    def test_q_shows_the_recovered_symbols_and_fills_nothing_in(self):
        claw, lock = self.open_lock()
        self.frames(1, [key(K.K_q)])
        self.assertIsNotNone(lock.log)
        self.assertEqual(lock.log.pages[lock.log.page], "CHAPTER 02")
        self.assertEqual([r[1] for r in lock.log.symbol_rows()], ["STAR", "MOON", "PAW"])
        lock.draw(pygame.Surface((400, 300)))
        self.frames(1, [key(K.K_DOWN)])                                # keys go to the log, not the wheels
        self.assertEqual(lock.marks, [None, None, None])
        self.frames(1, [key(K.K_q)])
        self.assertIsNone(lock.log)
        self.assertIs(self.game.scenes.current, lock)

    def test_the_wheels_turn_through_every_mark_and_back(self):
        claw, lock = self.open_lock()
        seen = []
        for _ in range(len(fg.LOCK_CHOICES)):
            self.frames(1, [key(K.K_DOWN)])
            seen.append(lock.marks[0])
        self.assertEqual(seen, list(fg.LOCK_CHOICES))
        self.frames(1, [key(K.K_DOWN)])
        self.assertEqual(lock.marks[0], fg.LOCK_CHOICES[0])            # it wraps round
        self.frames(1, [key(K.K_UP)])
        self.assertEqual(lock.marks[0], fg.LOCK_CHOICES[-1])
        self.frames(1, [key(K.K_LEFT)])
        self.assertEqual(lock.cursor, 2)                               # LEFT from wheel I goes round to III

    def test_wrong_combinations_are_gentle_and_retryable(self):
        claw, lock = self.open_lock()
        tokens, tickets = self.p.tokens, self.p.tickets
        for marks in (("MOON", "STAR", "PAW"), ("PAW", "MOON", "STAR"), ("STAR", "MOON", "HEART")):
            self.set_lock(lock, marks)
            self.assertFalse(self.m.riddle_solved)
            self.assertIn(lock.reply, fg.WRONG_LINES)
            self.assertEqual(lock.marks, list(marks))                  # the wheels stay where they were
            self.assertTrue(lock.can_answer)
        self.assertEqual((self.p.tokens, self.p.tickets), (tokens, tickets))
        self.assertIs(self.game.scenes.current, lock)
        self.set_lock(lock, fg.COMBINATION)
        self.assertTrue(self.m.riddle_solved)

    def test_star_moon_paw_opens_it_and_the_golden_cat_drops_in(self):
        claw, lock = self.open_lock()
        self.assertFalse(any(p.spec is fg.GOLDEN_CAT for p in claw.claw.plushies))
        self.set_lock(lock, ("STAR", "MOON", "PAW"))
        self.assertTrue(self.m.riddle_solved and self.m.golden_cat_wanted)
        self.assertEqual(lock.reply, fg.RIGHT_LINE)
        self.assertFalse(self.m.has_secret_item(Q.SECRET_ITEM_CLAW))   # no item for the lock itself
        lock.draw(pygame.Surface((400, 300)))
        self.frames(int(2.4 / DT))                                     # a moment, then back to the claw machine
        self.assertIs(self.game.scenes.current, claw)
        self.assertTrue(any(p.spec is fg.GOLDEN_CAT for p in claw.claw.plushies))
        self.assertIsNotNone(claw.claw.special)
        self.assertFalse(claw.lock_waiting)
        self.assertNotIn("PRIZE LOCK", [what for _k, what in claw.controls_lines()])
        self.assertFalse(self.p.inventory.has_item("claw_golden_cat"))

    def test_escape_from_the_lock_leaves_the_claw_playable(self):
        claw, lock = self.open_lock()
        self.frames(1, [key(K.K_ESCAPE)])
        self.frames(30)
        self.assertIs(self.game.scenes.current, claw)
        self.assertTrue(claw.press())                                  # ordinary play: pay and start
        self.assertEqual(claw.claw.phase, cm.AIM)


class ClawLockGateTests(HubBase):
    story_kw = {"clues": ("maze", "galaxy")}

    def test_no_lock_before_all_three(self):
        room = goto_room(self.game, "prize_plaza")
        room.popup = None
        claw = ClawScene(self.game, self.game.session.primary)
        self.game.scenes.push(claw)
        self.frames(40)
        self.assertFalse(claw.lock_waiting)
        self.frames(1, [key(K.K_w)])
        self.frames(20)
        self.assertIs(self.game.scenes.current, claw)
        lock = ClawLockScene(self.game, self.game.session.primary)
        self.assertFalse(lock.can_answer)
        lock.set_marks(fg.COMBINATION)
        self.assertFalse(lock.submit())
        self.assertFalse(self.m.riddle_solved)


class GoldenCatTests(HubBase):
    story_kw = {"clues": ("maze", "galaxy", "volley"), "hint_told": True, "solved": True}

    def claw_scene(self):
        room = goto_room(self.game, "prize_plaza")
        room.popup = None
        return ClawScene(self.game, self.game.session.primary)

    def golden(self, g):
        return next((p for p in g.plushies if p.spec is fg.GOLDEN_CAT), None)

    def test_it_waits_in_the_machine_after_the_answer(self):
        g = self.claw_scene().claw
        cat = self.golden(g)
        self.assertIsNotNone(cat)
        self.assertEqual(cat.slot, fg.GOLDEN_SLOT)
        self.assertEqual(sum(1 for p in g.plushies if p.spec is fg.GOLDEN_CAT), 1)
        self.assertEqual(len(g.plushies), len(cm.SLOTS))

    def test_a_slip_awards_nothing_and_a_real_win_awards_secret_item_02_once(self):
        scene = self.claw_scene()
        g = scene.claw
        g.rng = FixedRoll(0.999)                                        # every roll fails ...
        cat = self.golden(g)
        play_claw(g, cat.x)
        self.assertFalse(self.m.has_secret_item(Q.SECRET_ITEM_CLAW))
        self.assertEqual(self.m.golden_misses, 1)
        self.assertIsNotNone(self.golden(g))                             # it is still there
        g.rng = FixedRoll(0.0)                                          # ... until one holds
        play_claw(g, self.golden(g).x)
        self.assertTrue(self.m.has_secret_item(Q.SECRET_ITEM_CLAW))
        self.assertEqual(self.m.state["stats"]["secret_items"].count(Q.SECRET_ITEM_CLAW), 1)
        self.assertEqual(self.p.inventory.get_quantity("claw_golden_cat"), 1)
        self.assertIsNone(self.golden(g))                                # restocked with an ordinary plushie
        for _ in range(3):
            play_claw(g, cm.SLOTS[fg.GOLDEN_SLOT])
        self.assertEqual(self.m.state["stats"]["secret_items"].count(Q.SECRET_ITEM_CLAW), 1)
        self.assertEqual(self.p.inventory.get_quantity("claw_golden_cat"), 1)
        again = self.claw_scene().claw
        self.assertIsNone(again.special)                                 # owned: the machine is ordinary again
        self.assertIsNone(self.golden(again))

    def test_bad_luck_cannot_last(self):
        g = self.claw_scene().claw
        g.rng = FixedRoll(0.999)                                       # the worst luck there is
        edge = fg.GOLDEN_CAT.width / 2 + 2                             # a prong only just catching its side
        odds = []
        for _ in range(fg.GOLDEN_SURE_AFTER):
            odds.append(play_claw(g, self.golden(g).x + edge).odds)
        self.assertFalse(self.m.has_secret_item(Q.SECRET_ITEM_CLAW))
        self.assertEqual(odds, sorted(odds))                           # each slip makes the next grab firmer
        self.assertGreater(odds[-1], odds[0])
        attempt = play_claw(g, self.golden(g).x + edge)                # the roll still fails: the grip holds anyway
        self.assertEqual(attempt.odds, 1.0)
        self.assertTrue(self.m.has_secret_item(Q.SECRET_ITEM_CLAW))

    def test_a_centred_grab_is_already_a_good_chance(self):
        self.assertGreaterEqual(cm.grab_odds(0, fg.GOLDEN_CAT), 0.75)

    def test_a_clean_miss_beside_it_is_not_counted(self):
        g = self.claw_scene().claw
        g.rng = FixedRoll(0.999)
        play_claw(g, cm.SLOTS[0] - 40 if cm.SLOTS[0] > 80 else cm.HOME_X + 1)
        self.assertEqual(self.m.golden_misses, 0)

    def test_ordinary_play_is_unchanged_alongside_it(self):
        g = self.claw_scene().claw
        g.rng = FixedRoll(0.0)
        ordinary = next(p for p in g.plushies if p.spec is not fg.GOLDEN_CAT)
        before = self.p.tickets
        attempt = play_claw(g, ordinary.x)
        self.assertTrue(attempt.won)
        self.assertEqual(self.p.tickets - before, ordinary.spec.tickets)
        self.assertEqual(attempt.odds, ordinary.spec.grip)
        self.assertFalse(self.m.has_secret_item(Q.SECRET_ITEM_CLAW))

    def test_leaving_mid_attempt_still_pays_it_out_properly(self):
        scene = self.claw_scene()
        g = scene.claw
        g.rng = FixedRoll(0.0)
        self.assertTrue(g.start())
        g.x = self.golden(g).x
        g.drop()
        g.finish()
        self.assertTrue(self.m.has_secret_item(Q.SECRET_ITEM_CLAW))


class GoldenCatGateTests(HubBase):
    story_kw = {"clues": ("maze", "galaxy", "volley"), "hint_told": True}

    def test_no_golden_cat_before_the_answer(self):
        goto_room(self.game, "prize_plaza")
        g = ClawScene(self.game, self.game.session.primary).claw
        self.assertIsNone(g.special)
        self.assertFalse(any(p.spec.hidden for p in g.plushies))

    def test_no_secret_item_02_before_chapter_two(self):
        p = profile("early", chapter2=False, solved=True, clues=("maze", "galaxy", "volley"))
        m = QuestManager(LocalSession(p))
        self.assertFalse(m.golden_cat_wanted)
        prize = fg.GoldenCatPrize(m, lambda kind, k: m.handle(kind, k))
        prize.on_win(None, fg.GOLDEN_CAT, p)
        m.handle("secret_item_found", Q.SECRET_ITEM_CLAW)
        self.assertFalse(m.has_secret_item(Q.SECRET_ITEM_CLAW))


class OrdinaryMachinesTests(HubBase):
    story_kw = {"chapter2": False}

    def test_capsule_and_claw_and_minigames_still_play_before_chapter_two(self):
        svc = CapsuleScene(self.game, self.game.session.primary, RETRO).service
        self.assertTrue(svc.pull(RETRO).success)
        goto_room(self.game, "prize_plaza")
        g = ClawScene(self.game, self.game.session.primary).claw
        g.rng = FixedRoll(0.0)
        self.assertTrue(play_claw(g, g.plushies[0].x).won)
        for machine_id, cls in (("puzzle_drop", CatMazeScene), ("galaxy_defender", GalaxyDefenderScene),
                                ("pixel_volleyball", PixelVolleyballScene)):
            room, scene = self.start_machine(machine_id, cls)
            self.frames(1, [key(K.K_RETURN)])
            self.frames(30)
            scene.draw(pygame.Surface((400, 300)))
            scene.leaving = True
            self.game.scenes.pop()
            self.frames(40)

    def test_the_session_is_one_player(self):
        self.assertEqual(len(self.game.session.players), 1)
        self.assertIs(self.game.session.primary.profile, self.p)


# ===================================================================== the Quest Log and the corner tracker
class QuestLogSymbolTests(unittest.TestCase):
    def setUp(self):
        self.p = profile()
        self.m = QuestManager(LocalSession(self.p))

    def log(self):
        from quest_ui import QuestLogUI
        return QuestLogUI(self.m, self.p)

    def tracker_texts(self):
        from quest_ui import ObjectiveTracker
        return [t for t, _ in ObjectiveTracker(self.m)._detail()]

    def test_unknown_symbols_show_as_question_marks_in_fixed_order(self):
        rows = self.log().symbol_rows()
        self.assertEqual([r[0] for r in rows], ["I", "II", "III"])
        self.assertEqual([r[1] for r in rows], ["???", "???", "???"])
        self.m.handle(Q.CLUE_FOUND_EVENT, "volley")
        rows = self.log().symbol_rows()
        self.assertEqual(rows, [("I", "???", "NOT FOUND YET"), ("II", "???", "NOT FOUND YET"),
                                ("III", "PAW", "FOUND IN CAT VOLLEYBALL")])

    def test_a_discovery_updates_both_the_tracker_and_the_log(self):
        self.assertEqual(self.m.active.id, "ch2_secret_item")
        self.assertIn("SYMBOLS 0/3", self.tracker_texts())
        self.m.handle(Q.CLUE_FOUND_EVENT, "maze")
        self.m.handle(Q.CLUE_FOUND_EVENT, "galaxy")
        self.assertIn("SYMBOLS 2/3", self.tracker_texts())
        self.assertEqual([r[1] for r in self.log().symbol_rows()], ["STAR", "MOON", "???"])

    def test_the_tracker_never_lists_the_symbols(self):
        for clue in CH2_CLUES:
            self.m.handle(Q.CLUE_FOUND_EVENT, clue)
            for text in self.tracker_texts():
                for word in ("STAR", "MOON", "PAW"):
                    self.assertFalse(mentions(text, word), text)

    def test_the_symbols_page_turns_and_draws(self):
        log = self.log()
        self.assertEqual(log.pages, ("OVERVIEW", "CHAPTER 02"))
        log.handle_event(key(K.K_RIGHT))
        self.assertEqual(log.page, 1)
        self.m.handle(Q.CLUE_FOUND_EVENT, "volley")
        surf = pygame.Surface((400, 300))
        log.draw(surf)
        log.handle_event(key(K.K_LEFT))
        self.assertEqual(log.page, 0)
        log.draw(surf)

    def test_no_symbols_page_before_chapter_two(self):
        p = profile("pre", chapter2=False)
        from quest_ui import QuestLogUI
        log = QuestLogUI(QuestManager(LocalSession(p)), p)
        self.assertEqual(log.pages, ("OVERVIEW",))
        log.handle_event(key(K.K_RIGHT))
        self.assertEqual(log.page, 0)

    def test_still_readable_after_the_chapter(self):
        p = profile("done", clues=CH2_CLUES, solved=True, hint_told=True, item=True)
        from quest_ui import QuestLogUI
        m = QuestManager(LocalSession(p))
        self.assertNotEqual(m.active.id, "ch2_secret_item")
        log = QuestLogUI(m, p)
        self.assertIn("CHAPTER 02", log.pages)
        self.assertEqual([r[1] for r in log.symbol_rows()], ["STAR", "MOON", "PAW"])


# ===================================================================== bag, collection and showcase
class InventoryLayoutTests(unittest.TestCase):
    def ui(self, items):
        from inventory import Inventory
        from inventory_ui import InventoryUI
        return InventoryUI(Inventory(items=items), on_use=lambda _i: None, use_keys=(K.K_u,))

    def test_no_detail_text_overlaps_or_leaves_its_box_for_any_item(self):
        from font import get_font
        font = get_font()
        for d in ITEM_REGISTRY:
            ui = self.ui({d.id: min(3, d.limit)})
            for inspecting in (False, True):
                ui.inspecting = inspecting
                box = ui.detail_rect()
                rects = [pygame.Rect(x, y, font.size(t)[0], 7) for t, _c, x, y in ui.detail_lines(d, 1)]
                for r in rects:
                    self.assertTrue(box.contains(r), (d.id, inspecting, r, box))
                for i, a in enumerate(rects):
                    for b in rects[i + 1:]:
                        self.assertFalse(a.colliderect(b), (d.id, inspecting, a, b))

    def test_the_hint_card_shows_everything_when_inspected(self):
        ui = self.ui({"hint_card_galaxy": 1})
        ui.inspecting = True
        d = ITEM_REGISTRY.get("hint_card_galaxy")
        text = " ".join(t for t, *_ in ui.detail_lines(d, 1))
        self.assertNotIn("...", text)
        self.assertIn("OWNED: 1", text)
        self.assertIn("ONE ONLY", text)
        self.assertIn("READ IT ANY TIME", text)

    def test_scrolling_only_moves_when_the_cursor_leaves_the_view(self):
        from inventory_ui import COLS, ROWS
        items = {d.id: 1 for d in list(ITEM_REGISTRY)[:COLS * (ROWS + 3)]}
        ui = self.ui(items)
        for _ in range(ROWS + 1):
            ui.handle_event(key(K.K_DOWN))
        self.assertEqual(ui.scroll_row, 2)
        ui.handle_event(key(K.K_UP))
        self.assertEqual(ui.scroll_row, 2)                              # back up inside the view: no scroll
        for _ in range(3):
            ui.handle_event(key(K.K_UP))
        self.assertEqual(ui.scroll_row, 0)
        self.assertTrue(pygame.Rect(0, 0, 400, 300).contains(ui.slot_rect(ui.selected)))


class CollectionConsistencyTests(unittest.TestCase):
    def test_every_chapter_two_item_shows_in_bag_collection_and_showcase(self):
        from collection import CollectionService
        from showcase import COLLECTIBLE_SLOT, ShowcaseService
        p = profile()
        for item in CARDS + ("claw_golden_cat", "claw_plush_berry"):
            p.inventory.add_item(item)
        p.inventory.add_item("claw_plush_berry", 2)
        bag = {d.id: q for d, q in p.inventory.get_all_items(COLLECTIBLE)}
        owned = {d.id for d, o in CollectionService(p).entries() if o}
        shown = {o.value: o.count for o in ShowcaseService(p).options(COLLECTIBLE_SLOT)}
        self.assertEqual(set(bag), owned)
        self.assertEqual(bag, shown)
        self.assertEqual(bag["claw_plush_berry"], 3)                   # a counted duplicate
        self.assertEqual(bag["claw_golden_cat"], 1)

    def test_singles_never_stack_and_survive_a_reload(self):
        p = profile()
        for item in CARDS + ("claw_golden_cat",):
            self.assertEqual(p.inventory.add_item(item), 1)
            self.assertEqual(p.inventory.add_item(item), 0)          # one only
        p.inventory.add_item("claw_plush_berry", 4)
        before = p.inventory.to_dict()
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        path = os.path.join(folder, "p.json")
        ProfileStore(path).save(p)
        self.assertEqual(ProfileStore(path).load().inventory.to_dict(), before)

    def test_new_items_have_a_name_text_and_an_icon(self):
        from item_icons import item_icon
        for item in CARDS + ("claw_golden_cat",) + tuple(d.id for d in ITEM_REGISTRY if d.id.startswith("claw_plush")):
            d = ITEM_REGISTRY.get(item)
            self.assertTrue(d.name and d.description and d.use_hint, item)
            icon = item_icon(d)
            self.assertTrue(any(icon.get_at((x, y))[3] for x in range(icon.get_width()) for y in range(icon.get_height())))

    def test_the_collection_screen_draws_with_long_texts(self):
        from collection_ui import CollectionScene, description_lines
        rows = description_lines("WORD " * 60, 100, 3)
        self.assertEqual(len(rows), 3)
        self.assertTrue(rows[-1].endswith("..."))


# ===================================================================== chapter order and the earnings milestone
class ChapterTwoProgressionTests(unittest.TestCase):
    def test_chapter_two_walks_item_then_trial_with_lifetime_earnings(self):
        p = profile(clues=CH2_CLUES, solved=True, hint_told=True)
        m = QuestManager(LocalSession(p))
        self.assertEqual(m.current_chapter, 2)
        self.assertEqual(m.active.id, "ch2_secret_item")
        m.handle("secret_item_found", Q.SECRET_ITEM_CLAW)
        self.assertEqual(m.active.id, "ch2_secret_trial")
        need = Q.trial_earnings("trial_02")
        self.assertEqual(need, (15, 150))
        trial = next(t for t in Q.TRIALS if t.id == "trial_02")
        status = Q.trial_status(m, p, trial)
        self.assertEqual(status.code, "locked")                       # not enough EARNED yet
        p.add_tokens(500, "TEST")                                     # (the wallet is not what counts, earnings are)
        p.spend_tokens(480, "TEST")
        p.add_tickets(150)
        status = Q.trial_status(m, p, trial)
        self.assertNotEqual(status.lock, Q.LOCK_EARNINGS)
        self.assertFalse(m.chapter_unlocked(3))                       # Chapter 03 waits for Trial 02

    def test_secret_item_02_is_refused_before_chapter_two(self):
        p = profile(chapter2=False)
        m = QuestManager(LocalSession(p))
        m.handle("secret_item_found", Q.SECRET_ITEM_CLAW)
        self.assertFalse(m.has_secret_item(Q.SECRET_ITEM_CLAW))
        self.assertEqual(m.current_chapter, 1)


if __name__ == "__main__":
    unittest.main()
