import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
import json
import os
import datetime

# --- 1. 페이지 설정 ---
st.set_page_config(
    page_title="대한민국 축제",
    page_icon="🎉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. 커스텀 CSS (Aesthetics 고도화) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&display=swap');
    
    html, body, [data-testid="stSidebar"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* 사이드바 글래스모피즘 스타일 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.95));
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* 폰트 및 제목 커스텀 */
    h1, h2, h3 {
        background: linear-gradient(135deg, #60A5FA 0%, #C084FC 50%, #F472B6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700 !important;
    }
    
    /* 카드 디자인 */
    .festival-card {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 0px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
        transition: all 0.3s ease;
        border: 1px solid #F1F5F9;
        overflow: hidden;
        color: #1E293B;
    }
    .festival-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
        border-color: #6366F1;
    }
    .card-img {
        width: 100%;
        height: 180px;
        object-fit: cover;
        border-bottom: 1px solid #F1F5F9;
    }
    .card-content {
        padding: 16px;
    }
    .card-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 8px;
        color: #0F172A;
        display: -webkit-box;
        -webkit-line-clamp: 1;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .card-info {
        font-size: 0.85rem;
        color: #64748B;
        margin: 4px 0;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .detail-btn {
        display: inline-block;
        margin-top: 12px;
        padding: 6px 16px;
        background: linear-gradient(135deg, #6366F1, #4F46E5);
        color: white;
        border-radius: 20px;
        font-size: 0.8rem;
        text-decoration: none;
        font-weight: 500;
        text-align: center;
        transition: 0.2s;
    }
    .detail-btn:hover {
        background: #4338CA;
        color: white;
    }
    
    /* 메트릭 박스 */
    [data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 700;
        color: #1E293B;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 데이터 로드 및 전처리 ---
@st.cache_data
def load_data():
    if not os.path.exists('festivals.json'):
        # Fallback empty data or generate fallback if file not exists
        return pd.DataFrame()
        
    with open('festivals.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    
    if df.empty:
        return df
        
    # 데이터 정제 및 파생 변수 생성
    # 1. 시/도 추출 (location에서 첫 단어 추출)
    df['sido'] = df['location'].apply(lambda x: x.split()[0] if isinstance(x, str) and x.split() else '기타')
    
    # 대표 시도 매핑 정규화 (예: 서울시 -> 서울)
    sido_map = {
        '서울특별시': '서울', '부산광역시': '부산', '대구광역시': '대구', 
        '인천광역시': '인천', '광주광역시': '광주', '대전광역시': '대전', 
        '울산광역시': '울산', '세종특별자치시': '세종', '경기도': '경기',
        '강원도': '강원', '충청북도': '충북', '충청남도': '충남',
        '전라북도': '전북', '전라남도': '전남', '경상북도': '경북',
        '경상남도': '경남', '제주도': '제주'
    }
    df['sido'] = df['sido'].replace(sido_map)
    
    # 2. 기간에서 월(Month) 추출 (간단히 매칭)
    def extract_month(period_str):
        for m in range(1, 13):
            if f"{m}." in period_str or f" {m}월" in period_str:
                return m
        return 12 # 기본값
        
    df['month'] = df['period'].apply(extract_month)
    df['month_str'] = df['month'].astype(str) + "월"
    
    return df

df = load_data()

# --- 4. 에러 핸들링 ---
if df.empty:
    st.error("데이터를 불러오지 못했습니다. `data_collector.py`를 실행하여 데이터를 먼저 수집해주세요.")
    st.stop()

# --- 5. 사이드바 (필터 컨트롤) ---
st.sidebar.image("https://images.unsplash.com/photo-1540959733332-e94e2708f08a?auto=format&fit=crop&w=300&q=80", use_column_width=True)
st.sidebar.markdown("### 🔍 축제 필터")

# 지역 필터
sido_options = ['전체'] + sorted(df['sido'].unique().tolist())
selected_sido = st.sidebar.selectbox("🗺️ 지역 선택", sido_options)

# 월 필터
month_options = ['전체'] + [f"{i}월" for i in range(1, 13)]
selected_month = st.sidebar.selectbox("📅 월별 필터", month_options)

# 검색
search_query = st.sidebar.text_input("🔎 축제 이름 검색")

# 데이터 필터링
filtered_df = df.copy()
if selected_sido != '전체':
    filtered_df = filtered_df[filtered_df['sido'] == selected_sido]
if selected_month != '전체':
    filtered_df = filtered_df[filtered_df['month_str'] == selected_month]
if search_query:
    filtered_df = filtered_df[filtered_df['title'].str.contains(search_query, case=False)]

# --- 6. 메인 헤더 ---
st.title("🇰🇷 대한민국 축제 탐색기 & 분석")
st.markdown("정부부처 및 지자체 공식 정보 기반 제공")

# --- 7. 메트릭 상단 셀 (KPI) ---
m_col1, m_col2, m_col3 = st.columns(3)

with m_col1:
    st.metric(label="📊 총 축제 수", value=f"{len(filtered_df)}개")
with m_col2:
    current_month_name = f"{datetime.datetime.now().month}월"
    this_month_count = len(df[df['month_str'] == current_month_name])
    st.metric(label=f"⏰ {current_month_name} 개최 축제", value=f"{this_month_count}개")
with m_col3:
    if not filtered_df.empty:
        top_sido = filtered_df['sido'].value_counts().idxmax()
        st.metric(label="🏆 최다 개최 지역", value=top_sido)
    else:
        st.metric(label="🏆 최다 개최 지역", value="-")

st.markdown("---")

# --- 8. 메인 바디 레이아웃 (지도 & 리스트) ---
body_col1, body_col2 = st.columns([12, 10])

with body_col1:
    st.subheader("📍 축제 분포 지도")
    
    if not filtered_df.empty:
        # Pydeck 레이어 설정
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=filtered_df,
            get_position="[lng, lat]",
            get_color="[220, 38, 38, 160]" if not df.empty else "[49, 130, 206, 160]",
            get_radius=20000, # 반지름
            pickable=True,
            opacity=0.8,
            stroked=True,
            filled=True,
            radius_scale=1,
            radius_min_pixels=6,
            radius_max_pixels=20,
            line_width_min_pixels=1,
            get_line_color=[255, 255, 255]
        )
        
        # 뷰포트 센터
        view_state = pdk.ViewState(
            latitude=filtered_df['lat'].mean(),
            longitude=filtered_df['lng'].mean(),
            zoom=6.5,
            pitch=0
        )
        
        # 툴팁 설정 (HTML 지원)
        r = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={
                "html": """
                <div style="font-family: 'Outfit', sans-serif; padding: 10px;">
                    <b style="font-size: 1.1rem; color: #4338CA;">{title}</b><br/>
                    <b>📍 장소:</b> {location}<br/>
                    <b>📅 기간:</b> {period}<br/>
                    <img src="{image_url}" width="200" style="border-radius: 8px; margin-top: 8px;"/>
                </div>
                """,
                "style": {
                    "backgroundColor": "white",
                    "color": "#1E293B",
                    "borderRadius": "12px",
                    "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                }
            },
            map_style="light" # 또는 dark
        )
        
        st.pydeck_chart(r)
    else:
        st.info("조건에 부합하는 축제가 없습니다.")

with body_col2:
    st.subheader("📋 축제 리스트")
    
    # 스크롤 가능한 상세 리스트 (streamlit expander 또는 custom html)
    container = st.container(height=500)
    
    with container:
        if filtered_df.empty:
            st.write("표시할 축제 정보가 없습니다.")
        else:
            # 2열로 카드 배치용 컬럼 생성
            items = filtered_df.to_dict('records')
            for i in range(0, len(items), 2):
                col_c1, col_c2 = st.columns(2)
                
                with col_c1:
                    item = items[i]
                    # 이미지 결측 처리
                    img_src = item['image_url'] if item['image_url'] else "https://images.unsplash.com/photo-1517457373958-b7bdd4587205?auto=format&fit=crop&w=400&q=80"
                    
                    st.markdown(f"""
                    <div class="festival-card">
                        <img class="card-img" src="{img_src}" onerror="this.src='https://images.unsplash.com/photo-1517457373958-b7bdd4587205?auto=format&fit=crop&w=400&q=80'">
                        <div class="card-content">
                            <div class="card-title">{item['title']}</div>
                            <div class="card-info">📍 {item['location']}</div>
                            <div class="card-info">📅 {item['period']}</div>
                            <a class="detail-btn" href="{item['detail_url']}" target="_blank">🔎 상세 정보</a>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                if i + 1 < len(items):
                    with col_c2:
                        item = items[i+1]
                        img_src = item['image_url'] if item['image_url'] else "https://images.unsplash.com/photo-1517457373958-b7bdd4587205?auto=format&fit=crop&w=400&q=80"
                        
                        st.markdown(f"""
                        <div class="festival-card">
                            <img class="card-img" src="{img_src}" onerror="this.src='https://images.unsplash.com/photo-1517457373958-b7bdd4587205?auto=format&fit=crop&w=400&q=80'">
                            <div class="card-content">
                                <div class="card-title">{item['title']}</div>
                                <div class="card-info">📍 {item['location']}</div>
                                <div class="card-info">📅 {item['period']}</div>
                                <a class="detail-btn" href="{item['detail_url']}" target="_blank">🔎 상세 정보</a>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

st.markdown("---")

# --- 9. 데이터 시각화 분석 단 영역 ---
st.subheader("📈 페스티벌 트렌드 분석")
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    if not filtered_df.empty:
        sido_counts = filtered_df['sido'].value_counts().reset_index()
        sido_counts.columns = ['지역', '축제 수']
        
        fig = px.bar(
            sido_counts, x='지역', y='축제 수',
            title='📌 지역별 축제 개최 현황',
            labels={'축제 수': '축제 수 (건)', '지역': '지역'},
            color='축제 수', # 바 색상 매핑
            color_continuous_scale=px.colors.sequential.Tealgrn,
        )
        # 디자인 꾸미기
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font={'color': '#1E293B'})
        st.plotly_chart(fig, use_column_width=True)

with chart_col2:
    if not filtered_df.empty:
        # 월별 카운트 정렬
        month_order = [f"{i}월" for i in range(1, 13)]
        month_counts = filtered_df['month_str'].value_counts().reindex(month_order).fillna(0).reset_index()
        month_counts.columns = ['월', '축제 수']
        
        fig_line = px.line(
            month_counts, x='월', y='축제 수',
            title='🗓️ 월별 축제 개최 트렌드',
            markers=True,
            line_shape='spline' # 곡선
        )
        fig_line.update_traces(line_color='#8B5CF6', marker=dict(size=8, color='#EC4899'))
        fig_line.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font={'color': '#1E293B'})
        st.plotly_chart(fig_line, use_column_width=True)
