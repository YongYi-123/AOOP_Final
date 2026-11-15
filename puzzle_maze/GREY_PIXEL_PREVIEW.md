# Grey Pixel 開發預覽

## 直接啟動

在專案根目錄執行；使用已安裝 Pygame 的專案虛擬環境：

```bash
cd /home/nora/AOOP_Final
.venv/bin/python -m puzzle_maze --dev-preview grey-pixel
```

不必先過 Maze，也不必建立／選擇 Lobby 玩家。視窗會從正式 Grey Pixel 發現與取得動畫開始，自動接入 r28，播放原版 Miao Meow 的門口步行與對話，再開放探索。所有可選日記與正式房間出口都可操作。

相依套件與主遊戲相同（專案環境目前使用 pygame-ce 2.5.8、Python 3.12）。預覽不需要網路或新素材套件。

## 其他入口

```bash
.venv/bin/python -m puzzle_maze --dev-preview developer-room
.venv/bin/python -m puzzle_maze --dev-preview miao-entrance
.venv/bin/python -m puzzle_maze --dev-preview developer-diaries
```

| 入口 | 行為 |
|---|---|
| `grey-pixel` | 正式道具揭示 → 工程室 → Miao 入場 → 探索 |
| `developer-room` | 已完成入場的工程室，直接探索 |
| `miao-entrance` | 從西門重新觀看 Miao 步行與對話 |
| `developer-diaries` | 出現在第一篇日記附近，按 E 閱讀 |

## 操作

| 鍵 | 功能 |
|---|---|
| WASD／方向鍵 | 使用正式 Maze 移動 |
| E | 閱讀面向／附近物件；也可推進 Miao 對話 |
| Enter | 推進對話、關閉閱讀、跳過道具揭示 |
| Space | 跳過目前發現動畫／Miao 入場；探索時保留正式 Pulse 功能 |
| R | 重建目前選定的預覽入口 |
| F5 | 從完整 Grey Pixel 序列重來 |
| F6 | 直接回已完成入場的工程室 |
| F7 | 重播 Miao 入場 |
| F8 | 依序定位並開啟七篇日記、鴨子、咖啡、紅按鈕互動 |
| Esc | 退出整個預覽（閱讀時也退出；用 Enter 關閉閱讀） |

從 r28 西門 `(1,7)` 可回正式 r24；預覽仍保持記憶體隔離。想回房間按 F6。F8 是便利測試定位，會走正式 E 互動，不使用另一套閱讀內容。

## 存檔保護

`PreviewGame` 共用正式 `Game`、`RemasteredSession`、`GreyPixelReveal`、`LabEntrance` 和房間資料。僅初始化一次性的記憶體前置條件，沒有複製假房間。

預覽固定 `persistent=False`：不綁定 CampaignProfile、不讀 Continue 存檔、`save()` 直接返回；離開與關閉視窗也不能寫檔。沒有 Arcade Lobby session／story manager，不會發出真人玩家秘密事件，不會授予真實 Tokens／Tickets，也不改存檔格式。R／F5 會捨棄本次預覽狀態，正式存檔不受影響。

只有明確使用 `--screenshot` 時，才會寫入你指定的圖片路徑。診斷工具預設把圖放 `/tmp`，不建立玩家檔案。

## 無視窗驗證及截圖

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m puzzle_maze --dev-preview grey-pixel --headless --frames 2
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m puzzle_maze --dev-preview grey-pixel --headless --frames 180 --screenshot /tmp/grey-pixel.png
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m puzzle_maze.review_personality
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=.:puzzle_maze/tests .venv/bin/python -m unittest puzzle_maze.tests.test_dev_preview puzzle_maze.tests.test_personality_art -v
```

`--screenshot` 用固定 1/60 秒推進指定幀數，適合重現道具揭示。`review_personality` 會輸出工程室全景、入場、日記、史萊姆及房間畫面到 `/tmp/maze-personality`，並檢查文字框邊界。

## 常見問題

- **No module named pygame**：使用 `.venv/bin/python`，不要換成尚未安裝專案依賴的系統 Python。
- **No module named puzzle_maze**：先 `cd /home/nora/AOOP_Final`，再用 `-m puzzle_maze`。
- **聲音裝置不可用**：沿用正式遊戲的無音訊降級；無視窗測試使用上述 dummy 設定。
- **Esc 為什麼沒有關閉日記而是離開？** 預覽明確保留 Esc 安全退出，用 Enter 關閉閱讀；正式遊戲仍可用 Esc 關閉日記。
- **想保留預覽進度？** 此功能刻意不保存；正式遊戲請從一般入口啟動。
- **想重新看動畫？** F5 全序列、F7 Miao；按住按鍵不會連續重設。
