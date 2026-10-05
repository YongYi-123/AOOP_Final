"""Cozy Corner Arcade - a small top-down arcade room prototype.

Run with:  python main.py [--style lofi|neon]
"""
import argparse

from game import Game
from settings import BACKGROUND_STYLE, BACKGROUND_STYLES


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--style", choices=BACKGROUND_STYLES, default=BACKGROUND_STYLE,
                        help="room background style (default: %(default)s)")
    Game(style=parser.parse_args().style).run()
