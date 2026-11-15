# Puzzle Maze v4.5 完整攻略

此攻略對應目前實作的 28 房戰役，正常樓層只有 **1F／B1F**。皇家寶庫是 B1F 結局區，Developer Room 是 1F 秘密房；沒有第三層。舊房號保留，方便舊存檔與地圖辨識。

## 開始與控制

在儲存庫根目錄執行 `.venv/bin/python arcade_lobby/main.py`，到 Arcade Floor 的 Puzzle Maze 免費試玩機台。獨立執行可用 `.venv/bin/python -m puzzle_maze --campaign 4.5`。

WASD／方向鍵移動；J 揮劍；E 調查、開箱、提起／放下物件；Q 切換工具；SPACE 使用工具／推開金屬；F 吸引金屬；SHIFT 衝刺；B 炸彈；P 魔法粉；G 投擲；T 召回 Iron Orb；H 藥水；TAB 地圖；N 漸進提示；R 回本房檢查點；Esc 暫停。先取得 Map，地圖才顯示一般房間輪廓；Compass 另標示寶物／Boss。秘密房須先發現。

座標一律是地圖格 `(x,y)`，左上為 `(0,0)`，不是螢幕像素。走到物件旁面向它按 E；同一位置通常也能調查。戰鬥盡量繞到側面或背面，揮擊後移位，補給可再取，不必猜密碼。

## 主線概要

1. **r1 Stone Vestibule／1F**：E 取 Map、操作 Lever，北上 r2。
2. **r4 Weight and Light／1F**：先取 Gloves，回 r2；拿到第 4 步的 Mirror 後才回來解反射光路。
3. **r19 Torch Shrine／1F**：取 Magic Powder。依 **Dawn → Noon → Dusk** 面向火盆按 P；擊敗受火焰影響的幽靈，啟動 Flame Signal。Hidden Fire 與 Disc 是選拿物。
4. **r2 → r19 → r5 Ancient Library**：切晶體為 BLUE 後進圖書館。用 Lever、取 Mirror；推箱壓 Plate，啟動 East，取 Compass（附一把 Small Key）。
5. **r4 → r20 Pot Storage**：先由 `(6,10)` 北推 Box 到 Plate `(6,8)`，轉 Prism，啟動 West，再下到 r20。提壺、G 投擲擊敗獵手；拿另一壺站上三點重壓板 `(13,8)`，開通路。箱子可稍後取。E 帶上 Iron Orb；由 `(13,10)` 朝東 G 投出 Iron Orb，打碎 Tower Pillar `(15,10)`，重新 E 拾回 Orb，經 r7 前進。
6. **r7 → r9 Boots Trial**：拿 Bomb Powder／補炸彈；擊敗敵人、推箱壓板，取 Boots。回 r3 清敵、開 Combat Key 箱（兩把鑰匙），再開 Gate。
7. 可先走 **r7 → r8 → r23**、**r5 → r24 → r28** 秘密支線。Grey Pixel 的完整步驟見下方。
8. **r2 Lower → r10 Lower Landing／B1F**：West、East、Flame 齊備後使用 Lower。地圖切換到 B1F，先取 Rest、用 Lever。
9. **r21 Crystal Warden**：BLUE 開路入房；敲 Crystal 為 RED 才能有效傷害 Warden。擊敗後改回 BLUE，拿 Warden Cache；炸開下方裂縫進 r22。
10. **r22 Hidden Sanctuary**：依 **Slime → Bat → Mirror Mask** 順序殺敵；拿 Skin、Stamp、Fragment、Cache。把兩塊標號石像分別由 `(16,10)`、`(20,10)` 北推到第 9 列，可拿 Layout Cache。
11. **r11 Magnetic Foundry**：清敵、Lever、取 Magnet。帶著 Orb 的投擲擊碎 Engine Pillar `(16,10)`；兩柱皆碎便得到 `floor_lowered`。
12. 帶 Orb 到 **r22**，站 `(9,13)` 朝北 E，放入 Crown Socket `(9,12)`，取得 **Royal Resonance**。Orb 可拿回，T 也可召回至 r20。
13. **r12 Prism Engine**：在 `(6,8)` 朝東，用 Magnet／SPACE 推金屬箱兩次到 Plate `(11,8)`，轉 Prism，啟動 Prism Signal；拿 Key、Crystal Cache；按 T 召回 Orb，避免接下來的 E 優先放下 Orb。
14. 返回 **r6 Returning Runner／1F**：站 Clock `(16,8)` 操作 E，立即朝東 SHIFT 穿 Gate；取得 Boss Key。需要 Boots、Prism、Warden、Royal Resonance，缺一不可。
15. 回 B1F 經 **r10 → r13 Hungry Portal**。用小鑰匙進門；放炸彈餵 Bomb Eater 並退開；拿 Portal Key。
16. **r14 Threefold Circuit**：同 r12 的 Magnet／Prism 光路，再用 Clock 往東衝刺；拿 Reward。
17. **r15 Sentinel Gallery** 清敵，拿 Rest 並開 Gate；**r16 Golem Antechamber** 用 Boss Key 開 Gate，補血後進 r17。
18. **r17 Ancient Golem**：依下方 Boss 解法擊敗三階段，等待死亡動畫完成開門。
19. **r18 Dawn Reservoir**：拿 Treasure、操作 Dawn，向東進 **r27 Royal Treasure Vault**。
20. 開三個 Royal Chests，東側出口完成戰役。寶庫捲軸仍是 `COMING SOON`，不是通關條件。回結果選 `Return to arcade`。

