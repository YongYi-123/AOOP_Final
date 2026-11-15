"""Academic art, attached cat animation, ambient isolation and staff lifecycle."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import unittest
from unittest.mock import patch
import pygame
from neon_brawl.model import Campaign,EnemyFighter
from neon_brawl.lab_cats import DESIGNS,SIZE,cat_sprite
from neon_brawl.lab_staff import LabStaff,CYCLES,engineer_sprite

class DepartmentTests(unittest.TestCase):
    def test_active_departments_and_sections_replace_the_old_settings(self):
        from neon_brawl.data import STAGES,SECTIONS
        self.assertEqual([s[0] for s in STAGES],['MACHINE LEARNING LAB','COMPUTER ARCHITECTURE LAB','AOOP DEVELOPMENT CORE'])
        self.assertEqual(tuple(map(len,SECTIONS)),(4,4,5))
        from neon_brawl.art import background
        with patch('neon_brawl.market.paint_market',side_effect=AssertionError('obsolete market renderer')):
            background.cache_clear();images=[pygame.image.tobytes(background(stage,1,section),'RGBA') for stage in range(3) for section in range(len(SECTIONS[stage]))]
        self.assertEqual(len(set(images)),13)
    def test_every_diagram_label_fits_its_actual_pixel_canvas(self):
        from font import get_font
        from neon_brawl import ml_lab,hardware_posters,oop_core,research_art
        recorded=[]
        def record(surface,label,x,y,color=(207,226,212)):
            rect=get_font().render(label,color).get_rect(topleft=(x,y))
            self.assertTrue(surface.get_rect().contains(rect),(label,rect,surface.get_size()))
            recorded.append(label);research_art.text(surface,label,x,y,color)
        for module,function,count in ((ml_lab,ml_lab.ml_screen,4),(hardware_posters,hardware_posters.schematic,6),(oop_core,oop_core.class_diagram,5)):
            function.cache_clear()
            with patch.object(module,'text',record):
                for i in range(count):function(i)
        self.assertIn('MEMORY ACCESS WRITE BACK',recorded);self.assertIn('POLYMORPHISM: UPDATE',recorded)
        self.assertGreaterEqual(len(recorded),45)
    def test_decorations_and_phase_lighting_do_not_modify_combat(self):
        from font import get_font
        from neon_brawl.art import Renderer
        r=Renderer(get_font());s=pygame.Surface((400,300));c=Campaign();c.stage=2;c.wave=3;c.camera=1050;c.player.x=1130;c.spawn()
        before=(c.player.health,c.score,c.kills,[(e.x,e.y,e.health) for e in c.enemies])
        c.enemies[0].phase=2;r.world(s,c,5);r.world(s,c,5.6);a=pygame.image.tobytes(s,'RGB')
        c.enemies[0].phase=3;r.world(s,c,5.6);b=pygame.image.tobytes(s,'RGB')
        self.assertNotEqual(a,b)
        self.assertEqual(before,(c.player.health,c.score,c.kills,[(e.x,e.y,e.health) for e in c.enemies]))

class LaboratoryCatTests(unittest.TestCase):
    def test_all_frames_have_one_connected_silhouette_and_exact_mirroring(self):
        for variant in range(5):
            for state in ('walk','sit','groom','sleep','stretch','run','observe'):
                for frame in range(8):
                    right=cat_sprite(variant,state,frame,1);left=cat_sprite(variant,state,frame,-1)
                    self.assertEqual(right.get_size(),SIZE)
                    self.assertEqual(len(pygame.mask.from_surface(right).connected_components()),1,(variant,state,frame))
                    self.assertEqual(pygame.image.tobytes(left,'RGBA'),pygame.image.tobytes(pygame.transform.flip(right,True,False),'RGBA'))
    def test_five_designs_include_structural_markings_not_only_recoloring(self):
        signatures=[]
        for i,d in enumerate(DESIGNS):
            s=cat_sprite(i,'sit',0,1)
            signatures.append(tuple(1 if tuple(s.get_at((x,y)))[:3]==d.muzzle else 2 if tuple(s.get_at((x,y)))[:3]==d.shade else 0 for y in range(SIZE[1]) for x in range(SIZE[0])))
        self.assertEqual(len(set(signatures)),5)
        self.assertEqual(len({d.personality for d in DESIGNS}),5)
    def test_visible_combat_cats_recur_in_all_departments(self):
        from neon_brawl.ambient import AmbientCats
        for stage in range(3):
            cats=AmbientCats();enemy=EnemyFighter('grunt',stage*350+150,220);enemy.attack('enemy')
            for i in range(900):
                camera=stage*350+i*.1
                cats.update(.1,i*.1,stage,0,camera+80,[enemy],camera)
                if cats.cat:
                    self.assertTrue(camera+20<=cats.cat.x<=camera+380)
                    self.assertNotIn(cats.cat,[enemy]);self.assertFalse(hasattr(cats.cat,'health'))
            self.assertEqual(cats.spawn_count,4)
    def test_department_change_respawns_without_carrying_a_faraway_cat(self):
        from neon_brawl.ambient import AmbientCats
        cats=AmbientCats();cats.update(.1,6,0,0,80,[],0)
        cats.update(.1,100,1,0,800,[],700);self.assertIsNone(cats.cat)
        cats.update(.1,104,1,0,800,[],700);self.assertTrue(720<=cats.cat.x<=1080)

class EngineerTests(unittest.TestCase):
    def test_all_work_cycles_animate_without_becoming_fighters(self):
        staff=LabStaff();seen={role:set() for role in CYCLES};c=Campaign();c.spawn()
        before=(c.player.health,c.score,[(e.x,e.y,e.health) for e in c.enemies])
        for _ in range(300):
            staff.update(.1,0,1,0,c.player,c.enemies,0)
            for p in staff.people:
                seen[p.role].add(p.state);self.assertFalse(hasattr(p,'health'));self.assertFalse(hasattr(p,'hurtbox'))
        for role,states in CYCLES.items():self.assertEqual(seen[role],set(states))
        self.assertEqual(before,(c.player.health,c.score,[(e.x,e.y,e.health) for e in c.enemies]))
        for role in CYCLES:
            self.assertNotEqual(pygame.image.tobytes(engineer_sprite(role,CYCLES[role][0],0,0),'RGBA'),pygame.image.tobytes(engineer_sprite(role,CYCLES[role][3],1,0),'RGBA'))
    def test_staff_parallax_matches_the_benches_and_pause_freezes_it(self):
        c=Campaign();c.stage=1;c.update(.05)
        self.assertEqual(len(c.staff.people),4)
        s=pygame.Surface((400,300));s.fill((0,0,0));c.staff.draw(s,0,0);a=pygame.image.tobytes(s,'RGB')
        s.fill((0,0,0));c.staff.draw(s,100,0);self.assertNotEqual(a,pygame.image.tobytes(s,'RGB'))
        before=[(p.state,p.timer) for p in c.staff.people];c.state='paused';c.update(1)
        self.assertEqual(before,[(p.state,p.timer) for p in c.staff.people])
