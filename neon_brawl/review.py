"""Reproducible rendered review sheets; no saves or live playthrough claims.
PYTHONPATH=arcade_lobby:. .venv/bin/python -m neon_brawl.review --output /tmp/neon-brawl-review
"""
import argparse
from pathlib import Path
import time
import pygame
from .game import BrawlGame
from .model import Campaign
from .art import sprite
from .outfits import OUTFITS

def generate(output):
    from font import get_font
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    pygame.init(); font=get_font(); game=BrawlGame(font)
    image=pygame.Surface((400,300))
    sheet=pygame.Surface((800,900))
    for i,t in enumerate((.4,2.2,3.5,5.4,6.8,8.8)):
        game.screen_time=t; game.draw(image); sheet.blit(image,((i%2)*400,(i//2)*300))
    pygame.image.save(sheet,output/'intro.png')
    sheet=pygame.Surface((1600,900))
    frames=[]
    for stage in range(3):
        for section in range(4):
            c=Campaign('NOVA'); c.stage=stage; c.wave=section
            c.player.x=section*350+80; c.camera=section*350; c.spawn()
            game.campaign=c; game.screen='playing'; game.time=4.5
            game.draw(image); sheet.blit(image,(section*400,stage*300))
            frames.append(c)
    pygame.image.save(sheet,output/'districts.png')
    sheet=pygame.Surface((500,400)); sheet.fill((15,15,30))
    for row,(name,pool) in enumerate(OUTFITS.items()):
        for column,outfit in enumerate(pool):
            x,y=column*100,row*100
            sheet.blit(sprite(name,'walk',1,1,column),(x+18,y+5))
            sheet.blit(font.render(outfit.name.upper(),(205,220,235)),(x+3,y+76))
    pygame.image.save(pygame.transform.scale(sheet,(1000,800)),output/'outfits.png')
    sheet=pygame.Surface((500,180)); sheet.fill((15,15,30))
    for i,name in enumerate(('duelist','shield','elite','cyber','security','sniper','assassin','echo')):
        x,y=i%5*100,i//5*90
        sheet.blit(sprite(name,'idle',1,1,i),(x+18,y))
        sheet.blit(font.render(name.upper(),(205,220,235)),(x+3,y+70))
    pygame.image.save(pygame.transform.scale(sheet,(1000,360)),output/'operatives.png')
    sheet=pygame.Surface((500,270)); sheet.fill((15,15,30))
    for row,name in enumerate(('WARDEN','RELAY','NULL')):
        for col,state in enumerate(('idle','charge','phase','guard','defeated')):
            sheet.blit(sprite(name,state,1),(col*100+18,row*90))
            sheet.blit(font.render(state.upper(),(205,220,235)),(col*100+3,row*90+72))
    pygame.image.save(pygame.transform.scale(sheet,(1000,540)),output/'bosses.png')
    start=time.perf_counter()
    for i in range(240): game.campaign=frames[i%12]; game.time=i/60; game.draw(image)
    print(f'Review sheets: {output}; native render mean: {(time.perf_counter()-start)*1000/240:.2f} ms/frame (240 frames)')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',default='/tmp/neon-brawl-review')
    generate(parser.parse_args().output)
