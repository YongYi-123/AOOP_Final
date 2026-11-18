"""Tests for TRIAL 02 - THE UNBEATEN RECORD (the tournament night behind the Legacy Terminal).

The rules are tested on their own (THE MISSING ENTRY, the run and its save, the three opponents on NEON BRAWL's engine),
and the hall is played with real key events through the real Game (unbeaten_testing.HallDriver): walking, talking, the
documents, the terminal's wheels, the fights, the ending and the way back out. Every test uses a throw-away in-memory
profile (or a temporary folder); no real save is read or written.

Run headless from this folder:   python -m unittest test_unbeaten_record -v
"""
import json
import os
import re
import shutil
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import font  # noqa: E402
import legacy_terminal as LT  # noqa: E402
import quests as Q  # noqa: E402
import unbeaten_art as A  # noqa: E402
import unbeaten_bout as B  # noqa: E402
import unbeaten_content as C  # noqa: E402
import unbeaten_record as T  # noqa: E402
import unbeaten_scene as S  # noqa: E402
import unbeaten_ui as UI  # noqa: E402
from game import Game  # noqa: E402
from local_session import LocalSession  # noqa: E402
from neon_brawl.ai import BossBrain  # noqa: E402
from neon_brawl.data import ATTACKS, ENEMIES, ROSTER  # noqa: E402
from neon_brawl.game import BrawlGame  # noqa: E402
from neon_brawl.model import Campaign, EnemyFighter  # noqa: E402
from player_profile import PlayerProfile, ProfileStore, clean_story  # noqa: E402
from room_testing import goto_room  # noqa: E402
from unbeaten_testing import DT, HallDriver, K, bot_move, key_down, key_up  # noqa: E402
from miao_meow import point_clear  # noqa: E402
from vending_ui import GLITCH_TIME, VendingScene  # noqa: E402

CLASSIC = [K.K_UP, K.K_UP, K.K_DOWN, K.K_DOWN, K.K_LEFT, K.K_RIGHT, K.K_LEFT, K.K_RIGHT, K.K_b, K.K_a]
TUTORIAL = ["grand_tour", "meet_the_locals", "arcade_explorer", "earn_some_rewards"]
HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = ("unbeaten_record.py", "unbeaten_content.py", "unbeaten_scene.py", "unbeaten_bout.py", "unbeaten_ui.py", "unbeaten_art.py")


def new_profile(pid="alice", tokens=40, tickets=60):
    p = PlayerProfile(profile_id=pid, display_name=pid.upper(), tokens=tokens, tickets=tickets)
    p.set_story({"opening_done": True, "completed": list(TUTORIAL), "flags": {"vending_secret": True}})
    return p


def open_chapter_two(m, item=True):
    m.handle("vending_secret")
    m.handle("secret_item_found", Q.SECRET_ITEM_RETRO_RACER)
    m.handle("secret_trial_done", "trial_01")
    if item:
        m.handle("secret_item_found", Q.SECRET_ITEM_CLAW)


def earn(profile, tokens=15, tickets=150):
    profile.add_tokens(tokens, "TEST")
    profile.add_tickets(tickets)


def simulate(opponent, style, character="REX", limit=200.0):
    bout = B.TournamentBout(opponent, character)
    t = 0.0
    while bout.state not in ("won", "lost") and t < limit:
        direction, action = bot_move(bout, style, t) if bout.state == "playing" else ((0, 0), None)
        if action:
            bout.player.act(action)
        bout.update(DT, direction)
        t += DT
    return bout, t


# ===================================================================== the rules
class MissingEntryTests(unittest.TestCase):
    def test_the_answer_is_unique_and_fixed(self):
        self.assertEqual(len(T.candidates()), 1)
        self.assertEqual(T.ANSWER, "B10")
        self.assertEqual(T.check_code("B10")[0], "ok")
        self.assertEqual(T.check_code("b10")[0], "ok")

    def test_every_clue_is_needed(self):
        """Leave out any one clue (the fee, the torn time, the unreadable name, the crossed-out refund) and more than
        one entry fits: it is a deduction across all three documents, not a lookup."""
        for clue in ("fee", "time", "smudge", "refunds"):
            self.assertGreaterEqual(len(T.candidates(**{clue: False})), 2, clue)

    def test_the_ledger_does_not_say_the_division(self):
        self.assertNotIn("DIV", C.LEDGER_DOC["head"])
        self.assertEqual(C.LEDGER_DOC["head"], ("NO.", "NAME", "PAID", "IN"))
        self.assertEqual(T.division_of(next(r for r in T.LEDGER if r[0] == 10)), "B")

    def test_the_documents_carry_the_clues_and_never_the_code(self):
        poster = " ".join(C.POSTER_DOC["lines"] + C.POSTER_DOC["footer"] + tuple(" ".join(r) for r in C.POSTER_DOC["table"]))
        self.assertIn("B  STUDENT", poster)
        self.assertIn("WAITING LIST", poster)
        self.assertIn("2 TOKENS", poster)
        self.assertIn("DIVISION LETTER", poster)
        ticket = " ".join(C.TICKET_DOC["lines"])
        self.assertIn("PAID: 2 TOKENS", ticket)
        self.assertIn("CHECKED IN: 6:4", ticket)
        self.assertNotIn("6:47", ticket)                                       # the end of the time is torn off
        self.assertNotIn("STUDENT", ticket)                                    # the division has to be worked out
        for doc in C.DOCS.values():
            self.assertNotIn("B10", json.dumps(doc))
        ledger = {r[0]: r for r in C.LEDGER_DOC["rows"]}
        self.assertIsNone(ledger["10"][1])
        self.assertEqual(ledger["07"][4], "REFUNDED")

    def test_wrong_codes_are_answered_without_giving_it_away(self):
        self.assertEqual(T.check_code("C01"), ("taken", "ENTRY 01 IS DANNY K. AND THEY ARE ALREADY HERE."))
        self.assertEqual(T.check_code("B14")[0], "waiting")
        self.assertEqual(T.check_code("B07")[0], "refunded")
        self.assertEqual(T.check_code("B09")[0], "taken")
        self.assertEqual(T.check_code("B12")[0], "other")
        self.assertEqual(T.check_code("D08")[0], "other")
        self.assertEqual(T.check_code("A10")[0], "none")                       # (a wrong letter never says which is right)
        self.assertEqual(T.check_code("C10"), T.check_code("D10"))
        self.assertEqual(T.check_code("")[0], "none")
        for code in ("C01", "B14", "B07", "B09", "B12", "D08", "A10", "B06"):
            self.assertNotIn("B10", T.check_code(code)[1])

    def test_the_wheels_start_empty_and_wrap(self):
        w = T.CodeWheels()
        self.assertEqual(w.code, "A00")
        w.turn(-1)
        self.assertEqual(w.code, "D00")
        w.move(1)
        w.turn(1)
        w.turn(1)
        self.assertEqual(w.code, "D00")                                      # the tens wheel is 0 / 1 only
        w.move(-2)
        self.assertEqual(w.cursor, 2)
        w.set_code("B10")
        self.assertEqual(w.code, "B10")

    def test_a_run_only_registers_on_the_right_code(self):
        run = T.TournamentRun()
        self.assertEqual(run.try_code("B12")[0], "other")
        self.assertFalse(run.registered or run.has_badge)
        self.assertEqual(run.wrong_codes, 1)
        self.assertEqual(run.try_code("B10")[0], "ok")
        self.assertTrue(run.registered and run.has_badge)

    def test_hints_never_say_the_code(self):
        run = T.TournamentRun()
        seen = []
        for doc in ("", "poster", "ticket", "ledger"):
            run.look_at(doc)
            seen.append(T.hint(run))
        for wrong in (1, 3):
            run.wrong_codes = wrong
            seen.append(T.hint(run))
        run.registered = True
        for n in range(4):
            run.rounds_won = n
            seen.append(T.hint(run))
        text = " ".join(seen).upper()
        for banned in ("B10", " 10", "TEN", "6:47", "KAI"):
            self.assertNotIn(banned, text)
        self.assertEqual(len(set(seen)), len(seen))


class BrokenBracketRuleTests(unittest.TestCase):
    def test_exactly_one_bracket_fits_all_the_evidence(self):
        solutions = T.bracket_solutions()
        self.assertEqual(len(solutions), 1)
        board, winners = solutions[0]
        self.assertEqual(board, {3: "MEI L.", 4: "THE CHALLENGER", 5: "DANNY K.", 6: "JUNE P.", 7: "ROCKO", 8: "THE CHAMPION"})
        self.assertEqual(set(winners), {1, 4, 5, 8})
        self.assertEqual(T.semifinal_opponent(board, winners), "THE CHALLENGER")   # the round 02 opponent

    def test_the_rules_the_slips_and_the_eyewitnesses_are_each_needed(self):
        for piece in ("rules", "slips", "fan", "student"):
            self.assertGreaterEqual(len(T.bracket_solutions(skip=(piece,))), 2, piece)

    def test_every_fact_is_really_said_or_printed_in_the_hall(self):
        said = {k: " ".join(t for _, t, _ in C.PEOPLE[k]["talk"][1].get("clue", ())).upper() for k in T.TESTIMONY_FACTS}
        self.assertIn("ROCKO", said["fan"])
        self.assertIn("CHAMPION", said["fan"])
        self.assertIn("OVER BEFORE", said["fan"])
        self.assertIn("DANNY K. BEAT JUNE P.", said["student"])
        self.assertIn("THREE ROUNDS", said["nycu"])
        self.assertIn("FOURTEEN BLOCKS", said["challenger"])
        slips = json.dumps(C.SLIPS_DOC)
        for words in ("14 BLOCKS", "LONGEST", "FASTEST", "WINNER: SLOT 4", "WINNER: SLOT 5", "WINNER: SLOT 8"):
            self.assertIn(words, slips)
        self.assertTrue(T.is_junior("TOMMY"))                                  # the ledger says he paid 1 token
        self.assertEqual([T.ledger_number(n) for n in ("DANNY K.", "MEI L.", "ROCKO", "JUNE P.")], [1, 2, 4, 6])
        for name in T.INVITED:
            self.assertIsNone(T.ledger_number(name))
        self.assertNotIn("THE CHALLENGER", json.dumps(C.SLIPS_DOC))              # the slips never print a name

    def test_the_draft_clears_one_slot_or_the_whole_board(self):
        draft = T.BracketDraft()
        draft.place(3, "MEI L.")
        draft.place(4, "ROCKO")
        draft.mark_winner(4)
        draft.clear_slot(4)
        self.assertEqual(draft.slots[4], None)
        self.assertNotIn(4, draft.winners)
        self.assertEqual(draft.slots[3], "MEI L.")
        draft.mark_winner(3)
        draft.clear()
        self.assertTrue(all(n is None for n in draft.slots.values()))
        self.assertEqual(draft.winners, {1})                                   # the qualifier stays won

    def test_names_come_round_in_a_to_z_order(self):
        draft = T.BracketDraft()
        seen = []
        for _ in range(len(T.BRACKET_POOL)):
            draft.cycle(3, 1)
            seen.append(draft.slots[3])
        self.assertEqual(seen, sorted(T.BRACKET_POOL))

    def test_the_draft_is_never_filled_in_and_skips_names_in_use(self):
        d = T.BracketDraft()
        self.assertEqual(set(d.slots.values()), {None})
        self.assertEqual(d.winners, {1})
        self.assertEqual(d.check(), "incomplete")
        d.cycle(3, 1)
        first = d.slots[3]
        d.cycle(4, 1)
        self.assertNotEqual(d.slots[4], first)
        d.cycle(3, -1)
        self.assertIsNone(d.slots[3])
        d.mark_winner(3)
        d.mark_winner(4)
        self.assertEqual(d.winners & {3, 4}, {4})
        d.mark_winner(2)
        self.assertIn(1, d.winners)                                           # (the qualifier result is fixed)

    def test_a_wrong_board_costs_nothing(self):
        run = T.TournamentRun()
        run.registered, run.rounds_won = True, 1
        d = T.BracketDraft()
        for slot, name in T.BRACKET_ANSWER.items():
            d.place(slot, name)
        d.winners = {1, 3, 5, 8}
        self.assertEqual(run.solve_bracket(d), "wrong")
        self.assertFalse(run.bracket)
        d.winners = set(T.BRACKET_WINNERS)
        self.assertEqual(run.solve_bracket(d), "ok")
        self.assertTrue(run.bracket)


