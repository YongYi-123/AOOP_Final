"""Original music and sound-effect generator for the arcade hub.

Everything the hub plays is composed here from scratch (notes written by hand
below, rendered with plain square / pulse / triangle / sine voices and noise),
so there is nothing to license: the WAV files in assets/music and assets/sfx
are generated output of THIS file and may be redistributed with the game.

Run  `python audio_synth.py`  to (re)write the assets. The game itself only
loads the WAVs (audio_manager.py) and falls back to short synthesized beeps if a
file is missing, so this module is never imported while playing.

One musical identity runs through all four room themes: the same chiptune
instrument set (pulse lead, triangle bass, noise percussion), a short rising
"power-on" arpeggio at the top of every loop, and a 16th-note arpeggio hook built
from each chord's own notes.

    arcade_floor  A minor synthwave, 120 BPM
    prize_plaza   C major cheerful retro electronic, 132 BPM
    lucky_corner  swung electronic casino jazz, 104 BPM
    home          cozy lo-fi chiptune, 76 BPM

and the same instrument family carries the minigame themes, each with its own key,
tempo and groove (see the MINIGAME section below).
"""
import math
import os
import random
import struct
import wave

RATE = 22050
HERE = os.path.dirname(os.path.abspath(__file__))
MUSIC_DIR = os.path.join(HERE, "assets", "music")
SFX_DIR = os.path.join(HERE, "assets", "sfx")

_NAMES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(name):
    """'A5' / 'C#6' / 'Bb3' -> MIDI note number."""
    n = _NAMES[name[0]]
    rest = name[1:]
    while rest and rest[0] in "#b":
        n += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    return 12 * (int(rest) + 1) + n


def hz(note):
    return 440.0 * 2 ** ((note - 69) / 12)


# ------------------------------------------------------------------ voices
def _wave(kind, ph):
    f = ph - math.floor(ph)
    if kind == "sine":
        return math.sin(6.283185307 * f)
    if kind == "tri":
        return 4 * abs(f - 0.5) - 1
    if kind == "saw":
        return 2 * f - 1
    if kind == "sq":
        return 1.0 if f < 0.5 else -1.0
    if kind == "p25":
        return 1.0 if f < 0.25 else -1.0
    if kind == "p12":
        return 1.0 if f < 0.125 else -1.0
    if kind == "bell":
        return math.sin(6.283185307 * f) + 0.4 * math.sin(6.283185307 * 2.01 * f) + 0.15 * math.sin(6.283185307 * 3.97 * f)
    raise ValueError(kind)


class Mix:
    """A mono float buffer of `seconds`; notes that run past the end wrap round to
    the start, so a track loops without a click."""

    def __init__(self, seconds, clean=False):
        self.n = int(RATE * seconds)
        self.buf = [0.0] * self.n
        self.clean = clean          # one-shots: remove the DC offset (pulse waves have one) and fade in, so no click

    def note(self, start, dur, freq, kind, vol, attack=0.005, release=0.06, vibrato=0.0, slide=0.0):
        """Add one tone. `slide`: Hz change per second (pitch glide)."""
        n0, count = int(start * RATE), int((dur + release) * RATE)
        atk, rel = max(1, int(attack * RATE)), int(release * RATE)
        body = int(dur * RATE)
        buf, size, ph = self.buf, self.n, 0.0
        for i in range(count):
            if i < atk:
                env = i / atk
            elif i > body:
                env = max(0.0, 1 - (i - body) / max(1, rel))
            else:
                env = 1.0
            t = i / RATE
            f = freq + slide * t
            if vibrato:
                f *= 1 + 0.006 * math.sin(6.283185307 * vibrato * t)
            ph += f / RATE
            buf[(n0 + i) % size] += _wave(kind, ph) * env * vol

    def noise(self, start, dur, vol, decay=30.0, bright=1.0, seed=1):
        """A burst of noise (hat / snare / brush). `bright` < 1 darkens it."""
        rng = random.Random(seed)
        n0, count = int(start * RATE), int(dur * RATE)
        buf, size, last = self.buf, self.n, 0.0
        for i in range(count):
            raw = rng.random() * 2 - 1
            last += (raw - last) * bright
            buf[(n0 + i) % size] += last * vol * math.exp(-decay * i / RATE)

    def kick(self, start, vol=0.5):
        n0, count = int(start * RATE), int(0.16 * RATE)
        buf, size, ph = self.buf, self.n, 0.0
        for i in range(count):
            t = i / RATE
            ph += (48 + 110 * math.exp(-28 * t)) / RATE
            buf[(n0 + i) % size] += math.sin(6.283185307 * ph) * vol * math.exp(-17 * t)

    def finish(self, lowpass=0.0, peak=0.8, fade=0.0, rms=None):
        """The 16-bit samples, normalised (and optionally warmed by a one-pole low-pass).
        `rms` (dBFS): normalise to this average loudness instead of to `peak`, then soft-limit to `peak`,
        so every track in a family sits at the same perceived level."""
        buf = self.buf
        if self.clean or rms is not None:
            mean = sum(buf) / len(buf)
            buf = self.buf = [x - mean for x in buf]
        if self.clean:
            for i in range(min(len(buf), int(0.003 * RATE))):
                buf[i] *= i / (0.003 * RATE)
        if lowpass:
            y = 0.0
            for i, x in enumerate(buf):
                y += (x - y) * (1 - lowpass)
                buf[i] = y
        if rms is not None:
            level = math.sqrt(sum(x * x for x in buf) / len(buf)) or 1e-9
            k = 10 ** (rms / 20) / level * 32767
            out = [int(peak * 32767 * math.tanh(x * k / (peak * 32767))) for x in buf]
        else:
            top = max(max(buf), -min(buf), 1e-9)
            k = peak * 32767 / top
            out = [int(x * k) for x in buf]
        tail = int(fade * RATE)                             # a short fade-out so a one-shot never clicks at its end
        for i in range(min(tail, len(out))):
            out[-1 - i] = int(out[-1 - i] * i / tail)
        return out


