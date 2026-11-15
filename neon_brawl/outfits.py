"""Curated clothing families; silhouettes and equipment accompany palettes."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Outfit:
    name: str
    color: tuple
    trim: tuple
    style: str

OUTFITS = {
    'grunt': (Outfit('Leather',(48,47,66),(215,180,90),'leather'),
              Outfit('Red hood',(175,48,75),(245,145,115),'hood'),
              Outfit('Denim',(65,105,165),(175,210,220),'denim'),
              Outfit('Biker',(90,52,74),(235,160,100),'vest'),
              Outfit('Field vest',(75,105,70),(195,190,115),'military')),
    'runner': (Outfit('Track',(55,155,140),(220,245,175),'track'),
               Outfit('Night hood',(70,65,120),(155,230,220),'hood'),
               Outfit('Masked',(85,105,145),(240,165,95),'mask'),
               Outfit('Courier',(125,65,150),(105,245,220),'courier')),
    'bruiser': (Outfit('Enforcer',(90,100,125),(235,155,70),'armor'),
                Outfit('Industry',(185,115,45),(250,220,100),'worker'),
                Outfit('Lieutenant',(115,55,75),(235,160,115),'coat'),
                Outfit('Security',(55,95,115),(120,220,240),'armor')),
    'ranged': (Outfit('Neon tech',(60,105,155),(90,245,225),'tech'),
               Outfit('Signal mask',(95,60,125),(235,135,220),'mask'),
               Outfit('Tactical',(70,95,80),(220,195,125),'military'),
               Outfit('Technician',(145,115,70),(125,240,220),'worker')),
}
FAMILIES = {'duelist':'runner','shield':'bruiser','elite':'grunt','cyber':'runner',
            'security':'bruiser','sniper':'ranged','assassin':'runner','echo':'ranged'}

def outfit_for(name,index=0):
    pool=OUTFITS[FAMILIES.get(name,name)]
    return pool[index%len(pool)]

BOSS_NAMES={'WARDEN':'WARDEN / STREET KING','RELAY':'RELAY / PHANTOM ENFORCER','NULL':'SIGNAL OVERLORD'}
