"""Production interaction, seating and atmospheric entry regressions."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from collections import defaultdict
from unittest import TestCase
from unittest.mock import patch
import pygame
from puzzle_maze.dev_preview import PreviewGame
from puzzle_maze.game import GameScene
from puzzle_maze.studio_interactions import nearby
from puzzle_maze.studio_layout import FURNITURE,SOURCE_FURNITURE,approach

def key(app,k,repeat=False):app.event(pygame.event.Event(pygame.KEYDOWN,key=k,repeat=repeat))
class StudioRefinementTests(TestCase):
    def test_furniture_is_smaller_with_real_depth_and_unchanged_safe_entry(self):
        app=PreviewGame('developer-room',True)
        for old,new in zip(SOURCE_FURNITURE,FURNITURE):
            if old.name not in ('plant','lamp'):self.assertLess(new.bounds[2]*new.bounds[3],old.bounds[2]*old.bounds[3])
            self.assertGreater(new.footprint[2],0)
        self.assertTrue(app.session.can_enter(1,7));self.assertTrue(app.session.can_enter(3,8))
    def test_every_note_prompt_selects_exactly_the_same_object_as_e(self):
        app=PreviewGame('developer-room',True)
        for obj in app.session.puzzles.objects.values():
            app.scene=GameScene.PLAY
            pos,facing=approach(app.session.rooms.data,obj.pos)
            app.session.player.x,app.session.player.y=pos;app.session.player.facing=facing
            app.visual=list(map(float,pos))
            selected=nearby(app.session);self.assertIsNotNone(selected);self.assertEqual(selected[0],obj.id)
            key(app,pygame.K_e);self.assertEqual(app.scene,GameScene.SCROLL)
            self.assertEqual(app.reading,obj.data['content_id'])
    def test_prompt_disappears_at_distance_and_does_not_cover_dialogue(self):
        app=PreviewGame('developer-room',True)
        app.session.player.x,app.session.player.y=10,8;app.visual=[10.,8.]
        self.assertIsNone(nearby(app.session))
        for scene in (GameScene.PLAY,GameScene.SCROLL):
            app.scene=scene;app.reading='kevin_note';app.reading_page=0;app.draw(0)
            self.assertTrue(all(app.screen.get_rect().contains(rect) for rect in app.renderer.ui.rects))
        self.assertFalse(app.renderer.studio_interactive)
    def test_sofa_sit_animation_blocks_walk_and_returns_to_safe_approach(self):
        app=PreviewGame('developer-room',True);p=app.session.player
        p.x,p.y=4,11;p.facing=(0,-1);app.visual=[4.,11.]
        self.assertEqual(nearby(app.session),('sofa','Sit'))
        key(app,pygame.K_e);seat=app.studio_seat
        self.assertEqual(seat.position,(72.,192.))
        app.update(.2,defaultdict(bool,{pygame.K_RIGHT:True}));mid=seat.position
        self.assertGreater(mid[1],179);self.assertLess(mid[1],192)
        app.update(.2);self.assertEqual(seat.position,(64.,179.));self.assertEqual((p.x,p.y),(4,11))
        app.draw(0);key(app,pygame.K_e,True);self.assertFalse(seat.leaving)
        key(app,pygame.K_e);self.assertTrue(seat.leaving);app.update(.4)
        self.assertIsNone(app.studio_seat);self.assertTrue(app.session.can_enter(p.x,p.y))
        app.cooldown=0;app.update(.14,defaultdict(bool,{pygame.K_RIGHT:True}));self.assertEqual((p.x,p.y),(5,11))
    def test_preview_restart_and_inspect_clear_seated_pose_without_progress_writes(self):
        app=PreviewGame('developer-room',True);p=app.session.player;p.x,p.y=4,11;p.facing=(0,-1);app.visual=[4.,11.]
        key(app,pygame.K_e);app.update(.4);app.inspect_key('studio_todo')
        self.assertIsNone(app.studio_seat);self.assertEqual(app.reading,'studio_todo');self.assertFalse(app.persistent)
        app.restart_preview();self.assertIsNone(app.studio_seat)
    def test_cinematic_uses_a_copy_of_real_maze_frame_and_remains_skippable(self):
        from puzzle_maze.lab_scene import LabEntrance
        frame=pygame.Surface((320,240));frame.fill((50,60,70));scene=LabEntrance(frame)
        frame.fill((0,0,0));self.assertEqual(tuple(scene.maze_frame.get_at((0,0)))[:3],(50,60,70))
        app=PreviewGame('miao-entrance',True);app.last_maze_frame=scene.maze_frame
        app.update(.01);self.assertEqual(app.scene,GameScene.MEMORY)
        self.assertIsNotNone(app.lab_entrance.maze_frame)
        key(app,pygame.K_SPACE);self.assertEqual(app.scene,GameScene.PLAY);self.assertTrue(app.session.lab_memory_seen)
    def test_wall_has_no_room_name_text_and_dim_base_preserves_wood_contrast(self):
        from puzzle_maze.developer_art import DeveloperRoomArt
        with patch('puzzle_maze.developer_art.render',side_effect=AssertionError('wall text')):
            art=DeveloperRoomArt();base=art.floor()
        self.assertLess(sum(base.get_at((150,20))[:3]),600)
        self.assertNotEqual(base.get_at((150,20)),base.get_at((150,125)))

    def test_new_expedition_drops_transient_pose_and_old_maze_capture(self):
        app=PreviewGame('developer-room',True);app.session.player.x,app.session.player.y=4,11
        app.session.player.facing=(0,-1);app.visual=[4.,11.];key(app,pygame.K_e)
        self.assertIsNotNone(app.studio_seat);app.last_maze_frame=pygame.Surface((320,240))
        app.start(onboarding=False)
        self.assertIsNone(app.studio_seat);self.assertIsNone(app.last_maze_frame)
