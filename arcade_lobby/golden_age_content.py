"""Everything the player READS in TRIAL 01: the notebook, the books, the sticky notes, the homework, and what the room's
little objects say when you inspect them. All of it is English, written like an exhausted university student (NYCU wind,
professors, deadlines, instant noodles, 3 AM debugging), and none of it is marked as important: a clue is only a clue once
the player connects it.

The owner of the room stays anonymous (no name anywhere) and nothing here tells how the story ends.

Only characters the game's pixel font has are used: capitals (it upper-cases), digits and  ! " ' ( ) + , - . / : < > ? [ ] _ ~
(no semicolons, ampersands, percent signs, dashes or curly quotes).

Pages are dicts: {"title": ..., "text": ...}. Dialogue lines are (speaker, text, mood) tuples.
"""

# ------------------------------------------------------------------ the notebook (12 entries behind a plain cover)
JOURNAL_COVER = {
    "title": "UNTITLED NOTEBOOK",
    "text": "No name on the cover. Just a coffee ring and a sticker of a very tired cat.\n\n"
            "The first page says: If found, please return. If you read it, please do not judge my handwriting.",
}

JOURNAL_ENTRIES = (
    {"title": "OCT 17 - ANOTHER DEADLINE",
     "text": "The wind at NYCU almost launched me into another dimension today. I walked from the dorm to class and arrived "
             "with a new hairstyle and a lower will to live.\n\n"
             "Then my professor assigned another project. The last one is not even submitted yet. I am starting to think "
             "professors have a secret group chat about how to keep students awake.\n\n"
             "Anyway. Tonight I will tweak my little game. It is more fun than writing reports. Probably."},
    {"title": "OCT 19 - LUNCH.EXE HAS STOPPED",
     "text": "Lunch today tasted like a bug. Not a bug in the food. The food WAS a bug. Rice: fine. Vegetables: fine. "
             "Mystery sauce: segmentation fault.\n\n"
             "I ate it anyway because the line was 40 minutes long and my wallet is a cry for help.\n\n"
             "Note to self: instant noodles are not a food group, but they are a lifestyle."},
    {"title": "OCT 22 - ASSIGNMENT NUMBER WHO KNOWS",
     "text": "New assignment today. Write a program that sorts things. I told the professor I already sort my problems by "
             "deadline. He did not laugh.\n\n"
             "It is due Thursday at midnight. Midnight, as in the exact moment I will be asleep face-down on my keyboard.\n\n"
             "I have decided to start on Wednesday. Past me is a hero. Future me is going to be furious."},
    {"title": "OCT 25 - 3 AM",
     "text": "It is 3 AM. I opened my editor to fix one tiny thing. One. Tiny. Thing.\n\n"
             "Now the paddle is green, the bricks are pastel, and the ball makes a noise like a happy microwave. "
             "The tiny thing is still broken.\n\n"
             "Why do my best ideas only show up when I should be sleeping? My brain has terrible time management."},
    {"title": "OCT 28 - WIND REPORT",
     "text": "Wind report: terrible. Someone's umbrella flew past me like a bird that hates its owner. A bicycle fell over. "
             "Then another bicycle fell over because of the first one. Domino effect, NYCU edition.\n\n"
             "I held onto a tree for ten seconds just to feel safe.\n\n"
             "The tree held onto the ground. Respect."},
    {"title": "NOV 2 - THE CAT",
     "text": "A stray cat has decided my keyboard is a heated bed. Every time I write code it hops on and adds its own. "
             "Last night it committed forty lines of the letter J.\n\n"
             "I named it Mr. Compile because it breaks everything and I cannot stay mad at it. It sat on the Enter key "
             "and submitted my homework unfinished.\n\n"
             "I blame the cat. The cat blames nobody. That is why the cat is happier than me."},
    {"title": "NOV 5 - THE COLLISION BUG",
     "text": "The ball goes through the bricks. Sometimes. Only on Tuesdays, apparently.\n\n"
             "I stared at the collision code for two hours. Then I found it. I wrote less-than where I meant "
             "greater-than. Two hours. For one little arrow.\n\n"
             "I am not saying I am a genius. I am saying the arrow was very small."},
    {"title": "NOV 9 - PLAYTEST",
     "text": "Today I let a friend try my little game. They were TERRIBLE. Lost five times in three minutes. "
             "Missed the ball by a whole country.\n\n"
             "But they were laughing so hard they had to sit on the floor. And then I was laughing too.\n\n"
             "I do not know. Maybe you do not always have to win. Maybe a game can just make people happy."},
    {"title": "NOV 12 - A FAILED DESIGN",
     "text": "Terrible idea of the week: a game where you collect socks and every sock slightly changes gravity. "
             "I made a prototype. Nobody understood it, including me.\n\n"
             "My friend asked, why are there so many socks? I said, that is the point. They said, what is the point? "
             "I said, I will get back to you.\n\n"
             "The prototype is in the trash. The socks are in my heart."},
    {"title": "NOV 15 - I FORGOT",
     "text": "I forgot to submit the assignment. Not late. FORGOT. The portal closed and I just watched it close like a sad "
             "little door.\n\n"
             "The professor said, see me after class. I thought, this is it, this is how it ends.\n\n"
             "He gave me partial credit and a speech about time management. Sir, I know the speech. I have given the "
             "speech. To myself. At 3 AM."},
    {"title": "NOV 20 - LATE NIGHT THOUGHTS",
     "text": "Late night thoughts, which are always dangerous. I keep thinking about the friend who laughed on the floor.\n\n"
             "What if there was a place full of games where nobody had to be good? Where winning was optional and "
             "curiosity counted more than skill? Where the person who loses five times is just as welcome as the one "
             "with the high score?\n\n"
             "It sounds silly. It sounds nice, though. Maybe I will build something like that. Someday. After the homework."},
    {"title": "NOV 23 - COMPLAINTS DEPARTMENT",
     "text": "Complaint list. One: the wind. Two: the stairs to the third floor, which are somehow longer going up. "
             "Three: group projects where my group is me, a ghost, and a group chat nobody reads.\n\n"
             "Four: the vending machine ate my coin and gave me nothing. I stared at it for a full minute. "
             "I think it was judging me.\n\n"
             "Five: it is 4 AM. I am fine. Everything is fine. Goodnight, notebook."},
)
JOURNAL_PAGES = (JOURNAL_COVER,) + JOURNAL_ENTRIES          # 1 cover + 12 entries

