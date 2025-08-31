from __future__ import annotations
from langchain.tools import tool
from datetime import datetime, date as ddate
from zoneinfo import ZoneInfo
import datetime as _dt
import dateparser
from typing import Dict

JST = ZoneInfo("Asia/Tokyo")

@tool
def resolve_date(text: str, base_date: str) -> str:
    """相対/曖昧な日本語日付をYYYY-MM-DDに変換する。
    入力:
      - text: 例『来週金曜』『明後日』『8/30』
      - base_date: 基準日(YYYY-MM-DD, JST)
    失敗時は空文字を返す。
    """
    try:
        base = ddate.fromisoformat(base_date)
    except Exception:
        base = datetime.now(JST).date()
    dt = dateparser.parse(
        text, languages=["ja"],
        settings={
            "PREFER_DATES_FROM": "future",
            "RELATIVE_BASE": datetime(base.year, base.month, base.day),
            "TIMEZONE": "Asia/Tokyo",
            "RETURN_AS_TIMEZONE_AWARE": False,
        }
    )
    return dt.date().isoformat() if dt else ""

@tool
def check_collectible(date_iso: str, address: str) -> str:
    """
    ごみの収集可能日を返す。住所（address）と希望日（preferred_date）が揃っている場合のみ使用可能。
    入力: {"address": "住所", "preferred_date": "YYYY-MM-DD"}
    出力: 'ok' または 'ng:理由'（短文）
    """
    try:
        d = _dt.date.fromisoformat(date_iso)
    except Exception:
        return "ng: 日付形式エラー"
    if d.weekday() == 6:
        return "ng: 日曜日は回収不可です"
    if (d.month, d.day) in {(1,1), (12,31)}:
        return "ng: 祝日/年末年始は回収不可です"
    return "ok"

_PRICE_TABLE: Dict[str,int] = {"ソファ": 1200, "マットレス": 800, "机": 700, "椅子": 300}

@tool
def estimate_fee(item_description: str, quantity: int, size_hint: str = "") -> dict:
    """料金概算を返す。未知品目は500円。
    入力: item_description, quantity, size_hint(任意)"""
    unit = _PRICE_TABLE.get(item_description, 500)
    qty = max(1, int(quantity or 1))
    return {"unit": unit, "subtotal": unit * qty, "notes": ""}

@tool
def rag_search(query: str) -> str:
    """
    FAQ検索。ユーザーとの会話の中で、制度・ルールの質問があった際に使う。
    入力: 質問文の全文
    """
    if "サイズ" in query or "大きさ" in query:
        return "最大辺が2mを超えるものは個別相談となります。詳しくは市の案内をご参照ください。"
    return "市の粗大ごみ案内ページをご確認ください。"

@tool
def reserve(req_json: dict) -> dict:
    """予約実行。ユーザーに聴取内容を最終確認した後にのみ使用する。"""
    import uuid
    return {
        "confirmation_id": f"G{uuid.uuid4().hex[:8].upper()}",
        "date": req_json.get("preferred_date"),
        "time_slot": req_json.get("time_slot"),
        "address": req_json.get("address"),
        "item": req_json.get("item_description"),
        "quantity": req_json.get("quantity"),
        "pickup_location": req_json.get("pickup_location"),
        "contact": req_json.get("phone"),
        "applicant": req_json.get("name"),
    }