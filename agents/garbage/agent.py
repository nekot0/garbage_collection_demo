from __future__ import annotations
from functools import lru_cache
import os
import re
import json
from datetime import date
from typing import List
from zoneinfo import ZoneInfo

from langchain_openai import AzureChatOpenAI
from langchain.agents import create_tool_calling_agent, create_react_agent, AgentExecutor
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException
from langchain.tools.render import render_text_description
from pydantic import BaseModel

from .schema import (
    GarbageRequest, AgentInput, AgentOutput,
    AgentAsk, AgentReview, AgentAnswer, AgentError,
    REQUIRED_FIELDS, FeeQuote
)
from .prompts import make_extract_prompt, agent_system
from agents.common.tools import resolve_date, check_collectible, estimate_fee, rag_search
from agents.common.llm_factory import get_llm, get_llm_json

from dotenv import load_dotenv
load_dotenv()

JST = ZoneInfo("Asia/Tokyo")

PRIORITY = [
    "name", "address", "phone", "item_description", "quantity",
    "preferred_date", "time_slot", "pickup_location", "notes"
]

FIELD_LABEL = {
    "name": "お名前（フルネーム・カタカナ）",
    "address": "ご住所（市区町村〜番地）",
    "phone": "お電話番号（数字のみ）",
    "item_description": "回収物の品目",
    "quantity": "個数（半角数字）",
    "preferred_date": "希望日（YYYY-MM-DD もしくは『来週火曜』でも可）",
    "time_slot": "時間帯（午前/午後）",
    "pickup_location": "回収場所（自宅前/集合所 など）",
}

FIELD_EXAMPLE = {
    "name": "アイウエオ タロウ",
    "address": "大阪市北区中之島1-1-1",
    "phone": "09012345678",
    "item_description": "ソファ",
    "quantity": "1",
    "preferred_date": "2025-08-22",
    "time_slot": "午前",
    "pickup_location": "自宅前",
}

# 出力契約：エージェントが最後に返す“印”と request 同梱
_RESP_KIND = re.compile(r"\[(ASK|REVIEW|ANSWER)\]")
_REQ_BLOCK = re.compile(r"\[REQUEST_JSON\](.*?)\[/REQUEST_JSON\]", re.DOTALL)


# ===== LLM 初期化 =====
@lru_cache(maxsize=1)
def _get_llm_json():
    llm = get_llm_json(temperature=0.0)
    if os.getenv("LLM_PROVIDER").lower() == "openai":
        return llm.bind(stream=False)
    return llm

@lru_cache(maxsize=1)
def _get_llm():
    llm = get_llm(temperature=0.2)
    if os.getenv("LLM_PROVIDER").lower() == "openai":
        return llm.bind(stream=False)
    return llm

# ===== 構造化抽出 =====
def _invoke_with_retry(chain, payload, retries=2):
    last = None
    for _ in range(retries + 1):
        try:
            return chain.invoke(payload)
        except OutputParserException as e:
            last = e
    raise last


def extract_fields(user_utterance: str, today_iso: str) -> GarbageRequest:
    parser = PydanticOutputParser(pydantic_object=GarbageRequest)
    prompt = make_extract_prompt(parser.get_format_instructions()).partial(today_iso=today_iso)

    if os.getenv("LLM_PROVIDER").lower() == "openai":
        schema = GarbageRequest.model_json_schema()
        llm = _get_llm_json().bind(
            stream=False,
            extra_body={"guided_json": schema}
        )
    else:
        llm = _get_llm_json()

    chain = prompt | llm | parser
    #return chain.invoke({"user_utterance": user_utterance})
    return _invoke_with_retry(chain, {"user_utterance": user_utterance})


def _merge(base: GarbageRequest, new: GarbageRequest) -> GarbageRequest:
    b = base.model_dump()
    n = new.model_dump()
    for k, v in n.items():
        if v not in (None, "", []):
            b[k] = v
    # 型/形式の軽いバリデーション
    if b.get("phone"):
        b["phone"] = re.sub(r"\D+", "", b["phone"])
    if b.get("quantity") is not None:
        try:
            b["quantity"] = int(b["quantity"])
        except Exception:
            b["quantity"] = None
    # 日付形式チェック
    if b.get("preferred_date"):
        try:
            date.fromisoformat(b["preferred_date"])
        except Exception:
            # 後段で resolve_date に任せるため一旦消しておく
            b["preferred_date"] = None
    return GarbageRequest(**b)


