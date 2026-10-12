"""Shared test helpers: a Run past its READY banner, stepping and a scripted cat."""
import random

from neon_cat_maze import config as cfg
from neon_cat_maze.model import Run

DT = 1 / 60


def running(seed=1, level=1, quiet=True):
    """A Run in its 'run' phase. quiet=True keeps every robot in the den so movement can be tested alone."""
    run = Run(random.Random(seed), level)
    run.phase, run.phase_time = "run", 0.0
    if quiet:
        for robot in run.robots:
            robot.release_in = 10 ** 6
    return run


def advance(run, seconds, dt=DT):
    for _ in range(round(seconds / dt)):
        run.update(dt)
        yield


def play(run, seconds, dt=DT):
    for _ in advance(run, seconds, dt):
        pass


def names(run):
    return [e.name for e in run.take_events()]


def clear_level(run):
    """Eat everything and sit through the level-clear panel."""
    run.phase, run.phase_time = "run", 0.0
    run.fish.clear()
    play(run, 0.05)
    play(run, cfg.CLEAR_SECONDS + 0.1)
