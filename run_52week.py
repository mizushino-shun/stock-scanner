import requests
import subprocess
from datetime import datetime, timedelta
import os
import glob
import re

KEEP_DAYS = 10  # KEEP LAST 10 DAYS

# ---------- Weekday check ----------
# Stock prices only update Mon-Fri, so skip weekends.
today = datetime.now()
weekday = today.weekday()   # 0=Mon, ..., 5=Sat, 6=Sun

if weekday >= 5:
    print(f"Skip: today is {today.strftime('%A')} (weekend). No execution needed.")
    exit(0)

target_date = today.strftime("%Y%m%d")

# ---------- Fetch stocks list from Elefolo API ----------
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
    raise RuntimeError("52week fetch failed")

codes = data["codes"].split()

if len(codes) == 0:
    raise RuntimeError("no stocks retrieved")

print(f"Target date: {target_date}")
print(f"Number of stocks: {len(codes)}")

# ---------- Run download_prices.py with date-suffixed filename ----------
cmd = [
    "python",
    "download_prices.py",
    "--codes",
    *codes,
    "--out",
    f"52week_stock_data_{target_date}.csv"
]

subprocess.run(cmd, check=True)

# ---------- Delete CSVs older than KEEP_DAYS ----------
pattern = re.compile(r"52week_stock_data_(\d{8})\.csv$")
files = []
for f in glob.glob("52week_stock_data_*.csv"):
    m = pattern.match(os.path.basename(f))
    if m:
        files.append((f, m.group(1)))

# Sort by date (oldest first)
files.sort(key=lambda x: x[1])

# Remove old files beyond KEEP_DAYS
if len(files) > KEEP_DAYS:
    for old_file, _ in files[:-KEEP_DAYS]:
        print(f"[delete] {old_file}")
        os.remove(old_file)

print(f"[keep] {len(files)} files")
