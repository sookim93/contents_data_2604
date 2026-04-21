"""
Generates 10 daily KOSPI content topic suggestions and sends to stokku_daily Slack channel.
Topics focus on sector maps and structure, with Claude web prompts attached.
"""

import json
import os
import random
import requests
from datetime import datetime, timedelta

try:
    from pykrx import stock as krx
    HAS_PYKRX = True
except ImportError:
    HAS_PYKRX = False

WEBHOOK_URL = os.getenv("STOKKU_SLACK_WEBHOOK_URL", "")
TODAY = datetime.today().strftime("%Y-%m-%d")
TODAY_KRX = datetime.today().strftime("%Y%m%d")
PREV_DATE = (datetime.today() - timedelta(days=1)).strftime("%Y%m%d")

# Sector definitions with representative tickers
SECTORS = {
    "반도체": ["005930", "000660", "042700", "066970", "112040"],
    "2차전지": ["373220", "247540", "006400", "051910", "096770"],
    "자동차": ["005380", "000270", "012330", "204320", "현대차"],
    "금융·은행": ["105560", "055550", "086790", "316140", "138930"],
    "바이오·제약": ["068270", "207940", "128940", "326030", "000100"],
    "조선": ["009540", "010140", "329180", "현대미포조선"],
    "방산": ["047810", "012450", "064350", "272210"],
    "플랫폼·IT": ["035420", "035720", "259960", "263750"],
    "에너지·화학": ["096770", "011170", "010950", "000880"],
    "소비재·유통": ["139480", "004990", "023530", "282330"],
}

TOPIC_TEMPLATES = {
    "sector_map": [
        ("{sector} 섹터 지형도 — 시총 탑3 기업과 그 비중",
         "코스피 {sector} 섹터를 분석해줘. 시총 상위 3개 기업 이름, 시총 규모, 전체 섹터 대비 비중을 정리하고, 각 기업이 왜 이 섹터를 대표하는지 1~2줄로 설명해줘. 결과는 인스타그램 카드뉴스 형태(제목 + 핵심 데이터 3개 + 한줄 인사이트)로 만들어줘."),
        ("코스피 시총 1조+ 기업은 몇 개? 섹터별로 얼마나 분포돼 있나",
         "코스피 시총 1조원 이상 기업의 섹터별 분포를 분석해줘. 각 섹터에 몇 개 기업이 있는지, 시총 합계는 얼마인지 정리하고 가장 기업이 많은 섹터와 가장 시총이 큰 섹터를 비교해줘. 인스타그램 카드뉴스 형태로 만들어줘."),
        ("{sector} vs {sector2} — 코스피에서 차지하는 시총 비중 비교",
         "코스피에서 {sector} 섹터와 {sector2} 섹터의 시총 비중을 비교해줘. 각 섹터의 대표 기업 2개씩, 시총 규모, 최근 1년 변화 방향을 정리해줘. 인스타그램 카드뉴스 형태로 만들어줘."),
        ("{sector} 섹터 구조 해부 — 대형주·중형주·소형주로 나눠보면",
         "코스피 {sector} 섹터를 시총 기준으로 대형주/중형주/소형주로 나눠서 설명해줘. 각 그룹의 대표 기업 1~2개와 특징을 정리하고, 투자자 입장에서 어떤 기업에 주목해야 하는지 인사이트를 담아줘. 인스타그램 카드뉴스 형태로 만들어줘."),
        ("코스피 섹터 지도 — 올해 시총이 가장 커진 섹터 TOP3",
         "코스피에서 올해 시총이 가장 많이 증가한 섹터 TOP3를 분석해줘. 각 섹터의 성장 배경(정책, 글로벌 트렌드, 실적 등)을 1~2줄로 설명하고, 대표 수혜 기업을 1개씩 언급해줘. 인스타그램 카드뉴스 형태로 만들어줘."),
    ],
    "sector_deep": [
        ("{sector} 섹터 탑3 기업 스토리 — 왜 이 기업들이 대장인가",
         "코스피 {sector} 섹터 시총 탑3 기업의 사업 모델을 각각 2~3줄로 설명해줘. 이 기업들이 섹터를 대표하게 된 이유, 최근 주요 이슈나 성장 동력도 포함해줘. 인스타그램 카드뉴스 형태(기업별 슬라이드 구성)로 만들어줘."),
        ("{sector} 섹터, 지금 어느 사이클에 있나 — 성장기·성숙기·침체기",
         "코스피 {sector} 섹터가 현재 산업 사이클의 어느 단계에 있는지 분석해줘. 성장 동력과 리스크 요인을 각각 2개씩 정리하고, 대표 기업의 최근 실적 방향과 연결해서 설명해줘. 인스타그램 카드뉴스 형태로 만들어줘."),
        ("{sector} 섹터 글로벌 비교 — 한국 기업의 위치는",
         "글로벌 {sector} 산업에서 한국 코스피 기업들의 위치를 설명해줘. 시장 점유율, 기술력, 주요 경쟁국 대비 강점과 약점을 정리하고, 대표 기업 2개의 글로벌 경쟁력을 간단히 비교해줘. 인스타그램 카드뉴스 형태로 만들어줘."),
    ],
    "theme": [
        ("코스피 신규 시총 1조 진입 기업 — 어떤 섹터에서 나왔나",
         "최근 1~2년 사이 코스피에서 시총 1조원에 새로 진입한 기업들을 분석해줘. 어느 섹터에서 많이 나왔는지, 공통된 성장 배경이 있는지 정리해줘. 인스타그램 카드뉴스 형태로 만들어줘."),
        ("코스피 섹터별 밸류에이션 지도 — PER로 보는 고평가·저평가 섹터",
         "코스피 주요 섹터의 평균 PER를 비교해줘. 현재 고평가 구간인 섹터와 저평가 구간인 섹터를 각각 2개씩 꼽고, 그 이유를 간단히 설명해줘. 인스타그램 카드뉴스 형태로 만들어줘."),
        ("정책 수혜 섹터 지도 — 올해 정부 정책이 미치는 섹터는",
         "올해 한국 정부의 주요 정책(산업, 에너지, 방산 등)이 코스피 어느 섹터에 수혜를 주는지 분석해줘. 수혜 섹터 TOP3와 각각의 대표 기업 1개씩을 정리해줘. 인스타그램 카드뉴스 형태로 만들어줘."),
    ],
    "individual": [
        ("이번 주 외국인이 가장 많이 산 섹터는 — 수급으로 보는 시장 흐름",
         "이번 주 코스피에서 외국인 순매수가 가장 많았던 섹터 TOP3를 분석해줘. 각 섹터에서 가장 많이 순매수된 대표 종목 1개씩과, 외국인이 해당 섹터를 사는 이유(글로벌 트렌드, 환율, 실적 등)를 연결해서 설명해줘. 인스타그램 카드뉴스 형태로 만들어줘."),
    ],
}


