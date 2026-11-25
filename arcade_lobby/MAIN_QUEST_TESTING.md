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
| `python3 play_story.py ch1` | 第一章開啟 | 先找 Miao 聊（她叫你去問 Mochi），再問 Mochi Retro Racer 的故事（聽完 Reverse Road 才會出現；可重聽），在 Retro Racer 找到 Reverse Road（秘密道具 01） |
| `python3 play_story.py trial01` | 已有秘密道具 01 | 再開一次販賣機秘密畫面 → Legacy Terminal → Trial 01 |
| `python3 play_story.py ch2` | 第二章開啟 | 扭蛋機的提示卡、三個小遊戲的符號 |
| `python3 play_story.py routes` | 第二章開啟，三個秘密都已經出現 | 不用先達成路線條件，直接去三個小遊戲找符號 |
| `python3 play_story.py clues` | 三個符號都已找到 | 回大廳等 Miao 主動說話，找 Mochi 看紀錄，再到夾娃娃機按 W 開鎖 |
| `python3 play_story.py solved` | 符號鎖已打開 | 在 NEON CLAW 夾到 Golden Cat（秘密道具 02） |
| `python3 play_story.py trial02` | 已有秘密道具 02，累積賺到 15 代幣 / 150 彩票 | 再開一次販賣機秘密畫面 → Legacy Terminal → Trial 02（THE UNBEATEN RECORD） |

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

Trial 01 新增的兩個謎題（2026-11-17）：

- **PUZZLE 05 照片板（必做）**：右邊牆上的木頭照片板有 4 個空格。4 張舊照片藏在：書桌抽屜裡、書架上的 INTRO TO PROGRAMMING 書頁之間、地上的作業堆底下、床邊小櫃子裡。按 E 查看照片板，用方向鍵選、E 拿起／放下、V 看大圖、ESC 關閉。依照照片裡的變化（電腦從零件到能玩、螢幕上的遊戲越來越完整、桌上的小盆栽越長越大、最後一群朋友在玩）排出正確順序，照片板會「喀」一聲，下面掉出 ARCHIVE INDEX 01。
- **電腦**：開機磁碟還是一樣可以玩 HAPPY BREAKOUT.EXE。LOCKED FILES 要「破關 + 拿到 ARCHIVE INDEX 01」兩個條件都達成才會打開；只破關會顯示 ARCHIVE INDEX NOT FOUND.，順序不限，拿到索引後不用再玩一次 Breakout。
- **貓的秘密（選做）**：查看床上的 Miao Meow 布偶，原本的對話之後會出現鈴鐺，有三個小轉盤。線索：書桌便利貼最後一張（貓的一天）、地上教科書的封底塗鴉、遊戲卡匣側面、床邊櫃側面的雕刻。順序對了按 E，鈴鐺會響，床邊櫃後面的暗格打開，裡面有紙條和 OLD CAT SKETCH（收藏品，只給一次，不給代幣、彩票或任何主線進度）。
- 照片、照片板、索引、鈴鐺、紙條和素描都會存在存檔裡（離開、關遊戲、重玩都不會不見）。舊存檔如果已經完成 Trial 01，記憶碎片照樣保留，重玩時也不需要照片板。

### 只測 Trial 02 的錦標賽大廳

跳過大廳和販賣機，直接進 Trial 02 的 Tournament Hall（存檔只在記憶體裡，不會寫檔）：

```bash
python3 play_trial02.py
```

連開場一起看：

```bash
python3 play_trial02.py --fresh
```

前面的輪都贏了，停在第 N 輪前面的謎題（2 = THE BROKEN BRACKET，3 = THE CHAMPION'S TROPHY）：

```bash
python3 play_trial02.py --round 2
```

```bash
python3 play_trial02.py --round 3
```

謎題也已經解開，直接打第 N 輪：

```bash
python3 play_trial02.py --round 3 --solved
```

三輪都贏了（大廳開著，跟主持人說話開始頒獎典禮，也就是結尾）：

```bash
python3 play_trial02.py --ending
```

Trial 02 的流程：

