"""Golden Age style: opaque props, small object prompts and physical companions."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from puzzle_maze.tests.studio_flow import open_paper,close_inspection
import pygame
from puzzle_maze.dev_preview import PreviewGame
from puzzle_maze.game import GameScene
from puzzle_maze.studio_layout import FURNITURE,approach
from puzzle_maze.studio_interactions import nearby,WALL_NOTES,object_anchor

class StudioConsistencyTests(TestCase):
    def test_only_single_small_e_is_shown_before_inspection_and_footer_is_floor(self):
        g=PreviewGame('developer-room',True);g.inspect_key('note')
        close_inspection(g)
        with patch.object(g.renderer,'text',wraps=g.renderer.text) as text:
            g.draw(.2);self.assertEqual(text.call_count,0)
        self.assertEqual(g.renderer.studio_prompt.label,'INSPECT')
        self.assertTrue(pygame.Rect(0,0,320,240).contains(g.renderer.studio_prompt_rect))
        footer=pygame.Rect(120,208,40,32)
        self.assertEqual(pygame.image.tobytes(g.renderer.surface.subsurface(footer),'RGB'),pygame.image.tobytes(g.renderer.developer_art.floor().subsurface(footer),'RGB'))
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e));self.assertEqual(g.scene,GameScene.SCROLL)
        self.assertIsNotNone(g.inspection_intro)
        open_paper(g)
        with patch.object(g.renderer,'text',wraps=g.renderer.text) as text:
            g.draw(0);self.assertNotIn('[E/ENTER] INSPECT',[c.args[0] for c in text.call_args_list]);self.assertGreater(len(text.call_args_list),1)
        close_inspection(g);self.assertEqual(g.scene,GameScene.PLAY)
    def test_prompt_disappears_out_of_range_and_closest_wins_over_facing(self):
        g=PreviewGame('developer-room',True);p=g.session.player
        p.x,p.y=11,10;g.visual=[11.,10.]
        with patch.object(g.renderer,'text',wraps=g.renderer.text) as text:g.draw(0);self.assertEqual(text.call_count,0)
        p.x,p.y=15,4;p.facing=(-1,0)
        self.assertEqual(nearby(g.session)[0],'lab_duck') # same tile beats a more distant facing card
    def test_miao_allows_open_floor_and_has_reachable_conversation_and_exit(self):
        g=PreviewGame('developer-room',True);s=g.session;s.player.x,s.player.y=10,8
        self.assertTrue(s.can_enter(10,7));self.assertTrue(s.move(0,-1));self.assertEqual((s.player.x,s.player.y),(10,7))
        self.assertTrue(s.move(1,0));self.assertTrue(s.can_enter(1,7))
        pos,facing=approach(s.rooms.data,s.puzzles.objects['miao'].pos)
        self.assertTrue(s.can_enter(*pos));s.player.x,s.player.y=pos;s.player.facing=facing
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e));self.assertEqual(g.reading,'miao_memory')
    def test_both_lamps_and_desk_block_physical_overlap(self):
        g=PreviewGame('developer-room',True);s=g.session
        self.assertFalse(s.can_enter(5,10)) # standing lamp's base
        self.assertFalse(s.can_enter(17,5)) # desk lamp / solid tabletop
        for start,direction in (((5,9),(0,1)),((17,4),(0,1))):
            s.player.x,s.player.y=start;self.assertFalse(s.move(*direction));self.assertEqual((s.player.x,s.player.y),start)
    def test_all_prop_pixels_remain_opaque_when_ghost_requested(self):
        g=PreviewGame('developer-room',True);art=g.renderer.developer_art
        for item in FURNITURE:
            sprite=art.sprite(item);self.assertIs(sprite,art.sprite(item,True))
            self.assertIn(sprite.get_alpha(),(None,255))
            self.assertLessEqual({sprite.get_at((x,y)).a for x in range(sprite.get_width()) for y in range(sprite.get_height())},{0,255})
    def test_wall_notes_are_on_wall_with_anchors_above_furniture(self):
        g=PreviewGame('developer-room',True)
        for key,(x,y) in WALL_NOTES.items():
            self.assertLess(y+13,105 if key in ('dev_001','dev_002','dev_003') else 45)
            self.assertEqual(object_anchor(g.session,key),(x+5,y))
    def test_original_lobby_cat_has_multiple_idle_frames(self):
        from puzzle_maze.miao_adapter import guide_frame
        frames={pygame.image.tobytes(guide_frame(False,t),'RGBA') for t in (0.,.6,1.1,4.05,7.1,8.6)}
        self.assertGreaterEqual(len(frames),4)
    def test_revision_two_save_on_new_collision_migrates_and_preserves_backup(self):
        g=PreviewGame('developer-room',True);s=g.session
        with TemporaryDirectory() as directory:
            path=Path(directory)/'save.json';s.save(path);data=json.loads(path.read_text())
            data['extension']['remaster']['studio_revision']=2
            data['player']=[9,6];data['checkpoint']['pos']=[11,4]
            path.write_text(json.dumps(data));before=path.read_bytes()
            restored=type(s).load(path)
            self.assertTrue(restored.can_enter(restored.player.x,restored.player.y));self.assertEqual(restored.lore,s.lore)
            restored.save(path);self.assertEqual(path.with_name(path.name+'.pre-studio-v3').read_bytes(),before)
