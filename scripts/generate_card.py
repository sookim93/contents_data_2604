"""
Bloomberg dark theme chart + Instagram card generator.
Input:  output/analysis_result.json
Output: output/chart.png (1080x1080), output/card.png (1080x1350)
"""

import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import font_manager
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BG = "#0A0A0A"
GREEN = "#00FF41"
CYAN = "#00D9FF"
PINK = "#FF006E"
GRAY = "#333333"
WHITE = "#FFFFFF"
DIM = "#888888"

CHART_SIZE = (1080, 1080)
CARD_SIZE = (1080, 1350)

INPUT_FILE = "output/analysis_result.json"
CHART_FILE = "output/chart.png"
CARD_FILE = "output/card.png"


def setup_korean_font():
    font_dirs = [
        "/usr/share/fonts",
        "/System/Library/Fonts",
        os.path.expanduser("~/.fonts"),
        "fonts",
    ]
    for d in font_dirs:
        p = Path(d)
        if p.exists():
            for font_file in p.rglob("*.[ot]tf"):
                try:
                    font_manager.fontManager.addfont(str(font_file))
                except Exception:
                    pass

    available = {f.name for f in font_manager.fontManager.ttflist}
    korean_fonts = ["NanumGothic", "NanumBarunGothic", "AppleGothic", "Malgun Gothic", "나눔고딕"]
    for fname in korean_fonts:
        if fname in available:
            plt.rcParams["font.family"] = fname
            plt.rcParams["axes.unicode_minus"] = False
            return fname

    plt.rcParams["font.family"] = "DejaVu Sans"
    return "DejaVu Sans"


def hex_to_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def make_sector_chart(result: dict) -> None:
    tickers = result.get("all_tickers", result.get("top_gainers", []))[:8]
    if not tickers:
        tickers = [{"name": "데이터 없음", "change_pct": 0}]

    names = [t["name"][:6] for t in tickers]
    changes = [t["change_pct"] for t in tickers]
    colors = [GREEN if c >= 0 else PINK for c in changes]

    fig, axes = plt.subplots(2, 1, figsize=(10.8, 10.8),
                              gridspec_kw={"height_ratios": [2.5, 1]},
                              facecolor=BG)
    fig.subplots_adjust(left=0.1, right=0.95, top=0.88, bottom=0.08, hspace=0.35)

    ax_bar = axes[0]
    ax_bar.set_facecolor(BG)
    bars = ax_bar.barh(range(len(names)), changes, color=colors, height=0.6, edgecolor="none")

    for i, (bar, val) in enumerate(zip(bars, changes)):
        sign = "+" if val >= 0 else ""
        color = GREEN if val >= 0 else PINK
        ax_bar.text(val + (0.1 if val >= 0 else -0.1), i,
                    f"{sign}{val:.1f}%", va="center",
                    ha="left" if val >= 0 else "right",
                    color=color, fontsize=11, fontweight="bold")

    ax_bar.set_yticks(range(len(names)))
    ax_bar.set_yticklabels(names, color=WHITE, fontsize=12)
    ax_bar.axvline(0, color=GRAY, linewidth=0.8)
    ax_bar.set_xlabel("등락률 (%)", color=DIM, fontsize=10)
    ax_bar.tick_params(colors=DIM, which="both")
    ax_bar.spines[:].set_color(GRAY)
    for spine in ax_bar.spines.values():
        spine.set_linewidth(0.5)
    ax_bar.grid(axis="x", color=GRAY, linewidth=0.3, alpha=0.5)

    key_metrics = result.get("key_metrics", [])
    ax_table = axes[1]
    ax_table.set_facecolor(BG)
    ax_table.axis("off")

    if key_metrics:
        m = key_metrics
        col_labels = ["지표", "값"]
        table_data = [[item["label"], item["value"]] for item in m[:4]]
        table = ax_table.table(cellText=table_data, colLabels=col_labels,
                                loc="center", cellLoc="center")
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        for (row, col), cell in table.get_celld().items():
            cell.set_facecolor(GRAY if row == 0 else BG)
            cell.set_text_props(color=CYAN if row == 0 else WHITE)
            cell.set_edgecolor(GRAY)

    topic_label = result.get("topic_label", "")
    fig.suptitle(topic_label, color=CYAN, fontsize=16, fontweight="bold", y=0.96)

    watermark = f"KRX DATA  |  {result.get('analyzed_at', '')[:10]}"
    fig.text(0.95, 0.01, watermark, color=DIM, fontsize=8,
             ha="right", va="bottom")

    plt.savefig(CHART_FILE, dpi=100, facecolor=BG, bbox_inches="tight",
                pad_inches=0.1)
    plt.close(fig)
    print(f"[OK] 차트 저장: {CHART_FILE}")


