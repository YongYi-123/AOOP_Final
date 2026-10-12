"""Arcade world polish: seated avatars are painted over their stool (and ordered correctly against
walkers), and petting a cat answers with exactly one gentle sound through the hub's effects.

Run headless from this folder:   python -m unittest test_world_polish -v
"""
import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import audio_manager as am  # noqa: E402
import cat_voice  # noqa: E402
import dataclasses  # noqa: E402
import random  # noqa: E402

from cat import PERSONALITIES, PET_SFX, FRIENDLY, CatNPC, CatProfile, CatState  # noqa: E402
from cat_sprites import CatLook  # noqa: E402
from room_scene import ENTRIES  # noqa: E402
from settings import CATS, ROOM_IDS  # noqa: E402
from game import Game  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player_profile import PlayerProfile  # noqa: E402
from room_testing import goto_room  # noqa: E402
from stations import Seat  # noqa: E402

DT = 1 / 60
PET_SOUNDS = {"pet", "pet_b", "pet_c", "purr"}
OLD_CATS = {"miso", "pixel", "mochi", "luna", "bean"}


def key_event(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


class Base(unittest.TestCase):
    ROOM = "arcade_floor"
    PLAYERS = 2

    def setUp(self):
        profiles = [PlayerProfile(profile_id=f"wp{i}", display_name=f"P{i}") for i in range(self.PLAYERS)]
        self.game = Game(session=LocalSession(profiles))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, self.ROOM)
        self.frames(80)
        for _ in range(4):
            if self.room.modal is None:
                break
            self.press(pygame.K_ESCAPE, 10)

    def frames(self, n=1):
        for _ in range(n):
            self.game.step([], DT)

    def press(self, *keys, after=1):
        self.game.step([key_event(k) for k in keys], DT)
        self.frames(after - 1)


