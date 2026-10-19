"""Royal clear receipts, not a wallet. External Arcade payout stays disabled."""
import copy
import hashlib
import json
from dataclasses import dataclass,field
from pathlib import Path
from puzzle_maze.rewards import COLLECTIONS

class RoyalRewardPolicy:
    FIRST=(1000,300)
    REPLAY=(100,30)
    @classmethod
    def receipt(cls,bag,first):
        # Exploration rewards retain their existing values; only the royal bonus shrinks.
        tokens,tickets=bag.tokens,bag.tickets
        if not first:
            tokens-=cls.FIRST[0]-cls.REPLAY[0];tickets-=cls.FIRST[1]-cls.REPLAY[1]
        if tokens<0 or tickets<0:raise ValueError('Incomplete royal escrow')
        return dict(run_id=bag.run_id,tokens=tokens,tickets=tickets,collections=sorted(bag.collections),tier='first' if first else 'replay')

@dataclass
class RoyalClearHistory:
    receipts:dict=field(default_factory=dict)
    blocked:bool=False
    @property
    def first_claimed(self):return any(r['tier']=='first' for r in self.receipts.values())
    def get(self,run_id):return copy.deepcopy(self.receipts.get(run_id))
    def finalize(self,bag,finished,alive,vault_complete):
        if self.blocked or not finished or not alive or not vault_complete or not bag.claimed:return None
        required={'r27:royal_tokens:royal_tokens','r27:royal_tickets:royal_tickets','r27:royal_collection:royal_crown'}
        if not required<=bag.sources:return None
        if bag.run_id not in self.receipts:
            self.receipts[bag.run_id]=RoyalRewardPolicy.receipt(bag,not self.first_claimed)
        return self.get(bag.run_id)
    def capture(self):return dict(version=1,receipts=copy.deepcopy(self.receipts),blocked=self.blocked)
    @classmethod
    def restore(cls,data):
        if not isinstance(data,dict) or data.get('version')!=1 or type(data.get('blocked',False)) is not bool or not isinstance(data.get('receipts'),dict):raise ValueError('Invalid royal history')
        receipts=copy.deepcopy(data['receipts'])
        for run_id,r in receipts.items():
            if not isinstance(run_id,str) or not 1<=len(run_id)<=64 or not isinstance(r,dict) or r.get('run_id')!=run_id:raise ValueError('Invalid royal receipt')
            if any(type(r.get(k)) is not int or not 0<=r[k]<=1000000 for k in ('tokens','tickets')):raise ValueError('Invalid royal values')
            if r.get('tier') not in ('first','replay') or not isinstance(r.get('collections'),list) or any(not isinstance(c,str) for c in r['collections']) or not set(r['collections'])<=COLLECTIONS:raise ValueError('Invalid royal reward tier')
        if sum(r['tier']=='first' for r in receipts.values())>1:raise ValueError('Repeated first clear')
        return cls(receipts,data.get('blocked',False))
    def merge(self,other):
        combined=copy.deepcopy(self.receipts)
        for id,receipt in other.receipts.items():
            if id in combined and combined[id]!=receipt:raise ValueError('Conflicting royal receipt')
            combined[id]=copy.deepcopy(receipt)
        checked=self.restore(dict(version=1,receipts=combined,blocked=self.blocked or other.blocked))
        self.receipts=checked.receipts;self.blocked=checked.blocked

class CampaignProfile:
    """A hashed player directory isolates campaigns and an authoritative clear history."""
    def __init__(self,player_id,root=None,legacy_save=None):
        if not isinstance(player_id,str) or not player_id:raise ValueError('Missing campaign owner')
        self.owner=hashlib.sha256(player_id.encode()).hexdigest()
        self.directory=Path(root or Path(__file__).parent/'profiles')/self.owner[:24]
        self.save_path=Path(legacy_save) if legacy_save is not None else self.directory/'campaign.json'
        self.history_path=self.directory/'royal_history.json'
    def load_history(self):
        if not self.history_path.exists():return RoyalClearHistory()
        data=json.loads(self.history_path.read_text())
        if not isinstance(data,dict) or data.get('owner')!=self.owner:raise ValueError('Royal history belongs to another player')
        return RoyalClearHistory.restore(data['history'])
    def save_history(self,history):
        # A bad existing file must never be silently replaced with an empty history.
        if history.blocked:return False
        disk=self.load_history();disk.merge(history)
        data=dict(owner=self.owner,history=disk.capture())
        self.directory.mkdir(parents=True,exist_ok=True)
        tmp=self.history_path.with_suffix('.json.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');tmp.replace(self.history_path)
        history.merge(disk)
        return True
