import streamlit as st
import streamlit.components.v1 as components  # 자바스크립트 사용을 위한 컴포넌트
import pandas as pd
import datetime
import json
import os

# --- 1. 데이터 관리 (JSON 파일 저장/로드) ---
DATA_FILE = "study_planner_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "schedules": [],
            "logs": []
        }
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

data = load_data()

# --- 2. 유틸리티 함수 ---
def get_today_schedules(schedules):
    today = datetime.date.today()
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
            todays_list.append(sc)
    
    todays_list.sort(key=lambda x: x['time'])
    return todays_list

# [추가됨] 자바스크립트 실시간 시계 함수
def show_realtime_clock():
    clock_html = """
    <style>
        .clock-container {
            font-family: 'Source Sans Pro', sans-serif;
            text-align: center;
            padding: 10px;
            background-color: #f0f2f6;
            border-radius: 10px;
            border: 1px solid #dcdcdc;
            color: #31333F;
        }
        .time-text {
            font-size: 2em;
            font-weight: bold;
            margin: 0;
        }
        .date-text {
            font-size: 1em;
            color: #666;
            margin: 0;
        }
    </style>
    <div class="clock-container">
        <div id="date" class="date-text"></div>
        <div id="clock" class="time-text">Loading...</div>
    </div>
    <script>
        function updateClock() {
            var now = new Date();
            var timeString = now.toLocaleTimeString('ko-KR', { hour12: true, hour: '2-digit', minute: '2-digit', second: '2-digit' });
            var dateString = now.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' });
            
            document.getElementById('clock').innerHTML = timeString;
            document.getElementById('date').innerHTML = dateString;
        }
        setInterval(updateClock, 1000); // 1초마다 갱신
        updateClock(); // 즉시 실행
    </script>
    """
    # HTML을 렌더링 (높이는 적절히 조절)
    components.html(clock_html, height=110)

# --- 3. UI 레이아웃 및 페이지 설정 ---
st.set_page_config(page_title="나만의 스터디 플래너", layout="wide", page_icon="📝")

st.sidebar.title("📚 메뉴")
page = st.sidebar.radio("이동", ["대시보드 (Main)", "공부 기록하기", "일정 관리"])

# --- 페이지 1: 대시보드 (Main) ---
if page == "대시보드 (Main)":
    st.title("🏠 대시보드")
    
    # [추가됨] 상단에 실시간 시계 배치
    show_realtime_clock()
    
    st.markdown("---")

    # 통계 데이터 계산
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    today_logs = [log for log in data['logs'] if log['date'] == today_str]
    total_minutes = sum(log['duration'] for log in today_logs)
    today_schedules = get_today_schedules(data['schedules'])
    
    col1, col2 = st.columns(2)
    col1.metric("⏱️ 오늘 공부량", f"{total_minutes} 분")
    col2.metric("🔔 남은 일정", f"{len(today_schedules)} 개")

    st.markdown("---")

    c1, c2 = st.columns([1, 1])

    with c1:
        st.subheader("📝 오늘의 일정")
        if today_schedules:
            for item in today_schedules:
                with st.container(border=True):
                    display_val = item['value']
                    if isinstance(display_val, list):
                        display_val = ",".join(display_val)
                    elif display_val is None:
                        display_val = "All"
                        
                    st.markdown(f"### ⏰ {item['time']}") 
                    st.markdown(f"**{item['title']}**")
                    st.caption(f"조건: {item['type']} ({display_val})")
        else:
            st.info("오늘 예정된 일정이 없습니다.")

    with c2:
        st.subheader("🔥 최근 공부 기록")
        if data['logs']:
            df_logs = pd.DataFrame(data['logs']).sort_values(by=["date", "time"], ascending=False).head(5)
            st.dataframe(
                df_logs[["date", "time", "subject", "duration", "note"]],
                column_config={
                    "date": "날짜", "time": "시간", "subject": "과목", "duration": "분", "note": "내용"
                },
                use_container_width=True, hide_index=True
            )
        else:
            st.warning("아직 공부 기록이 없습니다.")

