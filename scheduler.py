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
        # 데이터 호환성 처리 (기존 데이터에 없는 키가 있을 수 있음)
        if 'all_day' not in sc: sc['all_day'] = False
        if 'no_alert' not in sc: sc['no_alert'] = False

        # 시간 포맷 안전장치
        try:
            parts = sc['time'].split(':')
            h, m, s = int(parts[0]), int(parts[1]), 0
            if len(parts) == 3: s = int(parts[2])
            sc['time'] = f"{h:02d}:{m:02d}:{s:02d}"
        except: pass

        keep = True
        
        # 삭제 로직: '하루 종일'인 경우 시간이 아니라 '날짜'가 지나야 삭제됨
        if sc['type'] == '특정 날짜':
            if sc['value'] < today_str: 
                keep = False
            elif sc['value'] == today_str and not sc['all_day'] and sc['time'] < current_time_str:
                # 오늘인데 '시간 지정' 일정이고 시간이 지났으면 삭제
                keep = False
            # (하루 종일 일정은 오늘 하루 내내 떠있어야 하므로 삭제 안 함)
                
        elif sc['type'] == '기간 (Start ~ End)':
            try:
                if sc['value'][1] < today_str: 
                    keep = False
                elif sc['value'][1] == today_str and not sc['all_day'] and sc['time'] < current_time_str:
                    keep = False
            except: keep = True

        if keep: new_schedules.append(sc)
        else: is_changed = True
            
    if is_changed:
        data['schedules'] = new_schedules
        save_data(data)
    return data

data = load_data()
data = clean_expired_schedules(data)

# --- 2. 일정 계산 함수 ---
def get_schedules_for_date(schedules, target_date):
    target_str = target_date.strftime("%Y-%m-%d")
    weekday_map = ["월", "화", "수", "목", "금", "토", "일"]
    target_weekday = weekday_map[target_date.weekday()] 
    
    matched_list = []
    
    for sc in schedules:
        is_matched = False
        
        if sc['type'] == '매일': is_matched = True
        elif sc['type'] == '매주 요일':
            if isinstance(sc['value'], list) and target_weekday in sc['value']: is_matched = True
            elif isinstance(sc['value'], str) and sc['value'] == target_weekday: is_matched = True
        elif sc['type'] == '특정 날짜' and sc['value'] == target_str: is_matched = True
        elif sc['type'] == '기간 (Start ~ End)':
            if isinstance(sc['value'], list) and len(sc['value']) == 2:
                try:
                    s = datetime.datetime.strptime(sc['value'][0], "%Y-%m-%d").date()
                    e = datetime.datetime.strptime(sc['value'][1], "%Y-%m-%d").date()
                    if s <= target_date <= e: is_matched = True
                except: pass
        
        # 시간 포맷 재확인
        try:
            parts = sc['time'].split(':')
            h, m, s = int(parts[0]), int(parts[1]), 0
            if len(parts) == 3: s = int(parts[2])
            sc['time'] = f"{h:02d}:{m:02d}:{s:02d}"
        except: continue

        if is_matched: matched_list.append(sc)
    
    # 정렬: [하루 종일]이 맨 위, 그 다음 시간순
    # 파이썬 정렬 튜플: (False, "09:00")가 (True, "09:00")보다 앞섬.
    # 우리는 True(하루종일)가 먼저 와야 하므로 'not sc' 사용 -> False(0)가 먼저
    matched_list.sort(key=lambda x: (not x.get('all_day', False), x['time']))
    return matched_list

