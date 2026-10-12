"""Original synthesized arcade music and effects with separate volume controls."""
from array import array
import json
import logging
import math
import os
import time
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
# Mixer channel plan (set_reserved keeps automatic allocation - Sound.play(), cat voices, racer effects - off 0..7):
#   0-1 Retro Racer engine   2-3 background music crossfade   4-7 SCENE EFFECT channels (below)   8.. everything else
#   last channel: the device-liveness probe
SFX_CHANNELS = 8        # channels 0..7 are reserved
SCENE_SFX = (4, 5, 6, 7)   # one dedicated effect channel per scene on the stack, shared by all of that scene's effects
ORPHAN_GRACE = 0.6      # a scene that left may let its last effect finish this long (then the channel is stopped and freed)
SFX_STUCK_GRACE = 1.0   # an effect still "playing" this long after it should have ended means the device is not consuming
# Effect priority inside a scene's one channel: a new effect replaces the playing one unless the playing one matters more.
PRIORITY = {"footstep": 0, "meow": 1, "card": 1, "sit": 1, "pet": 1, "emote": 1, "bounce": 1, "hit": 1, "laser": 1,
            "skid": 1, "reveal": 1, "flag": 1, "confirm": 2, "cancel": 2, "machine": 2, "token": 2, "ticket": 2,
            "point": 2, "boom": 2, "purchase": 3, "equip": 3, "spike": 3, "powerup": 3, "win": 4, "loss": 4}
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
# Device liveness. The mixer only knows what it has queued: when the sound card (or WSLg's PulseAudio sink) stops
# consuming samples it still reports "playing". A 40 ms silent probe on a spare channel tells the difference:
# a healthy device finishes it at once, a stalled one never does. Opening the mixer again gets a fresh stream.
PROBE_EVERY = 3.0       # seconds between probes (wall clock: the device clock is what is being measured)
PROBE_SECONDS = 0.04
PROBE_STALL = 1.2       # a probe still unfinished after this long means the device has stopped consuming
REOPEN_MIN_GAP = 6.0    # seconds between recovery attempts; doubles after each one that did not help, up to ...
REOPEN_MAX_GAP = 60.0
FLAP_WINDOW, FLAP_LIMIT, FLAP_GAP = 120.0, 4, 20.0   # a device that stalls again and again is reopened at most every 20 s
                                                      # (each reopen costs the game a ~0.7 s pause on WSLg)
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
        self.clock = time.monotonic     # (tests replace it)
        self.device_state = "UNKNOWN"   # OK / STALLED / UNKNOWN (no probe has finished yet)
        self.probe_ms = None            # how long the last probe took to be consumed
        self.probe_started = None
        self.next_probe = 0.0
        self.device_stalls = 0          # stalls detected
        self.reopens = 0                # times the mixer was reopened to get a live stream back
        self.reopen_gap = REOPEN_MIN_GAP
        self.next_reopen = 0.0
        self.last_reopen = None         # (wall time, reason) of the latest reopen
        self.scene_keys = []            # [(key, label)] of the scenes on the stack, bottom first (see sync_scenes)
        self.scene_ch = {}              # scene key -> its effect channel
        self.orphans = {}               # channel -> time it must be freed by (its scene left)
        self.ch_label = {}              # channel -> label of the scene that owns / owned it
        self.ch_playing = {}            # channel -> (effect name, priority, started, length)
        self.stuck_sfx = 0              # effects that never finished (a sign the device stopped consuming)
        self.sfx_requested, self.sfx_played, self.sfx_dropped = {}, {}, {}
        self.reopen_times = []          # monotonic times of recent reopens (flapping limiter)
        self.warned_flapping = False
        self._probe_sound = None
        self._files = None              # cached (time, missing music, missing sfx)
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
            pygame.mixer.set_reserved(SFX_CHANNELS)  # 0/1 engine, 2/3 music, 4-7 scene effects (see the plan above)
            self.channels = [pygame.mixer.Channel(2), pygame.mixer.Channel(3)]
            self._probe_sound = self._silence(PROBE_SECONDS)
            self.probe_started, self.next_probe = None, 0.0
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
        missing_music, missing_sfx = self.missing_files()
        return {"enabled": self.enabled, "mixer": pygame.mixer.get_init(), "driver": self.driver,
                "init_error": self.init_error, "last_error": self.last_error, "theme": self.theme,
                "music_playing": self.music_playing(), "muted": self.muted, "duck": self.duck,
                "recoveries": self.recoveries,
                "music_volume": self.bgm_volume, "effective_music": self._music_level(),
                "sfx_volume": self.sfx_volume, "effective_sfx": self.effective_sfx,
                "missing_music": missing_music, "missing_sfx": missing_sfx, "music_starts": self.music_starts,
                "device_state": self.device_state, "probe_ms": self.probe_ms, "device_stalls": self.device_stalls,
                "reopens": self.reopens, "last_reopen": self.last_reopen,
                "fade_stuck": self.fade_stuck(), "sfx_owners": self.sfx_owners(), "stuck_sfx": self.stuck_sfx,
                "sfx_requested": dict(self.sfx_requested), "sfx_played": dict(self.sfx_played),
                "sfx_dropped": dict(self.sfx_dropped)}

    def missing_files(self):
        """(missing music themes, missing effects): re-checked at most every 5 s (it touches the disk)."""
        now = self.clock()
        if self._files is None or now - self._files[0] > 5.0:
            music = [t for t, n in MUSIC_FILES.items() if not os.path.isfile(os.path.join(self.asset_dir, "music", f"{n}.wav"))]
            sfx = [n for n in SFX_FILES if not os.path.isfile(os.path.join(self.asset_dir, "sfx", f"{n}.wav"))]
            self._files = (now, music, sfx)
        return self._files[1], self._files[2]

    def fade_stuck(self):
        """True when the music should be audible but its channel sits at zero (a crossfade that never came in)."""
        if not self.enabled or self.muted or self.bgm_volume <= 0 or not self.theme:
            return False
        return self.mix_to[self.active] == 1 and self.mix[self.active] < 0.01 and self.music_playing() \
            and self.channels[self.active].get_volume() < 0.005

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

    def set_volumes(self, bgm=None, sfx=None, save=True):
        """Set either volume (0..1) and apply it at once. `save=False` while a slider is being dragged
        (call save_prefs() when it is let go)."""
        if bgm is not None:
            self.bgm_volume = max(0, min(1, bgm))
        if sfx is not None:
            self.sfx_volume = max(0, min(1, sfx))
        self._apply_volumes()
        if save:
            self.save_prefs()

    def restore_defaults(self):
        self.bgm_volume, self.sfx_volume, self.muted = DEFAULT_BGM, DEFAULT_SFX, False
        self._apply_volumes()
        self.save_prefs()

    def play_test_sound(self):
        """The settings screen's TEST SOUND: an effect at the current effects volume. Returns False (and plays
        nothing) when muted or when there is no audio device, so the screen can say why."""
        if not self.enabled or self.muted:
            return False
        self.last_effect.pop("purchase", None)
        self.play("purchase")
        return "purchase" in self.last_effect

    def sfx_busy(self):
        """Mixer channels currently playing an effect (the music and engine channels are not counted)."""
        if not self.enabled:
            return []
        try:
            return [i for i in range(SCENE_SFX[0], pygame.mixer.get_num_channels() - 1) if pygame.mixer.Channel(i).get_busy()]       # (not the probe channel)
        except pygame.error:
            return []

    @property
    def fade_state(self):
        return "CROSSFADING" if self.mix != self.mix_to else "STEADY"

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

    # ------------------------------------------------------------ device liveness
    def _silence(self, seconds):
        samples = array('h', [0] * (int(self.rate * seconds) * self.stereo))
        return pygame.mixer.Sound(buffer=samples)

    def _probe_channel(self):
        """The spare channel (the last one: automatic allocation reaches it only when every other is busy)."""
        return pygame.mixer.Channel(pygame.mixer.get_num_channels() - 1)

    def _check_device(self):
        """Once a frame, cheaply: start a probe every PROBE_EVERY seconds and look at the one in flight.
        Only a probe that is STILL unfinished after PROBE_STALL counts as a stall - a probe that has finished by the
        time we look is healthy however late we looked (a frozen game loop is not a frozen device)."""
        if not self.enabled or self.closed or self._probe_sound is None:
            return
        now = self.clock()
        try:
            channel = self._probe_channel()
            if self.probe_started is not None:
                if not channel.get_busy():
                    self.probe_ms = round((now - self.probe_started) * 1000)
                    self.probe_started = None
                    self.next_probe = now + PROBE_EVERY
                    if self.device_state != "OK":
                        log.info("audio device is consuming samples (probe %s ms)", self.probe_ms)
                    self.device_state, self.reopen_gap = "OK", REOPEN_MIN_GAP
                elif now - self.probe_started > PROBE_STALL:
                    self._device_stalled(now)
            elif now >= self.next_probe:
                channel.play(self._probe_sound)
                self.probe_started = now
        except pygame.error as exc:
            self._fail("device probe", exc)

    def _device_stalled(self, now):
        first = self.device_state == "OK"             # UNKNOWN -> STALLED right after a reopen is the same episode
        self.device_state = "STALLED"
        if first or self.device_stalls == 0:
            self.device_stalls += 1
            log.warning("AUDIO DEVICE STALLED: samples are not being consumed (mixer still reports playback)")
        if now >= self.next_reopen:
            self.reopen_mixer("device stalled")
            now = self.clock()
            self.reopen_times = [t for t in self.reopen_times if now - t < FLAP_WINDOW] + [now]
            gap = self.reopen_gap
            if len(self.reopen_times) >= FLAP_LIMIT:
                gap = max(gap, FLAP_GAP)
                if not self.warned_flapping:
                    self.warned_flapping = True
                    log.warning("the audio device keeps stalling (%d reopens in %.0f s); limiting recoveries to one per %.0f s. "
                                "On WSL this is the WSLg audio bridge: try 'wsl --update' and 'wsl --shutdown' from Windows",
                                len(self.reopen_times), FLAP_WINDOW, FLAP_GAP)
            self.next_reopen = now + gap
            self.reopen_gap = min(REOPEN_MAX_GAP, self.reopen_gap * 2)     # back off while reopening does not help

    def reopen_mixer(self, reason):
        """Open the output stream again (a new stream is consumed even when the old one has stalled), keeping the
        cached sounds, volumes, mute and the current theme. Returns True when audio is available afterwards."""
        old = pygame.mixer.get_init()
        log.warning("reopening the mixer: %s", reason)
        started = self.clock()
        try:
            self.stop_all_channels()
            pygame.mixer.quit()
        except pygame.error as exc:
            self._fail("close mixer", exc)
        self.enabled = False
        try:
            pygame.mixer.init(*(old if old else (self.rate, -16, self.stereo)))
        except pygame.error as exc:
            self.init_error = str(exc)
            log.error("reopening the mixer failed: %s%s", exc, self.hint())
            self.retry_in = REINIT_EVERY
            return False
        if old and pygame.mixer.get_init() != old:               # the device came back in another format
            log.warning("audio format changed %s -> %s: reloading sounds", old, pygame.mixer.get_init())
            self.music.clear()
            self.sounds.clear()
            _SOUND_CACHE.clear()
        theme = self.theme
        self.mix, self.mix_to, self.active = [0.0, 0.0], [0.0, 0.0], 1
        self.theme = None
        self.init_mixer()                                        # channels, reservations, probe sound, volumes
        if theme:
            self.switch(theme)
        self._apply_volumes()
        self.reopens += 1
        self.last_reopen = (time.time(), reason)
        self.device_state, self.probe_started, self.next_probe = "UNKNOWN", None, self.clock() + 1.0
        log.warning("mixer reopened in %.2f s", self.clock() - started)
        return self.enabled

    def stop_all_channels(self):
        for i in range(pygame.mixer.get_num_channels()):
            pygame.mixer.Channel(i).stop()
        self.scene_ch.clear()
        self.orphans.clear()
        self.ch_label.clear()
        self.ch_playing.clear()

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
    # ---- scene-owned effect channels -------------------------------------------------------------
    def sync_scenes(self, scenes):
        """Tell the manager which scenes are on the stack, bottom first: [(key, label), ...]. A scene that has left
        gives its effect channel back (after letting a playing effect finish, ORPHAN_GRACE at most); the topmost scene
        is the one whose effects play. Cheap enough to call every frame."""
        keys = [k for k, _ in scenes]
        if keys == [k for k, _ in self.scene_keys]:
            return
        self.scene_keys = list(scenes)
        live = set(keys)
        for key in [k for k in self.scene_ch if k not in live]:
            self._release(key)

    def _release(self, key):
        ch = self.scene_ch.pop(key)
        if self.enabled and self._busy(ch):
            self.orphans[ch] = self.clock() + ORPHAN_GRACE
        else:
            self.ch_label.pop(ch, None)
            self.ch_playing.pop(ch, None)

    def _busy(self, ch):
        try:
            return pygame.mixer.Channel(ch).get_busy()
        except pygame.error:
            return False

    def _free_channel(self, ch):
        try:
            pygame.mixer.Channel(ch).stop()
        except pygame.error:
            pass
        self.orphans.pop(ch, None)
        self.ch_label.pop(ch, None)
        self.ch_playing.pop(ch, None)

    def _scene_channel(self):
        """The effect channel of the topmost scene (allocated on its first effect: a scene that makes no sound never
        takes one). Never more than one per scene; when all four are taken the oldest leaver, then the scene deepest
        in the stack, gives its channel up."""
        key, label = self.scene_keys[-1] if self.scene_keys else (None, "-")
        if key in self.scene_ch:
            return self.scene_ch[key]
        owned = set(self.scene_ch.values())
        free = [c for c in SCENE_SFX if c not in owned and c not in self.orphans]
        if free:
            ch = free[0]
        elif self.orphans:
            ch = min(self.orphans, key=self.orphans.get)
        else:
            below = [k for k, _ in self.scene_keys if k in self.scene_ch and k != key]
            ch = self.scene_ch.pop(below[0] if below else next(iter(self.scene_ch)))      # the deepest scene gives way
        self._free_channel(ch)
        self.scene_ch[key] = ch
        self.ch_label[ch] = label
        return ch

    def _upkeep_sfx(self):
        """Once a frame: free the channels of departed scenes, and stop an effect that has outlived its length by
        SFX_STUCK_GRACE - it can only mean the device is not consuming samples (see _check_device)."""
        if not (self.orphans or self.ch_playing):
            return
        now = self.clock()
        for ch, until in list(self.orphans.items()):
            if now >= until or not self._busy(ch):
                self._free_channel(ch)
        for ch, (name, _prio, started, length) in list(self.ch_playing.items()):
            if self._busy(ch) and now - started > length + SFX_STUCK_GRACE:
                self.stuck_sfx += 1
                log.warning("effect '%s' never finished on channel %d (%.1f s): the device is not consuming samples",
                            name, ch, now - started)
                if ch in self.orphans:
                    self._free_channel(ch)
                else:                                   # the scene is still here: keep its channel, drop the stuck effect
                    pygame.mixer.Channel(ch).stop()
                    self.ch_playing.pop(ch, None)
            elif not self._busy(ch) and ch not in self.orphans:
                self.ch_playing.pop(ch, None)

    def play_object(self, sound, label="sound", priority=1, volume=1.0):
        """Play a Sound that is not one of the named effects (a cat's meow) on the topmost scene's channel."""
        if not self.enabled or self.muted:
            return False
        try:
            return self._play_on_scene_channel(sound, label, priority, volume)
        except (pygame.error, TypeError) as exc:
            self._fail(f"play '{label}'", exc)
            return False

    def _play_on_scene_channel(self, sound, name, priority, volume):
        ch = self._scene_channel()
        channel = pygame.mixer.Channel(ch)
        now = self.clock()
        playing = self.ch_playing.get(ch)
        if playing and channel.get_busy() and priority < playing[1] and now - playing[2] < playing[3]:
            self.sfx_dropped[name] = self.sfx_dropped.get(name, 0) + 1          # a more important effect is still sounding
            return False
        sound.set_volume(volume)
        channel.set_volume(1.0)
        channel.play(sound)
        self.ch_playing[ch] = (name, priority, now, sound.get_length())
        self.sfx_played[name] = self.sfx_played.get(name, 0) + 1
        return True

    def sfx_owners(self):
        """[(channel, scene label, effect playing or None)] for the scene effect channels in use."""
        out = []
        for ch in SCENE_SFX:
            if ch in self.ch_label:
                playing = self.ch_playing.get(ch)
                out.append((ch, self.ch_label[ch] + ("*" if ch in self.orphans else ""),
                            playing[0] if playing and self._busy(ch) else None))
        return out

    # ------------------------------------------------------------ effects
    def play(self, name):
        if not self.enabled or self.muted or (name not in self.EFFECTS and name not in SFX_FILES):
            return
        self.sfx_requested[name] = self.sfx_requested.get(name, 0) + 1
        if self.time - self.last_effect.get(name, -100) < MIN_GAP.get(name, .06):
            return
        try:
            if name not in self.sounds:
                sound = self._effect_sound(name)
                if sound is None:
                    return
                self.sounds[name] = sound
            if self._play_on_scene_channel(self.sounds[name], name, PRIORITY.get(name, 1),
                                           self.sfx_volume * SFX_GAIN.get(name, 1.0)):
                self.last_effect[name] = self.time
        except pygame.error as exc:
            self._fail(f"play effect '{name}'", exc)

    def update(self, dt):
        self.time += max(0, dt)
        self._fade(max(0, dt))
        self._watch(max(0, dt))
        self._check_device()
        self._upkeep_sfx()

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
