# 預先登記：商品長歷史驗證（Dukascopy）

登記時間：以本檔案 commit 時間為準，在下載與檢視任何 Dukascopy 價格之前提交。

## 資料
- 來源：Dukascopy 公開歷史資料（datafeed.dukascopy.com），1 小時 K（BID），重採樣為 4h
- 標的：黃金 XAUUSD、白銀 XAGUSD、WTI 原油、布蘭特原油、天然氣，以及 Dukascopy 有提供的銅
- **只使用 2025-04-01 之前的資料**。這之後的期間已經在 OKX 永續合約上看過，排除以保持乾淨
- 處理方式與 OKX 永續相同：美東時間休市排除、流動性暖身
- 成本：對應 OKX 永續的實測成本（未實測者 10 bps／邊）
- 資金費率：沒有歷史，依引擎規則多空各收約 1 bp／8h（偏保守）
- 價格刻度：以與 OKX 永續重疊期間的價格比對決定，只比對價格水準，不看任何策略報酬

## A. 確認性檢定：已凍結的前向候選
參數完全照 `research/forward/preregistered.csv`，不重新選參數，評估整段 2025-04-01 之前的歷史：
1. `tsmom` 4h，{"lookback": 24, "min_move_atr": 0.0}，WTI
2. `tsmom` 4h，{"lookback": 192, "min_move_atr": 0.0}，黃金
3. `donchian_breakout` 4h，{"entry": 20, "exit": 20}，能源組合（WTI、布蘭特、天然氣）

`ema_trend` 布蘭特 30m 無法用 1 小時資料重建，排除。
- 多重檢定 N = 3
- 通過條件：DSR ≥ 0.95、手續費與滑價加倍後仍賺錢、拿掉最賺 3 筆仍賺錢、前後兩半都賺錢

## B. 探索性檢定：趨勢策略家族
- 策略：`tsmom`、`donchian_breakout`、`ema_trend`，現有參數網格
- 時間窗口：4h、1h
- 每個標的單獨檢定，加上金屬組合與能源組合
- 樣本內 60%／樣本外 40%（全部在 2025-04-01 之前），門檻為 `quant/research/gates.py` 全部 10 道
- 獨立帳本 `research/longhist/ledger.csv`，N 為本研究的樣本外嘗試數；另外揭露全專案 N 下的 DSR

## 結論規則
- A 有任何一個通過：該候選有長期證據，前向測試繼續，並優先考慮接模擬盤
- B 有 accept：預先登記到前向測試
- 全部未通過：結論是「長歷史也不支持」，不針對這份資料做第二輪搜尋
