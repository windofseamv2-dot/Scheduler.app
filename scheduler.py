import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import datetime
import json
import os

# --- 1. 기본 설정 ---
st.set_page_config(page_title="나만의 스터디 플래너", layout="wide", page_icon="📝")

DATA_FILE = "study_planner_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"schedules": [], "logs": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

data = load_data()

# --- 한국 시간 함수 ---
def get_korea_now():
    # 서버 시간(UTC) + 9시간 = 한국 시간(KST)
    return datetime.datetime.utcnow() + datetime.timedelta(hours=9)

def get_korea_today():
    return get_korea_now().date()

# --- 2. 일정 필터링 및 처리 함수 ---
def process_schedules(schedules):
    # 이 함수는 "오늘 해당하는 일정"을 모두 골라내고, 시간 형식을 "HH:MM:SS"로 통일합니다.
    now = get_korea_now()
    today_date = now.date()
    today_str = today_date.strftime("%Y-%m-%d")
    weekday_map = ["월", "화", "수", "목", "금", "토", "일"]
    today_weekday = weekday_map[today_date.weekday()] 
    
    todays_list = []
    
    for sc in schedules:
        is_today = False
        # 1. 날짜/요일 체크
        if sc['type'] == '매일':
            is_today = True
        elif sc['type'] == '매주 요일':
            if isinstance(sc['value'], list) and today_weekday in sc['value']: is_today = True
            elif isinstance(sc['value'], str) and sc['value'] == today_weekday: is_today = True
        elif sc['type'] == '특정 날짜' and sc['value'] == today_str:
            is_today = True
        elif sc['type'] == '기간 (Start ~ End)':
            if isinstance(sc['value'], list) and len(sc['value']) == 2:
                try:
                    s_d = datetime.datetime.strptime(sc['value'][0], "%Y-%m-%d").date()
                    e_d = datetime.datetime.strptime(sc['value'][1], "%Y-%m-%d").date()
                    if s_d <= today_date <= e_d: is_today = True
                except: pass

        # 2. 시간 포맷 강제 통일 (무조건 HH:MM:SS 두 자리 숫자)
        # 예: "9:0:0" -> "09:00:00", "09:30" -> "09:30:00"
        try:
            parts = sc['time'].split(':')
            if len(parts) == 2: # HH:MM
                h, m = int(parts[0]), int(parts[1])
                s = 0
            elif len(parts) == 3: # HH:MM:SS
                h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
            else:
                continue # 이상한 형식은 무시
            
            # 포맷팅 적용
            formatted_time = f"{h:02d}:{m:02d}:{s:02d}"
            sc['time'] = formatted_time # 데이터 업데이트
            
        except:
            continue

        if is_today:
            todays_list.append(sc)
            
    todays_list.sort(key=lambda x: x['time'])
    return todays_list

# --- 3. [핵심] 알림 기능 시계 ---
def show_realtime_clock_with_alert(today_schedules):
    # 오늘 울려야 할 알림들의 시간을 추출해서 JS로 보냄
    # 디버깅을 위해 화면에도 표시해줌
    schedules_json = json.dumps(today_schedules, ensure_ascii=False)
    
    # 다음 알림 미리보기 텍스트 생성
    alert_times_debug = [f"[{item['title']} {item['time']}]" for item in today_schedules]
    debug_text = " / ".join(alert_times_debug) if alert_times_debug else "없음"

    clock_html = f"""
    <style>
        .clock-wrapper {{
            text-align: center;
            padding: 15px;
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            margin-bottom: 20px;
            border: 1px solid #eee;
        }}
        .time {{ font-size: 2.5em; font-weight: 800; color: #FF4B4B; margin: 0; line-height: 1.2; }}
        .date {{ font-size: 1.1em; color: #666; margin-bottom: 5px; }}
        .debug {{ font-size: 0.8em; color: #aaa; margin-top: 10px; }}
    </style>
    <div class="clock-wrapper">
        <div id="date" class="date"></div>
        <div id="clock" class="time">--:--:--</div>
        <div class="debug">🔔 알림 대기중인 일정: {debug_text}</div>
    </div>
    <script>
        var schedules = {schedules_json};
        var alertedTimes = []; // 이미 알림 보낸 시간 저장

        function updateClock() {{
            var now = new Date();
            // 1. 한국 시간 계산 (브라우저 시간 대신 서버시간을 따라가진 못하지만, 포맷은 맞춤)
            // 시간 포맷을 HH:MM:SS (09:05:01) 형태로 강제 변환
            var h = String(now.getHours()).padStart(2, '0');
            var m = String(now.getMinutes()).padStart(2, '0');
            var s = String(now.getSeconds()).padStart(2, '0');
            var timeString = h + ":" + m + ":" + s;
            
            // 날짜 표시
            var dateString = now.toLocaleDateString('ko-KR', {{ year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' }});
            
            document.getElementById('clock').innerHTML = timeString;
            document.getElementById('date').innerHTML = dateString;

            // 2. 알림 체크 (초 단위 일치 확인)
            schedules.forEach(function(item) {{
                // 파이썬에서 보내준 item.time은 무조건 "HH:MM:SS" 형태임
                if (item.time === timeString && !alertedTimes.includes(timeString)) {{
                    // 알림창 띄우기
                    alert("⏰ 딩동! [" + item.title + "] 할 시간입니다!");
                    alertedTimes.push(timeString);
                }}
            }});
        }}
        setInterval(updateClock, 1000); // 1초마다 실행
        updateClock(); // 즉시 실행
    </script>
    """
    components.html(clock_html, height=180)

