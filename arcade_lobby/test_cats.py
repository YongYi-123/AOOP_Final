"""Tests for the arcade cats: spawning, looks, behaviour, petting, meows,
following, collision and pausing around minigames.

Run headless from this folder:   python -m unittest test_cats -v
"""
import os
import shutil
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from cat import CURIOUS, FRIENDLY, CatNPC, CatState  # noqa: E402
from cat_sprites import CatLook, cat_sheet  # noqa: E402
from cat_voice import KINDS, CatVoice, meow_bank, synth_samples  # noqa: E402
from game import Game  # noqa: E402
from scenes import ArcadeRoomScene, MinigamePlaceholderScene  # noqa: E402
from settings import CATS  # noqa: E402
from ui import SpeechBubble  # noqa: E402

DT = 1 / 60


def key(k, down=True):
    return pygame.event.Event(pygame.KEYDOWN if down else pygame.KEYUP, key=k, mod=0, unicode="")


class CatSceneTest(unittest.TestCase):
    STYLE = "lofi"

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.game = Game(style=self.STYLE, save_path=os.path.join(self.dir, "save.json"))
        self.room = self.game.scenes.current
        self.cats = self.room.cats

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_frames(self, n, events=()):
        self.game.step(list(events), DT)
        for _ in range(n - 1):
            self.game.step([], DT)

    def isolate(self, keep):
        """Put every other cat into a long nap (sleeping cats don't react,
        wander or meow), so a test only watches `keep`."""
        for cat in self.cats:
            if cat is not keep:
                cat.set_state(CatState.SLEEP, 999)
                cat.chat_timer = 999

    def place_player_by(self, cat, dx=-14):
        self.room.player.x, self.room.player.y = cat.x + dx, cat.y
        cat.set_state(CatState.SIT, 999)
        cat.chat_timer = 999
        self.run_frames(2)      # let the scene notice what is nearby


# ---------------------------------------------------------------- spawning
class SpawnTests(CatSceneTest):
    def test_multiple_named_cats_spawn(self):
        self.assertGreaterEqual(len(self.cats), 4)
        self.assertLessEqual(len(self.cats), 6)
        names = [c.name for c in self.cats]
        self.assertEqual(len(set(names)), len(names))
        self.assertEqual(self.cats.drawables(), self.cats.cats)
        for cat in self.cats:
            self.assertEqual(cat.position, tuple(map(float, cat.spots[0])))   # at home

    def test_several_personalities(self):
        kinds = {c.personality.name for c in self.cats}
        self.assertTrue({"friendly", "shy", "lazy", "curious"} <= kinds)

    def test_one_reusable_class(self):
        # One CatNPC class configured by data, no per-cat subclasses
        self.assertTrue(all(type(c) is CatNPC for c in self.cats))


class SpotTests(unittest.TestCase):
    def test_every_spot_is_clear_in_both_rooms(self):
        """Spots are not inside furniture, machine fronts or the doorway."""
        for style in ("lofi", "neon"):
            with self.subTest(style=style):
                d = tempfile.mkdtemp()
                try:
                    room = Game(style=style, save_path=os.path.join(d, "s.json")).scenes.current
                    for cat in room.cats:
                        for spot in cat.spots:
                            self.assertTrue(room.cats.is_free(spot), (style, cat.name, spot))
                finally:
                    shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------- looks
class AppearanceTests(unittest.TestCase):
    def test_each_cat_has_a_distinct_look(self):
        looks = [CatLook(**d["look"]) for d in CATS]
        self.assertEqual(len(set(looks)), len(looks))
        frames = [pygame.image.tobytes(cat_sheet(look)[("sit", "left")][0], "RGBA") for look in looks]
        self.assertEqual(len(set(frames)), len(frames))

    def test_sheets_are_shared_not_rebuilt(self):
        look = CatLook(**CATS[0]["look"])
        self.assertIs(cat_sheet(look), cat_sheet(CatLook(**CATS[0]["look"])))


