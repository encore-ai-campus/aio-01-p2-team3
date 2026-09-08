from __future__ import annotations

from uuid import uuid4

import streamlit as st

import api
from common import render_feeding_reminder


def _send(message: str) -> None:
    st.session_state.chat_messages.append(("user", message))
    response = api.send_chat(message, st.session_state.baby_id, st.session_state.session_id, st.session_state.user_id)
    if not response["success"]:
        st.session_state.chat_messages.append(("ai", response["message"]))
        return
    answer = response["data"]
    source_text = ""
    if answer.get("sources"):
        source_text = "\n\n📚 " + " · ".join(source["title"] for source in answer["sources"][:3])
    if answer.get("safety_notice"):
        source_text += "\n\n⚠️ " + answer["safety_notice"]
    st.session_state.chat_messages.append(("ai", answer["answer"] + source_text))


def _save_quick_record(event_type: str, payload: dict) -> None:
    payload.update({"baby_id": st.session_state.baby_id, "event_type": event_type, "input_source": "ui", "idempotency_key": str(uuid4())})
    response = api.create_care_log(payload, st.session_state.user_id, st.session_state.session_id)
    st.session_state.quick_record_notice = response["message"]
    if response["success"]:
        st.session_state.quick_record_type = None
    else:
        st.session_state.quick_record_notice = "저장하지 못했습니다: " + response["message"]


def _render_quick_record_form() -> None:
    kind = st.session_state.quick_record_type
    if not kind:
        return
    labels = {"feeding": "수유", "sleep": "수면", "diaper": "배변"}
    with st.form(f"quick_{kind}", border=True):
        st.markdown(f"#### 빠른 {labels[kind]} 기록")
        if kind == "feeding":
            feeding = st.selectbox("수유 방식", ["분유", "모유", "혼합"])
            amount = st.number_input("수유량(ml) · 모유는 비워둘 수 있어요", min_value=0, max_value=500, value=0)
            submitted = st.form_submit_button("수유 기록 저장", type="primary")
            if submitted:
                mapping = {"분유": "formula", "모유": "breast", "혼합": "mixed"}
                _save_quick_record("feeding", {"feeding_type": mapping[feeding], "amount_ml": None if feeding == "모유" and amount == 0 else int(amount)})
                st.rerun()
        elif kind == "sleep":
            action = st.radio("수면 상태", ["start", "end"], format_func=lambda value: "수면 시작" if value == "start" else "수면 종료", horizontal=True)
            if st.form_submit_button("수면 기록 저장", type="primary"):
                _save_quick_record("sleep", {"action": action})
                st.rerun()
        else:
            urine = st.checkbox("소변", value=True)
            stool = st.checkbox("대변")
            color = st.text_input("색상 (선택)")
            consistency = st.text_input("형태 (선택)")
            if st.form_submit_button("배변 기록 저장", type="primary"):
                if not urine and not stool:
                    st.warning("소변 또는 대변을 하나 이상 선택해 주세요.")
                else:
                    _save_quick_record("diaper", {"urine": urine, "stool": stool, "color": color or None, "consistency": consistency or None})
                    st.rerun()
        if st.form_submit_button("취소"):
            st.session_state.quick_record_type = None
            st.rerun()


