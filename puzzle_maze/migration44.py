"""Additive royal content; preserve keys, already-revealed chests and completion."""
import copy
from puzzle_maze.puzzles import PuzzleManager

def migrate(data,rooms):
    if data.get('content_revision')=='4.4':return data
    result=copy.deepcopy(data)
    for name,snapshot in list(result['snapshots'].items())+[(result['room'],result['checkpoint']['objects'])]:
        for id,obj in PuzzleManager(rooms[name]).objects.items():
            if id not in snapshot and obj.data.get('optional'):
                snapshot[id]=dict(pos=list(obj.pos),active=False,remaining=0,unlocked=False,latched=False)
    # Existing expeditions that earned or revealed the key retain that earned access.
    earned=result.get('boss_key',False) or any(s.get('boss_key',{}).get('chest_phase') in ('spawning','available','opened') for name,s in result['snapshots'].items() if name=='r6')
    if earned:
        result['flags']=sorted(set(result.get('flags',[]))|{'royal_resonance'})
        result['checkpoint']['flags']=sorted(set(result['checkpoint'].get('flags',[]))|{'royal_resonance'})
    result['content_revision']='4.4'
    return result
