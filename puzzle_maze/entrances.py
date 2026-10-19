"""Original, functional entrance art; visibility shares transition conditions."""
import pygame
from puzzle_maze.icons import BossKeyIcon


def entrance_visible(session, exit):
    if exit.get('flag_requires') and not set(exit['flag_requires']) <= session.inventory.flags:return False
    if exit.get('entrance') == 'remote':
        return set(exit.get('flag_requires', [])) <= session.inventory.flags
    return all(session.puzzles.condition(i) for i in exit.get('requires',[]) if session.puzzles.objects[i].data['type'] in ('secret','cracked'))


def draw_entrance(surface, session, exit, sx, sy, wall_tile):
    draw = pygame.draw
    kind = exit.get('entrance', 'stairs_down' if exit.get('stairs') else 'stone')
    discovered = exit['target'] in session.visited
    if exit.get('transformed') and not entrance_visible(session,exit):return
    if kind == 'walkthrough' and not discovered or not entrance_visible(session, exit):
        surface.blit(wall_tile, (sx, sy))
        draw.line(surface, (95, 103, 102), (sx+5, sy+14), (sx+11, sy+14))
        return
    stone = (121, 130, 139)
    edge = (177, 166, 135)
    if kind=='boss_gate':
        gate=next((session.puzzles.objects[i] for i in exit.get('requires',[]) if session.puzzles.objects[i].data.get('key')=='boss'),None)
        opened=all(session.puzzles.condition(i) for i in exit.get('requires',[]))
        opening=getattr(gate,'opening',0.)
        progress=1-opening/gate.data.get('opening_duration',.6) if opening and gate else 1 if opened else 0
        draw.rect(surface,(68,62,81),(sx-4,sy-7,24,24),border_radius=3)
        draw.rect(surface,(211,177,104),(sx-3,sy-6,22,22),1)
        draw.rect(surface,(15,21,32),(sx,sy-3,16,19))
        for sign in (-1,1):
            draw.rect(surface,(118,109,126),(sx+8+(0 if sign>0 else -8)+int(sign*progress*9),sy-3,8,19))
        if not opened:surface.blit(BossKeyIcon.surface(),(sx,sy-1-int(progress*8)))
        return
    if kind.startswith('stairs'):
        draw.rect(surface, (16, 22, 35), (sx+1, sy+1, 14, 14))
        for step in range(4):
            width = 12-step*2 if kind == 'stairs_down' else 6+step*2
            x = sx+8-width//2
            draw.rect(surface, (78+step*23, 88+step*21, 108+step*18), (x, sy+2+step*3, width, 2))
        draw.line(surface, edge, (sx+1, sy+1), (sx+1, sy+14))
        draw.line(surface, edge, (sx+14, sy+1), (sx+14, sy+14))
        return
    if exit.get('portal'):
        draw.circle(surface,(152,102,230),(sx+8,sy+8),7,2)
        draw.circle(surface,(67,172,183),(sx+8,sy+8),4,1)
        return
    draw.ellipse(surface, (16, 22, 32), (sx+1, sy+11, 14, 5))
    draw.rect(surface, stone, (sx+1, sy+3, 14, 11))
    draw.rect(surface, stone, (sx+3, sy+1, 10, 4))
    draw.rect(surface, (14, 19, 29), (sx+4, sy+4, 8, 10))
    draw.line(surface, edge, (sx+3, sy+3), (sx+12, sy+3))
    draw.line(surface, edge, (sx+2, sy+5), (sx+2, sy+13))
    if kind == 'cave':
        draw.rect(surface, (76, 87, 84), (sx+1, sy+6, 3, 3))
        draw.rect(surface, (87, 95, 91), (sx+11, sy+4, 4, 4))
    elif kind in ('locked', 'boss_gate'):
        opened = all(session.puzzles.condition(i) for i in exit.get('requires', []))
        if not opened:
            for x in (5, 8, 11):
                draw.line(surface, (153, 117, 79), (sx+x, sy+5), (sx+x, sy+13))
            draw.rect(surface, (223, 180, 94), (sx+6, sy+8, 4, 4))
            draw.rect(surface, (23, 28, 38), (sx+8, sy+9, 1, 2))
        if kind == 'boss_gate':
            draw.rect(surface, (137, 83, 171), (sx+6, sy, 4, 3))
    elif 'library' in session.rooms.data.get('theme', ''):
        draw.rect(surface, (125, 86, 57), (sx+2, sy+3, 2, 11))
        draw.rect(surface, (169, 118, 70), (sx+12, sy+3, 2, 11))
