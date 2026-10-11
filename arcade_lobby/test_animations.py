"""Tests for the avatar action animations and the interactions that trigger them:
state transitions, no duplicated interactions, P1 / P2 independence, movement
staying responsive and collision boxes staying untouched.

Run headless from this folder:   python -m unittest test_animations -v
"""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from controls import P1_CONTROLS, P2_CONTROLS, SOLO_CONTROLS  # noqa: E402
from game import Game  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player import ACTIONS, FACINGS, HubPlayer, P1_LOOK, POSES, styled_sheet  # noqa: E402
from player_profile import PlayerProfile  # noqa: E402
from room_testing import goto_room  # noqa: E402
from shop_ui import ShopScene  # noqa: E402
from stations import PrizeCounter, Seat  # noqa: E402
from wardrobe_ui import WardrobeScene  # noqa: E402

DT = 1 / 60
SOLIDS = []


def key_event(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def run(player, seconds, direction=(0, 0)):
    for _ in range(int(seconds / DT) + 1):
        player.update(DT, direction, SOLIDS)


class ActionStateTests(unittest.TestCase):
    def setUp(self):
        self.p = HubPlayer((100, 100))

    def test_an_action_plays_its_pose_then_returns_to_idle(self):
        for name, (_, total) in ACTIONS.items():
            if total is None:
                continue
            p = HubPlayer((100, 100))
            p.play_action(name if name != "equip" else "equip", "down")
            self.assertEqual(p.action, name)
            run(p, total * 0.5)
            self.assertEqual(p.action, name, name)
            run(p, total)
            self.assertIsNone(p.action, name)
            self.assertEqual(p.anim.name, "idle_down")

    def test_pose_frames_are_played_while_the_action_runs(self):
        self.p.play_action("press", "up")
        self.assertEqual(self.p.anim.name, "press_up")
        self.p.play_action("pet", "left")
        self.assertEqual(self.p.anim.name, "pet_left")
        self.assertEqual(self.p.facing, "left")

    def test_walking_ends_any_action_at_once(self):
        for name in ("press", "pet", "cheer", "wave", "equip", "sit"):
            p = HubPlayer((100, 100))
            p.play_action(name, "down")
            run(p, DT, (1, 0))
            self.assertIsNone(p.action, name)
            self.assertTrue(p.moving)
            self.assertEqual(p.anim.name, "walk_right")
            self.assertIsNone(p.seat)

    def test_sitting_lasts_until_the_player_moves_or_stands(self):
        self.p.sit((120, 90), "down")
        run(self.p, 5.0)
        self.assertTrue(self.p.sitting)
        self.p.stop_action()
        self.assertFalse(self.p.sitting)
        self.assertIsNone(self.p.seat)

    def test_unknown_action_is_rejected(self):
        with self.assertRaises(ValueError):
            self.p.play_action("backflip")

    def test_walk_and_idle_behaviour_is_unchanged(self):
        run(self.p, 0.3, (0, -1))
        self.assertEqual(self.p.anim.name, "walk_up")
        run(self.p, 0.1)
        self.assertEqual(self.p.anim.name, "idle_up")
        before = self.p.y
        run(self.p, 0.5, (0, 1))
        self.assertGreater(self.p.y, before)

    def test_collision_box_never_changes_with_an_action(self):
        feet = self.p.feet.copy()
        for name in ACTIONS:
            self.p.play_action(name, "left")
            run(self.p, DT * 3)
            self.assertEqual(self.p.feet, feet, name)
        self.p.sit((130, 80), "down")
        self.assertEqual(self.p.feet, feet)           # only the DRAWING moves to the seat
        self.assertEqual((self.p.x, self.p.y), (100.0, 100.0))

    def test_emote_is_cosmetic_and_expires(self):
        self.p.play_action("cheer", "down", emote="heart")
        self.assertEqual(self.p.emote[0], "heart")
        run(self.p, 1.5)
        self.assertIsNone(self.p.emote)

    def test_every_pose_has_two_frames_for_every_facing_and_cosmetics_follow(self):
        outfit = {"hat": "pixel_crown", "tail": "cat_tail", "jacket": "rainbow_jacket"}
        sheet = styled_sheet(P1_LOOK, outfit)
        plain = styled_sheet(P1_LOOK, {})
        for facing in FACINGS:
            for pose in POSES:
                self.assertEqual(len(sheet[facing][pose]), 2)
                self.assertNotEqual(pygame.image.tobytes(sheet[facing][pose][0], "RGBA"),
                                    pygame.image.tobytes(plain[facing][pose][0], "RGBA"))

    def test_changing_clothes_in_the_middle_of_an_action_keeps_the_pose(self):
        profile = PlayerProfile(profile_id="x")
        profile.inventory.add_item("neon_cap")
        p = HubPlayer((100, 100), profile=profile)
        p.play_action("cheer", "down")
        profile.set_appearance("hat", "neon_cap")
        self.assertEqual(p.anim.name, "cheer_down")
        self.assertEqual(p.appearance, {"hat": "neon_cap"})

    def test_footstep_flag_is_raised_on_foot_down_frames_only_while_walking(self):
        steps = 0
        for _ in range(60):
            self.p.update(DT, (1, 0), SOLIDS)
            if self.p.footstep:
                steps += 1
                self.p.footstep = False
        self.assertTrue(4 <= steps <= 12)             # ~2 per 0.48 s walk cycle
        run(self.p, 1.0)
        self.p.footstep = False
        run(self.p, 1.0)
        self.assertFalse(self.p.footstep)

    def test_p1_and_p2_animate_independently(self):
        a = HubPlayer((100, 100), P1_CONTROLS, label="P1", look=P1_LOOK)
        b = HubPlayer((150, 100), P2_CONTROLS, label="P2")
        a.play_action("pet", "right", emote="heart")
        self.assertIsNone(b.action)
        self.assertIsNone(b.emote)
        run(b, 0.3, (-1, 0))
        self.assertEqual(a.action, "pet")
        b.play_action("wave", "down")
        run(a, ACTIONS["pet"][1] + .1)
        self.assertIsNone(a.action)
        self.assertEqual(b.action, "wave")


class RoomInteractionTests(unittest.TestCase):
    def setUp(self):
        self.profiles = [PlayerProfile(profile_id="ra", display_name="Ann", tickets=300, tokens=20),
                         PlayerProfile(profile_id="rb", display_name="Bo", tickets=300, tokens=20)]
        self.game = Game(session=LocalSession(self.profiles))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "arcade_floor")
        self.frames(80)

    def frames(self, n=30):
        for _ in range(n):
            self.game.step([], DT)

    def key(self, k, frames=1):
        self.game.step([key_event(k)], DT)
        self.frames(frames - 1)

    def stand_at(self, thing, index=0):
        avatar = self.room.players[index]
        avatar.x, avatar.y = thing.zone.centerx, thing.zone.bottom - 3
        self.frames(4)
        return avatar

    def seat(self, n=0):
        return [p for p in self.room.props if isinstance(p, Seat)][n]

    # ---------------------------------------------------------------- machine
    def test_e_at_a_machine_plays_the_press_pose_once(self):
        machine = self.room.machines[0]
        p = self.stand_at(machine)
        self.assertIs(p.nearby, machine)
        self.game.step([key_event(pygame.K_e)], DT)
        self.assertEqual(p.action, "press")
        self.assertIsNotNone(p.activating)
        visits = self.profiles[0].daily_tasks
        self.game.step([key_event(pygame.K_e)], DT)         # mashing E during the flash: ignored
        self.game.step([key_event(pygame.K_e)], DT)
        self.frames(30)
        self.assertEqual(len([m for m in self.game.scenes.stack if m is not self.room]), 0)
        self.assertIsNotNone(self.room.modal)                # exactly one dialogue opened

    def test_walking_still_works_right_after_pressing_and_esc_closes_the_dialogue(self):
        machine = self.room.machines[0]
        self.stand_at(machine)
        self.key(pygame.K_e, 30)
        self.assertIsNotNone(self.room.modal)
        self.key(pygame.K_ESCAPE, 5)
        self.assertIsNone(self.room.modal)
        p = self.room.players[0]
        self.game.step([key_event(pygame.K_a)], DT)
        x = p.x
        self.frames(20)
        self.assertLess(p.x, x)

    # ---------------------------------------------------------------- seats
    def test_a_stool_can_be_sat_on_and_stood_up_from(self):
        seat = self.seat()
        p = self.stand_at(seat)
        self.assertIs(p.nearby, seat)
        feet = p.feet.copy()
        self.key(pygame.K_e, 30)
        self.assertTrue(p.sitting)
        self.assertEqual(p.seat, seat.seat_pos)
        self.assertEqual(p.feet, feet)
        self.assertIsNone(p.nearby)                          # no prompt while seated
        self.key(pygame.K_e, 5)                              # E again: stand
        self.assertFalse(p.sitting)
        self.assertEqual(p.feet, feet)
        self.assertIs(self.room.modal, None)

    def test_moving_stands_up_immediately(self):
        p = self.stand_at(self.seat())
        self.key(pygame.K_e, 30)
        self.assertTrue(p.sitting)
        self.game.step([key_event(pygame.K_d)], DT)
        self.frames(3)
        self.assertFalse(p.sitting)
        self.assertTrue(p.moving)

    def test_a_second_player_cannot_take_an_occupied_stool(self):
        # two-player session
        game = Game(session=LocalSession(self.profiles))
        self.addCleanup(game.quit)
        room = goto_room(game, "arcade_floor")
        for _ in range(80):
            game.step([], DT)
        seat = [p for p in room.props if isinstance(p, Seat)][0]
        a, b = room.players
        for avatar in (a, b):
            avatar.x, avatar.y = seat.zone.centerx, seat.zone.bottom - 3
        for _ in range(4):
            game.step([], DT)
        game.step([key_event(pygame.K_e)], DT)               # P1 sits
        for _ in range(30):
            game.step([], DT)
        self.assertTrue(a.sitting)
        game.step([key_event(pygame.K_RETURN)], DT)          # P2 tries the same stool
        for _ in range(30):
            game.step([], DT)
        self.assertFalse(b.sitting)
        self.assertTrue(a.sitting)

    def test_changing_room_stands_everyone_up(self):
        p = self.stand_at(self.seat())
        self.key(pygame.K_e, 30)
        self.assertTrue(p.sitting)
        self.room._close_transients()
        self.assertFalse(p.sitting)

    # ---------------------------------------------------------------- emotes
    def test_t_waves_then_celebrates_and_p2_has_its_own_key(self):
        a, b = self.room.players
        self.key(pygame.K_t)
        self.assertEqual(a.action, "wave")
        self.assertIsNone(b.action)
        self.key(pygame.K_t)
        self.assertEqual(a.action, "cheer")
        self.key(pygame.K_SLASH)
        self.assertEqual(b.action, "wave")
        self.assertEqual(a.action, "cheer")

    def test_emote_does_not_interrupt_walking_input(self):
        a = self.room.players[0]
        self.key(pygame.K_t)
        self.game.step([key_event(pygame.K_d)], DT)
        self.frames(3)
        self.assertIsNone(a.action)
        self.assertTrue(a.moving)