# --- 3. 알림 시계 (업그레이드) ---
def show_realtime_clock_with_alert(today_schedules):
    # 알림 대상 필터링: '하루 종일' 아니고, '알림 끄기' 안 한 것만
    alert_targets = [
        s for s in today_schedules 
        if not s.get('all_day', False) and not s.get('no_alert', False)
    ]
    schedules_json = json.dumps(alert_targets, ensure_ascii=False)
    
    # 디버그 표시
    debug_list = []
    for i in alert_targets:
        try:
            h = int(i['time'].split(':')[0])
            ampm = "오전" if h < 12 else "오후"
            h12 = h if h <= 12 else h - 12
            if h == 0: h12 = 12
            debug_list.append(f"{i['title']}({ampm} {h12}시)")
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
    today_schedules_for_alert = get_schedules_for_date(data['schedules'], get_korea_today())
    show_realtime_clock_with_alert(today_schedules_for_alert)
    
    st.markdown("### 📅 캘린더 모드")
    col_date_picker, col_empty = st.columns([1, 2])
    selected_date = col_date_picker.date_input("확인하고 싶은 날짜를 선택하세요", get_korea_today())
    
    view_schedules = get_schedules_for_date(data['schedules'], selected_date)
    
    curr_time_str = korea_now.strftime("%H:%M:%S")
    
    # 표시할 일정 필터링
    upcoming = []
    for s in view_schedules:
        # 하루 종일은 무조건 표시
        if s.get('all_day', False):
            upcoming.append(s)
        # 시간 지정 일정은...
        else:
            # 선택한 날짜가 오늘이면 -> 지난 시간은 숨김
            if selected_date == get_korea_today():
                if s['time'] > curr_time_str:
                    upcoming.append(s)
            # 다른 날짜면 -> 시간 상관없이 다 보여줌
            else:
                upcoming.append(s)
    
    today_logs = [log for log in data['logs'] if log['date'] == korea_today_str]
    total_minutes = sum(log['duration'] for log in today_logs)
    
    c1, c2 = st.columns(2)
    c1.metric("⏱️ 오늘 공부량", f"{total_minutes} 분")
    c2.metric("🔔 선택일 일정", f"{len(upcoming)} 개")
    
    st.markdown("---")
    
    col_L, col_R = st.columns([1, 1])
    sel_weekday_kor = ["월","화","수","목","금","토","일"][selected_date.weekday()]
    sel_date_str = selected_date.strftime("%m월 %d일")

    with col_L:
        st.subheader(f"📝 {sel_date_str} ({sel_weekday_kor}) 일정")
        if upcoming:
            for item in upcoming:
                with st.container(border=True):
                    # 시간 표시 로직
                    if item.get('all_day', False):
                        time_disp = "☀️ 하루 종일"
                    else:
                        try:
                            ih = int(item['time'].split(':')[0])
                            im = item['time'].split(':')[1]
                            ampm_str = "오전" if ih < 12 else "오후"
                            ih_12 = ih if ih <= 12 else ih - 12
                            if ih == 0: ih_12 = 12
                            time_disp = f"⏰ {ampm_str} {ih_12}:{im}"
                        except: time_disp = f"⏰ {item['time']}"

                    # 제목 옆에 알림 끔 표시
                    title_disp = item['title']
                    if item.get('no_alert', False) and not item.get('all_day', False):
                        title_disp += " (🔕알림 OFF)"

                    st.markdown(f"### {time_disp}")
                    st.markdown(f"**📌 {title_disp}**")
                    
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
            st.info("일정이 없습니다! 🎉")

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
        
        ampm = c_ampm.selectbox("오전/오후", ["오전", "오후"])
        hh_12 = c_h.number_input("시 (1~12)", 1, 12, 12)
        mm = c_m.number_input("분", 0, 59, 0)
        
        c1, c2 = st.columns(2)
        subj = c1.text_input("과목")
        dur = c2.number_input("시간(분)", value=60)
        note = st.text_area("메모")
        
        if st.form_submit_button("저장"):
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
    
    st.write("옵션 설정")
    # [NEW] 하루 종일 & 알림 끄기 체크박스
    c_check1, c_check2 = st.columns(2)
    is_all_day = c_check1.checkbox("☀️ 하루 종일 (시간 입력 안 함)")
    is_no_alert = c_check2.checkbox("🔕 알림 끄기 (기록만 하고 싶을 때)")

    # 하루 종일이 아닐 때만 시간 입력창 보여줌
    if not is_all_day:
        st.write("시간 설정")
        c_ampm, c_h, c_m = st.columns([1, 1, 1])
        ampm = c_ampm.selectbox("오전/오후", ["오전", "오후"], key="sc_ampm")
        s_h = c_h.number_input("시 (1~12)", 1, 12, 1, key="sc_h")
        s_m = c_m.number_input("분", 0, 59, 0, key="sc_m")
    else:
        st.info("하루 종일 일정으로 설정됩니다.")

    if st.button("추가", type="primary"):
        if not title: st.error("내용 입력 필요")
        elif type_opt == "매주 요일" and not val: st.error("요일 선택 필요")
        else:
            final_time = "00:00:00" # 기본값
            
            if not is_all_day:
                h_24 = s_h
                if ampm == "오후" and s_h != 12: h_24 += 12
                if ampm == "오전" and s_h == 12: h_24 = 0
                final_time = f"{h_24:02d}:{s_m:02d}:00"
            
            data['schedules'].append({
                "id": (max([x['id'] for x in data['schedules']] or [0])) + 1,
                "title": title,
                "time": final_time,
                "type": type_opt, "value": val,
                "all_day": is_all_day,   # 하루 종일 여부
                "no_alert": is_no_alert  # 알림 끄기 여부
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
        # 호환성 처리
        if 'all_day' not in df.columns: df['all_day'] = False
        if 'no_alert' not in df.columns: df['no_alert'] = False

        df['time'] = df['time'].apply(lambda x: x + ":00" if len(str(x))==5 else x)
        
        def fmt_time(row):
            if row['all_day']: return "☀️ 하루 종일"
            t = row['time']
            try:
                h = int(t.split(':')[0])
                m = t.split(':')[1]
                ap = "오전" if h < 12 else "오후"
                h12 = h if h <= 12 else h - 12
                if h == 0: h12 = 12
                res = f"{ap} {h12}:{m}"
                if row['no_alert']: res += " (🔕)"
                return res
            except: return t
            
        def fmt_val(v):
            if isinstance(v, list):
                if len(v)==2 and v[0][0].isdigit(): return f"{v[0]}~{v[1]}"
                return ",".join(v)
            return v
            
        # axis=1로 행 단위 처리
        df['disp_time'] = df.apply(fmt_time, axis=1)
        df['disp_val'] = df['value'].apply(fmt_val)
        df['del'] = False
        
        ed = st.data_editor(
            df, 
            column_config={
                "del": st.column_config.CheckboxColumn("삭제"), 
                "title":"내용", 
                "disp_time":"시간/옵션", 
                "disp_val":"상세", 
                "value":None, "id":None, "time":None, "type":None, 
                "all_day":None, "no_alert":None 
            }, 
            hide_index=True, use_container_width=True
        )
        if st.button("선택 삭제"):
            ids = ed[ed['del']]['id'].tolist()
            data['schedules'] = [x for x in data['schedules'] if x['id'] not in ids]
            save_data(data)
            st.rerun()
