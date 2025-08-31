from __future__ import annotations
from typing import Tuple
from datetime import datetime
from zoneinfo import ZoneInfo

from agents.garbage.schema import AgentInput, AgentOutput, GarbageRequest
from agents.garbage import agent as garbage_agent

JST = ZoneInfo("Asia/Tokyo")

def route(thread_id: str, user_utterance: str, current_request: GarbageRequest) -> Tuple[AgentOutput, GarbageRequest]:
    """今は常に GarbageAgent に委譲。将来ここでルーティング。"""
    today_iso = datetime.now(JST).date().isoformat()
    ainput = AgentInput(
        thread_id=thread_id,
        user_utterance=user_utterance,
        context_today_iso=today_iso,
        request=current_request,
    )
    out = garbage_agent.run(ainput)

    if hasattr(out, "request") and out.request:
        return out, out.request
    return out, current_request