def render() -> None:
    baby = api.get_baby(st.session_state.baby_id)["data"]
    topic_questions = {
        "feeding": "서아의 최근 기록을 기준으로 수유량과 수유 간격을 알려주세요.",
        "sleep": "서아의 월령에 맞는 수면 시간과 수면 패턴을 알려주세요.",
        "hospital": "서아와 가까운 소아과를 찾는 방법을 알려주세요.",
        "weaning": "서아의 월령에 맞는 이유식 시작 시기와 준비 방법이 궁금해요.",
    }
    topic = st.session_state.chat_topic
    if topic in topic_questions and st.session_state.applied_chat_topic != topic:
        _send(topic_questions[topic])
        st.session_state.applied_chat_topic = topic
    st.markdown(f"<div class='page-title'>{baby['baby_name']}의 AI 육아 도우미</div><div class='page-subtitle' style='margin-bottom:.25rem'>생후 {baby['age_days']}일 · {baby['current_weight_kg']}kg · {baby['feeding_type']} 수유</div><div style='color:#20A26B;font-size:.82rem;margin-bottom:.8rem'>● 아기 정보를 반영하고 있어요</div>", unsafe_allow_html=True)
    render_feeding_reminder({})

    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True):
        # 고정 높이 영역으로 메시지가 길어져도 하단 정보 카드가 밀리지 않게 합니다.
        with st.container(height=400):
            if not st.session_state.chat_messages:
                st.markdown("<div class='chat-ai'>안녕하세요! 서아는 오늘 생후 30일이에요. 수유·수면·배변을 간단히 기록하거나, 월령에 맞는 육아 정보를 물어보세요.</div>", unsafe_allow_html=True)
                st.markdown("<div class='chat-user'>생후 30일 아기는 분유를 얼마나 먹나요?</div>", unsafe_allow_html=True)
                st.markdown("<div class='chat-ai'>생후 30일 아기의 수유량은 아기마다 달라요. 서아의 최근 수유와 배고픔 신호를 함께 보세요.<br><span class='muted'>📚 공식 육아정보 기반 · 이가 추천됨</span></div>", unsafe_allow_html=True)
            else:
                for sender, message in st.session_state.chat_messages[-4:]:
                    css = "chat-user" if sender == "user" else "chat-ai"
                    st.markdown(f"<div class='{css}'>{message}</div>", unsafe_allow_html=True)

        chips = st.columns(4)
        for column, label in zip(chips, ["🍼 월령별 수유", "▣ 기저귀 사진 분석", "🏥 주변 소아과", "🍚 이유식 궁금증"]):
            if column.button(label, use_container_width=True):
                _send(label)
                st.rerun()

        input_col, send_col = st.columns([8, 1])
        prompt = input_col.text_input("채팅 입력", placeholder="육아 기록이나 궁금한 점을 입력하세요", label_visibility="collapsed")
        if send_col.button("↑", type="primary", use_container_width=True) and prompt.strip():
            _send(prompt.strip())
            st.rerun()

    # 빠른 기록 폼은 하단 카드 내부가 아니라 채팅 바로 아래에 표시합니다.
    # 버튼 클릭 뒤 rerun해 Streamlit 위젯 상태가 확실히 반영되도록 합니다.
    _render_quick_record_form()
    if st.session_state.quick_record_notice:
        st.success(st.session_state.quick_record_notice)
        st.session_state.quick_record_notice = ""

    st.markdown("<br>", unsafe_allow_html=True)
    left, right = st.columns([1, 1.35])
    with left:
        with st.container(border=True):
            st.markdown("<div class='section-title'>빠른 기록</div>", unsafe_allow_html=True)
            quick = st.columns(3)
            if quick[0].button("🍼 수유", use_container_width=True):
                st.session_state.quick_record_type = "feeding"
                st.rerun()
            if quick[1].button("🌙 수면", use_container_width=True):
                st.session_state.quick_record_type = "sleep"
                st.rerun()
            if quick[2].button("💩 배변", use_container_width=True):
                st.session_state.quick_record_type = "diaper"
                st.rerun()
    with right:
        with st.container(border=True):
            st.markdown("<div class='section-title'>AI가 참고 중인 정보</div>", unsafe_allow_html=True)
            rows = [("월령", f"생후 {baby['age_days']}일"), ("몸무게", f"{baby['current_weight_kg']}kg"), ("수유 방식", baby["feeding_type"]), ("특이사항", f"{', '.join(baby['allergies'])} 알레르기")]
            info_rows = "".join(
                f"<div class='ai-reference-row'><span>{label}</span><b>{value}</b></div>"
                for label, value in rows
            )
            st.markdown(
                f"<style>.ai-reference-row{{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:.5rem 0;color:#778198;font-size:.88rem}}.ai-reference-row b{{color:#202737;text-align:right;font-size:.88rem;white-space:nowrap}}</style>{info_rows}",
                unsafe_allow_html=True,
            )
