# 主線任務測試指令

所有指令都在 `arcade_lobby/` 資料夾裡執行：

```bash
cd arcade_lobby
```

## 1. 自己動手玩（臨時存檔）

`play_story.py` 會建一個**臨時存檔**，直接站在主線的某個階段。你在 `saves/` 的真實存檔完全不會被讀取或修改。
- 臨時存檔放在系統暫存資料夾，啟動時會印出路徑。
- 預設給 300 代幣、300 彩票。
- Debug 鍵已開啟：F5 +10 代幣、F6 跳到隔天、F7 刷新每日任務、F8/F9 加測試道具。
- 關閉視窗就結束。

| 指令 | 從哪裡開始 | 要測什麼 |
|---|---|---|
| `python3 play_story.py new` | 全新玩家 | 開場動畫、新手任務（Miao 帶路、見 Mochi、玩 3 台機器、贏彩票） |
| `python3 play_story.py vending` | 新手任務完成 | 找出販賣機的秘密畫面 |
| `python3 play_story.py ch1` | 第一章開啟 | 問 Mochi Retro Racer 的故事，在 Retro Racer 找到 Reverse Road（秘密道具 01） |
| `python3 play_story.py trial01` | 已有秘密道具 01 | 再開一次販賣機秘密畫面 → Legacy Terminal → Trial 01 |
| `python3 play_story.py ch2` | 第二章開啟 | 扭蛋機的提示卡、三個小遊戲的符號 |
| `python3 play_story.py routes` | 第二章開啟，三個秘密都已經出現 | 不用先達成路線條件，直接去三個小遊戲找符號 |
| `python3 play_story.py clues` | 三個符號都已找到 | 回大廳等 Miao 主動說話，找 Mochi 看紀錄，再到夾娃娃機按 W 開鎖 |
| `python3 play_story.py solved` | 符號鎖已打開 | 在 NEON CLAW 夾到 Golden Cat（秘密道具 02） |

接著上次的臨時存檔繼續玩（不重建）：

```bash
python3 play_story.py --keep
```

看說明：

```bash
python3 play_story.py --help
```

### 只測 Trial 01 的房間

跳過大廳和販賣機，直接進 Trial 01 房間（存檔只在記憶體裡，不會寫檔）：

```bash
python3 play_trial01.py
```

連房間的開場一起看：

```bash
python3 play_trial01.py --fresh
```

### 第二章要做的事（`ch2` 階段）

1. **提示卡**：到 Prize Plaza 的扭蛋機抽卡。三張卡不會重複，連續 4 抽沒卡，下一抽保證出卡；最多 15 抽全部到手。卡片可以在背包重讀，不是必要的。
2. **三個符號**（每個小遊戲有兩條路，結果一樣；找到的順序不限）。達成路線只會讓秘密「出現」，還是要自己去找；路線條件存在存檔裡，離開遊戲或重新讀檔都還在，直到找到為止。

| 遊戲 | 技術路線 | 堅持路線（可跨多次遊玩累積，贏了也不歸零） | 發現 |
|---|---|---|---|
| Neon Cat Maze | 在一局內完成第 3 關 | 12 次 game over，每次至少 600 分 | 左上角外牆出現細裂縫，走進去牆會崩開，走到暗道盡頭，牌子亮起金色星星和「I」 |
| Starfall Assault | 打倒第 10 波（第二隻 Mothership） | 12 次 game over，每次至少 250 分 | 每次波與波之間的空檔都會有灰色船飛過（下一波會等它飛完），站在光束下收到訊號，它投射出月亮和「II」；錯過會在下一次空檔或下一局再來 |
| Cat Volleyball | 贏 Sandra 一場 | 輸 12 場，每場至少得 1 分 | 比賽打完後先播約 2.7 秒的動畫：一張舊票從看台飛到貓手上，放大顯示貓掌和「III」，再釘到角落，然後才出現勝負畫面 |

中途重新開始、從暫停選單離開、還沒打完就離開，都不算堅持路線的次數。

   找到的符號會自動記在任務日誌：按 Q，再按右鍵翻到「CHAPTER 02」頁的 RECOVERED SYMBOLS。順序固定是 I、II、III，還沒找到的顯示 `???`。右下角的任務追蹤只顯示 `SYMBOLS N/3`。

3. **Miao**：三個符號都找到後回到大廳，等畫面上的提示跑完，她會主動說一次話。
4. **Mochi 和獎品鎖**：找 Mochi 聊天，選「Did you find something unusual?」，她會給你看維修紀錄（只能閱讀），告訴你鎖在夾娃娃機上。到 NEON CLAW 按 W 打開獎品鎖：左右鍵選格、上下鍵轉符號、E 嘗試，按 Q 可以直接看任務日誌裡找到的符號。正確是 星星 → 月亮 → 貓掌。鎖一開始是空的，不會自動填入；錯了只會得到一句溫和的回覆，可以直接再試。打開後回到夾娃娃機，Golden Cat 會出現在機台裡。
5. **Golden Cat**：在 NEON CLAW 用一般玩法夾。每次滑掉，下次會抓得更緊；滑掉 3 次後，只要碰到就一定抓得住。真的掉進出口才算拿到秘密道具 02，而且只給一次。

### 從新建檔案一路自動玩到第二章（無視窗）

```bash
python3 verify_main_story.py
```

用真實的按鍵事件，從標題畫面建立新檔案，依序完成：開場、導覽、販賣機秘密、Reverse Gear、Trial 01（含 HAPPY BREAKOUT.EXE）、提示卡、三個符號、Miao、符號鎖、Golden Cat，最後檢查 Trial 02 的條件，並重新讀檔確認進度都還在。存檔放在臨時資料夾，跑完會刪掉。截圖存在 `review_screenshots/main_story/`。在這台電腦上大約跑 5 分鐘。

## 2. 自動測試

### 主線相關的測試

```bash
python3 -m unittest test_story test_chapters test_vending test_mochi_chat test_reverse_gear test_golden_age test_lifetime_earnings test_capsule test_capsule_exchange test_claw_machine test_forgotten_games test_inventory test_collection test_showcase
```

`test_golden_age` 要跑大約 6 分鐘。只想快速檢查第二章：

```bash
python3 -m unittest test_forgotten_games test_capsule test_claw_machine test_mochi_chat test_chapters
```

### 小遊戲裡的秘密

這三個指令要回到專案根目錄執行：

```bash
cd ../neon_cat_maze/tests && PYTHONPATH=../.. python3 -m unittest discover; cd -
```

```bash
cd ../galaxy_defender/tests && PYTHONPATH=../.. python3 -m unittest discover; cd -
```

```bash
cd ../pixel_volleyball/tests && PYTHONPATH=../.. python3 -m unittest discover; cd -
```

Retro Racer 的 Reverse Road：

```bash
cd ../retro_racer && PYTHONPATH=.. python3 -m unittest test_reverse_road test_out_of_time; cd -
```

### 完整的 Arcade Hub 測試（每個模組平行跑，約 3–4 分鐘）

```bash
ls test_*.py | sed 's/\.py$//' | xargs -P 14 -I{} sh -c 'python3 -m unittest {} > {}.log 2>&1 && echo "OK   {}" || echo "FAIL {}"'
```

有 FAIL 的話，看那個模組的 `.log` 檔（例如 `test_story.log`）。`.log` 檔已在 `.gitignore` 裡。
