import unittest
from neon_brawl.data import ROSTER, ATTACKS
from neon_brawl.model import PlayerFighter, EnemyFighter, CombatSystem, Campaign
from neon_brawl.tests.pilot import play

class CombatTests(unittest.TestCase):
    def test_roster_distinct(self):
        r,n,b=(PlayerFighter(name) for name in ROSTER)
        self.assertGreater(n.speed,r.speed); self.assertGreater(b.max_health,r.max_health)
        self.assertGreater(b.power,r.power)
    def test_movement_acceleration_and_bounds(self):
        p=PlayerFighter(); p.move(.01,(1,0),(18,382)); self.assertGreater(p.vx,0); self.assertLess(p.vx,p.speed)
        for _ in range(500): p.move(.016,(1,-1),(18,382))
        self.assertEqual(p.x,382); self.assertEqual(p.y,173)
        p.move(.05,(0,0),(18,382)); self.assertLess(p.vx,p.speed)
    def target(self): return EnemyFighter('grunt',110,220)
    def test_hitbox_active_frame_and_one_hit(self):
        p=PlayerFighter(); e=self.target(); p.attack('light')
        self.assertEqual(CombatSystem.resolve(p,[e]),[])
        p.tick(.08); self.assertEqual(len(CombatSystem.resolve(p,[e])),1)
        hp=e.health; self.assertEqual(CombatSystem.resolve(p,[e]),[]); self.assertEqual(e.health,hp)
    def test_lane_and_facing(self):
        for x,y in ((60,220),(110,250),(200,220)):
            p=PlayerFighter(); e=EnemyFighter('grunt',x,y); p.attack('light'); p.tick(.08)
            self.assertFalse(CombatSystem.resolve(p,[e]))
    def test_combo_progression_timeout(self):
        p=PlayerFighter()
        for name in ('light','combo2','combo3','light'):
            self.assertTrue(p.act('light')); self.assertEqual(p.swing.name,name); p.tick(.7)
        p.move(1,(0,0),(18,382)); p.act('light'); self.assertEqual(p.swing.name,'light')
    def test_damage_defense_knockback_and_invulnerability(self):
        p=PlayerFighter('BRUNO'); hp=p.health
        self.assertEqual(p.damage(25,100),20); self.assertEqual(p.health,hp-20)
        self.assertEqual(p.damage(25,100),0)
        x=p.x; p.tick(.1); self.assertGreater(p.x,x)
        p.tick(1); self.assertGreater(p.damage(25,100),0)
    def test_knockdown_recovery(self):
        p=PlayerFighter(); p.damage(10,100,True); self.assertEqual(p.state,'knockdown')
        self.assertFalse(p.act('heavy')); p.tick(1); self.assertTrue(p.act('heavy'))
    def test_jump_and_dodge(self):
        p=PlayerFighter(); self.assertTrue(p.act('jump')); p.tick(.25); self.assertGreater(p.jump,17)
        self.assertEqual(p.damage(25,10),0); self.assertTrue(p.act('light')); self.assertEqual(p.swing.name,'air')
        p.tick(1); self.assertTrue(p.act('dodge')); self.assertEqual(p.damage(10,10),0)
        p.tick(.31); p.move(.31,(0,0),(18,382)); self.assertFalse(p.act('dodge'))
    def test_special_energy(self):
        p=PlayerFighter(); self.assertTrue(p.act('special')); self.assertEqual(p.energy,60)
        p.tick(1); p.energy=39; self.assertFalse(p.act('special'))
    def test_enemy_telegraph_recovery_defeat(self):
        p=PlayerFighter(); e=self.target(); e.tick(2); e.think(.01,p,True)
        self.assertIsNotNone(e.swing); self.assertEqual(CombatSystem.resolve(e,[p]),[])
        e.tick(.41); self.assertTrue(CombatSystem.resolve(e,[p]))
        e.tick(.15); self.assertTrue(e.swing); e.tick(1); self.assertIsNone(e.swing)
        e.invulnerable=0; e.damage(1000,10); self.assertFalse(e.alive); self.assertEqual(e.state,'defeated')
    def test_enemy_waits_and_positions(self):
        p=PlayerFighter(); e=self.target(); e.think(.01,p,True); self.assertIsNone(e.swing)
        e.tick(2); e.think(.01,p,False); self.assertEqual(e.state,'positioning')
    def test_boss_phase(self):
        e=EnemyFighter('NULL',110,220); e.tick(3); e.health=e.max_health//2
        e.think(.01,PlayerFighter(),True); self.assertEqual(e.phase,2); self.assertEqual(e.state,'phase')
        self.assertGreater(e.invulnerable,0)
    def test_wave_and_stage_progression(self):
        c=Campaign(); c.spawn()
        for e in c.enemies: e.health=0
        c.update(.02); self.assertEqual(c.state,'checkpoint'); c.advance(); self.assertEqual(c.wave,1)
        c.wave=3; c.state='stage_clear'; c.advance(); self.assertEqual((c.stage,c.wave),(1,0))
        c.stage=2; c.wave=3; c.state='stage_clear'; c.advance(); self.assertEqual(c.state,'victory')
    def test_defeat(self):
        c=Campaign(); c.player.health=0; c.update(.02); self.assertEqual(c.state,'defeat')
    def test_hazard_telegraph_then_damage(self):
        c=Campaign(); c.stage=1; c.player.y=251; c.hazard_clock=4
        c.update(.02); self.assertEqual(c.damage_received,0)
        c.hazard_clock=4.8; c.update(.02); self.assertGreater(c.damage_received,0)
    def test_pickup(self):
        c=Campaign(); c.player.health=10; c.pickups=[(80,220)]; c.pickup()
        self.assertEqual(c.player.health,40); self.assertFalse(c.pickups)
    def test_deterministic_campaign_normal_inputs(self):
        for name in ROSTER:
            with self.subTest(character=name):
                c,frames=play(name)
                self.assertEqual(c.state,'victory',f'{name}: stage {c.stage} wave {c.wave}')
                self.assertGreaterEqual(c.kills,70); self.assertGreater(c.tickets,40)