def write_wav(path, samples):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples))


# ------------------------------------------------------------------ music helpers
CHORDS = {"": (0, 4, 7), "m": (0, 3, 7), "m7": (0, 3, 7, 10), "maj7": (0, 4, 7, 11), "7": (0, 4, 7, 10),
          "m9": (0, 3, 7, 10, 14), "9": (0, 4, 7, 10, 14), "maj9": (0, 4, 7, 11, 14), "m7b5": (0, 3, 6, 10),
          "dim": (0, 3, 6, 9), "5": (0, 7, 12)}


def chord_tones(symbol):
    """('Am' | 'Fmaj7' | 'G7' ...) -> (root name, [semitone offsets])."""
    root = symbol[:2] if len(symbol) > 1 and symbol[1] in "#b" else symbol[:1]
    return root, CHORDS[symbol[len(root):]]


def grid(mix, start, step, pattern, kind, vol, octave_shift=0, **kw):
    """Play a space separated 'note . note' pattern, one slot per `step` seconds
    ('.' rests, '-' holds the previous note)."""
    tokens = pattern.split()
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in (".", "-"):
            i += 1
            continue
        length = 1
        while i + length < len(tokens) and tokens[i + length] == "-":
            length += 1
        mix.note(start + i * step, length * step * 0.92, hz(midi(tok) + octave_shift), kind, vol, **kw)
        i += length


def signature(mix, start, root, minor=False, vol=0.16):
    """The rising 'power-on' bell arpeggio that opens every theme."""
    third = 3 if minor else 4
    for k, off in enumerate((0, third, 7, 12)):
        mix.note(start + k * 0.1, 0.18, hz(root + off + 12), "bell", vol, attack=0.003, release=0.35)


