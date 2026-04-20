"""
Posts a failure alert to Slack webhook when a GitHub Actions step fails.
Reads env vars set by the workflow's failure step.
"""

import json
import os
import sys
import requests


SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
FAILED_STEP = os.getenv("FAILED_STEP", "unknown step")
GITHUB_RUN_ID = os.getenv("GITHUB_RUN_ID", "")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY", "")
ERROR_MESSAGE = os.getenv("ERROR_MESSAGE", "")[:500]


def main():
    if not SLACK_WEBHOOK_URL:
        print("[ERROR] SLACK_WEBHOOK_URL not set", file=sys.stderr)
        sys.exit(1)

    run_url = f"https://github.com/{GITHUB_REPOSITORY}/actions/runs/{GITHUB_RUN_ID}"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🔴 파이프라인 실패",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*실패 단계:*\n{FAILED_STEP}"},
                {"type": "mrkdwn", "text": f"*Run ID:*\n`{GITHUB_RUN_ID}`"},
            ],
        },
    ]

    if ERROR_MESSAGE:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*에러 메시지:*\n```{ERROR_MESSAGE}```",
            },
        })

    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "View Run Log", "emoji": False},
                "url": run_url,
                "style": "danger",
            }
        ],
    })

    payload = {
        "text": f"🔴 파이프라인 실패: {FAILED_STEP} (Run #{GITHUB_RUN_ID})",
        "blocks": blocks,
    }

    resp = requests.post(
        SLACK_WEBHOOK_URL,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    resp.raise_for_status()
    print("[OK] Slack 실패 알림 전송 완료")


if __name__ == "__main__":
    main()
