"""Owner-routed neon prize counter and garage scenes."""
import pygame
from font import get_font
from scene_base import BaseScene
from input_router import PlayerInput
from .catalog import PRIZES
from .service import PrizeService


class PrizeCounterScene(BaseScene):
    KINDS = ('car','track','scenery','paint','decoration')

    def __init__(self,game,owner):
        super().__init__(game)
        self.owner = owner
        self.input = PlayerInput(owner.controls)
        self.shop = PrizeService(owner.profile)
        self.category = self.index = 0
        self.message = 'E/ENTER BUY - OWNED: EQUIP'
        self.font = get_font()
        self.spectators = [p for p in game.session if p is not owner]

    @property
    def rows(self):
        return tuple(p for p in PRIZES if p.kind == self.KINDS[self.category])

    def handle_event(self,event):
        action = self.input.feed(event)
        if event.type != pygame.KEYDOWN:
            return
        if action == 'back':
            self.game.audio.play('cancel')
            self.game.scenes.pop()
        elif action == 'menu':
            self.game.scenes.push(GarageScene(self.game,self.owner))
        elif action in ('left','right'):
            self.category = (self.category + (1 if action == 'right' else -1)) % len(self.KINDS)
            self.index = 0
        elif action in ('up','down'):
            self.index = (self.index + (1 if action == 'down' else -1)) % len(self.rows)
        elif action == 'interact':
            self.purchase_or_equip()

    def purchase_or_equip(self):
        prize = self.rows[self.index]
        if self.shop.garage.owns(prize.kind,prize.key):
            success = (self.shop.equip_decoration(prize.key) if prize.kind == 'decoration'
                       else self.shop.garage.select(prize.kind,prize.key))
            self.message = 'EQUIPPED!' if success else 'CANNOT EQUIP'
        else:
            result = self.shop.buy(prize.kind,prize.key)
            self.message,success = result.reason,result.success
        self.game.audio.play('confirm' if success else 'cancel')

    def text(self,surface,text,pos,color=(90,240,255),scale=1):
        image = self.font.render_glow(text,color,(25,15,45),scale)
        surface.blit(image,pos)

    def draw(self,surface):
        surface.fill((12,7,30))
        for y in range(0,300,12):
            pygame.draw.line(surface,(30,18,55),(0,y),(400,y))
        pygame.draw.rect(surface,(255,110,210),(8,8,384,284),2)
        self.text(surface,'PRIZE COUNTER',(20,17),(255,110,210),2)
        self.text(surface,self.owner.tag,(20,40))
        self.text(surface,f'TICKETS {self.owner.profile.tickets}',(240,40),(255,224,90))
        self.text(surface,f'< {self.KINDS[self.category].upper()} >',(20,62),(255,224,90),2)
        for i,prize in enumerate(self.rows):
            y = 90+i*23
            selected = i == self.index
            if selected:pygame.draw.rect(surface,(65,35,95),(16,y-3,368,21))
            self.text(surface,prize.name,(22,y),prize.color)
            owned = self.shop.garage.owns(prize.kind,prize.key)
            self.text(surface,'OWNED' if owned else f'{prize.cost}T LOCK',(302,y),
                      (90,240,160) if owned else (255,224,90))
        self.text(surface,self.message,(20,243),(255,224,90))
        self.text(surface,'LEFT/RIGHT CATEGORY  UP/DOWN PRIZE',(20,264))
        self.text(surface,'E BUY/EQUIP  MENU GARAGE  ESC RETURN',(20,280))


class GarageScene(PrizeCounterScene):
    KINDS = ('car','paint')

    def __init__(self,game,owner):
        super().__init__(game,owner)
        from retro_racer_scene import load_retro_racer
        game_mod,_ = load_retro_racer()
        self.preview = game_mod.GaragePreview()
        self.progression_factory = game_mod.RacerProgression
        self.message = 'CHOOSE YOUR OWNED CAR OR PAINT'

    @property
    def rows(self):
        kind = self.KINDS[self.category]
        return tuple(p for p in PRIZES if p.kind == kind and self.shop.garage.owns(kind,p.key))

    def handle_event(self,event):
        if event.type == pygame.KEYDOWN and self.input.action(event) == 'menu':
            self.game.scenes.pop()
            return
        super().handle_event(event)

    def draw(self,surface):
        super().draw(surface)
        pygame.draw.rect(surface,(12,7,30),(16,14,370,24))
        self.text(surface,'GARAGE',(20,17),(255,110,210),2)
        prize = self.rows[self.index]
        key = prize.key if prize.kind == 'car' else self.shop.garage.selected('car')
        equipped = self.shop.garage.selected('car')
        self.text(surface,f'ACTIVE: {equipped.upper()}',(20,188),(255,224,90))
        progression = self.progression_factory(self.shop.garage)
        spec = self.preview.spec(key)
        self.preview.draw(surface,key,(336,203),progression.livery(spec))
        active = self.preview.spec(equipped)
        for i,(label,value) in enumerate((('SPEED',spec.max_speed),('ACCEL',spec.acceleration),('GRIP',spec.handling))):
            baseline = (active.max_speed,active.acceleration,active.handling)[i]
            self.text(surface,f'{label} {value:.2f} / {baseline:.2f}',(22,204+i*12))
        pygame.draw.rect(surface,(12,7,30),(16,254,370,36))
        self.text(surface,'SELECTED / ACTIVE PERFORMANCE',(20,254))
        self.text(surface,'LEFT/RIGHT CAR/PAINT  UP/DOWN SELECT',(20,267))
        self.text(surface,'E EQUIP  MENU/ESC RETURN',(20,280))
