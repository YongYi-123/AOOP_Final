"""CHAT WITH MOCHI: her talk about the old arcade and its Retro Racer secret, opened from her shop with the bag key (I).

Nothing here is a second unlock system. It only READS the shared story (quests.QuestManager.mochi_story_stage):

    locked    the vending machine's real Secret Interface has not opened      no chat entry exists at all (the shop looks and
                                                                               behaves exactly as it always did)
    "new"     unlocked, the first story not heard yet                         "Any stories about the old arcade?"
    "heard"   the first story was told, Secret Item 01 not found yet           + "Tell me more about Retro Racer." (a hint to STOP)
    "found"   Secret Item 01 (Reverse Gear) is in hand                        + "About that secret race..." (the hint is gone)
    Chapter 02, once all three of its clues are found                        + "Did you find something unusual?": she shows
                                                                               the old maintenance record (maintenance_note.py),
                                                                               which points to the claw machine's prize lock

The first story is recorded ONCE, in the shared story (a flag saved in every profile of the session), when it is finished;
it can be read again as often as you like. The conversations are plain StoryDialogue boxes; Miao Meow only joins in when she
is already standing in the Prize Plaza (she is never moved here). Mochi's shop is untouched.
"""
import pygame

import forgotten_games as fg

from menu_kit import FRAME, ROW_H, MenuScene, fit_text
from miao_meow import PLAZA
from quests import MOCHI_ARCADE_STORY
from settings import Col
from story_dialogue import Line, StoryDialogue
from ui import draw_text

MIAO, MOCHI, YOU = "MIAO MEOW", "MOCHI", "PLAYER"

STORIES = "Any stories about the old arcade?"
HINT = "Tell me more about Retro Racer."
RACE = "About that secret race..."

OLD_ARCADE = (
    Line(MOCHI, "You know, back when this arcade was packed, Retro Racer was everyone's favorite.", "gentle"),
    Line(YOU, "Really? Racing games were that popular?"),
    Line(MOCHI, "Oh, absolutely. People would line up just to get a turn.", "normal"),
    Line(MOCHI, "Though the funny thing is... the best players never seemed to follow the rules.", "gentle"),
    Line(YOU, "What do you mean?"),
    Line(MOCHI, "Heh. Let's just say some of them spent more time doing everything except racing.", "happy"),
)
OLD_ARCADE_MIAO = (                     # only when Miao Meow is already in the room
    Line(MIAO, "I tried that once! I finished last!", "happy"),
    Line(MOCHI, "You finished last when you were actually racing, too.", "gentle"),
    Line(MIAO, "MOCHI!!", "surprised"),
)
HINT_LINES = (
    Line(MOCHI, "Funny thing about racing...", "gentle"),
    Line(MOCHI, "Everyone thinks the only way to win is to go faster.", "normal"),
    Line(MOCHI, "But the weirdest players? They knew when to stop.", "happy"),
)
RACE_LINES = (
    Line(MOCHI, "So you actually found that strange road, huh?", "surprised"),
    Line(MOCHI, "Heh. Guess you're one of those players who don't follow the rules either.", "happy"),
)


def chat_options(stage, unusual=False):
    """The menu for a story stage: [(label, key)]. Locked (None) has none. `unusual`: Chapter 02's three clues are
    all found, so Mochi has the maintenance record to show."""
    if stage is None:
        return []
    options = [(STORIES, "stories")]
    options.append((RACE, "race") if stage == "found" else (HINT, "hint") if stage == "heard" else None)
    if unusual:
        options.append((fg.UNUSUAL, "unusual"))
    return [o for o in options if o]


def has_record(manager):
    """Does Mochi have the maintenance record to show? Only in Chapter 02, after all three clues."""
    return manager.chapter_two_open and manager.all_clues_found


def chat_lines(key, miao_here):
    if key == "stories":
        return OLD_ARCADE + (OLD_ARCADE_MIAO if miao_here else ())
    return {"hint": HINT_LINES, "race": RACE_LINES, "unusual": fg.RECORD_INTRO}[key]


def chat_available(game):
    """Is there anything to say yet? (The shop only offers the chat key when so.)"""
    manager = game.hub.story.manager
    return bool(chat_options(manager.mochi_story_stage, has_record(manager)))


class MochiChatScene(MenuScene):
    title = "CHAT WITH MOCHI"
    hints = ("UP/DOWN CHOOSE", "E TALK", "ESC BACK")

    def __init__(self, game, owner, keeper=None):
        super().__init__(game, owner)
        self.story = game.hub.story
        self.keeper = keeper
        self.index = 0
        self.talk = None                # the StoryDialogue being read
        self.talking = None             # its option key
        self.heard = []                 # the options read in this visit (tests, debugging)

    # ------------------------------------------------------------ what is on offer (always read from the story)
    @property
    def options(self):
        manager = self.story.manager
        return chat_options(manager.mochi_story_stage, has_record(manager))

    def miao_here(self):
        return self.story.brain.is_in(PLAZA)

    # ------------------------------------------------------------ input
    def handle_event(self, event):
        if self.talk is not None:
            if event.type == pygame.KEYDOWN:
                self.talk.handle_event(event)
            return
        super().handle_event(event)

    def on_action(self, action):
        options = self.options
        if action == "back":
            self.play("cancel")
            self.close()
        elif action in ("up", "down") and options:
            self.index = (self.index + (-1 if action == "up" else 1)) % len(options)
        elif action == "interact" and options:
            self.start(options[min(self.index, len(options) - 1)][1])

    def start(self, key):
        self.play("confirm")
        context = {"players": list(self.game.hub.avatars)}
        self.talking = key
        self.talk = StoryDialogue(chat_lines(key, self.miao_here()), context, on_done=self._finished,
                                  play_sound=self.play)

    def _finished(self):
        key, self.talk, self.talking = self.talking, None, None
        self.heard.append(key)
        if key == "stories":
            self.story.manager.handle(MOCHI_ARCADE_STORY)       # recorded once, whatever the number of re-reads
        elif key == "unusual" and has_record(self.story.manager):
            from maintenance_note import MaintenanceNoteScene
            self.game.scenes.push(MaintenanceNoteScene(self.game, self.owner))
        self.index = min(self.index, max(0, len(self.options) - 1))

    # ------------------------------------------------------------ frame
    def update(self, dt):
        super().update(dt)
        if self.keeper is not None:
            self.keeper.update(dt)
        if self.talk is not None:
            self.talk.update(dt)

    def draw_body(self, surf):
        self.draw_frame(surf)
        draw_text(surf, "ASK MOCHI ABOUT...", (14, 52), Col.TEXT_MUTED)
        for i, (label, _key) in enumerate(self.options):
            rect = pygame.Rect(14, 66 + i * (ROW_H + 2), FRAME.w - 22, ROW_H - 2)
            self.draw_row_bg(surf, rect, i == self.index)
            self.hit(rect, lambda i=i: (setattr(self, "index", i), self.on_action("interact")))
            draw_text(surf, fit_text(label, rect.w - 12), (rect.x + 6, rect.y + 5),
                      Col.TEXT if i == self.index else Col.TEXT_MUTED)
        self.draw_footer(surf)
        if self.talk is not None:
            self.talk.draw(surf)
