"""Single-player cat minesweeper adapter; only the starter's profile is rewarded."""
import pygame
from audio_manager import GameSoundBus
from minigame import MinigameScene, MiniGameResult, PlayerResult
from rewards import RewardBundle
from cat_minesweeper.game import MineGame
from cat_minesweeper.mouse import MineMouseInput


class CatMinesweeperScene(MinigameScene):
    def __init__(self, game, machine):
        super().__init__(game, machine)
        self.mine_game = MineGame()
        if hasattr(self.game, "audio"):
            self.mine_game.audio.stop()
            self.mine_game.audio = GameSoundBus(self.game.audio)
        self.leaving = False

    def handle_event(self, event):
        if self.leaving:
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            point = MineMouseInput.canvas_position(event.pos, self.game.screen.get_size())
            self.mine_game.click(point, event.button)
            return
        action = self.input.feed(event)
        if event.type == pygame.WINDOWFOCUSLOST:
            if not self.mine_game.paused:
                self.mine_game.toggle_pause()
        elif event.type == pygame.KEYDOWN:
            if action == "back":
                self.leaving = True
                self.game.scenes.pop()
            elif event.key == pygame.K_BACKSPACE:
                self.mine_game.select_difficulty()
            elif action == "interact" or (event.key in (pygame.K_RETURN, pygame.K_KP_ENTER)
                                          and not self.game.session.player_for_key(event.key)):
                self.mine_game.confirm()
            elif action in ("menu", "pause"):
                self.mine_game.toggle_pause()
            elif action in ("up", "down"):
                self.mine_game.move_selection(-1 if action == "up" else 1)

    def update(self, dt):
        if not self.leaving:
            self.mine_game.update(dt)

    def draw(self, surface):
        self.mine_game.draw(surface)

    def get_result(self):
        result = self.mine_game.outcome()
        score = result.score if self.mine_game.best is not None else None
        return MiniGameResult(tuple(PlayerResult(profile.profile_id, score,
                                                  RewardBundle(tickets=result.tickets, reason="CAT MINESWEEPER"))
                                    for profile in self.participants[:1]))

    def on_exit(self):
        self.mine_game.audio.stop()

    def on_quit(self):
        self.mine_game.audio.stop()
