import os
import json
import copy
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pygame
from puzzle_maze.game import Game,GameScene
from puzzle_maze.icons import IconAtlas
from puzzle_maze.rewards import TREASURES,COLLECTIONS
from puzzle_maze.rooms import validate_rooms
from puzzle_maze.advanced_dungeon import AdvancedDungeonSession
from puzzle_maze.exploration import DungeonAtlas
from puzzle_maze.room_art import RoomArt

class FourthPresentationTests(unittest.TestCase):
    def tearDown(self):pygame.quit()
    def test_all_treasures_have_real_icons_and_secret_conditions(self):
        pygame.init();atlas=IconAtlas()
        for treasure in TREASURES:
            image=atlas.get(treasure);self.assertTrue(any(image.get_at((x,y)).a for x in range(12) for y in range(12)))
            self.assertNotEqual(pygame.image.tobytes(image,'RGBA'),pygame.image.tobytes(atlas.get('pulse'),'RGBA'))
        rooms=AdvancedDungeonSession().rooms.rooms
        found={t for room in rooms.values() for o in room['objects'] for t in o.get('loot',[]) if t in COLLECTIONS}
        self.assertEqual(found,COLLECTIONS)
        self.assertTrue(all(room['goal'] and room['objects'] for room in rooms.values()))
    def test_all_new_rooms_and_two_tutorial_pages_fit(self):
        game=Game(headless=True)
        for room in ('r19','r20','r21','r22','r17'):
            game.session.enter(room);game.visual=[2.,7.]
            for size in ((240,180),(320,240),(640,480),(960,720),(1000,700)):
                target=pygame.Surface(size);game.scene=GameScene.PLAY;game.draw(.016,target)
                self.assertTrue(all(target.get_rect().contains(rect) for rect in game.renderer.ui.rects))
        for page in (0,1):
            game.tutorial.page=page;game.scene=GameScene.TUTORIAL;game.draw(.016)
            self.assertTrue(all(c[0].isascii() for c in game.renderer.ui.commands))
        game.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_LEFT));self.assertEqual(game.tutorial.page,0)
    def test_room_art_cached_distinct_and_noncolliding(self):
        pygame.init();s=AdvancedDungeonSession();art=RoomArt()
        samples={pygame.image.tobytes(art.layer(s.rooms.rooms[name]),'RGBA') for name in ('r1','r2','r5','r19','r20','r21','r22')}
        self.assertEqual(len(samples),7)
        for room in s.rooms.rooms.values():
            original=list(room['tiles']);self.assertIs(art.layer(room),art.layer(room));self.assertEqual(room['tiles'],original)
            for y,row in enumerate(original):
                for x,tile in enumerate(row):
                    if tile in '#O~':self.assertEqual(art.layer(room).get_at((x*16+8,y*16+8)).a,0)
    def test_secret_chests_not_marked_before_unlocked(self):
        s=AdvancedDungeonSession();s.enter('r22');s.inventory.abilities.add('compass');s.exploration.tiles['r22']={(20,5)}
        self.assertNotIn(('chest',(20,5)),DungeonAtlas(s.rooms).discovered_markers(s))
        s.puzzles.objects['sequence'].state.active=True
        s.puzzles.objects['skin'].advance(s.puzzles,0)
        self.assertIn(('chest',(20,5)),DungeonAtlas(s.rooms).discovered_markers(s))
    def test_archive_navigation_does_not_overwrite_current_expedition(self):
        game=Game(headless=True)
        with patch.object(game.session,'save') as saved:
            game.choose('Archived expeditions');game.choose('Main menu');saved.assert_not_called()
            game.choose('Archived expeditions');game.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE));saved.assert_not_called()
        self.assertEqual(game.scene,GameScene.MENU)
    def test_powder_and_throw_repeat_do_not_consume_twice(self):
        game=Game(headless=True);game.start(onboarding=False);s=game.session;s.inventory.abilities.update(('powder','gloves'));s.inventory.powder=5;s.enter('r19')
        s.player.x,s.player.y=7,6;s.player.facing=(0,-1)
        game.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_p));game.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_p,repeat=True));self.assertEqual(s.inventory.powder,4)
        s.enter('r20');s.player.x,s.player.y=5,6;s.player.facing=(1,0);game.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e))
        game.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_g));game.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_g,repeat=True));self.assertEqual(len(s.pot_flights),1)
    def test_wrong_order_respawn_and_summons_never_overlap_player(self):
        s=AdvancedDungeonSession();s.enter('r22');s.player.x,s.player.y=7,5
        s.combat.enemies[-1].receive_damage(s.combat,99,'bomb',s.player)
        self.assertTrue(all(e.pos!=(s.player.x,s.player.y) and s.puzzles.can_enter(*e.pos) for e in s.combat.enemies))
        s.enter('r21');s.player.x,s.player.y=15,5;s.combat.enemies[0].hp=3;s.tick(.1)
        self.assertTrue(all(e.pos!=(s.player.x,s.player.y) for e in s.combat.enemies))
    def test_death_does_not_settle_or_replace_living_save(self):
        s=AdvancedDungeonSession();s.grant_treasure('test','token_cache')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'run.json';s.save(path);original=path.read_bytes();s.player.hp=0;s.finished=True
            self.assertIsNone(s.rewards.settle(True,False));s.save(path);self.assertEqual(path.read_bytes(),original)
            loaded=AdvancedDungeonSession.load(path);self.assertFalse(loaded.rewards.claimed);self.assertEqual(loaded.rewards.tokens,10)

    def test_boss_hud_avoids_live_actor_and_carry_prompt_matches_input(self):
        game=Game(headless=True);game.scene=GameScene.PLAY;s=game.session;s.enter('r21')
        for x,y in ((9,9),(3,3),(12,13)):
            s.player.x,s.player.y=x,y;game.visual=[float(x),float(y)];game.draw(.016)
            camera=game.renderer.camera;actor=pygame.Rect(x*16-int(camera.x),y*16-int(camera.y),16,16)
            self.assertFalse(game.renderer.boss_panel_rect.colliderect(actor))
        s.inventory.abilities.add('gloves');s.enter('r20');s.inventory.carried='jar';s.puzzles.objects['jar'].state.active=True
        s.player.x,s.player.y=8,9;game.visual=[8.,9.];game.draw(.016)
        self.assertTrue(any('Drop / G Throw' in c[0] for c in game.renderer.ui.commands))

    def test_corrupt_reward_save_falls_back_without_overwriting(self):
        s=AdvancedDungeonSession();s.grant_treasure('cache','token_cache')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'save.json';s.save(path);data=json.loads(path.read_text())
            data['extension']['rewards']['claimed']=True;path.write_text(json.dumps(data));original=path.read_bytes()
            loaded=AdvancedDungeonSession.load(path);self.assertEqual(loaded.rewards.tokens,0);self.assertFalse(loaded.rewards.claimed);self.assertEqual(path.read_bytes(),original)
    def test_settled_reward_cannot_be_reset_to_claim_again(self):
        s=AdvancedDungeonSession();s.grant_treasure('cache','token_cache');s.finished=True
        receipt=s.rewards.settle(True,True);self.assertFalse(s.reset());self.assertTrue(s.rewards.claimed);self.assertEqual(s.rewards.settle(True,True),receipt)
    def test_invalid_torches_crystals_weights_and_ghosts_rejected(self):
        for mutation in ('order','color','weight','ghost'):
            rooms=copy.deepcopy(AdvancedDungeonSession().rooms.rooms)
            if mutation=='order':next(o for o in rooms['r19']['objects'] if o['id']=='flames')['order']=['missing']
            elif mutation=='color':next(o for o in rooms['r21']['objects'] if o['id']=='red')['color']='purple'
            elif mutation=='weight':next(o for o in rooms['r20']['objects'] if o['id']=='load')['weight']=-1
            else:rooms['r19']['enemies'][0]['torch']='missing'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):validate_rooms(rooms)
    def test_both_tutorial_pages_fit_without_truncating_key_hints(self):
        from puzzle_maze import pixel_font
        game=Game(headless=True);game.scene=GameScene.TUTORIAL
        for page in (0,1):
            game.tutorial.page=page
            for size in ((240,180),(320,240),(640,480),(960,720),(1000,700)):
                game.draw(.016,pygame.Surface(size));scale=min(size[0]/320,size[1]/240);scale=int(scale) if scale>=1 else scale
                for text,x,y,color,base,width in game.renderer.ui.commands:
                    if base==24:continue
                    self.assertLessEqual(pixel_font.render(text,max(8,int(base*scale)),color).get_width(),int(width*scale))
