"""Inventory: how many of each item the player owns.

The counts are private; everything goes through add_item / remove_item. The
inventory knows item limits (from the ItemRegistry) but not what items do or
how they look. PlayerProfile owns one and saves it with the rest of the
profile; `on_change` lets the profile announce changes so they autosave.
"""
from item_registry import ITEM_REGISTRY


class Inventory:
    def __init__(self, registry=ITEM_REGISTRY, items=None, on_change=None):
        self.registry = registry
        self.on_change = on_change
        self._counts = {}
        for item_id, quantity in (items or {}).items():
            self._counts[item_id] = quantity

    # ------------------------------------------------------------ queries
    def get_quantity(self, item_id):
        return self._counts.get(item_id, 0)

    def has_item(self, item_id, quantity=1):
        return self.get_quantity(item_id) >= quantity

    def get_all_items(self, category=None):
        """[(ItemDefinition, quantity)] for every owned item the registry
        knows, in registry order, optionally only one category. Unknown ids
        are left out (but kept for saving)."""
        return [(d, self._counts[d.id]) for d in self.registry
                if self._counts.get(d.id, 0) > 0 and category in (None, d.category)]

    @property
    def unknown_items(self):
        """Saved ids the registry no longer has, kept so nothing is lost."""
        return {k: v for k, v in self._counts.items() if k not in self.registry}

    # ------------------------------------------------------------ changes
    def add_item(self, item_id, quantity=1):
        """Add copies, up to the item's stack limit (1 if not stackable).
        Returns how many were actually added (0 if full)."""
        definition = self.registry.get(item_id)
        if definition is None:
            raise ValueError(f"unknown item {item_id!r}")
        self._check_quantity(quantity)
        owned = self._counts.get(item_id, 0)
        added = min(quantity, definition.limit - owned)
        if added > 0:
            self._counts[item_id] = owned + added
            self._changed()
        return max(added, 0)

    def remove_item(self, item_id, quantity=1):
        """Remove copies. All or nothing: returns False and changes nothing
        if fewer than `quantity` are owned."""
        self._check_quantity(quantity)
        if not self.has_item(item_id, quantity):
            return False
        left = self._counts[item_id] - quantity
        if left:
            self._counts[item_id] = left
        else:
            del self._counts[item_id]
        self._changed()
        return True

    @staticmethod
    def _check_quantity(quantity):
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError(f"quantity must be a positive int, got {quantity!r}")

    def _changed(self):
        if self.on_change:
            self.on_change()

    # ------------------------------------------------------------ save data
    def to_dict(self):
        return dict(self._counts)

    @classmethod
    def from_dict(cls, data, registry=ITEM_REGISTRY, on_change=None):
        """Rebuild from saved {item_id: quantity}. Bad entries are dropped,
        counts are clamped to the item's limit, unknown ids are kept."""
        counts = {}
        for item_id, quantity in (data.items() if isinstance(data, dict) else ()):
            if (not isinstance(item_id, str) or isinstance(quantity, bool)
                    or not isinstance(quantity, int) or quantity < 1):
                continue
            definition = registry.get(item_id)
            counts[item_id] = min(quantity, definition.limit) if definition else quantity
        return cls(registry, counts, on_change)
