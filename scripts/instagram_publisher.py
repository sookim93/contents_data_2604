"""
Instagram publisher — three modes via INSTAGRAM_MODE env var.
  manual:   card already sent via DM in slack_notifier.py; just log.
  approval: post to Slack with ✅/❌ buttons (Slack bot handles the response).
  auto:     directly publish via Meta Graph API.
Input: output/analysis_result.json, output/card.png
"""

import json
import os
import sys
import time
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


INSTAGRAM_MODE = os.getenv("INSTAGRAM_MODE", "manual")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "")
INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID", "")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
IMAGE_PUBLIC_URL = os.getenv("IMAGE_PUBLIC_URL", "")

INPUT_FILE = "output/analysis_result.json"
CARD_FILE = "output/card.png"


def post_approval_request(client: WebClient, result: dict) -> None:
    """Sends card to Slack with Approve/Reject buttons."""
    topic_label = result.get("topic_label", "")
    caption = result.get("caption", "")

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"📸 *Instagram 게시 승인 요청*\n*주제:* {topic_label}\n\n*캡션:*\n```{caption[:500]}```",
            },
        },
        {
            "type": "actions",
            "block_id": "ig_approval",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ 승인하고 게시", "emoji": True},
                    "style": "primary",
                    "action_id": "ig_approve",
                    "value": json.dumps({
                        "topic_id": result.get("topic_id", ""),
                        "mode": "auto",
                    }),
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "❌ 거절", "emoji": True},
                    "style": "danger",
                    "action_id": "ig_reject",
                    "value": result.get("topic_id", ""),
                },
            ],
        },
    ]

    client.chat_postMessage(
        channel=SLACK_CHANNEL_ID,
        blocks=blocks,
        text=f"Instagram 게시 승인 요청: {topic_label}",
    )

    if os.path.exists(CARD_FILE):
        client.files_upload_v2(
            channel=SLACK_CHANNEL_ID,
            file=CARD_FILE,
            filename="instagram_card_preview.png",
            title="게시 예정 카드 미리보기",
        )

    print("[OK] 승인 요청 Slack 전송 완료")


def publish_to_instagram(image_url: str, caption: str) -> dict:
    """Calls Meta Graph API to publish image post."""
    if not INSTAGRAM_USER_ID or not INSTAGRAM_ACCESS_TOKEN:
        print("[ERROR] INSTAGRAM_USER_ID 또는 INSTAGRAM_ACCESS_TOKEN 미설정", file=sys.stderr)
        sys.exit(1)

    base = f"https://graph.instagram.com/v18.0/{INSTAGRAM_USER_ID}"

    container_resp = requests.post(
        f"{base}/media",
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
        timeout=30,
    )
    container_resp.raise_for_status()
    container_id = container_resp.json().get("id")
    if not container_id:
        print(f"[ERROR] Media container 생성 실패: {container_resp.json()}", file=sys.stderr)
        sys.exit(1)

    time.sleep(5)

    publish_resp = requests.post(
        f"{base}/media_publish",
        data={
            "creation_id": container_id,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
        timeout=30,
    )
    publish_resp.raise_for_status()
    post_id = publish_resp.json().get("id", "")
    print(f"[OK] Instagram 게시 완료 (post_id={post_id})")
    return {"post_id": post_id, "container_id": container_id}


def notify_slack_posted(client: WebClient, result: dict, post_id: str) -> None:
    topic_label = result.get("topic_label", "")
    client.chat_postMessage(
        channel=SLACK_CHANNEL_ID,
        text=f"✅ Instagram 게시 완료!\n*{topic_label}*\nPost ID: `{post_id}`",
    )


def main():
    with open(INPUT_FILE, encoding="utf-8") as f:
        result = json.load(f)

    caption = result.get("caption", "")

    if INSTAGRAM_MODE == "manual":
        print("[INFO] INSTAGRAM_MODE=manual — DM으로 카드 전송됨. 수동 업로드 필요.")
        return

    if INSTAGRAM_MODE == "approval":
        if not SLACK_BOT_TOKEN:
            print("[ERROR] SLACK_BOT_TOKEN 필요 (approval 모드)", file=sys.stderr)
            sys.exit(1)
        client = WebClient(token=SLACK_BOT_TOKEN)
        try:
            post_approval_request(client, result)
        except SlackApiError as e:
            print(f"[ERROR] 승인 요청 실패: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if INSTAGRAM_MODE == "auto":
        if not IMAGE_PUBLIC_URL:
            print("[ERROR] IMAGE_PUBLIC_URL 필요 (auto 모드 — Meta API는 공개 URL 필요)", file=sys.stderr)
            sys.exit(1)
        ig_result = publish_to_instagram(IMAGE_PUBLIC_URL, caption)

        if SLACK_BOT_TOKEN:
            client = WebClient(token=SLACK_BOT_TOKEN)
            notify_slack_posted(client, result, ig_result.get("post_id", ""))
        return

    print(f"[ERROR] 알 수 없는 INSTAGRAM_MODE: {INSTAGRAM_MODE}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
