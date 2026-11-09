"""On-screen control text; embedded matches replace it with the lobby's own key names."""


def hint_lines(left, right, jump, smash):
    """The one control line, from the key labels of the player's bindings."""
    return (f"{left} / {right} MOVE   {jump} JUMP   {smash} SMASH (IN AIR)",)


def default_hints():
    """Matches VolleyKeyboard's standalone bindings."""
    return hint_lines("A", "D", "W", "SPACE")
