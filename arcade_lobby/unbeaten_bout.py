"""TRIAL 02's tournament fights, played on NEON BRAWL's own engine (neon_brawl/, by the game's author, not changed).

NEON BRAWL is a side-scrolling street fight: a Campaign of blocks, each a squad of EnemyFighters, rendered by its Renderer
and driven by BrawlGame (fighter select, controls card, input buffering, pause menu, sounds). A tournament round is the
same machinery with one opponent in one block:

    TournamentBout(Campaign)       one arena (an existing district of Neon Alley), one opponent, no checkpoints;
                                   ends "won" / "lost" a moment after the knock-out so the fall can be seen
    TournamentFighter(EnemyFighter) THE ROOKIE / THE CHALLENGER: the regular fighters' bodies and attacks ('enemy',
                                   'double', 'lunge', 'bash', the shield troops' guard), tuned per round
    THE CHAMPION                   NEON BRAWL's own boss WARDEN with its own BossBrain patterns, at tournament health
    TournamentRenderer(Renderer)   the same world drawing with a versus HUD (both health bars) instead of the run HUD
    TournamentBrawl(BrawlGame)     the game's own select screen / controls card / pause menu, starting a bout instead of
                                   the campaign
    TournamentBoutScene            the hub scene: round banner, the fight, and the result card (RETRY / BACK TO THE HALL)

Nothing here pays anything: the bout is not a machine, so no token is taken and no ticket is given, however often a
round is fought. The hall is told the outcome through `on_result(outcome, round, selection)`.
"""
import os
import random
import sys
from dataclasses import dataclass

import pygame

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:                          # (neon_brawl lives next to arcade_lobby)
    sys.path.insert(0, _ROOT)

from font import get_font
from neon_brawl.art import Renderer
from neon_brawl.data import ATTACKS, ENEMIES, ROSTER
from neon_brawl.game import CONFIRM, MOVEMENT, BrawlGame
from neon_brawl.model import Campaign, EnemyFighter, PlayerFighter
from scene_base import BaseScene

BOSSES = ("WARDEN", "RELAY", "NULL")
FINISH = 1.6                    # seconds between the knock-out and the result card
BANNER = 2.2                    # ROUND 01 ... FIGHT!


@dataclass(frozen=True)
class Opponent:
    """One tournament opponent, made only of what NEON BRAWL already has: a body (`base`, a fighter of data.ENEMIES), its
    attacks (data.ATTACKS) and the guard the shield troops use. The numbers are the difficulty."""
    key: str
    title: str
    base: str                   # the NEON BRAWL fighter whose body, outfit and attacks it uses
    health: int
    power: float                # damage multiplier (NEON BRAWL's stage multipliers are 1.0 / 1.25 / 1.5)
    speed: float
    stage: int                  # which NEON BRAWL district is the arena (visuals only) ...
    wave: int                   # ... and which block of it
    music: str
    attacks: tuple = ("enemy",)
    gap: float = 1.2            # seconds between two attacks
    guard: float = 0.0          # chance to raise a guard against a swing in reach
    guard_rest: float = 4.0     # seconds before it may guard again
    counter: bool = False       # strikes back ('bash') the moment a guard drops
    spacing: float = 36.0       # how far it waits from the player between attacks
    strafe: float = 0.0         # pixels it steps off the player's lane between attacks (0: walks straight in)
    armor: tuple = ()           # attacks whose windup a light hit does not interrupt (only a knockdown blow does)


OPPONENTS = {
    # ROUND 01: aggressive but predictable; one simple jab, hardly ever blocks
    "rookie": Opponent("rookie", "THE ROOKIE", "grunt", health=95, power=0.8, speed=60, stage=0, wave=0, music="neon_brawl_0",
                       attacks=("enemy",), gap=1.15, guard=0.12, guard_rest=5.0, spacing=30),
    # ROUND 02: more defensive, counters from its guard, moves about between attacks
    "challenger": Opponent("challenger", "THE CHALLENGER", "duelist", health=150, power=0.95, speed=76, stage=0, wave=1,
                           music="neon_brawl_1", attacks=("double", "lunge", "enemy", "double"), gap=0.95, guard=0.5,
                           guard_rest=1.3, counter=True, spacing=62, strafe=18),
    # ROUND 03: NEON BRAWL's WARDEN, its own boss brain (charge / slam / barrage, then the wave in its second phase)
    "champion": Opponent("champion", "THE CHAMPION", "WARDEN", health=230, power=1.0, speed=46, stage=0, wave=3,
                         music="neon_brawl_3", armor=("charge", "slam")),
}
for _o in OPPONENTS.values():                     # (every body and attack really exists in NEON BRAWL)
    assert _o.base in ENEMIES and all(a in ATTACKS for a in _o.attacks + ("bash",)), _o