def _missing(req: GarbageRequest) -> List[str]:
    return [f for f in REQUIRED_FIELDS if not getattr(req, f)]


# 次に聞く項目を選ぶ
def _pick_next_field(missing: list[str]) -> str:
    # PRIORITY に基づき最初の1つを返す
    for f in PRIORITY:
        if f in missing:
            return f
    # フォールバック（理論上来ない）
    return missing[0]


def _make_question_for(field: str) -> str:
    label = FIELD_LABEL.get(field, field)
    ex = FIELD_EXAMPLE.get(field, "")
    # 丁寧かつ短文、1項目のみ
    msg = f"ありがとうございます。次に **{label}** を教えてください。"
    if ex:
        msg += f"\n例）{ex}"
    # preferred_date は曖昧表現も許容することを追記
    if field == "preferred_date":
        msg += "\n※『来週金曜』などの表現でも大丈夫です。こちらで日付に直します。"
    return msg


def _parse_agent_response(text: str, base_req: GarbageRequest) -> tuple[str, GarbageRequest, str]:
    """エージェントの最終出力から kind / request(JSON) / message を抽出して返す。失敗時はASK扱い。"""
    kind = "ASK"
    m_kind = _RESP_KIND.search(text or "")
    if m_kind:
        kind = m_kind.group(1)

    # デフォルトはベース
    req = base_req
    req_text = ""
    m_req = _REQ_BLOCK.search(text or "")
    if m_req:
        req_text = m_req.group(1).strip()
        try:
            payload = json.loads(req_text)
            req = _merge(base_req, GarbageRequest(**payload))
        except Exception:
            pass

    # kind の行以外をメッセージに
    message = (text or "")
    message = _RESP_KIND.sub("", message)
    message = _REQ_BLOCK.sub("", message)
    message = message.strip()

    return kind, req, message


# ===== エージェント本体 =====
def build_agent_executor() -> AgentExecutor:
    llm = _get_llm()
    tools = [resolve_date, check_collectible, estimate_fee, rag_search]

    tools_str = render_text_description(tools)
    prompt = agent_system.partial(tools=tools_str)

    agent = create_tool_calling_agent(llm, tools, prompt)

    if os.getenv("LLM_PROVIDER").lower() == "openai":
        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3,
            stream_runnable=False,
        )
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=3,
    )


def run(input: AgentInput) -> AgentOutput:
    extracted = extract_fields(input.user_utterance, input.context_today_iso)
    req = _merge(input.request, extracted)
    miss = _missing(req)

    agent = build_agent_executor()

    task = f"""
today_jst: {input.context_today_iso}
request (現時点の値):
{json.dumps(req.model_dump(), indent=2, ensure_ascii=False)}
missing: {", ".join(miss) if miss else "(なし)"}
"""

    result = agent.invoke({
        "input": input.user_utterance,   # ← 重要: {input} に対応
        "context": task,                 # ← prompts側の {context}
    })

    raw = str(result.get("output", "")).strip()
    kind, new_req, message = _parse_agent_response(raw or "", req)

    if not message:
        miss = _missing(new_req)
        next_f = _pick_next_field(miss) if miss else None
        msg = _make_question_for(next_f) if next_f else "内容を理解しました。"
        return AgentAsk(message=msg, missing=miss, next_field=next_f or "", request=new_req)

    if kind == "ASK":
        miss_now = _missing(new_req)
        next_f = _pick_next_field(miss_now) if miss_now else ""
        return AgentAsk(message=message, missing=miss_now, next_field=next_f, request=new_req)

    if kind == "REVIEW":
        fee = None
        if new_req.item_description and new_req.quantity:
            f = estimate_fee.invoke({"item_description": new_req.item_description, "quantity": new_req.quantity})
            fee = FeeQuote(unit=int(f["unit"]), subtotal=int(f["subtotal"]), notes=f.get("notes",""))
        return AgentReview(message=message, request=new_req, fee=fee)

    if kind == "ANSWER":
        return AgentAnswer(message=message)

    miss_now = _missing(new_req)
    next_f = _pick_next_field(miss_now) if miss_now else ""
    return AgentAsk(message=message, missing=miss_now, next_field=next_f, request=new_req)