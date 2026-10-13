"""Pygame scene state machine; no lobby or shared save dependencies."""
import argparse
import math
import os
import textwrap
from enum import Enum, auto
import pygame
from puzzle_maze.session import GameSession, SAVE_PATH
from puzzle_maze.dungeon import DungeonSession
from puzzle_maze.advanced_dungeon import AdvancedDungeonSession
from puzzle_maze.render import Renderer, GOLD, TEAL
from puzzle_maze.audio import AudioManager
from puzzle_maze.onboarding import IntroSequence,TutorialCard

class GameScene(Enum):
    MENU=auto()
    PLAY=auto()
    PAUSE=auto()
    HELP=auto()
    MAP=auto()
    VICTORY=auto()
    GAMEOVER=auto()
    INTRO=auto()
    TUTORIAL=auto()
    ARCHIVE=auto()

class Game:
    def __init__(self,headless=False,embedded=False,audio=None,legacy=False,campaign=None):
        if headless:
            os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
        pygame.display.init();pygame.font.init()
        self.embedded=embedded
        self.screen=pygame.display.get_surface() if embedded else pygame.display.set_mode((960,720),pygame.RESIZABLE)
        if not embedded:pygame.display.set_caption('Puzzle Maze / Clockwork Hollow')
        self.clock=pygame.time.Clock();self.renderer=Renderer();self.audio=audio if audio is not None else AudioManager()
        self.session_factory=GameSession if embedded and campaign is None or legacy or campaign=="2" else DungeonSession if campaign=="3" else AdvancedDungeonSession
        self.session=self.session_factory();self.scene=GameScene.MENU;self.previous=GameScene.MENU
        self.selection=0;self.running=True;self.cooldown=0
        self.visual=[float(self.session.player.x),float(self.session.player.y)]
        self.toast='';self.toast_time=0;self.fade=0;self.autosave=0
        self.last_solved=False
        self.tool='pulse'
        self.intro=IntroSequence();self.tutorial=TutorialCard()
        self.tutorial.bombs=isinstance(self.session,DungeonSession)
        self.tutorial.advanced=isinstance(self.session,AdvancedDungeonSession);self.tutorial.page=0

    def notify(self,message,seconds=3):
        self.toast=message;self.toast_time=seconds

    def save(self):
        if self.scene in (GameScene.INTRO,GameScene.TUTORIAL,GameScene.MENU,GameScene.ARCHIVE):return
        try:self.session.save()
        except OSError:self.notify('Save unavailable: progress stays in memory')

    def start(self,continuing=False,onboarding=True,legacy=False,archived=False):
        factory=GameSession if legacy else DungeonSession if archived else self.session_factory
        self.session=factory.load() if continuing else factory()
        self.tutorial.bombs=isinstance(self.session,DungeonSession)
        self.tutorial.advanced=isinstance(self.session,AdvancedDungeonSession);self.tutorial.page=0
        self.tool="pulse"
        self.scene=GameScene.GAMEOVER if self.session.player.hp<=0 else GameScene.VICTORY if self.session.finished else GameScene.PLAY
        if not continuing and onboarding:
            self.intro=IntroSequence();self.scene=GameScene.INTRO
        self.visual=[float(self.session.player.x),float(self.session.player.y)]
        self.fade=.5;self.cooldown=.2;self.last_solved=self.session.puzzles.solved
        self.notify(self.session.migration_notice or self.session.rooms.data['name'])

    def event(self,event):
        if event.type==pygame.QUIT:
            if self.scene!=GameScene.MENU:self.save()
            self.running=False;return
        if event.type!=pygame.KEYDOWN:return
        key=event.key
        if self.scene==GameScene.PLAY and self.session.player.hp<=0:
            self.scene=GameScene.GAMEOVER;self.selection=0;return
        if key==pygame.K_m:self.audio.toggle()
        if self.scene in (GameScene.INTRO,GameScene.TUTORIAL) and getattr(event,"repeat",False):return
        if self.scene==GameScene.INTRO:
            if key==pygame.K_RETURN:self.scene=GameScene.TUTORIAL;self.fade=0
            elif key==pygame.K_ESCAPE:self.scene=GameScene.MENU
            return
        if self.scene==GameScene.TUTORIAL:
            if self.tutorial.advanced and key in (pygame.K_LEFT,pygame.K_RIGHT):self.tutorial.page=1-self.tutorial.page
            if key==pygame.K_RETURN:
                self.scene=GameScene.PLAY;self.cooldown=.2;self.fade=0
                self.notify(f"Basic Sword ready. {self.tutorial.controls['attack']} attacks. {self.tutorial.controls['interact']} opens chests.")
            elif key==pygame.K_ESCAPE:self.scene=GameScene.MENU
            return
        if self.scene in (GameScene.MENU,GameScene.PAUSE,GameScene.VICTORY,GameScene.GAMEOVER,GameScene.ARCHIVE):
            options=self.options()
            if key in (pygame.K_DOWN,pygame.K_s):self.selection=(self.selection+1)%len(options)
            if key in (pygame.K_UP,pygame.K_w):self.selection=(self.selection-1)%len(options)
            if key in (pygame.K_RETURN,pygame.K_SPACE):self.choose(options[self.selection])
            if key==pygame.K_ESCAPE and self.scene==GameScene.PAUSE:self.scene=GameScene.PLAY
            elif key==pygame.K_ESCAPE and self.scene==GameScene.ARCHIVE:self.scene=GameScene.MENU;self.selection=0
            elif key==pygame.K_ESCAPE and self.scene==GameScene.GAMEOVER:self.choose("Main menu")
            return
        if self.scene==GameScene.HELP:
            if self.tutorial.advanced and key in (pygame.K_LEFT,pygame.K_RIGHT):self.tutorial.page=1-self.tutorial.page
            if key in (pygame.K_ESCAPE,pygame.K_RETURN):self.scene=self.previous
            return
        if key==pygame.K_ESCAPE:
            self.scene=GameScene.PAUSE;self.selection=0;self.save();return
        if self.scene==GameScene.MAP and key in (pygame.K_LEFT,pygame.K_RIGHT):
            if hasattr(self.session,'map_floor'):self.session.map_floor='B1F' if self.session.map_floor=='1F' else '1F'
            return
        if key==pygame.K_TAB:
            self.scene=GameScene.PLAY if self.scene==GameScene.MAP else GameScene.MAP;return
        if key==pygame.K_r:
            self.session.reset();self.visual=[float(self.session.player.x),float(self.session.player.y)]
            self.last_solved=self.session.puzzles.solved;self.renderer.particles.clear()
            self.notify('Room restored to entrance checkpoint');self.save();return
        if self.scene!=GameScene.PLAY:return
        if getattr(event,'repeat',False) and key in (pygame.K_b,pygame.K_j,pygame.K_e,pygame.K_SPACE,pygame.K_p,pygame.K_g):return
        if key==pygame.K_b and hasattr(self.session,'bombs'):
            if not self.session.bombs.place():self.notify('Find powder / wait for placement cooldown',2)
            return
        if key==pygame.K_p and hasattr(self.session,'powder'):
            if not self.session.powder():self.notify('P: face a fire / refill powder',2)
            return
        if key==pygame.K_g and hasattr(self.session,'throw_pot'):
            if not self.session.throw_pot():self.notify('E lifts a pot; G throws it',2)
            return
        if key==pygame.K_e and getattr(self.session.inventory,'carried',None):
            if not self.session.drop_pot():self.notify('Face a clear tile to set down',2)
            return
        if key==pygame.K_j:self.session.attack();return
        if key==pygame.K_h:
            if not self.session.heal():self.notify("H: use a potion when hurt",2)
            return
        if key==pygame.K_q:
            tools=['pulse']+[a for a in ('mirror','magnet') if a in self.session.inventory.abilities]
            self.tool=tools[(tools.index(self.tool)+1)%len(tools)] if self.tool in tools else 'pulse'
            self.notify('Tool: '+self.tool);return
        if key in (pygame.K_LSHIFT,pygame.K_RSHIFT):
            if self.session.dash():
                self.renderer.burst(self.session.player.x,self.session.player.y,TEAL)
                self.audio.play('pulse');self.cooldown=.13
                if self.session.transition():
                    if self.session.finished:self.scene=GameScene.VICTORY;self.selection=0
                    self.visual=[float(self.session.player.x),float(self.session.player.y)]
                    self.fade=.45;self.save()
            else:self.notify('Find boots / dash recharging',2)
            return
        if key==pygame.K_f or key==pygame.K_SPACE and self.tool=='magnet':
            result=self.session.puzzles.magnet(self.session.player,key==pygame.K_f)
            if result:self.renderer.burst(self.session.player.x,self.session.player.y,TEAL);self.audio.play('pulse')
            else:self.notify('Face metal: SPACE repels, F attracts',2)
            return
        if key in (pygame.K_e,pygame.K_SPACE):
            obj=self.session.puzzles.interact(self.session.player,key==pygame.K_SPACE)
            if obj:
                self.audio.play('pulse' if key==pygame.K_SPACE else 'use')
                self.renderer.burst(self.session.player.x,self.session.player.y,TEAL)
                obj_data=self.session.puzzles.objects[obj].data
                if obj_data.get('ability'):self.notify('Acquired: '+obj_data['ability'])
            else:self.notify('E: chest / mechanism. Q: tool. SPACE: pulse.',2)

    def options(self):
        exit_label='Return to arcade' if self.embedded else 'Quit'
        if self.scene==GameScene.MENU:
            options=['New expedition','Quick start (skip tutorial)','Continue expedition']
            if not self.embedded:options.append('Archived expeditions')
            return options+['Controls',exit_label]
        if self.scene==GameScene.ARCHIVE:return ['3.0 Clockwork Hollow','2.1 Prism Chambers','Main menu']
        if self.scene==GameScene.GAMEOVER:return ['Main menu','Retry room']
        if self.scene==GameScene.VICTORY:return ['New expedition','Main menu',exit_label]
        return ['Resume','Controls','Reset room','Save and main menu',exit_label]

    def choose(self,option):
        self.selection=0
        if option=='New expedition':self.start()
        elif option=='Quick start (skip tutorial)':self.start(onboarding=False)
        elif option=='Continue expedition':self.start(True)
        elif option in ('Continue 2.1 archive','2.1 Prism Chambers'):self.start(True,legacy=True)
        elif option=='3.0 Clockwork Hollow':self.start(True,archived=True)
        elif option=='Archived expeditions':self.scene=GameScene.ARCHIVE
        elif option=='Controls':self.previous=self.scene;self.scene=GameScene.HELP
        elif option=='Resume':self.scene=GameScene.PLAY
        elif option in ('Reset room','Retry room'):
            self.session.reset();self.visual=[float(self.session.player.x),float(self.session.player.y)]
            self.last_solved=self.session.puzzles.solved;self.scene=GameScene.PLAY;self.save()
        elif option in ('Save and main menu','Main menu'):
            self.save();self.scene=GameScene.MENU
        elif option in ('Quit','Return to arcade'):
            if self.scene!=GameScene.MENU:self.save()
            self.running=False

    def update(self,dt,keys=None):
        self.toast_time=max(0,self.toast_time-dt);self.fade=max(0,self.fade-dt)
        if self.scene==GameScene.INTRO:
            if self.intro.update(dt):self.scene=GameScene.TUTORIAL;self.fade=0
            return
        if self.scene!=GameScene.PLAY:return
        self.cooldown=max(0,self.cooldown-dt)
        p=self.session.player
        self.session.tick(dt)
        for cue in self.session.combat.events:
            self.audio.play(cue)
            if cue in ('hurt','heal','defeat'):self.renderer.burst(p.x,p.y,TEAL if cue!='hurt' else (230,95,97))
        self.session.combat.events.clear()
        if p.hp<=0:
            self.scene=GameScene.GAMEOVER;self.selection=0;self.save();return
        if self.session.puzzles.solved and not self.last_solved:
            self.renderer.burst(p.x,p.y,GOLD,40);self.audio.play('solve');self.notify('Mechanism aligned! Check the map for routes.')
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
        r=self.renderer;r.world(self.session,self.visual,dt,self.tool,self.tutorial.controls)
        if self.scene==GameScene.INTRO:self.intro.draw(r,self.tutorial.controls["confirm"])
        elif self.scene==GameScene.TUTORIAL:self.tutorial.draw(r)
        elif self.scene in (GameScene.MENU,GameScene.PAUSE,GameScene.VICTORY,GameScene.GAMEOVER,GameScene.ARCHIVE):
            title={GameScene.MENU:'PUZZLE MAZE',GameScene.PAUSE:'EXPEDITION PAUSED',GameScene.VICTORY:'HOLLOW AWAKENED',GameScene.GAMEOVER:'GAME OVER',GameScene.ARCHIVE:'OLD EXPEDITIONS'}[self.scene]
            if self.scene==GameScene.MENU and isinstance(self.session,AdvancedDungeonSession):title='PUZZLE MAZE 4.1'
            r.panel(title,self.options(),self.selection)
            if self.scene==GameScene.VICTORY and hasattr(self.session,'rewards'):
                bag=self.session.rewards
                r.text(f'Tokens {bag.tokens} / Tickets {bag.tickets}',36,151,GOLD,max_width=244)
                r.text(f'Found {len(bag.collections)}/5 / '+('Settled once' if bag.claimed else 'Pending'),36,170,TEAL,max_width=244)
            label='4.1 / Emberglass Hollow' if isinstance(self.session,AdvancedDungeonSession) else '3.0 / Clockwork Hollow' if isinstance(self.session,DungeonSession) else '2.1 / The Prism Chambers'
            r.text(label,36,193,(133,163,156),max_width=244)
        elif self.scene==GameScene.HELP:
            r.panel('FIELD GUIDE',self.tutorial.lines(False))
        elif self.scene==GameScene.MAP:r.map_panel(self.session)
        else:
            boss_room=any(e.kind in ('golem','crystal_warden') for e in self.session.combat.enemies)
            if self.toast_time and not boss_room:
                for i,line in enumerate(textwrap.wrap(self.toast,26)):
                    pygame.draw.rect(r.surface,(18,26,39),(6,6+i*16,226,16));r.text(line,10,8+i*16,GOLD,max_width=220)
            elif self.session.player.x<5 and not boss_room:
                for i,line in enumerate(textwrap.wrap(self.session.rooms.data['hint'],26)):
                    pygame.draw.rect(r.surface,(18,26,39),(6,6+i*16,226,16));r.text(line,10,8+i*16,max_width=220)
        if self.scene==GameScene.PLAY:r.minimap(self.session)
        if self.fade>0:
            shade=pygame.Surface((320,240));shade.fill((11,20,30));shade.set_alpha(int(255*min(1,self.fade/.45)));r.surface.blit(shade,(0,0))
        screen=target if target is not None else self.screen
        w,h=screen.get_size();scale=min(w/320,h/240)
        scale=math.floor(scale) if scale>=1 else scale
        size=(max(1,int(320*scale)),max(1,int(240*scale)))
        screen.fill((10,17,27));screen.blit(pygame.transform.scale(r.surface,size),((w-size[0])//2,(h-size[1])//2))
        self.renderer.ui.present(screen,((w-size[0])//2,(h-size[1])//2),scale)
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
    parser.add_argument('--campaign',choices=('4','3','2'),default='4',help='Campaign version, each with its own save')
    parser.add_argument('--legacy',action='store_true',help='Play the original 2.1 campaign and save')
    parser.add_argument('--headless',action='store_true');parser.add_argument('--frames',type=int)
    parser.add_argument('--screenshot',help='Write a screenshot after a bounded run')
    args=parser.parse_args()
    game=Game(args.headless,legacy=args.legacy,campaign=args.campaign)
    if args.screenshot:
        game.start(onboarding=False);game.fade=0
        for _ in range(args.frames or 1):game.draw(1/60)
        pygame.image.save(game.screen,args.screenshot);pygame.quit()
    else:game.run(args.frames)
