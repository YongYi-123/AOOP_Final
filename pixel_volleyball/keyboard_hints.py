"""On-screen control text; embedded matches replace it with the lobby's own key names."""


def hint_lines(players):
    """`players` is [(name, left, right, jump, smash)] key labels, one per local player."""
    if len(players) == 1:
        _, left, right, jump, smash = players[0]
        return (f"{left} / {right} MOVE   {jump} JUMP   {smash} SMASH (IN AIR)",)
    return tuple(f"{name}  {left} / {right} MOVE  {jump} JUMP  {smash} SMASH"
                 for name, left, right, jump, smash in players)


def default_hints(local_players):
    """Matches VolleyKeyboard's standalone bindings."""
    if local_players == 1:
        return hint_lines([("", "A", "D", "W", "SPACE")])
    return hint_lines([("P1", "A", "D", "W", "SPACE"),
                       ("P2", "LEFT", "RIGHT", "UP", "R-SHIFT")])
