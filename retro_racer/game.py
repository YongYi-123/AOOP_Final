"""Game: window, main loop, state machine, menus, input, audio hooks and scene rendering.

One shared loop drives every mode: `self.manager` (RaceManager or EndlessManager) supplies the rules
and `self.theme` the look, so nothing in update()/draw() branches on the mode or the track.
"""
import gc
import math
import pygame
import settings as S
from road_hazards import RoadHazards
from road import Road
from car import PlayerCar
from traffic import TrafficManager
from race import RaceManager, State
from endless import EndlessManager
from modes import GameMode
from theme import TrackThemeManager
from car_specs import CAR_CATALOG
from car_select import CarSelectMenu
from hud import Hud
from tuning import Tuner
from audio import Audio
from difficulty import DIFFICULTIES, DEFAULT_DIFFICULTY
from drift_effects import DriftEffects
from tracks import TRACKS
from minimap import MiniMap
from scenery import SCENERY_THEMES
from scenery_select import SceneryGallery

IDLE = {"accelerate": False, "brake": False, "steer": 0}
COAST = {"accelerate": False, "brake": True, "steer": 0}    # slow to a stop after the race ends
CHECKPOINT_FLASH = 0.16                                      # seconds
CHECKPOINT_FLASH_COLOR = (255, 240, 140)

MODE_MENU = [(GameMode.COMPETITIVE, "COMPETITIVE", f"{S.RACE_LAPS} LAPS - CHECKPOINTS - BEAT THE CLOCK"),
             (GameMode.ENDLESS, "ENDLESS", f"DRIVE ON UNTIL {S.ENDLESS_MAX_CRASHES} CRASHES - TRAFFIC GROWS")]
# Any of these fires the held item. SPACE is the main key; the others exist because many keyboards cannot
# register UP + LEFT/RIGHT + SPACE together ("ghosting"), which makes SPACE seem dead while steering.
ITEM_KEYS = (pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_z, pygame.K_x, pygame.K_LCTRL, pygame.K_RCTRL)
RACE_STATES = (State.COUNTDOWN, State.PLAYING)
MENU_STATES = (State.MODE_SELECT, State.TRACK_SELECT, State.CAR_SELECT)
ATTRACT_STATES = (State.TITLE,) + MENU_STATES   # car cruises behind these screens


