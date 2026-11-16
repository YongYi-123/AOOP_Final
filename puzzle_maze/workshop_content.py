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
