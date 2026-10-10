"""Pure result policy tests; no racer window or asset loading required."""
import unittest
from types import SimpleNamespace as NS

from racer_results import RacerOutcome, RacerVisitResults


def racer(state="FINISHED", mode="COMPETITIVE", score=3000, position=2, size=4):
    return NS(state=NS(value=state), mode=NS(value=mode), player=NS(score=score),
              manager=NS(result={"score": score, "position": position, "field_size": size}
                         if state in ("FINISHED", "GAME_OVER") else None))


class RacerResultTests(unittest.TestCase):
    def test_finish_uses_frozen_score_and_rank(self):
        r = racer()
        r.player.score = 999999
        result = RacerOutcome.from_racer(r)
        self.assertEqual((result.score, result.position, result.status), (3000, 2, "completed"))
        self.assertEqual(result.tickets, 23)

    def test_rank_changes_finish_reward(self):
        self.assertEqual(RacerOutcome.from_racer(racer(position=1)).tickets, 28)
        self.assertEqual(RacerOutcome.from_racer(racer(position=4)).tickets, 13)

    def test_time_up_has_no_completion_bonus(self):
        result = RacerOutcome.from_racer(racer(state="GAME_OVER"))
        self.assertEqual((result.status, result.tickets), ("game_over", 3))

    def test_endless_has_no_rank(self):
        result = RacerOutcome.from_racer(racer(state="GAME_OVER", mode="ENDLESS"))
        self.assertEqual((result.mode, result.position, result.tickets), ("ENDLESS", None, 3))

    def test_abandon_does_not_record_score_or_pay(self):
        for state in ("TITLE", "COUNTDOWN", "PLAYING", "MODE_SELECT"):
            with self.subTest(state=state):
                pr = RacerOutcome.from_racer(racer(state=state)).player_result("p2")
                self.assertEqual((pr.profile_id, pr.score, pr.reward.tickets), ("p2", None, 0))

    def test_score_ticket_cap(self):
        self.assertEqual(RacerOutcome.from_racer(racer(score=999999)).tickets, 70)

    def test_replay_keeps_best_instead_of_summing(self):
        visit = RacerVisitResults()
        visit.observe(racer())
        visit.observe(racer(state="PLAYING"))
        visit.observe(racer(score=1000, position=4))
        self.assertEqual(visit.outcome.tickets, 23)
        visit.observe(racer(score=5000, position=1))
        self.assertEqual(visit.outcome.tickets, 30)

    def test_new_visit_has_no_previous_reward(self):
        self.assertEqual(RacerVisitResults().outcome.tickets, 0)

    def test_result_belongs_to_participant(self):
        visit = RacerVisitResults()
        visit.observe(racer())
        result = visit.get_result([NS(profile_id="p2")])
        self.assertIsNone(result.for_profile("p1"))
        self.assertEqual(result.for_profile("p2").reward.tickets, 23)
