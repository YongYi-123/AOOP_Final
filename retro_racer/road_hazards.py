"""Sparse original track hazards, generated independently of item/AI RNG."""
import random
from items import OilSlick


class TrackOilSlick(OilSlick):
    lifetime = float('inf')


class RoadHazards:
    """Own visible oil puddles and route contact to the existing hostile API."""
    def __init__(self,road):
        self.road = road
        self.length = road.length
        self.entities = []
        self.events = []
        self.player = None
        rng = random.Random('oil:'+road.route.key)
        count = 5
        # First puddle is in the opening view, clear of every starting grid.
        positions = [9000.0] + [i*self.length/count+rng.uniform(-2000,2000) for i in range(1,count)]
        self.puddles = [TrackOilSlick(None,z,rng.choice((-.55,0,.55))) for z in positions]

    def update(self,dt,player,opponents=()):
        self.player = player
        self.entities = [player]+list(opponents)
        for puddle in self.puddles:
            puddle.update(dt,self)

    def hostile(self,target,effect):
        landed = target.receive_hostile(effect)
        if target is self.player:
            self.events.append(effect.sound if landed else 'shield')
        return landed

    def pop_events(self):
        events,self.events = self.events,[]
        return events

    def drawables(self):
        return list(self.puddles)
