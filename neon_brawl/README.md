# NEON BRAWL 環境擴充更新

目前版本保留既有控制、戰鬥、敵群、頭目、機台與票券結算，新增：

- 四區香港風格霓虹夜街：直式英文招牌、密集公寓／冷氣機、電纜、餐館、夜市攤棚、蒸氣、雨影與燈光閃爍。依英文限定要求，遊戲招牌不使用中文。
- 三色背景街貓：走動、坐下、伸展、理毛、觀望與逃離；最多一隻，完全不進入戰鬥目標／碰撞，也不會受傷。
- 四區廢棄地鐵：閘門、路線圖、空月台、破損售賣機、維修管道、漏水、火花、列車光影與控制室。
- 五種運算設施視覺：保全入口、機櫃走廊、冷卻供電、中央處理室、頭目競技場；保留四個戰鬥區，後兩種外觀隨最終戰階段銜接。
- 0.45 秒背景漸變；風扇、資料流、狀態燈與核心階段燈色。背景快取有上限，裝飾不影響戰鬥。

```sh
.venv/bin/python arcade_lobby/main.py
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m unittest neon_brawl.tests.test_combat neon_brawl.tests.test_evolution neon_brawl.tests.test_environment_expansion test_neon_brawl -q
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m neon_brawl.review --output /tmp/neon-brawl-review
```

由 Arcade Floor 左島台 NEON BRAWL 進入。檢視工具輸出包括十二區、額外競技場及背景貓。
本次整合與驗證紀錄見 [Maze 開發紀錄](../puzzle_maze/DEVELOPMENT.md) 最後一節。以下為保留的遊戲與 Phase 2 說明；其中舊場景名稱以此更新為準。

---

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

1. **Neon Alley:** lantern alley, market, commercial street and gang crossing.
   Introduces Grunts, Runners and Bruisers. WARDEN is a long-coated gang leader
   with a charging punch, slam, barrage and short shockwave.
2. **Abandoned Station:** entrance, empty platform, service tunnel and control
   room. Duelists, shield troops, ranged fighters and elites introduce new
   counters. Armored RELAY dashes, emits electric pulses, guards, targets ground
   strikes and calls at most one reinforcement.
3. **Signal Core:** security checkpoint, lab, data corridor and reactor chamber.
   Cyber fighters, heavy security, snipers and assassins appear progressively.
   NULL / SIGNAL OVERLORD has a mechanical silhouette, aimed energy attacks,
   shockwaves, marked teleport, laser, ground strikes and at most two clones.
   Its three phases expose the core in the final desperation phase.

Regular enemies use 17 curated outfits with structural variations, including
hoods, leather/denim jackets, vests, armor, workwear, masks and equipment.
Stage damage multipliers are **1.00 / 1.25 / 1.50** for regular enemies and
**1.00 / 1.40 / 1.70** for bosses. Difficulty is centralized in `data.py`;
existing enemy HP is preserved. Heavy attacks break defensive guards. Use the
marked ground warnings to change lanes before attacks; teleport arrivals do
not deal damage. Boss chambers have no live rails.

All dangerous attacks have a visible windup; only two enemies may initiate
attacks concurrently. Ranged beams hit in their marked lane. Rails flash a
warning before activation; move upward or jump. Dodge, post-hit invulnerability,
knockdown recovery and checkpoint aid prevent continuous stun loops.

## Architecture

- `data.py`: immutable stats, explicit attack timing/range/damage, wave definitions.
- `model.py`: `Fighter`, `PlayerFighter`, `EnemyFighter`, `Swing`,
  `CombatSystem`, `Campaign`. Enemy and boss polymorphism uses data-driven
  names/patterns; simulation has no Pygame dependency.
- `outfits.py` / `wardrobe.py`: curated clothing and dedicated boss bodies.
- `ai.py`: composed boss patterns and phase logic.
- `scenery.py` / `effects.py`: twelve districts and collision-matched warnings.
- `cinematic.py`: separate visual, logo, subtitle and prompt zones.
- `art.py`: cached original pixel animation cels, layered backgrounds and
  `Renderer`; host bitmap font, nearest-neighbor scaling.
- `game.py`: `BrawlGame` presentation state machine, keyboard input, focus/pause,
  input buffering, intro/tutorial/ending, HUD and results.
- `arcade_lobby/neon_brawl_scene.py`: `NeonBrawlScene`, thin lifecycle and reward
  adapter. `RoomHub` and `PlaySession` remain the only payment/settlement owners.
- `build_audio.py`: original music and SFX source, using the existing offline
  synthesizer. Four looped tracks and thirteen effects obey shared audio settings.

No save schema or third-party artwork/audio is introduced. The new game simply
uses `neon_brawl` in existing high scores and played-game records. Results reads
are side-effect free. The host settles once on pop/window close. Closing before
the launch wipe completes refunds the token/coupon; exiting after launch costs
the credit and pays performance tickets. Tickets are bounded at 150:
`score // 180 + stage_index * 8 + (40 if victory else 0)`.

## Automated verification

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. \
  .venv/bin/python -m unittest neon_brawl.tests.test_combat neon_brawl.tests.test_evolution test_neon_brawl -v

SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. \
  .venv/bin/python -m unittest discover -s arcade_lobby -p 'test_*.py'

PYTHONPATH=. .venv/bin/python -m neon_brawl.tests.pilot
```

The simulation pilot uses ordinary movement/actions without changing HP,
facing, damage, rewards, or stage state. It uses heavy attacks against guards, moves out of ground warnings, avoids live rails,
collects checkpoint food and advances normally.
The scene integration pilot sends keyboard events through the launched adapter,
updates the real SceneManager, visits all three stages and NULL phases two and three,
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
in this session. The optimized pilot clears in roughly 4–8 minutes; the desired
10–15 minute first-human-run duration is a balance target, not measured evidence.
Backgrounds repeat original tiles; portraits use enlarged animated character
cels. Art is generated and cached at runtime, without external asset downloads.


Rendered review sheets (intro, all districts, outfits, operatives and bosses):

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. \
  .venv/bin/python -m neon_brawl.review --output /tmp/neon-brawl-review
```

See [PHASE2_VERIFICATION.md](PHASE2_VERIFICATION.md) for the current feature and
verification report; `VERIFICATION.md` records the original implementation.
