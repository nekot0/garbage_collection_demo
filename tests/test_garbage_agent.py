import os
import pytest
from datetime import date
from zoneinfo import ZoneInfo
from agents.garbage.schema import AgentInput, GarbageRequest
from agents.garbage.agent import run

JST = ZoneInfo("Asia/Tokyo")

@pytest.mark.skipif(
    not os.getenv("AZURE_OPENAI_API_KEY"),
    reason="Azure OpenAI 環境が未設定"
)
def test_agent_simple_flow():
    req = GarbageRequest()
    today = date.today().isoformat()
    out = run(AgentInput(
        thread_id="t1",
        user_utterance="来週火曜にソファ1点を自宅前で回収してほしい。住所は大阪市北区中之島1-1-1、電話は090-1234-5678、午前希望。名前はアイウエオ タロウ。",
        context_today_iso=today,
        request=req
    ))
    assert out.kind in ("ask","review","answer","error")