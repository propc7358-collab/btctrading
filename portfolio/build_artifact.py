"""把 index.html 轉成 claude.ai Artifact 用的頁面（去掉 doctype/html/head/body，發布時平台會自己包）。

用法：python3 portfolio/build_artifact.py <輸出資料夾>
輸出：<輸出資料夾>/index.html、data.js、prices.js、history.js
"""
import re, shutil, sys
from pathlib import Path

here = Path(__file__).parent
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
html = (here / 'index.html').read_text(encoding='utf-8')
for pat in [r'<!DOCTYPE html>\s*', r'<html[^>]*>\s*', r'</html>\s*', r'<head>\s*', r'</head>\s*',
            r'<body>\s*', r'</body>\s*', r'<meta charset="utf-8">\s*', r'<meta name="viewport"[^>]*>\s*']:
    html = re.sub(pat, '', html, flags=re.I)
(out / 'index.html').write_text(html, encoding='utf-8')
shutil.copy(here / 'data.js', out / 'data.js')
for extra in ('prices.js', 'history.js'):
    if (here / extra).exists():
        shutil.copy(here / extra, out / extra)
print(out / 'index.html')
