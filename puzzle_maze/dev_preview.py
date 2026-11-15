"""Disposable previews of production scenes. Never bind a profile or write a save."""
import pygame
from puzzle_maze.game import Game,GameScene
from puzzle_maze.remaster import RemasteredSession
from puzzle_maze.pixel_font import render
from puzzle_maze.studio_layout import ENTRY,approach
TARGETS=('grey-pixel','developer-room','miao-entrance','developer-diaries','kevin-notes')
class PreviewGame(Game):
    def __init__(self,target='grey-pixel',headless=False):
        super().__init__(headless=headless,campaign='4.5',persistent=False)
        self.note_index=0;self.preview_target=target;self.restart_preview(target)
    def restart_preview(self,target=None):
        if target is not None:self.preview_target=target
        self.session=RemasteredSession();self.scene=GameScene.PLAY;self.running=True
        self.fade=0;self.cooldown=0;self.toast_time=0;self.autosave=0
        self.renderer.particles.clear();self.renderer.lab_effect=None
        self.session.inventory.abilities.add('map')
        if self.preview_target=='grey-pixel':
            self.session.enter('r24',(21,7))
            seam=self.session.puzzles.objects['debug_seam'];seam.state.active=True
            # Let the real reveal state machine spawn the item, then collect it through E.
            for _ in range(90):self.session.tick(1/60)
            self.session.player.x,self.session.player.y=23,8
            self.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e))
        else:
            self.session.grey_pixel=True;self.session.observe_secret()
            self.session.lab_memory_seen=self.preview_target!='miao-entrance'
            arrival=ENTRY if self.preview_target=='miao-entrance' else approach(self.session.rooms.rooms['r28'],(3,4))[0] if self.preview_target=='developer-diaries' else (12,8)
            self.session.enter('r28',arrival)
        self.visual=[float(self.session.player.x),float(self.session.player.y)]
        self.last_solved=self.session.puzzles.solved
        if self.preview_target=='kevin-notes':self.inspect_key('studio_todo')
    def finish_discovery(self):
        super().finish_discovery()
        self.session.enter('r28',ENTRY);self.visual=list(map(float,ENTRY));self.fade=0
    def inspect_key(self,key):
        if self.session.rooms.current!='r28':self.restart_preview('developer-room')
        self.session.lab_memory_seen=True;self.scene=GameScene.PLAY;self.reading_page=0
        obj=self.session.puzzles.objects[key]
        pos,facing=approach(self.session.rooms.data,obj.pos)
        self.session.player.x,self.session.player.y=pos;self.session.player.facing=facing
        self.visual=list(map(float,pos))
        super().event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e))
    def next_note(self):
        from puzzle_maze.developer_diaries import DIARIES
        from puzzle_maze.studio_notes import NOTES
        keys=tuple(DIARIES)+tuple(NOTES)
        key=keys[self.note_index%len(keys)];self.note_index+=1;self.inspect_key(key)
    def event(self,event):
        if event.type==pygame.KEYDOWN:
            if getattr(event,'repeat',False) and event.key in (pygame.K_r,pygame.K_F5,pygame.K_F6,pygame.K_F7,pygame.K_F8,pygame.K_F9):return
            if event.key==pygame.K_ESCAPE:self.running=False;return
            if event.key==pygame.K_r:self.restart_preview();return
            if event.key==pygame.K_F5:self.restart_preview('grey-pixel');return
            if event.key==pygame.K_F6:self.restart_preview('developer-room');return
            if event.key==pygame.K_F9:self.inspect_key('studio_todo');return
            if event.key==pygame.K_F8:self.next_note();return
            if event.key==pygame.K_F7:self.restart_preview('miao-entrance');return
        super().event(event)
    def draw(self,dt,target=None):
        super().draw(dt,target)
        output=target if target is not None else self.screen
        if self.session.rooms.current=='r28' and self.scene in (GameScene.MEMORY,GameScene.SCROLL):return
        guide=pygame.Surface((320,16));guide.fill((22,30,43))
        for i,line in enumerate(('PREVIEW / R REPLAY / F5 ALL / F6 ROOM','F7 MEMORY / F8 NOTES / F9 TODO / ESC EXIT')):
            guide.blit(render(line,8,(222,205,161)),(4,i*8))
        scale=min(output.get_width()/320,output.get_height()/240)
        scale=int(scale) if scale>=1 else scale
        width=max(1,int(320*scale));height=max(1,int(16*scale))
        origin=((output.get_width()-width)//2,(output.get_height()-int(240*scale))//2)
        if self.session.rooms.current=='r28':origin=(origin[0],origin[1]+int(208*scale))
        output.blit(pygame.transform.scale(guide,(width,height)),origin)
        if target is None:pygame.display.flip()
