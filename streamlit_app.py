"""
🐾 PetKor - 반려동물 동반여행 AI 챗봇
Streamlit Cloud 배포용 단일 앱
"""
import sys
import os

# 로컬 서비스 임포트를 위해 경로 추가
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import folium
from streamlit_folium import st_folium
from typing import List

from services.query_parser import parse_query
from services.retriever import retrieve
from services.llm_service import generate_answer
from services.document_builder import PlaceDocument

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="🐾 PetKor - 반려동물 동반여행",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# 커스텀 CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}

/* 헤더 그라디언트 */
.main-header {
    background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 50%, #FFA07A 100%);
    padding: 2rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    text-align: center;
    box-shadow: 0 8px 32px rgba(255, 107, 107, 0.3);
}
.main-header h1 {
    color: white;
    font-size: 2.5rem;
    font-weight: 700;
    margin: 0;
    text-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.main-header p {
    color: rgba(255,255,255,0.9);
    font-size: 1.1rem;
    margin-top: 0.5rem;
}

/* 장소 카드 */
.place-card {
    background: white;
    border-radius: 16px;
    padding: 1.2rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    border-left: 4px solid #FF6B6B;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.place-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.12);
}
.place-card h3 {
    color: #2D3748;
    font-size: 1.05rem;
    font-weight: 700;
    margin: 0 0 0.4rem 0;
}
.place-card .address {
    color: #718096;
    font-size: 0.85rem;
    margin-bottom: 0.4rem;
}
.place-card .badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-right: 0.3rem;
}
.badge-ok {
    background: #C6F6D5;
    color: #276749;
}
.badge-warn {
    background: #FEFCBF;
    color: #744210;
}
.place-card .score {
    float: right;
    color: #FF6B6B;
    font-weight: 700;
    font-size: 0.8rem;
}
.place-card .overview {
    color: #4A5568;
    font-size: 0.82rem;
    margin-top: 0.5rem;
    line-height: 1.5;
}

/* 채팅 UI */
.stChatMessage {
    border-radius: 12px !important;
}

