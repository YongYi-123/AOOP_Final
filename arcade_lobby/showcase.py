"""The Prize Plaza SHOWCASE: one owned car, one collectible and one trophy a player
chooses to put on display.

Pure show: nothing here changes a stat, a price or a payout. The profile saves only the
choice (PlayerProfile.showcase: slot -> car key / item id); ownership is the inventory and
the racing garage, checked every time the showcase is read, so an item that is no longer
owned (or a removed one) just leaves an empty pedestal and never breaks a save.
"""
from dataclasses import dataclass

from item_registry import COLLECTIBLE, ITEM_REGISTRY
from player_profile import SHOWCASE_SLOTS
from racing_progression.catalog import PRIZES
from racing_progression.service import RacingGarage

CAR, COLLECTIBLE_SLOT, TROPHY = SHOWCASE_SLOTS
SLOT_NAMES = {CAR: "CAR", COLLECTIBLE_SLOT: "COLLECTIBLE", TROPHY: "TROPHY"}

# Prize-like items that can stand in the TROPHY slot (the COLLECTIBLE slot shows the other collectibles).
TROPHY_IDS = ("arcade_trophy", "champion_badge", "cat_champion_cup", "retro_silver_cup", "retro_gold_trophy",
              "retro_star_medal")


@dataclass(frozen=True)
class ShowcaseOption:
    slot: str
    value: str              # what is saved: a car key or an item id
    name: str
    color: tuple
    accent: tuple
    shape: str              # "car", or an item_icons shape
    count: int = 1          # copies owned (a stackable collectible)


class ShowcaseService:
    """Choosing what a profile displays."""

    def __init__(self, profile, registry=ITEM_REGISTRY):
        self.profile = profile
        self.registry = registry
        self.garage = RacingGarage(profile)

    # ------------------------------------------------------------ what can be shown
    def options(self, slot):
        """Everything the profile owns that fits `slot`, in a stable order."""
        if slot == CAR:
            return [ShowcaseOption(CAR, p.key, p.name.split("/")[0].strip(), p.color, (255, 250, 220), "car")
                    for p in PRIZES if p.kind == "car" and self.garage.owns("car", p.key)]
        if slot not in SHOWCASE_SLOTS:
            return []
        out = []
        for definition, count in self.profile.inventory.get_all_items(COLLECTIBLE):
            if (definition.id in TROPHY_IDS) != (slot == TROPHY):
                continue
            out.extend([self._item_option(slot, definition, count)])
        if slot == TROPHY:                      # a few trophy-like badges are cosmetics rather than collectibles
            for definition, count in self.profile.inventory.get_all_items():
                if definition.category != COLLECTIBLE and definition.id in TROPHY_IDS:
                    out.append(self._item_option(slot, definition, count))
        return out

    @staticmethod
    def _item_option(slot, definition, count):
        icon = definition.icon
        return ShowcaseOption(slot, definition.id, definition.name, icon.get("color", (255, 214, 90)),
                              icon.get("accent", (255, 250, 220)), icon.get("shape", ""), count)

    # ------------------------------------------------------------ the current choice
    def displayed(self, slot):
        """The ShowcaseOption now on display in `slot`, or None (nothing chosen, or no longer owned)."""
        value = self.profile.showcase.get(slot)
        if value is None:
            return None
        return next((o for o in self.options(slot) if o.value == value), None)

    def all_displayed(self):
        return {slot: self.displayed(slot) for slot in SHOWCASE_SLOTS}

    def choose(self, slot, value):
        """Display `value` in `slot`. False (nothing changes) if it is not owned / does not fit."""
        if not any(o.value == value for o in self.options(slot)):
            return False
        self.profile.set_showcase(slot, value)
        return True

    def clear(self, slot):
        if slot not in SHOWCASE_SLOTS:
            return False
        return self.profile.set_showcase(slot, None)
