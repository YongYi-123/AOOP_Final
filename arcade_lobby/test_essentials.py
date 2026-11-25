"""The hub's essential smoke and regression tests: the game starts, rooms connect, every cabinet opens its real game
and pays exactly once, the story's trials unlock and complete once, and the developer shortcuts used to test the
story (play_story.py stages, play_trial01.py, play_trial02.py, the --debug keys) still reach the state they promise.

Save integrity, migration, rewards, chapters and lifetime earnings have their own modules (test_profiles,
test_rewards, test_chapters, test_lifetime_earnings, test_save_lock); the whole story is played end to end by
verify_main_story.py.

Run with:  python -m unittest test_essentials      (or, from the repository root: python run_tests.py)
Every profile here lives in memory or in a temporary folder: arcade_lobby/saves/ is never opened.
"""
import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import quests as Q  # noqa: E402
from game import Game  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player_profile import PlayerProfile, ProfileStore  # noqa: E402
from room_testing import goto_room  # noqa: E402
from scenes import MINIGAME_SCENES  # noqa: E402

DT = 1 / 60
MAZE_PROFILES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "puzzle_maze", "profiles")


def frames(game, n=1, events=()):
    for i in range(n):
        game.step(list(events) if i == 0 else [], DT)


def press(game, key):
    frames(game, 1, [pygame.event.Event(pygame.KEYDOWN, key=key, mod=0)])


def new_game(profile=None, **kw):
    """A Game for one in-memory profile (no save file); the caller's cleanup quits it."""
    return Game(session=LocalSession(profile or PlayerProfile(profile_id="essentials", tokens=100)), **kw)


class HubTests(unittest.TestCase):
    def setUp(self):
        self.game = new_game()
        self.addCleanup(self.game.quit)

    def test_the_game_starts_in_home_and_runs_frames(self):
        frames(self.game, 30)
        self.assertEqual(self.game.scenes.current.room_id, "home")
        self.assertIs(self.game.hub.room("home"), self.game.scenes.current)

    def test_a_doorway_changes_room_once_and_keeps_the_same_player_and_wallet(self):
        home = self.game.scenes.current
        door = home.exits[0]
        tokens = self.game.profile.tokens
        self.assertTrue(self.game.hub.travel(home, door))
        self.assertFalse(self.game.hub.travel(home, door))         # a second request during the wipe is refused
        frames(self.game, 60)
        self.assertEqual(self.game.scenes.current.room_id, door.target)
        self.assertIs(self.game.scenes.current.players[0], home.players[0])
        self.assertEqual(self.game.profile.tokens, tokens)


class MinigameTests(unittest.TestCase):
    def setUp(self):
        saves = patch("puzzle_maze.game.Game.save")              # the Puzzle Maze saves per player: not in a test
        saves.start()
        self.addCleanup(saves.stop)
        self.maze_profiles = sorted(os.listdir(MAZE_PROFILES)) if os.path.isdir(MAZE_PROFILES) else None
        self.game = new_game()
        self.addCleanup(self.game.quit)

    def tearDown(self):
        if self.maze_profiles is not None:
            self.assertEqual(sorted(os.listdir(MAZE_PROFILES)), self.maze_profiles, "a test touched puzzle_maze/profiles")

    def test_every_cabinet_opens_its_real_game_and_settles_exactly_once(self):
        room = goto_room(self.game, "arcade_floor")
        profile = self.game.profile
        machines = [m for m in room.machines if m.game_id in MINIGAME_SCENES]
        self.assertEqual({m.game_id for m in machines}, set(MINIGAME_SCENES))
        for machine in machines:
            with self.subTest(machine=machine.id):
                tokens, played = profile.tokens, profile.total_games_played
                room._start_game(machine, player=room.players[0])
                room._start_game(machine, player=room.players[0])        # a double press never charges twice
                frames(self.game, 40)
                self.assertIsInstance(self.game.scenes.current, MINIGAME_SCENES[machine.game_id])
                self.assertEqual(profile.tokens, tokens - machine.play_cost)
                self.game.scenes.pop()
                frames(self.game, 40)
                self.assertIs(self.game.scenes.current, room)
                self.assertIsNone(room.active_play)
                self.assertEqual(profile.total_games_played, played + 1)
                tickets = profile.tickets
                room._end_play(ran=True)                                 # nothing left to settle: no second payout
                self.assertEqual((profile.tickets, profile.total_games_played), (tickets, played + 1))

    def test_a_player_who_cannot_pay_is_not_charged_and_no_game_opens(self):
        self.game.profile.spend_tokens(self.game.profile.tokens)
        room = goto_room(self.game, "arcade_floor")
        room._start_game(room.machines[0], player=room.players[0])
        frames(self.game, 20)
        self.assertIs(self.game.scenes.current, room)
        self.assertEqual(self.game.profile.tokens, 0)
        self.assertIsNone(room.active_play)


