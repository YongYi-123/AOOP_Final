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
