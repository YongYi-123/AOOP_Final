"""Original synthesized arcade music and effects with separate volume controls."""
from array import array
import math
import pygame


class AudioManager:
    THEMES = {'lobby': (262, 330, 392, 330, 294, 349, 440, 349),
              'retro_racer': (196, 247, 294, 392, 196, 294, 247, 392),
              'pixel_volleyball': (330, 392, 440, 523, 440, 392, 330, 294),
              'cat_minesweeper': (262, 392, 330, 440, 349, 330, 294, 392)}
    EFFECTS = {'machine': (440, 660), 'confirm': (660, 880), 'cancel': (440, 220),
               'hit': (560,), 'spike': (1480, 880, 440), 'bounce': (240,), 'point': (660, 880),
               'win': (523, 659, 784), 'loss': (440, 330, 220),
               'reveal': (700,), 'flag': (420, 560), 'skid': (480, 320, 160)}

    def __init__(self, bgm_volume=.22, sfx_volume=.7):
        self.bgm_volume, self.sfx_volume = bgm_volume, sfx_volume
        self.theme = None
        self.sounds, self.music = {}, {}
        self.channels = []
        self.enabled, self.active, self.time = False, 0, 0.0
        self.last_effect = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 2)
            self.rate, sample_format, self.stereo = pygame.mixer.get_init()
            if sample_format != -16:
                return
            pygame.mixer.set_num_channels(max(16, pygame.mixer.get_num_channels()))
            pygame.mixer.set_reserved(4)  # 0/1 engine, 2/3 music crossfade
            self.channels = [pygame.mixer.Channel(2), pygame.mixer.Channel(3)]
            self.enabled = True
        except pygame.error:
            pass

    def _sound(self, notes, beat, music=False):
        samples = array('h')
        length = int(self.rate * beat)
        for note in notes:
            for i in range(length):
                phase = i / self.rate
                envelope = min(1, i / max(1, self.rate * .01)) * (1 - i / length)
                value = math.sin(2 * math.pi * note * phase)
                if music:
                    value += .25 * math.sin(2 * math.pi * note / 2 * phase)
                samples.extend([int(value * envelope * (2600 if music else 6000))] * self.stereo)
        return pygame.mixer.Sound(buffer=samples)

    def set_volumes(self, bgm=None, sfx=None):
        if bgm is not None:
            self.bgm_volume = max(0, min(1, bgm))
        if sfx is not None:
            self.sfx_volume = max(0, min(1, sfx))
        if self.enabled:
            try:
                for channel in self.channels:
                    channel.set_volume(self.bgm_volume)
                for sound in self.sounds.values():
                    sound.set_volume(self.sfx_volume)
            except pygame.error:
                self.enabled = False

    def switch(self, theme):
        theme = theme if theme in self.THEMES else 'lobby'
        if theme == self.theme:
            return
        self.theme = theme
        if not self.enabled:
            return
        try:
            if theme not in self.music:
                self.music[theme] = self._sound(self.THEMES[theme], .24, True)
            self.channels[self.active].fadeout(400)
            self.active = 1 - self.active
            channel = self.channels[self.active]
            channel.set_volume(self.bgm_volume)
            channel.play(self.music[theme], loops=-1, fade_ms=400)
        except pygame.error:
            self.enabled = False

    def play(self, name):
        if not self.enabled or name not in self.EFFECTS:
            return
        if self.time - self.last_effect.get(name, -100) < .06:
            return
        try:
            if name not in self.sounds:
                self.sounds[name] = self._sound(self.EFFECTS[name], .07)
            self.sounds[name].set_volume(self.sfx_volume)
            self.sounds[name].play()
            self.last_effect[name] = self.time
        except pygame.error:
            self.enabled = False

    def update(self, dt):
        self.time += max(0, dt)

    def stop(self):
        if self.enabled:
            try:
                for channel in self.channels:
                    channel.stop()
                for sound in self.sounds.values():
                    sound.stop()
            except pygame.error:
                pass


class GameSoundBus:
    """Route game events through shared SFX mixing without owning lobby music."""
    def __init__(self, manager):
        self.manager = manager

    def play(self, events, now=None):
        for name in ([events] if isinstance(events, str) else events):
            self.manager.play(name)

    def stop(self):
        pass
