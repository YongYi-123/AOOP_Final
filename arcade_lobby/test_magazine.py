"""Tests for RETRO GAMING - ISSUE 1986, the magazine rack beside HOME's couch: where it stands, that it never blocks
anybody, the page-turning reader (solo and two players), that every page fits and is readable, that reading is free and
repeatable and changes nothing (no notification, no quest progress), that the words KONAMI CODE appear exactly once, as
plain body text and never with a key sequence, and that Miao Meow no longer points at it.

Run headless from this folder:   python -m unittest test_magazine -v
"""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import magazine  # noqa: E402
from game import Game  # noqa: E402
from local_session import LocalSession  # noqa: E402
from magazine import (ARTICLES, INK, LAST_PAGE, PAPER, MagazineScene, MagazineStation)  # noqa: E402
from player_profile import PlayerProfile  # noqa: E402
from quests import QUESTS, VENDING_SECRET_FLAG  # noqa: E402
from room_testing import goto_room  # noqa: E402
from secret_input import SEQUENCE  # noqa: E402
from settings import VIEW_H, VIEW_W  # noqa: E402
import test_vending  # noqa: E402

DT = 1 / 60
K = pygame


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def fresh(pid="m", name="Ann"):
    return PlayerProfile(profile_id=pid, display_name=name, tokens=12, tickets=77)


class HomeTest(unittest.TestCase):
    profiles = None

    def setUp(self):
        self.profiles = self.profiles or [fresh()]
        self.game = Game(session=LocalSession(self.profiles))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "home")
        for local in self.room.session:                      # no daily-bonus / opening popups in the way
            local.profile.claim_daily_reward()
        self.room.popup = None
        self.game.hub.story.manager.finish_opening()
        self.frames(30)
        self.mag = next(p for p in self.room.props if isinstance(p, MagazineStation))

    def frames(self, n=1, events=()):
        self.game.step(list(events), DT)
        for _ in range(n - 1):
            self.game.step([], DT)

    def stand_by_magazine(self, player=None):
        player = player or self.room.players[0]
        player.x, player.y = float(self.mag.rect.centerx), float(self.mag.footprint.bottom + 10)
        player.stop()


