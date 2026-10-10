"""Exercise the real room settlement boundary with controlled racer outcomes."""
import os
from unittest import mock

import pygame

from daily_tasks import DailyTaskManager
from profile_manager import ProfileManager
from retro_racer_scene import RetroRacerScene
from settings import DAILY_TASK_POOL
from test_multiplayer import DAY1, TwoPlayerTest, key
from test_racer_results import racer


class RacerSettlementTests(TwoPlayerTest):
    def launch(self, player=None):
        player = player or self.p2
        room = self.arcade()
        machine = self.machine(room, "retro_racer")
        scene = RetroRacerScene(self.game, machine)
        scene.attach_players([player], [self.p1 if player is self.p2 else self.p2])
        session = machine.start_play(player.profile)
        self.assertIsNotNone(session)
        room.active_play = (session, scene)
        room.active_plays = [(player.avatar, session)]
        return room, scene, session

    def test_room_pays_real_score_only_to_starter_once(self):
        room, scene, session = self.launch()
        before = (self.p1.profile.tickets, self.p2.profile.tickets)
        scene.results.observe(racer())
        room._end_play(True)
        room._end_play(True)
        session.settle_result(scene.get_result().for_profile(self.p2.profile.profile_id))
        self.assertEqual(self.p1.profile.tickets, before[0])
        self.assertEqual(self.p2.profile.tickets, before[1] + 23)
        self.assertEqual(self.p2.profile.high_score("retro_racer"), 3000)

    def test_abandon_pays_nothing_and_keeps_entry_charge(self):
        tokens = self.p2.profile.tokens
        room, scene, _ = self.launch()
        before = self.p2.profile.tickets
        scene.results.observe(racer(state="PLAYING"))
        room._end_play(True)
        self.assertEqual(self.p2.profile.tickets, before)
        self.assertEqual(self.p2.profile.tokens, tokens - 1)
        self.assertNotIn("retro_racer", self.p2.profile.high_scores)

    def test_loading_failure_refunds_once(self):
        tokens = self.p2.profile.tokens
        room, scene, _ = self.launch()
        scene.error = "LOAD FAILED"
        room._end_play(True)
        room._end_play(True)
        self.assertEqual(self.p2.profile.tokens, tokens)

    def test_time_up_and_endless_use_actual_score(self):
        for mode in ("COMPETITIVE", "ENDLESS"):
            with self.subTest(mode=mode):
                room, scene, _ = self.launch()
                before = self.p2.profile.tickets
                scene.results.observe(racer(state="GAME_OVER", mode=mode))
                room._end_play(True)
                self.assertEqual(self.p2.profile.tickets, before + 3)

    def test_enter_replay_captures_before_reset(self):
        room, scene, _ = self.launch()
        r = racer()
        def reset(event):
            r.state.value = "COUNTDOWN"
            r.manager.result = None
        r.handle_event = reset
        with mock.patch.object(RetroRacerScene, "_racer", r):
            scene.handle_event(key(pygame.K_RETURN))
        self.assertEqual(scene.results.outcome.tickets, 23)
        scene.results.observe(racer(state="PLAYING", score=999999))
        self.assertEqual(scene.get_result().player_results[0].reward.tickets, 23)

    def test_quit_captures_result_and_stops_engine(self):
        room, scene, _ = self.launch()
        r = racer()
        r.audio = mock.Mock()
        before = self.p2.profile.tickets
        self.game.scenes.stack.append(scene)
        with mock.patch.object(RetroRacerScene, "_racer", r):
            self.game.quit()
            self.game.quit()
        self.assertEqual(self.p2.profile.tickets, before + 23)
        r.audio.stop_engine.assert_called_once()

    def test_pop_captures_end_screen_before_room_resumes(self):
        room, scene, _ = self.launch()
        r = racer()
        r.audio = mock.Mock()
        r.set_paused = mock.Mock()
        before = self.p2.profile.tickets
        self.game.scenes.stack.append(scene)
        with mock.patch.object(RetroRacerScene, "_racer", r):
            self.game.scenes.pop(fade=False)
        self.assertEqual(self.p2.profile.tickets, before + 23)

    def test_update_captures_new_end_state(self):
        _, scene, _ = self.launch()
        r = racer(state="PLAYING")
        r.running = True
        def finish(dt, controls):
            r.state.value = "FINISHED"
            r.manager.result = racer().manager.result
        r.update = finish
        with mock.patch.object(RetroRacerScene, "_racer", r):
            scene.update(1 / 60)
        self.assertEqual(scene.results.outcome.score, 3000)

    def test_reward_interface_never_returns_placeholder(self):
        _, scene, _ = self.launch()
        self.assertEqual(scene.get_reward().tickets_earned, 0)
        scene.results.observe(racer())
        self.assertEqual((scene.get_reward().score, scene.get_reward().tickets_earned), (3000, 23))

    def test_settlement_saves_score_and_tickets(self):
        room, scene, _ = self.launch()
        before = self.p2.profile.tickets
        scene.results.observe(racer())
        room._end_play(True)
        loaded = ProfileManager(os.path.join(self.dir, "saves")).load_profile(self.p2.profile.profile_id)
        self.assertEqual(loaded.tickets, before + 23)
        self.assertEqual(loaded.high_score("retro_racer"), 3000)

    def test_real_score_completes_high_score_daily_task(self):
        spec = next(s for s in DAILY_TASK_POOL if s["id"] == "beat_high_score")
        self.assertTrue(spec.get("available", True))
        self.p2.profile._tasks = DailyTaskManager(pool=[spec], count=1)
        self.p2.profile._tasks.ensure_current(DAY1)
        room, scene, _ = self.launch()
        scene.results.observe(racer())
        room._end_play(True)
        self.assertTrue(self.p2.profile._tasks.get("beat_high_score").completed)
