import requests
import subprocess
from datetime import datetime, timedelta
import os
import glob
import csv
import re
import sys

KEEP_DAYS = 12

URL = "http://elefolo.com/NewChartList/getCodeGroup.php"


def fetch_codes_for_date(ymd):
    """Elefolo APIから指定日(YYYYMMDD)の52週高値銘柄コード一覧を取得"""
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

    r = requests.get(URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    if data.get("success") != 1:
        return []

    codes_str = data.get("codes", "").strip()
    if not codes_str:
        return []

    return codes_str.split()


def extract_codes_from_csv(csv_path):
    """download_prices.py が出力したCSVから code 列を読み、銘柄コード集合を返す"""
    codes = set()

    try:
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = (row.get("code") or "").strip()
                if code:
                    codes.add(code)
    except Exception as e:
        print(f"Warning: failed to read {csv_path}: {e}")

    return codes


def write_empty_csv(path):
    """銘柄0件の日用の空CSVを出力"""
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("code,date,close\n")


def cleanup_old_csvs():
    """日付付きCSVを新しい順に KEEP_DAYS 件だけ残す"""
    pattern = re.compile(r"^52week_stock_data_(\d{8})\.csv$")
    files = []

    for f in glob.glob("52week_stock_data_*.csv"):
        name = os.path.basename(f)
        m = pattern.match(name)
        if m:
            files.append((f, m.group(1)))

    files.sort(key=lambda x: x[1])  # 古い順

    if len(files) > KEEP_DAYS:
        for old_file, _ in files[:-KEEP_DAYS]:
            print(f"[delete] {old_file}")
            os.remove(old_file)

    print(f"[keep] {min(len(files), KEEP_DAYS)} files")


def run_download_prices(codes, output_csv):
    """download_prices.py を呼び出して株価CSVを生成"""
    cmd = [
        "python",
        "download_prices.py",
        "--codes",
        *codes,
        "--out",
        output_csv
    ]
    subprocess.run(cmd, check=True)


def main():
    today = datetime.now()
    weekday = today.weekday()  # 0=Mon, ..., 5=Sat, 6=Sun
    today_str = today.strftime("%Y%m%d")
    output_csv = f"52week_stock_data_{today_str}.csv"

    # 日曜は何もしない
    if weekday == 6:
        print(f"Skip: today is {today.strftime('%A')} (Sunday). No execution needed.")
        sys.exit(0)

    # 月〜金: 当日分を取得
    if weekday <= 4:
        print(f"Mode: daily ({today.strftime('%A')})")

        codes = fetch_codes_for_date(today_str)

        print(f"Target date: {today_str}")
        print(f"Number of stocks: {len(codes)}")

        if len(codes) == 0:
            print("No stocks retrieved. Creating empty CSV.")
            write_empty_csv(output_csv)
        else:
            run_download_prices(codes, output_csv)

    # 土曜: 今週の既存ファイル（月〜金）から union を作る
    elif weekday == 5:
        print("Mode: weekly union (Saturday)")

        this_monday = today - timedelta(days=5)  # 土曜 - 5日 = 月曜
        all_files_in_week = []

        for offset in range(5):  # Mon..Fri
            d = this_monday + timedelta(days=offset)
            ymd = d.strftime("%Y%m%d")
            path = f"52week_stock_data_{ymd}.csv"
            if os.path.exists(path):
                all_files_in_week.append(path)

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
            print("No stocks retrieved across the week. Creating empty CSV.")
            write_empty_csv(output_csv)
        else:
            run_download_prices(codes, output_csv)

    cleanup_old_csvs()


if __name__ == "__main__":
    main()
