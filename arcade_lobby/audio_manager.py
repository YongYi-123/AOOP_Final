"""Original synthesized arcade music and effects with separate volume controls."""
from array import array
import json
import logging
import math
import os
import pygame

log = logging.getLogger("arcade.audio")


ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
# theme -> music file (assets/music/<file>.wav, composed by audio_synth.py). The hub's own
# theme keeps its old name "lobby". Minigame themes below are short synthesized loops.
MUSIC_FILES = {"lobby": "arcade_floor", "prize_plaza": "prize_plaza", "lucky_corner": "lucky_corner",
               "home": "home",
               # one theme per minigame (the key is the machine / game id the scene reports)
               "retro_racer": "retro_racer", "pixel_volleyball": "pixel_volleyball", "cat_minesweeper": "cat_minesweeper",
               "galaxy_defender": "galaxy_defender", "neon21": "neon21", "lucky_wheel": "lucky_wheel",
               "high_low": "high_low"}
# Per-track level so every theme sits at the same perceived loudness (the files are not touched). The room themes
# were mastered up to 1.7 dB louder than the minigame ones; the racing track sits low so the engine stays on top.
TRACK_GAIN = {"lobby": .86, "home": .82, "lucky_corner": .87, "prize_plaza": 1.0, "retro_racer": .72}
SFX_CHANNELS = 4        # mixer channels 0-1 = racer engine, 2-3 = music crossfade; effects use the rest
SFX_FILES = ("footstep", "confirm", "cancel", "machine", "token", "ticket", "purchase", "card", "equip",
             "pet", "emote", "sit", "meow")
# some effects are meant to be barely there
SFX_GAIN = {"footstep": 0.3, "card": 0.7, "confirm": 0.8, "cancel": 0.8, "sit": 0.7, "emote": 0.8, "meow": 0.6,
            # the shooter fires dozens of these a second of play: keep them a soft texture, not a buzz
            "laser": 0.3, "boom": 0.75, "point": 0.8, "skid": 0.6, "bounce": 0.8}
MIN_GAP = {"footstep": 0.16, "meow": 1.2, "laser": 0.14, "boom": 0.09, "point": 0.1, "bounce": 0.08,
           "hit": 0.07}                              # seconds between two plays of the same effect (default .06)
DEFAULT_BGM, DEFAULT_SFX = .5, .7      # the music files are mastered at about -14 dB, so .5 is comfortable
FADE_MS = 700           # music crossfade length, driven by game time (not by the audio clock: a stalled device cannot freeze it)
WATCHDOG_GRACE = .35    # seconds the music may be missing before it is restarted
REINIT_EVERY = 5.0      # seconds between attempts to open the device again after a failed start
DUCK_PAUSED = .4        # music level while a game is paused

_SOUND_CACHE = {}       # (path, mixer format) -> Sound: a theme is read from disk once per run


THEME_TITLES = {"lobby": "ARCADE FLOOR", "prize_plaza": "PRIZE PLAZA", "lucky_corner": "LUCKY CORNER", "home": "HOME",
                "retro_racer": "RETRO RACER", "pixel_volleyball": "CAT VOLLEYBALL", "cat_minesweeper": "CAT TERRITORY",
                "galaxy_defender": "STARFALL ASSAULT", "neon21": "NEON 21", "lucky_wheel": "SPIN", "high_low": "HI-LO"}