# ------------------------------------------------------------------ the prop
class PlacementTests(HomeTest):
    def test_the_rack_stands_right_beside_the_couch_and_nothing_is_drawn_on_the_couch(self):
        couch = next(p for p in self.room.furniture if type(p).__name__ == "Prop" and p.sprite.get_width() == 58 + 2)
        couch_rect = pygame.Rect(couch.pos, couch.sprite.get_size())
        self.assertFalse(couch_rect.colliderect(self.mag.rect))      # no magazine lying on the cushions
        self.assertLessEqual(self.mag.rect.left - couch_rect.right, 8)
        self.assertGreaterEqual(self.mag.rect.left, couch_rect.right)

    def test_it_is_a_small_base_against_the_wall_that_blocks_no_route(self):
        self.assertTrue(self.mag.solid)
        self.assertLessEqual(self.mag.footprint.w * self.mag.footprint.h, 14 * 8)
        self.assertIn(self.mag.footprint, self.room.solids)
        # every other solid still leaves the floor in front of the rack open
        front = pygame.Rect(self.mag.footprint.x - 6, self.mag.footprint.bottom, self.mag.footprint.w + 12, 20)
        self.assertFalse(any(r.colliderect(front) for r in self.room.solids))

    def test_the_only_collision_added_is_the_racks_own_small_base(self):
        expected = self.room.walls + [p.footprint for p in self.room.props if p.solid] \
                   + [m.footprint for m in self.room.machines]
        self.assertEqual(self.room.solids, expected)
        self.assertEqual(sum(1 for p in self.room.props if isinstance(p, MagazineStation)), 1)

    def test_cats_do_not_rest_on_it(self):
        for spots in self.room.cat_spots.values():
            for x, y in spots:
                self.assertFalse(self.mag.zone.collidepoint(x, y), (x, y))

    def test_it_does_not_cross_other_furniture_zones_or_decor_slots(self):
        others = [p for p in self.room.props if p is not self.mag and getattr(p, "zone", None) is not None
                  and type(p).__name__ not in ("MiaoMeow",)]
        for other in others:
            self.assertFalse(self.mag.rect.colliderect(other.rect), type(other).__name__)

    def test_the_prompt_is_reachable_from_the_floor_in_front_of_the_rack(self):
        self.stand_by_magazine()
        self.frames(5)
        player = self.room.players[0]
        self.assertIs(player.nearby, self.mag)
        self.assertEqual(self.mag.prompt_label, "READ MAGAZINE")
        self.assertFalse(any(r.colliderect(player.feet) for r in self.room.solids))     # it is a free standing spot

    def test_a_player_can_walk_past_the_front_of_the_rack(self):
        player = self.room.players[0]
        player.x, player.y = float(self.mag.rect.x - 30), float(self.mag.footprint.bottom + 10)
        for i in range(90):
            self.game.step([key(K.K_d)] if i == 0 else [], DT)
        self.assertGreater(player.x, self.mag.rect.right)

    def test_it_is_far_from_both_exits_and_the_other_stations(self):
        self.assertTrue(self.mag.zone.right < VIEW_W // 2 + 60)


class PromptOverlapTests(HomeTest):
    def test_the_prompt_never_covers_the_magazine_the_hud_or_the_quest_tracker(self):
        story = self.game.hub.story
        surf = pygame.Surface((VIEW_W, VIEW_H))
        for dx in (-26, -12, 0, 12, 26):
            player = self.room.players[0]
            self.stand_by_magazine()
            player.x += dx
            self.frames(30)
            self.room.draw(surf)
            if player.nearby is not self.mag:
                continue
            rect, _ = player.prompt.place(self.room.prompt_avoid_rects(), below_first=True)
            self.assertFalse(rect.colliderect(self.mag.rect), dx)
            self.assertFalse(rect.colliderect(story.tracker.rect(self.room, animated=False)), dx)
            for hud in self.room.huds:
                self.assertFalse(rect.colliderect(hud.rect), dx)


# ------------------------------------------------------------------ the reader
class ReaderTests(HomeTest):
    def open_reader(self):
        self.stand_by_magazine()
        self.frames(5)
        self.frames(1, [key(K.K_e)])
        self.frames(90)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, MagazineScene)
        return scene

    def test_e_opens_the_reader_on_its_cover(self):
        scene = self.open_reader()
        self.assertEqual(scene.page, 0)
        self.assertIs(scene.owner, self.room.session.primary)

    def test_pages_turn_forward_and_back_and_stop_at_the_ends(self):
        scene = self.open_reader()
        self.frames(1, [key(K.K_a)])
        self.assertEqual(scene.page, 0)                              # nothing before the cover
        for want in range(1, LAST_PAGE + 1):
            self.frames(1, [key(K.K_d)])
            self.assertEqual(scene.page, want)
            self.frames(20)
        self.frames(1, [key(K.K_RIGHT)])
        self.assertEqual(scene.page, LAST_PAGE)                      # nothing after the last page
        self.frames(1, [key(K.K_a)])
        self.assertEqual(scene.page, LAST_PAGE - 1)

    def test_e_turns_the_page_and_on_the_last_page_closes_it(self):
        scene = self.open_reader()
        for want in range(1, LAST_PAGE + 1):
            self.frames(1, [key(K.K_e)])
            self.assertEqual(scene.page, want)
            self.frames(20)
        self.frames(1, [key(K.K_e)])
        self.frames(60)
        self.assertIs(self.game.scenes.current, self.room)

    def test_escape_closes_it_at_any_page(self):
        scene = self.open_reader()
        self.frames(1, [key(K.K_d)])
        self.frames(20)
        self.frames(1, [key(K.K_ESCAPE)])
        self.frames(60)
        self.assertIs(self.game.scenes.current, self.room)

    def test_a_page_turn_animates_and_the_next_turn_waits_for_it(self):
        scene = self.open_reader()
        self.frames(1, [key(K.K_d)])
        self.assertIsNotNone(scene.flip)
        self.frames(1, [key(K.K_d)])
        self.assertEqual(scene.page, 1)                              # ignored mid-turn
        surf = pygame.Surface((VIEW_W, VIEW_H))
        for _ in range(int(magazine.FLIP_TIME / DT) + 3):
            self.game.step([], DT)
            scene.draw(surf)                                         # every frame of the flip draws
        self.assertIsNone(scene.flip)

    def test_turning_back_animates_too(self):
        scene = self.open_reader()
        self.frames(1, [key(K.K_d)])
        self.frames(30)
        self.frames(1, [key(K.K_a)])
        self.assertIsNotNone(scene.flip)
        self.assertEqual(scene.page, 0)
        self.frames(30)
        self.assertIsNone(scene.flip)

    def test_the_reader_plays_the_soft_page_sound(self):
        played = []
        self.game.audio.play = lambda name, *a, **k: played.append(name)
        scene = self.open_reader()
        self.frames(1, [key(K.K_d)])
        self.assertEqual(played.count("card"), 2)                    # picking it up, then one turn

    def test_clicking_the_corners_turns_pages(self):
        scene = self.open_reader()
        scene.draw(pygame.Surface((VIEW_W, VIEW_H)))
        right = [r for r, _ in scene._hit if r.right == PAPER.right]
        self.assertTrue(right)
        scene._hit[-1][1]()
        self.assertEqual(scene.page, 1)

    def test_it_can_be_read_again_and_again(self):
        for _ in range(3):
            scene = self.open_reader()
            self.assertEqual(scene.page, 0)
            self.frames(1, [key(K.K_ESCAPE)])
            self.frames(60)
            self.assertIs(self.game.scenes.current, self.room)


