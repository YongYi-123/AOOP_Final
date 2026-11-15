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
    def test_scaled_attacks_deliver_actual_progressive_damage(self):
        for name,attack in (('grunt','enemy'),('WARDEN','charge')):
            damages=[]
            for stage in range(3):
                p=PlayerFighter(); e=EnemyFighter(name,110,220,stage=stage)
                e.tick(2); e.facing=-1; e.begin(attack,p)
                e.tick(ATTACKS[attack].windup+.01)
                hits=CombatSystem.resolve(e,[p])
                self.assertEqual(len(hits),1)
                damages.append(hits[0][1])
                self.assertEqual(p.damage(100,0),0)
            self.assertLess(damages[0],damages[1]); self.assertLess(damages[1],damages[2])
    def test_boss_peak_damage_leaves_a_recovery_margin_for_every_character(self):
        from neon_brawl.data import ROSTER
        attacks={n for phases in BOSS_PATTERNS.values() for phase in phases for n in phase if n in ATTACKS}
        for character in ROSTER:
            p=PlayerFighter(character)
            worst=max(round(ATTACKS[n].damage*BOSS_DAMAGE[2]/p.defense) for n in attacks)
            self.assertLess(worst,p.max_health*.35)

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

from neon_brawl.data import BOSS_PATTERNS

class BossEvolutionTests(unittest.TestCase):
    def test_each_boss_has_distinct_mechanics_and_telegraphs(self):
        for name,phase_patterns in BOSS_PATTERNS.items():
            e=EnemyFighter(name,120,220)
            p=PlayerFighter()
            observed=set()
            for phase,patterns in enumerate(phase_patterns,1):
                e.phase=phase; e.pattern=0
                for _ in patterns:
                    e.x,e.y=120,220; e.timer=0; e.swing=None
                    e.think(.02,p,True)
                    action=e.swing.name if e.swing else e.state
                    observed.add(action)
                    if e.swing:
                        self.assertGreaterEqual(ATTACKS[action].windup,.6)
                        self.assertFalse(CombatSystem.resolve(e,[p]))
                    e.tick(3)
            for attack in phase_patterns[0]: self.assertIn(attack,observed)
            self.assertGreaterEqual(len(observed),4)
    def test_overlord_three_phases_expose_the_core(self):
        e=EnemyFighter('NULL',120,220); p=PlayerFighter()
        for health,phase in ((.49,2),(.19,3)):
            e.tick(3); e.health=int(e.max_health*health); e.think(.02,p,True)
            self.assertEqual(e.phase,phase); self.assertEqual(e.state,'phase')
            self.assertGreaterEqual(e.invulnerable,1)
        self.assertLess(e.defense,1)
    def test_targeted_strike_locks_its_warning_and_has_single_damage(self):
        e=EnemyFighter('NULL',120,220,stage=2); p=PlayerFighter()
        e.tick(3); e.begin('strike',p); target=e.swing.target
        e.tick(1.11); p.y=175
        self.assertFalse(CombatSystem.resolve(e,[p])); self.assertEqual(e.swing.target,target)
        p.y=220; self.assertEqual(len(CombatSystem.resolve(e,[p])),1)
        self.assertFalse(CombatSystem.resolve(e,[p]))
    def test_dash_motion_integrates_only_the_active_interval(self):
        first=EnemyFighter('WARDEN',200,220); second=EnemyFighter('WARDEN',200,220)
        for e in (first,second): e.tick(2); e.facing=-1; e.attack('charge')
        first.tick(.95)
        for _ in range(95): second.tick(.01)
        self.assertAlmostEqual(first.x,second.x,places=6)
        self.assertAlmostEqual(first.x,181,places=6)
        first.tick(2)
        self.assertAlmostEqual(first.x,200-190*.24,places=6)

    def test_teleport_is_marked_bounded_and_never_hits_on_arrival(self):
        e=EnemyFighter('NULL',120,220); p=PlayerFighter(); e.tick(3)
        e.arena_bounds=(18,382); e.pattern=3
        e.think(.02,p,True); hp=p.health
        self.assertEqual(e.state,'teleport'); self.assertIsNotNone(e.destination)
        self.assertTrue(33<=e.destination[0]<=367)
        e.tick(.81); self.assertEqual(p.health,hp); self.assertIsNone(e.swing)
        self.assertEqual(e.state,'recovery'); self.assertFalse(e.ready)
    def test_reinforcements_are_capped_and_do_not_spawn_on_player(self):
        c=Campaign(); c.stage=2; c.wave=3; c.player.x=1120; c.spawn()
        boss=c.enemies[0]
        for _ in range(8): boss.summon_request=True; c.update(.02)
        self.assertEqual(boss.support_count,2); self.assertEqual(len(c.enemies),3)
        for e in c.enemies[1:]: self.assertGreater(abs(e.x-c.player.x),80)
    def test_boss_chamber_has_no_leftover_live_rail(self):
        c=Campaign(); c.stage=2; c.wave=3; c.player.x=1120; c.player.y=251; c.hazard_clock=4.8
        c.update(.02); self.assertEqual(c.damage_received,0)
    def test_defeat_cannot_complete_before_the_boss_animation(self):
        c=Campaign(); c.wave=3; c.player.x=1120; c.spawn(); c.enemies[0].health=0
        for _ in range(20): c.update(.05)
        self.assertEqual(c.state,'playing')
        for _ in range(10): c.update(.05)
        self.assertEqual(c.state,'stage_clear')

