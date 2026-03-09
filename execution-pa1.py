import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
# NEW IMPORT: For auto-refreshing the UI
from streamlit_autorefresh import st_autorefresh

# --- 1. Page Configuration ---
st.set_page_config(page_title="Market Analyzer V18: Auto-Refresh", layout="wide")
st.markdown("""<style> .main { background-color: #0e1117; } .stMetric { background-color: #161b22; border-radius: 10px; padding: 15px; border: 1px solid #30363d; } </style>""", unsafe_allow_html=True)
st.title("⚡ Market Analyzer Pro: Global Macro Strategist")

# --- 2. Sidebar Controls ---
st.sidebar.header("🕹️ Control Center")

# --- NEW: AUTO REFRESH SETTINGS ---
st.sidebar.subheader("🔄 Live Refresh Settings")
auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh", value=False)
if auto_refresh:
    refresh_interval = st.sidebar.selectbox(
        "Refresh Interval",
        options=[10, 30, 60, 120, 300, 600],
        format_func=lambda x: f"{x} Seconds" if x < 60 else f"{x//60} Minutes",
        index=2  # Default to 60 seconds
    )
    # Trigger the refresh component (interval is in milliseconds)
    st_autorefresh(interval=refresh_interval * 1000, key="market_refresh")

st.sidebar.markdown("---")
exchange = st.sidebar.radio("Market Selection", ["NSE (India)", "BSE (India)", "US Markets"])
search_query = st.sidebar.text_input("🔍 Ticker Symbol", "RELIANCE")
interval = st.sidebar.selectbox("⏱️ Timeframe", ["1m", "5m", "15m", "30m", "1h", "1d"], index=2)

period_map = {"1m": "5d", "5m": "5d", "15m": "5d", "30m": "5d", "1h": "1mo", "1d": "6mo"}
period = period_map[interval]

st.sidebar.markdown("---")
apply_duty = st.sidebar.checkbox("Apply Custom Premium/Duty", value=False)
duty_percentage = st.sidebar.number_input("Duty %", value=6.0, step=0.1) if apply_duty else 0

# --- 3. Dynamic Ticker & Currency Engine ---
raw_ticker = search_query.upper().strip()
if exchange == "NSE (India)":
    ticker_input = f"{raw_ticker}.NS" if not raw_ticker.endswith(".NS") else raw_ticker
    currency = "₹"
elif exchange == "BSE (India)":
    ticker_input = f"{raw_ticker}.BO" if not raw_ticker.endswith(".BO") else raw_ticker
    currency = "₹"
else:
    ticker_input = raw_ticker
    currency = "$"

# --- 4. Global Macro Data Fetcher ---
@st.cache_data(ttl=60)
def fetch_global_cues():
    indices = {
        "Nifty 50": "^NSEI", 
        "Gold COMEX": "GC=F", 
        "Silver COMEX": "SI=F", 
        "Brent Crude": "BZ=F", 
        "Dollar Index": "DX-Y.NYB"
    }
    results = {}
    for name, sym in indices.items():
        try:
            h = yf.Ticker(sym).history(period="5d")
            if not h.empty:
                c, p = h['Close'].iloc[-1], h['Close'].iloc[-2]
                results[name] = {"price": c, "change": ((c - p) / p) * 100 if p != 0 else 0}
            else:
                results[name] = {"price": 0.0, "change": 0.0}
        except: results[name] = {"price": 0.0, "change": 0.0}
    return results

# --- 5. Stock Data Engine ---
@st.cache_data(ttl=15) # Reduced TTL for faster live updates
def load_stock_data(ticker, period, interval):
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    daily = yf.download(ticker, period="10d", interval="1d", progress=False)
    for d in [df, daily]:
        if not d.empty:
            if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
            d.reset_index(inplace=True)
            if 'Datetime' in d.columns: d.rename(columns={'Datetime': 'Date'}, inplace=True)
            if 'Date' in d.columns: d['Date'] = pd.to_datetime(d['Date']).dt.tz_localize(None)
    return df, daily

# --- 6. Main UI Logic ---
tab1, tab2 = st.tabs(["🌍 Global Market Pulse", "📈 Decisive Stock Analyzer"])

with tab1:
    st.subheader("Live Global Macro Cues")
    cues = fetch_global_cues()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Nifty 50", f"{cues['Nifty 50']['price']:.0f}", f"{cues['Nifty 50']['change']:.2f}%")
    c2.metric("Gold COMEX", f"${cues['Gold COMEX']['price']:.1f}", f"{cues['Gold COMEX']['change']:.2f}%")
    c3.metric("Silver COMEX", f"${cues['Silver COMEX']['price']:.1f}", f"{cues['Silver COMEX']['change']:.2f}%")
    c4.metric("Brent Crude", f"${cues['Brent Crude']['price']:.2f}", f"{cues['Brent Crude']['change']:.2f}%", delta_color="inverse")
    c5.metric("Dollar Index", f"{cues['Dollar Index']['price']:.2f}", f"{cues['Dollar Index']['change']:.2f}%", delta_color="inverse")