## 每個主要謎題的精確解法

| 房間 | 條件／動作 | 失敗與修復 |
|---|---|---|
| r4 | Gloves + Mirror；站 `(6,10)` 向北推一次，Box 從 `(6,9)` 到 `(6,8)`；E 轉 Prism `(10,6)`；E West | R 還原本房箱位，不會永久失去本房入口前能力 |
| r5 | Lever → Mirror；同 r4 的推箱動作；E East、Compass | 晶體為 BLUE 才能走圖書館路線；回 r2 可調整 |
| r19 | P 依序 Dawn `(7,5)`、Noon `(10,5)`、Dusk `(13,5)`；清幽靈；Flame Signal | 次序錯可重試；Dust `(4,10)` 可補魔法粉 |
| r20 | E 提壺、G 朝獵手擲出；帶壺站 `(13,8)` 使重量達三；用 Iron Orb 打柱 | Pot Rack 補可再生壺；T 召回 Orb，不會永久卡住 |
| r9 | 清敵，Box 往北推到 Plate `(6,8)`，取 Boots | 胸箱生成需短暫等待，未生成不能強開 |
| r12 | Q 選 Magnet；站 `(6,8)` 朝東 SPACE 兩次；E Prism `(11,4)`，使光到 Eye `(11,2)` | F 可吸回金屬；R 還原；Prism Signal 在 `(23,5)` |
| r6／r14 | Clock `(16,8)` 的窗口是 0.85 秒；在開關格 E 後朝東 SHIFT，穿過 `(18,8)` | 不需慢慢走；已閂開的門可返回 |
| r21 | RED 暴露 Warden，BLUE 用於開路；J 改色；擊敗後改回 BLUE | 若打不動，檢查顏色而非一直砍 |
| r22 | Slime → Bat → Mask；把兩尊方塊北推一格，標號與目標配對 | 殺錯順序敵人會重新出現，可重新解，不永久封鎖 |
| r22 Crown Socket | Tower Pillar、Engine Pillar 皆毀；將 Iron Orb 放在 `(9,12)` | 一般壺不是 Orb；T 回 r20 召回，拿起後沿地圖樓梯送回 |
| r13 | 先開 Small Key 門；在 Bomb Eater 前方放炸彈、後撤；取 Portal Key | Supply 可補炸彈，不能帶著已點燃炸彈換房 |
| r15／r16 | 清哨兵才開小鑰匙門；Boss Key 加 Warden 才開最後大門 | 兩種鑰匙不同；r16 開門有動畫，等完成 |

## Grey Pixel／Developer Room：完整劇透

Grey Pixel 是 **Secret Item 03**，穩定 ID 為 `dungeon_grey_pixel`。Item 02 仍是夾娃娃機 Golden Cat，不會改號。

