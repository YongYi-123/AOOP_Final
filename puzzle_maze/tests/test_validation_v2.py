import copy
import json
from pathlib import Path
import tempfile
import unittest
from puzzle_maze.rooms import load_rooms,validate_rooms
from puzzle_maze.session import GameSession

class ValidationV2Tests(unittest.TestCase):
    def test_reject_invalid_conditions_enemy_tools_and_light(self):
        rooms=load_rooms()
        for mutation in ('cycle','enemy','ability','light','atlas','missing_exit'):
            bad=copy.deepcopy(rooms)
            if mutation=='cycle':bad['r1']['objects'][1]['requires']=['seal']
            elif mutation=='enemy':bad['r1']['enemies'][0]['pos']=bad['r1']['spawn']
            elif mutation=='ability':next(o for o in bad['r1']['objects'] if o['type']=='chest')['ability']='unknown'
            elif mutation=='light':next(o for o in bad['r5']['objects'] if o['type']=='light')['direction']=[1,1]
            elif mutation=='atlas':bad['r1']['atlas']=[-1,0]
            else:bad['r1']['exits'][0]['requires']=['missing']
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):validate_rooms(bad)

    def test_bad_growth_health_encounter_and_fog_saves_fall_back(self):
        s=GameSession()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';s.save(path);valid=json.loads(path.read_text())
            for field,value in [('abilities',['unknown']),('hp',99),('dash_cooldown',float('inf')),('potions',-1),('explored',{'r1':[[999,0]]}),('encounters',{'r1':{'enemies':{},'loot':[]}})]:
                data=copy.deepcopy(valid);data[field]=value;path.write_text(json.dumps(data))
                loaded=GameSession.load(path)
                self.assertEqual(loaded.player.hp,5);self.assertEqual(loaded.inventory.abilities,set())
                self.assertEqual(loaded.rooms.current,'r1')

    def test_legacy_save_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';original='{"version":1,"room":"r1"}'
            path.write_text(original);GameSession.load(path)
            self.assertEqual(path.read_text(),original)
