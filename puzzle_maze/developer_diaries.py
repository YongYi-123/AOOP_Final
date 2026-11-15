"""Optional studio humor: production mishaps, not the Golden Age's college archive."""
DIARIES={
 'dev_001':('DEV LOG 001 / FINAL FINAL',('Release folder: FINAL.','Backup folder: FINAL_REAL.','Actual build: a floppy','labeled DO NOT USE.')),
 'dev_002':('DEV LOG 002 / NETWORKING',('Connected the mini fridge','to the network.','It keeps sending packets.','All of them are cold.')),
 'dev_003':('DEV LOG 003 / CABLE LABELS',('Labeled every cable.','Both ends say THIS END.','Future me will understand.','Future me is furious.')),
 'dev_004':('DEV LOG 004 / PATCH NOTES',('Fixed a bug in the clock.','Tuesday now occurs twice.','This is a feature until','the next deadline.')),
 'dev_005':('DEV LOG 005 / QUALITY CHECK',('The rubber duck reviewed','my code without complaint.','Promoted it to lead.','It wants a bigger pond.')),
 'dev_006':('DEV LOG 006 / KEYBOARDS',('One keyboard for coding.','One for games. One spare.','The other twelve are','emotional support.')),
 'dev_007':('DEV LOG 007 / SAVE SPACE',('Deleted a 4 MB file.','Bought a 4 MB drive.','Net storage gain: zero.','Excellent afternoon.')),
 'lab_duck':('SENIOR DEBUG CONSULTANT',('Senior Debug Consultant.','Employee of the Month.','Every month.','The duck remains humble.')),
 'lab_coffee':('COMPILING...',('The coffee is cold.','The computer is not.')),
 'lab_button':('RED BUTTON / TEST ONLY',('PLEASE STOP PRESSING THAT.','The monitor is blushing.','No files were harmed.')),
}
POSITIONS=((3,10),(6,12),(10,13),(13,13),(17,13),(20,13),(23,12),(13,7),(18,4),(19,8))

def add_interactions(dev):
    from puzzle_maze.build_dungeon import obj
    for key,pos in zip(DIARIES,POSITIONS):
        dev['objects'].append(obj('mystery_scroll',key,pos,optional=True,content_id=key))
