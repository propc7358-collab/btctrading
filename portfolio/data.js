// 投資水位紀錄的資料檔。每次上傳截圖就在 records 新增一筆（一個帳戶一筆）。
// 格式說明見 repo 根目錄的 CLAUDE.md。
window.PORTFOLIO = {
  settings: {
    // 可投資總資金（TWD）。填了才算得出水位 = 已投入本金 ÷ 可投資總資金。
    budget: null
  },

  // 帳戶：使用者上傳截圖時說明是哪個帳戶
  accounts: [
    {
      id: 'A', name: 'LINE Bank 基金',
      // 定期定額設定（2026/11/10 截圖）
      plans: [
        { fund: '施羅德台灣樂活中小基金-A類型', frequency: '每週', day: '週一', amount: 1000,
          start: '2026-08-03', next: '2026-11-16', count: 14, status: '正常扣款', asOf: '2026-11-10' }
      ]
    },
    { id: 'B', name: '國泰銀行基金' },
    {
      id: 'C', name: '中國信託台股',
      note: '現值 = 投入成本 + 券商的投資損益（已扣除預估賣出手續費與證交稅），所以會比「股數 × 市價」略低'
    }
  ],

  // 標的基本資料：category 用於配置比例；cnyesId（鉅亨基金代碼）或 code（證券代號）用於每日抓價
  funds: {
    '施羅德台灣樂活中小基金-A類型': { category: '台股', type: '基金', cnyesId: 'A42010' },
    '安聯台灣科技基金':             { category: '台股', type: '基金', cnyesId: 'A36004' },
    '統一龍馬基金':                 { category: '台股', type: '基金', cnyesId: 'A09004' },
    '復華全球物聯網科技臺幣':       { category: '全球', type: '基金', cnyesId: 'A23065' },
    '復華全方位基金A類型':          { category: '台股', type: '基金', cnyesId: 'A23015' },
    // 中國信託台股（code = 證券代號）
    '群益臺灣加權正2':   { category: '台股', type: 'ETF', code: '00685L', note: '2 倍槓桿' },
    '兆豐台灣晶圓製造':  { category: '台股', type: 'ETF', code: '00913' },
    '野村臺灣新科技50':  { category: '台股', type: 'ETF', code: '00935' },
    '主動統一台股增長':  { category: '台股', type: 'ETF', code: '00981A' },
    '貝萊德世界股票':    { category: '全球', type: 'ETF', code: '009826' },
    '主動統一全球創新':  { category: '全球', type: 'ETF', code: '00988A' },
    '主動復華未來50':    { category: '台股', type: 'ETF', code: '00991A' },
    '台達電':            { category: '台股', type: '股票', code: '2308' },
    '台光電':            { category: '台股', type: '股票', code: '2383' },
    '聯發科':            { category: '台股', type: '股票', code: '2454' }
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
    },
    {
      date: '2026-11-10',
      account: 'C',
      // 截圖合計：市值 397,710（股數 × 市價），投資損益 −99,927
      reported: { pnl: -99927, marketValue: 397710 },
      holdings: [
        { name: '群益臺灣加權正2', shares: 8500, price: 9.85, cost: 108588, value: 83523 },
        { name: '兆豐台灣晶圓製造', shares: 100, price: 40.84, cost: 5020, value: 4060 },
        { name: '野村臺灣新科技50', shares: 50, price: 49.45, cost: 2934, value: 2450 },
        { name: '主動統一台股增長', shares: 400, price: 24.27, cost: 11944, value: 9679 },
        { name: '貝萊德世界股票', shares: 278, price: 10.11, cost: 2888, value: 2788 },
        { name: '主動統一全球創新', shares: 5872, price: 13.18, cost: 106124, value: 77205 },
        { name: '主動復華未來50', shares: 3449, price: 14.42, cost: 59697, value: 49615 },
        { name: '台達電', shares: 18, price: 1275, cost: 32372, value: 22850 },
        { name: '台光電', shares: 13, price: 4365, cost: 66999, value: 56495 },
        { name: '聯發科', shares: 23, price: 3830, cost: 99727, value: 87701 }
      ]
    }
  ]
};
