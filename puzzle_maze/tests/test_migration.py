import json
from pathlib import Path
import tempfile
import unittest
from puzzle_maze.rooms import load_rooms,MAP_PATH
from puzzle_maze.session import GameSession
from puzzle_maze.combat import EnemyState

class CompactMigrationTests(unittest.TestCase):
    def test_v20_progress_and_checkpoint_migrate_without_reset(self):
        old=GameSession(rooms=load_rooms(MAP_PATH.with_name('dungeon_v20.json')))
        old.inventory.abilities.update({'gloves','boots','mirror','magnet'})
        old.inventory.keys['amber']=2;old.inventory.potions=3;old.inventory.coins=7
        old.enter('r6');old.player.x,old.player.y=38,20;old.player.hp=3
        enemy=old.combat.enemies[0];enemy.hp=0;enemy.state=EnemyState.DEAD;enemy.dropped=True
        old.exploration.tiles['r6'].add((38,20))
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';old.save(path)
            data=json.loads(path.read_text());data.pop('map_revision');data.pop('weapon')
            path.write_text(json.dumps(data));original=path.read_bytes()
            loaded=GameSession.load(path)
            self.assertEqual(loaded.rooms.current,'r6')
            self.assertEqual(loaded.inventory.abilities,old.inventory.abilities)
            self.assertEqual(loaded.inventory.keys,{'amber':2})
            self.assertEqual((loaded.inventory.potions,loaded.inventory.coins,loaded.player.hp),(3,7,3))
            self.assertEqual(loaded.combat.enemies[0].hp,0)
            self.assertTrue(loaded.migration_notice)
            self.assertFalse(loaded.puzzles.blocked(loaded.player.x,loaded.player.y))
            self.assertEqual(path.read_bytes(),original)
            loaded.save(path)
            self.assertEqual(path.with_name(path.name+'.v20.bak').read_bytes(),original)
            self.assertEqual(json.loads(path.read_text())['map_revision'],'2.1')
            loaded.reset();self.assertEqual(loaded.inventory.abilities,old.inventory.abilities)

    def test_boxes_from_removed_empty_space_are_relocated_safely(self):
        old=GameSession(rooms=load_rooms(MAP_PATH.with_name('dungeon_v20.json')))
        old.inventory.abilities.add('gloves');old.enter('r3')
        old.puzzles.objects['box1'].x,old.puzzles.objects['box1'].y=5,24
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';old.save(path);loaded=GameSession.load(path)
            self.assertEqual(loaded.rooms.current,'r3')
            box=loaded.puzzles.objects['box1']
            self.assertTrue(loaded.puzzles.tilemap.walkable(*box.pos))
            self.assertNotEqual(box.pos,loaded.puzzles.objects['box2'].pos)
            loaded.reset()
            self.assertEqual(loaded.puzzles.objects['box1'].pos,tuple(loaded.rooms.legacy_position((5,5))))

    def test_only_water_with_gameplay_purpose_remains(self):
        for name,room in load_rooms().items():
            water=[(x,y) for y,row in enumerate(room['tiles']) for x,t in enumerate(row) if t=='~']
            self.assertEqual(len(water),1 if name in ('r6','r7','r8') else 0)