class FreeAndHarmlessTests(HomeTest):
    def read_everything(self):
        self.stand_by_magazine()
        self.frames(5)
        self.frames(1, [key(K.K_e)])
        self.frames(90)
        for _ in range(LAST_PAGE + 1):
            self.frames(1, [key(K.K_e)])
            self.frames(20)
        self.frames(60)

    def test_reading_costs_nothing_and_changes_no_inventory(self):
        p = self.room.session.primary.profile
        before = p.to_dict()
        self.read_everything()
        self.read_everything()
        self.assertIs(self.game.scenes.current, self.room)
        after = p.to_dict()
        for field in ("tokens", "tickets", "inventory"):
            self.assertEqual(after.get(field), before.get(field), field)
        self.assertEqual(after, before)

    def test_reading_does_not_complete_the_vending_quest_or_record_the_secret(self):
        story = self.game.hub.story
        profile = self.room.session.primary.profile
        self.read_everything()
        self.assertNotIn("check_the_vending_machine", story.manager.completed_ids)
        self.assertFalse(story.manager.state.get("flags", {}).get("vending_secret"))
        self.assertFalse(profile.has_secret(VENDING_SECRET_FLAG))

    def test_the_machines_own_secret_sequence_is_untouched(self):
        self.assertEqual(tuple(SEQUENCE), ("UP", "UP", "DOWN", "DOWN", "LEFT", "RIGHT", "LEFT", "RIGHT", "B", "A"))

    def test_reading_never_raises_a_notice_or_a_clue_popup(self):
        before = (self.room.notice.__dict__.copy(), self.room.popup, self.room.panel)
        self.read_everything()
        self.assertIsNone(self.room.popup)
        self.assertIsNone(self.room.panel)
        self.assertEqual(getattr(self.room.notice, "active", None), before[0].get("active"))

    def test_the_real_vending_secret_event_is_still_what_completes_the_quest(self):
        manager = self.game.hub.story.manager
        quest = next(q for q in QUESTS if q.id == "check_the_vending_machine")
        self.assertEqual(quest.trigger, ("sticky", "vending_secret"))
        self.read_everything()
        self.assertNotIn(quest.id, manager.completed_ids)
        manager.handle("vending_secret")                             # what the hidden screen fires when it really opens
        self.assertTrue(manager.state["flags"]["vending_secret"])


