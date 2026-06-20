#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
download_prices.py
==================
Kabutan新高値 × RS スクリーナー用
週足価格CSV ダウンローダー（Yahoo Finance経由）

■ 出力フォーマット（アプリが読み込める形式）
  code,date,close
  7203,2025-04-28,2697.7
  7203,2025-05-05,2638.9
  ...

■ 使い方
  1. 必要ライブラリをインストール:
       pip install yfinance pandas openpyxl

  2. 銘柄コードの指定方法（いずれか）:
       A. Excelファイル（.xlsx）を --excel で指定（推奨）
            A列・A2セル以降に銘柄コードが記載されている想定
       B. テキストファイルを --file で指定（1行1コード）
       C. コマンドラインで --codes 7203 9984 6758
       D. スクリプト内の CODES リストに直接書く

  3. 実行例:
       python download_prices.py
       python download_prices.py --excel "C:\\Users\\linmu\\codes.xlsx"
       python download_prices.py --codes 7203 9984 6758

■ 注意
  ・東証銘柄コードは ".T" を自動付与して Yahoo Finance に問い合わせます
  ・週足データは月曜始まり（その週の月曜日の日付）で返ってきます
  ・--weeks で取得週数を指定（デフォルト 52週＝約1年）
  ・最低 13週分のデータが必要です（13週MA計算のため）
  ・Yahoo Finance の仕様変更でエラーになる場合は yfinance を更新してください:
       pip install --upgrade yfinance
  ・Excelファイル読込には openpyxl が必要です:
       pip install openpyxl
