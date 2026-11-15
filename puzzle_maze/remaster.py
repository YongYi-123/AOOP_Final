"""v4.5 campaign; compose the proven 4.4 adventure without altering archived data."""
from puzzle_maze.advanced_dungeon import AdvancedDungeonSession
from puzzle_maze.rooms import load_rooms,MAP_PATH
from puzzle_maze.layout45 import upgrade

class RemasteredSession(AdvancedDungeonSession):
    def __init__(self,rooms=None):
        super().__init__(upgrade(rooms or load_rooms(MAP_PATH.with_name('dungeon_v4.json'))))

    def prepare_loaded_save(self,data):
        if data.get('content_revision')=='4.5': return data
        result=super().prepare_loaded_save(data)
        result['content_revision']='4.5'
        self.migration_notice='Progress restored in the two-floor 4.5 remaster.'
        return result
