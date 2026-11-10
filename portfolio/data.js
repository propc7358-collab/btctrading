// 投資水位紀錄的資料檔。每次上傳截圖就在 records 新增一筆（一個帳戶一筆）。
// 格式說明見 repo 根目錄的 CLAUDE.md。
window.PORTFOLIO = {
  settings: {
    // 可投資總資金（TWD）。填了才算得出水位 = 已投入本金 ÷ 可投資總資金。
    budget: null
  },

  // 帳戶：使用者上傳截圖時說明是哪個帳戶
  accounts: [
    { id: 'A', name: '帳戶 A', note: '藍色介面 App，有 1 筆定期定額（尚未確認是哪一檔）' },
    { id: 'B', name: '帳戶 B', note: '綠色介面 App' }
  ],

  // 基金基本資料（類別用於配置比例）
  funds: {
    '施羅德台灣樂活中小基金-A類型': { category: '台股' },
    '安聯台灣科技基金':             { category: '台股' },
    '統一龍馬基金':                 { category: '台股' },
    '復華全球物聯網科技臺幣':       { category: '全球' },
    '復華全方位基金A類型':          { category: '台股' }
  },

  // 截圖紀錄（依日期排序）
  //   value = 截圖上的投資現值／參考現值
  //   cost  = 本金。截圖只給報酬率時，用 value ÷ (1 + 報酬率) 推算，並標 costDerived: true
  //   reported = 截圖上的帳戶合計，用來核對（頁面會在對不上時顯示警告）
  records: [
    {
      date: '2026-11-10',
      account: 'A',
      holdings: [
        { name: '施羅德台灣樂活中小基金-A類型', value: 215051, cost: 254000 },
        { name: '安聯台灣科技基金',             value: 166341, cost: 200000 },
        { name: '統一龍馬基金',                 value: 125992, cost: 150000 }
      ]
    },
    {
      date: '2026-11-10',
      account: 'B',
      reported: { value: 345772, cost: 446500 },
      holdings: [
        { name: '安聯台灣科技基金',       value: 223570, cost: 275000, navDate: '2026-11-09', costDerived: true },
        { name: '復華全球物聯網科技臺幣', value: 100388, cost: 147000, navDate: '2026-11-06', costDerived: true },
        { name: '復華全方位基金A類型',    value: 21814,  cost: 24500,  navDate: '2026-11-09', costDerived: true }
      ]
    }
  ]
};
