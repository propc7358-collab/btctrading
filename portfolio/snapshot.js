// 每日紀錄：用無頭瀏覽器打開 index.html，讀出頁面算好的合計，寫進 history.js。
// 用法：node portfolio/snapshot.js [YYYY-MM-DD]
//   不給日期時，用「台北時間現在減 1 小時」的日期：22:00 執行記成當天，00:00 執行記成剛結束的前一天。
// 同一天重跑會覆蓋那一天。
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const dir = __dirname;
const out = path.join(dir, 'history.js');

function taipeiDate(offsetHours) {
  const t = new Date(Date.now() + (8 + offsetHours) * 3600 * 1000);
  return t.toISOString().slice(0, 10);
}

(async () => {
  const date = process.argv[2] || taipeiDate(-1);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('file://' + path.join(dir, 'index.html'));
  const s = await page.evaluate(() => window.PORTFOLIO_SUMMARY);
  await browser.close();
  if (!s || errors.length) {
    console.error('頁面計算失敗：', errors.join('; ') || '沒有 PORTFOLIO_SUMMARY');
    process.exit(1);
  }

  let hist = [];
  if (fs.existsSync(out)) {
    global.window = {};
    require(out);
    hist = global.window.HISTORY || [];
  }
  const entry = {
    date, recordedAt: new Date().toISOString(), priceDate: s.priceDate,
    value: s.value, cost: s.cost, loans: s.loans,
    accounts: Object.fromEntries(s.accounts.map((a) => [a.id, a.value]))
  };
  hist = hist.filter((h) => h.date !== date).concat(entry).sort((a, b) => a.date.localeCompare(b.date));
  const body = '// 每日紀錄（每天午夜 12 點由 portfolio/snapshot.js 寫入），不要手動編輯。\n'
    + 'window.HISTORY = [\n' + hist.map((h) => '  ' + JSON.stringify(h)).join(',\n') + '\n];\n';
  fs.writeFileSync(out, body);
  const prev = hist[hist.findIndex((h) => h.date === date) - 1];
  const dv = prev ? entry.value - prev.value : null;
  console.log(`${date} 總現值 ${entry.value.toLocaleString()}、淨資產 ${(entry.value - entry.loans).toLocaleString()}`
    + (dv == null ? '（第一筆）' : `、較前一天 ${dv >= 0 ? '+' : ''}${dv.toLocaleString()}`) + `，價格日 ${s.priceDate}`);
})();
