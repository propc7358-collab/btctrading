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
    },
    {
      id: 'D', name: '國泰台股',
      note: '截圖只有股數與總損益（含息）；本金 = 損益 ÷ 報酬率 推算，現值 = 本金 + 損益'
    },
    {
      id: 'E', name: '國泰美股（台幣）',
      note: '複委託台幣交割；金額都是台幣。本金由損益 ÷ 報酬率推算（SpaceX 用總成本扣掉其他檔）'
    },
    {
      id: 'F', name: '國泰美股（美金）',
      note: '複委託美金交割；截圖金額是美元，依 2026/11/10 匯率 32.907 換成台幣（原始美元金額保留在 costUSD／valueUSD）'
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
    '聯發科':            { category: '台股', type: '股票', code: '2454' },
    // 國泰美股（currency: 'USD'，每日估算用美元收盤價 × 匯率）
    'Applied Optoelectronics': { category: '美股', type: '股票', code: 'AAOI', currency: 'USD' },
    'Broadcom': { category: '美股', type: '股票', code: 'AVGO', currency: 'USD' },
    'Alphabet C': { category: '美股', type: '股票', code: 'GOOG', currency: 'USD' },
    'Rocket Lab': { category: '美股', type: '股票', code: 'RKLB', currency: 'USD' },
    'VanEck 半導體 ETF': { category: '美股', type: 'ETF', code: 'SMH', currency: 'USD' },
    'SpaceX': { category: '美股', type: '股票', code: 'SPCX', currency: 'USD' },
    'Roundhill Memory ETF': { category: '美股', type: 'ETF', code: 'DRAM', currency: 'USD' },
    'VanEck 金礦 ETF': { category: '美股', type: 'ETF', code: 'GDX', currency: 'USD' },
    'Alphabet A': { category: '美股', type: '股票', code: 'GOOGL', currency: 'USD' },
    'iShares 軟體 ETF': { category: '美股', type: 'ETF', code: 'IGV', currency: 'USD' },
    'Tema 太空 ETF': { category: '美股', type: 'ETF', code: 'NASA', currency: 'USD' },
    // 國泰台股新增
    '主動安聯亞半導體': { category: '亞洲', type: 'ETF', code: '00412A' },
    '元大MSCI金融': { category: '台股', type: 'ETF', code: '0055' },
    '富邦臺灣中小': { category: '台股', type: 'ETF', code: '00733' },
    '統一FANG+': { category: '美股', type: 'ETF', code: '00757' },
    '國泰網路資安': { category: '全球', type: 'ETF', code: '00875' },
    '中信關鍵半導體': { category: '台股', type: 'ETF', code: '00891' },
    '第一金太空衛星': { category: '全球', type: 'ETF', code: '00910' },
    '中信台日韓PCB': { category: '亞洲', type: 'ETF', code: '009828' },
    '主動野村台灣50': { category: '台股', type: 'ETF', code: '00985A' },
    '大立光': { category: '台股', type: '股票', code: '3008' },
    '日月光投控': { category: '台股', type: '股票', code: '3711' }
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
    },
    {
      date: '2026-11-10',
      account: 'D',
      // 截圖：庫存股數、總損益（含息）與報酬率；標「定額」的是定期定額買股
      holdings: [
        { name: '主動安聯亞半導體', shares: 23000, cost: 211661, value: 178409, pnl: -33252, rate: -15.71, costDerived: true },
        { name: '元大MSCI金融', shares: 59, cost: 2982, value: 2948, pnl: -34, rate: -1.14, costDerived: true, dca: true },
        { name: '群益臺灣加權正2', shares: 95000, cost: 1183481, value: 934595, pnl: -248886, rate: -21.03, costDerived: true },
        { name: '富邦臺灣中小', shares: 3000, cost: 231493, value: 183412, pnl: -48081, rate: -20.77, costDerived: true },
        { name: '統一FANG+', shares: 50, cost: 6544, value: 6722, pnl: 178, rate: 2.72, costDerived: true },
        { name: '國泰網路資安', shares: 100, cost: 5681, value: 5802, pnl: 121, rate: 2.13, costDerived: true },
        { name: '中信關鍵半導體', shares: 14000, cost: 504283, value: 442004, pnl: -62279, rate: -12.35, costDerived: true },
        { name: '第一金太空衛星', shares: 2700, cost: 186811, value: 145750, pnl: -41061, rate: -21.98, costDerived: true, dca: true },
        { name: '主動統一台股增長', shares: 1000, cost: 26252, value: 24249, pnl: -2003, rate: -7.63, costDerived: true },
        { name: '中信台日韓PCB', shares: 20000, cost: 204034, value: 157555, pnl: -46479, rate: -22.78, costDerived: true },
        { name: '主動野村台灣50', shares: 16000, cost: 371839, value: 331197, pnl: -40642, rate: -10.93, costDerived: true },
        { name: '主動復華未來50', shares: 24000, cost: 420506, value: 345698, pnl: -74808, rate: -17.79, costDerived: true },
        { name: '台達電', shares: 55, cost: 106246, value: 70048, pnl: -36198, rate: -34.07, costDerived: true },
        { name: '台光電', shares: 25, cost: 130645, value: 108775, pnl: -21870, rate: -16.74, costDerived: true, dca: true },
        { name: '聯發科', shares: 61, cost: 275259, value: 233282, pnl: -41977, rate: -15.25, costDerived: true, dca: true },
        { name: '大立光', shares: 6, cost: 37590, value: 30290, pnl: -7300, rate: -19.42, costDerived: true },
        { name: '日月光投控', shares: 30, cost: 20646, value: 18090, pnl: -2556, rate: -12.38, costDerived: true }
      ]
    },
    {
      date: '2026-11-10',
      account: 'E',
      // 截圖：總預估現值 673,753、總成本 787,600、總預估損益 −113,847（台幣）
      reported: { value: 673753, cost: 787600, pnl: -113847 },
      holdings: [
        { name: 'Applied Optoelectronics', shares: 1, avgUSD: 79.99, cost: 2615, value: 1688, pnl: -927, rate: -35.45, costDerived: true },
        { name: 'Broadcom', shares: 1.26654, avgUSD: 344.355488, cost: 14072, value: 13253, pnl: -819, rate: -5.82, costDerived: true, dca: true },
        { name: 'Alphabet C', shares: 30, avgUSD: 357.171333, cost: 344120, value: 283142, pnl: -60978, rate: -17.72, costDerived: true },
        { name: 'Rocket Lab', shares: 32, avgUSD: 92.883438, cost: 94785, value: 58378, pnl: -36407, rate: -38.41, costDerived: true },
        { name: 'VanEck 半導體 ETF', shares: 7.66629, avgUSD: 552.938905, cost: 136808, value: 122320, pnl: -14488, rate: -10.59, costDerived: true, dca: true },
        { name: 'SpaceX', shares: 42, avgUSD: 145.006429, cost: 195200, value: 194972, pnl: -228, rate: -0.12, costDerived: true }
      ]
    },
    {
      date: '2026-11-10',
      account: 'F',
      fx: 32.907,
      // 截圖（美元）：總預估現值 16,157.73、總成本 21,114.67、總預估損益 −4,956.94
      reportedUSD: { value: 16157.73, cost: 21114.67, pnl: -4956.94 },
      holdings: [
        { name: 'Roundhill Memory ETF', shares: 49, avgUSD: 69.120408, costUSD: 3386.9, valueUSD: 2025.17, cost: 111453, value: 66642 },
        { name: 'VanEck 金礦 ETF', shares: 25, avgUSD: 115.4248, costUSD: 2885.62, valueUSD: 2237.5, cost: 94957, value: 73629 },
        { name: 'Alphabet A', shares: 10, avgUSD: 336.097, costUSD: 3360.97, valueUSD: 2903.5, cost: 110599, value: 95545 },
        { name: 'iShares 軟體 ETF', shares: 5, avgUSD: 101.24, costUSD: 506.2, valueUSD: 505.3, cost: 16658, value: 16628 },
        { name: 'Tema 太空 ETF', shares: 100, avgUSD: 33.9105, costUSD: 3391.05, valueUSD: 2094.0, cost: 111589, value: 68907 },
        { name: 'VanEck 半導體 ETF', shares: 13.14333, avgUSD: 577.017392, costUSD: 7583.93, valueUSD: 6392.26, cost: 249564, value: 210350, dca: true }
      ]
    }
  ]
};
