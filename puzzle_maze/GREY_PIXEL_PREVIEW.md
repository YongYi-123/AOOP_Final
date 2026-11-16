# Grey Pixel / Developer Room 預覽與驗證

## 直接測試

```bash
cd /home/nora/AOOP_Final
.venv/bin/python -m puzzle_maze --dev-preview developer-room
```

這是正式 r28 **The Forgotten Arcade Workshop**，使用正式 Game、RemasteredSession、碰撞、調查、Miao 與渲染元件。預覽固定 `persistent=False`，不讀寫玩家存檔、不綁 Lobby 帳戶、不派發真實獎勵。

| 入口 | 內容 |
|---|---|
| `--dev-preview grey-pixel` | Grey Pixel 發現演出，再正常進工坊 |
| `--dev-preview developer-room` | 直接探索工坊 |
| `--dev-preview miao-entrance` | 重播全畫面 CRT 入場與泛黃修機照片 |
| `--dev-preview developer-diaries` | 工程桌實驗筆記旁 |
| `--dev-preview kevin-notes` | 直接調查待辦清單 |

| 按鍵 | 功能 |
|---|---|
| WASD / 方向鍵 | 移動；閱讀時鎖住角色移動 |
| E / Enter | 調查、補完逐字對話、繼續對話；NOTE 顯示 Read more 時讀本頁後段，Continue 時到下一頁，Close 時關閉 |
| Left / Right | NOTE 前後翻頁，限制在第一頁與最後一頁之間 |
| Up / Down / 滑鼠滾輪 | 在同一個較長頁面內捲動，右下角 X/Y 不變 |
| Esc | 關閉調查 / NOTE；未開資訊時退出預覽 |
| Space | 跳過原本 Grey Pixel / 入場演出；調查中與確認鍵相同 |
| R | 重建一次性預覽，清除本次調查次數 |
| F5 / F6 / F7 | 重播全部 / 直接回房間 / 重播入場 |
| F8 / F9 | 輪流調查主要物件 / 調查待辦清單 |

功能鍵仍可用，但不再覆蓋開場畫面。Grey Pixel 標題與揭示文字按實際字寬置中，包括有黑邊的視窗。

## 主角觀察與 Kevin 的 NOTE

四份主要文件先以主角口吻、頭像與 Golden Age 共用的逐字對話觀察物件，確認後才進入 Kevin 的第一人稱內容。翻頁不會增加調查次數，也不會切換成下一個回應。

| 實體 / ID | 文件 | 固定頁數 | 外觀 |
|---|---|---|---|
| 工程桌上的筆記本 `note` | KEVIN'S EXPERIMENT LOG | 7 | 泛黃裝訂筆記 |
| 維修車上的數位維修站 `repair_log` | ARCADE REPAIR LOG | 4 | 淺灰綠維修表單 |
| 唯一的工作桌剪貼板 `studio_todo` | KEVIN'S PERSONAL TO-DO LIST | 3 | 手寫檢核清單 |
| 工作站另一個螢幕的資料夾 `project_file` | ABANDONED GAME PROJECT FILE | 4 | 泛黃紙底、終端風格頁首 |

實作採用提供的完整段落，包含 CPU 慢 23%、PleaseDoNotAddAnotherBoss、Grand Theft Arcade、Miao 的罐頭、02:43 AM 編譯成功與日常工作。像素字型不支援的長破折號、箭頭和彎引號僅在顯示時轉成 ASCII。

較短的罐頭櫃、咖啡杯、GPU、鍵盤、工具、線材與貓床資訊改由主角逐字唸出，搭配原本的打字音效，不再逐件開 NOTE。機台和配電櫃的較長測試 / 維修紀錄則先觀察，再以 Kevin 第一人稱開啟紙頁。所有 NOTE 都是泛黃底，包括數位專案檔案；藉裝訂、表單線、剪貼板與終端風格頁首區分來源。

所有 NOTE 本文字級一致，原生字高 7px、行高 11px，段落之間另留一空行。每個可視區最多 16 行，長頁用明確的 Read more、Up/Down 或滾輪閱讀，保留真正的 1/7 至 7/7 等頁碼。頁碼固定在右下角，頁面切換只有短暫邊緣提示，不阻擋輸入。一般資訊窗也使用 11px 行高。

