"""Presentation-only onboarding: enemies and puzzle clocks stay frozen."""
import math
import pygame

DEFAULT_CONTROLS=dict(move='WASD / ARROWS',attack='J',interact='E',ability='SPACE',tool='Q',dash='SHIFT',pull='F',heal='H',map='TAB',reset='R',pause='ESC',confirm='ENTER')

class IntroSequence:
    duration=6.0
    def __init__(self):self.elapsed=0

    def update(self,dt):
        self.elapsed=min(self.duration,self.elapsed+max(0,dt))
        return self.elapsed>=self.duration

    def draw(self,renderer):
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
        py=10.5-min(1,max(0,(progress-.6)/.4))*2
        renderer.player((9.5,py),(0,-1),progress>.6,0,0)
        if .2<progress<.65:
            angle=-math.pi/2+.6*math.sin(progress*9)
            origin=(160,int(py*16+8))
            r.line(s,WHITE,origin,(int(origin[0]+math.cos(angle)*23),int(origin[1]+math.sin(angle)*23)),3)
            r.circle(s,GOLD,origin,2)
        renderer.text('PUZZLE MAZE',35,16,GOLD,renderer.title,max_width=248)
        r.rect(s,INK,(12,170,296,60));r.rect(s,(68,99,112),(12,170,296,60),1)
        renderer.text('Basic Sword equipped',24,178,WHITE)
        renderer.text('The dungeon gate is opening.',24,195,TEAL)
        renderer.text('ENTER: skip animation',24,213,GOLD)

class TutorialCard:
    def __init__(self,controls=None):self.controls=dict(DEFAULT_CONTROLS if controls is None else controls)

    def lines(self,begin=False):
        c=self.controls
        return [f"Move: {c['move']}",
                f"Sword: {c['attack']} | Interact: {c['interact']}",
                f"Tool: {c['ability']} | Select: {c['tool']} | Pull: {c['pull']}",
                f"Dash: {c['dash']} (boots) | Heal: {c['heal']}",
                f"Map: {c['map']} | Reset room: {c['reset']}",
                f"Pause: {c['pause']} | Basic Sword ready",
                f"{c['confirm']}: {'begin' if begin else 'return'} | ESC: {'main menu' if begin else 'return'}"]

    def draw(self,renderer):renderer.panel('HOW TO PLAY',self.lines(True))
