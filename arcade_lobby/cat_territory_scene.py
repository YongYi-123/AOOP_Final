"""Single-player cat territory adapter; only the starter's profile is rewarded."""
import pygame
from audio_manager import GameSoundBus
from minigame import MinigameScene, MiniGameResult, PlayerResult
from rewards import RewardBundle
from cat_territory.game import TerritoryGame
from cat_minesweeper.mouse import MineMouseInput


class CatTerritoryScene(MinigameScene):
    def __init__(self, game, machine):
        super().__init__(game, machine)
        self.territory = TerritoryGame()
        if hasattr(self.game, "audio"):
            self.territory.audio.stop()
            self.territory.audio = GameSoundBus(self.game.audio)
        self.leaving = False

    def handle_event(self, event):
        if self.leaving:
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            point = MineMouseInput.canvas_position(event.pos, self.game.screen.get_size())
            self.territory.click(point, event.button)
            return
        action = self.input.feed(event)
        if event.type == pygame.WINDOWFOCUSLOST:
            if not self.territory.paused:
                self.territory.toggle_pause()
        elif event.type == pygame.KEYDOWN:
            if action == "back":
                self.leaving = True
                self.game.scenes.pop()
            elif event.key == pygame.K_BACKSPACE:
                self.territory.select_difficulty()
            elif action == "interact" or (event.key in (pygame.K_RETURN, pygame.K_KP_ENTER)
                                          and not self.game.session.player_for_key(event.key)):
                self.territory.confirm()
            elif action in ("menu", "pause"):
                self.territory.toggle_pause()
            elif action in ("up", "down", "left", "right"):
                if self.territory.selecting:
                    if action in ("up", "down"):
                        self.territory.move_selection(-1 if action == "up" else 1)
                else:
                    dx,dy = {"up":(0,-1),"down":(0,1),"left":(-1,0),"right":(1,0)}[action]
                    self.territory.move_cursor(dx,dy)
            elif action == "item":
                self.territory.clicks.clear()
                self.territory.mark(*self.territory.cursor)

    def update(self, dt):
        if not self.leaving:
            self.territory.update(dt)

    def draw(self, surface):
        self.territory.draw(surface)

    def get_result(self):
        result = self.territory.outcome()
        score = result.score if self.territory.best is not None else None
        return MiniGameResult(tuple(PlayerResult(profile.profile_id, score,
                                                  RewardBundle(tickets=result.tickets, reason="CAT TERRITORY"))
                                    for profile in self.participants[:1]))

    def on_exit(self):
        self.territory.audio.stop()

    def on_quit(self):
        self.territory.audio.stop()