# ------------------------------------------------------------------ the books on the shelf: key -> (spine title, spine colour, pages)
BOOKS = {
    "programming": ("INTRO TO PROGRAMMING, 3RD ED.", (184, 70, 56), (
        {"title": "CHAPTER 1: HELLO, WORLD",
         "text": "Hello, World is the first program everyone writes.\n\nMargin note in pen: this is a lie. The first program "
                 "everyone writes is a bug.\n\nAnother note: the author promises that programming is fun. The author has "
                 "clearly never had a deadline."},
        {"title": "CHAPTER 4: LOOPS",
         "text": "A loop repeats until a condition is met.\n\nMargin note: also known as my sleep schedule.\n\n"
                 "Underlined three times: ALWAYS CHECK YOUR EXIT CONDITION. Next to it, a tiny drawing of a person "
                 "stuck inside a box."},
        {"title": "CHAPTER 9: DEBUGGING",
         "text": "When your code does not work, explain it out loud to a rubber duck.\n\nMargin note: I explained it to a "
                 "cat. The cat did not help, but it was supportive."},
    )),
    "logic": ("DIGITAL LOGIC, VOL. 2", (62, 140, 138), (
        {"title": "NAND IS ALL YOU NEED",
         "text": "In theory you can build any circuit out of NAND gates alone. In practice you can also build a headache.\n\n"
                 "Margin note: why does the lab always have exactly one broken breadboard?"},
        {"title": "LAB 3: THE COUNTER",
         "text": "Lab 3 asks you to wire a counter. Do not touch the wires while the power is on.\n\n"
                 "Margin note: lesson learned. The wires get warm. Do not ask."},
    )),
    "pixels": ("A SHORT HISTORY OF PIXELS", (222, 170, 60), (
        {"title": "THE FIRST ARCADES",
         "text": "Arcades began as rooms full of glowing cabinets and the sound of coins. Kids saved lunch money for one "
                 "more try.\n\nNobody remembers the high scores. Everybody remembers the sounds."},
        {"title": "BREAK THE WALL",
         "text": "One famous early game gave you a paddle, a ball and a wall of bricks. That was the whole game. People "
                 "played it for hours.\n\nMargin note: simple is not the same as easy. Also simple is not the same as boring."},
        {"title": "THE END OF EVERY LEVEL",
         "text": "Designers say a good game respects the player's time.\n\nMargin note, underlined twice: and the player's "
                 "feelings."},
    )),
    "fun": ("WHAT MAKES A GAME FUN?", (120, 76, 110), (
        {"title": "AN ESSAY",
         "text": "Some people say fun comes from winning. Others say it comes from learning. The best answer I found says "
                 "fun comes from being curious about what happens next."},
        {"title": "A REVIEW",
         "text": "Reviewer's verdict on a puzzle game: 4 out of 5 stars. One star lost because the tutorial was longer than "
                 "the game.\n\nSomeone circled that and wrote: RELATABLE."},
    )),
    "handbook": ("NYCU SURVIVAL HANDBOOK", (70, 90, 150), (
        {"title": "CHAPTER 1: THE WIND",
         "text": "Rule one: the wind here is not weather. It is a personality. Dress in layers, hold your umbrella like it "
                 "owes you money, and never trust a flat hat."},
        {"title": "CHAPTER 2: FOOD",
         "text": "The cafeteria offers many things. Some of them are food.\n\nRule one: when in doubt, instant noodles. "
                 "Rule two: when in despair, more instant noodles."},
        {"title": "CHAPTER 3: DEADLINES",
         "text": "A deadline is only a suggestion until it is tomorrow. Then it is a monster.\n\nSleep is optional. "
                 "Pretending sleep is optional is mandatory."},
    )),
    "cats": ("CATS AND YOU", (200, 120, 60), (
        {"title": "KEYBOARDS",
         "text": "Cats sit on keyboards because keyboards are warm and because you are busy. Both reasons are good.\n\n"
                 "Do not move the cat. Move your schedule."},
        {"title": "SIGNS OF AFFECTION",
         "text": "Signs your cat likes you: it ignores you while you are free, and follows you the moment you sit down "
                 "to work."},
    )),
    "calculus": ("MAKE-UP EXAM SURVIVAL GUIDE", (126, 150, 98), (
        {"title": "CALCULUS",
         "text": "The cover says Calculus. Inside, every page is a doodle of a very sad potato."},
        {"title": "THE LAST PAGE",
         "text": "The last page says: YOU CAN DO THIS.\n\nUnderneath, in a different pen: no you cannot.\n\n"
                 "Underneath that, in a third pen: yes you can."},
    )),
}
BOOK_ORDER = ("programming", "logic", "pixels", "fun", "handbook", "cats", "calculus")
NOTEBOOK_KEY = "notebook"                    # the eighth book: only on the shelf once the cabinet's note has been read
NOTEBOOK_TITLE = "UNTITLED NOTEBOOK"
NOTEBOOK_COLOUR = (96, 60, 40)

