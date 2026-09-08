from __future__ import annotations

import time

import streamlit as st

import api


def _save_feeding(baby: dict, amount_ml: int) -> None:
    result = api.create_care_log(
        baby["baby_id"],
        amount_ml=amount_ml,
        feeding_type=baby["feeding_type"],
        session_id=st.session_state.session_id,
    )
    if result["success"]:
        st.session_state.chat_messages.append(("user", f"{amount_ml}ml"))
        st.session_state.chat_messages.append(("ai", result["message"]))
        st.session_state.feeding_save_message = ""
        st.session_state.show_feeding_amount_options = False
    else:
        st.session_state.feeding_save_message = result.get("message", "수유 기록을 저장하지 못했습니다.")


def _approve_stt_record(baby: dict) -> None:
    pending = st.session_state.pending_stt_record
    if not pending:
        return
    result = api.create_care_log(
        baby["baby_id"],
        amount_ml=pending["amount_ml"],
        feeding_type=pending["feeding_type"],
        session_id=st.session_state.session_id,
        input_source="stt",
        confirmed_by_user=True,
        idempotency_key=pending["idempotency_key"],
    )
    if result["success"]:
        st.session_state.chat_messages.append(("user", pending["transcript"]))
        st.session_state.chat_messages.append(("ai", result["message"]))
        st.session_state.pending_stt_record = None
    else:
        st.error(result.get("message", "음성 기록을 저장하지 못했습니다."))


def _cancel_stt_record() -> None:
    st.session_state.pending_stt_record = None
    st.session_state.voice_transcript = ""
    st.session_state.last_voice_audio_signature = ""
    st.session_state.voice_recording_counter += 1


def _format_feeding_interval(minutes: int) -> str:
    hours, remainder = divmod(minutes, 60)
    if hours and remainder:
        return f"{hours}시간 {remainder}분"
    if hours:
        return f"{hours}시간"
    return f"{remainder}분"


def _skip_feeding_reminder() -> None:
    interval = _format_feeding_interval(st.session_state.feeding_interval_minutes)
    st.session_state.chat_messages.append(
        ("ai", f"이번 알람은 건너뛰겠습니다. {interval} 후에 다시 알람을 드릴게요.")
    )
    st.session_state.feeding_reminder_status = "skipped"


def _snooze_feeding_reminder() -> None:
    """시연에서는 10초 뒤 알림을 다시 표시한다."""
    st.session_state.chat_messages.append(("ai", "10분 뒤에 다시 알려드릴게요."))
    st.session_state.show_feeding_amount_options = False
    st.session_state.feeding_reminder_status = "snoozed"
    st.session_state.feeding_snooze_until = time.time() + 10


@st.fragment(run_every=1)
def _render_chat_feeding_reminder(baby: dict) -> None:
    """AI 육아 도우미용 수유 알림과 수유량 선택·저장 흐름을 표시한다."""
    if st.session_state.feeding_reminder_status == "skipped":
        return
    if st.session_state.feeding_reminder_status == "snoozed":
        if time.time() < (st.session_state.feeding_snooze_until or 0):
            st.empty()
            return
        st.session_state.feeding_reminder_status = "active"
        st.session_state.feeding_snooze_until = None
    with st.container(border=True):
        st.markdown(
            "<div class='soft-panel' style='margin:0 0 .7rem'>"
            "<b>🍼 마지막 수유 후 3시간이 지났어요</b>"
            "<div class='assistant-reminder-sub'>서아의 배고픔 신호를 확인해 주세요.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<style>"
            "@media(max-width:700px){"
            "[data-testid='stHorizontalBlock']:has(.st-key-chat_feeding_done){flex-wrap:nowrap!important;gap:.35rem!important}"
            "[data-testid='stHorizontalBlock']:has(.st-key-chat_feeding_done)>[data-testid='stColumn']{min-width:0!important;width:auto!important}"
            "[data-testid='stHorizontalBlock']:has(.st-key-chat_feeding_done) button{font-size:.78rem!important;padding:.45rem .2rem!important;white-space:nowrap}"
            "}"
            "</style>",
            unsafe_allow_html=True,
        )
        action_cols = st.columns(3)
        if action_cols[0].button("수유했어요", key="chat_feeding_done", type="primary", use_container_width=True):
            st.session_state.show_feeding_amount_options = True
            st.session_state.feeding_save_message = ""
            st.rerun()
        if action_cols[1].button("10분 후", key="chat_feeding_snooze", use_container_width=True):
            _snooze_feeding_reminder()
            st.rerun()
        if action_cols[2].button("건너뛰기", key="chat_feeding_skip", use_container_width=True):
            _skip_feeding_reminder()
            st.rerun()

    if st.session_state.feeding_save_message:
        st.success(st.session_state.feeding_save_message)


