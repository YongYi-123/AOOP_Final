"""What the NEON VEND-O-MATIC novelty items do when used.

Using one removes a single copy from the player's bag and returns a UseResult describing the little
show to put on (an effect name, a sound, a speech-bubble line). That is ALL it does: no score, token,
ticket, speed or combat is touched, so these are safe toys. Rendering the show is novelty_fx.py's job;
this module only decides what happens, which keeps it testable without a window.
"""
import random
from dataclasses import dataclass

# one-line harmless jokes for the MYSTERY CAN
MYSTERY_MESSAGES = (
    "IT WAS EMPTY. IT WAS ALSO FULL.",
    "THE CAN SAYS: WELL DONE, I GUESS.",
    "YOU FEEL SLIGHTLY MORE CAN-SHAPED.",
    "INSIDE: A TINY SIGN. IT SAYS 'HI'.",
    "TASTES LIKE THE COLOR PURPLE.",
    "YOU HEAR DISTANT ARCADE WHALES.",
    "CONGRATULATIONS! YOU OPENED A CAN.",
    "NOTHING HAPPENED. BUT SO CONFIDENTLY.",
)

# item id -> (effect kind, sound, bubble text; None = pick from MYSTERY_MESSAGES)
NOVELTY_EFFECTS = {
    "suspicious_soda": ("burp", "burp", "BURRRP!"),
    "invisible_sandwich": ("munch", "munch", "NOM NOM NOM"),
    "pocket_rainbow": ("rainbow", "rainbow", "TA-DA!"),
    "rubber_duck": ("squeak", "squeak", "SQUEAK!"),
    "questionable_battery": ("flicker", "zap", "BZZZT?"),
    "mystery_can": ("mystery", "mystery", None),
}


@dataclass(frozen=True)
class UseResult:
    success: bool
    code: str               # ok / not_usable / none_owned
    item_id: str = ""
    effect: str = ""        # burp / munch / rainbow / squeak / flicker / mystery
    sound: str = ""
    message: str = ""


def is_usable(item_id):
    return item_id in NOVELTY_EFFECTS


def use_item(profile, item_id, rng=random):
    """Use one novelty item from `profile`'s bag. Nothing changes if it is not usable or not owned."""
    spec = NOVELTY_EFFECTS.get(item_id)
    if spec is None:
        return UseResult(False, "not_usable", item_id, message="CAN'T USE THAT")
    if not profile.consume_item(item_id):
        return UseResult(False, "none_owned", item_id, message="NONE LEFT")
    effect, sound, text = spec
    return UseResult(True, "ok", item_id, effect, sound, text or rng.choice(MYSTERY_MESSAGES))
