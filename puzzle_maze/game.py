"""Pygame scene state machine; no lobby or shared save dependencies."""
import argparse
import os
import textwrap
from enum import Enum, auto
import pygame
from puzzle_maze.session import GameSession, SAVE_PATH
from puzzle_maze.render import Renderer, GOLD, TEAL
from puzzle_maze.audio import AudioManager

class GameScene(Enum):
    MENU=auto()
    PLAY=auto()
    PAUSE=auto()
    HELP=auto()
    MAP=auto()
    VICTORY=auto()

class Game:
    def __init__(self,headless=False,embedded=False,audio=None):
        if headless:
            os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
        pygame.display.init();pygame.font.init()
        self.embedded=embedded
        self.screen=pygame.display.get_surface() if embedded else pygame.display.set_mode((960,720),pygame.RESIZABLE)
        if not embedded:pygame.display.set_caption('Puzzle Maze / The Prism Chambers')
        self.clock=pygame.time.Clock();self.renderer=Renderer();self.audio=audio if audio is not None else AudioManager()
        self.session=GameSession();self.scene=GameScene.MENU;self.previous=GameScene.MENU
        self.selection=0;self.running=True;self.cooldown=0
        self.visual=[float(self.session.player.x),float(self.session.player.y)]
        self.toast='';self.toast_time=0;self.fade=0;self.autosave=0
        self.last_solved=False

    def notify(self,message,seconds=3):
        self.toast=message;self.toast_time=seconds

    def save(self):
        try:self.session.save()
        except OSError:self.notify('Save unavailable: progress stays in memory')

    def start(self,continuing=False):
        self.session=GameSession.load() if continuing else GameSession()
        self.scene=GameScene.VICTORY if self.session.finished else GameScene.PLAY
        self.visual=[float(self.session.player.x),float(self.session.player.y)]
        self.fade=.5;self.cooldown=.2;self.last_solved=self.session.puzzles.solved
        self.notify(self.session.rooms.data['name'])

    def event(self,event):
        if event.type==pygame.QUIT:
            if self.scene!=GameScene.MENU:self.save()
            self.running=False;return
        if event.type!=pygame.KEYDOWN:return
        key=event.key
        if key==pygame.K_m:self.audio.toggle()
        if self.scene in (GameScene.MENU,GameScene.PAUSE,GameScene.VICTORY):
            options=self.options()
            if key in (pygame.K_DOWN,pygame.K_s):self.selection=(self.selection+1)%len(options)
            if key in (pygame.K_UP,pygame.K_w):self.selection=(self.selection-1)%len(options)
            if key in (pygame.K_RETURN,pygame.K_SPACE):self.choose(options[self.selection])
            if key==pygame.K_ESCAPE and self.scene==GameScene.PAUSE:self.scene=GameScene.PLAY
            return
        if self.scene==GameScene.HELP:
            if key in (pygame.K_ESCAPE,pygame.K_RETURN):self.scene=self.previous
            return
        if key==pygame.K_ESCAPE:
            self.scene=GameScene.PAUSE;self.selection=0;self.save();return
        if key==pygame.K_TAB:
            self.scene=GameScene.PLAY if self.scene==GameScene.MAP else GameScene.MAP;return
        if key==pygame.K_r:
            self.session.reset();self.visual=[float(self.session.player.x),float(self.session.player.y)]
            self.last_solved=self.session.puzzles.solved;self.renderer.particles.clear()
            self.notify('Room restored to entrance checkpoint');self.save();return
        if self.scene!=GameScene.PLAY:return
        if key in (pygame.K_e,pygame.K_SPACE):
            obj=self.session.puzzles.interact(self.session.player,key==pygame.K_SPACE)
            if obj:
                self.audio.play('pulse' if key==pygame.K_SPACE else 'use')
                self.renderer.burst(self.session.player.x,self.session.player.y,TEAL)
            else:self.notify('Face a mechanism / cracked walls need SPACE',2)

    def options(self):
        exit_label='Return to arcade' if self.embedded else 'Quit'
        if self.scene==GameScene.MENU:return ['New expedition','Continue expedition','Controls',exit_label]
        if self.scene==GameScene.VICTORY:return ['New expedition','Main menu',exit_label]
        return ['Resume','Controls','Reset room','Save and main menu',exit_label]

    def choose(self,option):
        self.selection=0
        if option=='New expedition':self.start()
        elif option=='Continue expedition':self.start(True)
        elif option=='Controls':self.previous=self.scene;self.scene=GameScene.HELP
        elif option=='Resume':self.scene=GameScene.PLAY
        elif option=='Reset room':
            self.session.reset();self.visual=[float(self.session.player.x),float(self.session.player.y)]
            self.last_solved=self.session.puzzles.solved;self.scene=GameScene.PLAY;self.save()
        elif option in ('Save and main menu','Main menu'):
            self.save();self.scene=GameScene.MENU
        elif option in ('Quit','Return to arcade'):
            if self.scene!=GameScene.MENU:self.save()
            self.running=False

    def update(self,dt,keys=None):
        self.toast_time=max(0,self.toast_time-dt);self.fade=max(0,self.fade-dt)
        if self.scene!=GameScene.PLAY:return
        self.cooldown=max(0,self.cooldown-dt)
        p=self.session.player
        self.session.tick(dt)
        if self.session.puzzles.solved and not self.last_solved:
            self.renderer.burst(p.x,p.y,GOLD,40);self.audio.play('solve');self.notify('Mechanism aligned! Follow the eastern passage.')
        self.last_solved=self.session.puzzles.solved
        if keys is None:keys=pygame.key.get_pressed()
        if self.cooldown<=0:
            dx=dy=0
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:dx=-1
            elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:dx=1
            elif keys[pygame.K_w] or keys[pygame.K_UP]:dy=-1
            elif keys[pygame.K_s] or keys[pygame.K_DOWN]:dy=1
            if dx or dy:
                before=sum(self.session.inventory.keys.values())
                if self.session.move(dx,dy):
                    self.audio.play('key' if sum(self.session.inventory.keys.values())>before else 'step')
                    if self.session.transition():
                        if self.session.finished:self.scene=GameScene.VICTORY;self.selection=0
                        self.visual=[float(self.session.player.x),float(self.session.player.y)]
                        self.fade=.45;self.last_solved=self.session.puzzles.solved;self.save()
                        self.notify(self.session.rooms.data['name'])
                self.cooldown=.13
            else:p.moving=False
        p=self.session.player
        for i,target in enumerate((p.x,p.y)):
            self.visual[i]+=(target-self.visual[i])*min(1,dt*24)
        self.autosave+=dt
        if self.autosave>=15:self.save();self.autosave=0

    def draw(self,dt,target=None):
        r=self.renderer;r.world(self.session,self.visual,dt)
        if self.scene in (GameScene.MENU,GameScene.PAUSE,GameScene.VICTORY):
            title={GameScene.MENU:'PUZZLE MAZE',GameScene.PAUSE:'EXPEDITION PAUSED',GameScene.VICTORY:'PRISM RESTORED'}[self.scene]
            r.panel(title,self.options(),self.selection)
            r.text('The Prism Chambers / original pixel adventure',36,193,(133,163,156))
        elif self.scene==GameScene.HELP:
            r.panel('FIELD GUIDE',['WASD / arrows: move and push stones','E: switch or unlock adjacent gate','SPACE: pulse cracked walls','TAB: atlas   R: entrance checkpoint','ESC: pause   M: toggle music','Doors glow teal when open.','Enter / ESC: return'])
        elif self.scene==GameScene.MAP:r.map_panel(self.session)
        else:
            if self.toast_time:
                for i,line in enumerate(textwrap.wrap(self.toast,53)):
                    pygame.draw.rect(r.surface,(18,26,39),(6,6+i*12,308,12));r.text(line,10,8+i*12,GOLD)
            elif self.session.player.x<5:
                for i,line in enumerate(textwrap.wrap(self.session.rooms.data['hint'],52)):
                    pygame.draw.rect(r.surface,(18,26,39),(6,6+i*12,308,12));r.text(line,10,8+i*12)
        if self.fade>0:
            shade=pygame.Surface((320,240));shade.fill((11,20,30));shade.set_alpha(int(255*min(1,self.fade/.45)));r.surface.blit(shade,(0,0))
        screen=target if target is not None else self.screen
        w,h=screen.get_size();scale=min(w/320,h/240)
        size=(max(1,int(320*scale)),max(1,int(240*scale)))
        screen.fill((10,17,27));screen.blit(pygame.transform.scale(r.surface,size),((w-size[0])//2,(h-size[1])//2))
        if target is None:pygame.display.flip()

    def run(self,frames=None):
        count=0
        try:
            while self.running and (frames is None or count<frames):
                dt=min(.05,self.clock.tick(60)/1000)
                for event in pygame.event.get():self.event(event)
                self.update(dt);self.draw(dt);count+=1
        finally:pygame.quit()

def main():
    parser=argparse.ArgumentParser(description='Independent Puzzle Maze')
    parser.add_argument('--headless',action='store_true');parser.add_argument('--frames',type=int)
    parser.add_argument('--screenshot',help='Write a screenshot after a bounded run')
    args=parser.parse_args()
    game=Game(args.headless)
    if args.screenshot:
        game.start();game.fade=0
        for _ in range(args.frames or 1):game.draw(1/60)
        pygame.image.save(game.renderer.surface,args.screenshot);pygame.quit()
    else:game.run(args.frames)
