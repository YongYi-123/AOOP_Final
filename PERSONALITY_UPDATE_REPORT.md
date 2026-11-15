# Personality、街道人物與 Grey Pixel 預覽驗收

## 交付狀態

分支：`feature/arcade-personality-preview`，從上一輪已保存的 `7647727` 建立。工作範圍是 Maze 與 Brawl，保留其他開發者功能與所有歷史。沒有 push、merge、reset、rebase、squash 或更改作者。

本次完成 18 筆真實提交（含本報告 docs 提交）；目前分支相對遠端整合基底 `fc32c29` 有 34 筆未推送提交，包含上一輪 16 筆。唯讀 `ls-remote` 查詢確認兩個新功能分支尚不存在遠端，整合分支仍是 fc32c29。保留設定 `nora950817 <nora.ee13@nycu.edu.tw>`；無法由 Git 設定證明 email 在 GitHub 已驗證。

## 秘密房比較與敘事取捨

實際閱讀並追蹤的正式路徑：

- `vending_ui.VendingScene` 的秘密啟動會登錄 `vending_secret`、降低音樂音量，稍後開 Legacy Terminal；Terminal 依原章節與秘密條件開 Trial 01。
- `golden_age_scene`／`golden_age_content` 是匿名學生房間、十二篇校園與深夜筆記、供電／電話／磁碟的探索；既有內容包括 NYCU、3 AM、貓踩鍵盤、朋友玩遊戲與管理員線索。
- `retro_racer.reverse_road` 真正用靜止時間與倒退距離觸發，分開處理過場、駕駛、獎勵、離場；獎勵由 `first_time` 與一次性事件記錄。
- Maze 原本以 Grey Pixel 胸箱與 r28 物件、`lab_memory_seen`／LORE 記錄串接既有主線服務。

本次不複製學生日記、管理員揭示或 Miao 失憶段落。r28 改以發行版本命名、冷冰箱網路封包、線材標籤、鍵盤收藏等生活化笑話補充 Kevin 的個性。照片與筆記仍用原 key，內容改成工作草圖、訪客的好椅子。Miao 新開場會笑談十二個鍵盤與鴨子，再注意留給訪客的小椅子，以「Let's leave the lamp on. Just for a little while.」收束，沒有再揭示角色身份或 THE LOST SIGNAL 的答案。

## Developer Room 視覺與互動

保留上一輪工程桌、兩個 CRT、平面顯示器、GPU／CPU／RAM／主機板、示波器、電表與焊台。新增桌腳與櫃體投影、牆地交界層次、低床／皺被、貓抱枕、迷你冰箱、鍵盤架、卡匣、飲料、麵杯、零食包裝、便條及遊戲海報。入口與 Miao 路徑維持開放。

七篇可選日記：

| 日記 | 新笑點 |
|---|---|
| DEV LOG 001 / FINAL FINAL | FINAL、FINAL_REAL 與標成 DO NOT USE 的真正發行磁碟 |
| DEV LOG 002 / NETWORKING | 冰箱封包全是冷的 |
| DEV LOG 003 / CABLE LABELS | 每條線兩端都寫 THIS END |
| DEV LOG 004 / PATCH NOTES | 修時鐘後星期二出現兩次 |
| DEV LOG 005 / QUALITY CHECK | 鴨子升任主管，要求更大池塘 |
| DEV LOG 006 / KEYBOARDS | 多出的十二個鍵盤是 emotional support |
| DEV LOG 007 / SAVE SPACE | 刪 4 MB 又買 4 MB，空間淨增零 |

另有鴨子、咖啡、紅按鈕三個互動。鍵盤讓 Miao 抱怨太吵；終端顯示 `BUILD FAILED: TOO MANY CATS.` 並短暫出現螢幕貓；紅按鈕只會讓螢幕泛紅，沒有破壞或額外獎勵。E 提示會指出 Log、GPU、Keyboard、Photo 等目標。閱讀改在下方固定區，避免遮住工程桌與角色。

這十個新增互動全部 `optional=True`，不影響主線出口。LORE 記錄沿用相同存檔欄位，舊快照透過既有可選物件補入機制相容。

## Grey Pixel 動畫與直接預覽

正式 `GreyPixelReveal` 約 5.8 秒：座標異常 → 像素成形 → Secret Item 03／03 → 系統確認 → 回遊戲。使用 dt、原創格線與細小粒子、既有 pulse／solve 音效，可跳過，不等待 blocking sleep。取得道具仍使用正式 chest 與 `observe_secret`，保留 `dungeon_grey_pixel`，不改 Golden Cat `claw_secret_reward`。

正式遊戲回 r24 後自行走入 r28；預覽把同一段動畫自動銜接到正式工程室／原版 Miao 入場，沒有另一套假場景。

直接啟動：

```bash
cd /home/nora/AOOP_Final
.venv/bin/python -m puzzle_maze --dev-preview grey-pixel
```

其他入口：`developer-room`、`miao-entrance`、`developer-diaries`。

R 重播所選入口、F5 全序列、F6 回房、F7 重播 Miao、F8 輪覽十個筆記／小彩蛋、E 互動、Enter 推進／關閉、Space 跳過動畫、Esc 退出。西門仍可用正式移動回 r24。

