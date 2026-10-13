# 開發紀錄

2026-10-12，分支 `feature/puzzle-maze`，基底 `1204778`。
原有未追蹤檔案 `tatus -sb` 保留。所有新檔、測試與文件位於 `puzzle_maze/`。

- Phase A：移動、碰撞、Camera；2 項測試通過。Commit `4ae3e05`。
- Phase B：JSON 地圖、八房連接、合法性檢查；5 項測試通過。Commit `e7a46dd`。
- Phase C：推箱、壓力板、AND 條件門、開關、鑰匙；11 項測試通過。Commit `b4b5807`。
- Phase D：秘密牆、限時門佔用保護、綜合機關、檢查點、獨立原子存檔；
  17 項測試通過。Commit `d771d3f`。
- Phase E：原創像素渲染、四方向動畫、跟隨鏡頭、選單、HUD、地圖、粒子、
  房間轉場、合成音樂音效、8 主房 + 1 隱藏房、關卡搜尋與通關重播。
  26 項測試通過，SDL dummy 啟動及截圖檢查通過。

一般門採完成条件後鎖定開啟，限時門則持續觀察倒數。
入口檢查點同步還原鑰匙與物件，避免重置後重複取得鑰匙。
程式化美術及聲音無外部資產或授權依賴。沒有加入 Lobby，沒有 Push/Pull/Merge。

Phase E 後的呈現檢查修正：壓力板先繪製，避免覆蓋其上的木箱；
Atlas 依 JSON 的實際出口關係繪製已探索連線，包含第六房到秘密房的支線。
26 項測試、compileall 與 Git 空白格式檢查重新通過。

既有遊戲回歸：Retro Racer 82、Pixel Volleyball 110、Cat Territory 27、
Cat Minesweeper 14、Galaxy Defender 78 項均通過（SDL dummy，獨立程序）。

最終回歸：Arcade Lobby 完整 discover 測試成功（exit code 0；同一 discovery
共 1,361 項），上述其他遊戲合計 311 項亦成功。Puzzle Maze 26 項全部通過。
最終 Git 差異全部限定 `puzzle_maze/`，原未追蹤檔案不變；未修改 main 或推送。

使用者後續授權接入 Lobby 試玩：新增中央島列 `island_1` 的免費機台。
僅修改 Lobby 的 settings.MACHINES 與 scenes 註冊，新增整合測試；可選介面
位於 puzzle_maze/lobby_scene.py。使用既有參與者輸入、視窗及音訊 API，沒有
修改音效管理、經濟或其他遊戲。主選單 Esc / 暫停 Return to arcade 可返回。
獨立模式 26 項測試及 3 項機台整合測試通過，新增測試不寫入玩家存檔。

## Puzzle Maze 2.0

基底 `04ec231`，沿用 feature/puzzle-maze；原未追蹤 tatus -sb 保留。
本次只修改 puzzle_maze/，不擴充或更動 Lobby 介面及其他遊戲。

Phase A：字體改到最終視窗解析度繪製；像素场景整數倍率 nearest 縮放。
附 Noto Sans CJK TC（SIL OFL）及授權檔，驗證繁中文字形與五種視窗尺寸。

Phase B：八個主要房間擴為 56×34，保留原核心謎題、增加東翼第二階段封印、
蜿蜒通道、回頭路與脈衝寶庫。出口檢查具名條件，限時門跨越紀錄可供後續
機關使用但不讓限時門永久開啟。以原版 fixtures 保留核心回歸，新增實際八房
通關及出口防繞過測試；箱子搜尋可指定階段物件並重播生產碰撞。

Phase C：寶箱依序提供手套、衝刺靴、光之鏡、磁力裝置。重箱檢查手套；
衝刺三格、1.2 秒冷卻並逐格碰撞；光束逐格追蹤、鏡面轉向啟動接收器；
磁力可隔水遠端操作金屬，不穿牆、不把箱子移進玩家或障礙。
後期封印組合鏡面及磁力，第四房限時封印需靴子衝刺。Q 切換工具、SHIFT
衝刺、F 吸引、SPACE 排斥。34 項測試通過，包括帶能力的全八房通關。
2.0 改用 save_v2.json，原 save.json 保留；能力與補給納入存檔及房間檢查點。

