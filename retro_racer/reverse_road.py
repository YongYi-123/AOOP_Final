"""SECRET ITEM 01 - THE REVERSE ROAD.

The secret: in ANY normal race, stop the car completely, keep it still for STILL_SECONDS, then really back up. The
cutscene plays once and the car backs out of the race onto THE FORGOTTEN HIGHWAY (forgotten_highway.py): a one-way road with
three checkpoint gates and a garage at the end. Reaching the garage awards the Reverse Gear.

    ReverseTrigger   the pure rule (no pygame): fed the game's frame time and the car's REAL movement along the track
    SecretRun        everything after the trigger: the cutscene, the highway, the checkpoints, the reward animation

SecretRun is not a second racing engine. It drives the racer's own PlayerCar / Road / traffic / drift effects / HUD / audio;
the Game hands it update() and render() while `game.state is State.SECRET`.

What reaches the outside is `game.secret_events` ("secret_item_found", key, first_time): the embedding arcade drains it and
fires its story event. The racer itself knows nothing about the arcade's story or saves.
"""
import math
import random

import pygame

import forgotten_highway as FH
import out_of_time as OOT
import settings as S
from assets import CYAN, WHITE, YELLOW
from car import PlayerCar
from menu_layout import fit_font

# ------------------------------------------------------------------ the secret's rule
STILL_SECONDS = 20.0         # the car must stand completely still this long (the game's own time, not wall-clock)
MIN_BACKWARD = 8600.0        # ... and keep backing up this far (world units): about 5 seconds at the reversing crawl
ITEM_KEY = "reverse_gear"    # what the arcade records the item under (arcade_lobby/quests.py: SECRET_ITEM_RETRO_RACER)
ITEM_NUMBER, ITEM_TOTAL = 1, 3
ITEM_NAME = "THE REVERSE GEAR"

NEON_CYAN, NEON_PINK = FH.NEON_CYAN, FH.NEON_PINK