# ------------------------------------------------------------------ loose paper
STICKY_NOTES = (
    {"title": "STICKY NOTE", "text": "DO NOT SIT ON THE CHAIR IF THERE IS A CAT ON IT. THE CAT HAS SENIORITY."},
    {"title": "STICKY NOTE", "text": "Wind warning: bring a jacket. Also an umbrella. Also hope."},
    {"title": "STICKY NOTE", "text": "Assignment 4 due FRIDAY. Not next Friday. THIS Friday. Check the portal. Then check it again."},
    {"title": "STICKY NOTE", "text": "Whatever is in the top drawer: do NOT lose it again."},
    {"title": "STICKY NOTE", "text": "Buy noodles."},
)
HOMEWORK_PAGES = (
    {"title": "ASSIGNMENT 4",
     "text": "Question 3: Sort the list.\n\nMy answer: it sorts itself if you believe in it.\n\n"
             "Score: 2 out of 10. In red pen: see me."},
    {"title": "SCRATCH CODE",
     "text": "while ball is alive:\n    move ball\n    if ball touches brick:\n        remove brick\n"
             "        flip direction (which one??)\n\nBUG: ball gets stuck inside a brick. Why. WHY."},
    {"title": "DOODLES",
     "text": "A margin full of cats, tiny bricks, and a cartoon of a professor saying DEADLINE EXTENDED while the student "
             "faints from joy.\n\nWishful thinking."},
)
TEXTBOOK_PAGES = (
    {"title": "ALGORITHMS: A GENTLE INTRODUCTION",
     "text": "The cover says gentle. Someone crossed out gentle and wrote: NOT."},
    {"title": "CHAPTER 2: SORTING",
     "text": "Bubble sort compares neighbors and swaps them if they are in the wrong order.\n\n"
             "Margin note: just like my study group."},
    {"title": "CHAPTER 5: RECURSION",
     "text": "To understand recursion, see recursion.\n\nMargin note: I see it. I do not understand it."},
)
TRASH_PAGES = (
    {"title": "IDEA 14: SOCK SIMULATOR", "text": "Collect socks. Lose socks. Feel something. Verdict: nobody asked for this."},
    {"title": "IDEA 15: YOU ARE A NOODLE",
     "text": "Cook yourself in exactly three minutes. Win condition: do not overcook. Lose condition: you are soup."},
    {"title": "IDEA 16: THE HARDEST GAME",
     "text": "Impossible on purpose. Crossed out.\n\nReplaced with: nobody wants this. Crossed out.\n\n"
             "Replaced with: what if even the loser walked away smiling?"},
)

