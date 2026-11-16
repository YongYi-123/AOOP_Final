"""Authored workshop responses. Paragraph wording follows the requested dialogue."""
from dataclasses import dataclass
import textwrap

@dataclass(frozen=True)
class Response:
    title:str
    paragraphs:tuple
    style:str='screen'

def R(title,*paragraphs,style='screen'):
    return Response(title,paragraphs,style)

RESPONSES={
 'store_aoop':(
  R("KEVIN'S DESIGN BOARD", "These sketches appear to be Kevin's early game architecture notes.", "Classes, memory layouts, object relationships... and a surprisingly detailed drawing of a cat.",style='board'),
  R('PROJECT: GRAND THEFT ARCADE', 'Kevin once planned an open-world crime simulator called Grand Theft Arcade.', 'The prototype featured three streets, two vehicles, and one extremely judgmental pigeon.', 'Development was suspended after a suspiciously large game company sent a very professionally worded legal warning.', "Kevin's final note reads: 'Maybe I should make a farming game instead.'",style='board'),
  R('UNFINISHED ARCHITECTURE','An ambitious object-oriented design covers half the board.','GameObject → Character → Player → LegendaryPlayer → Kevin.', 'Someone has crossed out the last two classes.', "Underneath, Kevin wrote: 'Inheritance is easy. Explaining it to Miao Meow is impossible.'",style='board'),
 ),
 'work_crt':(
  R('RETRO RACER — PROTOTYPE 01','The original racing cabinet is still here.','Its steering controller is broken, and half the display is missing.', "A maintenance tag reads: 'STEERING INPUT FAILURE — DO NOT TURN LEFT.'",style='paper'),
  R('AN UNFORTUNATE TEST DRIVE','According to the testing log, Kevin accidentally swapped the accelerator and brake inputs.','The test driver reached a maximum speed of three pixels per second.', "The incident report describes the experience as 'emotionally devastating.'"),
  R('A QUESTIONABLE HOTFIX','Someone attempted to repair the steering system using a paper clip and a rubber band.', "The repair log says: 'Works on my machine.'",'It does not work on this machine.'),
 ),
 'work_back':(
  R('PROJECT: STREET BRAWL','An unfinished fighting game prototype.', "The cabinet's attack buttons are worn down from repeated testing.", "A small repair tag reads: 'BUTTON B STUCK — POSSIBLY PERSONAL.'",style='paper'),
  R('BALANCE PATCH 0.0.1','The patch notes reveal that Kevin accidentally gave the weakest enemy 9,999 HP.','Every playtester lost.', "Kevin labeled the update: 'Increased difficulty for experienced players.'"),
  R('A DEVASTATING REVIEW','An old tester comment remains on the screen.', "'The enemies are fine. The developer is the final boss.'", "Kevin replied: 'Thank you for your constructive feedback.'"),
 ),
 'work_frozen':(
  R('CAT SIMULATOR 199X','A mysterious prototype built around a single cat.', "The screen displays a sleeping cat and a progress bar labeled 'Productivity.'",'The bar has not moved.'),
  R('UNEXPECTED GAMEPLAY','The original design required players to complete difficult missions.','During testing, Miao Meow walked across the keyboard and activated a hidden nap mechanic.','Kevin apparently decided the nap mechanic was better than the entire original game.'),
  R('DEVELOPMENT STATUS','PROJECT STATUS: 99% COMPLETE.','REMAINING TASK: Convince the cat to wake up.','Estimated completion date: Unknown.'),
 ),
 'work_space':(
  R('STARFALL ASSAULT — TEST UNIT','The cabinet is covered in scorch marks.', "A tiny maintenance label reads: 'POWER SUPPLY FAILURE — AGAIN.'"),
  R('THE FINAL FRONTIER','Kevin attempted to simulate ten thousand enemies on a computer with almost no memory.','The game achieved one frame every seven seconds.', "The development notes call this 'cinematic pacing.'"),
  R('PERFORMANCE REPORT','CPU: 100%','GPU: VERY CONCERNED','RAM: PLEASE STOP', "Kevin wrote: 'Optimization can wait until tomorrow.'"),
 ),
 'kevin_note':(
  R("KEVIN'S WORKBENCH",'The workbench is covered with circuit boards, controllers, spare parts, and half-finished repairs.','Despite the chaos, every tool seems to have its own designated place.',style='blueprint'),
  R('DEBUGGING PHILOSOPHY','A small engineering log is still open.', "'Fixed one bug today.'", "'Discovered eleven new bugs.'", "'Overall progress: emotionally complicated.'",style='blueprint'),
  R('THE REAL SUPERVISOR','Several tiny paw prints cross the corner of a circuit diagram.', "A handwritten note reads: 'Miao Meow has reviewed the design.'", "'Approval status: MEOW.'",style='blueprint'),
 ),
 'lab_terminal':(
  R('DEVELOPMENT TERMINAL','The screen still displays an old diagnostic program.','BUILD STATUS: FAILED','ERROR: Unexpected cat input detected.'),
  R('COMPUTER ORGANIZATION NOTES','A performance test compares different processor configurations.','CPU: Operational','REGISTER FILE: Operational','CACHE: Missed everything','DEVELOPER: Also missed everything'),
  R('THE LAST COMPILATION','The terminal contains a final compilation message.', "'Build completed with 0 errors and 47 warnings.'", "Someone added: 'Warnings are just suggestions from an overly dramatic compiler.'"),
 ),
 'studio_todo':(
  R("KEVIN'S TO-DO LIST", "09:00 — Repair arcade cabinet #3.", '11:00 — Test the new graphics engine.', "14:00 — Buy Miao Meow's favorite canned food.", '17:00 — Remember to eat something myself.',style='paper'),
  R('AN UPDATED PRIORITY LIST','1. Feed Miao Meow.', "2. Clean Miao Meow's bed.", "3. Fix the arcade's catastrophic power failure.", '4. Maybe take a break.','Someone has drawn a large star beside the first item.',style='paper'),
  R('A SMALL PROMISE','One final note is written in smaller handwriting.', "'If the workshop ever gets too loud, I'll make a quiet place just for you.'", "There's a tiny paw print beside the sentence.",style='paper'),
 ),
 'studio_cushion':(
  R("MIAO MEOW'S CORNER",'A small cat bed sits beside the engineering equipment.','It looks much more carefully maintained than the surrounding machinery.'),
  R('A VERY IMPORTANT EMPLOYEE','A tiny homemade nameplate reads:', "'MIAO MEOW — CHIEF QUALITY INSPECTOR.'",'Responsibilities: Sleeping, supervising, and occasionally disconnecting cables.'),
  R('HOME, SOMEHOW','Everything else in this room looks abandoned.','But someone once made sure this little corner was warm and safe.'),
 ),
 'power_cabinet':(
  R('MAIN POWER DISTRIBUTION','The old electrical cabinet is damaged.','Several cables are disconnected, and a warning light flickers weakly.'),
  R('INCIDENT REPORT','CAUSE: Unauthorized modification.','RESPONSIBLE PERSON: Kevin.', "Kevin's response: 'In my defense, it looked much easier in the tutorial.'"),
  R('SAFETY INSPECTION','An inspection checklist remains attached to the cabinet.','Electrical safety: FAILED.','Fire safety: FAILED.','Cat safety: PASSED.','The last result has been circled three times.'),
 ),
 'work_prototype':(
  R('ORIGINAL ARCADE CONTROL SYSTEM','The prototype terminal flickers to life.','An unfamiliar directory appears on the screen.','/ARCADE/ORIGINAL_BUILD/','A damaged recording begins to play.'),
  R('SYSTEM DIAGNOSTICS','Several connections lead to machines scattered throughout Neon Corner Arcade.','Some are offline.','Others appear to be waiting for something.'),
  R('A FAMILIAR SIGNATURE','A tiny cat-shaped symbol appears in the corner of the display.','Someone added it to the original system interface.','No documentation explains why.'),
 ),
}

