import requests
import subprocess
from datetime import datetime, timedelta
import os
import glob
import csv
import re

KEEP_DAYS = 12

# ---------- Weekday check ----------
today = datetime.now()
weekday = today.weekday()   # 0=Mon, 4=Fri, 5=Sat, 6=Sun

# Skip on Sunday
if weekday == 6:
    print(f"Skip: today is {today.strftime('%A')} (Sunday). No execution needed.")
    exit(0)

today_str = today.strftime("%Y%m%d")
url = "http://elefolo.com/NewChartList/getCodeGroup.php"

def fetch_codes_for_date(ymd):
    """Fetch 52-week-high stock codes for a specific YYYYMMDD date."""
    params = {
        "key": "w52Taka",
        "market": "",
        "ymd1": ymd,
        "ymd2": ymd,
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
        return []
    return data["codes"].split()

def extract_codes_from_csv(csv_path):
    """Read CSV and return set of stock codes."""
    codes = set()
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "code" in row and row["code"]:
                    codes.add(row["code"])
    except Exception as e:
        print(f"  Warning: failed to read {csv_path}: {e}")
    return codes

# ---------- Mode selection ----------
if weekday <= 4:
    # Monday-Friday: daily fetch (single day)
    print(f"Mode: daily ({today.strftime('%A')})")
    codes = fetch_codes_for_date(today_str)
    print(f"Target date: {today_str}")
    print(f"Number of stocks: {len(codes)}")
    
    if len(codes) == 0:
        raise RuntimeError("no stocks retrieved")

elif weekday == 5:
    # Saturday: union of this-week's existing daily files
    print(f"Mode: weekly union ({today.strftime('%A')})")
    
    # This week's Monday date
    this_monday = today - timedelta(days=5)   # Saturday minus 5 days = Monday
    
    all_files_in_week = []
    for offset in range(0, 5):  # Mon..Fri
        d = this_monday + timedelta(days=offset)
        ymd = d.strftime("%Y%m%d")
        path = f"52week_stock_data_{ymd}.csv"
        if os.path.exists(path):
            all_files_in_week.append(path)
    
    # If somehow the Saturday file already exists, skip it
    all_files_in_week = [f for f in all_files_in_week 
                          if os.path.basename(f) != f"52week_stock_data_{today_str}.csv"]
    
    print("Daily files this week (used for union):")
    all_codes = set()
    for path in all_files_in_week:
        codes_in_file = extract_codes_from_csv(path)
        all_codes.update(codes_in_file)
        print(f"  {os.path.basename(path)}: {len(codes_in_file)} codes")
    
    codes = sorted(all_codes)
    print(f"Week union date (Saturday): {today_str}")
    print(f"Total unique stocks across week: {len(codes)}")
    
    if len(codes) == 0:
        raise RuntimeError("no stocks retrieved across the week")

# ---------- Run download_prices.py with today's filename ----------
output_csv = f"52week_stock_data_{today_str}.csv"

cmd = [
    "python",
    "download_prices.py",
    "--codes",
    *codes,
    "--out",
    output_csv
]

subprocess.run(cmd, check=True)

# ---------- Delete CSVs older than KEEP_DAYS ----------
pattern = re.compile(r"52week_stock_data_(\d{8})\.csv$")
files = []
for f in glob.glob("52week_stock_data_*.csv"):
    m = pattern.match(os.path.basename(f))
    if m:
        files.append((f, m.group(1)))

files.sort(key=lambda x: x[1])

if len(files) > KEEP_DAYS:
    for old_file, _ in files[:-KEEP_DAYS]:
        print(f"[delete] {old_file}")
        os.remove(old_file)

print(f"[keep] {len(files)} files")
