"""Kevin's authored records. Logical pages remain 7 / 4 / 3 / 4 pages."""
from dataclasses import dataclass
import textwrap
from puzzle_maze.workshop_content import ascii_text

@dataclass(frozen=True)
class Page:
    heading:str
    paragraphs:tuple

@dataclass(frozen=True)
class Document:
    title:str
    style:str
    pages:tuple
    observations:tuple

def P(heading,*paragraphs):return Page(heading,paragraphs)

DOCUMENTS={
 'kevin_note':Document("KEVIN'S EXPERIMENT LOG",'notebook',(
  P('Day 01 — Workshop Log',
    'Finally got the old development terminal working.',
    'The CPU is ancient, the monitor makes an alarming noise, and the keyboard only works when I press the spacebar at a very specific angle.',
    'Perfect.', 'This is exactly the kind of environment that inspires innovation.', 'My goal is simple:',
    'Build an arcade system that can run all our games without exploding.', 'Preferably.'),
  P('Day 04 — CPU Experiment',
    'Spent six hours trying to improve memory access performance.', 'I studied the register file, cache hierarchy, and instruction pipeline.',
    'Everything looked correct on paper.', 'Then I ran the benchmark.', 'The new version was 23% slower.',
    'I stared at the results for fifteen minutes.', 'Miao Meow stared at me.', 'I think we were both disappointed.', "Tomorrow, I'll try again."),
  P('Day 09 — Software Architecture',
    'Today I reorganized the entire game engine.', 'I created a beautiful object-oriented class hierarchy.',
    'GameObject.', 'Character.', 'Enemy.', 'Boss.', 'FinalBoss.', 'AbsolutelyFinalBoss.', 'PleaseDoNotAddAnotherBoss.',
    'The architecture is now extremely flexible.', 'Unfortunately, nothing compiles.',
    "I'm beginning to suspect that naming classes is not the same as programming."),
  P('Day 13 — Project Proposal',
    'I had a brilliant idea.', 'An open-world crime simulator set in a tiny pixel city.',
    'Players could steal bicycles, escape from security guards, and dramatically crash into trash cans.',
    'I called it Grand Theft Arcade.', 'I was very proud.',
    'Then we received a legal warning from a suspiciously large game company.',
    'Apparently, they were not impressed by my artistic vision.', 'Project status: Suspended.',
    'Current development budget: One sandwich.', "I'm keeping the city map anyway.", 'It took me three days to draw those roads.'),
  P('Day 18 — Unexpected Interruption',
    'Miao Meow fell asleep on my keyboard today.', 'Again.', 'I tried moving her.',
    'She looked at me like I had committed a terrible crime.', 'So I worked on the other computer instead.',
    'I should probably buy her a softer bed.', "Also, we're almost out of her favorite canned food.",
    'Reminder:', 'Buy cat food before buying another GPU.', 'This is becoming a serious budgeting problem.'),
  P('Day 26 — 02:43 AM',
    'The prototype finally runs.', 'No crashes.', 'No missing textures.', 'No mysterious objects flying across the screen.',
    'For the first time, everything works.', 'I almost woke everyone up to celebrate.',
    'Instead, I made instant noodles and watched the title screen for a while.', 'Miao Meow was asleep beside the monitor.',
    'I think this might actually become something wonderful.', 'I should remember this night.'),
  P('Day 31 — Personal Note',
    "I've been spending too much time fixing machines.", 'Sometimes I forget why I started building games in the first place.',
    "It wasn't about making the fastest computer or writing the cleverest code.",
    'I just wanted to create somewhere people could have fun.', 'Somewhere they could forget their worries for a little while.',
    'Miao Meow is sleeping on my chair again.', 'I suppose she already understands the idea better than I do.',
    'Anyway.', "Tomorrow's tasks:", 'Fix the audio driver.', 'Test the new arcade cabinet.', 'Buy canned food.', 'And maybe get some sleep.'),
 ),(
  ('This looks like an abandoned experiment log.','The pages are filled with circuit diagrams, strange calculations, and coffee stains.','Someone must have spent a lot of time working here.'),
  ("The handwriting is messy... but strangely familiar.","I wonder how many of these coffee rings were part of the experiment."),
  ("There are little paw prints between the calculations.","Someone had a very demanding lab partner."),
 )),
 'repair_log':Document('ARCADE REPAIR LOG','repair',(
  P('REPAIR LOG — CABINET 01',
    'Steering controller malfunction.', 'The car turns left when the player presses right.',
    'It also turns left when the player presses nothing.', 'I suspect the cabinet has developed a personal preference.', 'Replacement parts ordered.'),
  P('REPAIR LOG — CABINET 02',
    'Attack button B is stuck.', 'One tester managed to defeat the entire game using a single punch.',
    'He described the experience as "surprisingly relaxing."', 'I may have accidentally invented an accessibility feature.'),
  P('REPAIR LOG — CABINET 03',
    'Cooling fan failure.', 'GPU temperature reached a number I would prefer not to write down.', 'I installed a bigger fan.',
    'The machine now sounds like a departing airplane.', 'Performance improved by 4%.', 'Noise increased by approximately 900%.'),
  P('WEEKLY MAINTENANCE SUMMARY',
    'Machines repaired: 2', 'Machines accidentally damaged: 3', 'New problems discovered: 11', 'Coffee consumed: Too much',
    "Miao Meow's professional assessment: Meow.", "I think we're making progress."),
 ),(
  ("This maintenance station has an old repair log.","The totals at the bottom look slightly worrying."),
  ("Someone kept careful records of every repair.","And every repair that needed another repair."),
  ("There's a weekly inspection summary here.","Apparently, the cat was the most qualified inspector."),
 )),
 'studio_todo':Document("KEVIN'S PERSONAL TO-DO LIST",'checklist',(
  P('Monday',
    '[ ] Replace broken monitor','[ ] Fix memory leak','[ ] Review the new game architecture','[x] Feed Miao Meow',
    '[ ] Buy groceries','[ ] Sleep before sunrise','I completed the most important task.'),
  P('Wednesday',
    "[x] Clean Miao Meow's bed",'[x] Buy her favorite canned food','[ ] Fix the arcade power system',
    '[ ] Finish the prototype','[ ] Stop adding unnecessary features','I added three new features today.','None of them were necessary.'),
  P('Friday',
    '[ ] Finish the next build','[ ] Organize the workshop','[ ] Call the team','[ ] Buy a new keyboard',
    '[x] Make sure Miao Meow is comfortable', "I wonder if she'll remember this place when she's older.",
    'Maybe I should build something that remembers it for her.'),
 ),(
  ("Someone left a small clipboard beside the workbench.","The cat food is checked off. Of course."),
  ("This to-do list has several different dates.","The unfinished jobs seem to be following him through the week."),
  ("One task is checked off more carefully than the others.","I think I know who came first around here."),
 )),
 'project_file':Document('ABANDONED GAME PROJECT FILE','digital',(
  P('PROJECT: GRAND THEFT ARCADE',
    'An open-world action game featuring an enormous city.', 'Current city size: Three streets.',
    'Playable vehicles: One bicycle and a suspiciously fast shopping cart.', 'Current NPC count: Four.', 'One of them keeps walking into a wall.'),
  P('Technical Architecture',
    'I designed an event-driven system with reusable game objects.', 'The class diagram looks beautiful.',
    'The actual implementation is held together by inheritance, questionable assumptions, and fear.',
    'I have named the most dangerous function:', 'please_work()', 'It has not worked yet.'),
  P('Legal Department',
    'Received a letter today.', 'Apparently, naming the game Grand Theft Arcade was a terrible idea.',
    'I explained that our game contains significantly fewer crimes and substantially more cats.',
    'The legal department did not respond to this argument.', 'Project status: ON HOLD.'),
  P('A New Idea',
    'Perhaps I should make something smaller.', 'Something cheerful.', 'Racing games.', 'Volleyball.', 'Puzzles.', 'Maybe a little maze adventure.',
    'A place where all these games can exist together.', 'That actually sounds much better.', "I think I'll start sketching it tomorrow."),
 ),(
  ('These must be the original development records.',"There's a folder marked Grand Theft Arcade."),
  ("Someone left a project file on this old computer.","The city map is... surprisingly compact."),
  ("This folder never made it into a finished game.","I wonder what its developer built instead."),
 )),
}

def page_lines(page,width=44,rows=16):
    # A consistent paragraph rhythm is more important than forcing a full logical
    # page into one viewport. Long pages scroll without changing X/Y.
    lines=[]
    for text in page.paragraphs:
        if lines:lines.append('')
        lines.extend(textwrap.wrap(ascii_text(text),width,break_long_words=False,break_on_hyphens=False) or [''])
    return tuple(lines)