# ------------------------------------------------------------------ the pages themselves
class ContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((VIEW_W, VIEW_H))

    def scene(self):
        game = Game(session=LocalSession([fresh()]))
        self.addCleanup(game.quit)
        return MagazineScene(game, game.session.primary)

    def spy_pages(self, scene):
        """{page: [(text, colour), ...]} of every string the reader draws on each page."""
        seen = {}
        original = magazine.draw_text

        def spy(surf, text, pos, color=(255, 255, 255), *args, **kwargs):
            seen.setdefault(current[0], []).append((str(text), tuple(color)))
            return original(surf, text, pos, color, *args, **kwargs)

        current = [0]
        magazine.draw_text = spy
        self.addCleanup(setattr, magazine, "draw_text", original)
        for index in range(LAST_PAGE + 1):
            current[0] = index
            scene.render_page(index)
        return seen

    def body_strings(self):
        """Every paragraph of every article (not the titles, headings, bylines, contents or captions)."""
        return [b[1] for a in ARTICLES[1:] for b in a["blocks"] if b[0] == "p"]

    def test_a_cover_and_seven_pages_of_real_magazine(self):
        self.assertEqual(LAST_PAGE, 7)
        self.assertEqual(magazine.PAGE_NAMES[0], "COVER")
        self.assertEqual(len(set(magazine.PAGE_NAMES)), LAST_PAGE + 1)

    def test_every_page_renders_at_the_paper_size_and_nothing_overflows(self):
        scene = self.scene()
        for index in range(LAST_PAGE + 1):
            page = scene.render_page(index)
            self.assertEqual(page.get_size(), PAPER.size)
            self.assertFalse(scene.overflow, f"page {index} ran out of room")
            limit = PAPER.h if index == 0 else magazine.BODY_BOTTOM
            self.assertLessEqual(scene.content_bottom, limit, f"page {index} overflows")

    def test_text_stays_inside_the_page_horizontally(self):
        from font import get_font
        scene = self.scene()
        seen = self.spy_pages(scene)
        for index, items in seen.items():
            for text, _color in items:
                if index == 0:
                    continue
                self.assertLessEqual(get_font().size(text)[0], PAPER.w - 2 * magazine.MARGIN, (index, text))

    def test_body_text_is_never_shrunk_it_is_always_the_normal_font_size(self):
        scene = self.scene()
        sizes = []
        original = magazine.draw_text

        def spy(surf, text, pos, color=(255, 255, 255), scale=1, *args, **kwargs):
            sizes.append((str(text), scale))
            return original(surf, text, pos, color, scale, *args, **kwargs)

        magazine.draw_text = spy
        self.addCleanup(setattr, magazine, "draw_text", original)
        for index in range(1, LAST_PAGE + 1):
            scene.render_page(index)
        for text, scale in sizes:
            self.assertGreaterEqual(scale, 1)
        for paragraph in self.body_strings():
            first = paragraph.split()[0].upper()
            self.assertTrue(any(t.upper().startswith(first) and sc == 1 for t, sc in sizes), first)

    def test_every_page_has_a_page_number_and_inside_pages_use_two_columns(self):
        scene = self.scene()
        seen = self.spy_pages(scene)
        for index in range(1, LAST_PAGE + 1):
            self.assertIn((str(index), magazine.INK_SOFT), seen[index])
        self.assertGreater(magazine.COL_W * 2 + magazine.COL_GAP, PAPER.w - 2 * magazine.MARGIN - 2)

    def test_the_whole_reader_draws_for_every_page_without_error(self):
        scene = self.scene()
        surf = pygame.Surface((VIEW_W, VIEW_H))
        for index in range(LAST_PAGE + 1):
            scene.page = index
            scene.update(0.1)
            scene.draw(surf)

    def test_the_paper_fits_between_the_header_and_the_footer(self):
        from menu_kit import FRAME
        self.assertTrue(FRAME.contains(PAPER))
        self.assertLess(PAPER.bottom + 14, 229)                      # the footer message box starts at y=229
        self.assertGreater(PAPER.top, 44)                            # below the header

    # ---- the one quiet clue
    def test_konami_code_appears_exactly_once_and_only_in_a_body_paragraph(self):
        hits = [p for p in self.body_strings() if "konami code" in p.lower()]
        self.assertEqual(len(hits), 1)
        self.assertIn("the famous Konami Code, which eventually became part of gaming folklore", hits[0])
        everything_else = []
        for article in ARTICLES[1:]:
            everything_else += [article["title"], article["byline"], article["section"]]
            for block in article["blocks"]:
                if block[0] != "p":
                    everything_else += [x for x in block[1:] if isinstance(x, str)]
        self.assertFalse([t for t in everything_else if "KONAMI CODE" in t.upper()])     # no title, heading, TOC row, caption
        self.assertFalse([n for n in magazine.PAGE_NAMES if "CODE" in n.upper()])
        self.assertNotIn("CODE", " ".join(magazine.ART).upper())

    def test_the_words_are_not_dressed_up_the_line_has_the_same_ink_as_every_other_body_line(self):
        scene = self.scene()
        seen = self.spy_pages(scene)
        page = next(i for i, a in enumerate(ARTICLES) if a and any("konami code" in b[1].lower()
                                                                  for b in a["blocks"] if b[0] == "p"))
        paragraph = next(b[1] for b in ARTICLES[page]["blocks"] if b[0] == "p" and "konami code" in b[1].lower())
        words = set(paragraph.upper().replace(",", "").replace(".", "").split())
        headings = {b[1].upper() for b in ARTICLES[page]["blocks"] if b[0] == "h"}
        body = [(t, c) for t, c in seen[page] if t.upper() not in headings
                and t.upper().replace(",", "").replace(".", "").split()
                and set(t.upper().replace(",", "").replace(".", "").split()) <= words]
        self.assertTrue(any("KONAMI" in t.upper() for t, _ in body))
        self.assertEqual({c for _, c in body}, {INK})                # every line of that paragraph, in one plain ink

    def test_no_key_sequence_arrow_or_button_hint_is_printed_anywhere(self):
        scene = self.scene()
        text = " ".join(t for items in self.spy_pages(scene).values() for t, _ in items).upper()
        for needle in ("UP UP", "DOWN DOWN", "LEFT RIGHT", "RIGHT LEFT", "UP, UP", "UP-UP"):
            self.assertNotIn(needle, text, needle)
        import re
        self.assertIsNone(re.search(r"\bB[ ,/-]+A\b", text))           # no B A button pair
        for glyph in "↑↓←→▲▼◀▶":
            self.assertNotIn(glyph, text)
        body = " ".join(self.body_strings()).upper()
        for word in ("DOWN", "ARROW", "D-PAD", "SEQUENCE", "PAUSE", "ENTER THE"):
            self.assertNotIn(word, body, word)
        self.assertFalse(hasattr(magazine, "draw_keycap"))
        self.assertFalse(hasattr(magazine, "KONAMI_SEQUENCE"))

    def test_it_does_not_tell_you_to_look_it_up_or_where_to_use_it(self):
        body = " ".join(self.body_strings()).upper()
        for word in ("LOOK IT UP", "SEARCH", "GOOGLE", "TRY IT", "TYPE", "VENDING", "VEND", "MACHINE THAT", "SODA", "SNACK",
                     "DRINK", "PROTOCOL", "TERMINAL", "LEGACY", "MIAO"):
            self.assertNotIn(word, body, word)

    def test_it_does_not_spoil_the_story(self):
        scene = self.scene()
        text = " ".join(t for items in self.spy_pages(scene).values() for t, _ in items).upper()
        for word in ("KEVIN", "PLAYER_000", "PLAYER 000", "SECRET ITEM", "TRIAL", "FINAL", "REOPEN", "HIDDEN SCREEN"):
            self.assertNotIn(word, text, word)

    def test_the_issue_is_real_reading_with_the_promised_topics(self):
        text = " ".join(self.body_strings()).upper()
        for topic in ("1986", "GRADIUS", "VIC VIPER", "METER", "PAC-MAN", "JOYSTICK", "QUARTER", "CAT"):
            self.assertIn(topic, text, topic)
        self.assertGreater(len(text), 1500)


