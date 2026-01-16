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

# --- 한국 시간 함수 ---
def get_korea_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=9)

def get_korea_today():
    return get_korea_now().date()

# --- [NEW] 청소부 함수: 지난 일정 영구 삭제 ---
def clean_expired_schedules(data):
    now = get_korea_now()
    today_str = now.strftime("%Y-%m-%d")
    current_time_str = now.strftime("%H:%M:%S")
    
    new_schedules = []
    is_changed = False
    
    for sc in data['schedules']:
        # 시간 포맷 안전하게 통일 (HH:MM -> HH:MM:00)
        try:
            parts = sc['time'].split(':')
            h, m, s = int(parts[0]), int(parts[1]), 0
            if len(parts) == 3: s = int(parts[2])
            sc['time'] = f"{h:02d}:{m:02d}:{s:02d}"
        except:
            pass # 포맷 에러나면 건드리지 않음

        keep = True
        
        # 1. '특정 날짜': 날짜가 지났거나, (오늘인데 시간이 지났으면) 삭제
        if sc['type'] == '특정 날짜':
            if sc['value'] < today_str: # 날짜가 어제 이전임
                keep = False
            elif sc['value'] == today_str and sc['time'] < current_time_str: # 오늘인데 시간 지남
                keep = False
                
        # 2. '기간': 종료일이 지났거나, (종료일이 오늘인데 시간이 지났으면) 삭제
        elif sc['type'] == '기간 (Start ~ End)':
            try:
                end_date = sc['value'][1]
                if end_date < today_str:
                    keep = False
                elif end_date == today_str and sc['time'] < current_time_str:
                    keep = False
            except:
                keep = True # 데이터 꼬였으면 안전하게 보존

        # 3. '매일', '매주 요일'은 반복이므로 삭제 안 함
        
        if keep:
            new_schedules.append(sc)
        else:
            is_changed = True # 지워진 게 하나라도 있다!
            
    if is_changed:
        data['schedules'] = new_schedules
        save_data(data) # 파일에 영구 반영
        
    return data

# 데이터 로드 후 바로 청소 시작
data = load_data()
data = clean_expired_schedules(data)

# --- 2. 일정 처리 함수 ---
def process_schedules(schedules):
    now = get_korea_now()
    today_date = now.date()
    today_str = today_date.strftime("%Y-%m-%d")
    weekday_map = ["월", "화", "수", "목", "금", "토", "일"]
    today_weekday = weekday_map[today_date.weekday()] 
    
    todays_list = []
    
    for sc in schedules:
        is_today = False
        if sc['type'] == '매일': is_today = True
        elif sc['type'] == '매주 요일':
            if isinstance(sc['value'], list) and today_weekday in sc['value']: is_today = True
            elif isinstance(sc['value'], str) and sc['value'] == today_weekday: is_today = True
        elif sc['type'] == '특정 날짜' and sc['value'] == today_str: is_today = True
        elif sc['type'] == '기간 (Start ~ End)':
            if isinstance(sc['value'], list) and len(sc['value']) == 2:
                try:
                    s = datetime.datetime.strptime(sc['value'][0], "%Y-%m-%d").date()
                    e = datetime.datetime.strptime(sc['value'][1], "%Y-%m-%d").date()
                    if s <= today_date <= e: is_today = True
                except: pass
        
        if is_today:
            todays_list.append(sc)
            
    todays_list.sort(key=lambda x: x['time'])
    return todays_list

