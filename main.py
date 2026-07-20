import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta

# ---------------- 기본 설정 ----------------
st.set_page_config(
    page_title="글로벌 주식 대시보드",
    page_icon="📈",
    layout="wide"
)

# ---------------- 종목 리스트 ----------------
INDICES = {
    "S&P 500 (미국)": "^GSPC",
    "다우존스 (미국)": "^DJI",
    "나스닥 (미국)": "^IXIC",
    "코스피 (한국)": "^KS11",
    "니케이225 (일본)": "^N225",
    "항셍지수 (홍콩)": "^HSI",
    "상해종합 (중국)": "000001.SS",
    "DAX (독일)": "^GDAXI",
    "FTSE100 (영국)": "^FTSE",
    "CAC40 (프랑스)": "^FCHI",
}

STOCKS = {
    "애플 (AAPL)": "AAPL",
    "마이크로소프트 (MSFT)": "MSFT",
    "구글 (GOOGL)": "GOOGL",
    "아마존 (AMZN)": "AMZN",
    "엔비디아 (NVDA)": "NVDA",
    "테슬라 (TSLA)": "TSLA",
    "메타 (META)": "META",
    "삼성전자 (005930.KS)": "005930.KS",
    "SK하이닉스 (000660.KS)": "000660.KS",
    "TSMC (TSM)": "TSM",
}

ALL_TICKERS = {**INDICES, **STOCKS}

# ---------------- 사이드바 ----------------
st.sidebar.title("⚙️ 설정")

category = st.sidebar.radio("카테고리 선택", ["주요 지수", "주요 종목", "직접 입력"])

if category == "주요 지수":
    name = st.sidebar.selectbox("지수 선택", list(INDICES.keys()))
    ticker = INDICES[name]
elif category == "주요 종목":
    name = st.sidebar.selectbox("종목 선택", list(STOCKS.keys()))
    ticker = STOCKS[name]
else:
    ticker = st.sidebar.text_input("티커 직접 입력 (예: AAPL, 005930.KS)", value="AAPL")
    name = ticker

period_map = {
    "1개월": "1mo",
    "3개월": "3mo",
    "6개월": "6mo",
    "1년": "1y",
    "2년": "2y",
    "5년": "5y",
    "최대": "max",
}
period_label = st.sidebar.selectbox("기간 선택", list(period_map.keys()), index=3)
period = period_map[period_label]

chart_type = st.sidebar.radio("차트 유형", ["캔들스틱", "라인차트"])
show_volume = st.sidebar.checkbox("거래량 표시", value=True)
show_ma = st.sidebar.checkbox("이동평균선 표시 (20, 60일)", value=True)

st.sidebar.markdown("---")
st.sidebar.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ---------------- 데이터 로드 ----------------
@st.cache_data(ttl=300)
def load_data(ticker_symbol, period):
    data = yf.Ticker(ticker_symbol)
    hist = data.history(period=period)
    info = data.info
    return hist, info

st.title("📈 글로벌 주식 대시보드")
st.caption("Yahoo Finance 데이터 기반 실시간(지연) 시세 대시보드")

try:
    hist, info = load_data(ticker, period)

    if hist.empty:
        st.error("데이터를 불러올 수 없습니다. 티커를 확인해주세요.")
    else:
        # ---------------- 상단 요약 지표 ----------------
        current_price = hist["Close"].iloc[-1]
        prev_price = hist["Close"].iloc[-2] if len(hist) > 1 else current_price
        change = current_price - prev_price
        change_pct = (change / prev_price) * 100 if prev_price != 0 else 0

        high_52w = hist["High"].max()
        low_52w = hist["Low"].min()
        avg_volume = hist["Volume"].mean()

        st.subheader(f"{name}")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric(
            "현재가",
            f"{current_price:,.2f}",
            f"{change:+.2f} ({change_pct:+.2f}%)"
        )
        col2.metric("기간 최고가", f"{high_52w:,.2f}")
        col3.metric("기간 최저가", f"{low_52w:,.2f}")
        col4.metric("평균 거래량", f"{avg_volume:,.0f}")

        st.markdown("---")

        # ---------------- 차트 ----------------
        rows = 2 if show_volume else 1
        row_heights = [0.7, 0.3] if show_volume else [1.0]

        fig = make_subplots(
            rows=rows, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=row_heights
        )

        if chart_type == "캔들스틱":
            fig.add_trace(
                go.Candlestick(
                    x=hist.index,
                    open=hist["Open"],
                    high=hist["High"],
                    low=hist["Low"],
                    close=hist["Close"],
                    name="가격",
                    increasing_line_color="#ef4444",
                    decreasing_line_color="#3b82f6",
                ),
                row=1, col=1
            )
        else:
            fig.add_trace(
                go.Scatter(
                    x=hist.index,
                    y=hist["Close"],
                    mode="lines",
                    name="종가",
                    line=dict(color="#6366f1", width=2)
                ),
                row=1, col=1
            )

        if show_ma:
            hist["MA20"] = hist["Close"].rolling(window=20).mean()
            hist["MA60"] = hist["Close"].rolling(window=60).mean()
            fig.add_trace(
                go.Scatter(x=hist.index, y=hist["MA20"], mode="lines",
                           name="MA20", line=dict(color="orange", width=1)),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(x=hist.index, y=hist["MA60"], mode="lines",
                           name="MA60", line=dict(color="green", width=1)),
                row=1, col=1
            )

        if show_volume:
            colors = ["#ef4444" if hist["Close"].iloc[i] >= hist["Open"].iloc[i] else "#3b82f6"
                     for i in range(len(hist))]
            fig.add_trace(
                go.Bar(x=hist.index, y=hist["Volume"], name="거래량", marker_color=colors),
                row=2, col=1
            )

        fig.update_layout(
            height=700,
            xaxis_rangeslider_visible=False,
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=40, b=20)
        )

        st.plotly_chart(fig, use_container_width=True)

        # ---------------- 데이터 테이블 ----------------
        with st.expander("📋 원본 데이터 보기"):
            st.dataframe(hist.sort_index(ascending=False), use_container_width=True)

except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
    st.info("티커 심볼이 올바른지 확인해주세요. (예: 미국 AAPL, 한국 005930.KS)")

st.markdown("---")

# ---------------- 글로벌 지수 한눈에 보기 ----------------
st.subheader("🌍 글로벌 주요 지수 한눈에 보기")

cols = st.columns(5)
for i, (idx_name, idx_ticker) in enumerate(INDICES.items()):
    try:
        idx_data = yf.Ticker(idx_ticker).history(period="5d")
        if not idx_data.empty and len(idx_data) > 1:
            last = idx_data["Close"].iloc[-1]
            prev = idx_data["Close"].iloc[-2]
            pct = ((last - prev) / prev) * 100
            with cols[i % 5]:
                st.metric(idx_name, f"{last:,.1f}", f"{pct:+.2f}%")
    except Exception:
        pass
