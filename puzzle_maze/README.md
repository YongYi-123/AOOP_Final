# Puzzle Maze — The Prism Chambers

獨立 Python + Pygame 俯視解謎遊戲。原創像素繪圖與合成音樂，核心不依賴
Arcade Lobby、Tokens、Tickets、共同存檔或其他遊戲模組；`lobby_scene.py` 是可選機台介面。

## 啟動

從 AOOP_Final 根目錄：

```bash
.venv/bin/python -m puzzle_maze
```

其他環境先安裝 `python3 -m pip install -r puzzle_maze/requirements.txt`，再執行
`python3 -m puzzle_maze`。請使用 pygame-ce，勿同時安裝另一個 pygame 套件。

## Arcade Lobby 試玩

```bash
.venv/bin/python arcade_lobby/main.py
```

到 Arcade Floor，使用中央機台列的 **PUZZLE MAZE**（`island_1`），按 E 開啟
機台並選 PLAY。此機台免費，不給 Tickets 或分數獎勵；Lobby 的遊玩紀錄仍按
既有流程記錄。選 New expedition 開始，或 Continue expedition 延續獨立遊戲存檔。

主選單按 Esc 回大廳；遊戲中按 Esc 暫停，選 **Return to arcade** 回大廳。
單人沿用下列操作；雙人模式使用啟動機台者的 Lobby 移動、互動及道具鍵。
Tab 與 R 為查看地圖與重置，音樂及音量使用 Lobby 的設定。
內嵌模式沿用 Lobby 的視窗、背景音樂及音效混音，獨立模式保持原創合成音樂。

## 操作

| 按鍵 | 功能 |
| --- | --- |
| WASD / 方向鍵 | 四方向移動，接觸箱子時推動 |
| E | 操作相鄰開關、以對應鑰匙解鎖門；優先面朝物件 |
| Space | 脈衝能力，打開有裂紋與青苔箭頭的秘密牆 |
| Tab | 已探索房間地圖，開啟時暫停機關時間 |
| Esc | 暫停；選單使用上下鍵及 Enter |
| R | 恢復目前房間進入時的物件、位置與鑰匙檢查點 |
| M | 切換背景音樂 |

沿東側入口探索八個主要房間；西側傳送點可以返回。第六房另有隱藏入口，
通往可選的 Moss Archive。抵達第八房東側出口即通關。

普通門的全部條件成立後會保持開啟；限時門只在時鐘有效時開啟。
門格有玩家或箱子時延後關閉，離開後才關閉。未解鎖的門不會消耗錯誤鑰匙。
箱子可推入死角，R 可撤回到入口檢查點。重訪已完成房間會保留其狀態。

## 房間

| 房間 | 目標 |
| --- | --- |
| Lantern Courtyard | 操作黃銅開關並通過東側迷宮 |
| Weight of Stone | 踩住單一壓力板，鎖定門的開啟狀態 |
| Twin Foundations | 將兩個木箱推到兩塊壓力板 |
| Amber Lock | 找到琥珀鑰匙，解鎖門 |
| Signal Garden | 啟動南北兩個開關 |
| Whispering Wall | 從裂紋與青苔箭頭推理出脈衝通道 |
| A Fleeting Bridge | 啟動時鐘，於 4.5 秒內通過門 |
| The Prism Vault | 雙箱、鑰匙、秘密牆、開關與限時門的綜合謎題 |
| Hidden Moss Archive | 第六房的可選隱藏房間，點亮兩座機關取得額外印記 |

## 存檔

只寫入 `puzzle_maze/save.json`，已由資料夾自己的 `.gitignore` 排除。
每 15 秒、房間切換、暫停及退出時自動存檔。原子替換避免半寫入；
缺少、損毀或不相容存檔會開啟新遊戲，存檔寫入失敗不會終止遊戲。
倒數在離開房間、暫停及地圖時停止。選 New expedition 建立新進度，
下一次自動存檔會取代本遊戲舊存檔。

## 架構

- `Game` / `GameScene`：事件迴圈、選單及場景 State。
- `Player`、`TileMap`、`CollisionManager`、`Camera`：獨立於 Pygame 的座標與碰撞。
- `RoomManager`：讀取 JSON、驗證地圖、房間出口。
- `PuzzleManager`：組合 Inventory 與 PuzzleObject；物件 Factory 依 type 建立實例。
- `PuzzleObject` → `PushableBox`、`PressurePlate`、`Switch`、`Door`、`Key`、
  `SecretPassage`、`TimedSwitch`：繼承與多型互動。門每次更新觀察具名條件。
- `PuzzleState` / `Inventory`：物件狀態與分類鑰匙計數。
- `GameSession`：房間快照、入口檢查點、完成紀錄、存檔。
- `Renderer` / `AudioManager`：原創程式化像素素材、四方向動畫、粒子、Camera、
  水面動畫、復古音樂與音效。音訊裝置失敗時靜音運作。
- `solver.py`：推箱狀態 BFS，以玩家可達區域合併重複狀態，排除靜態角落死局。

地圖位於 `maps/dungeon.json`。`#` 牆、`.` 地板、`g` 草地、`~` 水、`O` 石塊。
新增物件類型需註冊 `FACTORY` 並更新合法性檢查及 Renderer。
門的 `requires` 為 AND；`key` 另外要求對應鑰匙。出口附目標房與到達座標。

## 驗證

```bash
.venv/bin/python -m unittest discover -s puzzle_maze/tests -v
.venv/bin/python -m puzzle_maze --headless --frames 60
.venv/bin/python -m puzzle_maze --headless --screenshot /tmp/puzzle-maze.png
```

測試包括移動、碰撞、Camera、推箱、壓力板、多開關、鑰匙、秘密牆、倒數、
門格佔用、房間切換、重置、存檔容錯、音訊失敗、選單與所有房間渲染。
推箱關卡透過狀態搜尋產生解答，並使用真正的遊戲移動重播；通關測試以
每步 0.13 秒的遊戲時間走完八房，另測試秘密房進出。

仍需真人驗證：實際鍵盤手感、四方向動畫、全程解謎難度、真實音訊裝置音量，
以及不同桌面大小下的視覺可讀性。Headless 測試不能替代這些檢查。
