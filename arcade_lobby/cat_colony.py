"""CatColony: the cats living in one hub room, and the shared rules between them.

The colony is the cats' view of the world: the player, the room's collision,
places cats should keep clear of (machine fronts, doorways), the single
follow slot and the shared meow cooldown. Every room scene owns one colony
with only the cats that live there (a cat is never in two rooms); minigame
scenes never see it, and pause()/resume() bracket a minigame or a room change
so cats stop cleanly and pick up where they were afterwards."""
import math
import random

from cat import CatNPC, CatProfile, CatState


class CatColony:
    INTERACT_RANGE = 24      # player <-> cat distance for the [E] prompt
    AMBIENT_GAP = 4.0        # seconds between unprompted meows, across all cats
    PUSH_TIME = 0.35         # player bumping a cat this long makes it step aside

    def __init__(self, roster, room, rng=None):
        self.rng = rng or random.Random()
        self.room_solids = room.solids
        # Cats never pick a spot in front of a machine or in a doorway.
        self.keep_clear = [m.zone for m in room.machines]
        self.keep_clear += [p.zone for p in room.props if hasattr(p, "zone")]   # stations
        self.keep_clear += list(room.keep_clear_areas)
        self.cats = [CatNPC(CatProfile.from_data(data), room.cat_spots[data["id"]],
                            random.Random(self.rng.random()))
                     for data in roster]
        self.player = None
        self.follower = None
        self.paused = False
        self.ambient_cooldown = self.AMBIENT_GAP
        self.push_time = 0.0
        self._last_player_pos = None

    def __iter__(self):
        return iter(self.cats)

    def __len__(self):
        return len(self.cats)

    def get(self, cat_id):
        return next((c for c in self.cats if c.profile.id == cat_id), None)

    # ------------------------------------------------------ world for cats
    def is_free(self, point, avoid=True):
        """Can a cat stand here without overlapping furniture (or, with
        avoid=True, a machine front or the doorway)?"""
        feet = CatNPC.feet_at(*point)
        if feet.collidelist(self.room_solids) != -1:
            return False
        return not (avoid and feet.collidelist(self.keep_clear) != -1)

    def cat_solids(self):
        """What a walking cat collides with: furniture and the player."""
        return self.room_solids + [self.player.feet]

    def request_follow(self, cat):
        """Only one cat follows the player at a time."""
        if self.follower is None or self.follower is cat:
            self.follower = cat
            return True
        return False

    def stop_following(self):
        if self.follower is not None and self.follower.state == CatState.FOLLOW:
            self.follower.anchor = self.follower.position
            self.follower.set_state(CatState.SIT)
        self.follower = None

    def claim_ambient_meow(self):
        if self.ambient_cooldown > 0:
            return False
        self.ambient_cooldown = self.AMBIENT_GAP
        return True

    # ------------------------------------------------------ player side
    def blockers(self, player):
        """Cat collision boxes for the player. A cat already overlapping the
        player is left out, so the player can always walk free of it, and so
        is the follower, which trots at the player's heels."""
        feet = player.feet
        return [c.feet for c in self.cats
                if c is not self.follower and not c.feet.colliderect(feet)]

    def find_nearby(self, player):
        """The closest cat that can be petted right now, or None."""
        best, best_d = None, self.INTERACT_RANGE
        for cat in self.cats:
            d = cat.distance_to(player)
            if d < best_d and cat.can_pet:
                best, best_d = cat, d
        return best

    def interact(self, cat):
        """Pet a cat (E). Returns True only if it actually reacted."""
        if self.paused or cat is None:
            return False
        if self.follower is cat:
            self.follower = None
        return cat.pet(self)

    # ------------------------------------------------------ per frame
    def update(self, dt, player, busy=False):
        self.player = player
        if self.paused:
            return
        self.ambient_cooldown -= dt
        if busy:
            self.stop_following()
        if self.follower is not None and self.follower.state != CatState.FOLLOW:
            self.follower = None
        self._check_push(dt, player)
        for cat in self.cats:
            cat.update(dt, self)

    def _check_push(self, dt, player):
        """If the player keeps walking into a cat without getting anywhere,
        the cat steps aside so it can never trap them (e.g. in a doorway)."""
        pos = (player.x, player.y)
        stuck = (player.moving and self._last_player_pos is not None
                 and math.dist(pos, self._last_player_pos) < 0.2)
        self._last_player_pos = pos
        touching = None
        if stuck:
            reach = player.feet.inflate(4, 4)
            touching = next((c for c in self.cats if c.feet.colliderect(reach)), None)
        self.push_time = self.push_time + dt if touching else 0.0
        if touching and self.push_time >= self.PUSH_TIME:
            touching.make_way(self, player)
            self.push_time = 0.0

    def pause(self):
        """Entering a minigame: stop following, meowing and bubbles."""
        self.paused = True
        self.stop_following()
        for cat in self.cats:
            cat.settle()

    def resume(self):
        self.paused = False
        self.push_time = 0.0
        self._last_player_pos = None

    # ------------------------------------------------------ draw
    def drawables(self):
        return self.cats

    def draw_overlay(self, surf):
        for cat in self.cats:
            cat.draw_bubble(surf)