class AnimationTests(CatSceneTest):
    def test_cats_animate_independently(self):
        controllers = [c.animation_controller for c in self.cats]
        self.assertEqual(len({id(a.current) for a in controllers}), len(controllers))
        seen = [set() for _ in self.cats]
        for _ in range(240):
            self.run_frames(1)
            for s, cat in zip(seen, self.cats):
                s.add((cat.state, cat.animation_controller.name, cat.animation_controller.frame_index))
        for s in seen:
            self.assertGreater(len(s), 1)        # every cat is animating
        snapshot = [(c.animation_controller.name, c.animation_controller.frame_index) for c in self.cats]
        self.assertGreater(len(set(snapshot)), 1)  # ...and not in lockstep


# ---------------------------------------------------------------- petting
class InteractionTests(CatSceneTest):
    def friendly_cat(self):
        cat = next(c for c in self.cats if c.personality is FRIENDLY)
        self.isolate(cat)
        self.place_player_by(cat)
        return cat

    def test_prompt_appears_near_a_cat(self):
        cat = self.friendly_cat()
        self.run_frames(10)
        self.assertIs(self.room.nearby_cat, cat)
        self.assertEqual(self.room.prompt.label, "PET")
        self.assertGreater(self.room.prompt.alpha, 0)

    def test_shy_cat_prompt_says_hi(self):
        cat = next(c for c in self.cats if c.personality.name == "shy")
        self.isolate(cat)
        self.place_player_by(cat, dx=-14)
        self.assertIs(self.room.nearby_cat, cat)
        self.assertEqual(self.room.prompt.label, "SAY HI")

    def test_no_prompt_when_far_away(self):
        cat = self.friendly_cat()
        self.room.player.x, self.room.player.y = cat.x - 80, cat.y
        self.run_frames(5)
        self.assertIsNone(self.room.nearby_cat)

    def test_e_pets_once_with_meow_and_bubble(self):
        cat = self.friendly_cat()
        self.run_frames(3)
        self.run_frames(1, [key(pygame.K_e)])
        self.assertEqual(cat.state, CatState.PET)
        self.assertEqual(cat.voice.plays, 1)
        self.assertTrue(cat.bubble.visible)
        self.assertIn(cat.bubble.text, [t for t, _ in cat.personality.phrases])
        self.assertGreater(cat.heart_time, 0)

        # Mashing E (and just holding it) neither restarts the reaction nor meows again.
        timer = cat.timer
        for _ in range(20):
            self.run_frames(1, [key(pygame.K_e), key(pygame.K_e)])
        self.assertEqual(cat.voice.plays, 1)
        self.assertLess(cat.timer, timer)

    def test_cat_returns_to_normal(self):
        cat = self.friendly_cat()
        cat.rng.random = lambda: 0.99            # no follow this time
        self.run_frames(3, [key(pygame.K_e)])
        self.assertEqual(cat.state, CatState.PET)
        self.run_frames(int((CatNPC.PET_TIME + 0.1) / DT))
        self.assertEqual(cat.state, CatState.SIT)
        self.run_frames(int(SpeechBubble().duration / DT))
        self.assertFalse(cat.bubble.visible)
        self.run_frames(int(CatNPC.PET_COOLDOWN / DT) + 2)
        self.assertTrue(cat.can_pet)
        self.run_frames(1, [key(pygame.K_e)])     # and can be petted again
        self.assertEqual(cat.voice.plays, 2)

    def test_petting_wakes_a_sleeping_cat_with_a_purr(self):
        cat = self.friendly_cat()
        cat.set_state(CatState.SLEEP, 999)
        self.run_frames(2)
        self.run_frames(1, [key(pygame.K_e)])
        self.assertEqual(cat.state, CatState.PET)
        self.assertEqual(cat.bubble.text, "prrr...")

    def test_petting_does_not_lock_the_player(self):
        cat = self.friendly_cat()
        self.run_frames(1, [key(pygame.K_e)])
        y = self.room.player.y
        self.run_frames(10, [key(pygame.K_s)])
        self.assertGreater(self.room.player.y, y)

    def test_machine_prompt_wins_over_cat(self):
        machine = self.room.machines[1]
        p = self.room.player
        p.x, p.y = machine.rect.centerx, machine.rect.bottom + 12
        cat = self.cats.cats[0]
        self.isolate(None)
        cat.x, cat.y = p.x + 10, p.y + 4
        self.run_frames(3)
        self.assertIs(self.room.nearby, machine)
        self.assertIsNone(self.room.nearby_cat)
        self.assertEqual(self.room.prompt.label, "PLAY")