# ------------------------------------------------------------------ small objects: key -> list of variants (each a list of lines).
# The first inspection says the first variant, the next ones the next, then it starts again.
# "reader": pages opened after the words (only the first time; later the pages open straight away)
LIFE = {
    "window": {"lines": [
        [("PLAYER", "Why is it so windy outside?", "normal"), ("PLAYER", "Wait... this almost feels like NYCU.", "normal")],
        [("MIAO MEOW", "Listen to it whistle.", "normal"), ("PLAYER", "It's trying to get in. Politely. For now.", "normal")],
        [("PLAYER", "Somewhere out there, an umbrella is having the worst night of its life.", "normal")]]},
    "noodle_cup": {"lines": [
        [("PLAYER", "Instant noodles. The universal language of university students.", "normal")],
        [("MIAO MEOW", "It still smells salty.", "normal"), ("PLAYER", "Do not eat it. It is older than your last assignment.", "normal")],
        [("PLAYER", "The cup says: just add hot water. Somebody added a lot of regret instead.", "normal")]]},
    "coffee_mug": {"lines": [
        [("PLAYER", "There's still coffee inside.", "normal"), ("PLAYER", "...I'm not drinking that.", "normal")],
        [("MIAO MEOW", "Is it still coffee, or is it a science project?", "surprised"), ("PLAYER", "Yes.", "normal")]]},
    "alarm_clock": {"lines": [
        [("PLAYER", "3:47 AM.", "normal"), ("PLAYER", "Somebody really needed a better sleep schedule.", "normal")],
        [("PLAYER", "The alarm is set for 7:00. Very optimistic.", "normal")],
        [("MIAO MEOW", "It stopped ticking. Even time gave up.", "gentle")]]},
    "trash_bin": {"lines": [
        [("PLAYER", "Rejected game ideas. A lot of them.", "normal"), ("PLAYER", "Honestly, relatable.", "normal")]],
        "reader": "trash"},
    "cookie_jar": {"lines": [
        [("PLAYER", "Cookies!", "happy"), ("PLAYER", "...It's empty.", "normal"),
         ("MIAO MEOW", "That's the saddest thing I've seen all day.", "gentle")],
        [("PLAYER", "There are crumbs. Evidence of a crime.", "normal")],
        [("MIAO MEOW", "I would like to report a cookie shortage.", "surprised")]]},
    "homework": {"lines": [
        [("PLAYER", "Homework. Everywhere. It's like a paper snowstorm.", "normal")]], "reader": "homework"},
    "textbook": {"lines": [
        [("PLAYER", "A thick textbook. Somebody wrote all over the margins.", "normal")]], "reader": "textbook"},
    "cartridges": {"lines": [
        [("PLAYER", "Old game cartridges. Half of them have no labels.", "normal"),
         ("MIAO MEOW", "Do you think any of them still work?", "normal"),
         ("PLAYER", "Only one way to find out. Also, no console.", "normal")],
        [("PLAYER", "One label says BEST GAME EVER. Underneath: not really. Underneath that: well, kind of.", "normal")]]},
    "poster": {"lines": [
        [("PLAYER", "A pixel hero staring at the sunset.", "normal"),
         ("PLAYER", "The poster says INSERT COIN TO CONTINUE. Mood.", "normal")],
        [("MIAO MEOW", "He looks so brave.", "happy"), ("PLAYER", "He's holding a sword that is three pixels wide.", "normal")]]},
    "photo_frame": {"lines": [
        [("PLAYER", "A photo of a lake. The camera was mostly pointed at the sky.", "normal"),
         ("PLAYER", "Whoever took it had terrible framing.", "normal")],
        [("MIAO MEOW", "Is anybody in the picture?", "normal"), ("PLAYER", "Just a blurry elbow.", "normal")]]},
    "plant": {"lines": [
        [("PLAYER", "A cactus? ...No. It's plastic.", "normal"),
         ("PLAYER", "It's thriving. Fake plants have the best survival rate.", "normal")],
        [("MIAO MEOW", "I'd water it, but I think that would be mean.", "gentle")]]},
    "plushie": {"lines": [
        [("PLAYER", "Wait... doesn't this look like you?", "normal"), ("MIAO MEOW", "Me?!", "surprised"),
         ("MIAO MEOW", "Hey! That plushie is adorable!", "happy"),
         ("MIAO MEOW", "...Actually, I think it looks smarter than me.", "gentle"),
         ("PLAYER", "That's a pretty low bar.", "normal"), ("MIAO MEOW", "HEY!!", "surprised")],
        [("MIAO MEOW", "Okay, okay, we both look great. Can we get back to work?", "happy")],
        [("PLAYER", "The crown is a little crooked. Somebody loved this toy a lot.", "gentle")]]},
    "desk": {"lines": [
        [("PLAYER", "A solid wooden desk. Coffee rings, pencil dents and a lot of sticky notes.", "normal")]],
        "reader": "sticky"},
}
LAMP_ON = (("PLAYER", "Perfect lighting for staying up way too late.", "normal"),)
LAMP_OFF = (("PLAYER", "It clicks. Nothing happens. The whole room feels asleep.", "normal"),)
BEDSIDE_ON = (("PLAYER", "A small lamp. Warm to the touch, like a tiny sun on a tiny budget.", "normal"),)
BEDSIDE_OFF = (("PLAYER", "A small lamp. It doesn't turn on.", "normal"),)

