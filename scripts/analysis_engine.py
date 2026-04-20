"""
Processes raw collected data into a structured analysis result.
Input:  output/analysis_data.json
Output: output/analysis_result.json
"""

import json
import os
from datetime import datetime


INPUT_FILE = "output/analysis_data.json"
OUTPUT_FILE = "output/analysis_result.json"


def analyze_sector_trend(data: dict) -> dict:
    tickers = data.get("tickers", [])
    if not tickers:
        return {"summary": "데이터가 없습니다.", "key_metrics": [], "top_gainers": [], "top_losers": []}

    sorted_by_change = sorted(tickers, key=lambda x: x["change_pct"], reverse=True)
    gainers = [t for t in sorted_by_change if t["change_pct"] > 0]
    losers = [t for t in sorted_by_change if t["change_pct"] < 0]
    avg_change = sum(t["change_pct"] for t in tickers) / len(tickers)

    sector = data.get("sector", "")
    period = data.get("period", {})
    top = sorted_by_change[0] if sorted_by_change else {}
    bottom = sorted_by_change[-1] if sorted_by_change else {}

    summary_lines = [
        f"📊 *{sector} 섹터 분석* ({period.get('from', '')} ~ {period.get('to', '')})",
        f"",
        f"• 분석 종목: {len(tickers)}개",
        f"• 평균 등락률: {avg_change:+.1f}%",
        f"• 상승 종목: {len(gainers)}개 / 하락 종목: {len(losers)}개",
    ]
    if top:
        summary_lines.append(f"• 최고 상승: {top['name']} ({top['change_pct']:+.1f}%)")
    if bottom:
        summary_lines.append(f"• 최고 하락: {bottom['name']} ({bottom['change_pct']:+.1f}%)")

    key_metrics = [
        {"label": "평균 등락률", "value": f"{avg_change:+.1f}%"},
        {"label": "상승 종목 수", "value": f"{len(gainers)}개"},
        {"label": "하락 종목 수", "value": f"{len(losers)}개"},
    ]

    return {
        "analysis_type": "sector_trend",
        "sector": sector,
        "summary": "\n".join(summary_lines),
        "key_metrics": key_metrics,
        "top_gainers": sorted_by_change[:3],
        "top_losers": sorted_by_change[-3:][::-1],
        "all_tickers": sorted_by_change,
        "avg_change_pct": round(avg_change, 2),
        "gainer_count": len(gainers),
        "loser_count": len(losers),
    }


def format_krw(value) -> str:
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.1f}조원"
    if abs(value) >= 100_000_000:
        return f"{value / 100_000_000:.0f}억원"
    return f"{value:,}원"


def analyze_performance(data: dict) -> dict:
    companies = data.get("companies", [])
    if not companies:
        return {"summary": "데이터가 없습니다.", "key_metrics": [], "companies": []}

    period = data.get("period", {})
    year = period.get("year", "")
    quarter = period.get("quarter", "")

    summary_parts = [
        f"📊 *{data.get('sector', '')} 섹터 실적 분석* ({year}년 {quarter}분기)",
        "",
    ]
    key_metrics = []

    for co in companies:
        rev = co.get("revenue")
        op = co.get("operating_profit")
        net = co.get("net_profit")
        eps = co.get("eps")
        price_chg = co.get("price_change_pct", 0)

        op_margin = None
        if rev and op:
            op_margin = round(op / rev * 100, 1)

        summary_parts.append(f"*{co['name']}* ({co['ticker']})")
        summary_parts.append(f"  • 매출액: {format_krw(rev)}")
        summary_parts.append(f"  • 영업이익: {format_krw(op)}" + (f" (이익률 {op_margin}%)" if op_margin else ""))
        summary_parts.append(f"  • 당기순이익: {format_krw(net)}")
        if eps:
            summary_parts.append(f"  • EPS: {eps:,}원")
        summary_parts.append(f"  • 주가 변동 (1개월): {price_chg:+.1f}%")
        summary_parts.append("")

        key_metrics.append({
            "company": co["name"],
            "revenue": format_krw(rev),
            "operating_profit": format_krw(op),
            "op_margin": f"{op_margin}%" if op_margin else "N/A",
            "net_profit": format_krw(net),
            "eps": f"{eps:,}원" if eps else "N/A",
            "price_change": f"{price_chg:+.1f}%",
        })

    return {
        "analysis_type": "performance",
        "sector": data.get("sector", ""),
        "period": f"{year}년 {quarter}분기",
        "summary": "\n".join(summary_parts),
        "key_metrics": key_metrics,
        "companies": companies,
    }


def generate_caption(result: dict, topic_label: str) -> str:
    sector = result.get("sector", "")
    analysis_type = result.get("analysis_type", "")

    if analysis_type == "sector_trend":
        avg = result.get("avg_change_pct", 0)
        gainers = result.get("gainer_count", 0)
        losers = result.get("loser_count", 0)
        caption = (
            f"📊 {topic_label}\n\n"
            f"{sector} 섹터 최근 한 달 성과\n"
            f"평균 등락률 {avg:+.1f}% | 상승 {gainers}개 하락 {losers}개\n\n"
            f"#국내주식 #{sector} #투자공부 #주식분석 #블룸버그스타일 #KOSPI #KOSDAQ"
        )
    else:
        companies = result.get("key_metrics", [])
        lines = [f"📊 {topic_label}\n"]
        for co in companies[:2]:
            lines.append(f"{co['company']}: 매출 {co['revenue']} | 영업이익 {co['operating_profit']}")
        caption = (
            "\n".join(lines) + "\n\n"
            f"#국내주식 #{sector} #투자공부 #주식실적 #블룸버그스타일 #KOSPI"
        )
    return caption


def main():
    with open(INPUT_FILE, encoding="utf-8") as f:
        data = json.load(f)

    analysis_type = data.get("type", "sector_trend")
    topic_label = data.get("meta", {}).get("topic_label", "")

    if analysis_type == "sector_trend":
        result = analyze_sector_trend(data)
    else:
        result = analyze_performance(data)

    result["topic_label"] = topic_label
    result["topic_id"] = data.get("meta", {}).get("topic_id", "")
    result["caption"] = generate_caption(result, topic_label)
    result["analyzed_at"] = datetime.now().isoformat()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    print(f"[OK] 분석 완료: {OUTPUT_FILE}")
    print(result["summary"])


if __name__ == "__main__":
    main()
