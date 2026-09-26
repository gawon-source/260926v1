(function() {
    // ================= 설정 영역 =================
    const TARGET_KEYWORD = "치이카와";  // 찾고자 하는 영화 키워드
    const CHECK_INTERVAL_SEC = 5;       // 새로고침 주기 (5초 권장)
    // ============================================

    console.log(`[감시 시작] 키워드: '${TARGET_KEYWORD}', 주기: ${CHECK_INTERVAL_SEC}초`);

    // 비프음 알람 생성기
    const playAlertSound = () => {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.type = "sine";
            osc.frequency.setValueAtTime(880, ctx.currentTime); // 880Hz 고음
            gain.gain.setValueAtTime(0.5, ctx.currentTime);
            osc.start();
            osc.stop(ctx.currentTime + 1.2);
        } catch(e) {
            console.error("오디오 재생 오류:", e);
        }
    };

    // 상단 알림 배너 UI 주입
    const banner = document.createElement("div");
    banner.id = "tracker-banner";
    banner.style.cssText = `
        position: fixed; top: 10px; right: 10px; z-index: 999999;
        background: #111827; color: #fff; padding: 16px 24px;
        border-radius: 12px; border: 2px solid #8b5cf6;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5); font-family: sans-serif;
    `;
    banner.innerHTML = `
        <div style="font-weight:bold; font-size:16px; margin-bottom:4px; color:#a78bfa;">
            🎟️ 실시간 회차 감시기 작동 중
        </div>
        <div id="tracker-status" style="font-size:13px; color:#9ca3af;">
            키워드: [${TARGET_KEYWORD}] 감시 대기 중...
        </div>
        <button id="tracker-stop-btn" style="
            margin-top:8px; padding:4px 10px; background:#ef4444; color:#fff;
            border:none; border-radius:4px; cursor:pointer; font-size:12px;
        ">감시 중지</button>
    `;
    document.body.appendChild(banner);

    let checkCount = 0;
    let timerId = null;

    document.getElementById("tracker-stop-btn").onclick = () => {
        clearInterval(timerId);
        banner.remove();
        console.log("[감시 중지됨]");
    };

    const runCheck = () => {
        checkCount++;
        const now = new Date().toTimeString().split(" ")[0];
        const statusEl = document.getElementById("tracker-status");

        // 1. 현재 화면 전체 텍스트 및 시간표 영역에서 영화 키워드 검색
        const pageText = document.body.innerText || "";
        const timetableArea = document.querySelector(".theater-list") || document.body;

        const isFound = timetableArea.innerText.includes(TARGET_KEYWORD);

        if (isFound) {
            // 회차 발견 시
            clearInterval(timerId);
            playAlertSound();
            setInterval(playAlertSound, 2000); // 2초마다 계속 알림음 울림

            if (statusEl) {
                statusEl.innerHTML = `<span style="color:#34d399; font-weight:bold; font-size:15px;">🚨 [${TARGET_KEYWORD}] 예매 오픈 감지!! 지금 바로 좌석을 선택하세요!</span>`;
            }
            banner.style.borderColor = "#34d399";
            banner.style.backgroundColor = "#064e3b";

            alert(`🚨 [${TARGET_KEYWORD}] 예매가 열렸습니다! 좌석을 선택하세요!`);
            return;
        }

        // 2. 미오픈 상태일 때: 상태 메시지 갱신
        if (statusEl) {
            statusEl.innerText = `[${now}] ${checkCount}회차 확인 완료 (아직 미오픈) - ${CHECK_INTERVAL_SEC}초 후 재확인`;
        }

        // 3. 날짜/극장 새로고침 트리거
        // 메가박스 빠른예매의 경우 활성화된 날짜 버튼을 다시 클릭해주면 전체 페이지를 새로고침하지 않고도 시간표만 리로드됩니다.
        const activeDateBtn = document.querySelector(".date-area button.active, .time-schedule button.active");
        if (activeDateBtn) {
            activeDateBtn.click();
        } else {
            // 특정 버튼을 못 찾으면 페이지 새로고침 보조
            // location.reload();
        }
    };

    // 설정된 주기마다 검사 실행
    timerId = setInterval(runCheck, CHECK_INTERVAL_SEC * 1000);
    runCheck(); // 즉시 첫 1회 실행
})();
