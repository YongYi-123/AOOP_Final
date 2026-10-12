"""NEON CAT MAZE inside the real lobby: the cabinet, launch, input ownership, payout once, saves and profiles, music
lifecycle, window scaling and return.

Run with:  python -m unittest test_cat_maze
"""
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
import audio_manager as am
from game import Game                    # first: it puts the project root (and so neon_cat_maze) on sys.path
from cat_maze_scene import LEVEL_KEY, SCORE_KEY, CatMazeScene
import display as dp
from display import DisplayManager
from local_session import LocalSession
from machine import H, W, ArcadeMachine
from neon_cat_maze import config as cfg
from neon_cat_maze.game import Screen
from neon_cat_maze.settlement import tickets_for
from player_profile import PlayerProfile
from room_testing import goto_room
from scenes import MINIGAME_DEFINITIONS, MINIGAME_SCENES, MinigamePlaceholderScene, minigame_definition
from settings import MACHINES, VIEW_H, VIEW_W

DT = 1 / 60
BIG_DESKTOP = (7680, 4320)


def machine_data(machine_id):
    return next(d for d in MACHINES if d["id"] == machine_id)


class LobbyCase(unittest.TestCase):
    def make_game(self, two=False, starter=0, **profile_kwargs):
        profiles = [PlayerProfile(profile_id="maze_a", **profile_kwargs)]
        if two:
            profiles.append(PlayerProfile(profile_id="maze_b", **profile_kwargs))
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.game = Game(session=LocalSession(profiles), audio_prefs=os.path.join(self.dir, "audio.json"))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "arcade_floor")
        self.machine = next(m for m in self.room.machines if m.id == "puzzle_drop")
        self.room._start_game(self.machine, player=self.room.players[starter])
        self.frames(30)
        self.scene = self.game.scenes.current
        self.assertIsInstance(self.scene, CatMazeScene)
        return profiles

    def frames(self, count=1, key=None, down=True):
        events = [] if key is None else [pygame.event.Event(
            pygame.KEYDOWN if down else pygame.KEYUP, key=key, mod=0)]
        for i in range(count):
            self.game.step(events if i == 0 else [], DT)

    def confirm_key(self):
        """The active player's own confirm key (ENTER solo or for P2, E for P1)."""
        return self.scene.input.scheme.interact[0]

    def start_run(self):
        self.frames(1, self.confirm_key())
        self.assertEqual(self.scene.cat_maze.screen, Screen.PLAYING)
        self.frames(int((cfg.READY_SECONDS + 0.2) / DT))
        self.assertEqual(self.scene.cat_maze.run.phase, "run")

    def finish_with_score(self, score, level=3, cleared=2):
        run = self.scene.cat_maze.run
        run.score, run.level, run.levels_cleared = score, level, cleared
        run.lives, run.invulnerable = 1, 0.0
        robot = run.robots[1]
        robot.mode, robot.fright = "active", False
        robot.place(run.cat.nearest_tile())
        self.frames(int((cfg.DYING_SECONDS + cfg.OVER_SECONDS + 0.4) / DT))
        self.assertEqual(self.scene.cat_maze.screen, Screen.OVER)

    def leave(self):
        self.frames(1, pygame.K_ESCAPE)             # the results screen: ESC returns to the lobby
        self.frames(40)
        self.assertIs(self.game.scenes.current, self.room)