# --- 3. 알림 시계 ---
def show_realtime_clock_with_alert(today_schedules):
    schedules_json = json.dumps(today_schedules, ensure_ascii=False)
    
    # 디버그용: 화면에 알림 대기중인 일정 표시
    debug_list = [f"{i['title']}({i['time']})" for i in today_schedules]
    debug_msg = ", ".join(debug_list) if debug_list else "없음"

    clock_html = f"""
    <style>
        .clock-box {{
            text-align: center; padding: 20px; background: white;
            border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin-bottom: 20px; border: 1px solid #eee;
        }}
        .time-big {{ font-size: 3em; font-weight: 800; color: #FF4B4B; margin: 0; letter-spacing: 2px; }}
        .date-small {{ font-size: 1.2em; color: #555; margin-bottom: 5px; font-weight: bold; }}
        .status {{ font-size: 0.9em; color: #aaa; margin-top: 10px; }}
    </style>
    <div class="clock-box">
        <div id="date" class="date-small"></div>
        <div id="clock" class="time-big">--:--:--</div>
        <div class="status">🔔 알림 대기중: {debug_msg}</div>
    </div>
    <script>
        var schedules = {schedules_json};
        var alertedIds = []; 

        function toSeconds(tStr) {{
            var p = tStr.split(':');
            return parseInt(p[0])*3600 + parseInt(p[1])*60 + parseInt(p[2]);
        }}

        function updateClock() {{
            var now = new Date();
            var h = String(now.getHours()).padStart(2, '0');
            var m = String(now.getMinutes()).padStart(2, '0');
            var s = String(now.getSeconds()).padStart(2, '0');
            var timeString = h + ":" + m + ":" + s;
            
            var currentSeconds = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
            
            document.getElementById('clock').innerHTML = timeString;
            document.getElementById('date').innerHTML = now.toLocaleDateString('ko-KR', {{ weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }});

            schedules.forEach(function(item) {{
                var schedSeconds = toSeconds(item.time);
                var diff = currentSeconds - schedSeconds;

                // 0~5초 차이면 알림 (지나갔어도 바로 울림)
                if (diff >= 0 && diff <= 5) {{
                    if (!alertedIds.includes(item.time + item.title)) {{
                        alert("⏰ [" + item.title + "] 할 시간입니다!\\n" + item.time);
                        alertedIds.push(item.time + item.title);
                    }}
                }}
            }});
        }}
        setInterval(updateClock, 1000);
        updateClock();
    </script>
    """
    components.html(clock_html, height=200)

# --- 4. 메인 화면 ---
st.sidebar.title("📚 메뉴")
page = st.sidebar.radio("이동", ["대시보드 (Main)", "공부 기록하기", "일정 관리"])

korea_now = get_korea_now()
korea_today_str = korea_now.strftime("%Y-%m-%d")

if page == "대시보드 (Main)":
    # 1. 시계 표시 (알림 기능)
    all_schedules = process_schedules(data['schedules'])
    show_realtime_clock_with_alert(all_schedules)
    
    # 2. 화면 표시용 (이미 지난 건 숨기기)
    curr_time_str = korea_now.strftime("%H:%M:%S")
    upcoming = [s for s in all_schedules if s['time'] > curr_time_str]
    
    # 통계
    today_logs = [log for log in data['logs'] if log['date'] == korea_today_str]
    total_minutes = sum(log['duration'] for log in today_logs)
    
    c1, c2 = st.columns(2)
    c1.metric("⏱️ 오늘 공부량", f"{total_minutes} 분")
    c2.metric("🔔 남은 일정", f"{len(upcoming)} 개")
    
    st.markdown("---")
    
    col_L, col_R = st.columns([1, 1])
    weekday_kor = ["월","화","수","목","금","토","일"][korea_now.weekday()]

    with col_L:
        st.subheader(f"📝 남은 일정 ({weekday_kor})")
        if upcoming:
            for item in upcoming:
                with st.container(border=True):
                    st.markdown(f"### ⏰ {item['time']}")
                    st.markdown(f"**📌 {item['title']}**")
                    
                    t_type = item['type']
                    val = item['value']
                    info_text = ""
                    if t_type == "매일": info_text = "🔄 매일 반복"
                    elif t_type == "매주 요일": 
                        days = ",".join(val) if isinstance(val, list) else str(val)
                        info_text = f"📅 매주 {days}요일"
                    elif t_type == "특정 날짜": info_text = f"📆 날짜: {val}"
                    elif t_type == "기간 (Start ~ End)":
                        if isinstance(val, list) and len(val) == 2:
                            info_text = f"🗓️ 기간: {val[0]} ~ {val[1]}"
                    st.info(info_text)
        else:
            st.info("남은 일정이 없습니다! 🎉")

    with col_R:
        st.subheader("🔥 최근 공부 기록")
        if data['logs']:
            df_logs = pd.DataFrame(data['logs']).sort_values(by=["date", "time"], ascending=False).head(5)
            st.dataframe(df_logs[["date", "time", "subject", "duration", "note"]], use_container_width=True, hide_index=True)
        else:
            st.warning("기록이 없습니다.")

