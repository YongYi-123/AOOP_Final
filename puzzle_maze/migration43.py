"""Add optional objects to valid 4.2 saves without moving earned progress."""
import copy
from puzzle_maze.puzzles import PuzzleManager

def migrate(data,rooms):
    if data.get('content_revision')=='4.3':return data
    result=copy.deepcopy(data)
    for name,snapshot in list(result['snapshots'].items())+[(result['room'],result['checkpoint']['objects'])]:
        manager=PuzzleManager(rooms[name])
        for id,obj in manager.objects.items():
            if id not in snapshot and obj.data.get('optional'):
                snapshot[id]=dict(pos=list(obj.pos),active=False,remaining=0,unlocked=False,latched=False)
    result['content_revision']='4.3'
    return result
