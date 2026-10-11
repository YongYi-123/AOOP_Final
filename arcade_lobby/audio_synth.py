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

    def __init__(self, seconds):
        self.n = int(RATE * seconds)
        self.buf = [0.0] * self.n

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

    def finish(self, lowpass=0.0, peak=0.8, fade=0.0):
        """The 16-bit samples, normalised (and optionally warmed by a one-pole low-pass)."""
        buf = self.buf
        if lowpass:
            y = 0.0
            for i, x in enumerate(buf):
                y += (x - y) * (1 - lowpass)
                buf[i] = y
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
CHORDS = {"": (0, 4, 7), "m": (0, 3, 7), "m7": (0, 3, 7, 10), "maj7": (0, 4, 7, 11), "7": (0, 4, 7, 10)}


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


MUSIC = {"arcade_floor": arcade_floor, "prize_plaza": prize_plaza, "lucky_corner": lucky_corner, "home": home}


# ------------------------------------------------------------------ sound effects (short, quiet)
def _sfx(seconds):
    return Mix(seconds)


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


SFX = {"footstep": sfx_footstep, "confirm": sfx_confirm, "cancel": sfx_cancel, "machine": sfx_machine,
       "token": sfx_token, "ticket": sfx_ticket, "purchase": sfx_purchase, "card": sfx_card,
       "equip": sfx_equip, "pet": sfx_pet, "emote": sfx_emote, "sit": sfx_sit}


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
