import json
import os
import requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

load_dotenv()

app = App(token=os.environ["SLACK_BOT_TOKEN"])

with open("data/topics.json", encoding="utf-8") as f:
    ALL_TOPICS = json.load(f)["topics"]


def build_topic_blocks():
    topics = ALL_TOPICS[:3]
    buttons = [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": t["label"], "emoji": True},
            "value": t["id"],
            "action_id": f"topic_{t['id']}",
        }
        for t in topics
    ]
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "📊 *이번 주 추천 주제 (AI Pick)*\n아래에서 분석할 주제를 선택하세요.",
            },
        },
        {"type": "actions", "elements": buttons},
    ]


@app.event("app_mention")
def handle_mention(event, say):
    say(blocks=build_topic_blocks())


@app.command("/topics")
def handle_topics_command(ack, respond):
    ack()
    respond(blocks=build_topic_blocks())


def dispatch_to_github(topic_id: str, channel_id: str) -> bool:
    topic = next((t for t in ALL_TOPICS if t["id"] == topic_id), None)
    if not topic:
        return False

    owner = os.environ["GITHUB_REPO_OWNER"]
    repo = os.environ["GITHUB_REPO_NAME"]
    token = os.environ["GITHUB_PAT"]

    resp = requests.post(
        f"https://api.github.com/repos/{owner}/{repo}/dispatches",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        },
        json={
            "event_type": "invest_pipeline",
            "client_payload": {
                "topic_id": topic_id,
                "topic_label": topic["label"],
                "analysis_type": topic["type"],
                "tickers": topic["tickers"],
                "sector": topic["sector"],
                "channel_id": channel_id,
            },
        },
        timeout=10,
    )
    return resp.status_code == 204


def make_topic_action_handler(topic_id: str):
    def handler(ack, body, client):
        ack()
        channel_id = body["channel"]["id"]
        topic = next((t for t in ALL_TOPICS if t["id"] == topic_id), None)

        client.chat_postMessage(
            channel=channel_id,
            text=f"📈 *{topic['label']}* 분석을 시작했습니다.\n⏳ 약 5-10분 후 결과가 전송됩니다.",
        )

        success = dispatch_to_github(topic_id, channel_id)
        if not success:
            client.chat_postMessage(
                channel=channel_id,
                text="⚠️ GitHub Actions 트리거 실패. 잠시 후 다시 시도해 주세요.",
            )

    return handler


for topic in ALL_TOPICS:
    app.action(f"topic_{topic['id']}")(make_topic_action_handler(topic["id"]))


if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    print("⚡ Invest Insta Bot is running...")
    handler.start()
