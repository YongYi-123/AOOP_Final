# Developer Room：Golden Age 一致性與實體互動修整

## Golden Age 實際觀察

本次先閱讀 arcade_lobby/golden_age_scene.py 的 spot_at、draw、_sorted_things、solids 與動畫互動，golden_age_art.py 的家具外框與快取，golden_age_testing.py 的按鍵／步行工具；並對照 HOME 的家具足部碰撞、Miao 原始畫格與現有正式 r28。

使用既有 TrialCase／Driver 在 SDL dummy 中啟動真正 Arcade Game，由 Vending Machine → Legacy Terminal → Trial 01，完成開場，再以真實方向鍵走到 desk、按 E 觸發檢視文字。實際開啟觀察 room.png、desk_prompt.png、desk_open.png（/tmp/golden-reference）。Golden Age 參考畫面是實際程式渲染，不是概念圖；這不是桌面真人操作驗收。Golden Age 本身沒有任何檔案被修改。

看到的設計原則：深色細輪廓、接地陰影、家具正常遮擋、最近互動目標、小型動作提示，按下後才開內容。按本次要求，工作室進一步簡化為僅 [E]，不照搬 Golden Age 的完整按鍵／動作字串與故事內容。

## 實作改善

- 正式 `Renderer.world → studio_view.draw_studio` 與預覽繼續共用同一場景。
- 完全移除底部黑色資訊面板、物件預告名稱、操作說明與自動描述，原生房間美術延伸到 320×240；下方是木地板與房間邊緣。
- 靠近互動物件只顯示一個附著在實際物件旁的 [E] 像素框。最近物件優先，距離相同才參考朝向；按 E 後才顯示標題／內容。閱讀、對話時隱藏世界提示，Enter 關閉。
- 修正測試預覽定位：挑選沒有其他物件占用的合法接近位置，F8／F9 仍經正式 E 互動，不會因最近優先而誤讀旁邊的紙張。
- 右上 `dev_004` 與 `studio_todo` 改成真正貼在牆上的便條，略有不同斜角、上緣貼附高光與陰影；互動提示跟隨新可見位置。物件穩定 ID 與內容不變。
- 移除玩家站在家具後方時的半透明。家具所有實體像素保持 alpha 255，正常按腳底排序遮擋，沒有 proximity fade。新增一像素暖棕外輪廓，使桌、椅、電腦與其他道具更接近 Arcade 的精緻像素風格。沒有再次重做既有色盤或光照。
- Miao 沿用 Lobby 的原始畫格與等級外觀，新增耳朵輕動、抬頭與既有眨眼、尾巴動作。正式渲染擷取的多個待機畫面確實不同。
- Miao 完成入場後具有 12×6 足部碰撞；玩家走路與衝刺都不能穿過。周圍通道與對話接近位置仍可達，入口演出不與自己的碰撞相撞。
- 落地燈從固定底圖提升為獨立、按深度排序的實體家具，底座有碰撞；工程桌的碰撞向後涵蓋工作表面，不能再從桌燈位置穿過。一般家具維持原有地面輪廓，不把高處全部當成牆。
- 工作室存檔版本標記更新為 3。舊存檔站在新增桌面／燈／Miao 碰撞區時安全遷位，保留物品、秘密、故事與獎勵旗標；舊版 2 存檔首次保存前保留 `.pre-studio-v3`。更舊存檔既有 `.pre-studio-v2` 備份規則保留。

## 測試與實際畫面

| 測試 | 結果 |
|---|---|
| 全 Puzzle Maze | 265 tests / 69.086s / OK |
| 工作室／預覽專項（包含於全套） | 33 tests / 7.777s / OK |
| Lobby、Maze 整合、秘密、經濟、獎勵、房間、Miao、HOME | 320 tests / 88.223s / OK |
| Golden Age 入口、房間、存檔、內容、退出返回 | 44 tests / 85.783s / OK |
| 正式流程與截圖工具 | 成功取得 Grey Pixel、進入 r28、演出、閱讀、坐下起身、繞行家具並退出 |

新增八項回歸：只有單一 [E]／無底部資訊列、按 E 開關內容、遠離隱藏與最近優先、Miao 真實走路碰撞與對話可達、兩種燈具碰撞、全部家具 alpha 0/255、牆面便條位置、原 Lobby 貓待機變化、版本 2 存檔安全遷移備份（相關行為合併在八個測試方法）。舊遮擋測試更新為本次明確要求的不淡化行為，仍檢查前後深度順序。

已實際開啟檢視：Golden Age 全景與 E 鍵前後畫面，工作室全景、牆面便條提示、桌後不透明家具、Miao 待機近照。工作室圖片在 `/tmp/studio-consistency`：07_studio_overview.png、12_desk_behind.png、21_todo_prompt.png、miao_idle_0.png 至 miao_idle_4.png，以及入口、沙發、閱讀截圖。文字框邊界與重疊也由工具檢查。

沒有宣稱桌面真人全流程或音效聽感驗收；這些仍需人工確認。沒有改 Golden Age、其他 minigames 或 Lobby 的任何檔案。

## 重現命令

```bash
cd /home/nora/AOOP_Final
.venv/bin/python -m puzzle_maze --dev-preview developer-room
```

WASD／方向鍵走路，靠近小 [E] 按 E，Enter 關閉閱讀。左下沙發前方按 E 坐下，再 E 起身。F7 入場演出、F8 可選互動、F9 待辦，左右鍵翻頁，Esc 安全退出。預覽不讀寫真人存檔，也不派發帳戶獎勵。

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m puzzle_maze.review_studio_refinement --output /tmp/studio-consistency
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=.:puzzle_maze/tests .venv/bin/python -m unittest discover -s puzzle_maze/tests -p 'test_*.py' -q
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:.:puzzle_maze/tests .venv/bin/python -m unittest test_puzzle_maze test_maze45_secret test_economy test_rewards test_rooms test_miao_meow test_home_decor -q
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m unittest test_golden_age.EntryTests test_golden_age.RoomTests test_golden_age.SaveTests test_golden_age.ContentTests test_golden_age.LeaveAndReturnTests -q
```

## 修改檔案與 Git

正式程式：studio_view.py、studio_interactions.py、studio_layout.py、studio_furniture.py、developer_art.py、miao_adapter.py、remaster.py、.gitignore。
驗證：tests/test_studio_consistency.py、tests/test_cozy_studio.py、tests/test_studio_refinement.py、tests/test_visual_story.py、review_studio_refinement.py。
文件：GREY_PIXEL_PREVIEW.md、本報告。

- 4d7c21f feat(maze): align studio prompts opaque props and companion collision with arcade style
- 後續文件與待機畫面擷取提交：docs(maze): document Golden Age reference and studio consistency verification（最終 ID 見 git log）。

沿用 feature/kevin-cozy-studio，保留既有作者與歷史。沒有 Push、Merge、Force Push 或 Squash。
