"""Optional lobby adapter: shared window, participant-only input, zero payout."""
from collections import defaultdict
import pygame
from minigame import MinigameScene, MiniGameResult
from puzzle_maze.game import Game, GameScene

class LobbyAudio:
    def __init__(self,manager):
        self.manager=manager

    def play(self,name):
        self.manager.play({'step':'footstep','use':'confirm','key':'equip','solve':'win','pulse':'confirm'}.get(name,'confirm'))

    def toggle(self):
        pass  # M is handled by the lobby's audio controls.

class PuzzleMazeScene(MinigameScene):
    def __init__(self,game,machine):
        super().__init__(game,machine)
        self.maze=Game(embedded=True,audio=LobbyAudio(game.audio))
        self.leaving=False
        self.dt=0

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
        if action=='interact':
            key=pygame.K_e if self.maze.scene==GameScene.PLAY else pygame.K_RETURN
        elif action in canonical:key=canonical[action]
        elif event.key in (pygame.K_TAB,pygame.K_r):key=event.key
        else:return
        self.maze.event(pygame.event.Event(pygame.KEYDOWN,key=key))
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