# Trial 01 owns the actual Memory Fragment reward. This local recording neither
# grants an item nor dispatches a trial event or reveals the protagonist's identity.
RECORDING=(
 ('SYSTEM','The prototype terminal flickers to life.'),
 ('SYSTEM','An unfamiliar directory appears on the screen.'),
 ('SYSTEM','/ARCADE/ORIGINAL_BUILD/'),
 ('SYSTEM','A damaged recording begins to play.'),
 ('KEVIN — RECORDED MESSAGE',"If you're seeing this, then the old system still remembers."),
 ('KEVIN — RECORDED MESSAGE','I built these machines so people could have somewhere to laugh, compete, and forget about the world for a little while.'),
 ('KEVIN — RECORDED MESSAGE','I never expected the Arcade to become something bigger.'),
 ('SYSTEM','The recording suddenly cuts out.'),
 ('SYSTEM','ORIGINAL BUILD DETECTED.'),
 ('SYSTEM','LOCAL RECORDING RESTORED.'),
 ('SYSTEM','ACCESS LEVEL: INCOMPLETE.'),
)

def ascii_text(text):
    return text.translate(str.maketrans({'—':'-','→':'->','’':"'",'“':'"','”':'"'}))

def paginate(response,width=42,rows=8):
    lines=[]
    for paragraph in response.paragraphs:
        if lines:lines.append('')
        lines.extend(textwrap.wrap(ascii_text(paragraph),width,break_long_words=False,break_on_hyphens=False) or [''])
    pages=[]
    while lines:
        page=lines[:rows];lines=lines[rows:]
        while page and not page[-1]:page.pop()
        while lines and not lines[0]:lines.pop(0)
        pages.append(tuple(page))
    return tuple(pages) or (('',),)