Phase D：5 HP、近戰 J、補給 H、1.1 秒受傷無敵、閃爍及碰撞安全擊退。
Slime 慢速追蹤、Bat 週期衝刺、Guardian 高 HP / 0.7 秒前搖；尋路遵守牆、
水與機關碰撞。敵人有限生成、死亡粒子與一次性生命/晶片掉落；房間快照
及存檔保存戰鬥狀態。第八房需擊敗南側三守衛。死亡停止操作並提供主選單。
含戰鬥八房通關及 40 項全套測試通過，另補 HP/死亡存檔與 Bat 衝刺測試。
修正南區可達性、跨限時門後敵人位置與門關閉時的敵人佔用保護。

Phase E：右上即時房間小地圖、Tab 完整連接圖與當房探索迷霧。
DungeonAtlas 讀 RoomManager 的出口與 JSON atlas 座標；隱藏房發現前完全
排除，發現的門、出口、寶箱與接收器有標記。Exploration 視線被牆及閉門
阻擋，紀錄跨房間與重置保留並存檔。46 項測試通過，最終解析度截圖檢查
文字與五顆愛心清楚、小地圖不遮擋提示框。

Phase F：全八房使用真實碰撞 / 推箱搜尋 / 能力 / 戰鬥通關，另驗證秘密房
往返及第四房步行超時、衝刺成功。新增錯誤條件循環、能力、敵人位置、光線
方向與探索/戰鬥損毀存檔測試；衝刺及戰鬥冷卻、無敵時間納入讀檔。
HUD 增加工具、冷卻與晶片；說明與地圖使用繁中 / 英文。截圖發現原生文字
延遲繪製會透過模態覆蓋 HUD，已修正並加回歸測試；標題及提示受版面寬度
約束。更新 README 的操作、工具路線、生命、存檔及架構說明。

最終驗證：55 項測試全數通過（16.830 秒）；headless 60 幀、compileall、
Git diff --check 通過。相對基底 04ec231 的變更全部在 puzzle_maze/。

本次新增 / 修改檔案清單：

- `puzzle_maze/.gitignore`
- `puzzle_maze/DEVELOPMENT.md`
- `puzzle_maze/README.md`
- `puzzle_maze/assets/fonts/NotoSansCJKtc-Regular.otf`
- `puzzle_maze/assets/fonts/OFL.txt`
- `puzzle_maze/audio.py`
- `puzzle_maze/combat.py`
- `puzzle_maze/core.py`
- `puzzle_maze/exploration.py`
- `puzzle_maze/game.py`
- `puzzle_maze/maps/dungeon.json`
- `puzzle_maze/puzzles.py`
- `puzzle_maze/render.py`
- `puzzle_maze/rooms.py`
- `puzzle_maze/session.py`
- `puzzle_maze/solver.py`
- `puzzle_maze/tests/fixtures/dungeon_v1.json`
- `puzzle_maze/tests/legacy.py`
- `puzzle_maze/tests/test_abilities.py`
- `puzzle_maze/tests/test_campaign.py`
- `puzzle_maze/tests/test_combat.py`
- `puzzle_maze/tests/test_exploration.py`
- `puzzle_maze/tests/test_game.py`
- `puzzle_maze/tests/test_playthrough.py`
- `puzzle_maze/tests/test_puzzles.py`
- `puzzle_maze/tests/test_rooms.py`
- `puzzle_maze/tests/test_session.py`
- `puzzle_maze/tests/test_ui.py`
- `puzzle_maze/tests/test_validation_v2.py`
- `puzzle_maze/ui.py`

## Puzzle Maze 2.1

