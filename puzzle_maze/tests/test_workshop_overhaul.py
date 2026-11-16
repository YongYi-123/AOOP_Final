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
from puzzle_maze.workshop_inspection import DOC_ROWS,DOC_LINE_HEIGHT


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
                    inspection=g.workshop_inspection;inspection.page=page
                    max_scroll=max(0,len(inspection.pages[page])-DOC_ROWS)
                    offsets=sorted({0,max_scroll,*range(0,max_scroll+1,DOC_ROWS-2)})
                    for offset in offsets:
                        inspection.scroll=offset;g.draw(0,target)
                        rects=g.renderer.ui.rects
                        self.assertTrue(all(target.get_rect().contains(r) for r in rects),(content,page,size,offset))
                        self.assertFalse(any(a.colliderect(b) for i,a in enumerate(rects) for b in rects[i+1:]),(content,page,size,offset))
                        commands=g.renderer.ui.commands
                        counter=next(c for c in commands if c[0]==f'{page+1}/{len(doc.pages)}')
                        self.assertGreaterEqual(counter[1],274)
                        body=[i for i,c in enumerate(commands) if c[1]==23 and 42<=c[2]<218]
                        self.assertTrue(all(commands[b][2]-commands[a][2]>=DOC_LINE_HEIGHT for a,b in zip(body,body[1:])))
                        scale=min(size[0]/320,size[1]/240)
                        self.assertTrue(all(rects[b].top-rects[a].bottom>=3*int(scale) for a,b in zip(body,body[1:])))
            finish(g)

    def test_scroll_controls_preserve_page_response_and_counter_then_escape_restores_play(self):
        g=PreviewGame('developer-room',True);g.inspect_key('note');observe(g)
        inspection=g.workshop_inspection;count=g.session.inspection_counts['note']
        self.assertGreater(len(inspection.pages[0]),DOC_ROWS)
        for _ in range(50):key(g,pygame.K_DOWN)
        self.assertEqual(inspection.scroll,len(inspection.pages[0])-DOC_ROWS)
        self.assertEqual(inspection.page,0)
        g.event(pygame.event.Event(pygame.MOUSEWHEEL,y=100,x=0))
        self.assertEqual(inspection.scroll,0);self.assertEqual(inspection.page,0)
        for _ in range(10):key(g,pygame.K_UP)
        self.assertEqual(inspection.scroll,0)
        self.assertEqual(g.session.inspection_counts['note'],count)
        key(g,pygame.K_ESCAPE)
        self.assertEqual(g.scene,GameScene.PLAY);self.assertTrue(g.running)

    def test_normal_response_windows_use_the_same_readable_line_spacing(self):
        g=PreviewGame('developer-room',True)
        for content in RESPONSES:
            obj=next(o for o in g.session.puzzles.objects.values() if o.data['content_id']==content)
            for _ in range(3):
                g.inspect_key(obj.id);inspection=g.workshop_inspection;observe(g)
                if inspection.closed:continue
                if inspection.document:finish(g);continue
                for page in range(len(inspection.pages)):
                    inspection.page=page
                    for size in ((640,480),(960,720),(1280,720)):
                        target=pygame.Surface(size);g.draw(0,target);rects=g.renderer.ui.rects
                        self.assertTrue(all(target.get_rect().contains(r) for r in rects))
                        self.assertFalse(any(a.colliderect(b) for i,a in enumerate(rects) for b in rects[i+1:]))
                        rows=[c[2] for c in g.renderer.ui.commands if c[1]==27]
                        self.assertTrue(all(b-a>=11 for a,b in zip(rows,rows[1:])))
                finish(g)

    def test_visual_reactions_are_real_and_do_not_change_collision_health_or_rewards(self):
        g=PreviewGame('developer-room',True);r=g.renderer;s=g.session
        r.time=1.;r.lab_effect=None;r.world(s,g.visual,0)
        baseline=pygame.image.tobytes(r.surface,'RGB')
        before=(s.player.hp,s.inventory.coins,list(s.rooms.data['solid_footprints']))
        for content in ('work_crt','work_back','work_frozen','work_space','lab_terminal','store_aoop','power_cabinet','work_prototype','studio_cushion','repair_log'):
            changed=False
            for age in (.1,.2,.3,.4):
                r.lab_effect=(content,1.-age);r.world(s,g.visual,0)
                changed|=pygame.image.tobytes(r.surface,'RGB')!=baseline
            self.assertTrue(changed,content)
        self.assertEqual(before,(s.player.hp,s.inventory.coins,list(s.rooms.data['solid_footprints'])))

    def test_revision_eight_retired_papers_migrate_without_weakening_current_save_validation(self):
        g=PreviewGame('developer-room',True);s=g.session;s.lore.add('dev_001');s.inventory.coins=23
        with TemporaryDirectory() as directory:
            path=Path(directory)/'legacy.json';s.save(path);data=json.loads(path.read_text())
            data['extension']['remaster']['studio_revision']=8
            data['extension']['remaster'].pop('inspection_counts')
            data['extension']['remaster'].pop('prototype_recording_seen')
            data['player']=[10,5];data['checkpoint']['pos']=[10,5]
            for snapshot in (data['snapshots']['r28'],data['checkpoint']['objects']):
                snapshot['dev_001']=dict(snapshot['photo'],pos=[3,6])
                for key in ('work_space','power_cabinet','repair_log','project_file'):snapshot.pop(key)
            path.write_text(json.dumps(data));before=path.read_bytes();loaded=type(s).load(path)
            self.assertEqual(loaded.rooms.current,'r28');self.assertEqual(loaded.inventory.coins,23)
            self.assertIn('dev_001',loaded.lore);self.assertNotIn('dev_001',loaded.puzzles.objects)
            self.assertTrue(loaded.can_enter(loaded.player.x,loaded.player.y))
            self.assertIn('work_space',loaded.puzzles.objects);self.assertEqual(loaded.inspection_counts,{})
            loaded.save(path);self.assertEqual(path.with_name(path.name+'.pre-studio-v9').read_bytes(),before)
            current=json.loads(path.read_text());current['snapshots']['r28']['foreign_object']=current['snapshots']['r28']['photo']
            path.write_text(json.dumps(current));self.assertEqual(type(s).load(path).rooms.current,'r1')

    def test_short_details_are_typed_speech_without_a_note_and_all_note_backgrounds_are_yellowed(self):
        from puzzle_maze.workshop_content import WRITTEN_RECORDS
        g=PreviewGame('developer-room',True);g.audio=Mock()
        for object_id in ('studio_food','gpu','keyboard','lab_duck','store_tools','store_cables','studio_cushion'):
            g.inspect_key(object_id);inspection=g.workshop_inspection
            self.assertTrue(inspection.speech_only,object_id)
            self.assertEqual(inspection.dialogue.line.speaker,'PLAYER')
            self.assertEqual(inspection.dialogue.shown,0)
            g.update(.1);self.assertGreater(inspection.dialogue.shown,0)
            g.audio.play.assert_called_with('vend_select')
            g.draw(0);self.assertNotIn('NOTE',[c[0] for c in g.renderer.ui.commands])
            finish(g);self.assertEqual(g.scene,GameScene.PLAY)
        for content in DOCUMENTS:
            obj=next(o for o in g.session.puzzles.objects.values() if o.data['content_id']==content)
            g.inspect_key(obj.id);observe(g);g.draw(0)
            red,green,blue,_=g.renderer.surface.get_at((30,219))
            self.assertGreater(red,green,content);self.assertGreater(green,blue,content)
            finish(g)
        for content,index in WRITTEN_RECORDS:
            obj=next(o for o in g.session.puzzles.objects.values() if o.data['content_id']==content)
            from puzzle_maze.workshop_inspection import WorkshopInspection
            inspection=WorkshopInspection(obj.id,content,index)
            self.assertFalse(inspection.speech_only)
            for _ in range(20):
                if inspection.dialogue is None:break
                inspection.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
            g.renderer.surface.fill((0,0,0))
            inspection.draw(g.renderer,g.session.rooms.data)
            obj_y=obj.data['pos'][1]
            sample=(20,216 if obj_y<=7 else 140)
            red,green,blue,_=g.renderer.surface.get_at(sample)
            self.assertGreater(red,green,(content,index));self.assertGreater(green,blue,(content,index))

    def test_recording_must_complete_before_diagnostics_and_does_not_grant_any_reward(self):
        g=PreviewGame('developer-room',True);s=g.session
        before=(set(s.inventory.flags),s.inventory.coins,set(s.lore),s.grey_pixel)
        g.inspect_key('work_prototype');self.assertTrue(g.workshop_inspection.recording)
        key(g,pygame.K_ESCAPE)
        self.assertFalse(s.prototype_recording_seen)
        g.inspect_key('work_prototype');self.assertTrue(g.workshop_inspection.recording)
        finish(g);self.assertTrue(s.prototype_recording_seen)
        self.assertEqual(s.inspection_counts['work_prototype'],1)
        g.inspect_key('work_prototype');self.assertEqual(g.workshop_inspection.response.title,'SYSTEM DIAGNOSTICS')
        self.assertFalse(g.workshop_inspection.recording)
        self.assertEqual(g.workshop_inspection.dialogue.line.speaker,'PLAYER');finish(g)
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