# ------------------------------------------------------------------ seat depth
class SeatDepthTests(Base):
    def seats(self):
        return [p for p in self.room.props if isinstance(p, Seat)]

    def sit(self, avatar, seat, key):
        avatar.x, avatar.y = seat.zone.centerx, seat.zone.bottom - 3
        self.frames(4)
        self.press(key, after=30)
        self.assertTrue(avatar.sitting)

    def order(self):
        """The back-to-front list the room draws (the same sort as RoomScene.draw)."""
        things = self.room.drawables() + self.room.players + self.room.cats.drawables()
        return sorted(things, key=lambda t: t.sort_y)

    def test_there_are_stools_to_test(self):
        self.assertGreaterEqual(len(self.seats()), 3)

    def test_walkers_sort_behind_and_in_front_of_every_stool_by_their_feet(self):
        a, b = self.room.players
        for seat in self.seats():
            a.x, a.y = seat.footprint.centerx, seat.footprint.top - 8       # feet behind the stool
            b.x, b.y = seat.footprint.centerx, seat.footprint.bottom + 8    # feet in front of it
            order = self.order()
            self.assertLess(order.index(a), order.index(seat))
            self.assertGreater(order.index(b), order.index(seat))

    def test_a_seated_player_is_painted_over_the_stool_from_any_approach(self):
        a = self.room.players[0]
        for seat in self.seats():
            a.stop_action()
            a.x, a.y = seat.zone.centerx, seat.zone.top + 2                 # approached from behind
            self.frames(4)
            self.press(pygame.K_e, after=30)
            self.assertTrue(a.sitting)
            self.assertLess(a.y, seat.sort_y)                               # the body itself is "behind" the stool ...
            order = self.order()
            self.assertGreater(order.index(a), order.index(seat))           # ... but the sitter is drawn over it
            a.stop_action()
            self.assertIsNone(a.seat_depth)
            self.assertEqual(a.sort_y, a.y)                                 # standing again: plain feet sorting

    def test_draw_calls_paint_the_stool_before_its_sitter(self):
        a = self.room.players[0]
        seat = self.seats()[0]
        self.sit(a, seat, pygame.K_e)
        a.y = seat.footprint.top - 6                                        # worst case: body behind the stool
        calls = []
        with mock.patch.object(Seat, "draw", lambda s, surf: calls.append(("seat", s))), \
                mock.patch.object(type(a), "draw", lambda p, surf: calls.append(("player", p))):
            self.room.draw(pygame.Surface((self.game.screen.get_size())))
        names = [(k, t) for k, t in calls if t is seat or t is a]
        self.assertEqual([k for k, _ in names], ["seat", "player"])

    def test_one_player_sits_while_the_other_walks_behind_and_in_front(self):
        a, b = self.room.players
        seat = self.seats()[0]
        self.sit(a, seat, pygame.K_e)
        seated_y = a.sort_y
        b.x, b.y = seat.footprint.centerx, seat.footprint.top - 10          # P2 walks behind
        order = self.order()
        self.assertLess(order.index(b), order.index(seat))
        self.assertLess(order.index(b), order.index(a))
        b.y = seat.footprint.bottom + 10                                    # P2 walks in front
        order = self.order()
        self.assertGreater(order.index(b), order.index(a))
        self.assertGreater(order.index(b), order.index(seat))
        self.assertEqual(a.sort_y, seated_y)                                # P1's depth never changed
        self.assertFalse(b.sitting)
        self.assertIsNone(b.seat_depth)

    def test_both_players_sit_on_different_stools_independently(self):
        a, b = self.room.players
        s0, s1 = self.seats()[:2]
        self.sit(a, s0, pygame.K_e)
        self.sit(b, s1, pygame.K_RETURN)
        self.assertEqual((a.seat, b.seat), (s0.seat_pos, s1.seat_pos))
        self.assertEqual((a.seat_depth, b.seat_depth), (s0.sort_y + 0.5, s1.sort_y + 0.5))
        self.press(pygame.K_e, after=3)                                     # P1 stands; P2 stays seated
        self.assertFalse(a.sitting)
        self.assertTrue(b.sitting)
        self.assertEqual(b.seat_depth, s1.sort_y + 0.5)

    def test_footprints_zones_and_seat_positions_are_unchanged(self):
        for x, seat in zip((123, 207, 291), self.seats()):
            self.assertEqual(seat.footprint, pygame.Rect(x + 1, 192, 12, 5))
            self.assertEqual(seat.seat_pos[1], 184 + 8)
        a = self.room.players[0]
        seat = self.seats()[0]
        feet = None
        a.x, a.y = seat.zone.centerx, seat.zone.bottom - 3
        self.frames(4)
        feet = a.feet.copy()
        self.press(pygame.K_e, after=30)
        self.assertEqual(a.feet, feet)                                      # collision box stays put

    def test_other_props_keep_their_plain_footprint_sort(self):
        for prop in self.room.props:
            if not isinstance(prop, Seat):
                self.assertEqual(prop.sort_y, prop.footprint.bottom)


# ------------------------------------------------------------------ petting
class PetFixture(Base):
    ROOM = "home"

    def setUp(self):
        super().setUp()
        self.cat = next(c for c in self.room.cats if c.personality is FRIENDLY)
        self.cat.personality = dataclasses.replace(FRIENDLY, purr=0.0)      # (purring has its own tests below)
        for c in self.room.cats:
            if c is not self.cat:
                c.set_state(CatState.SLEEP, 999)
                c.chat_timer = 999
        self.a, self.b = self.room.players
        self.b.x, self.b.y = 20.0, 20.0
        self.place(self.a)
        self.played = []
        self.game.audio.play = lambda name: self.played.append(name)       # what the voice routes through
        cat_voice.sfx_route = self.game.audio.play

    def place(self, avatar, dx=-14):
        self.cat.set_state(CatState.SIT, 999)
        self.cat.chat_timer = 999
        avatar.x, avatar.y = self.cat.x + dx, self.cat.y
        self.frames(4)
        self.assertIs(avatar.nearby_cat, self.cat)

    def pet_sounds(self):
        return [n for n in self.played if n in PET_SOUNDS]



