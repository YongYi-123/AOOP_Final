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
from puzzle_maze.studio_layout import FURNITURE,approach

def key(app,k,repeat=False):app.event(pygame.event.Event(pygame.KEYDOWN,key=k,repeat=repeat))
class StudioRefinementTests(TestCase):
    def test_furniture_is_smaller_with_real_depth_and_unchanged_safe_entry(self):
        app=PreviewGame('developer-room',True)
        self.assertFalse({'sofa','bookshelf','table'} & {f.name for f in FURNITURE})
        for item in FURNITURE:self.assertGreater(item.footprint[2],0)
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
        app.session.player.x,app.session.player.y=18,7;app.visual=[18.,7.]
        self.assertIsNone(nearby(app.session))
        for scene in (GameScene.PLAY,GameScene.SCROLL):
            app.scene=scene;app.reading='kevin_note';app.reading_page=0;app.draw(0)
            self.assertTrue(all(app.screen.get_rect().contains(rect) for rect in app.renderer.ui.rects))
        self.assertFalse(app.renderer.studio_interactive)
    def test_prototype_inspection_returns_control_to_the_clear_service_aisle(self):
        app=PreviewGame('developer-room',True);app.inspect_key('work_prototype')
        self.assertEqual(app.scene,GameScene.SCROLL);self.assertEqual(app.reading,'work_prototype')
        key(app,pygame.K_RETURN);p=app.session.player
        self.assertEqual((p.x,p.y),(1,10));app.cooldown=0
        app.update(.14,defaultdict(bool,{pygame.K_DOWN:True}));self.assertEqual((p.x,p.y),(1,11))
    def test_preview_restart_and_inspect_do_not_write_real_progress(self):
        app=PreviewGame('developer-room',True);app.inspect_key('studio_todo')
        self.assertEqual(app.reading,'studio_todo');self.assertFalse(app.persistent)
        app.restart_preview();self.assertEqual(app.scene,GameScene.PLAY)
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
        with patch('puzzle_maze.workshop_art.render',side_effect=AssertionError('wall text')):
            art=DeveloperRoomArt();base=art.floor()
        self.assertLess(sum(base.get_at((150,20))[:3]),600)
        self.assertNotEqual(base.get_at((150,20)),base.get_at((150,125)))

    def test_new_expedition_drops_old_maze_capture(self):
        app=PreviewGame('developer-room',True);app.last_maze_frame=pygame.Surface((320,240))
        app.start(onboarding=False);self.assertIsNone(app.last_maze_frame)
