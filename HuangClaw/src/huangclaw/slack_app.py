from __future__ import annotations

import asyncio
import re

from fastapi import FastAPI, Request
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from slack_bolt.async_app import AsyncApp

from huangclaw import __version__
from huangclaw.agent import get_agent
from huangclaw.config import get_settings


settings = get_settings()
if not settings.slack_bot_token or not settings.slack_signing_secret:
    raise RuntimeError("SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET are required for Slack mode.")

slack_app = AsyncApp(
    token=settings.slack_bot_token,
    signing_secret=settings.slack_signing_secret,
)
handler = AsyncSlackRequestHandler(slack_app)
api = FastAPI(title="HuangClaw Slack Agent", version=__version__)


def _clean_prompt(text: str) -> str:
    without_mentions = re.sub(r"<@[A-Z0-9]+>\s*", "", text or "")
    return without_mentions.strip()


def _slack_safe(text: str) -> str:
    if len(text) <= 38000:
        return text
    return text[:38000] + "\n\n[truncated for Slack]"


async def _answer(prompt: str) -> str:
    if not prompt:
        return "Please send a question or task."
    return await asyncio.to_thread(get_agent().ask, prompt)


@api.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "huangclaw-slack", "version": __version__}


@api.post("/slack/events")
async def slack_events(req: Request):
    return await handler.handle(req)


@slack_app.event("app_mention")
async def handle_app_mention(event, say, ack):
    await ack()
    prompt = _clean_prompt(event.get("text", ""))
    thread_ts = event.get("thread_ts") or event.get("ts")
    await say(text="收到，我正在处理。", thread_ts=thread_ts)
    answer = await _answer(prompt)
    await say(text=_slack_safe(answer), thread_ts=thread_ts)


@slack_app.event("message")
async def handle_direct_message(event, say, ack):
    await ack()
    if event.get("bot_id") or event.get("subtype"):
        return
    if event.get("channel_type") != "im":
        return

    prompt = _clean_prompt(event.get("text", ""))
    thread_ts = event.get("thread_ts") or event.get("ts")
    answer = await _answer(prompt)
    await say(text=_slack_safe(answer), thread_ts=thread_ts)
