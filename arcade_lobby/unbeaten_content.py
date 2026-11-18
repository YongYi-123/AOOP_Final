"""TRIAL 02 - THE UNBEATEN RECORD: everything the hall says (English only; the pixel font has no ; * & # = or long dashes).

Dialogue lines are (speaker, text, mood) tuples. People in the hall speak as "T2_<key>" (registered by the scene with
their own name tag and portrait); "PLAYER", "MIAO MEOW", "SYSTEM" and "CORE" are the story's speakers.

The founder of the arcade is named by the people who knew the place, a few of them, in passing. Nothing here says what
became of him, what his last message was, or why the arcade closed; PLAYER_000 stays a name on a board.
"""
import unbeaten_record as T

TITLE = "TRIAL 02 - THE UNBEATEN RECORD"
OBJECTIVE = "Explore the tournament."

OPENING = (
    ("SYSTEM", "MEMORY RECONSTRUCTION LOADED.", "normal"),
    ("MIAO MEOW", "WHOA!!", "surprised"),
    ("MIAO MEOW", "Look at all these people!", "happy"),
    ("PLAYER", "Is this really the same arcade?", "normal"),
    ("MIAO MEOW", "It's so lively!", "happy"),
    ("MIAO MEOW", "Wait... there's a tournament going on!", "surprised"),
    ("PLAYER", "So we're supposed to enter?", "normal"),
    ("MIAO MEOW", "Obviously! I wanna see you win!", "happy"),
)

# Miao Meow and the player put two and two together (the bedroom of Trial 01); she only feels she knew him.
REALIZATION = (
    ("MIAO MEOW", "Kevin... That name sounds so familiar.", "gentle"),
    ("PLAYER", "You think he's the one who lived in that bedroom?", "normal"),
    ("MIAO MEOW", "Maybe! The games, the homework, all those silly notes...", "happy"),
    ("PLAYER", "And now he built an entire arcade.", "normal"),
    ("MIAO MEOW", "He really did it...", "gentle"),
    ("MIAO MEOW", "But why do I feel like I knew him?", "normal"),
    ("PLAYER", "Maybe you were friends?", "normal"),
    ("MIAO MEOW", "Hehe... I'd like that.", "happy"),
    ("MIAO MEOW", "...Actually, I think we might have been really close.", "gentle"),
)

# ------------------------------------------------------------------ the people of the hall
# key: name tag, where they stand (feet), what they do, look, and what they say.
#   pose     idle / sit / cheer / press (playing a cabinet) / wave; "walk" with a route of points
#   talk     {phase: conversation} where the phase is the saved number of rounds won (T.phase): 0 before the qualifier,
#            1 after it, 2 after the semifinal, 3 after the final. Phase 0 may also have "0+" (once the badge is on).
#            A conversation: first (the first talk in that phase), again (later talks, in turn), clue (what this person
#            knows that a puzzle of that phase needs: told on the first talk and kept in the "again" turn, so it can
#            always be asked for again), kevin (the first talk mentions the founder: counted for Miao's realisation).
# Nobody's lines from an earlier phase come back in a later one.
SKINS = {"peach": ((250, 214, 180), (255, 140, 170), (30, 20, 50)), "tan": ((228, 176, 128), (240, 120, 130), (30, 20, 50)),
         "caramel": ((190, 132, 90), (226, 112, 118), (24, 14, 40)), "brown": ((150, 102, 70), (214, 104, 110), (255, 244, 230)),
         "porcelain": ((255, 232, 212), (255, 150, 176), (30, 20, 50))}


def say(who, *rows):
    """Lines for one person: "PLAYER: ..." / "MIAO: ..." switch speaker, a leading ^ is happy and ! is surprised."""
    out = []
    for text in rows:
        speaker = f"T2_{who}"
        for tag, name in (("PLAYER: ", "PLAYER"), ("MIAO: ", "MIAO MEOW")):
            if text.startswith(tag):
                speaker, text = name, text[len(tag):]
        mood = "normal"
        if text[:1] in "^!":
            mood, text = ("happy" if text[0] == "^" else "surprised"), text[1:]
        out.append((speaker, text, mood))
    return tuple(out)


def talk(who, phases):
    """{phase: dict(first=(...), again=((...), ...), clue=(...), kevin=bool)} with every line run through say()."""
    out = {}
    for phase, conv in phases.items():
        c = dict(conv)
        c["first"] = say(who, *conv["first"])
        c["again"] = tuple(say(who, *rows) for rows in conv.get("again", ()))
        if "clue" in conv:
            c["clue"] = say(who, *conv["clue"])
        out[phase] = c
    return out


