"""Background reactions are visual state only, never combat participants."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import unittest
import pygame
from neon_brawl.model import Campaign,EnemyFighter
from neon_brawl.civilians import StreetLife,civilian_sprite

class StreetLifeTests(unittest.TestCase):
    def scene(self,section=0):
        c=Campaign();c.player.x=section*350+180
        c.enemies=[EnemyFighter('grunt',section*350+170+i*10,225,i) for i in range(3)]
        return c,StreetLife()
    def test_normal_roles_and_capped_population(self):
        c,s=self.scene();s.update(.05,0,0,0,c.player,[],0)
        self.assertEqual(len(s.people),6)
        self.assertEqual(next(p for p in s.people if p.role=='vendor').state,'cook')
        self.assertEqual(next(p for p in s.people if p.role=='walker').state,'walk')
        for i in range(1000):s.update(.05,26+i*.05,0,0,c.player,[],0)
        self.assertEqual(len(s.people),7);self.assertEqual(sum(p.role=='police' for p in s.people),1)
    def test_spectators_photograph_panic_hide_and_police_direction(self):
        c,s=self.scene(1)
        for _ in range(20):s.update(.05,10,0,1,c.player,c.enemies,350)
        states={p.role:p.state for p in s.people}
        self.assertEqual(states['shopper'],'panic');self.assertEqual(states['spectator'],'watch')
        self.assertEqual(states['tourist'],'photo');self.assertEqual(states['vendor'],'cook')
        # Place the police near the actual disturbance, then observe its safe hand signal.
        officer=next(p for p in s.people if p.role=='police');officer.x=c.player.x
        s.update(.05,10,0,1,c.player,c.enemies,350);self.assertEqual(officer.state,'direct')
        for _ in range(50):s.update(.05,11,0,1,c.player,c.enemies,350)
        self.assertEqual(next(p for p in s.people if p.role=='shopper').state,'hide')
    def test_no_damage_targets_and_stage_reset(self):
        c,s=self.scene();before=(c.player.health,[(e.health,e.x,e.y) for e in c.enemies],c.score)
        s.update(1,26,0,0,c.player,c.enemies,0)
        for person in s.people:
            self.assertFalse(hasattr(person,'health'));self.assertFalse(hasattr(person,'hurtbox'));self.assertNotIn(person,c.enemies)
        self.assertEqual(before,(c.player.health,[(e.health,e.x,e.y) for e in c.enemies],c.score))
        s.update(.1,27,1,0,c.player,c.enemies,0);self.assertEqual(s.people,[])
    def test_native_sprites_and_camera_rendering(self):
        c,s=self.scene(1);s.update(.1,10,0,1,c.player,[],350)
        image=pygame.Surface((400,300));image.fill((0,0,0));s.draw(image,350,1)
        self.assertNotEqual(pygame.image.tobytes(image.subsurface((0,130,200,50)),'RGB'),bytes(200*50*3))
        image.fill((0,0,0));s.draw(image,0,1)
        self.assertEqual(pygame.image.tobytes(image.subsurface((0,130,200,50)),'RGB'),bytes(200*50*3))
        for role in ('vendor','shopper','tourist','spectator','customer','walker','police'):
            for state in ('walk','watch','photo','panic','peek','direct'):
                sprite=civilian_sprite(role,state,1,1,1)
                self.assertEqual(sprite.get_size(),(18,31));self.assertGreater(pygame.mask.from_surface(sprite).count(),80)
    def test_pause_freezes_environment(self):
        c=Campaign();c.update(.05);before=[(p.x,p.timer,p.state) for p in c.street_life.people]
        c.state='paused';c.update(1)
        self.assertEqual(before,[(p.x,p.timer,p.state) for p in c.street_life.people])