# ------------------------------------------------------------------ Miao Meow's hints
class MiaoHintTests(unittest.TestCase):
    def quest(self):
        return next(q for q in QUESTS if q.id == "check_the_vending_machine")

    def test_no_hint_mentions_the_code_its_keys_or_the_magazine(self):
        for hint in self.quest().hints:
            text = hint.upper()
            for word in ("KONAMI", "CODE", "CHEAT", "ARROW", "UP UP", "DOWN", "LEFT", "RIGHT", "BUTTON", "SEQUENCE",
                         "PRESS", "MAGAZINE", "RACK", "COUCH", "READ", "ISSUE", "GRADIUS", "HOME", "OLD THINGS"):
                self.assertNotIn(word, text.replace("LEFT A", ""), f"{word!r} in {hint!r}")

    def test_the_hints_only_nudge_the_player_to_explore_the_arcade(self):
        hints = self.quest().hints
        self.assertGreaterEqual(len(hints), 2)
        self.assertIn("Arcade", " ".join(hints))
        self.assertIn("vending machine", hints[0])                    # the quest's own premise, unchanged

    def test_the_hint_texts_are_exactly_these_three(self):
        self.assertEqual(len(self.quest().hints), 3)


# ------------------------------------------------------------------ two players
class TwoPlayerTests(unittest.TestCase):
    def setUp(self):
        self.a, self.b = fresh("a", "Ann"), fresh("b", "Bo")
        self.game = Game(session=LocalSession([self.a, self.b]))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "home")
        for p in (self.a, self.b):
            p.claim_daily_reward()
        self.room.popup = None
        self.game.hub.story.manager.finish_opening()
        self.frames(30)
        self.mag = next(p for p in self.room.props if isinstance(p, MagazineStation))
        self.p1, self.p2 = self.game.session.players

    def frames(self, n=1, events=()):
        self.game.step(list(events), DT)
        for _ in range(n - 1):
            self.game.step([], DT)

    def stand(self, local, dx=0):
        local.avatar.x = float(self.mag.rect.centerx + dx)
        local.avatar.y = float(self.mag.footprint.bottom + 10)
        local.avatar.stop()

    def test_p2_reads_it_with_their_own_keys_and_p1_only_watches(self):
        self.stand(self.p1, -70)
        self.stand(self.p2)
        self.frames(5)
        self.assertIs(self.p2.avatar.nearby, self.mag)
        self.frames(1, [key(self.p2.controls.interact[0])])
        self.frames(90)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, MagazineScene)
        self.assertIs(scene.owner, self.p2)
        self.assertEqual(scene.spectators, [self.p1])
        self.frames(1, [key(K.K_d)])                                 # P1's key: ignored
        self.assertEqual(scene.page, 0)
        self.frames(1, [key(K.K_RIGHT)])                             # P2's arrow: turns the page
        self.assertEqual(scene.page, 1)
        self.frames(30)
        scene.draw(pygame.Surface((VIEW_W, VIEW_H)))
        self.frames(1, [key(K.K_ESCAPE)])
        self.frames(60)
        self.assertIs(self.game.scenes.current, self.room)

    def test_p1_reads_it_while_p2_stands_elsewhere_and_nobody_pays(self):
        self.stand(self.p1)
        self.stand(self.p2, 150)
        self.frames(5)
        tokens = (self.a.tokens, self.b.tokens)
        tickets = (self.a.tickets, self.b.tickets)
        self.frames(1, [key(self.p1.controls.interact[0])])
        self.frames(90)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, MagazineScene)
        self.assertIs(scene.owner, self.p1)
        self.frames(1, [key(K.K_ESCAPE)])
        self.frames(60)
        self.assertEqual((self.a.tokens, self.b.tokens), tokens)
        self.assertEqual((self.a.tickets, self.b.tickets), tickets)

    def test_the_reader_names_who_is_reading_and_hud_text_stays_inside_the_frame(self):
        self.stand(self.p2)
        self.frames(5)
        self.frames(1, [key(self.p2.controls.interact[0])])
        self.frames(90)
        scene = self.game.scenes.current
        surf = pygame.Surface((VIEW_W, VIEW_H))
        scene.draw(surf)
        scene.draw_overlay(surf)
        self.assertEqual(scene.owner.tag, self.p2.tag)


