"""The three robot brains. Each is a pure function of (maze, robot, cat, rng): it only ever picks one of the open
neighbouring tiles, so a robot cannot leave the maze lanes, and every tie is broken by the fixed direction order, so
a seeded rng reproduces a whole run exactly."""
from . import config as cfg
from .mazes import DIRS
from .pathing import best_option, farthest_option, path_distance


def options_for(maze, robot):
    """The (direction, tile) choices at the tile `robot` has just reached: no turning back unless it is a dead end,
    and no re-entering the den unless it is leaving it or returning as eyes."""
    opts = maze.neighbours(robot.tile)
    if robot.mode == "active":
        opts = [o for o in opts if o[1] not in maze.restricted]
    ahead = [o for o in opts if o[0] != (-robot.dir[0], -robot.dir[1])]
    return ahead or opts


def ambush_target(maze, cat):
    """The tile `AMBUSH_LOOKAHEAD` tiles ahead of the cat along its way (stopping at the first wall)."""
    tile = cat.tile if cat.t < 0.5 else (cat.tile[0] + cat.dir[0], cat.tile[1] + cat.dir[1])
    d = cat.dir if cat.dir != (0, 0) else cat.facing
    for _ in range(cfg.AMBUSH_LOOKAHEAD):
        nxt = (tile[0] + d[0], tile[1] + d[1])
        if not maze.is_open(nxt) or nxt in maze.restricted:
            break
        tile = nxt
    return tile


def scatter_corner(maze, kind):
    corners = maze.corners
    return {"patrol": corners[3], "chase": corners[1], "ambush": corners[0]}[kind]


def choose(maze, robot, cat, scattering, difficulty, rng):
    """The direction `robot` takes from the tile it has just reached, or (0, 0) to wait."""
    opts = options_for(maze, robot)
    if not opts:
        return (0, 0)
    cat_tile = cat.nearest_tile()
    if robot.mode == "exit":
        return best_option(maze, opts, maze.door)[0]
    if robot.mode == "eyes":
        return best_option(maze, opts, maze.den[len(maze.den) // 2])[0]
    if robot.fright:
        # run away - but not perfectly: now and then a frightened robot takes a random lane
        if len(opts) > 1 and rng.random() < 0.25:
            return rng.choice(opts)[0]
        return farthest_option(maze, opts, cat_tile)[0]
    if robot.kind == "patrol":
        return _patrol(maze, robot, opts, difficulty, rng)
    if len(opts) > 1 and rng.random() < (difficulty.chase_noise if robot.kind == "chase" else difficulty.chase_noise * 1.5):
        return rng.choice(opts)[0]                 # a moment of confusion: never perfect pursuit
    if scattering:
        target = scatter_corner(maze, robot.kind)
    elif robot.kind == "chase":
        target = cat_tile
    else:                                          # ambush
        target = scatter_corner(maze, "ambush") if path_distance(maze, robot.tile, cat_tile) < cfg.AMBUSH_GIVE_UP \
            else ambush_target(maze, cat)
    return best_option(maze, opts, target)[0]


def _patrol(maze, robot, opts, difficulty, rng):
    """Walk the loop of corner waypoints; at an intersection sometimes turn off at random instead."""
    waypoints = robot.route
    if robot.tile == waypoints[robot.waypoint]:
        robot.waypoint = (robot.waypoint + 1) % len(waypoints)
    if len(opts) > 2 and rng.random() < difficulty.patrol_turn:
        return rng.choice(opts)[0]
    return best_option(maze, opts, waypoints[robot.waypoint])[0]


__all__ = ["choose", "options_for", "ambush_target", "scatter_corner", "DIRS"]
