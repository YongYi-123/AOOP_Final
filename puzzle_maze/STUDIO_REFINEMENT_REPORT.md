# Developer Room：比例、互動與遺留工作室氛圍更新

## 實作範圍與參考

由乾淨的 feature/kevin-cozy-studio（d16222f）繼續開發，未修改 main、Lobby 或其他小遊戲。實作前閱讀 HOME 的 home_room.py（細小層板、家具足部碰撞、局部燈光），The Golden Age 的 golden_age_art.py（桌面厚度、開放膝部空間、木材陰影）、golden_age_content.py（已有故事與匿名日記），及正式 Grey Pixel／r28 路徑、預覽、家具、對話與存檔程式。

仍是正式 Game.draw → Renderer.world → studio_view.draw_studio，預覽共用同一房間。沒有建立替代假房間，也沒有改 Grey Pixel 或 Golden Cat 的識別、獎勵或故事旗標。

## 可見改善

- 工程桌、主機、書櫃、終端櫃尺寸縮至原圖約 67%；沙發、茶几與貓用品約 80%。保留側面、薄桌緣、桌腳、陰影，碰撞同步按相同比例換算。小植物保留原大小，避免變成難辨識的像素點。
- 主工程桌由 144×75 改成 96×50 原生像素，沙發由 67×46 改成 54×37；保持走道與門口可達。
- 木材與布料減亮、褪色，暗角與局部暖燈形成對比；螢幕微光、稀疏浮塵與入場時逐一啟動的螢幕，帶出被遺留多年的感覺。
- 移除原本牆上的 KEVIN'S STUDIO 大字，不再以牆面文字說明房間。改用小夜窗、淺層板、照片與時鐘。
- 紙本筆記、照片、鍵盤、GPU、咖啡、鴨子與紅按鈕有小型實體圖像；終端、食品櫃、貓床與 Miao 使用對應家具／角色本身。既有二十項故事與可選互動保留。

## E 鍵與沙發

studio_interactions.nearby 是提示與 E 鍵動作的共同來源：優先面向、再按距離選取一格內物件。底部固定顯示 [E] Read Notebook、[E] Check To-Do List、[E] Examine Photograph 等完整動作；遠離就消失，讀紙張／故事時不繪製互動提示。預覽快捷鍵橫幅已停止遮擋正式提示。

沙發從正前方格子 (4,11) 接近、朝上，可按 [E] Sit。0.4 秒緩動將人物移至坐墊前緣，使用既有玩家外觀、彎曲的靴腿與獨立深度排序；按 E 起身再回原本合法腳位，完成後恢復移動。按住 E 不會重複切換。坐姿不寫入存檔，重啟預覽、新遠征、檢視筆記會清除暫時姿勢。

## 入口與故事

首次實際進入 r28 時，LabEntrance 取得進門前的真實迷宮畫面副本：迷宮變暗並出現少量像素干擾，隨後工作室淡入、螢幕逐一醒來，接續原本 Miao 的門口步行與溫柔風扇回憶。可用 Space／Esc 安全跳過，既有完成旗標仍防止首次故事重複派發。沒有新增或重複 The Golden Age 的身分、關係與秘密揭露。所有遊戲文字為英文。

## 測試結果

| 範圍 | 實際結果 |
|---|---|
| 全部 Puzzle Maze | 257 tests / 49.467s / OK |
| 最後坐姿、牆飾與碰撞專項 | 17 tests / 3.208s / OK（與全套重疊） |
| Lobby、Maze 整合、秘密、經濟、獎勵、房間、Miao、HOME 裝飾 | 320 tests / 71.909s / OK |
| Golden Age 入口、房間、存檔、內容、離開返回 | 44 tests / 70.712s / OK |
| Reverse Gear、章節 | 80 tests / 50.701s / OK |

全 Maze 執行後又加了小夜窗／時鐘等純美術細節，最後 17 項專項檢查及實際渲染已涵蓋這些改動。原先一次執行的 Arcade 大批次遭環境終止（exit 143），沒有把該次算成通過；上表是後續成功完成的拆批結果，並非宣稱執行過所有 Arcade 測試。

新增八項回歸測試覆蓋家具縮小、全部物件提示與 E 選取一致、遠近與模態提示、坐下緩動及恢復移動、按住按鍵、預覽重啟隔離、迷宮畫面副本／跳過、無牆面標題、開始新遠征清除暫時姿勢。既有碰撞、連通路徑、存檔遷移、秘密獎勵與正式／預覽畫面一致性測試也通過。

實際流程工具成功經過放炸彈、取得 Grey Pixel、正常入門、Miao 演出、四頁待辦、繞行家具、西門退出；新增工具再驗證沙發坐下起身、筆記提示、入口淡出淡入與文字框範圍。

## 實際畫面檢查

已開啟檢視 /tmp/studio-refinement 中實際渲染的全景、沙發提示、坐姿、筆記提示、迷宮干擾、房間淡入、Miao 與故事對話。坐姿原先偏靠椅背，已改到坐墊前緣並重拍；沙發僅允許正面入座。

重點圖片：26_final_overview.png、16_sofa_prompt.png、18_seated.png、20_notebook_prompt.png、23_maze_distortion.png、24_room_fade.png、06_story_dialogue.png。這是 SDL dummy 的正式渲染與圖片人工檢視；沒有宣稱桌面真人完整操作或音效聽感驗收。圖片為 /tmp 診斷輸出，不加入 Git。

## 直接測試

```bash
cd /home/nora/AOOP_Final
.venv/bin/python -m puzzle_maze --dev-preview developer-room
```

WASD／方向鍵走路、E 依底部提示互動；走到左下沙發前方按 E 坐下，再 E 起身。F7 重播 Miao 入場與回憶；F5 從 Grey Pixel 開始；F8 可選筆記；F9 待辦，左右鍵翻頁、Enter 關閉；Esc 退出。也可直接 --dev-preview miao-entrance 或 --dev-preview kevin-notes。

預覽 persistent=False，不讀寫真人檔案、不綁定 Lobby 帳戶，不發 Tokens／Tickets。已實際執行 developer-room 命令的 headless 截圖形式，正常視窗需可用的桌面顯示環境。

重現驗證：

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m puzzle_maze.review_studio_refinement --output /tmp/studio-refinement
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=.:puzzle_maze/tests .venv/bin/python -m unittest discover -s puzzle_maze/tests -p 'test_*.py' -q
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:.:puzzle_maze/tests .venv/bin/python -m unittest test_puzzle_maze test_maze45_secret test_economy test_rewards test_rooms test_miao_meow test_home_decor -q
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m unittest test_golden_age.EntryTests test_golden_age.RoomTests test_golden_age.SaveTests test_golden_age.ContentTests test_golden_age.LeaveAndReturnTests -q
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m unittest test_reverse_gear test_chapters -q
```

## 修改檔案與提交

主要程式：studio_layout.py、studio_furniture.py、developer_art.py、studio_view.py、studio_interactions.py、game.py、lab_scene.py、dev_preview.py。驗證：tests/test_studio_refinement.py、review_studio_refinement.py。文件：GREY_PIXEL_PREVIEW.md 與本報告。

- 0ebcb72 feat(maze): refine dim studio furniture prompts and usable sofa
- 9d4fca2 fix(maze): polish seated depth and verify forgotten studio transitions
- 文件以 docs(maze): record studio atmosphere interaction and visual verification 提交，ID 見 git log。

本次三個真實提交；保留先前歷史，未 Push、Merge 或重寫作者。桌面視窗操作與聲音聽感仍需人工確認；預覽坐姿刻意不跨存檔保存。