基底 2d594de，沿用 feature/puzzle-maze，原未追蹤 tatus -sb 保留。
Phase A：Player 預設 BasicSword，Weapon 封裝面向、距離、傷害、冷卻與動畫。
揮劍只判定一次，正前方一格，敵人閃爍 / 擊退 / hit 音效。補上既有可選
puzzle_maze/lobby_scene.py 丟棄 J 的輸入問題，不改 host 模組。舊 v2 存檔
缺少武器欄位會自動補基礎劍。59 項全套與新增 1 項橋接攻擊測試通過。

Phase B：獨立 INTRO / TUTORIAL 狀態，6 秒拔劍與開門動畫、Enter 略過，
之後操作說明等待确认。Quick start 可略過全部教學，Continue 不重播。
IntroSequence / TutorialCard 封裝動畫與操作資料；開場及教學凍結敵人、
機關與存檔寫入，取消不覆蓋原進度。63 項全套測試通過。

Phase C：全部遊戲 UI 改英文，改用附授權的 DejaVu regular / bold；移除不再
需要的 CJK 字型。文字在最終輸出解析度繪製，字型原生抗鋸齒而非放大文字
貼圖；像素場景仍 nearest 整數倍率。既有可選介面 full_resolution=True，
避免 host 再放大低解析度文字。TutorialCard 作為教學/說明/HUD 的按鍵來源，
補 Q/F/H/Shift 傳遞並依玩家控制方案顯示按鍵。66 項全套與 UI 回歸通過。

Phase D：前兩房先驗證後套用八房，主房 56×34 → 40×26，秘密房 19×14；
清掉無用途水坑與南側空白，縮短出口走廊，保留鏡台、金屬水槽、寶庫與
南側敵人場地，可行走格數減少 64–66%。房名與 theme 分別定義各房環境。
CoordinateTransform / LayoutMigration 以保留座標軸轉換合法 v2.0 存檔，
保留道具、生命、敵人、探索及檢查點；移除區的箱子找合法可移動位置。
讀檔不寫檔，首次覆寫 2.0 資料前保留 .v20.bak。69 項全套測試通過。

Phase E：RoomTheme / EnvironmentPainter 原創程式像素美術；八種材質/配色、
地磚變體、石柱與書堆障礙、火把/齒輪/書架/武器架/水晶/旗幟/封印掛飾。
光暈與火焰、齒輪、晶體閃光動畫；所有掛飾在既有牆格且遠離必要機關，
不改碰撞。紋理/光暈快取，粒子數量受限。隱藏寶庫增加一次性補給箱；
缺少此可選物件的舊快照補預設狀態，其他缺少物件仍拒絕。精簡房間提示。
72 項全套及最後材質/版面回歸通過；已檢查入口的最終解析度截圖。

Phase F：78 項測試全部通過（10.073 秒），含初始劍、單次命中、前兩房敵人、
教學等待與重複鍵、兩玩家按鍵一致性、全八房搜尋/能力/戰鬥通關、秘密寶庫
獎勵一次性、舊存檔及新增可選物件。補持久化面向與鎖定揮劍方向，限制存檔
冷卻值，排除鏡頭外物件文字。已查看房間主題、英文教學與 Game Over 截圖。
Dummy driver 的 180 幀純繪製平均 1.51 ms（0.272 秒），為 headless 繪製容量，
不等同實際硬體 FPS。修正字型授權檔末端空白，保留完整授權文字。
人工待驗證：J 揮劍手感 / 音量、完整關卡難度、真實螢幕字體及縮放、實際 FPS。

最終再檢查：開場角色被字幕板遮住，已移至字幕上方並加可見範圍測試。
近戰接觸改為朝敵人轉向但不重疊，避免貼身後劍無法命中；箱子/衝刺也不會
落在活敵人上，通關模擬以實際攻擊處理阻路敵人。最終 80 項全部通過
（11.244 秒），含所有九房、開場/教學與死亡流程；全部變更仍只在 puzzle_maze/。

