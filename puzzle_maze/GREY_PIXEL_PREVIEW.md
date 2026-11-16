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

提示只顯示完整的 `[E/ENTER] INSPECT`，不預告物件名稱或內容；沒有底部資訊面板。最近物件優先，相同距離才參考朝向。提示使用原生 5×7 小像素字，具有輕微浮動，會避開角色與大型設備。物件內容只在按 E／Enter 後出現。

## 開場與倉庫機房風格

入場沿用 Golden Age 的 `StoryDialogue`：上方像素對話框、Miao 頭像與姓名標籤，42 字／秒逐字出現，每三字觸發同一個 `vend_select.wav`。以 320px 原生畫布調整框寬及換行，避免縮圖破壞字形。Enter／E 先補完文字，再次按下才換句；Space 跳過整段，F7 可重播。

房間改用較暗的冷灰水泥地、金屬牆、鏽蝕工作桌；四台機台約 28×48px、工作桌 104×52px，比例比上一版縮小。新增舊伺服器、線材迴圈與外露接頭、保險絲箱、舊 CRT、紙箱及拆下的通風面板。邊緣堆放物件屬場景裝飾；伺服器具有實際碰撞。既有 24 項調查內容保留。

## 房間配置

舊沙發、書櫃、茶几與大片地毯已移除。左上是三台故障街機，右上是 Kevin 的工程桌與工具板，左下是接上測試線的第 07 號原型機，中央是帶輪維修車，右下只留很小的 Miao 用品角。

四台街機共用 Arcade Floor 真正的 cabinet 繪圖方式，分別有裂掉的 CRT、拆開後面板的配線、凍結錯誤畫面與測試原型。每台都可用 E／Enter 檢視。工具、GPU、鍵盤、照片、筆記與原型記錄也走相同正式互動。

家具與機台實心、不淡化，腳底深度排序；Miao 保留原 Lobby 外觀、待機動作與身體碰撞。工坊西門 `(1,7)` 可返回 r24；新入口落點為 `(6,8)`。沙發坐下功能隨沙發一併移除，沒有隱藏的舊座位互動。

## 存檔隔離

PreviewGame 使用正式 Game、RemasteredSession、LabEntrance、GreyPixelReveal、DeveloperRoomArt／WorkshopArt。僅建立一次性前置狀態，固定 `persistent=False`：不讀寫實際玩家存檔、不綁 Lobby 帳戶、不派發真實秘密或 Tokens／Tickets。重播就丟棄本次記憶體狀態。

正式舊工作室存檔由 studio_revision 5 安全遷位，保留物品、故事與獎勵；從第 4 版更新前保留 `.pre-studio-v5`，舊有備份不覆寫。

## 截圖與完整正常路線驗證

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m puzzle_maze --dev-preview developer-room --headless --frames 1 --screenshot /tmp/workshop.png
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m puzzle_maze.review_workshop --output /tmp/forgotten-workshop
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=.:puzzle_maze/tests .venv/bin/python -m unittest puzzle_maze.tests.test_workshop puzzle_maze.tests.test_dev_preview -q
```

review_workshop 實際放炸彈、步行取得 Grey Pixel、正常進入 r28、完成對話、以 E／Enter 交替檢視全部 24 項物件、驗證碰撞，再由西門退出。PNG 只存在指定輸出目錄，不加入玩家存檔。舊 review_cozy_studio／review_studio_refinement 指令亦轉接到目前正式工坊。

## 常見問題

- 找不到 pygame：使用 `.venv/bin/python`。
- 找不到 puzzle_maze：先進入 `/home/nora/AOOP_Final`，以 `-m puzzle_maze` 執行。
- 無顯示環境：使用上方 SDL dummy 指令產生真實渲染畫面。
- 想重看故事：F7，或 F5 連 Grey Pixel 一起重播。
- 閱讀按住 Enter：不會連續開關，請放開後再按一次。
- 預覽沒有保存：這是刻意隔離；正式進度請從一般 Arcade 入口測試。

## 倉庫版驗證

已以 `review_workshop` 走完正式炸牆、收集、入場、五句逐字對話、24 項調查、碰撞和西門退出。截圖包含 `06_story_dialogue.png`（打字中）、`dialogue_0_complete.png` 至 `dialogue_4_complete.png`（全文）、`07_workshop_overview.png`。預設位置仍為 `/tmp/forgotten-workshop`，可用 `--output` 指定。

新增 `puzzle_maze.tests.test_warehouse` 驗證上方對話、打字音效回呼、補完後換句，以及第 4 版存檔卡入新設備的安全遷位與不覆寫備份。自動檢查使用 SDL dummy；音效聽感仍需在有音訊的預覽視窗確認。
