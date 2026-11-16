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
        self.grey_pixel=False;self.lore=set();self.lab_memory_seen=False
        self.hint_requests={};self.room_elapsed=0.
        self.inspection_counts={};self.prototype_recording_seen=False
        from puzzle_maze.studio_companion import StudioCompanion
        self.studio_companion=StudioCompanion()
        super().__init__(upgrade(rooms or load_rooms(MAP_PATH.with_name('dungeon_v4.json'))))

    def enter(self,name,arrival=None):
        super().enter(name,arrival);self.room_elapsed=0.
        self.observe_secret()

    def tick(self,dt):
        super().tick(dt)
        if self.player.hp>0:self.room_elapsed+=max(0,dt)
        self.observe_secret()
        if self.rooms.current=='r28' and self.lab_memory_seen:
            self.studio_companion.update(dt,self)
            miao=self.puzzles.objects.get('miao')
            if miao:miao.x,miao.y=self.studio_companion.tile

    def observe_secret(self):
        from puzzle_maze.puzzles import ChestPhase
        from puzzle_maze.secret45 import DISCOVERY
        obj=self.puzzles.objects.get('grey_pixel')
        if obj and obj.state.active and not self.grey_pixel:
            self.grey_pixel=True
            self.inventory.notifications.append(('map',DISCOVERY))
            self.combat.events.append('solve')
        if self.grey_pixel:
            self.inventory.flags.add('grey_pixel')
            if obj:obj.state.active=True;obj.phase=ChestPhase.OPENED

    def interact_orb(self):
        from puzzle_maze.puzzles import ChestPhase
        # Story objects take E priority, so carrying the campaign weight never traps the secret flow.
        for obj in self.puzzles.objects.values():
            if abs(obj.x-self.player.x)+abs(obj.y-self.player.y)>1:continue
            if obj.data['type']=='mystery_scroll' or obj.data.get('grey_pixel') and obj.phase==ChestPhase.AVAILABLE:
                return False
        return super().interact_orb()

    def reset(self):
        super().reset();self.observe_secret()

    def read_lore(self,key):
        from puzzle_maze.secret45 import LORE
        if self.rooms.current=='r28' and key in LORE:self.lore.add(key)

    def inspect_object(self,object_id):
        if self.rooms.current!='r28' or object_id not in self.puzzles.objects:raise ValueError('Unknown workshop object')
        # The essential recording cannot be skipped by reopening or cancelling it.
        if object_id=='work_prototype' and not self.prototype_recording_seen:return 0
        count=self.inspection_counts.get(object_id,0)
        self.inspection_counts[object_id]=min(1000000000,count+1)
        from puzzle_maze.workshop_content import RESPONSES
        content=self.puzzles.objects[object_id].data['content_id']
        from puzzle_maze.workshop_documents import DOCUMENTS
        return count%(3 if content in DOCUMENTS else len(RESPONSES.get(content,(None,))))

    def complete_prototype_recording(self):
        self.prototype_recording_seen=True
        self.inspection_counts['work_prototype']=1
        self.read_lore('work_prototype')

    def capture(self):
        snapshot=super().capture()
        # Miao's walking location is transient; the existing save schema validates
        # readable story objects at their authored coordinates.
        if self.rooms.current=='r28' and 'miao' in snapshot:
            from puzzle_maze.studio_layout import MIAO_TILE
            snapshot['miao']['pos']=list(MIAO_TILE)
        return snapshot

    def save_extension(self):
        result=super().save_extension()
        result['remaster']=dict(grey_pixel=self.grey_pixel,lore=sorted(self.lore),lab_memory_seen=self.lab_memory_seen,studio_revision=9,inspection_counts=dict(self.inspection_counts),prototype_recording_seen=self.prototype_recording_seen)
        return result

    def load_extension(self,data):
        super().load_extension(data)
        from puzzle_maze.secret45 import LORE
        extra=data.get('remaster',{})
        if type(extra.get('grey_pixel',False)) is not bool or not isinstance(extra.get('lore',[]),list) or not set(extra.get('lore',[]))<=LORE.keys():raise ValueError('Invalid remaster secrets')
        if type(extra.get('studio_revision',0)) is not int or extra.get('studio_revision',0) not in (0,2,3,4,5,6,7,8,9):raise ValueError('Invalid studio revision')
        self.grey_pixel=extra.get('grey_pixel',False);self.lore=set(extra.get('lore',[]))
        if type(extra.get('lab_memory_seen',False)) is not bool:raise ValueError('Invalid lab memory')
        self.lab_memory_seen=extra.get('lab_memory_seen',False)
        counts=extra.get('inspection_counts',{})
        if not isinstance(counts,dict) or any(not isinstance(key,str) or type(value) is not int or not 0<=value<=1000000000 for key,value in counts.items()):raise ValueError('Invalid inspection counters')
        self.inspection_counts=dict(counts)
        seen=extra.get('prototype_recording_seen',False)
        if type(seen) is not bool:raise ValueError('Invalid prototype recording')
        self.prototype_recording_seen=seen
        self.observe_secret()

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
            old_studio=old.get('extension',{}).get('remaster',{}).get('studio_revision',0)
            studio_backup=path.with_name(path.name+('.pre-studio-v2' if old_studio==0 else '.pre-studio-v'+str(old_studio+1)))
            if old.get('version')==2 and old.get('extension',{}).get('remaster',{}).get('studio_revision')!=9 and (old.get('room')=='r28' or 'r28' in old.get('snapshots',{})) and not studio_backup.exists():shutil.copy2(path,studio_backup)
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
        result=copy.deepcopy(data) if data.get('content_revision')=='4.5' else super().prepare_loaded_save(data)
        from puzzle_maze.studio_layout import migrate_save
        migrate_save(result,self.rooms.rooms['r28'])
        from puzzle_maze.puzzles import Chest
        entries=list(result['snapshots'].items())+[(result['room'],result['checkpoint']['objects'])]
        for room,snapshot in entries:
            objects=self.make_puzzles(self.rooms.rooms[room]).objects
            if room=='r28':
                for old_id in set(snapshot)-set(objects):snapshot.pop(old_id)
            for id,obj in objects.items():
                if id not in snapshot and obj.data.get('optional'):
                    snapshot[id]=dict(pos=list(obj.pos),active=False,remaining=0,unlocked=False,latched=False)
                    if isinstance(obj,Chest):snapshot[id].update(chest_phase=obj.phase.value,spawn_time=0.,triggered=False)
        result['content_revision']='4.5'
        self.migration_notice='Progress restored in the two-floor 4.5 remaster.'
        return result