# ------------------------------------------------------------------ the puzzle objects
PHONE_DEAD = "The line is dead."
CABINET_DEAD = "The little keypad on the cabinet is dark."
COMPUTER_DEAD = "The screen is cold and black."
COMPUTER_STANDBY = "The screen glows faintly. A floppy drive slot sits empty."
BOOKSHELF_TITLE = "THE BOOKSHELF"
POWER_BOX_DONE = "The little light on the box is steady and green."

OPENING = (
    ("SYSTEM", "TRIAL 01 - THE GOLDEN AGE", "normal"),
    ("SYSTEM", "Explore the room.", "normal"),
    ("PLAYER", "This doesn't look like an arcade...", "normal"),
    ("PLAYER", "More like someone's old bedroom.", "normal"),
    ("MIAO MEOW", "Whoa... it's actually kind of cozy!", "happy"),
    ("MIAO MEOW", "Well, except for the part where nothing works.", "normal"),
)
POWER_RESTORED = (("SYSTEM", "POWER RESTORED.", "normal"),)
JOURNAL_REACTION = (
    ("MIAO MEOW", "They lost five times in three minutes... and they laughed anyway?", "gentle"),
    ("MIAO MEOW", "That sounds really nice.", "gentle"),
    ("MIAO MEOW", "I think I'd love a place like that.", "happy"),
)
DISK_FOUND = (
    ("SYSTEM", "A floppy disk was taped inside the back cover.", "normal"),
    ("SYSTEM", "OLD BOOT DISK ADDED TO THE TRIAL INVENTORY.", "normal"),
)
COMPUTER_AFTER = (
    ("PLAYER", "Wait... the top player had administrator access?", "normal"),
    ("MIAO MEOW", "I think I've seen that name on the leaderboard before...", "normal"),
    ("MIAO MEOW", "But I thought they just really liked playing games.", "gentle"),
)

