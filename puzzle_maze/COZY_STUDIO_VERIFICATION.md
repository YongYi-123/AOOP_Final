# Kevin's Cozy Studio：實作與驗證報告

## 正式路徑診斷

本次開始時工作樹乾淨，main 位於 af6d283；另建 feature/kevin-cozy-studio，保留原有合併歷史。未推送、未合併、未修改作者。

實際入口是 arcade_lobby/scenes.py 註冊的 puzzle_maze.lobby_scene.PuzzleMazeScene → Game(embedded=True, campaign="4.5") → RemasteredSession。r24 實際取得 Grey Pixel 後開啟 r28，Game.draw → Renderer.world。預覽亦走同一正式實作。

問題並非找到未使用的替代房間或舊 PNG 快取：舊素材是程式生成的 416×256 合成圖，放進較小原生視野被裁切，構圖擁擠，且之後仍繪製一般地城介面與裝飾；家具沒有碰撞，舊鏡頭效果移動了人物的顯示位置。無證據可判定使用者之前開啟的是哪個版本的程序，更新後請重開遊戲視窗。

現在 Renderer.world 對 r28 直接呼叫 studio_view.draw_studio 並返回，完全避開地城牆、地板、光照、指南針與 HUD。DeveloperRoomArt 提供原生 320×208 木地板底圖與獨立家具。實際素材來源是 developer_art.py、studio_furniture.py、studio_layout.py；不依賴外部圖片快取。Miao 使用 miao_adapter.py 取得原 Arcade Lobby 畫格，未修改 Lobby 角色。

## 新構圖、碰撞與敘事

上方主工程桌含 CRT、平面螢幕、鍵盤、滑鼠、暖燈、照片、鴨子及可見風扇的主機；左下橄欖色沙發、地毯、落地燈、書與咖啡；右下粉色修補貓床、摺毯、食水碗、貓抓柱與玩具；右上記憶終端、紙張與食物櫃。奶油牆、蜂蜜木材、柔粉與橄欖綠，保留中央步行區。

家具具桌面厚度、側面、支架與接地陰影。共用 footprint 定義阻擋玩家走路與衝刺，僅地面輪廓碰撞，人物與家具按腳底排序；實際不透明像素遮到玩家時才局部半透明。入口、西門出口與所有 20 個互動均可達。Miao 的連續腳本路徑避開全部家具。

Kevin 待辦清單四頁共七項，包含修 Arcade 音響、換 GPU 風扇、買 Miao 喜歡的罐頭、洗睡墊、吃正常晚餐、完成原型及雨停後帶毯子出門。新增罐頭手寫標籤、修補睡墊、安靜風扇提醒；照片與筆記呈現日常照顧，保留可選開發日記、冷咖啡與資深除錯鴨子的幽默。沒有新增身份或關係的大揭露。全部遊戲內容為英文。

首次入場 0–1.2 秒暖光揭示，1.2–5.4 秒由門口自然步行，停頓後焦點移向照片，7.6–9.2 秒顯示 Kevin 調低風扇、Miao 睡在墊子上的小回憶，9.8 秒後才可閱讀五句對話。保留眨眼、尾巴與抬頭反應，Enter 逐句、Space 安全跳過。重訪不強制重播；預覽 F7 可重播。

## 存檔與秘密保護

r28、dungeon_grey_pixel（Item 03）、claw_secret_reward（Item 02）保持原識別。舊 r28 存檔依 studio_revision 遷移家具位置與安全落點，保留物品、進度、旗標及攜帶 Iron Orb；首次覆寫前保留 .pre-studio-v2 原始備份。預覽 persistent=False 不載入、寫入或派發真人玩家故事與經濟事件。

## 測試結果

- 全 Puzzle Maze：249 tests，59.147 秒，OK。
- Arcade 整合、Grey Pixel、章節、Golden Age、Reverse Gear、經濟、獎勵、房間、Miao：526 tests，357.962 秒，OK。有既有 pygame.image.tostring 棄用警告，沒有失敗。
- 工作室專項：9 tests，1.426 秒，OK（已包含在全 Maze 數量內）。
- review_cozy_studio：實際放炸彈破牆、步行取得 Grey Pixel、進入 r28、逐句完成故事、四頁待辦、家具前後繞行與西門退出全部通過。
- kevin-notes 的下列 CLI 命令已成功執行，exit code 0。
- 正式取得／入室與預覽在相同狀態下的原生畫面逐像素一致；測試禁止誤呼叫一般地城圖塊與 HUD。

