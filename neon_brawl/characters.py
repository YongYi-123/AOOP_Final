"""Original 32px character drawings, presented at crisp 2x with a fixed foot anchor.

Short fixed-length arms rotate at shoulder and elbow. Combat reach belongs to
energy ribbons and game rules, never stretching limbs or changing hitboxes.
"""
import math
import pygame
from .data import ROSTER, ATTACKS
from .outfits import outfit_for, BOSS_NAMES

INK = (24, 23, 47)
WHITE = (245, 250, 244)
SKIN = (249, 200, 165)
ARM_UPPER = ARM_FORE = 3.


def mix(a, b, amount=.5):
    return tuple(round(x*(1-amount)+y*amount) for x,y in zip(a,b))


def arm_joints(shoulder, state, frame):
    """Two rigid bones, in native pixels. Exposed for geometry regression tests."""
    frame %= 8
    upper, fore = 65, 105
    if state in ATTACKS:
        upper = (105, 125, 10, 0, 10, 35, 50, 65)[frame]
        fore = (-105, -130, -10, 0, 15, 50, 80, 105)[frame]
    if state in ('heavy', 'smash', 'bash'):
        upper = (-25, -65, -85, -80, -50, 0, 35, 65)[frame]
        fore = (-90, -100, -90, -45, 0, 40, 60, 105)[frame]
    if state in ('slam', 'strike'):
        upper = (-80, -100, -10, 40, 50, 45, 50, 65)[frame]
        fore = (-75, -90, 25, 70, 75, 60, 70, 105)[frame]
    if state in ('special', 'shot', 'snipe', 'orb', 'laser', 'pulse', 'wave'):
        upper = (90, 110, 5, 0, 10, 35, 50, 65)[frame]
        fore = (-100, -110, -15, 0, 15, 45, 75, 105)[frame]
    if state in ('guard', 'hurt'): upper, fore = 65, -110
    if state in ('summon', 'phase'): upper, fore = -30, -70
    if state == 'victory': upper, fore = -65, -90
    elbow = (shoulder[0]+math.cos(math.radians(upper))*ARM_UPPER,
             shoulder[1]+math.sin(math.radians(upper))*ARM_UPPER)
    hand = (elbow[0]+math.cos(math.radians(fore))*ARM_FORE,
            elbow[1]+math.sin(math.radians(fore))*ARM_FORE)
    return shoulder, elbow, hand