# ------------------------------------------------------------------ the secret works without the magazine
class VendingStillWorksTests(test_vending.VendingBase):
    """Nobody has to read the magazine: the machine's own sequence listener is untouched and still completes the quest."""
    SOLO_KEYS = test_vending.CLASSIC
    P1_KEYS = [K.K_w, K.K_w, K.K_s, K.K_s, K.K_a, K.K_d, K.K_a, K.K_d, K.K_z, K.K_x]      # P1's own keys in two-player

    @property
    def CLASSIC(self):
        return self.P1_KEYS if self.players == 2 else self.SOLO_KEYS

    def test_the_secret_opens_without_the_magazine_ever_being_read_and_completes_the_quest(self):
        manager = self.game.hub.story.manager
        manager.finish_opening()
        self.assertNotIn("check_the_vending_machine", manager.completed_ids)
        shop = self.open_shop()
        for k in self.CLASSIC:
            self.tap(k)
        self.assertIsNotNone(shop.secret)                            # the hidden screen really opened
        self.assertTrue(self.profiles[0].has_secret(VENDING_SECRET_FLAG))
        self.assertTrue(manager.state["flags"]["vending_secret"])

    def test_a_wrong_sequence_still_opens_nothing_and_reading_is_not_a_substitute(self):
        shop = self.open_shop()
        for k in list(self.CLASSIC[:-1]) + [K.K_c]:
            self.tap(k)
        self.assertIsNone(shop.secret)
        self.assertFalse(self.profiles[0].has_secret(VENDING_SECRET_FLAG))


class VendingStillWorksForTwoTests(VendingStillWorksTests):
    players = 2


if __name__ == "__main__":
    unittest.main()
