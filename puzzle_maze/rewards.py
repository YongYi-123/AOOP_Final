"""Private run escrow and idempotent settlement; no external economy dependencies."""
from dataclasses import dataclass,field
import copy
from uuid import uuid4

TREASURES={
 'token_cache':('TOKEN CACHE','tokens',10),'ticket_bundle':('TICKET BUNDLE','tickets',15),
 'golden_cat':('GOLDEN CAT','collectible',1),'music_disc':('SECRET MUSIC DISC','collectible',1),
 'crystal_skin':('CRYSTAL SWORD SKIN','cosmetic',1),'lucky_charm':('LUCKY CAT CHARM','collectible',1),
 'ancient_stamp':('ANCIENT STAR STAMP','decoration',1),
 'heart_fragment':('HEART FRAGMENT','fragment',1),'heart_recovery':('HEART RECOVERY','heal',2),
 'magic_powder':('MAGIC POWDER / P','powder',8),'bomb_bundle':('BOMB BUNDLE','bomb',4),
 'small_key':('SMALL KEY','key',1),'boss_key':('BOSS KEY','boss',1),
 'map':('DUNGEON MAP','ability',1),'compass':('COMPASS','ability',1)}
COLLECTIONS={k for k,(_,kind,_) in TREASURES.items() if kind in ('collectible','cosmetic','decoration')}

@dataclass
class DungeonRewardBag:
    run_id:str=field(default_factory=lambda:uuid4().hex)
    tokens:int=0
    tickets:int=0
    collections:set=field(default_factory=set)
    sources:set=field(default_factory=set)
    claimed:bool=False
    receipt:dict|None=None
    def collect(self,source,treasure):
        if self.claimed or source in self.sources:return False
        name,kind,amount=TREASURES[treasure]
        self.sources.add(source)
        if kind=='tokens':self.tokens+=amount
        elif kind=='tickets':self.tickets+=amount
        elif treasure in COLLECTIONS:self.collections.add(treasure)
        return True
    def settle(self,finished,alive):
        if not finished or not alive:return None
        if not self.claimed:
            self.receipt=dict(run_id=self.run_id,tokens=self.tokens,tickets=self.tickets,collections=sorted(self.collections))
            self.claimed=True
        return copy.deepcopy(self.receipt)
    def capture(self):
        return dict(run_id=self.run_id,tokens=self.tokens,tickets=self.tickets,collections=sorted(self.collections),sources=sorted(self.sources),claimed=self.claimed,receipt=copy.deepcopy(self.receipt))
    @classmethod
    def restore(cls,data):
        if not isinstance(data,dict):raise ValueError('Invalid reward bag')
        if not isinstance(data['run_id'],str) or not 1<=len(data['run_id'])<=64:raise ValueError('Invalid run id')
        if any(type(data[k]) is not int or not 0<=data[k]<=1000000 for k in ('tokens','tickets')):raise ValueError('Invalid reward count')
        if not isinstance(data['collections'],list) or not set(data['collections'])<=COLLECTIONS:raise ValueError('Unknown collection')
        if not isinstance(data['sources'],list) or any(not isinstance(s,str) for s in data['sources']):raise ValueError('Invalid reward sources')
        if type(data['claimed']) is not bool:raise ValueError('Invalid claim flag')
        bag=cls(data['run_id'],data['tokens'],data['tickets'],set(data['collections']),set(data['sources']),data['claimed'],copy.deepcopy(data['receipt']))
        expected=dict(run_id=bag.run_id,tokens=bag.tokens,tickets=bag.tickets,collections=sorted(bag.collections))
        if bag.claimed and bag.receipt!=expected or not bag.claimed and bag.receipt is not None:raise ValueError('Invalid settlement receipt')
        return bag