## 多次調查與首次錄音

黑板、四台原型街機、工作桌、終端、待辦清單、貓床、配電櫃和原始控制系統使用指定的多次回應。一般重要物件按 0 → 1 → 2 → 0 循環，不立即重複；四份文件保持固定內容，開頭觀察循環變化。

`work_prototype` 首次調查會啟動短暫掃描線與 Kevin 錄音。中途退出不算完成，下次仍先播放必要內容；完成後才顯示 SYSTEM DIAGNOSTICS、A FAMILIAR SIGNATURE 等回應。完成狀態與每個物件的調查次數存入遠征擴充資料。

現有 Memory Fragment 由 Secret Trial 控制，所以錄音最後的恢復訊息使用 **LOCAL RECORDING RESTORED.**；不發送新 trial 事件、不新增秘密道具、不改變 Tokens / Tickets / 灰色像素進度。Grey Pixel 仍沿既有 Secret Item 03 與 Lobby 章節條件同步；照片仍使用原有 Kevin easter egg。

## 環境與可見物件

房間維持灰暗倉庫與破舊水泥地。四台上方街機分別是損壞賽車、按鍵故障格鬥、睡貓進度條、燒痕太空射擊；左下是獨立的斜面原始控制台，不把它當作第五台普通機台。

黑板有 OBJ → ACT → PLY、CPU → RAM、R0、匯流排、小街道與貓咪圖。資訊只畫短標籤與圖形，長內容在調查窗中閱讀。配電櫃只有裝飾性損壞，沒有傷害或不可避免的危險。

已移除七張開發日記與零散提醒紙的實體目標，舊閱讀旗標保留。房內僅三件有用途的紙本：賽車故障小標籤、Kevin 的實驗筆記、待辦清單；格鬥機使用金屬故障牌，其他內容透過螢幕、工具、電路與調查呈現。原有相框是獨立故事物件。

罐頭櫃重畫為開放式貓耳小櫃，可看見三個有金屬頂蓋、彩色肉球標籤的罐頭；原本位置與碰撞不變。

調查提示沿用 Golden Age 的 `[E/ENTER] INSPECT` 氣泡外觀，但以**物品**為錨點，只在物品附近選擇位置。機台會閃屏、終端顯示 ERR、黑板局部發亮、貓床使 Miao 有反應，控制台啟動錄音演出。Miao 仍會漫遊、跟隨、避讓與睡覺。

門使用 Golden Age 窄側門輪廓，位於 x=0 的左側牆體內，沒有凸入通道的外框。西門 `(1,7)` 仍返回 r24；正常入口落點仍為 `(6,8)`。

## 存檔相容

`studio_revision=9` 安全遷移既有房間快照，移除已退休的實體紙條、補入新的可選物件、保留道具、故事、閱讀記錄與獎勵。由第 8 版覆存前建立不覆寫的 `.pre-studio-v9` 備份。未知的新版本物件仍受原有快照驗證，不能借遷移略過壞存檔。

Miao 的走動位置不寫入靜態調查物件座標。`inspection_counts` 和 `prototype_recording_seen` 是獨立的房間狀態，離房、重載與檢查點重設不會額外派發獎勵。

## 自動驗證與截圖

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m puzzle_maze.review_workshop --output /tmp/workshop-review
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m unittest puzzle_maze.tests.test_workshop_overhaul -q
```

`review_workshop` 實際放炸彈、收集 Grey Pixel、步行進入 r28、完成入場、對所有物件調查，再查看主要物件的第二與第三次回應、每份 NOTE 的每一頁與捲動位置、錄音、碰撞、Miao 漫遊 / 睡覺和西門退出。PNG 只寫入指定輸出資料夾。

回歸測試涵蓋完整提供的內容、固定頁數、確認鍵 / 重複鍵、對話與 NOTE 關閉、移動鎖定與恢復、頁碼位置、行距、不同視窗尺寸、舊存檔遷移、計數循環、首次錄音與沒有新獎勵。自動測試使用 SDL dummy，沒有宣稱音效的真人聽感驗收。
