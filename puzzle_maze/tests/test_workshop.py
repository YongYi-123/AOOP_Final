"""The production workshop replaces the lounge and uses real Arcade cabinet art."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from collections import deque
from unittest import TestCase
from unittest.mock import patch
import pygame
from puzzle_maze.dev_preview import PreviewGame
from puzzle_maze.game import GameScene
from puzzle_maze.studio_layout import FURNITURE,ENTRY,approach
from puzzle_maze.studio_interactions import PROMPT,nearby
class WorkshopTests(TestCase):
    def test_four_different_arcade_cabinets_replace_domestic_furniture(self):
        g=PreviewGame('developer-room',True);names={f.name for f in FURNITURE}
        self.assertFalse(names&{'sofa','bookshelf','table','plant'})
        cabinets=[f for f in FURNITURE if f.name.startswith('cab_') or f.name=='prototype']
        self.assertEqual(len(cabinets),4)
        frames={pygame.image.tobytes(g.renderer.developer_art.sprite(f),'RGBA') for f in cabinets}
        self.assertEqual(len(frames),4)
    def test_all_inspections_remain_connected_and_both_keys_work(self):
        g=PreviewGame('developer-room',True);s=g.session
        todo=deque([ENTRY]);seen={ENTRY}
        while todo:
            x,y=todo.popleft()
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                p=x+dx,y+dy
                if p not in seen and s.can_enter(*p):seen.add(p);todo.append(p)
        self.assertIn((1,7),seen)
        for obj in s.puzzles.objects.values():
            pos,facing=approach(s.rooms.data,obj.pos);self.assertIn(pos,seen,obj.id)
            for key in (pygame.K_e,pygame.K_RETURN):
                g.scene=GameScene.PLAY;s.player.x,s.player.y=pos;s.player.facing=facing;g.visual=list(map(float,pos))
                self.assertEqual(nearby(s)[0],obj.id)
                g.event(pygame.event.Event(pygame.KEYDOWN,key=key));self.assertEqual(g.scene,GameScene.SCROLL)
                self.assertEqual(g.reading,obj.data['content_id'])
                g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN));self.assertEqual(g.scene,GameScene.PLAY)
    def test_exact_prompt_no_names_before_e_and_no_repeated_enter(self):
        g=PreviewGame('developer-room',True);g.inspect_key('work_crt')
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
        with patch.object(g.renderer,'text',wraps=g.renderer.text) as text:
            g.draw(0);self.assertEqual([c.args[0] for c in text.call_args_list],[PROMPT])
        self.assertEqual(PROMPT,'[E/ENTER] INSPECT')
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN,repeat=True));self.assertEqual(g.scene,GameScene.PLAY)
    def test_opaque_solids_and_cat_do_not_allow_overlap(self):
        g=PreviewGame('developer-room',True);s=g.session
        for item in FURNITURE:
            image=g.renderer.developer_art.sprite(item)
            self.assertIs(image,g.renderer.developer_art.sprite(item,True))
            self.assertLessEqual({image.get_at((x,y)).a for x in range(image.get_width()) for y in range(image.get_height())},{0,255})
            x,y,w,h=item.footprint
            self.assertTrue(any(not s.can_enter(tx,ty) for tx in range(1,19) for ty in range(3,12) if x<=tx*16+8<x+w and y<=ty*16+15<y+h),item.name)
        s.player.x,s.player.y=10,8;self.assertFalse(s.move(0,-1))
    def test_prototype_has_distinct_optional_story_and_no_economy_binding(self):
        g=PreviewGame('developer-room',True);g.inspect_key('work_prototype')
        self.assertIn('work_prototype',g.session.lore);self.assertFalse(g.persistent)
        self.assertTrue(g.session.grey_pixel)
