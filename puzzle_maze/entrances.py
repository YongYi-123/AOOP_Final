"""Original, functional entrance art; visibility shares transition conditions."""
import pygame


def entrance_visible(session, exit):
    if exit.get('entrance') == 'remote':
        return set(exit.get('flag_requires', [])) <= session.inventory.flags
    return all(session.puzzles.condition(i) for i in exit.get('requires',[]) if session.puzzles.objects[i].data['type'] in ('secret','cracked'))


def draw_entrance(surface, session, exit, sx, sy, wall_tile):
    draw = pygame.draw
    kind = exit.get('entrance', 'stairs_down' if exit.get('stairs') else 'stone')
    discovered = exit['target'] in session.visited
    if kind == 'walkthrough' and not discovered or not entrance_visible(session, exit):
        surface.blit(wall_tile, (sx, sy))
        draw.line(surface, (95, 103, 102), (sx+5, sy+14), (sx+11, sy+14))
        return
    stone = (121, 130, 139)
    edge = (177, 166, 135)
    if kind.startswith('stairs'):
        draw.rect(surface, (16, 22, 35), (sx+1, sy+1, 14, 14))
        for step in range(4):
            width = 12-step*2 if kind == 'stairs_down' else 6+step*2
            x = sx+8-width//2
            draw.rect(surface, (78+step*23, 88+step*21, 108+step*18), (x, sy+2+step*3, width, 2))
        draw.line(surface, edge, (sx+1, sy+1), (sx+1, sy+14))
        draw.line(surface, edge, (sx+14, sy+1), (sx+14, sy+14))
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
