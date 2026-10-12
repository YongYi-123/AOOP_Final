"""Original 12-pixel item silhouettes; palette and quantity follow live inventory."""
import pygame

ICONS={
 'heart':['............','..rr..rr....','.rrrrrrrr...','.rrrrrrrr...','..rrrrrr....','...rrrr.....','....rr......'],
 'sword':['........s...','.......ss...','......ss....','.....ss.....','..g.ss......','...gg.......','..g.gg......','.gg.........'],
 'small_key':['..ggg.......','.g...g......','.g...g......','..gggggggg..','........g.g.'],
 'boss_key':['..g.g.......','..ggg.......','.g...g......','..gggggggg..','.......g.gg.'],
 'bomb':['......g.....','.....g......','....sss.....','...sbbbs....','..sbbbbbs...','..sbbbbbs...','...sbbbs....','....sss.....'],
 'boots':['..tt..tt....','..tt..tt....','..tt..tt....','..ttt.ttt...','..ggg.ggg...','..sss.sss...'],
 'gloves':['...t.t.t....','..tttttt....','..ttttttt...','...tttttt...','....gggg....'],
 'mirror':['...ssss.....','..stttts....','..ststts....','..stttts....','...ssss.....','....gg......','....gg......'],
 'magnet':['..rr..bb....','..rr..bb....','..gg..gg....','..gg..gg....','...gggg.....'],
 'map':['..sssssss...','..sttttts...','..stststs...','..sttttts...','..stststs...','..sssssss...'],
 'compass':['...sss......','..sgggs.....','.sgtrtgs....','.sgtgtgs....','.sgtbtgs....','..sgggs.....','...sss......'],
 'pulse':['....t.......','..t.t.t.....','...ttt......','.tttgttt....','...ttt......','..t.t.t.....','....t.......']}
PALETTE={'r':(239,102,119),'g':(245,198,96),'s':(205,223,230),'b':(65,85,127),'t':(81,195,165)}

class IconAtlas:
    def __init__(self):self.cache={}
    def get(self,kind,enabled=True):
        key=kind,enabled
        if key not in self.cache:
            surface=pygame.Surface((12,12),pygame.SRCALPHA)
            for y,row in enumerate(ICONS.get(kind,ICONS['pulse'])):
                for x,pixel in enumerate(row):
                    if pixel!='.':surface.set_at((x,y),PALETTE[pixel] if enabled else (66,75,87))
            self.cache[key]=surface
        return self.cache[key]

class IconHUD:
    def __init__(self):self.atlas=IconAtlas()
    def draw(self,renderer,session,tool):
        s=renderer.surface;inv=session.inventory
        pygame.draw.rect(s,(18,26,39),(0,184,320,56))
        for index in range(session.player.max_hp):s.blit(self.atlas.get('heart',index<session.player.hp),(5+index*12,186))
        s.blit(self.atlas.get('sword'),(73,186))
        for kind,value,x in (('small_key',sum(inv.keys.values()),94),('bomb',getattr(inv,'bombs',0),145)):
            s.blit(self.atlas.get(kind),(x,186));renderer.text(str(value),x+14,185,max_width=28)
        s.blit(self.atlas.get('boss_key',getattr(inv,'boss_key',False)),(194,186))
        for i,kind in enumerate(('boots','gloves','mirror','magnet','map','compass')):
            x=219+i*16;s.blit(self.atlas.get(kind,kind in inv.abilities),(x,186))
            if tool==kind:pygame.draw.rect(s,(245,198,96),(x-2,184,15,15),1)
        room=session.rooms.data
        renderer.text(room['name'],6,205,(245,198,96),max_width=235)
        renderer.text(room.get('floor','1F'),281,205,max_width=34)
        renderer.text('J / E / B / SHIFT',6,224,max_width=232)
        renderer.text('TAB Map',244,224,max_width=73)
        pickup=getattr(session,'pickup',None)
        if pickup:
            kind,label,remaining=pickup
            pygame.draw.rect(s,(18,26,39),(65,137,190,34));pygame.draw.rect(s,(245,198,96),(65,137,190,34),1)
            s.blit(pygame.transform.scale(self.atlas.get(kind),(24,24)),(72,142))
            renderer.text(label,102,149,max_width=146)
