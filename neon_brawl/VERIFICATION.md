# NEON BRAWL 交付與驗證紀錄

## 實作內容

- 11 秒非阻塞開場、標題、三人選角、9 秒互動教學。
- REX（平衡）、NOVA（高速）、BRUNO（重擊）；各自的生命、速度、攻擊、
  防禦與收招參數，以及原創像素外觀與動作。
- WASD／方向鍵移動，J 三連擊、K 重擊、L 跳躍、空中 J、U 特殊技、
  I 閃避、E 補給；Esc 暫停並可重看操作或結束本局。
- 明確前搖／有效時間／收招與距離、方向、巷道判定；單次揮擊不重複命中。
  擊停、震動、火花、受傷閃光、擊退、倒地、無敵與能量管理。
- Grunt、Runner、Bruiser、Ranged 四種敵人；接近、站位、預警攻擊、收招、
  受傷、倒地與死亡；同時起手上限與出生保護。
- 三關十二個封鎖區，總計 70 名敵人；背景視差、雨、霓虹、月台與伺服器。
  月台／核心的通電軌道有提前預警；檢查點回血、能量與食物。
- WARDEN、RELAY、NULL 三場頭目戰。NULL 有重擊、遠射、第二階段橫掃，
  明確血條與階段轉換，勝利後有結局與成績。
- 四首原創循環音樂與十種原創音效；沿用共用音量、靜音、場景聲道及無裝置容錯。
- Arcade Floor 的 `island_0`（70,138）登錄為一代幣機台。
  保留原六台遊戲、原清單順序及 `island_2` 劇情故障機台。
- 沿用 MinigameScene / RoomHub / PlaySession，不增加存檔結構。
  啟動前關閉退代幣／券，啟動後退出按既有政策結算；結果讀取無副作用。

## 架構與檔案

`neon_brawl/data.py` 為平衡設定；`model.py` 的 Fighter、PlayerFighter、
EnemyFighter、CombatSystem、Campaign 負責模擬；`art.py` 負責快取像素動畫與
Renderer；`game.py` 的 BrawlGame 管理畫面與操作；`build_audio.py` 生成音訊。

`arcade_lobby/neon_brawl_scene.py` 是場景及獎勵轉接器。既有整合修改集中於
settings.py、scenes.py、machine.py、game.py、audio_manager.py。

新增測試為 `neon_brawl/tests/`、`arcade_lobby/test_neon_brawl.py`。
既有 `test_rooms.py` 的假機台改用未登錄槽位，`test_audio_system.py` 的音軌總數
由 13 更新為 17；保留原本重複位置、資產唯一性與品質斷言。

## 驗證方式與限制

三位角色的模擬駕駛只使用正常移動與動作，不調整生命、朝向、傷害或敵人狀態：

| 角色 | 結果 | 擊敗敵人 | 剩餘 HP | 承受傷害 | 遊戲時間 |
|---|---|---:|---:|---:|---:|
| REX | 勝利 | 70 | 140 | 233 | 294.3 秒 |
| NOVA | 勝利 | 70 | 109 | 215 | 318.4 秒 |
| BRUNO | 勝利 | 70 | 179 | 359 | 227.6 秒 |

另有場景層的鍵盤事件通關：機台啟動 → 開場 → 標題 → 選角 → 教學 → 三關 →
NULL 第二階段 → 結局 → 結果 → 回街機，檢查扣幣及一次性領獎。
自然戰敗測試讓敵人正常攻擊至死亡；暫停選單退出、視窗關閉、啟動前退款、
免費券退款、再次進入、存檔往返均有覆蓋。

已檢視 Pygame 實際渲染的選角、戰鬥與 NULL 第二階段截圖。
本環境沒有進行真人桌面通關或實體喇叭試聽；自動化通關不代表真人手感驗收。
首輪 10–15 分鐘仍是未經真人量測的平衡目標，最佳化自動操作約 4–6 分鐘。
背景採重複原創圖塊，選角肖像使用放大的角色動畫。

曾在開發回歸發現機台清單順序、音軌長度／響度及重複別名問題，已修正。
早期的全街機探索測試因已載入舊機台順序而停止，不將該次執行算作通過。
最終採下列受影響模組的完整回歸，沒有宣稱全儲存庫測試全部通過。

## 執行命令

在專案根目錄啟動：

```sh
.venv/bin/python arcade_lobby/main.py
```

從 HOME 向左進入 ARCADE FLOOR，接近左側島台 NEON BRAWL，E 互動並確認。
完整操作與手動驗收清單見 [README.md](README.md)。

## Git 里程碑

分支：`feature/neon-brawl`，由乾淨的本機 main 建立；未推送、合併或改寫歷史。

- `fa89d71`：核心戰鬥、關卡資料與像素繪圖。
- `7a80da5`：完整畫面流程與街機轉接。
- `1479ef0`：原創音樂、危險地形與戰鬥測試。
- `6d958d7`：鍵盤通關及一次性結算驗證。
- `1f88109`：動畫、碰撞、音效與操作文件。
- `b695aa2`：機台相容性與音訊品質修正。

## 最終自動測試結果

環境：既有 `.venv`，Python 3.12.3 / pygame-ce 2.5.8；SDL 視訊與音訊皆用 dummy。

| 測試組 | 精確結果 |
|---|---|
| 既有街機／六款遊戲與經濟相關模組 | 314 tests / 73.657s / OK |
| NEON BRAWL、資料相容性、音訊生命週期及設定 | 277 tests / 60.824s / OK |
| 音訊資產品質與場地登錄聚焦檢查 | 17 tests / 4.160s / OK |
| 最後開場淡入／標誌動畫後的畫面流程檢查 | 7 tests / 0.073s / OK |

前兩組為互不重複的 591 項測試；後兩組是其中測試的聚焦重跑，不重複計入總數。
最終程式碼交付前，新功能專項再確認 34 tests / 4.679s / OK。

```sh
export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:.
.venv/bin/python -m unittest test_rooms test_economy test_rewards test_cat_maze \
  test_galaxy_defender test_pixel_volleyball test_racer_launch test_puzzle_maze \
  test_audio_manager -q
.venv/bin/python -m unittest test_neon_brawl neon_brawl.tests.test_combat \
  test_machine_themes test_profiles test_reward_loop test_save_lock \
  test_single_player test_scene_wipe test_audio_lifecycle test_audio_system \
  test_audio_settings -q
```

`git diff --check` 通過。沒有提交存檔、快取、測試日誌或虛擬環境。
