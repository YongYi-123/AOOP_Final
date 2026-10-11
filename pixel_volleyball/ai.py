"""Reaction-limited AI strategies; all opponents use the same player physics."""
import math
from .court import BALL_GRAVITY
from .smash import SmashAttack


class VolleyAI:
    """Sandra is a friendly opponent: she re-aims every 180 ms with a visible
    positioning error, is caught napping by one incoming ball in four (LAPSE_EVERY),
    and goes for a Smash on one offered ball in four (SMASH_EVERY). She uses ordinary player
    inputs and the same movement speed as a human."""
    REACTION = .18
    ERROR = 16
    LAPSE_EVERY = 4         # every 4th ball struck toward her catches her napping
    LAPSE_DELAY = .25       # she stands still this long (seconds) on that ball
    SMASH_EVERY = 4         # she smashes one offered ball in four
    SMASH_AIM_EVERY = 2     # only every 2nd Smash is placed away from the human; the rest go straight at them
    SMASH_SHOCK = .30       # a Smash coming over costs her this long: it can score, if she is out of position

    def __init__(self):
        self.wait = 0
        self.decisions = 0
        self.target = 290
        self.jump_wait = 0.0
        self.opportunities = 0      # balls offered in the Smash zone so far
        self.had_chance = False
        self.going_for_smash = False
        self.prev_incoming = False
        self.smashes = 0
        self.freeze = 0.0
        self.balls_received = 0
        self.lapse = False

    def smash_aim(self, human_x):
        """Landing x for Sandra's Smash. Every SMASH_AIM_EVERY-th one is placed away from the
        human; the others land near where the human is standing, so they can be returned."""
        self.smashes += 1
        if self.smashes % self.SMASH_AIM_EVERY == 0:
            return 60 if human_x > 120 else 150
        return max(60, min(150, human_x))

    @staticmethod
    def predict(ball):
        """Simulate gravity, ceiling and side walls until receiving height."""
        x, y, vx, vy = ball.x, ball.y, ball.vx, ball.vy
        step = 1 / 120
        for _ in range(360):
            vy += BALL_GRAVITY * step
            x += vx * step
            y += vy * step
            if x < 26 or x > 374:
                x = max(26, min(374, x))
                vx = -vx
            if y < 58:
                y, vy = 58, abs(vy)
            if y >= 224 and vy > 0:
                return x
        return x

    @staticmethod
    def intercept(ball, height=150):
        """(x, seconds) where the ball first descends through `height` on Sandra's
        side, or None if it never does (it lands, or is hit away, first)."""
        x, y, vx, vy = ball.x, ball.y, ball.vx, ball.vy
        step = 1 / 120
        for i in range(360):
            vy += BALL_GRAVITY * step
            x += vx * step
            y += vy * step
            if x < 26 or x > 374:
                x = max(26, min(374, x))
                vx = -vx
            if y < 58:
                y, vy = 58, abs(vy)
            if y >= 224 and vy > 0:
                return None
            if y >= height and vy > 0:
                return (x, (i + 1) * step) if x >= 205 else None
        return None

    def smash_target(self, player, ball):
        """Where to stand to jump-smash, only when she can arrive with time to spare."""
        chance = self.intercept(ball)
        if chance is None or not self.going_for_smash:
            return None
        x, seconds = chance
        reach = 155 * max(0, seconds - self.REACTION) + 8
        return x if abs(x - player.x) <= reach else None

    def controls(self, player, ball, dt=1/120):
        from .model import VolleyInput
        # Sandra goes for a Smash on one ball in SMASH_EVERY offered in the zone, so
        # she stays beatable and a human always gets a breather.
        chance = self.intercept(ball)
        if chance is not None and not self.had_chance:
            self.opportunities += 1
        self.had_chance = chance is not None
        self.going_for_smash = self.opportunities % self.SMASH_EVERY == self.SMASH_EVERY - 1
        incoming = ball.vx > 30                                    # heading for her side
        if incoming and not self.prev_incoming:                    # a new ball has just been struck toward her
            self.balls_received += 1
            self.lapse = self.balls_received % self.LAPSE_EVERY == 0
            if self.lapse:
                self.freeze = self.LAPSE_DELAY                     # caught napping: she stands still for a moment
            if ball.smash_left > 0 or ball.vx > 190:               # blazing yarn: a moment of shock
                self.freeze = max(self.freeze, self.SMASH_SHOCK)
        self.prev_incoming = incoming
        if self.freeze > 0:
            self.freeze = max(0.0, self.freeze - dt)
            return VolleyInput()
        self.wait -= dt
        self.jump_wait = max(0, self.jump_wait - dt)
        if self.wait <= 0:
            self.decisions += 1
            error = self.ERROR * math.sin(self.decisions * 1.7) * (2 if self.lapse else 1)
            target = self.predict(ball)
            attack = self.smash_target(player, ball)
            if attack is not None:
                target = attack
            self.target = max(218, min(366, target + error)) if target > 200 else 290
            self.wait = self.REACTION
        delta = self.target - player.x
        move = 0 if abs(delta) < 4 else (1 if delta > 0 else -1)
        near = abs(ball.x - player.x) < 28 and ball.x > 207
        # A jump takes ~0.2 seconds to meet a descending ball above the net.
        jump = (near and 80 < ball.y < 145 and -40 < ball.vy < 180
                and player.y >= 258-player.radius and player.hit_cooldown == 0
                and self.jump_wait == 0)
        # Smash jump: leave the floor ~0.34 s before the ball reaches the zone just
        # above the net, which puts her near head height of the ball at the top.
        jump = jump or (chance is not None and self.going_for_smash and .24 < chance[1] < .42
                        and abs(chance[0] - player.x) < 26
                        and player.y >= 258 - player.radius and player.hit_cooldown == 0
                        and self.jump_wait == 0)
        if jump:
            self.jump_wait = 1.1
        # Press once shortly before head contact; the swing stays live for
        # ~0.24 s, so Sandra only needs to be roughly on time.
        relative_y = ball.y - player.y
        closing = ball.vy - player.vy
        approaching = (-45 < relative_y < -12 and closing > 0)
        time_to_contact = max(0, (-18-relative_y) / max(1, closing))
        spike = (near and player.y < 190 and ball.y < 156
                 and approaching and time_to_contact < .12
                 and player.attack.age >= SmashAttack.RECOVER and not player.attack.held)
        return VolleyInput(move, jump, spike)
