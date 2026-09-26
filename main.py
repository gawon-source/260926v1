import streamlit as st
import requests
import time
from datetime import datetime, date
import pandas as pd

# 메가박스 주요 지점 목록 (지점명: 지점코드)
THEATER_MAP = {
    "코엑스": "1351",
    "성수": "0019",
    "홍대": "1211",
    "강남": "1372",
    "신촌": "1202",
    "목동": "1581",
    "하남스타필드": "1291",
    "고양스타필드": "1051",
    "안성스타필드": "1751",
    "수원AK플라자": "1646",
    "대전현대아울렛": "3011",
    "대구신세계": "7011",
    "부산대": "6091",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.megabox.co.kr/booking/timetable",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}

# 브라우저 소리 알림 (HTML5 Audio Web Audio API 주입)
def play_alert_sound():
    sound_script = """
    <script>
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = 880;
    gain.gain.value = 0.5;
    osc.start();
    setTimeout(() => osc.stop(), 500);
    </script>
    """
    st.components.v1.html(sound_script, height=0)

# Discord Webhook 발송
def send_discord_alert(webhook_url, target_date, movie_keyword, schedules):
    if not webhook_url:
        return
    fields = []
    for item in schedules[:5]:
        fields.append({
            "name": f"🎬 {item['상영관']} - {item['영화명']}",
            "value": f"시간: `{item['상영시간']}` | 잔여석: **{item['잔여석']}**",
            "inline": False
        })
    payload = {
        "content": f"🚨 **[메가박스 예매 오픈 알림]** '{movie_keyword}' 예매가 시작되었습니다!",
        "embeds": [{
            "title": f"상영일자: {target_date}",
            "color": 15158332,
            "fields": fields,
            "timestamp": datetime.utcnow().isoformat()
        }]
    }
    try:
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception as e:
        st.warning(f"디스코드 발송 실패: {e}")

# 메가박스 스케줄 확인 로직
def check_megabox(brch_no, play_de, keyword, screen_filter):
    url = "https://www.megabox.co.kr/on/oh/ohc/Brch/schedulePage.do"
    payload = {
        "masterType": "brch",
        "detailType": "spcl",
        "brchNo": brch_no,
        "firstAt": "N",
        "playDe": play_de
    }

    try:
        res = requests.post(url, data=payload, headers=HEADERS, timeout=8)
        if res.status_code != 200:
            return False, f"서버 응답 오류 (HTTP {res.status_code})", []

        data = res.json()
        movie_list = data.get("megaMap", {}).get("movieFormList", [])
        if not movie_list:
            return False, f"{play_de} 해당 일자의 시간표가 아직 열리지 않았습니다.", []

        matched = []
        cleaned_kw = keyword.replace(" ", "").lower()

        for movie in movie_list:
            movie_nm = movie.get("movieNm", "")
            if cleaned_kw and cleaned_kw not in movie_nm.replace(" ", "").lower():
                continue

            for play in movie.get("playScheduleList", []):
                screen_nm = play.get("theabExposNm", "")
                if screen_filter and screen_filter.upper() not in screen_nm.upper():
                    continue

                matched.append({
                    "영화명": movie_nm,
                    "상영관": screen_nm,
                    "상영시간": f"{play.get('playStartTime', '')} ~ {play.get('playEndTime', '')}",
                    "잔여석": f"{play.get('restSeatCnt', 0)} / {play.get('totSeatCnt', 0)}"
                })

        if matched:
            return True, f"'{keyword}' 상영 일정이 감지되었습니다! (총 {len(matched)}회차)", matched
        else:
            return False, f"시간표는 열렸으나 '{keyword}' 영화는 아직 등록되지 않았습니다.", []

    except Exception as e:
        return False, f"조회 중 오류 발생: {e}", []

# ================= UI 레이아웃 =================
st.set_page_config(page_title="메가박스 예매 오픈 감시기", page_icon="🎟️", layout="centered")

st.title("🎟️ 메가박스 실시간 예매 오픈 감시기")
st.caption("원하는 지점, 날짜, 영화를 설정하면 예매 오픈 시 화면과 알림으로 즉시 안내합니다.")

# 세션 상태 초기화
if "monitoring" not in st.session_state:
    st.session_state.monitoring = False

# 입력 설정 영역
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        theater_name = st.selectbox("지점 선택", options=list(THEATER_MAP.keys()), index=0) # 기본: 코엑스
        movie_keyword = st.text_input("영화 키워드", value="치이카와")
        screen_type = st.text_input("상영관 필터 (선택)", placeholder="예: DOLBY, 2D (비우면 전체)")
    with col2:
        target_date = st.date_input("상영 날짜", value=date(2026, 9, 30))
        interval_sec = st.number_input("체크 주기 (초)", min_value=15, max_value=300, value=30, help="IP 차단 방지를 위해 30초 이상 권장합니다.")
        discord_webhook = st.text_input("Discord Webhook URL (선택)", placeholder="https://discord.com/api/webhooks/...")

btn_col1, btn_col2 = st.columns(2)

def start_mon():
    st.session_state.monitoring = True

def stop_mon():
    st.session_state.monitoring = False

with btn_col1:
    st.button("▶ 실시간 감시 시작", type="primary", use_container_width=True, on_click=start_mon, disabled=st.session_state.monitoring)
with btn_col2:
    st.button("⏹ 정지", use_container_width=True, on_click=stop_mon, disabled=not st.session_state.monitoring)

# 모니터링 실행 영역
status_placeholder = st.empty()
result_placeholder = st.empty()

if st.session_state.monitoring:
    brch_code = THEATER_MAP[theater_name]
    play_de_str = target_date.strftime("%Y%m%d")

    while st.session_state.monitoring:
        now_str = datetime.now().strftime("%H:%M:%S")
        is_opened, message, schedules = check_megabox(brch_code, play_de_str, movie_keyword, screen_type)

        if is_opened:
            status_placeholder.success(f"🎉 [{now_str}] {message}")
            play_alert_sound() # 소리 알람 재생
            
            if discord_webhook:
                send_discord_alert(discord_webhook, play_de_str, movie_keyword, schedules)

            # 결과 테이블 출력
            df = pd.DataFrame(schedules)
            result_placeholder.dataframe(df, use_container_width=True)
            
            st.session_state.monitoring = False
            st.balloons() # 오픈 축하 풍선 효과
            break
        else:
            status_placeholder.info(f"⏳ [{now_str}] 감시 중... {message}")
            time.sleep(interval_sec)
else:
    status_placeholder.write("상단에서 설정을 마친 후 **[▶ 실시간 감시 시작]**을 눌러주세요.")