2.1 檔案變更清單（A 新增 / M 修改 / D 移除；相對 2d594de）：

- `M puzzle_maze/.gitignore`
- `M puzzle_maze/DEVELOPMENT.md`
- `M puzzle_maze/README.md`
- `A puzzle_maze/assets/fonts/DejaVu-LICENSE.txt`
- `A puzzle_maze/assets/fonts/DejaVuSans-Bold.ttf`
- `A puzzle_maze/assets/fonts/DejaVuSans.ttf`
- `D puzzle_maze/assets/fonts/NotoSansCJKtc-Regular.otf`
- `D puzzle_maze/assets/fonts/OFL.txt`
- `M puzzle_maze/audio.py`
- `M puzzle_maze/combat.py`
- `M puzzle_maze/core.py`
- `A puzzle_maze/environment.py`
- `M puzzle_maze/game.py`
- `M puzzle_maze/lobby_scene.py`
- `M puzzle_maze/maps/dungeon.json`
- `A puzzle_maze/maps/dungeon_v20.json`
- `A puzzle_maze/migration.py`
- `A puzzle_maze/onboarding.py`
- `M puzzle_maze/puzzles.py`
- `M puzzle_maze/render.py`
- `M puzzle_maze/rooms.py`
- `M puzzle_maze/session.py`
- `M puzzle_maze/tests/test_abilities.py`
- `A puzzle_maze/tests/test_bridge.py`
- `M puzzle_maze/tests/test_campaign.py`
- `A puzzle_maze/tests/test_environment.py`
- `M puzzle_maze/tests/test_exploration.py`
- `M puzzle_maze/tests/test_game.py`
- `A puzzle_maze/tests/test_migration.py`
- `A puzzle_maze/tests/test_onboarding.py`
- `M puzzle_maze/tests/test_rooms.py`
- `A puzzle_maze/tests/test_sword.py`
- `M puzzle_maze/tests/test_ui.py`
- `A puzzle_maze/themes.py`
- `M puzzle_maze/ui.py`
- `A puzzle_maze/weapons.py`


## 3.0 — Clockwork Hollow (2026-10-13)

Continued from `5f3de80` on `feature/puzzle-maze-v3`, without merging main or
changing `backup/puzzle-maze-recovery`. The unrelated root Git-log text file
was left untouched. All new edits are confined to `puzzle_maze/`.

- Foundation: original bitmap font and live icon HUD; bounded bombs, cracked
  walls, renewable supply, multi-key/Boss Key locks and enemy strategies.
- Campaign: eighteen connected rooms over two floors, branch relays, optional
  secret treasure, ability backtracking, optical/magnetic/timed combinations.
- Boss: dash exposure, bomb armor, combined final phase, telegraphed projectiles,
  finite death animation, exit unlock and retry without overwriting living saves.
- Polish: cold B1F palettes, meaningful columns/bookshelves, floor-aware atlas,
  Compass markers, concise tutorial, native bitmap text and pickup bounce.
- Save regression fixed: the active dash anchor now declares its six-second
  duration, allowing a primed boss encounter to load successfully.
- Bypass regression fixed: magnetic-only weights reject manual pushing.
- Validator derives resource rewards and costs from annotated JSON objects;
  all 109 abstract resource states have a winning continuation. Removing the
  spare sixth key remains solvable; removing necessary combat keys is rejected.

Baseline: 80 tests passed. Final: 108 tests passed in 18.552 seconds, including
complete production-action victory, all eighteen room visits, enemy weaknesses,
boss phases, active bomb/anchor saves and UI bounds at 240×180 through 1000×700.
`compileall` and `git diff --check` passed. Screenshot review covered all rooms,
boss HUD and tutorial. Render-only benchmark: 2.56 ms/frame, 180 draws.

The first v3 foundation commit accidentally preceded review of one failing legacy
assertion that expected exactly three enemy kinds. That assertion was updated
for the seven supported kinds; subsequent complete suites passed. No history was
rewritten. New tests use temporary saves or mock the game save method.

