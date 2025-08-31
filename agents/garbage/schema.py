from __future__ import annotations
from typing import Optional, List, Literal, Union
from pydantic import BaseModel, Field

class GarbageRequest(BaseModel):
    name: Optional[str] = Field(None, description="カタカナ氏名")
    address: Optional[str] = Field(None, description="市区町村〜番地")
    phone: Optional[str] = Field(None, description="数字のみ")
    item_description: Optional[str] = Field(None, description="品目")
    quantity: Optional[int] = Field(None, description="個数")
    preferred_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    time_slot: Optional[str] = Field(None, description="午前/午後")
    pickup_location: Optional[str] = Field(None, description="自宅前/集合所")
    notes: Optional[str] = None

REQUIRED_FIELDS: List[str] = [
    "name","address","phone","item_description","quantity",
    "preferred_date","time_slot","pickup_location"
]

class FeeQuote(BaseModel):
    unit: int
    subtotal: int
    notes: Optional[str] = ""

class AgentInput(BaseModel):
    thread_id: str
    user_utterance: str
    context_today_iso: str
    request: GarbageRequest

class AgentAsk(BaseModel):
    kind: Literal["ask"] = "ask"
    message: str
    missing: List[str]
    next_field: str         # 次に聞くフィールド
    request: GarbageRequest # ここまでに埋まったフィールドの最新値

class AgentReview(BaseModel):
    kind: Literal["review"] = "review"
    message: str
    request: GarbageRequest
    fee: Optional[FeeQuote] = None

class AgentAnswer(BaseModel):
    kind: Literal["answer"] = "answer"
    message: str
    request: GarbageRequest | None = None

class AgentError(BaseModel):
    kind: Literal["error"] = "error"
    message: str

AgentOutput = Union[AgentAsk, AgentReview, AgentAnswer, AgentError]
