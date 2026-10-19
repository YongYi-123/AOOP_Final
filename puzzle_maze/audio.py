"""Original synthesized chiptune and cues, with silent fallback."""
import math
from array import array
import pygame

class AudioManager:
    def __init__(self):
        self.enabled = False
        self.sounds = {}
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self.enabled = True
            for name,freq in [('step',180),('use',520),('key',880),('solve',1046),('pulse',330),('attack',440),('hit',170),('hurt',110),('heal',740),('defeat',660),('bomb_place',280),('explosion',70),('shield',130),('teleport',620),('projectile',410),('ignite',570),('pot_lift',230),('pot_break',90),('crystal',960),('order_wrong',140),('order_step',760),('chest_spawn',1320),('wall_break',85),('boss_break',1180)]:
                self.sounds[name]=self.tone(freq,.09 if name=='step' else .25)
            notes=[261.63,329.63,392,523.25,440,392,329.63,293.66,
                   220,261.63,329.63,440,392,329.63,293.66,246.94]
            samples=array('h')
            for f in notes:
                for i in range(11025):
                    t=i/22050
                    env=min(1,t*20)*max(0,1-t/.5)
                    v=math.sin(2*math.pi*f*t)*.6+math.sin(2*math.pi*(f/2)*t)*.25
                    samples.append(int(v*env*1900))
            self.music=pygame.mixer.Sound(buffer=samples)
            self.music_channel=pygame.mixer.Channel(0)
            self.music_channel.play(self.music,loops=-1)
        except (pygame.error, OSError):
            self.enabled=False

    def tone(self,freq,duration):
        rate=22050
        data=array('h',(int(math.sin(2*math.pi*freq*i/rate)*2500*(1-i/(rate*duration))) for i in range(int(rate*duration))))
        return pygame.mixer.Sound(buffer=data)

    def play(self,name):
        if self.enabled and name in self.sounds:
            channel=pygame.mixer.find_channel()
            if channel and channel != self.music_channel:
                channel.play(self.sounds[name])

    def toggle(self):
        if self.enabled:
            if self.music_channel.get_busy():self.music_channel.stop()
            else:self.music_channel.play(self.music,loops=-1)