Automated campaign traversal uses collision-aware moves with explicit combat and
fuse ticks. It does not exhaustively prove every real-time enemy trajectory or
crate arrangement. Actual input feel, audio and graphical FPS need human checks.
Old 2.1 saves remain separate and playable via `--legacy` / archive continuation.

### 3.0 file manifest

- `puzzle_maze/.gitignore`
- `puzzle_maze/DEVELOPMENT.md`
- `puzzle_maze/README.md`
- `puzzle_maze/README_V21.md`
- `puzzle_maze/audio.py`
- `puzzle_maze/build_dungeon.py`
- `puzzle_maze/combat.py`
- `puzzle_maze/dungeon.py`
- `puzzle_maze/enemies.py`
- `puzzle_maze/environment.py`
- `puzzle_maze/exploration.py`
- `puzzle_maze/game.py`
- `puzzle_maze/icons.py`
- `puzzle_maze/items.py`
- `puzzle_maze/maps/dungeon_v3.json`
- `puzzle_maze/onboarding.py`
- `puzzle_maze/pixel_font.py`
- `puzzle_maze/puzzles.py`
- `puzzle_maze/render.py`
- `puzzle_maze/rooms.py`
- `puzzle_maze/session.py`
- `puzzle_maze/tests/test_combat.py`
- `puzzle_maze/tests/test_game.py`
- `puzzle_maze/tests/test_v3_campaign.py`
- `puzzle_maze/tests/test_v3_presentation.py`
- `puzzle_maze/tests/test_v3_systems.py`
- `puzzle_maze/themes.py`
- `puzzle_maze/ui.py`
- `puzzle_maze/validator.py`


## 4.0 — Emberglass Hollow (2026-10-13)

Created `feature/puzzle-maze-v4` from completed v3 `b82fe85`. The unrelated
`tatus --short` file remains untouched, as do main, backup branches and all other
modules. Baseline: 108 tests passed.

- Added powder braziers/sequences, refill stands, lift/drop/throw pots, carried
  weight plates, shared red/blue barriers, ordered enemy resets and safe respawns.
- Extended the encounter factory with Mirror Mask, Pot Hunter, Crystal Ghost,
  Elite Guardian and Crystal Warden. Finite Warden summons save their dormant
  state and awaken at legal positions. Existing Golem gains a final crystal rule.
- Added four meaningful rooms and multiple bidirectional shortcut loops; the old
  eighteen chambers retain their solved mechanical layouts with revised art.
- Added a local reward escrow/receipt with source deduplication, five distinct
  secret collections and Heart Fragments. No external economy writes or imports.
- Added original icon assets in code, cached floor compositions, new palettes,
  animated braziers, crystals, carried/thrown pots, shards, chest lids and motes.
- Added 4.0 private save and old-campaign archives. Archive navigation and death
  cannot overwrite a live expedition. Settled receipts cannot be reset.

Validation: 135 tests pass in 17.235 seconds, including a legal complete route visiting all 22
rooms, all five secrets, Warden, Golem and saved final receipt. Resource search
has 341 reachable states and 341 winning continuations. The route includes coupled
player/Mirror Mask state search. Room walking is untimed in the witness, while
combat/fuses receive explicit ticks; real-time difficulty is not exhaustively
proven. UI bounds and both tutorial pages are checked at five resolutions.

Headless room/shrine/pot/Warden screenshots reviewed. Cached Warden rendering:
1.87 ms/frame over 180 frames. This is a render benchmark, not physical-display
FPS. Manual keyboard feel, boss difficulty, sound and display scaling remain.

### 4.0 file manifest