def pick_topics():
    sectors = list(SECTORS.keys())
    topics = []

    # 5 sector map topics
    templates = TOPIC_TEMPLATES["sector_map"].copy()
    random.shuffle(templates)
    for tmpl in templates[:5]:
        s1 = random.choice(sectors)
        s2 = random.choice([s for s in sectors if s != s1])
        title = tmpl[0].replace("{sector}", s1).replace("{sector2}", s2)
        prompt = tmpl[1].replace("{sector}", s1).replace("{sector2}", s2)
        topics.append(("섹터맵", title, prompt))

    # 3 sector deep topics
    templates = TOPIC_TEMPLATES["sector_deep"].copy()
    random.shuffle(templates)
    for tmpl in templates[:3]:
        s1 = random.choice(sectors)
        title = tmpl[0].replace("{sector}", s1)
        prompt = tmpl[1].replace("{sector}", s1)
        topics.append(("섹터심층", title, prompt))

    # 1 theme topic
    tmpl = random.choice(TOPIC_TEMPLATES["theme"])
    topics.append(("테마", tmpl[0], tmpl[1]))

    # 1 individual/flow topic
    tmpl = random.choice(TOPIC_TEMPLATES["individual"])
    topics.append(("수급", tmpl[0], tmpl[1]))

    random.shuffle(topics)
    return topics


def build_slack_message(topics):
    date_str = datetime.today().strftime("%Y년 %m월 %d일")
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📊 {date_str} 오늘의 콘텐츠 주제 10선"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "주제를 고르고, 아래 프롬프트를 Claude 웹에 붙여넣으세요."}
        },
        {"type": "divider"}
    ]

    tag_emoji = {"섹터맵": "🗺️", "섹터심층": "🔍", "테마": "💡", "수급": "📈"}

    for i, (tag, title, prompt) in enumerate(topics, 1):
        emoji = tag_emoji.get(tag, "📌")
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{i}. {emoji} [{tag}] {title}*\n```{prompt}```"
            }
        })
        blocks.append({"type": "divider"})

    return {"blocks": blocks}


def send_to_slack(message):
    resp = requests.post(WEBHOOK_URL, json=message, timeout=10)
    resp.raise_for_status()
    print(f"[Slack] 전송 완료 ({resp.status_code})")


if __name__ == "__main__":
    if not WEBHOOK_URL:
        print("[ERROR] STOKKU_SLACK_WEBHOOK_URL 환경변수가 없습니다.")
        exit(1)

    random.seed(int(datetime.today().strftime("%Y%m%d")))
    topics = pick_topics()
    message = build_slack_message(topics)
    send_to_slack(message)
