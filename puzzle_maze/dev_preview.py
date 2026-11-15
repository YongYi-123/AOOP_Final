"""Disposable previews of production scenes. Never bind a profile or write a save."""
import pygame
from puzzle_maze.game import Game,GameScene
from puzzle_maze.remaster import RemasteredSession
from puzzle_maze.pixel_font import render
TARGETS=('grey-pixel','developer-room','miao-entrance','developer-diaries')
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
            arrival=(2,7) if self.preview_target=='miao-entrance' else (3,11) if self.preview_target=='developer-diaries' else (12,8)
            self.session.enter('r28',arrival)
        self.visual=[float(self.session.player.x),float(self.session.player.y)]
        self.last_solved=self.session.puzzles.solved
    def finish_discovery(self):
        super().finish_discovery()
        self.session.enter('r28',(2,7));self.visual=[2.,7.];self.fade=0
    def next_note(self):
        from puzzle_maze.developer_diaries import DIARIES
        if self.session.rooms.current!='r28':self.restart_preview('developer-diaries')
        key=tuple(DIARIES)[self.note_index%len(DIARIES)];self.note_index+=1
        self.session.lab_memory_seen=True;self.scene=GameScene.PLAY
        obj=self.session.puzzles.objects[key]
        self.session.player.x,self.session.player.y=obj.x,obj.y+1
        self.session.player.facing=(0,-1);self.visual=[float(obj.x),float(obj.y+1)]
        super().event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e))
    def event(self,event):
        if event.type==pygame.KEYDOWN:
            if getattr(event,'repeat',False) and event.key in (pygame.K_r,pygame.K_F5,pygame.K_F6,pygame.K_F7,pygame.K_F8):return
            if event.key==pygame.K_ESCAPE:self.running=False;return
            if event.key==pygame.K_r:self.restart_preview();return
            if event.key==pygame.K_F5:self.restart_preview('grey-pixel');return
            if event.key==pygame.K_F6:self.restart_preview('developer-room');return
            if event.key==pygame.K_F8:self.next_note();return
            if event.key==pygame.K_F7:self.restart_preview('miao-entrance');return
        super().event(event)
    def draw(self,dt,target=None):
        super().draw(dt,target)
        output=target if target is not None else self.screen
        guide=pygame.Surface((320,16));guide.fill((22,30,43))
        for i,line in enumerate(('PREVIEW / R REPLAY / F5 ALL / F6 ROOM','F7 MIAO / F8 NOTES / E READ / ESC EXIT')):
            guide.blit(render(line,8,(222,205,161)),(4,i*8))
        scale=min(output.get_width()/320,output.get_height()/240)
        scale=max(1,int(scale))
        output.blit(pygame.transform.scale(guide,(320*scale,16*scale)),((output.get_width()-320*scale)//2,0))
        if target is None:pygame.display.flip()
