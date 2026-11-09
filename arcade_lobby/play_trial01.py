"""Open TRIAL 01 - THE GOLDEN AGE directly, for testing the room.

    python3 play_trial01.py            # straight into the room, with a throw-away profile
    python3 play_trial01.py --fresh    # same, but the opening cutscene plays

It skips the vending machine and the Legacy Terminal. The profile lives only in memory: nothing is read from or written
to your saves. Finishing the room records the trial for that throw-away profile only. ESC > LEAVE (or closing the
window) ends the program.
"""
import sys

from game import Game
from golden_age_scene import GoldenAgeScene
from local_session import LocalSession
from player_profile import PlayerProfile


def main(fresh=False):
    profile = PlayerProfile(profile_id="trial-test", display_name="TESTER")
    profile.set_story({"opening_done": True, "completed": ["get_your_bearings", "arcade_explorer", "earn_some_rewards"],
                       "flags": {"vending_secret": True}})
    game = Game(session=LocalSession(profile))
    if not fresh:                                       # (the room's own opening is only skipped when its flag is set)
        game.hub.story.manager.handle("trial01_intro")
    game.scenes.push(GoldenAgeScene(game, game.session.primary), fade=False)
    game.run()


if __name__ == "__main__":
    main("--fresh" in sys.argv[1:])
