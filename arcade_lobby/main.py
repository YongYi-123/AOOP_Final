"""Cozy Corner Arcade - a small top-down arcade room prototype.

Run with:  python main.py [--style lofi|neon] [--debug]
"""
import argparse

from game import Game
from settings import BACKGROUND_STYLE, BACKGROUND_STYLES, DEBUG


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--style", choices=BACKGROUND_STYLES, default=BACKGROUND_STYLE,
                        help="room background style (default: %(default)s)")
    parser.add_argument("--debug", action="store_true", default=DEBUG,
                        help="debug helpers: F5 in the arcade adds 10 coins")
    args = parser.parse_args()
    Game(style=args.style, debug=args.debug).run()
