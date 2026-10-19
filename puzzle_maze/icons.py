"""Original 12-pixel item silhouettes; palette and quantity follow live inventory."""
import pygame
import math

ICONS={
 'heart':['............','..rr..rr....','.rrrrrrrr...','.rrrrrrrr...','..rrrrrr....','...rrrr.....','....rr......'],
 'sword':['........s...','.......ss...','......ss....','.....ss.....','..g.ss......','...gg.......','..g.gg......','.gg.........'],
 'small_key':['..sss.......','.s...s......','.s...s......','..ssssssss..','........s.s.'],
 'boss_key':['..g.g.......','..ggg.......','.g...g......','..gggggggg..','.......g.gg.'],
 'bomb':['......g.....','.....g......','....sss.....','...sbbbs....','..sbbbbbs...','..sbbbbbs...','...sbbbs....','....sss.....'],
 'boots':['..tt..tt....','..tt..tt....','..tt..tt....','..ttt.ttt...','..ggg.ggg...','..sss.sss...'],
 'gloves':['...t.t.t....','..tttttt....','..ttttttt...','...tttttt...','....gggg....'],
 'mirror':['...ssss.....','..stttts....','..ststts....','..stttts....','...ssss.....','....gg......','....gg......'],
 'magnet':['..rr..bb....','..rr..bb....','..gg..gg....','..gg..gg....','...gggg.....'],
 'map':['..sssssss...','..sttttts...','..stststs...','..sttttts...','..stststs...','..sssssss...'],
 'compass':['...sss......','..sgggs.....','.sgtrtgs....','.sgtgtgs....','.sgtbtgs....','..sgggs.....','...sss......'],
 'potion':['....sss.....','....srs.....','...sttts....','...sttts....','...sttts....','....sss.....'],
 'pulse':['....t.......','..t.t.t.....','...ttt......','.tttgttt....','...ttt......','..t.t.t.....','....t.......']}
ICONS.update({
 'mystery_scroll':['.gg......gg.','gssggggggssg','gssssssssssg','.gssssssssg.','.gssppppssg.','.gssssssssg.','.gssppppssg.','gssssssssssg','gssggggggssg','.gg......gg.'],
 'royal_crown':['g....g....g.','gg..ggg..gg.','.ggggggggg..','.ggprgbrgg..','.ggggggggg..','.ggggggggg..'],
 'powder':['....gggg....','...gppppg...','...gppppg...','..gppppppg..','..gppssppg..','..gppssppg..','...gggggg...'],
 'pot':['....kkkk....','...kggggk...','..kggggggk..','..kgkkkkgk..','..kggggggk..','...kggggk...','....kkkk....'],
 'heart_fragment':['....rr......','...rrrr.....','..rrrsrr....','...rsrr.....','....rr......'],
 'heart_recovery':['..rr..rr....','.rrrrrrrr...','.rrrssrrr...','..rssssr....','...rssr.....','....rr......'],
 'token_cache':['...ggggg....','..gssgggg...','..gggtggg...','..ggtttgg...','..gggtggg...','...ggggg....'],
 'ticket_bundle':['..gggggggg..','..grrrrrrg..','...rrsrrr...','..grrrrrrg..','..grrsrrrg..','..gggggggg..'],
 'golden_cat':['..g.....g...','..gg...gg...','..ggggggg...','..gbgggbg...','...ggggg....','...ggggg....','..ggggggg...','..gggggggg..'],
 'music_disc':['...ppppp....','..pptttpp...','.pptssstpp..','.ptssbsstp..','.pptssstpp..','..pptttpp...','...ppppp....'],
 'crystal_skin':['........t...','.......tt...','......tt....','.....tt.....','..p.tt......','...pp.......','..g.pp......','.gg.........'],
 'lucky_charm':['....rrr.....','...rsssr....','...ssgss....','...sgggs....','...sgbgs....','...ssgss....','...rsssr....','....rrr.....'],
 'ancient_stamp':['..sssssss...','..sppppps...','..sptptps...','..sptgtps...','..sptptps...','..sppppps...','..sssssss...'],
 'bomb_bundle':['..gbb..gbb..','..bbbbb.bbb.','...bbb..bbb.','.....gg.....','....sbbbs...','....sbbbs...','.....sss....'],
})
ALIASES={'magic_powder':'powder','royal_circuit':'boss_key','royal_tokens':'token_cache','royal_tickets':'ticket_bundle'}
PALETTE={'p':(184,123,226),'k':(88,59,53),'r':(239,102,119),'g':(245,198,96),'s':(205,223,230),'b':(65,85,127),'t':(81,195,165)}

class BossKeyIcon:
    """One jewel/crown silhouette shared by keys, locks, HUD and rewards."""
    cache={}
    @classmethod
    def surface(cls,enabled=True):
        if enabled not in cls.cache:
            s=pygame.Surface((16,16),pygame.SRCALPHA);r=pygame.draw
            gold=(245,198,96) if enabled else (66,75,87)
            edge=(147,94,48) if enabled else (46,55,67)
            r.circle(s,edge,(5,5),5);r.circle(s,gold,(5,5),4)
            r.polygon(s,(203,96,207) if enabled else edge,[(5,1),(8,5),(5,8),(2,5)])
            if enabled:r.line(s,(255,226,245),(4,3),(5,2))
            r.line(s,edge,(8,8),(14,14),4);r.line(s,gold,(8,8),(14,14),2)
            r.rect(s,gold,(11,9,3,2));r.rect(s,gold,(9,12,2,3));r.rect(s,gold,(13,12,3,2))
            r.rect(s,gold,(1,0,2,2));r.rect(s,gold,(8,0,2,2))
            cls.cache[enabled]=s
        return cls.cache[enabled]