PEOPLE = {
    "host": dict(
        name="HOST", pos=(184, 92), facing="down", pose="wave", zone=(170, 100, 60, 16), accent=(255, 214, 90),
        look=dict(shirt=(200, 40, 60), hair=(40, 30, 40), skin="tan", hair_style="spiky", eyes="happy"),
        outfit=(None, "retro_sunglasses", "star_pin", None, None, None)),
    "clerk": dict(
        name="REGISTRATION", pos=(40, 82), facing="down", pose="idle", zone=(30, 102, 16, 12), accent=(80, 230, 245),
        look=dict(shirt=(90, 160, 255), hair=(112, 70, 44), skin="porcelain", hair_style="bob"),
        talk=talk("clerk", {
            0: dict(first=("Welcome! Badge pick-up for competitors is right here.",
                           "Let me find you... huh. Your entry isn't coming up.",
                           "Somebody knocked a soda over the ledger an hour ago. Half the names are just... sticky.",
                           "PLAYER: So I'm not in the tournament?",
                           "Oh, you're in there somewhere! Tell the terminal your entry code and it'll find you.",
                           "^The rules are on the poster behind me. I'm not going anywhere."),
                    again=(("The terminal's right here whenever you've got your code.",),
                           ("Lost something? Everything people drop ends up in the lost and found, right beside me.",),
                           ("The ledger's on the desk. Try not to touch the sticky page. Or do. It's already ruined.",))),
            "0+": dict(first=("^Nice badge. It suits you.",),
                       again=(("^The host is on the stage. Go get them!",),
                              ("Registration's closed. Anyone who shows up now goes on the waiting list. Rules are rules.",))),
            1: dict(first=("^Everyone's talking about your qualifier! Three people asked me your name.",),
                    again=(("The bracket board? Don't look at me, I only do the ledger. It's still on the desk if you need a number.",),
                           ("I gave my last badge pin to the kid. He told me he's ten. He is not ten.",))),
            2: dict(first=("^A finalist from MY desk. I'm framing that ledger. Sticky page and all.",),
                    again=(("The old champ used to sign in here every year. Always early, always with a joke for the clerk.",),
                           ("The stage is dark? Ask the people who've been coming here forever. They know the old stories.",))),
            3: dict(first=("^You did it! I'm writing CHAMPION next to your entry. In pen. Permanent pen.",),
                    again=(("I should start closing the ledger. The night's nearly over.",),
                           ("Funny. I wrote ten o'clock as closing time, but that clock still says six-fifty.",))),
        })),
    "attendant": dict(
        name="PRIZE COUNTER", pos=(354, 82), facing="down", pose="idle", zone=(330, 102, 40, 12), accent=(255, 140, 190),
        look=dict(shirt=(255, 122, 172), hair=(240, 202, 96), skin="peach", hair_style="long"),
        talk=talk("attendant", {
            0: dict(first=("Prize counter! Tonight's grand prize is the big gold one on the stage.",
                           "Funny thing about tournament night. Nobody spends their tickets. They're all too busy watching."),
                    again=(("See the little black cat stickers on the machines? The boss puts one on every cabinet. For luck.",),
                           ("The newest plate on the trophy shelf is still blank. Tonight we find out whose name goes on it.",))),
            1: dict(first=("^One round down! I've started polishing the empty spot on the shelf. Not for you specifically.",
                           "^...It's for you."),
                    again=(("Nobody's spent a single ticket since the qualifier. They're all crowded round that bracket board.",),)),
            2: dict(first=("The stage key? The old champion who set up that cabinet loved puzzles. Sorry, that's all I know!",),
                    clue=("Every time somebody dusts the trophy cabinet, the trophies get put back any old way.",
                          "The old champ HATED that. Said there was only one proper way to stand them."),
                    again=(("I'd help you look, but if I leave the counter the tickets get ideas.",),)),
            3: dict(first=("^The newest name for the shelf! Engraved in gold, or in very fancy gold?",),
                    again=(("I'm boxing up the prize table. Everyone's heading home soon.",),
                           ("Strange. I counted the tickets twice and the number keeps going UP.",))),
        })),
    "old_regular": dict(
        name="OLD REGULAR", pos=(98, 114), facing="up", pose="idle", accent=(214, 164, 62),
        look=dict(shirt=(126, 150, 98), hair=(200, 204, 224), skin="tan", hair_style="short", eyes="sleepy"),
        outfit=("neon_cap", None, None, None, None, None),
        talk=talk("old_regular", {
            0: dict(kevin=True,
                    first=("Kevin built this place, you know.",
                           "Started with a couple of homemade games.",
                           "^Look at it now. You can barely find a free machine!"),
                    again=(("First week, it was two cabinets and a fan that only worked if you kicked it.",),
                           ("That board up there? PLAYER_000 has been on top longer than I can remember.",
                            "Nobody knows who it is. Nobody's come close, either."))),
            1: dict(first=("^That was a great fight! I knew you had it in you. I said so to nobody, but I said it.",),
                    clue=("I had a bench seat for the Challenger's first match.",
                          "Fourteen blocks. I counted every one. Then one clean hit, and the Challenger walked off the winner.",
                          "Strange that the bracket board can't remember any of it."),
                    again=(("My knees say sit down. My heart says stand up and cheer. My knees are winning.",),)),
            2: dict(first=("^Into the final! The last newcomer who managed that ended up on the photo wall.",),
                    clue=("Those trophies weren't always arranged like that, you know.",
                          "There's an old photo wall around here somewhere. Every trophy got its own night. The years are on the banners."),
                    again=(("I watched every one of those trophies get handed out. Best nights of my life.",),)),
            3: dict(kevin=True,
                    first=("^What a tournament! Kevin would've loved seeing everyone cheering like this.",),
                    again=(("Guess I should head home. I always say that. Then I stay for one more game.",),
                           ("Hm. The door's right there. Why does it feel so far away tonight?",))),
        })),
    "student": dict(
        name="STUDENT", pos=(35, 250), facing="up", pose="press", accent=(80, 230, 245),
        look=dict(shirt=(166, 110, 250), hair=(38, 32, 50), skin="caramel", hair_style="bob", eyes="wide"),
        outfit=(None, None, None, None, None, None),
        talk=talk("student", {
            0: dict(kevin=True,
                    first=("Kevin's a genius.",
                           "Most places only care about high scores.",
                           "^But he made this place fun even for people like me.",
                           "PLAYER: People like you?",
                           "^People who are TERRIBLE at games. Never beaten level two. Best night of my week, every week."),
                    again=(("Don't watch me play. It's embarrassing. For both of us.",),
                           ("I lost to the claw machine once. It wasn't even trying.",))),
            1: dict(first=("!You WON! I screamed. A security guard looked at me. We don't even have a security guard.",),
                    clue=("!And did you hear? DANNY K. beat JUNE P.! Nobody beats June!",
                          "I was so shocked I dropped my coin. It's still under the machine somewhere."),
                    again=(("I'm studying your fight. For science. My science is bad.",),)),
            2: dict(first=("^You're in the FINAL? I'm telling everyone I know you. I don't know you. I'm telling them anyway.",),
                    clue=("Fun fact: the very first championship had two cabinets and a bedsheet banner.",
                          "It's in one of the photos on the wall. I've stared at those a LOT. Instead of homework."),
                    again=(("My homework is due tomorrow. My priorities are due tonight.",),)),
            3: dict(first=("^CHAMPION! I knew it! I didn't know it. But I hoped it!",),
                    again=(("I should go home and do my assignment. Right after one more game.",),
                           ("My phone says it's late. The arcade says it's early. I trust the arcade.",))),
        })),
    "waiting": dict(
        name="WAITING PLAYER", pos=(61, 254), facing="up", pose="idle", accent=(140, 240, 150),
        look=dict(shirt=(130, 230, 90), hair=(214, 104, 52), skin="peach", hair_style="spiky"),
        talk=talk("waiting", {
            0: dict(first=("Twenty minutes I've been waiting for this machine. He's on his last life. Again.",
                           "Every time he's about to lose, the screen says CONTINUE? and he says yes.",
                           "Every. Single. Time."),
                    again=(("Still waiting. I've made peace with it.",),
                           ("If you win tonight, can I have your turn on this machine? Kidding. Mostly.",))),
            1: dict(first=("You won a whole round and I STILL haven't had a turn. Inspiring and upsetting.",),
                    clue=("TOMMY wanted to enter tonight. He cried a little. Juniors get their own bracket on Saturday.",),
                    again=(("He just said yes to CONTINUE again. I didn't even have to look.",),)),
            2: dict(first=("Still here. Still waiting. The guy is on his ninth continue.",),
                    again=(("At this point I'm not waiting for the machine. I'm waiting to see if he ever stops.",),)),
            3: dict(first=("^You won? Great! Wait. Does that mean the machine is free now?",
                           "...He pressed CONTINUE again."),
                    again=(("Everybody's leaving. Except him. And therefore me.",),
                           ("Weird. The CONTINUE timer has been stuck on nine for five minutes.",))),
        })),
    "maintenance": dict(
        name="MAINTENANCE", pos=(132, 250), facing="left", pose="walk", route=((132, 250), (132, 268), (112, 268), (132, 268)),
        accent=(255, 168, 70),
        look=dict(shirt=(70, 66, 110), hair=(112, 70, 44), skin="brown", hair_style="short"),
        outfit=("neon_headphones", None, None, None, None, None),
        talk=talk("maintenance", {
            0: dict(first=("Evening. Don't mind me. I'm keeping an eye on number three.",
                           "It switched itself on twice today. Unplugged, mind you. Unplugged.",
                           "Probably a loose wire. Probably."),
                    again=(("The boss wrote half the code in these machines himself. When something acts weird, he fixes it.",),
                           ("I keep a log taped to the side of number three. If it does anything funny, it goes on the list.",))),
            1: dict(first=("Nice footwork out there. Number three cheered for you. Not a figure of speech. It beeped.",),
                    again=(("The bracket board's on the same circuit as number three. Funny coincidence. I don't like funny coincidences.",),)),
            2: dict(first=("The championship cabinet won't wake up without its key. The old champ insisted. Very dramatic person.",),
                    clue=("I rigged the trophy cabinet for them years ago. A little lever on the side.",
                          "It only opens when everything inside is just so. Their words, not mine."),
                    again=(("I logged a flicker on the leaderboard earlier. Then I un-logged it. Then I logged it again.",),)),
            3: dict(first=("^Congratulations, champ. Even number three looks proud.",
                           "...Which is a strange thing to say about a machine that's switched off."),
                    again=(("I'll start unplugging things once everyone's out. Number three first. Just in case.",),
                           ("I swear I heard that cabinet say something. Probably the fan. Probably.",))),
        })),
    "kid": dict(
        name="YOUNG VISITOR", pos=(196, 250), facing="right", pose="walk", route=((196, 250), (214, 264), (200, 284), (140, 284), (150, 252)),
        accent=(255, 214, 90),
        look=dict(shirt=(255, 218, 80), hair=(84, 140, 240), skin="peach", hair_style="spiky", eyes="sparkle"),
        talk=talk("kid", {
            0: dict(first=("Are you in the tournament?! Are you good?! Are you the BEST?!",
                           "I'm gonna be in it when I'm big. Mom says you have to be ten.",
                           "I'm seven and three quarters."),
                    again=(("Can you do a spinning kick? Can you teach me? Can you do it NOW?",),
                           ("The magazines say if you press every button at once, something happens. It's usually my mom.",))),
            1: dict(first=("^You were SO COOL! I did the kick at my mom. She was not happy.",
                           "I didn't see the other matches. I was in the bathroom. For ALL of them."),
                    again=(("When I'm big I'm gonna block fifteen times. No. SIXTEEN.",),)),
            2: dict(first=("!You're in the FINAL?! Can I hold your badge? I won't run. I'll walk. Fast.",),
                    again=(("I touched a trophy once. The lady at the counter made a face like a dropped ice cream.",),)),
            3: dict(first=("^YOU'RE THE CHAMPION! I'm telling my whole class. Even the ones I don't like.",),
                    again=(("Mom says it's time to go. I said five more minutes. She said that an hour ago.",),
                           ("Why is everybody walking so slow? It's like the floor got longer.",))),
        })),
    "fan": dict(
        name="TOURNAMENT FAN", pos=(270, 138), facing="up", pose="cheer", accent=(255, 90, 170),
        look=dict(shirt=(255, 90, 150), hair=(240, 112, 176), skin="tan", hair_style="long", eyes="happy"),
        talk=talk("fan", {
            0: dict(kevin=True,
                    first=("You know what I like about Kevin?",
                           "^He actually listens when we complain about the controls!",
                           "Pretty sure he's fixed the same game twelve times."),
                    again=(("I made a sign. It says GO. I ran out of time for the rest.",),)),
            1: dict(first=("^THAT is how you open a tournament!",),
                    clue=("Did you catch the Champion's first match? Poor ROCKO.",
                          "It was over before I finished my soda. And I drink FAST."),
                    again=(("I'm adding your name to my sign. I'm out of space. It's going on the back.",),)),
            2: dict(first=("^I updated my sign! It now says GO YOU.",),
                    again=(("Champion versus you. I'm cheering for both. Mostly you.",),)),
            3: dict(first=("^WE WON! I mean, you won. But I held the sign, so. Team effort.",),
                    again=(("I bet tonight ends up on the photo wall. Front and centre.",),
                           ("My voice is gone. I'm cheering in sign language now.",))),
        })),
    "visitor": dict(
        name="VISITOR", pos=(112, 138), facing="up", pose="sit", accent=(120, 200, 255),
        look=dict(shirt=(90, 160, 255), hair=(70, 50, 110), skin="caramel", hair_style="long"),
        talk=talk("visitor", {
            0: dict(kevin=True,
                    first=("The owner? Kevin? I heard he used to make games instead of finishing his assignments.",
                           "^Honestly, I respect that."),
                    again=(("My professor would hate this place. That's how I know it's good.",),)),
            1: dict(first=("Your qualifier was the most exciting thing I've seen all semester. Low bar. Still.",),
                    clue=("MEI and JUNE are best friends. They were SO relieved they didn't have to fight each other in round one.",),
                    again=(("I'm here for the atmosphere. And the popcorn. Mostly the popcorn.",),)),
            2: dict(first=("The final! I should leave. I'm not leaving.",),
                    clue=("The old champ used to say the first thing you see walking in should make you gasp.",),
                    again=(("My professor emailed. I'll answer after the final. Or after the semester.",),)),
            3: dict(first=("^Congratulations! I'll tell my professor I learned something tonight. It won't be true.",),
                    again=(("I should catch the last bus. The clock says I've got plenty of time. It's been saying that for a while.",),)),
        })),
    "nycu": dict(
        name="NIGHT OWL", pos=(336, 246), facing="up", pose="idle", accent=(80, 230, 245),
        look=dict(shirt=(236, 240, 252), hair=(38, 32, 50), skin="porcelain", hair_style="short", eyes="sleepy"),
        talk=talk("nycu", {
            0: dict(kevin=True,
                    first=("Came straight from campus. The wind at NYCU nearly blew me here faster than the bus.",
                           "Kevin studied there too, they say. Debugged his first game at 3 AM on instant noodles.",
                           "^Which, as a student, is the only way anything gets debugged."),
                    again=(("Unfinished homework: three. Cups of instant noodles today: also three. Balance.",),
                           ("I'll do my assignment after the final. Or after the prizes. Or tomorrow. Probably tomorrow.",))),
            1: dict(first=("^Nice win. You fight like someone with a deadline.",),
                    clue=("DANNY's first match took FOREVER. Three rounds. My noodles went cold watching it.",),
                    again=(("I timed every match tonight. Instead of writing my lab report. Worth it.",),)),
            2: dict(first=("A final? I'm staying. My assignment can wait. It's very patient.",),
                    clue=("The old champs hid notes all over this place, you know. Tucked behind boards, under things.",
                          "I found one behind the schedule board once. Put it back where I found it. I respect privacy. Mostly."),
                    again=(("The wind outside is louder than the crowd. Or I've gone deaf from the cheering.",),)),
            3: dict(first=("^You won! Time to go home and... no. Time to stay a bit longer.",),
                    again=(("The bus app says no more buses tonight. Usually it says LATE. Not NEVER.",),)),
        })),
    "spectator": dict(
        name="SPECTATOR", pos=(136, 122), facing="up", pose="cheer", accent=(255, 214, 90),
        look=dict(shirt=(255, 168, 70), hair=(112, 70, 44), skin="brown", hair_style="spiky", eyes="happy"),
        talk=talk("spectator", {
            0: dict(first=("^WOOO! Oh. Sorry. I've been cheering since six o'clock. I don't know how to stop.",),
                    again=(("I'm saving my loudest WOOO for the final. You'll know it when you hear it.",),)),
            1: dict(first=("^WOOO! I lost track of the other matches. Too much woo-ing.",),
                    again=(("I'm pacing myself. Small woo. Medium woo. Saving the big one.",),)),
            2: dict(first=("^Final! Final! Final! Sorry. I've been chanting it to myself.",),
                    again=(("Tradition says the winner of the final ends up on the photo wall. Smile big!",),)),
            3: dict(first=("^WOOOOOOO! That was it. That was the big one. I have no woo left.",),
                    again=(("Okay. Heading out. Right after this last... woo.",),
                           ("Did the lights just dim? Or is that my eyes after all that woo-ing?",))),
        })),
    "rookie": dict(
        name="THE ROOKIE", pos=(150, 196), facing="right", pose="idle", accent=(155, 90, 220),
        look=dict(shirt=(155, 90, 220), hair=(214, 104, 52), skin="peach", hair_style="spiky", eyes="wide"),
        talk=talk("rookie", {
            0: dict(first=("Hey! Are you in my bracket? I've been practising all week.",
                           "Well. All yesterday. Okay, mostly this morning.",
                           "^I just go for it, you know? Swing first, think later!"),
                    again=(("My plan is: rush in. That's the whole plan.",),)),
            1: dict(first=("^Good match! You were so fast. I'm practising for a whole week this time. Probably.",),
                    again=(("Next year I'm going to wait before I swing. For like, half a second.",),)),
            2: dict(first=("The FINAL? Tell the Champion I said hi. Then dodge.",),
                    again=(("I asked the Challenger for tips. They just blocked my question.",),)),
            3: dict(first=("^You beat EVERYONE? Now I can say I lost to the champion. Technically true!",),
                    again=(("I'm going home to practise. Right after one more game.",),)),
        })),
    "challenger": dict(
        name="THE CHALLENGER", pos=(288, 186), facing="left", pose="idle", accent=(190, 90, 100),
        look=dict(shirt=(190, 90, 100), hair=(38, 32, 50), skin="caramel", hair_style="long", eyes="sleepy"),
        outfit=(None, "retro_sunglasses", None, None, None, None),
        talk=talk("challenger", {
            0: dict(first=("So you're the one everyone's whispering about.",
                           "I don't rush in. I wait behind my guard, then I hit back.",
                           "Only a heavy blow gets through. Not that you'll find out."),
                    again=(("Patience wins tournaments.",),)),
            1: dict(first=("So you're through. As was I.",),
                    clue=("Fourteen blocks in my first match. A new record. And the win, naturally.",
                          "You'll be number fifteen."),
                    again=(("Patience. You'll see.",),)),
            2: dict(first=("Hm. You read me. Not many people do.",
                           "^Go win it. Make the semifinal look good."),
                    again=(("I'll be watching the final. Blocking nothing. Just watching.",),)),
            3: dict(first=("Champion. Hm. It suits you better than I expected.",
                           "Next season, I block sixteen."),
                    again=(("Everyone's leaving. I'd rather go last. Old habit.",),)),
        })),
    "champion": dict(
        name="THE CHAMPION", pos=(324, 122), facing="left", pose="idle", accent=(235, 150, 65),
        look=dict(shirt=(235, 150, 65), hair=(40, 30, 40), skin="brown", hair_style="short"),
        outfit=(None, None, "champion_badge", None, None, None),
        talk=talk("champion", {
            0: dict(first=("Undefeated three years running. I don't plan on stopping tonight.",
                           "When I wind up, you'd better move. Little hits won't stop me.",
                           "Even I never got near the top of that old board, though. PLAYER_000.",
                           "Nobody even knows who it is."),
                    again=(("Warm up. You'll need it.",),)),
            1: dict(first=("My first match? Short. I don't like to keep a crowd waiting.",),
                    again=(("The semifinal's yours to lose. Don't.",),)),
            2: dict(first=("So. It's you and me. Good.",),
                    clue=("Well. Once they find the stage key. The old champs always kept it with their trophies.",),
                    again=(("Three years I've walked past that trophy cabinet. Never once looked closely.",),)),
            3: dict(first=("...Well played. Really.",
                           "Three years is a good run. Maybe it's time the gold went to somebody new."),
                    again=(("I'll slip out before the crowd does. Former champions leave first.",),
                           ("That old board still says PLAYER_000 up top. Some records just don't move.",))),
        })),
}
KEVIN_PEOPLE = tuple(k for k, v in PEOPLE.items() if any(c.get("kevin") for c in v.get("talk", {}).values()))
STAFF = ("host", "clerk", "attendant")                      # they stay when the crowd goes home
COMPETITORS = {"rookie": 1, "challenger": 2, "champion": 3}