def response_for(content,index=0):
    if content in RESPONSES:return RESPONSES[content][index%len(RESPONSES[content])]
    from puzzle_maze.secret45 import LORE
    title,lines=LORE[content]
    return R(title,' '.join(lines),style='paper' if content=='kevin_photo' else 'screen')

# Brief object discoveries are spoken by the protagonist. These longer records
# have real written contents; the latest brief asks for Kevin's first-person voice.
WRITTEN_RECORDS={
 ('store_aoop',1):(
  'I once planned an open-world crime simulator called Grand Theft Arcade.',
  'My prototype featured three streets, two vehicles, and one extremely judgmental pigeon.',
  'I suspended development after a suspiciously large game company sent a very professionally worded legal warning.',
  'Maybe I should make a farming game instead.',
 ),
 ('store_aoop',2):(
  'I covered half the board with an ambitious object-oriented design.',
  'GameObject → Character → Player → LegendaryPlayer → Kevin.',
  'I crossed out the last two classes.',
  'Inheritance is easy. Explaining it to Miao Meow is impossible.',
 ),
 ('work_crt',1):(
  'I accidentally swapped the accelerator and brake inputs.',
  'My test driver reached a maximum speed of three pixels per second.',
  'I filed the incident under: emotionally devastating.',
 ),
 ('work_crt',2):(
  'I tried repairing the steering system with a paper clip and a rubber band.',
  'I wrote: Works on my machine.',
  'It does not work on this machine.',
 ),
 ('work_back',1):(
  'I accidentally gave my weakest enemy 9,999 HP.',
  'Every playtester lost.',
  'I labeled my update: Increased difficulty for experienced players.',
 ),
 ('work_frozen',1):(
  'I originally designed difficult missions for this prototype.',
  'During testing, Miao Meow walked across my keyboard and activated a hidden nap mechanic.',
  'I decided her nap mechanic was better than my entire original game.',
 ),
 ('work_space',1):(
  'I tried simulating ten thousand enemies on a computer with almost no memory.',
  'My game achieved one frame every seven seconds.',
  'I am calling this cinematic pacing.',
 ),
 ('lab_terminal',1):(
  'I compared different processor configurations.',
  'CPU: Operational','REGISTER FILE: Operational','CACHE: Missed everything',
  'DEVELOPER: Also missed everything',
 ),
 ('lab_terminal',2):(
  'I saved my final compilation message.',
  'Build completed with 0 errors and 47 warnings.',
  'Warnings are just suggestions from an overly dramatic compiler.',
 ),
 ('power_cabinet',1):(
  'CAUSE: Unauthorized modification.','RESPONSIBLE PERSON: Kevin.',
  'In my defense, it looked much easier in the tutorial.',
 ),
 ('power_cabinet',2):(
  'I left my inspection checklist attached to the cabinet.',
  'Electrical safety: FAILED.','Fire safety: FAILED.','Cat safety: PASSED.',
  'I circled the last result three times.',
 ),
}

