"""Audio: every sound is synthesised at start-up (no files). Fails soft: no mixer -> silent game.

Mix: master VOLUME scales everything; ENGINE_VOLUME and SFX_VOLUME then balance the engine against the
effects. Effects are mastered louder than the engine so a checkpoint jingle or crash always stands out.
"""
import array
import math
import random
import pygame
import settings as S

RATE = 22050
ENGINE_LOOP = 4410            # 0.2 s; every engine pitch has a whole number of cycles in it -> seamless loop
ENGINE_CYCLES = [6, 8, 12, 16, 20, 24, 30, 36, 44, 52, 60]   # 30 .. 300 Hz
LOW_EXTRA, BASE_SPAN = 1, 7   # the original 8 pitches are loops 1..8; 0 (lower) and 9-10 (higher) give cars room to shift
ENGINE_BASE, ENGINE_SLOPE = 0.45, 0.5                # engine gain = BASE + SLOPE * speed fraction


# ---- tiny synth ---------------------------------------------------------------------------------------
def _square(phase):
    return 1.0 if (phase % 1.0) < 0.5 else -1.0


def _saw(phase):
    return 2.0 * (phase % 1.0) - 1.0


def _tone(freq, dur, wave=_square, vol=0.8, fade=True):
    n = int(RATE * dur)
    return [vol * wave(freq * i / RATE) * ((1 - i / n) ** 1.2 if fade else 1.0) for i in range(n)]


def _noise_thump(dur=0.45, vol=1.0):
    rng, n = random.Random(1), int(RATE * dur)
    out = []
    for i in range(n):
        env = (1 - i / n) ** 1.6
        thump = math.sin(2 * math.pi * (40 + 60 * (1 - i / n)) * i / RATE)
        out.append(max(-1.0, min(1.0, vol * env * (0.75 * rng.uniform(-1, 1) + 0.7 * thump))))
    return out


def _seq(notes, dur, **kw):
    out = []
    for f in notes:
        out += _tone(f, dur, **kw)
    return out


def _engine_loop(cycles):
    """Buzzy saturated engine: many harmonics + sub-rumble, soft-clipped so it carries on small speakers."""
    raw = []
    for i in range(ENGINE_LOOP):
        p = cycles * i / ENGINE_LOOP
        wob = 1 + 0.3 * math.sin(2 * math.pi * 6 * i / ENGINE_LOOP)      # 30 Hz roughness (6 whole cycles)
        s = sum(math.sin(2 * math.pi * h * p) / h ** 0.8 for h in range(1, 11))
        s += 0.9 * math.sin(2 * math.pi * p / 2)                         # sub-rumble
        raw.append(s * wob)
    peak = max(abs(v) for v in raw)
    return [0.9 * math.tanh(2.2 * v / peak) for v in raw]                # tanh is periodic-safe: loop stays seamless


