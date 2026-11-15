# NEON BRAWL 研究設施與貓咪重建驗收

## 1. 完成範圍與 Git 安全

分支：`feature/brawl-research-complex`，從上一輪 `39a0077` 的乾淨工作目錄建立。僅修改 NEON BRAWL，保留 Puzzle Maze、其他街機與既有歷史。沒有 reset、rebase、squash、push 或 merge，沒有更改作者。採用新的每 3–5 分鐘目標，以完整可驗證功能作提交邊界，不為時間拆出不完整功能。

本次 8 筆提交（含最後報告 docs）；相對遠端整合基底 fc32c29，分支累積 42 筆未推送提交，含前兩輪 34 筆。唯讀 ls-remote 確認本功能分支及前兩個新功能分支均尚不存在遠端，整合基底仍為 fc32c29。

## 2. Stage 1 — MACHINE LEARNING LAB

夜市不再是正式場景，改成同一研究設施的 ML 部門。四區為 DATA COLLECTION、MODEL TRAINING、NEURAL NETWORK RESEARCH、FAILED EXPERIMENTS。

- 青綠／米金建材、工程桌、CRT、攝影採樣設備、資料帶、電路板、破損機櫃與貓抱枕。
- 可辨識的散點分類與決策界線、下降 training loss 與反向上升 validation loss、多層神經網路、混淆矩陣／一律分類成 CAT 的結果。
- 畫面使用 TRAINING DATA、VALIDATION SET、FEATURE EXTRACTION、GRADIENT DESCENT、NEURAL NETWORK、CLASSIFICATION、REGRESSION、LOSS FUNCTION、EPOCH、ACCURACY、ANOMALY DETECTED 等英文。
- `EPOCH 9999 / 10000`、`ACCURACY: 99.9%`、`REAL-WORLD ACCURACY: 12%`、`OVERFITTING. AGAIN.` 等笑話實際出現在設備上。
- 共用設施有水管接頭、滴水、線路破損、受損設備、蒸氣、閃爍監視器與小火花；地板改為有維修蓋板的設備走道。所有新裝飾不造成傷害。

## 3. Stage 2 — COMPUTER ARCHITECTURE LAB

四區改為 INSTRUCTION FETCH / DECODE、DATAPATH WORKSHOP、CACHE AND MEMORY、PIPELINE CONTROL，使用銅藍配色、硬體工作檯、插槽、RAM、CPU 板、示波器、焊台與機殼。

六種原創快取圖解：

1. MIPS 五階段 IF → ID → EX → MEM → WB，配完整 FETCH／DECODE／EXECUTE／MEMORY ACCESS／WRITE BACK 說明。
2. PC、registers、ALU、RAM、control unit 與回寫通路。
3. Register file 的讀出 A／B 與寫入。
4. CPU → L1 → L2 → RAM 的記憶體階層。
5. ALU 雙輸入、操作選擇與 ZERO 訊號。
6. NAND、XOR 形狀、輸入線與反相泡泡。

圖解是低解析度示意，不是完整可執行 MIPS datapath。文字放在掛牆圖與狀態看板，不覆蓋戰鬥區。

## 4. 背景工程師

`LabStaff` 與 `Engineer` 是獨立環境資料，沒有 Fighter、HP、hurtbox、傷害或波次介面。架構部門有四個工作位置，其他部門有兩個研究員位置；視差與工作檯使用相同 0.55 倍鏡頭偏移。

- Programmer：三螢幕打字、看錯誤、喝咖啡、打瞌睡、醒來。
- Electronics：焊接、查看元件、調整設備、被小火花嚇一下。
- Debugger：指著圖、抓頭、困惑、喝咖啡。
- Student：打字、抱咖啡、趴桌、醒來，再繼續。

狀態看板實際顯示 SEGMENTATION FAULT、TIMING VIOLATION、WHY DOES THIS WORK?、ONE MORE SIMULATION。人物、手、杯子、桌腳及螢幕支架均在同一原生素材中；暫停凍結工作循環。原夜市市民不再用於正式場景，避免設施中出現不相干攤販。

## 5. Stage 3 — AOOP DEVELOPMENT CORE

四個戰鬥區為 CLASS GALLERY、INHERITANCE TREE、COMPONENT WORKSHOP、ARCADE RUNTIME。最終頭目第二階段起切換第五種外觀 CENTRAL SOFTWARE CONTROL，仍是原本第四場戰鬥，沒有新增流程或改 Boss。

- 紫／青建材、機櫃、街機機械、元件托盤與小機器人。
- CLASS／OBJECT、CONSTRUCTOR → INSTANCE、INHERITANCE、POLYMORPHISM、COMPOSITION、ENCAPSULATION／PRIVATE、INTERFACE、METHOD、ABSTRACTION、ATTRIBUTE 等可讀英文。
- UML 風格繼承空心三角、組合實心菱形、介面虛線、Game → Scene／Object 圖解。小封包沿連線移動，表現 method dispatch。
- 飄浮的是有小臉的抽象像素物件，不是敵人。街機內有原創小機器人／數位貓，並有 BUILD FAILED、TRY SNACKS、NULL IS NOT A GAME PLAN 等軟體笑話。
- 最終中央大螢幕已按真正視差與頭目鏡頭位置重新置中；資料通道隨 Boss 三階段改色。提示加深色底襯，保持危險預警優先。