def _send(message: str) -> None:
    st.session_state.chat_messages.append(("user", message))
    response = api.send_chat(
        message,
        baby_id=st.session_state.baby_id,
        session_id=st.session_state.session_id,
    )
    if response["success"]:
        answer = response["data"]
        st.session_state.chat_messages.append(("ai", answer.get("answer", response.get("message", "답변을 준비하지 못했습니다."))))
    else:
        st.session_state.chat_messages.append(("ai", response.get("message", "채팅 요청을 처리하지 못했습니다.")))


def _send_draft() -> None:
    """입력창 내용을 보내고 다음 메시지를 위해 비운다."""
    draft = st.session_state.chat_draft.strip()
    if draft:
        _send(draft)
        st.session_state.chat_draft = ""


def render() -> None:
    baby = api.get_baby(st.session_state.baby_id)["data"]
    st.session_state.setdefault("show_diaper_capture", False)
    topic_questions = {
        "feeding": "서아의 최근 기록을 기준으로 수유량과 수유 간격을 알려주세요.",
        "sleep": "서아의 월령에 맞는 수면 시간과 수면 패턴을 알려주세요.",
        "hospital": "서아와 가까운 소아과를 찾는 방법을 알려주세요.",
        "weaning": "서아의 월령에 맞는 이유식 시작 시기와 준비 방법이 궁금해요.",
    }
    topic = st.session_state.chat_topic
    if topic == "diaper" and st.session_state.applied_chat_topic != topic:
        st.session_state.show_diaper_capture = True
        st.session_state.applied_chat_topic = topic
    elif topic == "hospital" and st.session_state.applied_chat_topic != topic:
        st.session_state.show_hospital_search = True
        st.session_state.applied_chat_topic = topic
    elif topic in topic_questions and st.session_state.applied_chat_topic != topic:
        _send(topic_questions[topic])
        st.session_state.applied_chat_topic = topic
    st.markdown(f"<div class='page-title'>{baby['baby_name']}의 AI 육아 도우미</div><div class='page-subtitle' style='margin-bottom:.25rem'>생후 {baby['age_days']}일 · {baby['current_weight_kg']}kg · {baby['feeding_type']} 수유</div><div style='color:#20A26B;font-size:.82rem;margin-bottom:.8rem'>● 아기 정보를 반영하고 있어요</div>", unsafe_allow_html=True)
    _render_chat_feeding_reminder(baby)

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

            pending_stt = st.session_state.pending_stt_record
            if pending_stt:
                st.markdown(f"<div class='chat-user'>{pending_stt['transcript']}</div>", unsafe_allow_html=True)
                st.markdown(
                    "<div class='chat-ai'><b>내용을 확인해 주세요. DB에 저장됩니다.</b><br>"
                    f"{pending_stt['feeding_type']} {pending_stt['amount_ml']}ml를 기록할까요?</div>",
                    unsafe_allow_html=True,
                )
                approve_col, cancel_col, _ = st.columns([1, 1, 3])
                if approve_col.button("승인", key="approve_stt_record", type="primary", use_container_width=True):
                    _approve_stt_record(baby)
                    st.rerun()
                if cancel_col.button("취소", key="cancel_stt_record", use_container_width=True):
                    _cancel_stt_record()
                    st.rerun()

            if st.session_state.show_feeding_amount_options:
                st.markdown(
                    "<div class='chat-ai'><b>수유량을 선택해 주세요.</b><br>"
                    "선택하면 수유 기록으로 저장됩니다.</div>",
                    unsafe_allow_html=True,
                )
                amount_cols = st.columns(4)
                for column, amount in zip(amount_cols[:3], (80, 100, 120)):
                    if column.button(f"{amount}ml", key=f"feeding_amount_{amount}", use_container_width=True):
                        _save_feeding(baby, amount)
                        st.rerun()
                with amount_cols[3]:
                    custom_amount = st.number_input(
                        "직접 입력",
                        min_value=1,
                        max_value=2000,
                        value=100,
                        step=10,
                        label_visibility="collapsed",
                        key="custom_feeding_amount",
                    )
                    if st.button("직접 입력", key="save_custom_feeding_amount", use_container_width=True):
                        _save_feeding(baby, int(custom_amount))
                        st.rerun()

            if st.session_state.show_hospital_search:
                st.markdown("<div class='chat-ai'><b>주변 소아과를 찾아드릴게요.</b><br>검색할 지역을 입력해 주세요.</div>", unsafe_allow_html=True)
                hospital_region = st.text_input(
                    "소아과 검색 지역",
                    placeholder="예: 서울특별시 동작구",
                    key="hospital_search_region",
                    label_visibility="collapsed",
                )
                if st.button("소아과 검색", key="search_pediatric_hospitals", use_container_width=True):
                    region = hospital_region.strip()
                    if not region:
                        st.warning("검색할 지역을 입력해 주세요.")
                    else:
                        result = api.search_hospitals(region, hospital_type="pediatric")
                        if result["success"]:
                            data = result["data"]
                            items = data.get("items", data.get("data", []))
                            if items:
                                first = items[0]
                                message = (
                                    f"{first.get('hospital_name', '소아과')}\n"
                                    f"{first.get('address', '')}\n"
                                    f"{first.get('phone', '전화번호 확인 필요')}\n"
                                    f"{data.get('notice', '방문 전 진료 가능 여부를 확인해 주세요.')}"
                                )
                            else:
                                message = f"{region}에서 검색된 소아과가 없어요. 지역명을 다시 확인해 주세요."
                            st.session_state.chat_messages.append(("user", f"{region} 주변 소아과를 찾아줘"))
                            st.session_state.chat_messages.append(("ai", message))
                            st.session_state.show_hospital_search = False
                            st.rerun()
                        else:
                            st.error(result.get("message", "소아과 검색을 처리하지 못했습니다."))

        topic_links = [
            ("feeding", "🍼 월령별 수유"),
            ("diaper", "▣ 기저귀 사진 분석"),
            ("hospital", "🏥 주변 소아과"),
            ("weaning", "🍚 이유식 궁금증"),
        ]
        links = "".join(
            "<a class='chat-topic-link' target='_self' "
            f"href='?demo=1&amp;page=AI%20%EC%9C%A1%EC%95%84%20%EB%8F%84%EC%9A%B0%EB%AF%B8&amp;topic={topic}'>{label}</a>"
            for topic, label in topic_links
        )
        st.markdown(
            "<style>"
            ".chat-topic-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:.45rem 0 .7rem}"
            ".chat-topic-link,.chat-topic-link:link,.chat-topic-link:visited{display:block;box-sizing:border-box;width:100%;text-align:center;text-decoration:none!important;color:#202737;background:#fff;border:1px solid #DFE4F1;border-radius:9px;padding:9px 6px;font-size:13px}"
            ".chat-topic-link:hover{border-color:#6374DC;color:#6374DC;background:#EEF1FF}"
            "@media(max-width:700px){.chat-topic-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.chat-topic-link{font-size:13px;padding:10px 5px}}"
            "</style>"
            f"<div class='chat-topic-grid'>{links}</div>",
            unsafe_allow_html=True,
        )

        if st.session_state.show_diaper_capture:
            st.markdown("<div class='notice'>사진을 올리면 AI가 색상·형태 등 관찰 가능한 정보를 분석해 알려드려요. 사진만으로 육아 기록이 자동 저장되지는 않습니다.</div>", unsafe_allow_html=True)
            camera_col, file_col = st.columns(2)
            with camera_col:
                camera_photo = st.camera_input("📷 카메라 촬영", key="diaper_camera")
            with file_col:
                selected_photo = st.file_uploader("🖼 사진 선택", type=["jpg", "jpeg", "png", "webp"], key="diaper_file")
            photo = camera_photo or selected_photo
            if photo is not None:
                st.image(photo, caption="선택한 기저귀 사진", use_container_width=True)
                signature = f"{getattr(photo, 'name', 'diaper')}:{getattr(photo, 'size', 0)}"
                if signature != st.session_state.last_diaper_signature:
                    result = api.analyze_diaper_image(
                        photo,
                        baby_id=baby["baby_id"],
                        age_days=baby["age_days"],
                        feeding_type=baby["feeding_type"],
                    )
                    if result["success"]:
                        st.session_state.diaper_analysis_result = result["data"]
                        st.session_state.last_diaper_signature = signature
                    else:
                        st.error(result.get("message", "사진을 분석하지 못했습니다."))

                analysis = st.session_state.diaper_analysis_result
                if analysis:
                    if analysis.get("is_analyzable"):
                        observation = analysis.get("observation", {})
                        risk = analysis.get("risk", {})
                        signals = ", ".join(risk.get("signals", [])) or "특별한 주의 신호 없음"
                        st.markdown(
                            "<div class='chat-ai'><b>🔎 AI 기저귀 사진 분석</b><br>"
                            f"관찰: {observation.get('color', '확인 필요')} · {observation.get('consistency', '확인 필요')}<br>"
                            f"주의 신호: {signals}<br>"
                            f"{risk.get('recommended_action', '')}<br>"
                            f"<span class='muted'>{analysis.get('safety_notice', '')}</span></div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        issues = ", ".join(analysis.get("quality_issues", [])) or "사진 품질을 확인해 주세요."
                        st.warning(f"사진을 분석하기 어려워요. {issues}")
            if st.button("사진 선택 닫기", key="close_diaper_capture"):
                st.session_state.show_diaper_capture = False
                st.session_state.diaper_analysis_result = None
                st.session_state.last_diaper_signature = ""
                st.rerun()

        st.markdown(
            "<style>"
            "@media(max-width:700px){"
            "[data-testid='stHorizontalBlock']:has(.st-key-chat_send_message){flex-wrap:wrap!important;gap:.55rem!important}"
            "[data-testid='stHorizontalBlock']:has(.st-key-chat_send_message)>[data-testid='stColumn']{min-width:0!important}"
            "[data-testid='stHorizontalBlock']:has(.st-key-chat_send_message)>[data-testid='stColumn']:first-child{flex:0 0 100%!important;width:100%!important}"
            "[data-testid='stHorizontalBlock']:has(.st-key-chat_send_message)>[data-testid='stColumn']:nth-child(2),[data-testid='stHorizontalBlock']:has(.st-key-chat_send_message)>[data-testid='stColumn']:nth-child(3){flex:1 1 0!important;width:calc(50% - .3rem)!important}"
            "}"
            "</style>",
            unsafe_allow_html=True,
        )
        input_col, voice_col, send_col = st.columns([7, 1, 1])
        input_col.text_input(
            "채팅 입력",
            key="chat_draft",
            placeholder="육아 기록이나 궁금한 점을 입력하세요",
            label_visibility="collapsed",
        )
        with voice_col:
            with st.popover("🎙️", help="음성으로 입력", use_container_width=True):
                st.markdown("**음성으로 말하기**")
                st.caption("녹음한 내용은 바로 전송·저장되지 않으며, 아래에서 확인하고 수정할 수 있어요.")
                audio_input = getattr(st, "audio_input", None)
                if audio_input is None:
                    st.warning("현재 Streamlit 버전에서는 음성 녹음을 지원하지 않습니다.")
                else:
                    audio = audio_input(
                        "음성 녹음",
                        key=f"chat_voice_recording_{st.session_state.voice_recording_counter}",
                        label_visibility="collapsed",
                    )
                    if audio is not None:
                        signature = f"{getattr(audio, 'name', 'voice')}:{getattr(audio, 'size', 0)}"
                        if signature != st.session_state.last_voice_audio_signature:
                            result = api.transcribe_audio(audio, baby["baby_id"], st.session_state.session_id)
                            if result["success"]:
                                data = result["data"]
                                snapshot = data.get("approval_snapshot", {})
                                if data.get("response_type") == "stt_record_approval" and snapshot.get("event_type") == "feeding":
                                    st.session_state.pending_stt_record = {
                                        "transcript": data.get("transcript", ""),
                                        "amount_ml": int(snapshot.get("amount_ml", 0)),
                                        "feeding_type": snapshot.get("feeding_type", baby["feeding_type"]),
                                        "tool_call_id": data.get("tool_call_id"),
                                        "idempotency_key": f"{st.session_state.session_id}-{data.get('tool_call_id', 'stt')}",
                                    }
                                else:
                                    st.session_state.voice_transcript = data.get("transcript", "")
                                st.session_state.last_voice_audio_signature = signature
                                st.rerun()
                            else:
                                st.error(result.get("message", "음성을 텍스트로 바꾸지 못했습니다."))
                    st.caption("녹음 후 인식된 문장이 채팅창에 표시됩니다. 내용이 맞을 때만 승인해 주세요.")
        send_col.button("↑", key="chat_send_message", type="primary", use_container_width=True, on_click=_send_draft)

    st.markdown("<br>", unsafe_allow_html=True)
    left, right = st.columns([1, 1.35])
    with left:
        with st.container(border=True):
            st.markdown("<div class='section-title'>빠른 기록</div>", unsafe_allow_html=True)
            quick = st.columns(3)
            for column, record_type, label in zip(
                quick,
                ("feeding", "sleep", "diaper"),
                ("🍼 수유", "🌙 수면", "💩 배변"),
            ):
                if column.button(label, key=f"quick_record_{record_type}", use_container_width=True):
                    st.session_state.editing_record_index = {"feeding": 0, "sleep": 1, "diaper": 2}[record_type]
                    st.session_state.selected_menu = "육아 관리"
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
