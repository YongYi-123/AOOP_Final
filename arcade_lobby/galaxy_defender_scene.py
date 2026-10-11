"""Thin input and settlement adapter for the independent galaxy_defender package (the Starfall Assault minigame).

Single-player: only the player who started the machine plays, scores and is paid. The best run of
the play session is the one reported, so Retry and Restart can never pay twice."""
import pygame
from audio_manager import GameSoundBus
from minigame import MinigameScene, MiniGameResult, PlayerResult
from rewards import RewardBundle
from galaxy_defender.game import GalaxyGame, Screen

SCORE_KEY = "galaxy_defender"           # the profile's high score, the same key as the machine id
WAVE_KEY = "galaxy_defender_wave"       # the highest wave, kept in the profile's existing record table


class GalaxyDefenderScene(MinigameScene):
    spectator_corner = "topleft"

    def __init__(self, game, machine):
        super().__init__(game, machine)
        self.galaxy = GalaxyGame()
        self.leaving = False
        self._wire_audio()

    def _wire_audio(self):
        if hasattr(self.game, "audio"):
            self.galaxy.audio = GameSoundBus(self.game.audio)

    def attach_players(self, players, spectators=()):
        super().attach_players(players, spectators)
        profile = self.participants[0] if self.participants else None
        if profile is not None:
            self.galaxy.saved_score = profile.high_score(SCORE_KEY)
            self.galaxy.saved_wave = profile.high_score(WAVE_KEY)

    def handle_event(self, event):
        if self.leaving:
            return
        if event.type == pygame.WINDOWFOCUSLOST:
            self.input.feed(event)
            self.galaxy.pause()
            return
        action = self.input.feed(event)
        if event.type != pygame.KEYDOWN:
            return
        galaxy = self.galaxy
        if event.key == pygame.K_f:
            galaxy.toggle_reduced()
        elif action == "back":
            galaxy.act("back")
        elif action in ("menu", "pause"):
            if galaxy.screen is Screen.PLAYING:
                galaxy.pause()
            elif galaxy.screen is Screen.PAUSED:
                galaxy.act("back")
        elif action in ("up", "down"):
            galaxy.act(action)
        elif action in ("interact", "confirm") or (
                event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and not self.game.session.player_for_key(event.key)):
            galaxy.act("confirm")
        if galaxy.wants_exit:
            self.leaving = True
            self.game.scenes.pop()

    def update(self, dt):
        if self.leaving:
            return
        move = self.input.axis("left", "right")
        self.galaxy.update(dt, move, self.input.held("item"))

    def draw(self, surface):
        self.galaxy.draw(surface)

    def get_result(self):
        """Idempotent: the same MiniGameResult however often it is asked for, and the record only grows."""
        self.galaxy.observe()
        best = self.galaxy.best
        results = []
        for profile in self.participants[:1]:
            if self.galaxy.has_played:
                profile.record_score(WAVE_KEY, self.galaxy.session_wave)
            results.append(PlayerResult(profile.profile_id, best.score if self.galaxy.has_played else None,
                                        RewardBundle(tickets=best.tickets, reason="STARFALL ASSAULT")))
        return MiniGameResult(tuple(results))

    def on_exit(self):
        self.galaxy.observe()

    def on_quit(self):
        self.galaxy.observe()