class PettingTests(PetFixture):
    def test_a_pet_plays_exactly_one_gentle_sound(self):
        self.press(pygame.K_e, pygame.K_e)                                  # even a double press
        self.assertEqual(self.cat.state, CatState.PET)
        self.assertEqual(len(self.pet_sounds()), 1)
        self.assertEqual(self.cat.voice.plays, 1)
        self.assertGreater(self.cat.heart_time, 0)
        self.assertTrue(self.cat.bubble.visible)

    def test_the_sound_matches_the_bubble_and_comes_from_the_cats_own_options(self):
        self.press(pygame.K_e)
        kind = dict(self.cat.personality.phrases)[self.cat.bubble.text]
        self.assertIn(self.pet_sounds()[0], PET_SFX[kind])

    def test_holding_or_mashing_the_key_cannot_spam(self):
        for _ in range(60):
            self.press(pygame.K_e)
        self.assertEqual(len(self.pet_sounds()), 1)

    def test_it_can_be_petted_again_after_the_cooldown_with_a_second_sound(self):
        self.press(pygame.K_e)
        self.frames(int((CatNPC.PET_TIME + CatNPC.PET_COOLDOWN) / DT) + 6)
        self.cat.set_state(CatState.SIT, 999)
        self.cat.x, self.cat.y = self.a.x + 14, self.a.y
        self.frames(4)
        self.press(pygame.K_e)
        self.assertEqual(len(self.pet_sounds()), 2)

    def test_replies_vary_between_pets(self):
        names = set()
        for _ in range(40):
            self.cat.pet_cooldown = 0
            self.cat.voice.last_time = None
            self.cat.state = CatState.SIT
            self.cat.pet(self.room.cats)
            names.add(self.played[-1])
        self.assertGreaterEqual(len(names & PET_SOUNDS), 2)

    def test_p2_pets_independently_and_p1_is_untouched(self):
        self.place(self.b)
        self.a.x, self.a.y = 20.0, 20.0
        self.frames(4)
        self.press(pygame.K_RETURN)
        self.assertEqual(self.b.action, "pet")
        self.assertIsNone(self.a.action)
        self.assertEqual(len(self.pet_sounds()), 1)

    def test_both_pressing_at_once_counts_once(self):
        self.place(self.b, dx=14)
        self.press(pygame.K_e, pygame.K_RETURN)
        self.assertEqual(len(self.pet_sounds()), 1)

    def test_every_cat_sound_kind_has_valid_effect_files(self):
        self.assertEqual(set(PET_SFX), set(cat_voice.KINDS))
        for names in PET_SFX.values():
            for name in names:
                self.assertIn(name, am.SFX_FILES)
                self.assertIn(name, am.PRIORITY)
        self.assertGreaterEqual(am.PRIORITY["purr"], am.PRIORITY["pet"])  # the small effects never cut a purr

    def test_it_goes_through_the_real_effects_volume_and_mute(self):
        game = self.game
        del game.audio.play                                                # back to the real AudioManager.play
        cat_voice.sfx_route = game.audio.play
        requested = lambda: sum(game.audio.sfx_requested.get(n, 0) for n in PET_SOUNDS)
        game.audio.set_muted(True)
        self.press(pygame.K_e)
        self.assertEqual(requested(), 0)                                   # muted: nothing is even requested
        self.assertEqual(self.cat.state, CatState.PET)                     # ... but the cat still reacts
        game.audio.set_muted(False)
        self.frames(int((CatNPC.PET_TIME + CatNPC.PET_COOLDOWN) / DT) + 6)
        self.cat.set_state(CatState.SIT, 999)
        self.cat.x, self.cat.y = self.a.x + 14, self.a.y
        self.frames(4)
        self.press(pygame.K_e)
        self.assertEqual(requested(), 1)

    def test_other_cat_sounds_are_untouched(self):
        voice = cat_voice.CatVoice()
        voice.play("meow", 0.0)                                            # ambient chatter: no named effect
        self.assertEqual(self.played, [])
        voice.play("meow", 5.0, sfx="pet")
        self.assertEqual(self.played, ["pet"])

    def test_mochi_still_meows_through_her_own_effect(self):
        room = goto_room(self.game, "prize_plaza")
        self.frames(5)
        self.game.audio.play = mock.Mock()
        room.mochi.sound("meow")
        self.game.audio.play.assert_called_with("meow")


