"""Native-resolution text over integer-scaled pixel scenery, with readable bundled English fonts."""
from pathlib import Path
import pygame
from puzzle_maze import pixel_font

FONT_PATH = Path(__file__).parent / 'assets/fonts/DejaVuSans.ttf'
BOLD_FONT_PATH = FONT_PATH.with_name('DejaVuSans-Bold.ttf')

class NativeText:
    def __init__(self):
        self.commands=[]
        self.fonts={}
        self.rects=[]

    def clear(self):
        self.commands.clear()

    def queue(self,text,x,y,color,title=False,max_width=None):
        self.commands.append((str(text),x,y,color,24 if title else 11,max_width))

    def font(self,size,bold=False):
        key=(size,bold)
        if key not in self.fonts:
            path=BOLD_FONT_PATH if bold else FONT_PATH
            self.fonts[key]=pygame.font.Font(str(path) if path.exists() else None,size)
        return self.fonts[key]

    def present(self,target,origin,scale):
        self.rects=[]
        for text,x,y,color,base,max_width in self.commands:
            px=max(0,int(origin[0]+x*scale));py=max(0,int(origin[1]+y*scale))
            size=max(8,int(base*scale))
            font=self.font(size,base==24)
            width=max(1,target.get_width()-px-4)
            if max_width is not None:width=min(width,max(1,int(max_width*scale)))
            if base==24:
                while font.size(text)[0]>width and size>8:
                    size-=1;font=self.font(size,base==24)
            elif font.size(text)[0]>width:
                while text and font.size(text+'...')[0]>width:text=text[:-1]
                text+='...'
            img=pixel_font.render(text,size,color)
            while img.get_width()>width and len(text)>1:
                text=text[:-1];img=pixel_font.render(text,size,color)
            if img.get_height()>target.get_height():continue
            py=min(py,max(0,target.get_height()-img.get_height()))
            rect=img.get_rect(topleft=(px,py))
            target.blit(img,(px,py));self.rects.append(rect)