1. **開場**：MEMORY RECONSTRUCTION LOADED，Miao 和玩家的對話（只播一次，ESC 可跳過）。目標只有「Explore the tournament.」。
2. **大廳**：15 個 NPC 可以按 E 聊天（有些會提到 Kevin，有些只是閒聊或給提示），十幾樣東西可以按 E 查看（排行榜、時鐘、故障的 3 號機、維修紀錄、照片牆等）。聽過 3 個人講 Kevin 之後，Miao 頭上會出現「...」，按 E 跟她說話會播她的回想（只播一次，可以不看）：她和玩家推測 Kevin 大概就是 Trial 01 那間臥室的主人，他真的做到了；她覺得自己好像認識他、可能很親近，但沒有真正想起來。結尾燈光閃爍時她會說好像看過，但「只是一種感覺」。其他時候跟 Miao 說話是提示。
3. **THE MISSING ENTRY（報名謎題）**：看海報（各組別的報名費）、失物招領箱裡的票根（付了多少、報到時間被撕掉一半）、報名簿（只寫付了多少錢、沒寫組別；有些名字被汽水弄髒；退費的人被劃掉）。四個線索都要用到才只剩一個答案：B10。推出代碼後到報名台的終端機：左右鍵選輪、上下鍵轉、E 送出。答錯只會顯示一句回覆，輪子不會被重設，也不會自動填答案。答對後拿到 TOURNAMENT BADGE（只在這個 Trial 裡用，不是秘密道具，也不會進背包）。
4. **三輪比賽，每一輪前面都有一個謎題**：跟舞台上的主持人說話 → FIGHT!。用的是 NEON BRAWL 本身的選角畫面、操作說明、暫停選單（J 輕攻擊、K 重攻擊、L 跳、U 必殺、I 閃避）。輸了可以直接 RETRY 這一輪，或回大廳；已經贏的輪數和已經解開的謎題都會存起來，不用重來。比賽不收代幣、不給彩票。
   - **第 1 輪 THE ROOKIE（簡單）**：謎題是上面的 THE MISSING ENTRY。
   - **謎題 2：THE BROKEN BRACKET**（贏了第 1 輪後）：賽程板亂掉了，主持人不知道準決賽要叫誰。到大廳右下的賽程板（相片牆右邊）：上下選格子、左右換名字（名字照 A→Z 排，已經放在別格的會跳過）、E 標記勝者、X（或 Backspace / Delete）清空目前那格、選 CLEAR 一鍵清空整個板子、選 CHECK 檢查。板子左邊標了 MATCH 1～4（1-2 格是第 1 場、3-4 第 2 場、5-6 第 3 場、7-8 第 4 場），和裁判單上的 MATCH 編號一樣。雜誌架、相片牆、賽程板站在正下方（前面）也能按 E；相片牆左側、賽程板右側也可以。證據有三種（還沒看過裁判單時，Miao 的提示會先叫你去問主持人）：賽程板下方的規則、主持人給的裁判單（勝者是第幾格、比賽時間、備註，但名字被印表機弄糊了）、大家的證詞（贏了第 1 輪後很多 NPC 會講其他場比賽，重複問也會再講）。還要對照報名簿的編號和付費（TOMMY 付 1 代幣 = 少年組）。答案只有一個：3 MEI L. / 4 THE CHALLENGER / 5 DANNY K. / 6 JUNE P. / 7 ROCKO / 8 THE CHAMPION，勝者是 1、4、5、8。答錯只會說「IT STILL DOESN'T ADD UP.」，板子不會被重設或自動改正。
   - **第 2 輪 THE CHALLENGER（普通）**：會防禦、會反擊，重攻擊可以破防。
   - **謎題 3：THE CHAMPION'S TROPHY**（贏了第 2 輪後）：舞台的鑰匙不見了。看相片牆的三張照片（每張有一種獎盃和年份；三張都蓋同樣的 PRINTED 03/91 章，是無害的干擾）、時程板後面夾著的老冠軍紙條（最新的放最靠近門的地方、別讓獎盃背對觀眾），再到獎盃櫃（獎品櫃台右邊）：左右移動、E 拿起再放下（互換位置）、上下轉向、移到右邊的拉桿按 E 試。門在大廳左邊，所以答案從左到右是 搖桿（1990）、火箭（1989）、獎盃杯（1988），刻字都朝前。拉錯只會「CLUNK」，什麼都不會少。打開後拿到 CHAMPIONSHIP STAGE KEY（只在 Trial 裡用），插進舞台左邊的冠軍機台，會出現 DISPLAY DATA UPDATED，排行榜閃一下又恢復。
   - **第 3 輪 THE CHAMPION（普通+）**：NEON BRAWL 的 WARDEN，大招不會被輕攻擊打斷，要閃。
   - 卡關時可以一直跟 Miao 說話。每個階段第一次找她會先聊幾句（第 0 階段：人好多好開心；第 1 階段：剛剛那一擊好帥，然後提醒你先去找主持人拿裁判單；第 2 階段：決賽好興奮，大螢幕好像閃了一下；第 3 階段：冠軍！然後覺得音樂變小聲了），之後才是提示，提示一次比一次清楚，但不會直接講答案。聊過哪幾個階段會存檔。
   - **NPC 對話分四個階段**，階段就是存檔裡贏了幾輪（0～3），讀檔後馬上用對的階段。每個 NPC 每個階段都有自己的話，上一階段的話不會再出現：
     - 第 0 階段（第 1 輪前）：介紹比賽和大廳，五個人會提到 Kevin，櫃台給謎題 1 的方向。
     - 第 1 階段（贏了第 1 輪）：恭喜你、聊其他場比賽。謎題 2 的證詞：TOURNAMENT FAN（冠軍秒殺 ROCKO）、STUDENT（DANNY 贏 JUNE）、NIGHT OWL（DANNY 那場打了三回合）、THE CHALLENGER（擋了 14 次），另外 OLD REGULAR、VISITOR（MEI 和 JUNE 沒有對打）、WAITING PLAYER（TOMMY 是少年組）是輔助證詞。第一次講話就會說，之後輪流也會再說。
     - 第 2 階段（贏了第 2 輪）：聊決賽、老獎盃、相片牆、老冠軍。只指方向（相片牆、年份、時程板後面的紙條、獎盃櫃的拉桿），不會講順序。
     - 第 3 階段（贏了第 3 輪）：贏了之後大廳不會馬上播結尾，可以先到處跟大家道別（大家開始聊要回家，有幾句會有點怪）。準備好了跟主持人說話 → START IT 開始頒獎典禮。
   - **證據（TAB）**：隨時按 TAB 打開 EVIDENCE，左右鍵換頁。ITEMS 頁可以重看找到過的海報、票根、報名簿、賽程板、裁判單（MATCH RECORDS）、獎盃照片、老冠軍的紙條；WHAT PEOPLE SAID 頁是聽過的所有線索對話（誰說的、第幾輪後說的）。在報名終端機、賽程板、獎盃櫃裡面也可以按 TAB 查看，關掉後回到原本的謎題，輸入到一半的東西都還在。找到過的東西和聽過的對話都會存檔。
