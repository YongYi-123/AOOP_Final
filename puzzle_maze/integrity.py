"""Entrance/reward integrity plus resource-state and crate search validation.

The report distinguishes resource search from physical gameplay witnesses in
 tests/test_v4_campaign.py. It does not claim to simulate every enemy trajectory.
"""
from puzzle_maze.core import TileMap
from puzzle_maze.validator import DungeonValidator

ENTRANCES = {'stone', 'locked', 'cave', 'walkthrough', 'remote',
             'stairs_up', 'stairs_down', 'boss_gate'}
ABILITIES = {'map', 'compass', 'boots', 'gloves', 'mirror', 'magnet', 'powder'}


class DungeonIntegrityValidator:
    def __init__(self, rooms):
        self.rooms = rooms

    def validate(self):
        report = DungeonValidator(self.rooms).validate()
        flags = {o['flag'] for room in self.rooms.values() for o in room['objects'] if 'flag' in o}
        flags |= {room['on_clear_flag'] for room in self.rooms.values() if 'on_clear_flag' in room}
        chests = hidden = stairs = exits = secrets = 0
        finish = []
        for name, room in self.rooms.items():
            for obj in room['objects']:
                if obj['type'] != 'chest':
                    continue
                chests += 1
                hidden += bool(obj.get('hidden'))
                if not set(obj.get('ability_requires', [])) <= ABILITIES:
                    raise ValueError(f'{name}: invalid chest ability trigger')
                if not set(obj.get('flag_requires', [])) <= flags:
                    raise ValueError(f'{name}: missing chest flag producer')
                if obj.get('hidden') and not any(obj.get(key) for key in ('requires', 'ability_requires', 'flag_requires')):
                    raise ValueError(f'{name}: hidden chest lacks a trigger')
                if not any(obj.get(key) for key in ('ability', 'loot', 'small_keys', 'boss_key', 'bombs', 'powder', 'potions', 'coins')):
                    raise ValueError(f'{name}: empty chest')
            for exit in room['exits']:
                exits += 1
                kind = exit.get('entrance')
                if kind not in ENTRANCES:
                    raise ValueError(f'{name}: invalid entrance art')
                target = self.rooms[exit['target']]
                arrival = tuple(exit['arrival'])
                if not TileMap(target['tiles']).walkable(*arrival):
                    raise ValueError(f'{name}: blocked arrival')
                if any(tuple(o['pos']) == arrival and o['type'] in ('box', 'door', 'pot', 'cracked', 'secret', 'crystal_barrier') for o in target['objects']):
                    raise ValueError(f'{name}: arrival overlaps mechanism')
                if any(tuple(e['pos']) == arrival for e in target.get('enemies', [])):
                    raise ValueError(f'{name}: arrival overlaps enemy')
                if not set(exit.get('flag_requires', [])) <= flags:
                    raise ValueError(f'{name}: missing entrance flag producer')
                if not set(exit.get('abilities', [])) <= ABILITIES:
                    raise ValueError(f'{name}: unknown entrance ability')
                if exit.get('finish'):
                    finish.append(name)
                    if not exit.get('requires'):
                        raise ValueError('Unguarded final exit')
                    continue
                returns = [e for e in target['exits'] if e['target'] == name]
                if not returns:
                    raise ValueError(f'{name}: entrance has no return')
                if room['floor'] != target['floor']:
                    stairs += 1
                    expected = 'stairs_down' if room['floor'] == '1F' else 'stairs_up'
                    if kind != expected or not any(e.get('stairs') for e in returns):
                        raise ValueError(f'{name}: inconsistent floor stairs')
                elif kind.startswith('stairs'):
                    raise ValueError(f'{name}: stairs have no floor change')
                if kind in ('walkthrough', 'remote') or any(o['type']=='cracked' and o['id'] in exit.get('requires', []) for o in room['objects']):
                    secrets += 1
        if len(finish) != 1:
            raise ValueError('Expected one final destination')
        report.update(chests=chests, hidden_chests=hidden, entrances=exits,
                      stair_entrances=stairs, secret_entrances=secrets,
                      final_room=finish[0])
        return report


if __name__ == '__main__':
    import json
    from puzzle_maze.advanced_dungeon import AdvancedDungeonSession
    print(json.dumps(DungeonIntegrityValidator(AdvancedDungeonSession().rooms.rooms).validate(), indent=2))
