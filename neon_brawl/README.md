# NEON BRAWL 研究設施改版

## 角色與戰鬥動畫更新

角色已重新以 **32×32 原生像素**繪製，再用整數 2 倍顯示；NOVA 保留青色短髮、耳機與飄帶。
普通敵人的蓬鬆髮型、快攻型的尖髮／圍巾、重裝型的寬身與安全帽，以及三位頭目的金色髮捲、天線頭盔、貓耳機械兜帽，使用不同輪廓。
頭目與一般角色維持相同像素倍率，沒有改動原有世界座標碰撞或攻擊範圍。

出拳、重擊與技能使用八幀姿勢，直接依照 `windup`／`active`／角色各自的 `recovery` 取樣。
上下臂各維持 3 個原生像素長度，透過關節旋轉出拳，不會拉長；攻擊距離用短拳風與能量效果表達。
新增跳躍收腿／灰塵、閃避殘影、眨眼與受擊瞇眼、倒地翻轉、青色技能環、星形命中粒子與連擊提示。
保留原有 45ms 命中停頓；強力命中才有 1–2 像素、120ms 的場景震動，HUD 保持固定。

每關第三區清場、進入 Boss 區前的保證補血由 **35 HP 提高到 65 HP**，最多補到角色血量上限。
一般檢查點仍補 35 HP；原有食物額外補 30 HP，其他數值與主線、存檔、票券結算不變。

正常由 Lobby 的 ARCADE FLOOR 左島 **NEON BRAWL** 進入。選 NOVA，使用 J／K／L／U／I 測試連段、重擊、跳躍、特殊技與閃避。
也可啟動不寫存檔、不扣代幣的獨立正常遊玩視窗：

```sh
PYTHONPATH=arcade_lobby:. .venv/bin/python -m neon_brawl.review_combat --play
```

專項回歸測試和可重現的動作／實戰渲染圖：

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m unittest neon_brawl.tests.test_character_polish -v
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m neon_brawl.review_combat
```

渲染圖存於 `/tmp/brawl-combat-review`；包含角色、NOVA 八幀動作，以及透過真實輸入和更新迴圈擷取的拳擊、重擊、技能、跳躍、閃避，另有三位頭目的預警／出招／收招。
這些是離屏渲染檢查與自動化操作，並非真人桌面遊玩紀錄。

目前版本保留戰鬥、角色、敵群、頭目、四區流程、機台與票券結算；三關統一為同一座部分廢棄研究設施：

- **MACHINE LEARNING LAB**：資料收集、模型訓練、神經網路、失敗實驗；有 loss 曲線、散點分類、混淆矩陣、漏水、破損機櫃與「只認得貓」的模型。
- **COMPUTER ARCHITECTURE LAB**：MIPS 五階段、CPU datapath、暫存器、cache／RAM、ALU／control 與邏輯閘；四種背景工程師會打字、焊接、喝咖啡、研究圖紙與打瞌睡。
- **AOOP DEVELOPMENT CORE**：類別／物件、繼承、多型、組合、封裝與介面，搭配原創街機機械、飄浮像素物件與方法呼叫封包。最終戰的中央軟體螢幕隨頭目階段改變資料通道燈色。
- **五種新貓**：重新繪製的 26×22 原生短腿／寬頭像素貓，不使用舊 Brawl 貓圖或直接複製 Lobby 貓。三關約每 22 秒出現一隻，可走、坐、理毛、睡覺、伸展與短跑，最多一隻且永不成為戰鬥目標。

裝飾火花、漏水、工程師與貓都不影響碰撞或傷害。原有帶預警的地面危險區仍有效，畫面現在稱為 LIVE CIRCUIT。背景維持 0.45 秒漸變與兩層視差。

```sh
cd /home/nora/AOOP_Final
.venv/bin/python arcade_lobby/main.py
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m unittest neon_brawl.tests.test_combat neon_brawl.tests.test_evolution neon_brawl.tests.test_environment_expansion neon_brawl.tests.test_street_life neon_brawl.tests.test_research_complex test_neon_brawl -q
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m neon_brawl.review_research
```

由 Arcade Floor 左島 NEON BRAWL 進入，每局一代幣。檢視工具產生十三個真實場景、貓的花紋／步行幀、工程師循環與技術圖解到 `/tmp/brawl-research-review`，不寫玩家存檔。舊 `market.py`／`metro.py`／`facility.py` 僅保留相容性，已不在正式場景註冊；舊貓繪圖已移除。開發歷史文件中的舊地名屬於過去版本。

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

- WASD / arrows: move horizontally and between combat lanes.
- J: light attack; successive attacks form a three-hit combo; airborne J kicks.
- K: slower, powerful uppercut that knocks enemies down.
- L: jump; high jumps avoid grounded attacks and live circuits.
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
scroll across layered pixel environments. Continuing from a checkpoint grants
35 HP (65 HP before each boss) and 20 energy; E collects an additional 30 HP meal.
Defeat ends the run.

1. **Machine Learning Lab:** data collection, model training, neural research and failed experiments.
   Introduces Grunts, Runners and Bruisers. WARDEN is a long-coated gang leader
   with a charging punch, slam, barrage and short shockwave.
2. **Computer Architecture Lab:** instruction decoding, datapath benches, cache/memory and pipeline control. Duelists, shield troops, ranged fighters and elites introduce new
   counters. Armored RELAY dashes, emits electric pulses, guards, targets ground
   strikes and calls at most one reinforcement.
3. **AOOP Development Core:** classes, inheritance, components and the arcade runtime.
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
not deal damage. Boss chambers have no live circuits.

All dangerous attacks have a visible windup; only two enemies may initiate
attacks concurrently. Ranged beams hit in their marked lane. Circuits flash a
warning before activation; move upward or jump. Dodge, post-hit invulnerability,
knockdown recovery and checkpoint aid prevent continuous stun loops.

## Architecture

- `data.py`: immutable stats, explicit attack timing/range/damage, wave definitions.
- `model.py`: `Fighter`, `PlayerFighter`, `EnemyFighter`, `Swing`,
  `CombatSystem`, `Campaign`. Enemy and boss polymorphism uses data-driven
  names/patterns; combat never calls background rendering or environmental collision.
- `outfits.py` / `characters.py`: curated clothing, original 32px characters and rigid arm geometry (`wardrobe.py` is the unused legacy drawing).
- `animation.py`: simulation-clock sampling of anticipation, active and recovery poses.
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