class IconAtlas:
    def __init__(self):self.cache={}
    def get(self,kind,enabled=True):
        kind=ALIASES.get(kind,kind)
        if kind=='boss_key':return BossKeyIcon.surface(enabled)
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
    def draw(self,renderer,session,tool,controls):
        s=renderer.surface;inv=session.inventory
        if hasattr(session,"rewards"):return self.draw_advanced(renderer,session,tool,controls)
        pygame.draw.rect(s,(18,26,39),(0,184,320,56))
        for index in range(session.player.max_hp):s.blit(self.atlas.get('heart',index<session.player.hp),(5+index*12,186))
        s.blit(self.atlas.get('sword'),(73,186))
        for kind,value,x in (('small_key',sum(inv.keys.values()),94),('bomb',getattr(inv,'bombs',0),145)):
            s.blit(self.atlas.get(kind),(x,186));renderer.text(str(value),x+14,185,max_width=28)
        s.blit(self.atlas.get('boss_key',getattr(inv,'boss_key',False)),(188,186))
        for i,kind in enumerate(('boots','gloves','mirror','magnet','map','compass')):
            x=219+i*16;s.blit(self.atlas.get(kind,kind in inv.abilities),(x,186))
            if tool==kind:pygame.draw.rect(s,(245,198,96),(x-2,184,15,15),1)
        s.blit(self.atlas.get('pulse'),(207,186))
        if tool=='pulse':pygame.draw.rect(s,(245,198,96),(205,184,15,15),1)
        room=session.rooms.data
        renderer.text(room['name'],6,205,(245,198,96),max_width=235)
        s.blit(self.atlas.get('potion',inv.potions>0),(246,207));renderer.text(str(inv.potions),260,205,max_width=20)
        renderer.text(room.get('floor','1F'),281,205,max_width=34)
        pygame.draw.rect(s,(52,65,82),(219,200,12,2))
        if 'boots' in inv.abilities:pygame.draw.rect(s,(81,195,165),(219,200,int(12*(1-session.dash_cooldown/1.2)),2))
        keys=f"{controls['attack']} / {controls['interact']} / "+('B / ' if hasattr(session,'bombs') else '')+controls['dash']
        renderer.text(keys,6,224,max_width=232)
        renderer.text(controls['map']+' Map',244,224,max_width=73)
        pickup=getattr(session,'pickup',None)
        if pickup:
            kind,label,remaining=pickup
            pygame.draw.rect(s,(18,26,39),(65,137,190,34));pygame.draw.rect(s,(245,198,96),(65,137,190,34),1)
            s.blit(pygame.transform.scale(self.atlas.get(kind),(24,24)),(72,142+int(math.sin(renderer.time*10)*2)))
            renderer.text(label,102,149,max_width=146)

    def draw_advanced(self,renderer,session,tool,controls):
        s=renderer.surface;inv=session.inventory;r=pygame.draw
        r.rect(s,(15,23,35),(0,184,320,56));r.line(s,(90,115,125),(0,184),(320,184))
        for i in range(session.player.max_hp):s.blit(self.atlas.get('heart',i<session.player.hp),(5+i*12,186))
        for kind,value,x in (('sword',None,108),('small_key',sum(inv.keys.values()),132),('bomb',inv.bombs,180),('powder',inv.powder,230),('boss_key',None,285)):
            enabled=inv.boss_key if kind=='boss_key' else 'powder' in inv.abilities if kind=='powder' else True
            if kind=='boss_key' and enabled:r.rect(s,(117+int(math.sin(renderer.time*5)*15),92,66),(x-1,185,18,18),1)
            s.blit(self.atlas.get(kind,enabled),(x,186))
            if value is not None:renderer.text(str(value),x+14,186,max_width=30)
        for i,kind in enumerate(('gloves','boots','mirror','magnet','map','compass','pulse')):
            x=5+i*18;s.blit(self.atlas.get(kind,kind=='pulse' or kind in inv.abilities),(x,204))
            if kind==tool:r.rect(s,(245,198,96),(x-2,202,16,16),1)
        s.blit(self.atlas.get('pot',inv.carried is not None),(137,204));renderer.text('G' if inv.carried else 'E',152,202,max_width=12)
        s.blit(self.atlas.get('potion',inv.potions>0),(170,204));renderer.text(str(inv.potions),185,202,max_width=24)
        s.blit(self.atlas.get('heart_fragment'),(211,204));renderer.text(f'{inv.heart_fragments%4}/4',225,202,max_width=40)
        s.blit(self.atlas.get('golden_cat'),(272,204));renderer.text(f'{len(session.rewards.collections)}/6',286,202,max_width=28)
        renderer.text(session.rooms.data['name'],6,222,(245,198,96),max_width=222)
        renderer.text('BLUE' if 'crystal_blue' in inv.flags else 'RED',234,222,(112,190,241) if 'crystal_blue' in inv.flags else (236,117,113),max_width=44)
        renderer.text(session.rooms.data.get('floor','1F'),285,222,max_width=30)
        if session.pickup:
            kind,label,remaining=session.pickup
            if kind=='boss_key':
                r.rect(s,(20,24,43),(45,78,230,92));r.rect(s,(245,198,96),(45,78,230,92),2)
                pulse=int(math.sin(renderer.time*7)*2)
                s.blit(pygame.transform.scale(self.atlas.get('boss_key'),(40,40)),(140,88+pulse))
                renderer.text('BOSS KEY ACQUIRED',61,139,(245,198,96),max_width=204)
                return
            r.rect(s,(15,23,35),(60,139,202,34));r.rect(s,(245,198,96),(60,139,202,34),1)
            s.blit(pygame.transform.scale(self.atlas.get(kind),(24,24)),(66,143+int(math.sin(renderer.time*10)*2)))
            renderer.text(label,95,149,max_width=161)