# ---------------------------------------------------------------- audio
class AudioTests(unittest.TestCase):
    def test_every_kind_synthesises(self):
        for kind in KINDS:
            samples = synth_samples(kind, 1.2)
            self.assertGreater(len(samples), 1000)
            self.assertLessEqual(max(abs(v) for v in samples), 1.0)

    def test_pitch_changes_the_sound(self):
        self.assertNotEqual(synth_samples("meow", 0.8)[:2000], synth_samples("meow", 1.3)[:2000])

    def test_bank_builds_playable_sounds_once(self):
        pygame.mixer.init()
        bank = meow_bank()
        sound = bank.get("meow", 1.0)
        self.assertIsInstance(sound, pygame.mixer.Sound)
        self.assertIs(bank.get("meow", 1.0), sound)
        self.assertGreater(sound.get_length(), 0.2)

    def test_voice_cooldown_blocks_spam(self):
        voice = CatVoice()
        self.assertTrue(voice.play("mew", 0.0))
        self.assertFalse(voice.play("mew", 0.1))
        self.assertTrue(voice.play("mew", 1.0))
        self.assertEqual(voice.plays, 2)

    def test_silent_bank_is_safe(self):
        class NoAudio:
            def get(self, kind, pitch):
                return None
        voice = CatVoice(bank=NoAudio())
        self.assertTrue(voice.play("meow", 0.0))
        voice.stop()


# ---------------------------------------------------------------- following
class FollowTests(CatSceneTest):
    def test_friendly_cat_follows_after_pet_then_stops(self):
        cat = next(c for c in self.cats if c.personality is FRIENDLY)
        self.isolate(cat)
        self.place_player_by(cat)
        cat.rng.random = lambda: 0.0             # always chooses to follow
        self.run_frames(1, [key(pygame.K_e)])
        self.run_frames(int((CatNPC.PET_TIME + 0.05) / DT))
        self.assertEqual(cat.state, CatState.FOLLOW)
        self.assertIs(self.cats.follower, cat)

        start = cat.position
        self.run_frames(1, [key(pygame.K_d)])     # walk away; the cat trots after
        self.run_frames(30)
        self.run_frames(1, [key(pygame.K_d, down=False)])
        self.assertNotEqual(cat.position, start)
        self.run_frames(int(CatNPC.PET_FOLLOW_TIME / DT) + 5)
        self.assertEqual(cat.state, CatState.SIT)
        self.assertIsNone(self.cats.follower)

    def test_only_one_follower(self):
        a, b = self.cats.cats[:2]
        self.assertTrue(self.cats.request_follow(a))
        a.start_follow()
        self.assertFalse(self.cats.request_follow(b))
        self.assertTrue(self.cats.request_follow(a))

    def test_curious_cat_trails_a_passing_player(self):
        cat = next(c for c in self.cats if c.personality is CURIOUS)
        self.isolate(cat)
        cat.set_state(CatState.SIT, 999)
        cat.follow_cooldown = 0
        cat.chat_timer = 999
        p = self.room.player
        p.x, p.y = cat.x + 30, cat.y + 20
        self.run_frames(3, [key(pygame.K_s)])
        self.assertIs(self.cats.follower, cat)
        self.run_frames(1, [key(pygame.K_s, down=False)])

    def test_follow_stops_when_dialogue_opens(self):
        cat = self.cats.cats[0]
        self.isolate(cat)
        self.cats.request_follow(cat)
        cat.start_follow(99)
        machine = self.room.machines[1]
        self.room.player.x, self.room.player.y = machine.rect.centerx, machine.rect.bottom + 12
        self.run_frames(3)
        self.run_frames(30, [key(pygame.K_e)])
        self.assertIsNotNone(self.room.dialogue)
        self.assertNotEqual(cat.state, CatState.FOLLOW)
        self.assertIsNone(self.cats.follower)