# --- 4. 메인 화면 구성 ---
st.sidebar.title("📚 메뉴")
page = st.sidebar.radio("이동", ["대시보드 (Main)", "공부 기록하기", "일정 관리"])

korea_now = get_korea_now()
korea_today_str = korea_now.strftime("%Y-%m-%d")

if page == "대시보드 (Main)":
    # 1. 오늘 해당하는 모든 일정 가져오기 (알림용)
    today_all_schedules = process_schedules(data['schedules'])
    
    # 2. 시계 표시 (알림 기능 포함)
    show_realtime_clock_with_alert(today_all_schedules)
    
    # 3. 화면에 보여줄 일정 (시간 지난 건 숨기기)
    current_time_str = korea_now.strftime("%H:%M:%S")
    upcoming_schedules = [s for s in today_all_schedules if s['time'] > current_time_str]
    
    today_logs = [log for log in data['logs'] if log['date'] == korea_today_str]
    total_minutes = sum(log['duration'] for log in today_logs)
    
    c1, c2 = st.columns(2)
    c1.metric("⏱️ 오늘 공부량", f"{total_minutes} 분")
    c2.metric("🔔 남은 일정", f"{len(upcoming_schedules)} 개")
    
    st.markdown("---")
    
    col_left, col_right = st.columns([1, 1])
    weekday_korean = ["월", "화", "수", "목", "금", "토", "일"][korea_now.weekday()]

    with col_left:
        st.subheader(f"📝 남은 일정 ({weekday_korean})")
        if upcoming_schedules:
            for item in upcoming_schedules:
                with st.container(border=True):
                    # [요청사항 반영] 상세 정보 표시 로직
                    t_type = item['type']
                    val = item['value']
                    desc = ""
                    
                    if t_type == "매일":
                        desc = "매일 반복"
                    elif t_type == "매주 요일":
                        weekdays = ",".join(val) if isinstance(val, list) else str(val)
                        desc = f"매주 {weekdays}요일"
                    elif t_type == "특정 날짜":
                        desc = f"날짜: {val}"
                    elif t_type == "기간 (Start ~ End)":
                        if isinstance(val, list) and len(val) == 2:
                            desc = f"기간: {val[0]} ~ {val[1]}"
                        else:
                            desc = "기간 설정 오류"

                    # 카드 디자인
                    st.markdown(f"### ⏰ {item['time']}") 
                    st.markdown(f"**📌 {item['title']}**") # 제목 강조
                    st.caption(f"└ {desc}") # 상세 조건 표시
        else:
            st.info("남은 일정이 없습니다! 🎉")

    with col_right:
        st.subheader("🔥 최근 공부 기록")
        if data['logs']:
            df_logs = pd.DataFrame(data['logs']).sort_values(by=["date", "time"], ascending=False).head(5)
            st.dataframe(
                df_logs[["date", "time", "subject", "duration", "note"]],
                column_config={"date":"날짜", "time":"시간", "subject":"과목", "duration":"분", "note":"내용"},
                use_container_width=True, hide_index=True
            )
        else:
            st.warning("아직 공부 기록이 없습니다.")