"""

import argparse
import sys
import time
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    print("[エラー] yfinance がインストールされていません。")
    print("         pip install yfinance  を実行してください。")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("[エラー] pandas がインストールされていません。")
    print("         pip install pandas  を実行してください。")
    sys.exit(1)

try:
    import openpyxl  # noqa: F401
    _OPENPYXL_OK = True
except ImportError:
    _OPENPYXL_OK = False


# ============================================================
#  デフォルト Excel ファイルパス
#  --excel オプションを省略したときに読み込まれます。
# ============================================================
DEFAULT_EXCEL_PATH = r"C:\Users\linmu\codes.xlsx"

EXCEL_COL_INDEX  = 0   # A列
EXCEL_START_ROW  = 1   # 0始まりで 1 = 2行目（A2）

CODES = []

DEFAULT_WEEKS = 52
SLEEP_BETWEEN = 0.5


def parse_args():
    p = argparse.ArgumentParser(description="Yahoo Financeから週足価格CSVをダウンロードします")
    p.add_argument("--excel", "-e", metavar="XLSX",
                   help="銘柄コードが入ったExcelファイル(.xlsx)のパス。A列・A2セル以降を読み込みます。")
    p.add_argument("--sheet", metavar="SHEET", default=None, help="読み込むシート名（省略時は先頭シート）")
    p.add_argument("--col",      type=int, default=EXCEL_COL_INDEX, metavar="N",
                   help="コードが入っている列番号（0=A列, 1=B列 …）")
    p.add_argument("--startrow", type=int, default=EXCEL_START_ROW, metavar="N",
                   help="読み込み開始行（0始まり。デフォルト: 1 = 2行目）")
    p.add_argument("--codes", "-c", nargs="+", metavar="CODE",
                   help="銘柄コード（スペース区切り）例: --codes 7203 9984 6758")
    p.add_argument("--file",  "-f", metavar="FILE",
                   help="銘柄コード一覧テキストファイル（1行1コード）")
    p.add_argument("--weeks", "-w", type=int, default=DEFAULT_WEEKS, metavar="N",
                   help=f"取得週数（デフォルト: {DEFAULT_WEEKS}）最低13以上を推奨")
    p.add_argument("--out",   "-o", default="stock_data.csv", metavar="FILE",
                   help="出力CSVファイル名（デフォルト: stock_data.csv）")
    p.add_argument("--no-round",  action="store_true",
                   help="終値を丸めずそのまま出力する（デフォルトは小数点以下2桁）")
    p.add_argument("--no-excel",  action="store_true",
                   help="DEFAULT_EXCEL_PATHの自動読み込みを無効にする")
    return p.parse_args()


def load_codes_from_excel(path, sheet, col, startrow):
    if not _OPENPYXL_OK:
        print("[エラー] openpyxl がインストールされていません。")
        print("         pip install openpyxl  を実行してください。")
        sys.exit(1)
    p = Path(path)
    if not p.exists():
        print(f"[エラー] Excelファイルが見つかりません: {path}")
        sys.exit(1)
    try:
        df = pd.read_excel(p, header=None, sheet_name=sheet if sheet else 0)
    except Exception as e:
        print(f"[エラー] Excelファイルの読み込みに失敗しました: {e}")
        sys.exit(1)
    if col >= len(df.columns):
        print(f"[エラー] 指定列({col})がExcelの列数({len(df.columns)})を超えています。")
        sys.exit(1)
    codes = []
    for raw in df.iloc[startrow:, col]:
        if pd.isna(raw) or str(raw).strip() == "":
            continue
        val = str(raw).strip()
        if "." in val:
            try:
                val = str(int(float(val)))
            except ValueError:
                pass
        val = val.upper().replace(".T", "").replace(".JP", "")
        if val and val[0].isdigit():
            codes.append(val)
    return codes


def load_codes_from_file(path):
    codes = []
    p = Path(path)
    if not p.exists():
        print(f"[エラー] ファイルが見つかりません: {path}")
        sys.exit(1)
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            for part in line.replace(",", " ").split():
                part = part.strip().upper().replace(".T", "").replace(".JP", "")
                if part and part[0].isdigit():
                    codes.append(part)
    return codes


def fetch_weekly_prices(code, weeks):
    ticker_symbol = f"{code}.T"
    try:
        ticker = yf.Ticker(ticker_symbol)
        if weeks <= 52:
            period = "1y"
        elif weeks <= 104:
            period = "2y"
        else:
            period = "5y"
        df = ticker.history(period=period, interval="1wk", auto_adjust=True)
        if df is None or df.empty:
            print(f"  [警告] {code}: データなし（上場廃止・コード誤りの可能性）")
            return None
        df = df.tail(weeks).reset_index()
        date_col  = "Date" if "Date" in df.columns else "Datetime"
        close_col = "Close"
        if close_col not in df.columns:
            print(f"  [警告] {code}: Closeカラムが見つかりません")
            return None
        result = pd.DataFrame({
            "code":  code,
            "date":  pd.to_datetime(df[date_col]).dt.strftime("%Y-%m-%d"),
            "close": df[close_col],
        })
        result = result.dropna(subset=["close"])
        result = result[result["close"] > 0]
        if result.empty:
            print(f"  [警告] {code}: 有効な終値データなし")
            return None
        if len(result) < 13:
            print(f"  [警告] {code}: データが {len(result)} 週しかありません（13週MA計算に最低13週必要）")
        return result
    except Exception as e:
        print(f"  [エラー] {code}: 取得失敗 - {e}")
        return None


def main():
    args = parse_args()
    codes = []

    if args.codes:
        for c in args.codes:
            c = c.strip().upper().replace(".T", "").replace(".JP", "")
            if c:
                codes.append(c)

    if args.file:
        codes.extend(load_codes_from_file(args.file))

    if not codes and not args.no_excel:
        excel_path = args.excel if args.excel else DEFAULT_EXCEL_PATH
        if excel_path and Path(excel_path).exists():
            print(f"[Excel] {excel_path} を読み込みます...")
            xlsx_codes = load_codes_from_excel(excel_path, args.sheet, args.col, args.startrow)
            if xlsx_codes:
                codes.extend(xlsx_codes)
                print(f"[Excel] {len(xlsx_codes)} 件のコードを読み込みました。")
            else:
                print(f"[警告] Excelファイルからコードを読み込めませんでした: {excel_path}")
        elif args.excel:
            print(f"[エラー] Excelファイルが見つかりません: {args.excel}")
            sys.exit(1)

    if not codes:
        codes = [c.strip() for c in CODES if c.strip()]

    if not codes:
        print("[エラー] 銘柄コードが指定されていません。")
        print(f"  方法1: Excel ファイル（デフォルト: {DEFAULT_EXCEL_PATH}）")
        print('  方法2: --excel "C:\\Users\\linmu\\codes.xlsx"')
        print("  方法3: --codes 7203 9984 6758")
        print("  方法4: --file codes.txt")
        sys.exit(1)

    seen = set()
    codes = [c for c in codes if not (c in seen or seen.add(c))]

    print("=" * 55)
    print("  週足価格CSVダウンローダー")
    print("=" * 55)
    print(f"  対象銘柄数  : {len(codes)} 件")
    print(f"  取得週数    : {args.weeks} 週")
    print(f"  出力ファイル: {args.out}")
    print("=" * 55)
    print()

    if args.weeks < 13:
        print(f"[警告] 取得週数が13未満です（--weeks {args.weeks}）。13週MA計算に13週分必要です。")

    all_frames = []
    success_count = 0
    fail_count = 0

    for i, code in enumerate(codes, 1):
        print(f"[{i:3d}/{len(codes)}] {code}.T 取得中...", end=" ", flush=True)
        df = fetch_weekly_prices(code, args.weeks)
        if df is not None:
            if not args.no_round:
                df["close"] = df["close"].round(2)
            all_frames.append(df)
            success_count += 1
            print(f"OK ({len(df)}週)")
        else:
            fail_count += 1
        if i < len(codes):
            time.sleep(SLEEP_BETWEEN)

    print()

    if not all_frames:
        print("[エラー] 取得できたデータが0件です。コードや接続を確認してください。")
        sys.exit(1)

    combined = pd.concat(all_frames, ignore_index=True)
    out_path  = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(out_path, index=False, encoding="utf-8")

    print("=" * 55)
    print("  完了!")
    print(f"  成功 : {success_count} 銘柄")
    if fail_count > 0:
        print(f"  失敗 : {fail_count} 銘柄（上記 [警告]/[エラー] を確認）")
    print(f"  総行数: {len(combined)} 行")
    print(f"  出力  : {out_path.resolve()}")
    print("=" * 55)
    print()
    print("  次のステップ:")
    print(f"  1. アプリの「週足価格CSVファイル」欄に {out_path.name} をアップロード")
    print("  2. その他の設定（RS CSV、Kabutan HTML）を指定して実行")


if __name__ == "__main__":
    main()
