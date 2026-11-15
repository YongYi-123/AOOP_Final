"""Dedicated production view: no dungeon HUD, compass, tile borders or generic props."""
import pygame
from puzzle_maze.studio_layout import FURNITURE,MIAO_TILE
from puzzle_maze.miao_adapter import guide_frame
from puzzle_maze.studio_notes import NAMES

def draw_studio(renderer,session,visual,controls):
    s=renderer.surface;art=renderer.developer_art;r=pygame.draw
    renderer.camera.x=renderer.camera.y=0
    s.set_clip((0,0,320,208));s.blit(art.floor(),(0,0))
    p=session.player;feet=(visual[0]*16+8,visual[1]*16+16)
    actor_rect=pygame.Rect(round(feet[0]-8),round(feet[1]-18),16,18)
    scene=getattr(renderer,'studio_scene',None)
    miao=scene.position if scene and scene.time>=1.2 else None if scene or not session.lab_memory_seen else (MIAO_TILE[0]*16+8,MIAO_TILE[1]*16+16)
    layers=[(f.footprint[1]+f.footprint[3],0,f) for f in FURNITURE]
    layers.append((feet[1],1,'player'))
    if miao:layers.append((miao[1],1,'miao'))
    orb=getattr(session,'orb',None)
    if orb and orb.room=='r28' and not orb.carried:layers.append((orb.y*16+16,1,'orb'))
    for depth,_,obj in sorted(layers,key=lambda item:(item[0],item[1])):
        if obj=='player':renderer.player(visual,p.facing,p.moving,0,0)
        elif obj=='orb':
            pygame.draw.circle(s,(129,145,143),(orb.x*16+8,orb.y*16+10),5)
            pygame.draw.circle(s,(219,217,178),(orb.x*16+6,orb.y*16+8),2)
        elif obj=='miao':
            walking=bool(scene and scene.walking)
            image=guide_frame(walking,scene.time if scene else renderer.time,reaction=bool(scene and scene.reaction))
            s.blit(image,image.get_rect(midbottom=(round(miao[0]),round(miao[1]))))
        else:
            bounds=pygame.Rect(obj.bounds)
            ghost=feet[1]<depth and bounds.colliderect(actor_rect)
            s.blit(art.sprite(obj,ghost),obj.bounds[:2])
    if orb and orb.carried:pygame.draw.circle(s,(150,166,153),(round(feet[0]+6),round(feet[1]-11)),4)
    art.effects(s,renderer.time,getattr(renderer,'lab_effect',None))
    s.set_clip(None)
    r.rect(s,(244,226,190),(0,208,320,32));r.line(s,(199,159,111),(0,208),(320,208))
    renderer.text("KEVIN'S COZY STUDIO",10,212,(123,83,61),max_width=190)
    renderer.text('WASD: Walk / E: Inspect',10,227,(147,108,78),max_width=280)
    target=(p.x+p.facing[0],p.y+p.facing[1])
    near=sorted((o for o in session.puzzles.objects.values() if abs(o.x-p.x)+abs(o.y-p.y)<=1),key=lambda o:o.pos!=target)
    if near:
        key=near[0].data.get('content_id','')
        name='Log '+key[-3:] if key.startswith('dev_') else NAMES.get(key,'Read')
        renderer.text('[E] '+name,202,212,(148,101,70),max_width=112)
