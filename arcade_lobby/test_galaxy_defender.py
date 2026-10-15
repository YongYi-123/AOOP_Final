"""Starfall Assault inside the real lobby: launch, input ownership, payout once, records, return.

Run with:  python -m unittest test_galaxy_defender
"""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from game import Game
from galaxy_defender.game import Screen
from galaxy_defender_scene import SCORE_KEY, WAVE_KEY, GalaxyDefenderScene
from local_session import LocalSession
from player_profile import PlayerProfile
from room_testing import goto_room
from scenes import minigame_definition
from settings import MACHINES


class GalaxyLobbyTests(unittest.TestCase):
    def make_game(self, two=False, starter=0, **profile_kwargs):
        profiles = [PlayerProfile(profile_id="gal_a", **profile_kwargs)]
        if two:
            profiles.append(PlayerProfile(profile_id="gal_b", **profile_kwargs))
        self.game = Game(session=LocalSession(profiles))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "arcade_floor")
        self.machine = next(m for m in self.room.machines if m.id == "galaxy_defender")
        self.room._start_game(self.machine, player=self.room.players[starter])
        self.frames(30)
        self.scene = self.game.scenes.current
        self.assertIsInstance(self.scene, GalaxyDefenderScene)
        return profiles

    def frames(self, count=1, key=None, down=True):
        events = [] if key is None else [pygame.event.Event(
            pygame.KEYDOWN if down else pygame.KEYUP, key=key, mod=0)]
        for i in range(count):
            self.game.step(events if i == 0 else [], 1 / 60)

    def start_run(self):
        self.frames(1, pygame.K_RETURN)
        self.assertEqual(self.scene.galaxy.screen, Screen.PLAYING)
        self.scene.galaxy.run.banner = 0.001
        self.frames(3)

    def finish_with_score(self, score, wave=1, cleared=0):
        run = self.scene.galaxy.run
        run.score, run.reached, run.waves_cleared = score, wave, cleared
        run.hp, run.invuln = 1, 0
        run.damage()
        self.frames(2)
        self.assertEqual(self.scene.galaxy.screen, Screen.OVER)

    def leave(self):
        self.frames(1, pygame.K_ESCAPE)             # game over screen: ESC returns to the lobby
        self.frames(40)
        self.assertIs(self.game.scenes.current, self.room)

    # ------------------------------------------------------------ registration
    def test_machine_is_registered_with_its_own_look_and_a_free_slot(self):
        data = [d for d in MACHINES if d["id"] == "galaxy_defender"]
        self.assertEqual(len(data), 1)
        self.assertEqual((data[0]["name"], data[0]["marquee"], data[0]["screen"]),
                         ("Starfall Assault", "STARFALL ASSAULT", "galaxy"))
        positions = [m["slot"] if "slot" in m else (m["x"], m.get("y")) for m in MACHINES]
        self.assertEqual(len(set(positions)), len(positions))
        self.assertEqual(minigame_definition("galaxy_defender").max_players, 1)

    def test_every_machine_still_exists_in_the_arcade(self):
        self.make_game()
        ids = {m.id for m in self.room.machines}
        self.assertTrue({"retro_racer", "puzzle_drop", "pixel_volleyball",
                         "cat_minesweeper", "galaxy_defender"} <= ids)
        self.assertNotIn("space_blaster", ids)

    # ------------------------------------------------------------ launch and controls
    def test_launch_charges_one_play_and_shows_the_title(self):
        profiles = self.make_game()
        self.assertEqual(self.scene.galaxy.screen, Screen.TITLE)
        self.assertEqual(profiles[0].tokens, PlayerProfile().tokens - self.machine.play_cost)
        self.assertEqual(self.scene.participants, [profiles[0]])

    def test_keys_move_and_fire_through_the_players_own_bindings(self):
        self.make_game()
        self.start_run()
        run = self.scene.galaxy.run
        start = run.x
        self.frames(1, pygame.K_a)
        self.frames(10)
        self.assertLess(run.x, start)
        self.frames(1, pygame.K_a, down=False)
        self.frames(1, pygame.K_RIGHT)
        self.frames(25)
        self.assertGreater(run.x, start - 40)
        self.frames(1, pygame.K_RIGHT, down=False)
        self.frames(1, pygame.K_SPACE)
        self.frames(20)
        self.assertGreaterEqual(len(run.player_bolts), 1)
        self.frames(1, pygame.K_SPACE, down=False)
        self.frames(60)
        self.assertEqual(len(run.player_bolts), 0)      # released: no more shots

    def test_escape_pauses_then_menu_returns_to_the_lobby(self):
        self.make_game()
        self.start_run()
        self.frames(1, pygame.K_ESCAPE)
        self.assertEqual(self.scene.galaxy.screen, Screen.PAUSED)
        self.frames(1, pygame.K_ESCAPE)
        self.assertEqual(self.scene.galaxy.screen, Screen.PLAYING)
        self.frames(1, pygame.K_ESCAPE)
        self.frames(1, pygame.K_s)
        self.frames(1, pygame.K_s)
        self.frames(1, pygame.K_RETURN)
        self.frames(40)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertIsNone(self.room.active_play)

    def test_returning_restores_the_lobby_for_the_next_game(self):
        self.make_game()
        self.leave_from_title()
        self.frames(60)
        self.room._start_game(self.machine, player=self.room.players[0])
        self.frames(30)
        self.assertIsInstance(self.game.scenes.current, GalaxyDefenderScene)

    def leave_from_title(self):
        self.frames(1, pygame.K_ESCAPE)
        self.frames(40)
        self.assertIs(self.game.scenes.current, self.room)

    def test_window_focus_loss_pauses(self):
        self.make_game()
        self.start_run()
        self.game.step([pygame.event.Event(pygame.WINDOWFOCUSLOST)], 1 / 60)
        self.assertEqual(self.scene.galaxy.screen, Screen.PAUSED)

    # ------------------------------------------------------------ rewards and records
    def test_leaving_without_playing_pays_nothing_and_saves_no_record(self):
        profiles = self.make_game()
        tickets = profiles[0].tickets
        self.leave_from_title()
        self.assertEqual(profiles[0].tickets, tickets)
        self.assertNotIn(SCORE_KEY, profiles[0].high_scores)
        self.assertNotIn(WAVE_KEY, profiles[0].high_scores)

    def test_tickets_score_and_wave_are_saved_and_paid_once(self):
        profiles = self.make_game()
        self.start_run()
        self.finish_with_score(2400, wave=5, cleared=4)
        expected = self.scene.galaxy.best.tickets
        self.assertGreater(expected, 0)
        first = self.scene.get_result()
        self.assertEqual(self.scene.get_result(), first)
        self.assertEqual(first.player_results[0].reward.tickets, expected)
        self.leave()
        self.frames(30)
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets + expected)
        self.assertEqual(profiles[0].high_score(SCORE_KEY), 2400)
        self.assertEqual(profiles[0].high_score(WAVE_KEY), 5)
        self.assertEqual(profiles[0].total_games_played, 1)

    def test_retry_and_restart_cannot_farm_tickets(self):
        profiles = self.make_game()
        self.start_run()
        self.finish_with_score(2400, wave=5, cleared=4)
        best = self.scene.galaxy.best.tickets
        for _ in range(4):
            self.frames(1, pygame.K_RETURN)             # RETRY
            self.scene.galaxy.run.banner = 0.001
            self.frames(2)
            self.finish_with_score(2400, wave=5, cleared=4)
        self.leave()
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets + best)
        self.assertEqual(profiles[0].total_games_played, 1)

    def test_a_worse_run_does_not_lower_the_saved_record(self):
        profiles = self.make_game()
        profiles[0].record_score(SCORE_KEY, 9000)
        profiles[0].record_score(WAVE_KEY, 12)
        self.scene.attach_players(self.scene.players)
        self.start_run()
        self.finish_with_score(300, wave=2, cleared=1)
        self.assertEqual(self.scene.galaxy.personal_best, 9000)
        self.assertFalse(self.scene.galaxy.new_record)
        self.leave()
        self.assertEqual((profiles[0].high_score(SCORE_KEY), profiles[0].high_score(WAVE_KEY)), (9000, 12))

    def test_quitting_mid_run_pays_the_progress_once(self):
        profiles = self.make_game()
        self.start_run()
        run = self.scene.galaxy.run
        run.score, run.reached, run.waves_cleared = 1500, 4, 3
        expected = run.result().tickets
        self.frames(1, pygame.K_ESCAPE)
        self.frames(1, pygame.K_s)
        self.frames(1, pygame.K_s)
        self.frames(1, pygame.K_RETURN)
        self.frames(60)
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets + expected)
        self.frames(60)
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets + expected)

    def test_second_player_starting_is_the_one_scored_and_paid(self):
        profiles = self.make_game(two=True, starter=1)
        self.assertEqual(self.scene.participants, [profiles[1]])
        self.assertEqual(self.scene.galaxy.saved_score, 0)
        profiles[1].record_score(SCORE_KEY, 777)
        self.scene.attach_players(self.scene.players)
        self.assertEqual(self.scene.galaxy.saved_score, 777)
        self.start_run()
        self.finish_with_score(2000, wave=4, cleared=3)
        paid = self.scene.galaxy.best.tickets
        self.leave()
        self.frames(30)
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets)
        self.assertEqual(profiles[1].tickets, PlayerProfile().tickets + paid)
        self.assertNotIn(SCORE_KEY, profiles[0].high_scores)
        self.assertEqual(profiles[1].high_score(SCORE_KEY), 2000)

    def test_second_players_keys_drive_the_ship_when_they_start_it(self):
        self.make_game(two=True, starter=1)
        self.start_run()
        run = self.scene.galaxy.run
        before = run.x
        self.frames(1, pygame.K_a)                       # player 1's key: ignored
        self.frames(10)
        self.assertEqual(run.x, before)
        self.frames(1, pygame.K_a, down=False)
        self.frames(1, pygame.K_LEFT)                    # player 2's key
        self.frames(10)
        self.assertLess(run.x, before)

    def test_old_saves_without_galaxy_records_still_load(self):
        profile = PlayerProfile.from_dict({"high_scores": {"pixel_volleyball": 300}, "tokens": 5})
        self.assertEqual(profile.high_score(SCORE_KEY), 0)
        profile.record_score(SCORE_KEY, 100)
        profile.record_score(WAVE_KEY, 3)
        again = PlayerProfile.from_dict(profile.to_dict())
        self.assertEqual((again.high_score(SCORE_KEY), again.high_score(WAVE_KEY), again.high_score("pixel_volleyball")),
                         (100, 3, 300))

    def test_other_machines_still_launch(self):
        self.make_game()
        self.leave_from_title()
        self.frames(60)
        other = next(m for m in self.room.machines if m.id == "pixel_volleyball")
        self.room._start_game(other, player=self.room.players[0])
        self.frames(30)
        self.assertEqual(type(self.game.scenes.current).__name__, "PixelVolleyballScene")


if __name__ == "__main__":
    unittest.main()