# Miao Meow, the first time she is asked in each phase (after that: her hints, which grow clearer when asked again).
MIAO_CHAT = {
    0: (("MIAO MEOW", "So many people! Everybody looks SO happy in here.", "happy"),
        ("MIAO MEOW", "Whoever built this place really pulled it off. You can tell they love it.", "gentle"),
        ("MIAO MEOW", "Ask me again if you get stuck. I'm VERY good at noticing things.", "happy")),
    1: (("MIAO MEOW", "Did you see that last hit? WHAM!", "happy"),
        ("MIAO MEOW", "I did a little victory spin. Nobody saw. Good.", "happy"),
        ("MIAO MEOW", "But the board... Before we try to fix it, let's go ask the host what the referee wrote down!", "normal")),
    2: (("MIAO MEOW", "The FINAL! I'm so excited my tail is doing a thing.", "happy"),
        ("MIAO MEOW", "...Hey. Did the big screen just blink? Or was that me?", "surprised"),
        ("MIAO MEOW", "Never mind! Ask me again if you want a hint.", "happy")),
    3: (("MIAO MEOW", "CHAMPION! CHAMPION! You're the CHAMPION!", "happy"),
        ("MIAO MEOW", "...Huh. Is it just me, or is the music getting quieter?", "surprised"),
        ("MIAO MEOW", "Probably nothing! Go get your trophy!", "happy")),
}
OBJECTIVES = {"entry": "Explore the tournament.", "bracket": "Fix the bracket board.",
              "trophies": "Find the championship stage key.", "key": "Unlock the championship stage.",
              "done": "Meet the host for the trophy ceremony.",
              "fight": {1: "Ask the host for ROUND 01.", 2: "Ask the host for ROUND 02.", 3: "Ask the host for the GRAND FINAL."}}


