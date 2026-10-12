"""Helpers for tests that drive the hub: teleport between rooms without the
wipe, as if the player had already walked through the door."""


def goto_room(game, room_id):
    """Make `room_id` the active room and return its scene. The player
    arrives at the room's default spawn; the room it left is closed exactly
    as a real doorway would close it."""
    room = game.hub.room(room_id)
    if game.scenes.current is not room:
        game.scenes.replace(room, fade=False)
    return room


def with_placeholder_minigame(cls, game_id="puzzle_drop"):
    """Class decorator for tests of the hub's generic play flow (tokens, coupons, rewards, spectating, saves).

    Those tests were written when the Puzzle Drop machine had no minigame yet, which made it a cheap stand-in: it loads
    instantly and pays the flat placeholder reward. That machine now runs NEON CAT MAZE, so for these tests only, the
    registry maps it back to the placeholder scene. (The real game is covered by test_cat_maze.py.)"""
    from unittest.mock import patch

    import scenes
    original = cls.setUp

    def setUp(self):
        patcher = patch.dict(scenes.MINIGAME_SCENES)
        patcher.start()
        self.addCleanup(patcher.stop)
        scenes.MINIGAME_SCENES.pop(game_id, None)
        original(self)

    cls.setUp = setUp
    return cls
