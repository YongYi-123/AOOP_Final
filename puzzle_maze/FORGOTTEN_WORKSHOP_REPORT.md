# Grey Pixel：The Forgotten Arcade Workshop

## 根本設計變更

正式 r28 從「第二間溫馨客廳」改成 Kevin 曾維修、開發與測試街機的隱藏工坊。舊沙發、茶几、書櫃、大地毯、室內生活式配置與坐下互動全部移除；不是保留原客廳再加幾台機器。

新配置：左上三台故障街機、右上主工程檯與工具板、左下連線測試原型機、中央維修車與零件、右下小型 Miao 用品角。中央維修通道保持暢通，西門仍可回到迷宮。新的安全入口落點為 (6,8)，避免人物被左下原型機遮住。

本次訊息沒有可讀取的附件圖片，因此以修改前實際 Developer Room、真正 Arcade Floor 與 Golden Age 的新擷取畫面作比較。已閱讀 arcade_lobby/machine.py 的 _build_cabinet、機殼與腳位，machine_themes.py，以及 HOME／Golden Age 既有設計；也實際啟動 Arcade Game、經 Vending Machine／Legacy Terminal 進入 Golden Age 並開啟觀察圖片。沒有修改 Golden Age、HOME 或其他遊戲。

## 街機與工程美術

四台機器不是通用長方形：workshop_art.cabinet 直接呼叫 Arcade Floor 使用的 machine._build_cabinet，保留 36×62 原生像素的斜面機殼、CRT 框、搖桿、按鈕、投幣門、底座與各遊戲機身裝飾，再做褪色、磨損與維修改繪。

1. 裂掉的 CRT：賽車街機外殼、分支裂紋、受損面板。
2. 拆開的背板：露出線路、板卡、接頭與框架，移除正面操作台的視覺。
3. 凍結錯誤畫面：舊迷宮街機、ERR 與停滯畫面、灰塵刮痕。
4. 第 07 號原型機：測試 CRT、外接電路架、開啟的維修窗與通往工作檯的線路。

工程檯包含兩台 CRT、鍵盤、滑鼠、雙風扇 GPU、焊接設備、工具、零件抽屜、暖色檯燈、照片、筆記、鴨子與咖啡。維修車有腳輪、控制器、晶片板與手工具。房間還有線槽、維修區地面標記、工具板與螺絲／板卡細節。沒有大型牆面說明文字。

Miao 的床、罐頭、水碗與玩具縮成一小角，與機械設備形成溫柔對比；她仍使用 Lobby 原角色與眨眼、抬頭、耳朵及尾巴待機動作。

## 故事與動畫

首次正常取得 Grey Pixel 並入室，沿用真實迷宮暗化／干擾與工坊淡入。原型機先醒來，再輪到工程桌螢幕；Miao 由西門走進，走過沒有家具碰撞的通道，注意連線中的原型機。

主事件改成「Return Path」：鏡頭聚焦原型機，顯示 Kevin 維修原型、Miao 坐在旁邊的像素回憶。新對話只透露他留下可返回的路，沒有重講身分或整個 Arcade 謎底。灰色測試像素沿線路往返，使 Grey Pixel 與這台未完成的實驗有所連結。

四項新可選機台內容：禁止用槌子修 CRT、同時接到門鈴的兩條矛盾標籤、等待貓長出拇指的第二玩家，以及原型的「Leave a way back. Always.」維修記錄。已搜尋既有 Golden Age／工程日記，沒有這些相同文字。保留原來 Kevin／Miao 筆記與四頁待辦的穩定 ID。

所有遊戲內容為英文；維修記錄以文字與像素回憶呈現，沒有配製新的真人語音。

## 精確互動與碰撞

- 所有可檢視物件只顯示 `[E/ENTER] INSPECT`，不提前顯示名稱或內容。
- E 與 Enter 都走同一正式檢視路徑；按住不會重複開關。內容視窗可關閉，待辦可翻頁。
- 最近物件優先，距離相同才比較朝向；只出現一個浮動框。框的位置避開角色與大型設備，有一像素的輕微浮動。
- 實際 QA 發現原字級會把長提示截成省略號，已在現有 NativeText 管線增加原生 8px 小字選項，確認整句完整呈現。其他文字預設字級不變。
- 沒有恢復底部資訊列，背景仍覆蓋整個原生 320×240。
- 街機、工程檯、維修車、貓用品與 Miao 保持足部碰撞、實心渲染與腳底排序，沒有接近時半透明。桌燈是工作檯的一部分，不會穿過。
- 舊 SofaSeat 狀態與無人使用的客廳 furniture 繪圖模組已刪除；預覽與正式遊戲仍共用同一個真實工坊。

## 正式路徑與存檔

Arcade Lobby → PuzzleMazeScene → Game → RemasteredSession → r24 取得 Grey Pixel → r28 → Renderer.world → studio_view.draw_studio → DeveloperRoomArt（WorkshopArt）。美術主要檔為 workshop_art.py；房間幾何與互動位置以 studio_layout.py 為共同來源。

