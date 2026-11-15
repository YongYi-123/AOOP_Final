# NEON BRAWL Phase 2：交付與驗證

本文件記錄敵人、頭目、場景及開場的第二階段優化；第一階段歷史結果保留於
`VERIFICATION.md`。控制、機台費用、存檔與結算責任保持原介面。

## 服裝與敵人

17 套原創服裝分成四個家族，具有不同輪廓、帽兜、護甲、面罩、背包、武器與手套，
不是僅換色。服裝在鏡像、走路、攻擊、受傷及倒地前，先依身體／手部座標繪製。

- Grunt：皮衣、紅帽衫、丹寧、無袖騎士裝、軍用背心。
- Runner：運動服、夜行帽衫、蒙面裝、快遞裝。
- Bruiser：裝甲執法者、工業工作服、幫派長衣、保全護甲。
- Ranged：霓虹科技裝、訊號面罩、戰術服、技師服。

新敵種：Duelist 雙擊手、Shield 盾兵、Elite 精銳、Cyber 義體兵、Security 重裝警衛、
Sniper 狙擊手、Assassin 刺客；Echo 是最終頭目的限量數位分身。
盾兵會短暫防守，重擊可破防；義體兵使用近距離電波，刺客有前搖突進，狙擊手
射程更長但預警更久。精銳與雙擊手使用較長攻擊動作。
所有揮擊仍遵守每次攻擊對每個目標最多一次傷害，雙擊動作不會繞過受傷無敵。

第一關只出現 Grunt／Runner／Bruiser；第二關再引入遠攻、雙擊手、盾兵和精銳；
第三關引入義體兵、重裝警衛、狙擊手、刺客。基礎敵群仍為 70 人，限量召援最多
額外 3 人。出生格與玩家至少相距 95 像素，並檢查其他敵人的位置；同時起手仍受限。

## 難度與頭目

| 關卡 | 一般敵人傷害 | 頭目傷害 |
|---|---:|---:|
| Neon Alley | 1.00× | 1.00× |
| Abandoned Station | 1.25× | 1.40× |
| Signal Core | 1.50× | 1.70× |

倍率與攻擊資料集中於 `data.py`，不隨關卡提高同一敵種生命值。增加的難度主要來自
敵群搭配、攻擊形狀、防守、位移、射程及頭目階段。

- **WARDEN／Street King**：長皮衣、淺色尖髮、重手套與幫派徽記。
  衝拳、地面重擊、連擊動作與短震波，教導預警與換巷／閃避。
- **RELAY／Phantom Enforcer**：面罩、發光護目鏡、工業護甲與機械拳套。
  突進、電波、防守、定點打擊，最多召喚一名支援。
- **SIGNAL OVERLORD**：保留內部 ID `NULL`；寬肩機械身體、角狀頭甲、反應爐核心。
  第一階段為能量射擊、重連擊、震波及傳送；第二階段加入雷射、鎖定地面打擊、
  最多兩名分身，並縮短收招；第三階段增加組合變化，同時暴露核心，使玩家傷害提高。

頭目入場有短暫保護及動作／提示，各自有專用入場音效。攻擊地面框使用實際攻擊資料，
定點打擊鎖定預警位置，傳送會先標記落點，落地後留反擊時間且不直接傷害玩家。
重擊破防不要求特定角色。頭目房不沿用通電軌道，避免疊加無法迴避的壓力。
死亡不再週期閃爍，頭目保留 1.35 秒敗北動畫；RELAY 有火花，OVERLORD 逐行瓦解。

## 場景與開場

十二個快取區域構圖：

1. 燈籠巷 → 夜市 → 雨夜商圈 → 幫派路口。
2. 車站入口 → 空月台 → 維修通道 → 保全控制室。
3. 保全關卡 → 地下實驗室 → 資料通道 → 核心頭目房。

保留視差，新增招牌、攤棚、燈籠、販賣機、海報、街燈、管線、蒸氣、監控畫面、
培養槽、伺服器與反應爐。背景裝飾位於角色之後，保留街道辨識度。

11 秒開場重組為 CRT → 城市／雨 → 敵影 → 主角入場 → 訊號干擾 → 標誌。
畫面、角色、標誌、上下字幕及跳過提示分區；標誌有獨立底板，避免與招牌疊字。
非阻塞計時，Enter／Space／Esc 可跳過；同一次按壓不會連續跳過後續選單。
400×300 邏輯畫布沿用最近鄰放大，不同比例畫布使用等比縮放及留邊。

## 主要檔案

- 新增 `outfits.py`、`wardrobe.py`：服裝資料、身體附著繪製與獨立頭目像素圖。
- 新增 `ai.py`：與 EnemyFighter 組合的 BossBrain，管理專屬模式與階段。
- 新增 `effects.py`、`scenery.py`：攻擊預警及十二區場景。
- 新增 `cinematic.py`、`review.py`：開場排版及可重現的畫面檢視工具。
- 修改 `data.py`、`model.py`、`art.py`、`game.py`、`build_audio.py`。
- 修改街機 `neon_brawl_scene.py` 的恢復輸入狀態、`audio_manager.py` 的三個新音效登錄，
  新增 `brawl_warden.wav`、`brawl_relay.wav`、`brawl_overlord.wav`。
- 新增 `tests/test_evolution.py`，更新普通操作測試駕駛及街機通關測試；更新 README。

沒有更動機台位置、遊玩費用、結算服務或存檔格式，也沒有修改其他遊戲的實作。

## 最終測試結果

Python 3.12.3 / pygame-ce 2.5.8，使用專案 `.venv` 與 SDL dummy 影像／音訊。