with tab2:
    with st.spinner("Crunching Live Data..."):
        df, daily_df = load_stock_data(ticker_input, period, interval)
        news_data = yf.Ticker(ticker_input).news

    if df.empty or len(daily_df) < 2:
        st.error("Data error. Check Ticker/Exchange.")
    else:
        # Indicators
        df['Date_Only'] = df['Date'].dt.date
        df['Typical'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['VWAP'] = df.groupby('Date_Only', group_keys=False).apply(lambda x: (x['Typical'] * x['Volume']).cumsum() / x['Volume'].cumsum())
        df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()

        # Pivot Targets
        yest = daily_df.iloc[-2]
        P = (yest['High'] + yest['Low'] + yest['Close']) / 3
        R1, S1 = (2 * P) - yest['Low'], (2 * P) - yest['High']
        R2, S2 = P + (yest['High'] - yest['Low']), P - (yest['High'] - yest['Low'])
        R3, S3 = R1 + (yest['High'] - yest['Low']), S1 - (yest['High'] - yest['Low'])
        R4, S4 = R2 + (yest['High'] - yest['Low']), S2 - (yest['High'] - yest['Low'])
        R5, S5 = R3 + (yest['High'] - yest['Low']), S3 - (yest['High'] - yest['Low'])

        levels = [S5, S4, S3, S2, S1, P, R1, R2, R3, R4, R5]
        if apply_duty: levels = [lvl * (1 + (duty_percentage / 100)) for lvl in levels]
        S5, S4, S3, S2, S1, P, R1, R2, R3, R4, R5 = levels

        cur, vwap = float(df['Close'].iloc[-1]), float(df['VWAP'].iloc[-1])
        is_bullish = cur > vwap and df['EMA9'].iloc[-1] > df['EMA21'].iloc[-1]
        is_bearish = cur < vwap and df['EMA9'].iloc[-1] < df['EMA21'].iloc[-1]

        # Dashboard
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Price", f"{currency}{cur:.2f}")
        c2.metric("VWAP", f"{currency}{vwap:.2f}")
        c3.metric("9 EMA", f"{currency}{df['EMA9'].iloc[-1]:.2f}")
        c4.metric("21 EMA", f"{currency}{df['EMA21'].iloc[-1]:.2f}")

        st.markdown("---")
        left, right = st.columns([1.6, 1])
        with left:
            st.subheader("📖 Execution Strategy")
            if is_bullish:
                st.success("### Trend: UP. Buy Dips.")
                st.write(f"1. **Buy Half:** {currency}{cur:.2f} | 2. **Avg Down:** {currency}{S1:.2f} | 3. **Exit:** {currency}{R1:.2f}")
            elif is_bearish:
                st.error("### Trend: DOWN. Short Rallies.")
                st.write(f"1. **Short Half:** {currency}{cur:.2f} | 2. **Avg Up:** {currency}{R1:.2f} | 3. **Exit:** {currency}{S1:.2f}")
            else:
                st.warning("### Trend: SIDEWAYS. Play Range.")
            
            st.markdown("---")
            st.subheader("🎲 Options Hedge")
            sb = 50 if cur > 1000 else 10
            atm = int(sb * round(cur/sb))
            if is_bullish: st.info(f"**Bull Spread:** Buy {atm} CE | Sell {atm+sb} CE")
            elif is_bearish: st.info(f"**Bear Spread:** Buy {atm} PE | Sell {atm-sb} PE")

        with right:
            st.subheader("🎯 10 Targets")
            targets = {"R5": R5, "R4": R4, "R3": R3, "R2": R2, "R1": R1, "Pivot": P, "S1": S1, "S2": S2, "S3": S3, "S4": S4, "S5": S5}
            for k, v in targets.items():
                clr = "#00FF00" if "R" in k else "#FF4136" if "S" in k else "#FFFFFF"
                st.markdown(f"<p style='color:{clr}; font-size:18px;'><b>{k}:</b> {currency}{v:.2f}</p>", unsafe_allow_html=True)

        st.markdown("---")
        st.subheader(f"Live Chart ({interval})")
        chart_df = df.tail(150)
        fig = go.Figure(data=[go.Candlestick(x=chart_df['Date'], open=chart_df['Open'], high=chart_df['High'], low=chart_df['Low'], close=chart_df['Close'], name='Price')])
        fig.add_trace(go.Scatter(x=chart_df['Date'], y=chart_df['VWAP'], line=dict(color='purple', width=2), name='VWAP'))
        fig.update_layout(xaxis_rangeslider_visible=False, height=550, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)