class CabinetAndRegistrationTests(LobbyCase):
    def test_the_old_placeholder_machine_is_now_neon_cat_maze_in_the_same_slot(self):
        data = machine_data("puzzle_drop")
        self.assertEqual((data["name"], data["marquee"], data["screen"]), ("Neon Cat Maze", "CAT MAZE", "maze"))
        self.assertEqual(data["x"], 148)                                       # the Puzzle Drop slot
        self.assertEqual(data["play_cost"], 1)                                 # the entry cost is untouched
        self.assertNotIn("Puzzle", data["name"] + data["description"])
        self.assertIs(MINIGAME_SCENES["puzzle_drop"], CatMazeScene)
        self.assertEqual(minigame_definition("puzzle_drop").max_players, 1)
        positions = [m["slot"] if "slot" in m else (m["x"], m.get("y")) for m in MACHINES]
        self.assertEqual(len(set(positions)), len(positions))

    def test_no_machine_still_uses_the_placeholder_scene(self):
        for data in MACHINES:
            self.assertIn(data.get("game_id", data["id"]), MINIGAME_SCENES)
        self.assertNotIn(MinigamePlaceholderScene, MINIGAME_SCENES.values())

    def test_the_cabinet_keeps_the_standard_collision_box_and_interaction_zone(self):
        mine = ArcadeMachine(dict(machine_data("puzzle_drop"), x=100, y=30))
        other = ArcadeMachine(dict(machine_data("galaxy_defender"), x=100, y=30))
        self.assertEqual((mine.rect.size, mine.footprint.size, mine.zone.size),
                         ((W, H), other.footprint.size, other.zone.size))
        self.assertEqual(mine.footprint, other.footprint)
        self.assertEqual(mine.zone, other.zone)

    def test_the_cabinet_has_cat_ears_a_scrolling_marquee_and_an_animated_screen(self):
        pygame.display.set_mode((1, 1))
        m = ArcadeMachine(dict(machine_data("puzzle_drop"), x=100, y=30))
        self.assertGreater(m.art["pad"], 0)
        ears = m.art["cabinet"][0].subsurface((0, 0, m.art["cabinet"][0].get_width(), m.art["pad"]))
        self.assertGreater(pygame.mask.from_surface(ears).count(), 12)
        screens, marquees, doors = set(), set(), set()
        for _ in range(400):
            m.update(DT)
            screens.add(pygame.image.tobytes(m.image, "RGB"))
            marquees.add(pygame.image.tobytes(m.art["cabinet"][m.marquee.image], "RGBA"))
        self.assertGreater(len(screens), 12)
        self.assertGreater(len(marquees), 6)
        self.assertGreater(m.art["marquee_frames"], 6)                         # the whole name scrolls past

    def test_the_cabinet_is_not_a_copy_of_its_neighbours(self):
        pygame.display.set_mode((1, 1))
        frames = {i: ArcadeMachine(dict(machine_data(i), x=100, y=30)).art["cabinet"][0] for i in
                  ("puzzle_drop", "cat_minesweeper", "galaxy_defender", "pixel_volleyball", "retro_racer")}
        images = {i: pygame.image.tobytes(s, "RGBA") for i, s in frames.items()}
        self.assertEqual(len(set(images.values())), 5)
        self.assertNotEqual(machine_data("puzzle_drop")["neon"], machine_data("cat_minesweeper")["neon"])

    def test_every_machine_still_exists_and_nearby_prompts_work(self):
        self.make_game()
        self.frames(1, pygame.K_ESCAPE)
        self.frames(60)
        ids = {m.id for m in self.room.machines}
        self.assertTrue({"retro_racer", "puzzle_drop", "pixel_volleyball", "cat_minesweeper", "galaxy_defender"} <= ids)
        mine = next(m for m in self.room.machines if m.id == "puzzle_drop")
        for other in self.room.machines:
            if other is not mine:
                self.assertFalse(mine.footprint.colliderect(other.footprint))