def objective(run):
    stage = run.stage
    goal = OBJECTIVES[stage]
    return goal[run.next_round.number] if stage == "fight" else goal

HOST = {
    "unregistered": (("T2_host", "Welcome, welcome to the NEON CORNER CHAMPIONSHIP!", "happy"),
                     ("T2_host", "Competitors, pick up your badge at the registration desk. No badge, no fight!", "normal")),
    "unregistered_again": (("T2_host", "Registration's on the left, champ. The desk with the clock.", "normal"),),
    "offer": {1: (("T2_host", "Fresh blood! ROUND 01, the QUALIFIER!", "happy"),
                  ("T2_host", "Your opponent: THE ROOKIE!", "normal")),
              2: (("T2_host", "ROUND 02, the SEMIFINAL! Facing you: THE CHALLENGER!", "happy"),
                  ("T2_host", "They block, they counter, they never blink.", "normal")),
              3: (("T2_host", "This is it, folks. The GRAND FINAL!", "happy"),
                  ("T2_host", "Undefeated three years running... THE CHAMPION!", "normal"))},
    "won": {1: (("T2_host", "WHAT A MATCH!", "happy"),
                ("T2_host", "OUR CHALLENGER MOVES ON TO THE SEMIFINAL!", "happy"),
                ("T2_host", "And in the semifinal you'll face... uh. Huh. The bracket board!", "surprised"),
                ("T2_host", "It scrambled itself! Every name, everywhere! Can somebody put it right?", "normal"),
                ("MIAO MEOW", "Round one, done! But... who do we fight next?", "surprised")),
            3: (("T2_host", "THE UNDEFEATED... HAS BEEN DEFEATED!", "happy"),
                ("T2_host", "Folks, the trophy ceremony starts in a moment! Somebody find me a microphone that works!", "happy"),
                ("MIAO MEOW", "We WON! Go say hi to everyone. Then the host wants us on the stage!", "happy")),
            2: (("T2_host", "UNBELIEVABLE!", "happy"),
                ("T2_host", "FOLKS, WE HAVE A FINALIST!", "happy"),
                ("T2_host", "Championship stage, power UP!", "happy"),
                ("T2_host", "...Power up? Hello? Where's the stage key? The old brass one?", "surprised"),
                ("T2_host", "Nobody's seen it since the last old champ set that cabinet up. It has to be in this hall somewhere!", "normal"),
                ("MIAO MEOW", "A treasure hunt before the final? I LOVE this place!", "happy"))},
    "bracket": (("T2_host", "The board's still scrambled. I can't call the semifinal without it!", "normal"),
                ("T2_host", "All I've got are the referee's slips. The printer smudged every name. Here, take a look.", "normal")),
    "bracket_done": (("T2_host", "The board's fixed! Folks, the semifinal is set!", "happy"),
                     ("T2_host", "Our newcomer against... THE CHALLENGER!", "happy")),
    "key_missing": (("T2_host", "No key, no championship stage. The old champs always said it was safe with the trophies.", "normal"),),
    "key_found": (("T2_host", "You found it?! Put it in the championship cabinet, left side of the stage!", "happy"),),
    "key_used": (("T2_host", "THE CHAMPIONSHIP STAGE IS LIVE!", "happy"),
                 ("T2_host", "Whenever you're ready, champ. The final awaits!", "normal")),
    "ceremony": (("T2_host", "There's our new champion! The trophy's polished, the crowd's warmed up.", "happy"),
                 ("T2_host", "Say the word and we start the ceremony!", "normal")),
    "lost": (("T2_host", "Ooh, so close! The crowd loves a comeback.", "normal"),
             ("T2_host", "Catch your breath. The stage isn't going anywhere.", "normal")),
    "forfeit": (("T2_host", "Cold feet? No shame in it. The stage will wait for you.", "normal"),),
}