`PreviewGame` 固定 `persistent=False`，不綁 profile、不讀 Continue、不保存；沒有 Lobby session 或真實主線事件匯流排，因此預覽取得、閱讀與重播皆只在記憶體中。測試禁止 Session save／load、禁止視窗版 constructor 綁正式 profile，並比對測試存檔位元組與目錄保持不變。

完整操作與故障排除：[GREY_PIXEL_PREVIEW.md](puzzle_maze/GREY_PIXEL_PREVIEW.md)。正常流程攻略同步更新 [PLAYER_ROUTE_V45.md](puzzle_maze/PLAYER_ROUTE_V45.md)。

## Maze 色彩與史萊姆

僅重製版 `v45_` 材質加入稀疏、低對比的角落嵌紋與小花；圖書館增暖紅／琥珀，機械區增銅藍，地下區增紫藍。保留牆、路、互動物件辨識與舊版材質。

史萊姆使用獨立原生 16×16 快取素材：柔和亮眼、細小藍綠瞳孔、腮紅、小嘴、同步眨眼與一像素壓縮伸展；攻擊保留正式紅色預警，受傷換色，倒下扁化，移除舊共用臉部覆畫與 X 眼。測試涵蓋所有狀態、幀、受傷版本與像素連接性，沒有漂浮五官。

## Brawl 貓與市民

街貓重繪為橘虎斑、黑白、灰、三花、奶油五種；雙眼、細瞳、小鼻、嘴、內耳、花紋與尾巴都在同一原生 22×16 幀內。保留走、坐、理毛、觀察，新增眨眼及短跑，以最近鄰放大到 33×24。仍約每 22 秒出現、可在交戰時停留，不加入敵人清單或碰撞。

`StreetLife` 是輕量環境組件，Stage 1 每區六名市民，最多加一名警察：

- 攤販持續料理，遊客拍照，觀眾停步／退後指看，顧客從店面探頭。
- 購物客與路人遇密集近戰或累積驚慌會跑離、躲藏；安全後可返回。
- 第二／第四區有警察；其他區停留到合適時段也會偶爾出現。警察觀察或揮手疏導，旁邊有小型巡邏機車，不參戰。
- 所有人物只有環境狀態、位置與動畫，沒有 HP、hurtbox、傷害或波次完成介面。鏡頭以世界座標繪製、換關清除、暫停凍結，使用有限快取。

## 實際測試結果

| 測試 | 結果 |
|---|---|
| Maze 全套（最後重跑） | 240 tests / 42.273s / OK |
| Brawl 戰鬥、演進、環境、市民與街機整合 | 72 tests / 26.220s / OK |
| Arcade 房間、經濟、獎勵、其他遊戲、章節、秘密、音訊與原版 Miao | 546 tests / 201.502s / OK |
| 預覽專項（包含四次子程序實際 module 啟動） | 8 tests / 10.451s / OK |
| 日記版面與史萊姆專項 | 3 tests / 0.324s / OK |
| `git diff --check` | 通過 |

初次全套發現舊測試仍預期靜態 SCROLL；已依真正設計改成檢查 DISCOVERY、跳過、道具與 Orb 保留，而不是刪掉測試。預覽初始化也曾遇唯讀 phase 與阻住道具生成的位置，已以正式 state 及淨空生成位置修正，保留真實修復提交。

完整回歸包含 Maze 真正 API 全路線、存檔相容、Grey Pixel／Golden Cat 分離、Boss／寶庫／結算；Brawl 三角色通關、各階段 Boss、勝敗退出、扣幣退款與一次性獎勵。新測試另外檢查七篇日記與三個彩蛋的正式 E 互動、所有預覽模式／重播／跳過／對話／出口、窗體 constructor 隔離、三種解析度的閱讀文字、雙眼、NPC 觀戰／恐慌／警察／鏡頭／暫停／戰鬥隔離。

七名市民的 240 幀 400×300 原生繪圖樣本為平均 1.30 ms/frame；只代表本環境的繪圖樣本，沒有宣稱完整遊戲 FPS 或所有機器表現。

## 真實視覺檢視

已用影像檢視工具查看正式渲染幀：工程室全景／桌面／床與個人物品、日記視窗、Grey Pixel 揭示、Miao 步行／對話、工程室西門離場、史萊姆世界內閒置／攻擊、圖書館／地下房間、五種貓臉、正常街面／圍觀／逃離／警察與交戰街貓。

實際檢視修正：預覽閱讀的 Esc 提示與實際退出不一致、診斷捕捉時玩家遮住史萊姆、警察與路人位置重疊，以及預覽操作列在縮放／letterbox 對齊。沒有以單元測試代替圖片檢視。

截圖可重建到 `/tmp/maze-personality`、`/tmp/brawl-street-life`；不提交暫存圖片或玩家資料。

## 手動驗收與命令

```bash
cd /home/nora/AOOP_Final
.venv/bin/python -m puzzle_maze --dev-preview grey-pixel
.venv/bin/python arcade_lobby/main.py
```

