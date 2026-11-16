# Grey Pixel／Forgotten Arcade Workshop 開發預覽

## 直接啟動正式工坊

```bash
cd /home/nora/AOOP_Final
.venv/bin/python -m puzzle_maze --dev-preview developer-room
```

依賴與主遊戲相同：專案虛擬環境、Python、pygame-ce，不需額外素材或網路。這個入口直接進入正式 r28 **The Forgotten Arcade Workshop**，不是另一個預覽假房間。

## 入口與控制

| 入口 | 內容 |
|---|---|
| `--dev-preview grey-pixel` | 正式發現與道具揭示 → 工坊 → Miao 演出 → 探索 |
| `--dev-preview developer-room` | 直接探索已完成演出的工坊 |
| `--dev-preview miao-entrance` | 從門口重播 Miao 與原型機記錄 |
| `--dev-preview developer-diaries` | 第一篇維修日記附近 |
| `--dev-preview kevin-notes` | 開啟 Kevin 的四頁待辦清單 |

| 鍵 | 功能 |
|---|---|
| WASD／方向鍵 | 正式移動與碰撞 |
| E／Enter | 靠近物件出現 `[E/ENTER] INSPECT` 後檢視；劇情第一次按下補完文字，再按一次換句 |
| Enter／E | 關閉目前閱讀視窗 |
| 左右鍵 | 待辦清單翻頁 |
| Space | 跳過發現或入場動畫 |
| R | 重建目前預覽 |
| F5 | 從 Grey Pixel 全序列重來 |
| F6 | 直接回工坊 |
| F7 | 重播 Miao 入場與原型機回憶 |
| F8 | 依次開啟既有可選日記及生活筆記 |
| F9 | 四頁待辦清單 |
| Esc | 安全退出預覽；閱讀也可用 Enter 關閉 |

提示直接沿用 Golden Age 的 `ui.PromptBubble`，文字為 `[E/ENTER] INSPECT`，不提前透露物件名稱或內容。霓虹邊框、尾巴、淡入、浮動與脈動均使用同一套元件；定位限制在 320×240 畫布內並避開家具。按下 E／Enter 後，以泛黃、磨損紙邊、摺痕與褪色墨字的舊紙卡顯示內容。

## 開場與倉庫機房風格

入場沿用 Golden Age 的 `StoryDialogue`：上方 272×50px 暗灰氣泡框、低亮度青綠／灰紫霓虹邊線與 Miao 頭像，42 字／秒逐字出現，每三字觸發同一個 `vend_select.wav`。以 320px 原生畫布調整框寬及換行，避免縮圖破壞字形。Enter／E 先補完文字，再次按下才換句；Space 跳過整段，F7 可重播。

房間使用灰暗、磨損的澆築水泥地，具有細小砂礫、裂痕與污漬。上方三台機台各 24×40px；工程桌調整為 100×48px，分開電腦、測試儀器、筆記與零件。倉庫鐵門內嵌左牆，工具抽屜、零件箱、備用 CRT、電表與麵包板試驗箱、線捲、伺服器和貓咪用品沿邊分區，保留中央通道。牆上有 `GAME → ROOM → CAT` 的 AOOP 黑板、補過的外套與失去指針的時鐘。全部 31 項調查內容可由正式移動抵達。

入場參考 Reverse Gear，改為覆蓋全畫面的訊號撕裂、霓虹座標框、掃描線與 CRT 水平點亮。房間全程維持原比例，已刪除原先突然放大主角的鏡頭。`A Small Memory` 的 160×108px 泛黃照片直接使用 Lobby 的 `PlayerLook`／`player_sheet` 小角色與操作姿勢：Kevin 穿工作服，帶識別證和筆，在麵包板旁修機；不使用大型人物肖像。

新便條使用簡單英文和直接的笑點：10mm 套筒被 Miao 坐住、只有 Kevin 看著才正常的零件、會打噴嚏的 Bug 箱、互相散熱卻沒插電的風扇，以及放了三明治仍無法工作的麵包板。

## 房間配置

