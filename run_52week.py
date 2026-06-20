import requests
import subprocess
from datetime import datetime, timedelta
import os
import glob
import re

KEEP_DAYS = 7  # 保持日数

# ---------- 対象日計算（土日なら直近営業日） ----------
today = datetime.now()

if today.weekday() == 5:  # 土曜日
    target = today - timedelta(days=1)

elif today.weekday() == 6:  # 日曜日
    target = today - timedelta(days=2)

else:
    target = today

target_date = target.strftime("%Y%m%d")

# ---------- 52週高値銘柄取得（Elefolo API） ----------
url = "http://elefolo.com/NewChartList/getCodeGroup.php"

params = {
    "key": "w52Taka",
    "market": "",
    "ymd1": target_date,
    "ymd2": target_date,
    "minDekidakaSuu": "10000",
    "minDekidakaRitu": "3",
    "minBaibaiDaikinCur": "100",
    "minBaibaiDaikinPrev": "100",
    "pass": ""
}

r = requests.get(url, params=params, timeout=30)
r.raise_for_status()

data = r.json()

if data.get("success") != 1:
    raise RuntimeError("52week high stock list fetch failed")

codes = data["codes"].split()

if len(codes) == 0:
    raise RuntimeError("no stocks retrieved")

print(f"Target date: {target_date}")
print(f"Number of stocks: {len(codes)}")

# ---------- download_prices.py 実行（日付付きファイル名） ----------
cmd = [
    "python",
    "download_prices.py",
    "--codes",
    *codes,
    "--out",
    f"52week_stock_data_{target_date}.csv"
]

subprocess.run(cmd, check=True)

# ---------- 古いファイル削除（7日分のみ保持） ----------
pattern = re.compile(r"52week_stock_data_(\d{8})\.csv$")
files = []
for f in glob.glob("52week_stock_data_*.csv"):
    m = pattern.match(os.path.basename(f))
    if m:
        files.append((f, m.group(1)))

# 日付順に並べ替え（古い順）
files.sort(key=lambda x: x[1])

# KEEP_DAYS を超える古いものを削除
if len(files) > KEEP_DAYS:
    for old_file, _ in files[:-KEEP_DAYS]:
        print(f"[delete] {old_file}")
        os.remove(old_file)

print(f"[keep] {len(files)} files")
