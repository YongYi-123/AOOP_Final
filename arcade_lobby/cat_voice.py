"""Cat meows: tiny synthesised placeholder sounds, one bank shared by all cats.

Every sound is generated in code (no samples ship), lazily on first use and
cached per (mixer format, kind, pitch), so each cat can have its own pitch.
To use real recordings instead, drop original or CC0 files named after a
kind (meow.ogg, mrrp.wav, ...) into assets/cats/ - a file replaces the synth
for that kind (at its recorded pitch). Without an audio device the cats are
silent; nothing else changes.
"""
import array
import math
import os
import random

import pygame

CAT_SOUND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "cats")
KINDS = ("meow", "mew", "mrrp", "nya", "prrr")
SYNTH_RATE = 22050
TAU = 2 * math.pi


# ---------------------------------------------------------------- synthesis
def _voice(dur, f_of, bright_of, amp_of, harmonics=5):
    """A gliding, buzzy tone. f_of/bright_of/amp_of map t in 0..1 to the
    frequency (Hz), harmonic roll-off (0..1, higher = brighter) and gain."""
    n = int(SYNTH_RATE * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / n
        phase += f_of(t) / SYNTH_RATE
        b = bright_of(t)
        s = w = 0.0
        k = 1.0
        for h in range(1, harmonics + 1):
            s += k * math.sin(TAU * h * phase)
            w += k
            k *= b
        out.append(amp_of(t) * s / w)
    return out


def _env(attack, power=0.7):
    return lambda t: min(1.0, t / attack) * (1 - t) ** power


def _meow(f0):        # "mee-ow": rises, then falls as the mouth closes
    return _voice(0.42, lambda t: f0 * (0.78 + 0.5 * math.sin(math.pi * t ** 0.8))
                  * (1 + 0.015 * math.sin(TAU * 6 * t)),
                  lambda t: 0.78 - 0.45 * t, _env(0.12))


def _mew(f0):         # short, high and soft
    return _voice(0.2, lambda t: f0 * 1.3 * (0.9 + 0.3 * math.sin(math.pi * t)),
                  lambda t: 0.5, _env(0.15, 0.9), harmonics=3)


def _nya(f0):         # quick bright chirp that drops at the end
    return _voice(0.3, lambda t: f0 * (1.0 + 0.55 * math.sin(math.pi * min(1.0, t * 1.4))),
                  lambda t: 0.8 - 0.2 * t, _env(0.08, 0.6))


def _mrrp(f0):        # rolled trill sliding up into a little question
    def amp(t):
        trill = 0.55 + 0.45 * math.sin(TAU * 8 * t) if t < 0.65 else 1.0
        return _env(0.1, 0.5)(t) * trill
    return _voice(0.3, lambda t: f0 * 0.7 * (1 + 0.45 * t * t), lambda t: 0.5, amp)


def _prrr(f0):        # low rumbling purr: soft pulses with a little breath
    rng = random.Random(5)
    base = _voice(0.7, lambda t: f0 * 0.16, lambda t: 0.6,
                  lambda t: min(1.0, t / 0.15) * min(1.0, (1 - t) / 0.25), harmonics=4)
    n = len(base)
    out = []
    for i, v in enumerate(base):
        pulse = abs(math.sin(math.pi * 26 * 0.7 * i / n)) ** 2
        out.append(0.8 * pulse * (v + 0.25 * rng.uniform(-1, 1)))
    return out


SYNTHS = {"meow": _meow, "mew": _mew, "mrrp": _mrrp, "nya": _nya, "prrr": _prrr}
BASE_HZ = 560


def synth_samples(kind, pitch=1.0):
    """Mono float samples (-1..1) at SYNTH_RATE, normalised and soft-clipped."""
    raw = SYNTHS[kind](BASE_HZ * pitch)
    peak = max(1e-6, max(abs(v) for v in raw))
    return [0.85 * math.tanh(1.4 * v / peak) for v in raw]


def _to_mixer_bytes(samples, freq, size, channels):
    """Resample (linear) to the mixer rate and pack into its sample format."""
    ratio = SYNTH_RATE / freq
    n = int(len(samples) / ratio)
    last = len(samples) - 1
    resampled = []
    for j in range(n):
        p = j * ratio
        i = int(p)
        a = samples[min(i, last)]
        b = samples[min(i + 1, last)]
        resampled.append(a + (b - a) * (p - i))
    if size == -16:
        data = array.array("h", (int(v * 32000) for v in resampled))
    elif size == 16:
        data = array.array("H", (int(v * 32000) + 32768 for v in resampled))
    elif size == 32:
        data = array.array("f", resampled)
    elif size == -8:
        data = array.array("b", (int(v * 126) for v in resampled))
    elif size == 8:
        data = array.array("B", (int(v * 126) + 128 for v in resampled))
    else:
        return None
    if channels > 1:
        data = array.array(data.typecode, (v for v in data for _ in range(channels)))
    return data.tobytes()


# ---------------------------------------------------------------- playback
class MeowBank:
    """Creates and caches cat sounds. The cache is keyed by the mixer format,
    so if a minigame re-opens the mixer differently the sounds are rebuilt."""

    def __init__(self, folder=CAT_SOUND_DIR):
        self.folder = folder
        self.sounds = {}
        self.failed = False

    def _mixer(self):
        if self.failed:
            return None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            return pygame.mixer.get_init()
        except (pygame.error, NotImplementedError):
            self.failed = True   # no audio device: stay silent
            return None

    def _file_for(self, kind):
        for ext in (".ogg", ".wav"):
            path = os.path.join(self.folder, kind + ext)
            if os.path.isfile(path):
                return path
        return None

    def get(self, kind, pitch=1.0):
        """The Sound for a kind at a pitch, or None when audio is unavailable."""
        fmt = self._mixer()
        if fmt is None:
            return None
        key = (fmt, kind, round(pitch, 2))
        if key not in self.sounds:
            self.sounds[key] = self._build(kind, pitch, fmt)
        return self.sounds[key]

    def _build(self, kind, pitch, fmt):
        try:
            path = self._file_for(kind)
            if path:
                return pygame.mixer.Sound(path)
            data = _to_mixer_bytes(synth_samples(kind, pitch), *fmt)
            return pygame.mixer.Sound(buffer=data) if data else None
        except pygame.error:
            return None


_bank = None


def meow_bank():
    global _bank
    if _bank is None:
        _bank = MeowBank()
    return _bank


class CatVoice:
    """One cat's voice: its pitch and loudness, plus a short cooldown so
    repeated requests can never stack the same cat's meows."""
    MIN_GAP = 0.35   # seconds

    def __init__(self, pitch=1.0, volume=0.45, bank=None):
        self.pitch = pitch
        self.volume = volume
        self.bank = bank
        self.channel = None
        self.sound = None
        self.last_time = None
        self.plays = 0   # sounds actually requested (handy for tests)

    def play(self, kind, now, loudness=1.0):
        """Meow at time `now` (seconds, any monotonic clock). Returns False if
        the cat meowed too recently, True otherwise (even when silent)."""
        if self.last_time is not None and now - self.last_time < self.MIN_GAP:
            return False
        self.last_time = now
        self.plays += 1
        sound = (self.bank or meow_bank()).get(kind, self.pitch)
        if sound is not None:
            channel = sound.play()
            if channel is not None:
                channel.set_volume(self.volume * loudness)
                self.channel, self.sound = channel, sound
        return True

    def stop(self):
        # only touch the channel if it is still playing this cat's meow
        if self.channel is not None:
            try:
                if self.channel.get_sound() is self.sound:
                    self.channel.fadeout(120)
            except pygame.error:
                pass
            self.channel = self.sound = None