elif page == "공부 기록하기":
    st.title("✍️ 공부 기록")
    st.info(f"현재 한국 시간: {korea_now.strftime('%H시 %M분 %S초')}")
    
    with st.form("log_form"):
        col_date, c_h, c_m, c_s = st.columns([2, 1, 1, 1])
        input_date = col_date.date_input("날짜", get_korea_today())
        
        hh = c_h.number_input("시", 0, 23, korea_now.hour)
        mm = c_m.number_input("분", 0, 59, korea_now.minute)
        ss = c_s.number_input("초", 0, 59, korea_now.second)
        time_str = f"{hh:02d}:{mm:02d}:{ss:02d}"
        
        c1, c2 = st.columns(2)
        subject = c1.text_input("과목명")
        duration = c2.number_input("공부 시간(분)", value=60, step=10)
        note = st.text_area("메모")
        
        if st.form_submit_button("저장"):
            new_log = {
                "date": input_date.strftime("%Y-%m-%d"),
                "time": time_str, 
                "subject": subject,
                "duration": duration,
                "note": note,
                "timestamp": str(korea_now)
            }
            data['logs'].append(new_log)
            save_data(data)
            st.success("저장 완료!")
            st.rerun()
            
    st.divider()
    st.subheader("📜 전체 기록")
    if data['logs']:
        df_all = pd.DataFrame(data['logs']).sort_values(by=["date", "time"], ascending=False)
        st.dataframe(df_all[["date", "time", "subject", "duration", "note"]], use_container_width=True, hide_index=True)
        
        with st.expander("기록 삭제"):
            target = st.selectbox("삭제할 항목", df_all.index, format_func=lambda i: f"[{df_all.loc[i]['date']} {df_all.loc[i]['time']}] {df_all.loc[i]['subject']}")
            if st.button("삭제"):
                tgt_ts = df_all.loc[target]['timestamp']
                data['logs'] = [x for x in data['logs'] if x['timestamp'] != tgt_ts]
                save_data(data)
                st.rerun()

elif page == "일정 관리":
    st.title("🗓️ 일정 관리")
    st.subheader("새 일정 추가")
    
    # 1. 반복 유형
    type_opt = st.selectbox("반복 유형", ["매일", "매주 요일", "특정 날짜", "기간 (Start ~ End)"])
    
    # 2. 추가 옵션
    val = None
    if type_opt == "매주 요일":
        val = st.multiselect("요일 선택", ["월", "화", "수", "목", "금", "토", "일"])
    elif type_opt == "특정 날짜":
        d = st.date_input("날짜 선택")
        val = d.strftime("%Y-%m-%d")
    elif type_opt == "기간 (Start ~ End)":
        c_s, c_e = st.columns(2)
        d_start = c_s.date_input("시작일")
        d_end = c_e.date_input("종료일")
        val = [d_start.strftime("%Y-%m-%d"), d_end.strftime("%Y-%m-%d")]
        if d_start > d_end:
            st.warning("⚠️ 종료일이 시작일보다 빠릅니다!")
        
    # 3. 내용 및 시간
    title = st.text_input("일정 내용 (예: 겨울방학 특강)")
    
    st.write("시간 설정 (24시간제)")
    c_h, c_m, c_s = st.columns(3)
    s_h = c_h.number_input("시", 0, 23, 9)
    s_m = c_m.number_input("분", 0, 59, 0)
    s_s = c_s.number_input("초", 0, 59, 0)
    schedule_time_str = f"{s_h:02d}:{s_m:02d}:{s_s:02d}" # 무조건 00:00:00 형태로 만듦

    # 4. 추가 버튼
    if st.button("일정 추가하기", type="primary"):
        if not title:
            st.error("⚠️ 일정 내용을 입력해주세요!")
        elif type_opt == "매주 요일" and not val:
            st.error("⚠️ 요일을 최소 하나 이상 선택해주세요!")
        else:
            new_item = {
                "id": (max(x['id'] for x in data['schedules']) + 1) if data['schedules'] else 1,
                "title": title,
                "time": schedule_time_str, 
                "type": type_opt,
                "value": val
            }
            data['schedules'].append(new_item)
            save_data(data)
            st.success("✅ 일정이 추가되었습니다!")
            import time
            time.sleep(1)
            st.rerun()
    
    st.divider()
    if data['schedules']:
        st.subheader("일정 목록")
        df_sc = pd.DataFrame(data['schedules'])
        
        # 목록 표시용 변환 함수
        def fmt_val(v):
            if isinstance(v, list):
                # 기간인 경우
                if len(v) == 2 and v[0][0].isdigit():
                    return f"{v[0]} ~ {v[1]}"
                return ",".join(v)
            return v
            
        df_sc['disp'] = df_sc['value'].apply(fmt_val)
        df_sc['del'] = False
        
        edited = st.data_editor(
            df_sc,
            column_config={
                "del": st.column_config.CheckboxColumn("삭제", default=False),
                "title": "내용", "time":"시간", "type":"반복", "disp":"상세",
                "value": None, "id": None
            },
            hide_index=True, use_container_width=True
        )
        if st.button("선택 삭제"):
            del_ids = edited[edited['del']]['id'].tolist()
            if del_ids:
                data['schedules'] = [x for x in data['schedules'] if x['id'] not in del_ids]
                save_data(data)
                st.rerun()
