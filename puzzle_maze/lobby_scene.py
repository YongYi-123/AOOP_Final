"""Optional lobby adapter: shared window, participant-only input, zero payout."""
from collections import defaultdict
import pygame
from minigame import MinigameScene, MiniGameResult
from puzzle_maze.game import Game, GameScene

class LobbyAudio:
    def __init__(self,manager):
        self.manager=manager

    def play(self,name):
        self.manager.play({'step':'footstep','use':'confirm','key':'equip','solve':'win','pulse':'confirm','attack':'hit','hit':'hit','hurt':'loss','heal':'powerup','defeat':'win','chest_spawn':'equip','wall_break':'hit','boss_break':'win'}.get(name,'confirm'))

    def toggle(self):
        pass  # M is handled by the lobby's audio controls.

class PuzzleMazeScene(MinigameScene):
    full_resolution=True  # Native UI is drawn directly on the host output surface.
    def __init__(self,game,machine):
        super().__init__(game,machine)
        self.maze=Game(embedded=True,audio=LobbyAudio(game.audio),campaign="4")
        self.leaving=False
        self.dt=0

    def attach_players(self,players,spectators=()):
        super().attach_players(players,spectators)
        scheme=self.input.scheme.name
        controls=self.maze.tutorial.controls
        if scheme=='P2':
            controls.update(move='ARROWS',attack='K',interact='ENTER',ability='KP0',dash='RSHIFT',confirm='ENTER')
        elif scheme=='P1':
            controls.update(move='WASD',attack='J',interact='E',ability='SPACE',dash='LSHIFT',confirm='E',pages='A / D')

    def handle_event(self,event):
        if self.leaving:return
        action=self.input.feed(event)
        if event.type==pygame.WINDOWFOCUSLOST:
            if self.maze.scene==GameScene.PLAY:
                self.maze.scene=GameScene.PAUSE;self.maze.selection=0
            return
        if event.type!=pygame.KEYDOWN:return
        if action=='back' and self.maze.scene in (GameScene.MENU,GameScene.VICTORY):
            self.leave();return
        canonical={'up':pygame.K_UP,'down':pygame.K_DOWN,'left':pygame.K_LEFT,
                   'right':pygame.K_RIGHT,'back':pygame.K_ESCAPE,'menu':pygame.K_ESCAPE,
                   'pause':pygame.K_ESCAPE,'item':pygame.K_SPACE,'confirm':pygame.K_RETURN}
        # Combat is a Maze action absent from the lobby's generic schemes.
        attack_key=pygame.K_k if self.input.scheme.name=='P2' else pygame.K_j
        if event.key==attack_key:key=pygame.K_j
        elif event.key in (pygame.K_q,pygame.K_f,pygame.K_h,pygame.K_TAB,pygame.K_r,pygame.K_b,pygame.K_p,pygame.K_g,pygame.K_t):key=event.key
        elif event.key in (pygame.K_LSHIFT,pygame.K_RSHIFT) and (self.input.scheme.name=='SOLO' or self.input.scheme.owns(event.key)):key=pygame.K_LSHIFT
        elif action=='interact':
            key=pygame.K_e if self.maze.scene==GameScene.PLAY else pygame.K_RETURN
        elif action in canonical:key=canonical[action]
        elif event.key in (pygame.K_TAB,pygame.K_r):key=event.key
        else:return
        self.maze.event(pygame.event.Event(pygame.KEYDOWN,key=key,repeat=getattr(event,"repeat",False)))
        if not self.maze.running:self.leave()

    def update(self,dt):
        if self.leaving:return
        self.dt=dt
        keys=defaultdict(bool)
        for action,key in [('left',pygame.K_LEFT),('right',pygame.K_RIGHT),('up',pygame.K_UP),('down',pygame.K_DOWN)]:
            keys[key]=self.input.held(action)
        self.maze.update(dt,keys)

    def draw(self,surface):
        self.maze.draw(self.dt,target=surface)

    def leave(self):
        if self.leaving:return
        self.leaving=True
        self.game.scenes.pop()

    def get_result(self):
        return MiniGameResult()  # Trial cabinet never adds tickets or scores.

    def on_exit(self):
        if self.maze.scene!=GameScene.MENU:self.maze.save()

    def on_quit(self):
        self.on_exit()
