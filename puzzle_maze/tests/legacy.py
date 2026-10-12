"""Version-one fixtures keep original engine regression tests independent of campaign design."""
from pathlib import Path
from puzzle_maze.rooms import load_rooms as load
from puzzle_maze.session import GameSession as Session

def load_rooms():
    return load(Path(__file__).parent/'fixtures/dungeon_v1.json')

class GameSession(Session):
    def __init__(self):
        super().__init__(rooms=load_rooms())
