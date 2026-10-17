"""MOCHI'S CAPSULE EXCHANGE: turn spare capsule collectibles into Capsule Stamps, and Stamps into
a chosen capsule prize.

RECYCLE: only the capsule-only stackable collectibles listed below, only the copies beyond the
last one (you always keep one - which also keeps any copy the Showcase displays). CAT items give
3 Stamps per spare copy, RETRO items 6.
REDEEM: any prize either capsule machine can give, for a Stamp price set by rarity
(COMMON 12, UNCOMMON 18, RARE 25, EPIC 45). A single-copy item you already own, or a full stack,
cannot be redeemed.

Economy: Stamps exist only as the proceeds of giving up a spare collectible, so there is no
passive source. The best recycle value (6) is at most half the cheapest redeem price (12), so a
redeem -> recycle loop always loses Stamps and can never mint them. Stamps are a bare balance on
the profile (PlayerProfile.capsule_stamps), not an item, and cannot become Tokens, Tickets or
anything else. Both operations are one profile batch (one save) that either happens completely or
not at all.
"""
from dataclasses import dataclass

from capsule import CAPSULE_MACHINES, CAT, RETRO
from item_registry import COLLECTIBLE, COMMON, EPIC, ITEM_REGISTRY, RARE, UNCOMMON
from player_profile import MAX_CAPSULE_STAMPS
from rewards import RewardService

# explicit ids (never decided from a display name): the capsule-only stackable collectibles
RECYCLABLE = {
    **{i: 3 for i in ("cat_paw_sticker", "cat_bell_charm", "cat_fish_badge", "cat_yarn_ball",
                      "cat_mochi_plush", "cat_champion_cup")},
    **{i: 6 for i in ("retro_pixel_heart", "retro_cartridge", "retro_mini_joystick", "retro_star_medal",
                      "retro_silver_cup", "retro_gold_trophy")},
}
KEEP = 1                                    # copies that can never be recycled
PRICES = {COMMON: 12, UNCOMMON: 18, RARE: 25, EPIC: 45}
REDEEMABLE = tuple(dict.fromkeys(p.item_id for kind in (CAT, RETRO) for p in CAPSULE_MACHINES[kind].prizes))


def recycle_value(item_id):
    """Stamps one spare copy is worth (0 = not recyclable)."""
    return RECYCLABLE.get(item_id, 0)


def redeem_price(item_id, registry=ITEM_REGISTRY):
    definition = registry.get(item_id)
    return PRICES.get(definition.rarity, 0) if definition and item_id in REDEEMABLE else 0


@dataclass(frozen=True)
class ExchangeResult:
    success: bool
    code: str           # ok / unknown / not_recyclable / no_spare / bad_quantity / stamp_full / owned / full / need_stamps / failed
    message: str
    item_id: str = ""
    name: str = ""
    quantity: int = 0   # copies recycled / granted
    stamps: int = 0     # Stamps gained (recycle) or spent (redeem)


@dataclass(frozen=True)
class RecycleEntry:
    item_id: str
    name: str
    owned: int
    spare: int          # copies that may be recycled right now
    value: int          # Stamps per copy
    displayed: bool     # the Showcase currently shows it (the kept copy)


@dataclass(frozen=True)
class RedeemEntry:
    item_id: str
    name: str
    rarity: str
    price: int
    owned: int
    status: str         # ok / owned / full / need_stamps


def _fail(code, message, item_id="", name=""):
    return ExchangeResult(False, code, message, item_id, name)


