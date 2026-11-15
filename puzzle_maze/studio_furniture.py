"""New honey-wood studio furniture, painted in a consistent three-quarter view."""
import pygame
WOOD=(158,108,67);TOP=(204,160,105);EDGE=(240,202,144);DARK=(102,68,47);INK=(66,54,51)

def monitor(s,x,y,flat=False):
    r=pygame.draw
    r.polygon(s,(95,107,105) if flat else (164,158,132),[(x+2,y),(x+26,y),(x+31,y+5),(x+30,y+21),(x+2,y+21)])
    r.rect(s,(211,204,169) if not flat else (133,151,144),(x,y,26,21));r.rect(s,(39,72,74),(x+3,y+3,20,13))
    for yy,w in ((6,12),(9,8),(12,15)):r.line(s,(146,197,168),(x+5,y+yy),(x+5+w,y+yy))
    r.rect(s,(109,110,96),(x+10,y+21,6,5));r.rect(s,(198,189,151),(x+5,y+25,20,2))
    r.rect(s,(231,200,122),(x+21,y+18,2,1))

def book(s,x,y,c,height=14):
    r=pygame.draw;r.rect(s,(92,68,54),(x+1,y+1,5,height));r.rect(s,c,(x,y,5,height))
    r.line(s,(241,211,151),(x+1,y+4),(x+3,y+4))

def picture(s,x,y,small=False):
    r=pygame.draw;w,h=(12,12) if small else (16,19)
    r.rect(s,(126,84,57),(x,y,w,h));r.rect(s,(230,194,127),(x+1,y+1,w-2,h-2),1)
    r.rect(s,(191,202,175),(x+3,y+3,w-6,h-6))
    r.rect(s,(181,133,97),(x+4,y+5,3,3));r.rect(s,(114,153,128),(x+3,y+8,5,4))
    r.rect(s,(77,79,117),(x+w-7,y+h-8,4,4));r.rect(s,(227,195,112),(x+w-6,y+h-9,2,1))

