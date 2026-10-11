"""Presentation and match lifecycle; input providers supply logical controls."""
import pygame
from .model import MatchState, VolleyMatch
from .settlement import VolleyReward
from .rendering import VolleyRenderer
from .audio import VolleySounds
from .effects import SmashTrail
from .keyboard_hints import default_hints


class VolleyGame:
    def __init__(self, local_players=1):
        self.local_players = local_players
        self.match = VolleyMatch(local_players)
        self.renderer = VolleyRenderer()
        self.effects = SmashTrail()
        self.hints = default_hints(local_players)
        self.audio = VolleySounds()
        self.best = [VolleyReward() for _ in range(local_players)]
        self._observed = None

    @property
    def has_completed(self):
        return self._observed is not None

    def restart(self):
        self.observe_result()
        self.match = VolleyMatch(self.local_players)
        self.match.start()
        self.effects = SmashTrail()

    def confirm(self):
        if self.match.state is MatchState.FINISHED:
            self.restart()
        elif self.match.state is MatchState.PAUSED:
            self.match.toggle_pause()
        else:
            self.match.start()

    def observe_result(self):
        outcome = self.match.outcome
        if outcome is None or outcome is self._observed:
            return
        self._observed = outcome
        for side in range(self.local_players):
            result = VolleyReward.from_outcome(outcome, side)
            if result.score > self.best[side].score:
                self.best[side] = result

    def update(self, dt, controls=()):
        before = self.match.elapsed
        self.match.update(dt, controls)
        self.effects.update(self.match.elapsed - before, self.match.ball, self.match.impacts)
        self.audio.play(self.match.events)
        self.observe_result()

    def draw(self, surface):
        dx, dy = self.effects.shake_offset() if self.match.state is MatchState.PLAYING else (0, 0)
        if not (dx or dy):
            self.renderer.draw(surface, self.match, self.effects, self.hints)
            return
        frame = pygame.Surface(surface.get_size())
        self.renderer.draw(frame, self.match, self.effects, self.hints)
        surface.fill((10, 5, 28))
        surface.blit(frame, (dx, dy))