class DebugKeyTests(unittest.TestCase):
    def test_debug_build_f6_to_f9_are_the_rooms_helpers_not_also_volume(self):
        """Regression: with --debug, F6 used to skip a day AND lower the music; F8/F9 gave an item AND moved the
        effects volume. In a room the debug helper wins; without --debug they stay volume keys."""
        profile = PlayerProfile(profile_id="debug_keys_test")
        game = new_game(profile, debug=True)
        self.addCleanup(game.quit)
        room = goto_room(game, "arcade_floor")
        bgm, sfx, day = game.audio.bgm_volume, game.audio.sfx_volume, profile.clock.today()
        tokens = profile.tokens
        press(game, pygame.K_F5)
        self.assertEqual(profile.tokens, tokens + 10)                       # F5 +10 Tokens
        press(game, pygame.K_F6)
        self.assertNotEqual(profile.clock.today(), day)                     # F6 next day ...
        self.assertAlmostEqual(game.audio.bgm_volume, bgm)                  # ... and the music did not move
        coupons = profile.inventory.get_quantity("free_play_coupon")
        press(game, pygame.K_F9)
        self.assertEqual(profile.inventory.get_quantity("free_play_coupon"), coupons + 1)
        self.assertAlmostEqual(game.audio.sfx_volume, sfx)
        game.debug = False                                                  # a normal build: they are volume keys
        press(game, pygame.K_F6)
        self.assertAlmostEqual(game.audio.bgm_volume, bgm - .1)
        self.assertFalse(room.takes_debug_key(pygame.K_F9))


class StoryShortcutTests(unittest.TestCase):
    """The developer tools that jump into the story must keep working: each one is checked for the state it
    promises, on a throw-away save in a temporary folder."""

    def setUp(self):
        import play_story
        self.play_story = play_story
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.save = os.path.join(folder.name, "story_test.json")
        patcher = patch.object(play_story, "SAVE", self.save)     # never the tool's own temp save, which you may --keep
        patcher.start()
        self.addCleanup(patcher.stop)

    def story_at(self, stage):
        self.play_story.build(stage)
        game = Game(save_path=self.save, debug=True)
        self.addCleanup(game.quit)
        return game, game.hub.story.manager

    def test_every_play_story_stage_builds_and_opens(self):
        for stage in self.play_story.STAGES:
            with self.subTest(stage=stage):
                game, m = self.story_at(stage)
                frames(game, 5)
                self.assertEqual(game.scenes.current.room_id, "home")

    def test_the_stages_stand_where_they_say(self):
        _, m = self.story_at("ch1")
        self.assertEqual(m.current_chapter, 1)
        self.assertFalse(m.has_secret_item(Q.SECRET_ITEM_RETRO_RACER))
        _, m = self.story_at("trial01")
        self.assertTrue(m.has_secret_item(Q.SECRET_ITEM_RETRO_RACER))
        self.assertFalse(m.trial_done("trial_01"))
        _, m = self.story_at("ch2")
        self.assertEqual(m.current_chapter, 2)
        self.assertTrue(m.trial_done("trial_01"))
        _, m = self.story_at("solved")
        self.assertTrue(m.riddle_solved)
        game, m = self.story_at("trial02")
        self.assertTrue(m.has_secret_item(Q.SECRET_ITEM_CLAW))
        status = Q.trial_status(m, game.profile, Q.TRIALS_BY_ID["trial_02"])
        self.assertEqual(status.code, "available")

    def test_a_trial_completes_once_and_unseals_one_memory_fragment(self):
        game, m = self.story_at("trial01")
        profile = game.profile
        self.assertEqual(Q.trial_status(m, profile, Q.TRIALS_BY_ID["trial_01"]).code, "available")
        wallet = (profile.tokens, profile.tickets)
        m.handle("secret_trial_done", "trial_01")
        m.handle("secret_trial_done", "trial_01")                  # a replay finishing again changes nothing
        self.assertTrue(m.trial_done("trial_01"))
        self.assertEqual(m.memory_fragments, 1)
        self.assertEqual(m.current_chapter, 2)
        self.assertEqual((profile.tokens, profile.tickets), wallet)
        game.store.save(profile)                                   # and it survives a reload
        reloaded = ProfileStore(self.save).load()
        self.assertIn("trial_01", str(reloaded.story))

    def run_tool(self, module, *args):
        """Run a play_trial tool's main() up to the point where it would hand the window to the player."""
        started = []
        with patch.object(Game, "run", lambda game: started.append(game)):
            module.main(*args)
        self.assertEqual(len(started), 1)
        game = started[0]
        self.addCleanup(game.quit)
        frames(game, 5)
        return game

    def test_play_trial01_opens_the_golden_age_room(self):
        import play_trial01
        from golden_age_scene import GoldenAgeScene
        for fresh in (False, True):
            with self.subTest(fresh=fresh):
                game = self.run_tool(play_trial01, fresh)
                self.assertIsInstance(game.scenes.current, GoldenAgeScene)
                self.assertEqual(game.profile.display_name, "TESTER")       # the tool's in-memory profile

    def test_play_trial02_opens_the_tournament_hall_at_every_documented_point(self):
        import play_trial02
        import unbeaten_record as T
        from unbeaten_scene import TournamentHallScene
        for args, rounds in (([], 0), (["--fresh"], 0), (["--round", "2"], 1), (["--round", "3"], 2),
                             (["--round", "3", "--solved"], 2), (["--ending"], 3)):
            with self.subTest(args=args):
                game = self.run_tool(play_trial02, args)
                self.assertIsInstance(game.scenes.current, TournamentHallScene)
                m = game.hub.story.manager
                self.assertEqual(m.trial_progress(T.TRIAL_ID).get("rounds", 0), rounds)


if __name__ == "__main__":
    unittest.main()