def source_sprite(item):
    x,y,w,h=item.bounds;s=pygame.Surface((w,h),pygame.SRCALPHA);r=pygame.draw;k=item.name
    if k=='desk':
        r.polygon(s,DARK,[(4,27),(136,27),(143,39),(139,63),(7,63),(0,50)])
        r.polygon(s,TOP,[(7,25),(132,25),(140,49),(0,49)])
        r.line(s,EDGE,(7,26),(131,26),2);r.rect(s,WOOD,(0,49,140,10))
        r.polygon(s,(126,82,52),[(140,49),(143,39),(143,60),(140,64)])
        r.line(s,EDGE,(2,49),(137,49));r.line(s,DARK,(6,59),(137,59))
        for xx in (9,126):r.rect(s,DARK,(xx,59,7,16));r.rect(s,(180,128,79),(xx,60,2,12))
        monitor(s,15,1);monitor(s,65,2,True)
        r.polygon(s,(100,92,76),[(24,34),(65,34),(71,44),(20,44)])
        r.polygon(s,(223,208,167),[(25,35),(64,35),(68,42),(22,42)])
        for yy in (37,40):
            for xx in range(27,63,5):r.rect(s,(113,109,92),(xx,yy,3,1))
        r.ellipse(s,(228,212,171),(76,36,6,9));r.line(s,(114,119,103),(79,31),(79,36))
        picture(s,102,28)
        # A modest lamp, a closed notebook and a single rubber duck.
        r.line(s,(112,95,66),(127,34),(127,12),2);r.polygon(s,(244,208,136),[(120,12),(133,12),(136,21),(116,21)])
        r.rect(s,(119,144,123),(116,37,12,8));r.line(s,(225,207,155),(119,39),(125,39))
        r.ellipse(s,(237,191,87),(113,47,8,4));r.circle(s,(245,204,108),(120,45),3);r.rect(s,(107,86,62),(120,44,1,1))
    elif k=='tower':
        r.polygon(s,(101,111,103),[(1,6),(19,0),(24,7),(24,49),(1,50)])
        r.rect(s,(192,187,154),(1,7,18,42));r.rect(s,(51,77,72),(4,12,12,29))
        r.rect(s,(120,166,124),(6,15,7,12));r.rect(s,(209,198,153),(8,17,4,5))
        for xx in (7,13):r.circle(s,(44,64,67),(xx,33),4);r.circle(s,(147,166,148),(xx,33),3,1)
        r.rect(s,(203,166,96),(6,38,10,2));r.rect(s,(226,154,127),(8,44,3,2))
    elif k=='bookshelf':
        r.polygon(s,DARK,[(0,7),(28,1),(33,5),(33,52),(3,55),(0,50)])
        r.rect(s,WOOD,(0,8,29,44));r.polygon(s,(186,137,82),[(0,8),(5,4),(33,4),(29,8)])
        for yy in (14,33):
            for i,c in enumerate(((142,89,106),(112,151,127),(109,133,157),(198,158,96))):book(s,3+i*6,yy,c,14-i%2*2)
            r.rect(s,EDGE,(1,yy+15,28,3));r.rect(s,DARK,(1,yy+18,28,2))
    elif k=='sofa':
        r.ellipse(s,(94,76,59),(0,34,67,12));r.rect(s,(124,139,106),(4,4,59,29),border_radius=4)
        r.rect(s,(170,183,139),(7,5,53,17),border_radius=3)
        for xx in (9,33):r.rect(s,(193,197,153),(xx,21,24,15),border_radius=3)
        r.rect(s,(123,145,111),(0,15,9,25),border_radius=3);r.rect(s,(113,132,100),(58,15,9,26),border_radius=3)
        r.rect(s,(221,193,153),(10,11,14,14),border_radius=2);r.line(s,(190,157,131),(12,14),(21,21))
        for xx in (9,54):r.rect(s,DARK,(xx,38,4,6))
        # One folded blanket; the living corner is tidy rather than a storage pile.
        r.rect(s,(210,155,139),(35,22,17,15));r.line(s,(238,199,166),(37,25),(50,25),2)
    elif k=='table':
        r.ellipse(s,(113,82,57),(0,18,28,14));r.polygon(s,TOP,[(3,3),(24,3),(27,19),(0,19)])
        r.line(s,EDGE,(3,4),(23,4));r.rect(s,WOOD,(0,19,28,5))
        for xx in (4,21):r.rect(s,DARK,(xx,24,3,8))
        r.rect(s,(238,211,168),(5,7,7,8));r.arc(s,(238,211,168),(9,8,6,5),-1.5,1.5,1)
        r.rect(s,(124,153,132),(14,9,9,8));r.line(s,(223,209,169),(16,11),(21,11))
    elif k=='archive':
        r.polygon(s,DARK,[(2,35),(39,30),(44,38),(44,70),(2,72)])
        r.polygon(s,TOP,[(0,32),(36,29),(43,37),(2,40)]);r.rect(s,WOOD,(2,40,38,28))
        r.rect(s,(189,144,90),(6,46,30,17));r.line(s,DARK,(20,46),(20,63));r.rect(s,(236,198,117),(18,52,3,2))
        monitor(s,7,4);r.rect(s,(228,215,170),(5,33,14,5))
        for yy in (35,36):r.line(s,(113,114,93),(8,yy),(16,yy))
        for xx in (7,33):r.rect(s,DARK,(xx,68,3,5))
    elif k=='food':
        r.polygon(s,TOP,[(2,2),(25,0),(30,6),(0,8)]);r.rect(s,WOOD,(0,8,27,23));r.rect(s,DARK,(2,10,23,16))
        for row in (12,21):
            for col in (4,11,18):
                r.rect(s,(183,188,151),(col,row,6,7));r.rect(s,(239,217,163),(col,row+2,6,2));r.rect(s,(156,114,92),(col+2,row+3,2,1))
    elif k=='cushion':
        r.ellipse(s,(130,103,86),(0,12,50,21));r.ellipse(s,(214,158,152),(0,4,50,25))
        r.ellipse(s,(244,214,184),(4,7,42,17));r.ellipse(s,(226,186,164),(9,11,32,11))
        for xx,yy in ((8,11),(40,12),(13,24),(33,25)):r.line(s,(159,115,120),(xx,yy),(xx+2,yy+1))
        r.rect(s,(161,183,156),(19,5,15,9));r.line(s,(220,225,185),(21,8),(32,8))
    elif k=='post':
        r.ellipse(s,(118,85,58),(0,28,18,13));r.rect(s,(180,142,98),(5,6,8,28))
        for yy in range(8,33,3):r.line(s,(227,194,137),(5,yy),(12,yy+1))
        r.ellipse(s,(143,110,79),(2,3,14,8))
    elif k=='plant':
        r.polygon(s,(172,119,83),[(2,19),(16,19),(13,31),(5,31)]);r.line(s,(87,123,79),(9,21),(9,4),2)
        for xx,yy in ((2,7),(10,2),(0,13),(10,11)):r.ellipse(s,(135,166,105),(xx,yy,8,6))
    return s


def furniture_sprite(item):
    from puzzle_maze.studio_layout import SOURCE_FURNITURE
    source=next(f for f in SOURCE_FURNITURE if f.name==item.name)
    return pygame.transform.scale(source_sprite(source),item.bounds[2:])
