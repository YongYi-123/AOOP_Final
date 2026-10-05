"""Rewards and payment.

PAYMENT: what a minigame pays out (RewardResult) and the paid credit it pays
out against (PlaySession). The flow for every machine is:

    session = machine.start_play(profile)    # a token (or a coupon) taken once
    ... the minigame runs ...
    session.settle(minigame.get_reward())     # tickets paid exactly once

The arcade room never knows how a minigame scores; it only passes the
minigame's RewardResult to the session.

REWARDS: RewardBundle describes tokens + tickets + items to give;
RewardService.grant() delivers it safely and returns a RewardGrantResult.
Paying to enter a machine is separate from granting rewards; both use
PlayerProfile's own methods.
"""
from dataclasses import dataclass, field
from types import MappingProxyType

from item_registry import FREE_PLAY_COUPON, ITEM_REGISTRY


@dataclass(frozen=True)
class RewardResult:
    game_id: str
    tickets_earned: int = 0
    score: int | None = None    # None: the game has no score to record


class PlaySession:
    """One paid play on one machine. Created only after the tokens were
    taken; ends exactly once, by either `settle` (pay the reward) or
    `refund` (return the tokens). Every later call is ignored."""

    def __init__(self, profile, game_id, cost, name=None, coupon=False):
        self.profile = profile
        self.game_id = game_id
        self.cost = cost                # tokens paid (0 when a coupon paid instead)
        self.coupon = coupon            # True: one Free Play Coupon paid for this play
        self.name = name or game_id.upper()
        self._settled = False

    @property
    def settled(self):
        return self._settled

    def settle(self, result):
        """The game was played: count it and pay `result` (a RewardResult, or
        None for no reward). Returns the result paid, or None if this session
        was already settled or refunded."""
        if self._settled:
            return None
        if result is not None and result.game_id != self.game_id:
            raise ValueError(f"reward for {result.game_id!r} settled on a {self.game_id!r} session")
        self._settled = True
        with self.profile.batch():                      # one save for the whole payout
            self.profile.record_game_played(self.game_id)
            if self.coupon:
                self.profile.record_coupon_used()
            if result is None:
                return None
            if result.score is not None:
                self.profile.record_score(self.game_id, result.score)
            self.profile.add_tickets(result.tickets_earned)
        return result

    def refund(self):
        """The game never ran (failed to start, or the app closed before it
        opened): give back the tokens, or the coupon. Returns False if already
        settled."""
        if self._settled:
            return False
        self._settled = True
        if self.coupon:
            RewardService.grant_item(self.profile, FREE_PLAY_COUPON)
        else:
            self.profile.refund_tokens(self.cost, self.name)
        return True


@dataclass(frozen=True)
class ItemGrantResult:
    """What happened when a reward tried to give the player an item."""
    success: bool           # True if at least one copy was granted
    item_id: str
    requested_quantity: int
    granted_quantity: int
    reason: str             # "ok", "partial", "unknown_item", "invalid_quantity",
                            # "already_owned" or "stack_full"


class RewardService:
    """The safe way for rewards (prize counter, daily rewards, ...) to hand out
    tokens, tickets and items. Inventory stays strict and raises on bad input;
    this checks first, reports what happened and never raises, so a reward that
    names a missing item cannot crash the game."""

    @staticmethod
    def grant_item(profile, item_id, quantity=1):
        inventory = profile.inventory
        definition = inventory.registry.get(item_id) if isinstance(item_id, str) else None
        if definition is None:
            print(f"[reward] unknown item {item_id!r}: nothing granted")
            return ItemGrantResult(False, str(item_id), quantity, 0, "unknown_item")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            print(f"[reward] invalid quantity {quantity!r} for {item_id!r}: nothing granted")
            return ItemGrantResult(False, item_id, quantity, 0, "invalid_quantity")
        granted = inventory.add_item(item_id, quantity)
        if granted == 0:
            reason = "stack_full" if definition.stackable else "already_owned"
        else:
            reason = "ok" if granted == quantity else "partial"
        return ItemGrantResult(granted > 0, item_id, quantity, granted, reason)

    @staticmethod
    def grant(profile, bundle):
        """Deliver `bundle` to `profile`. Each part is independent: a bad
        part is skipped and reported, the rest is still granted. The whole
        bundle causes one save."""
        errors = []
        tokens = tickets = 0
        item_results = []
        with profile.batch():
            if not _is_amount(bundle.tokens):
                errors.append(f"invalid tokens amount {bundle.tokens!r}")
            elif bundle.tokens:
                profile.add_tokens(bundle.tokens, bundle.reason)
                tokens = bundle.tokens
            if not _is_amount(bundle.tickets):
                errors.append(f"invalid tickets amount {bundle.tickets!r}")
            elif bundle.tickets:
                profile.add_tickets(bundle.tickets)
                tickets = bundle.tickets
            for item_id, quantity in bundle.items.items():
                item_results.append(RewardService.grant_item(profile, item_id, quantity))
        for error in errors:
            print(f"[reward] {error}: skipped")
        return RewardGrantResult(bundle, tokens, tickets, tuple(item_results), tuple(errors))


def _is_amount(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


@dataclass(frozen=True)
class RewardBundle:
    """Everything one reward gives: tokens, tickets and items (item id ->
    quantity). Pure data; RewardService.grant() delivers it. `reason` labels
    the token transaction history."""
    tokens: int = 0
    tickets: int = 0
    items: dict = field(default_factory=dict)
    reason: str = "REWARD"

    def __post_init__(self):
        object.__setattr__(self, "items", MappingProxyType(dict(self.items)))  # read-only copy

    @property
    def is_empty(self):
        return not (self.tokens or self.tickets or self.items)

    @classmethod
    def from_config(cls, value, reason="REWARD"):
        """A bundle from settings data: a RewardBundle, a plain token amount
        (5), or a dict like {"tokens": 15, "items": {"free_play_coupon": 1}}."""
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls(reason=reason, **value)
        return cls(tokens=value, reason=reason)

    def lines(self, registry=ITEM_REGISTRY):
        """Readable lines for the UI, e.g. ['+5 TOKENS', '+1 FREE PLAY COUPON'].
        Unknown item ids are shown by id rather than hidden."""
        out = []
        if self.tokens:
            out.append(f"+{self.tokens} TOKEN" + ("" if self.tokens == 1 else "S"))
        if self.tickets:
            out.append(f"+{self.tickets} TICKET" + ("" if self.tickets == 1 else "S"))
        for item_id, quantity in self.items.items():
            definition = registry.get(item_id)
            out.append(f"+{quantity} {definition.name if definition else str(item_id).upper()}")
        return out


@dataclass(frozen=True)
class RewardGrantResult:
    """What delivering a RewardBundle actually did."""
    requested: RewardBundle
    tokens_granted: int = 0
    tickets_granted: int = 0
    item_results: tuple = ()        # one ItemGrantResult per requested item
    errors: tuple = ()              # problems with the token/ticket amounts

    @property
    def fully_granted(self):
        return (not self.errors and self.tokens_granted == self.requested.tokens
                and self.tickets_granted == self.requested.tickets
                and all(r.reason == "ok" for r in self.item_results))

    @property
    def granted_anything(self):
        return bool(self.tokens_granted or self.tickets_granted
                    or any(r.granted_quantity for r in self.item_results))

    @property
    def success(self):
        """Everything requested was granted (an empty bundle counts)."""
        return self.fully_granted

    @property
    def partial(self):
        """Something was granted, but not everything."""
        return self.granted_anything and not self.fully_granted

    @property
    def status(self):
        return "success" if self.success else "partial" if self.partial else "failed"
