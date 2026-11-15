"""v4.5 campaign; compose the proven 4.4 adventure without altering archived data."""
from puzzle_maze.advanced_dungeon import AdvancedDungeonSession
from puzzle_maze.rooms import load_rooms,MAP_PATH
from puzzle_maze.layout45 import upgrade
import copy
import json
import shutil
from pathlib import Path
V45_SAVE=Path(__file__).parent/"save_v45.json"

class RemasteredSession(AdvancedDungeonSession):
    def __init__(self,rooms=None):
        self.hint_requests={};self.room_elapsed=0.
        super().__init__(upgrade(rooms or load_rooms(MAP_PATH.with_name('dungeon_v4.json'))))

    def enter(self,name,arrival=None):
        super().enter(name,arrival);self.room_elapsed=0.

    def tick(self,dt):
        super().tick(dt)
        if self.player.hp>0:self.room_elapsed+=max(0,dt)

    def next_hint(self):
        from puzzle_maze.hints45 import HINTS
        room=self.rooms.current
        self.hint_requests[room]=self.hint_requests.get(room,0)+1
        clues=(self.rooms.data['hint'],)+HINTS.get(room,())
        tier=min(len(clues)-1,self.hint_requests[room]-1+(self.room_elapsed>=75))
        return clues[tier]

    def save(self,path=V45_SAVE):
        path=Path(path)
        if path.exists():
            try:old=json.loads(path.read_text())
            except (OSError,ValueError):old={}
            backup=path.with_name(path.name+'.pre-v45')
            if old.get('content_revision')!='4.5' and not backup.exists():shutil.copy2(path,backup)
        return super().save(path)

    @classmethod
    def load(cls,path=V45_SAVE):
        from puzzle_maze.advanced_dungeon import V4_SAVE
        path=Path(path)
        if path==V45_SAVE and not path.exists() and V4_SAVE.exists():path=V4_SAVE
        return super().load(path)

    def normalize_save_header(self,data):
        result=copy.deepcopy(data)
        if result.get('version')!=2: return result
        old=result.get('room')
        if old in self.rooms.rooms: return result
        aliases={'B2F':'r27','b2_vault':'r27','royal_vault':'r27','underground':'r10'}
        destination=aliases.get(old,'r1')
        for field in ('snapshots','encounters','explored'):
            result[field]={k:v for k,v in result.get(field,{}).items() if k in self.rooms.rooms}
        for field in ('visited','completed'):
            result[field]=[k for k in result.get(field,[]) if k in self.rooms.rooms]
        self.enter(destination)
        result['room']=destination;result['player']=list(self.rooms.data['spawn'])
        checkpoint=copy.deepcopy(self.checkpoint)
        for field in ('hp','inventory','abilities','potions','coins','powder','heart_fragments','bombs','boss_key','flags'):
            checkpoint[field]=copy.deepcopy(result.get(field,checkpoint.get(field)))
        checkpoint['reward_bag']=copy.deepcopy(result.get('extension',{}).get('rewards',checkpoint['reward_bag']))
        if destination in result['snapshots']: checkpoint['objects']=copy.deepcopy(result['snapshots'][destination])
        result['checkpoint']=checkpoint;result['carried']=None;result['bomb_state']={}
        if 'extension' in result: result['extension']['orb']=copy.deepcopy(checkpoint['orb'])
        self.migration_notice='Old floor reference recovered; items and objectives retained.'
        return result

    def prepare_loaded_save(self,data):
        if data.get('content_revision')=='4.5': return data
        result=super().prepare_loaded_save(data)
        result['content_revision']='4.5'
        self.migration_notice='Progress restored in the two-floor 4.5 remaster.'
        return result
