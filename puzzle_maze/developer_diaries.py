"""Optional studio humor: production mishaps, not the Golden Age's college archive."""
DIARIES={
 'dev_001':('DEV LOG 001 / PAC-MAN TEST',('I built a Pac-Man test.','Every ghost chose one door.','They queued very politely.','My cat ate all the dots.')),
 'dev_002':('DEV LOG 002 / MY AI AGENT',('I asked my agent for a fix.','It asked for a clear spec.','I asked it to stop arguing.','It opened a second issue.')),
 'dev_003':('DEV LOG 003 / REVERSE GEAR',('I tested my reverse gear.','The car drove into the past.','My agent called it a race.','I called it a late backup.')),
 'dev_004':('DEV LOG 004 / BRICK PHYSICS',('I fixed one bouncing ball.','It escaped through a brick.','My agent blamed the brick.','I had to debug both of them.')),
 'dev_005':('DEV LOG 005 / CODE REVIEW',('I let a duck review my code.','It found nothing to say.','I promoted it over my agent.','Now my agent wants a pond.')),
 'dev_006':('DEV LOG 006 / NIGHT BUILD',('I tuned my brawler tonight.','One punch launched a chair.','Miao liked the flying chair.','I kept that part of the bug.')),
 'dev_007':('DEV LOG 007 / SAFE EXITS',('I built a secret maze room.','My agent removed the exit.','It called this immersion.','I put the door back myself.')),
 'lab_duck':('SENIOR DEBUG CONSULTANT',('I hired this rubber duck.','It listens before replying.','My agent calls it cheating.','I call it senior experience.')),
 'lab_coffee':('COMPILING...',('I brewed this for a build.','The build is still running.','My coffee has gone cold.','I may need to compile lunch.')),
 'lab_button':('RED BUTTON / TEST ONLY',('I wired a dramatic button.','It only prints HELLO.','My agent added a countdown.','I unplugged the loudspeaker.')),
}

# Extra pages are Kevin's own test records, not narration about him.
DIARY_PAGES={
 'dev_001':(
  DIARIES['dev_001'][1],
  ('I gave the bots three jobs:','patrol, chase, and ambush.','My ambusher waited ahead.','I forgot to draw its door.'),
  ('I made frightened bots flee.','One fled into my test rig.','My agent called it brave.','I called it a bug.'),
 ),
 'dev_002':(
  DIARIES['dev_002'][1],
  ('I wrote: FIX ONE THING.','It rewrote the entire game.','I asked for the old build.','It asked which FINAL folder.'),
  ('I restored my own backup.','The duck watched in silence.','I gave it a tiny badge.','My agent requested a badge.'),
 ),
 'dev_007':(
  DIARIES['dev_007'][1],
  ('I saved one tiny grey pixel.','It still knows the way back.','I left the test lead in.','Someone may finish this.'),
 ),
}

POSITIONS=((3,10),(6,12),(10,13),(13,13),(17,13),(20,13),(23,12),(13,7),(18,4),(19,8))

def add_interactions(dev):
    from puzzle_maze.build_dungeon import obj
    for key,pos in zip(DIARIES,POSITIONS):
        dev['objects'].append(obj('mystery_scroll',key,pos,optional=True,content_id=key))
