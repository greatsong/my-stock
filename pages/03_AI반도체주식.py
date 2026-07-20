import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import time
from datetime import datetime

# ---------------- 기본 설정 ----------------
st.set_page_config(
    page_title="AI 반도체 전문 분석",
    page_icon="🧠",
    layout="wide"
)

# ---------------- AI 반도체 종목 리스트 ----------------
AI_CHIP_STOCKS = {
    "엔비디아 (NVDA)": "NVDA",
    "AMD (AMD)": "AMD",
    "브로드컴 (AVGO)": "AVGO",
    "TSMC (TSM)": "TSM",
    "ASML (ASML)": "ASML",
    "인텔 (INTC)": "INTC",
    "퀄컴 (QCOM)": "QCOM",
    "마이크론 (MU)": "MU",
    "마벨테크 (MRVL)": "MRVL",
    "슈퍼마이크로 (SMCI)": "SMCI",
    "삼성전자 (005930.KS)": "005930.KS",
    "SK하이닉스 (000660.KS)": "000660.KS",
    "ARM홀딩스 (ARM)": "ARM",
    "램리서치 (LRCX)": "LRCX",
    "어플라이드머티리얼즈 (AMAT)": "AMAT",
}

SECTOR_ETF = {"필라델피아 반도체 지수 ETF": "SOXX"}

# ---------------- 재시도 유틸 ----------------
def fetch_with_retry(func, max_retries=3, base_delay=2):
    for attempt in range(max_retries):
        try:
            result = func()
            if result is None or (hasattr(result, "empty") and result.empty):
                raise ValueError("empty data")
            return result
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(base_delay * (2 ** attempt))
    return None

# ---------------- 데이터 로드 함수 ----------------
@st.cache_data(ttl=600, show_spinner="AI 반도체 데이터 불러오는 중...")
def load_batch(tickers):
    def _fetch():
        return yf.download(tickers, period="1y", group_by="ticker", progress=False, threads=False)
    return fetch_with_retry(_fetch)

@st.cache_data(ttl=600, show_spinner=False)
def load_single_info(ticker_symbol):
    def _fetch():
        return yf.Ticker(ticker_symbol).info
    try:
        return fetch_with_retry(_fetch)
    except Exception:
        return {}

@st.cache_data(ttl=600, show_spinner=False)
def load_single_history(ticker_symbol, period="1y"):
    def _fetch():
        return yf.Ticker(ticker_symbol).history(period=period)
    return fetch_with_retry(_fetch)

# ---------------- 사이드바 ----------------
st.sidebar.title("🧠 AI 반도체 분석 설정")

selected_names = st.sidebar.multiselect(
    "비교할 종목 선택 (최대 6개 권장)",
    list(AI_CHIP_STOCKS.keys()),
    default=["엔비디아 (NVDA)", "AMD (AMD)", "브로드컴 (AVGO)", "TSMC (TSM)"]
)

focus_name = st.sidebar.selectbox("상세 분석 종목", list(AI_CHIP_STOCKS.keys()), index=0)
focus_ticker = AI_CHIP_STOCKS[focus_name]

period_map = {"3개월": "3mo", "6개월": "6mo", "1년": "1y", "2년": "2y", "5년": "5y"}
period_label = st.sidebar.selectbox("기간", list(period_map.keys()), index=2)
period = period_map[period_label]

st.sidebar.markdown("---")
if st.sidebar.button("🔄 새로고침 (캐시 초기화)"):
    st.cache_data.clear()
    st.rerun()
st.sidebar.caption(f"업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ---------------- 헤더 ----------------
st.title("🧠 AI 반도체 전문 분석 대시보드")
st.caption("엔비디아, AMD, TSMC 등 AI 반도체 밸류체인 핵심 기업 심층 분석")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 종목 상세 분석", "⚖️ 상대 성과 비교", "💰 밸류에이션 비교", "🔗 상관관계 분석"
])

