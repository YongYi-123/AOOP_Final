"""Arcade adapter; RoomHub alone owns payment and exactly-once settlement."""
from minigame import MinigameScene, MiniGameResult, PlayerResult
from rewards import RewardBundle
from font import get_font
from neon_brawl.game import BrawlGame

class NeonBrawlScene(MinigameScene):
    def __init__(self,game,machine):
        super().__init__(game,machine)
        self.brawl=BrawlGame(get_font(),getattr(game,'audio',None))
        self.leaving=False

    @property
    def music_override(self):
        c = self.brawl.campaign
        boss = c and any(e.boss and e.alive for e in c.enemies)
        return f"neon_brawl_{3 if boss else c.stage if c else 0}"

    @property
    def music_duck(self): return .45 if self.brawl.paused else 1.
    def handle_event(self,event):
        if not self.leaving:
            self.brawl.handle_event(event)
            if self.brawl.wants_exit:
                self.leaving=True
                self.game.scenes.pop()
    def update(self,dt):
        if not self.leaving: self.brawl.update(dt)
    def draw(self,surface): self.brawl.draw(surface)
    def get_result(self):
        result=self.brawl.result()
        return MiniGameResult(tuple(PlayerResult(p.profile_id,result['score'],
            RewardBundle(tickets=result['tickets'],reason='NEON BRAWL')) for p in self.participants[:1]))
    def on_resume(self):
        self.brawl.held.clear()
        self.brawl._pressed.clear()
    def on_exit(self): self.brawl.held.clear()
    def on_quit(self): self.brawl.held.clear()
