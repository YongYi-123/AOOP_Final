"""Thin input and settlement adapter for the independent neon_cat_maze package (the NEON CAT MAZE minigame).

Single-player: only the player who started the machine plays, scores and is paid; the other player spectates and none of
their keys reach the game. The best run of the play session is the one reported, so Play Again and Restart can never
pay twice."""
import pygame
from audio_manager import GameSoundBus
from minigame import MinigameScene, MiniGameResult, PlayerResult
from rewards import RewardBundle
from neon_cat_maze.game import CatMazeGame, Screen

SCORE_KEY = "puzzle_drop"               # the profile's high score: the machine's id, so existing saves keep their record
LEVEL_KEY = "neon_cat_maze_level"       # the highest level reached, kept in the profile's existing record table
DIRECTIONS = ("up", "down", "left", "right")


class CatMazeScene(MinigameScene):
    spectator_corner = "bottomright"

    def __init__(self, game, machine):
        super().__init__(game, machine)
        self.cat_maze = CatMazeGame()
        self.leaving = False
        self.order = []                 # direction actions currently held, oldest first: the newest one steers
        self._wire_audio()
        self._refresh_keys()

    def _wire_audio(self):
        if hasattr(self.game, "audio"):
            self.cat_maze.audio = GameSoundBus(self.game.audio)

    def _refresh_keys(self):
        scheme = self.input.scheme
        move = "WASD/ARROWS" if scheme.name == "SOLO" else scheme.move_hint
        self.cat_maze.keys = {"move": move, "pause": scheme.label("menu", "pause") or "P"}

    def attach_players(self, players, spectators=()):
        super().attach_players(players, spectators)
        self._refresh_keys()
        profile = self.participants[0] if self.participants else None
        if profile is not None:
            self.cat_maze.saved_score = profile.high_score(SCORE_KEY)
            self.cat_maze.saved_level = profile.high_score(LEVEL_KEY)

    def handle_event(self, event):
        if self.leaving:
            return
        if event.type == pygame.WINDOWFOCUSLOST:
            self.input.feed(event)
            self.order.clear()
            self.cat_maze.pause()
            return
        action = self.input.feed(event)
        if event.type == pygame.KEYUP:
            released = self.input.scheme.action_for(event.key) if self.input.scheme.owns(event.key) else None
            if released in self.order:
                self.order.remove(released)
            return
        if event.type != pygame.KEYDOWN:
            return
        game = self.cat_maze
        if event.key == pygame.K_f:
            game.toggle_reduced()
        elif action in DIRECTIONS:
            self.order = [a for a in self.order if a != action] + [action]
            game.act(action)
        elif action == "back":
            game.act("back")
        elif action in ("menu", "pause"):
            if game.screen is Screen.PLAYING:
                game.pause()
            elif game.screen is Screen.PAUSED:
                game.resume()
        elif action in ("interact", "confirm") or (
                event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and not self.game.session.player_for_key(event.key)):
            game.act("confirm")
        if game.wants_exit:
            self.leaving = True
            self.game.scenes.pop()

    def update(self, dt):
        if self.leaving:
            return
        if self.order and self.cat_maze.screen is Screen.PLAYING:
            self.cat_maze.steer(self.order[-1])             # a held key keeps asking for its turn
        self.cat_maze.update(dt)

    def draw(self, surface):
        self.cat_maze.draw(surface)

    def get_result(self):
        """Idempotent: the same MiniGameResult however often it is asked for, and the record only grows."""
        game = self.cat_maze
        game.observe()
        best = game.best
        results = []
        for profile in self.participants[:1]:
            if game.has_played:
                profile.record_score(LEVEL_KEY, game.session_level)
            results.append(PlayerResult(profile.profile_id, game.session_score if game.has_played else None,
                                        RewardBundle(tickets=best.tickets, reason="NEON CAT MAZE")))
        return MiniGameResult(tuple(results))

    def on_exit(self):
        self.cat_maze.observe()

    def on_quit(self):
        self.cat_maze.observe()