class LaunchAndControlTests(LobbyCase):
    def test_launch_charges_exactly_one_token_and_shows_the_title(self):
        profiles = self.make_game()
        self.assertEqual(self.scene.cat_maze.screen, Screen.TITLE)
        self.assertEqual(profiles[0].tokens, PlayerProfile().tokens - 1)
        self.assertEqual(self.scene.participants, [profiles[0]])

    def test_p1_wasd_and_the_solo_arrow_keys_steer_the_cat(self):
        self.make_game()
        self.start_run()
        run = self.scene.cat_maze.run
        self.frames(1, pygame.K_d)
        self.frames(20)
        self.assertGreater(run.cat.pos[0], run.maze.start[0] + 1)
        self.frames(1, pygame.K_d, down=False)
        self.frames(1, pygame.K_LEFT)                                         # solo keeps the arrow keys too
        self.frames(8)
        self.assertEqual(run.cat.dir, (-1, 0))

    def test_a_held_key_turns_at_the_next_junction_without_more_presses(self):
        self.make_game()
        self.start_run()
        run = self.scene.cat_maze.run
        self.frames(1, pygame.K_d)
        self.frames(5)
        self.frames(1, pygame.K_w)                                            # hold W as well: newest wins
        self.frames(60)
        self.assertEqual(run.cat.facing, (0, -1))
        self.assertLess(run.cat.pos[1], run.maze.start[1])
        self.frames(1, pygame.K_w, down=False)
        self.frames(30)                                                       # D is still held: back to going right
        self.assertEqual(run.cat.facing, (1, 0))

    def test_p2_arrow_keys_drive_the_cat_when_p2_starts_and_p1_keys_do_nothing(self):
        profiles = self.make_game(two=True, starter=1)
        self.assertEqual(self.scene.participants, [profiles[1]])
        self.frames(1, self.confirm_key())                                    # P2's confirm (ENTER) starts the run
        self.assertEqual(self.scene.cat_maze.screen, Screen.PLAYING)
        self.frames(int((cfg.READY_SECONDS + 0.2) / DT))
        run = self.scene.cat_maze.run
        start = run.cat.pos
        self.frames(1, pygame.K_d)                                            # P1's key: ignored
        self.frames(15)
        self.assertEqual(run.cat.pos, start)
        self.frames(1, pygame.K_d, down=False)
        self.frames(1, pygame.K_RIGHT)                                        # P2's key
        self.frames(15)
        self.assertGreater(run.cat.pos[0], start[0])

    def test_the_hint_line_names_the_active_players_own_keys(self):
        self.make_game(two=True, starter=1)
        self.assertIn("ARROWS", self.scene.cat_maze.hint_line())
        self.assertNotIn("WASD", self.scene.cat_maze.hint_line())
        self.frames(1, pygame.K_ESCAPE)
        self.frames(40)
        self.room._start_game(self.machine, player=self.room.players[0])
        self.frames(30)
        self.assertIn("WASD", self.game.scenes.current.cat_maze.hint_line())

    def test_the_spectator_can_watch_but_cannot_steer_pause_or_start(self):
        self.make_game(two=True, starter=0)
        self.start_run()
        run = self.scene.cat_maze.run
        before = run.cat.pos
        for key in (pygame.K_LEFT, pygame.K_UP, pygame.K_o, pygame.K_RETURN):    # all P2's keys
            self.frames(1, key)
        self.frames(20)
        self.assertEqual(self.scene.cat_maze.screen, Screen.PLAYING)
        self.assertEqual(run.cat.pos, before)
        self.assertEqual([p.profile.profile_id for p in self.scene.spectators], ["maze_b"])

    def test_pause_resume_and_the_pause_key_per_player(self):
        self.make_game()
        self.start_run()
        self.frames(1, pygame.K_p)                                            # solo: P pauses
        self.assertEqual(self.scene.cat_maze.screen, Screen.PAUSED)
        self.frames(1, pygame.K_p)
        self.assertEqual(self.scene.cat_maze.screen, Screen.PLAYING)
        self.frames(1, pygame.K_ESCAPE)
        self.assertEqual(self.scene.cat_maze.screen, Screen.PAUSED)
        self.frames(1, pygame.K_ESCAPE)
        self.assertEqual(self.scene.cat_maze.screen, Screen.PLAYING)

    def test_a_paused_game_does_not_move(self):
        self.make_game()
        self.start_run()
        self.frames(1, pygame.K_d)
        self.frames(10)
        self.frames(1, pygame.K_p)
        before = self.scene.cat_maze.run.cat.pos
        self.frames(120)
        self.assertEqual(self.scene.cat_maze.run.cat.pos, before)

    def test_window_focus_loss_pauses_and_drops_held_keys(self):
        self.make_game()
        self.start_run()
        self.frames(1, pygame.K_d)
        self.game.step([pygame.event.Event(pygame.WINDOWFOCUSLOST)], DT)
        self.assertEqual(self.scene.cat_maze.screen, Screen.PAUSED)
        self.assertEqual(self.scene.order, [])
        self.frames(1, pygame.K_p)                                            # resume
        self.assertEqual(self.scene.cat_maze.screen, Screen.PLAYING)
        before = self.scene.cat_maze.run.cat.pos
        self.frames(60)
        self.assertEqual(self.scene.cat_maze.run.cat.pos[1], before[1])       # D was released by the focus loss: no ghost steering

    def test_restart_after_game_over_and_return_to_the_hub(self):
        profiles = self.make_game()
        self.start_run()
        self.finish_with_score(1200)
        self.frames(1, pygame.K_RETURN)                                       # PLAY AGAIN
        self.assertEqual((self.scene.cat_maze.screen, self.scene.cat_maze.run.phase), (Screen.PLAYING, "ready"))
        self.frames(1, pygame.K_ESCAPE)                                       # pause
        self.frames(1, pygame.K_s)
        self.frames(1, pygame.K_s)
        self.frames(1, pygame.K_RETURN)                                       # RETURN TO LOBBY
        self.frames(40)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertIsNone(self.room.active_play)

    def test_returning_restores_the_lobby_for_the_next_game(self):
        self.make_game()
        self.frames(1, pygame.K_ESCAPE)
        self.frames(60)
        self.assertIs(self.game.scenes.current, self.room)
        self.room._start_game(self.machine, player=self.room.players[0])
        self.frames(30)
        self.assertIsInstance(self.game.scenes.current, CatMazeScene)

    def test_other_machines_still_launch(self):
        self.make_game()
        self.frames(1, pygame.K_ESCAPE)
        self.frames(60)
        for machine_id, name in (("pixel_volleyball", "PixelVolleyballScene"), ("galaxy_defender", "GalaxyDefenderScene"),
                                 ("cat_minesweeper", "CatTerritoryScene")):
            other = next(m for m in self.room.machines if m.id == machine_id)
            self.room._start_game(other, player=self.room.players[0])
            self.frames(30)
            self.assertEqual(type(self.game.scenes.current).__name__, name)
            self.game.scenes.pop(fade=False)
            self.frames(30)
            self.game.scenes.current.active_play = None