def _unit(value, default):
    """A saved volume if it is a number in 0..1, else the default."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        return default
    return float(value)


class AudioManager:
    """Music (one looping theme at a time, crossfaded) and effects with independent
    volumes and a mute. Every call is safe without an audio device: `enabled` is
    False and the game never waits on sound - but the reason is never hidden: it is
    logged (logger "arcade.audio") and kept in `init_error` / `last_error`, and
    `status()` reports it (see audio_diagnostics.py).

    Music: set_track()/switch() ignores a request for the theme that is already
    playing, so opening a menu never restarts the song. Preferences (volumes and
    mute) are saved to `prefs_path` when one is given."""
    THEMES = {'lobby': (262, 330, 392, 330, 294, 349, 440, 349),
              'retro_racer': (196, 247, 294, 392, 196, 294, 247, 392),
              'pixel_volleyball': (330, 392, 440, 523, 440, 392, 330, 294),
              'cat_minesweeper': (262, 392, 330, 440, 349, 330, 294, 392),
              'galaxy_defender': (220, 262, 330, 262, 247, 294, 370, 294)}
    EFFECTS = {'machine': (440, 660), 'confirm': (660, 880), 'cancel': (440, 220),
               'hit': (560,), 'spike': (1480, 880, 440), 'bounce': (240,), 'point': (660, 880),
               'win': (523, 659, 784), 'loss': (440, 330, 220),
               'laser': (990, 760), 'boom': (180, 120), 'powerup': (660, 990), 'reveal': (700,), 'flag': (420, 560), 'skid': (480, 320, 160)}

    def __init__(self, bgm_volume=DEFAULT_BGM, sfx_volume=DEFAULT_SFX, prefs_path=None, asset_dir=ASSET_DIR):
        self.bgm_volume, self.sfx_volume, self.muted = bgm_volume, sfx_volume, False
        self.prefs_path, self.asset_dir = prefs_path, asset_dir
        self.theme = None
        self.sounds, self.music = {}, {}
        self.channels = []
        self.enabled, self.active, self.time = False, 0, 0.0
        self.last_effect = {}
        self.music_starts = 0           # how many times a track was (re)started: lets tests see "no restart"
        self.closed = False             # stop() was called: the watchdog leaves the silence alone
        self.mix = [0.0, 0.0]           # how far each music channel is faded in (0..1)
        self.mix_to = [0.0, 0.0]        # where it is heading
        self.duck = 1.0                 # 1.0 normal; lower while a game is paused
        self.unhealthy = 0.0            # seconds the current theme has been missing from its channel
        self.recoveries = 0             # times the watchdog had to restart the music
        self.retry_in = 0.0
        self.init_error = None          # why the mixer could not start (None: it started)
        self.last_error = None          # the most recent playback / loading problem
        self.load_prefs()
        self.init_mixer()

    def init_mixer(self):
        """Open the mixer on the real output device (also usable to retry after a failure).
        Never forces a dummy driver. Returns True when audio is available."""
        self.enabled = False
        if "PULSE_SERVER" not in os.environ and os.path.exists("/mnt/wslg/PulseServer"):
            os.environ["PULSE_SERVER"] = "unix:/mnt/wslg/PulseServer"     # WSLg's audio socket
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 2)
            self.rate, sample_format, self.stereo = pygame.mixer.get_init()
            if sample_format != -16:
                raise pygame.error(f"unsupported sample format {sample_format}")
            pygame.mixer.set_num_channels(max(24, pygame.mixer.get_num_channels()))
            pygame.mixer.set_reserved(SFX_CHANNELS)  # 0/1 engine, 2/3 music crossfade
            self.channels = [pygame.mixer.Channel(2), pygame.mixer.Channel(3)]
            self.enabled, self.init_error = True, None
            log.info("audio ready: driver=%s %s", self.driver, pygame.mixer.get_init())
            if self.theme:                      # a retry after a failed start: bring the music in now
                theme, self.theme = self.theme, None
                self.switch(theme)
        except (pygame.error, TypeError, ValueError) as exc:
            self.init_error = str(exc)
            self.retry_in = REINIT_EVERY
            log.warning("AUDIO DISABLED - the mixer could not start: %s%s", exc, self.hint())
        return self.enabled

    @property
    def driver(self):
        try:
            return pygame.mixer.get_driver() if hasattr(pygame.mixer, "get_driver") else \
                os.environ.get("SDL_AUDIODRIVER", "?")
        except pygame.error:
            return os.environ.get("SDL_AUDIODRIVER") or None

    def hint(self):
        """A one-line suggestion for the commonest cause of a failed start."""
        text = (self.init_error or "").lower()
        if "libpulse" in text or "no such audio device" in text or "not available" in text:
            return ("\n  On WSL: sudo apt install libpulse0   (SDL needs it to reach WSLg's sound server), "
                    "then run: python audio_diagnostics.py")
        return "\n  Run: python audio_diagnostics.py"

    def _fail(self, what, exc, disable=False):
        """Record (and log) a playback problem instead of swallowing it."""
        self.last_error = f"{what}: {exc}"
        log.error("audio %s failed: %s", what, exc)
        if disable:
            self.enabled = False

    def music_playing(self):
        """True while a music channel is actually producing the current theme."""
        try:
            return bool(self.enabled and self.theme and any(c.get_busy() for c in self.channels))
        except pygame.error:
            return False

    def status(self):
        """Everything needed to tell 'engine failed' from 'muted' from 'missing files'."""
        files = {t: os.path.isfile(os.path.join(self.asset_dir, "music", f"{n}.wav")) for t, n in MUSIC_FILES.items()}
        sfx = {n: os.path.isfile(os.path.join(self.asset_dir, "sfx", f"{n}.wav")) for n in SFX_FILES}
        return {"enabled": self.enabled, "mixer": pygame.mixer.get_init(), "driver": self.driver,
                "init_error": self.init_error, "last_error": self.last_error, "theme": self.theme,
                "music_playing": self.music_playing(), "muted": self.muted, "duck": self.duck,
                "recoveries": self.recoveries,
                "music_volume": self.bgm_volume, "effective_music": self._music_level(),
                "sfx_volume": self.sfx_volume, "effective_sfx": self.effective_sfx,
                "missing_music": [t for t, ok in files.items() if not ok],
                "missing_sfx": [n for n, ok in sfx.items() if not ok], "music_starts": self.music_starts}

    def test_tone(self, seconds=0.6, volume=0.5):
        """Play a short chord straight on the output device (ignores mute) to prove sound comes out."""
        if not self.enabled:
            return False
        try:
            notes = (523, 659, 784)
            samples = array('h')
            n = int(self.rate * seconds)
            for i in range(n):
                env = min(1, i / (self.rate * .02)) * min(1, (n - i) / (self.rate * .05))
                v = sum(math.sin(2 * math.pi * f * i / self.rate) for f in notes) / len(notes)
                samples.extend([int(v * env * 20000)] * self.stereo)
            sound = pygame.mixer.Sound(buffer=samples)
            sound.set_volume(volume)
            sound.play()
            return True
        except pygame.error as exc:
            self._fail("test tone", exc)
            return False

    # ------------------------------------------------------------ preferences
    def load_prefs(self):
        """Read saved volumes / mute; a missing or damaged file keeps the defaults."""
        if not self.prefs_path:
            return
        try:
            with open(self.prefs_path, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return
        except (OSError, ValueError) as exc:
            log.warning("could not read audio settings %s (%s); using defaults", self.prefs_path, exc)
            return
        if isinstance(data, dict):
            self.bgm_volume = _unit(data.get("music"), self.bgm_volume)
            self.sfx_volume = _unit(data.get("sfx"), self.sfx_volume)
            self.muted = data.get("muted") is True

    def save_prefs(self):
        if not self.prefs_path:
            return False
        tmp = self.prefs_path + ".tmp"
        try:
            os.makedirs(os.path.dirname(self.prefs_path) or ".", exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"music": round(self.bgm_volume, 3), "sfx": round(self.sfx_volume, 3),
                           "muted": self.muted}, f)
            os.replace(tmp, self.prefs_path)
        except OSError as exc:
            log.warning("could not save audio settings to %s: %s", self.prefs_path, exc)
            return False
        return True

    # ------------------------------------------------------------ sound building
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

    def _load(self, folder, name):
        """A Sound from assets/<folder>/<name>.wav, or None if the file is missing / unreadable."""
        path = os.path.join(self.asset_dir, folder, f"{name}.wav")
        key = (path, pygame.mixer.get_init())
        if key in _SOUND_CACHE:
            return _SOUND_CACHE[key]
        try:
            _SOUND_CACHE[key] = sound = pygame.mixer.Sound(path)
            return sound
        except (pygame.error, FileNotFoundError, OSError) as exc:
            log.warning("missing or unreadable sound file %s (%s) - using a synthesized stand-in", path, exc)
            self.last_error = f"load {folder}/{name}: {exc}"
            return None

    def _music_sound(self, theme):
        sound = self._load("music", MUSIC_FILES[theme]) if theme in MUSIC_FILES else None
        return sound or self._sound(self.THEMES.get(theme, self.THEMES['lobby']), .24, True)

    def _effect_sound(self, name):
        sound = self._load("sfx", name) if name in SFX_FILES else None
        if sound is None and name in self.EFFECTS:
            sound = self._sound(self.EFFECTS[name], .07)
        return sound

    # ------------------------------------------------------------ volumes / mute
    def _music_level(self):
        return 0.0 if self.muted else self.bgm_volume * self.duck

    def set_duck(self, factor):
        """Lower (or restore, with 1.0) the music under a pause menu. Takes effect at once."""
        factor = max(0.0, min(1.0, factor))
        if factor != self.duck:
            self.duck = factor
            self._apply_volumes()

    def _channel_level(self, i):
        return self._music_level() * math.sin(self.mix[i] * math.pi / 2)        # equal-power fade curve

    def _apply_volumes(self):
        if not self.enabled:
            return
        try:
            for i, channel in enumerate(self.channels):
                channel.set_volume(self._channel_level(i))
            for name, sound in self.sounds.items():
                sound.set_volume(self.sfx_volume * SFX_GAIN.get(name, 1.0))
        except pygame.error as exc:
            self._fail("set volume", exc)

    def _fade(self, dt):
        """Move the crossfade along by `dt` seconds of game time; a track that has faded out is stopped for good."""
        if not self.enabled or self.mix == self.mix_to:
            return
        step = dt * 1000.0 / FADE_MS
        for i in (0, 1):
            self.mix[i] = min(self.mix_to[i], self.mix[i] + step) if self.mix[i] < self.mix_to[i] \
                else max(self.mix_to[i], self.mix[i] - step)
            if self.mix[i] <= 0 and self.mix_to[i] <= 0:
                try:
                    self.channels[i].stop()
                except pygame.error as exc:
                    self._fail("stop faded-out music", exc)
        self._apply_volumes()

    def set_volumes(self, bgm=None, sfx=None):
        if bgm is not None:
            self.bgm_volume = max(0, min(1, bgm))
        if sfx is not None:
            self.sfx_volume = max(0, min(1, sfx))
        self._apply_volumes()
        self.save_prefs()

    def set_muted(self, muted):
        self.muted = bool(muted)
        self._apply_volumes()
        self.save_prefs()

    def toggle_mute(self):
        self.set_muted(not self.muted)
        return self.muted

    @property
    def track_title(self):
        """The name of the music that is playing, for on-screen readouts."""
        return THEME_TITLES.get(self.theme, "")

    @property
    def effective_sfx(self):
        """The effect volume games should use right now (0 when muted)."""
        return 0.0 if self.muted else self.sfx_volume

    # ------------------------------------------------------------ music
    def switch(self, theme):
        """Crossfade to `theme`. The same theme is left alone (no restart); None keeps
        whatever is playing (menus and dialogs have no music of their own)."""
        if theme is None:
            return
        theme = theme if theme in self.THEMES or theme in MUSIC_FILES else 'lobby'
        if theme == self.theme:
            return
        self.theme = theme
        self.unhealthy = 0.0
        self.closed = False
        if self.enabled:
            self._start_track(theme)

    def _start_track(self, theme):
        """Start `theme` on the idle music channel and fade the previous one out (see _fade)."""
        try:
            if theme not in self.music:
                self.music[theme] = self._music_sound(theme)
            self.music[theme].set_volume(TRACK_GAIN.get(theme, 1.0))
            old, new = self.active, 1 - self.active
            channel = self.channels[new]
            if not channel.get_busy():
                self.mix[new] = 0.0                  # (a channel still fading out keeps its level: no jump)
            self.mix_to[old], self.mix_to[new] = 0.0, 1.0
            channel.set_volume(self._channel_level(new))
            channel.play(self.music[theme], loops=-1)
            channel.set_volume(self._channel_level(new))          # (playing may reset the channel volume)
            self.active = new
            self.music_starts += 1
            log.info("music: %s", theme)
        except (pygame.error, MemoryError) as exc:
            self._fail(f"start music '{theme}'", exc)

    def preload(self):
        """Read every theme and effect from disk now (and build the stand-in beeps), so
        nothing is loaded or synthesized in the middle of play."""
        if not self.enabled:
            return
        try:
            for theme in MUSIC_FILES:
                if theme not in self.music:
                    self.music[theme] = self._music_sound(theme)
            for name in (*SFX_FILES, *self.EFFECTS):
                if name not in self.sounds:
                    sound = self._effect_sound(name)
                    if sound is not None:
                        self.sounds[name] = sound
            self._apply_volumes()
        except (pygame.error, MemoryError) as exc:
            self._fail("preload", exc)

    def _watch(self, dt):
        """Self-healing: if the current theme is not actually on its channel (something stopped it, the
        crossfade was interrupted, the device came back) start it again. Silence cannot last."""
        if self.closed:
            return
        if not self.enabled:
            self.retry_in -= dt
            if self.retry_in <= 0:
                self.retry_in = REINIT_EVERY
                if pygame.mixer.get_init() is None or self.init_error:
                    self.init_mixer()
            return
        if pygame.mixer.get_init() is None:               # somebody closed the mixer under us
            log.error("the mixer was closed by another module; reopening it")
            self.init_mixer()
            return
        if not self.theme:
            return
        try:
            channel = self.channels[self.active]
            alive = channel.get_busy() and channel.get_sound() is self.music.get(self.theme)
            if alive:
                self.unhealthy = 0.0
                return
            self.unhealthy += dt
            if self.unhealthy >= WATCHDOG_GRACE:
                self.unhealthy = 0.0
                self.recoveries += 1
                log.warning("music '%s' stopped unexpectedly; restarting it", self.theme)
                self._start_track(self.theme)
        except pygame.error as exc:
            self._fail("music watchdog", exc)

    set_track = switch

    # ------------------------------------------------------------ effects
    def play(self, name):
        if not self.enabled or self.muted or (name not in self.EFFECTS and name not in SFX_FILES):
            return
        if self.time - self.last_effect.get(name, -100) < MIN_GAP.get(name, .06):
            return
        try:
            if name not in self.sounds:
                sound = self._effect_sound(name)
                if sound is None:
                    return
                self.sounds[name] = sound
            self.sounds[name].set_volume(self.sfx_volume * SFX_GAIN.get(name, 1.0))
            self.sounds[name].play()
            self.last_effect[name] = self.time
        except pygame.error as exc:
            self._fail(f"play effect '{name}'", exc)

    def update(self, dt):
        self.time += max(0, dt)
        self._fade(max(0, dt))
        self._watch(max(0, dt))

    def stop(self):
        """Silence everything (the program is closing); the watchdog will not bring the music back."""
        self.closed = True
        if self.enabled:
            try:
                for channel in self.channels:
                    channel.stop()
                self.mix, self.mix_to = [0.0, 0.0], [0.0, 0.0]
                for sound in self.sounds.values():
                    sound.stop()
            except pygame.error as exc:
                self._fail("stop", exc)


class GameSoundBus:
    """Route game events through shared SFX mixing without owning lobby music."""
    def __init__(self, manager):
        self.manager = manager

    def play(self, events, now=None):
        for name in ([events] if isinstance(events, str) else events):
            self.manager.play(name)

    def stop(self):
        pass
