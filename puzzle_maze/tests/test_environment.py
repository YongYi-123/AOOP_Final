import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import copy
import unittest
import pygame
from puzzle_maze.environment import EnvironmentPainter
from puzzle_maze.rooms import load_rooms,validate_rooms
from puzzle_maze.core import TileMap
from puzzle_maze.themes import THEMES

class EnvironmentTests(unittest.TestCase):
    def tearDown(self):pygame.quit()

    def test_room_materials_are_distinct_and_cached(self):
        pygame.display.init();pygame.display.set_mode((320,240))
        painter=EnvironmentPainter()
        fingerprints={pygame.image.tobytes(painter.tile(name,'.',2),'RGB') for name in THEMES}
        self.assertEqual(len(fingerprints),len(THEMES))
        self.assertIs(painter.tile('library','.',2),painter.tile('library','.',2))
        self.assertIs(painter.glow('crystal'),painter.glow('crystal'))

    def test_decorations_do_not_change_collision_or_cover_puzzles(self):
        rooms=load_rooms();validate_rooms(rooms)
        for room in rooms.values():
            self.assertTrue(room['decorations'])
            original=TileMap(room['tiles'])
            stripped=copy.deepcopy(room);stripped['decorations']=[]
            for y,row in enumerate(room['tiles']):
                for x in range(len(row)):self.assertEqual(original.walkable(x,y),TileMap(stripped['tiles']).walkable(x,y))
            for d in room['decorations']:
                self.assertEqual(room['tiles'][d['pos'][1]][d['pos'][0]],'#')

    def test_bad_theme_or_floor_decoration_is_rejected(self):
        for kind in ('theme','decor'):
            rooms=load_rooms()
            if kind=='theme':rooms['r1']['theme']='unknown'
            else:rooms['r1']['decorations'][0]['pos']=rooms['r1']['spawn']
            with self.assertRaises(ValueError):validate_rooms(rooms)
