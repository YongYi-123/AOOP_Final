"""One profile owns each shop and garage. Inventory is the unlock ledger."""
from dataclasses import dataclass
from rewards import RewardService
from .catalog import PRIZES, DEFAULTS, prize_for


@dataclass(frozen=True)
class PurchaseResult:
    success: bool
    reason: str


class RacingGarage:
    def __init__(self,profile):
        self.profile = profile

    def owns(self,kind,key):
        prize = prize_for(kind,key)
        return prize is not None and (prize.free or self.profile.inventory.has_item(prize.item_id))

    def selected(self,kind):
        key = self.profile.racing_selection.get(kind,DEFAULTS.get(kind))
        return key if self.owns(kind,key) else DEFAULTS.get(kind)

    def select(self,kind,key):
        if kind not in DEFAULTS or not self.owns(kind,key):
            return False
        self.profile.set_racing_selection(kind,key)
        return True

    def owned_cars(self):
        return tuple(p for p in PRIZES if p.kind == 'car' and self.owns('car',p.key))


class PrizeService:
    def __init__(self,profile):
        self.profile = profile
        self.garage = RacingGarage(profile)

    def buy(self,kind,key):
        prize = prize_for(kind,key)
        if prize is None:
            return PurchaseResult(False,'UNKNOWN PRIZE')
        if self.garage.owns(kind,key):
            return PurchaseResult(False,'ALREADY OWNED')
        if self.profile.inventory.registry.get(prize.item_id) is None:
            return PurchaseResult(False,'PRIZE UNAVAILABLE')
        with self.profile.batch():
            if not self.profile.spend_tickets(prize.cost):
                return PurchaseResult(False,'NEED MORE TICKETS')
            grant = RewardService.grant_item(self.profile,prize.item_id)
            if not grant.success:
                self.profile.refund_tickets(prize.cost)
                return PurchaseResult(False,'PURCHASE REFUNDED')
        return PurchaseResult(True,'UNLOCKED!')

    def equip_decoration(self,key):
        if not self.garage.owns('decoration',key):
            return False
        from decorations import HomeDecorationManager, default_catalog
        from home_room import HOME_SLOTS
        manager = HomeDecorationManager(self.profile, HOME_SLOTS, default_catalog())
        try:
            for slot_id in manager.slots:
                if manager.can_equip(slot_id,key):
                    return manager.equip(slot_id,key)
            return False
        finally:
            manager.close()