room ID r28、Grey Pixel 的 dungeon_grey_pixel／Item 03、Golden Cat 的 claw_secret_reward／Item 02 沒有變更。studio_revision 更新至 4，舊客廳存檔遷到合法位置，保留秘密、物品與故事；新機台缺少的 snapshot 狀態由正式房間初始化。由第 3 版保存前保留不可覆寫的 `.pre-studio-v4` 備份。預覽 persistent=False，不動真人進度或經濟。

## 測試結果

| 範圍 | 結果 |
|---|---|
| 全部 Puzzle Maze | 272 tests / 72.191s / OK |
| 最後工坊／預覽專項 | 15 tests / 7.147s / OK（與全套重疊） |
| Lobby、Maze 整合、秘密、經濟、獎勵、房間、Miao、HOME | 320 tests / 87.939s / OK |
| Golden Age 入口、房間、存檔、內容、退出返回 | 44 tests / 85.872s / OK |
| 真實流程截圖工具 | 正常入室、全部 24 項互動、碰撞與退出成功 |

新的工坊測試覆蓋四台不同機殼、沒有客廳家具、所有互動及出口連通、每一物件 E／Enter 都可用、精確完整提示不省略、無自動名稱、按住 Enter、不透明像素、Miao 碰撞、新可選故事、舊客廳存檔缺少新機台狀態的遷移與備份。舊沙發測試改為原型機檢視後恢復控制；沒有保留不存在的座位或放寬現有進度檢查。

完整 Maze 後又完成最後微幅浮動動畫及舊擷取工具落點更新，15 項專項與實際流程工具已再次驗證。既有存檔、獎勵、迷宮完整路線與秘密重複領取防護測試仍在全套內。

## 真實畫面驗證

已開啟檢視：修改前 Developer Room、Arcade Floor、Golden Age、新工坊全景、完整浮動提示、原型機回憶、原型檢視視窗及前後比較。全景明確不再使用沙發／地毯構圖；新機台與 Lobby 共有輪廓及控制台形狀。

圖片：

- /tmp/workshop-comparison.png：舊房間／新工坊／Golden Age 三方比較。
- /tmp/workshop-reference/arcade-floor.png、golden-age.png：實際 Lobby 遊戲畫面。
- /tmp/forgotten-workshop/07_workshop_overview.png：正常進入後的工坊。
- /tmp/forgotten-workshop/inspect_work_crt_prompt.png：完整提示。
- /tmp/forgotten-workshop/inspect_work_prototype_open.png：按鍵後才出現內容。
- /tmp/forgotten-workshop/05_archived_repair.png：主故事回憶。

這是 SDL dummy 中實際啟動、按鍵操作與渲染後的圖片檢視；沒有宣稱桌面真人完整操作或音效聽感驗收。圖片只在 /tmp，不加入 Git。

## 直接測試

```bash
cd /home/nora/AOOP_Final
.venv/bin/python -m puzzle_maze --dev-preview developer-room
```

WASD／方向鍵走路，浮動 `[E/ENTER] INSPECT` 出現後按任一鍵檢視；Enter 關閉，F7 重播主事件，F5 從 Grey Pixel 開始，F9 待辦，Esc 退出。預覽不會改真實存檔。

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m puzzle_maze.review_workshop --output /tmp/forgotten-workshop
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=.:puzzle_maze/tests .venv/bin/python -m unittest discover -s puzzle_maze/tests -p 'test_*.py' -q
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:.:puzzle_maze/tests .venv/bin/python -m unittest test_puzzle_maze test_maze45_secret test_economy test_rewards test_rooms test_miao_meow test_home_decor -q
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m unittest test_golden_age.EntryTests test_golden_age.RoomTests test_golden_age.SaveTests test_golden_age.ContentTests test_golden_age.LeaveAndReturnTests -q
```

## Git 與修改檔案

分支沿用 feature/kevin-cozy-studio，從乾淨工作樹 f56a68b 開始，保留原作者及歷史。

- a7775ea feat(maze): replace the lounge with a forgotten arcade repair workshop
- 9123b2e fix(maze): fit inspect prompts and validate the real workshop campaign route
- 文件提交：docs(maze): document the forgotten workshop and verified preview flow（最終 ID 見 git log）。

主要變更：workshop_art.py、developer_art.py、studio_layout.py、studio_interactions.py、studio_view.py、game.py、lab_scene.py、remaster.py、dev_preview.py、render.py、ui.py。移除 studio_furniture.py。新增 review_workshop.py、tests/test_workshop.py，更新既有路線／視覺／預覽驗證工具、攻略、預覽指南與 .gitignore。

本次共三筆真實提交；沒有 Push、Merge、Force Push 或 Squash，其他小遊戲與 Golden Age 檔案沒有修改。可在確認預覽後自行 Push，保留每筆提交。
