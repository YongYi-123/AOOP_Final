# Kevin Engineering Lab 與 Arcade 視覺更新驗收

## 本次成果

開發分支 `feature/kevin-lab-visual-polish`，從整合分支 `fc32c29` 安全建立，沒有改動 main、重寫歷史、push 或 merge。作者設定保留 `nora950817 <nora.ee13@nycu.edu.tw>`；本機設定不能證明 GitHub 已驗證該 email。

### Puzzle Maze

- r28 是完整、獨立、快取的 416×256 暖色工程室；普通石牆、石門、隱形石柱和地圖覆蓋已移除。保留西門、原始照片／筆記／Miao 位置及秘密條件。
- 中央木工作桌、兩部 CRT、一部平面顯示器、多個鍵盤與滑鼠；維修區有開殼電腦、GPU、CPU、RAM、主機板、風扇、電源、硬碟、磁碟片、示波器、焊台、電表、線材與線路圖。另有書櫃、椅子、地毯、盆栽、暖燈及獨立網路終端。
- `lab_hardware.equipment` 以原生像素繪製並快取；14 種素材有不同輪廓，不依賴外部圖片。
- `miao_adapter.guide_frame` 直接呼叫 Lobby `miao_meow.miao_frame`／`facing_frame`，共用原本海軍藍毛色、金色眼睛、皇冠、比例與四拍步行腿。以快取物件同一性測試驗證，不修改 Lobby 素材。
- `LabEntrance` 從真正西側門口 `(24,120)` 出發，沿分段路徑步行 4.2 秒、反應停頓到 5.2 秒，再進入五段英文故事。鏡頭緩移向桌面；底部字幕保留獨立區域。ENTER／E 逐段，SPACE／ESC 完成跳過，忽略重複按鍵；故事期間凍結遊戲邏輯。
- 完成或跳過後保存 `lab_memory_seen`，讀取 Kevin 照片與 Miao 記錄；再次入室不重播。未完成時退出／中斷可重新完整播放。可選設備互動不新增必需謎題。
- Grey Pixel 維持 `dungeon_grey_pixel`／Item 03，Golden Cat 維持 `claw_secret_reward`／Item 02。既有章節事件與 owner 範圍不變。舊 4.5 存檔缺少新欄位／設備時安全補預設，保留物品、照片與秘密。
- 可破壞牆使用高對比、粗分支裂紋、內層色與碎石；普通牆沒有新增可破壞標記。炸彈及入口條件不變。
- 皇家寶庫加入到牆高的金銀堆、寶石、皇冠金像、權杖與旗幟；三個原始獎勵箱的位置與通道不變。增加 1.8 秒可跳過金門揭幕，展示控制器不讀寫獎勵；原開箱與結局結算繼續使用既有系統。
- 修正工程室普通石門覆畫、入場穿盆栽、寶庫提示／小地圖互擋，以及新增畫面被直接列舉時未初始化的錯誤。

### NEON BRAWL

- Stage 1 街貓首隻約第 5 秒出現，其後約每 22 秒一隻，每隻約 16 秒；三種毛色、雙向行走、坐下、理毛與觀察。戰鬥不再迫使牠立即消失。
- 原生貓畫面放大至 33×24，以最近鄰縮放，放在街面 y=247，鏡頭內生成並限制可見範圍；人物之後、戰鬥特效及 HUD 之前繪製。貓沒有健康／傷害欄位，從未加入 Fighter 或敵人清單，不改碰撞。
- 九種營業店面：JADE NOODLES、BUBBLE TEA、LUCKY MART、PIXEL ARCADE、CIRCUIT REPAIR、GOLDEN BAKERY、FRESH FRUIT、DIM SUM、HOT SKEWERS。使用不同寬度、開放門口、暖燈、菜單、碗、飲料、食品、顯示器、棚簷與燈籠；第四區也不再整排關門。
- Stage 2 固定牆面看板有 CPU、REGISTER、ALU、CACHE、GPU 平行單元、CLOCK／PIPELINE、RAM／DATA BUS、CONTROL UNIT、INSTRUCTION DECODER；NVIDIA、AMD、INTEL 僅為原創看板上的純文字背景提及，沒有官方圖標或贊助聲明。
- 快取四種工程圖，保留三關背景、視差、漸變、敵人／Boss 行為與經濟邏輯；更新檢視工具以實際鏡頭捕捉貓。

## 測試與視覺驗收

| 測試 | 實際結果 |
|---|---|
| Maze 全套（含實際 API 全路線與舊存檔） | 229 tests / 30.102s / OK（最後硬體補繪後完整重跑） |
| Brawl 戰鬥、演進、環境與街機整合 | 66 tests / 6.081s / OK |
| 街機房間、經濟、獎勵、其他遊戲、主線、Golden Cat、音訊、原版 Miao | 546 tests / 110.255s / OK |
| 原生素材／入場／持續化／舊快照專項 | 9 tests / 0.434s / OK |
| 三個輸出解析度 | 640×480、960×720、1280×720：入場字幕及全部七種閱讀視窗文字框均在畫面內、互不相交 |
| `git diff --check` | 通過 |

測試涵蓋故事前不顯示對話、步行與停頓時間、世界凍結、重複按鍵、跳過、再次造訪、記憶存檔、舊快照補物件、裂牆炸彈、完整戰役、寶庫開箱／結算、Grey Pixel 與 Golden Cat 分離，以及街貓交戰期間可見、攝影機位置、出現節奏、外觀、碰撞隔離與暫停。

