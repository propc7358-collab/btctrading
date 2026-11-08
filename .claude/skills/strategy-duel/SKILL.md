---
name: strategy-duel
description: 兩個角色的策略對決回合：研究員提出新策略，驗證者攻擊結果，主持人只採納能重現的結論。每 10 分鐘一回合，最多 12 回合。Use for /strategy-duel or "跑一回合對決".
---

# 策略對決

主持人是主 session。研究員是 `strategy-researcher`，驗證者是 `overfit-skeptic`（兼看成本與風險）。兩個角色在整個對決期間都是同一個 agent，用 SendMessage 延續，讓它們記得前面的討論。對話紀錄寫在 `research/duel/dialogue.md`。

## 「好結果」的定義（寫死，對決期間不准改）
- **GOOD**：單一標的或合併組合的候選通過 `quant/research/gates.py` 全部門檻（verdict = accept），並且驗證者攻擊後，主持人重跑沒有出現 KILL。
- **PROMISING**：verdict = watch，並且通過驗證者攻擊。這只能進前向測試，不算證明有效。
- 其他都是失敗。

## 停止條件
- 出現 GOOD，或已經跑完 12 回合。
- 停止時刪除排程，並向使用者回報。

## 每回合步驟
1. 讀 `research/duel/state.md` 確認回合數。超過 12 就停止。
2. **研究員**：讀 `research/duel/dialogue.md` 裡驗證者上一回合的意見，在 `quant/strategies/library.py` 新增 1–2 個**機制不同**的策略。不准只把舊策略換參數或換名字重登錄，主持人會檢查。每個參數最多 3 個值。跑 `./scripts/verify.sh`，然後跑：
   - `uv run python -m quant.research.cli --strategies <新策略...>`
   - `uv run python -m quant.research.cli --pooled --strategies <新策略...>`

   把提案、經濟理由和兩份報告的重點寫進 dialogue.md。
3. **驗證者**：攻擊這回合所有 accept/watch 候選。如果沒有，就攻擊最接近的 3 個。每個判定都要附指令與輸出。寫進 dialogue.md，並告訴研究員下一回合該處理什麼**失敗型態**（例如「訊號在週一開盤跳空時失效」）。不准建議參數數值。
4. **主持人**：對 accept/watch 候選重跑驗證者的關鍵證據。記錄到 `research/decisions.tsv`，更新 state.md，commit 並 push。

## 不准做的事
- 改門檻、改成本、改資料處理來讓候選通過
- 不經帳本就試策略（所有回測都要透過 research CLI，嘗試次數會自動累計）
- 實盤或模擬盤下單
