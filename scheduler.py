import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import datetime
import json
import os

# --- 1. 기본 설정 및 데이터 관리 ---
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
    return datetime.datetime.utcnow() + datetime.timedelta(hours=9)

def get_korea_today():
    return get_korea_now().date()

# --- 2. 일정 필터링 함수 (기간 로직 추가됨) ---
def get_upcoming_schedules(schedules):
    now = get_korea_now()
    today_date = now.date()
    current_time_str = now.strftime("%H:%M:%S")
    
    weekday_map = ["월", "화", "수", "목", "금", "토", "일"]
    today_weekday = weekday_map[today_date.weekday()] 
    today_str = today_date.strftime("%Y-%m-%d")
    
    upcoming_list = []
    
    for sc in schedules:
        is_today = False
        
        # [1] 반복 유형 체크
        if sc['type'] == '매일':
            is_today = True
            
        elif sc['type'] == '매주 요일':
            if isinstance(sc['value'], list) and today_weekday in sc['value']:
                is_today = True
            elif isinstance(sc['value'], str) and sc['value'] == today_weekday:
                is_today = True
                
        elif sc['type'] == '특정 날짜' and sc['value'] == today_str:
            is_today = True
            
        # [추가됨] 기간 (Start ~ End) 로직
        elif sc['type'] == '기간 (Start ~ End)':
            # value가 [시작일, 종료일] 형태여야 함
            if isinstance(sc['value'], list) and len(sc['value']) == 2:
                try:
                    start_date = datetime.datetime.strptime(sc['value'][0], "%Y-%m-%d").date()
                    end_date = datetime.datetime.strptime(sc['value'][1], "%Y-%m-%d").date()
                    # 오늘이 시작일과 종료일 사이에 있으면 True
                    if start_date <= today_date <= end_date:
                        is_today = True
                except:
                    pass # 날짜 형식이 꼬였을 경우 무시

        # [2] 시간 포맷 통일
        if len(sc['time']) == 5: 
            sc['time'] += ":00"

        # [3] 시간이 안 지난 것만 담기
        if is_today and sc['time'] > current_time_str:
            upcoming_list.append(sc)
    
    upcoming_list.sort(key=lambda x: x['time'])
    return upcoming_list

# 알림용 전체 일정 (기간 로직 추가됨)
def get_today_all_schedules_for_alert(schedules):
    today_date = get_korea_today()
    weekday_map = ["월", "화", "수", "목", "금", "토", "일"]
    today_weekday = weekday_map[today_date.weekday()] 
    today_str = today_date.strftime("%Y-%m-%d")
    
    alert_list = []
    for sc in schedules:
        is_today = False
        if sc['type'] == '매일': is_today = True
        elif sc['type'] == '매주 요일':
            if isinstance(sc['value'], list) and today_weekday in sc['value']: is_today = True
            elif isinstance(sc['value'], str) and sc['value'] == today_weekday: is_today = True
        elif sc['type'] == '특정 날짜' and sc['value'] == today_str: is_today = True
        
        # [추가됨] 기간 로직
        elif sc['type'] == '기간 (Start ~ End)':
            if isinstance(sc['value'], list) and len(sc['value']) == 2:
                try:
                    start_date = datetime.datetime.strptime(sc['value'][0], "%Y-%m-%d").date()
                    end_date = datetime.datetime.strptime(sc['value'][1], "%Y-%m-%d").date()
                    if start_date <= today_date <= end_date:
                        is_today = True
                except: pass
        
        if len(sc['time']) == 5: sc['time'] += ":00"
        
        if is_today:
            alert_list.append(sc)
    return alert_list

# --- 3. 알림 시계 ---
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
            var h = String(now.getHours()).padStart(2, '0');
            var m = String(now.getMinutes()).padStart(2, '0');
            var s = String(now.getSeconds()).padStart(2, '0');
            var timeString = h + ":" + m + ":" + s;
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
st.sidebar.title("📚 메뉴")
page = st.sidebar.radio("이동", ["대시보드 (Main)", "공부 기록하기", "일정 관리"])

korea_now = get_korea_now()
korea_today_str = korea_now.strftime("%Y-%m-%d")

if page == "대시보드 (Main)":
    alert_schedules = get_today_all_schedules_for_alert(data['schedules'])
    show_realtime_clock_with_alert(alert_schedules)
    
    upcoming_schedules = get_upcoming_schedules(data['schedules'])
    
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
                    # 값 표시 예쁘게 (기간인 경우 ~ 표시)
                    val = item['value']
                    if item['type'] == '기간 (Start ~ End)' and isinstance(val, list):
                        val_disp = f"{val[0]} ~ {val[1]}"
                    else:
                        val_disp = ",".join(val) if isinstance(val, list) else str(val)
                        
                    st.markdown(f"#### ⏰ {item['time']}") 
                    st.markdown(f"**{item['title']}**")
                    st.caption(f"조건: {item['type']} ({val_disp})")
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
    
    # 1. 반복 유형 선택 (기간 추가됨)
    type_opt = st.selectbox("반복 유형", ["매일", "매주 요일", "특정 날짜", "기간 (Start ~ End)"])
    
    # 2. 유형에 따른 추가 옵션
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
    schedule_time_str = f"{s_h:02d}:{s_m:02d}:{s_s:02d}"

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
        df_sc['time'] = df_sc['time'].apply(lambda x: x + ":00" if len(str(x)) == 5 else x)
        
        # 목록에서 보여줄 때 리스트([]) 깨지지 않게 변환
        def fmt_val(v):
            if isinstance(v, list):
                if len(v) == 2 and v[0][0].isdigit(): # 날짜 두개면 기간으로 표시
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
