"""Ambient sound beds for the arcade room (placeholder structure).

No audio ships with the prototype. Drop your own original or CC0 loops into
assets/ambience/ using the file names below and they will loop quietly
under the room; missing files are skipped silently. The mixer is only
initialised when at least one file exists, so nothing changes until then.
"""
import os

import pygame

AMBIENCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ambience")

# name -> (file name, volume 0..1)
LAYERS = {
    "machine_hum": ("machine_hum.ogg", 0.20),   # low cabinet/fridge drone
    "arcade_buzz": ("arcade_buzz.ogg", 0.12),   # distant bleeps and chatter
    "rain": ("rain.ogg", 0.25),                 # soft rain on the window
}


class AmbienceManager:
    """Loops each available layer on its own channel; pause/resume follow the
    arcade room scene (paused while a minigame is open)."""

    def __init__(self, folder=AMBIENCE_DIR, layers=LAYERS):
        self.sounds = {}
        self.channels = {}
        self.mix = {}
        paths = {name: (os.path.join(folder, fname), vol) for name, (fname, vol) in layers.items()}
        available = {n: pv for n, pv in paths.items() if os.path.isfile(pv[0])}
        if not available:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            for name, (path, volume) in available.items():
                sound = pygame.mixer.Sound(path)
                sound.set_volume(volume)
                self.sounds[name] = sound
        except pygame.error:
            self.sounds.clear()   # no audio device: stay silent

    def set_mix(self, mix):
        """Set each layer's volume for the room now on screen; layers the mix
        does not name go quiet. Rooms differ only in this mix, so nothing
        restarts when you walk through a door."""
        self.mix = dict(mix)
        for name, sound in self.sounds.items():
            sound.set_volume(self.mix.get(name, 0.0))

    @property
    def enabled(self):
        return bool(self.sounds)

    def start(self):
        for name, sound in self.sounds.items():
            if name not in self.channels:
                self.channels[name] = sound.play(loops=-1, fade_ms=1500)

    def pause(self):
        for channel in self.channels.values():
            if channel:
                channel.pause()

    def resume(self):
        for channel in self.channels.values():
            if channel:
                channel.unpause()

    def set_volume(self, name, volume):
        if name in self.sounds:
            self.sounds[name].set_volume(volume)

    def stop(self):
        for channel in self.channels.values():
            if channel:
                channel.fadeout(500)
        self.channels.clear()