## 6. 新貓咪：從輪廓重建

實際閱讀 Lobby `cat_sprites.draw_cat`／`cat_sheet` 與 Miao 的眼睛／步行流程，參考其短腿、寬頭、連接的尾巴與表情。沒有直接複製 Lobby 圖，也沒有以舊 Brawl 貓重新著色；舊 inline 繪圖已移除，改由 `lab_cats.py` 提供新素材。

原生 26×22 畫布、明確輪廓、大而清楚的雙眼、細小瞳孔與高光、鼻子、奶油色嘴邊、小耳內色、短腿與連接身體的尾巴。正式畫面直接使用原生尺寸，再由主畫面整數放大，移除之前貓自身 1.5 倍的非整數縮放。

| 貓 | 花紋與個性 |
|---|---|
| MARMALADE | 橘虎斑、前額／背部條紋、好奇觀望 |
| SOCKS | 深色燕尾服、白胸／白襪／臉部白紋，坐姿拘謹 |
| MISO | 灰虎斑、不同尾紋與背紋、偏藍瞳，喜歡伸展／觀察 |
| PATCH | 三花背部兩塊色斑、不對稱耳／臉，常理毛 |
| CUSTARD | 奶油色、柔亮嘴邊與尾色、淡紫瞳，喜歡打瞌睡 |

走路、坐下、觀望、同步眨眼、理毛、睡覺、伸展、短跑都有正式幀；跑動有較快節奏和較寬步幅，沒有拉長腿。完整測試檢查 280 組幀的連接輪廓，並逐一驗證左右鏡像（共 560 張圖）。

## 7. 三關貓咪整合

保留已有可靠的生成／暫停隔離邏輯：每關都可出現，第一關約第 5 秒，換部門後約 4 秒，之後約每 22 秒一隻，停留約 16 秒，最多一隻。交戰不會強迫牠消失。

在鏡頭內生成，並維持走道可見範圍。花紋依次輪替，坐／觀望／理毛／睡覺依個性變化，硬體部門會伸展；軟體部門的實體貓會看螢幕與光點。沒有血量、受擊、碰撞或 AI 目標介面，不影響 Boss、波次、票券或玩家傷害。

## 8. 保留的正式玩法

ROSTER 參數、攻擊資料、AI、敵群組成、Boss patterns、三階段戰鬥、復原道具、場地邊界與結算服務保持不變。只改場景名稱、背景與相應開場／結尾文字。既有地面危險區仍有效，提示改為 LIVE CIRCUIT，不與純裝飾小火花混淆。

## 9. 測試：實際結果

| 指令範圍 | 結果 |
|---|---|
| Brawl 全套＋正式街機整合（最後重跑） | 82 tests / 7.194s / OK |
| Arcade 房間、經濟、獎勵、音訊設定與生命週期 | 277 tests / 94.831s / OK |
| 新研究設施＋環境專項（百分號修正後） | 20 tests / 0.147s / OK |
| `git diff --check` | 通過 |

全套包含三角色普通輸入確定性通關、全部 Boss／階段／勝敗／暫停／退出、機台註冊、扣幣、未啟動退款、已遊玩退出政策、一次性領獎與存檔相容。新測試另檢查十三張背景互異、正式 Stage 1 不再呼叫舊 market painter、圖解真實字型邊界、百分號不改共用字型、全部貓姿勢／花紋與全關卡生成、工作循環、鏡頭、暫停、渲染不改戰鬥。

未修改測試掩蓋失敗：舊「地鐵與核心不可有貓」測試依新需求改為三關生成／換關後重新出現；四張硬體圖測試擴為六張；舊正式市民暫停檢查改為目前使用的 staff。既有獨立 StreetLife 相容性測試保留。

## 10. 真實視覺檢視與修正

已使用圖片檢視工具看過：三關十二區合成、額外最終競技場、ML 失敗實驗、架構實驗室全畫面、技術圖解近景、工程師所有工作姿勢、五種貓完整姿勢／步行眨眼、改版開場字幕。

實際截圖發現並修正：

- CRT 遮住 MIPS 最後一行，調整圖板高度。
- 最終大螢幕因視差偏離 Boss 鏡頭，改成跨 800px 背景拼接的置中地標。
- 工程師螢幕支架沒有接到桌面，延伸支架並補桌腳。
- 灰貓尾紋使用固定座標，改跟隨尾巴姿勢。
- 介面虛線與 CPU 控制訊號補到實際節點。
- 背景標題與 Boss 警告重疊，增加局部深色底襯。
- Lobby 字型不含 `%`，在本功能局部補字，實際重看確認 12%／99.9% 可見；未更動 Lobby 的字型物件。

