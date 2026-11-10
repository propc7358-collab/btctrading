# 投資水位紀錄：用截圖更新的流程

使用者會上傳基金 App 的截圖，並說明是哪個帳戶。請依下面步驟更新 `portfolio/data.js`，`portfolio/index.html` 會自動讀取它。頁面本身不用改。

## 每次收到截圖

1. **確認帳戶**：在 `accounts` 找使用者說的帳戶。
   - 使用者給的名字對應到 `帳戶 A`、`帳戶 B` 這類暫名時，直接改 `name`，`id` 不要動。
   - 是新帳戶就新增一筆，`id` 用簡短英文。
2. **新增一筆 `records`**：每個帳戶、每次上傳一筆，放在陣列最後，並按日期排序。
   - `date`：截圖日期，預設用今天，使用者另外說明就照他說的。
   - `account`：帳戶 id。
   - `holdings`：截圖上的每一檔基金。
     - `name`：基金名稱，和既有紀錄**完全一致**，這樣才能接上前一次的紀錄。
     - `value`：投資現值／參考現值。
     - `cost`：本金。
       - 截圖只有報酬率時，用 `round(value / (1 + 報酬率))` 推算，並加上 `costDerived: true`。
       - 如果截圖有帳戶的本金合計，推算結果要對得上那個合計。
     - `navDate`：有淨值日就填。
     - `dca: true`：使用者說明是定期定額才加。
   - `reported`：截圖上有帳戶合計（現值、本金）時填入，頁面會自動核對。
3. **新基金**：在 `funds` 補上 `category`（台股／全球／債券……）。
4. **其他設定**：使用者說了可投資總資金，就填 `settings.budget`。
5. **檢查**：
   - `node -e "global.window={};require('./portfolio/data.js');console.log('ok')"` 能執行。
   - 合計和截圖一致。
6. **commit 並 push。**
7. **重新發布 claude.ai 網頁**（網址不變）：
   - 先執行 `python3 portfolio/build_artifact.py <scratchpad>/artifact`。
   - 再用 Artifact 工具 publish：
     - `file_path` 是 `<scratchpad>/artifact/index.html`
     - `files` 是 `{"data.js": "<scratchpad>/artifact/data.js"}`
   - 不同的對話裡要另外帶 `url: https://claude.ai/artifact/Dwqpy3WYGDKyEPf5ScjntG`，並且先用 `action: "read"` 讀一次。

## 回報給使用者

用一段話說明下面幾件事：

- 這次各帳戶的現值、損益和報酬率。
- 和上次相比，持股有沒有變動：
  - 本金都沒變：寫「無變動，純淨值變化 X」。
  - 有變動：列出新增、加碼、減碼、出清。
- 扣掉加碼或減碼之後的淨值變動金額和 %。計算方式：
  - 淨值變動 = 本次現值 − 上次現值 − 本金變化
  - 淨值變動率 = 淨值變動 ÷ 上次現值
- 截圖看不清、或本金是推算出來的地方，要明白說。

## 帳戶對照

- `A` = LINE Bank 基金
- `B` = 國泰銀行基金

## 定期定額

- 定期定額設定寫在 `accounts[].plans`，包含：
  - `fund`、`frequency`、`day`、`amount`
  - `start`、`next`、`count`、`status`、`asOf`
- 收到定期定額頁面的截圖時，更新對應那一筆。
- 有定期定額的基金本金增加時，頁面會標成「定期定額」，不會標成「加碼」。
- 回報時核對本金增加的金額是否接近「扣款次數 × 金額」。
- 目前的設定：
  - LINE Bank：施羅德台灣樂活中小基金-A類型，每週一扣 1,000。

## 注意

- **不要記錄使用者的個人資料**：
  - 截圖上出現的姓名、身分證字號、銀行帳號、電話、Email 都不要寫進資料檔、commit 訊息或網頁。
  - 帳戶一律用帳戶代號（`A`、`B`）和帳戶名稱（例如「LINE Bank 基金」）。

- 損益用台灣慣例：紅色是賺，綠色是賠。
- 不要刪除或修改舊紀錄，它們是走勢和淨值追蹤的歷史。除非使用者說哪一筆有錯。
- 某天只更新了部分帳戶時，其他帳戶自動沿用各自最近一次的截圖，不用複製舊資料。