def fighter_cel(name, state, frame, outfit=0):
    s = pygame.Surface((32,32), pygame.SRCALPHA)
    frame %= 8
    boss = name in BOSS_NAMES
    heavy = name in ('BRUNO','bruiser','shield','security','RELAY','NULL')
    fast = name in ('NOVA','runner','duelist','cyber','assassin')
    outfit = None if name in ROSTER or boss else outfit_for(name,outfit)
    color = ROSTER[name].color if name in ROSTER else {
        'WARDEN':(186,91,126),'RELAY':(110,186,205),'NULL':(157,120,213)
    }[name] if boss else outfit.color
    trim = outfit.trim if outfit else (255,213,131) if name in ('BRUNO','WARDEN') else (255,172,220) if name=='NULL' else (178,250,239)
    dark, pale = mix(color,INK,.55), mix(color,WHITE,.4)
    style = outfit.style if outfit else 'nova' if name=='NOVA' else 'worker' if name=='BRUNO' else 'jacket'
    walking = state in ('walk','approach','positioning')
    stride = (0,1,2,1,0,-1,-2,-1)[frame] if walking else 0
    if heavy: stride = round(stride*.5)
    bob = (0,0,1,0,0,0,1,0)[frame] if walking else (0,0,0,0,1,1,0,0)[frame]
    lean = 0
    if state in ATTACKS:
        lean = (-1,-1,0,1,1,1,0,0)[frame]
        bob = (1,1,0,0,0,1,0,0)[frame]
    if state=='hurt': lean=(-2,-2,-1,-1,0,0,0,0)[frame]
    if state=='dodge':
        lean=(0,1,1,1,1,0,0,0)[frame]
        bob=(1,2,3,3,2,1,1,0)[frame]
    if boss and state in ('idle','intro','phase','summon','teleport'):
        if name=='WARDEN': lean=(0,0,0,1,1,0,0,0)[frame]
        elif name=='RELAY': bob=(0,0,-1,0,0,1,0,0)[frame]
        else: bob=(0,-1,-1,0,0,1,1,0)[frame]
    cx, width = 15+lean, 5 if heavy else 4
    head_w = 16 if heavy else 14
    hx,hy = cx-head_w//2,5+bob

    def box(c,x,y,w,h): pygame.draw.rect(s,c,(round(x),round(y),w,h))
    def poly(c,pts): pygame.draw.polygon(s,c,[(round(x),round(y)) for x,y in pts])
    def rounded(c,rect,r=2,outline=True):
        rect=pygame.Rect(*(round(v) for v in rect))
        pygame.draw.rect(s,INK if outline else c,rect,border_radius=r)
        if outline: pygame.draw.rect(s,c,rect.inflate(-2,-2),border_radius=max(0,r-1))
    def limb(points,c,size=2):
        points=[(round(x),round(y)) for x,y in points]
        pygame.draw.lines(s,INK,False,points,size+2)
        pygame.draw.lines(s,c,False,points,size)
        for x,y in (points[0],points[-1]):
            box(c,x,y,1,1)

    # Readable silhouette accessories, all authored on this 32px grid.
    if name in ('NOVA','runner','assassin'):
        poly(INK,[(cx-4,15+bob),(cx-12,16+bob),(cx-10,19+bob),(cx-4,18+bob)])
        poly(color,[(cx-5,16+bob),(cx-10,17+bob),(cx-9,18+bob),(cx-4,17+bob)])
    if name in ('WARDEN','NULL') or style=='coat':
        poly(INK,[(cx-5,19),(cx+5,19),(cx+7,27),(cx+1,26),(cx,24),(cx-3,27),(cx-7,26)])
        poly(dark,[(cx-4,20),(cx+4,20),(cx+5,26),(cx+2,25),(cx,23),(cx-3,26),(cx-5,25)])
    if style=='courier': rounded(dark,(cx-8,17+bob,5,8));box(trim,cx-7,19+bob,2,2)
    tucked=2 if state=='airborne' and 1<=frame<=5 else 0
    for back,foot in ((True,cx-3+stride),(False,cx+3-stride)):
        limb([(cx-2 if back else cx+2,23+bob),(foot,26-tucked),(foot,28-tucked)],(65,68,99),2 if not heavy else 3)
        rounded(dark if back else color,(foot-2,27-tucked,6,3),1)
        box(trim,foot-1,29-tucked,4,1)
    # Rear arm remains short even in rapid double punches.
    rear = arm_joints((cx-width,18+bob),'guard' if state in ('double','barrage') and frame in (2,4) else 'idle',frame)
    rear = [(2*(cx-width)-x,y) for x,y in rear]
    limb(rear,dark,2)
    rounded(color,(cx-width-1,16+bob,width*2+2,9),3)
    box(dark,cx-width+1,20+bob,2,3)
    box(trim,cx,18+bob,1,5)
    box(INK,cx-width+1,24+bob,width*2-2,1)
    if style in ('worker','vest','military'):
        rounded((66,76,102),(cx-3,19+bob,7,5),1)
        for x in (cx-3,cx+3):box(trim,x,17+bob,1,6)
        box(pale,cx-1,21+bob,3,1)
    elif style in ('armor','tech') or name in ('RELAY','NULL','cyber','security'):
        for x in (cx-width-1,cx+width-2): rounded(pale,(x,17+bob,4,4),1)
        rounded(dark,(cx-3,19+bob,7,5),2)
        if name=='NULL':
            poly(trim,[(cx,19+bob),(cx+2,21+bob),(cx,23+bob),(cx-2,21+bob)])
            box(WHITE,cx,21+bob,1,1)
        else:box(trim,cx-1,21+bob,3,1)
    elif style=='track':
        for x in (cx-3,cx+3):box(trim,x,18+bob,1,5)
    elif style=='nova':
        poly(WHITE,[(cx-4,17+bob),(cx+3,17+bob),(cx+1,19+bob),(cx-2,18+bob)])
        box((255,165,200),cx-3,21+bob,2,2)
    else:
        for direction in (-1,1):poly(pale,[(cx+direction,17+bob),(cx+direction*4,18+bob),(cx+direction*2,20+bob)])
        box(trim,cx+2,22+bob,2,1)
    if name=='WARDEN':
        for direction in (-1,1):poly(trim,[(cx+direction,17+bob),(cx+direction*5,18+bob),(cx+direction*3,21+bob)])

    # Broad face, tiny chin, cheek pixels, and large dark eyes with a one-pixel glint.
    if style=='hood' or name in ('NULL','assassin'): rounded(dark,(hx-1,hy-1,head_w+2,15),4)
    skin=(195,226,229) if name in ('NULL','RELAY','echo') else SKIN
    rounded(skin,(hx,hy,head_w,13),4)
    box(mix(skin,WHITE,.4),hx+3,hy+2,2,1)
    if name=='NOVA':
        poly(INK,[(hx,hy+6),(hx-1,hy+2),(hx+3,hy-2),(hx+9,hy-2),(hx+13,hy),(hx+14,hy+6),(hx+10,hy+4),(hx+8,hy+1),(hx+5,hy+5)])
        poly(color,[(hx+1,hy+4),(hx,hy+2),(hx+3,hy-1),(hx+9,hy-1),(hx+12,hy+1),(hx+12,hy+4),(hx+10,hy+3),(hx+8,hy),(hx+5,hy+4)])
        box(pale,hx+3,hy,3,1)
        rounded(dark,(hx-2,hy+4,4,6),1);box(trim,hx-1,hy+6,2,2)
        box((255,169,205),hx+11,hy+4,2,1)
    elif name=='BRUNO' or name=='bruiser' or style=='worker':
        rounded(color,(hx,hy-2,head_w,6),3)
        rounded(trim,(hx-1,hy+2,head_w+2,3),1)
        box(pale,cx,hy-1,1,3)
    elif name in ('RELAY','security') or style=='armor':
        rounded(dark,(hx,hy-1,head_w,6),3)
        for x in (hx-2,hx+head_w-2):rounded(pale,(x,hy+3,4,7),1)
        box(trim,hx+3,hy+2,head_w-6,1)
        if name=='RELAY':
            box(INK,cx-3,hy-3,1,3);box(trim,cx-4,hy-3,3,1)
    elif name=='NULL':
        for sign in (-1,1):
            poly(INK,[(cx+sign*3,hy+1),(cx+sign*8,hy-3),(cx+sign*7,hy+6)])
            poly(color,[(cx+sign*4,hy+1),(cx+sign*7,hy-1),(cx+sign*6,hy+4)])
        rounded(dark,(hx+2,hy,head_w-4,4),2)
    elif name=='WARDEN':
        rounded((255,219,157),(hx,hy-2,head_w,6),3)
        rounded((255,237,197),(cx,hy-3,7,4),2)
    elif fast:
        rounded(dark,(hx,hy-1,head_w,5),2)
        poly(color,[(hx+2,hy+3),(hx+3,hy-2),(hx+6,hy),(hx+10,hy-2),(hx+12,hy+3)])
        box(trim,hx,hy+4,head_w,1)
        if style=='courier':rounded(color,(hx+2,hy-2,head_w-1,4),2)
    else:
        for x,y,r in ((hx+3,hy+1,3),(cx,hy,4),(hx+head_w-3,hy+1,3)):
            pygame.draw.circle(s,INK,(x,y),r)
            pygame.draw.circle(s,(91,65,90),(x,y),max(1,r-1))
        if style=='hood':rounded(color,(hx-1,hy-2,4,11),2)
        if style=='denim':box(trim,hx+1,hy+4,2,2)
        if style=='military':rounded(color,(hx-1,hy-2,head_w+2,4),1)
    eye_y=hy+7
    for x in (cx-3,cx+3):
        if state in ('hurt','knockdown','defeated'):
            poly(INK,[(x-1,eye_y),(x+1,eye_y+1),(x-1,eye_y+2)])
        elif frame==7 and state not in ATTACKS and state not in ('intro','phase','guard'):
            box(INK,x-1,eye_y+1,3,1)
        else:
            box(INK,x-1,eye_y,2,3);box(WHITE,x-1,eye_y,1,1)
    for x in (cx-5,cx+4):box((246,143,169),x,eye_y+3,2,1)
    if state in ('intro','phase') or state in ATTACKS and frame<2:
        box(INK,cx,eye_y+3,1,2)
    else:
        box(INK,cx-1,eye_y+4,1,1);box(INK,cx+1,eye_y+4,1,1)
        box(INK,cx,eye_y+5,1,1)

    arm=arm_joints((cx+width,18+bob),state,frame)
    limb(arm,color,3 if heavy else 2)
    hand_x,hand_y=map(round,arm[-1])
    rounded(trim if heavy or boss else skin,(hand_x-1,hand_y-1,4 if heavy else 3,4 if heavy else 3),1)
    if state in ('combo3','air','sweep') and 2<=frame<=4:
        limb([(cx+2,23),(cx+5,23),(cx+7,22)],(74,78,111),2)
        rounded(color,(cx+6,21,5,4),1)
        box(trim,cx+7,24,3,1)
    if name in ('shield','security'):
        rounded(dark,(cx-9,18+bob,7,10),2)
        rounded(pale,(cx-8,20+bob,5,6),1);box(trim,cx-7,22+bob,3,1)
    if name in ('ranged','sniper','echo'):
        rounded(dark,(min(26,hand_x-1),hand_y-2,5,3),1)
        box(trim,min(29,hand_x+2),hand_y-1,1,1)
    if name in ('duelist','assassin'):
        pygame.draw.line(s,INK,(hand_x,hand_y),(min(30,hand_x+2),hand_y-6),2)
        pygame.draw.line(s,pale,(hand_x,hand_y-1),(min(30,hand_x+2),hand_y-6),1)
    if state in ('knockdown','defeated'):
        body=s.subsurface(s.get_bounding_rect()).copy()
        body=pygame.transform.rotate(body,(15,35,60,80,90,90,90,90)[frame])
        factor=min(1,30/body.get_width(),29/body.get_height())
        if factor<1:body=pygame.transform.scale(body,(int(body.get_width()*factor),int(body.get_height()*factor)))
        s.fill((0,0,0,0));s.blit(body,((32-body.get_width())//2,30-body.get_height()))
    image=pygame.Surface((64,64),pygame.SRCALPHA)
    image.blit(pygame.transform.scale(s,(64,64)),(0,-1))
    return image
