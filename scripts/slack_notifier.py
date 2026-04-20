"""
Posts analysis text + chart image to Slack channel.
Sends card image via DM when INSTAGRAM_MODE=manual.
Input: output/analysis_result.json, output/chart.png, output/card.png
"""

import json
import os
import sys
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL_ID = os.environ["SLACK_CHANNEL_ID"]
INSTAGRAM_MODE = os.getenv("INSTAGRAM_MODE", "manual")

INPUT_FILE = "output/analysis_result.json"
CHART_FILE = "output/chart.png"
CARD_FILE = "output/card.png"


def post_analysis_to_channel(client: WebClient, result: dict) -> str:
    summary = result.get("summary", "분석 결과 없음")
    topic_label = result.get("topic_label", "")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📊 {topic_label} 분석 완료", "emoji": True},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": summary[:2900]},
        },
    ]

    msg = client.chat_postMessage(
        channel=SLACK_CHANNEL_ID,
        blocks=blocks,
        text=f"📊 {topic_label} 분석 완료",
    )
    thread_ts = msg["ts"]

    if os.path.exists(CHART_FILE):
        client.files_upload_v2(
            channel=SLACK_CHANNEL_ID,
            file=CHART_FILE,
            filename="chart.png",
            title=f"{topic_label} 차트",
            thread_ts=thread_ts,
        )

    print(f"[OK] Slack 채널 게시 완료 (ts={thread_ts})")
    return thread_ts


def send_card_via_dm(client: WebClient, result: dict) -> None:
    topic_label = result.get("topic_label", "")
    caption = result.get("caption", "")

    dm = client.conversations_open(users=[os.getenv("SLACK_USER_ID", "")])
    dm_channel = dm["channel"]["id"]

    client.chat_postMessage(
        channel=dm_channel,
        text=(
            f"📸 *Instagram 카드 준비됨*\n"
            f"*주제:* {topic_label}\n\n"
            f"*캡션 (복사해서 사용):*\n```{caption}```\n\n"
            f"아래 이미지를 저장 후 Instagram에 올려주세요."
        ),
    )

    if os.path.exists(CARD_FILE):
        client.files_upload_v2(
            channel=dm_channel,
            file=CARD_FILE,
            filename="instagram_card.png",
            title=f"{topic_label} 인스타 카드",
        )

    print(f"[OK] Slack DM으로 카드 전송 완료")


def main():
    client = WebClient(token=SLACK_BOT_TOKEN)

    with open(INPUT_FILE, encoding="utf-8") as f:
        result = json.load(f)

    try:
        post_analysis_to_channel(client, result)
    except SlackApiError as e:
        print(f"[ERROR] Slack 채널 게시 실패: {e}", file=sys.stderr)
        sys.exit(1)

    if INSTAGRAM_MODE == "manual":
        try:
            send_card_via_dm(client, result)
        except SlackApiError as e:
            print(f"[WARN] DM 전송 실패 (계속 진행): {e}", file=sys.stderr)

    print("[OK] Slack 알림 완료")


if __name__ == "__main__":
    main()
