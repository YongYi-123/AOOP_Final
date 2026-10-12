"""NEON VEND-O-MATIC: the novelty-item vending machine on the Arcade Floor.

It sells ordinary inventory items (CONSUMABLE, see item_registry) for TICKETS and reuses the Prize
Counter's ShopService, so a purchase is the same all-or-nothing profile batch: the charge and the
item land together or not at all, a profile can never go below zero Tickets, and the goods go to the
profile of the player who pressed the key. Only the stock is different.

Novelty goods are stackable up to NOVELTY_STACK; a full stack refuses the sale ("POCKETS FULL") so
nothing is charged for an item that could not be handed over.
"""
from prize_shop import PurchaseResult, ShopEntry, ShopService
from item_registry import ITEM_REGISTRY

VEND = "VEND"

# item id -> tickets, in the order the machine lists them (top shelf first)
_PRICES = (("suspicious_soda", 5), ("invisible_sandwich", 8), ("pocket_rainbow", 12),
           ("rubber_duck", 15), ("questionable_battery", 20), ("mystery_can", 25))

VEND_ENTRIES = tuple(ShopEntry(item_id, VEND, cost, ITEM_REGISTRY.get(item_id).name)
                     for item_id, cost in _PRICES)


def vend_entry(item_id):
    return next((e for e in VEND_ENTRIES if e.item_id == item_id), None)


class VendingService(ShopService):
    """Buying from the machine for one profile."""

    entries = VEND_ENTRIES

    def find_entry(self, item_id):
        return vend_entry(item_id)

    def purchase(self, item_id):
        result = super().purchase(item_id)
        if result.code == "stack_full":
            return PurchaseResult(False, "stack_full", "POCKETS FULL")
        if result.success:
            return PurchaseResult(True, "ok", "ENJOY!")
        return result