REGISTERED = (("T2_clerk", "There you are! Your entry is back in the bracket.", "happy"),
              ("T2_clerk", "Here's your TOURNAMENT BADGE. It's only good for tonight, so wear it proudly!", "happy"),
              ("T2_clerk", "The host is on the stage. Good luck out there!", "normal"),
              ("MIAO MEOW", "Ooh, shiny! Let's go, let's go!", "happy"))

ENDING_CHEER = (("T2_host", "AND WE HAVE OUR CHAMPION!", "happy"),
                ("T2_host", "WHAT A NIGHT!", "happy"),
                ("T2_host", "EVERYONE, GIVE OUR WINNER A ROUND OF APPLAUSE!", "happy"))
ENDING_GOODBYE = (("T2_host", "Thank you for coming, everyone!", "happy"),
                  ("T2_host", "See you all next year!", "happy"))
ENDING_FINAL = (("PLAYER", "Huh? Didn't they just turn that machine off?", "normal"),
                ("MIAO MEOW", "Maybe it wants one more round!", "happy"))
ENDING_FLICKER = (("MIAO MEOW", "That's strange... I feel like I've seen those lights flicker before.", "gentle"),
                  ("PLAYER", "You remember something?", "normal"),
                  ("MIAO MEOW", "Not really. Just... a feeling.", "gentle"))