1. 在 r1 E 取得 Map；於 r7 取得／補充炸彈，並開通 Ancient Library 路線。
2. 到 **r5 Ancient Library／1F**，炸開東側裂縫 `secret43` `(24,8)`，後退並等爆炸、裂牆展開。
3. 進 **r24 Whisper Archive**；可先對 Candle `(9,7)` 用 P，再拿 Cache `(15,7)`。
4. 帶 Map 調查 `(22,7)` 的異色接縫。站 `(21,7)` 朝東按 B，再退到 `(18,7)`，等爆炸及展開動畫。
5. 接縫後方 `(23,7)` 會生成小灰色像素。等它生成完成，旁邊按 E 拾取。
6. 出現 `DEBUG LAYER DISCOVERED. ORIGINAL MAP RESTORED.`；右側 `(23,8)` 開通 **r28 Developer Room／1F**。攜帶 Iron Orb 也可通行。
7. E 讀 Photo `(12,5)`、Note `(14,5)`，再與 Miao Miao `(8,8)` 互動。她會說：`This room... I've been here before. So why can't I remember anything?`
8. 從西側 `(1,7)` 安全返回 r24，再回圖書館。收集與閱讀進度會存檔，R 不會重複發獎。
9. Arcade 主線第三章開啟時，既有事件系統登錄 Item 03；若提前找到，先保留 Maze 進度，第三章開啟後再進機台／繼續存檔即可同步。照片另記 Kevin Easter Egg，沒有額外貨幣。

## Ancient Golem 實戰

進 r17 前保持 BLUE 晶體，並準備 Boots、炸彈與藥水。不要只靠連砍。

- 第一階段：站 `(5,8)` 朝東 SHIFT 衝過錨點，暴露核心。靠近 Boss 朝它 J，隔收招再攻擊。
- 第二階段：在 Boss 相鄰位置朝它 B，立刻退開，爆炸破甲後用劍打核心。
- 第三階段：維持 BLUE；重新衝錨、炸甲，最後打核心。
- 通關測試以每次暴露約四次普通揮擊完成一段，實際仍應注意 Boss 的反應與 HP；受傷用 H。
- HP 歸零不會立刻開門，等死亡動畫完成，再進 r18、r27。不要在結算前重開新局。

## 可選支線

- r19 Hidden Fire → Disc；r20 碑文壺 → Lucky Charm。
- r8 爆牆到 r23 Amber Mine：殺蝙蝠、Vein 開 Cache。
- r24 Candle／Cache 與 Grey Pixel；Developer Room 不要求主線通關後才進。
- r6 東裂牆到 r25 Moonlit Mint：推重箱壓 Plate，拿 Cache。
- r22 北裂牆到 r26 Starling Shrine：Gloves 加 BLUE，拿 Cache。
- r22 的 Layout Cache、Orb Cache、Stamp 等保留。外觀收藏與皇家清算是 Maze 的私有遠征紀錄；街機試玩不把顯示的代幣／票券直接加到大廳帳戶。

## 卡關排查與存檔

N 每按一次提供更明確提示；房間停留較久也會提高提示層級。TAB 可切樓層；地圖只有 1F 與 B1F。看不到箱子可能是顏色、清敵、能力或旗標未齊，或箱子尚在生成，先讀提示，不要反覆空按。

E 優先處理附近 Orb／攜帶物，若想操作普通機關請先放下物件。魔法粉 P 不等於炸彈 B。R 是本房入口檢查點，會還原本房暫存消耗；跨房前先確認已解的機關。Boss Key 前必須兩柱、Royal Resonance、Prism、Warden、Boots 齊備。

Esc 可保存退出再選 Continue。舊版載入不改寫原檔；首次以 4.5 保存到舊檔路徑時保留 `.pre-v45` 備份。失效舊房號會送到安全位置並保留能辨識的物品與旗標。請勿手動覆蓋或刪除備份。

## 已執行的完整路線紀錄

以下表格由通過 `test_v45_route.RemasterRouteTests` 的實際互動與房間轉移紀錄產生；戰鬥、推箱、光路、點火、投擲與衝刺的細節依上文子程序執行。它涵蓋全部 28 房、38 個箱子與結局，並非只做圖論可達性推測。

