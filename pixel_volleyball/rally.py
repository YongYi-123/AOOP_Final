"""Normal returns: a gentle, aimed lob that always clears the net.

A normal hit is not a fixed velocity. The ball is lifted to a comfortable apex
(LOB_APEX above the contact point, raised only when the net needs it) and sent
to a landing spot in the opponent's half. The player steers the depth with the
direction key at contact: toward the net lands deeper, away from it lands
shorter. Horizontal speed is capped (LOB_VX_MAX), so a return is never fast.
"""
import math
from .court import BALL_GRAVITY, FLOOR, NET_X
from .smash import SmashAttack

LOB_APEX = 100              # px above the contact point, normally
LOB_APEX_STEP = 10          # how much higher to lift it, until the net is cleared
CEILING_MARGIN = 62         # the apex never goes above this y
LOB_VX_MIN, LOB_VX_MAX = 45, 150
LOB_DEPTH = 85              # landing distance beyond the net with no steering
LOB_STEER = 28              # px of extra / less depth when the key is held at contact
LOB_DEPTH_MIN, LOB_DEPTH_MAX = 45, 125
MIN_APEX = 25               # a return always rises at least this far
POP_CEILING = 90            # the yarn is never popped higher than this y
POP_UP = 10                 # px the yarn is lifted per retry when the net is in the way


def lob_velocity(player, ball):
    """(vx, vy) for a normal return struck by `player`; ball.y may be raised a
    few pixels (the yarn pops up off the paw) when the contact is so close to the
    net that no arc from the head could otherwise clear the tape."""
    direction = 1 if player.side == 0 else -1
    depth = LOB_DEPTH + LOB_STEER * player.moving * direction
    target = NET_X + direction * max(LOB_DEPTH_MIN, min(LOB_DEPTH_MAX, depth))
    land_y = FLOOR - ball.radius
    ball_y0 = ball.y
    # Normally: a 2px safety gap over the tape and at least LOB_VX_MIN forward. A yarn hit while touching
    # the tape needs a tighter gap and, last of all, a slower drift so it can rise before it crosses.
    for margin, vx_min in ((ball.radius + 2, LOB_VX_MIN), (ball.radius + .5, LOB_VX_MIN),
                           (ball.radius + .5, 25), (ball.radius + .5, 12)):
        ball.y = ball_y0
        for _lift in range(8):
            limit = ball.y - CEILING_MARGIN
            height = max(MIN_APEX, min(LOB_APEX, limit))
            while True:
                vy = -math.sqrt(2 * BALL_GRAVITY * height)
                flight = (-vy + math.sqrt(vy * vy + 2 * BALL_GRAVITY * max(0.0, land_y - ball.y))) / BALL_GRAVITY
                vx = direction * max(vx_min, min(LOB_VX_MAX, (target - ball.x) * direction / flight))
                if SmashAttack._clears_net(ball, vx, vy, direction, margin):
                    return vx, vy
                if height + LOB_APEX_STEP > max(limit, MIN_APEX):
                    break
                height += LOB_APEX_STEP
            if ball.y - POP_UP < POP_CEILING:
                break
            ball.y -= POP_UP                     # still blocked by the net: pop it a little higher and retry
    return vx, vy
