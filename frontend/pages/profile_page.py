from __future__ import annotations
import streamlit as st
import api
from common import render_page_header

def render() -> None:
    b=api.get_baby(st.session_state.baby_id)["data"]
    render_page_header("내 정보","보호자 정보와 AI 답변에 반영할 아기 정보를 관리해요.",b)
    tab_labels = ["아기 정보", "보호자 정보", "알림 설정"]
    st.session_state.setdefault("profile_selected", "아기 정보")
    tab_columns = st.columns(3, gap="small")
    for column, label in zip(tab_columns, tab_labels):
        if column.button(
            label,
            key=f"profile_tab_{label}",
            use_container_width=True,
            type="primary" if st.session_state.profile_selected == label else "secondary",
        ):
            st.session_state.profile_selected = label
    selected = st.session_state.profile_selected
    if selected=="보호자 정보":
        st.markdown("<div style='background:#fff;border:1px solid #E3E7F1;border-radius:14px;padding:16px'><h3>보호자 정보</h3><p style='color:#778198'>테스트 사용자 정보는 읽기 전용입니다.</p><div style='background:#F4F6FB;border-radius:8px;padding:12px'><b>서아 보호자</b><br><small>아기 생활 기록과 맞춤형 안내를 관리합니다.</small></div></div>",unsafe_allow_html=True); return
    if selected=="알림 설정":
        st.markdown("<div style='background:#fff;border:1px solid #E3E7F1;border-radius:14px;padding:16px'><h3>수유 알림 설정</h3><p style='color:#778198'>마지막 수유 시각을 기준으로 다음 알림을 알려드려요.</p><div style='background:#F4F6FB;border-radius:8px;padding:12px'>현재 알림 간격　<b style='float:right'>3시간</b></div><p style='margin-top:16px'><button style='background:#6374DC;color:white;border:0;border-radius:8px;padding:9px 14px'>알림 설정 저장</button></p></div>",unsafe_allow_html=True); return
    st.markdown(f'''<style>.babyx,.boxx{{background:#fff;border:1px solid #E3E7F1;border-radius:14px;padding:14px;margin:9px 0}}.boxx h4{{margin:0 0 4px}}.boxx small{{color:#778198;font-size:11px}}.fields{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:12px}}.field{{font-size:11px;color:#778198}}.inputx{{background:#F4F6FB;border:1px solid #DFE4F1;border-radius:7px;color:#202737;padding:9px;margin-top:5px;font-size:12px}}.noticex{{background:#EEF1FF;border-radius:8px;color:#68758E;padding:9px;font-size:10px;margin-top:10px}}</style><div class='babyx'>👶　<b>{b['baby_name']} · 생후 {b['age_days']}일</b><br><small style='margin-left:25px;color:#778198'>{b['birth_date']} 출생 · {b['gender']} · {b['feeding_type']} 수유</small></div><div class='boxx'><h4>기본 정보 <span style='float:right;font-size:11px;border:1px solid #DFE4F1;padding:5px;border-radius:7px'>✎ 수정</span></h4><small>월령 계산과 맞춤형 육아 안내에 사용됩니다.</small><div class='fields'><div class='field'>아기 이름<div class='inputx'>{b['baby_name']}</div></div><div class='field'>생년월일<div class='inputx'>{b['birth_date']}</div></div><div class='field'>성별<div class='inputx'>{b['gender']}</div></div><div class='field'>수유 방식<div class='inputx'>{b['feeding_type']}</div></div></div></div><div class='boxx'><h4>성장 정보</h4><small>성장 곡선과 월령별 참고값 비교에 사용됩니다.</small><div class='fields'><div class='field'>출생 몸무게<div class='inputx'>{b['birth_weight_kg']} kg</div></div><div class='field'>현재 몸무게<div class='inputx'>{b['current_weight_kg']} kg</div></div><div class='field'>현재 키<div class='inputx'>{b['current_height_cm']} cm</div></div><div class='field'>머리둘레<div class='inputx'>{b['head_circumference_cm']} cm</div></div></div><div class='noticex'>성장 측정값은 ‘육아 관리’에서 새 기록을 추가하면 최신 값으로 갱신됩니다.</div></div><div class='boxx'><h4>중요 건강정보</h4><small>관련 육아 정보를 안내하기 전에 AI가 우선 확인합니다.</small><div class='field' style='margin-top:12px'>음식·약물 알레르기<div class='inputx'>⚠ {', '.join(b['allergies'])}</div></div></div>''',unsafe_allow_html=True)
