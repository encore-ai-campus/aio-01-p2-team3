from __future__ import annotations

import streamlit as st

import api
from common import render_feeding_reminder


def _send(message: str) -> None:
    st.session_state.chat_messages.append(("user", message))
    answer = api.send_chat(message)["data"]
    st.session_state.chat_messages.append(("ai", answer["answer"]))


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

    st.markdown("<br>", unsafe_allow_html=True)
    left, right = st.columns([1, 1.35])
    with left:
        with st.container(border=True):
            st.markdown("<div class='section-title'>빠른 기록</div>", unsafe_allow_html=True)
            quick = st.columns(3)
            quick[0].button("🍼 수유", use_container_width=True)
            quick[1].button("🌙 수면", use_container_width=True)
            quick[2].button("💩 배변", use_container_width=True)
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