# =========================================================
# TAB 1. 종목 상세 분석
# =========================================================
with tab1:
    st.subheader(f"📊 {focus_name} 상세 분석")

    try:
        hist = load_single_history(focus_ticker, period)
        info = load_single_info(focus_ticker)

        if hist is None or hist.empty:
            st.warning("데이터를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.")
        else:
            current = hist["Close"].iloc[-1]
            prev = hist["Close"].iloc[-2] if len(hist) > 1 else current
            change_pct = ((current - prev) / prev) * 100

            high_period = hist["High"].max()
            low_period = hist["Low"].min()

            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("현재가", f"${current:,.2f}", f"{change_pct:+.2f}%")
            col2.metric("기간 최고", f"${high_period:,.2f}")
            col3.metric("기간 최저", f"${low_period:,.2f}")
            col4.metric("시가총액", f"${info.get('marketCap', 0)/1e9:,.1f}B" if info.get('marketCap') else "N/A")
            col5.metric("PER", f"{info.get('trailingPE', 0):.1f}" if info.get('trailingPE') else "N/A")

            st.markdown("---")

            # 캔들스틱 + 이동평균 + 거래량
            hist["MA20"] = hist["Close"].rolling(20).mean()
            hist["MA60"] = hist["Close"].rolling(60).mean()
            hist["MA120"] = hist["Close"].rolling(120).mean()

            fig = make_subplots(
                rows=3, cols=1, shared_xaxes=True,
                vertical_spacing=0.03,
                row_heights=[0.55, 0.2, 0.25],
                subplot_titles=("가격 & 이동평균선", "RSI (14)", "거래량")
            )

            fig.add_trace(go.Candlestick(
                x=hist.index, open=hist["Open"], high=hist["High"],
                low=hist["Low"], close=hist["Close"], name="가격",
                increasing_line_color="#ef4444", decreasing_line_color="#3b82f6"
            ), row=1, col=1)

            for ma, color in [("MA20", "orange"), ("MA60", "green"), ("MA120", "purple")]:
                fig.add_trace(go.Scatter(
                    x=hist.index, y=hist[ma], mode="lines", name=ma,
                    line=dict(color=color, width=1)
                ), row=1, col=1)

            # RSI 계산
            delta = hist["Close"].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            fig.add_trace(go.Scatter(
                x=hist.index, y=rsi, mode="lines", name="RSI",
                line=dict(color="#8b5cf6", width=1.5)
            ), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="blue", row=2, col=1)

            colors = ["#ef4444" if hist["Close"].iloc[i] >= hist["Open"].iloc[i] else "#3b82f6"
                     for i in range(len(hist))]
            fig.add_trace(go.Bar(
                x=hist.index, y=hist["Volume"], name="거래량", marker_color=colors
            ), row=3, col=1)

            fig.update_layout(
                height=850,
                xaxis_rangeslider_visible=False,
                template="plotly_white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=40, b=20)
            )
            fig.update_yaxes(range=[0, 100], row=2, col=1)

            st.plotly_chart(fig, use_container_width=True)

            # 기업 정보
            with st.expander("🏢 기업 개요"):
                st.write(f"**섹터:** {info.get('sector', 'N/A')}")
                st.write(f"**산업:** {info.get('industry', 'N/A')}")
                st.write(f"**직원 수:** {info.get('fullTimeEmployees', 'N/A'):,}" if info.get('fullTimeEmployees') else "N/A")
                st.write(f"**설명:** {info.get('longBusinessSummary', '정보 없음')[:500]}...")

    except Exception as e:
        st.error("데이터 조회 중 오류(요청 제한 가능성). 잠시 후 다시 시도해주세요.")
        st.caption(f"상세: {e}")

# =========================================================
# TAB 2. 상대 성과 비교 (정규화된 수익률)
# =========================================================
with tab2:
    st.subheader("⚖️ 종목별 상대 성과 비교 (기준일 = 100)")

    if len(selected_names) < 1:
        st.info("사이드바에서 비교할 종목을 1개 이상 선택해주세요.")
    else:
        try:
            tickers = [AI_CHIP_STOCKS[n] for n in selected_names] + list(SECTOR_ETF.values())
            data = load_batch(tickers)

            if data is None or data.empty:
                st.warning("데이터를 불러올 수 없습니다.")
            else:
                fig = go.Figure()
                all_names = selected_names + list(SECTOR_ETF.keys())
                all_tickers = tickers

                for name, tkr in zip(all_names, all_tickers):
                    try:
                        closes = data[tkr]["Close"].dropna()
                        if len(closes) > 0:
                            normalized = (closes / closes.iloc[0]) * 100
                            is_etf = tkr in SECTOR_ETF.values()
                            fig.add_trace(go.Scatter(
                                x=normalized.index, y=normalized.values,
                                mode="lines", name=name,
                                line=dict(width=3 if is_etf else 2, dash="dash" if is_etf else "solid")
                            ))
                    except Exception:
                        continue

                fig.update_layout(
                    height=550,
                    template="plotly_white",
                    yaxis_title="정규화 지수 (시작일=100)",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig, use_container_width=True)

                st.markdown("##### 📈 기간 수익률 순위")
                returns = []
                for name, tkr in zip(all_names, all_tickers):
                    try:
                        closes = data[tkr]["Close"].dropna()
                        ret = ((closes.iloc[-1] / closes.iloc[0]) - 1) * 100
                        returns.append({"종목": name, "수익률(%)": round(ret, 2)})
                    except Exception:
                        continue

                if returns:
                    df_returns = pd.DataFrame(returns).sort_values("수익률(%)", ascending=False)
                    st.dataframe(
                        df_returns.style.format({"수익률(%)": "{:+.2f}"}),
                        use_container_width=True, hide_index=True
                    )

        except Exception as e:
            st.error("데이터 조회 중 오류(요청 제한 가능성). 잠시 후 다시 시도해주세요.")
            st.caption(f"상세: {e}")

