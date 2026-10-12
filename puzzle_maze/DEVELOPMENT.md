# 開發紀錄

2026-10-12，分支 `feature/puzzle-maze`，基底 `1204778`。
原有未追蹤檔案 `tatus -sb` 保留。所有新檔、測試與文件位於 `puzzle_maze/`。

- Phase A：移動、碰撞、Camera；2 項測試通過。Commit `4ae3e05`。
- Phase B：JSON 地圖、八房連接、合法性檢查；5 項測試通過。Commit `e7a46dd`。
- Phase C：推箱、壓力板、AND 條件門、開關、鑰匙；11 項測試通過。Commit `b4b5807`。
- Phase D：秘密牆、限時門佔用保護、綜合機關、檢查點、獨立原子存檔；
  17 項測試通過。Commit `d771d3f`。
- Phase E：原創像素渲染、四方向動畫、跟隨鏡頭、選單、HUD、地圖、粒子、
  房間轉場、合成音樂音效、8 主房 + 1 隱藏房、關卡搜尋與通關重播。
  26 項測試通過，SDL dummy 啟動及截圖檢查通過。

一般門採完成条件後鎖定開啟，限時門則持續觀察倒數。
入口檢查點同步還原鑰匙與物件，避免重置後重複取得鑰匙。
程式化美術及聲音無外部資產或授權依賴。沒有加入 Lobby，沒有 Push/Pull/Merge。

Phase E 後的呈現檢查修正：壓力板先繪製，避免覆蓋其上的木箱；
Atlas 依 JSON 的實際出口關係繪製已探索連線，包含第六房到秘密房的支線。
26 項測試、compileall 與 Git 空白格式檢查重新通過。

既有遊戲回歸：Retro Racer 82、Pixel Volleyball 110、Cat Territory 27、
Cat Minesweeper 14、Galaxy Defender 78 項均通過（SDL dummy，獨立程序）。

最終回歸：Arcade Lobby 完整 discover 測試成功（exit code 0；同一 discovery
共 1,361 項），上述其他遊戲合計 311 項亦成功。Puzzle Maze 26 項全部通過。
最終 Git 差異全部限定 `puzzle_maze/`，原未追蹤檔案不變；未修改 main 或推送。

使用者後續授權接入 Lobby 試玩：新增中央島列 `island_1` 的免費機台。
僅修改 Lobby 的 settings.MACHINES 與 scenes 註冊，新增整合測試；可選介面
位於 puzzle_maze/lobby_scene.py。使用既有參與者輸入、視窗及音訊 API，沒有
修改音效管理、經濟或其他遊戲。主選單 Esc / 暫停 Return to arcade 可返回。
獨立模式 26 項測試及 3 項機台整合測試通過，新增測試不寫入玩家存檔。

## Puzzle Maze 2.0

基底 `04ec231`，沿用 feature/puzzle-maze；原未追蹤 tatus -sb 保留。
本次只修改 puzzle_maze/，不擴充或更動 Lobby 介面及其他遊戲。

Phase A：字體改到最終視窗解析度繪製；像素场景整數倍率 nearest 縮放。
附 Noto Sans CJK TC（SIL OFL）及授權檔，驗證繁中文字形與五種視窗尺寸。
