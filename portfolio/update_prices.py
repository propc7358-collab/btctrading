"""抓每日淨值／收盤價，寫進 portfolio/prices.js（保留歷史）。

用法：python3 portfolio/update_prices.py
- 基金：用 data.js 裡 funds[名稱].cnyesId 到鉅亨（fund.api.cnyes.com）抓淨值歷史。
- 股票／ETF：用 funds[名稱].code 到證交所（openapi.twse.com.tw）抓最新收盤價；查不到再找櫃買中心（www.tpex.org.tw）。
- 美股（funds[名稱].currency == 'USD'）：到 Yahoo Finance（query1.finance.yahoo.com）抓美元收盤價與 USD/TWD 匯率，
  寫成「台幣價格 = 美元收盤 × 當天匯率」放在該標的名稱下；原始資料另存 'USD:代號' 與 'FX:USDTWD'。
- 截圖上的股價（records 裡有 shares 與 price 的持有）也會寫進歷史，當作該日收盤價。
結束時印出這次新增的價格筆數；沒有新資料時檔案不會變。
"""
import datetime as dt
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / 'data.js'
OUT = HERE / 'prices.js'
TZ = dt.timezone(dt.timedelta(hours=8))
HEADERS = {'User-Agent': 'Mozilla/5.0 (portfolio tracker)', 'Accept': 'application/json'}


def load_data():
    js = "global.window={};require(process.argv[1]);process.stdout.write(JSON.stringify(window.PORTFOLIO))"
    return json.loads(subprocess.check_output(['node', '-e', js, str(DATA)]))


def load_prices():
    if not OUT.exists():
        return {}
    js = "global.window={};require(process.argv[1]);process.stdout.write(JSON.stringify(window.PRICES||{}))"
    return json.loads(subprocess.check_output(['node', '-e', js, str(OUT)])).get('series', {})


def get_json(url, timeout=120):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def roc_to_iso(s):
    s = s.strip()
    y, m, d = int(s[:-4]) + 1911, int(s[-4:-2]), int(s[-2:])
    return f'{y:04d}-{m:02d}-{d:02d}'


def num(s):
    try:
        return float(str(s).replace(',', ''))
    except ValueError:
        return None


def fetch_fund_navs(cnyes_id):
    url = f'https://fund.api.cnyes.com/fund/api/v1/funds/{urllib.parse.quote(cnyes_id)}/nav?format=table&page=1'
    rows = get_json(url)['items']['data']
    out = {}
    for r in rows:
        d = dt.datetime.fromtimestamp(r['tradeDate'], TZ).date().isoformat()
        if r.get('nav') is not None:
            out[d] = float(r['nav'])
    return out


def fetch_yahoo(symbol):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range=1mo&interval=1d'
    res = get_json(url)['chart']['result'][0]
    off = res['meta'].get('gmtoffset', 0)
    closes = res['indicators']['quote'][0]['close']
    out = {}
    for t, c in zip(res.get('timestamp', []), closes):
        if c is not None and c > 0:  # Yahoo 對停牌／下市標的會給 0
            out[dt.datetime.fromtimestamp(t + off, dt.timezone.utc).date().isoformat()] = round(float(c), 4)
    return out


def main():
    data = load_data()
    series = {k: {d: round(float(x), 4) for d, x in v} for k, v in load_prices().items()}
    added = 0
    errors = []

    def put(name, date, price):
        nonlocal added
        if price is None:
            return
        s = series.setdefault(name, {})
        if date not in s:
            added += 1
        s[date] = round(float(price), 4)

    # 截圖上的股價
    for rec in data.get('records', []):
        for h in rec.get('holdings', []):
            if h.get('shares') and h.get('price'):
                series.setdefault(h['name'], {}).setdefault(rec['date'], float(h['price']))

    funds = data.get('funds', {})
    held = {h['name'] for r in data.get('records', []) for h in r.get('holdings', [])}

    # 基金淨值
    for name in sorted(held):
        meta = funds.get(name, {})
        if meta.get('cnyesId'):
            try:
                for d, v in fetch_fund_navs(meta['cnyesId']).items():
                    put(name, d, v)
            except Exception as e:  # noqa: BLE001
                errors.append(f'{name}（{meta["cnyesId"]}）：{e}')

    # 股票／ETF 收盤價
    codes = {funds[n]['code']: n for n in held if funds.get(n, {}).get('code') and funds[n].get('currency') != 'USD'}
    if codes:
        found = set()
        try:
            for r in get_json('https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL'):
                if r.get('Code') in codes:
                    put(codes[r['Code']], roc_to_iso(r['Date']), num(r.get('ClosingPrice')))
                    found.add(r['Code'])
        except Exception as e:  # noqa: BLE001
            errors.append(f'證交所：{e}')
        missing = set(codes) - found
        if missing:
            try:
                for r in get_json('https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes'):
                    c = r.get('SecuritiesCompanyCode')
                    if c in missing:
                        put(codes[c], roc_to_iso(r['Date']), num(r.get('Close')))
                        found.add(c)
            except Exception as e:  # noqa: BLE001
                errors.append(f'櫃買中心：{e}')
        for c in sorted(set(codes) - found):
            errors.append(f'{codes[c]}（{c}）：證交所與櫃買中心都查不到')

    # 美股：美元收盤 × 匯率
    usd = {n: funds[n]['code'] for n in held if funds.get(n, {}).get('currency') == 'USD' and funds[n].get('code')}
    if usd:
        try:
            for d, v in fetch_yahoo('TWD=X').items():
                put('FX:USDTWD', d, v)
        except Exception as e:  # noqa: BLE001
            errors.append(f'USD/TWD 匯率：{e}')
        fx = sorted(series.get('FX:USDTWD', {}).items())
        for name, code in sorted(usd.items()):
            try:
                for d, v in fetch_yahoo(code).items():
                    put('USD:' + code, d, v)
                    rate = [r for fd, r in fx if fd <= d]
                    if rate:
                        put(name, d, round(v * rate[-1], 4))
            except Exception as e:  # noqa: BLE001
                errors.append(f'{name}（{code}）：{e}')

    # 只保留第一筆截圖前 30 天以後的資料
    first = min((r['date'] for r in data.get('records', [])), default=None)
    cutoff = (dt.date.fromisoformat(first) - dt.timedelta(days=30)).isoformat() if first else None

    lines = []
    latest = None
    for name in sorted(series):
        pts = sorted((d, v) for d, v in series[name].items() if not cutoff or d >= cutoff)
        if not pts:
            continue
        latest = max(latest or pts[-1][0], pts[-1][0])
        lines.append('    ' + json.dumps(name, ensure_ascii=False) + ': ' + json.dumps([[d, v] for d, v in pts]))

    body = (
        '// 每日淨值／收盤價，由 portfolio/update_prices.py 產生，不要手動編輯。\n'
        'window.PRICES = {\n'
        f'  latest: {json.dumps(latest)},\n'
        '  series: {\n' + ',\n'.join(lines) + '\n  }\n'
        '};\n'
    )
    old = OUT.read_text(encoding='utf-8') if OUT.exists() else ''
    if body != old:
        OUT.write_text(body, encoding='utf-8')
    print(f'新增 {added} 筆價格，最新價格日 {latest}，檔案{"已更新" if body != old else "沒有變動"}')
    for e in errors:
        print('⚠', e, file=sys.stderr)
    return 1 if errors and not added else 0


if __name__ == '__main__':
    sys.exit(main())