截圖由正式 Campaign／Renderer 產生，預設在 `/tmp/brawl-research-review`；人物／Boss 階段在診斷中刻意安排以便查看，不宣稱這些截圖是人類實戰紀錄。圖層與渲染保持有界快取。核心畫面 240 幀原生繪圖樣本平均 0.23 ms/frame；跨十二區完整 BrawlGame 繪圖樣本 2.09 ms/frame（240 幀）。這些不是完整遊戲 FPS 或所有硬體的效能保證。

## 11. 手動測試

先關閉仍在跑的舊版遊戲視窗，再啟動，讓 Python 重新載入新程式與快取：

```bash
cd /home/nora/AOOP_Final
.venv/bin/python arcade_lobby/main.py
```

選玩家，從 HOME 向左進 Arcade Floor，到左島 NEON BRAWL 機台按 E，確認一代幣。選角色後照原控制遊玩。Stage 1 應直接是研究桌／訓練螢幕，不應有店面或攤販。待約五秒看貓，之後每二十餘秒觀察不同花紋與睡覺／伸展。

Stage 2 觀察 MIPS、cache、ALU 等圖與桌前研究員；讓畫面停留十餘秒可看完整工作循環。Stage 3 檢查繼承／組合／介面、街機與浮動像素，最終 Boss 第二階段應出現中央軟體控制大螢幕，原攻擊規則不變。確認暫停會凍結貓與工作循環，勝敗與退出回 Lobby 仍只結算一次。

原控制：WASD／方向鍵移動、J 輕擊、K 重擊、L 跳、U 特殊、I 閃避、E 拾取、Enter 確認、Esc 暫停。

## 12. 重現測試與畫面

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m unittest neon_brawl.tests.test_combat neon_brawl.tests.test_evolution neon_brawl.tests.test_environment_expansion neon_brawl.tests.test_street_life neon_brawl.tests.test_research_complex test_neon_brawl -q
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m unittest test_rooms test_economy test_rewards test_audio_manager test_audio_lifecycle test_audio_settings -q
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m neon_brawl.review_research
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m neon_brawl.review --output /tmp/brawl-research-legacy-review
```

## 13. 已知限制

沒有真人桌面完整通關或實體音訊試聽；完成的是自動普通操作通關、正式整合測試與實際渲染幀檢視。技術圖解為刻意簡化的像素示意，背景牌子捲到畫面邊緣時會正常裁切。工程師是定時環境動畫，不是完整人群 AI。舊 market／metro／facility 模組僅留作相容，未註冊到正式環境；舊貓繪圖已替換。音樂仍用既有原創曲目與設定，沒有新增下載或付費資產。所有新遊戲文字為英文。

## 14. 修改檔案

- `neon_brawl/README.md`
- `neon_brawl/ambient.py`
- `neon_brawl/architecture_lab.py`
- `neon_brawl/art.py`
- `neon_brawl/cinematic.py`
- `neon_brawl/data.py`
- `neon_brawl/game.py`
- `neon_brawl/hardware_posters.py`
- `neon_brawl/lab_cats.py`
- `neon_brawl/lab_staff.py`
- `neon_brawl/ml_lab.py`
- `neon_brawl/model.py`
- `neon_brawl/oop_core.py`
- `neon_brawl/research_art.py`
- `neon_brawl/review.py`
- `neon_brawl/review_life.py`
- `neon_brawl/review_research.py`
- `neon_brawl/scenery.py`
- `neon_brawl/tests/test_environment_expansion.py`
- `neon_brawl/tests/test_research_complex.py`
- `neon_brawl/tests/test_street_life.py`

另新增本報告 `neon_brawl/RESEARCH_COMPLEX_VERIFICATION.md`。沒有修改 Puzzle Maze 或 Arcade Lobby 原始碼。

## 15. 本次完整提交紀錄

- `6b8ecf2` feat(brawl): replace the night market with a damaged machine-learning research lab
- `9a33196` feat(brawl): build architecture workbenches six schematics and animated background engineers
- `f74107b` feat(brawl): turn the final core into a playful AOOP runtime and arcade laboratory
- `3ef7bd7` feat(brawl): rebuild compact expressive lab cats and populate every department
- `6ea6e32` fix(brawl): refine laboratory composition diagrams monitor supports and research story presentation
- `b8dc844` test(brawl): verify research diagrams cat animation continuity and ambient isolation
- `9fa178c` fix(brawl): render accuracy percentages without changing the shared Lobby font

本報告本身另有最後一筆 docs 提交；其自身雜湊見交付訊息或 `git log 39a0077..HEAD`。你可自行確認後 `git push -u origin feature/brawl-research-complex`，保留全部獨立提交，不 squash。本次沒有執行 Push 或 Merge。