已實際使用影像檢視工具查看：1F／B1F 房間配色合成圖、r24 裂牆、工程室門口、步行、對話、640×480 字幕、寶庫開箱前／後、夜市四區、地鐵四區、核心區及交戰街貓。檢視發現的遮擋有直接修正。這是 headless 真實渲染幀檢視與自動操作測試，沒有宣稱真人桌面通關、實體音訊試聽或所有硬體的 FPS。

可重現截圖放在 `/tmp/kevin-lab-review`、`/tmp/visual-lab-review`、`/tmp/brawl-polish-review`；不把暫存 PNG、存檔或快取提交。

## 啟動及手動檢查

```sh
cd /home/nora/AOOP_Final
.venv/bin/python arcade_lobby/main.py
.venv/bin/python -m puzzle_maze --campaign 4.5
```

Arcade Floor 中島 Puzzle Maze 免費機台：依 `puzzle_maze/PLAYER_ROUTE_V45.md` 從 r5 炸開東牆進 r24，取得 Grey Pixel 後由 `(23,8)` 進 r28。首次等待門口步行與停頓，再逐句讀；測試 SPACE 跳過、回西門、重進及 Continue。可在 GPU `(18,6)`、Keyboard `(10,6)`、Terminal `(21,9)` 鄰格按 E，照片／筆記座標不變。通關後進 r27，看金門揭幕、三箱、開箱後出口與結算。

左島 NEON BRAWL 每局一代幣：選角後 Stage 1 等約 5 秒，交戰時留意腳邊的貓；繼續 1 分鐘應看到多次出現。沿四區查看營業店面。Stage 2 查看壁掛硬體圖；繼續測頭目、Stage 3、暫停、勝敗及離開結算。

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=.:puzzle_maze/tests .venv/bin/python -m unittest discover -s puzzle_maze/tests -p 'test_*.py' -q
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m unittest neon_brawl.tests.test_combat neon_brawl.tests.test_evolution neon_brawl.tests.test_environment_expansion test_neon_brawl -q
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:.:puzzle_maze/tests .venv/bin/python -m unittest test_rooms test_economy test_rewards test_cat_maze test_galaxy_defender test_pixel_volleyball test_racer_launch test_puzzle_maze test_maze45_secret test_chapters test_forgotten_games test_audio_manager test_miao_meow -q
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m puzzle_maze.review_lab
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m puzzle_maze.review45
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m neon_brawl.review
```

## 已知限制

- 程序像素美術為刻意的限色風格；設備為可辨識的簡化表現，沒有外部寫實素材。
- 皇家捲軸既有 `COMING SOON` 內容不在本次秘密改造範圍，保留原狀。
- 劇情完成後不會自動重播入場；舊檔若尚無記憶欄位會在下次入室播放一次。
- 沒有新增音樂或修改原音訊設定／獎勵服務；沿用現有開箱與互動音效。無音訊裝置的降級路徑由測試覆蓋。

## 修改檔案

- `neon_brawl/ambient.py`
- `neon_brawl/art.py`
- `neon_brawl/hardware_posters.py`
- `neon_brawl/market.py`
- `neon_brawl/metro.py`
- `neon_brawl/model.py`
- `neon_brawl/review.py`
- `neon_brawl/tests/test_environment_expansion.py`
- `puzzle_maze/PLAYER_ROUTE_V45.md`
- `puzzle_maze/developer_art.py`
- `puzzle_maze/game.py`
- `puzzle_maze/lab_hardware.py`
- `puzzle_maze/lab_scene.py`
- `puzzle_maze/miao_adapter.py`
- `puzzle_maze/remaster.py`
- `puzzle_maze/render.py`
- `puzzle_maze/review_lab.py`
- `puzzle_maze/secret45.py`
- `puzzle_maze/tests/test_visual_story.py`
- `puzzle_maze/treasury_scene.py`
- `puzzle_maze/vault.py`

另新增本報告 `VISUAL_POLISH_REPORT.md`。

## 真實提交紀錄

- `2ffaccc` feat(maze): create distinct CRT computer and engineering hardware pixel assets
- `8ccd173` feat(maze): replace secret dungeon with cozy engineering studio and Lobby Miao artwork
- `3699183` feat(maze): add optional engineering inspections and compatible memory persistence
- `2989d63` fix(maze): enlarge branching bomb-wall fractures and render engineering objects
- `b610859` feat(maze): animate Miao doorway entrance with paced persistent memory dialogue
- `2f6f183` feat(maze): fill royal vault with layered wealth and frame the memory camera
- `16ee64b` fix(brawl): keep larger ambient cats visible inside the combat viewport
- `90cd7a6` feat(brawl): open nine varied night-market businesses with lit counters and food displays
- `7215721` feat(brawl): mount computer-architecture schematics in abandoned metro stations
- `36950b0` fix(arcade): remove hidden lab collisions and capture cats with the actual camera
- `5c6e1ba` feat(maze): reveal royal treasury through skippable golden doors without altering payouts
- `1daaad4` fix(maze): keep special interiors clear of dungeon overlays and verify rendered story frames
- `9f8152a` test(maze): verify old remaster snapshots retain secrets while gaining lab interactions
- `721d693` docs(maze): update the engineering-lab route and capture unobstructed bomb-wall art
- `81b0761` feat(maze): detail storage and power hardware while clearing the Miao walking route

本報告本身以獨立 docs 提交保存；完整最終 ID 以 `git log fc32c29..HEAD` 及交付訊息為準。交付時應為 16 筆新提交，全部未推送。唯讀 `ls-remote` 確認遠端整合分支仍是 fc32c29，新的功能分支尚未存在遠端。可自行 `git push -u origin feature/kevin-lab-visual-polish`，保留全部原始提交，不 squash。本次沒有執行 push。