# Miao Meow's hints, only when asked (talk to her): vague, then the area, then a clearer direction. Never the password.
HINTS = {
    "power": ("It's awfully dark in here. And awfully quiet.",
              "That grey box on the wall looks like it has something to do with electricity.",
              "Maybe there's a way to join the battery to the lamp. Try turning the pieces inside the box."),
    "phone": ("Machines like to talk once they wake up.",
              "The telephone on the desk might have something to say.",
              "It beeps in long and short sounds. Maybe something around the desk can help read them."),
    "cabinet": ("People hide useful things in boring places.",
                "The desk has a drawer. The cabinet has a keypad.",
                "A chart that turns beeps into letters, and a keypad that wants letters. See where I'm going?"),
    "bookshelf": ("That note sounded like a riddle.",
                  "Where do stories sleep? Think shelves.",
                  "Look through the books on the bookshelf. One of them is not like the others."),
    "computer": ("I think this room still has one machine nobody has touched.",
                 "The old computer has a slot that looks like it eats floppy disks.",
                 "We found a disk. The computer has a drive. Do the math."),
    "done": ("That was fun. Whoever lived here was a legend. Let's head back whenever you're ready.",),
}

# ------------------------------------------------------------------ the old computer
BREAKOUT_TITLE = "HAPPY BREAKOUT v0.3"
BREAKOUT_BLURB = '"A tiny game I made instead of doing homework."'
DESKTOP_MENU = ("PLAY GAME", "HIGH SCORES", "LOCKED FILES", "EXIT")
LOCKED_DENIED = ("ACCESS DENIED.", "THIS FILE UNLOCKS WHEN THE GAME IS CLEARED.")
GAME_CLEAR = ("GAME CLEAR!", "Finally fixed the collision bug.", "Only took me three nights.", "I should probably do my homework now.")
HIGH_SCORES = (("AAA", 4200), ("NYCU", 3100), ("CAT", 1337), ("ZZZ", 10))
ARCHIVE_LINES = ("ARCHIVE RESTORED.", "MEMORY FRAGMENT 01 UNSEALED.")
ADMIN_CARD = ("PLAYER_000", "SYSTEM ADMINISTRATOR ACCESS")
