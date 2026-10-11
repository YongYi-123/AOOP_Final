"""A simple scripted pilot, used to prove the early waves are fair: it dodges the bolt about to land
on it, otherwise lines up under the lowest enemy, and holds fire."""
from galaxy_defender import config as cfg


def _landing_x(bolt):
    return bolt.x + bolt.vx * max(0, (cfg.PLAYER_Y - bolt.y) / max(bolt.vy, 1))


def move_for(run):
    near = [b for b in run.enemy_bolts if cfg.PLAYER_Y - 120 < b.y < cfg.PLAYER_Y + 10
            and (abs(_landing_x(b) - run.x) < 22 or abs(b.x - run.x) < 22)]
    if near:
        step = 1 if run.x >= _landing_x(max(near, key=lambda b: b.y)) else -1
        if (step > 0 and run.x > cfg.FIELD_W - 14) or (step < 0 and run.x < 14):
            step = -step
        return step
    targets = list(run.enemies) + ([run.boss] if run.boss else [])
    if not targets:
        return 0
    target = max(targets, key=lambda e: e.y)
    return 0 if abs(target.x - run.x) < 4 else (1 if target.x > run.x else -1)