- `puzzle_maze/.gitignore`
- `puzzle_maze/DEVELOPMENT.md`
- `puzzle_maze/README.md`
- `puzzle_maze/README_V3.md`
- `puzzle_maze/advanced_dungeon.py`
- `puzzle_maze/advanced_enemies.py`
- `puzzle_maze/advanced_puzzles.py`
- `puzzle_maze/audio.py`
- `puzzle_maze/build_dungeon_v4.py`
- `puzzle_maze/combat.py`
- `puzzle_maze/enemies.py`
- `puzzle_maze/exploration.py`
- `puzzle_maze/game.py`
- `puzzle_maze/icons.py`
- `puzzle_maze/items.py`
- `puzzle_maze/maps/dungeon_v4.json`
- `puzzle_maze/onboarding.py`
- `puzzle_maze/puzzles.py`
- `puzzle_maze/render.py`
- `puzzle_maze/rewards.py`
- `puzzle_maze/room_art.py`
- `puzzle_maze/rooms.py`
- `puzzle_maze/session.py`
- `puzzle_maze/tests/test_combat.py`
- `puzzle_maze/tests/test_v4_campaign.py`
- `puzzle_maze/tests/test_v4_mechanics.py`
- `puzzle_maze/tests/test_v4_presentation.py`
- `puzzle_maze/themes.py`
- `puzzle_maze/validator.py`

Final CLI smoke checks passed for campaigns 4, 3 and 2. The v4 JSON exactly
matches its deterministic authoring generator. `compileall` and `git diff --check`
passed. No other tracked module was edited.


## Existing cabinet upgraded to 4.0

User authorized replacing the old cabinet entrance after playing the archived
2.1 campaign by mistake. `PuzzleMazeScene` now explicitly selects campaign 4 while
sharing the host window/audio. Embedded games without an explicit campaign keep
the old default for compatibility. B/P/G reach the live bomb/powder/pot actions.
Tutorial and nearby prompts use participant-specific sword/interact/dash keys.
Menu title/footer show the active campaign version. No host module or economy
was modified. The private result still has no player payouts.

Bridge regressions include a real two-player lobby session launched by P2,
onboarding, powder input and safe return with identical token/ticket balances.

Cabinet follow-up validation: all 137 Puzzle Maze tests passed in 18.186 seconds;
`compileall` and `git diff --check` passed. Only Puzzle Maze files were changed.

## 4.1 — Hidden rewards, usable entrances and final access

Continued on feature/puzzle-maze-v4 with only an unrelated untracked root file
present. Baseline: 137 tests passed. No host files or shared currencies changed.

ChestPhase adds four explicit states, a persistent 0.45-second appearance timer,
latched availability and one-time collection. Copper Watch's old key ID is now
a hidden reward chest, preserving old collected state. Ten hidden chests use
real puzzle/ability/flag conditions. Compass/proximity prompts honor visibility.
Boss Key requires timed crossing, Boots, prism and Warden progress.

Original entrance drawing replaces arrow exits with arches, caves, locks,
Boss Gate and direction-specific stairs. Two optional loops add a library
walk-through and a flame/Warden remote foundry passage. Remote passages block
movement while closed; room-completion history cannot bypass their conditions.
Bomb-wall cracks blend into their stone and show no arrow. Landing safety
checks restored crates and live enemies before creating the room checkpoint.

DungeonIntegrityValidator checks the 59 entrance records, 27 chests, two stair
records and four secret entries, then runs existing crate/resource search.
All 341 resource states remain winning; six keys cover five mandatory costs.
The production campaign witness still reaches r18, completes the expedition,
visits all rooms, defeats the Golem and reloads its settled save correctly.
Tests additionally cover 60 FPS timed crossing, legacy chest fields, a legacy
save on the new closed foundry entrance, safe returns and hidden exit markers.

Human input was unavailable. Headless startup and rendered library/stair/menu
screens were checked; continuous combat difficulty, sound, FPS and how subtle
clues feel still need a real play session. PLAYER_ROUTE.md provides a practical
route through the final room without revealing every optional collectible.

Final 4.1 validation: all 150 Puzzle Maze tests passed in 19.422 seconds.
The 60-frame default campaign smoke run, integrity CLI, compileall and
git diff --check passed. Screenshot review covered native crisp UI and
functional stairs/library entry art. No manual real-time play was performed.

