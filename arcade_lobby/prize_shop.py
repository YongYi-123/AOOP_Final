"""The Prize Counter's goods and how they are bought.

The shop sells ordinary inventory items for TICKETS; it owns no wallet and no
inventory of its own. A purchase is PlayerProfile.spend_tickets + RewardService
.grant_item inside one profile batch (one save), refunded if the item cannot be
granted, so a profile can never lose tickets for nothing or get an item for free.

Prices are decided here (cosmetics, collectibles, coupon) or by the decoration
catalogue's ticket_cost (home decorations, shared with the racing counter).
Racing cars, tracks and paints keep their own counter (racing_progression).
"""
from dataclasses import dataclass

from decorations import decoration_item_id, default_catalog
from item_registry import FREE_PLAY_COUPON, ITEM_REGISTRY
from rewards import RewardService

FREE_PLAY, HOME, COSMETICS, COLLECTIBLES = "FREE PLAY", "HOME", "COSMETICS", "COLLECT"
CATEGORIES = (FREE_PLAY, HOME, COSMETICS, COLLECTIBLES)

COUPON_PRICE = 12       # tickets: one play is worth a token, a coupon is a convenience, not a discount

# item id -> tickets, in the order the shop lists them
_COSMETIC_PRICES = {"neon_cap": 30, "cat_ears": 25, "retro_sunglasses": 35, "star_pin": 20,
                    "palette_sunset": 20, "palette_mint": 20, "palette_grape": 20, "palette_cherry": 20}
_COLLECTIBLE_PRICES = {"cat_sticker": 15, "lucky_clover": 35, "retro_badge": 40, "golden_token": 50,
                       "arcade_trophy": 60, "mini_cabinet": 75}


@dataclass(frozen=True)
class ShopEntry:
    item_id: str
    category: str
    cost: int
    name: str
    decoration_id: str = ""         # HOME entries: which decoration it unlocks


@dataclass(frozen=True)
class PurchaseResult:
    success: bool
    code: str                       # ok / unknown / owned / stack_full / need_tickets / failed
    message: str


def build_entries(registry=ITEM_REGISTRY):
    entries = [ShopEntry(FREE_PLAY_COUPON, FREE_PLAY, COUPON_PRICE, registry.get(FREE_PLAY_COUPON).name)]
    for d in default_catalog():
        if d.ticket_cost > 0:
            entries.append(ShopEntry(decoration_item_id(d.decoration_id), HOME, d.ticket_cost,
                                     d.name.upper(), d.decoration_id))
    for table, category in ((_COSMETIC_PRICES, COSMETICS), (_COLLECTIBLE_PRICES, COLLECTIBLES)):
        for item_id, cost in table.items():
            entries.append(ShopEntry(item_id, category, cost, registry.get(item_id).name))
    for e in entries:                       # a coding error, not a runtime state: fail early
        if registry.get(e.item_id) is None or e.cost <= 0:
            raise ValueError(f"bad shop entry {e!r}")
    return tuple(entries)


SHOP_ENTRIES = build_entries()


def entries_in(category):
    return [e for e in SHOP_ENTRIES if e.category == category]


def entry_for(item_id):
    return next((e for e in SHOP_ENTRIES if e.item_id == item_id), None)


class ShopService:
    """Buying for one profile."""

    def __init__(self, profile, registry=ITEM_REGISTRY):
        self.profile = profile
        self.registry = registry

    @property
    def tickets(self):
        return self.profile.tickets

    def quantity(self, entry):
        return self.profile.inventory.get_quantity(entry.item_id)

    def definition(self, entry):
        return self.registry.get(entry.item_id)

    def is_owned(self, entry):
        return self.quantity(entry) > 0

    def is_unique(self, entry):
        return not self.definition(entry).stackable

    def blocked(self, entry):
        """Why this entry cannot be bought at all right now (not about money):
        'owned' for a unique item already held, 'stack_full' for a full stack, else None."""
        definition, owned = self.definition(entry), self.quantity(entry)
        if definition is None:
            return "unknown"
        if owned >= definition.limit:
            return "owned" if not definition.stackable else "stack_full"
        return None

    def can_afford(self, entry):
        return self.profile.tickets >= entry.cost

    def purchase(self, item_id):
        """Buy one `item_id`. Every refusal changes nothing."""
        entry = entry_for(item_id)
        if entry is None:
            return PurchaseResult(False, "unknown", "NOT FOR SALE")
        why = self.blocked(entry)
        if why == "owned":
            return PurchaseResult(False, "owned", "ALREADY OWNED")
        if why == "stack_full":
            return PurchaseResult(False, "stack_full", "YOU HAVE ENOUGH")
        if why:
            return PurchaseResult(False, why, "NOT FOR SALE")
        with self.profile.batch():              # one save for the charge and the item
            if not self.profile.spend_tickets(entry.cost):
                return PurchaseResult(False, "need_tickets", "NEED MORE TICKETS")
            grant = RewardService.grant_item(self.profile, entry.item_id)
            if not grant.success:
                self.profile.refund_tickets(entry.cost)
                return PurchaseResult(False, "failed", "PURCHASE CANCELLED")
        return PurchaseResult(True, "ok", "PURCHASED!")
