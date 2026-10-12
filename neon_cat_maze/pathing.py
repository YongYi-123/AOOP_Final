"""Maze-aware path finding for the robots: breadth-first distance fields, cached per (maze, target)."""
from collections import deque

_FIELDS = {}


def distance_field(maze, target):
    """{tile: steps from `target`} over every floor tile (walls are never crossed)."""
    key = (maze.name, target)
    field = _FIELDS.get(key)
    if field is None:
        field, queue = {target: 0}, deque([target])
        while queue:
            tile = queue.popleft()
            for _, nxt in maze.neighbours(tile):
                if nxt not in field:
                    field[nxt] = field[tile] + 1
                    queue.append(nxt)
        _FIELDS[key] = field
    return field


def path_distance(maze, a, b):
    return distance_field(maze, b).get(a, 10 ** 6)


def best_option(maze, options, target):
    """The (direction, tile) of `options` closest to `target`; ties go to the earliest in the fixed direction order."""
    field = distance_field(maze, target)
    return min(options, key=lambda o: field.get(o[1], 10 ** 6))


def farthest_option(maze, options, threat):
    """The option leading furthest from `threat`; ties go to the earliest in the fixed direction order."""
    field = distance_field(maze, threat)
    return max(options, key=lambda o: field.get(o[1], -1))


def shortest_path(maze, a, b):
    """The tiles from `a` to `b` inclusive (empty if unreachable)."""
    field = distance_field(maze, b)
    if a not in field:
        return []
    path = [a]
    while path[-1] != b:
        path.append(min((t for _, t in maze.neighbours(path[-1])), key=lambda t: field.get(t, 10 ** 6)))
    return path