class ReverseTrigger:
    """Still for STILL_SECONDS, then really backing up. Pure logic: update() gets the frame time and the player's car and
    judges only what the car ACTUALLY did (`step_dz`, its signed movement along the track this frame), never the keys.

    * `active` is False outside a running race (menus, countdown, end screens): the clock is cleared, nothing accumulates.
      A paused game does not call update() at all, so a pause adds no time either.
    * Moving at all before the time is up starts the count again.
    * It fires once. The caller then leaves the race, and reset() clears it for the next one."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.still = 0.0          # seconds of standing still so far
        self.armed = False        # the full time was served: the next real backward movement fires
        self.back = 0.0           # backward distance travelled since it was armed
        self.fired = False
        self.cue = False          # a one-shot "you can reverse now" sound is due

    def take_cue(self):
        """True once, the moment the full wait is served (the game plays its cue sound then)."""
        cue, self.cue = self.cue, False
        return cue

    @property
    def progress(self):
        """0..1: how far into the final back-up it is (0 until the full time was served). Drives the beeping."""
        return min(1.0, self.back / MIN_BACKWARD) if self.armed else 0.0

    def update(self, dt, player, active=True):
        if self.fired:
            return False
        if not active or dt <= 0:
            if not active:
                self.reset()
            return False
        velocity = player.step_dz / dt
        if abs(velocity) <= S.STILL_SPEED:                    # (a tiny float error is still "still")
            if not self.armed:
                self.still += dt
                self.armed = self.still >= STILL_SECONDS
                if self.armed:
                    self.cue = True                           # the wait is served: tell the player they may back up now
            return False
        if velocity > 0 or not self.armed:                    # driving on, or backing up too early: start over
            self.still, self.armed, self.back = 0.0, False, 0.0
            return False
        self.back += -player.step_dz
        if self.back >= MIN_BACKWARD:
            self.fired = True
            return True
        return False


# ------------------------------------------------------------------ the run
REVERSING = {"accelerate": False, "brake": True, "steer": 0}      # the car keeps backing during the cutscene
CUT_TOTAL = 6.8              # seconds of cutscene
CUT_SKIP_AFTER = 1.0         # ENTER may skip it from here on
T_STATIC, T_WRONG, T_RIGHT, T_ROAD, T_FADE = 1.0, 2.8, 4.3, 5.0, 6.1
TITLE_TIME = 2.0
FAIL_TIME = 1.3
OFF_ROAD_LIMIT = 3.5         # seconds off the tarmac before the road "glitches" you back to the last checkpoint
RESPAWN_SPEED = 0.35         # fraction of top speed you are given back at the checkpoint
REWARD_MIN = 2.6             # seconds before the reward can be dismissed
REWARD_AUTO = 12.0
RESTORED_TITLE_TIME = 2.2
LEAVE_TIME = 2.6             # the walk out of the restored road: fade, message, back to the arcade
CHASE_WARN = 12000.0         # the collapse this close behind you: the warning pulses
DUCK_LOW = 0.12              # the hub music's level at the quietest point of the cutscene


def ramp(t, a, b):
    """0 before a, 1 after b, linear between."""
    return max(0.0, min(1.0, (t - a) / (b - a)))


class SecretRun:
    CUTSCENE, TITLE, DRIVE, ARRIVE, REWARD = "cutscene", "title", "drive", "arrive", "reward"
    TIMETRAVEL, PAST_TITLE, PAST, LEAVING = "timetravel", "past_title", "past", "leaving"     # OUT OF TIME (out_of_time.py)

    def __init__(self, game):
        self.game = game
        self.phase = self.CUTSCENE
        self.t = 0.0
        self.said = set()                       # the cutscene's one-shot sounds that have played
        self.rng = random.Random(7)
        self.road = FH.ForgottenRoad()
        self.traffic = FH.obstacle_traffic(self.road)
        self.backdrop = game.themes.backdrop(FH.THEME, S.WIDTH, S.HEIGHT // 2)
        self.offset = S.CAMERA_HEIGHT * S.CAMERA_DEPTH         # how far ahead of the camera the car itself is
        self.player = None
        self.checkpoints = 0                    # gates collected, in order
        self.fails = 0                          # times sent back to a checkpoint
        self.fail_reason = ""
        self.fail_time = 0.0
        self.off_time = 0.0
        self.banner, self.banner_time = [], 0.0
        self.shake = 0.0
        self.flash = 0.0
        self.go_time = 0.0
        self.bg_scroll = 0.0
        self.arrive_time = 0.0
        self.reward_t = 0.0
        self.first_time = False
        self.finished = False                   # the garage was reached (the item has been awarded)
        self.noise = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)
        self.collapse = None                    # the falling road's state (forgotten_highway.Collapse), while on the highway
        self.rumble = 0.0                       # how hard the screen shakes while the break is close
        self.clock = 0.0
        self.owned_at_entry = game.gear_owned   # OUT OF TIME needs the Reverse Gear found BEFORE this visit
        self.egg_found = False
        self.tt = None                          # the TimeTravel cutscene while it plays
        self.past_t = 0.0
        self.leave_t = 0.0
        FH.STATE.update(sev=0.0, t=0.0, warm=False)

    # ------------------------------------------------------------ questions
    @property
    def in_cutscene(self):
        return self.phase == self.CUTSCENE

    @property
    def pausable(self):
        return self.phase in (self.DRIVE, self.ARRIVE, self.PAST)

    @property
    def progress(self):
        """How far along the highway the car itself is (world units)."""
        return self.player.distance + self.offset

    @property
    def music_duck(self):
        """The hub music's level, 0..1: it sinks through the cutscene and comes back up over the title card."""
        t = self.t
        if self.phase == self.CUTSCENE:
            return 1.0 - (1.0 - DUCK_LOW) * ramp(t, 0.4, 3.0)
        if self.phase == self.TITLE:
            return DUCK_LOW + (1.0 - DUCK_LOW) * ramp(t, 0.0, TITLE_TIME)
        return 1.0

    # ------------------------------------------------------------ input
    def confirm(self):
        """ENTER: skip the cutscene (after a moment), or dismiss the reward once it has been shown."""
        if self.phase == self.CUTSCENE and self.t >= CUT_SKIP_AFTER:
            self.skip()
        elif self.phase == self.REWARD and self.reward_t >= REWARD_MIN:
            self.leave()
        elif self.phase == self.TIMETRAVEL and self.tt.skippable:
            self.tt.skip()

    def skip(self):
        """Jump to the end of the cutscene. Safe to call any number of times."""
        if self.phase != self.CUTSCENE:
            return
        self.said.update(("glitch1", "glitch2", "wrong", "right", "warp"))
        self.t = CUT_TOTAL
        self._begin_title()

    def leave(self):
        """The run is over: the racer asks its host to close it (the arcade returns to its own world)."""
        FH.STATE.update(sev=0.0, t=0.0, warm=False)
        self.game.music_duck = 1.0
        self.game.running = False

    # ------------------------------------------------------------ the phases
    def update(self, dt, controls):
        self.t += dt
        self.clock += dt
        game = self.game
        game.music_duck = self.music_duck
        FH.STATE.update(t=self.clock, sev=self._severity())
        self.shake = max(0.0, self.shake - dt)
        self.flash = max(0.0, self.flash - dt)
        self.banner_time = max(0.0, self.banner_time - dt)
        if self.phase == self.CUTSCENE:
            self._update_cutscene(dt)
        elif self.phase == self.TITLE:
            self._update_title(dt)
        elif self.phase == self.DRIVE:
            self._update_drive(dt, controls)
        elif self.phase == self.ARRIVE:
            self._update_arrive(dt)
        elif self.phase == self.REWARD:
            self._update_reward(dt)
        elif self.phase == self.TIMETRAVEL:
            self._update_timetravel(dt)
        elif self.phase == self.PAST_TITLE:
            self._update_past_title(dt)
        elif self.phase == self.PAST:
            self._update_past(dt, controls)
        elif self.phase == self.LEAVING:
            self._update_leaving(dt)

    def _severity(self):
        if self.collapse is None or self.player is None or self.phase not in (self.DRIVE, self.ARRIVE, self.REWARD, self.TIMETRAVEL):
            return 0.0
        return self.collapse.severity(self.progress)

    def _once(self, key, at, sound):
        if key not in self.said and self.t >= at:
            self.said.add(key)
            self.game.audio.play(sound)

    def _update_cutscene(self, dt):
        game = self.game
        game._update_world(dt, REVERSING)                      # the car keeps backing up, the world keeps moving
        self._once("glitch1", T_STATIC, "glitch")
        self._once("glitch2", T_STATIC + 1.4, "glitch")
        self._once("wrong", T_WRONG, "wrongway")
        self._once("right", T_RIGHT, "rightway")
        self._once("warp", T_ROAD, "warp")
        spec = game.player.spec
        game.audio.engine(0.12 + 0.2 * ramp(self.t, 0, 1.2), True, spec.engine_pitch, spec.engine_volume * self.music_duck)
        if self.t >= CUT_TOTAL:
            self._begin_title()

    def _begin_title(self):
        """The new road: a fresh car at its start line (the one the racer was driving, same spec and paint)."""
        game = self.game
        old = game.player
        self.player = PlayerCar(old.spec)
        self.player.livery = old.livery
        self.collapse = FH.Collapse(self.road)
        self.collapse.reset(0.0, False)
        self.road.collapse = self.collapse
        self.road.plate = self.owned_at_entry              # (the hidden plate glows faintly for those who know)
        game.drift.reset()
        self.phase, self.t = self.TITLE, 0.0
        self.bg_scroll = 0.0
        game.audio.stop_engine()

    def _update_title(self, dt):
        self._engine(0.0)
        if self.t >= TITLE_TIME:
            self.phase, self.t = self.DRIVE, 0.0
            self.go_time = S.GO_TIME
            self.game.audio.play("go")

    def _engine(self, frac):
        p = self.player
        self.game.audio.engine(frac, True, p.spec.engine_pitch, p.spec.engine_volume)

    def _step_car(self, dt, controls):
        """One frame of the racer's own physics on the highway, plus the parts of the road model the Game normally adds."""
        p, road = self.player, self.road
        p.update(dt, road, **controls)
        if p.distance < 0:                                    # the road starts here: there is nothing behind the line
            p.distance, p.z, p.reverse_speed = 0.0, 0.0, 0.0
        self.bg_scroll -= road.segment_at(p.z).curve * p.speed_percent * dt * 40
        self.game.drift.update(dt, p, road, controls, active=True)
        self._engine(p.speed_percent)

    def _update_drive(self, dt, controls):
        game, p = self.game, self.player
        self.go_time = max(0.0, self.go_time - dt)
        if self.fail_time > 0:                                 # the glitch that sends you back: the car waits for it
            self.fail_time -= dt
            if self.fail_time <= 0:
                self._respawn()
            return
        self._step_car(dt, controls)
        hit = self.traffic.find_collision(p)
        if hit:
            if p.collide(hit):
                self.shake = S.SHAKE_TIME
                game.audio.play("crash")
            else:
                game.audio.play("shield")
        self._gates()
        if self.phase != self.DRIVE:
            return
        self._collapse_step(dt)
        self.off_time = self.off_time + dt if abs(p.x) > 1.0 else 0.0
        if self.off_time > OFF_ROAD_LIMIT:
            self._fail("OFF THE ROAD")
        elif not self.egg_found and OOT.crosses_plate(self.progress, p):
            self._begin_timetravel()

    # ------------------------------------------------------------ the falling road
    def _collapse_step(self, dt):
        """Keep the collapse in step with the car (it reads the car's own position every frame). After the last gate it runs
        after you; if it ever reaches you the road gives way and you are sent back to the last gate, nothing worse."""
        c = self.collapse
        chase = self.checkpoints >= len(self.road.checkpoint_z)
        c.update(dt, self.progress, chase)
        gap = c.gap(self.progress)
        self.rumble = max(0.0, 1.0 - gap / FH.CHASE_GAP) * 0.6 if chase else 0.0
        if chase and gap <= 0:
            self._fail("THE ROAD GAVE WAY")

    def _begin_timetravel(self):
        game = self.game
        self.egg_found = True
        self.phase, self.t = self.TIMETRAVEL, 0.0
        self.tt = OOT.TimeTravel(self)
        self.rumble = 0.0
        game.secret_events.append(("easter_egg_found", OOT.EGG_KEY, not game.egg_found))
        game.egg_found = True

    def _update_timetravel(self, dt):
        """The car carries on for a moment, then the world holds still while it pulls away and vanishes."""
        if self.tt.t < OOT.T_RECEDE:
            self._step_car(dt, {"accelerate": True, "brake": False, "steer": 0})
        else:
            self._engine(0.0)
        self.collapse.update(dt, self.progress, False)
        self.tt.update(dt)
        if self.tt.done:
            self._enter_past()

    def _enter_past(self):
        """The same road long ago: whole, warm, busy. A new car at its start line, no collapse, no gates."""
        game, old = self.game, self.player
        self.road = FH.ForgottenRoad(past=True)
        self.player = PlayerCar(old.spec)
        self.player.livery = old.livery
        self.traffic = FH.past_traffic(self.road, self.player)
        self.backdrop = game.themes.backdrop(FH.PAST_THEME, S.WIDTH, S.HEIGHT // 2)
        self.collapse = None
        self.tt = None
        self.rumble = 0.0
        self.banner, self.banner_time = [], 0.0
        game.drift.reset()
        FH.STATE.update(sev=0.0, warm=True)
        self.phase, self.t = self.PAST_TITLE, 0.0
        self.bg_scroll = 0.0

    def _update_past_title(self, dt):
        self._engine(0.0)
        if self.t >= RESTORED_TITLE_TIME:
            self.phase, self.t = self.PAST, 0.0
            self.go_time = S.GO_TIME
            self.game.audio.play("go")

    def _update_past(self, dt, controls):
        """Free driving on the restored road. Nothing can go wrong here: the way out is straight ahead."""
        game, p = self.game, self.player
        self.go_time = max(0.0, self.go_time - dt)
        self.past_t += dt
        self.traffic.update(dt, p)
        self._step_car(dt, controls)
        hit = self.traffic.find_collision(p)
        if hit:
            if p.collide(hit):
                self.shake = S.SHAKE_TIME
                game.audio.play("crash")
        if self.progress >= self.road.exit_z:
            self.phase, self.leave_t = self.LEAVING, 0.0
            game.audio.play("rightway")

    def _update_leaving(self, dt):
        p = self.player
        self.leave_t += dt
        p.speed = max(0.0, p.speed - S.BRAKING * 0.6 * dt)
        self._step_car(dt, {"accelerate": False, "brake": False, "steer": 0})
        limit = self.road.exit_z + FH.EXIT_DEPTH - 1500.0 - self.offset
        if p.distance > limit:
            p.distance, p.z, p.speed = limit, limit, 0.0
        if self.leave_t >= LEAVE_TIME:
            if self.game.gear_owned:
                self.leave()
            else:                                   # the round trip through time is how this run earns the Reverse Gear
                self._begin_reward()

    # ------------------------------------------------------------ checkpoints
    def _gates(self):
        """Gates must be taken IN ORDER and ON the road: only the next gate is ever looked at, and crossing its line off the
        tarmac is a miss. The finish line needs all three."""
        p, road = self.player, self.road
        while self.checkpoints < len(road.checkpoint_z) and self.progress >= road.checkpoint_z[self.checkpoints]:
            if abs(p.x) > FH.GATE_HALF_WIDTH:
                return self._fail("MISSED THE GATE")
            self.checkpoints += 1
            self.flash = 0.16
            self.banner, self.banner_time = [f"CHECKPOINT {self.checkpoints}/{len(road.checkpoint_z)}"], S.BANNER_TIME
            self.game.audio.play("checkpoint")
            if self.checkpoints == len(road.checkpoint_z):          # the last gate: the whole road starts to give way
                self.banner = [self.banner[0], "THE ROAD IS FALLING - RUN!"]
                self.banner_time = S.BANNER_TIME * 2
                self.game.audio.play("glitch")
        if self.progress >= road.finish_z:
            if self.checkpoints < len(road.checkpoint_z) or abs(p.x) > FH.GATE_HALF_WIDTH:
                return self._fail("MISSED THE GATE")
            self.phase, self.arrive_time = self.ARRIVE, 0.0
            self.game.audio.play("finish")

    def _fail(self, reason):
        self.fails += 1
        self.fail_reason, self.fail_time = reason, FAIL_TIME
        self.flash, self.shake = 0.3, 0.25
        self.game.audio.play("glitch")

    def checkpoint_progress(self):
        """Where a retry starts: just past the last gate collected (or the start line)."""
        if self.checkpoints == 0:
            return 0.0
        return self.road.checkpoint_z[self.checkpoints - 1] - self.offset + 600.0

    def _respawn(self):
        p = self.player
        p.distance = self.checkpoint_progress()
        p.z = p.distance
        p.x, p.push, p.reverse_speed, p.reverse_hold = 0.0, 0.0, 0.0, 0.0
        p.speed = S.MAX_SPEED * p.spec.max_speed * RESPAWN_SPEED
        p.effects = []
        p.hit_cooldown = 1.0
        self.off_time = 0.0
        self.collapse.reset(self.progress, self.checkpoints >= len(self.road.checkpoint_z))    # a retry starts from a clean break
        self.rumble = 0.0
        self.go_time = S.GO_TIME * 0.6
        self.banner, self.banner_time = ["BACK ON THE ROAD"], S.BANNER_TIME

    # ------------------------------------------------------------ the garage and the reward
    def _update_arrive(self, dt):
        p = self.player
        p.speed = max(0.0, p.speed - S.BRAKING * dt)                       # the garage stops you: a firm automatic brake
        self._step_car(dt, {"accelerate": False, "brake": False, "steer": 0})
        limit = self.road.garage_z - 1500.0 - self.offset                  # never through the door
        if p.distance > limit:
            p.distance, p.z, p.speed = limit, limit, 0.0
        if p.speed <= 1.0:
            self.arrive_time += dt
        if self.arrive_time >= 0.9:
            self._begin_reward()

    def _begin_reward(self):
        game = self.game
        self.phase, self.reward_t = self.REWARD, 0.0
        self.finished = True
        self.first_time = not game.gear_owned
        game.gear_owned = True
        game.secret_events.append(("secret_item_found", ITEM_KEY, self.first_time))
        game.audio.stop_engine()
        game.audio.play("gear")

    def _update_reward(self, dt):
        self.reward_t += dt
        if self.reward_t >= REWARD_AUTO:
            self.leave()

    # ================================================================ drawing
    def render(self, screen):
        """Everything but the first cutscene (the Game draws the old race under that one)."""
        game = self.game
        if self.phase == self.CUTSCENE:
            return
        p = self.player
        scene = game.scene
        theme = FH.PAST_THEME if self.road.past else FH.THEME
        scene.fill(theme.ground[1])
        self.backdrop.draw(scene, self.bg_scroll)
        if self.collapse is not None:
            FH.draw_background_decay(scene, self._severity(), self.bg_scroll, self.clock)
        self.road.draw(scene, p.z, p.x, game.drift.road_drawables() + self.traffic.cars)
        if self.collapse is not None:
            self.collapse.draw_debris(scene)
        game.drift.draw_smoke(scene)
        if self.phase != self.TIMETRAVEL:                    # (in the time-travel cutscene the scene draws the car itself)
            p.draw(scene, visual_offset=game.drift.rear_offset, visual_yaw=game.drift.yaw)
        game.drift.draw_sparks(scene)
        screen.fill((0, 0, 0))
        screen.blit(scene, game.drift.shake_offset(max(self.shake / S.SHAKE_TIME, self.rumble)))
        if self.shake > 0:
            game._flash((255, 40, 40), int(90 * self.shake / S.SHAKE_TIME))
        if self.flash > 0:
            game._flash((255, 240, 140), int(150 * min(1.0, self.flash / 0.16)))
        if self.phase == self.TIMETRAVEL:
            self.tt.draw(screen, game.hud)
            return
        self._draw_hud(screen)
        if self.phase == self.TITLE:
            self._draw_title(screen)
        elif self.phase == self.PAST_TITLE:
            self._draw_past_title(screen)
        elif self.phase == self.REWARD:
            self._draw_reward(screen)
        elif self.phase == self.LEAVING:
            self._draw_leaving(screen)
        if self.road.past and self.phase in (self.PAST_TITLE, self.PAST) and self.past_t_total() < 1.6:
            OOT.draw_arrival(screen, self.past_t_total(), S.WIDTH // 2, S.HEIGHT - 30, 150 * p.spec.width,
                             random.Random(int(self.clock * 22)))
        if self.fail_time > 0:
            self._draw_fail(screen)

    def past_t_total(self):
        """Seconds since arriving in the past (the title card, then the free drive)."""
        return self.t if self.phase == self.PAST_TITLE else RESTORED_TITLE_TIME + self.t

    def _draw_hud(self, screen):
        hud, p = self.game.hud, self.player
        if self.phase == self.REWARD:
            return
        kmh = int(p.speed_ratio * S.DISPLAY_MAX_KMH)
        hud.text(screen, "SPEED", (20, 12), CYAN)
        hud.text(screen, f"{kmh:3d} KM/H", (20, 38), YELLOW, hud.big)
        hud.text(screen, "COLLISIONS", (20, S.HEIGHT - 66), CYAN)
        hud.text(screen, f"{p.collisions:02d}", (20, S.HEIGHT - 44), YELLOW, hud.big)
        if self.road.past:
            self._draw_past_hud(screen)
            return
        total = len(self.road.checkpoint_z)
        hud.text(screen, "CHECKPOINT", (S.WIDTH // 2, 8), CYAN, align="center")
        hud.text(screen, f"{self.checkpoints}/{total}", (S.WIDTH // 2, 30), YELLOW, hud.huge, align="center")
        self._draw_route_bar(screen)
        self._draw_no_signal(screen)
        hud.draw_track_name(screen, FH.NAME, "")
        if self.banner_time > 0 and self.fail_time <= 0:
            a = int(255 * min(1.0, (self.banner_time / S.BANNER_TIME) * 2))
            hud.text(screen, self.banner[0], (S.WIDTH // 2, hud.BANNER_Y), YELLOW, hud.huge, "center", a)
            if len(self.banner) > 1:
                hud.text(screen, self.banner[1], (S.WIDTH // 2, hud.BANNER_Y + 52), (255, 110, 150), hud.big, "center", a)
        if self.phase == self.DRIVE and self.go_time > 0 and self.fail_time <= 0:
            hud.draw_go(screen, self.go_time)
        if self.owned_at_entry and not self.egg_found and self.phase == self.DRIVE and OOT.on_straight(self.progress):
            self._draw_gauge(screen)

    def _draw_gauge(self, screen):
        """The egg's own speed reading, shown only on the long straight and only to someone who already has the Reverse Gear."""
        hud, value = self.game.hud, OOT.mph(self.player)
        hot = value >= OOT.TARGET_MPH
        box = pygame.Rect(14, 84, 220, 56)
        shade = pygame.Surface(box.size, pygame.SRCALPHA)
        shade.fill((10, 8, 40, 180))
        screen.blit(shade, box.topleft)
        pygame.draw.rect(screen, (255, 200, 90) if hot else (110, 190, 255), box, 2)
        hud.text(screen, "TEMPORAL SPEED", (box.centerx, box.y + 4), (140, 200, 255), hud.small, "center")
        color = (255, 226, 120) if hot and int(self.clock * 6) % 2 == 0 else (230, 245, 255)
        hud.text(screen, f"{int(value):3d} MPH", (box.centerx, box.y + 22), color, hud.big, "center")

    def _draw_no_signal(self, screen):
        """Where the minimap normally sits there is nothing to show on this road: a dead screen reading NO SIGNAL (static, a
        flickering label). While the road is breaking up right behind you it also blinks RUN! under the route bar."""
        hud = self.game.hud
        rect = pygame.Rect(S.WIDTH - 200, 12, 188, 140)
        pygame.draw.rect(screen, (10, 6, 26), rect)
        rng = random.Random(int(self.clock * 14))
        for _ in range(90):                                         # static
            color = rng.choice(((60, 52, 100), (90, 80, 140), (30, 24, 60), NEON_CYAN, NEON_PINK))
            pygame.draw.rect(screen, color, (rect.x + rng.randrange(rect.w - 4), rect.y + rng.randrange(rect.h - 4), rng.choice((2, 4)), 2))
        for y in range(rect.y, rect.bottom, 4):                     # scanlines
            pygame.draw.line(screen, (10, 6, 26), (rect.x, y), (rect.right - 1, y))
        pygame.draw.rect(screen, (110, 96, 170), rect, 2)
        if int(self.clock * 2) % 4 != 3:
            font = hud.font
            height = font.render("NO SIGNAL", False, (255, 255, 255)).get_height()
            hud.text(screen, "NO SIGNAL", (rect.centerx, rect.centery - height // 2), (255, 110, 150), font, "center")
        if self.collapse is not None and self.collapse.chase and self.collapse.gap(self.progress) < CHASE_WARN \
                and int(self.clock * 6) % 2 == 0:
            hud.text(screen, "RUN!", (S.WIDTH // 2, 98), (255, 90, 110), hud.big, "center")

    def _draw_past_hud(self, screen):
        hud, road = self.game.hud, self.road
        hud.text(screen, "THEN", (S.WIDTH // 2, 8), (255, 206, 120), hud.small, "center")
        hud.text(screen, "EXIT AHEAD", (S.WIDTH // 2, 30), (255, 236, 200), hud.big, "center")
        x0, x1, y = S.WIDTH // 2 - 160, S.WIDTH // 2 + 160, 86
        pygame.draw.rect(screen, (50, 30, 60), (x0 - 2, y - 4, x1 - x0 + 4, 10))
        pygame.draw.rect(screen, (255, 130, 150), (x0 - 2, y - 4, x1 - x0 + 4, 10), 1)
        fill = max(0.0, min(1.0, self.progress / road.exit_z))
        pygame.draw.rect(screen, (255, 206, 120), (x0, y - 2, int((x1 - x0) * fill), 6))
        pygame.draw.rect(screen, WHITE, (x1 - 1, y - 7, 3, 16))
        hud.draw_track_name(screen, FH.NAME + " (THEN)", "")
        if self.phase == self.PAST and self.go_time > 0:
            hud.draw_go(screen, self.go_time)

    def _draw_past_title(self, screen):
        hud = self.game.hud
        a = int(255 * min(ramp(self.t, 0.5, 1.0), 1 - ramp(self.t, RESTORED_TITLE_TIME - 0.5, RESTORED_TITLE_TIME)))
        shade = pygame.Surface((S.WIDTH, 150), pygame.SRCALPHA)
        shade.fill((60, 20, 60, int(150 * a / 255)))
        screen.blit(shade, (0, 190))
        font = fit_font((hud.title, hud.huge, hud.big), FH.NAME, S.WIDTH - 60)
        hud.text(screen, FH.NAME, (S.WIDTH // 2, 214), (255, 236, 200), font, "center", a)
        hud.text(screen, "LONG BEFORE IT FELL", (S.WIDTH // 2, 290), (255, 150, 150), hud.font, "center", a)

    def _draw_leaving(self, screen):
        hud = self.game.hud
        f = ramp(self.leave_t, 0.2, LEAVE_TIME - 0.3)
        layer = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)
        layer.fill((255, 236, 200, int(255 * f)))
        screen.blit(layer, (0, 0))
        if f > 0.4:
            hud.text(screen, "BACK TO THE PRESENT", (S.WIDTH // 2, 270), (120, 70, 110), hud.huge, "center", int(255 * ramp(f, 0.4, 0.8)))

    def _draw_route_bar(self, screen):
        """A thin progress line along the top of the road: where you are between the start and the garage, and the gates."""
        road = self.road
        x0, x1, y = S.WIDTH // 2 - 160, S.WIDTH // 2 + 160, 86
        pygame.draw.rect(screen, (20, 10, 44), (x0 - 2, y - 4, x1 - x0 + 4, 10))
        pygame.draw.rect(screen, NEON_PINK, (x0 - 2, y - 4, x1 - x0 + 4, 10), 1)
        span = road.finish_z
        fill = max(0.0, min(1.0, self.progress / span))
        pygame.draw.rect(screen, NEON_CYAN, (x0, y - 2, int((x1 - x0) * fill), 6))
        for i, z in enumerate(road.checkpoint_z):
            gx = x0 + int((x1 - x0) * z / span)
            pygame.draw.rect(screen, YELLOW if i < self.checkpoints else WHITE, (gx - 1, y - 7, 3, 16))
        pygame.draw.rect(screen, WHITE, (x1 - 1, y - 7, 3, 16))

    def _draw_title(self, screen):
        hud = self.game.hud
        a = int(255 * min(ramp(self.t, 0, 0.5), 1 - ramp(self.t, TITLE_TIME - 0.5, TITLE_TIME)))
        shade = pygame.Surface((S.WIDTH, 150), pygame.SRCALPHA)
        shade.fill((10, 4, 30, int(170 * a / 255)))
        screen.blit(shade, (0, 190))
        font = fit_font((hud.title, hud.huge, hud.big), FH.NAME, S.WIDTH - 60)
        hud.text(screen, FH.NAME, (S.WIDTH // 2, 214), NEON_CYAN, font, "center", a)
        hud.text(screen, "A ROAD THAT WAS NEVER ON THE MAP", (S.WIDTH // 2, 290), NEON_PINK, hud.font, "center", a)

    def _draw_fail(self, screen):
        hud = self.game.hud
        shade = pygame.Surface((S.WIDTH, 120), pygame.SRCALPHA)
        shade.fill((10, 4, 30, 170))
        screen.blit(shade, (0, 200))
        hud.text(screen, "GLITCH!", (S.WIDTH // 2 + self.rng.choice((-3, 0, 3)), 210), NEON_PINK, hud.huge, "center")
        hud.text(screen, self.fail_reason, (S.WIDTH // 2, 262), WHITE, hud.big, "center")
        where = f"BACK TO CHECKPOINT {self.checkpoints}" if self.checkpoints else "BACK TO THE START"
        hud.text(screen, where, (S.WIDTH // 2, 300), YELLOW, hud.font, "center")

    # ------------------------------------------------------------ the cutscene
    def draw_cutscene(self, screen):
        """Drawn over the old race (which the Game has just rendered): static, flickering neon, the two titles and the new road."""
        t, hud, rng = self.t, self.game.hud, random.Random(int(self.t * 24))
        live = ramp(t, 0.5, T_STATIC)
        screen.blit(hud.scanlines, (0, 0)) if live > 0 else None
        self._neon_flicker(screen, t, rng)
        if t >= T_STATIC and t < T_FADE + 0.4:
            self._static(screen, rng, min(1.0, live) * (1.0 - 0.5 * ramp(t, T_ROAD, T_FADE)))
        if t >= T_ROAD:
            self._new_road(screen, t)
            self.game.player.draw(screen, visual_offset=0, visual_yaw=0)           # the car stays on top of it
        self._cutscene_text(screen, t, rng)
        fade = ramp(t, T_FADE, CUT_TOTAL)
        if fade > 0:
            self.game._flash((14, 6, 36), int(255 * fade))

    def _neon_flicker(self, screen, t, rng):
        """The old track's neon misbehaves: a tinted wash and bright tubes that stutter. (Steps ~4 times a second and kept
        soft: it is meant to look broken, not to strobe.)"""
        if not 1.5 < t < T_ROAD + 0.6:
            return
        step = random.Random(int(t * 4))
        if step.random() < 0.65:
            color = step.choice((NEON_CYAN, NEON_PINK, (170, 120, 255)))
            self.game._flash(color, 46)
        for y, color in ((self.game.scene.get_height() // 2 - 2, NEON_PINK), (self.game.scene.get_height() // 2 + 6, NEON_CYAN)):
            if step.random() < 0.7:
                pygame.draw.rect(screen, color, (0, y, S.WIDTH, 3))

    def _static(self, screen, rng, amount):
        """Torn rows of the picture shoved sideways, and a sprinkle of coloured pixels."""
        if amount <= 0:
            return
        snap = screen.copy()
        for _ in range(int(3 + 7 * amount)):
            y, h = rng.randrange(0, S.HEIGHT - 40), rng.choice((6, 10, 16, 24))
            dx = rng.choice((-1, 1)) * rng.randrange(8, int(16 + 56 * amount))
            screen.blit(snap, (dx, y), (0, y, S.WIDTH, h))
            screen.blit(snap, (dx - S.WIDTH * (1 if dx > 0 else -1), y), (0, y, S.WIDTH, h))
        for _ in range(int(60 * amount)):
            color = rng.choice((NEON_CYAN, NEON_PINK, WHITE, (170, 120, 255)))
            pygame.draw.rect(screen, color, (rng.randrange(S.WIDTH), rng.randrange(S.HEIGHT), rng.choice((2, 4, 6)), 2))

    def _cutscene_text(self, screen, t, rng):
        hud = self.game.hud
        if T_WRONG <= t < T_RIGHT - 0.1:
            text, color, shade = "WRONG WAY?", (255, 80, 110), (110, 20, 50)
        elif T_RIGHT <= t < T_FADE + 0.3:
            text, color, shade = "...OR THE RIGHT WAY?", NEON_CYAN, (30, 80, 120)
        else:
            return
        start = T_WRONG if t < T_RIGHT else T_RIGHT
        a = int(255 * ramp(t, start, start + 0.15))
        font = fit_font((hud.title, hud.huge, hud.big), text, S.WIDTH - 60)
        jitter = rng.choice((-4, 0, 0, 4)) if t - start < 0.4 else 0                # a short stutter as each title lands
        plate = pygame.Surface((S.WIDTH, 120), pygame.SRCALPHA)
        plate.fill((10, 4, 30, int(150 * a / 255)))
        screen.blit(plate, (0, 224))
        hud.extruded(screen, text, (S.WIDTH // 2 + jitter, 252), color, shade, font, 3)

    def _new_road(self, screen, t):
        """A road that was never there, opening up beneath the car: a neon trapezoid reaching the horizon, edges and dashes
        scrolling towards you, streaks of light flaring out from the vanishing point."""
        g = ramp(t, T_ROAD, T_ROAD + 1.0)
        horizon, cx = S.HEIGHT // 2, S.WIDTH // 2
        bottom_half = 40 + 520 * g
        top_half = 6 + 22 * g
        pts = [(cx - top_half, horizon), (cx + top_half, horizon), (cx + bottom_half, S.HEIGHT), (cx - bottom_half, S.HEIGHT)]
        layer = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(layer, (46, 38, 86, int(235 * g)), pts)
        pygame.draw.line(layer, (*NEON_CYAN, 255), pts[0], pts[3], 5)
        pygame.draw.line(layer, (*NEON_PINK, 255), pts[1], pts[2], 5)
        scroll = (t * 1.6) % 1.0
        for k in range(8):
            f = ((k + scroll) / 8) ** 2
            y = horizon + (S.HEIGHT - horizon) * f
            half = top_half + (bottom_half - top_half) * f
            pygame.draw.line(layer, (196, 168, 255, int(255 * g)), (cx - half * 0.04, y), (cx + half * 0.04, y),
                             max(2, int(2 + 8 * f)))
        for i in range(14):
            a = i * math.tau / 14 + t
            r0, r1 = 40 + 30 * ((i * 7) % 5), 180 + 420 * g
            color = NEON_CYAN if i % 2 else NEON_PINK
            pygame.draw.line(layer, (*color, int(150 * g)), (cx + r0 * math.cos(a), horizon + r0 * 0.4 * math.sin(a)),
                             (cx + r1 * math.cos(a), horizon + r1 * 0.55 * math.sin(a)), 2)
        screen.blit(layer, (0, 0))

    # ------------------------------------------------------------ the reward animation
    def _draw_reward(self, screen):
        hud, t = self.game.hud, self.reward_t
        dim = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)
        dim.fill((10, 4, 30, int(210 * ramp(t, 0, 0.5))))
        screen.blit(dim, (0, 0))
        screen.blit(hud.scanlines, (0, 0))
        cx = S.WIDTH // 2
        fall = ramp(t, 0.15, 0.95)
        bounce = abs(math.sin((t - 0.95) * 7)) * 14 * max(0.0, 1 - (t - 0.95) / 0.8) if t > 0.95 else 0.0
        gy = -60 + (250 + 60) * (1 - (1 - fall) ** 2) - bounce
        radius = 74 + 4 * math.sin(t * 3)
        for i in range(12):                                            # slow rays behind the gear
            a = t * 0.6 + i * math.tau / 12
            pygame.draw.line(screen, (90, 60, 140), (cx, gy), (cx + 330 * math.cos(a), gy + 330 * math.sin(a)), 3)
        FH.draw_gear(screen, (cx, gy), radius, angle=t * 0.9)
        for i in range(10):                                            # little pixel sparkles around it
            a, r = i * 2.4 + t * 1.5, radius * (1.15 + 0.35 * ((i * 5) % 3) / 3)
            if int(t * 6 + i) % 3:
                pygame.draw.rect(screen, YELLOW if i % 2 else WHITE, (cx + r * math.cos(a), gy + r * math.sin(a), 6, 6))
        title = "SECRET ITEM FOUND" if self.first_time else "ALREADY IN YOUR COLLECTION"
        if t >= 1.0:
            font = fit_font((hud.huge, hud.big), title, S.WIDTH - 60)
            hud.extruded(screen, title, (cx, 352), YELLOW, (150, 60, 0), font, 3)
        if t >= 1.6:
            hud.text(screen, f"{ITEM_NUMBER:02d} / {ITEM_TOTAL:02d}", (cx, 410), NEON_CYAN, hud.huge, "center")
        if t >= 2.2:
            hud.text(screen, ITEM_NAME, (cx, 468), WHITE, hud.big, "center")
        if t >= REWARD_MIN and int(t * 2) % 2 == 0:
            hud.text(screen, f"{hud.keys['confirm']}: BACK TO THE ARCADE", (cx, 540), NEON_PINK, hud.small, "center")
