from __future__ import annotations
import streamlit as st
import api
from common import render_page_header

def render() -> None:
    baby=api.get_baby(st.session_state.baby_id)["data"]
    records=api.get_care_records(st.session_state.baby_id)["data"]
    render_page_header("육아 관리","기록부터 성장·예방접종까지 한눈에 확인해요.",baby)
    tab_labels = ["육아 기록", "생활 패턴", "성장", "예방접종"]
    st.session_state.setdefault("care_selected", "육아 기록")
    tab_columns = st.columns(4, gap="small")
    for column, label in zip(tab_columns, tab_labels):
        if column.button(
            label,
            key=f"care_tab_{label}",
            use_container_width=True,
            type="primary" if st.session_state.care_selected == label else "secondary",
        ):
            st.session_state.care_selected = label
    selected = st.session_state.care_selected
    if selected=="생활 패턴":
        p=api.get_care_pattern(st.session_state.baby_id)["data"]
        st.markdown(f"<div style='background:#fff;border:1px solid #E3E7F1;border-radius:15px;padding:16px'><h3>생활 패턴</h3><div style='display:grid;grid-template-columns:1fr 1fr;gap:10px'><div style='background:#F4F6FB;padding:12px;border-radius:10px'>평균 수유 간격<br><b>{p['average_interval']}</b></div><div style='background:#F4F6FB;padding:12px;border-radius:10px'>1일 평균 수유<br><b>{p['daily_feeding']}</b></div><div style='background:#F4F6FB;padding:12px;border-radius:10px'>평균 수면<br><b>{p['daily_sleep']}</b></div><div style='background:#F4F6FB;padding:12px;border-radius:10px'>1일 평균 배변<br><b>{p['daily_diaper']}</b></div></div><h4>최근 7일 수유 간격</h4><div style='height:150px;border-bottom:2px solid #DDE3FF;background:linear-gradient(170deg,transparent 48%,#EEF1FF 49%,#EEF1FF 51%,transparent 52%)'></div><div style='background:#EEF1FF;padding:12px;border-radius:9px'>💡 수유 간격과 수면 기록은 더 많은 기록이 쌓이면 정확하게 요약됩니다.</div></div>",unsafe_allow_html=True); return
    if selected=="성장":
        st.markdown("<div style='background:#fff;border:1px solid #E3E7F1;border-radius:15px;padding:16px'><h3>몸무게 변화</h3><div style='height:230px;border-bottom:2px solid #DDE3FF;background:linear-gradient(170deg,transparent 48%,#DDE3FF 49%,#DDE3FF 51%,transparent 52%)'></div><h3>최근 측정 결과</h3><div style='background:#EEF1FF;padding:12px;border-radius:9px'><b>현재 몸무게 4.2kg</b><br>성장 추세는 참고 정보이며 정상·비정상을 단정하지 않습니다.</div></div>",unsafe_allow_html=True); return
    if selected=="예방접종":
        v=api.get_vaccinations(st.session_state.baby_id)["data"]
        items=''.join(f"<p style='border-bottom:1px solid #E3E7F1;padding:10px'>✓　<b>{n}</b><span style='float:right;color:#20A26B'>{s}</span><br><small>　　{d}</small></p>" for n,d,s,_ in v['items'])
        st.markdown(f"<div style='background:#fff;border:1px solid #E3E7F1;border-radius:15px;padding:16px'><div style='background:#EEF1FF;padding:12px;border-radius:10px'><b>다음 예방접종 · {v['next']['name']}</b><span style='float:right;color:#6374DC'>{v['next']['date']}</span></div><h3>접종 내역 및 일정</h3>{items}</div>",unsafe_allow_html=True); return
    rows=''.join(f"<div class='r'><span>{x['time']}</span><b>{x['icon']}　{x['title']}</b><small>{x['detail']}</small><i>✎　♲</i></div>" for x in records)
    st.markdown(f'''<style>.metrics{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}.m,.cardx{{background:#fff;border:1px solid #E3E7F1;border-radius:15px;padding:14px}}.m small,.r span,.r small{{color:#778198;font-size:11px}}.m b{{display:block;font-size:17px;margin-top:7px}}.cardx{{margin-top:16px}}.r{{display:grid;grid-template-columns:86px 1fr 2fr 65px;align-items:center;border:1px solid #E3E7F1;border-radius:12px;padding:11px;margin:8px 0;font-size:13px}}.r small{{display:block;margin-top:4px}}.r i{{color:#778198;font-style:normal;text-align:right}}.filter{{float:right;color:#6374DC;font-size:12px}}.note{{background:#EEF1FF;color:#68758E;border-radius:9px;padding:10px;font-size:11px;margin-top:10px}}</style><div class='metrics'><div class='m'><small>최근 7일 수유</small><b>47 <em>회</em></b></div><div class='m'><small>평균 수유량</small><b>96 <em>ml</em></b></div><div class='m'><small>하루 평균 수면</small><b>14.2 <em>시간</em></b></div><div class='m'><small>최근 7일 배변</small><b>19 <em>회</em></b></div></div><div class='cardx'><b>최근 기록</b><span class='filter'>전체　 수유　 수면　 배변　 성장</span>{rows}<div class='note'>수정·삭제는 보호자가 최종 확인한 뒤 반영됩니다.</div></div>''',unsafe_allow_html=True)