def make_performance_chart(result: dict) -> None:
    companies = result.get("companies", [])
    if not companies:
        make_placeholder_chart(result)
        return

    fig, ax = plt.subplots(figsize=(10.8, 10.8), facecolor=BG)
    ax.set_facecolor(BG)

    names = [c["name"][:6] for c in companies]
    revenues = []
    op_profits = []
    for c in companies:
        rev = c.get("revenue") or 0
        op = c.get("operating_profit") or 0
        revenues.append(rev / 1e8)
        op_profits.append(op / 1e8)

    x = np.arange(len(names))
    width = 0.35
    bars1 = ax.bar(x - width/2, revenues, width, label="매출액", color=CYAN, alpha=0.85, edgecolor="none")
    bars2 = ax.bar(x + width/2, op_profits, width, label="영업이익", color=GREEN, alpha=0.85, edgecolor="none")

    ax.set_xticks(x)
    ax.set_xticklabels(names, color=WHITE, fontsize=12)
    ax.set_ylabel("금액 (억원)", color=DIM, fontsize=10)
    ax.tick_params(colors=DIM, which="both")
    ax.spines[:].set_color(GRAY)
    for spine in ax.spines.values():
        spine.set_linewidth(0.5)
    ax.grid(axis="y", color=GRAY, linewidth=0.3, alpha=0.5)

    legend = ax.legend(facecolor=BG, edgecolor=GRAY, labelcolor=WHITE, fontsize=11)

    for bar in bars1:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2, h * 1.01,
                    f"{h:,.0f}", ha="center", va="bottom", color=CYAN, fontsize=9)
    for bar in bars2:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2, h * 1.01,
                    f"{h:,.0f}", ha="center", va="bottom", color=GREEN, fontsize=9)

    period = result.get("period", "")
    topic_label = result.get("topic_label", "")
    fig.suptitle(f"{topic_label}  |  {period}", color=CYAN, fontsize=15, fontweight="bold")
    fig.text(0.95, 0.01, f"DART  |  {result.get('analyzed_at', '')[:10]}",
             color=DIM, fontsize=8, ha="right", va="bottom")

    plt.tight_layout(rect=[0, 0.02, 1, 0.96])
    plt.savefig(CHART_FILE, dpi=100, facecolor=BG, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    print(f"[OK] 실적 차트 저장: {CHART_FILE}")


def make_placeholder_chart(result: dict) -> None:
    fig, ax = plt.subplots(figsize=(10.8, 10.8), facecolor=BG)
    ax.set_facecolor(BG)
    ax.text(0.5, 0.5, "데이터 수집 중...", color=CYAN, fontsize=24,
            ha="center", va="center", transform=ax.transAxes)
    ax.axis("off")
    plt.savefig(CHART_FILE, dpi=100, facecolor=BG)
    plt.close(fig)


def compose_instagram_card(result: dict) -> None:
    card = Image.new("RGB", CARD_SIZE, color=(10, 10, 10))
    draw = ImageDraw.Draw(card)

    chart_img = Image.open(CHART_FILE).convert("RGB")
    chart_resized = chart_img.resize(CHART_SIZE, Image.LANCZOS)
    card.paste(chart_resized, (0, 0))

    footer_top = CHART_SIZE[1]

    draw.rectangle([0, footer_top, CARD_SIZE[0], CARD_SIZE[1]], fill=(15, 15, 20))
    # Cyan accent line
    draw.rectangle([0, footer_top, CARD_SIZE[0], footer_top + 4], fill=(0, 217, 255))
    # Side accent bar
    draw.rectangle([0, footer_top + 4, 6, CARD_SIZE[1]], fill=(0, 217, 255))

    def try_font(size):
        candidates = [
            "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "/System/Library/Fonts/AppleGothic.ttf",
            "fonts/NanumGothic.ttf",
        ]
        for path in candidates:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
        return ImageFont.load_default()

    font_title = try_font(42)
    font_metric_label = try_font(24)
    font_metric_value = try_font(28)
    font_small = try_font(20)

    PAD = 54
    y = footer_top + 28

    topic_label = result.get("topic_label", "")
    draw.text((PAD, y), topic_label, font=font_title, fill=(0, 217, 255))
    y += 58

    # Divider
    draw.rectangle([PAD, y, CARD_SIZE[0] - PAD, y + 1], fill=(50, 50, 60))
    y += 14

    key_metrics = result.get("key_metrics", [])
    analysis_type = result.get("analysis_type", "sector_trend")

    if analysis_type == "sector_trend":
        for metric in key_metrics[:4]:
            draw.text((PAD, y), metric["label"], font=font_metric_label, fill=(136, 136, 136))
            draw.text((PAD + 300, y), metric["value"], font=font_metric_value, fill=(255, 255, 255))
            y += 44
    else:
        for metric in key_metrics[:2]:
            name = metric.get("company", "")
            draw.text((PAD, y), name, font=font_metric_label, fill=(0, 217, 255))
            y += 34
            draw.text((PAD + 20, y), f"매출  {metric['revenue']}", font=font_metric_label, fill=(200, 200, 200))
            draw.text((PAD + 340, y), f"영업이익  {metric['operating_profit']}", font=font_metric_label, fill=(0, 255, 65))
            y += 42

    date_str = result.get("analyzed_at", "")[:10]
    footer_text = f"KRX DATA  ·  Bloomberg Style  ·  {date_str}"
    draw.text((PAD, CARD_SIZE[1] - 44), footer_text, font=font_small, fill=(80, 80, 90))

    card.save(CARD_FILE, "PNG", quality=95)
    print(f"[OK] 인스타 카드 저장: {CARD_FILE}  ({CARD_SIZE[0]}x{CARD_SIZE[1]}px)")


def main():
    setup_korean_font()
    os.makedirs("output", exist_ok=True)

    with open(INPUT_FILE, encoding="utf-8") as f:
        result = json.load(f)

    analysis_type = result.get("analysis_type", "sector_trend")
    if analysis_type == "sector_trend":
        make_sector_chart(result)
    else:
        make_performance_chart(result)

    compose_instagram_card(result)
    print("[OK] 카드 생성 완료")


if __name__ == "__main__":
    main()