RECORD_OBSERVATIONS={
 ('store_aoop',1):("There's an abandoned game proposal on this board.","Three streets and a pigeon. Ambitious."),
 ('store_aoop',2):("Someone crossed out the last two classes in this diagram.","I'll read the explanation before judging."),
 ('work_crt',1):("This cabinet still has its testing log.","The test drive seems to have gone very slowly."),
 ('work_crt',2):("There's a steering repair report here.","That really is a paper clip."),
 ('work_back',1):("There's a balance patch in the testing menu.","I wonder what changed."),
 ('work_frozen',1):("The test notes mention Miao Meow.","That probably explains the nap."),
 ('work_space',1):("A performance log is still open.","Those frame timestamps are very far apart."),
 ('lab_terminal',1):("There's a processor benchmark here.","Even the developer has a status line."),
 ('lab_terminal',2):("This must be the last compilation.","Forty-seven warnings... optimistic."),
 ('power_cabinet',1):("There's an incident report in the maintenance display.",),
 ('power_cabinet',2):("Someone recorded a safety inspection.","One result has been circled very enthusiastically."),
}

def written_response(content,index):
    response=response_for(content,index)
    return Response(response.title,WRITTEN_RECORDS[(content,index)],'paper')

SPOKEN_DETAILS={
 'kevin_photo':("Someone wrote on the back of this photograph:","'I asked Miao to pose. She inspected my soldering. I kept the blurry photo. Best review I got all week.'"),
 'lab_gpu':('Twin fans, worn contacts, and a very determined repair.','Whoever kept this card alive really wanted one more build.'),
 'lab_keyboard':('The label says: NO CATS ON KEYS.','The paw prints suggest the cat had final approval.'),
 'lab_duck':('A rubber duck with a tiny staff badge.','I suppose silence counts as excellent code review.'),
 'lab_coffee':('That coffee looks older than this entire build.',"The computer is still warm. The mug definitely isn't."),
 'studio_food':('Three little cans, all lined up by flavour.',"The labels say they're Miao's favourites.",'Someone clearly took feeding time very seriously.'),
 'store_tools':('The 10 mm socket has its own empty compartment.','An impression in the dust suggests Miao borrowed the whole drawer.'),
 'store_parts':('Three painted categories: tested, broken, and only works when watched.',"I don't think I trust that third box."),
 'store_timebox':('The box is marked BUGS.','Something inside just sneezed.',"I'm going to assume that was a sound effect."),
 'store_server':('Two fans, each aimed at the other.',"The server isn't even plugged in.","At least they've got each other."),
 'store_breadboard':('An old breadboard, a multimeter, and... a sandwich?',"I can't tell which part was the experiment."),
 'store_cables':('This was probably a straight cable once.',"Now it's a very ambitious knot.",'Miao seems to consider it a pillow.'),
}
