"""Progression, telegraph fairness, clothing and cinematic regression."""
import os
import unittest
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from neon_brawl.art import sprite
from neon_brawl.outfits import OUTFITS

class OutfitTests(unittest.TestCase):
    def test_each_family_has_structural_clothing_variations(self):
        for name,pool in OUTFITS.items():
            with self.subTest(name=name):
                self.assertGreaterEqual(len(pool),4)
                frames=[sprite(name,'idle',0,1,i) for i in range(len(pool))]
                self.assertEqual(len({pygame.image.tobytes(s,'RGBA') for s in frames}),len(pool))
                self.assertGreaterEqual(len({pygame.mask.from_surface(s).count() for s in frames}),3)
    def test_clothes_follow_facing_and_animation_without_changing_canvas(self):
        for name,pool in OUTFITS.items():
            for index in range(len(pool)):
                for state in ('walk','enemy','hurt','knockdown'):
                    for frame in range(4):
                        right=sprite(name,state,frame,1,index)
                        left=sprite(name,state,frame,-1,index)
                        self.assertEqual(right.get_size(),(64,64))
                        self.assertEqual(pygame.image.tobytes(left,'RGBA'),
                                         pygame.image.tobytes(pygame.transform.flip(right,True,False),'RGBA'))
    def test_bosses_have_original_silhouettes(self):
        images=[sprite(n) for n in ('WARDEN','RELAY','NULL','grunt')]
        self.assertEqual(len({pygame.mask.from_surface(s).count() for s in images}),4)

from neon_brawl.data import WAVES, STAGE_POOLS, ENEMY_DAMAGE, BOSS_DAMAGE, ATTACKS
from neon_brawl.model import Campaign, EnemyFighter, PlayerFighter, CombatSystem

class ProgressionTests(unittest.TestCase):
    def test_stage_pools_introduce_new_mechanics(self):
        pools=[set(n for wave in stage for n in wave) for stage in WAVES]
        for index,pool in enumerate(pools): self.assertLessEqual(pool,STAGE_POOLS[index])
        self.assertNotIn('ranged',pools[0]); self.assertIn('duelist',pools[1]); self.assertIn('shield',pools[1])
        self.assertTrue({'cyber','security','sniper','assassin'}<=pools[2]-pools[1])
        self.assertEqual(sum(len(w) for stage in WAVES for w in stage),70)
    def test_damage_scaling_preserves_health_and_avoids_stat_inflation(self):
        for name,scaling in (('grunt',ENEMY_DAMAGE),('NULL',BOSS_DAMAGE)):
            fighters=[EnemyFighter(name,100,220,stage=i) for i in range(3)]
            self.assertEqual(len({e.max_health for e in fighters}),1)
            self.assertEqual(tuple(e.power for e in fighters),scaling)
            self.assertLess(scaling[0],scaling[1]); self.assertLess(scaling[1],scaling[2])
    def test_every_spawn_avoids_player_and_other_bodies(self):
        for stage in range(3):
            for wave in range(4):
                for location in (45,200,350):
                    c=Campaign(); c.stage=stage; c.wave=wave; c.player.x=wave*350+location
                    c.spawn()
                    for i,e in enumerate(c.enemies):
                        self.assertGreaterEqual(((e.x-c.player.x)**2+(e.y-c.player.y)**2)**.5,90)
                        self.assertGreaterEqual(e.timer,.9)
                        for other in c.enemies[i+1:]:
                            self.assertGreaterEqual(((e.x-other.x)**2+(e.y-other.y)**2)**.5,24)
    def test_advanced_archetypes_have_different_attacks(self):
        expected={'duelist':'double','cyber':'pulse','sniper':'snipe','assassin':'lunge','elite':'double'}
        for name,attack in expected.items():
            e=EnemyFighter(name,110,220,stage=2); e.tick(2); e.think(.02,PlayerFighter(),True)
            self.assertEqual(e.swing.name,attack)
    def test_shield_has_counterplay(self):
        e=EnemyFighter('shield',110,220); e.tick(2); e.think(.02,PlayerFighter(),True)
        self.assertEqual(e.state,'guard')
        self.assertEqual(e.damage(20,0),7)
        e.invulnerable=0; e.state='guard'
        self.assertEqual(e.damage(20,0,True),20)