# ---------------------------------------------------------------- collision
class CollisionTests(CatSceneTest):
    def test_player_bumps_into_cat_but_is_never_trapped(self):
        cat = self.cats.get("bean")
        self.isolate(cat)
        cat.x, cat.y = 150.0, 170.0
        cat.set_state(CatState.SIT, 999)
        cat.chat_timer = 999
        p = self.room.player
        p.x, p.y = 120.0, 170.0
        self.run_frames(1, [key(pygame.K_d)])
        self.run_frames(int(0.25 / DT))
        self.assertLess(p.feet.right, cat.feet.left + 1)    # blocked: not walking through
        self.run_frames(int(1.2 / DT))
        self.run_frames(1, [key(pygame.K_d, down=False)])
        self.assertGreater(p.x, cat.feet.right)            # the cat stepped aside
        self.assertNotEqual(cat.position, (150.0, 170.0))

    def test_player_overlapping_a_cat_can_walk_out(self):
        cat = self.cats.cats[0]
        self.isolate(cat)
        cat.set_state(CatState.SIT, 999)
        p = self.room.player
        p.x, p.y = cat.x, cat.y
        self.run_frames(1, [key(pygame.K_s)])
        self.run_frames(30)
        self.assertGreater(p.y, cat.y + 8)

    def test_resting_cats_keep_machine_fronts_and_door_clear(self):
        p = self.room.player
        for _ in range(int(90 / DT)):            # a minute and a half of cat life
            self.game.step([], DT)
            for cat in self.cats:
                if cat.state in (CatState.SIT, CatState.SLEEP, CatState.IDLE):
                    self.assertEqual(cat.feet.collidelist(self.cats.keep_clear), -1,
                                     (cat.name, cat.position, cat.state))
        self.assertTrue(p.feet.collidelist(self.room.room.solids) == -1)


# ---------------------------------------------------------------- scenes
class SceneSafetyTests(CatSceneTest):
    def enter_minigame(self):
        machine = next(m for m in self.room.machines if m.id == "space_blaster")
        self.room.player.x, self.room.player.y = machine.rect.centerx, machine.rect.bottom + 12
        self.run_frames(3)
        self.run_frames(30, [key(pygame.K_e)])
        self.run_frames(40, [key(pygame.K_RETURN)])
        self.assertIsInstance(self.game.scenes.current, MinigamePlaceholderScene)

    def test_enter_and_leave_minigame(self):
        cat = self.cats.get("miso")
        cat.say("meow!", "meow")
        self.cats.request_follow(cat)
        cat.start_follow(99)
        self.enter_minigame()
        scene = self.game.scenes.current
        self.assertFalse(hasattr(scene, "cats"))
        self.assertTrue(self.cats.paused)
        self.assertIsNone(self.cats.follower)
        for c in self.cats:
            self.assertNotIn(c.state, (CatState.FOLLOW, CatState.PET))
            self.assertFalse(c.bubble.visible)

        frozen = [(c.time, c.position) for c in self.cats]
        self.run_frames(60)                      # minigame running: cats don't update
        self.assertEqual(frozen, [(c.time, c.position) for c in self.cats])

        self.run_frames(40, [key(pygame.K_ESCAPE)])
        self.assertIsInstance(self.game.scenes.current, ArcadeRoomScene)
        self.assertFalse(self.cats.paused)
        self.run_frames(30)
        self.assertTrue(all(c.time > t for c, (t, _) in zip(self.cats, frozen)))

        # and petting still works afterwards
        self.isolate(cat)
        self.place_player_by(cat)
        self.run_frames(3)
        plays = cat.voice.plays
        self.run_frames(1, [key(pygame.K_e)])
        self.assertEqual(cat.state, CatState.PET)
        self.assertEqual(cat.voice.plays, plays + 1)

    def test_e_in_minigame_does_not_pet(self):
        cat = self.cats.get("miso")
        self.enter_minigame()
        self.run_frames(5, [key(pygame.K_e)])
        self.assertNotEqual(cat.state, CatState.PET)
        self.assertFalse(self.cats.interact(cat))


class NeonRoomTests(SpawnTests):
    STYLE = "neon"


if __name__ == "__main__":
    unittest.main()