class RewardAndSaveTests(LobbyCase):
    def test_leaving_without_playing_pays_nothing_and_saves_no_record(self):
        profiles = self.make_game()
        tickets = profiles[0].tickets
        self.frames(1, pygame.K_ESCAPE)
        self.frames(40)
        self.assertEqual(profiles[0].tickets, tickets)
        self.assertNotIn(SCORE_KEY, profiles[0].high_scores)
        self.assertNotIn(LEVEL_KEY, profiles[0].high_scores)

    def test_tickets_score_and_level_are_saved_and_paid_once(self):
        profiles = self.make_game()
        self.start_run()
        self.finish_with_score(2400, level=4, cleared=3)
        expected = self.scene.cat_maze.best.tickets
        self.assertGreater(expected, 0)
        first = self.scene.get_result()
        self.assertEqual(self.scene.get_result(), first)                        # asking again changes nothing
        self.assertEqual(first.player_results[0].reward.tickets, expected)
        self.leave()
        self.frames(30)
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets + expected)
        self.assertEqual(profiles[0].high_score(SCORE_KEY), 2400)
        self.assertEqual(profiles[0].high_score(LEVEL_KEY), 4)
        self.assertEqual(profiles[0].total_games_played, 1)

    def test_play_again_cannot_farm_tickets(self):
        profiles = self.make_game()
        self.start_run()
        self.finish_with_score(2400, level=4, cleared=3)
        best = self.scene.cat_maze.best.tickets
        for _ in range(4):
            self.frames(1, pygame.K_RETURN)                                     # PLAY AGAIN
            self.frames(int((cfg.READY_SECONDS + 0.2) / DT))
            self.finish_with_score(2400, level=4, cleared=3)
        self.leave()
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets + best)
        self.assertEqual(profiles[0].total_games_played, 1)

    def test_a_worse_run_does_not_lower_the_saved_record(self):
        profiles = self.make_game()
        profiles[0].record_score(SCORE_KEY, 9000)
        profiles[0].record_score(LEVEL_KEY, 12)
        self.scene.attach_players(self.scene.players)
        self.start_run()
        self.finish_with_score(300, level=2, cleared=1)
        self.assertEqual(self.scene.cat_maze.personal_best, 9000)
        self.assertFalse(self.scene.cat_maze.new_record)
        self.leave()
        self.assertEqual((profiles[0].high_score(SCORE_KEY), profiles[0].high_score(LEVEL_KEY)), (9000, 12))

    def test_quitting_mid_run_pays_the_progress_once(self):
        profiles = self.make_game()
        self.start_run()
        run = self.scene.cat_maze.run
        run.score, run.level, run.levels_cleared = 1500, 3, 2
        expected = run.result().tickets
        self.frames(1, pygame.K_ESCAPE)                                         # pause
        self.frames(1, pygame.K_s)
        self.frames(1, pygame.K_s)
        self.frames(1, pygame.K_RETURN)                                         # RETURN TO LOBBY
        self.frames(60)
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets + expected)
        self.frames(60)
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets + expected)

    def test_the_score_the_player_sees_matches_what_is_reported(self):
        profiles = self.make_game()
        self.start_run()
        self.scene.cat_maze.run.steer((1, 0))
        self.frames(120)
        shown = self.scene.cat_maze.run.score
        self.assertGreater(shown, 0)
        self.frames(1, pygame.K_ESCAPE)
        self.frames(1, pygame.K_s)
        self.frames(1, pygame.K_s)
        self.frames(1, pygame.K_RETURN)
        self.frames(60)
        self.assertEqual(profiles[0].high_score(SCORE_KEY), shown)

    def test_ticket_rewards_are_bounded(self):
        self.make_game()
        self.start_run()
        self.finish_with_score(10 ** 9, level=99, cleared=98)
        self.assertEqual(self.scene.cat_maze.best.tickets, cfg.TICKETS["cap"])

    def test_the_second_player_who_starts_it_is_scored_and_paid_the_first_is_untouched(self):
        profiles = self.make_game(two=True, starter=1)
        self.assertEqual(self.scene.cat_maze.saved_score, 0)
        profiles[1].record_score(SCORE_KEY, 777)
        self.scene.attach_players(self.scene.players)
        self.assertEqual(self.scene.cat_maze.saved_score, 777)
        self.frames(1, pygame.K_RETURN)
        self.frames(int((cfg.READY_SECONDS + 0.2) / DT))
        self.finish_with_score(2000, level=3, cleared=2)
        paid = self.scene.cat_maze.best.tickets
        self.leave()
        self.frames(30)
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets)
        self.assertEqual(profiles[1].tickets, PlayerProfile().tickets + paid)
        self.assertNotIn(SCORE_KEY, profiles[0].high_scores)
        self.assertNotIn(LEVEL_KEY, profiles[0].high_scores)
        self.assertEqual(profiles[1].high_score(SCORE_KEY), 2000)
        self.assertEqual(profiles[0].total_games_played, 0)

    def test_old_saves_keep_working_and_gain_no_unexpected_fields(self):
        profile = PlayerProfile.from_dict({"high_scores": {"pixel_volleyball": 300, "puzzle_drop": 50}, "tokens": 5})
        self.assertEqual(profile.high_score(SCORE_KEY), 50)                     # an old Puzzle Drop record is just kept
        profile.record_score(SCORE_KEY, 100)
        profile.record_score(LEVEL_KEY, 3)
        again = PlayerProfile.from_dict(profile.to_dict())
        self.assertEqual((again.high_score(SCORE_KEY), again.high_score(LEVEL_KEY), again.high_score("pixel_volleyball")),
                         (100, 3, 300))
        fresh = PlayerProfile.from_dict({"tokens": 5})
        self.assertEqual(fresh.high_score(SCORE_KEY), 0)

    def test_the_entry_cost_is_not_changed_and_a_broke_player_cannot_play(self):
        self.assertEqual(machine_data("puzzle_drop")["play_cost"], 1)
        machine = ArcadeMachine(dict(machine_data("puzzle_drop"), x=100, y=30))
        self.assertEqual(machine.cost_label, "1 TOKEN")
        self.assertFalse(machine.can_afford(PlayerProfile(tokens=0)))
        self.assertTrue(machine.can_afford(PlayerProfile(tokens=1)))


