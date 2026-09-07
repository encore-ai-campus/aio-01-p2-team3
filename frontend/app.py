from __future__ import annotations

import streamlit as st

from common import (
    apply_style,
    init_session,
    persist_navigation_to_url,
    render_sidebar,
    restore_navigation_from_url,
)
from pages import care_page, chat_page, home_page, login_page, profile_page


st.set_page_config(page_title="Baby Care", page_icon="👶", layout="wide")
init_session()
restore_navigation_from_url()
apply_style()

if st.session_state.pending_notice:
    message = "10분 후 다시 알려드릴게요." if st.session_state.pending_notice == "snooze" else "이번 알림은 건너뛰었어요."
    st.toast(message)
    st.session_state.pending_notice = ""

if not st.session_state.logged_in:
    # 로그인 화면에는 Streamlit 기본 사이드바가 필요하지 않습니다.
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { display: none; }
        [data-testid="stSidebarCollapsedControl"] { display: none; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    login_page.render()
else:
    menu = render_sidebar()
    if menu == "홈":
        home_page.render()
    elif menu == "AI 육아 도우미":
        chat_page.render()
    elif menu == "육아 관리":
        care_page.render()
    elif menu == "내 정보":
        profile_page.render()

    # 현재 메뉴를 URL에 남겨 브라우저 새로고침 뒤에도 같은 화면을 연다.
    persist_navigation_to_url()