class ExchangeService:
    """The exchange for one profile (so P1 and P2 each have their own)."""

    def __init__(self, profile, registry=ITEM_REGISTRY):
        self.profile = profile
        self.registry = registry

    @property
    def stamps(self):
        return self.profile.capsule_stamps

    def owned(self, item_id):
        return self.profile.inventory.get_quantity(item_id)

    # ------------------------------------------------------------ recycle
    def _recyclable(self, item_id):
        d = self.registry.get(item_id) if isinstance(item_id, str) else None
        return d if d is not None and recycle_value(item_id) and d.stackable and d.category == COLLECTIBLE else None

    def spare(self, item_id):
        """Copies that can be recycled: everything but the last one."""
        return max(0, self.owned(item_id) - KEEP) if self._recyclable(item_id) else 0

    def _displayed(self, item_id):
        return item_id in self.profile.showcase.values()

    def recycle_entries(self):
        """Every recyclable item the profile owns (even with nothing spare), registry order."""
        out = []
        for d in self.registry:
            if self._recyclable(d.id) and self.owned(d.id):
                out.append(RecycleEntry(d.id, d.name, self.owned(d.id), self.spare(d.id), recycle_value(d.id),
                                        self._displayed(d.id)))
        return out

    def max_recycle(self, item_id):
        """The most copies one recycle may take: the spares that also fit in the Stamp book."""
        value = recycle_value(item_id)
        room = (MAX_CAPSULE_STAMPS - self.stamps) // value if value else 0
        return min(self.spare(item_id), room)

    def preview(self, item_id, quantity):
        """The exact Stamps a recycle of `quantity` copies would pay (0 if it would be refused)."""
        if (isinstance(quantity, bool) or not isinstance(quantity, int)
                or not 1 <= quantity <= self.max_recycle(item_id)):
            return 0
        return recycle_value(item_id) * quantity

    def recycle(self, item_id, quantity=1):
        d = self._recyclable(item_id)
        if d is None:
            return _fail("not_recyclable", "MOCHI CANNOT TAKE THAT", str(item_id))
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            return _fail("bad_quantity", "PICK AT LEAST ONE", item_id, d.name)
        if self.spare(item_id) < 1:
            return _fail("no_spare", "KEEP YOUR LAST COPY", item_id, d.name)
        if quantity > self.spare(item_id):
            return _fail("no_spare", "NOT ENOUGH SPARES", item_id, d.name)
        pay = recycle_value(item_id) * quantity
        if self.stamps + pay > MAX_CAPSULE_STAMPS:
            return _fail("stamp_full", "STAMP BOOK IS FULL", item_id, d.name)
        with self.profile.batch():                      # one save: the copies leave and the Stamps arrive together
            if not self.profile.consume_item(item_id, quantity):
                return _fail("no_spare", "NOT ENOUGH SPARES", item_id, d.name)
            self.profile.add_capsule_stamps(pay)
        return ExchangeResult(True, "ok", f"+{pay} STAMPS", item_id, d.name, quantity, pay)

    # ------------------------------------------------------------ redeem
    def status(self, item_id):
        d = self.registry.get(item_id)
        if d is None or item_id not in REDEEMABLE:
            return "unknown"
        if self.owned(item_id) >= d.limit:
            return "owned" if not d.stackable else "full"
        return "ok" if self.stamps >= redeem_price(item_id, self.registry) else "need_stamps"

    def redeem_entries(self):
        """Every redeemable prize with its price and status, cheapest first (then registry order)."""
        out = []
        for item_id in REDEEMABLE:
            d = self.registry.get(item_id)
            if d is not None:
                out.append(RedeemEntry(item_id, d.name, d.rarity, redeem_price(item_id, self.registry),
                                       self.owned(item_id), self.status(item_id)))
        return sorted(out, key=lambda e: e.price)

    def redeem(self, item_id):
        d = self.registry.get(item_id) if isinstance(item_id, str) else None
        if d is None or item_id not in REDEEMABLE:
            return _fail("unknown", "NOT ON THE EXCHANGE", str(item_id))
        price = redeem_price(item_id, self.registry)
        status = self.status(item_id)
        if status == "owned":
            return _fail("owned", "YOU ALREADY HAVE THIS", item_id, d.name)
        if status == "full":
            return _fail("full", "YOU HAVE ENOUGH", item_id, d.name)
        if status == "need_stamps":
            return _fail("need_stamps", f"NEED {price - self.stamps} MORE STAMPS", item_id, d.name)
        with self.profile.batch():                      # one save: the Stamps leave and the prize arrives together
            if not self.profile.spend_capsule_stamps(price):
                return _fail("need_stamps", "NEED MORE STAMPS", item_id, d.name)
            grant = RewardService.grant_item(self.profile, item_id)
            if not grant.success:
                self.profile.add_capsule_stamps(price)  # put them back: nothing was given
                return _fail("failed", "EXCHANGE CANCELLED - STAMPS KEPT", item_id, d.name)
        return ExchangeResult(True, "ok", "ENJOY!", item_id, d.name, 1, price)
