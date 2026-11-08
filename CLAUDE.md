# quant：OKX 波段策略研究

目標：在 OKX 的美股、台股（TSM ADR）、貴金屬、原物料永續合約上，找出扣除成本後、經得起質詢的波段策略。時間窗口：10m / 30m / 1h / 4h。

## 完成的定義
`./scripts/verify.sh` 全部通過。說「完成」之前必須跑過，並貼出最後一行輸出。

## 常用指令
- 更新資料：`uv run python -m quant.data.cli`（只抓公開行情，不需要金鑰）
- 跑研究：`uv run python -m quant.research.cli`，報告在 `research/reports/`
- 多角色研究回合：`/research-round`

## 架構
- `quant/data/`：OKX 抓資料（邊界，資料在這裡解析與驗證）、5m 原始資料、重採樣成各時間窗口。所有時間窗口都從同一份 5m 資料產生。
- `quant/strategies/`：策略只輸出想持有的部位 -1/0/1。
- `quant/engine/backtest.py`：引擎在下一根開盤成交，扣手續費、滑價、資金費率。
- `quant/research/`：樣本內選參數 → 樣本外驗證 → 8 道門檻 → ACCEPT / WATCH / REJECT。每次嘗試都寫進 `research/ledger.csv`。

## 規則與強制機制

| 規則 | 由什麼強制 |
|---|---|
| 策略不能偷看未來 | 架構：引擎在下一根開盤成交。`tests/test_lookahead.py` 對每個策略的每組參數做「截掉未來，過去訊號不變」檢查。`tools/check_lookahead.py` 擋 `shift(-n)`、`bfill`、`center=True` |
| 策略要有經濟理由 | `register()` 拒絕少於 40 字的 rationale |
| 訊號只能是 -1/0/1 | `backtest()` 的 `_validate_signal` 丟出 `SignalError` |
| K 線資料必須乾淨 | `validate_bars()` 在抓資料與重採樣時檢查 |
| 不能隱藏嘗試次數 | `Ledger` 由 `research()` 自動寫入，deflated Sharpe 的 N 從帳本讀 |
| 門檻不能放寬到讓雜訊通過 | `tests/test_pipeline.py`：純雜訊 0 個通過，埋入趨勢必須被找到 |
| 資金費率歷史不足時要保守 | `_funding_cost` 對多空兩邊都收費，`test_missing_funding_history_is_charged_against_both_sides` |
| 不在傳統市場休市的 K 棒上算指標或成交 | `quant/data/sessions.py` 在重採樣前移除週五 21:00–週日 22:00 UTC 與每日 21:00 的 K 棒，`tests/test_sessions.py` |
| 排除上市第一週的異常波動 | `tradable_bars()` 的 `LISTING_BURN_IN`，`test_tradfi_instruments_drop_closed_hours_and_listing_week` |
| 沒有資金費率歷史時，各邊收較不利的費率 | `_funding_cost` 取假設值與觀察平均值的較差者，`test_before_funding_history_each_side_pays_the_worse_of_assumed_and_observed` |
| 不寫註解 | `tools/check_no_comments.py`。用命名、型別、測試表達 |
| 型別嚴格 | `mypy --strict` |

你糾正 agent 的時候：先修錯，再把規則加進這張表。如果規則已經在表上但沒有機制強制，就在同一個改動裡補上 check 或 test。

## 不准做的事
- 為了讓策略通過而放寬 `quant/research/gates.py`
- 看過樣本外結果後回頭調同一個策略的參數
- 實盤下單（需要使用者明確授權）