重現指令：

```bash
cd /home/nora/AOOP_Final
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=.:puzzle_maze/tests .venv/bin/python -m unittest discover -s puzzle_maze/tests -p 'test_*.py' -q
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:.:puzzle_maze/tests .venv/bin/python -m unittest test_puzzle_maze test_maze45_secret test_chapters test_golden_age test_reverse_gear test_economy test_rewards test_rooms test_miao_meow -q
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m puzzle_maze.review_cozy_studio --output /tmp/cozy-studio-review
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m puzzle_maze --dev-preview kevin-notes --headless --frames 1 --screenshot /tmp/kevin-todo-command.png
```

## 實際視覺檢查

已開啟並檢視實際渲染 PNG：全景、工程桌、生活角、Miao 角、門口步行、照片焦點、回憶、正式對話、待辦頁與家具背後遮擋。修正了回憶字幕原先覆蓋角色的問題，以及透明外框造成整件家具不必要變淡的問題。新畫面沒有石牆、地城 HUD 或小地圖。

截圖位於 /tmp/cozy-studio-review：07_studio_overview.png、08_engineering_desk.png、09_living_corner.png、10_miao_corner.png、02_miao_walk.png、04_photo_focus.png、05_memory_fragment.png、06_story_dialogue.png、todo_1.png 至 todo_4.png、11_desk_front.png、12_desk_behind.png、13_sofa_front.png、15_safe_exit.png。這是 SDL dummy 真實渲染與人工檢視，不是桌面視窗的真人操作驗收；音效聽感仍待有音訊裝置的人工測試。截圖是暫存輸出，不納入 Git。

## 手動預覽

```bash
cd /home/nora/AOOP_Final
.venv/bin/python -m puzzle_maze --dev-preview developer-room
```

F7 重播完整 Miao 演出；F9 開待辦，方向鍵翻頁；F8 輪流檢視可選互動；WASD／方向鍵繞桌、沙發、櫃子確認碰撞；E 檢視；Enter 關閉閱讀／推進對話；F5 重來 Grey Pixel；Esc 退出預覽。也可直接選 miao-entrance、kevin-notes、grey-pixel。正式西門 (1,7) 可安全回 r24。

## Git 紀錄

- 287ea13 feat(maze): rebuild the production Grey Pixel studio with warm furniture depth collision and safe saves
- f26f419 feat(maze): stage Miao warm-memory cinematic and direct Kevin note previews
- 802e3f1 fix(maze): refine furniture occlusion and verify the production studio walkthrough
- 本報告與預覽／攻略更新另以 docs(maze): document the verified cozy studio runtime and preview controls 提交，最終 ID 見 git log。

遠端檢查 main 仍 af6d283，尚無 feature/kevin-cozy-studio。完成文件提交後本次共四個未推送提交。作者設定沿用 nora950817 / nora.ee13@nycu.edu.tw，沒有改寫既有作者或歷史。未推送／合併。

## 修改檔案

- `puzzle_maze/.gitignore`
- `puzzle_maze/PLAYER_ROUTE_V45.md`
- `puzzle_maze/GREY_PIXEL_PREVIEW.md`
- `puzzle_maze/dev_preview.py`
- `puzzle_maze/developer_art.py`
- `puzzle_maze/developer_diaries.py`
- `puzzle_maze/game.py`
- `puzzle_maze/lab_scene.py`
- `puzzle_maze/miao_adapter.py`
- `puzzle_maze/puzzles.py`
- `puzzle_maze/remaster.py`
- `puzzle_maze/render.py`
- `puzzle_maze/review_cozy_studio.py`
- `puzzle_maze/review_lab.py`
- `puzzle_maze/review_personality.py`
- `puzzle_maze/secret45.py`
- `puzzle_maze/studio_furniture.py`
- `puzzle_maze/studio_layout.py`
- `puzzle_maze/studio_notes.py`
- `puzzle_maze/studio_view.py`
- `puzzle_maze/tests/test_cozy_studio.py`
- `puzzle_maze/tests/test_dev_preview.py`
- `puzzle_maze/tests/test_v45_remaster.py`
- `puzzle_maze/tests/test_visual_story.py`
- `puzzle_maze/COZY_STUDIO_VERIFICATION.md`
