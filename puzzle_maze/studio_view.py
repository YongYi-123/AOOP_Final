"""Dedicated production view: no dungeon HUD, compass, tile borders or generic props."""
import pygame
from puzzle_maze.studio_layout import FURNITURE
from puzzle_maze.miao_adapter import guide_frame

def draw_studio(renderer,session,visual,controls):
    s=renderer.surface;art=renderer.developer_art;r=pygame.draw
    renderer.camera.x=renderer.camera.y=0
    s.set_clip((0,0,320,240));s.blit(art.floor(),(0,0))
    from puzzle_maze.studio_interactions import nearby,physical_objects
    p=session.player;feet=(visual[0]*16+8,visual[1]*16+16)
    scene=getattr(renderer,'studio_scene',None)
    companion=session.studio_companion
    miao=scene.position if scene and scene.time>=1.2 else None if scene or not session.lab_memory_seen else companion.position
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
            walking=scene.walking if scene else companion.walking
            effect=getattr(renderer,'lab_effect',None)
            bed_reaction=bool(effect and effect[0]=='studio_cushion' and 0<=renderer.time-effect[1]<2.4)
            image=guide_frame(walking,scene.time if scene else companion.time,reaction=bool(scene and scene.reaction) or bed_reaction,side='right' if scene else companion.side,sleeping=not scene and not bed_reaction and companion.state=='sleep')
            s.blit(image,image.get_rect(midbottom=(round(miao[0]),round(miao[1]))))
            if bed_reaction:
                r.line(s,(155,194,172),(round(miao[0])+9,round(miao[1])-24),(round(miao[0])+9,round(miao[1])-21))
                s.fill((155,194,172),(round(miao[0])+9,round(miao[1])-19,1,1))
            if not scene and not bed_reaction and companion.state=='sleep':
                x,y=round(miao[0])+9,round(miao[1])-13-int(renderer.time%3)
                r.lines(s,(117,157,165),False,[(x,y),(x+3,y),(x,y+3),(x+3,y+3)])
        else:
            s.blit(art.sprite(obj),obj.bounds[:2])
    if orb and orb.carried:pygame.draw.circle(s,(150,166,153),(round(feet[0]+6),round(feet[1]-11)),4)
    physical_objects(s,session)
    art.effects(s,renderer.time,getattr(renderer,'lab_effect',None))
    if scene and scene.time<2.5:
        # Prototype wakes before the service bench; all screens share the real scene.
        for i,(x,y,w,h) in enumerate(((38,151,24,16),(187,44,19,13),(234,46,19,13))):
            if scene.time<1.1+i*.3 or int(scene.time*13+i)%5==0:r.rect(s,(25,34,33),(x,y,w,h))
    s.set_clip(None)
    # Quiet foreground floor: no automatic information panel or object names.
    if getattr(renderer,'studio_interactive',True):
        from puzzle_maze.studio_interactions import draw_prompt
        draw_prompt(renderer,session)