# --- 페이지 2: 공부 기록하기 ---
elif page == "공부 기록하기":
    st.title("✍️ 공부 기록")
    st.info("공부한 날짜와 시간을 직접 지정하여 기록할 수 있습니다.")
    
    with st.form("log_form"):
        col_date, col_time = st.columns(2)
        input_date = col_date.date_input("공부한 날짜", datetime.date.today())
        # 현재 시간 자동 세팅
        input_time = col_time.time_input("시작 시간", datetime.datetime.now().time())
        
        c1, c2 = st.columns(2)
        subject = c1.text_input("과목명", placeholder="예: 수학, 코딩")
        duration = c2.number_input("공부 시간(분)", min_value=1, step=10, value=60)
        
        note = st.text_area("학습 내용 메모")
        
        if st.form_submit_button("기록 저장"):
            new_log = {
                "date": input_date.strftime("%Y-%m-%d"),
                "time": input_time.strftime("%H:%M"),
                "subject": subject,
                "duration": duration,
                "note": note,
                "timestamp": str(datetime.datetime.now())
            }
            data['logs'].append(new_log)
            save_data(data)
            st.success("저장 완료!")
            st.rerun()

    st.divider()
    st.subheader("📜 전체 기록")
    
    if data['logs']:
        df_all = pd.DataFrame(data['logs']).sort_values(by=["date", "time"], ascending=False)
        st.dataframe(
            df_all[["date", "time", "subject", "duration", "note"]],
            column_config={
                "date": "날짜", "time": "시간", "subject": "과목", "duration": "시간(분)", "note": "메모"
            },
            use_container_width=True, hide_index=True
        )

        with st.expander("기록 삭제하기"):
            log_to_delete = st.selectbox(
                "삭제할 기록 선택", 
                df_all.index, 
                format_func=lambda x: f"[{df_all.loc[x]['date']} {df_all.loc[x]['time']}] {df_all.loc[x]['subject']}"
            )
            if st.button("선택한 기록 삭제"):
                log_item = df_all.loc[log_to_delete].to_dict()
                data['logs'] = [x for x in data['logs'] if x['timestamp'] != log_item['timestamp']]
                save_data(data)
                st.rerun()

# --- 페이지 3: 일정 관리 ---
elif page == "일정 관리":
    st.title("🗓️ 일정 설정")
    
    st.subheader("새 일정 추가")
    with st.form("schedule_form"):
        title = st.text_input("일정 내용", placeholder="예: 영어 단어 암기")
        t_time = st.time_input("일정 시간 설정", datetime.time(9, 0))
        
        s_type = st.selectbox("반복 유형", ["매일", "매주 요일", "특정 날짜"])
        
        s_value = None
        if s_type == "매주 요일":
            s_value = st.multiselect("요일 선택", ["월", "화", "수", "목", "금", "토", "일"])
        elif s_type == "특정 날짜":
            d = st.date_input("날짜 선택")
            s_value = d.strftime("%Y-%m-%d")
            
        if st.form_submit_button("추가하기"):
            if not title:
                st.error("내용을 입력하세요.")
            elif s_type == "매주 요일" and not s_value:
                st.error("요일을 선택하세요.")
            else:
                new_id = (max([x['id'] for x in data['schedules']]) + 1) if data['schedules'] else 1
                new_item = {
                    "id": new_id,
                    "title": title,
                    "time": t_time.strftime("%H:%M"),
                    "type": s_type,
                    "value": s_value
                }
                data['schedules'].append(new_item)
                save_data(data)
                st.success("추가되었습니다.")
                st.rerun()

    st.divider()

    st.subheader("일정 목록 관리")
    if data['schedules']:
        df_sche = pd.DataFrame(data['schedules'])
        def fmt(val):
            if isinstance(val, list): return ", ".join(val)
            return val
        df_view = df_sche.copy()
        df_view['value_display'] = df_view['value'].apply(fmt)
        df_view['delete'] = False
        
        edited = st.data_editor(
            df_view,
            column_config={
                "delete": st.column_config.CheckboxColumn("삭제", default=False),
                "time": st.column_config.TextColumn("시간"),
                "title": "내용", "type": "유형", "value_display": "상세정보",
                "value": None, "id": None
            },
            hide_index=True, use_container_width=True
        )
        
        if st.button("선택한 일정 삭제"):
            del_ids = edited[edited['delete']]['id'].tolist()
            if del_ids:
                data['schedules'] = [s for s in data['schedules'] if s['id'] not in del_ids]
                save_data(data)
                st.success("삭제 완료!")
                st.rerun()
    else:
        st.write("등록된 일정이 없습니다.")