5. **結尾**：慶祝、彩帶、99%，然後機台自己開機、排行榜出現不可能的分數、音樂失真、EXIT 燈閃、門鎖上、人群停住，CORE：「One more game?」，最後畫面變黑，出現 MEMORY FRAGMENT 02 RECOVERED / TRIAL 02 COMPLETE。（Trial 01 完成時現在也是同一個黑畫面和同一張完成卡。）選 RETURN TO ARCADE 回到 Legacy Terminal；選 STAY IN THE HALL 會重新開始這一晚（重玩不會再給任何東西）。

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

測試已精簡成一小組冒煙／回歸測試（約 300 個，一分鐘內跑完）。主線的完整檢查交給上面的 `verify_main_story.py`。

全部測試（在專案根目錄執行）：

```bash
python3 run_tests.py
```

只跑 Arcade Hub（專案根目錄）：

```bash
python3 run_tests.py arcade_lobby
```

### 主線和開發捷徑的測試

在 `arcade_lobby/` 裡執行：

```bash
python3 -m unittest test_essentials test_chapters test_lifetime_earnings test_maze45_secret
```

`test_essentials` 會檢查 `play_story.py` 的每一個階段、`play_trial01.py`、`play_trial02.py` 的每一種參數、以及 `--debug` 的 F5～F9 都還能用；Trial 完成只記一次、記憶碎片只給一次。

### 小遊戲裡的秘密

Neon Cat Maze、Starfall Assault、Cat Volleyball 的三個符號和 Retro Racer 的 Reverse Road，由 `verify_main_story.py` 用真實按鍵實際玩過一遍來檢查（沒有單獨的自動測試）。

### Lobby 的貓咪午睡彩蛋

從專案根目錄執行 `.venv/bin/python arcade_lobby/main.py`，進入 HOME、ARCADE FLOOR 或 PRIZE PLAZA。
在空地放開方向鍵，連續站著超過 30 秒：目前區域的貓咪會陸續走到腳邊，躺下睡覺並飄出 Z 字。
走動會解除聚集，貓咪會讓出通路；摸貓、選單、劇情、跳舞或切換房間後，等待時間重新計算。
不用修改存檔，也不會獲得道具或改變主線進度。
