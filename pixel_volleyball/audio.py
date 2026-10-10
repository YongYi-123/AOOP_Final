"""Original short synth bleeps, generated locally without external samples."""
from array import array
import math
import pygame


class VolleySounds:
    def __init__(self):
        self.sounds, self.channels = {}, []
        config = pygame.mixer.get_init()
        if not config or config[1] != -16:
            return
        rate, _, channels = config
        for name, pitch in (("hit", 560), ("spike", 880), ("bounce", 240),
                            ("point", 660), ("win", 1040)):
            samples = array("h")
            length = int(rate * .07)
            for i in range(length):
                value = int(2500 * math.sin(2 * math.pi * pitch * i / rate) * (1 - i / length))
                samples.extend([value] * channels)
            self.sounds[name] = pygame.mixer.Sound(buffer=samples)

    def play(self, events):
        self.channels = [c for c in self.channels if c.get_busy()]
        for event in set(events):
            sound = self.sounds.get(event)
            if sound:
                channel = sound.play()
                if channel:
                    self.channels.append(channel)

    def stop(self):
        for sound in self.sounds.values():
            sound.stop()
        self.channels.clear()
