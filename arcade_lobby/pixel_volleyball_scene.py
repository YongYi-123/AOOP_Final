"""Thin player-input and settlement adapter for the independent volleyball package."""
import pygame
from audio_manager import GameSoundBus
from minigame import MinigameScene, MiniGameResult, PlayerResult
from rewards import RewardBundle
from pixel_volleyball.game import VolleyGame
from pixel_volleyball.model import VolleyInput, MatchState
from pixel_volleyball.keyboard_hints import hint_lines


class PixelVolleyballScene(MinigameScene):
    spectator_corner = "topleft"       # the bottom corners hold the help text
    spectator_offset = (4, 50)         # under the title and score line, left of the net

    def __init__(self, game, machine):
        super().__init__(game, machine)
        self.volley = VolleyGame()
        self.leaving = False
        self._tapped = set()    # item presses since the last frame, even if already released

    def attach_players(self, players, spectators=()):
        super().attach_players(players, spectators)
        self.volley.audio.stop()
        self.volley = VolleyGame(len(self.players) or 1)
        if hasattr(self.game, "audio"):
            self.volley.audio.stop()
            self.volley.audio = GameSoundBus(self.game.audio)
        self._tapped.clear()
        self.volley.hints = self._hints()

    def _hints(self):
        """Each player's own key names, so the screen matches the real bindings."""
        names = ("P1", "P2") if len(self.players) > 1 else ("",)
        keys = [(name, *(p.controls.label(action, limit=limit) for action, limit in
                         (("left", 1), ("right", 1), ("up", 1), ("item", 2))))
                for name, p in zip(names, self.players)]
        return hint_lines(keys) if keys else self.volley.hints

    def handle_event(self, event):
        if self.leaving:
            return
        if event.type == pygame.WINDOWFOCUSLOST:
            for input_ in self._inputs.values():
                input_.feed(event)
            if self.volley.match.state is MatchState.PLAYING:
                self.volley.match.toggle_pause()
            return
        actors = self.players or [None]
        actions = [self.input_for(player).feed(event) for player in actors]
        for player, action in zip(actors, actions):
            if action == "item":
                self._tapped.add(id(player))
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.volley.observe_result()
            self.leaving = True
            self.game.scenes.pop()
        elif event.key == pygame.K_BACKSPACE:
            self.volley.restart()
        elif any(action in ("menu", "pause") for action in actions):
            self.volley.match.toggle_pause()
        elif "interact" in actions or (event.key in (pygame.K_RETURN, pygame.K_KP_ENTER)
                                      and not self.game.session.player_for_key(event.key)):
            self.volley.confirm()

    def update(self, dt):
        if self.leaving:
            return
        controls = []
        for player in self.players or [None]:
            input_ = self.input_for(player)
            controls.append(VolleyInput(input_.axis("left", "right"), input_.held("up"),
                                        input_.held("item") or id(player) in self._tapped))
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
