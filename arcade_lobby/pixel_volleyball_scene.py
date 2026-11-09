"""Thin player-input and settlement adapter for the independent volleyball package."""
import pygame
from audio_manager import GameSoundBus
from minigame import MinigameScene, MiniGameResult, PlayerResult
from rewards import RewardBundle
from pixel_volleyball.game import VolleyGame
from pixel_volleyball.model import VolleyInput, MatchState
from pixel_volleyball.keyboard_hints import hint_lines


class PixelVolleyballScene(MinigameScene):
    def __init__(self, game, machine):
        super().__init__(game, machine)
        self.volley = VolleyGame()
        self.leaving = False
        self._tapped = set()    # item presses since the last frame, even if already released

    def attach_players(self, players):
        super().attach_players(players)
        self.volley.audio.stop()
        self.volley = VolleyGame()
        if hasattr(self.game, "audio"):
            self.volley.audio.stop()
            self.volley.audio = GameSoundBus(self.game.audio)
        self._tapped.clear()
        self.volley.hints = self._hints()

    def _hints(self):
        """The player's own key names, so the screen matches the real bindings."""
        if not self.players:
            return self.volley.hints
        c = self.players[0].controls
        return hint_lines(*(c.label(action, limit=limit) for action, limit in
                            (("left", 1), ("right", 1), ("up", 1), ("item", 2))))

    def handle_event(self, event):
        if self.leaving:
            return
        if event.type == pygame.WINDOWFOCUSLOST:
            for input_ in self._inputs.values():
                input_.feed(event)
            if self.volley.match.state is MatchState.PLAYING:
                self.volley.match.toggle_pause()
            return
        action = self.input.feed(event)
        if action == "item":
            self._tapped.add("item")
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.volley.observe_result()
            self.leaving = True
            self.game.scenes.pop()
        elif event.key == pygame.K_BACKSPACE:
            self.volley.restart()
        elif action in ("menu", "pause"):
            self.volley.match.toggle_pause()
        elif action == "interact" or (event.key in (pygame.K_RETURN, pygame.K_KP_ENTER)
                                      and not self.game.session.player_for_key(event.key)):
            self.volley.confirm()

    def update(self, dt):
        if self.leaving:
            return
        held = self.input
        controls = [VolleyInput(held.axis("left", "right"), held.held("up"),
                                held.held("item") or "item" in self._tapped)]
        self._tapped.clear()
        self.volley.update(dt, controls)

    def draw(self, surface):
        self.volley.draw(surface)

    def get_result(self):
        self.volley.observe_result()
        results = tuple(PlayerResult(profile.profile_id,
                                     result.score if self.volley.has_completed else None,
                                     RewardBundle(tickets=result.tickets, reason="CAT VOLLEYBALL"))
                        for profile, result in zip(self.participants, self.volley.best))
        return MiniGameResult(results)

    def on_exit(self):
        self.volley.audio.stop()

    def on_quit(self):
        self.volley.audio.stop()
