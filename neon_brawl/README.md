# NEON BRAWL

Original Python/Pygame beat 'em up integrated with Neon Corner Arcade.

## Launch

From `/home/nora/AOOP_Final`:

```sh
.venv/bin/python arcade_lobby/main.py
```

Choose a profile, walk left from HOME into ARCADE FLOOR, and approach the
left island cabinet, **NEON BRAWL**, at `(70, 138)` (`island_0`). Press E and
confirm the one-token play. The existing story cabinet at `island_2` remains
untouched, as do the six other games.

## Play

- WASD / arrows: move horizontally and between street lanes.
- J: light attack; successive attacks form a three-hit combo; airborne J kicks.
- K: slower, powerful uppercut that knocks enemies down.
- L: jump; high jumps avoid grounded attacks and live rails.
- U: radial special; costs 40 energy. Energy regenerates and successful hits restore it.
- I: dodge through opponents; brief invulnerability and a cooldown.
- E: collect checkpoint food before continuing.
- Enter: confirm / advance. Escape: pause; pause menu includes controls and end run.
- F4, F6–F9, M: existing host audio controls.

REX is balanced (140 HP), NOVA has faster movement/recovery (112 HP), BRUNO has
higher damage, defense, knockback and health (185 HP). Character identity
persists throughout the run, including the tutorial preview.

The 11-second opening is non-blocking and skippable. A nine-second interactive
tutorial follows character selection. Four locked encounter blocks per stage
scroll across layered pixel environments. Clearing each block grants 35 HP and
20 energy; E collects an additional 30 HP meal. Defeat ends the run.

1. **Neon Alley:** rain, shop shutters, neon skyline; Grunts and Runners teach
   spacing before Bruisers and ranged troops. WARDEN has a heavy smash and
   second-phase sweep.
2. **Abandoned Station:** transit arches, damaged displays, mixed squads and
   live rails. RELAY adds ranged bursts and phase-two sweeps.
3. **Signal Core:** server racks and circuitry; stronger mixed squads culminate
   in NULL, who alternates smash, ranged shot and phase-two sweep. Breaking
   the signal leads to an ending, results and return to the floor.

All dangerous attacks have a visible windup; only two enemies may initiate
attacks concurrently. Ranged beams hit in their marked lane. Rails flash a
warning before activation; move upward or jump. Dodge, post-hit invulnerability,
knockdown recovery and checkpoint aid prevent continuous stun loops.

## Architecture

- `data.py`: immutable stats, explicit attack timing/range/damage, wave definitions.
- `model.py`: `Fighter`, `PlayerFighter`, `EnemyFighter`, `Swing`,
  `CombatSystem`, `Campaign`. Enemy and boss polymorphism uses data-driven
  names/patterns; simulation has no Pygame dependency.
- `art.py`: cached original pixel animation cels, layered backgrounds and
  `Renderer`; host bitmap font, nearest-neighbor scaling.
- `game.py`: `BrawlGame` presentation state machine, keyboard input, focus/pause,
  input buffering, intro/tutorial/ending, HUD and results.
- `arcade_lobby/neon_brawl_scene.py`: `NeonBrawlScene`, thin lifecycle and reward
  adapter. `RoomHub` and `PlaySession` remain the only payment/settlement owners.
- `build_audio.py`: original music and SFX source, using the existing offline
  synthesizer. Four looped tracks and ten effects obey shared audio settings.

No save schema or third-party artwork/audio is introduced. The new game simply
uses `neon_brawl` in existing high scores and played-game records. Results reads
are side-effect free. The host settles once on pop/window close. Closing before
the launch wipe completes refunds the token/coupon; exiting after launch costs
the credit and pays performance tickets. Tickets are bounded at 150:
`score // 180 + stage_index * 8 + (40 if victory else 0)`.

## Automated verification

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. \
  .venv/bin/python -m unittest neon_brawl.tests.test_combat test_neon_brawl -v

SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. \
  .venv/bin/python -m unittest discover -s arcade_lobby -p 'test_*.py'

PYTHONPATH=. .venv/bin/python -m neon_brawl.tests.pilot
```

The simulation pilot uses ordinary movement/actions without changing HP,
facing, damage, rewards, or stage state. It advances checkpoints normally.
The scene integration pilot sends keyboard events through the launched adapter,
updates the real SceneManager, visits all three stages and NULL phase two,
confirms ending/results, returns to the room, and verifies payment once.
Simulation and scene-layer tests are automated verification, not human playtests.

To rebuild audio:

```sh
PYTHONPATH=arcade_lobby .venv/bin/python -m neon_brawl.build_audio
```

## Manual acceptance checks

1. Approach the cabinet normally; check prompt, payment and intro skip.
2. Try each fighter, tutorial actions, combo/J+L, special and dodge.
3. Pause, revisit controls, resume; open F4 and change volumes/mute.
4. Clear every stage; confirm rail warnings, boss windups, phase transitions,
   checkpoints, ending, result statistics and one payout on return.
5. Lose intentionally; exit via pause; close the window during play and during
   the launch wipe. Reopen and confirm no stale state or repeated rewards.
6. Enter the other games and check the story cabinet still works.

Known verification limits: rendered screenshots have been inspected, but no
live desktop/human playthrough or physical-speaker listening test is available
in this session. The optimized pilot clears in roughly 4–6 minutes; the desired
10–15 minute first-human-run duration is a balance target, not measured evidence.
Backgrounds repeat original tiles; portraits use enlarged animated character
cels. Art is generated and cached at runtime, without external asset downloads.
