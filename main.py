import streamlit as st
import requests
import time
from datetime import datetime, date
import pandas as pd

# 메가박스 실제 사용 극장 코드 (0013 = 코엑스)
THEATER_MAP = {
    "코엑스": "0013",
    "강남": "0023",
    "성수": "0056",
    "홍대": "0046",
    "신촌": "0028",
    "목동": "0011",
    "하남스타필드": "0044",
    "고양스타필드": "0047",
    "수원스타필드": "0070",
    "대전현대아울렛": "0059",
    "대구신세계": "0045",
    "부산대": "0007"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.megabox.co.kr/booking/timetable",
    "Origin": "https://www.megabox.co.kr",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest"
}

def fetch_megabox_raw(brch_no, play_de):
    """메가박스 서버에서 상영시간표 원본 데이터를 호출합니다."""
    url = "https://www.megabox.co.kr/on/oh/ohc/Brch/schedulePage.do"
    
    # 메가박스 기본 상영시간표 요청 파라미터
    payload = {
        "masterType": "brch",
        "detailType": "",
        "brchNo": brch_no,
        "firstAt": "N",
        "playDe": play_de
    }

    try:
        res = requests.post(url, data=payload, headers=HEADERS, timeout=8)
        if res.status_code != 200:
            return None, f"HTTP {res.status_code} 오류"
        return res.json(), "성공"
    except Exception as e:
        return None, str(e)

def parse_schedule(data, keyword="", screen_filter=""):
    """응답 JSON에서 영화 및 회차 목록을 추출합니다."""
    movie_list = data.get("megaMap", {}).get("movieFormList", [])
    if not movie_list:
        return []

    results = []
    cleaned_kw = keyword.replace(" ", "").lower()

    for movie in movie_list:
        movie_nm = movie.get("movieNm", "")
        # 키워드가 비어있으면 모든 영화 통과, 있으면 포함 여부 검사
        if cleaned_kw and cleaned_kw not in movie_nm.replace(" ", "").lower():
            continue

        for play in movie.get("playScheduleList", []):
            screen_nm = play.get("theabExposNm", "")
            if screen_filter and screen_filter.upper() not in screen_nm.upper():
                continue

            results.append({
                "영화명": movie_nm,
                "상영관": screen_nm,
                "상영시간": f"{play.get('playStartTime', '')} ~ {play.get('playEndTime', '')}",
                "잔여석": f"{play.get('restSeatCnt', 0)} / {play.get('totSeatCnt', 0)}"
            })
    return results

# ================= UI 레이아웃 =================
st.set_page_config(page_title="메가박스 예매 오픈 감시기", page_icon="🎟️", layout="centered")

st.title("🎟️ 메가박스 실시간 오픈 감시기")

if "monitoring" not in st.session_state:
    st.session_state.monitoring = False

with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        theater_name = st.selectbox("지점 선택", options=list(THEATER_MAP.keys()), index=0)
        movie_keyword = st.text_input("영화 키워드 (예: 치이카와)", value="치이카와")
        screen_type = st.text_input("상영관 필터 (선택)", placeholder="예: DOLBY (비우면 전체)")
    with col2:
        # 기본값: 2026년 9월 30일
        target_date = st.date_input("상영 날짜", value=date(2026, 9, 30))
        interval_sec = st.number_input("체크 주기 (초)", min_value=15, max_value=300, value=30)
        discord_webhook = st.text_input("Discord Webhook (선택)", placeholder="https://discord.com/...")

col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])

def start_mon():
    st.session_state.monitoring = True

def stop_mon():
    st.session_state.monitoring = False

with col_btn1:
    st.button("▶ 감시 시작", type="primary", use_container_width=True, on_click=start_mon, disabled=st.session_state.monitoring)
with col_btn2:
    st.button("⏹ 정지", use_container_width=True, on_click=stop_mon, disabled=not st.session_state.monitoring)
with col_btn3:
    test_btn = st.button("🔍 현재 열린 영화 확인", use_container_width=True)

status_placeholder = st.empty()
result_placeholder = st.empty()

# [테스트 버튼]: 현재 날짜/지점에 실제로 어떤 영화가 열려있는지 즉시 확인
if test_btn:
    brch_code = THEATER_MAP[theater_name]
    play_de_str = target_date.strftime("%Y%m%d")
    raw_data, msg = fetch_megabox_raw(brch_code, play_de_str)
    
    if raw_data:
        all_movies = parse_schedule(raw_data, keyword="")
        if all_movies:
            st.success(f"{theater_name} ({target_date}) 현재 등록된 상영 회차 총 {len(all_movies)}건")
            st.dataframe(pd.DataFrame(all_movies), use_container_width=True)
        else:
            st.warning(f"{theater_name} ({target_date})에는 아직 어떤 영화도 시간표가 등록되지 않았습니다.")
    else:
        st.error(f"데이터 조회 실패: {msg}")

# 실시간 모니터링 루프
if st.session_state.monitoring:
    brch_code = THEATER_MAP[theater_name]
    play_de_str = target_date.strftime("%Y%m%d")

    while st.session_state.monitoring:
        now_str = datetime.now().strftime("%H:%M:%S")
        raw_data, msg = fetch_megabox_raw(brch_code, play_de_str)

        if not raw_data:
            status_placeholder.error(f"[{now_str}] 조회 실패: {msg}")
            time.sleep(interval_sec)
            continue

        matched_schedules = parse_schedule(raw_data, movie_keyword, screen_type)

        if matched_schedules:
            status_placeholder.success(f"🎉 [{now_str}] '{movie_keyword}' 상영 일정이 감지되었습니다! (총 {len(matched_schedules)}회차)")
            result_placeholder.dataframe(pd.DataFrame(matched_schedules), use_container_width=True)
            st.session_state.monitoring = False
            st.balloons()
            break
        else:
            total_registered = len(parse_schedule(raw_data, keyword=""))
            if total_registered > 0:
                status_placeholder.info(f"⏳ [{now_str}] 시간표는 열렸으나(다른 영화 {total_registered}건 있음), '{movie_keyword}'는 아직 없습니다.")
            else:
                status_placeholder.info(f"⏳ [{now_str}] {target_date} 일자의 상영시간표 전체가 아직 열리지 않았습니다.")
            
            time.sleep(interval_sec)
