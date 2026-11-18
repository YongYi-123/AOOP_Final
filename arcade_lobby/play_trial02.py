"""Open TRIAL 02 - THE UNBEATEN RECORD directly, for testing the Tournament Hall.

    python3 play_trial02.py              # straight into the hall, with a throw-away profile
    python3 play_trial02.py --fresh      # same, but the opening plays
    python3 play_trial02.py --round 2    # rounds before 2 won; the puzzle before round 2 (THE BROKEN BRACKET) is waiting
    python3 play_trial02.py --round 3    # rounds before 3 won; THE CHAMPION'S TROPHY is waiting
    python3 play_trial02.py --round 3 --solved   # same, with that round's puzzle already solved: straight to the fight
    python3 play_trial02.py --ending     # all three rounds won: talk to the host to start the ceremony (the ending)

It skips the vending machine and the Legacy Terminal. The profile lives only in memory: nothing is read from or written
to your saves. Finishing the night records the trial for that throw-away profile only. ESC > LEAVE (or closing the
window) ends the program.
"""
import sys

import quests as Q
import unbeaten_record as T
from game import Game
from local_session import LocalSession
from player_profile import PlayerProfile
from unbeaten_scene import TournamentHallScene


def main(args):
    profile = PlayerProfile(profile_id="trial-test", display_name="TESTER")
    profile.set_story({"opening_done": True, "completed": ["grand_tour", "meet_the_locals", "arcade_explorer", "earn_some_rewards"],
                       "flags": {"vending_secret": True}})
    game = Game(session=LocalSession(profile))
    m = game.hub.story.manager
    m.handle("vending_secret")
    m.handle("secret_item_found", Q.SECRET_ITEM_RETRO_RACER)
    m.handle("secret_trial_done", "trial_01")
    m.handle("secret_item_found", Q.SECRET_ITEM_CLAW)
    if "--fresh" not in args:                       # (the hall's own opening is only skipped when its flag is set)
        m.handle(T.INTRO_FLAG)
    solved = "--solved" in args
    if "--round" in args:
        n = max(1, min(3, int(args[args.index("--round") + 1])))
        data = {"registered": True, "rounds": n - 1, "bracket": n > 2 or (n == 2 and solved),
                "trophies": n == 3 and solved, "key": n == 3 and solved}
        m.save_trial_progress(T.TRIAL_ID, data)
    elif "--ending" in args:
        m.save_trial_progress(T.TRIAL_ID, {"registered": True, "rounds": 3, "bracket": True, "trophies": True, "key": True})
    game.scenes.push(TournamentHallScene(game, game.session.primary), fade=False)
    game.run()


if __name__ == "__main__":
    main(sys.argv[1:])
