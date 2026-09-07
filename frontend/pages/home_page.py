from __future__ import annotations

import streamlit as st

import api
from common import render_page_header


def render() -> None:
    baby = api.get_baby(st.session_state.baby_id)["data"]
    data = api.get_dashboard(st.session_state.baby_id)["data"]
    vaccine = data["next_vaccination"]
    render_page_header(
        f"안녕하세요, {baby['baby_name']} 보호자님 👋",
        f"{baby['baby_name']}는 오늘 생후 {baby['age_days']}일이에요.",
        baby,
    )
    st.markdown(
        f"""
        <style>
        .home-reminder{{background:#EEF1FF;border:1px solid #C9D2FF;border-radius:15px;padding:18px 20px;margin:8px 0 16px;display:flex;justify-content:space-between;align-items:center}}.home-reminder b{{font-size:16px}}.home-sub,.home-label{{font-size:14px;color:#778198}}.home-btn,.home-btn:link,.home-btn:visited{{display:inline-block;text-decoration:none!important;color:#202737;background:#fff;border:1px solid #DFE4F1;border-radius:8px;padding:8px 11px;margin-left:5px;font-size:13px}}.home-btn.primary{{background:#6374DC;color:#fff;border-color:#6374DC;font-weight:700}}.home-grid{{display:grid;grid-template-columns:1.55fr 1fr;gap:14px}}.home-card{{background:#fff;border:1px solid #E3E7F1;border-radius:16px;padding:16px;box-sizing:border-box}}.home-title{{font-weight:800;font-size:17px;margin-bottom:14px}}.home-stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}}.home-stat{{background:#F4F6FB;border-radius:10px;padding:12px 10px;min-height:76px}}.home-value{{font-weight:800;font-size:16px}}.home-unit{{color:#6374DC;font-size:12px;font-weight:700}}.growth{{margin-top:14px;min-height:238px}}.growth-chart{{width:100%;height:auto;display:block;margin-top:4px}}.vaccine-date{{display:inline-block;background:#EEF1FF;color:#6374DC;border-radius:10px;padding:10px;font-weight:800}}.topic-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:10px}}.topic-btn,.topic-btn:link,.topic-btn:visited,.topic-btn:hover,.topic-btn:active{{display:block;box-sizing:border-box;width:100%;text-align:center;text-decoration:none!important;color:#202737;border:1px solid #DFE4F1;border-radius:8px;padding:8px 5px;font-size:13px;background:#fff}}.topic-btn:hover{{border-color:#6374DC;color:#6374DC;background:#EEF1FF}}@media(max-width:700px){{.home-grid{{grid-template-columns:1fr}}.home-stats{{grid-template-columns:1fr}}.topic-grid{{grid-template-columns:1fr}}.home-reminder{{align-items:flex-start;gap:12px;flex-direction:column}}.home-btn{{margin-left:0!important;margin-right:5px}}}}
        </style>
        <div class="home-reminder"><div><b>🍼 마지막 수유 후 3시간이 지났어요</b><div class="home-sub">서아의 배고픔 신호를 확인해 주세요.</div></div><div><a class="home-btn primary" href="?demo=1&amp;page=%EC%9C%A1%EC%95%84%20%EA%B4%80%EB%A6%AC">수유했어요</a><a class="home-btn" href="?demo=1&amp;page=%ED%99%88&amp;notice=snooze">10분 후</a><a class="home-btn" href="?demo=1&amp;page=%ED%99%88&amp;notice=skip">건너뛰기</a></div></div>
        <div class="home-grid"><div><div class="home-card"><div class="home-title">최근 7일 육아 기록</div><div class="home-stats"><div class="home-stat"><div class="home-label">수유</div><div class="home-value">7 <span class="home-unit">하루 평균</span></div></div><div class="home-stat"><div class="home-label">수면</div><div class="home-value">15시간 <span class="home-unit">하루 평균</span></div></div><div class="home-stat"><div class="home-label">배변</div><div class="home-value">5 <span class="home-unit">하루 평균</span></div></div></div></div>
        <div class="home-card growth"><div class="home-title">몸무게 성장</div><div class="home-label">같은 성별·월령 기준과 비교한 참고 그래프</div><svg class="growth-chart" viewBox="0 0 430 180" role="img" aria-label="서아의 몸무게 성장 그래프"><path d="M42 32H410 M42 72H410 M42 112H410 M42 145H410" stroke="#E3E7F1" stroke-dasharray="3 3"/><path d="M52 106 L140 91 L228 74 L316 56 L402 42 L402 63 L316 78 L228 96 L140 113 L52 128Z" fill="#DDE3FF"/><path d="M52 119 L140 103 L228 86 L316 67 L402 51" fill="none" stroke="#6374DC" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><g fill="#6374DC"><circle cx="52" cy="119" r="4"/><circle cx="140" cy="103" r="4"/><circle cx="228" cy="86" r="4"/><circle cx="316" cy="67" r="4"/><circle cx="402" cy="51" r="4"/></g><g fill="#778198" font-size="11"><text x="4" y="36">5kg</text><text x="4" y="76">4kg</text><text x="4" y="116">3kg</text><text x="40" y="169">출생</text><text x="126" y="169">1주</text><text x="214" y="169">2주</text><text x="302" y="169">3주</text><text x="385" y="169">현재</text></g><text x="370" y="41" fill="#6374DC" font-size="11" font-weight="700">4.2kg</text></svg></div></div>
        <div><div class="home-card"><div class="home-title">다음 예방접종</div><span class="vaccine-date">{vaccine['date']}</span> <b>{vaccine['name']}</b><div class="home-sub" style="margin:8px 0 0">접종 예정일까지 {vaccine['remaining']}</div></div><div class="home-card" style="margin-top:14px"><div class="home-title">AI 육아 도우미</div><div class="home-label">서아의 월령과 최근 기록을 반영해 답변해 드려요.</div><div class="topic-grid"><a class="topic-btn" href="?demo=1&amp;page=AI%20%EC%9C%A1%EC%95%84%20%EB%8F%84%EC%9A%B0%EB%AF%B8&amp;topic=feeding">수유 기록</a><a class="topic-btn" href="?demo=1&amp;page=AI%20%EC%9C%A1%EC%95%84%20%EB%8F%84%EC%9A%B0%EB%AF%B8&amp;topic=sleep">수면 기록</a><a class="topic-btn" href="?demo=1&amp;page=AI%20%EC%9C%A1%EC%95%84%20%EB%8F%84%EC%9A%B0%EB%AF%B8&amp;topic=hospital">주변 소아과</a><a class="topic-btn" href="?demo=1&amp;page=AI%20%EC%9C%A1%EC%95%84%20%EB%8F%84%EC%9A%B0%EB%AF%B8&amp;topic=weaning">이유식 궁금증</a></div></div></div></div>
        """,
        unsafe_allow_html=True,
    )
