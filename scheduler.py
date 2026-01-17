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

# --- 청소부 함수 (지난 일정 삭제) ---
def clean_expired_schedules(data):
    now = get_korea_now()
    today_str = now.strftime("%Y-%m-%d")
    current_time_str = now.strftime("%H:%M:%S")
    
    new_schedules = []
    is_changed = False
    
    for sc in data['schedules']:
        try:
            parts = sc['time'].split(':')
            h, m, s = int(parts[0]), int(parts[1]), 0
            if len(parts) == 3: s = int(parts[2])
            sc['time'] = f"{h:02d}:{m:02d}:{s:02d}"
        except: pass

        keep = True
        if sc['type'] == '특정 날짜':
            if sc['value'] < today_str: keep = False
            elif sc['value'] == today_str and sc['time'] < current_time_str: keep = False
        elif sc['type'] == '기간 (Start ~ End)':
            try:
                if sc['value'][1] < today_str: keep = False
                elif sc['value'][1] == today_str and sc['time'] < current_time_str: keep = False
            except: keep = True

        if keep: new_schedules.append(sc)
        else: is_changed = True
            
    if is_changed:
        data['schedules'] = new_schedules
        save_data(data)
    return data

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
        
        # 시간 포맷 재확인
        try:
            parts = sc['time'].split(':')
            h, m, s = int(parts[0]), int(parts[1]), 0
            if len(parts) == 3: s = int(parts[2])
            sc['time'] = f"{h:02d}:{m:02d}:{s:02d}"
        except: continue

        if is_today: todays_list.append(sc)
            
    todays_list.sort(key=lambda x: x['time'])
    return todays_list

# --- 3. 알림 시계 ---
def show_realtime_clock_with_alert(today_schedules):
    schedules_json = json.dumps(today_schedules, ensure_ascii=False)
    
    # 디버그용: 화면에 12시간제로 변환해서 보여줌 (가독성 UP)
    debug_list = []
    for i in today_schedules:
        try:
            h = int(i['time'].split(':')[0])
            ampm = "오전" if h < 12 else "오후"
            h_12 = h if h <= 12 else h - 12
            if h == 0: h_12 = 12
            debug_list.append(f"{i['title']}({ampm} {h_12}시)")
        except: pass
        
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
    all_schedules = process_schedules(data['schedules'])
    show_realtime_clock_with_alert(all_schedules)
    
    curr_time_str = korea_now.strftime("%H:%M:%S")
    upcoming = [s for s in all_schedules if s['time'] > curr_time_str]
    
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
                    # 12시간제로 보기 편하게 변환해서 표시
                    try:
                        ih = int(item['time'].split(':')[0])
                        im = item['time'].split(':')[1]
                        ampm_str = "오전" if ih < 12 else "오후"
                        ih_12 = ih if ih <= 12 else ih - 12
                        if ih == 0: ih_12 = 12
                        time_disp = f"{ampm_str} {ih_12}:{im}"
                    except: time_disp = item['time']

                    st.markdown(f"### ⏰ {time_disp}")
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
        c_d, c_ampm, c_h, c_m = st.columns([2, 1, 1, 1])
        in_date = c_d.date_input("날짜", get_korea_today())
        
        # [NEW] 오전/오후 입력 방식
        ampm = c_ampm.selectbox("오전/오후", ["오전", "오후"])
        hh_12 = c_h.number_input("시 (1~12)", 1, 12, 12)
        mm = c_m.number_input("분", 0, 59, 0)
        
        c1, c2 = st.columns(2)
        subj = c1.text_input("과목")
        dur = c2.number_input("시간(분)", value=60)
        note = st.text_area("메모")
        
        if st.form_submit_button("저장"):
            # 24시간제로 변환
            hh_24 = hh_12
            if ampm == "오후" and hh_12 != 12: hh_24 += 12
            if ampm == "오전" and hh_12 == 12: hh_24 = 0
            
            data['logs'].append({
                "date": in_date.strftime("%Y-%m-%d"),
                "time": f"{hh_24:02d}:{mm:02d}:00",
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
    if type_opt == "매주 요일": val = st.multiselect("요일", ["월","화","수","목","금","토","일"])
    elif type_opt == "특정 날짜": val = st.date_input("날짜").strftime("%Y-%m-%d")
    elif type_opt == "기간 (Start ~ End)":
        c1, c2 = st.columns(2)
        d1 = c1.date_input("시작일")
        d2 = c2.date_input("종료일")
        val = [d1.strftime("%Y-%m-%d"), d2.strftime("%Y-%m-%d")]
    
    title = st.text_input("내용")
    
    # [NEW] 시간 입력 UI 개선 (오전/오후 선택)
    st.write("시간 설정")
    c_ampm, c_h, c_m = st.columns([1, 1, 1])
    ampm = c_ampm.selectbox("오전/오후", ["오전", "오후"], key="sc_ampm")
    s_h = c_h.number_input("시 (1~12)", 1, 12, 1, key="sc_h")
    s_m = c_m.number_input("분", 0, 59, 0, key="sc_m")
    
    if st.button("추가", type="primary"):
        if not title: st.error("내용 입력 필요")
        elif type_opt == "매주 요일" and not val: st.error("요일 선택 필요")
        else:
            # 24시간제로 자동 변환 저장
            h_24 = s_h
            if ampm == "오후" and s_h != 12: h_24 += 12
            if ampm == "오전" and s_h == 12: h_24 = 0
            
            data['schedules'].append({
                "id": (max([x['id'] for x in data['schedules']] or [0])) + 1,
                "title": title,
                "time": f"{h_24:02d}:{s_m:02d}:00", # 초는 00으로 고정
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
        
        # 목록에서도 오전/오후로 보여주기
        def fmt_time(t):
            try:
                h = int(t.split(':')[0])
                m = t.split(':')[1]
                ap = "오전" if h < 12 else "오후"
                h12 = h if h <= 12 else h - 12
                if h == 0: h12 = 12
                return f"{ap} {h12}:{m}"
            except: return t
            
        def fmt_val(v):
            if isinstance(v, list):
                if len(v)==2 and v[0][0].isdigit(): return f"{v[0]}~{v[1]}"
                return ",".join(v)
            return v
            
        df['disp_time'] = df['time'].apply(fmt_time) # 보여주기용 시간
        df['disp_val'] = df['value'].apply(fmt_val)
        df['del'] = False
        
        ed = st.data_editor(
            df, 
            column_config={
                "del": st.column_config.CheckboxColumn("삭제"), 
                "title":"내용", 
                "disp_time":"시간", # 원본 time 대신 disp_time 보여줌
                "disp_val":"상세", 
                "value":None, "id":None, "time":None, "type":None # 숨김
            }, 
            hide_index=True, use_container_width=True
        )
        if st.button("선택 삭제"):
            ids = ed[ed['del']]['id'].tolist()
            data['schedules'] = [x for x in data['schedules'] if x['id'] not in ids]
            save_data(data)
            st.rerun()