/* 사이드바 */
.sidebar-section {
    background: linear-gradient(135deg, #FFF5F5, #FFF);
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 1rem;
    border: 1px solid #FFE0E0;
}

/* 검색 결과 스피너 */
.searching-text {
    color: #FF6B6B;
    font-weight: 600;
}

/* 통계 메트릭 */
.metric-container {
    background: linear-gradient(135deg, #FF6B6B, #FF8E53);
    border-radius: 12px;
    padding: 0.8rem 1rem;
    color: white;
    text-align: center;
    margin-bottom: 0.5rem;
}
.metric-container .metric-value {
    font-size: 1.8rem;
    font-weight: 700;
}
.metric-container .metric-label {
    font-size: 0.8rem;
    opacity: 0.85;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# API 키 로드
# ─────────────────────────────────────────────
def get_api_key() -> str:
    """Streamlit secrets 또는 환경변수에서 API 키 로드"""
    try:
        return st.secrets["TOUR_API_KEY"]
    except Exception:
        return os.environ.get("TOUR_API_KEY", "")

# ─────────────────────────────────────────────
# 세션 상태 초기화
# ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_places" not in st.session_state:
    st.session_state.last_places = []
if "total_searches" not in st.session_state:
    st.session_state.total_searches = 0

# ─────────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🐾 PetKor")
    st.markdown("반려동물과 함께하는 여행지를 찾아드려요")
    st.divider()

    st.markdown("#### 🔍 빠른 검색 예시")
    example_queries = [
        "제주도 반려견 동반 카페",
        "서울 강아지랑 갈 수 있는 공원",
        "강릉 반려동물 펜션",
        "부산 고양이 동반 숙소",
        "경주 반려동물 여행지",
        "제주 해변 산책 코스",
        "가평 글램핑 반려동물",
    ]
    for q in example_queries:
        if st.button(f"💬 {q}", key=f"ex_{q}", use_container_width=True):
            st.session_state._quick_query = q

    st.divider()

    # 검색 통계
    st.markdown("#### 📊 이용 현황")
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-value">{st.session_state.total_searches}</div>
        <div class="metric-label">총 검색 횟수</div>
    </div>
    <div class="metric-container">
        <div class="metric-value">{len(st.session_state.last_places)}</div>
        <div class="metric-label">마지막 검색 결과</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    if st.button("🗑️ 대화 초기화", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_places = []
        st.rerun()

    st.markdown("""
    <div style='text-align:center; color: #A0AEC0; font-size: 0.75rem; margin-top: 1rem;'>
        데이터: 한국관광공사 Open API<br>
        반려동물 동반여행 서비스 KorPetTourService2
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 메인 헤더
# ─────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🐾 PetKor 반려동물 동반여행</h1>
    <p>한국관광공사 데이터 기반 · 반려동물과 함께하는 여행지 AI 추천</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 메인 레이아웃 (챗봇 | 지도)
# ─────────────────────────────────────────────
col_chat, col_map = st.columns([1.1, 0.9], gap="large")

# ── 챗봇 패널 ──────────────────────────────
with col_chat:
    st.markdown("#### 💬 여행지 검색 챗봇")

    # 대화 히스토리 표시
    chat_container = st.container(height=480)
    with chat_container:
        if not st.session_state.messages:
            st.markdown("""
            <div style='text-align:center; padding: 3rem 1rem; color: #A0AEC0;'>
                <div style='font-size: 3rem; margin-bottom: 1rem;'>🐾</div>
                <div style='font-size: 1.1rem; font-weight: 600; color: #718096;'>반려동물 동반여행지를 찾아드려요!</div>
                <div style='font-size: 0.85rem; margin-top: 0.5rem;'>
                    왼쪽 사이드바의 예시를 클릭하거나<br>
                    아래 입력창에 질문을 입력해보세요.
                </div>
                <div style='margin-top: 1.5rem; font-size: 0.8rem; color: #CBD5E0;'>
                    예: "제주도 강아지랑 갈 수 있는 카페"
                </div>
            </div>
            """, unsafe_allow_html=True)

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"], avatar="🐾" if msg["role"] == "assistant" else "👤"):
                st.markdown(msg["content"])

    # 입력창
    user_input = st.chat_input("여행지를 물어보세요! 예: 서울 강아지 공원 추천")

    # 빠른 검색 버튼으로 들어온 쿼리 처리
    if hasattr(st.session_state, "_quick_query"):
        user_input = st.session_state._quick_query
        del st.session_state._quick_query

# ── 지도 패널 ──────────────────────────────
with col_map:
    st.markdown("#### 🗺️ 여행지 지도")

    places = st.session_state.last_places

    # 지도 중심 계산
    valid_places = [p for p in places if p.lat and p.lng]
    if valid_places:
        center_lat = sum(p.lat for p in valid_places) / len(valid_places)
        center_lng = sum(p.lng for p in valid_places) / len(valid_places)
        zoom = 10
    else:
        center_lat, center_lng, zoom = 36.5, 127.5, 7  # 한국 중심

    # folium 지도 생성
    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=zoom,
        tiles="CartoDB positron",
    )

    # 마커 추가
    for i, place in enumerate(valid_places):
        pet_icon = "✅" if place.petAvailable else "⚠️"
        popup_html = f"""
        <div style='font-family: sans-serif; min-width: 180px;'>
            <b style='color: #E53E3E; font-size: 14px;'>{place.title}</b><br>
            <span style='color: #718096; font-size: 11px;'>📍 {place.address}</span><br>
            <span style='font-size: 11px;'>{pet_icon} {"반려동물 동반 가능" if place.petAvailable else "조건 확인 필요"}</span>
            {"<br><span style='font-size: 10px; color: #A0AEC0;'>" + (place.caution or "") + "</span>" if place.caution else ""}
        </div>
        """
        folium.Marker(
            location=[place.lat, place.lng],
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=f"{'🟢' if place.petAvailable else '🟡'} {place.title}",
            icon=folium.Icon(
                color="red" if i == 0 else "orange",
                icon="paw" if i == 0 else "info-sign",
                prefix="glyphicon",
            ),
        ).add_to(m)

    st_folium(m, use_container_width=True, height=420, returned_objects=[])

# ─────────────────────────────────────────────
# 장소 카드 섹션 (하단)
# ─────────────────────────────────────────────
if st.session_state.last_places:
    st.divider()
    st.markdown(f"#### 📍 추천 여행지 ({len(st.session_state.last_places)}곳)")
    cols = st.columns(3)
    for i, place in enumerate(st.session_state.last_places):
        with cols[i % 3]:
            badge_cls = "badge-ok" if place.petAvailable else "badge-warn"
            badge_text = "✅ 동반 가능" if place.petAvailable else "⚠️ 조건 확인"
            overview_text = ""
            if place.overview:
                overview_text = f'<div class="overview">{place.overview[:80]}{"..." if len(place.overview) > 80 else ""}</div>'
            elif place.petInfo:
                overview_text = f'<div class="overview">🐾 {place.petInfo[:80]}</div>'

            caution_text = ""
            if place.caution:
                caution_text = f'<div class="overview" style="color:#E67E22;">⚠️ {place.caution[:60]}</div>'

            st.markdown(f"""
            <div class="place-card">
                <span class="score">★ {place.score}</span>
                <h3>{i+1}. {place.title}</h3>
                <div class="address">📍 {place.address or "주소 정보 없음"}</div>
                <span class="badge {badge_cls}">{badge_text}</span>
                {overview_text}
                {caution_text}
            </div>
            """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 쿼리 처리 로직
# ─────────────────────────────────────────────
if user_input:
    api_key = get_api_key()

    if not api_key:
        st.error("⚠️ API 키가 설정되지 않았습니다. `.streamlit/secrets.toml`에 `TOUR_API_KEY`를 설정해주세요.")
        st.stop()

    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.total_searches += 1

    # 검색 실행
    with st.spinner("🔍 반려동물 여행지를 검색 중입니다..."):
        try:
            query = parse_query(user_input)
            places = retrieve(query, api_key=api_key, top_k=9)
            answer, _ = generate_answer(query, places)

            st.session_state.last_places = places
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as e:
            error_msg = f"❌ 검색 중 오류가 발생했습니다: {str(e)}\n\n잠시 후 다시 시도해주세요."
            st.session_state.messages.append({"role": "assistant", "content": error_msg})

    st.rerun()