class Audio:
    # name -> (samples factory, base volume)
    # name -> (samples factory, base volume, category). The category picks its volume multiplier in settings.py.
    SFX = {
        "beep": (lambda: _tone(880, 0.16), 1.0, "race"),
        "go": (lambda: _tone(1047, 0.14) + _tone(1568, 0.5), 1.0, "race"),
        "checkpoint": (lambda: _seq((784, 988, 1175, 1568), 0.07), 1.0, "race"),
        "crash": (_noise_thump, 1.0, "collision"),
        "finish": (lambda: _seq((523, 659, 784, 1047), 0.12) + _tone(1047, 0.5), 1.0, "race"),
        "gameover": (lambda: _seq((392, 330, 262, 196), 0.2, wave=_saw, vol=1.0), 1.0, "race"),
        "pickup": (lambda: _seq((1047, 1319, 1568), 0.05, vol=0.7), 0.9, "item"),      # item box collected
        "item": (lambda: [v * (1 - i / 6000) for i, v in enumerate(_tone(300, 0.27, wave=_saw, vol=0.9, fade=False))], 0.9, "item"),
        "hit": (lambda: _seq((520, 380, 240, 160), 0.05, wave=_saw, vol=1.0), 1.0, "item"),   # hostile item landed on you
        "shield": (lambda: _seq((880, 1320), 0.06, vol=0.8), 0.9, "item"),                   # shield swallowed a hit
        "tick": (lambda: _tone(660, 0.04, vol=0.7), 0.8, "ui"),          # menu cursor
        "select": (lambda: _tone(880, 0.06, vol=0.7) + _tone(1320, 0.1, vol=0.7), 0.9, "ui"),
    }
    CATEGORY_VOLUME = {"ui": "UI_VOLUME", "collision": "COLLISION_VOLUME", "item": "ITEM_VOLUME", "race": "RACE_VOLUME"}
    MIN_GAP = {"ui": 0.04, "collision": 0.15, "item": 0.12, "race": 0.0}     # same sound can't retrigger sooner (s)
    REMOTE_GAP = 0.35
    DUCKERS = ("collision", "race")                                           # big events briefly lower the engine
    MAX_SFX_VOICES = 4

    def __init__(self, volume=None):
        self.enabled = False
        self.muted = False
        self.volume = S.VOLUME if volume is None else volume
        self.sounds, self.loops, self.channels = {}, [], []
        self.channel_loop = [None, None]
        self.clock = 0.0             # advanced by tick(dt); makes cooldowns deterministic (and testable)
        self.last_played = {}
        self.duck_left = 0.0
        try:
            pygame.mixer.quit()
            pygame.mixer.init(RATE, -16, 1, 512, allowedchanges=0)
            self.stereo = pygame.mixer.get_init()[2] == 2
            pygame.mixer.set_num_channels(8)
            pygame.mixer.set_reserved(2)                       # channels 0-1 belong to the engine
            self.channels = [pygame.mixer.Channel(0), pygame.mixer.Channel(1)]
            self.sounds = {name: (self._make(fn()), base) for name, (fn, base, _) in self.SFX.items()}
            self.loops = [self._make(_engine_loop(c)) for c in ENGINE_CYCLES]
            self.enabled = True
        except Exception as exc:                               # no device, no mixer module, etc.
            print(f"[audio] disabled: {exc}", flush=True)
            self.enabled = False

    def _make(self, samples):
        data = array.array("h", (int(max(-1.0, min(1.0, v)) * 32000) for v in samples))
        if self.stereo:
            data = array.array("h", (v for v in data for _ in (0, 1)))
        return pygame.mixer.Sound(buffer=data.tobytes())

    # ---- volume -----------------------------------------------------------------------------------
    @property
    def master(self):
        return 0.0 if self.muted else self.volume

    def change_volume(self, delta):
        self.volume = round(max(0.0, min(1.0, self.volume + delta)), 2)
        S.VOLUME = self.volume
        self.muted = False

    def toggle_mute(self):
        self.muted = not self.muted

    def tick(self, dt):
        """Advance the audio clock (cooldowns, ducking). Called once per frame by Game."""
        self.clock += dt
        self.duck_left = max(0.0, self.duck_left - dt)

    def sfx_gain(self, name, remote=False):
        """Volume of an effect: base x master x SFX x its category, capped so effects + engine can't clip."""
        base, category = self.SFX[name][1], self.SFX[name][2]
        gain = base * self.master * S.SFX_VOLUME * getattr(S, self.CATEGORY_VOLUME[category])
        if remote:
            gain *= S.REMOTE_ITEM_VOLUME
        return min(S.SFX_MAX_GAIN, gain)

    def _voices_busy(self):
        return sum(pygame.mixer.Channel(i).get_busy() for i in range(len(self.channels), pygame.mixer.get_num_channels()))

    def engine_gain(self, speed_frac):
        """Channel volume for the engine at a given speed fraction (before the pitch cross-fade)."""
        f = max(0.0, min(1.0, speed_frac))
        return min(1.0, self.master * S.ENGINE_VOLUME * (ENGINE_BASE + ENGINE_SLOPE * f))

    def engine_level(self, speed_frac, volume=1.0):
        """engine_gain with the car's own volume and the temporary duck while a big event plays."""
        duck = S.ENGINE_DUCK if self.duck_left > 0 else 1.0
        return min(1.0, self.engine_gain(speed_frac) * volume * duck)

    # ---- effects ----------------------------------------------------------------------------------
    def play(self, name):
        """Play an effect. "remote_<name>" is the quiet version used for AI racers' items.
        Identical sounds can't retrigger inside their cooldown, and busy mixers drop minor sounds."""
        remote = name.startswith("remote_")
        base = name[len("remote_"):] if remote else name
        if not self.enabled or self.master <= 0 or base not in self.sounds:
            return
        category = self.SFX[base][2]
        gap = self.REMOTE_GAP if remote else self.MIN_GAP[category]
        if self.clock - self.last_played.get(name, -9.0) < gap:
            return
        try:
            if category in ("ui", "item") and self._voices_busy() >= self.MAX_SFX_VOICES:
                return
            self.last_played[name] = self.clock
            sound = self.sounds[base][0]
            sound.set_volume(self.sfx_gain(base, remote))
            sound.play()
            if category in self.DUCKERS and not remote:
                self.duck_left = 0.4
        except pygame.error:
            pass

    # ---- engine: cross-fade between two neighbouring pre-rendered pitches -----------------------------
    def loop_position(self, speed_frac, pitch_shift=0.0):
        """Position along the pitch loops for a speed; pitch_shift moves a car's whole range up/down."""
        f = max(0.0, min(1.0, speed_frac))
        return max(0.0, min(len(ENGINE_CYCLES) - 1.0, LOW_EXTRA + f * BASE_SPAN + pitch_shift))

    def engine(self, speed_frac, on=True, pitch_shift=0.0, volume=1.0):
        if not self.enabled:
            return
        if not on:
            self.stop_engine()
            return
        try:
            n = len(self.loops)
            u = self.loop_position(speed_frac, pitch_shift)
            lo = min(int(u), n - 2)
            frac = u - lo
            # equal-power cross-fade keeps the loudness steady while the pitch changes
            weights = {lo: math.sqrt(1.0 - frac), lo + 1: math.sqrt(frac)}
            missing = [i for i in weights if i not in self.channel_loop]
            for c, ch in enumerate(self.channels):
                if self.channel_loop[c] not in weights:        # this channel's pitch is no longer needed
                    self.channel_loop[c] = missing.pop()
                    ch.play(self.loops[self.channel_loop[c]], loops=-1)
            level = self.engine_level(speed_frac, volume)
            for c, ch in enumerate(self.channels):
                ch.set_volume(level * weights[self.channel_loop[c]])
        except pygame.error:
            pass

    def stop_engine(self):
        if not self.enabled:
            return
        for c, ch in enumerate(self.channels):
            if self.channel_loop[c] is not None:
                ch.fadeout(250)
                self.channel_loop[c] = None
