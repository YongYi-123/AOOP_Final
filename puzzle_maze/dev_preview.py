"""Disposable previews of production scenes. Never bind a profile or write a save."""
import pygame
from puzzle_maze.game import Game,GameScene
from puzzle_maze.remaster import RemasteredSession
from puzzle_maze.studio_layout import ENTRY,approach
TARGETS=('grey-pixel','developer-room','miao-entrance','developer-diaries','kevin-notes')
class PreviewGame(Game):
    def __init__(self,target='grey-pixel',headless=False):
        super().__init__(headless=headless,campaign='4.5',persistent=False)
        self.note_index=0;self.preview_target=target;self.restart_preview(target)
    def restart_preview(self,target=None):
        if target is not None:self.preview_target=target
        self.last_maze_frame=None;self.inspection_intro=None
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
            arrival=ENTRY if self.preview_target=='miao-entrance' else approach(self.session.rooms.rooms['r28'],next(tuple(o['pos']) for o in self.session.rooms.rooms['r28']['objects'] if o['id']=='dev_001'))[0] if self.preview_target=='developer-diaries' else (12,8)
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
        # F8/F9 are direct developer page jumps; normal E uses the full introduction.
        self.inspection_intro=None
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
