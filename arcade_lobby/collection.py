"""The collection: every COLLECTIBLE item in the registry, which ones a profile
owns and which are pinned on HOME's display shelf.

Collectibles are only for showing off - nothing here changes a stat, a price
or a payout. Ownership is the inventory (one copy each); the only thing the
profile saves here is the display order (PlayerProfile.collection_display).
"""
from item_registry import COLLECTIBLE, ITEM_REGISTRY

DISPLAY_SLOTS = 3       # how many collectibles fit on the shelf


class CollectionService:
    def __init__(self, profile, registry=ITEM_REGISTRY):
        self.profile = profile
        self.registry = registry

    def all_collectibles(self):
        """Every collectible definition, in registry order."""
        return [d for d in self.registry if d.category == COLLECTIBLE]

    def owns(self, item_id):
        return self.profile.inventory.has_item(item_id)

    def entries(self):
        """[(ItemDefinition, owned)] for the whole collection."""
        return [(d, self.owns(d.id)) for d in self.all_collectibles()]

    def progress(self):
        """(owned, total)."""
        entries = self.entries()
        return sum(1 for _, owned in entries if owned), len(entries)

    # ------------------------------------------------------------ display shelf
    def displayed(self):
        """Ids on the shelf: the saved picks that are still owned collectibles."""
        collectible = {d.id for d in self.all_collectibles()}
        picks = [i for i in self.profile.collection_display if i in collectible and self.owns(i)]
        return picks[:DISPLAY_SLOTS]

    def is_displayed(self, item_id):
        return item_id in self.displayed()

    def toggle_display(self, item_id):
        """Pin an owned collectible on the shelf, or take it off. Returns True
        if the shelf changed; False for an unowned / unknown item or a full shelf."""
        if item_id not in {d.id for d in self.all_collectibles()} or not self.owns(item_id):
            return False
        picks = self.displayed()
        if item_id in picks:
            picks.remove(item_id)
        elif len(picks) >= DISPLAY_SLOTS:
            return False
        else:
            picks.append(item_id)
        return self.profile.set_collection_display(picks)
