import requests
import subprocess
from datetime import datetime, timedelta

today = datetime.now()

if today.weekday() == 5:  # 土曜
    target = today - timedelta(days=1)

elif today.weekday() == 6:  # 日曜
    target = today - timedelta(days=2)

else:
    target = today

target_date = target.strftime("%Y%m%d")

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
    raise RuntimeError("52週高値銘柄の取得に失敗")

codes = data["codes"].split()

if len(codes) == 0:
    raise RuntimeError("取得銘柄が0件です")

print(f"対象日: {target_date}")
print(f"取得銘柄数: {len(codes)}")

cmd = [
    "python",
    "download_prices.py",
    "--codes",
    *codes,
    "--out",
    "52week_stock_data.csv"
]

subprocess.run(cmd, check=True)