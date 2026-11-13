"""Play the main quest by hand from any point, on a THROW-AWAY save (your real saves/ folder is never touched).

    python3 play_story.py <stage> [--keep]

Stages (each one starts a new test save at that point of the story):
    new       a brand-new player: the opening cutscene and the tutorial quests
    vending   tutorial done: find the vending machine's secret screen
    ch1       Chapter 01 open: ask Mochi, find the Reverse Road in Retro Racer (Secret Item 01)
    trial01   Secret Item 01 owned: open the Legacy Terminal and play Trial 01
    ch2       Chapter 02 open: hint cards in the capsule machines, the three symbols in the minigames
    routes    Chapter 02 open AND every route already earned: the three secrets are waiting, go and find them
    clues     all three Chapter 02 symbols found: Miao's talk in the hub, then Mochi's maintenance lock
    solved    the lock opened: win the Golden Cat in NEON CLAW (Secret Item 02)

--keep   continue the last test save instead of starting the stage again (the stage name is then ignored).
Debug keys are on: F5 +10 tokens, F6 next day, F7 new daily tasks, F8/F9 test items.
The test save lives in your system temp folder (printed at start); close the window to stop.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

from game import Game  # noqa: E402
from player_profile import PlayerProfile, ProfileStore  # noqa: E402
import quests as Q  # noqa: E402

STAGES = ("new", "vending", "ch1", "trial01", "ch2", "routes", "clues", "solved")
TUTORIAL = ("grand_tour", "meet_the_locals", "arcade_explorer", "earn_some_rewards")
SAVE = os.path.join(tempfile.gettempdir(), "neon_arcade_story_test.json")


def build(stage):
    """Write a new test save that stands at `stage`."""
    for path in (SAVE, SAVE + ".tmp"):
        if os.path.exists(path):
            os.remove(path)
    if stage == "new":
        return
    profile = PlayerProfile(tokens=300, tickets=300)
    profile.set_story({"opening_done": True, "completed": list(TUTORIAL),
                       "flags": {name: True for name in Q.TOUR_EVENTS}})
    ProfileStore(SAVE).save(profile)
    if stage == "vending":
        return
    game = Game(save_path=SAVE)                      # the later steps go through the real story rules
    m = game.hub.story.manager
    m.handle("vending_secret")
    if stage != "ch1":
        m.handle("secret_item_found", Q.SECRET_ITEM_RETRO_RACER)
        m.handle(Q.MIAO_REVERSE_ROAD)
    if stage not in ("ch1", "trial01"):
        m.handle("secret_trial_done", "trial_01")
    if stage == "routes":
        for clue in Q.CH2_CLUES:
            m.handle(Q.CLUE_ROUTE_EVENT, clue)
    if stage in ("clues", "solved"):
        for clue in Q.CH2_CLUES:
            m.handle(Q.CLUE_FOUND_EVENT, clue)
    if stage == "solved":
        m.handle(Q.MIAO_CH2_HINT)
        m.handle(Q.CH2_RIDDLE_SOLVED)
    game.store.save(game.session.primary.profile)


def main(args):
    if "-h" in args or "--help" in args:
        print(__doc__)
        return
    keep = "--keep" in args and os.path.exists(SAVE)
    stage = next((a for a in args if a in STAGES), None)
    if not keep and stage is None:
        print(__doc__)
        print("pick a stage:", ", ".join(STAGES))
        return
    if not keep:
        build(stage)
    game = Game(save_path=SAVE, debug=True, opening=(stage == "new" and not keep))
    m = game.hub.story.manager
    print(f"{'continuing' if keep else 'stage ' + stage}: chapter {m.current_chapter}, "
          f"quest {m.active.id if m.active else '-'}, symbols {m.clues_found}/3, lock open {m.riddle_solved}")
    print("test save:", SAVE)
    game.run()


if __name__ == "__main__":
    main(sys.argv[1:])
