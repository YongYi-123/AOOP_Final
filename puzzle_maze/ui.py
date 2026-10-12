"""Native-resolution text over integer-scaled pixel scenery, including CJK."""
from pathlib import Path
import pygame

FONT_PATH = Path(__file__).parent / 'assets/fonts/NotoSansCJKtc-Regular.otf'

class NativeText:
    def __init__(self):
        self.commands=[]
        self.fonts={}
        self.rects=[]

    def clear(self):
        self.commands.clear()

    def queue(self,text,x,y,color,title=False):
        self.commands.append((str(text),x,y,color,24 if title else 10))

    def font(self,size):
        if size not in self.fonts:
            self.fonts[size]=pygame.font.Font(str(FONT_PATH) if FONT_PATH.exists() else None,size)
        return self.fonts[size]

    def present(self,target,origin,scale):
        self.rects=[]
        for text,x,y,color,base in self.commands:
            px=max(0,int(origin[0]+x*scale));py=max(0,int(origin[1]+y*scale))
            size=max(8,int(base*scale))
            font=self.font(size)
            width=max(1,target.get_width()-px-4)
            if base==24:
                while font.size(text)[0]>width and size>8:
                    size-=1;font=self.font(size)
            elif font.size(text)[0]>width:
                while text and font.size(text+'…')[0]>width:text=text[:-1]
                text+='…'
            img=font.render(text,False,color)
            if img.get_height()>target.get_height():continue
            py=min(py,max(0,target.get_height()-img.get_height()))
            rect=img.get_rect(topleft=(px,py)).clip(target.get_rect())
            target.blit(img,(px,py));self.rects.append(rect)
