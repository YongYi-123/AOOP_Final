"""Presentation-only onboarding: enemies and puzzle clocks stay frozen."""
import math
import pygame

DEFAULT_CONTROLS=dict(move='WASD / ARROWS',attack='J',interact='E',ability='SPACE',tool='Q',dash='SHIFT',pull='F',heal='H',map='TAB',reset='R',pause='ESC',confirm='ENTER',pages='LEFT / RIGHT')

class IntroSequence:
    duration=6.0
    caption_top=170
    def __init__(self):self.elapsed=0

    def update(self,dt):
        self.elapsed=min(self.duration,self.elapsed+max(0,dt))
        return self.elapsed>=self.duration

    @property
    def actor_position(self):
        progress=self.elapsed/self.duration
        return 9.5,8.5-min(1,max(0,(progress-.6)/.4))*2

    def draw(self,renderer,confirm='ENTER',pages='LEFT / RIGHT'):
        from puzzle_maze.render import INK,GOLD,TEAL,WHITE
        s=renderer.surface;r=pygame.draw;renderer.ui.clear();s.fill(INK)
        progress=self.elapsed/self.duration
        for y in range(4,14):
            for x in range(4,16):s.blit(renderer.tiles['.'],(x*16,y*16))
        for x in range(4,16):
            s.blit(renderer.tiles['#'],(x*16,4*16));s.blit(renderer.tiles['#'],(x*16,5*16))
        r.rect(s,(25,39,47),(8*16,4*16,4*16,2*16))
        opening=int(max(0,min(1,(progress-.35)/.5))*29)
        for x in (128-opening,158+opening):
            r.rect(s,(100,113,109),(x,64,28,32));r.rect(s,GOLD,(x+3,67,22,26),1)
        r.rect(s,TEAL,(157,68,5,25))
        px,py=self.actor_position
        renderer.player((px,py),(0,-1),progress>.6,0,0)
        if .2<progress<.65:
            angle=-math.pi/2+.6*math.sin(progress*9)
            origin=(160,int(py*16+8))
            r.line(s,WHITE,origin,(int(origin[0]+math.cos(angle)*23),int(origin[1]+math.sin(angle)*23)),3)
            r.circle(s,GOLD,origin,2)
        renderer.text('PUZZLE MAZE',35,16,GOLD,renderer.title,max_width=248)
        r.rect(s,INK,(12,self.caption_top,296,60));r.rect(s,(68,99,112),(12,self.caption_top,296,60),1)
        renderer.text('Basic Sword equipped',24,178,WHITE)
        renderer.text('The dungeon gate is opening.',24,195,TEAL)
        renderer.text(f'{confirm}: skip | ESC: menu',24,213,GOLD)

class TutorialCard:
    def __init__(self,controls=None):
        self.controls=dict(DEFAULT_CONTROLS if controls is None else controls);self.bombs=True;self.advanced=False;self.page=0

    def lines(self,begin=False):
        c=self.controls
        if self.advanced:
            if self.page==0:return [f'Move: {c["move"]}',f'{c["attack"]} Sword / {c["interact"]} Use / B Bomb',f'P Dust / {c["interact"]} Lift, Drop',f'G Throw / {c["attack"]} Crystal',f'{c["ability"]} Tool / Q Next / F Pull',f'{c["dash"]} Dash / H Heal',f'{c["pages"]} / {c["confirm"]} {"Begin" if begin else "Return"}']
            return ['TAB Map / R Reset','ESC Pause / H Heal','Powder reveals ghost foes','Pots break hunters and weigh','Crystal changes both floors','Read fire and enemy glyphs',f'{c["pages"]} / {c["confirm"]} {"Begin" if begin else "Return"}']
        return [f"Move: {c['move']}",
                f"{c['attack']} Sword / {c['interact']} Use"+(" / B Bomb" if self.bombs else ""),
                f"{c['ability']} Tool / {c['tool']} Next / {c['pull']} Pull",
                f"{c['dash']} Dash (boots) / {c['heal']} Heal",
                f"{c['map']} Map / {c['reset']} Reset",
                f"{c['pause']} Pause / Sword ready",
                f"{c['confirm']} {'Begin' if begin else 'Return'} / ESC {'Menu' if begin else 'Return'}"]

    def draw(self,renderer):renderer.panel('HOW TO PLAY',self.lines(True))
