import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import datetime
import json
import os

# --- 1. 데이터 관리 ---
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
    return datetime.datetime.utcnow() + datetime.timedelta(hours=9)

def get_korea_today():
    return get_korea_now().date()

# --- 2. 일정 필터링 함수 ---
def get_today_schedules(schedules):
    today = get_korea_today()
    weekday_map = ["월", "화", "수", "목", "금", "토", "일"]
    today_weekday = weekday_map[today.weekday()] 
    today_str = today.strftime("%Y-%m-%d")
    
    todays_list = []
    for sc in schedules:
        is_today = False
        if sc['type'] == '매일':
            is_today = True
        elif sc['type'] == '매주 요일':
            if isinstance(sc['value'], list) and today_weekday in sc['value']:
                is_today = True
            elif isinstance(sc['value'], str) and sc['value'] == today_weekday:
                is_today = True
        elif sc['type'] == '특정 날짜' and sc['value'] == today_str:
            is_today = True
            
        if is_today:
            # 시간 형식 통일 (HH:MM -> HH:MM:00)
            if len(sc['time']) == 5: 
                sc['time'] += ":00"
            todays_list.append(sc)
    
    todays_list.sort(key=lambda x: x['time'])
    return todays_list

# --- 3. 알림 기능 시계 ---
def show_realtime_clock_with_alert(today_schedules):
    schedules_json = json.dumps(today_schedules, ensure_ascii=False)
    
    clock_html = f"""
    <style>
        .clock-container {{
            font-family: 'Source Sans Pro', sans-serif;
            text-align: center;
            padding: 15px;
            background-color: #ffffff;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            color: #31333F;
            margin-bottom: 20px;
        }}
        .time-text {{ font-size: 2.2em; font-weight: 700; margin: 0; color: #ff4b4b; }}
        .date-text {{ font-size: 1.1em; color: #555; margin-bottom: 5px; }}
    </style>
    <div class="clock-container">
        <div id="date" class="date-text"></div>
        <div id="clock" class="time-text">Loading...</div>
    </div>
    <script>
        var schedules = {schedules_json};
        var alertedTimes = []; 

        function updateClock() {{
            var now = new Date();
            var timeString = now.toLocaleTimeString('ko-KR', {{ hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }});
            var dateString = now.toLocaleDateString('ko-KR', {{ year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' }});
            
            document.getElementById('clock').innerHTML = timeString;
            document.getElementById('date').innerHTML = dateString;

            schedules.forEach(function(item) {{
                if (item.time === timeString && !alertedTimes.includes(timeString)) {{
                    alert("⏰ 시간 됐어요!\\n[" + item.title + "] 할 시간입니다!");
                    alertedTimes.push(timeString);
                }}
            }});
        }}
        setInterval(updateClock, 1000);
        updateClock();
    </script>
    """
    components.html(clock_html, height=130)

# --- 4. 메인 화면 ---
st.set_page_config(page_title="나만의 스터디 플래너", layout="wide", page_icon="📝")

st.sidebar.title("📚 메뉴")
page = st.sidebar.radio("이동", ["대시보드 (Main)", "공부 기록하기", "일정 관리"])

korea_now = get_korea_now()
korea_today_str = korea_now.strftime("%Y-%m-%d")

if page == "대시보드 (Main)":
    today_schedules = get_today_schedules(data['schedules'])
    show_realtime_clock_with_alert(today_schedules)
    
    today_logs = [log for log in data['logs'] if log['date'] == korea_today_str]
    total_minutes = sum(log['duration'] for log in today_logs)
    
    c1, c2 = st.columns(2)
    c1.metric("⏱️ 오늘 공부량", f"{total_minutes} 분")
    c2.metric("🔔 남은 일정", f"{len(today_schedules)} 개")
    
    st.markdown("---")
    
    col_left, col_right = st.columns([1, 1])
    weekday_korean = ["월", "화", "수", "목", "금", "토", "일"][korea_now.weekday()]

    with col_left:
        st.subheader(f"📝 오늘의 일정 ({weekday_korean})")
        if today_schedules:
            for item in today_schedules:
                with st.container(border=True):
                    val_disp = ",".join(item['value']) if isinstance(item['value'], list) else str(item['value'])
                    st.markdown(f"#### ⏰ {item['time']}") 
                    st.markdown(f"**{item['title']}**")
                    st.caption(f"조건: {item['type']} ({val_disp})")
        else:
            st.info(f"오늘은 예정된 일정이 없습니다! ({weekday_korean}요일)")

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
        # [변경] 시/분/초 따로 입력받기 (에러 해결 & 초 단위 입력 가능)
        col_date, c_h, c_m, c_s = st.columns([2, 1, 1, 1])
        input_date = col_date.date_input("날짜", get_korea_today())
        
        # 기본값은 현재 시간
        hh = c_h.number_input("시", 0, 23, korea_now.hour)
        mm = c_m.number_input("분", 0, 59, korea_now.minute)
        ss = c_s.number_input("초", 0, 59, korea_now.second)
        
        # 시간 문자열 조립
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
    
    with st.form("new_schedule"):
        st.subheader("새 일정 추가")
        title = st.text_input("내용 (예: 수학학원)")

        # [변경] 시/분/초 따로 입력받기
        st.write("시간 설정")
        c_h, c_m, c_s = st.columns(3)
        s_h = c_h.number_input("시", 0, 23, 9)
        s_m = c_m.number_input("분", 0, 59, 0)
        s_s = c_s.number_input("초", 0, 59, 0)
        
        schedule_time_str = f"{s_h:02d}:{s_m:02d}:{s_s:02d}"
        
        type_opt = st.selectbox("반복", ["매일", "매주 요일", "특정 날짜"])
        
        val = None
        if type_opt == "매주 요일":
            val = st.multiselect("요일", ["월", "화", "수", "목", "금", "토", "일"])
        elif type_opt == "특정 날짜":
            d = st.date_input("날짜")
            val = d.strftime("%Y-%m-%d")
            
        if st.form_submit_button("추가"):
            if not title:
                st.error("내용을 입력하세요")
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
                st.success("추가됨")
                st.rerun()
    
    st.divider()
    if data['schedules']:
        st.subheader("일정 목록")
        df_sc = pd.DataFrame(data['schedules'])
        # 시간 형식 맞추기
        df_sc['time'] = df_sc['time'].apply(lambda x: x + ":00" if len(str(x)) == 5 else x)
        
        df_sc['disp'] = df_sc['value'].apply(lambda x: ",".join(x) if isinstance(x, list) else x)
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
