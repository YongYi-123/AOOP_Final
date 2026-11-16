"""One inspection, many pages. Page turns never select another response."""
import textwrap
import pygame
from puzzle_maze.workshop_content import RESPONSES,RECORDING,ascii_text,paginate,response_for

DOC_ROWS=16
DOC_LINE_HEIGHT=11
_PAPERS={}

def document_paper(style):
    if style in _PAPERS:return _PAPERS[style]
    paper=pygame.Surface((304,228));r=pygame.draw
    for y in range(228):
        edge=min(y,227-y,12)
        color=(222+edge,204+edge,158+edge) if style in ('repair','digital') else (219+edge,190+edge,138+edge)
        r.line(paper,color,(0,y),(303,y))
    r.rect(paper,(172,143,101),(0,0,304,228),1)
    r.line(paper,(198,170,125),(151,3),(150,224))
    r.line(paper,(238,214,170),(152,3),(151,224))
    # Quiet margins, not heavy rules behind the characters.
    for i in range(36):
        x=(i*71)%304;y=(i*43)%228
        if x<9 or x>296:paper.fill((185,156,111),(x,y,1,1))
    r.polygon(paper,(188,158,110),[(292,0),(303,0),(303,11)])
    r.line(paper,(245,224,182),(292,0),(303,11))
    _PAPERS[style]=paper;return paper