舊沙發、書櫃、茶几與大片地毯已移除。左上是三台故障街機，右上是 Kevin 的工程桌與工具板，左下是接上測試線的第 07 號原型機，左側靠原型機是帶輪維修車，右下只留很小的 Miao 用品角。

四台街機共用 Arcade Floor 真正的 cabinet 繪圖方式，分別有裂掉的 CRT、拆開後面板的配線、凍結錯誤畫面與測試原型。每台都可用 E／Enter 檢視。工具、GPU、鍵盤、照片、筆記與原型記錄也走相同正式互動。

家具與機台實心、不淡化，腳底深度排序；Miao 保留原 Lobby 外觀，會自行散步、跟隨、停留與睡覺；主角靠近可喚醒、交談，她會避讓而不封住地板。調查提示跟著實際位置移動，閱讀時暫停行動。工坊西門 `(1,7)` 可返回 r24；新入口落點為 `(6,8)`。沙發坐下功能隨沙發一併移除，沒有隱藏的舊座位互動。

## 存檔隔離

PreviewGame 使用正式 Game、RemasteredSession、LabEntrance、GreyPixelReveal、DeveloperRoomArt／WorkshopArt。僅建立一次性前置狀態，固定 `persistent=False`：不讀寫實際玩家存檔、不綁 Lobby 帳戶、不派發真實秘密或 Tokens／Tickets。重播就丟棄本次記憶體狀態。Miao 的散步位置也是當次狀態，正式存檔只保存穩定的故事物件座標，避免把移動中的位置誤判為損壞存檔。

正式舊工作室存檔由 studio_revision 8 安全遷位，保留物品、故事與獎勵；從第 7 版更新前保留 `.pre-studio-v8`，舊有備份不覆寫。

## 截圖與完整正常路線驗證

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m puzzle_maze --dev-preview developer-room --headless --frames 1 --screenshot /tmp/workshop.png
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m puzzle_maze.review_workshop --output /tmp/forgotten-workshop
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=.:puzzle_maze/tests .venv/bin/python -m unittest puzzle_maze.tests.test_workshop puzzle_maze.tests.test_dev_preview -q
```

review_workshop 實際放炸彈、步行取得 Grey Pixel、正常進入 r28、完成對話、以 E／Enter 交替檢視全部 31 項物件、驗證碰撞，再由西門退出。PNG 只存在指定輸出目錄，不加入玩家存檔。舊 review_cozy_studio／review_studio_refinement 指令亦轉接到目前正式工坊。

## 常見問題

- 找不到 pygame：使用 `.venv/bin/python`。
- 找不到 puzzle_maze：先進入 `/home/nora/AOOP_Final`，以 `-m puzzle_maze` 執行。
- 無顯示環境：使用上方 SDL dummy 指令產生真實渲染畫面。
- 想重看故事：F7，或 F5 連 Grey Pixel 一起重播。
- 閱讀按住 Enter：不會連續開關，請放開後再按一次。
- 預覽沒有保存：這是刻意隔離；正式進度請從一般 Arcade 入口測試。

## 倉庫版驗證

已以 `review_workshop` 走完正式炸牆、收集、入場、五句逐字對話、31 項調查、碰撞和西門退出。截圖包含 `06_story_dialogue.png`（打字中）、`dialogue_0_complete.png` 至 `dialogue_4_complete.png`（全文）、`07_workshop_overview.png`。預設位置仍為 `/tmp/forgotten-workshop`，可用 `--output` 指定。

新增 `puzzle_maze.tests.test_warehouse` 驗證上方對話、打字音效回呼、補完後換句，以及舊版存檔卡入移動後設備的安全遷位與不覆寫備份。自動檢查使用 SDL dummy；音效聽感仍需在有音訊的預覽視窗確認。

`puzzle_maze.tests.test_studio_companion` 以 70 秒正常 tick 驗證散步、跟隨、睡覺、醒來、動態交談與家具碰撞，並逐格驗證空地可行走與出口連通。`review_workshop` 額外輸出 全畫面 CRT 各階段、`miao_roaming.png` 與 `miao_sleeping.png`。
