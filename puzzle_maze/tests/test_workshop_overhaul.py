"""Authored variations, fixed logical document pages, recording lifecycle and layout."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from collections import defaultdict
from unittest import TestCase
from unittest.mock import Mock
import pygame
from puzzle_maze.dev_preview import PreviewGame
from puzzle_maze.game import GameScene
from puzzle_maze.studio_layout import approach,FURNITURE
from puzzle_maze.workshop_content import RESPONSES,RECORDING,ascii_text,paginate
from puzzle_maze.workshop_documents import DOCUMENTS,page_lines


def key(g,k=pygame.K_RETURN,repeat=False):g.event(pygame.event.Event(pygame.KEYDOWN,key=k,repeat=repeat))

def observe(g):
    g.update(.8)
    for _ in range(100):
        inspection=g.workshop_inspection
        if inspection is None or inspection.dialogue is None:return
        key(g)
    raise AssertionError('Observation or recording did not complete')

def finish(g):
    observe(g)
    for _ in range(50):
        if g.scene!=GameScene.SCROLL:return
        key(g)
    raise AssertionError('Inspection did not close')

class WorkshopOverhaulTests(TestCase):
    def test_all_authored_variations_cycle_without_repeating_and_turns_do_not_increment(self):
        g=PreviewGame('developer-room',True)
        for content,responses in RESPONSES.items():
            obj=next(o for o in g.session.puzzles.objects.values() if o.data['content_id']==content)
            indices=[]
            for expected in (0,1,2,0):
                g.inspect_key(obj.id);inspection=g.workshop_inspection
                self.assertEqual(inspection.index,expected,content);indices.append(inspection.index)
                count=g.session.inspection_counts.get(obj.id,0)
                if inspection.recording:
                    self.assertEqual(expected,0)
                else:
                    observe(g)
                    for _ in range(8):key(g,pygame.K_RIGHT)
                    self.assertEqual(g.session.inspection_counts[obj.id],count)
                finish(g)
            self.assertTrue(all(a!=b for a,b in zip(indices,indices[1:])))

    def test_exact_authored_titles_and_requested_paragraphs_are_not_replaced_with_generic_text(self):
        self.assertEqual(RESPONSES['store_aoop'][1].title,'PROJECT: GRAND THEFT ARCADE')
        self.assertIn('The prototype featured three streets, two vehicles, and one extremely judgmental pigeon.',RESPONSES['store_aoop'][1].paragraphs)
        self.assertIn('The test driver reached a maximum speed of three pixels per second.',RESPONSES['work_crt'][1].paragraphs)
        self.assertIn("'The enemies are fine. The developer is the final boss.'",RESPONSES['work_back'][2].paragraphs)
        self.assertIn('GPU: VERY CONCERNED',RESPONSES['work_space'][2].paragraphs)
        for responses in RESPONSES.values():
            for response in responses:
                displayed=' '.join(' '.join(page) for page in paginate(response))
                self.assertEqual(' '.join(displayed.split()),' '.join(ascii_text(' '.join(response.paragraphs)).split()))

    def test_document_counts_exact_content_and_all_logical_pages(self):
        expected={'kevin_note':7,'repair_log':4,'studio_todo':3,'project_file':4}
        for content,count in expected.items():self.assertEqual(len(DOCUMENTS[content].pages),count)
        self.assertIn('The new version was 23% slower.',DOCUMENTS['kevin_note'].pages[1].paragraphs)
        self.assertIn('PleaseDoNotAddAnotherBoss.',DOCUMENTS['kevin_note'].pages[2].paragraphs)
        self.assertIn('Current development budget: One sandwich.',DOCUMENTS['kevin_note'].pages[3].paragraphs)
        self.assertIn('I should remember this night.',DOCUMENTS['kevin_note'].pages[5].paragraphs)
        self.assertIn('And maybe get some sleep.',DOCUMENTS['kevin_note'].pages[6].paragraphs)
        self.assertIn('Noise increased by approximately 900%.',DOCUMENTS['repair_log'].pages[2].paragraphs)
        self.assertIn('please_work()',DOCUMENTS['project_file'].pages[1].paragraphs)
        for doc in DOCUMENTS.values():
            for page in doc.pages:
                self.assertEqual(' '.join(' '.join(page_lines(page)).split()),' '.join(ascii_text(' '.join(page.paragraphs)).split()))

    def test_observation_note_boundaries_close_and_movement_lock(self):
        g=PreviewGame('developer-room',True);s=g.session
        obj=s.puzzles.objects['note'];pos,facing=approach(s.rooms.data,obj.pos)
        s.player.x,s.player.y=pos;s.player.facing=facing;g.visual=list(map(float,pos));g.audio=Mock()
        key(g,pygame.K_e);inspection=g.workshop_inspection
        self.assertEqual(inspection.dialogue.line.speaker,'PLAYER')
        self.assertEqual(inspection.dialogue.line.text,'This looks like an abandoned experiment log.')
        count=s.inspection_counts['note'];g.update(.1);g.audio.play.assert_called_with('vend_select')
        shown=inspection.dialogue.shown;key(g,repeat=True);self.assertEqual(inspection.dialogue.shown,shown)
        key(g,pygame.K_RIGHT);self.assertEqual(inspection.page,0)
        g.update(.2,defaultdict(bool,{pygame.K_DOWN:True}));self.assertEqual((s.player.x,s.player.y),pos)
        observe(g);self.assertIsNone(inspection.dialogue)
        key(g,pygame.K_LEFT);self.assertEqual(inspection.page,0)
        for page in range(7):
            self.assertEqual(inspection.page,page);g.draw(.1)
            self.assertIn(f'{page+1}/7',[cmd[0] for cmd in g.renderer.ui.commands])
            if page<6:
                while inspection.page==page:key(g,pygame.K_e)
        key(g,pygame.K_RIGHT);self.assertEqual(inspection.page,6)
        self.assertEqual(s.inspection_counts['note'],count)
        finish(g);self.assertEqual(g.scene,GameScene.PLAY)
        before=(s.player.x,s.player.y)
        direction=next((dx,dy) for dx,dy in ((0,1),(1,0),(-1,0),(0,-1)) if s.can_enter(s.player.x+dx,s.player.y+dy))
        self.assertTrue(s.move(*direction));self.assertNotEqual((s.player.x,s.player.y),before)
        g.inspect_key('note');observe(g);self.assertEqual(g.workshop_inspection.page,0)

    def test_every_note_page_fits_window_letterbox_and_page_counter(self):
        g=PreviewGame('developer-room',True)
        for content,doc in DOCUMENTS.items():
            obj=next(o for o in g.session.puzzles.objects.values() if o.data['content_id']==content)
            g.inspect_key(obj.id);observe(g)
            for size in ((640,480),(960,720),(1280,720)):
                target=pygame.Surface(size)
                for page in range(len(doc.pages)):
                    g.workshop_inspection.page=page;g.workshop_inspection.scroll=0;g.draw(0,target)
                    rects=g.renderer.ui.rects
                    self.assertTrue(all(target.get_rect().contains(r) for r in rects),(content,page,size))
                    self.assertFalse(any(a.colliderect(b) for i,a in enumerate(rects) for b in rects[i+1:]),(content,page,size))
                    commands=g.renderer.ui.commands
                    counter=next(c for c in commands if c[0]==f'{page+1}/{len(doc.pages)}')
                    self.assertGreaterEqual(counter[1],274)
                    self.assertTrue(all('...' not in c[0] for c in commands))
            finish(g)

    def test_recording_must_complete_before_diagnostics_and_does_not_grant_any_reward(self):
        g=PreviewGame('developer-room',True);s=g.session
        before=(set(s.inventory.flags),s.inventory.coins,set(s.lore),s.grey_pixel)
        g.inspect_key('work_prototype');self.assertTrue(g.workshop_inspection.recording)
        # Escape aborts a real game modal (preview Escape intentionally exits the preview).
        from puzzle_maze.game import Game
        Game.event(g,pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE))
        self.assertFalse(s.prototype_recording_seen)
        g.inspect_key('work_prototype');self.assertTrue(g.workshop_inspection.recording)
        finish(g);self.assertTrue(s.prototype_recording_seen)
        self.assertEqual(s.inspection_counts['work_prototype'],1)
        g.inspect_key('work_prototype');self.assertEqual(g.workshop_inspection.response.title,'SYSTEM DIAGNOSTICS')
        self.assertIsNone(g.workshop_inspection.dialogue);finish(g)
        self.assertEqual((set(s.inventory.flags),s.inventory.coins,s.grey_pixel),(before[0],before[1],before[3]))
        text=' '.join(t for _,t in RECORDING)
        self.assertNotIn('MEMORY FRAGMENT RECOVERED',text)
        self.assertIn('LOCAL RECORDING RESTORED.',text)

    def test_counters_and_recording_persist_while_legacy_progress_remains_valid(self):
        g=PreviewGame('developer-room',True);s=g.session
        g.inspect_key('work_crt');finish(g);g.inspect_key('work_prototype');finish(g)
        s.lore.add('dev_001')
        with TemporaryDirectory() as directory:
            path=Path(directory)/'workshop.json';s.save(path);restored=type(s).load(path)
            self.assertEqual(restored.rooms.current,'r28');self.assertEqual(restored.inspection_counts,s.inspection_counts)
            self.assertTrue(restored.prototype_recording_seen);self.assertTrue(restored.grey_pixel)
            self.assertEqual(restored.lore,s.lore)
            self.assertEqual(restored.inspect_object('work_crt'),1)
            restored.enter('r24',(21,7));restored.enter('r28',(6,8))
            self.assertEqual(restored.inspect_object('work_crt'),2)

    def test_only_three_paper_objects_and_every_target_has_a_reachable_representation(self):
        from puzzle_maze.studio_interactions import PAPER_NOTES,object_anchor
        g=PreviewGame('developer-room',True);s=g.session
        self.assertEqual(set(PAPER_NOTES),{'work_crt','note','studio_todo'})
        self.assertEqual(len([f for f in FURNITURE if f.name.startswith('cab_')]),4)
        positions=[o.pos for o in s.puzzles.objects.values()]
        self.assertEqual(len(positions),len(set(positions)))
        for obj in s.puzzles.objects.values():
            pos,_=approach(s.rooms.data,obj.pos);self.assertTrue(s.can_enter(*pos),obj.id)
            x,y=object_anchor(s,obj.id);self.assertTrue(0<=x<320 and 0<=y<240,obj.id)
        self.assertTrue(s.can_enter(1,7))