elif page == "공부 기록하기":
    st.title("✍️ 공부 기록")
    st.info(f"현재: {korea_now.strftime('%H:%M:%S')}")
    
    with st.form("log"):
        c_d, c_h, c_m, c_s = st.columns([2, 1, 1, 1])
        in_date = c_d.date_input("날짜", get_korea_today())
        hh = c_h.number_input("시", 0, 23, korea_now.hour)
        mm = c_m.number_input("분", 0, 59, korea_now.minute)
        ss = c_s.number_input("초", 0, 59, korea_now.second)
        
        c1, c2 = st.columns(2)
        subj = c1.text_input("과목")
        dur = c2.number_input("시간(분)", value=60)
        note = st.text_area("메모")
        
        if st.form_submit_button("저장"):
            data['logs'].append({
                "date": in_date.strftime("%Y-%m-%d"),
                "time": f"{hh:02d}:{mm:02d}:{ss:02d}",
                "subject": subj, "duration": dur, "note": note,
                "timestamp": str(korea_now)
            })
            save_data(data)
            st.success("완료")
            st.rerun()
            
    st.divider()
    if data['logs']:
        df = pd.DataFrame(data['logs']).sort_values(by=["date", "time"], ascending=False)
        st.dataframe(df[["date", "time", "subject", "duration", "note"]], use_container_width=True, hide_index=True)
        
        with st.expander("삭제"):
            target = st.selectbox("선택", df.index, format_func=lambda i: f"{df.loc[i]['subject']} ({df.loc[i]['time']})")
            if st.button("삭제"):
                ts = df.loc[target]['timestamp']
                data['logs'] = [x for x in data['logs'] if x['timestamp'] != ts]
                save_data(data)
                st.rerun()

elif page == "일정 관리":
    st.title("🗓️ 일정 관리")
    st.subheader("일정 추가")
    
    type_opt = st.selectbox("반복 유형", ["매일", "매주 요일", "특정 날짜", "기간 (Start ~ End)"])
    val = None
    
    if type_opt == "매주 요일":
        val = st.multiselect("요일", ["월","화","수","목","금","토","일"])
    elif type_opt == "특정 날짜":
        val = st.date_input("날짜").strftime("%Y-%m-%d")
    elif type_opt == "기간 (Start ~ End)":
        c1, c2 = st.columns(2)
        d1 = c1.date_input("시작일")
        d2 = c2.date_input("종료일")
        val = [d1.strftime("%Y-%m-%d"), d2.strftime("%Y-%m-%d")]
    
    title = st.text_input("내용")
    st.write("시간 설정")
    c_h, c_m, c_s = st.columns(3)
    s_h = c_h.number_input("시", 0, 23, 9)
    s_m = c_m.number_input("분", 0, 59, 0)
    s_s = c_s.number_input("초", 0, 59, 0)
    
    if st.button("추가", type="primary"):
        if not title: st.error("내용 입력 필요")
        elif type_opt == "매주 요일" and not val: st.error("요일 선택 필요")
        else:
            data['schedules'].append({
                "id": (max([x['id'] for x in data['schedules']] or [0])) + 1,
                "title": title,
                "time": f"{s_h:02d}:{s_m:02d}:{s_s:02d}",
                "type": type_opt, "value": val
            })
            save_data(data)
            st.success("추가됨")
            import time
            time.sleep(0.5)
            st.rerun()

    st.divider()
    if data['schedules']:
        st.subheader("목록")
        df = pd.DataFrame(data['schedules'])
        df['time'] = df['time'].apply(lambda x: x + ":00" if len(x)==5 else x)
        
        def fmt(v):
            if isinstance(v, list):
                if len(v)==2 and v[0][0].isdigit(): return f"{v[0]}~{v[1]}"
                return ",".join(v)
            return v
        df['disp'] = df['value'].apply(fmt)
        df['del'] = False
        
        ed = st.data_editor(df, column_config={"del": st.column_config.CheckboxColumn("삭제"), "title":"내용", "time":"시간", "disp":"상세", "value":None, "id":None}, hide_index=True, use_container_width=True)
        if st.button("선택 삭제"):
            ids = ed[ed['del']]['id'].tolist()
            data['schedules'] = [x for x in data['schedules'] if x['id'] not in ids]
            save_data(data)
            st.rerun()