# ------------------------------------------------------------------ purring
class PurrTests(PetFixture):
    """Same cat and room as the petting tests; here the cat purrs (purr=1.0) unless a test says otherwise."""

    def setUp(self):
        super().setUp()
        self.cat.personality = dataclasses.replace(FRIENDLY, purr=1.0)

    def wav_seconds(self, name):
        import wave
        w = wave.open(os.path.join(am.ASSET_DIR, "sfx", f"{name}.wav"))
        return w.getnframes() / w.getframerate()

    def test_a_pet_with_a_purr_is_one_meow_then_one_purr_after_it_finishes(self):
        self.press(pygame.K_e, pygame.K_e)
        self.assertEqual([n for n in self.played if n in PET_SOUNDS and n != "purr"].__len__(), 1)
        self.assertNotIn("purr", self.played)                              # not at the same moment
        self.frames(int(CatNPC.PURR_DELAY / DT) + 2)
        self.assertEqual(self.played[-1], "purr")
        self.assertEqual(len(self.pet_sounds()), 2)                        # exactly meow + purr, nothing else
        self.frames(120)
        self.assertEqual(len(self.pet_sounds()), 2)                        # and no more later

    def test_the_purr_waits_for_the_longest_meow_so_it_cannot_cut_it_off(self):
        longest = max(self.wav_seconds(n) for n in ("pet", "pet_b", "pet_c"))
        self.assertGreater(CatNPC.PURR_DELAY, longest)
        self.assertLess(self.wav_seconds("purr"), 0.8)                     # still a short effect file

    def test_the_small_effects_cannot_interrupt_a_playing_purr(self):
        for small in ("pet", "pet_b", "pet_c", "meow", "footstep", "sit", "emote"):
            self.assertGreaterEqual(am.PRIORITY["purr"], am.PRIORITY[small], small)

    def test_the_real_audio_manager_plays_the_purr_after_the_meow_without_dropping_either(self):
        game = self.game
        del game.audio.play
        cat_voice.sfx_route = game.audio.play
        if not game.audio.enabled:
            self.skipTest("no audio device in this environment")
        self.press(pygame.K_e)
        self.frames(int(CatNPC.PURR_DELAY / DT) + 4)
        sent = game.audio.sfx_requested
        self.assertEqual(sum(sent.get(n, 0) for n in ("pet", "pet_b", "pet_c")), 1)
        self.assertEqual(sent.get("purr", 0), 1)
        self.assertEqual(game.audio.sfx_dropped.get("purr", 0), 0)

    def test_muted_means_no_purr_is_requested_either(self):
        game = self.game
        del game.audio.play
        cat_voice.sfx_route = game.audio.play
        game.audio.set_muted(True)
        self.press(pygame.K_e)
        self.assertEqual(self.cat.state, CatState.PET)                     # it still reacts (heart, bubble) ...
        self.frames(int(CatNPC.PURR_DELAY / DT) + 4)
        self.assertEqual(sum(game.audio.sfx_requested.get(n, 0) for n in PET_SOUNDS), 0)   # ... silently

    def test_mashing_cannot_queue_more_purrs(self):
        for _ in range(90):
            self.press(pygame.K_e)
        self.assertEqual(self.played.count("purr"), 1)
        self.assertEqual(len(self.pet_sounds()), 2)

    def test_p1_and_p2_pressing_together_make_one_meow_and_one_purr(self):
        self.place(self.b, dx=14)
        self.press(pygame.K_e, pygame.K_RETURN)
        self.frames(int(CatNPC.PURR_DELAY / DT) + 4)
        self.assertEqual(len(self.pet_sounds()), 2)
        self.assertEqual(self.played.count("purr"), 1)

    def test_p2_alone_gets_the_purr_and_p1_is_untouched(self):
        self.place(self.b)
        self.a.x, self.a.y = 20.0, 20.0
        self.frames(4)
        self.press(pygame.K_RETURN)
        self.frames(int(CatNPC.PURR_DELAY / DT) + 4)
        self.assertEqual(self.played.count("purr"), 1)
        self.assertIsNone(self.a.action)

    def test_leaving_the_room_drops_a_purr_that_has_not_started(self):
        self.press(pygame.K_e)
        self.cat.settle()                                                  # what pausing the hub does
        self.frames(int(CatNPC.PURR_DELAY / DT) + 4)
        self.assertNotIn("purr", self.played)

    def test_a_sleeping_cat_petted_purrs_alone_without_a_second_purr(self):
        self.cat.personality = dataclasses.replace(FRIENDLY, purr=1.0, sleepy_phrases=(("prrr...", "prrr"),))
        self.cat.set_state(CatState.SLEEP, 999)
        self.cat.pet_cooldown = 0
        self.frames(2)
        self.cat.pet(self.room.cats)
        self.frames(60)
        self.assertEqual(self.played, ["purr"])

    def test_purr_chance_follows_the_personalities(self):
        chance = {name: p.purr for name, p in PERSONALITIES.items()}
        self.assertGreaterEqual(chance["sleepy"], 0.7)
        self.assertGreaterEqual(chance["friendly"], 0.5)
        self.assertTrue(chance["regal"] < chance["friendly"] and chance["regal"] > chance["grumpy"])
        self.assertTrue(chance["grumpy"] > 0 and chance["grumpy"] <= 0.15)            # rare, but it can surprise
        self.assertTrue(0 < chance["playful"] < chance["friendly"])                  # usually chirps
        self.assertTrue(0 < chance["shy"] < chance["friendly"])

    def test_measured_purr_rates_match_the_chances(self):
        cat_voice.sfx_route = lambda name: None
        for name, p in PERSONALITIES.items():
            cat = self.dummy(p, seed=11)
            purrs = 0
            for _ in range(600):
                cat.state, cat.pet_cooldown, cat.purr_in = CatState.SIT, 0, None
                cat.voice.last_time = None
                cat.pet(self.room.cats)
                purrs += cat.purr_in is not None or cat.bubble.text.startswith("prrr")
            self.assertAlmostEqual(purrs / 600, max(p.purr, 0), delta=0.2 + 0.0, msg=name) if p.purr < 0.35 \
                else self.assertGreater(purrs / 600, p.purr - 0.2, name)

    def dummy(self, personality, seed=1):
        profile = CatProfile("t", "T", CatLook(fur=(200, 200, 200), shade=(120, 120, 120)), personality)
        return CatNPC(profile, [(100, 100)], random.Random(seed))

    def test_the_purr_file_is_audible_not_a_bare_80hz_sine(self):
        import array
        import math
        import wave
        w = wave.open(os.path.join(am.ASSET_DIR, "sfx", "purr.wav"))
        rate = w.getframerate()
        d = [x / 32768 for x in array.array("h", w.readframes(w.getnframes()))]
        rms = math.sqrt(sum(x * x for x in d) / len(d))
        self.assertGreater(rms, 0.08)                                      # not faint
        self.assertLess(max(map(abs, d)), 0.7)                             # not loud
        win = int(rate * 0.01)                                             # a purr pulses (~25 Hz): the loudness breathes
        env = [math.sqrt(sum(x * x for x in d[i:i + win]) / win) for i in range(len(d) // 5, 4 * len(d) // 5, win)]
        self.assertGreater((max(env) - min(env)) / max(env), 0.4)

        def power(freq):
            k = 2 * math.cos(2 * math.pi * freq / rate)
            s1 = s2 = 0.0
            for x in d:
                s1, s2 = x + k * s1 - s2, s1
            return s1 * s1 + s2 * s2 - k * s1 * s2
        low = power(80)
        upper = sum(power(f) for f in (210, 315, 420, 525, 630, 840))      # harmonics small speakers can reproduce
        self.assertGreater(upper, low)


# ------------------------------------------------------------------ personalities
class PersonalityTests(Base):
    ROOM = "home"

    def dummy_cat(self, personality, seed=1):
        profile = CatProfile("t", "T", CatLook(fur=(200, 200, 200), shade=(120, 120, 120)), personality)
        return CatNPC(profile, [(100, 100)], random.Random(seed))

    def test_the_six_requested_types_exist_and_are_data_not_subclasses(self):
        self.assertTrue({"shy", "friendly", "sleepy", "playful", "grumpy", "regal"} <= set(PERSONALITIES))
        for name, p in PERSONALITIES.items():
            self.assertEqual(p.name, name)
        for cat in (c for rid in ROOM_IDS for c in self.game.hub.room(rid).cats):
            self.assertIs(type(cat), CatNPC)

    def test_every_cat_has_a_known_personality_a_unique_id_and_flavor_data(self):
        ids = [d["id"] for d in CATS]
        self.assertEqual(len(ids), len(set(ids)))
        for d in CATS:
            self.assertIn(d["personality"], PERSONALITIES)
        used = {d["personality"] for d in CATS}
        self.assertTrue({"friendly", "shy", "sleepy", "playful", "grumpy", "regal", "curious", "lazy"} <= used)

    def test_every_personality_answers_a_pet_rewardingly_with_a_known_sound(self):
        for name, p in PERSONALITIES.items():
            cat = self.dummy_cat(p)
            played = []
            cat_voice.sfx_route = played.append
            self.assertTrue(cat.pet(self.room.cats), name)
            self.assertEqual(cat.state, CatState.PET, name)
            self.assertGreaterEqual(cat.heart_time, p.heart[0], name)           # grumpy ones still get a heart
            self.assertTrue(cat.bubble.visible, name)
            self.assertEqual(len(played), 1, name)
            self.assertIn(played[0], [n for names in PET_SFX.values() for n in names], name)
            for _, kind in p.phrases + p.sleepy_phrases:
                self.assertIn(kind, PET_SFX, name)

    def test_reactions_differ_by_personality(self):
        grumpy, playful, regal = (PERSONALITIES[n] for n in ("grumpy", "playful", "regal"))
        self.assertLess(grumpy.pet_time, 1.0)                                    # shorter
        self.assertLess(grumpy.heart[1], playful.heart[0])                       # smaller heart
        self.assertGreater(playful.hop, 0)
        self.assertTrue(regal.sparkle)
        self.assertEqual(PERSONALITIES["shy"].hop, 0)
        c = self.dummy_cat(grumpy)
        c.pet(self.room.cats)
        self.assertAlmostEqual(c.timer, CatNPC.PET_TIME * grumpy.pet_time)

    def test_repeated_pets_vary(self):
        cat = self.dummy_cat(PERSONALITIES["playful"], seed=7)
        cat_voice.sfx_route = lambda name: None
        hearts, texts = set(), set()
        for _ in range(30):
            cat.state, cat.pet_cooldown = CatState.SIT, 0
            cat.voice.last_time = None
            cat.pet(self.room.cats)
            hearts.add(round(cat.heart_time, 2))
            texts.add(cat.bubble.text)
        self.assertGreater(len(hearts), 5)
        self.assertGreaterEqual(len(texts), 2)

    def test_the_hop_lifts_only_a_playful_cat_while_it_is_petted(self):
        playful, grumpy = self.dummy_cat(PERSONALITIES["playful"]), self.dummy_cat(PERSONALITIES["grumpy"])
        for cat in (playful, grumpy):
            cat.state = CatState.PET
        lifts = set()
        for i in range(40):
            playful.time = i / 20
            lifts.add(playful._hop())
        self.assertTrue(max(lifts) > 0 and max(lifts) <= PERSONALITIES["playful"].hop)
        self.assertEqual(grumpy._hop(), 0)
        playful.state = CatState.SIT
        self.assertEqual(playful._hop(), 0)                                      # normal idle is untouched

    def test_new_personalities_idle_wander_and_never_get_stuck(self):
        for name in ("sleepy", "playful", "grumpy", "regal"):
            cat = self.dummy_cat(PERSONALITIES[name], seed=3)
            cat.x, cat.y = 150.0, 150.0
            states = set()
            for _ in range(60 * 60):
                cat.update(DT, self.room.cats)
                states.add(cat.state)
            self.assertIn(CatState.SIT, states | {CatState.IDLE}, name)


# ------------------------------------------------------------------ population
class PopulationTests(Base):
    PLAYERS = 1

    def rooms(self):
        return {rid: self.game.hub.room(rid) for rid in ROOM_IDS}

    def test_every_room_has_cats_and_the_new_ones_have_their_own_zones(self):
        rooms = self.rooms()
        self.assertEqual(sum(len(r.cats) for r in rooms.values()), len(CATS))
        self.assertGreaterEqual(len(CATS), 9)
        for rid, room in rooms.items():
            self.assertGreaterEqual(len(room.cats), 2, rid)
            self.assertLessEqual(len(room.cats), 6, rid)
        self.assertIn("nimbus", [c.profile.id for c in rooms["home"].cats])
        self.assertEqual({c.profile.id for c in rooms["prize_plaza"].cats}, {"tango", "duchess"})
        self.assertTrue({"pixel", "dash", "pepper"} <= {c.profile.id for c in rooms["arcade_floor"].cats})

    def test_spots_are_clear_and_away_from_stations_exits_and_arrival_points(self):
        for rid, room in self.rooms().items():
            solids = list(room.solids)
            targets = [m.zone for m in room.machines] + [p.zone for p in room.props if hasattr(p, "zone")]
            targets += [e.zone for e in room.exits]
            for cat in room.cats:
                for spot in cat.spots:
                    self.assertTrue(room.cats.is_free(spot), (rid, cat.name, spot))
                    feet = CatNPC.feet_at(*spot).inflate(*((0, 0) if cat.profile.id in OLD_CATS else (6, 6)))   # (the new cats keep a margin)
                    self.assertEqual(feet.collidelist(targets), -1, (rid, cat.name, spot))
                    for pos, _ in ENTRIES.values():                      # nobody on a doorstep / spawn point
                        self.assertGreater(abs(pos[0] - spot[0]) + abs(pos[1] - spot[1]), 30, (cat.name, spot))
                    self.assertEqual(feet.collidelist(solids), -1, (rid, cat.name, spot))

    def test_homes_do_not_cluster(self):
        for rid, room in self.rooms().items():
            homes = [c.spots[0] for c in room.cats]
            for i, a in enumerate(homes):
                for b in homes[i + 1:]:
                    self.assertGreater(abs(a[0] - b[0]) + abs(a[1] - b[1]), 40, (rid, a, b))

    def test_every_station_and_exit_stays_reachable_with_all_cats_at_home(self):
        """Flood-fill the player's feet over a 4 px grid with every cat's home as an obstacle."""
        for rid, room in self.rooms().items():
            blocks = list(room.solids) + [CatNPC.feet_at(*c.spots[0]) for c in room.cats]
            fw, fh = room.players[0].FEET_W, room.players[0].FEET_H

            def free(x, y):
                return pygame.Rect(x - fw // 2, y - fh, fw, fh).collidelist(blocks) == -1

            start = tuple(int(v) for v in ENTRIES["spawn"][0])
            step, seen, todo = 4, {start}, [start]
            while todo:
                x, y = todo.pop()
                for nx, ny in ((x + step, y), (x - step, y), (x, y + step), (x, y - step)):
                    if (nx, ny) not in seen and free(nx, ny):
                        seen.add((nx, ny))
                        todo.append((nx, ny))
            goals = [m.zone for m in room.machines] + [p.zone for p in room.props if hasattr(p, "zone")]
            goals += [e.zone for e in room.exits]
            for zone in goals:
                self.assertTrue(any(zone.collidepoint(p) for p in seen), (rid, zone))

    def test_other_cats_still_pet_and_idle_after_the_change(self):
        room = self.game.hub.room("arcade_floor")
        for cat in room.cats:
            self.assertTrue(cat.can_pet, cat.name)
        pixel = room.cats.get("pixel")
        self.assertIs(pixel.personality, PERSONALITIES["curious"])
        self.assertEqual(room.cats.get("dash").personality.name, "playful")


if __name__ == "__main__":
    unittest.main()