class Game:
    def __init__(self, screen=None):
        """screen: draw into this surface instead of opening a window (used when the game is embedded
        in another program, which then owns the window, the event loop and display.flip)."""
        pygame.init()
        if screen is None:
            screen = pygame.display.set_mode((S.WIDTH, S.HEIGHT))
            pygame.display.set_caption(S.TITLE)
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.hud = Hud()
        self.hud.prewarm()
        self.audio = Audio()
        self.tuner = Tuner(on_change=self._on_tune)
        self.themes = TrackThemeManager(SCENERY_THEMES)
        self.scenery_gallery = SceneryGallery(self.themes)
        self.theme = self.themes.themes[0]
        self.selected_theme = self.theme            # confirmed scenery
        self.theme_index = 0
        self.tracks = TRACKS
        self.track = self.selected_track = self.tracks[0]
        self.mode = GameMode.COMPETITIVE
        self.road = Road(self.theme, markers=True, route=self.track.build(S.SEGMENT_LENGTH))
        self.minimap = MiniMap(self.road.route, (S.WIDTH - 200, 12, 188, 140))
        self.track_previews = {}
        self.traffic = TrafficManager(self.road)
        self.managers = {GameMode.COMPETITIVE: RaceManager(self.road, self.traffic), GameMode.ENDLESS: EndlessManager()}
        self.scene = pygame.Surface((S.WIDTH, S.HEIGHT))
        self.overlay = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)   # reused for flashes
        self.running = True
        self.time = 0.0                 # wall-clock for blinking prompts
        self.last_dt = 0.0
        self.toast, self.toast_time = "", 0.0
        self.paused = False
        self.mode_index = 0
        self.track_index = 0
        self.car_menu = CarSelectMenu(CAR_CATALOG)
        self.ai_level = DEFAULT_DIFFICULTY               # AI difficulty for competitive races; persists across restarts
        self.selected_car_spec = CAR_CATALOG.default     # confirmed choice; survives countdown, restarts, end screens
        self.drift = DriftEffects(S.DRIVING_FX_INTENSITY)
        self.reset()
        self.apply_look()
        self.state = State.TITLE
        self._settle_memory()

    @property
    def manager(self):
        """The rules for the selected mode."""
        return self.managers[self.mode]

    # ---- setup / reset ------------------------------------------------------
    def apply_look(self):
        """Apply circuit + scenery; rebuild geometry-dependent managers on route changes."""
        if self.road.route.key != self.track.key:
            self.road = Road(self.theme, markers=self.manager.uses_markers,
                             route=self.track.build(S.SEGMENT_LENGTH))
            self.minimap.set_route(self.road.route)
            self.traffic = TrafficManager(self.road)
            self.managers = {GameMode.COMPETITIVE: RaceManager(self.road, self.traffic),
                             GameMode.ENDLESS: EndlessManager()}
            self.reset()
        self.road.apply(self.theme, markers=self.manager.uses_markers)
        self.backdrop = self.themes.backdrop(self.theme, S.WIDTH, S.HEIGHT // 2)

    def reset(self):
        """Put every piece of race state back to a fresh start (no process restart needed)."""
        self.hazards = RoadHazards(self.road)
        self.player = PlayerCar(self.selected_car_spec)       # position, speed, score, distance, collisions, cooldown, push
        self.traffic.reset(self.player, self.manager.traffic_count)     # also restores speed scale
        for manager in self.managers.values():
            manager.reset()             # timers, laps, checkpoints, endless level, banners, results
        self.shake = 0.0
        self.drift.reset()
        self.bg_scroll = 0.0
        self.flash_time = 0.0
        self.countdown = 0.0
        self.count_label = None
        self.go_time = 0.0
        self.end_time = 0.0
        self.paused = False

    @staticmethod
    def _settle_memory():
        """Avoid garbage-collector hitches during a race.

        Profiling showed the only big frame spikes (30-65 ms, all inside draw) were full GC passes
        walking the many long-lived surfaces and caches. Collect once now (menus / countdown are a
        safe moment), freeze the survivors so later passes skip them, and make full passes rare.
        """
        gc.collect()
        gc.freeze()
        gc.set_threshold(20000, 50, 200)

    def start_race(self):
        """Reset and begin the 3-2-1 countdown (the race itself starts at GO)."""
        self.reset()
        self.apply_look()
        self.manager.set_ai_level(self.ai_level)
        self.manager.setup(self.player)         # competitive: put the AI racers on the grid
        self.state = State.COUNTDOWN
        self.countdown = float(S.COUNTDOWN_SECONDS)
        self._settle_memory()               # the 3-second countdown is the safe place to pay for a collection

    def begin_playing(self):
        self.state = State.PLAYING
        self.go_time = S.GO_TIME
        self.audio.play("go")

    # ---- loop ---------------------------------------------------------------
    def run(self):
        while self.running:
            dt = min(self.clock.tick(S.FPS) / 1000.0, 0.05)
            self.handle_events()
            self.update(dt, self.read_controls())
            self.draw()
        pygame.quit()

    def handle_events(self):
        for e in pygame.event.get():
            self.handle_event(e)

    def handle_event(self, e):
        """React to one pygame event (split out so an embedding program can feed events in)."""
        if e.type == pygame.QUIT:
            self.running = False
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_F1:
                self.tuner.toggle()
            elif self.tuner.enabled and self.tuner.handle_key(e):
                pass
            elif e.key == pygame.K_m:
                self.minimap.toggle()
                self._say("MAP ON" if self.minimap.visible else "MAP OFF")
            elif self.paused:
                self._paused_key(e.key)
            elif e.key == pygame.K_p and self.state in RACE_STATES:
                self.set_paused(True)
            elif e.key == pygame.K_ESCAPE:
                self.escape()
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.press_enter()
            elif e.key == pygame.K_BACKSPACE:
                self.back()
            elif e.key in (pygame.K_LEFT, pygame.K_UP, pygame.K_RIGHT, pygame.K_DOWN):
                self.menu_move(-1 if e.key in (pygame.K_LEFT, pygame.K_UP) else 1, horizontal=e.key in (pygame.K_LEFT, pygame.K_RIGHT))
            elif e.key in ITEM_KEYS:
                self.use_item()
            elif e.key == pygame.K_v:
                levels = (0.0, 0.5, 1.0, 1.5, 2.0)
                current = min(range(len(levels)), key=lambda i: abs(levels[i] - S.DRIVING_FX_INTENSITY))
                S.DRIVING_FX_INTENSITY = levels[(current + 1) % len(levels)]
                self.drift.intensity = S.DRIVING_FX_INTENSITY
                self._say(f"DRIVING FX {int(S.DRIVING_FX_INTENSITY * 100)}%")
            elif e.key == pygame.K_n:
                self.audio.toggle_mute()
                self._say("MUTED" if self.audio.muted else f"VOLUME {int(self.audio.volume * 100)}%")
            elif e.key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
                self.audio.change_volume(0.1 if e.key == pygame.K_RIGHTBRACKET else -0.1)
                self._say(f"VOLUME {int(self.audio.volume * 100)}%")

    # ---- pause --------------------------------------------------------------
    def set_paused(self, paused):
        self.paused = paused
        if paused:
            self.audio.engine(0, False)         # silence the engine; it restarts on resume

    def _paused_key(self, key):
        if key in (pygame.K_p, pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
            self.set_paused(False)
        elif key == pygame.K_BACKSPACE:         # quit the race to the mode menu
            self.reset()
            self.state = State.MODE_SELECT
        elif key == pygame.K_q:
            self.running = False

    # ---- items --------------------------------------------------------------
    def use_item(self):
        """Fire the held item (SPACE etc.). Tells the player when the slot is empty."""
        if self.state is not State.PLAYING or not self.manager.has_items:
            return
        if not self.manager.use_item(self.player):
            self._say("NO ITEM - DRIVE THROUGH A BOX")

    def _say(self, msg):
        self.toast, self.toast_time = msg, 1.2

    # ---- menu flow: TITLE -> MODE_SELECT -> TRACK_SELECT -> COUNTDOWN --------
    def press_enter(self):
        if self.state is State.TITLE:
            self.mode_index = [m for m, _, _ in MODE_MENU].index(self.mode)
            self.state = State.MODE_SELECT
            self.audio.play("select")
        elif self.state is State.MODE_SELECT:
            self.mode = MODE_MENU[self.mode_index][0]
            self.track_index = self.tracks.index(self.track)
            self.theme_index = self.themes.themes.index(self.theme)
            self.apply_look()               # markers depend on the mode
            self.state = State.TRACK_SELECT
            self.audio.play("select")
        elif self.state is State.TRACK_SELECT:
            self.selected_track = self.track
            self.selected_theme = self.theme
            self.car_menu.select(self.selected_car_spec)
            self.player.spec = self.car_menu.selected       # the road behind the menu shows the highlighted car
            self.state = State.CAR_SELECT
            self.audio.play("select")
        elif self.state is State.CAR_SELECT:
            self.selected_car_spec = self.car_menu.selected
            self.audio.play("select")
            self.start_race()
        elif self.state in (State.FINISHED, State.GAME_OVER):
            self.start_race()               # same mode and track

    def back(self):
        """BACKSPACE: one step back through the menus (from an end screen: to the mode menu)."""
        if self.state is State.MODE_SELECT:
            self.state = State.TITLE
        elif self.state is State.CAR_SELECT:
            self.player.spec = self.selected_car_spec       # cancelled: forget the previewed car
            self.track_index = self.tracks.index(self.selected_track)
            self.theme_index = self.themes.themes.index(self.selected_theme)
            self.state = State.TRACK_SELECT
        elif self.state is State.TRACK_SELECT:
            self.theme = self.selected_theme
            self.track = self.selected_track                # discard an unconfirmed circuit preview
            self.apply_look()
            self.state = State.MODE_SELECT
        elif self.state in (State.FINISHED, State.GAME_OVER):
            self.reset()
            self.state = State.MODE_SELECT
        else:
            return
        self.audio.play("tick")

    def escape(self):
        """ESC goes back inside the menus and quits everywhere else."""
        if self.state in MENU_STATES:
            self.back()
        elif self.state in RACE_STATES:
            self.set_paused(True)               # ESC pauses a race instead of throwing it away
        else:
            self.running = False

    def menu_move(self, step, horizontal=False):
        if self.state is State.MODE_SELECT:
            if horizontal:      # LEFT/RIGHT = AI level (only for a mode that has AI opponents); UP/DOWN = mode
                if not self.managers[MODE_MENU[self.mode_index][0]].has_ai_levels:
                    return
                self.ai_level = DIFFICULTIES[(DIFFICULTIES.index(self.ai_level) + step) % len(DIFFICULTIES)]
            else:
                self.mode_index = (self.mode_index + step) % len(MODE_MENU)
        elif self.state is State.TRACK_SELECT:
            if horizontal:
                self.theme_index = (self.theme_index + step) % len(self.themes)
                self.theme = self.themes.themes[self.theme_index]
            else:
                self.track_index = (self.track_index + step) % len(self.tracks)
                self.track = self.tracks[self.track_index]
            self.apply_look()
        elif self.state is State.CAR_SELECT:
            self.car_menu.move(step)
            self.player.spec = self.car_menu.selected
        else:
            return
        self.audio.play("tick")

    def _on_tune(self, name, old, new):
        if self.state is State.PLAYING:
            self.manager.on_tune(name, old, new)

    @staticmethod
    def read_controls():
        k = pygame.key.get_pressed()
        return {
            "accelerate": k[pygame.K_UP],
            "brake": k[pygame.K_DOWN],
            "steer": int(k[pygame.K_RIGHT]) - int(k[pygame.K_LEFT]),
        }

    # ---- update, one method per state ---------------------------------------
    def update(self, dt, controls):
        self.time += dt
        self.hud.time = self.time
        self.audio.tick(dt)
        self.drift.intensity = S.DRIVING_FX_INTENSITY
        if self.paused:                         # frozen: no world, race clock, AI, effects or engine
            return
        self.last_dt = dt
        self.toast_time = max(0.0, self.toast_time - dt)
        handler = self._update_attract if self.state in ATTRACT_STATES else {
            State.COUNTDOWN: self._update_countdown, State.PLAYING: self._update_playing,
            State.FINISHED: self._update_ended, State.GAME_OVER: self._update_ended}[self.state]
        playing = self.state is State.PLAYING
        handler(dt, controls)
        self.drift.update(dt, self.player, self.road, controls, active=playing)
        self.flash_time = max(0.0, self.flash_time - dt)
        self._update_engine_sound()

    def _update_engine_sound(self):
        running = self.state in (State.COUNTDOWN, State.PLAYING)
        spec = self.player.spec
        self.audio.engine(self.player.speed_percent, running, spec.engine_pitch, spec.engine_volume)

    def _update_world(self, dt, controls):
        p = self.player
        p.update(dt, self.road, **controls)
        self.bg_scroll -= self.road.segment_at(p.z).curve * p.speed_percent * dt * 40   # parallax vs. curve
        self.traffic.update(dt, p)
        self.shake = max(0.0, self.shake - dt)

    def _update_attract(self, dt, controls):
        """Title / menu screens: cruise down the middle of the road."""
        self.player.speed = 0.45 * self.player.max_speed
        self._update_world(dt, IDLE)
        self.player.x = 0.0

    def _update_countdown(self, dt, controls):
        """Car, traffic and the mode clock are frozen; controls are ignored until GO."""
        self.countdown -= dt
        label = str(max(1, math.ceil(self.countdown)))
        if label != self.count_label and self.countdown > 0:
            self.count_label = label
            self.audio.play("beep")
        if self.countdown <= 0:
            self.begin_playing()

    def _update_playing(self, dt, controls):
        self.go_time = max(0.0, self.go_time - dt)
        self._update_world(dt, controls)
        hit = self.traffic.find_collision(self.player)
        if hit:
            if self.player.collide(hit):
                self.shake = S.SHAKE_TIME
                self.audio.play("crash")
            else:
                self.audio.play("shield")           # a shield swallowed the crash
        checkpoints = self.manager.next_checkpoint
        self.state = self.manager.update(dt, self.player)
        opponents = self.manager.field.racers if self.mode is GameMode.COMPETITIVE else ()
        self.hazards.update(dt, self.player, opponents)
        self.manager.apply_difficulty(self.traffic, self.player)
        for event in self.manager.pop_events() + self.hazards.pop_events():     # racer collisions, item pickups / hits
            if event == "bump":
                self.drift.trigger_impact(self.player)
                self.shake = S.SHAKE_TIME
                self.audio.play("crash")
                continue
            if event == "crash":
                self.shake = S.SHAKE_TIME
            self.audio.play(event)
        if self.manager.next_checkpoint != checkpoints:
            self.flash_time = CHECKPOINT_FLASH
            self.audio.play("checkpoint")
        if self.state is State.FINISHED:
            self.audio.play("finish")
        elif self.state is State.GAME_OVER:
            self.audio.play("gameover")

    def _update_ended(self, dt, controls):
        self.end_time += dt
        self._update_world(dt, COAST)

    # ---- drawing ------------------------------------------------------------
    def draw(self):
        self.render()
        pygame.display.flip()

    def render(self):
        """Draw the current frame into self.screen (without flipping the display)."""
        scene = self.scene
        scene.fill(self.theme.ground[1])
        self.backdrop.draw(scene, self.bg_scroll)
        # Camera sits behind the car; the car itself is drawn at a fixed spot.
        self.road.draw(scene, self.player.z, self.player.x,
                       self.drift.road_drawables() + self.traffic.cars + self.manager.drawables() + self.hazards.drawables())
        self.drift.draw_smoke(scene)
        self.player.draw(scene, visual_offset=self.drift.rear_offset, visual_yaw=self.drift.yaw)
        self.drift.draw_sparks(scene)
        # Collision feedback: shake the scene and tint it red, both fading out.
        t = self.shake / S.SHAKE_TIME
        offset = self.drift.shake_offset(t)
        self.screen.fill((0, 0, 0))
        self.screen.blit(scene, offset)
        if t:
            self._flash((255, 40, 40), int(110 * t))
        if self.flash_time > 0:      # checkpoint flash
            self._flash(CHECKPOINT_FLASH_COLOR, int(150 * self.flash_time / CHECKPOINT_FLASH))

        self._draw_screen()
        if self.paused:
            self.hud.draw_pause(self.screen, self.time)
        if self.toast_time > 0:
            self.hud.draw_toast(self.screen, self.toast)
        self.tuner.draw(self.screen, self.hud, self.last_dt)

    def _draw_screen(self):
        hud, scr, state = self.hud, self.screen, self.state
        if state in (State.PLAYING, State.COUNTDOWN):
            hud.draw_hud(scr, self.player, self.manager)
            opponents = self.manager.field.racers if self.mode is GameMode.COMPETITIVE else ()
            self.minimap.draw(scr, self.player, opponents)
            hud.draw_track_name(scr, self.track.name, self.manager.mode_note())
            if state is State.PLAYING:
                hud.draw_banner(scr, self.manager)
                if self.go_time > 0:
                    hud.draw_go(scr, self.go_time)
            elif self.count_label:
                hud.draw_countdown(scr, self.count_label)
        elif state is State.TITLE:
            hud.draw_start(scr, self.time)
        elif state is State.MODE_SELECT:
            options = [(name, desc, self.ai_level.name if self.managers[mode].has_ai_levels else None) for mode, name, desc in MODE_MENU]
            hud.draw_mode_select(scr, options, self.mode_index, self.time)
        elif state is State.CAR_SELECT:
            self.car_menu.draw(hud, scr, self.time)
        elif state is State.TRACK_SELECT:
            size = hud.card_size(min(3, len(self.tracks)))
            if size not in self.track_previews:
                self.track_previews[size] = tuple(MiniMap.preview(track.build(S.SEGMENT_LENGTH), size)
                                                   for track in self.tracks)
            cards = [(track.name, preview, track.tagline)
                     for track, preview in zip(self.tracks, self.track_previews[size])]
            hud.draw_track_select(scr, cards, self.track_index, self.time, self.theme.name)
            self.scenery_gallery.draw(scr, hud, self.road.route, self.theme_index,
                                      self.manager.uses_markers)
        else:
            hud.draw_end(scr, self.manager, state, self.time, self.end_time)

    def _flash(self, color, alpha):
        self.overlay.fill((*color, max(0, min(255, alpha))))
        self.screen.blit(self.overlay, (0, 0))
