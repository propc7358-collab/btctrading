---
name: research-round
description: 跑一輪多角色策略研究：資料稽核 → 研究員提案 → 回測與門檻 → 四個角色平行質詢 → 研究員辯護 → 主持人只採納有證據的結論並記錄。Use for /research-round, "找策略", "跑一輪研究".
---

# 研究回合

主持人是你（主 session）。你不提策略、不辯護，只負責流程與裁決。

## 步驟

1. **資料**：`uv run python -m quant.data.cli` 更新資料。派 `data-auditor` 做檢查。有 `BLOCKER` 就先修資料或排除標的，修完才往下。
2. **提案（可選）**：如果使用者要求新想法，派 `strategy-researcher` 新增策略。它新增的每組參數都會進帳本計數。
3. **回測與門檻**：`uv run python -m quant.research.cli`。讀 `research/reports/<run_id>.md`。程式門檻是硬性的，角色不能推翻 `REJECT`。
4. **質詢（平行）**：把所有 `ACCEPT` 與 `WATCH` 候選（若沒有，就取「最接近通過」的前 5 名）同時交給：
   - `overfit-skeptic`
   - `execution-realist`
   - `risk-manager`
   - `data-auditor`（只看與這些候選有關的資料問題）

   每個 brief 都要包含：使用者的目標（找可實際波段交易獲利的策略）、run_id、報告路徑、候選清單。
5. **辯護**：把質詢結果交給 `strategy-researcher`，它只能用指令輸出反駁。
6. **裁決**：逐條判斷。只採納「附指令與輸出、且你重跑得出相同結果」的發現。無證據的意見一律標記為未證實。
   - 任何 `KILL` 或 `UNTRADABLE` 成立 → 候選降為 `REJECT`
   - 通過全部門檻與質詢 → 進模擬盤清單，附風控官的部位與停用條件
   - `WATCH` 且通過質詢 → 進模擬盤做前向測試，不是實盤
7. **記錄**：
   - 每個裁決寫一行到 `research/decisions.tsv`：`date	run_id	candidate	verdict	evidence	decided_by`
   - 寫回合摘要 `research/rounds/<run_id>.md`
   - 如果質詢發現某類錯誤可以用程式擋住（例如新的資料檢查），在同一回合加上 check 或 test，並證明它會在這次的錯誤上失敗。這比寫進文件有用。

## 不准做的事
- 不准因為「沒有策略通過」而放寬 `quant/research/gates.py` 的門檻。改門檻要獨立一個 commit，附上用雜訊與正向對照組重新驗證的結果（`tests/test_pipeline.py` 必須仍然通過）。
- 不准實盤下單。實盤需要使用者明確授權，而且不在這個 skill 的範圍。

## 最後回覆使用者
先重述目標，然後：本回合候選數、各門檻通過數、角色質詢的關鍵發現（附證據）、最終清單（ACCEPT / 模擬盤前向測試 / 全部否決）、下一步。沒有找到就直接說沒有找到。
