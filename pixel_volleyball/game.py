"""Presentation and match lifecycle; input providers supply logical controls."""
import pygame
from .model import MatchState, VolleyMatch
from .settlement import VolleyReward
from .rendering import VolleyRenderer
from .audio import VolleySounds
from .effects import SmashTrail
from .keyboard_hints import default_hints
from . import old_ticket as secret


class VolleyGame:
    def __init__(self, *, cpu=True):
        self.cpu = cpu
        self.match = VolleyMatch(cpu=cpu)
        self.renderer = VolleyRenderer()
        self.effects = SmashTrail()
        self.hints = default_hints()
        self.audio = VolleySounds()
        self.best = [VolleyReward() for _ in range(1 if cpu else 2)]   # (the CPU side earns nothing)
        self._observed = None
        # THE OLD SPECTATOR TICKET (old_ticket.py). The hub sets these; on its own the game never drops it.
        self.secret_enabled = False         # may the ticket appear at all?
        self.secret_ready = False           # True: it is due after every completed match (a route was earned before)
        self.secret_found = False           # True: already picked up once (it never falls again)
        self.secret_events = []             # "unlocked" (Sandra was beaten) / "found" (picked up) / "try" (a real loss)
        self.ticket = None                  # the stub after the current match, once it has fallen
        self._tried = None
        self._won = None                    # the won match that earned the ACE route this session (reported once)

    def pop_secret_events(self):
        events, self.secret_events = self.secret_events, []
        return events

    def _secret_tick(self, dt, controls=()):
        """After the final point: count the match (an ACE win, or a meaningful loss) and, while the ticket is due, let it
        fall and let the player's cat stroll over to it. Nothing here runs while a match is being played."""
        match = self.match
        outcome = match.outcome
        if match.state is not MatchState.FINISHED or outcome is None:
            return
        if outcome.winner == 0 and self._won is None:
            self._won = outcome
            if self.secret_enabled and not (self.secret_ready or self.secret_found):
                self.secret_events.append("unlocked")
        found = self.secret_found or (self.ticket is not None and self.ticket.found)
        if (outcome is not self._tried and outcome.winner != 0 and outcome.points[0] >= secret.TRY_MIN_POINTS
                and not found):
            self._tried = outcome
            if self.secret_enabled:
                self.secret_events.append("try")
        if self.ticket is None and self.secret_enabled and not found and (self.secret_ready or self._won is not None):
            self.ticket = secret.OldTicket()
        if self.ticket is not None and self.ticket.update(dt, match.players[0]) == "found" and self.secret_enabled:
            self.secret_events.append("found")
            self.secret_found = True

    @property
    def ticket_playing(self):
        """The ticket scene is on: the result card and a rematch wait for it (about two seconds)."""
        return self.ticket is not None and self.ticket.blocking

    @property
    def has_completed(self):
        return self._observed is not None

    def restart(self):
        if self.ticket_playing:                                     # (the ticket scene is short: let it finish)
            return
        self.observe_result()
        self.match = VolleyMatch(cpu=self.cpu)
        self.match.start()
        self.effects = SmashTrail()
        self.ticket = None

    def confirm(self):
        if self.ticket_playing:
            return
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
        for side in range(len(self.best)):
            result = VolleyReward.from_outcome(outcome, side)
            if result.score > self.best[side].score:
                self.best[side] = result

    def update(self, dt, controls=()):
        before = self.match.elapsed
        self.match.update(dt, controls)
        self.effects.update(self.match.elapsed - before, self.match.ball, self.match.impacts)
        self.audio.play(self.match.events)
        self.observe_result()
        self._secret_tick(dt, controls)

    def draw(self, surface):
        dx, dy = self.effects.shake_offset() if self.match.state is MatchState.PLAYING else (0, 0)
        if not (dx or dy):
            self.renderer.draw(surface, self.match, self.effects, self.hints, self.ticket)
            return
        frame = pygame.Surface(surface.get_size())
        self.renderer.draw(frame, self.match, self.effects, self.hints, self.ticket)
        surface.fill((10, 5, 28))
        surface.blit(frame, (dx, dy))
