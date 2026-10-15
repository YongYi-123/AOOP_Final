"""Absolute geometry, functional mechanisms and optional multi-floor growth."""
import copy
import tempfile
import unittest
from pathlib import Path
from collections import deque
import pygame
from puzzle_maze.advanced_dungeon import AdvancedDungeonSession
from puzzle_maze.coordinates import RoomCoordinate,DoorValidator,DELTAS
from puzzle_maze.dependencies import ChestValidator,PuzzleDependencyValidator
from puzzle_maze.exploration import DungeonAtlas
from puzzle_maze.game import Game,GameScene
from puzzle_maze.entrances import entrance_visible

class Upgrade42Tests(unittest.TestCase):
    def test_coordinates_are_unique_and_all_cardinal_doors_adjacent(self):
        rooms=AdvancedDungeonSession().rooms.rooms;coordinates={RoomCoordinate.from_room(r) for r in rooms.values()}
        self.assertEqual(len(coordinates),22);self.assertEqual(DoorValidator(rooms).validate(),51)
        for name,room in rooms.items():
            for e in room['exits']:
                if e.get('stairs') or e.get('finish'):continue
                a=RoomCoordinate.from_room(room);b=RoomCoordinate.from_room(rooms[e['target']])
                self.assertEqual(a.direction_to(b),e['direction']);self.assertEqual(abs(a.grid_x-b.grid_x)+abs(a.grid_y-b.grid_y),1)

    def test_validator_rejects_overlap_wrong_direction_and_wrong_return_landing(self):
        rooms=AdvancedDungeonSession().rooms.rooms
        for change in ('overlap','direction','arrival','return'):
            bad=copy.deepcopy(rooms)
            if change=='overlap':bad['r1'].update(grid_x=2,grid_y=2)
            elif change=='direction':bad['r1']['exits'][0]['direction']='SOUTH'
            elif change=='arrival':bad['r1']['exits'][0]['arrival']=[2,7]
            else:bad['r1']['exits'][0]['return_id']='fake'
            with self.assertRaises(ValueError):DoorValidator(bad).validate()

    def test_every_door_has_walkable_approach_after_its_conditions(self):
        s=AdvancedDungeonSession()
        for name,room in s.rooms.rooms.items():
            s.enter(name);s.inventory.flags.update(flag for e in room['exits'] for flag in e.get('flag_requires',[]))
            for o in s.puzzles.objects.values():
                if o.blocking:o.state.active=True
            start=tuple(room['spawn']);queue=deque([start]);seen={start}
            while queue:
                x,y=queue.popleft()
                for dx,dy in DELTAS.values():
                    p=x+dx,y+dy
                    if p not in seen and s.puzzles.can_enter(*p):seen.add(p);queue.append(p)
            for exit in room['exits']:self.assertIn(tuple(exit['pos']),seen,f'{name}:{exit["id"]}')

    def test_all_chests_have_interaction_routes_and_actuators_have_targets(self):
        rooms=AdvancedDungeonSession().rooms.rooms
        self.assertEqual(ChestValidator(rooms).validate(),30)
        effects=PuzzleDependencyValidator(rooms).validate();self.assertEqual(len(effects),36)
        self.assertTrue(any(target.startswith('r2:') for target in effects['r19:flame_signal']))
        bad=copy.deepcopy(rooms);bad['r1']['objects'].append(dict(id='fake',type='switch',pos=[6,10]))
        with self.assertRaises(ValueError):PuzzleDependencyValidator(bad).validate()

    def test_validator_rejects_untriggerable_color_and_object_placement(self):
        from puzzle_maze.rooms import validate_rooms
        rooms=AdvancedDungeonSession().rooms.rooms
        for mutation in ('color','placement','pillar'):
            bad=copy.deepcopy(rooms)
            if mutation=='color':next(o for o in bad['r12']['objects'] if o['id']=='crystal_cache')['crystal_color']='green'
            elif mutation=='placement':next(o for o in bad['r22']['objects'] if o['id']=='arrangement')['placements'][0]['object']='missing'
            else:next(o for o in bad['r20']['objects'] if o['type']=='pillar')['flag']=''
            with self.assertRaises(ValueError):validate_rooms(bad)

    def test_real_transition_arrives_at_the_opposite_entrance_and_returns(self):
        s=AdvancedDungeonSession();s.puzzles.objects['lever'].state.active=True;s.tick(0)
        exit=next(e for e in s.rooms.data['exits'] if e['target']=='r2');s.player.x,s.player.y=exit['pos']
        self.assertTrue(s.transition());self.assertEqual((s.player.x,s.player.y),tuple(exit['arrival']))
        reverse=next(e for e in s.rooms.data['exits'] if e['target']=='r1');s.player.x,s.player.y=reverse['pos']
        self.assertTrue(s.transition());self.assertEqual((s.player.x,s.player.y),tuple(reverse['arrival']))

    def test_reversible_dash_gate_can_be_walked_back_after_timeout(self):
        s=AdvancedDungeonSession();s.inventory.abilities.add('boots');s.enter('r6');s.player.x,s.player.y=16,8;s.player.facing=(1,0)
        self.assertEqual(s.puzzles.interact(s.player),'clock');self.assertEqual(s.dash(),3);s.tick(1)
        self.assertEqual(s.player.x,19);self.assertTrue(s.move(-1,0));self.assertTrue(s.move(-1,0))
        self.assertEqual(s.player.x,17)

    def test_map_without_item_only_draws_current_room_in_minimap(self):
        game=Game(headless=True);s=game.session;s.visited.update(('r2','r4'))
        # Inspect graph API as well as rendered minimap; no future rooms or connections.
        self.assertNotIn('map',s.inventory.abilities)
        self.assertEqual(set(DungeonAtlas(s.rooms).displayed_layout(s,minimap=True)),{'r1'})
        self.assertEqual(set(DungeonAtlas(s.rooms).displayed_layout(s)),s.visited)
        game.renderer.ui.clear();game.renderer.atlas_graph(s,(8,8,94,44))
        s.inventory.abilities.add('map');self.assertGreater(len(DungeonAtlas(s.rooms).displayed_layout(s,minimap=True)),3);game.renderer.atlas_graph(s,(8,8,94,44))
        self.assertEqual(DungeonAtlas(s.rooms).layout(s.visited)['r2'],(2,2))
        self.assertNotIn('r8',DungeonAtlas(s.rooms).visible_rooms(s.visited))

    def test_orb_requires_gloves_and_game_e_g_t_match_real_actions(self):
        game=Game(headless=True);game.scene=GameScene.PLAY;s=game.session;s.enter('r20');s.player.x,s.player.y=10,12;s.player.facing=(0,-1)
        self.assertFalse(s.interact_orb());s.inventory.abilities.add('gloves')
        game.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e));self.assertTrue(s.orb.carried)
        game.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_g));self.assertFalse(s.orb.carried)
        game.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_t));self.assertEqual(s.orb.pos,(10,11));self.assertEqual(s.orb.room,'r20')

    def test_pot_cannot_be_lifted_while_orb_is_carried(self):
        s=AdvancedDungeonSession();s.inventory.abilities.add('gloves');s.enter('r20');s.orb.carried=True
        self.assertFalse(s.puzzles.objects['jar'].interact(s.puzzles,s.player));self.assertIsNone(s.inventory.carried)

    def test_carried_orb_prompt_matches_drop_action_instead_of_nearby_pot(self):
        game=Game(headless=True);game.scene=GameScene.PLAY;s=game.session;s.inventory.abilities.add('gloves');s.enter('r20')
        s.player.x,s.player.y=10,12;s.interact_orb();game.visual=[10.,12.];game.draw(.016)
        labels=[command[0] for command in game.renderer.ui.commands]
        self.assertTrue(any('Drop / G Orb / T Recall' in text for text in labels))
        self.assertFalse(any('[E] Lift' in text for text in labels))

    def test_orb_carries_through_allowed_door_with_correct_room_position(self):
        s=AdvancedDungeonSession();s.inventory.abilities.add('gloves');s.enter('r20');s.player.x,s.player.y=10,12
        self.assertTrue(s.interact_orb());exit=next(e for e in s.rooms.data['exits'] if e['target']=='r4');s.player.x,s.player.y=exit['pos'];s.tick(0)
        self.assertTrue(s.transition());self.assertTrue(s.orb.carried);self.assertEqual(s.orb.room,'r4');self.assertEqual(s.orb.pos,(s.player.x,s.player.y))

    def test_portal_refuses_orb_without_losing_it(self):
        s=AdvancedDungeonSession();s.inventory.abilities.update(('boots','mirror','magnet'));s.enter('r13')
        exit=next(e for e in s.rooms.data['exits'] if e.get('portal'));s.puzzles.objects['gate'].latched=True;s.puzzles.objects['gate'].state.active=True
        s.orb.carried=True;s.orb.room='r13';s.player.x,s.player.y=exit['pos'];self.assertFalse(s.transition());self.assertTrue(s.orb.carried)

    def test_orb_throw_destroys_pillar_and_does_not_pass_walls(self):
        s=AdvancedDungeonSession();s.inventory.abilities.add('gloves');s.enter('r20')
        for enemy in s.combat.enemies:enemy.receive_damage(s.combat,100,'pot',s.player)
        s.orb.carried=True;s.player.x,s.player.y=13,10;s.player.facing=(1,0)
        self.assertTrue(s.throw_pot());self.assertIn('pillar_storage',s.inventory.flags);self.assertTrue(s.puzzles.objects['tower_pillar'].state.active)
        self.assertEqual(s.orb.pos,(14,10));s.orb.carried=True;s.player.x,s.player.y=1,5;s.player.facing=(-1,0)
        self.assertTrue(s.throw_pot());self.assertEqual(s.orb.pos,(1,5))

    def test_two_pillars_unlock_real_new_stairs_and_map_connection(self):
        s=AdvancedDungeonSession();s.enter('r20');exit=next(e for e in s.rooms.data['exits'] if e.get('transformed'))
        self.assertFalse(entrance_visible(s,exit));s.player.x,s.player.y=exit['pos'];self.assertFalse(s.transition())
        s.inventory.flags.update(('pillar_storage','pillar_foundry'));s.tick(0)
        self.assertIn('floor_lowered',s.inventory.flags);self.assertTrue(entrance_visible(s,exit));self.assertTrue(s.transition())
        self.assertEqual(s.rooms.data['floor'],'B1F');self.assertEqual(s.rooms.current,'r22');self.assertEqual((s.player.x,s.player.y),(5,12))
        back=next(e for e in s.rooms.data['exits'] if e.get('transformed'));s.player.x,s.player.y=back['pos'];self.assertTrue(s.transition());self.assertEqual(s.rooms.current,'r20')

    def test_ordered_blocks_trigger_chest_and_wrong_layout_remains_retryable(self):
        s=AdvancedDungeonSession();s.inventory.abilities.add('gloves');s.enter('r22')
        s.puzzles.objects['totem_a'].x,s.puzzles.objects['totem_a'].y=20,9
        s.puzzles.objects['totem_b'].x,s.puzzles.objects['totem_b'].y=16,9;s.tick(0)
        self.assertFalse(s.puzzles.objects['arrangement'].state.active)
        s.reset();self.assertEqual(s.puzzles.objects['totem_a'].pos,(16,10))
        for x in (16,20):
            s.player.x,s.player.y=x,11;self.assertTrue(s.move(0,-1))
        self.assertTrue(s.puzzles.objects['arrangement'].state.active);s.tick(.45)
        self.assertTrue(s.puzzles.objects['layout_cache'].visible)

    def test_crystal_can_reveal_reward_in_another_room(self):
        s=AdvancedDungeonSession();s.enter('r12');s.puzzles.objects['gate'].latched=True;s.puzzles.update(0,s.player)
        self.assertFalse(s.puzzles.objects['crystal_cache'].visible)
        s.inventory.flags.add('crystal_blue');s.puzzles.update(0,s.player)
        self.assertTrue(s.puzzles.objects['crystal_cache'].visible)

    def test_orb_pillar_and_transformation_save_restore_reset(self):
        s=AdvancedDungeonSession();s.inventory.abilities.add('gloves');s.enter('r20')
        for enemy in s.combat.enemies:enemy.receive_damage(s.combat,100,'pot',s.player)
        s.orb.carried=True;s.player.x,s.player.y=13,10;s.player.facing=(1,0);s.throw_pot()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'run.json';s.save(path);loaded=AdvancedDungeonSession.load(path)
            self.assertEqual(loaded.rooms.current,'r20');self.assertEqual(loaded.orb.pos,(14,10));self.assertIn('pillar_storage',loaded.inventory.flags)
            loaded.reset();self.assertNotIn('pillar_storage',loaded.inventory.flags);self.assertEqual(loaded.orb.room,'r20');self.assertEqual(loaded.orb.pos,(10,11))

    def test_all_new_room_art_and_ui_render_without_mutating_geometry(self):
        game=Game(headless=True);game.scene=GameScene.PLAY
        for name in ('r2','r11','r20','r22'):
            game.session.enter(name);before=list(game.session.rooms.data['tiles']);game.visual=[game.session.player.x,game.session.player.y]
            game.draw(.016);self.assertEqual(game.session.rooms.data['tiles'],before)
