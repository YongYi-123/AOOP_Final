"""Compact dark-neon adaptation of Golden Age's real typewriter dialogue."""
import pygame

def make_dialogue(lines,play_sound=None,context=None):
    import sys
    from pathlib import Path
    host=str(Path(__file__).resolve().parents[1]/'arcade_lobby')
    if host not in sys.path:sys.path.append(host)
    from story_dialogue import StoryDialogue,Line
    from ui import wrap_text,draw_text
    class WorkshopDialogue(StoryDialogue):
        # Native pixels, restrained neon and a compact speech panel.
        def _rows(self):
            return wrap_text(self.line.text,222)[:3]
        def draw(self,surf):
            box=self.box;r=pygame.draw
            r.rect(surf,(16,24,31),box,border_radius=3)
            r.rect(surf,(42,77,83),box.inflate(2,2),1,border_radius=3)
            r.line(surf,(104,182,177),box.topleft,(box.right-1,box.top))
            r.line(surf,(113,99,153),(box.left,box.bottom-1),(box.right-1,box.bottom-1))
            r.polygon(surf,(16,24,31),[(box.left+18,box.bottom-1),(box.left+25,box.bottom+5),(box.left+31,box.bottom-1)])
            r.lines(surf,(79,126,134),False,[(box.left+18,box.bottom),(box.left+25,box.bottom+5),(box.left+31,box.bottom)])
            face=self.speaker.face(self.line.mood,self.context)
            if face is not None:surf.blit(pygame.transform.scale(face,(24,24)),(box.x+5,box.y+17))
            draw_text(surf,self.speaker.name,(box.x+35,box.y+5),(132,193,188))
            remaining=int(self.shown)
            for i,row in enumerate(self._rows()):
                part=row[:max(0,remaining)];remaining-=len(row)+1
                if part:draw_text(surf,part,(box.x+35,box.y+18+i*9),(194,207,210))
            if self.done_typing:
                r.polygon(surf,(123,178,178),[(box.right-9,box.bottom-7),(box.right-4,box.bottom-7),(box.right-7,box.bottom-4)])
    dialogue=WorkshopDialogue([Line(*line) for line in lines],top=True,play_sound=play_sound,context=context)
    dialogue.box=pygame.Rect(24,8,272,50)
    return dialogue
