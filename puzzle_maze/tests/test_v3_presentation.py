import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pygame
from puzzle_maze.game import Game,GameScene
from puzzle_maze.exploration import DungeonAtlas
from puzzle_maze.icons import IconAtlas,ICONS
from puzzle_maze import pixel_font
from puzzle_maze.dungeon import DungeonSession
from puzzle_maze.solver import solve_boxes
from puzzle_maze.validator import DungeonValidator

class DungeonPresentationTests(unittest.TestCase):
    def tearDown(self):pygame.quit()
    def test_font_has_only_solid_pixels_and_integer_blocks(self):
        pygame.font.init();surface=pixel_font.render('Basic Sword / 0123',33,(240,210,100))
        self.assertEqual(surface.get_height(),28)
        colors={surface.get_at((x,y))[:] for x in range(surface.get_width()) for y in range(surface.get_height())}
        self.assertEqual(colors,{(0,0,0,0),(240,210,100,255)})
        self.assertTrue(all(c.upper() in pixel_font.ROWS for c in 'Basic Sword / KEY +1 SHIFT E B'))
    def test_original_icons_are_distinct_and_disabled(self):
        icons=IconAtlas()
        self.assertEqual(len({pygame.image.tobytes(icons.get(k),'RGBA') for k in ICONS}),len(ICONS))
        for kind in ICONS:self.assertNotEqual(pygame.image.tobytes(icons.get(kind),'RGBA'),pygame.image.tobytes(icons.get(kind,False),'RGBA'))
    def test_hud_pickup_and_repeat_bomb_input(self):
        game=Game(headless=True);game.start(onboarding=False);game.session.inventory.supply_bombs(5);game.session.tick(0)
        self.assertEqual(game.session.pickup[0],'bomb')
        game.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_b,repeat=False));game.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_b,repeat=True))
        self.assertEqual(game.session.inventory.bombs,4);self.assertEqual(len(game.session.bombs.bombs),1)
        game.draw(.016);self.assertTrue(any('BOMB +5' in c[0] for c in game.renderer.ui.commands))
        game.session.tick(1.3);self.assertIsNone(game.session.pickup)
    def test_floor_map_compass_and_hidden_visibility(self):
        game=Game(headless=True);s=game.session;atlas=DungeonAtlas(s.rooms)
        self.assertNotIn('r8',atlas.visible_rooms(s.visited));s.enter('r8');self.assertIn('r8',atlas.visible_rooms(s.visited))
        s.enter('r1');s.exploration.tiles['r1']={(5,4)}
        self.assertNotIn(('chest',(5,4)),atlas.discovered_markers(s));s.inventory.abilities.add('compass')
        self.assertIn(('chest',(5,4)),atlas.discovered_markers(s))
        game.scene=GameScene.MAP;game.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RIGHT));self.assertEqual(s.map_floor,'B1F')
        game.draw(.016);self.assertTrue(any('B1F' in c[0] for c in game.renderer.ui.commands))
    def test_layout_all_rooms_all_window_sizes(self):
        game=Game(headless=True)
        for name in game.session.rooms.rooms:
            game.session.enter(name);game.visual=list(game.session.player.__dict__[k] for k in ('x','y'))
            for size in ((320,240),(640,480),(960,720),(1000,700),(240,180)):
                target=pygame.Surface(size);game.scene=GameScene.PLAY;game.draw(.016,target)
                self.assertTrue(all(target.get_rect().contains(rect) for rect in game.renderer.ui.rects))
    def test_box_search_replays_and_corner_deadlock_resets(self):
        s=DungeonSession();s.inventory.abilities.update(('gloves','mirror'))
        for name in ('r4','r5','r9'):
            room=s.rooms.rooms[name];solution=solve_boxes(room)
            self.assertIsNotNone(solution)
            bad=copy.deepcopy(room);next(o for o in bad['objects'] if o['type']=='box')['pos']=[1,1]
            self.assertIsNone(solve_boxes(bad))
            s.enter(name);s.puzzles.objects['box'].x=s.puzzles.objects['box'].y=1;s.reset()
            self.assertEqual(s.puzzles.objects['box'].pos,(6,9))
    def test_save_rejects_corrupt_bombs_and_preserves_old_file(self):
        s=DungeonSession()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'v3.json';s.save(path);data=json.loads(path.read_text());data['bombs']=99;path.write_text(json.dumps(data));original=path.read_bytes()
            loaded=DungeonSession.load(path);self.assertEqual(loaded.inventory.bombs,0);self.assertEqual(path.read_bytes(),original)
    def test_game_over_retry_restores_finite_boss_encounter(self):
        game=Game(headless=True);game.start(onboarding=False);game.session.inventory.abilities.add('boots');game.session.enter('r17');game.session.player.hp=0
        with patch.object(game,'save'):game.update(.016)
        self.assertEqual(game.scene,GameScene.GAMEOVER)
        with patch.object(game,'save'):game.choose('Retry room')
        self.assertEqual(game.scene,GameScene.PLAY);self.assertEqual(game.session.player.hp,5);self.assertEqual(game.session.combat.enemies[0].hp,12)
        self.assertFalse(game.session.bombs.bombs)
    def test_validator_detects_resource_and_supply_failure(self):
        for mutation in ('keys','bombs','boss_key'):
            rooms=copy.deepcopy(DungeonSession().rooms.rooms)
            if mutation=='keys':next(o for o in rooms['r3']['objects'] if o['id']=='combat_key')['amount']=0
            elif mutation=='bombs':rooms['r13']['objects']=[o for o in rooms['r13']['objects'] if o['type']!='supply']
            else:next(o for o in rooms['r6']['objects'] if o['id']=='boss_key')['boss_key']=False
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):DungeonValidator(rooms).validate()

    def test_removing_spare_key_keeps_all_spending_orders_solvable(self):
        rooms=copy.deepcopy(DungeonSession().rooms.rooms)
        next(o for o in rooms['r7']['objects'] if o['id']=='powder')['small_keys']=0
        report=DungeonValidator(rooms).validate()
        self.assertEqual(report['keys'],report['cost']);self.assertEqual(report['resource_states'],report['winning_states'])

    def test_dash_into_finish_enters_victory_scene(self):
        game=Game(headless=True);game.start(onboarding=False);s=game.session;s.inventory.abilities.add('boots');s.enter('r18')
        s.puzzles.objects['dawn'].state.active=True;s.puzzles.objects['treasure'].state.active=True;s.tick(0)
        s.player.x,s.player.y=20,8;s.player.facing=(1,0)
        with patch.object(game,'save'):game.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_LSHIFT))
        self.assertTrue(s.finished);self.assertEqual(game.scene,GameScene.VICTORY)
    def test_zero_health_rejects_gameplay_before_scene_update(self):
        game=Game(headless=True);game.start(onboarding=False);game.session.player.hp=0
        with patch.object(game,'save'):game.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_r))
        self.assertEqual(game.scene,GameScene.GAMEOVER);self.assertEqual(game.session.player.hp,0)

    def test_tutorial_controls_fit_without_truncation(self):
        game=Game(headless=True);game.scene=GameScene.TUTORIAL
        for size in ((320,240),(640,480),(960,720),(1000,700),(240,180)):
            target=pygame.Surface(size);game.draw(.016,target)
            scale=min(size[0]/320,size[1]/240);scale=int(scale) if scale>=1 else scale
            for text,x,y,color,base,width in game.renderer.ui.commands:
                if base==24:continue
                image=pixel_font.render(text,max(8,int(base*scale)),color)
                self.assertLessEqual(image.get_width(),int(width*scale) if width else size[0]-x*scale)