CORE_LINE = (("CORE", "One more game?", "normal"),)
SYSTEM_MESSAGES = ("ACTIVE PLAYERS: DECREASING", "SESSION EXTENSION: ENABLED", "EXIT CONTROL: OVERRIDE REQUESTED")
FINAL_CARD = ("MEMORY FRAGMENT 02 RECOVERED.", "TRIAL 02 COMPLETE.")

# ------------------------------------------------------------------ things to look at
# key: lines (the first look), again (later looks, in turn). Some open a document afterwards (see DOCS).
LOOKS = {
    "poster": dict(lines=(("PLAYER", "The championship poster. There's a lot of small print.", "normal"),)),
    "ledger": dict(lines=(("PLAYER", "The registration ledger. One page is soaked in soda.", "normal"),)),
    "lost_found": dict(lines=(("PLAYER", "A box of forgotten things. One glove. A yo-yo. A ticket stub for tonight.", "normal"),
                              ("MIAO MEOW", "No name on it... but nobody else is missing a ticket. I bet it's yours!", "happy")),
                       again=()),
    "clock": dict(lines=(("PLAYER", "The clock above the registration desk.", "normal"),
                         ("PLAYER", "It seems to be running slightly behind.", "normal")),
                  again=((("PLAYER", "It's further behind than last time. Or is it?", "normal"),),)),
    "leaderboard": dict(lines=(("PLAYER", "The old leaderboard. ALL-TIME BEST.", "normal"),)),
    "trophy_shelf": dict(lines=(("PLAYER", "The trophy cabinet. Three old trophies, each on a heavy brass base.", "normal"),
                                ("MIAO MEOW", "One more shelf is empty. It's waiting for a name! Yours, maybe?", "happy")),
                         again=((("PLAYER", "Somebody polishes these every day. You can tell.", "normal"),),)),
    "trophy_open": dict(lines=(("PLAYER", "The hidden compartment is empty now. The trophies stand proud.", "normal"),)),
    "trophy_first": dict(lines=(("PLAYER", "The trophy cabinet. A little brass lever sticks out of its side.", "normal"),
                                ("MIAO MEOW", "Ooh. Levers are for pulling. That's the rule.", "happy"))),
    "key_taken": dict(lines=(("PLAYER", "A brass key on a red ribbon. The tag says CHAMPIONSHIP STAGE.", "normal"),
                             ("MIAO MEOW", "We found it! The old champion really liked secrets, huh?", "happy"))),
    "final_cabinet": dict(lines=(("PLAYER", "The championship cabinet. Gold trim, and a brass keyhole under the screen.", "normal"),)),
    "final_locked": dict(lines=(("PLAYER", "The brass keyhole is empty. The screen stays dark.", "normal"),)),
    "final_insert": dict(lines=(("PLAYER", "The key fits. A heavy click, and the whole stage hums.", "normal"),
                                ("MIAO MEOW", "Did the leaderboard just blink? ...Must be the power coming back.", "normal"))),
    "final_ready": dict(lines=(("PLAYER", "The championship cabinet is humming, key in place.", "normal"),)),
    "bracket_board": dict(lines=(("PLAYER", "The bracket board. Eight names in neat little boxes.", "normal"),)),
    "bracket_broken": dict(lines=(("PLAYER", "The bracket board. Every name has slid out of its box.", "normal"),
                                  ("PLAYER", "The rules are still printed along the bottom.", "normal"))),
    "schedule": dict(lines=(("PLAYER", "TONIGHT. 7:30 QUALIFIER. 8:15 SEMIFINAL. 9:00 GRAND FINAL. 9:30 PRIZES.", "normal"),
                            ("PLAYER", "At the bottom, in pen: SESSIONS MAY RUN LATE.", "normal"))),
    "schedule_note": dict(lines=(("PLAYER", "A folded note is tucked behind the schedule. The paper is yellow with age.", "normal"),)),
    "snack_bar": dict(lines=(("PLAYER", "Popcorn, soda, and a sign that says CHEESE FRIES COMING SOON.", "normal"),
                             ("MIAO MEOW", "It's an old sign. A very hopeful old sign.", "normal")),
                      again=((("PLAYER", "The popcorn machine is working overtime tonight.", "normal"),),)),
    "magazines": dict(lines=(("PLAYER", "Old game magazines. Tips, codes, a review calling a racer TOO FAST FOR HUMAN EYES.", "normal"),),
                      again=((("PLAYER", "A reader's letter: DEAR EDITOR, MY CAT KEEPS PAUSING MY GAMES. IS THIS NORMAL?", "normal"),
                              ("MIAO MEOW", "Yes.", "happy")),
                             (("PLAYER", "HIDDEN CHARACTERS: TEN WAYS TO FIND THEM. Page nine is torn out.", "normal"),))),
    "photo_board": dict(lines=(("PLAYER", "The photo wall. Three old championship nights, each winner holding up a trophy.", "normal"),)),
    "bench_left": dict(lines=(("PLAYER", "Spectator benches. Somebody carved a tiny cat into the armrest.", "normal"),)),
    "bench_right": dict(lines=(("PLAYER", "The benches are full. Somebody saved a seat with a single shoe.", "normal"),)),
    "cab_0": dict(lines=(("PLAYER", "STAR BLASTER. The score on the screen is... modest.", "normal"),)),
    "cab_1": dict(lines=(("PLAYER", "PUZZLE PAWS. The queue for it is longer than the game.", "normal"),)),
    "cab_2": dict(lines=(("PLAYER", "OUT OF ORDER. The plug is lying on the floor.", "normal"),
                         ("PLAYER", "The screen says CONTINUE? even though nobody is playing.", "normal"),
                         ("PLAYER", "...Now it's dark again.", "normal")),
                  again=((("PLAYER", "A handwritten log is taped to its side.", "normal"),),)),
    "cab_3": dict(lines=(("PLAYER", "A racing cabinet. The seat is still warm.", "normal"),)),
    "terminal_done": dict(lines=(("SYSTEM", "ENTRY CHECKED IN. HAVE A GREAT TOURNAMENT.", "normal"),)),
}

