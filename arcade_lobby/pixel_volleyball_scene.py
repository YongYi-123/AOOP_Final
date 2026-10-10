"""Thin player-input and settlement adapter for the independent volleyball package."""
import pygame
from minigame import MinigameScene, MiniGameResult, PlayerResult
from rewards import RewardBundle
from pixel_volleyball.game import VolleyGame
from pixel_volleyball.model import VolleyInput, MatchState


class PixelVolleyballScene(MinigameScene):
    def __init__(self, game, machine):
        super().__init__(game, machine)
        self.volley = VolleyGame()
        self.leaving = False

    def attach_players(self, players, spectators=()):
        super().attach_players(players, spectators)
        self.volley.audio.stop()
        self.volley = VolleyGame(len(self.players) or 1)

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
                                        input_.held("item") or input_.held("interact")))
        self.volley.update(dt, controls)

    def draw(self, surface):
        self.volley.draw(surface)

    def get_result(self):
        self.volley.observe_result()
        results = tuple(PlayerResult(profile.profile_id,
                                     result.score if self.volley.has_completed else None,
                                     RewardBundle(tickets=result.tickets, reason="PIXEL VOLLEYBALL"))
                        for profile, result in zip(self.participants, self.volley.best))
        return MiniGameResult(results)

    def on_exit(self):
        self.volley.audio.stop()

    def on_quit(self):
        self.volley.audio.stop()
