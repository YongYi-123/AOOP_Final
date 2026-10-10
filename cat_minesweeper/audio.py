"""Reuse the lobby's own cat voices, with isolated cooldowns and channels."""
from arcade_lobby.cat_voice import CatVoice, MeowBank


class MineSounds:
    def __init__(self):
        bank = MeowBank()
        self.click_voice = CatVoice(pitch=1.15, volume=.22, bank=bank)
        self.result_voice = CatVoice(pitch=.95, volume=.35, bank=bank)

    def play(self, event, now):
        if event in ("win", "loss"):
            self.result_voice.play("prrr" if event == "win" else "meow", now)
        else:
            self.click_voice.play("mew" if event == "reveal" else "mrrp", now)

    def stop(self):
        self.click_voice.stop()
        self.result_voice.stop()
