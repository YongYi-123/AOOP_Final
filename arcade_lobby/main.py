"""Neon Corner Arcade - a small top-down arcade hub of three connected rooms
(ARCADE FLOOR <-> HOME <-> PRIZE PLAZA) for one or two local players, each with
their own saved profile.

Run with:  python main.py [--style neon_lofi|lofi|neon] [--debug]
"""
import argparse
import sys
import time

from arcade_style import DEFAULT_STYLE, STYLE_NAMES
from game import Game
from profile_manager import ProfileManager
from save_lock import SaveLock
from settings import DEBUG, SAVE_FILE, SAVES_DIR


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--style", choices=STYLE_NAMES, default=DEFAULT_STYLE,
                        help="visual style (default: %(default)s)")
    parser.add_argument("--debug", action="store_true", default=DEBUG,
                        help="debug helpers in the arcade: F5 +10 tokens, F6 next day, F7 new daily tasks, F8/F9 add test items")
    return parser


def tell_already_running(holder):
    """A second copy would overwrite the first copy's saves: say so and stop. The
    message goes to the console and, for people who launched it by double-click,
    into a small window."""
    message = ["ARCADE IS ALREADY RUNNING", "CLOSE THE OTHER WINDOW FIRST", holder.upper()] if holder else \
              ["ARCADE IS ALREADY RUNNING", "CLOSE THE OTHER WINDOW FIRST"]
    print("Neon Corner Arcade is already running (it holds the save folder). "
          "Close the other window first." + (f" [{holder}]" if holder else ""), file=sys.stderr)
    import pygame
    from font import get_font
    pygame.init()
    screen = pygame.display.set_mode((480, 160))
    pygame.display.set_caption("Neon Corner Arcade")
    screen.fill((18, 10, 40))
    font = get_font()
    for i, line in enumerate(message):
        img = font.render_glow(line, (255, 214, 90) if i == 0 else (236, 232, 255), (90, 60, 20), 2 if i < 2 else 1)
        screen.blit(img, img.get_rect(midtop=(240, 28 + i * 34)))
    pygame.display.flip()
    end = time.time() + 6
    while time.time() < end:
        if any(e.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN) for e in pygame.event.get()):
            break
        pygame.time.wait(50)
    pygame.quit()


if __name__ == "__main__":
    args = build_parser().parse_args()
    lock = SaveLock(SAVES_DIR)          # one running copy per save folder (see save_lock.py)
    if not lock.acquire():
        tell_already_running(lock.holder())
        sys.exit(1)
    try:
        # The old single save (save_data.json) is carried into the profile system once.
        profiles = ProfileManager(SAVES_DIR, legacy_path=SAVE_FILE)
        Game(style=args.style, debug=args.debug, profiles=profiles).run()
    finally:
        lock.release()
