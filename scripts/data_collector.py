"""
Collects Korean stock data from KRX (via pykrx) and DART API.
Reads topic config from env vars set by GitHub Actions repository_dispatch payload.
Outputs: output/analysis_data.json
"""

import json
import os
import sys
from datetime import datetime, timedelta

import pandas as pd
import requests
from pykrx import stock as krx


DART_API_KEY = os.getenv("DART_API_KEY", "")
TOPIC_ID = os.getenv("TOPIC_ID", "semiconductor_trend")
ANALYSIS_TYPE = os.getenv("ANALYSIS_TYPE", "sector_trend")
TICKERS = os.getenv("TICKERS", "000660,005930").split(",")
SECTOR = os.getenv("SECTOR", "반도체")
TOPIC_LABEL = os.getenv("TOPIC_LABEL", "반도체 섹터 동향")

OUTPUT_FILE = "output/analysis_data.json"
TODAY = datetime.today().strftime("%Y%m%d")
MONTH_AGO = (datetime.today() - timedelta(days=30)).strftime("%Y%m%d")


def fetch_sector_trend():
    print(f"[KRX] 섹터 데이터 수집: {SECTOR}")
    records = []
    for ticker in TICKERS:
        try:
            df = krx.get_market_ohlcv(MONTH_AGO, TODAY, ticker)
            if df.empty:
                continue
            name_raw = krx.get_market_ticker_name(ticker)
            name = ticker if hasattr(name_raw, "empty") else str(name_raw).strip()
            if not name:
                name = ticker
            start_price = df["종가"].iloc[0]
            end_price = df["종가"].iloc[-1]
            change_pct = round((end_price - start_price) / start_price * 100, 2)
            records.append({
                "ticker": ticker,
                "name": name,
                "start_price": int(start_price),
                "end_price": int(end_price),
                "change_pct": change_pct,
                "volume_avg": int(df["거래량"].mean()),
                "prices": df["종가"].tolist()[-10:],
                "dates": [str(d.date()) for d in df.index][-10:],
            })
        except Exception as e:
            print(f"[WARN] {ticker} 데이터 수집 실패: {e}", file=sys.stderr)

    sector_df = None
    try:
        sector_df = krx.get_market_sector_performance(TODAY, market="KOSPI")
    except Exception as e:
        print(f"[WARN] 섹터 전체 데이터 실패: {e}", file=sys.stderr)

    return {
        "type": "sector_trend",
        "sector": SECTOR,
        "period": {"from": MONTH_AGO, "to": TODAY},
        "tickers": records,
        "sector_summary": sector_df.to_dict() if sector_df is not None else {},
    }


def fetch_dart_performance():
    print(f"[DART] 종목 실적 수집: {TICKERS}")
    if not DART_API_KEY:
        print("[ERROR] DART_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    results = []
    current_year = datetime.today().year
    quarter = (datetime.today().month - 1) // 3 + 1
    reprt_code = {1: "11013", 2: "11012", 3: "11014", 4: "11011"}.get(quarter, "11013")

    for ticker in TICKERS:
        try:
            corp_code = get_dart_corp_code(ticker)
            if not corp_code:
                continue

            url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
            params = {
                "crtfc_key": DART_API_KEY,
                "corp_code": corp_code,
                "bsns_year": str(current_year),
                "reprt_code": reprt_code,
                "fs_div": "CFS",
            }
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()

            if data.get("status") != "000":
                print(f"[WARN] DART API 오류 ({ticker}): {data.get('message')}", file=sys.stderr)
                continue

            items = data.get("list", [])
            metrics = extract_dart_metrics(items)
            name = krx.get_market_ticker_name(ticker)

            price_df = krx.get_market_ohlcv(MONTH_AGO, TODAY, ticker)
            price_change = 0.0
            if not price_df.empty:
                price_change = round(
                    (price_df["종가"].iloc[-1] - price_df["종가"].iloc[0])
                    / price_df["종가"].iloc[0] * 100, 2
                )

            results.append({
                "ticker": ticker,
                "name": name,
                "price_change_pct": price_change,
                **metrics,
            })
        except Exception as e:
            print(f"[WARN] {ticker} DART 수집 실패: {e}", file=sys.stderr)

    return {
        "type": "performance",
        "sector": SECTOR,
        "period": {"year": current_year, "quarter": quarter},
        "companies": results,
    }


def get_dart_corp_code(ticker: str) -> str:
    """KRX ticker → DART corp_code 변환"""
    url = "https://opendart.fss.or.kr/api/company.json"
    params = {"crtfc_key": DART_API_KEY, "stock_code": ticker}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        return data.get("corp_code", "")
    except Exception:
        return ""


def extract_dart_metrics(items: list) -> dict:
    """재무제표 항목에서 핵심 지표 추출"""
    metrics = {
        "revenue": None,
        "operating_profit": None,
        "net_profit": None,
        "eps": None,
    }
    account_map = {
        "매출액": "revenue",
        "영업이익": "operating_profit",
        "당기순이익": "net_profit",
        "주당순이익": "eps",
    }
    for item in items:
        for kr_name, en_key in account_map.items():
            if kr_name in item.get("account_nm", ""):
                try:
                    val = item.get("thstrm_amount", "").replace(",", "")
                    metrics[en_key] = int(val) if val else None
                except ValueError:
                    pass
    return metrics


def main():
    os.makedirs("output", exist_ok=True)

    if ANALYSIS_TYPE == "sector_trend":
        data = fetch_sector_trend()
    else:
        data = fetch_dart_performance()

    data["meta"] = {
        "topic_id": TOPIC_ID,
        "topic_label": TOPIC_LABEL,
        "collected_at": datetime.now().isoformat(),
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print(f"[OK] 데이터 저장 완료: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