class ChampionsTrophyRuleTests(unittest.TestCase):
    def test_the_answer_comes_from_the_photos_and_the_note(self):
        years = {p["trophy"]: p["year"] for p in C.PHOTOS}
        self.assertEqual(years, {"rocket": "1989", "cup": "1988", "joystick": "'90"})
        self.assertEqual(T.TROPHY_ANSWER, ("joystick", "rocket", "cup"))      # newest nearest the door (the left wall)
        self.assertEqual(A.DOOR.x, 0)                                          # the door really is on the left
        self.assertLess(A.DOOR.centerx, A.TROPHY_SHELF.x)
        note = " ".join(C.CHAMP_NOTE_DOC["lines"])
        self.assertIn("NEWEST ONE ALWAYS GOES CLOSEST TO THE DOOR", note)
        self.assertIn("BACK TO THE CROWD", note)
        for word in ("JOYSTICK", "ROCKET", "CUP", "LEFT", "RIGHT", "1988", "1989", "1990"):
            self.assertNotIn(word, note)                                      # the note never spells the answer out
        self.assertEqual(len({p.get("stamp", C.PHOTO_STAMP) for p in C.PHOTOS}), 1)    # (the stamp is the same on all)

    def test_only_one_arrangement_opens_it(self):
        from itertools import permutations, product
        opened = []
        for order in permutations(T.TROPHY_YEARS):
            for facings in product(range(T.FACINGS), repeat=3):
                case = T.TrophyCase()
                case.arrange(order, facings)
                if case.pull():
                    opened.append((order, facings))
        self.assertEqual(opened, [(T.TROPHY_ANSWER, (0, 0, 0))])
        start = T.TrophyCase()
        self.assertFalse(start.correct)                                       # it is never found solved

    def test_lift_swap_turn_and_a_safe_wrong_pull(self):
        case = T.TrophyCase()
        before = case.order
        self.assertTrue(case.lift())
        case.move(2)
        self.assertFalse(case.turn(1))                                        # (nothing turns while one is lifted)
        self.assertTrue(case.lift())
        self.assertEqual(case.order, (before[2], before[1], before[0]))
        case.move(-2)
        f = case.slots[0][1]
        case.turn(1)
        self.assertEqual(case.slots[0][1], (f + 1) % 4)
        case.move(3)
        self.assertEqual(case.cursor, 3)
        self.assertFalse(case.lift())
        self.assertFalse(case.pull())
        self.assertEqual((case.tries, case.open), (1, False))
        self.assertTrue(case.lift() is False and case.turn(1) is False)        # (on the lever: nothing to lift)

    def test_the_key_is_taken_once_and_only_after_round_02(self):
        run = T.TournamentRun()
        run.registered, run.rounds_won, run.bracket = True, 1, True
        case = T.TrophyCase()
        case.arrange(T.TROPHY_ANSWER)
        case.pull()
        self.assertFalse(run.take_key(case))                                  # not before the semifinal is won
        run.rounds_won = 2
        self.assertTrue(run.take_key(case))
        self.assertFalse(run.take_key(case))
        self.assertTrue(run.use_key())
        self.assertEqual(run.stage, "fight")


class RunTests(unittest.TestCase):
    def test_rounds_only_advance_in_order_and_a_loss_keeps_the_round(self):
        run = T.TournamentRun()
        self.assertIsNone(run.next_round)                                     # no badge, no fight
        self.assertFalse(run.win(1))
        run.registered = True
        self.assertEqual(run.next_round.opponent, "rookie")
        self.assertFalse(run.win(2))                                          # not the round on offer
        self.assertEqual(run.lose(1).number, 1)
        self.assertTrue(run.win(1))
        self.assertEqual(run.next_round.number, 2)
        self.assertFalse(run.round_ready)                                     # THE BROKEN BRACKET comes first
        self.assertEqual(run.stage, "bracket")
        self.assertFalse(run.win(2))
        run.bracket = True
        self.assertTrue(run.win(2))
        self.assertEqual(run.stage, "trophies")
        self.assertFalse(run.win(3))                                          # then THE CHAMPION'S TROPHY and its key
        run.trophies = True
        self.assertEqual(run.stage, "key")
        self.assertFalse(run.win(3))
        self.assertTrue(run.use_key())
        self.assertFalse(run.use_key())
        self.assertTrue(run.win(3))
        self.assertTrue(run.finished)
        self.assertIsNone(run.next_round)
        self.assertFalse(run.win(3))

    def test_it_saves_and_loads(self):
        run = T.TournamentRun()
        run.registered, run.rounds_won, run.bracket, run.trophies = True, 2, True, True
        run.hear_kevin("fan")
        run.look_at("poster")
        again = T.TournamentRun.from_dict(json.loads(json.dumps(run.to_dict())))
        self.assertEqual((again.registered, again.rounds_won, again.kevin, again.seen), (True, 2, ["fan"], ["poster"]))
        self.assertEqual((again.bracket, again.trophies, again.key_used, again.stage), (True, True, False, "key"))
        self.assertEqual(T.TournamentRun().to_dict(), {})

    def test_damaged_saves_cannot_skip_anything(self):
        for data in (None, [], "x", {"rounds": 3}, {"registered": "yes", "rounds": 2}, {"registered": True, "rounds": True},
                     {"registered": True, "rounds": -4}, {"seen": ["poster", "lies"], "kevin": "fan"}):
            run = T.TournamentRun.from_dict(data)
            self.assertGreaterEqual(run.rounds_won, 0)
            if run.rounds_won:
                self.assertTrue(run.registered)
            self.assertTrue(set(run.seen) <= set(T.DOCUMENTS))
            self.assertIsInstance(run.kevin, list)
        self.assertEqual(T.TournamentRun.from_dict({"registered": True, "rounds": 99}).rounds_won, 1)   # no bracket solved
        self.assertEqual(T.TournamentRun.from_dict({"registered": True, "rounds": 3, "bracket": True}).rounds_won, 2)
        self.assertEqual(T.TournamentRun.from_dict({"registered": True, "rounds": 99, "bracket": True, "trophies": True,
                                                    "key": True}).rounds_won, 3)
        self.assertFalse(T.TournamentRun.from_dict({"registered": True, "rounds": 0, "bracket": True}).bracket)
        self.assertFalse(T.TournamentRun.from_dict({"registered": True, "rounds": 2, "bracket": True, "key": True}).key_used)

    def test_the_realisation_needs_three_different_people(self):
        run = T.TournamentRun()
        self.assertTrue(run.hear_kevin("fan"))
        self.assertFalse(run.hear_kevin("fan"))
        run.hear_kevin("student")
        self.assertFalse(run.realization_ready)
        run.hear_kevin("visitor")
        self.assertTrue(run.realization_ready)


# ===================================================================== the fights, on NEON BRAWL's engine
class OpponentTests(unittest.TestCase):
    def test_three_rounds_three_opponents(self):
        self.assertEqual([(r.number, r.stage, r.opponent, r.title, r.difficulty) for r in T.ROUNDS],
                         [(1, "QUALIFIER", "rookie", "THE ROOKIE", "EASY"), (2, "SEMIFINAL", "challenger", "THE CHALLENGER", "NORMAL"),
                          (3, "GRAND FINAL", "champion", "THE CHAMPION", "NORMAL+")])
        self.assertEqual(set(B.OPPONENTS), {"rookie", "challenger", "champion"})

    def test_they_are_made_of_neon_brawls_own_fighters_and_attacks(self):
        for spec in B.OPPONENTS.values():
            self.assertIn(spec.base, ENEMIES)
            for attack in spec.attacks + spec.armor:
                self.assertIn(attack, ATTACKS)
        foe = B.make_fighter(B.OPPONENTS["champion"], 300, 220)
        self.assertIsInstance(foe, EnemyFighter)
        self.assertIsInstance(foe.brain, BossBrain)                           # the WARDEN's own boss patterns
        for key in ("rookie", "challenger"):
            foe = B.make_fighter(B.OPPONENTS[key], 300, 220)
            self.assertIsInstance(foe, EnemyFighter)
            self.assertIsNone(foe.brain)
        self.assertTrue(issubclass(B.TournamentBout, Campaign))
        self.assertTrue(issubclass(B.TournamentBrawl, BrawlGame))

    def test_the_difficulty_rises_round_by_round(self):
        r, c, k = (B.OPPONENTS[x] for x in ("rookie", "challenger", "champion"))
        self.assertLess(r.health, c.health)
        self.assertLess(c.health, k.health)
        self.assertLessEqual(r.power, c.power)
        self.assertLessEqual(c.power, k.power)
        self.assertLess(r.guard, c.guard)                                     # limited blocking, then a real guard
        self.assertFalse(r.counter)
        self.assertTrue(c.counter)
        self.assertEqual(r.attacks, ("enemy",))                               # simple and predictable
        self.assertGreater(len(set(c.attacks)), 1)
        self.assertGreater(c.strafe, r.strafe)                                # more varied movement
        self.assertTrue(k.armor and not r.armor and not c.armor)

    def test_the_challengers_guard_holds_light_blows_and_breaks_on_heavy_ones(self):
        foe = B.make_fighter(B.OPPONENTS["challenger"], 200, 220)
        foe.state, foe.timer, foe.invulnerable = "guard", 0.5, 0.0
        dealt = foe.damage(12, 40)
        self.assertEqual(foe.state, "guard")
        self.assertLessEqual(dealt, 3)
        foe.invulnerable = 0.0
        foe.damage(30, 160, knockdown=True)
        self.assertEqual(foe.state, "knockdown")

    def test_the_champions_big_moves_come_through_light_blows(self):
        foe = B.make_fighter(B.OPPONENTS["champion"], 200, 220)
        foe.timer = foe.invulnerable = 0.0
        player = B.TournamentBout("champion").player
        player.x, player.y = 170, 220
        self.assertTrue(foe.begin("slam", player))
        foe.damage(12, 40)
        self.assertIsNotNone(foe.swing)                                       # still winding up
        foe.invulnerable = 0.0
        foe.damage(30, 160, knockdown=True)
        self.assertIsNone(foe.swing)                                          # a knockdown blow stops it

    def test_the_challenger_guards_and_counters_in_a_real_fight(self):
        totals = {"guards": 0, "counters": 0}
        for character in ROSTER:
            bout, _ = simulate("challenger", "mash", character)
            totals["guards"] += bout.opponent.guards
            totals["counters"] += bout.opponent.counters
        self.assertGreater(totals["guards"], 0)
        self.assertGreater(totals["counters"], 0)

    def test_every_round_is_winnable_with_every_fighter(self):
        for opponent in B.OPPONENTS:
            for character in ROSTER:
                bout, t = simulate(opponent, "smart", character)
                self.assertEqual(bout.state, "won", (opponent, character))
                self.assertLess(t, 60)

    def test_every_opponent_can_win_against_a_player_who_does_nothing(self):
        for opponent in B.OPPONENTS:
            bout, _ = simulate(opponent, "idle", "BRUNO")
            self.assertEqual(bout.state, "lost", opponent)

    def test_the_champion_is_the_hardest(self):
        hurt = {k: sum(simulate(k, "mash", c)[0].damage_received for c in ROSTER) for k in B.OPPONENTS}
        self.assertGreater(hurt["champion"], hurt["rookie"])
        self.assertGreater(hurt["champion"], hurt["challenger"])

    def test_a_bout_never_pays(self):
        bout, _ = simulate("rookie", "smart")
        self.assertEqual(bout.tickets, 0)
        self.assertEqual(bout.state, "won")

    def test_each_round_has_its_own_arena_without_hazards(self):
        for spec in B.OPPONENTS.values():
            bout = B.TournamentBout(spec.key)
            self.assertFalse(bout.stage > 0 and bout.wave < 3)               # (NEON BRAWL's live rails stay off)
            bout.update(DT)
            self.assertEqual(len(bout.enemies), 1)
            self.assertGreater(bout.opponent.x, bout.player.x)


