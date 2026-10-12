"""A scripted player, used to prove the game is fair and finishable: it eats the nearest fish, keeps away from robots
that are close and hunts frightened ones while the catnip lasts."""
from neon_cat_maze.model import neg
from neon_cat_maze.pathing import distance_field, path_distance

DANGER = 5            # path steps within which a hostile robot makes the pilot run


def steer_for(run):
    """The direction to ask for now (called every frame; it only matters at tile centres)."""
    maze, cat = run.maze, run.cat
    here = cat.nearest_tile()
    hostile = [r for r in run.robots if r.hostile and not r.fright]
    scared = [r for r in run.robots if r.hostile and r.fright]
    options = [(d, t) for d, t in maze.neighbours(here) if t not in maze.restricted]
    if not options:
        return None
    threat = min(hostile, key=lambda r: path_distance(maze, r.nearest_tile(), here), default=None)
    if threat and path_distance(maze, threat.nearest_tile(), here) <= DANGER:
        field = distance_field(maze, threat.nearest_tile())
        best = max(options, key=lambda o: (field.get(o[1], 0), o[0] != neg(cat.dir)))
        return best[0]
    if scared and run.catnip_left > 2.0:
        target = min(scared, key=lambda r: path_distance(maze, r.nearest_tile(), here)).nearest_tile()
        field = distance_field(maze, target)
        return min(options, key=lambda o: field.get(o[1], 10 ** 6))[0]
    targets = set(run.fish) | ({run.golden[0]} if run.golden else set())
    if not targets:
        return None
    field = {}
    from collections import deque
    queue = deque([here])
    field[here] = 0
    goal = None
    while queue:
        tile = queue.popleft()
        if tile in targets and tile != here:
            goal = tile
            break
        for _, nxt in maze.neighbours(tile):
            if nxt not in field and nxt not in maze.restricted:
                field[nxt] = field[tile] + 1
                queue.append(nxt)
    if goal is None:
        return None
    back = distance_field(maze, goal)
    return min(options, key=lambda o: back.get(o[1], 10 ** 6))[0]