| 步驟 | 樓層／房間 | 實際互動／出口座標與下一站 |
|---|---|---|
| 1 | 1F r1 Stone Vestibule | E：`map` (5, 4) |
| 2 | 1F r1 Stone Vestibule | E：`lever` (8, 5) |
| 3 | 1F r1 Stone Vestibule | 走出口 (12, 1) → r2 Relay Atrium；落點 (12, 13) |
| 4 | 1F r2 Relay Atrium | 走出口 (1, 8) → r4 Weight and Light；落點 (23, 8) |
| 5 | 1F r4 Weight and Light | E：`gloves` (4, 4) |
| 6 | 1F r4 Weight and Light | 走出口 (24, 8) → r2 Relay Atrium；落點 (2, 8) |
| 7 | 1F r2 Relay Atrium | 走出口 (24, 8) → r19 Torch Shrine；落點 (2, 8) |
| 8 | 1F r19 Torch Shrine | E：`powder` (5, 4) |
| 9 | 1F r19 Torch Shrine | E：`flame_signal` (23, 5) |
| 10 | 1F r19 Torch Shrine | E：`disc` (23, 11) |
| 11 | 1F r19 Torch Shrine | 走出口 (1, 8) → r2 Relay Atrium；落點 (23, 8) |
| 12 | 1F r2 Relay Atrium | 走出口 (24, 8) → r19 Torch Shrine；落點 (2, 8) |
| 13 | 1F r19 Torch Shrine | 走出口 (12, 1) → r5 Ancient Library；落點 (12, 13) |
| 14 | 1F r5 Ancient Library | E：`lever` (9, 5) |
| 15 | 1F r5 Ancient Library | E：`mirror` (5, 4) |
| 16 | 1F r5 Ancient Library | E：`east` (23, 5) |
| 17 | 1F r5 Ancient Library | E：`compass` (23, 11) |
| 18 | 1F r5 Ancient Library | 走出口 (12, 14) → r19 Torch Shrine；落點 (12, 2) |
| 19 | 1F r19 Torch Shrine | 走出口 (1, 8) → r2 Relay Atrium；落點 (23, 8) |
| 20 | 1F r2 Relay Atrium | 走出口 (1, 8) → r4 Weight and Light；落點 (23, 8) |
| 21 | 1F r4 Weight and Light | E：`prism` (10, 6) |
| 22 | 1F r4 Weight and Light | E：`west` (23, 5) |
| 23 | 1F r4 Weight and Light | 走出口 (12, 1) → r20 Pot Storage；落點 (12, 13) |
| 24 | 1F r20 Pot Storage | E：`charm_pot` (12, 4) |
| 25 | 1F r20 Pot Storage | E：`jar` (6, 6) |
| 26 | 1F r20 Pot Storage | E：`jar2` (9, 9) |
| 27 | 1F r20 Pot Storage | E：`cache` (23, 5) |
| 28 | 1F r20 Pot Storage | 走出口 (12, 1) → r7 Powder Workshop；落點 (12, 13) |
| 29 | 1F r7 Powder Workshop | E：`powder` (6, 5) |
| 30 | 1F r7 Powder Workshop | E：`lever` (12, 6) |
| 31 | 1F r7 Powder Workshop | 走出口 (24, 8) → r9 Boots Trial；落點 (2, 8) |
| 32 | 1F r9 Boots Trial | E：`boots` (15, 8) |
| 33 | 1F r9 Boots Trial | 走出口 (12, 14) → r3 Copper Watch；落點 (12, 2) |
| 34 | 1F r3 Copper Watch | E：`combat_key` (8, 4) |
| 35 | 1F r3 Copper Watch | E：`fragment` (5, 11) |
| 36 | 1F r3 Copper Watch | E：`gate` (12, 1) |
| 37 | 1F r3 Copper Watch | 走出口 (12, 1) → r9 Boots Trial；落點 (12, 13) |
| 38 | 1F r9 Boots Trial | 走出口 (1, 8) → r7 Powder Workshop；落點 (23, 8) |
| 39 | 1F r7 Powder Workshop | 走出口 (1, 8) → r8 Hidden Treasury；落點 (23, 8) |
| 40 | 1F r8 Hidden Treasury | E：`reward` (12, 6) |
| 41 | 1F r8 Hidden Treasury | 走出口 (12, 14) → r23 Amber Mine；落點 (12, 2) |
| 42 | 1F r23 Amber Mine | E：`vein` (9, 7) |
| 43 | 1F r23 Amber Mine | E：`cache` (15, 7) |
| 44 | 1F r23 Amber Mine | 走出口 (12, 1) → r8 Hidden Treasury；落點 (12, 13) |
| 45 | 1F r8 Hidden Treasury | E：`bonus` (16, 8) |
| 46 | 1F r8 Hidden Treasury | 走出口 (24, 8) → r7 Powder Workshop；落點 (2, 8) |
| 47 | 1F r7 Powder Workshop | 走出口 (24, 8) → r9 Boots Trial；落點 (2, 8) |
| 48 | 1F r9 Boots Trial | 走出口 (12, 14) → r3 Copper Watch；落點 (12, 2) |
| 49 | 1F r3 Copper Watch | 走出口 (12, 14) → r2 Relay Atrium；落點 (12, 2) |
| 50 | 1F r2 Relay Atrium | 走出口 (24, 8) → r19 Torch Shrine；落點 (2, 8) |
| 51 | 1F r19 Torch Shrine | 走出口 (12, 1) → r5 Ancient Library；落點 (12, 13) |
| 52 | 1F r5 Ancient Library | 走出口 (24, 8) → r24 Whisper Archive；落點 (2, 8) |
| 53 | 1F r24 Whisper Archive | E：`cache` (15, 7) |
| 54 | 1F r24 Whisper Archive | E：`grey_pixel` (23, 7) |
| 55 | 1F r24 Whisper Archive | 走出口 (23, 8) → r28 Developer Room；落點 (2, 7) |
| 56 | 1F r28 Developer Room | E：`photo` (12, 5) |
| 57 | 1F r28 Developer Room | E：`note` (14, 5) |
| 58 | 1F r28 Developer Room | E：`miao` (8, 8) |
| 59 | 1F r28 Developer Room | 走出口 (1, 7) → r24 Whisper Archive；落點 (23, 9) |
| 60 | 1F r24 Whisper Archive | 走出口 (1, 8) → r5 Ancient Library；落點 (23, 8) |
| 61 | 1F r5 Ancient Library | 走出口 (12, 14) → r19 Torch Shrine；落點 (12, 2) |
| 62 | 1F r19 Torch Shrine | 走出口 (1, 8) → r2 Relay Atrium；落點 (23, 8) |
| 63 | 1F r2 Relay Atrium | E：`lower` (22, 11) |
| 64 | 1F r2 Relay Atrium | 走出口 (22, 11) → r10 Lower Landing；落點 (2, 7) |
| 65 | B1F r10 Lower Landing | E：`rest` (5, 11) |
| 66 | B1F r10 Lower Landing | E：`lever` (8, 5) |
| 67 | B1F r10 Lower Landing | 走出口 (1, 8) → r21 Crystal Warden；落點 (23, 8) |
| 68 | B1F r21 Crystal Warden | E：`warden_cache` (23, 5) |
| 69 | B1F r21 Crystal Warden | 走出口 (12, 1) → r22 Hidden Sanctuary；落點 (12, 13) |
| 70 | B1F r22 Hidden Sanctuary | E：`skin` (20, 5) |
| 71 | B1F r22 Hidden Sanctuary | E：`stamp` (8, 5) |
| 72 | B1F r22 Hidden Sanctuary | E：`fragment` (19, 11) |
| 73 | B1F r22 Hidden Sanctuary | E：`cache` (21, 11) |
| 74 | B1F r22 Hidden Sanctuary | E：`layout_cache` (22, 6) |
| 75 | B1F r22 Hidden Sanctuary | 走出口 (12, 1) → r26 Starling Shrine；落點 (12, 13) |
| 76 | B1F r26 Starling Shrine | E：`cache` (15, 7) |
| 77 | B1F r26 Starling Shrine | 走出口 (12, 14) → r22 Hidden Sanctuary；落點 (12, 2) |
| 78 | B1F r22 Hidden Sanctuary | 走出口 (12, 14) → r21 Crystal Warden；落點 (12, 2) |
| 79 | B1F r21 Crystal Warden | 走出口 (24, 8) → r10 Lower Landing；落點 (2, 8) |
| 80 | B1F r10 Lower Landing | 走出口 (12, 1) → r11 Magnetic Foundry；落點 (12, 13) |
| 81 | B1F r11 Magnetic Foundry | E：`lever` (8, 4) |
| 82 | B1F r11 Magnetic Foundry | E：`magnet` (13, 8) |
| 83 | B1F r11 Magnetic Foundry | 走出口 (1, 8) → r22 Hidden Sanctuary；落點 (23, 8) |
| 84 | B1F r22 Hidden Sanctuary | E：`orb_cache` (6, 11) |
| 85 | B1F r22 Hidden Sanctuary | 走出口 (5, 13) → r20 Pot Storage；落點 (21, 12) |
| 86 | 1F r20 Pot Storage | 走出口 (21, 13) → r22 Hidden Sanctuary；落點 (5, 12) |
| 87 | B1F r22 Hidden Sanctuary | 走出口 (24, 8) → r11 Magnetic Foundry；落點 (2, 8) |
| 88 | B1F r11 Magnetic Foundry | 走出口 (24, 8) → r12 Prism Engine；落點 (2, 8) |
| 89 | B1F r12 Prism Engine | E：`prism` (11, 4) |
| 90 | B1F r12 Prism Engine | E：`prism_signal` (23, 5) |
| 91 | B1F r12 Prism Engine | E：`key` (23, 11) |
| 92 | B1F r12 Prism Engine | E：`crystal_cache` (15, 11) |
| 93 | B1F r12 Prism Engine | 走出口 (1, 8) → r11 Magnetic Foundry；落點 (23, 8) |
| 94 | B1F r11 Magnetic Foundry | 走出口 (12, 14) → r10 Lower Landing；落點 (12, 2) |
| 95 | B1F r10 Lower Landing | 走出口 (2, 8) → r2 Relay Atrium；落點 (22, 10) |
| 96 | 1F r2 Relay Atrium | 走出口 (12, 14) → r1 Stone Vestibule；落點 (12, 2) |
| 97 | 1F r1 Stone Vestibule | 走出口 (24, 8) → r6 Returning Runner；落點 (2, 8) |
| 98 | 1F r6 Returning Runner | E：`clock` (16, 8) |
| 99 | 1F r6 Returning Runner | E：`boss_key` (23, 6) |
| 100 | 1F r6 Returning Runner | 走出口 (24, 8) → r25 Moonlit Mint；落點 (2, 8) |
| 101 | 1F r25 Moonlit Mint | E：`cache` (15, 7) |
| 102 | 1F r25 Moonlit Mint | 走出口 (1, 8) → r6 Returning Runner；落點 (23, 8) |
| 103 | 1F r6 Returning Runner | 走出口 (1, 8) → r1 Stone Vestibule；落點 (23, 8) |
| 104 | 1F r1 Stone Vestibule | 走出口 (12, 1) → r2 Relay Atrium；落點 (12, 13) |
| 105 | 1F r2 Relay Atrium | 走出口 (22, 11) → r10 Lower Landing；落點 (2, 7) |
| 106 | B1F r10 Lower Landing | 走出口 (24, 8) → r13 Hungry Portal；落點 (2, 8) |
| 107 | B1F r13 Hungry Portal | E：`portal_key` (8, 4) |
| 108 | B1F r13 Hungry Portal | 走出口 (24, 8) → r14 Threefold Circuit；落點 (2, 8) |
| 109 | B1F r14 Threefold Circuit | E：`prism` (11, 4) |
| 110 | B1F r14 Threefold Circuit | E：`clock` (16, 8) |
| 111 | B1F r14 Threefold Circuit | E：`reward` (23, 6) |
| 112 | B1F r14 Threefold Circuit | 走出口 (23, 1) → r15 Sentinel Gallery；落點 (12, 13) |
| 113 | B1F r15 Sentinel Gallery | E：`rest` (8, 4) |
| 114 | B1F r15 Sentinel Gallery | E：`gate` (12, 1) |
| 115 | B1F r15 Sentinel Gallery | 走出口 (12, 1) → r16 Golem Antechamber；落點 (12, 13) |
| 116 | B1F r16 Golem Antechamber | E：`gate` (24, 8) |
| 117 | B1F r16 Golem Antechamber | E：`rest` (8, 5) |
| 118 | B1F r16 Golem Antechamber | 走出口 (24, 8) → r17 Ancient Golem；落點 (2, 8) |
| 119 | B1F r17 Ancient Golem | 走出口 (24, 8) → r18 Dawn Reservoir；落點 (2, 8) |
| 120 | B1F r18 Dawn Reservoir | E：`treasure` (8, 11) |
| 121 | B1F r18 Dawn Reservoir | E：`dawn` (10, 5) |
| 122 | B1F r18 Dawn Reservoir | 走出口 (24, 8) → r27 Royal Treasure Vault；落點 (2, 7) |
| 123 | B1F r27 Royal Treasure Vault | E：`royal_tokens` (6, 4) |
| 124 | B1F r27 Royal Treasure Vault | E：`royal_tickets` (15, 4) |
| 125 | B1F r27 Royal Treasure Vault | E：`royal_collection` (15, 10) |
| 126 | B1F r27 Royal Treasure Vault | E：`scroll` (11, 7) |


驗證命令：`PYTHONPATH=.:puzzle_maze/tests .venv/bin/python -m unittest test_v45_route -v`。
這是碰撞、物件、傷害、消耗與轉移 API 的自動化通關，不等同真人視窗操作驗收。