class SceneryTests(unittest.TestCase):
    def test_all_twelve_sections_have_different_compositions(self):
        from neon_brawl.art import background
        images=[pygame.image.tobytes(background(stage,1,section),'RGBA')
                for stage in range(3) for section in range(4)]
        self.assertEqual(len(set(images)),12)
        self.assertEqual(background.cache_info().maxsize,24)

class CinematicTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        from font import get_font
        from neon_brawl.game import BrawlGame
        self.game=BrawlGame(get_font())
    def test_all_intro_beats_keep_text_and_characters_in_separate_zones(self):
        surface=pygame.Surface((400,300)); bounds=surface.get_rect()
        for step in range(110):
            self.game.screen_time=step/10; self.game.draw(surface)
            items=self.game.cinematic.last_layout
            for kind,label,rect in items:
                self.assertTrue(bounds.contains(rect),(step,label,rect))
                for other_kind,other_label,other in items:
                    if kind=='text' and (other_kind=='actor' or other_label!=label):
                        self.assertFalse(rect.colliderect(other),(step,label,other_label))
    def test_real_display_sizes_scale_without_clipping_or_errors(self):
        for size in ((320,240),(800,600),(1280,720),(1200,900)):
            for time in (.4,3.5,5.5,6.8,8.5,10.5):
                self.game.screen_time=time; self.game.draw(pygame.Surface(size))
    def test_skip_requires_a_fresh_press_before_next_screen(self):
        event=pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN)
        self.game.handle_event(event); self.assertEqual(self.game.screen,'title')
        self.game.handle_event(event); self.assertEqual(self.game.screen,'title')
        self.game.handle_event(pygame.event.Event(pygame.KEYUP,key=pygame.K_RETURN))
        self.game.handle_event(event); self.assertEqual(self.game.screen,'select')
    def test_skip_keys_and_timeout_do_not_start_a_paid_campaign(self):
        for key in (pygame.K_RETURN,pygame.K_SPACE,pygame.K_ESCAPE):
            self.game.change('intro'); self.game._pressed.clear()
            self.game.handle_event(pygame.event.Event(pygame.KEYDOWN,key=key))
            self.assertEqual(self.game.screen,'title'); self.assertIsNone(self.game.campaign)
        self.game.change('intro')
        for _ in range(670): self.game.update(1/60)
        self.assertEqual(self.game.screen,'title'); self.assertFalse(self.game.started)