class PlayAgainAndSettlementTests(LobbyCase):
    """Audit of the entry fee and payout. The hub's convention (Starfall Assault and Cat Territory work the same way):
    ONE cabinet entry = ONE token = ONE PlaySession = ONE payout, and what is paid is the best run of that entry.
    Play Again / Restart stay inside the entry (no second fee, no second payout); leaving and pressing PLAY at the
    cabinet again is a brand-new entry that costs a token and pays on its own."""

    START_TOKENS = PlayerProfile().tokens

    def relaunch(self, starter=0):
        self.room._start_game(self.machine, player=self.room.players[starter])
        self.frames(30)
        self.scene = self.game.scenes.current
        self.assertIsInstance(self.scene, CatMazeScene)

    def again(self, score, level=3, cleared=2):
        """From the results screen: PLAY AGAIN, then finish that run with `score`."""
        self.frames(1, pygame.K_RETURN)
        self.assertEqual(self.scene.cat_maze.screen, Screen.PLAYING)
        self.frames(int((cfg.READY_SECONDS + 0.2) / DT))
        self.finish_with_score(score, level, cleared)

    def test_play_again_reuses_the_entry_fee_and_never_charges_a_second_token(self):
        profiles = self.make_game()
        self.start_run()
        self.finish_with_score(900, 2, 1)
        for _ in range(5):
            self.again(900, 2, 1)
            self.assertEqual(profiles[0].tokens, self.START_TOKENS - 1)
        self.assertEqual(self.scene.participants, [profiles[0]])
        self.assertFalse(self.room.active_play[0].settled)                    # still ONE open entry

    def test_many_play_agains_pay_exactly_the_best_run_once(self):
        profiles = self.make_game()
        self.start_run()
        self.finish_with_score(900, 2, 1)
        for score, level, cleared in ((2400, 4, 3), (500, 1, 0), (2400, 4, 3), (100, 1, 0)):
            self.again(score, level, cleared)
        best = tickets_for(2400, 3)
        self.leave()
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets + best)
        self.assertEqual(profiles[0].high_score(SCORE_KEY), 2400)
        self.assertEqual(profiles[0].total_games_played, 1)
        self.frames(120)
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets + best)  # and nothing arrives later

    def test_game_over_then_results_then_leaving_pays_once_and_not_before(self):
        profiles = self.make_game()
        self.start_run()
        self.finish_with_score(1800, 3, 2)                                    # now on the results screen
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets)        # paid when the entry closes, not earlier
        self.assertEqual(profiles[0].total_games_played, 0)
        self.leave()
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets + tickets_for(1800, 2))
        self.assertEqual(profiles[0].total_games_played, 1)
        self.assertIsNone(self.room.active_play)

    def test_a_better_run_in_a_later_play_again_is_not_lost(self):
        profiles = self.make_game()
        self.start_run()
        self.finish_with_score(300, 1, 0)
        self.again(5000, 5, 4)
        self.leave()
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets + tickets_for(5000, 4))
        self.assertEqual(profiles[0].high_score(SCORE_KEY), 5000)

    def test_the_score_record_is_not_lowered_by_a_run_that_earns_more_tickets(self):
        profiles = self.make_game()
        self.start_run()
        self.finish_with_score(3000, 1, 0)                                    # 6 tickets
        self.again(1100, 3, 2)                                                # 8 tickets, fewer points
        self.leave()
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets + tickets_for(1100, 2))
        self.assertEqual(profiles[0].high_score(SCORE_KEY), 3000)
        self.assertEqual(profiles[0].high_score(LEVEL_KEY), 3)

    def test_restarting_from_the_pause_menu_keeps_the_progress_made_so_far(self):
        profiles = self.make_game()
        self.start_run()
        run = self.scene.cat_maze.run
        run.score, run.level, run.levels_cleared = 3000, 4, 3
        self.frames(1, pygame.K_ESCAPE)
        self.frames(1, pygame.K_s)
        self.frames(1, pygame.K_RETURN)                                       # RESTART
        self.assertEqual(self.scene.cat_maze.run.score, 0)
        self.frames(1, pygame.K_ESCAPE)
        self.frames(1, pygame.K_s)
        self.frames(1, pygame.K_s)
        self.frames(1, pygame.K_RETURN)                                       # RETURN TO LOBBY with a zero-point new run
        self.frames(60)
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets + tickets_for(3000, 3))
        self.assertEqual(profiles[0].high_score(SCORE_KEY), 3000)

    def test_returning_to_the_hub_and_relaunching_is_a_new_paid_entry_with_its_own_payout(self):
        profiles = self.make_game()
        self.start_run()
        self.finish_with_score(2000, 3, 2)
        self.leave()
        first = tickets_for(2000, 2)
        self.assertEqual((profiles[0].tokens, profiles[0].tickets), (self.START_TOKENS - 1, PlayerProfile().tickets + first))
        self.frames(60)
        self.relaunch()
        self.assertEqual(profiles[0].tokens, self.START_TOKENS - 2)           # a second entry costs a second token
        self.assertEqual(self.scene.cat_maze.saved_score, 2000)               # and shows the record just set
        self.assertEqual(self.scene.cat_maze.screen, Screen.TITLE)
        self.assertEqual(self.scene.cat_maze.best.tickets, 0)                 # nothing carried over from the last entry
        self.start_run()
        self.finish_with_score(700, 2, 1)
        self.leave()
        second = tickets_for(700, 1)
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets + first + second)
        self.assertEqual(profiles[0].total_games_played, 2)
        self.assertEqual(profiles[0].high_score(SCORE_KEY), 2000)             # a worse second entry keeps the record

    def test_relaunching_and_leaving_at_once_costs_the_token_and_pays_nothing(self):
        profiles = self.make_game()
        self.frames(1, pygame.K_ESCAPE)
        self.frames(60)
        self.assertEqual(profiles[0].tokens, self.START_TOKENS - 1)
        self.relaunch()
        self.frames(1, pygame.K_ESCAPE)
        self.frames(60)
        self.assertEqual(profiles[0].tokens, self.START_TOKENS - 2)           # same as every other cabinet: a played entry
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets)

    def test_two_entries_in_a_row_cannot_be_settled_against_each_other(self):
        profiles = self.make_game()
        self.start_run()
        self.finish_with_score(2000, 3, 2)
        sessions = [self.room.active_play[0]]
        self.leave()
        self.frames(60)
        self.relaunch()
        sessions.append(self.room.active_play[0])
        self.assertIsNot(sessions[0], sessions[1])
        self.assertTrue(sessions[0].settled)
        self.assertFalse(sessions[1].settled)
        self.assertIsNot(self.scene.cat_maze, None)

    def test_asking_for_the_result_repeatedly_or_closing_the_window_never_pays_twice(self):
        profiles = self.make_game()
        self.start_run()
        self.finish_with_score(2000, 3, 2)
        for _ in range(3):
            self.scene.get_result()
        self.game.scenes.quit()                                               # the window is closed on the results screen
        self.game.scenes.quit()
        paid = tickets_for(2000, 2)
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets + paid)
        self.assertEqual(profiles[0].total_games_played, 1)

    def test_closing_the_window_mid_run_still_pays_the_progress(self):
        profiles = self.make_game()
        self.start_run()
        run = self.scene.cat_maze.run
        run.score, run.level, run.levels_cleared = 1500, 3, 2
        self.game.scenes.quit()
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets + tickets_for(1500, 2))
        self.assertEqual(profiles[0].high_score(SCORE_KEY), 1500)

    def test_play_again_and_relaunch_stay_with_the_player_who_started_it(self):
        profiles = self.make_game(two=True, starter=1)
        self.frames(1, self.confirm_key())
        self.frames(int((cfg.READY_SECONDS + 0.2) / DT))
        self.finish_with_score(1200, 2, 1)
        self.again(2200, 3, 2)
        self.leave()
        self.frames(60)
        self.assertEqual((profiles[0].tokens, profiles[0].tickets), (self.START_TOKENS, PlayerProfile().tickets))
        self.assertEqual(profiles[1].tokens, self.START_TOKENS - 1)
        self.assertEqual(profiles[1].tickets, PlayerProfile().tickets + tickets_for(2200, 2))
        self.relaunch(starter=0)                                              # now P1 starts it: P1 pays, P1 is paid
        self.assertEqual((profiles[0].tokens, profiles[1].tokens), (self.START_TOKENS - 1, self.START_TOKENS - 1))
        self.assertEqual(self.scene.cat_maze.saved_score, 0)                  # P2's record is not P1's
        self.assertEqual(self.scene.participants, [profiles[0]])

    def test_a_coupon_entry_also_pays_once_across_play_agains(self):
        from item_registry import FREE_PLAY_COUPON
        profiles = self.make_game(tokens=5)
        self.frames(1, pygame.K_ESCAPE)
        self.frames(60)
        profiles[0].inventory.add_item(FREE_PLAY_COUPON, 1)
        tokens = profiles[0].tokens
        self.room._start_game(self.machine, use_coupon=True, player=self.room.players[0])
        self.frames(30)
        self.scene = self.game.scenes.current
        self.start_run()
        self.finish_with_score(1000, 2, 1)
        self.again(1000, 2, 1)
        self.leave()
        self.assertEqual(profiles[0].tokens, tokens)                          # the coupon paid, no tokens moved
        self.assertEqual(profiles[0].inventory.get_quantity(FREE_PLAY_COUPON), 0)
        self.assertEqual(profiles[0].tickets, PlayerProfile().tickets + tickets_for(1000, 1))


