"""Golden Age dialogue behavior and safe migration into the warehouse layout."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock
import pygame
from puzzle_maze.dev_preview import PreviewGame
from puzzle_maze.lab_scene import LabEntrance,LINES

class WarehouseTests(TestCase):
    def test_top_dialogue_types_with_shared_sound_and_confirm_completes_before_advancing(self):
        play=Mock();scene=LabEntrance(play_sound=play)
        scene.update(9.8);play.assert_not_called()
        scene.update(.3)
        self.assertGreater(scene.dialogue.shown,0)
        self.assertLess(scene.dialogue.shown,len(scene.dialogue.line.text))
        play.assert_called_with('vend_select')
        scene.advance();self.assertEqual(scene.line,0);self.assertTrue(scene.dialogue.done_typing)
        play.reset_mock();scene.update(.3);play.assert_not_called()
        scene.advance();self.assertEqual(scene.line,1);self.assertEqual(scene.dialogue.shown,0)
        self.assertTrue(scene.dialogue.top);self.assertEqual(scene.dialogue.box.top,8)
        for index in range(1,len(LINES)):
            scene.update(3);scene.advance()
        self.assertTrue(scene.done)

    def test_native_dialogue_rows_and_box_stay_inside_screen(self):
        g=PreviewGame('miao-entrance',True);g.update(.01);g.update(12)
        scene=g.lab_entrance
        for index in range(len(LINES)):
            scene.dialogue.index=index;scene.dialogue.shown=1000
            self.assertEqual(' '.join(scene.dialogue._rows()),scene.dialogue.line.text)
            self.assertTrue(pygame.Rect(0,0,320,240).contains(scene.dialogue.box))
            g.draw(0)

    def test_revision_five_player_in_moved_server_is_relocated_and_backup_preserved(self):
        g=PreviewGame('developer-room',True);s=g.session
        with TemporaryDirectory() as directory:
            path=Path(directory)/'save.json';s.save(path);data=json.loads(path.read_text())
            data['extension']['remaster']['studio_revision']=5
            data['player']=[14,10];data['checkpoint']['pos']=[14,10]
            path.write_text(json.dumps(data));before=path.read_bytes()
            restored=type(s).load(path)
            self.assertTrue(restored.can_enter(restored.player.x,restored.player.y))
            self.assertNotEqual([restored.player.x,restored.player.y],[14,10])
            self.assertEqual(restored.grey_pixel,s.grey_pixel);self.assertEqual(restored.lore,s.lore)
            restored.save(path);backup=path.with_name(path.name+'.pre-studio-v6')
            self.assertEqual(backup.read_bytes(),before)
            restored.save(path);self.assertEqual(backup.read_bytes(),before)
