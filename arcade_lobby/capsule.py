"""The two capsule machines in Prize Plaza and how a pull is paid and rewarded.

CAT CAPSULE (15 Tickets) and RETRO CAPSULE (30 Tickets) hand out collectibles, light
cosmetics and decorations - never Tokens, Tickets, coupons or anything that changes a
score or a payout. A pull is PlayerProfile.spend_tickets + RewardService.grant_item inside
one profile batch (one save), refunded if the prize cannot be granted, so Tickets are
taken exactly once and a prize is granted exactly once.

Duplicates: the capsule-only collectibles are stackable, so a repeat is simply counted
(you hold X2, X3, ...) and reported as a DUPLICATE. Wardrobe / decoration prizes are
single items, so a pull never picks one you already own; it only offers what is still new.
"""
from dataclasses import dataclass
import random

from item_registry import ITEM_REGISTRY
from rewards import RewardService

CAT, RETRO = "cat", "retro"


@dataclass(frozen=True)
class CapsulePrize:
    item_id: str
    weight: int             # relative chance within its machine


@dataclass(frozen=True)
class CapsuleMachineSpec:
    kind: str
    name: str
    cost: int               # Tickets per pull
    prizes: tuple


CAPSULE_MACHINES = {
    CAT: CapsuleMachineSpec(CAT, "CAT CAPSULE", 15, tuple(CapsulePrize(i, w) for i, w in (
        ("cat_paw_sticker", 26), ("cat_bell_charm", 22), ("cat_fish_badge", 16), ("cat_yarn_ball", 14),
        ("cat_sticker", 8), ("star_hair_clip", 6), ("decor_cat_plush", 5), ("cat_mochi_plush", 5),
        ("cat_champion_cup", 4), ("cat_ears", 3), ("cat_tail", 2)))),
    RETRO: CapsuleMachineSpec(RETRO, "RETRO CAPSULE", 30, tuple(CapsulePrize(i, w) for i, w in (
        ("retro_pixel_heart", 24), ("retro_cartridge", 20), ("retro_mini_joystick", 15), ("retro_star_medal", 13),
        ("retro_badge", 7), ("star_pin", 7), ("retro_silver_cup", 6), ("retro_sunglasses", 4),
        ("neon_headphones", 3), ("arcade_trophy", 3), ("champion_badge", 2), ("retro_gold_trophy", 2),
        ("mini_cabinet", 1)))),
}


def spec_for(kind):
    return CAPSULE_MACHINES.get(kind)


@dataclass(frozen=True)
class CapsuleResult:
    success: bool
    code: str               # ok / unknown / need_tickets / failed
    message: str
    item_id: str = ""
    name: str = ""
    duplicate: bool = False     # True: the player already held this item before the pull
    count: int = 0              # how many they hold now
    cost: int = 0               # Tickets actually charged (0 on any refusal)


def _fail(code, message):
    return CapsuleResult(False, code, message)


class CapsuleService:
    """Pulling from a capsule machine for one profile."""

    def __init__(self, profile, rng=None, registry=ITEM_REGISTRY, machines=None):
        self.profile = profile
        self.rng = rng or random.Random()
        self.registry = registry
        self.machines = machines or CAPSULE_MACHINES

    def spec(self, kind):
        return self.machines.get(kind)

    def quantity(self, item_id):
        return self.profile.inventory.get_quantity(item_id)

    def can_afford(self, kind):
        spec = self.spec(kind)
        return spec is not None and self.profile.tickets >= spec.cost

    def available(self, kind):
        """The prizes this profile can still be given: a single-copy item they own is
        left out, and so is a stack that is full."""
        spec = self.spec(kind)
        out = []
        for prize in spec.prizes if spec else ():
            definition = self.registry.get(prize.item_id)
            if definition is not None and self.quantity(prize.item_id) < definition.limit:
                out.append(prize)
        return out

    def pull(self, kind):
        """Pay for one capsule and receive its prize. A refusal changes nothing."""
        spec = self.spec(kind)
        if spec is None:
            return _fail("unknown", "OUT OF ORDER")
        if not self.can_afford(kind):
            return _fail("need_tickets", f"NEED {spec.cost - self.profile.tickets} MORE TICKETS")
        pool = self.available(kind)
        if not pool:
            return _fail("failed", "MACHINE IS EMPTY")
        prize = self.rng.choices(pool, weights=[p.weight for p in pool])[0]
        before = self.quantity(prize.item_id)
        with self.profile.batch():                  # one save for the charge and the prize
            if not self.profile.spend_tickets(spec.cost):
                return _fail("need_tickets", "NEED MORE TICKETS")
            grant = RewardService.grant_item(self.profile, prize.item_id)
            if not grant.success:
                self.profile.refund_tickets(spec.cost)
                return _fail("failed", "CAPSULE JAMMED - NOT CHARGED")
        definition = self.registry.get(prize.item_id)
        duplicate = before > 0
        count = self.quantity(prize.item_id)
        message = f"DUPLICATE!  YOU HAVE X{count}" if duplicate else "NEW!"
        return CapsuleResult(True, "ok", message, prize.item_id, definition.name, duplicate, count, spec.cost)
