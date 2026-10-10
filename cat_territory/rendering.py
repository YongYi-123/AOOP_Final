"""Neon colored territories and tiny original tuxedo cats."""
import pygame
from arcade_lobby.font import get_font
from cat_minesweeper.rendering import MineGridLayout
from .model import DIFFICULTIES,BoardState

PALETTE=((68,133,163),(156,73,117),(88,148,98),(141,100,174),(169,126,63),
         (67,143,142),(155,82,67),(104,109,177),(145,139,70),(135,83,142))


class TerritoryGridLayout(MineGridLayout):
    def __init__(self,size):
        super().__init__(size)
        self.rect.y=64


class TerritoryRenderer:
    def __init__(self):
        self.font=get_font()

    def text(self,surface,text,center,color=(90,240,255),scale=1):
        image=self.font.render_glow(text,color,(30,15,45),scale)
        surface.blit(image,image.get_rect(center=center))

    @staticmethod
    def cat(surface,center,blink=False):
        x,y=center
        pygame.draw.rect(surface,(240,240,245),(x-6,y-4,12,10))
        pygame.draw.rect(surface,(30,30,40),(x-6,y-4,6,5))
        pygame.draw.polygon(surface,(30,30,40),[(x-6,y-3),(x-6,y-8),(x-1,y-3)])
        pygame.draw.polygon(surface,(30,30,40),[(x+6,y-3),(x+6,y-8),(x+1,y-3)])
        for dx in (-3,3):
            pygame.draw.rect(surface,(100,210,175),(x+dx,y-1,2,1 if blink else 2))
        surface.fill((255,135,170),(x,y+2,2,2))

    def draw(self,surface,game):
        surface.fill((12,7,30))
        for y in range(0,300,8):
            surface.fill((20+y//30,10,40+y//20),(0,y,400,3))
        self.text(surface,'CAT TERRITORY',(200,16),(255,110,210),2)
        if game.selecting:
            for i,difficulty in enumerate(DIFFICULTIES):
                rect=pygame.Rect(65,55+i*44,270,36)
                pygame.draw.rect(surface,(35,25,60),rect)
                pygame.draw.rect(surface,(255,224,90) if i==game.difficulty_index else (100,70,135),rect,2)
                self.text(surface,difficulty.name,rect.center,scale=2)
            for i,line in enumerate(('ONE CAT PER COLOR, ROW AND COLUMN','CATS CANNOT TOUCH, EVEN DIAGONALLY',
                                     'CLICK: X   DOUBLE CLICK: CAT','UP/DOWN SELECT  E/ENTER PLAY')):
                self.text(surface,line,(200,201+i*22))
            return
        board=game.board
        for i in range(3):
            x=21+i*15
            color=(255,110,155) if i<board.hearts else (60,40,65)
            pygame.draw.polygon(surface,color,[(x,39),(x-5,34),(x-5,29),(x,27),(x+3,30),
                                              (x+6,27),(x+11,29),(x+11,34),(x+3,42)])
        self.text(surface,f'{board.difficulty.name}  {len(board.cats)}/{board.size}',(200,36))
        self.text(surface,f'TIME {int(board.elapsed)}',(350,36))
        self.text(surface,f'SCORE {board.score}',(200,51),(255,224,90))
        for y,row in enumerate(board.regions):
            for x,color in enumerate(row):
                rect=game.layout.cell_rect(x,y).inflate(-1,-1)
                pygame.draw.rect(surface,PALETTE[color],rect)
                # Region borders and numeric tags supplement the color palette.
                for dx,dy,edge in ((-1,0,'left'),(1,0,'right'),(0,-1,'top'),(0,1,'bottom')):
                    nx,ny=x+dx,y+dy
                    if not board.contains(nx,ny) or board.regions[ny][nx]!=color:
                        if edge in ('left','right'):
                            px=rect.left if edge=='left' else rect.right-1
                            pygame.draw.line(surface,(20,15,35),(px,rect.top),(px,rect.bottom),2)
                        else:
                            py=rect.top if edge=='top' else rect.bottom-1
                            pygame.draw.line(surface,(20,15,35),(rect.left,py),(rect.right,py),2)
                if (x,y) in board.cats:
                    self.cat(surface,rect.center,int(game.time*2)%9==8)
                elif (x,y) in board.marks:
                    pygame.draw.line(surface,(230,220,240),rect.topleft,rect.bottomright,2)
                    pygame.draw.line(surface,(230,220,240),rect.topright,rect.bottomleft,2)
                else:
                    self.text(surface,str(color+1),rect.center,(185,185,210))
                if (x,y)==game.cursor:
                    pygame.draw.rect(surface,(255,224,90),rect,1)
                if game.error_left>0 and (x,y)==board.error_cell:
                    pygame.draw.rect(surface,(255,60,90),rect,3)
        self.text(surface,'CLICK X / DOUBLE CAT   ARROWS MOVE   E CAT',(200,282))
        self.text(surface,'SPACE X   MENU PAUSE   BACKSPACE LEVEL   ESC LOBBY',(200,295))
        if game.paused or board.outcome:
            pygame.draw.rect(surface,(15,10,35),(30,110,340,75))
            pygame.draw.rect(surface,(255,110,210),(30,110,340,75),2)
            title='CAT NAP - PAUSED' if game.paused else 'PURRFECT TERRITORY!' if board.state is BoardState.WON else 'NO HEARTS LEFT!'
            self.text(surface,title,(200,130),(255,224,90),2)
            self.text(surface,'E/ENTER RESUME' if game.paused else 'E/ENTER REPLAY  BACKSPACE LEVEL',(200,162))