| 測試組 | 精確結果 |
|---|---|
| 新版戰鬥、服裝、分關、頭目、開場與完整街機流程 | 57 tests / 6.230s / OK |
| 既有遊戲、房間、經濟與音訊管理 | 314 tests / 60.875s / OK |
| 檔案相容性、機台、音訊生命週期及設定 | 243 tests / 45.137s / OK |

以上為互不重複的 **614 項測試，零失敗、零錯誤**。最後的衝刺時間積分修改由專項
57 項重跑驗證；其他遊戲與共用音訊程式在回歸之後沒有再改動。

測試涵蓋服裝輪廓／鏡像／畫布、分關出生池、出生距離、實際傷害倍率、盾兵破防、
三個頭目的攻擊模式、三階段轉換、定點鎖定、傳送安全、召援上限、死亡動畫等待、
攻擊去重、衝刺不同步長一致性，以及每 0.1 秒的開場文字與角色矩形分離。
亦測試 320×240、800×600、1280×720、1200×900 畫布。

場景層鍵盤通關明確檢查三關、NULL 第二及第三階段、結局、結果、返回街機，
並確認一次扣幣、一次領獎；戰敗、暫停退出、視窗關閉、啟動前退款及券退款仍通過。

最後模擬駕駛僅使用正常動作、換巷、破盾及拾取檢查點食物，未改生命、傷害、朝向
或跳過敵人。剩餘 HP 是最終檢查點補給之後的結果：

| 角色 | 結果 | 擊敗敵人 | 最終 HP | 承受傷害 | 遊戲時間 |
|---|---|---:|---:|---:|---:|
| REX | 勝利 | 73 | 140 | 264 | 344.4 秒 |
| NOVA | 勝利 | 73 | 112 | 355 | 437.6 秒 |
| BRUNO | 勝利 | 73 | 185 | 204 | 262.5 秒 |

已實際檢視 Pygame 渲染的六個開場節點、十二區戰鬥、17 套服裝、新敵人、三頭目及
三種攻擊預警截圖；檢視後修正標誌與商店文字疊印、刀刃手部定位等問題。
這些包含指定狀態的渲染檢視，不是聲稱進行了真人桌面遊玩。
240 幀原生渲染樣本平均約 **0.39 ms/frame**，僅是此環境的繪圖樣本，非完整遊戲 FPS。

## 重現命令與手動驗收

```sh
cd /home/nora/AOOP_Final
.venv/bin/python arcade_lobby/main.py
```

從 HOME 向左到 Arcade Floor，靠近左島台 NEON BRAWL，按 E 確認。

1. 看完整開場，再重入機台測試 Enter／Space／Esc 跳過及長按不連跳。
2. 分別選三位角色，使用原 WASD、J/K/L/U/I/E 控制。
3. 第一關觀察服裝與近戰教學；第二關以 K 破盾、換巷躲射擊。
4. 第三關注意刺客突進、義體電波、狙擊預警及四個區域的場景變化。
5. 頭目預警時提早換巷；傳送後有反擊窗口；觀察 OVERLORD 三階段與核心暴露。
6. 測試暫停、重看操作、退出、戰敗及勝利結算；確認回街機並只領一次票。
7. 測試 F4 音量、靜音及其他舊遊戲。

```sh
export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:.
.venv/bin/python -m unittest neon_brawl.tests.test_combat neon_brawl.tests.test_evolution test_neon_brawl -q
.venv/bin/python -m unittest test_rooms test_economy test_rewards test_cat_maze test_galaxy_defender test_pixel_volleyball test_racer_launch test_puzzle_maze test_audio_manager -q
.venv/bin/python -m unittest test_machine_themes test_profiles test_reward_loop test_save_lock test_single_player test_scene_wipe test_audio_lifecycle test_audio_system test_audio_settings -q
.venv/bin/python -m neon_brawl.review --output /tmp/neon-brawl-review
.venv/bin/python -m neon_brawl.tests.pilot
```

## 已知限制

未進行真人桌面通關或實體音訊試聽。普通操作駕駛證明可完成，不能代替真人手感與
首輪耗時測試。服裝沿用共同骨架，場景沿用限色像素構圖；部分動作採用單次判傷的
多擊視覺，並非可以多次扣血的連段。未宣稱全儲存庫所有測試均已執行。

## Git 紀錄與作者核對

在既有 `feature/neon-brawl` 開發，沒有切換／改寫 main、沒有 squash、rebase、
amend、push 或 merge。提交前檢查狀態，只加入任務相關檔案。

本機作者為 `nora950817 <nora.ee13@nycu.edu.tw>`，與已連線 GitHub 帳號回傳的
nickname／email 相符。連線工具沒有提供 verified email 欄位，因此無法確認信箱
的驗證狀態；沒有擅自修改作者設定或歷史。

Phase 2 的開發提交：

- `9ede130` feat(neon-brawl): add articulated enemy outfits and bespoke boss silhouettes
- `a64a6b9` feat(neon-brawl): introduce staged enemy tactics and centralized damage scaling
- `ae005fb` feat(neon-brawl): evolve boss counterplay and build twelve district scenes
- `7deee81` feat(neon-brawl): recompose cinematic zones and polish readable combat visuals
- `20ed286` fix(neon-brawl): anchor duelist and assassin blades to animated hands
- `e0b9176` docs(neon-brawl): explain new enemy counters and evolved campaign
- `7349c3e` fix(neon-brawl): integrate dash motion only during active attack frames

最終驗證文件提交的 ID 請見 `git log`（避免文件對自身提交 ID 形成循環）。
唯讀 `git ls-remote` 查得遠端 feature 分支為 `c1dbd89`；本機 Git connectivity 檢查通過。
可以由使用者自行正常 push，保留所有原始提交，不需要 squash 或 force push。