# ===================================================================== the story's side
class StoryRuleTests(unittest.TestCase):
    def setUp(self):
        self.p = new_profile()
        self.m = Q.QuestManager(LocalSession(self.p))

    def test_trial_02_is_the_unbeaten_record_and_unseals_memory_fragment_02(self):
        self.assertEqual(Q.TRIALS_BY_ID["trial_02"].title, "THE UNBEATEN RECORD")
        self.assertEqual(Q.MEMORY_FRAGMENTS["trial_02"], "memory_fragment_02")
        self.assertEqual(Q.MEMORY_FRAGMENTS["trial_01"], "memory_fragment_01")
        self.assertIs(LT.TRIAL_SCENES["trial_02"], S.TournamentHallScene)
        self.assertNotIn("trial_03", LT.TRIAL_SCENES)

    def test_entry_needs_chapter_01_and_the_lifetime_earnings(self):
        trial = Q.TRIALS_BY_ID["trial_02"]
        self.assertEqual(Q.trial_status(self.m, self.p, trial).lock, Q.LOCK_CHAPTER)
        self.m.handle("vending_secret")
        self.m.handle("secret_item_found", Q.SECRET_ITEM_RETRO_RACER)
        self.assertEqual(Q.trial_status(self.m, self.p, trial).lock, Q.LOCK_CHAPTER)       # trial 01 not done
        self.m.handle("secret_trial_done", "trial_01")
        st = Q.trial_status(self.m, self.p, trial)
        self.assertEqual(st.lock, Q.LOCK_EARNINGS)                                          # the wallet (40 / 60) is not earnings
        self.assertEqual((st.tokens_needed, st.tickets_needed), (15, 150))
        earn(self.p, 15, 149)
        self.assertEqual(Q.trial_status(self.m, self.p, trial).lock, Q.LOCK_EARNINGS)
        self.p.add_tickets(1)
        self.assertEqual(Q.trial_status(self.m, self.p, trial).code, "available")
        self.p.spend_tokens(self.p.tokens, "TEST")                                         # spending never relocks
        self.assertEqual(Q.trial_status(self.m, self.p, trial).code, "available")

    def test_the_quest_order_puts_secret_item_02_first_and_chapter_03_needs_both(self):
        open_chapter_two(self.m, item=False)
        self.assertEqual(self.m.active.id, "ch2_secret_item")
        self.m.handle("secret_trial_done", "trial_02")
        self.assertFalse(self.m.chapter_unlocked(3))
        self.m.handle("secret_item_found", Q.SECRET_ITEM_CLAW)
        self.assertTrue(self.m.chapter_unlocked(3))
        self.assertEqual(self.m.active.id, "ch3_secret_item")

    def test_completion_grants_the_fragment_once(self):
        open_chapter_two(self.m)
        self.m.handle("secret_trial_done", "trial_02")
        self.m.handle("secret_trial_done", "trial_02")
        self.assertTrue(self.m.trial_done("trial_02"))
        self.assertEqual(self.m.state["stats"]["secret_trials"].count("trial_02"), 1)
        self.assertTrue(self.m.has_memory_fragment("trial_02"))
        self.assertEqual(self.m.memory_fragments, 2)                    # 01 and 02, each once

    def test_checkpoints_are_kept_only_while_the_chapter_is_open(self):
        self.assertFalse(self.m.save_trial_progress("trial_02", {"registered": True}))
        self.assertEqual(self.m.trial_progress("trial_02"), {})
        open_chapter_two(self.m)
        self.assertTrue(self.m.save_trial_progress("trial_02", {"registered": True, "rounds": 1}))
        self.assertEqual(self.m.trial_progress("trial_02"), {"registered": True, "rounds": 1})
        self.assertEqual(clean_story(self.p.story)["stats"][Q.TRIAL_PROGRESS]["trial_02"]["rounds"], 1)
        self.assertFalse(self.m.save_trial_progress("trial_99", {"x": 1}))
        self.m.trial_progress("trial_02")["rounds"] = 3                        # (a copy: the story is not changed by it)
        self.assertEqual(self.m.trial_progress("trial_02")["rounds"], 1)
        self.m.save_trial_progress("trial_02", {})
        self.assertNotIn(Q.TRIAL_PROGRESS, self.m.state.get("stats", {}))

    def test_checkpoints_survive_a_real_save_file(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        path = os.path.join(folder, "profile.json")
        open_chapter_two(self.m)
        self.m.save_trial_progress("trial_02", {"registered": True, "rounds": 2, "kevin": ["fan"], "bracket": True})
        ProfileStore(path).save(self.p)
        again = ProfileStore(path).load()
        m2 = Q.QuestManager(LocalSession(again))
        run = T.TournamentRun.from_dict(m2.trial_progress("trial_02"))
        self.assertEqual((run.registered, run.rounds_won, run.kevin), (True, 2, ["fan"]))


# ===================================================================== what people say, phase by phase
PHASE_SAVES = {0: {"registered": True}, 1: {"registered": True, "rounds": 1}, 2: {"registered": True, "rounds": 2, "bracket": True},
               3: {"registered": True, "rounds": 3, "bracket": True, "trophies": True, "key": True}}
CROWD = [k for k in C.PEOPLE if k != "host"]


def phase_text(key, phase):
    conv = C.PEOPLE[key]["talk"][phase]
    return [t for lines in (conv["first"], conv.get("clue", ())) + conv["again"] for _, t, _ in lines]


class PhaseDialogueRuleTests(unittest.TestCase):
    def test_every_person_has_their_own_lines_for_all_four_phases(self):
        for key in CROWD:
            talk = C.PEOPLE[key]["talk"]
            for phase in range(4):
                self.assertIn(phase, talk, key)
                self.assertTrue(talk[phase]["first"], (key, phase))
            seen = set()
            for phase in talk:                                              # nothing comes back in a later phase
                text = set(phase_text(key, phase))
                self.assertFalse(text & seen, (key, phase, text & seen))
                seen |= text

    def test_the_phase_is_the_saved_rounds(self):
        for phase, data in PHASE_SAVES.items():
            run = T.TournamentRun.from_dict(dict(data, miao=[0, phase]))
            self.assertEqual(run.phase, phase)
            self.assertEqual(sorted(set(run.chats)), sorted({0, phase}))
            self.assertEqual(T.TournamentRun.from_dict(run.to_dict()).phase, phase)
        self.assertEqual(T.TournamentRun.from_dict({"rounds": 3}).phase, 0)                # (a damaged save cannot skip)

    def test_bracket_testimony_is_told_after_the_qualifier_and_only_then(self):
        for key in list(T.TESTIMONY_FACTS) + list(T.SUPPORTING_FACTS):
            self.assertTrue(C.PEOPLE[key]["talk"][1].get("clue"), key)                    # a clue: kept for asking again
        names = ("DANNY", "JUNE", "MEI ", "MEI.", "ROCKO", "TOMMY", "FOURTEEN", "14 ", "THREE ROUNDS", "BLOCKS")
        for key in CROWD:
            for phase in (0, "0+", 2, 3):
                if phase not in C.PEOPLE[key]["talk"]:
                    continue
                text = " ".join(phase_text(key, phase)).upper() + " "
                for word in names:
                    self.assertNotIn(word, text, (key, phase))

    def test_every_testimony_agrees_with_the_one_answer(self):
        board = dict(T.BRACKET_FIXED)
        board.update(T.BRACKET_ANSWER)
        for key, fact in list(T.TESTIMONY_FACTS.items()) + list(T.SUPPORTING_FACTS.items()):
            self.assertTrue(fact(board, T.BRACKET_WINNERS), key)
        self.assertEqual(len(T.bracket_solutions()), 1)
        said = " ".join(t for k in T.SUPPORTING_FACTS for _, t, _ in C.PEOPLE[k]["talk"][1]["clue"]).upper()
        for words in ("FOURTEEN BLOCKS", "WINNER", "MEI AND JUNE", "DIDN'T HAVE TO FIGHT EACH OTHER", "TOMMY", "JUNIORS"):
            self.assertIn(words, said)
        kid = " ".join(phase_text("kid", 1)).upper()
        self.assertNotIn("WON HIS", kid)                                   # no guess that contradicts the answer

    def test_trophy_talk_points_the_way_but_never_gives_the_order(self):
        clues = " ".join(t for k in CROWD for _, t, _ in C.PEOPLE[k]["talk"][2].get("clue", ())).upper()
        for words in ("PHOTO", "YEARS", "SCHEDULE BOARD", "LEVER", "TROPHIES"):
            self.assertIn(words, clues)
        for key in CROWD:
            for phase in C.PEOPLE[key]["talk"]:
                text = " ".join(phase_text(key, phase)).upper()
                words = ("CUP", "ROCKET", "JOYSTICK", "1988", "1989", "1990", "'90") + (("LEFT", "RIGHT", "OLDEST", "NEWEST") if phase == 2 else ())
                for word in words:
                    self.assertIsNone(re.search(r"\b" + re.escape(word) + r"\b", text), (key, phase, word))

    def test_the_photos_the_note_and_the_door_give_the_trophy_answer(self):
        year = lambda p: int(p["year"][-2:]) + 1900
        newest_first = [p["trophy"] for p in sorted(C.PHOTOS, key=year, reverse=True)]
        note = " ".join(C.CHAMP_NOTE_DOC["lines"])
        self.assertIn("NEWEST ONE ALWAYS GOES CLOSEST TO THE DOOR", note)
        self.assertLess(A.DOOR.centerx, A.TROPHY_SHELF.centerx)            # the door is on the left of the cabinet
        self.assertEqual(tuple(newest_first), T.TROPHY_ANSWER)             # so: newest on the left
        self.assertIn("BACK TO THE CROWD", note)                           # (marks out: facing 0)
        visitor = " ".join(phase_text("visitor", 2)).upper()
        self.assertIn("FIRST THING YOU SEE WALKING IN", visitor)           # (echoes the note, says no order)

    def test_what_was_heard_is_saved_and_checked(self):
        run = T.TournamentRun()
        self.assertTrue(run.hear_clue("fan:1"))
        self.assertFalse(run.hear_clue("fan:1"))
        run.hear_clue("old_regular:2")
        self.assertEqual(T.TournamentRun.from_dict(run.to_dict()).heard, ["fan:1", "old_regular:2"])
        junk = T.TournamentRun.from_dict({"heard": ["fan:1", 3, "nocolon", "a:b:c", "x" * 50 + ":1"]})
        self.assertEqual(junk.heard, ["fan:1"])
        self.assertEqual(T.TournamentRun.from_dict({"heard": "fan:1"}).heard, [])

    def test_miao_and_the_objective_follow_the_night(self):
        for phase in range(4):
            lines = C.MIAO_CHAT[phase]
            self.assertTrue(all(s == "MIAO MEOW" for s, _, _ in lines))
        self.assertTrue(any("quieter" in t for _, t, _ in C.MIAO_CHAT[3]))  # puzzled, at the very end
        self.assertTrue(any("blink" in t for _, t, _ in C.MIAO_CHAT[2]))
        goals = [C.objective(T.TournamentRun.from_dict(d)) for d in PHASE_SAVES.values()]
        self.assertEqual(goals, ["Ask the host for ROUND 01.", "Fix the bracket board.", "Find the championship stage key.",
                                 "Meet the host for the trophy ceremony."])


# ===================================================================== the hall, played with the keyboard
class HallCase(unittest.TestCase):
    """A real game, one player, Chapter 02 open (Secret Item 02 owned), earnings reached, standing in the hall."""

    def setUp(self):
        self.profile = new_profile()
        self.game = Game(session=LocalSession(self.profile))
        self.addCleanup(self.game.quit)
        self.manager = self.game.hub.story.manager
        open_chapter_two(self.manager)
        earn(self.profile)
        self.room = goto_room(self.game, "arcade_floor")
        self.events = []
        self.game.session.add_listener(lambda owner, event: self.events.append((event.type, event.key)))
        self.d = HallDriver(self.game)
        self.d.frames(5)

    def enter(self, intro=False):
        if not intro:
            self.manager.handle(T.INTRO_FLAG)
        self.game.scenes.push(S.TournamentHallScene(self.game, self.game.session.primary), fade=False)
        self.d.frames(60)
        if intro:
            return self.hall
        self.d.seconds(1.0)
        return self.hall

    @property
    def hall(self):
        return self.d.hall

    def wallet(self):
        p = self.profile
        return (p.tokens, p.tickets, p.lifetime_tokens_earned, p.lifetime_tickets_earned, p.lifetime_tickets_won,
                p.total_games_played, dict(p.high_scores))

    def registered(self):
        self.d.read_documents()
        self.d.register()


class EntryTests(HallCase):
    def open_terminal(self):
        self.room.acting_player = self.room.players[0]
        self.room.open_vending()
        self.room.acting_player = None
        self.d.frames(90)
        self.assertIsInstance(self.game.scenes.current, VendingScene)
        for k in CLASSIC:
            self.d.tap(k)
        self.d.frames(int((GLITCH_TIME + 0.8) / DT))
        term = self.game.scenes.current
        self.assertIsInstance(term, LT.LegacyTerminalScene)
        self.d.seconds(5)
        return term

    def test_the_legacy_terminal_opens_the_hall_and_charges_nothing(self):
        term = self.open_terminal()
        self.d.tap(K.K_DOWN)
        self.assertEqual(term.trial.id, "trial_02")
        self.assertEqual(term.status().code, "available")
        before = self.wallet()
        self.d.tap(K.K_e)
        self.d.frames(40)
        self.assertIsInstance(self.game.scenes.current, S.TournamentHallScene)
        self.assertEqual(self.wallet(), before)
        names = [type(s).__name__ for s in self.game.scenes.stack]
        self.assertEqual(names[-3:], ["VendingScene", "LegacyTerminalScene", "TournamentHallScene"])

    def test_without_earnings_the_terminal_refuses_and_says_why(self):
        self.profile._lifetime_tokens_earned = 0
        term = self.open_terminal()
        self.d.tap(K.K_DOWN)
        self.d.tap(K.K_e)
        self.d.frames(5)
        self.assertEqual(term.notice["title"], "EARNINGS REQUIRED")
        self.assertNotIsInstance(self.game.scenes.current, S.TournamentHallScene)

    def test_a_completed_trial_is_replayable(self):
        self.manager.handle("secret_trial_done", "trial_02")
        term = self.open_terminal()
        self.d.tap(K.K_DOWN)
        self.assertEqual(term.status().code, "done")
        self.assertIn("COMPLETE. REPLAYABLE.", [r[0] for r in term.detail_rows()])
        self.d.tap(K.K_e)
        self.d.frames(40)
        self.assertIsInstance(self.game.scenes.current, S.TournamentHallScene)
        self.assertTrue(self.game.scenes.current.replay)

    def test_trial_01_is_unchanged(self):
        from golden_age_scene import GoldenAgeScene
        self.assertIs(LT.TRIAL_SCENES["trial_01"], GoldenAgeScene)
        self.assertEqual(Q.TRIALS_BY_ID["trial_01"].title, "THE GOLDEN AGE")
        self.assertEqual(Q.TRIALS_BY_ID["trial_01"].needs_items, ((Q.SECRET_ITEM_RETRO_RACER, "REVERSE GEAR (SECRET ITEM 01)"),))


class HallTests(HallCase):
    def test_the_hall_loads_with_a_crowd_and_everything_reachable(self):
        hall = self.enter()
        self.assertEqual(hall.music_id, "lobby")
        self.assertTrue(10 <= len(hall.people) <= 15)
        roles = {p.name for p in hall.people.values()}
        for role in ("HOST", "REGISTRATION", "PRIZE COUNTER", "OLD REGULAR", "STUDENT", "MAINTENANCE", "YOUNG VISITOR",
                     "TOURNAMENT FAN", "SPECTATOR", "WAITING PLAYER"):
            self.assertIn(role, roles)
        for key in list(hall.spots) + ["npc_" + k for k in hall.people]:
            self.assertIsNotNone(self.d.route(hall, key), key)
        av = hall.avatar
        self.assertEqual((av.x, av.y), A.START)
        self.assertGreaterEqual(len(hall.miao_spots), 6)
        for rect in hall.solids:                                             # nobody stands in the doorway
            self.assertFalse(rect.colliderect(A.DOOR_ZONE.inflate(-6, -6)) and rect not in hall.walls, rect)

    def test_the_ledger_never_hands_e_to_the_clock(self):
        hall = self.enter()
        ledger, clock = hall.spots["ledger"], hall.spots["clock"]
        for x in range(ledger.zone.left - 4, ledger.zone.right + 5):
            for y in range(ledger.zone.top + 4, ledger.zone.bottom + 5):
                sp = hall.spot_at(x, y)
                if sp is not None and sp.key == "clock":
                    self.assertFalse(ledger.zone.colliderect(pygame.Rect(x - 5, y - 5, 10, 5)), (x, y))
        self.assertEqual(hall.spot_at(*ledger.zone.center).key, "ledger")
        self.assertEqual(hall.spot_at(*clock.zone.center).key, "clock")

    def test_the_two_boards_work_from_the_front_and_from_the_side(self):
        hall = self.enter()
        for key in ("photo_board", "bracket_board"):
            sp = hall.spots[key]
            self.assertEqual(hall.spot_at(sp.zone.centerx, sp.zone.bottom).key, key)
            side = sp.extra[0]
            self.assertEqual(hall.spot_at(side.centerx, side.centery + 4).key, key)
            self.assertTrue(any(point_clear(side.centerx, y, hall.fixed_solids, 2) for y in range(side.top, side.bottom)), key)
        for key in ("magazines", "photo_board", "bracket_board"):            # and from below, right in front of them
            front = hall.spots[key].extra[-1]
            for x in range(front.left + 3, front.right - 2):
                y = A.FLOOR_BOTTOM - 1
                self.assertTrue(point_clear(x, y, hall.fixed_solids, 0), (key, x))
                self.assertEqual(hall.spot_at(x, y).key, key, (key, x))

    def test_the_opening_plays_once(self):
        hall = self.enter(intro=True)
        self.assertIsNotNone(hall.dialogue)
        lines = [l.text for l in hall.dialogue.lines]
        self.assertEqual(lines[0], "MEMORY RECONSTRUCTION LOADED.")
        self.assertEqual(lines[-1], "Obviously! I wanna see you win!")
        self.d.talk_through()
        self.assertTrue(self.manager.state["flags"].get(T.INTRO_FLAG))
        self.d.seconds(0.5)
        self.assertEqual(hall.last_notice, C.TITLE)
        self.d.tap(K.K_ESCAPE)
        self.d.tap(K.K_LEFT)
        self.d.tap(K.K_e)
        self.d.frames(30)
        again = self.enter(intro=True)
        self.d.seconds(1)
        self.assertIsNone(again.dialogue)

    def test_every_person_talks_and_says_something_of_their_own(self):
        hall = self.enter()
        firsts = set()
        for key, person in hall.people.items():
            self.d.use("npc_" + key)
            self.assertIsNotNone(hall.dialogue, key)
            firsts.add(hall.dialogue.lines[0].text)
            self.d.talk_through()
            self.assertFalse(person.talking)
        self.assertEqual(len(firsts), len(hall.people))
        self.assertEqual(sorted(hall.run.kevin), sorted(C.KEVIN_PEOPLE))
        self.assertEqual(sorted(self.manager.trial_progress(T.TRIAL_ID)["kevin"]), sorted(C.KEVIN_PEOPLE))

    def test_people_say_new_things_when_asked_again(self):
        hall = self.enter()
        said = []
        for _ in range(3):
            self.d.use("npc_old_regular")
            said.append(hall.dialogue.lines[0].text)
            self.d.talk_through()
        self.assertEqual(said[0], "Kevin built this place, you know.")
        self.assertEqual(len(set(said)), 3)

    def test_miao_hints_until_three_people_have_talked_about_the_founder(self):
        hall = self.enter()
        self.d.use("miao")
        self.assertEqual([l.text for l in hall.dialogue.lines], [t for _, t, _ in C.MIAO_CHAT[0]])
        self.d.talk_through()
        self.d.use("miao")
        self.assertIsNone(hall.dialogue)
        self.assertTrue(hall.bubble.visible)
        self.assertIn("poster", hall.bubble.text)
        for key in ("old_regular", "fan"):
            self.d.talk(key)
        self.assertFalse(hall.realization_waiting)
        self.d.talk("student")
        self.assertTrue(hall.realization_waiting)
        self.d.use("miao")
        self.assertEqual([(l.speaker, l.text) for l in hall.dialogue.lines], [(s, t) for s, t, _ in C.REALIZATION])
        self.d.talk_through()
        self.assertTrue(self.manager.state["flags"].get(T.REALIZED_FLAG))
        self.assertFalse(hall.realization_waiting)
        self.d.use("miao")
        self.assertIsNone(hall.dialogue)                                    # once only; then hints again

    def test_a_founders_story_heard_on_an_earlier_visit_still_counts(self):
        self.manager.save_trial_progress(T.TRIAL_ID, {"kevin": ["fan", "visitor", "nycu"]})
        hall = self.enter()
        self.assertTrue(hall.realization_waiting)
        self.d.use("npc_fan")
        self.assertNotIn("Kevin", hall.dialogue.lines[0].text)              # (already heard: their other lines)

    def test_the_things_in_the_hall_can_be_looked_at(self):
        hall = self.enter()
        for key in ("clock", "trophy_shelf", "schedule", "snack_bar", "magazines", "bench_left", "bench_right",
                    "cab_0", "cab_1", "cab_3", "bracket_board", "final_cabinet"):
            self.d.use(key)
            self.assertIsNotNone(hall.dialogue, key)
            self.d.talk_through()
            self.assertIsNone(hall.panel, key)
        self.d.use("photo_board")
        self.d.talk_through()
        self.assertIsInstance(hall.panel, UI.PhotoPanel)                    # the photo wall can always be looked at
        self.d.tap(K.K_e)
        self.d.use("leaderboard")
        self.assertEqual(hall.dialogue.lines[0].text, "The old leaderboard. ALL-TIME BEST.")
        self.d.talk_through()
        self.assertIsInstance(hall.panel, UI.DocumentPanel)
        self.assertEqual(hall.panel.kind, "leaderboard")
        self.d.tap(K.K_e)
        self.d.use("cab_2")
        self.assertIn("CONTINUE?", " ".join(l.text for l in hall.dialogue.lines))
        self.d.frames(50)
        self.assertGreater(hall._continue_flash, 0)                         # the dark machine flashes CONTINUE?
        self.d.talk_through()
        self.d.use("cab_2")
        self.assertIsInstance(hall.panel, UI.DocumentPanel)
        self.assertEqual(hall.panel.kind, "notes")

    def test_the_host_wants_a_badge_first(self):
        hall = self.enter()
        self.d.use("npc_host")
        self.assertIn("registration desk", hall.dialogue.lines[-1].text)
        self.d.talk_through()
        self.assertIsNone(hall.panel)
        self.assertFalse(any(isinstance(s, B.TournamentBoutScene) for s in self.game.scenes.stack))


class RegistrationTests(HallCase):
    def test_the_documents_open_and_are_remembered(self):
        hall = self.enter()
        self.d.read_documents()
        self.assertEqual(hall.run.seen, ["poster", "ticket", "ledger"])
        self.assertEqual(self.manager.trial_progress(T.TRIAL_ID)["seen"], ["poster", "ticket", "ledger"])
        self.d.use("poster")
        self.assertIsInstance(hall.panel, UI.DocumentPanel)                 # the second time: straight to the page
        self.d.tap(K.K_e)

    def test_a_wrong_code_changes_nothing(self):
        hall = self.enter()
        reply = self.d.register("B12")
        self.assertEqual(reply[0], "other")
        self.assertFalse(hall.run.registered)
        self.assertEqual(hall.panel.wheels.code, "B12")                     # the wheels stay where they were
        self.d.tap(K.K_ESCAPE)
        self.d.frames(5)
        self.assertIsNone(hall.dialogue)
        self.assertNotIn("registered", self.manager.trial_progress(T.TRIAL_ID))

    def test_the_right_code_brings_the_clerk_the_badge_and_the_tournament(self):
        hall = self.enter()
        self.d.use("terminal")
        self.d.enter_code(T.ANSWER)
        self.assertEqual(hall.panel.reply[0], "ok")
        self.d.tap(K.K_e)
        self.d.frames(10)
        self.assertEqual(hall.dialogue.lines[0].speaker, "T2_clerk")
        self.assertIn("TOURNAMENT BADGE", " ".join(l.text for l in hall.dialogue.lines))
        self.d.talk_through()
        self.assertTrue(hall.run.has_badge)
        self.assertEqual(hall.last_notice, "ITEM RECEIVED")
        self.assertEqual(self.manager.trial_progress(T.TRIAL_ID)["registered"], True)
        self.assertFalse(self.profile.inventory.get_quantity("tournament_badge"))     # a trial keepsake, not a bag item
        self.assertEqual(self.manager.secret_items, 2)                               # and not a Secret Item
        self.assertEqual(hall.screen_mode(), "round")
        self.d.use("terminal")
        self.assertEqual(hall.dialogue.lines[0].speaker, "SYSTEM")

    def test_closing_the_terminal_after_the_right_code_still_hands_over_the_badge(self):
        hall = self.enter()
        self.d.use("terminal")
        self.d.enter_code(T.ANSWER)
        self.d.tap(K.K_ESCAPE)
        self.d.frames(10)
        self.assertIsNotNone(hall.dialogue)
        self.d.talk_through()
        self.assertTrue(hall.run.has_badge)


class TournamentTests(HallCase):
    def setUp(self):
        super().setUp()
        self.enter()
        self.registered()

    def test_the_host_launches_round_01_on_neon_brawl(self):
        before = self.wallet()
        bout = self.d.start_round()
        self.assertIsInstance(bout, B.TournamentBoutScene)
        self.assertIsInstance(bout.brawl, B.TournamentBrawl)
        self.assertEqual(bout.brawl.screen, "select")                       # NEON BRAWL's own fighter select
        self.assertEqual(bout.round.number, 1)
        self.assertEqual(bout.music_override, "neon_brawl_0")
        self.assertIs(self.game.scenes.stack[-2], self.hall)
        self.d.tap(K.K_d)
        self.d.tap(K.K_RETURN)
        self.assertEqual(bout.brawl.screen, "tutorial")                     # its controls card, the first time
        self.assertEqual(bout.bout.opponent, None)
        self.d.tap(K.K_RETURN)
        self.d.frames(5)
        self.assertEqual(bout.bout.player.name, "NOVA")
        self.assertGreater(bout.banner, 0)
        self.assertEqual(self.wallet(), before)

    def test_winning_returns_to_the_hall_saves_the_round_and_the_hall_cheers(self):
        before = self.wallet()
        self.d.start_round()
        self.assertEqual(self.d.fight(real=True), "won")
        self.d.finish_bout()
        hall = self.hall
        self.assertIs(self.game.scenes.current, hall)
        self.assertEqual(hall.run.rounds_won, 1)
        self.assertEqual(self.manager.trial_progress(T.TRIAL_ID)["rounds"], 1)
        self.assertGreater(hall.celebrate, 0)
        self.assertEqual(hall.screen_mode(), "win")
        self.assertTrue(any(p.cheer > 0 for p in hall.people.values()))
        self.assertTrue(hall.confetti)
        self.d.seconds(1.4)
        self.assertEqual([l.text for l in hall.dialogue.lines[:2]], ["WHAT A MATCH!", "OUR CHALLENGER MOVES ON TO THE SEMIFINAL!"])
        self.d.talk_through()
        self.d.use("npc_rookie")
        self.assertIn("Good match", hall.dialogue.lines[0].text)              # the people react
        self.d.talk_through()
        self.assertEqual(self.wallet(), before)                              # no tokens, tickets, plays or high scores

    def test_losing_offers_the_same_round_again_without_leaving(self):
        bout = self.d.start_round()
        self.assertEqual(self.d.fight(style="idle", real=False), "lost")
        self.assertEqual(self.hall.run.rounds_won, 0)
        self.d.finish_bout(retry=True)
        self.assertIs(self.game.scenes.current, bout)
        self.assertIsNone(bout.result)
        self.assertEqual(bout.brawl.screen, "playing")                      # straight back in, same fighter
        self.assertEqual(bout.retries, 1)
        self.assertEqual(self.d.fight(real=False), "won")
        self.d.finish_bout()
        self.assertEqual(self.hall.run.rounds_won, 1)

    def test_a_loss_back_in_the_hall_keeps_every_round_already_won(self):
        self.d.win_round(real=False)
        self.d.fix_bracket()
        self.d.start_round()
        self.assertEqual(self.d.fight(style="idle", real=False), "lost")
        self.d.finish_bout(retry=False)
        self.assertIs(self.game.scenes.current, self.hall)
        self.d.seconds(0.6)
        self.assertEqual(self.hall.dialogue.lines[0].text, C.HOST["lost"][0][1])
        self.d.talk_through()
        self.assertEqual(self.hall.run.rounds_won, 1)
        self.assertEqual(self.hall.run.next_round.number, 2)
        self.assertTrue(self.hall.run.bracket)                              # the puzzle stays solved
        self.assertTrue(self.manager.trial_progress(T.TRIAL_ID)["bracket"])
        bout = self.d.start_round()
        self.assertEqual(bout.round.number, 2)                              # round 2 again, never round 1

    def test_a_player_just_mashing_on_the_keyboard_can_win_each_round_even_with_nova(self):
        """Accessibility, on the real input path (held arrows, tapped J): NOVA has the least health of the three."""
        for rnd in T.ROUNDS:
            scene = B.TournamentBoutScene(self.game, rnd, None, selection=1, tutorial=False)
            self.game.scenes.push(scene, fade=False)
            self.d.frames(3)
            self.assertEqual(self.d.fight(style="mash", real=True, character=1), "won", rnd.opponent)
            self.assertEqual(scene.bout.player.name, "NOVA")
            self.game.scenes.pop(fade=False)
            self.d.frames(2)

    def test_escape_from_the_fighter_select_is_a_forfeit_that_costs_nothing(self):
        bout = self.d.start_round()
        self.d.tap(K.K_ESCAPE)
        self.d.frames(40)
        self.assertIs(self.game.scenes.current, self.hall)
        self.assertEqual(self.hall.run.rounds_won, 0)
        self.d.seconds(0.6)
        self.assertEqual(self.hall.dialogue.lines[0].text, C.HOST["forfeit"][0][1])

    def test_the_pause_menu_end_run_also_returns(self):
        bout = self.d.start_round()
        self.d.tap(K.K_RETURN)
        self.d.tap(K.K_RETURN)
        self.d.seconds(2.6)
        self.d.tap(K.K_ESCAPE)
        self.assertTrue(bout.brawl.paused)
        self.d.tap(K.K_DOWN)
        self.d.tap(K.K_DOWN)
        self.d.tap(K.K_RETURN)
        self.d.frames(40)
        self.assertIs(self.game.scenes.current, self.hall)

    def test_three_rounds_in_a_row_with_the_right_opponents(self):
        seen = []
        for rnd in T.ROUNDS:
            bout = self.d.start_round()
            seen.append((bout.round.number, bout.spec.key, bout.music_override))
            self.assertEqual(self.d.fight(real=False), "won")
            self.d.finish_bout()
            self.d.seconds(2.0)
            self.d.talk_through()
            if rnd.number == 1:
                self.d.fix_bracket()
            elif rnd.number == 2:
                self.d.get_stage_key()
                self.d.insert_key()
        self.assertEqual(seen, [(1, "rookie", "neon_brawl_0"), (2, "challenger", "neon_brawl_1"), (3, "champion", "neon_brawl_3")])
        self.assertTrue(self.hall.run.finished)
        self.assertEqual(self.manager.trial_progress(T.TRIAL_ID)["rounds"], 3)
        self.d.seconds(1.0)
        self.assertFalse(self.hall.in_cutscene)                             # free to say goodbye first
        self.d.start_ceremony()
        self.d.seconds(1.0)
        self.assertTrue(self.hall.in_cutscene)

    def test_rounds_survive_leaving_and_coming_back(self):
        self.d.win_round(real=False)
        self.d.use("door")
        self.d.tap(K.K_LEFT)
        self.d.tap(K.K_e)
        self.d.frames(40)
        self.assertNotIsInstance(self.game.scenes.current, S.TournamentHallScene)
        hall = self.enter()
        self.assertTrue(hall.run.registered)
        self.assertEqual(hall.run.rounds_won, 1)
        self.assertEqual(hall.run.stage, "bracket")
        self.d.use("npc_host")
        self.assertEqual(hall.dialogue.lines[0].text, C.HOST["bracket"][0][1])


class BrokenBracketHallTests(HallCase):
    def setUp(self):
        super().setUp()
        self.enter()
        self.registered()

    def test_before_the_qualifier_the_board_is_just_a_board(self):
        self.d.use("bracket_board")
        self.assertEqual(self.hall.dialogue.lines[0].text, C.LOOKS["bracket_board"]["lines"][0][1])
        self.d.talk_through()
        self.assertIsNone(self.hall.panel)

    def test_the_semifinal_waits_for_the_board(self):
        self.d.win_round(real=False)
        hall = self.hall
        self.assertEqual(hall.run.stage, "bracket")
        self.assertEqual(hall.screen_mode(), "bracket")
        self.d.use("npc_host")
        self.assertEqual([l.text for l in hall.dialogue.lines], [t for _, t, _ in C.HOST["bracket"]])
        self.d.talk_through()
        self.assertIsInstance(hall.panel, UI.DocumentPanel)                   # the referee's slips
        self.assertEqual(hall.panel.kind, "slips")
        self.d.tap(K.K_e)
        self.d.frames(10)
        self.assertFalse(any(isinstance(s, B.TournamentBoutScene) for s in self.game.scenes.stack))

    def test_people_saw_the_other_matches_and_say_so_again_when_asked(self):
        self.d.win_round(real=False)
        hall = self.hall
        said = []
        for _ in range(3):
            self.d.use("npc_fan")
            said += [l.text for l in hall.dialogue.lines]
            self.d.talk_through()
        self.assertEqual(said.count("Did you catch the Champion's first match? Poor ROCKO."), 2)   # first talk, then again
        self.d.use("npc_student")                                            # (no founder's story now: a new phase)
        self.assertIn("DANNY K. beat JUNE P.", " ".join(l.text for l in hall.dialogue.lines))

    def test_a_wrong_board_then_the_right_one(self):
        self.d.win_round(real=False)
        hall = self.hall
        self.d.open_bracket()
        wrong = dict(T.BRACKET_ANSWER)
        wrong[3], wrong[6] = wrong[6], wrong[3]
        self.assertEqual(self.d.fill_bracket(wrong), "wrong")
        self.assertFalse(hall.run.bracket)
        self.assertEqual(hall.panel.draft.slots[3], "JUNE P.")                 # nothing is reset or corrected for you
        self.d.tap(K.K_ESCAPE)
        self.d.frames(5)
        self.assertNotIn("bracket", self.manager.trial_progress(T.TRIAL_ID))
        self.d.open_bracket()
        self.assertEqual(hall.panel.draft.slots[3], "JUNE P.")                 # (the board as it was left)
        self.assertEqual(self.d.fill_bracket(), "ok")
        self.d.tap(K.K_e)
        self.d.seconds(0.8)
        self.assertEqual([l.text for l in hall.dialogue.lines], [t for _, t, _ in C.HOST["bracket_done"]])
        self.d.talk_through()
        self.assertTrue(self.manager.trial_progress(T.TRIAL_ID)["bracket"])
        bout = self.d.start_round()
        self.assertEqual(bout.round.number, 2)
        self.assertEqual(bout.spec.title, T.semifinal_opponent(T.BRACKET_ANSWER, T.BRACKET_WINNERS))

    def test_x_empties_a_slot_and_clear_wipes_the_board(self):
        self.d.win_round(real=False)
        panel = self.d.open_bracket()
        self.d.fill_bracket(check=False)
        self.d._row(panel, 0)
        self.d.tap(K.K_x)
        self.assertIsNone(panel.draft.slots[3])
        self.assertEqual(panel.draft.slots[4], "THE CHALLENGER")
        self.d._row(panel, 7)
        self.d.tap(K.K_e)
        self.assertTrue(all(n is None for n in panel.draft.slots.values()))
        self.assertEqual(panel.draft.winners, {1})
        self.assertIsNone(panel.reply)
        self.assertEqual(self.d.fill_bracket(), "ok")                         # and it can still be solved after

    def test_the_solved_board_stays_solved_after_leaving(self):
        self.d.win_round(real=False)
        self.d.fix_bracket()
        self.d.use("door")
        self.d.tap(K.K_LEFT)
        self.d.tap(K.K_e)
        self.d.frames(40)
        hall = self.enter()
        self.assertTrue(hall.run.bracket)
        self.assertEqual(hall.run.stage, "fight")
        self.d.use("bracket_board")
        self.assertIsInstance(hall.panel, UI.BracketPanel)
        self.assertTrue(hall.panel.solved)
        self.assertEqual(hall.panel.draft.slots, T.BRACKET_ANSWER)

    def test_miaos_bracket_hints_grow_clearer_and_never_place_anyone(self):
        self.d.win_round(real=False)
        hall = self.hall
        self.d.use("miao")                                                   # (her say about the fight first)
        self.d.talk_through()
        for _ in range(2):                                                   # first: go and ask for the referee's slips
            self.d.use("miao")
            self.assertEqual(hall.bubble.text, T.SLIPS_FIRST)
            hall.bubble.clear()
        self.d.use("npc_host")
        self.d.talk_through()
        self.assertIsInstance(hall.panel, UI.DocumentPanel)
        self.d.tap(K.K_e)
        self.d.frames(5)
        tips = []
        for _ in range(5):
            self.d.use("miao")
            tips.append(hall.bubble.text)
            hall.bubble.clear()
        self.assertEqual(tips[:4], list(T.HINTS["bracket"]))
        self.assertEqual(tips[4], T.HINTS["bracket"][-1])
        text = " ".join(tips).upper()
        for name in ("MEI", "DANNY", "JUNE", "ROCKO", "TOMMY", "SLOT 4"):
            self.assertNotIn(name, text)


class ChampionsTrophyHallTests(HallCase):
    def setUp(self):
        super().setUp()
        self.manager.save_trial_progress(T.TRIAL_ID, {"registered": True, "rounds": 1, "bracket": True})
        self.enter()

    def win_semifinal(self):
        self.d.win_round(real=False)
        self.assertEqual(self.hall.run.stage, "trophies")

    def test_before_the_semifinal_the_cabinet_is_only_a_cabinet(self):
        self.d.use("trophy_shelf")
        self.assertEqual(self.hall.dialogue.lines[0].text, C.LOOKS["trophy_shelf"]["lines"][0][1])
        self.d.talk_through()
        self.assertIsNone(self.hall.panel)
        self.d.use("schedule")
        self.assertIn("SESSIONS MAY RUN LATE", " ".join(l.text for l in self.hall.dialogue.lines))

    def test_the_host_needs_the_missing_key(self):
        self.win_semifinal()
        hall = self.hall
        self.assertIn("stage key", " ".join(t for _, t, _ in C.HOST["won"][2]))
        self.assertEqual(hall.screen_mode(), "offline")
        self.d.use("npc_host")
        self.assertEqual(hall.dialogue.lines[0].text, C.HOST["key_missing"][0][1])
        self.d.talk_through()
        self.assertIsNone(hall.panel)
        self.d.use("final_cabinet")
        self.assertIn("keyhole is empty", " ".join(l.text for l in hall.dialogue.lines))
        self.d.talk_through()
        self.assertFalse(hall.run.key_used)

    def test_the_photos_and_the_note_can_be_read(self):
        self.win_semifinal()
        hall = self.hall
        self.d.use("photo_board")
        self.d.talk_through()
        self.assertIsInstance(hall.panel, UI.PhotoPanel)
        for _ in range(3):
            self.d.tap(K.K_RIGHT)
        self.assertEqual(hall.panel.seen, {0, 1, 2})
        self.d.tap(K.K_e)
        self.d.use("schedule")
        self.d.talk_through()
        self.assertIsInstance(hall.panel, UI.DocumentPanel)
        self.assertEqual(hall.panel.kind, "champ_note")
        self.d.tap(K.K_e)

    def test_wrong_arrangements_are_safe_and_the_right_one_gives_the_key_once(self):
        self.win_semifinal()
        hall = self.hall
        self.d.open_trophies()
        self.assertFalse(self.d.arrange_trophies(("cup", "rocket", "joystick")))     # oldest nearest the door: wrong
        self.assertFalse(self.d.arrange_trophies(T.TROPHY_ANSWER, (0, 2, 0)))       # one trophy sulking: wrong
        self.assertFalse(hall.run.trophies)
        self.assertEqual(hall.case.tries, 2)
        self.d.tap(K.K_ESCAPE)
        self.d.frames(5)
        self.assertNotIn("trophies", self.manager.trial_progress(T.TRIAL_ID))
        self.d.open_trophies()
        self.assertTrue(self.d.arrange_trophies())
        self.d.seconds(1.0)
        self.d.tap(K.K_e)                                                    # take the key
        self.d.frames(6)
        self.assertIn("CHAMPIONSHIP STAGE", " ".join(l.text for l in hall.dialogue.lines))
        self.d.talk_through()
        self.assertTrue(hall.run.trophies)
        self.assertEqual(hall.last_notice, "ITEM RECEIVED")
        self.assertTrue(self.manager.trial_progress(T.TRIAL_ID)["trophies"])
        self.d.use("trophy_shelf")                                           # the compartment is empty now
        self.assertEqual(hall.dialogue.lines[0].text, C.LOOKS["trophy_open"]["lines"][0][1])
        self.d.talk_through()
        self.assertFalse(hall.run.take_key(hall.case))                       # (and no second key)
        self.assertFalse(self.profile.inventory.get_quantity("championship_stage_key"))

    def test_the_key_wakes_the_stage_with_a_small_anomaly_and_round_03_opens(self):
        self.win_semifinal()
        hall = self.hall
        self.d.get_stage_key()
        self.d.use("npc_host")
        self.assertEqual(hall.dialogue.lines[0].text, C.HOST["key_found"][0][1])
        self.d.talk_through()
        self.d.use("final_cabinet")
        self.assertTrue(hall.run.key_used)
        self.assertEqual([m[0] for m in hall.fx.messages], ["DISPLAY DATA UPDATED"])
        self.assertGreater(hall.fx.board_glitch, 0)                          # the leaderboard flickers ...
        self.d.talk_through()
        self.d.seconds(5.0)
        self.assertEqual(hall.fx.board_glitch, 0)                            # ... and is back to normal
        self.assertTrue(all(age > life for _, age, life in hall.fx.messages))
        self.d.talk_through()
        self.assertTrue(self.manager.trial_progress(T.TRIAL_ID)["key"])
        self.assertEqual(hall.screen_mode(), "round")
        bout = self.d.start_round()
        self.assertEqual(bout.round.number, 3)

    def test_the_key_survives_leaving_and_a_lost_final_keeps_everything(self):
        self.win_semifinal()
        self.d.get_stage_key()
        self.d.use("door")
        self.d.tap(K.K_LEFT)
        self.d.tap(K.K_e)
        self.d.frames(40)
        hall = self.enter()
        self.assertEqual(hall.run.stage, "key")
        self.d.insert_key()
        self.d.start_round()
        self.assertEqual(self.d.fight(style="idle", real=False), "lost")
        self.d.finish_bout(retry=False)
        self.d.seconds(0.6)
        self.d.talk_through()
        run = T.TournamentRun.from_dict(self.manager.trial_progress(T.TRIAL_ID))
        self.assertEqual((run.bracket, run.trophies, run.key_used, run.rounds_won), (True, True, True, 2))


class FullNightTests(HallCase):
    def test_the_whole_night_with_all_three_puzzles(self):
        self.enter()
        self.d.play_through(real=False)
        self.assertTrue(self.manager.trial_done(T.TRIAL_ID))
        self.assertTrue(self.manager.has_memory_fragment(T.TRIAL_ID))
        self.assertEqual(self.manager.trial_progress(T.TRIAL_ID), {})
        self.assertEqual(self.events.count(("secret_trial_done", "trial_02")), 1)

    def test_a_replay_asks_for_every_puzzle_again_and_grants_nothing(self):
        self.enter()
        self.d.play_through(real=False)
        fragments, trials = self.manager.memory_fragments, list(self.manager.state["stats"]["secret_trials"])
        self.d.tap(K.K_RIGHT)
        self.d.tap(K.K_e)                                                    # STAY IN THE HALL: a fresh night
        self.d.frames(20)
        hall = self.hall
        self.assertEqual(hall.run.stage, "entry")
        self.assertFalse(hall.case.open or hall.draft.check() == "ok")
        self.d.play_through(real=False)
        self.assertFalse(hall.panel.first_time)
        self.assertEqual((self.manager.memory_fragments, self.manager.state["stats"]["secret_trials"]), (fragments, trials))
        self.assertEqual(self.events.count(("secret_trial_done", "trial_02")), 1)


class EndingTests(HallCase):
    def setUp(self):
        super().setUp()
        self.manager.save_trial_progress(T.TRIAL_ID, {"registered": True, "rounds": 2, "bracket": True, "trophies": True, "key": True})
        self.enter()
        self.d.start_round()
        self.assertEqual(self.d.fight(real=False), "won")
        self.d.finish_bout()
        self.d.seconds(2.0)
        self.d.talk_through()                                           # the host: the ceremony in a moment
        self.d.start_ceremony()

    def advance(self, until, limit=40.0):
        t = 0.0
        while not until() and t < limit:
            hall = self.hall
            if hall.dialogue is not None and hall.dialogue.done_typing:
                self.d.tap(K.K_e)
            else:
                self.d.frames(1)
            t += DT
        self.assertTrue(until(), "timed out")

    def test_the_celebration_then_the_malfunction_then_the_fragment(self):
        hall = self.hall
        before = self.wallet()
        self.advance(lambda: hall.fx.screen == "complete")
        self.assertTrue(hall.fx.party)
        self.assertTrue(hall.confetti)
        self.assertTrue(all(p.cheer > 0 for k, p in hall.people.items() if k not in ("clerk", "attendant")))
        self.advance(lambda: hall.dialogue is not None)
        self.assertEqual([l.text for l in hall.dialogue.lines], [t for _, t, _ in C.ENDING_CHEER])
        self.advance(lambda: hall.dialogue is not None and hall.dialogue.lines[0].text == "Thank you for coming, everyone!")
        self.advance(lambda: any(p.leaving for p in hall.people.values()))
        self.assertTrue(all(hall.people[k].leaving is None for k in C.STAFF))
        self.advance(lambda: hall.fx.cabinet_on)
        self.assertEqual([m[0] for m in hall.fx.messages], ["ACTIVE PLAYERS: DECREASING"])
        self.advance(lambda: hall.fx.board_glitch > 0)
        self.assertGreater(hall.fx.wobble, 0)
        self.assertLess(hall.music_duck, 1.0)
        self.advance(lambda: hall.fx.exit_flicker)
        self.advance(lambda: hall.fx.locked)
        self.assertEqual([m[0] for m in hall.fx.messages], list(C.SYSTEM_MESSAGES))
        self.advance(lambda: any(p.frozen for p in hall.people.values()))
        frozen = {k: (p.x, p.y) for k, p in hall.people.items() if p.frozen}
        self.d.frames(20)
        self.assertEqual(frozen, {k: (p.x, p.y) for k, p in hall.people.items() if p.frozen})
        self.advance(lambda: not any(p.frozen for p in hall.people.values()))
        self.advance(lambda: hall.dialogue is not None)
        self.assertEqual([l.text for l in hall.dialogue.lines], [t for _, t, _ in C.ENDING_FLICKER])
        self.advance(lambda: hall.dialogue is not None and hall.dialogue.lines[0].text == C.ENDING_FINAL[0][1])
        self.assertEqual([l.text for l in hall.dialogue.lines], [t for _, t, _ in C.ENDING_FINAL])
        self.advance(lambda: hall.dialogue is not None and hall.dialogue.lines[0].speaker == "CORE")
        self.assertEqual(hall.dialogue.lines[0].text, "One more game?")
        self.assertFalse(self.manager.trial_done(T.TRIAL_ID))                # not before the very end
        self.advance(lambda: hall.fx.freeze_all)
        self.advance(lambda: hall.fx.final == 2)
        self.assertGreater(hall.fx.fade, 0.9)
        self.advance(lambda: isinstance(hall.panel, UI.CompletePanel))
        self.assertTrue(self.manager.trial_done(T.TRIAL_ID))
        self.assertTrue(self.manager.has_memory_fragment(T.TRIAL_ID))
        self.assertEqual(self.events.count(("secret_trial_done", "trial_02")), 1)
        self.assertEqual(self.manager.trial_progress(T.TRIAL_ID), {})       # a replay starts at the desk again
        self.assertTrue(hall.panel.first_time)
        self.assertEqual(self.wallet(), before)
        self.assertEqual(self.manager.current_chapter, 3)                    # Secret Item 02 + Trial 02: Chapter 03 opens
        self.assertEqual(self.manager.active.id, "ch3_secret_item")

    def test_return_to_the_arcade_puts_the_player_back(self):
        hall = self.hall
        where = hall._saved
        self.d.watch_ending()
        self.d.tap(K.K_e)                                                    # RETURN TO ARCADE
        self.d.frames(40)
        self.assertIs(self.game.scenes.current, self.room)
        av = self.game.session.primary.avatar
        self.assertEqual((av.x, av.y, av.facing), where)

    def test_staying_starts_the_night_again(self):
        hall = self.hall
        self.d.watch_ending()
        self.d.tap(K.K_RIGHT)
        self.d.tap(K.K_e)
        self.d.frames(20)
        self.assertIs(self.game.scenes.current, hall)
        self.assertFalse(hall.run.registered)
        self.assertFalse(hall.fx.locked or hall.fx.freeze_all)
        self.assertTrue(all(not p.gone and not p.frozen for p in hall.people.values()))
        self.d.use("npc_host")
        self.assertIsNotNone(hall.dialogue)

    def test_a_replay_grants_nothing_twice(self):
        self.d.watch_ending()
        self.d.tap(K.K_RIGHT)
        self.d.tap(K.K_e)
        self.d.frames(20)
        before = (self.wallet(), json.dumps(self.manager.state["stats"]["secret_trials"]), self.manager.memory_fragments)
        self.manager.save_trial_progress(T.TRIAL_ID, {"registered": True, "rounds": 3, "bracket": True, "trophies": True, "key": True})
        self.d.use("door")
        self.d.tap(K.K_LEFT)
        self.d.tap(K.K_e)
        self.d.frames(40)
        hall = self.enter()
        self.assertTrue(hall.replay)
        self.d.watch_ending()
        self.assertFalse(hall.panel.first_time)
        self.assertEqual(before, (self.wallet(), json.dumps(self.manager.state["stats"]["secret_trials"]), self.manager.memory_fragments))
        self.assertEqual(self.events.count(("secret_trial_done", "trial_02")), 1)


class PhaseDialogueHallTests(HallCase):
    def first_line(self, key):
        self.d.use("npc_" + key)
        text = self.hall.dialogue.lines[0].text
        self.d.talk_through()
        return text

    def test_people_say_something_new_after_every_round(self):
        hall = self.enter()
        self.registered()
        said = {0: self.first_line("champion")}
        self.d.win_round(real=False)
        said[1] = self.first_line("champion")
        self.d.fix_bracket()
        self.d.win_round(real=False)
        said[2] = self.first_line("champion")
        self.d.get_stage_key()
        self.d.insert_key()
        self.d.win_round(real=False)
        self.assertIsNone(hall.script)                                     # (no ending until the ceremony)
        said[3] = self.first_line("champion")
        self.assertEqual(said, {p: C.PEOPLE["champion"]["talk"][p]["first"][0][1] for p in range(4)})
        self.assertEqual(self.manager.trial_progress(T.TRIAL_ID)["rounds"], 3)
        self.d.watch_ending()
        self.assertIsInstance(hall.panel, UI.CompletePanel)

    def test_a_restored_night_talks_like_that_night(self):
        for phase, data in PHASE_SAVES.items():
            self.manager.save_trial_progress(T.TRIAL_ID, dict(data, kevin=list(C.KEVIN_PEOPLE)))
            hall = self.enter()
            self.assertEqual(hall.run.phase, phase)
            for key in ("fan", "kid", "attendant"):
                want = C.PEOPLE[key]["talk"][phase]
                if phase == 0 and want.get("kevin"):
                    want = {"first": want["again"][0]}                 # (founder's story heard: not told twice)
                self.assertEqual(self.first_line(key), want["first"][0][1], (phase, key))
            self.d.tap(K.K_ESCAPE)
            self.d.tap(K.K_LEFT)
            self.d.tap(K.K_e)
            self.d.frames(40)

    def test_old_puzzle_talk_is_gone_and_the_clue_can_be_asked_again(self):
        self.manager.save_trial_progress(T.TRIAL_ID, PHASE_SAVES[1])
        hall = self.enter()
        clue = C.PEOPLE["student"]["talk"][1]["clue"][0][1]
        heard = []
        for _ in range(4):
            self.d.use("npc_student")
            heard.append([l.text for l in hall.dialogue.lines])
            self.d.talk_through()
        self.assertIn(clue, heard[0])
        self.assertIn(clue, heard[2])                                     # the testimony comes round again
        everything = " ".join(t for lines in heard for t in lines)
        for t in phase_text("student", 0):
            self.assertNotIn(t, everything)                                # nothing from before the qualifier
        self.d.tap(K.K_ESCAPE)
        self.d.tap(K.K_LEFT)
        self.d.tap(K.K_e)
        self.d.frames(40)
        self.manager.save_trial_progress(T.TRIAL_ID, PHASE_SAVES[2])
        hall = self.enter()
        for _ in range(4):
            self.d.use("npc_student")
            text = " ".join(l.text for l in hall.dialogue.lines)
            self.d.talk_through()
            self.assertNotIn("DANNY", text.upper())                        # the bracket talk is over

    def test_miao_has_her_say_once_a_phase_then_hints(self):
        self.manager.save_trial_progress(T.TRIAL_ID, PHASE_SAVES[1])
        hall = self.enter()
        self.d.use("miao")
        self.assertEqual([l.text for l in hall.dialogue.lines], [t for _, t, _ in C.MIAO_CHAT[1]])
        self.d.talk_through()
        self.d.use("miao")
        self.assertIsNone(hall.dialogue)
        self.assertEqual(hall.bubble.text, T.SLIPS_FIRST)                 # (the referee's slips not read yet)
        self.assertEqual(self.manager.trial_progress(T.TRIAL_ID)["miao"], [1])
        self.d.tap(K.K_ESCAPE)
        self.d.tap(K.K_LEFT)
        self.d.tap(K.K_e)
        self.d.frames(40)
        hall = self.enter()
        self.d.use("miao")
        self.assertIsNone(hall.dialogue)                                   # (saved: she does not repeat herself)

    def test_the_evidence_file_keeps_everything_found(self):
        hall = self.enter()
        self.d.tap(K.K_TAB)
        self.assertIsInstance(hall.panel, UI.EvidencePanel)
        self.assertEqual(hall.panel.items, [])
        self.d.tap(K.K_ESCAPE)
        self.registered()
        self.d.win_round(real=False)
        self.d.use("npc_host")
        self.d.talk_through()                                             # the referee's slips
        self.d.tap(K.K_e)
        self.d.fix_bracket()
        self.d.win_round(real=False)
        self.d.use("photo_board")
        self.d.talk_through()
        self.d.tap(K.K_e)
        self.d.use("schedule")
        self.d.talk_through()
        self.d.tap(K.K_e)
        self.d.frames(5)
        self.d.tap(K.K_TAB)
        self.assertEqual(hall.panel.items, list(T.EVIDENCE))
        for i, kind in enumerate(T.EVIDENCE):
            while hall.panel.index != i:
                self.d.tap(K.K_DOWN)
            self.d.tap(K.K_e)
            want = {"photos": UI.PhotoPanel, "bracket": UI.BracketPanel}.get(kind, UI.DocumentPanel)
            self.assertIsInstance(hall.panel, want, kind)
            self.d.tap(K.K_ESCAPE)
            self.d.frames(3)
            self.assertIsInstance(hall.panel, UI.EvidencePanel)             # back to the file
        self.d.tap(K.K_ESCAPE)
        self.assertIsNone(hall.panel)
        self.d.use("door")                                                  # and it is all still there next visit
        self.d.tap(K.K_LEFT)
        self.d.tap(K.K_e)
        self.d.frames(40)
        hall = self.enter()
        self.d.tap(K.K_TAB)
        self.assertEqual(hall.panel.items, list(T.EVIDENCE))

    def leave_and_enter(self):
        self.d.use("door")
        self.d.tap(K.K_LEFT)
        self.d.tap(K.K_e)
        self.d.frames(40)
        return self.enter()

    def test_what_people_said_goes_in_the_evidence_file(self):
        self.manager.save_trial_progress(T.TRIAL_ID, PHASE_SAVES[1])
        hall = self.enter()
        for key in ("fan", "kid", "student"):                              # (the kid has nothing useful to say)
            self.d.talk(key)
        self.assertEqual(hall.run.heard, ["fan:1", "student:1"])
        self.d.tap(K.K_TAB)
        self.d.tap(K.K_RIGHT)
        panel = hall.panel
        self.assertEqual(panel.tab, 1)
        self.assertEqual([(t, n) for t, n, _ in panel.said], [("fan:1", "TOURNAMENT FAN"), ("student:1", "STUDENT")])
        self.d.tap(K.K_DOWN)
        self.d.tap(K.K_e)
        self.assertIsInstance(hall.panel, UI.SaidPanel)
        self.assertIn("DANNY K. BEAT JUNE P.", " ".join(hall.panel.lines).upper())
        self.assertEqual(hall.panel.when, "AFTER ROUND 01")
        self.d.tap(K.K_ESCAPE)
        self.d.frames(3)
        self.assertIsInstance(hall.panel, UI.EvidencePanel)               # back on the same page, same line
        self.assertEqual((hall.panel.tab, hall.panel.index), (1, 1))
        self.d.tap(K.K_ESCAPE)
        self.assertIsNone(hall.panel)
        hall = self.leave_and_enter()                                       # kept with the save
        self.d.tap(K.K_TAB)
        self.assertEqual([t for t, _, _ in hall.panel.said], ["fan:1", "student:1"])

    def test_tab_inside_the_board_and_back_to_it_untouched(self):
        self.manager.save_trial_progress(T.TRIAL_ID, dict(PHASE_SAVES[1], seen=["poster", "ticket", "ledger"]))
        hall = self.enter()
        self.d.talk("fan")
        self.d.use("npc_host")
        self.d.talk_through()
        self.d.tap(K.K_e)                                                   # (the referee's slips, read)
        board = self.d.open_bracket()
        self.d.tap(K.K_RIGHT)
        name = board.draft.slots[3]
        self.d.tap(K.K_TAB)
        self.assertIsInstance(hall.panel, UI.EvidencePanel)
        self.assertIn("slips", hall.panel.items)
        while hall.panel.items[hall.panel.index] != "slips":
            self.d.tap(K.K_DOWN)
        self.d.tap(K.K_e)
        self.assertIsInstance(hall.panel, UI.DocumentPanel)
        self.assertEqual(hall.panel.kind, "slips")
        self.d.tap(K.K_ESCAPE)
        self.d.frames(3)
        self.d.tap(K.K_RIGHT)                                               # what people said, from the board too
        self.d.tap(K.K_e)
        self.assertIsInstance(hall.panel, UI.SaidPanel)
        self.d.tap(K.K_ESCAPE)
        self.d.frames(3)
        self.d.tap(K.K_ESCAPE)                                              # close the file: the board again
        self.d.frames(3)
        self.assertIs(hall.panel, board)
        self.assertFalse(board.closed)
        self.assertEqual((board.draft.slots[3], board.row), (name, 0))
        self.assertEqual(self.d.fill_bracket(), "ok")                       # and it still works

    def test_tab_inside_the_terminal_and_the_trophy_cabinet(self):
        hall = self.enter()
        self.d.use("terminal")
        term = hall.panel
        self.d.tap(K.K_DOWN)
        code = term.wheels.code
        self.d.tap(K.K_TAB)
        self.assertIsInstance(hall.panel, UI.EvidencePanel)
        self.d.tap(K.K_ESCAPE)
        self.d.frames(3)
        self.assertIs(hall.panel, term)
        self.assertEqual(term.wheels.code, code)
        self.d.tap(K.K_ESCAPE)
        self.d.frames(3)
        self.manager.save_trial_progress(T.TRIAL_ID, dict(PHASE_SAVES[2], seen=["photos"]))
        hall = self.leave_and_enter()
        case = self.d.open_trophies()
        self.d.tap(K.K_DOWN)
        turned = [list(s) for s in case.case.slots]
        self.d.tap(K.K_TAB)
        self.assertEqual(hall.panel.items, ["bracket", "slips", "photos"])
        self.d.tap(K.K_UP)                                                  # (the last one)
        self.d.tap(K.K_e)
        self.assertIsInstance(hall.panel, UI.PhotoPanel)
        self.d.tap(K.K_e)
        self.d.frames(3)
        self.d.tap(K.K_ESCAPE)
        self.d.frames(3)
        self.assertIs(hall.panel, case)
        self.assertEqual([list(s) for s in case.case.slots], turned)

    def test_after_the_final_the_hall_waits_for_the_ceremony(self):
        self.manager.save_trial_progress(T.TRIAL_ID, PHASE_SAVES[3])
        hall = self.enter()
        self.d.seconds(3.0)
        self.assertIsNone(hall.script)
        self.assertEqual(hall.last_notice, C.TITLE)
        self.assertFalse(self.manager.trial_done(T.TRIAL_ID))
        self.d.use("npc_host")
        self.d.talk_through()
        self.assertTrue(getattr(hall.panel, "ceremony", False))
        self.d.tap(K.K_RIGHT)                                               # NOT YET
        self.d.tap(K.K_e)
        self.d.frames(10)
        self.assertIsNone(hall.script)
        self.d.watch_ending()
        self.assertTrue(self.manager.trial_done(T.TRIAL_ID))
        self.d.tap(K.K_RIGHT)                                               # STAY IN THE HALL: a replay, from phase 0
        self.d.tap(K.K_e)
        self.d.frames(20)
        self.assertEqual(hall.run.phase, 0)
        self.assertEqual(self.first_line("kid"), C.PEOPLE["kid"]["talk"][0]["first"][0][1])
        self.assertTrue(self.manager.has_memory_fragment(T.TRIAL_ID))


class SinglePlayerTests(HallCase):
    def test_one_player_one_body_and_no_versus_mode(self):
        hall = self.enter()
        self.assertEqual(len(self.game.session.players), 1)
        self.assertIs(hall.avatar, self.game.session.primary.avatar)
        self.registered()
        bout = self.d.start_round()
        self.d.tap(K.K_RETURN)
        self.d.tap(K.K_RETURN)
        self.d.frames(5)
        fighters = [bout.bout.player] + bout.bout.enemies
        self.assertEqual(sum(1 for f in fighters if f.name in ROSTER), 1)        # one human fighter, one CPU opponent
        self.assertEqual(len(bout.bout.enemies), 1)
        self.assertFalse(hasattr(bout.brawl, "player_two"))

    def test_the_arcade_floor_cabinet_still_runs_the_full_game(self):
        import scenes
        from neon_brawl_scene import NeonBrawlScene
        self.assertIs(scenes.MINIGAME_SCENES.get("neon_brawl"), NeonBrawlScene)
        brawl = BrawlGame(font.get_font())
        self.assertEqual(brawl.screen, "intro")
        self.assertIs(type(Campaign().player).__name__, "PlayerFighter")


# ===================================================================== words
def all_text():
    rows = []
    for spec in C.PEOPLE.values():
        rows.append(spec["name"])
        for conv in spec.get("talk", {}).values():
            rows += [t for _, t, _ in conv["first"] + conv.get("clue", ())]
            for lines in conv["again"]:
                rows += [t for _, t, _ in lines]
    for lines in C.MIAO_CHAT.values():
        rows += [t for _, t, _ in lines]
    rows += [v for v in C.OBJECTIVES.values() if isinstance(v, str)] + list(C.OBJECTIVES["fight"].values())
    rows += list(UI.EvidencePanel.LABELS.values()) + [t for _, t, _ in C.HOST["ceremony"]]
    for group in (C.OPENING, C.REALIZATION, C.REGISTERED, C.ENDING_CHEER, C.ENDING_GOODBYE, C.ENDING_FINAL, C.ENDING_FLICKER, C.CORE_LINE,
                  C.HOST["unregistered"], C.HOST["unregistered_again"], C.HOST["lost"], C.HOST["forfeit"]):
        rows += [t for _, t, _ in group]
    for d in (C.HOST["offer"], C.HOST["won"]):
        for lines in d.values():
            rows += [t for _, t, _ in lines]
    for info in C.LOOKS.values():
        rows += [t for _, t, _ in info["lines"]]
        for lines in info.get("again", ()):
            rows += [t for _, t, _ in lines]
    rows += list(C.SYSTEM_MESSAGES) + list(C.FINAL_CARD) + [C.TITLE, C.OBJECTIVE, T.BADGE_NAME, T.FRAGMENT_NAME]
    rows.append(json.dumps(C.DOCS))
    run = T.TournamentRun()
    rows.append(T.hint(run))
    for msg in ("B10", "C01", "B14", "B07", "B12", "A00"):
        rows.append(T.check_code(msg)[1])
    rows += [o.title for o in B.OPPONENTS.values()] + [r.stage for r in T.ROUNDS]
    rows += list(T.BRACKET_RULES) + list(T.BRACKET_POOL) + [T.KEY_NAME, T.ANOMALY, C.PHOTO_STAMP]
    rows += [f"{p['banner']} {p['year']} {p['caption']}" for p in C.PHOTOS]
    for tiers in T.HINTS.values():
        rows += list(tiers)
    for group in ("bracket", "bracket_done", "key_missing", "key_found", "key_used"):
        rows += [t for _, t, _ in C.HOST[group]]
    return rows


class ContentTests(unittest.TestCase):
    def test_english_only_and_every_glyph_exists(self):
        glyphs = set(font._GLYPHS) | {" "}
        for text in all_text():
            text = text.replace("\\n", " ").replace('\\"', '"')
            self.assertTrue(text.isascii(), text)
            if text.startswith("{"):
                text = re.sub(r'[{}\[\]:,"]|null', " ", text)
            missing = {ch for ch in text.upper() if ch not in glyphs}
            self.assertFalse(missing, (text, missing))

    def test_the_founder_is_named_only_by_people_and_by_miao(self):
        named = [k for k in C.PEOPLE if any("KEVIN" in t.upper() for conv in C.PEOPLE[k].get("talk", {}).values()
                                            for lines in (conv["first"], conv.get("clue", ())) + conv["again"] for _, t, _ in lines)]
        self.assertGreaterEqual(len(named), 3)
        self.assertEqual(sorted(named), sorted(C.KEVIN_PEOPLE))
        self.assertLess(len(named), len(C.PEOPLE) // 2)                      # not everybody repeats the name
        for group in (C.OPENING, C.REGISTERED, C.ENDING_CHEER, C.ENDING_GOODBYE, C.ENDING_FINAL, C.ENDING_FLICKER, C.CORE_LINE) + tuple(C.MIAO_CHAT.values()):
            self.assertFalse(any("KEVIN" in t.upper() for _, t, _ in group))
        self.assertNotIn("KEVIN", json.dumps(C.DOCS).upper())
        self.assertNotIn("KEVIN", " ".join(C.SYSTEM_MESSAGES + C.FINAL_CARD).upper())
        for info in C.LOOKS.values():
            self.assertFalse(any("KEVIN" in t.upper() for _, t, _ in info["lines"]))

    def test_miao_guesses_who_kevin_was_but_does_not_remember_him(self):
        # allowed: he founded the arcade, he is probably the student from the Trial 01 bedroom, she feels they were close
        text = " ".join(t for _, t, _ in C.REALIZATION).upper()
        for allowed in ("KEVIN", "BEDROOM", "BUILT AN ENTIRE ARCADE", "HE REALLY DID IT", "KNEW HIM", "REALLY CLOSE"):
            self.assertIn(allowed, text)
        self.assertTrue(any(w in text for w in ("MAYBE", "THINK", "MIGHT")))          # a guess and a feeling, not a fact
        # not allowed: a full memory of him, shared moments told as fact, his departure, or his farewell
        miao = " ".join(t for group in (C.REALIZATION, C.ENDING_FLICKER) + tuple(C.MIAO_CHAT.values())
                        for s_, t, _ in group if s_ == "MIAO MEOW").upper()
        for banned in ("I REMEMBER", "BEST FRIEND", "WE USED TO", "HE USED TO", "HE LEFT", "WHY HE LEFT", "GOODBYE",
                       "FAREWELL", "RECORDING", "LAST MESSAGE", "FINAL MESSAGE", "HE SAID TO ME"):
            self.assertNotIn(banned, miao, banned)
        self.assertEqual(sum("KEVIN" in t.upper() for group in C.MIAO_CHAT.values() for _, t, _ in group), 0)
        self.assertFalse(hasattr(C, "MIAO_KEVIN_ECHO"))                              # no reminder every round
        ending = " ".join(t for _, t, _ in C.ENDING_FLICKER).upper()
        self.assertIn("JUST... A FEELING", ending)

    def test_the_journal_of_trial_01_is_echoed(self):
        text = " ".join(all_text()).upper()
        for word in ("NYCU", "WIND", "INSTANT NOODLES", "ASSIGNMENT", "HOMEWORK", "3 AM", "DEBUG"):
            self.assertIn(word, text)

    def test_the_mysteries_stay_mysteries(self):
        text = " ".join(all_text()).upper()
        for banned in ("FINAL MESSAGE", "LAST MESSAGE", "SHUT DOWN", "SHUTDOWN", "CLOSED FOREVER", "PASSED AWAY", "DIED",
                       "KEVIN IS PLAYER_000", "PLAYER_000 IS KEVIN", "TRAPPED", "EVIL"):
            self.assertIsNone(re.search(r"\b" + re.escape(banned) + r"\b", text), banned)
        for row in all_text():
            if "PLAYER_000" in row.upper():
                self.assertNotIn("KEVIN", row.upper())

    def test_the_ending_words_are_the_ones_asked_for(self):
        self.assertEqual(C.SYSTEM_MESSAGES, ("ACTIVE PLAYERS: DECREASING", "SESSION EXTENSION: ENABLED", "EXIT CONTROL: OVERRIDE REQUESTED"))
        self.assertEqual(C.FINAL_CARD, ("MEMORY FRAGMENT 02 RECOVERED.", "TRIAL 02 COMPLETE."))
        self.assertEqual(C.CORE_LINE[0][:2], ("CORE", "One more game?"))
        self.assertIn("99%", " ".join(open(os.path.join(HERE, "unbeaten_art.py"), encoding="utf-8").read().split()))

    def test_drawing_every_panel_and_state_works(self):
        surf = pygame.Surface((400, 300))
        for kind in C.DOCS:
            p = UI.DocumentPanel(kind)
            p.update(1.7)
            p.draw(surf)
        run = T.TournamentRun()
        tp = UI.TerminalPanel(run)
        tp.draw(surf)
        tp.reply = ("ok", "ENTRY RECORD RESTORED.")
        tp.draw(surf)
        UI.CompletePanel(True).draw(surf)
        for mode in ("title", "round", "win", "complete", "off"):
            A.stage_screen(1.0, mode, 2, 1.0)
        A.leaderboard(1.0, 1.0)
        for name in ("rookie", "challenger", "champion"):
            scene = B.TournamentBrawl(font.get_font(), None, T.ROUNDS[list(B.OPPONENTS).index(name)])
            scene.draw(surf)
            scene.begin()
            scene.update(0.1)
            scene.draw(surf)


if __name__ == "__main__":
    unittest.main()