class WorkshopInspection:
    def __init__(self,object_id,content,index,recording=False,play_sound=None):
        self.object_id=object_id;self.content=content;self.index=index
        self.response=response_for(content,index);self.pages=paginate(self.response);self.page=0
        self.time=0.;self.closed=False;self.recording=recording;self.recording_completed=False
        self.dialogue=None;self.scroll=0;self.turn_time=0.;self.speech_only=False
        from puzzle_maze.workshop_documents import DOCUMENTS,page_lines
        self.document=DOCUMENTS.get(content)
        if self.document:
            self.pages=tuple(page_lines(page) for page in self.document.pages)
            self._make_dialogue(self.document.observations[self.index%3],play_sound)
        elif not recording:
            from puzzle_maze.workshop_content import WRITTEN_RECORDS,RECORD_OBSERVATIONS,written_response
            if (content,index) in WRITTEN_RECORDS:
                self.response=written_response(content,index);self.pages=paginate(self.response)
                self._make_dialogue(RECORD_OBSERVATIONS[(content,index)],play_sound)
            else:
                self.speech_only=True
                speaker='MIAO MEOW' if content=='miao_memory' else 'PLAYER'
                from puzzle_maze.workshop_content import SPOKEN_DETAILS
                texts=SPOKEN_DETAILS.get(content,self.response.paragraphs)
                self._make_dialogue(texts,play_sound,speaker)
        if recording:
            from puzzle_maze.studio_dialogue import make_dialogue
            lines=[(ascii_text(speaker),part,'gentle') for speaker,text in RECORDING
                   for part in textwrap.wrap(ascii_text(text),70,break_long_words=False,break_on_hyphens=False)]
            self.dialogue=make_dialogue(lines,play_sound)

    def _make_dialogue(self,texts,play_sound,speaker='PLAYER'):
        from types import SimpleNamespace
        from puzzle_maze.studio_dialogue import make_dialogue
        import sys
        from pathlib import Path
        host=str(Path(__file__).resolve().parents[1]/'arcade_lobby')
        if host not in sys.path:sys.path.append(host)
        from player import PlayerLook
        look=PlayerLook('expedition',shirt=(67,158,163),shirt_dark=(49,112,127),
                        beanie=(85,89,103),beanie_dark=(57,65,79),pom=(94,98,111))
        lines=[(speaker,part,'normal') for text in texts
               for part in textwrap.wrap(ascii_text(text),70,break_long_words=False,break_on_hyphens=False)]
        context={'players':[SimpleNamespace(look=look)]} if speaker=='PLAYER' else None
        self.dialogue=make_dialogue(lines,play_sound,context)

    def scroll_by(self,amount):
        if self.document and self.dialogue is None:
            self.scroll=max(0,min(max(0,len(self.pages[self.page])-DOC_ROWS),self.scroll+amount))

    def change_page(self,delta):
        target=max(0,min(len(self.pages)-1,self.page+delta))
        if target!=self.page:self.page=target;self.scroll=0;self.turn_time=.1

    def update(self,dt):
        before=self.time;self.time+=max(0,dt)
        self.turn_time=max(0,self.turn_time-max(0,dt))
        if self.dialogue:self.dialogue.update(max(0,self.time-max(before,.7)) if self.recording else max(0,dt))

    def handle_event(self,event):
        if event.type!=pygame.KEYDOWN or getattr(event,'repeat',False):return
        key=event.key
        if key==pygame.K_ESCAPE:self.closed=True;return
        if self.dialogue:
            if self.recording and self.time<.7:return
            self.dialogue.handle_event(event)
            if self.dialogue.closed:
                if self.recording:self.closed=True;self.recording_completed=True
                elif self.speech_only:self.closed=True
                else:self.dialogue=None
            return
        if key in (pygame.K_e,pygame.K_RETURN,pygame.K_SPACE):
            if self.document and self.scroll<max(0,len(self.pages[self.page])-DOC_ROWS):
                self.scroll=min(max(0,len(self.pages[self.page])-DOC_ROWS),self.scroll+DOC_ROWS-2)
            elif self.page<len(self.pages)-1:self.change_page(1)
            else:self.closed=True
        elif key==pygame.K_RIGHT:self.change_page(1)
        elif key==pygame.K_LEFT:self.change_page(-1)
        elif self.document and key==pygame.K_DOWN:self.scroll_by(1)
        elif self.document and key==pygame.K_UP:self.scroll_by(-1)

    def draw(self,renderer,room):
        s=renderer.surface;r=pygame.draw;renderer.ui.clear()
        if self.dialogue:
            if not self.recording:
                obj=next(o for o in room['objects'] if o['id']==self.object_id)
                bottom=obj['pos'][1]<=7
                self.dialogue.box=pygame.Rect(24,158 if bottom else 8,272,50)
                self.dialogue.draw(s)
                if self.speech_only:renderer.centered_text(ascii_text(self.response.title),214 if bottom else 207,(165,188,176),small=True)
                renderer.centered_text('E/ENTER: Continue / ESC: Close',228 if bottom else 222,(151,171,176),small=True)
                return
            if self.time<.7:
                veil=pygame.Surface((320,240),pygame.SRCALPHA)
                veil.fill((7,20,27,int(160*(1-self.time/.7))));s.blit(veil,(0,0))
                for y in range(0,240,4):r.line(s,(25,62,68),(0,y),(319,y))
            else:self.dialogue.draw(s)
            renderer.centered_text('ORIGINAL ARCADE CONTROL SYSTEM',207,(132,192,184),small=True)
            renderer.centered_text('E/ENTER: Continue / ESC: Leave',222,(151,171,176),small=True)
            return
        if self.document:
            self.draw_document(renderer)
            return
        obj=next(o for o in room['objects'] if o['id']==self.object_id)
        y=88 if obj['pos'][1]<=7 else 12
        box=pygame.Rect(12,y,296,140);style=self.response.style
        r.rect(s,(39,34,29),box.move(1,3))
        s.blit(pygame.transform.scale(document_paper('repair' if style!='paper' else 'notebook'),box.size),box.topleft)
        ink=(92,72,48);accent=(115,80,47)
        if style in ('board','blueprint','screen'):
            accent=(68,104,94);r.rect(s,(114,135,112),box,1)
        renderer.text(ascii_text(self.response.title),24,y+7,accent,max_width=272)
        for i,line in enumerate(self.pages[self.page]):
            renderer.text(line,27,y+29+i*11,ink,max_width=266,small=True)
        footer='E/ENTER: Continue' if self.page<len(self.pages)-1 else 'E/ENTER: Close'
        renderer.text(footer,26,y+124,accent,max_width=210,small=True)
        renderer.text(f'{self.page+1}/{len(self.pages)}',274,y+124,accent,max_width=24,small=True)

    def draw_document(self,renderer):
        s=renderer.surface;r=pygame.draw;doc=self.document;box=pygame.Rect(8,6,304,228)
        r.rect(s,(40,35,30),box.move(1,2))
        s.blit(document_paper(doc.style),box.topleft)
        ink=(83,67,48);accent=(103,73,45)
        if doc.style=='digital':
            accent=(57,99,93)
            r.rect(s,(100,132,116),box,1)
            r.line(s,(100,132,116),(22,25),(296,25))
            for x in (13,17,21):s.fill((104,135,116),(x,9,2,2))
        elif doc.style=='repair':
            r.line(s,(133,151,124),(22,25),(296,25))
            for y in range(49,218,DOC_LINE_HEIGHT):r.line(s,(208,211,181),(22,y),(297,y))
        elif doc.style=='checklist':
            r.line(s,(178,123,95),(19,39),(19,217))
            r.rect(s,(86,94,84),(132,6,56,5));r.line(s,(169,175,143),(140,7),(180,7))
        elif doc.style=='notebook':
            for y in range(20,221,18):r.circle(s,(122,99,68),(12,y),1)
        renderer.text(doc.title,22,13,accent,max_width=250)
        renderer.text('NOTE',278,13,accent,max_width=25,small=True)
        renderer.text(ascii_text(doc.pages[self.page].heading),23,30,accent,max_width=274,small=True)
        lines=self.pages[self.page]
        for i,line in enumerate(lines[self.scroll:self.scroll+DOC_ROWS]):
            renderer.text(line,23,42+i*DOC_LINE_HEIGHT,ink,max_width=274,small=True)
        more=self.scroll<max(0,len(lines)-DOC_ROWS)
        footer='E/ENTER: Read more' if more else 'E/ENTER: Continue' if self.page<len(self.pages)-1 else 'E/ENTER: Close'
        renderer.text(footer+(' / UP/DOWN: Scroll' if len(lines)>DOC_ROWS else ' / LEFT/RIGHT: Page'),23,223,accent,max_width=236,small=True)
        renderer.text(f'{self.page+1}/{len(self.pages)}',281,223,accent,max_width=24,small=True)
        if len(lines)>DOC_ROWS:
            height=max(10,176*DOC_ROWS//len(lines));offset=round((176-height)*self.scroll/max(1,len(lines)-DOC_ROWS))
            r.rect(s,accent,(306,42+offset,2,height))
        if self.turn_time>0:
            r.line(s,accent,(310,10),(310,230))