# ------------------------------------------------------------------ the documents (drawn by unbeaten_ui.DocumentPanel)
POSTER_DOC = {
    "title": "THE NEON CORNER CHAMPIONSHIP",
    "lines": ("ONE NIGHT ONLY. DOORS OPEN 6:00.",
              "REGISTRATION CLOSES AT 7:00 SHARP.",
              "LATER NAMES GO ON THE WAITING LIST."),
    "table": (("DIVISION", "WHO", "ENTRY FEE"),) + tuple(
        (d[0] + "  " + d[1], d[2], (f"{d[3]} TOKEN" + ("S" if d[3] > 1 else "")) if d[3] else "FREE") for d in T.DIVISIONS),
    "footer": ("LOST YOUR WRISTBAND? YOUR ENTRY CODE IS",
               "YOUR DIVISION LETTER, THEN YOUR LEDGER NUMBER.",
               "FOR EXAMPLE: C04."),
}
TICKET_DOC = {
    "title": "ADMIT ONE",
    "lines": ("NEON CORNER", "CHAMPIONSHIP", "COMPETITOR ENTRY", f"PAID: {T.TICKET_FEE} TOKENS", f"CHECKED IN: {T.TICKET_TIME}"),
    "torn": True,
}
LEDGER_DOC = {
    "title": "REGISTRATION LEDGER",
    "head": ("NO.", "NAME", "PAID", "IN"),
    "rows": tuple((f"{n:02d}", name, f"{paid} TOKEN" + ("S" if paid > 1 else "") if paid else "FREE", clock, note)
                  for n, name, paid, clock, note in T.LEDGER),
    "note": "WAITING LIST FROM 7:00",
}
LEADERBOARD_DOC = {
    "title": "ALL-TIME BEST",
    "rows": (("01", "PLAYER_000", "999990", "00/00/00  25:61"),
             ("02", "THE CHAMPION", "412300", "THIS SEASON"),
             ("03", "ROCKO", "398750", "LAST SEASON"),
             ("04", "DANNY K.", "377100", "LAST SEASON"),
             ("05", "MEI L.", "352400", "TWO SEASONS AGO")),
    "glitch_name": "PLAYER_???",
    "note": "THE TOP LINE HAS NEVER BEEN BEATEN.",
}
NOTES_DOC = {
    "title": "MACHINE 3  MAINTENANCE LOG",
    "lines": ("MON  SCREEN CAME ON BY ITSELF. WAS UNPLUGGED.",
              "TUE  SCORE COUNTER WENT UP. NOBODY PLAYING.",
              "WED  NEW FUSE. SEEMS FINE.",
              "THU  IT SAID HELLO. PROBABLY THE TEST SCREEN.",
              "FRI  TOURNAMENT NIGHT. PLEASE BEHAVE."),
}
SLIPS_DOC = {
    "title": "REFEREE'S SLIPS  ROUND ONE",
    "slips": tuple((f"MATCH {m}  SLOTS {2 * m - 1} AND {2 * m}", f"WINNER: SLOT {w}", f"TIME {t}", note)
                   for m, w, t, note in T.SLIPS),
    "note": "THE PRINTER SMUDGED EVERY NAME.",
}
CHAMP_NOTE_DOC = {
    "title": "TO WHOEVER POLISHES THESE NEXT",
    "lines": ("KEEP MY BABIES IN ORDER, PLEASE.",
              "THE NEWEST ONE ALWAYS GOES CLOSEST TO THE DOOR,",
              "SO IT'S THE FIRST THING PEOPLE SEE WALKING IN.",
              "THE OLDEST KEEPS WATCH FROM THE FAR END.",
              "",
              "AND SHOW THE CROWD THEIR LITTLE ENGRAVINGS.",
              "A TROPHY WITH ITS BACK TO THE CROWD",
              "IS A SULKING TROPHY.",
              "",
              "- AN OLD CHAMP"),
}
# The photo wall: (pinned order on the wall) banner text, year as printed, the trophy, a caption.
PHOTOS = (
    {"banner": "NEON CORNER CUP", "year": "1989", "trophy": "rocket", "caption": "SECOND YEAR. STANDING ROOM ONLY."},
    {"banner": "OPENING NIGHT", "year": "1988", "trophy": "cup", "caption": "TWO CABINETS AND A BEDSHEET BANNER."},
    {"banner": "CHAMPIONSHIP", "year": "'90", "trophy": "joystick", "caption": "THE YEAR THE ROOF LEAKED."},
)
PHOTO_STAMP = "PRINTED 03/91"            # the same reprint stamp on all three (it says nothing about the order)
DOCS = {"slips": SLIPS_DOC, "champ_note": CHAMP_NOTE_DOC, "poster": POSTER_DOC, "ticket": TICKET_DOC, "ledger": LEDGER_DOC, "leaderboard": LEADERBOARD_DOC, "notes": NOTES_DOC}
