from __future__ import annotations
from typing import Dict, Any
from agents.garbage.schema import GarbageRequest

# デモ用のインメモリストア（本番はDBに差し替え）
class InMemoryStore:
    def __init__(self):
        self._threads: Dict[str, Dict[str, Any]] = {}
    
    def list_thread_ids(self):
        return list(self._threads.keys())

    def create_thread(self, thread_id: str):
        self._threads[thread_id] = {
            "messages": [],
            "request": GarbageRequest(),
            "pending_confirmation": False,
            "last_review_text": "",
        }

    def get_thread(self, thread_id: str) -> Dict[str, Any]:
        return self._threads[thread_id]

    def set_request(self, thread_id: str, req: GarbageRequest):
        self._threads[thread_id]["request"] = req

    def add_message(self, thread_id: str, role: str, content: str):
        self._threads[thread_id]["messages"].append((role, content))
    