class AudioLifecycleTests(LobbyCase):
    def test_the_games_own_theme_plays_and_the_room_music_returns(self):
        self.make_game()
        self.frames(60)
        audio = self.game.audio
        self.assertTrue(audio.enabled, audio.init_error)
        self.assertEqual(Game.music_for(self.game.scenes.stack), "puzzle_drop")
        self.assertEqual(audio.theme, "puzzle_drop")
        self.assertEqual(am.MUSIC_FILES["puzzle_drop"], "neon_cat_maze")
        self.assertEqual(am.THEME_TITLES["puzzle_drop"], "NEON CAT MAZE")
        self.assertTrue(audio.music_playing())
        starts = audio.music_starts
        self.frames(240)
        self.assertEqual(audio.music_starts, starts)                            # it loops, it is not restarted
        self.leave_from_title()
        self.frames(80)
        self.assertNotEqual(audio.theme, "puzzle_drop")
        self.assertTrue(audio.music_playing())

    def leave_from_title(self):
        self.frames(1, pygame.K_ESCAPE)
        self.frames(40)
        self.assertIs(self.game.scenes.current, self.room)

    def test_pause_lowers_the_music_and_resume_restores_it(self):
        self.make_game()
        self.start_run()
        self.frames(60)
        audio = self.game.audio
        self.assertEqual(audio.duck, 1.0)
        self.frames(1, pygame.K_p)
        self.frames(10)
        self.assertEqual(audio.duck, am.DUCK_PAUSED)
        self.assertEqual(audio.theme, "puzzle_drop")                            # same song, just quieter
        self.frames(1, pygame.K_p)
        self.frames(10)
        self.assertEqual(audio.duck, 1.0)

    def test_effects_play_through_the_shared_audio_manager_on_the_scenes_channel(self):
        self.make_game()
        audio = self.game.audio
        audio.clock = lambda: audio.time                                        # frames here run faster than real time
        audio.ch_playing.clear()
        self.start_run()
        self.assertEqual(audio.channels.__len__(), 2)                           # no second mixer or extra music channels
        self.scene.cat_maze.run.steer((1, 0))
        self.frames(90)
        self.assertGreater(audio.sfx_requested.get("maze_fish", 0) + audio.sfx_requested.get("maze_fish_b", 0), 2)
        self.assertGreater(audio.sfx_played.get("maze_fish", 0) + audio.sfx_played.get("maze_fish_b", 0), 0)
        owners = [label for _, label, _ in audio.sfx_owners()]
        self.assertTrue(any("PUZZLE" in o for o in owners), owners)

    def test_every_new_effect_and_the_new_track_exist_and_are_sound_files(self):
        for name in ("maze_fish", "maze_fish_b", "maze_golden", "maze_golden_spawn", "maze_catnip", "maze_catnip_end",
                     "maze_disable", "maze_life", "maze_clear", "maze_over"):
            self.assertIn(name, am.SFX_FILES)
            self.assertTrue(os.path.isfile(os.path.join(am.ASSET_DIR, "sfx", f"{name}.wav")), name)
            self.assertIn(name, am.PRIORITY)
        self.assertTrue(os.path.isfile(os.path.join(am.ASSET_DIR, "music", "neon_cat_maze.wav")))

    def test_big_moments_outrank_the_fish_munching(self):
        for big in ("maze_catnip", "maze_golden", "maze_disable", "maze_life", "maze_clear", "maze_over"):
            self.assertGreater(am.PRIORITY[big], am.PRIORITY["maze_fish"])
        self.assertGreaterEqual(am.PRIORITY["maze_over"], am.PRIORITY["maze_catnip"])

    def test_the_music_is_not_left_playing_after_quitting_the_game_from_inside(self):
        self.make_game()
        self.start_run()
        self.frames(1, pygame.K_ESCAPE)
        self.frames(1, pygame.K_s)
        self.frames(1, pygame.K_s)
        self.frames(1, pygame.K_RETURN)
        self.frames(120)
        audio = self.game.audio
        self.assertNotEqual(audio.theme, "puzzle_drop")
        self.assertFalse(audio.channels[1 - audio.active].get_busy())

    def test_the_wav_files_are_plain_22khz_16bit_mono_pcm_for_every_platform(self):
        import wave
        for path in (os.path.join(am.ASSET_DIR, "music", "neon_cat_maze.wav"),
                     os.path.join(am.ASSET_DIR, "sfx", "maze_clear.wav")):
            with wave.open(path, "rb") as w:
                self.assertEqual((w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getcomptype()),
                                 (1, 2, 22050, "NONE"))


class DisplayScalingTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(DisplayManager, "desktop_size", lambda self: BIG_DESKTOP)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        profile = PlayerProfile(profile_id="maze_d", tickets=300, tokens=50)
        self.game = Game(session=LocalSession([profile]), display_prefs=os.path.join(self.dir, "display.json"),
                         audio_prefs=os.path.join(self.dir, "audio.json"))
        self.addCleanup(self.game.quit)
        room = goto_room(self.game, "arcade_floor")
        machine = next(m for m in room.machines if m.id == "puzzle_drop")
        room._start_game(machine, player=room.players[0])
        for _ in range(30):
            self.game.step([], DT)
        self.scene = self.game.scenes.current

    def frames(self, n=1, key=None):
        for i in range(n):
            ev = [pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="")] if key and i == 0 else []
            self.game.step(ev, DT)

    def resize(self, size):
        pygame.display.set_mode(size, pygame.RESIZABLE)
        self.game.step([pygame.event.Event(pygame.VIDEORESIZE, size=size, w=size[0], h=size[1])], DT)

    def test_the_game_renders_crisply_at_800x600_1280x720_and_1920x1080(self):
        self.assertIsInstance(self.scene, CatMazeScene)
        self.frames(1, pygame.K_RETURN)
        self.frames(120)
        for size in ((800, 600), (1280, 720), (1920, 1080), (1600, 900)):
            self.resize(size)
            self.frames(5)
            lay = self.game.display.layout
            self.assertEqual(lay, dp.compute_layout(size, lay.scaling), size)
            self.assertTrue(pygame.Rect(0, 0, *size).contains(lay.rect), size)
            self.assertEqual(lay.screen_size[0] * 3, lay.screen_size[1] * 4)               # always 4:3: nothing stretched
            self.assertEqual(lay.screen_size[0] % VIEW_W, 0)
            self.assertIs(self.game.scenes.current, self.scene)
            shot = self.game.screen
            self.assertEqual(shot.get_size(), lay.screen_size)
            colours = {tuple(shot.get_at((x, y)))[:3] for x in range(0, shot.get_width(), 23) for y in range(0, shot.get_height(), 23)}
            self.assertGreater(len(colours), 6, size)

    def test_resizing_mid_game_never_changes_the_rules_or_loses_progress(self):
        self.frames(1, pygame.K_RETURN)
        self.frames(120)
        self.frames(1, pygame.K_d)
        self.frames(30)
        run = self.scene.cat_maze.run
        before = (run.score, run.lives, run.level)
        for size in ((800, 600), (1920, 1080), (1000, 640), (1280, 720)):
            self.resize(size)
            self.frames(10)
        self.assertEqual((run.lives, run.level), before[1:])
        self.assertGreaterEqual(run.score, before[0])
        self.assertEqual(self.scene.cat_maze.screen, Screen.PLAYING)
        self.assertTrue(self.scene.cat_maze.run.maze.is_open(run.cat.nearest_tile()))

    def test_fullscreen_toggle_keeps_the_game_running(self):
        self.frames(1, pygame.K_RETURN)
        self.frames(100)
        self.frames(1, pygame.K_F11)
        self.frames(30)
        self.assertIs(self.game.scenes.current, self.scene)
        self.assertEqual(self.scene.cat_maze.screen, Screen.PLAYING)
        self.frames(1, pygame.K_F11)
        self.frames(30)
        self.assertIs(self.game.scenes.current, self.scene)


if __name__ == "__main__":
    unittest.main()