class CatAndShopTests(unittest.TestCase):
    def setUp(self):
        self.profiles = [PlayerProfile(profile_id="ca", display_name="Ann", tickets=300),
                         PlayerProfile(profile_id="cb", display_name="Bo", tickets=300)]
        self.game = Game(session=LocalSession(self.profiles))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "home")
        self.frames(60)
        for _ in range(4):
            if self.room.modal is None:
                break
            self.key(pygame.K_ESCAPE, 10)

    def frames(self, n=30):
        for _ in range(n):
            self.game.step([], DT)

    def key(self, k, frames=1):
        self.game.step([key_event(k)], DT)
        self.frames(frames - 1)

    def test_petting_a_cat_crouches_once_with_a_heart_and_counts_once(self):
        cat = self.room.cats.cats[0]
        p = self.room.players[0]
        self.room.players[1].x, self.room.players[1].y = 20, 20
        p.x, p.y = cat.x - 12, cat.y
        self.frames(6)
        self.assertIs(p.nearby_cat, cat)
        before = self.profiles[0].cats_petted
        self.game.step([key_event(pygame.K_e), key_event(pygame.K_e)], DT)       # a double press
        self.assertEqual(p.action, "pet")
        self.assertEqual(p.emote[0], "heart")
        self.assertEqual(self.profiles[0].cats_petted, before + 1)
        self.assertIsNone(self.room.players[1].action)                           # P2 untouched

    def test_buying_at_the_prize_counter_celebrates_without_double_charging(self):
        owner = self.game.session.players[0]
        shop = ShopScene(self.game, owner)
        self.game.scenes.push(shop)
        self.frames(60)
        from prize_shop import entry_for
        entry = entry_for("star_pin")
        shop._answered(entry, "BUY")
        self.assertEqual(owner.avatar.action, "cheer")
        tickets = self.profiles[0].tickets
        shop._answered(entry, "BUY")                       # a second answer: already owned, nothing charged
        self.assertEqual(self.profiles[0].tickets, tickets)
        self.assertIsNone(self.room.players[1].action)

    def test_equipping_in_the_wardrobe_plays_the_outfit_change(self):
        self.profiles[0].inventory.add_item("neon_cap")
        owner = self.game.session.players[0]
        scene = WardrobeScene(self.game, owner)
        self.game.scenes.push(scene)
        self.frames(40)
        scene.set_tab(1)                                    # HAT
        scene.select(scene.rows.index("neon_cap"))
        scene.activate()
        self.assertEqual(owner.avatar.action, "equip")
        self.assertEqual(self.profiles[0].appearance, {"hat": "neon_cap"})

    def test_the_prize_counter_glass_glint_draws(self):
        counter = PrizeCounter((100, 100))
        surf = pygame.Surface((400, 300), pygame.SRCALPHA)
        for t in (0.0, 0.3, 0.8, 2.0):
            counter.time = t
            counter.draw(surf)


if __name__ == "__main__":
    unittest.main()