# =========================================================
# TAB 3. 밸류에이션 비교
# =========================================================
with tab3:
    st.subheader("💰 밸류에이션 & 펀더멘털 비교")

    compare_names = selected_names if selected_names else list(AI_CHIP_STOCKS.keys())[:6]

    try:
        rows = []
        for name in compare_names:
            tkr = AI_CHIP_STOCKS[name]
            info = load_single_info(tkr)
            rows.append({
                "종목": name,
                "현재가": info.get("currentPrice") or info.get("regularMarketPrice"),
                "시가총액($B)": round(info.get("marketCap", 0) / 1e9, 1) if info.get("marketCap") else None,
                "PER": round(info.get("trailingPE", 0), 1) if info.get("trailingPE") else None,
                "Forward PER": round(info.get("forwardPE", 0), 1) if info.get("forwardPE") else None,
                "PEG": round(info.get("pegRatio", 0), 2) if info.get("pegRatio") else None,
                "매출성장률(%)": round(info.get("revenueGrowth", 0) * 100, 1) if info.get("revenueGrowth") else None,
                "영업이익률(%)": round(info.get("operatingMargins", 0) * 100, 1) if info.get("operatingMargins") else None,
                "ROE(%)": round(info.get("returnOnEquity", 0) * 100, 1) if info.get("returnOnEquity") else None,
                "52주 최고": info.get("fiftyTwoWeekHigh"),
                "52주 최저": info.get("fiftyTwoWeekLow"),
            })

        df_val = pd.DataFrame(rows)
        st.dataframe(df_val, use_container_width=True, hide_index=True)

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("##### PER 비교")
            df_pe = df_val.dropna(subset=["PER"])
            if not df_pe.empty:
                fig_pe = go.Figure(go.Bar(
                    x=df_pe["종목"], y=df_pe["PER"],
                    marker_color="#6366f1", text=df_pe["PER"], textposition="outside"
                ))
                fig_pe.update_layout(height=400, template="plotly_white", margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig_pe, use_container_width=True)

        with col2:
            st.markdown("##### 매출 성장률 비교")
            df_growth = df_val.dropna(subset=["매출성장률(%)"])
            if not df_growth.empty:
                fig_growth = go.Figure(go.Bar(
                    x=df_growth["종목"], y=df_growth["매출성장률(%)"],
                    marker_color="#10b981", text=df_growth["매출성장률(%)"], textposition="outside"
                ))
                fig_growth.update_layout(height=400, template="plotly_white", margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig_growth, use_container_width=True)

    except Exception as e:
        st.error("밸류에이션 데이터 조회 중 오류(요청 제한 가능성). 잠시 후 다시 시도해주세요.")
        st.caption(f"상세: {e}")

# =========================================================
# TAB 4. 상관관계 분석
# =========================================================
with tab4:
    st.subheader("🔗 종목 간 수익률 상관관계")

    if len(selected_names) < 2:
        st.info("상관관계 분석을 위해 사이드바에서 종목을 2개 이상 선택해주세요.")
    else:
        try:
            tickers = [AI_CHIP_STOCKS[n] for n in selected_names]
            data = load_batch(tickers)

            if data is None or data.empty:
                st.warning("데이터를 불러올 수 없습니다.")
            else:
                returns_df = pd.DataFrame()
                for name, tkr in zip(selected_names, tickers):
                    try:
                        closes = data[tkr]["Close"].dropna()
                        daily_ret = closes.pct_change().dropna()
                        returns_df[name] = daily_ret
                    except Exception:
                        continue

                if not returns_df.empty:
                    corr = returns_df.corr()

                    fig_corr = go.Figure(data=go.Heatmap(
                        z=corr.values,
                        x=corr.columns,
                        y=corr.columns,
                        colorscale="RdBu_r",
                        zmid=0,
                        text=np.round(corr.values, 2),
                        texttemplate="%{text}",
                        textfont=dict(size=11),
                        colorbar=dict(title="상관계수")
                    ))
                    fig_corr.update_layout(
                        height=550, template="plotly_white",
                        margin=dict(l=20, r=20, t=40, b=20)
                    )
                    st.plotly_chart(fig_corr, use_container_width=True)

                    st.caption("💡 1에 가까울수록 함께 움직이는 경향이 강하고, 0에 가까울수록 독립적으로 움직입니다.")

        except Exception as e:
            st.error("상관관계 분석 중 오류(요청 제한 가능성). 잠시 후 다시 시도해주세요.")
            st.caption(f"상세: {e}")

st.markdown("---")
st.caption("⚠️ 본 대시보드는 투자 참고 자료이며, 투자 판단과 책임은 투자자 본인에게 있습니다.")
