# Puzzle Maze 2.0 — The Prism Chambers

在既有 TileMap、RoomManager 與 PuzzleManager 上升級的獨立地下城遊戲。
八個主要房間各 56×34 格（896×544 像素世界），另保留一間可選秘密房。
本次只修改 puzzle_maze/；沒有新增劇情、NPC 或擴充其他遊戲及 Lobby。

## 啟動

在 AOOP_Final 根目錄：

```bash
.venv/bin/python -m puzzle_maze
```

其他 Python 環境：

```bash
python3 -m pip install -r puzzle_maze/requirements.txt
python3 -m puzzle_maze
```

使用 pygame-ce，請勿同時安裝原版 pygame。預設 960×720，可調整視窗大小。
像素場景採 nearest 整數倍率；英文及繁中文本在最終解析度繪製。
內附 Noto Sans CJK TC 及 SIL OFL 授權於 assets/fonts/，不需系統中文字型。

## 操作

| 按鍵 | 功能 |
| --- | --- |
| WASD / 方向鍵 | 移動；取得手套後可推動重箱 |
| E | 開寶箱、開關、解鎖相鄰門；取得鏡後可旋轉鏡台 |
| Space | 使用目前工具：脈衝開裂牆、轉鏡、磁力排斥 |
| Q | 在脈衝與已取得的鏡、磁力工具間切換 |
| F | 磁力吸引面朝方向的金屬箱（需先取得磁力裝置） |
| Shift | 三格衝刺，逐格檢查碰撞；1.2 秒冷卻，短暫閃避無敵 |
| J | 面朝方向近戰；0.25 秒攻擊間隔 |
| H | 消耗一瓶藥水，恢復最多 3 HP |
| Tab | 完整迷宮關係圖、當房探索迷霧與已發現標記 |
| R | 還原當房入口檢查點的物件、生命、敵人及補給 |
| Esc | 暫停；選單使用上下鍵 / Enter |
| M | 背景音樂開關 |

HUD 顯示五顆愛心、藥水、目前工具、衝刺冷卻及晶片。G / B / L / M 分別
代表手套、靴子、鏡與磁力裝置；取得後變青色。脈衝是原有能力，起始可用。

R 會撤回本房新取得的工具、鑰匙、掉落及寶箱，避免重複領取；前房取得的
工具保留。重訪房間以重訪時狀態建立檢查點。探索迷霧不因 R 退回。
重置會還原該檢查點的敵人；一般切房或讀檔不會讓已死敵人重新生成。

## 房間與成長

每房保留原核心謎題，結合東翼封印、岔路、回頭路與裂牆寶庫。
八房主要出口都檢查具名完成條件，且實體牆與門阻擋繞路。

| 房間 | 複合目標 |
| --- | --- |
| Lantern Courtyard | 開關 → 東翼鑰匙鎖；先在南側寶箱取得手套 |
| Weight of Stone | 踩板開入口 → 用手套推重箱壓東翼板 |
| Twin Foundations | 雙箱雙板 → 東翼鑰匙封印；探索水景取得衝刺靴 |
| Amber Lock | 琥珀鑰匙門 → 訊號開關與 0.65 秒封印，需衝刺通過 |
| Signal Garden | 南北訊號 → 光源；找鏡、轉向北方接收器，再推重物啟動封印 |
| Whispering Wall | 脈衝通道 → 磁力遠端重物；取得磁力裝置，另找秘密房入口 |
| A Fleeting Bridge | 限時入口 → 光束反射與磁力壓板組合 |
| The Prism Vault | 雙箱、鑰匙 / 脈衝 / 計時、鏡 / 磁力，再擊敗南側三守衛 |
| Hidden Moss Archive | 可選秘密房；兩座訊號解封印，西側出口返回第六房 |

普通門條件滿足後鎖定開啟；限時門在倒數結束時關閉。玩家、箱子或活敵人
在門格時延後關閉。通過限時門的紀錄可供下一階段機關使用，不把原門永久
打開。裂牆有青苔箭頭與金色裂紋。各房可選寶庫提供兩瓶藥水。