## 4.2 — Absolute coordinates, progression repair and complete walkthrough

Safety: continued feature/puzzle-maze-v4; baseline 150 tests passed in 27.094s.
The unrelated untracked root file was preserved. All edits stay under
puzzle_maze; no host modules, shared saves, or external currency balances were
changed. No push/pull/merge/rebase/squash/reset/clean was performed.

The prior route witness did not validate physical door orientation. Original
loops included triangles and a six-branch central floor junction incompatible
with immediate cardinal neighbors. Return paths also depended on duplicate
exits while dash-only gates refused normal return walking. Fixed the topology
with 22 authoritative floor/grid_x/grid_y records, cardinal wall entrances,
reciprocal IDs and destination landings. The lower stairs were relocated away
from the Atrium east arrival. Five internal multi-condition gates now render as
gear controllers; actual exit gates sit on their exit tile. Timed doors preserve
normal return after the first successful timed crossing. Existing portal remains
special; no main-progression cheat portal was added.

RoomCoordinate / DoorConnection / DoorValidator verify orientation and returns.
PuzzleDependencyValidator resolves actual consumers for 36 actuators.
ChestValidator checks interaction routes after conditions; actual campaign
simulation independently acquires rewards by solving the puzzles. Compass and
Prism key require their controllers. Current counts: 51 directional entrance
records (49 repaired plus two new transformation records), four stair records,
30 chests (27 existing, three new), 13 hidden chests. Five secret-entry records
represent two bomb passages, reciprocal library/watch passage and remote
foundry/sanctuary entrance. Before Map, minimap shows the current room only; Tab
shows visited records. Map/Compass unlock their actual information scopes.

IronOrb is one persistent, recoverable object carried across authorized doors
and floors. E lifts/drops, G throws, T recalls. A carried pot and Orb are mutually
exclusive. DestructiblePillar in Storage/Foundry posts saved global flags; both
unlock a real new stair pair and treasure. OrderedLayoutSeal requires correctly
identified heavy blocks at marked positions; wrong arrangements reset safely.
Global blue crystal plus the Prism controller reveals another reward. Original
return routes survive transformation. Carried-Orb HUD suppresses misleading pot
prompts. Portal refusal gives a drop/recall hint.

migration42 validates archived 4.1 snapshots before moving static objects,
adding optional objects and selecting legal landings. Earned inventory, keys,
locks, combat, exploration and reward escrow remain intact. Current, legacy and
checkpoint Orb consistency are validated. Loading is read-only. The original
save_v4.json was not rewritten during development.

The extended production-action route starts from a new session, visits all
22 rooms, legally opens every one of the 30 chests, moves the Orb through doors
and transformed stairs, obtains Boss Key, defeats both bosses, finishes r18,
saves/reloads the settled receipt, and confirms reward idempotence. Cleared-room
and puzzle walking advances the actual 0.13-second movement interval. Combat
uses targeted legal action witnesses and real damage/AI/fuse/death timers; it
does not exhaustively simulate continuous human combat trajectories. Resource
search remains 341 reachable / 341 winning states, six keys / five costs.

PLAYER_ROUTE.md is now a complete Chinese 4.2 walkthrough including authoritative
coordinates, door directions, key budget, mechanism solutions, recovery controls,
optional treasures, Iron Orb route and the three-phase Golem. UI stays English.
README documents current geometry, architecture, counts and practical limits.
Headless screenshot review covered the menu, Orb/pot area and transformed stairs.
Manual input, continuous difficulty, audio balance, clue visibility and machine
FPS still need human verification.

Final validation: all 169 tests passed in 26.278 seconds; integrity CLI,
deterministic authoring/JSON equality, 60-frame headless startup, compileall and
git diff --check passed. Existing lobby bridge regression tests are included in
the suite. No manual real-time play session was performed.
