"""Rendering regressions exercise simulation clocks and real combat windows."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import unittest
import pygame
from neon_brawl.animation import animation_sample
from neon_brawl.art import Renderer, sprite
from neon_brawl.data import ATTACKS, ROSTER, ENEMIES, CHECKPOINT_HEAL, BOSS_ENTRY_HEAL
from neon_brawl.characters import arm_joints, ARM_UPPER, ARM_FORE
import math
from neon_brawl.effects import attack_effects, fighter_effects, draw_impact
from neon_brawl.model import Campaign, PlayerFighter, EnemyFighter, CombatSystem


class AnimationTimingTests(unittest.TestCase):
    def test_attacks_rotate_rigid_arm_bones_instead_of_stretching(self):
        for state in (*ATTACKS,'idle','hurt','guard','summon','victory'):
            for frame in range(8):
                shoulder, elbow, hand=arm_joints((20,18),state,frame)
                self.assertAlmostEqual(math.dist(shoulder,elbow),ARM_UPPER)
                self.assertAlmostEqual(math.dist(elbow,hand),ARM_FORE)
                self.assertLessEqual(math.dist(shoulder,hand),ARM_UPPER+ARM_FORE+.00001)

    def test_poses_match_damage_window_for_every_attack_and_recovery_multiplier(self):
        for name, attack in ATTACKS.items():
            for character in ('NOVA', 'BRUNO', 'grunt'):
                fighter = PlayerFighter(character) if character in ROSTER else EnemyFighter(character, 80, 220)
                fighter.timer = 0
                fighter.attack_recovery = .85
                self.assertTrue(fighter.attack(name))
                recovery = ROSTER[character].recovery if character in ROSTER else .85
                for age, expected in ((0, range(2)), (attack.windup-.0001, range(2)),
                                      (attack.windup, range(2,5)),
                                      (attack.windup+attack.active, range(2,5)),
                                      (attack.windup+attack.active+.0001, range(5,8)),
                                      (attack.windup+attack.active+attack.recovery*recovery-.0001, range(5,8))):
                    with self.subTest(attack=name, character=character, age=age):
                        fighter.swing.age = age
                        state, frame = animation_sample(fighter)
                        self.assertEqual(state, name)
                        self.assertIn(frame, expected)

    def test_impact_pose_does_not_grant_early_or_duplicate_damage(self):
        for name in ('light', 'heavy', 'special'):
            fighter = PlayerFighter('NOVA'); target = EnemyFighter('bruiser', 110, 220)
            fighter.attack(name)
            fighter.tick(ATTACKS[name].windup-.001)
            self.assertLess(animation_sample(fighter)[1], 2)
            self.assertFalse(CombatSystem.resolve(fighter,[target]))
            fighter.tick(.002)
            self.assertIn(animation_sample(fighter)[1],range(2,5))
            self.assertEqual(len(CombatSystem.resolve(fighter,[target])),1)
            self.assertFalse(CombatSystem.resolve(fighter,[target]))

    def test_hitstop_freezes_body_poses_but_particles_expire(self):
        c=Campaign('NOVA');c.spawn();c.player.attack('heavy')
        before=animation_sample(c.player);age=c.player.age
        c.impact(c.enemies[0],'heavy')
        c.update(.02)
        self.assertEqual(c.player.age,age)
        self.assertEqual(animation_sample(c.player),before)
        self.assertGreater(c.effects[0].age,0)
        for _ in range(20):c.update(.02)
        self.assertFalse(c.effects)

    def test_reactions_progress_from_squeeze_to_tumble_and_recover(self):
        fighter=PlayerFighter('NOVA');fighter.damage(5,100,True)
        self.assertEqual(animation_sample(fighter),('knockdown',0))
        fighter.tick(.2)
        self.assertEqual(animation_sample(fighter),('knockdown',3))
        fighter.tick(.7)
        self.assertEqual(animation_sample(fighter)[0],'idle')
        fighter.invulnerable=0;fighter.damage(1000,100)
        fighter.tick(.8)
        self.assertEqual(animation_sample(fighter),('defeated',7))


class CharacterRenderingTests(unittest.TestCase):
    def test_distinct_archetypes_have_different_contours(self):
        names=('NOVA','grunt','runner','bruiser','ranged','WARDEN','RELAY','NULL')
        masks=[pygame.mask.from_surface(sprite(name)) for name in names]
        for i,mask in enumerate(masks):
            for other in masks[i+1:]:
                self.assertGreater(mask.count()+other.count()-2*mask.overlap_area(other,(0,0)),15)

    def test_all_fighters_and_actions_are_mirrored_crisp_and_contained(self):
        for name in (*ROSTER,*ENEMIES):
            for state in ('idle','walk','light','heavy','special','airborne','dodge','hurt','knockdown','defeated','guard','phase'):
                for frame in range(8):
                    with self.subTest(name=name,state=state,frame=frame):
                        right=sprite(name,state,frame);left=sprite(name,state,frame,-1)
                        self.assertEqual(right.get_size(),(64,64))
                        self.assertEqual(pygame.image.tobytes(left,'RGBA'),pygame.image.tobytes(pygame.transform.flip(right,True,False),'RGBA'))
                        bounds=right.get_bounding_rect()
                        self.assertTrue(pygame.Rect(1,1,62,60).contains(bounds),bounds)
                        self.assertEqual(right.get_alpha(),255)
                        self.assertEqual(right.get_at((0,0)).a,0)
                        self.assertGreater(pygame.mask.from_surface(right).count(),400)

    def test_blink_hurt_and_boss_special_poses_are_visibly_different(self):
        for name in ('NOVA','grunt','runner','bruiser','WARDEN','RELAY','NULL'):
            images=[pygame.image.tobytes(sprite(name,state,frame),'RGBA')
                    for state,frame in (('idle',0),('idle',7),('hurt',0),('guard',0),('phase',0))]
            self.assertEqual(len(set(images)),len(images))


class FeedbackRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        from font import get_font
        cls.renderer=Renderer(get_font())

    def test_feedback_strength_is_visual_only_and_has_finite_lifetime(self):
        c=Campaign('NOVA');target=EnemyFighter('grunt',120,220)
        for kind,strong in (('light',False),('heavy',True),('special',True)):
            c.shake_time=0;c.impact(target,kind,-1)
            self.assertEqual(c.hitstop,.045)
            self.assertEqual(c.shake_time>0,strong)
            self.assertEqual(c.effects[-1].kind,kind)
            self.assertEqual(c.effects[-1].direction,-1)
            self.assertEqual(target.health,target.max_health)

    def test_special_warnings_and_particles_preserve_transparent_background_and_clip(self):
        c=Campaign('NOVA');c.player.x=200;c.player.attack('special')
        c.player.tick(.15);c.impact(c.player,'special')
        surface=pygame.Surface((400,300),pygame.SRCALPHA)
        clip=pygame.Rect(4,80,392,200);surface.set_clip(clip)
        fighter_effects(surface,c.player,0)
        draw_impact(surface,c.effects[-1],0)
        enemy=EnemyFighter('NULL',220,220);enemy.timer=0;enemy.begin('strike',c.player)
        attack_effects(surface,enemy,0,0)
        self.assertEqual(surface.get_clip(),clip)
        self.assertEqual(surface.get_at((200,20)).a,0)
        self.assertEqual(surface.get_at((0,200)).a,0)
        self.assertLess(pygame.mask.from_surface(surface).count(),3000)

    def test_screen_shake_preserves_hud_and_rendering_does_not_mutate_sprites(self):
        c=Campaign('NOVA');c.spawn();c.player.attack('heavy');c.player.tick(.3)
        c.player.flash=.1;c.combo=12;c.combo_time=2
        state,frame=animation_sample(c.player)
        cached=sprite('NOVA',state,frame);before=pygame.image.tobytes(cached,'RGBA')
        first=pygame.Surface((400,300));second=first.copy()
        self.renderer.world(first,c,4)
        c.impact(c.enemies[0],'special')
        self.renderer.world(second,c,4)
        self.assertEqual(pygame.image.tobytes(first.subsurface((0,0,400,38)),'RGB'),
                         pygame.image.tobytes(second.subsurface((0,0,400,38)),'RGB'))
        self.assertEqual(before,pygame.image.tobytes(cached,'RGBA'))


class BossEntryHealingTests(unittest.TestCase):
    def test_all_three_boss_entries_give_extra_health_once_and_cap_at_maximum(self):
        for character in ROSTER:
            for stage in range(3):
                for health in (10,ROSTER[character].health-5):
                    c=Campaign(character);c.stage=stage;c.wave=2;c.state='checkpoint'
                    c.player.health=health;c.advance()
                    expected=min(c.player.max_health,health+BOSS_ENTRY_HEAL)
                    self.assertEqual(c.player.health,expected)
                    self.assertEqual((c.stage,c.wave),(stage,3))
                    c.advance();self.assertEqual(c.player.health,expected)

    def test_ordinary_checkpoints_keep_existing_healing(self):
        for wave in (0,1):
            c=Campaign('NOVA');c.wave=wave;c.state='checkpoint';c.player.health=10
            c.advance();self.assertEqual(c.player.health,10+CHECKPOINT_HEAL)


if __name__=='__main__':unittest.main()
