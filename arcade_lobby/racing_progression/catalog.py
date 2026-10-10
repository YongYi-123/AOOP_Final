"""Original prize catalogue; definitions contain no wallet or rendering logic."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RacingPrize:
    kind: str
    key: str
    name: str
    cost: int
    color: tuple = (90,240,255)

    @property
    def item_id(self):
        return f'racing_{self.kind}_{self.key}'

    @property
    def free(self):
        return self.cost == 0


PRIZES = (
    RacingPrize('car','falcon','FALCON',0,(214,26,36)),
    RacingPrize('car','comet','COMET / ACCELERATION',80,(255,132,24)),
    RacingPrize('car','viper','VIPER / TOP SPEED',120,(150,48,210)),
    RacingPrize('car','titan','TITAN / DURABILITY',100,(116,128,144)),
    RacingPrize('track','emerald','EMERALD GP',0),
    RacingPrize('track','harbor','HARBOR SPRINT',60),
    RacingPrize('track','summit','SUMMIT RING',80),
    RacingPrize('track','starlight','STARLIGHT QUAYS',100),
    RacingPrize('track','cloudpass','CLOUDPASS RIDGE',120),
    RacingPrize('track','aurora','AURORA GRAND PRIX',150),
    RacingPrize('track','switchyard','SWITCHYARD CIRCUIT',160),
    RacingPrize('scenery','suburbs','SUBURBS',0),
    RacingPrize('scenery','city','NEON CITY',30),
    RacingPrize('scenery','beach','BEACH',30),
    RacingPrize('scenery','desert','DESERT',30),
    RacingPrize('scenery','sunset_coast','SUNSET SEA',40),
    RacingPrize('scenery','forest','FOREST',40),
    RacingPrize('paint','factory','FACTORY PAINT',0),
    RacingPrize('paint','tuxedo','TUXEDO WHITE',25,(235,235,245)),
    RacingPrize('paint','neon','NEON PINK',25,(255,80,185)),
    RacingPrize('paint','amber','AMBER GOLD',35,(245,185,55)),
    RacingPrize('paint','ice','ICE BLUE',35,(70,200,245)),
    RacingPrize('paint','crimson','CRIMSON RED',40,(225,45,70)),
    RacingPrize('paint','violet','MIDNIGHT VIOLET',40,(120,75,195)),
    RacingPrize('decoration','poster_cat','TUXEDO CAT POSTER',25,(220,220,240)),
    RacingPrize('decoration','rug_teal','TEAL GARAGE RUG',35,(65,185,175)),
    RacingPrize('decoration','neon_heart','NEON HEART',40,(255,110,180)),
    RacingPrize('decoration','bed_blue','BLUE CAT BED',30,(90,150,220)),
    RacingPrize('decoration','poster_arcade','ARCADE WALL POSTER',20,(255,110,210)),
    RacingPrize('decoration','neon_star','NEON STAR',35,(255,224,90)),
)
DEFAULTS = {'car':'falcon','track':'emerald','scenery':'suburbs','paint':'factory'}


def prize_for(kind,key):
    return next((p for p in PRIZES if p.kind == kind and p.key == key),None)
