"""Neon Corner Arcade - a small top-down arcade hub of three connected rooms
(ARCADE FLOOR <-> HOME <-> PRIZE PLAZA) for one or two local players, each with
their own saved profile.

Run with:  python main.py [--style neon_lofi|lofi|neon] [--debug]
"""
import argparse

from arcade_style import DEFAULT_STYLE, STYLE_NAMES
from game import Game
from profile_manager import ProfileManager
from settings import DEBUG, SAVE_FILE, SAVES_DIR


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--style", choices=STYLE_NAMES, default=DEFAULT_STYLE,
                        help="visual style (default: %(default)s)")
    parser.add_argument("--debug", action="store_true", default=DEBUG,
                        help="debug helpers in the arcade: F5 +10 tokens, F6 next day, F7 new daily tasks, F8/F9 add test items")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    # The old single save (save_data.json) is carried into the profile system once.
    profiles = ProfileManager(SAVES_DIR, legacy_path=SAVE_FILE)
    Game(style=args.style, debug=args.debug, profiles=profiles).run()