class TournamentFighter(EnemyFighter):
    """A regular NEON BRAWL fighter with a tournament temperament (see Opponent)."""

    def __init__(self, spec, x, y):
        super().__init__(spec.base, x, y, index=0, stage=spec.stage)
        self.spec = spec
        self.max_health = self.health = spec.health
        self.power, self.speed = spec.power, spec.speed
        self.timer = 0.9                            # a beat before the first move
        self.cooldown = 0.5
        self.guard_rest = 0.0
        self.counter_ready = False
        self.lane = 0.0
        self.lane_clock = 0.0
        self.rng = random.Random(f"tournament-{spec.key}")
        self.guards = self.counters = self.blocked = 0

    def damage(self, amount, force, knockdown=False):
        """A raised guard holds against light blows (a little damage gets through and the counter is coming); a
        knockdown blow (heavy, third combo hit, special) breaks it, as NEON BRAWL's HUD has always said."""
        if self.state == "guard" and self.timer > 0 and not knockdown and self.alive and self.invulnerable <= 0 and self.jump <= 17:
            dealt = max(1, round(amount * 0.25 / self.defense))
            self.health = max(0, self.health - dealt)
            if self.health > 0:
                self.flash, self.push, self.invulnerable = 0.1, force * 0.3, 0.2
                self.blocked += 1
                return dealt
            self.health += dealt                    # (the last blow: the normal fall)
        return super().damage(amount, force, knockdown)

    def tick(self, dt):
        super().tick(dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        self.guard_rest = max(0.0, self.guard_rest - dt)
        self.lane_clock -= dt
        if self.lane_clock <= 0:
            self.lane_clock = 1.3
            self.lane = self.rng.choice((-1, 0, 1)) * self.spec.strafe

    def think(self, dt, player, can_attack):
        if not self.ready:
            return
        s = self.spec
        dx, dy = player.x - self.x, player.y - self.y
        self.facing = 1 if dx > 0 else -1
        close = abs(dx) < 58 and abs(dy) < 16
        if self.counter_ready:
            self.counter_ready = False
            if close and can_attack and self.begin("bash", player):
                self.counters += 1
                self.cooldown = s.gap
                return
        if s.guard and self.guard_rest <= 0 and player.swing is not None and close:
            self.guard_rest = s.guard_rest
            if self.rng.random() < s.guard:
                self.state, self.timer = "guard", 0.55
                self.counter_ready = s.counter
                self.guards += 1
                return
        attack = s.attacks[self.pattern % len(s.attacks)]
        if can_attack and self.cooldown <= 0 and abs(dy) < 13 and abs(dx) <= ATTACKS[attack].reach - 2:
            if self.begin(attack, player):
                self.pattern += 1
                self.cooldown = s.gap
            return
        self.step_about(dt, player, can_attack)

    def step_about(self, dt, player, can_attack):
        s = self.spec
        ready = can_attack and self.cooldown <= 0
        side = 1 if self.x >= player.x else -1
        want = ATTACKS[s.attacks[self.pattern % len(s.attacks)]].reach * 0.6 if ready else s.spacing
        tx = player.x + side * want
        ty = player.y + (0 if ready else self.lane)
        self.x += max(-1, min(1, (tx - self.x) / 12)) * self.speed * dt
        self.y += max(-1, min(1, (ty - self.y) / 12)) * self.speed * 0.65 * dt
        self.y = max(175, min(263, self.y))
        self.state = "approach"


class ChampionFighter(EnemyFighter):
    """NEON BRAWL's boss with its own BossBrain. Its big moves (spec.armor) keep coming through light blows: dodge them,
    change lanes, or knock it down."""

    def __init__(self, spec, x, y):
        super().__init__(spec.base, x, y, 0, spec.stage)
        self.spec = spec
        self.max_health = self.health = spec.health
        self.power = spec.power
        self.armored = 0

    def damage(self, amount, force, knockdown=False):
        sw = self.swing
        if (sw is not None and sw.name in self.spec.armor and not knockdown and self.alive and self.invulnerable <= 0
                and self.jump <= 17 and sw.age < ATTACKS[sw.name].windup + ATTACKS[sw.name].active):
            dealt = max(1, round(amount / self.defense))
            if self.health - dealt > 0:
                self.health -= dealt
                self.flash, self.invulnerable = 0.14, 0.3
                self.armored += 1
                return dealt
        return super().damage(amount, force, knockdown)


def make_fighter(spec, x, y):
    if spec.base in BOSSES:
        return ChampionFighter(spec, x, y)
    return TournamentFighter(spec, x, y)


class TournamentBout(Campaign):
    """One round: the player against one opponent in one block of a NEON BRAWL district."""

    def __init__(self, opponent, character="REX"):
        super().__init__(character)
        self.spec = OPPONENTS[opponent]
        self.stage, self.wave = self.spec.stage, self.spec.wave
        left, _ = self.bounds
        self.player.x, self.player.y = left + 70, 220
        self.camera = max(0, min(1050, self.player.x - 150))
        self.finish_time = 0.0

    @property
    def opponent(self):
        return self.enemies[0] if self.enemies else None

    def spawn(self):
        _, right = self.bounds
        foe = make_fighter(self.spec, right - 95, 220)
        foe.facing = -1
        foe.arena_bounds = self.bounds
        self.enemies = [foe]
        self.encounter_age = 99.0                   # (no district / block caption: it is a tournament round)
        self.spawned = True
        self.events.append("wave")

    @property
    def tickets(self):
        return 0                                    # a tournament round never pays

    def update(self, dt, direction=(0, 0)):
        if self.state == "playing":
            super().update(dt, direction)
            if self.state in ("checkpoint", "stage_clear"):
                self.state, self.finish_time = "ko", 0.0
                self.pickups.clear()
            elif self.state == "defeat":
                self.state, self.finish_time = "down", 0.0
            return
        if self.state in ("ko", "down"):
            dt = max(0.0, min(dt, 0.05))
            self.events.clear()
            self.finish_time += dt
            for effect in self.effects:                  # (NEON BRAWL's hit sparks age the way Campaign.update ages them)
                effect.age += dt
            self.effects = [effect for effect in self.effects if effect.age < effect.duration]
            for f in [self.player] + self.enemies:
                f.vx = f.vy = 0.0
                f.tick(dt)
            if self.state == "ko" and self.player.ready:
                self.player.state = "victory"
            if self.finish_time >= FINISH:
                self.state = "won" if self.state == "ko" else "lost"


class TournamentRenderer(Renderer):
    """NEON BRAWL's renderer with a versus HUD."""
    P_COLOR, O_COLOR = (245, 80, 130), (255, 186, 90)

    def __init__(self, font, spec, round_def):
        super().__init__(font)
        self.spec, self.round = spec, round_def

    def hud(self, s, c):
        p, o = c.player, c.opponent
        s.fill((12, 10, 27), (0, 0, 400, 40))
        s.fill((60, 46, 26), (0, 39, 400, 1))
        self.text(s, p.name, 10, 4, ROSTER[p.name].color)
        s.fill((45, 35, 60), (10, 15, 150, 7))
        s.fill(self.P_COLOR, (11, 16, int(148 * p.health / p.max_health), 5))
        s.fill((45, 35, 60), (10, 25, 80, 4))
        s.fill((75, 225, 240), (11, 26, int(78 * p.energy / 100), 2))
        name = self.spec.title
        self.text(s, name, 390 - self.font.size(name)[0], 4, self.O_COLOR)
        s.fill((45, 35, 60), (240, 15, 150, 7))
        if o is not None:
            w = int(148 * max(0, o.health) / o.max_health)
            s.fill(self.O_COLOR, (241 + 148 - w, 16, w, 5))
        self.center(s, f"ROUND {self.round.number:02d}", 4, (255, 220, 120))
        self.center(s, self.round.stage, 15, (200, 190, 230))
        self.center(s, "VS", 27, (255, 105, 180))
        if c.combo > 1:
            self.text(s, f"{c.combo} HITS", 300, 44, (255, 220, 90))
        self.text(s, "J COMBO K HEAVY L JUMP U SPECIAL I DODGE ESC PAUSE", 12, 288, (150, 150, 185))
        if o is not None and o.alive and o.name in BOSSES:
            if o.state == "intro":
                self.center(s, "WATCH THE WINDUP", 76, (245, 200, 120))
            elif o.swing:
                self.center(s, o.swing.name.upper() + " // CHANGE LANES OR DODGE", 76, (245, 200, 120))
        elif o is not None and o.alive and o.state == "guard":
            self.center(s, "GUARD // HEAVY ATTACK BREAKS IT", 76, (245, 200, 120))


class TournamentBrawl(BrawlGame):
    """BrawlGame, starting a tournament bout from its own fighter select instead of the campaign."""

    def __init__(self, font, audio, round_def, selection=0, tutorial=True):
        super().__init__(font, audio)
        self.round = round_def
        self.spec = OPPONENTS[round_def.opponent]
        self.renderer = TournamentRenderer(font, self.spec, round_def)
        self.selection = selection
        self.show_tutorial = tutorial
        self.screen = "select"

    def begin(self):
        name = tuple(ROSTER)[self.selection]
        self.campaign = TournamentBout(self.round.opponent, name)
        self.tutorial_player = PlayerFighter(name)
        self.started = True
        self.change("tutorial" if self.show_tutorial else "playing")
        self.sound("confirm")

    def handle_event(self, event):
        if self.screen == "select" and event.type == pygame.KEYDOWN and not getattr(event, "repeat", False) \
                and event.key not in self._pressed and (event.key in CONFIRM or event.key == pygame.K_ESCAPE):
            self._pressed.add(event.key)
            self.held.add(event.key)
            if event.key == pygame.K_ESCAPE:
                self.wants_exit = True
            else:
                self.begin()
            return
        super().handle_event(event)


class TournamentBoutScene(BaseScene):
    """One tournament round, on screen. `on_result(outcome, round_def, selection)`, outcome "won" / "lost" / "forfeit",
    is called once, as the scene closes."""
    own_audio = True

    def __init__(self, game, round_def, on_result=None, selection=0, tutorial=True):
        super().__init__(game)
        self.round = round_def
        self.on_result = on_result
        self.audio = getattr(game, "audio", None)
        self.brawl = TournamentBrawl(get_font(), self.audio, round_def, selection, tutorial)
        self.fight_started = False
        self.banner = 0.0
        self.result = None              # None, "won" or "lost": the card is up
        self.choice = 0                 # on a lost card: 0 RETRY, 1 BACK TO THE HALL
        self.card_time = 0.0
        self.leaving = False
        self.retries = 0

    @property
    def spec(self):
        return OPPONENTS[self.round.opponent]

    @property
    def bout(self):
        return self.brawl.campaign

    @property
    def music_override(self):
        return self.spec.music

    @property
    def music_duck(self):
        return 0.45 if (self.brawl.paused or self.result) else 1.0

    def play(self, name):
        if self.audio is not None:
            self.audio.play(name)

    # ------------------------------------------------------------ flow
    def restart(self):
        """RETRY: the same round again, straight into the fight (same fighter, no select, no controls card)."""
        self.retries += 1
        self.brawl = TournamentBrawl(get_font(), self.audio, self.round, self.brawl.selection, tutorial=False)
        self.brawl.begin()
        self.fight_started = False
        self.result = None
        self.choice = 0

    def finish(self, outcome):
        if self.leaving:
            return
        self.leaving = True
        self.brawl.held.clear()
        selection = self.brawl.selection
        self.game.scenes.pop()
        if self.on_result is not None:
            self.on_result(outcome, self.round, selection)

    # ------------------------------------------------------------ input
    def handle_event(self, event):
        if self.leaving:
            return
        if self.result is not None:
            if event.type != pygame.KEYDOWN or self.card_time < 0.5:
                return
            k = event.key
            ok = k in CONFIRM or k == pygame.K_e
            if self.result == "won":
                if ok:
                    self.finish("won")
                return
            if k in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d, pygame.K_UP, pygame.K_DOWN, pygame.K_w, pygame.K_s):
                self.choice = 1 - self.choice
                self.play("machine")
            elif ok:
                self.play("confirm")
                if self.choice == 0:
                    self.restart()
                else:
                    self.finish("lost")
            elif k == pygame.K_ESCAPE:
                self.finish("lost")
            return
        if self.banner > 0 and event.type == pygame.KEYDOWN and event.key not in MOVEMENT and event.key != pygame.K_ESCAPE:
            return                                                  # (no swings before FIGHT!)
        self.brawl.handle_event(event)
        if self.brawl.wants_exit:
            self.finish("forfeit")

    # ------------------------------------------------------------ update
    def update(self, dt):
        if self.leaving:
            return
        if self.result is not None:
            self.card_time += dt
            self.brawl.time += dt
            return
        if self.banner > 0:
            self.banner = max(0.0, self.banner - dt)
            self.brawl.time += dt
            if self.banner == 0:
                self.play("brawl_special")
            return
        self.brawl.update(dt)
        if self.brawl.screen == "playing" and not self.fight_started:
            self.fight_started = True
            self.banner = BANNER
            self.play("machine")
        c = self.bout
        if c is not None and c.state in ("won", "lost"):
            self.result = c.state
            self.card_time = 0.0
            self.brawl.held.clear()
            self.play("brawl_win" if c.state == "won" else "brawl_loss")

    # ------------------------------------------------------------ drawing
    def draw(self, surf):
        self.brawl.draw(surf)
        r = self.brawl.renderer
        if self.brawl.screen in ("select", "tutorial"):
            surf.fill((12, 10, 27), (0, 258, 400, 13))
            r.center(surf, f"NEON CORNER CHAMPIONSHIP  ROUND {self.round.number:02d}  VS {self.spec.title}", 261, (255, 214, 120))
        if self.banner > 0 and self.brawl.screen == "playing":
            t = BANNER - self.banner
            band = pygame.Surface((400, 64), pygame.SRCALPHA)
            band.fill((8, 6, 20, 200))
            surf.blit(band, (0, 104))
            if t < BANNER - 0.6:
                r.center(surf, f"ROUND {self.round.number:02d}", 110, (255, 220, 120), 2)
                r.center(surf, self.round.stage, 132, (230, 220, 250))
                r.center(surf, f"YOU  VS  {self.spec.title}", 146, (255, 120, 180))
            else:
                r.center(surf, "FIGHT!", 120, (255, 90, 150), 4)
        if self.result is not None:
            self._card(surf, r)

    def _card(self, surf, r):
        shade = pygame.Surface((400, 300), pygame.SRCALPHA)
        shade.fill((5, 4, 18, 190))
        surf.blit(shade, (0, 0))
        pygame.draw.rect(surf, (20, 14, 30), (50, 70, 300, 150))
        pygame.draw.rect(surf, (214, 164, 62), (50, 70, 300, 150), 1)
        pygame.draw.rect(surf, (120, 78, 46), (53, 73, 294, 144), 1)
        c = self.bout
        if self.result == "won":
            r.center(surf, "YOU WIN!", 86, (255, 220, 120), 3)
            r.center(surf, f"ROUND {self.round.number:02d}  {self.round.stage}  CLEAR", 122, (230, 220, 250))
            r.center(surf, f"TIME {int(c.elapsed)}S   DAMAGE TAKEN {c.damage_received}", 140, (200, 190, 230))
            r.center(surf, "THE CROWD IS GOING WILD!", 160, (120, 240, 200))
            r.center(surf, "ENTER / E : BACK TO THE STAGE", 196, (255, 215, 100))
            return
        r.center(surf, "K.O.", 86, (255, 105, 140), 3)
        r.center(surf, f"{self.spec.title} TAKES THIS ONE.", 122, (230, 220, 250))
        r.center(surf, "NOTHING IS LOST. TRY THIS ROUND AGAIN?", 140, (200, 190, 230))
        for i, label in enumerate(("RETRY ROUND", "BACK TO THE HALL")):
            x = 70 + i * 138
            sel = i == self.choice
            pygame.draw.rect(surf, (90, 56, 30) if sel else (40, 26, 26), (x, 170, 122, 18))
            pygame.draw.rect(surf, (255, 214, 120) if sel else (120, 78, 46), (x, 170, 122, 18), 1)
            image = self.brawl.renderer.font.render(("> " if sel else "") + label, (255, 240, 220) if sel else (180, 150, 130))
            surf.blit(image, (x + (122 - image.get_width()) // 2, 175))
        r.center(surf, "A/D : CHOOSE   ENTER : CONFIRM", 200, (150, 150, 185))

    def on_resume(self):
        self.brawl.held.clear()
        self.brawl._pressed.clear()

    def on_exit(self):
        self.brawl.held.clear()

    def on_quit(self):
        self.brawl.held.clear()
