import os
import uuid
from datetime import datetime
import re
from zoneinfo import ZoneInfo
import streamlit as st

from memory.store import InMemoryStore
from orchestrator.router import route
from agents.common.tools import reserve
from agents.garbage.schema import GarbageRequest, AgentReview

JST = ZoneInfo("Asia/Tokyo")

# 判定（正規表現→曖昧は LLM フォールバックでもよいが、ここでは軽量に）
AFFIRM = re.compile(r"^(はい|OK|オーケー|承認|問題ない|大丈夫|了解|お願いします|実行|yes|ok)$", re.IGNORECASE)
NEG    = re.compile(r"^(いいえ|NO|だめ|修正|変更|やめる|保留|キャンセル|cancel)$", re.IGNORECASE)

st.set_page_config(page_title="粗大ごみ収集エージェント（シングル）", page_icon="🗑️", layout="centered")
st.title("🗑️ 粗大ごみ収集エージェント（シングル）")

# 共有ストア（セッション跨ぎで1つ持つ）
if "store" not in st.session_state:
    st.session_state.store = InMemoryStore()
store = st.session_state.store

with st.sidebar:
    st.subheader("スレッド管理")
    if "current_thread" not in st.session_state:
        st.session_state.current_thread = None
    existing = store.list_thread_ids()

    mode = st.radio("スレッド操作", ["新規作成", "選択して再開"], horizontal=True)
    if mode == "新規作成":
        if st.button("新しいスレッドを作成"):
            tid = datetime.now(JST).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
            store.create_thread(tid)
            st.session_state.current_thread = tid
            st.rerun()
    else:
        if existing:
            pick = st.selectbox("スレッドを選択", existing)
            if st.button("このスレッドを開く"):
                st.session_state.current_thread = pick
                st.rerun()
        else:
            st.info("スレッドがまだありません。新規作成してください。")

thread_id = st.session_state.get("current_thread")
if not thread_id:
    st.stop()

st.caption(f"スレッドID: `{thread_id}`")
thread = store.get_thread(thread_id)
messages = thread["messages"]
current_req: GarbageRequest = thread["request"]

# 既存メッセージ表示
for role, content in messages:
    with st.chat_message(role):
        st.markdown(content)

# 入力
user_input = st.chat_input("ご用件をどうぞ。例：「来週火曜にソファ1点を自宅前で回収してほしい」")
if user_input:
    store.add_message(thread_id, "user", user_input)
    with st.chat_message("user"):
        st.markdown(user_input)

    # 確認待ちか？
    if thread.get("pending_confirmation"):
        if AFFIRM.match(user_input.strip()):
            # 予約実行
            c = reserve.invoke({"req_json": current_req.model_dump()})
            text = (
                "【✅ 予約完了】\n"
                f"  受付番号：{c['confirmation_id']}\n"
                f"  回収日　：{c['date']}（{c['time_slot']}）\n"
                f"  回収物　：{c['item']} × {c['quantity']}点\n"
                f"  回収場所：{c['pickup_location']}（{c['address']}）\n"
                f"  申込者　：{c['applicant']}（連絡先：{c['contact']}）\n"
            )
            store.add_message(thread_id, "assistant", text)
            with st.chat_message("assistant"):
                st.markdown(text)
            thread["pending_confirmation"] = False
            thread["last_review_text"] = ""
            st.stop()
        elif NEG.match(user_input.strip()):
            msg = "どの項目を修正しますか？ 例：「希望日を2025-08-19に」「回収場所は集合所に」"
            store.add_message(thread_id, "assistant", msg)
            with st.chat_message("assistant"):
                st.markdown(msg)
            thread["pending_confirmation"] = False
            st.stop() # 再確認
        else:
            reprompt = thread.get("last_review_text","") + "\n"
            reprompt += "すみません、『はい』または『いいえ』でご回答ください。"
            store.add_message(thread_id, "assistant", reprompt)
            with st.chat_message("assistant"):
                st.markdown(reprompt)
            st.stop() # 再確認

    # オーケストレータ経由でエージェント実行
    out, new_req = route(thread_id, user_input, current_req)
    thread["request"] = new_req
    current_req = new_req

    # エージェント出力に応じて表示
    if out.kind == "ask":
        store.add_message(thread_id, "assistant", out.message)
        with st.chat_message("assistant"):
            st.markdown(out.message)

    elif out.kind == "answer":
        store.add_message(thread_id, "assistant", out.message)
        with st.chat_message("assistant"):
            st.markdown(out.message)

    elif out.kind == "review":
        # レビューを提示して Yes/No を待つ（予約は UI 側）
        store.add_message(thread_id, "assistant", out.message)
        with st.chat_message("assistant"):
            st.markdown(out.message)
        thread["pending_confirmation"] = True
        thread["last_review_text"] = out.message

    else:  # error
        store.add_message(thread_id, "assistant", out.message)
        with st.chat_message("assistant"):
            st.markdown(out.message)

with st.sidebar:
    st.divider()
    st.subheader("現在の申込情報")
    st.json(current_req.model_dump())