def arpeggio(mix, start, step, tones, root, kind, vol, count, octave=12):
    for k in range(count):
        mix.note(start + k * step, step * 0.8, hz(root + tones[k % len(tones)] + octave * (k // len(tones) % 2)),
                 kind, vol, attack=0.003, release=0.03)


# ------------------------------------------------------------------ the four themes
def arcade_floor():
    bpm, bars = 120, 16
    beat = 60 / bpm
    bar = beat * 4
    m = Mix(bars * bar)
    prog = ["Am", "F", "C", "G"] * 4
    roots = {"Am": "A", "F": "F", "C": "C", "G": "G"}
    lead = ["A5 . C6 . E6 . D6 C6", "C6 . A5 . F5 . A5 C6", "E6 . G6 . E6 . D6 C6", "D6 . B5 . G5 . B5 D6"]
    for b in range(bars):
        t0, sym = b * bar, prog[b]
        root, tones = chord_tones(sym)
        r = midi(root + "2")
        for k in range(8):                                  # pulsing 8th-note bass
            m.note(t0 + k * beat / 2, beat / 2 * 0.85, hz(r + (12 if k % 4 == 3 else 0)), "sq", 0.2, release=0.03)
        arpeggio(m, t0, beat / 4, tones, midi(root + "4"), "p25", 0.07, 16)     # 16th-note arp hook
        for off in tones:                                   # soft pad
            m.note(t0, bar * 0.98, hz(midi(root + "3") + off), "tri", 0.05, attack=0.25, release=0.2)
        for beat_i in range(4):
            m.kick(t0 + beat_i * beat, 0.5)
            m.noise(t0 + beat_i * beat + beat / 2, 0.05, 0.12, decay=70, seed=b * 9 + beat_i)       # off-beat hat
        for beat_i in (1, 3):
            m.noise(t0 + beat_i * beat, 0.16, 0.2, decay=22, bright=0.6, seed=b * 3 + beat_i)       # snare
        if b >= 4 and b not in (8, 9, 10, 11) or b >= 12:   # the lead joins after the intro, rests in the bridge
            grid(m, t0, beat / 2, lead[b % 4], "p12", 0.13, attack=0.004, release=0.08, vibrato=5.5)
    signature(m, 0.0, midi("A3"), minor=True)
    return m.finish(lowpass=0.18)


def prize_plaza():
    bpm, bars = 132, 16
    beat = 60 / bpm
    bar = beat * 4
    m = Mix(bars * bar)
    prog = ["C", "G", "Am", "F"] * 3 + ["F", "G", "C", "C"]
    lead = ["G5 . E5 G5 C6 . G5 .", "B5 . G5 B5 D6 . B5 .", "A5 . C6 E6 . C6 A5 .", "A5 C6 F6 . E6 D6 C6 ."]
    for b in range(bars):
        t0, sym = b * bar, prog[b]
        root, tones = chord_tones(sym)
        r = midi(root + "2")
        for k in range(8):                                  # bouncy octave bass
            m.note(t0 + k * beat / 2, beat / 2 * 0.7, hz(r + (12 if k % 2 else 0)), "tri", 0.34, release=0.03)
        for off in tones:                                   # off-beat stabs
            for beat_i in (1, 3):
                m.note(t0 + beat_i * beat + beat / 2, beat * 0.2, hz(midi(root + "4") + off), "p25", 0.06, release=0.04)
        arpeggio(m, t0, beat / 4, tones + (12,), midi(root + "4"), "sq", 0.04, 16)
        for beat_i in range(4):
            m.kick(t0 + beat_i * beat, 0.46 if beat_i % 2 == 0 else 0.0)
            m.noise(t0 + beat_i * beat + beat / 2, 0.04, 0.1, decay=80, seed=b * 7 + beat_i)
        for beat_i in (1, 3):
            m.noise(t0 + beat_i * beat, 0.1, 0.22, decay=34, bright=0.8, seed=b * 5 + beat_i)       # clap
        if b >= 2 and b != 15:
            grid(m, t0, beat / 2, lead[b % 4], "p25", 0.12, attack=0.004, release=0.06, vibrato=6)
    signature(m, 0.0, midi("C4"))
    return m.finish(lowpass=0.12)


def lucky_corner():
    bpm, bars = 104, 16
    beat = 60 / bpm
    bar = beat * 4
    swing = 0.62                                            # off-beat 8ths sit late
    m = Mix(bars * bar)
    prog = ["Dm7", "G7", "Cmaj7", "A7", "Dm7", "G7", "Cmaj7", "Cmaj7"] * 2
    lead = ["F5 . A5 . D6 . C6 A5", "B5 . D6 . G5 . F5 .", "E5 . G5 . B5 . C6 .", "C#6 . E6 . A5 . G5 E5",
            "D6 . F6 . E6 . D6 C6", "B5 . G5 . D5 . F5 G5", "C6 . B5 A5 G5 . E5 .", "C5 . . . . . . ."]
    for b in range(bars):
        t0, sym = b * bar, prog[b]
        root, tones = chord_tones(sym)
        r = midi(root + "2")
        walk = (0, tones[1] if len(tones) > 1 else 4, 7, 9 if b % 2 else 5)     # a walking line, one note per beat
        for k, off in enumerate(walk):
            m.note(t0 + k * beat, beat * 0.9, hz(r + off + (12 if r + off < midi("E2") else 0)), "tri", 0.4, release=0.05)
        for beat_i in (1, 3):                                # jazzy comping chords on 2 and 4
            for off in tones:
                m.note(t0 + beat_i * beat + (swing - 0.5) * beat, beat * 0.28, hz(midi(root + "3") + off + 12),
                       "p25", 0.05, release=0.05)
        for k in range(8):                                   # swung "ride" ticks
            late = (swing - 0.5) * beat if k % 2 else 0
            m.noise(t0 + k * beat / 2 + late, 0.05, 0.1 if k % 2 == 0 else 0.07, decay=60, bright=0.9, seed=b * 11 + k)
        m.kick(t0, 0.3)
        m.kick(t0 + 2 * beat, 0.24)
        for beat_i in (1, 3):
            m.noise(t0 + beat_i * beat, 0.12, 0.12, decay=26, bright=0.5, seed=b * 13 + beat_i)       # brush snare
        step = beat / 2
        pattern = lead[b % 8].split()
        for i, tok in enumerate(pattern):                    # the lead plays the swung grid
            if tok in (".", "-"):
                continue
            late = (swing - 0.5) * beat if i % 2 else 0
            m.note(t0 + i * step + late, step * 0.85, hz(midi(tok) + (12 if b >= 8 else 0)), "bell", 0.12,
                   attack=0.004, release=0.3)
    signature(m, 0.0, midi("C4"))
    return m.finish(lowpass=0.1)


def home():
    bpm, bars = 76, 12
    beat = 60 / bpm
    bar = beat * 4
    m = Mix(bars * bar)
    prog = ["Fmaj7", "Em7", "Dm7", "Cmaj7"] * 2 + ["Fmaj7", "Em7", "Dm7", "G7"]
    lead = ["A5 . . C6 . . E6 .", "D6 . . B5 . . G5 .", "F5 . A5 . . D6 . .", "E6 . . . D6 . C6 ."]
    rng = random.Random(7)
    for b in range(bars):
        t0, sym = b * bar, prog[b]
        root, tones = chord_tones(sym)
        r = midi(root + "2")
        m.note(t0, beat * 1.9, hz(r), "tri", 0.4, release=0.1)                     # lazy half-note bass
        m.note(t0 + 2 * beat, beat * 1.6, hz(r + (7 if b % 2 else 0)), "tri", 0.34, release=0.1)
        for k, off in enumerate(tones):                      # a slow rolled chord
            m.note(t0 + k * beat * 0.12, bar * 0.95, hz(midi(root + "3") + off), "tri", 0.07, attack=0.15, release=0.4)
        for k in range(8):                                   # soft broken-chord plucks
            m.note(t0 + k * beat / 2, beat * 0.4, hz(midi(root + "4") + tones[k % len(tones)]), "p12", 0.04,
                   attack=0.004, release=0.12)
        m.kick(t0, 0.36)
        m.kick(t0 + 2.5 * beat, 0.28)
        for beat_i in (1, 3):
            m.noise(t0 + beat_i * beat + 0.02, 0.09, 0.14, decay=40, bright=0.45, seed=b * 17 + beat_i)   # rim
        for k in range(8):
            m.noise(t0 + k * beat / 2, 0.03, 0.05, decay=90, bright=0.8, seed=b * 19 + k)
        if b >= 2:
            grid(m, t0, beat / 2, lead[b % 4], "sine", 0.17, attack=0.02, release=0.35, vibrato=4.5)
    for _ in range(90):                                      # vinyl crackle
        m.noise(rng.random() * bars * bar, 0.004, 0.06 + rng.random() * 0.05, decay=200, seed=rng.randint(0, 9999))
    signature(m, 0.0, midi("F3"), vol=0.12)
    return m.finish(lowpass=0.38)


# ------------------------------------------------------------------ MINIGAME themes
# Every game gets its own key, tempo, groove and lead voice; all are 16 bars, loop without a seam
# (notes wrap round the end) and are normalised to the same average loudness (MINIGAME_RMS).
MINIGAME_RMS = -14.5


def _drums(m, t0, beat, b, kick=(0, 1, 2, 3), snare=(1, 3), hat=8, kick_vol=0.5, snare_vol=0.2, hat_vol=0.08, seed=0):
    for k in kick:
        m.kick(t0 + k * beat, kick_vol)
    for k in snare:
        m.noise(t0 + k * beat, 0.15, snare_vol, decay=24, bright=0.65, seed=seed + b * 3 + k)
    for k in range(hat):
        m.noise(t0 + k * beat * 4 / hat + (beat * 2 / hat if hat == 4 else 0), 0.04, hat_vol, decay=75, seed=seed + b * 11 + k)


def retro_racer():
    """Fast synthwave: D minor, 140 BPM. Pumping 16th bass, four-on-the-floor, a soaring pulse lead,
    and a rising engine rev as the loop starts."""
    bpm, bars = 140, 16
    beat = 60 / bpm
    bar = beat * 4
    m = Mix(bars * bar)
    prog = ["Dm", "Bb", "F", "C"] * 3 + ["Dm", "Bb", "C", "A"]
    lead = {"Dm": "A5 . D6 . F6 . E6 D6", "Bb": "D6 . F6 . Bb5 . C6 D6", "F": "C6 . F6 . A6 . G6 F6",
            "C": "E6 . G6 . E6 . D6 C6", "A": "C#6 . E6 . A6 . G6 E6"}
    for b in range(bars):
        t0, sym = b * bar, prog[b]
        root, tones = chord_tones(sym if sym != "A" else "A")
        r = midi(root + "2")
        for k in range(16):                                           # driving 16th bass with octave pops
            m.note(t0 + k * beat / 4, beat / 4 * 0.8, hz(r + (12 if k % 4 == 3 else 0)), "saw", 0.16, release=0.02)
        arpeggio(m, t0, beat / 4, tones + (12,), midi(root + "4"), "p25", 0.05, 16)
        for off in tones:
            m.note(t0, bar * 0.98, hz(midi(root + "3") + off), "saw", 0.02, attack=0.3, release=0.2)
        _drums(m, t0, beat, b, kick_vol=0.52, snare_vol=0.22, seed=100)
        for k in (0.5, 1.5, 2.5, 3.5):
            m.noise(t0 + k * beat, 0.1, 0.07, decay=40, bright=0.9, seed=b * 5 + int(k * 2))     # open hat
        if b >= 2:
            grid(m, t0, beat / 2, lead[sym], "p12", 0.12, attack=0.004, release=0.07, vibrato=5.5)
    m.note(0.0, 1.6, 70, "saw", 0.07, attack=0.2, release=0.3, slide=260)                       # engine rev
    signature(m, 1.7, midi("D3"), minor=True, vol=0.1)
    return m.finish(lowpass=0.36, rms=MINIGAME_RMS)


def pixel_volleyball():
    """Upbeat chiptune: G major, 148 BPM. Bouncy octave bass, a woodblock 'ball' on every beat, bright hook."""
    bpm, bars = 148, 16
    beat = 60 / bpm
    bar = beat * 4
    m = Mix(bars * bar)
    prog = ["G", "Em", "C", "D"] * 3 + ["C", "D", "G", "G"]
    lead = {"G": "B5 . D6 B5 G6 . D6 .", "Em": "G5 . B5 E6 . D6 B5 .", "C": "E6 . C6 E6 G6 . E6 C6", "D": "F#6 . D6 A5 D6 . F#6 A6"}
    for b in range(bars):
        t0, sym = b * bar, prog[b]
        root, tones = chord_tones(sym)
        r = midi(root + "2")
        for k in range(8):
            m.note(t0 + k * beat / 2, beat / 2 * 0.65, hz(r + (12 if k % 2 else 0)), "tri", 0.34, release=0.03)
        for beat_i in range(4):                                       # the bouncing ball
            m.note(t0 + beat_i * beat, 0.05, 780 if beat_i % 2 else 520, "sine", 0.1, release=0.04, slide=-1500)
        for beat_i in (1, 3):
            for off in tones:
                m.note(t0 + beat_i * beat + beat / 2, beat * 0.22, hz(midi(root + "4") + off), "p25", 0.05, release=0.04)
        _drums(m, t0, beat, b, kick=(0, 2), snare=(1, 3), hat=8, kick_vol=0.44, snare_vol=0.18, hat_vol=0.06, seed=200)
        if b >= 1:
            grid(m, t0, beat / 2, lead[sym], "sq" if b % 4 == 3 else "p25", 0.1, attack=0.004, release=0.06, vibrato=5)
    signature(m, 0.0, midi("G3"), vol=0.12)
    return m.finish(lowpass=0.22, rms=MINIGAME_RMS)


def cat_minesweeper():
    """Cat Territory: cute, playful puzzle pop. C major pentatonic, 108 BPM, plucky glockenspiel, pizzicato bass,
    ticking shaker, and an occasional tiny 'mew' glide."""
    bpm, bars = 108, 16
    beat = 60 / bpm
    bar = beat * 4
    m = Mix(bars * bar)
    prog = ["C", "Am", "F", "G"] * 2 + ["C", "Em", "F", "G", "Am", "F", "G", "C"]
    hook = ["E6 G6 E6 C6 . D6 . .", "C6 . E6 . A5 . C6 .", "A5 C6 F6 . E6 C6 . .", "D6 . G6 . B5 D6 . ."]
    for b in range(bars):
        t0, sym = b * bar, prog[b]
        root, tones = chord_tones(sym)
        r = midi(root + "2")
        for k, off in enumerate((0, 7, 12, 7)):                       # pizzicato bass, one pluck a beat
            m.note(t0 + k * beat, beat * 0.3, hz(r + off), "tri", 0.4, release=0.05)
        for k in range(8):                                            # mallet comping
            m.note(t0 + k * beat / 2, beat * 0.2, hz(midi(root + "4") + tones[(k * 2) % len(tones)] + (12 if k % 3 == 2 else 0)),
                   "bell", 0.045, attack=0.003, release=0.12)
        for k in range(16):                                           # shaker
            m.noise(t0 + k * beat / 4, 0.02, 0.04 if k % 2 else 0.06, decay=120, bright=0.9, seed=b * 17 + k)
        m.kick(t0, 0.3)
        m.kick(t0 + 2 * beat, 0.22)
        m.noise(t0 + beat * 3, 0.06, 0.12, decay=45, bright=0.5, seed=b)                  # rim
        if b >= 2:
            grid(m, t0, beat / 2, hook[(b if b < 8 else b + 1) % 4], "bell", 0.14, attack=0.003, release=0.2)
        if b in (7, 15):                                              # a tiny mew
            m.note(t0 + 3 * beat, 0.16, 700, "sine", 0.07, release=0.05, vibrato=9, slide=900)
    signature(m, 0.0, midi("C4"), vol=0.12)
    return m.finish(lowpass=0.2, rms=MINIGAME_RMS)


def galaxy_defender():
    """Space arcade electro: E minor, 146 BPM. Pulsing saw bass, an up-down 16th arp, 16th hats, laser sweeps."""
    bpm, bars = 146, 16
    beat = 60 / bpm
    bar = beat * 4
    m = Mix(bars * bar)
    prog = ["Em", "C", "G", "D"] * 3 + ["Em", "C", "D", "B"]
    lead = {"Em": "B5 . E6 G6 . F#6 E6 .", "C": "G5 . C6 E6 . D6 C6 .", "G": "B5 . D6 G6 . F#6 D6 .",
            "D": "A5 . D6 F#6 . E6 D6 .", "B": "F#5 . B5 D#6 . C#6 B5 ."}
    for b in range(bars):
        t0, sym = b * bar, prog[b]
        root, tones = chord_tones(sym if sym != "B" else "B")
        r = midi(root + "2")
        for k in range(8):                                            # pulsing eighth bass
            m.note(t0 + k * beat / 2, beat / 2 * 0.8, hz(r + (12 if k in (3, 7) else 0)), "saw", 0.17, release=0.03)
        up_down = list(tones) + [12] + list(reversed(tones))
        for k in range(16):                                           # shimmering arp
            m.note(t0 + k * beat / 4, beat / 4 * 0.75, hz(midi(root + "4") + up_down[k % len(up_down)]), "sq", 0.035,
                   attack=0.003, release=0.03)
        _drums(m, t0, beat, b, kick_vol=0.5, snare_vol=0.2, hat=16, hat_vol=0.05, seed=300)
        if b >= 2:
            grid(m, t0, beat / 2, lead[sym], "p12", 0.11, attack=0.004, release=0.07, vibrato=6)
        if b % 4 == 0:                                                # a laser sweep opens each phrase
            m.note(t0, 0.35, 1900, "sine", 0.05, release=0.05, slide=-4200)
    signature(m, 0.0, midi("E3"), minor=True, vol=0.1)
    return m.finish(lowpass=0.34, rms=MINIGAME_RMS)


def neon21():
    """NEON 21: smooth electronic casino lounge. A minor 9ths, 90 BPM, electric-piano comping, walking bass, brushes."""
    bpm, bars = 90, 16
    beat = 60 / bpm
    bar = beat * 4
    swing = 0.58
    m = Mix(bars * bar)
    prog = ["Am9", "D9", "Gmaj9", "Cmaj9", "Fmaj9", "Bm7b5", "E7", "Am9"] * 2
    lead = ["E6 . . D6 . C6 . .", "F#6 . . A6 . . G6 .", "D6 . B5 . . D6 . .", "E6 . . . G6 . E6 .",
            "A6 . . G6 . F6 . .", "F6 . D6 . . B5 . .", "G#5 . B5 . D6 . E6 .", "C6 . . . . . . ."]
    for b in range(bars):
        t0, sym = b * bar, prog[b]
        root, tones = chord_tones(sym)
        r = midi(root + "2")
        for k, off in enumerate((0, tones[1], 7, 9 if b % 2 else 5)):          # walking bass
            m.note(t0 + k * beat, beat * 0.92, hz(r + off + (12 if r + off < midi("E2") else 0)), "tri", 0.42, release=0.06)
        for when in (0.0, 1.5 + (swing - 0.5), 2.5):                       # e-piano comping
            for off in tones:
                m.note(t0 + when * beat, beat * 0.9, hz(midi(root + "3") + off + 12), "bell", 0.035, attack=0.01, release=0.4)
        for off in tones[:4]:                                              # warm pad
            m.note(t0, bar, hz(midi(root + "3") + off), "tri", 0.03, attack=0.4, release=0.4)
        for k in range(8):                                                 # brushes
            late = (swing - 0.5) * beat if k % 2 else 0
            m.noise(t0 + k * beat / 2 + late, 0.05, 0.07 if k % 2 == 0 else 0.045, decay=55, bright=0.55, seed=b * 21 + k)
        m.kick(t0, 0.26)
        m.noise(t0 + 1 * beat, 0.14, 0.08, decay=22, bright=0.4, seed=b * 3)
        m.noise(t0 + 3 * beat, 0.14, 0.08, decay=22, bright=0.4, seed=b * 3 + 1)
        if b >= 1:
            for i, tok in enumerate(lead[b % 8].split()):
                if tok in (".", "-"):
                    continue
                late = (swing - 0.5) * beat if i % 2 else 0
                m.note(t0 + i * beat / 2 + late, beat * 0.7, hz(midi(tok)), "sine", 0.12, attack=0.015, release=0.4, vibrato=5)
    signature(m, 0.0, midi("A3"), minor=True, vol=0.1)
    return m.finish(lowpass=0.35, rms=MINIGAME_RMS)


def lucky_wheel():
    """SPIN: game-show bounce. C major then a key lift to D, 126 BPM. Oom-pah bass, brassy stabs, snare-roll fills,
    wheel-tick runs that slow down, and a 'ding' on the downbeats."""
    bpm, bars = 126, 16
    beat = 60 / bpm
    bar = beat * 4
    m = Mix(bars * bar)
    prog = ["C", "F", "G", "C", "C", "F", "G", "G"] + ["D", "G", "A", "D", "D", "G", "A", "A"]
    hook = ["E6 E6 G6 . E6 . C6 .", "F6 F6 A6 . F6 . C6 .", "G6 G6 B6 . G6 . D6 .", "E6 G6 C7 . G6 . E6 ."]
    for b in range(bars):
        t0, sym = b * bar, prog[b]
        root, tones = chord_tones(sym)
        r = midi(root + "2")
        for k, off in ((0, 0), (2, 7)):                                    # oom
            m.note(t0 + k * beat, beat * 0.5, hz(r + off), "tri", 0.45, release=0.04)
        for k in (1, 3):                                                   # pah
            for off in tones:
                m.note(t0 + k * beat, beat * 0.3, hz(midi(root + "4") + off), "sq", 0.04, release=0.05)
                m.note(t0 + k * beat, beat * 0.3, hz(midi(root + "3") + off), "saw", 0.025, release=0.05)
        m.kick(t0, 0.4)
        m.kick(t0 + 2 * beat, 0.4)
        for k in (1, 3):
            m.noise(t0 + k * beat, 0.12, 0.18, decay=26, bright=0.7, seed=b * 7 + k)
        for k in range(8):
            m.noise(t0 + k * beat / 2, 0.03, 0.05, decay=90, seed=b * 13 + k)
        m.note(t0, 0.5, hz(midi(root + "6")), "bell", 0.07, attack=0.002, release=0.5)           # ding
        if b % 4 == 3:                                                     # snare-roll fill into the next phrase
            for k in range(8):
                m.noise(t0 + 3 * beat + k * beat / 8, 0.05, 0.08 + 0.015 * k, decay=50, bright=0.7, seed=b * 29 + k)
        if b % 8 == 7:                                                     # the wheel slows to a stop
            t, gap = t0 + 2 * beat, 0.05
            while t < t0 + bar - 0.05:
                m.note(t, 0.012, 2200, "sine", 0.06, attack=0.001, release=0.01)
                t, gap = t + gap, gap * 1.28
        elif b >= 1:
            grid(m, t0, beat / 2, hook[b % 4], "sq", 0.085, attack=0.01, release=0.08, vibrato=5.5)
    signature(m, 0.0, midi("C4"), vol=0.12)
    return m.finish(lowpass=0.22, rms=MINIGAME_RMS)


def high_low():
    """HI-LO: suspenseful but playful. A minor, 100 BPM. Chromatic pizzicato bass, a ticking woodblock, a lub-dub
    heartbeat, and a call-and-response lead - a HIGH phrase answered by a LOW one."""
    bpm, bars = 100, 16
    beat = 60 / bpm
    bar = beat * 4
    m = Mix(bars * bar)
    prog = ["Am", "Am", "Dm", "E7", "Am", "F", "Dm", "E7"] * 2
    walk = {"Am": "A2 . A2 . Bb2 . B2 .", "Dm": "D3 . D3 . Eb3 . E3 .", "E7": "E2 . E2 . F2 . F#2 .", "F": "F2 . F2 . F#2 . G2 ."}
    high = "E6 . D#6 . E6 . G6 ."
    low = "E5 . D#5 . D5 . C5 ."
    for b in range(bars):
        t0, sym = b * bar, prog[b]
        root, tones = chord_tones(sym)
        grid(m, t0, beat / 2, walk[sym], "tri", 0.42, release=0.04, attack=0.004)
        for k in range(4):                                                 # tick-tock woodblock
            m.note(t0 + k * beat, 0.03, 1250 if k % 2 == 0 else 880, "sine", 0.1, attack=0.001, release=0.025, slide=-900)
        m.kick(t0, 0.36)                                                   # lub
        m.kick(t0 + 0.4 * beat, 0.22)                                      # dub
        m.kick(t0 + 2 * beat, 0.3)
        m.kick(t0 + 2.4 * beat, 0.18)
        m.noise(t0 + 3 * beat + 0.02, 0.07, 0.1, decay=45, bright=0.7, seed=b)                # card flick
        for off in tones:                                                  # tension pad that swells over 4 bars
            m.note(t0, bar * 0.99, hz(midi(root + "3") + off), "tri", 0.02 + 0.012 * (b % 4), attack=0.5, release=0.3)
        for k in (0.5, 1.5, 2.5, 3.5):
            m.note(t0 + k * beat, beat * 0.18, hz(midi(root + "5") + tones[int(k * 2) % len(tones)]), "bell", 0.035,
                   attack=0.002, release=0.1)
        if b >= 2:
            grid(m, t0, beat / 2, high if b % 2 == 0 else low, "bell", 0.14, attack=0.003, release=0.25)
    m.note(0.0, 1.0, hz(midi("E4")), "tri", 0.05, attack=0.6, release=0.3)
    signature(m, 0.0, midi("A3"), minor=True, vol=0.09)
    return m.finish(lowpass=0.3, rms=MINIGAME_RMS)


MINIGAME_MUSIC = {"retro_racer": retro_racer, "pixel_volleyball": pixel_volleyball, "cat_minesweeper": cat_minesweeper,
                  "galaxy_defender": galaxy_defender, "neon21": neon21, "lucky_wheel": lucky_wheel, "high_low": high_low}


ROOM_MUSIC = {"arcade_floor": arcade_floor, "prize_plaza": prize_plaza, "lucky_corner": lucky_corner, "home": home}
MUSIC = {**ROOM_MUSIC, **MINIGAME_MUSIC}


# ------------------------------------------------------------------ sound effects (short, quiet)
def _sfx(seconds):
    return Mix(seconds, clean=True)


def sfx_footstep():
    m = _sfx(0.09)
    m.noise(0, 0.06, 0.5, decay=70, bright=0.25, seed=3)
    m.note(0, 0.04, 90, "sine", 0.4, release=0.04)
    return m.finish(peak=0.5, fade=0.01)


def sfx_confirm():
    m = _sfx(0.2)
    m.note(0, 0.06, hz(midi("E5")), "p25", 0.5, release=0.04)
    m.note(0.06, 0.1, hz(midi("B5")), "p25", 0.5, release=0.08)
    return m.finish(peak=0.55, fade=0.01)


def sfx_cancel():
    m = _sfx(0.2)
    m.note(0, 0.07, hz(midi("B4")), "p25", 0.5, release=0.04)
    m.note(0.07, 0.1, hz(midi("E4")), "p25", 0.5, release=0.08)
    return m.finish(peak=0.5, fade=0.01)


def sfx_machine():
    m = _sfx(0.35)
    m.note(0, 0.05, hz(midi("A5")), "sq", 0.4, release=0.03)
    m.note(0.07, 0.18, hz(midi("E6")), "bell", 0.4, release=0.15)
    m.noise(0.0, 0.03, 0.4, decay=90, seed=5)
    return m.finish(peak=0.6, fade=0.01)


def sfx_token():
    m = _sfx(0.3)
    m.note(0, 0.03, 1900, "sine", 0.5, release=0.02)
    m.note(0.05, 0.2, 2500, "bell", 0.3, release=0.2)
    m.noise(0.0, 0.02, 0.3, decay=120, seed=6)
    return m.finish(peak=0.5, fade=0.01)


def sfx_ticket():
    m = _sfx(0.45)
    for k in range(5):
        m.note(k * 0.06, 0.05, hz(midi("C6") + k * 2), "p25", 0.4, release=0.03)
    m.note(0.32, 0.12, hz(midi("G6")), "bell", 0.35, release=0.2)
    return m.finish(peak=0.55, fade=0.01)


def sfx_purchase():
    m = _sfx(0.55)
    m.note(0, 0.08, hz(midi("E6")), "bell", 0.5, release=0.25)
    m.note(0.1, 0.12, hz(midi("A6")), "bell", 0.5, release=0.3)
    m.noise(0.0, 0.02, 0.4, decay=100, seed=8)
    return m.finish(peak=0.6, fade=0.01)


def sfx_card():
    m = _sfx(0.14)
    m.noise(0, 0.1, 0.5, decay=26, bright=0.7, seed=12)
    return m.finish(peak=0.45, fade=0.01)


def sfx_equip():
    m = _sfx(0.5)
    for k, n in enumerate(("C6", "E6", "G6", "C7", "E7")):
        m.note(k * 0.055, 0.06, hz(midi(n)), "bell", 0.28, release=0.18)
    return m.finish(peak=0.5, fade=0.01)


def sfx_pet():
    m = _sfx(0.4)
    m.note(0, 0.12, 520, "sine", 0.4, release=0.06, vibrato=14, slide=400)
    m.note(0.14, 0.18, 760, "sine", 0.35, release=0.12, vibrato=14, slide=-300)
    return m.finish(peak=0.45, fade=0.01)


def sfx_emote():
    m = _sfx(0.25)
    m.note(0, 0.08, hz(midi("G5")), "p25", 0.4, release=0.05)
    m.note(0.09, 0.1, hz(midi("C6")), "p25", 0.4, release=0.08)
    return m.finish(peak=0.45, fade=0.01)


def sfx_sit():
    m = _sfx(0.14)
    m.note(0, 0.08, 120, "sine", 0.5, release=0.06, slide=-250)
    m.noise(0, 0.05, 0.2, decay=60, bright=0.3, seed=21)
    return m.finish(peak=0.5, fade=0.01)


def sfx_meow():
    """Mochi's soft greeting: a short rising-then-falling mew."""
    m = _sfx(0.42)
    m.note(0, 0.13, 560, "tri", 0.35, attack=0.02, release=0.04, vibrato=9, slide=900)
    m.note(0.12, 0.2, 1000, "sine", 0.3, attack=0.02, release=0.1, vibrato=9, slide=-1100)
    return m.finish(peak=0.4, fade=0.01)


# ---- NEON VEND-O-MATIC (quiet, short)
def sfx_vend_hum():
    """The machine's compressor kicking in as its window opens: a low 50 Hz-ish hum with a soft rattle."""
    m = _sfx(0.7)
    m.note(0, 0.5, 55, "tri", 0.5, attack=0.12, release=0.18)
    m.note(0, 0.5, 110, "sine", 0.25, attack=0.12, release=0.18, vibrato=6)
    m.noise(0.1, 0.4, 0.05, decay=4, bright=0.1, seed=31)
    return m.finish(peak=0.4, fade=0.02)


def sfx_vend_select():
    m = _sfx(0.1)
    m.note(0, 0.04, hz(midi("A5")), "p25", 0.4, release=0.03)
    return m.finish(peak=0.4, fade=0.01)


def sfx_vend_drop():
    """The product falls, thuds into the tray and rocks once."""
    m = _sfx(0.6)
    m.note(0, 0.18, 900, "sine", 0.3, release=0.02, slide=-3200)
    m.noise(0.2, 0.05, 0.6, decay=60, bright=0.35, seed=33)
    m.note(0.2, 0.08, 90, "sine", 0.6, release=0.06, slide=-200)
    m.noise(0.31, 0.04, 0.3, decay=70, bright=0.3, seed=34)
    return m.finish(peak=0.55, fade=0.01)


def sfx_burp():
    m = _sfx(0.55)
    m.noise(0, 0.2, 0.5, decay=6, bright=0.2, seed=41)
    m.note(0.0, 0.4, 110, "saw", 0.5, attack=0.03, release=0.1, vibrato=24, slide=-90)
    return m.finish(lowpass=0.7, peak=0.5, fade=0.01)


def sfx_munch():
    m = _sfx(0.6)
    for k in range(3):
        m.noise(k * 0.18, 0.08, 0.5, decay=35, bright=0.4, seed=50 + k)
        m.note(k * 0.18, 0.06, 180 - 20 * k, "sine", 0.3, release=0.04)
    return m.finish(peak=0.45, fade=0.01)


def sfx_rainbow():
    m = _sfx(0.6)
    for k, n in enumerate(("C6", "D6", "E6", "G6", "A6", "C7")):
        m.note(k * 0.06, 0.05, hz(midi(n)), "bell", 0.25, release=0.2)
    return m.finish(peak=0.45, fade=0.01)


def sfx_squeak():
    m = _sfx(0.3)
    m.note(0, 0.08, 1500, "sine", 0.45, attack=0.01, release=0.03, slide=2600)
    m.note(0.1, 0.1, 2300, "sine", 0.4, attack=0.01, release=0.05, slide=-1800)
    return m.finish(peak=0.45, fade=0.01)


def sfx_zap():
    m = _sfx(0.45)
    for k in range(4):
        m.note(k * 0.09, 0.05, 300 + 220 * (k % 2), "sq", 0.3, release=0.02, slide=900)
        m.noise(k * 0.09, 0.03, 0.25, decay=80, seed=60 + k)
    return m.finish(peak=0.45, fade=0.01)


def sfx_mystery():
    m = _sfx(0.5)
    m.note(0, 0.12, hz(midi("E5")), "tri", 0.4, release=0.05, vibrato=8)
    m.note(0.14, 0.12, hz(midi("G#5")), "tri", 0.4, release=0.05, vibrato=8)
    m.note(0.28, 0.16, hz(midi("B4")), "bell", 0.35, release=0.12)
    return m.finish(peak=0.45, fade=0.01)


def sfx_glitch():
    """The secret: a burst of crushed noise and a falling then jumping tone. Short and dry."""
    m = _sfx(0.75)
    m.noise(0, 0.08, 0.5, decay=14, seed=71)
    m.note(0.0, 0.3, 900, "sq", 0.25, release=0.05, slide=-2400)
    m.noise(0.22, 0.06, 0.45, decay=20, seed=72)
    m.note(0.3, 0.1, 140, "saw", 0.3, release=0.05)
    m.note(0.44, 0.08, 1700, "p12", 0.2, release=0.03, slide=-3000)
    m.noise(0.5, 0.18, 0.2, decay=10, bright=0.5, seed=73)
    return m.finish(peak=0.5, fade=0.02)


SFX = {"footstep": sfx_footstep, "confirm": sfx_confirm, "cancel": sfx_cancel, "machine": sfx_machine,
       "token": sfx_token, "ticket": sfx_ticket, "purchase": sfx_purchase, "card": sfx_card,
       "equip": sfx_equip, "meow": sfx_meow, "pet": sfx_pet, "emote": sfx_emote, "sit": sfx_sit,
       "vend_hum": sfx_vend_hum, "vend_select": sfx_vend_select, "vend_drop": sfx_vend_drop, "burp": sfx_burp,
       "munch": sfx_munch, "rainbow": sfx_rainbow, "squeak": sfx_squeak, "zap": sfx_zap, "mystery": sfx_mystery,
       "glitch": sfx_glitch}


def generate(only=None):
    """Write every asset (or just the names in `only`). Returns the paths written."""
    written = []
    for name, build in MUSIC.items():
        if only is None or name in only:
            path = os.path.join(MUSIC_DIR, f"{name}.wav")
            write_wav(path, build())
            written.append(path)
    for name, build in SFX.items():
        if only is None or name in only:
            path = os.path.join(SFX_DIR, f"{name}.wav")
            write_wav(path, build())
            written.append(path)
    return written


if __name__ == "__main__":
    import sys
    for p in generate(set(sys.argv[1:]) or None):
        print(p, os.path.getsize(p) // 1024, "KB")
