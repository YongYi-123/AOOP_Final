"""Native pixel effects remain bounded, deterministic and outside the HUD."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import unittest
from unittest.mock import patch
import pygame
from puzzle_maze.game import Game,GameScene
from puzzle_maze.combat import EnemyState

class Presentation43Tests(unittest.TestCase):
    def tearDown(self):pygame.quit()
    def test_all_rooms_lighting_and_enemy_lifecycles_render_without_changing_rules(self):
        g=Game(headless=True);g.scene=GameScene.PLAY
        for name in g.session.rooms.rooms:
            g.session.enter(name);s=g.session;before=list(s.rooms.data['tiles']);visual=[s.player.x,s.player.y]
            for state in (EnemyState.HUNT,EnemyState.WINDUP,EnemyState.DYING):
                for e in s.combat.enemies:e.state=state;e.attack_timer=.2
                s.effects=[('chest',(10,8),.3),('shards',(12,8),.4)]
                s.bombs.blasts=[({(12,8),(13,8)},.3)]
                with patch('pygame.transform.smoothscale',side_effect=AssertionError('pixel art must stay sharp')):
                    g.renderer.world(s,visual,.016)
                self.assertEqual(before,s.rooms.data['tiles'])
                self.assertEqual(g.renderer.surface.get_clip(),g.renderer.surface.get_rect())
        self.assertLessEqual(len(g.renderer.particles),138)
    def test_effects_do_not_paint_over_hud_and_enemy_steps_interpolate(self):
        g=Game(headless=True);s=g.session;s.enter('r3');r=g.renderer
        r.world(s,[s.player.x,s.player.y],0)
        before=pygame.image.tobytes(r.surface.subsurface((0,184,320,56)),'RGB')
        s.effects=[('chest',(10,8),.3)];s.bombs.blasts=[({(10,8)},.3)]
        r.world(s,[s.player.x,s.player.y],0)
        self.assertEqual(before,pygame.image.tobytes(r.surface.subsurface((0,184,320,56)),'RGB'))
        e=s.combat.enemies[0];old=e.x*16;r.enemy_portraits.position(s.combat,e,0);e.x+=1
        x,_=r.enemy_portraits.position(s.combat,e,1/60)
        self.assertGreater(x,old);self.assertLess(x,e.x*16)