光源、鏡台與接收器沿格子追蹤光線，牆及重物阻擋光束。
金屬遠端槽位隔水可見，面向槽位使用三次排斥把金屬箱放到壓力板；
磁力最多作用六格，不能穿牆或把重物移到障礙與玩家身上。

## 戰鬥與死亡

- Slime：2 HP，慢速追蹤與短前搖。
- Bat：1 HP，快移動、週期間歇衝刺。
- Guardian：4 HP，較慢，攻擊前有紅框及 0.7 秒前搖。

受傷後 1.1 秒無敵，玩家閃爍並在合法地格內擊退。敵人尋路不穿牆、水、
閉門或箱子。死亡後短動畫，掉一顆生命 / 晶片，拾取後消失，不重複生成。
前期一隻慢敵，中期加入 Bat，後期三種類混合；終房戰鬥為必要條件。
HP 歸零停止移動與能力，顯示 GAME OVER，Enter / Esc 回 Puzzle Maze 主選單。
不會關閉整個程式。死亡存檔 Continue 仍顯示 GAME OVER，可選新遊戲再開始。

## 小地圖與存檔

右上小地圖直接讀 RoomManager 與 JSON 的 atlas / exits，顯示房間連接。
金色為當房，青色為完成，已訪房正常色、未訪灰色；秘密房發現前完全隱藏。
Tab 顯示同一張關係圖及當房逐格迷霧，門、出口、寶箱、接收器在看見後標記。
視線被牆及閉門阻擋。地圖、暫停及離開房間時，該房的倒數和敵人停止更新。

只使用 puzzle_maze/save_v2.json，已在資料夾自己的 .gitignore 排除；
原版 save.json 保留，2.0 不覆寫或自動轉換它。舊版地圖快照與新版房間不相容，
2.0 請從 New expedition 開始。存檔包含工具、鑰匙、生命、敵人、補給、
房間機關、入口檢查點與探索。每 15 秒、切房、暫停、死亡及退出時原子保存。
損毀或不相容存檔會安全開新遊戲，寫入失敗保留記憶體中的進度。

本次以獨立模式驗證。先前的可選 lobby_scene.py 保留，本次未擴充其輸入介面。

## OOP 架構

- Game / GameScene：事件與場景 State，含 MENU、PLAY、PAUSE、MAP、GAMEOVER。
- Player / TileMap / CollisionManager / Camera：座標、生命與碰撞，沿用原核心。
- RoomManager：JSON 房間、起點、出口與合法性。
- PuzzleManager 組合 Inventory / PuzzleState；FACTORY 建立 PuzzleObject 子類。
- PushableBox、PressurePlate、Switch、Door、Key、SecretPassage、TimedSwitch：原機關。
- Chest、LightSource、Reflector、Receiver、CombatSeal：工具成長、光束與戰鬥條件。
- CombatManager 組合 Enemy；Slime / Bat / Guardian 以繼承設定行為，EnemyState
  控制 HUNT / WINDUP / DYING / DEAD。
- GameSession：機關、戰鬥、工具、探索與檢查點的組合及存檔。
- Exploration / DungeonAtlas：視線迷霧與資料驅動的地圖，沒有另一份手動房間圖。
- Renderer / NativeText / AudioManager：像素場景、最終解析度文字、原創音樂音效。
- solver.py：推箱 BFS 合併可達區域，依階段求解、排除靜態角落死局。

## 驗證

```bash
.venv/bin/python -m unittest discover -s puzzle_maze/tests -v
.venv/bin/python -m puzzle_maze --headless --frames 60
.venv/bin/python -m puzzle_maze --headless --screenshot /tmp/puzzle-maze-v2.png
```

原版 fixtures 保留引擎回歸；生產地圖另以真實移動、求解器推箱重播、
光束、磁力、限時衝刺及戰鬥完成八房。測試也包含秘密房往返、步行超時 / 衝刺
成功、未取得工具限制、敵人 AI / 前搖 / 無敵 / 掉落 / 死亡存檔、探索保存、
損毀資料、出口防繞過、音訊失敗、中英字形與五種視窗尺寸。

仍需真人驗證：長時間鍵盤手感、解謎提示是否足夠、戰鬥難度與音量，以及
實際螢幕上的字體大小與視窗調整體驗。模擬通關只證明合法路線存在。