預覽：先看完／跳過揭示，等待 Miao 從門口步行與停頓；Enter 閱讀、Space 跳過，F7 再播；F8 逐一讀笑話、F6 回探索，從西門出去，Esc 關閉。重新執行一般 Maze Continue，確認原進度未變。

正式 Maze：依攻略進 r24 收 Grey Pixel，r28 讀新日記；原本已完成入場的存檔不強制重播新對話，可用預覽 F7 查看。

Brawl：Stage 1 待約五秒看第一隻貓；在商店附近打鬥，留意遊客拍照、購物客跑走、攤販繼續料理。前進第二區或停留超過 25 秒觀察警察；暫停後應全部凍結。繼續原三關頭目及勝敗返回流程。

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=.:puzzle_maze/tests .venv/bin/python -m unittest discover -s puzzle_maze/tests -p 'test_*.py' -q
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m unittest neon_brawl.tests.test_combat neon_brawl.tests.test_evolution neon_brawl.tests.test_environment_expansion neon_brawl.tests.test_street_life test_neon_brawl -q
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:.:puzzle_maze/tests .venv/bin/python -m unittest test_rooms test_economy test_rewards test_cat_maze test_galaxy_defender test_pixel_volleyball test_racer_launch test_puzzle_maze test_maze45_secret test_chapters test_forgotten_games test_audio_manager test_miao_meow -q
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m puzzle_maze.review_personality
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m neon_brawl.review_life
```

## 已知限制

沒有真人桌面全程通關或實體音訊試聽；完成的是自動通關、正式流程操作、真實渲染幀與版面檢查。警察是環境敘事，不會戰鬥／逮捕。市民狀態與反應採可預測輕量規則；不是複雜群眾模擬。預覽會依序準備記憶體條件，不代表真人帳號取得了秘密，關閉後刻意不保存。正式已完成的入場不重播，保留原一次性故事規則。所有新增遊戲文字英文，開發文件繁體中文。

## 修改檔案

- `neon_brawl/ambient.py`
- `neon_brawl/art.py`
- `neon_brawl/civilians.py`
- `neon_brawl/model.py`
- `neon_brawl/review_life.py`
- `neon_brawl/tests/test_environment_expansion.py`
- `neon_brawl/tests/test_street_life.py`
- `puzzle_maze/GREY_PIXEL_PREVIEW.md`
- `puzzle_maze/PLAYER_ROUTE_V45.md`
- `puzzle_maze/dev_preview.py`
- `puzzle_maze/developer_art.py`
- `puzzle_maze/developer_diaries.py`
- `puzzle_maze/enemy_art.py`
- `puzzle_maze/environment.py`
- `puzzle_maze/game.py`
- `puzzle_maze/grey_pixel_scene.py`
- `puzzle_maze/lab_scene.py`
- `puzzle_maze/palettes45.py`
- `puzzle_maze/render.py`
- `puzzle_maze/review_personality.py`
- `puzzle_maze/secret45.py`
- `puzzle_maze/slime_art.py`
- `puzzle_maze/studio_personality.py`
- `puzzle_maze/tests/test_dev_preview.py`
- `puzzle_maze/tests/test_personality_art.py`
- `puzzle_maze/tests/test_v45_remaster.py`

另新增本報告 `PERSONALITY_UPDATE_REPORT.md`。

## 本次提交

- `a7f3d6c` feat(maze): layer the studio with cozy bedding snacks plush toys and keyboard clutter
- `8121995` feat(maze): add seven optional developer logs and harmless studio inspection gags
- `3ea51ad` feat(maze): replace repeated memory exposition with Miao personality and a quiet emotional beat
- `ddf3145` feat(maze): stage the Grey Pixel reveal and move studio reading into a clear subtitle strip
- `990c585` feat(maze): launch isolated production Grey Pixel and studio previews from the CLI
- `0e7b391` fix(maze): spawn preview items on clear tiles and verify save-free replay controls
- `8c4f34f` fix(maze): give slimes soft blinking eyes and consistent jelly expressions
- `9ea38ee` feat(maze): enrich remaster rooms with restrained mosaics flowers and color accents
- `29d0c8b` feat(brawl): redesign five street cats with paired eyes blinking and expressive motion
- `48325bf` feat(brawl): add independent vendors spectators fleeing shoppers and police street reactions
- `1061c6b` test(brawl): verify spectators panic police camera placement and combat isolation
- `39be23d` test(arcade): capture production personality scenes and verify the new item reveal flow
- `c0c21d6` feat(maze): focus studio lore on everyday humor and add direct note inspection controls
- `716ace4` test(maze): cover every preview command diary action and friendly slime animation
- `3219203` docs(maze): document safe Grey Pixel preview commands controls and updated studio route
- `3d7a66f` test(maze): verify real preview exit transitions and unobstructed slime captures
- `b23e9a0` fix(maze): align preview controls with resized and letterboxed game output

本報告另有一筆最後 docs 提交；其自身雜湊請見交付訊息或 `git log 7647727..HEAD`。未自行推送；你可以在確認後 `git push -u origin feature/arcade-personality-preview`，不要 squash，以保留全部開發紀錄。
