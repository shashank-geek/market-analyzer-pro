import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. Page Configuration ---
st.set_page_config(page_title="Market Analyzer V21: Global Command", layout="wide")

# CSS Fix for 6 columns: Shrinks font slightly so metrics don't disappear
st.markdown("""
<style> 
    .main { background-color: #0e1117; } 
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 10px; border: 1px solid #30363d; }
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
    .vsa-box { padding: 15px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #30363d; background-color: #1c2128; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Market Analyzer Pro: Global Command Center")

# --- 2. Sidebar Controls ---
st.sidebar.header("🕹️ Control Center")
auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh", value=False)
if auto_refresh:
    refresh_interval = st.sidebar.selectbox("Interval", [10, 30, 60, 300], index=2)
    st_autorefresh(interval=refresh_interval * 1000, key="market_refresh")

st.sidebar.markdown("---")
exchange = st.sidebar.radio("Market Selection", ["NSE (India)", "BSE (India)", "US Markets"])
search_query = st.sidebar.text_input("🔍 Ticker Symbol", "RELIANCE")
interval = st.sidebar.selectbox("⏱️ Timeframe", ["1m", "5m", "15m", "30m", "1h", "1d"], index=2)

period_map = {"1m": "5d", "5m": "5d", "15m": "5d", "30m": "5d", "1h": "1mo", "1d": "6mo"}
period = period_map[interval]

apply_duty = st.sidebar.checkbox("Apply Custom Premium (e.g. 6%)", value=False)
duty_percentage = st.sidebar.number_input("Duty %", value=6.0, step=0.1) if apply_duty else 0

# --- 3. Dynamic Ticker Engine ---
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

# --- 4. Global Macro Data Fetcher (Corrected Tickers) ---
@st.cache_data(ttl=60)
def fetch_global_cues():
    indices = {
        "Nifty 50": "^NSEI",
        "Sensex": "^BSESN",
        "India Vix": "^INDIAVIX",
        "Gift Nifty": "NIFTY1!", 
        "Dow Jones": "^DJI",
        "S&P 500": "^GSPC",
        "Nasdaq": "^IXIC",
        "Gold MCX": "GOLD1!.NS",   
        "Silver MCX": "SILVER1!.NS", 
        "Gold COMEX": "GC=F",
        "Silver COMEX": "SI=F",
        "Brent Crude": "BZ=F",
        "Nymex Crude": "CL=F",
        "USD-INR": "INR=X",
        "Dollar Index": "DX-Y.NYB"
    }
    results = {}
    for name, sym in indices.items():
        try:
            h = yf.Ticker(sym).history(period="5d")
            if not h.empty:
                c, p = h['Close'].iloc[-1], h['Close'].iloc[-2]
                if name == "Gold MCX" and c < 20000: c *= 10  
                if name == "Silver MCX" and c < 10000: c *= 1000 
                results[name] = {"price": c, "change": ((c - p) / p) * 100 if p != 0 else 0}
            else: results[name] = {"price": 0.0, "change": 0.0}
        except: results[name] = {"price": 0.0, "change": 0.0}
    return results

# --- 5. Stock Data Engine ---
@st.cache_data(ttl=15)
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
    cues = fetch_global_cues()
    st.subheader("🏛️ Indian & Global Indices")
    r1 = st.columns(5)
    r1[0].metric("Nifty 50", f"{cues['Nifty 50']['price']:.0f}", f"{cues['Nifty 50']['change']:.2f}%")
    r1[1].metric("Sensex", f"{cues['Sensex']['price']:.0f}", f"{cues['Sensex']['change']:.2f}%")
    r1[2].metric("Gift Nifty", f"{cues['Gift Nifty']['price']:.0f}", f"{cues['Gift Nifty']['change']:.2f}%")
    r1[3].metric("India Vix", f"{cues['India Vix']['price']:.2f}", f"{cues['India Vix']['change']:.2f}%", delta_color="inverse")
    r1[4].metric("USD-INR", f"₹{cues['USD-INR']['price']:.2f}", f"{cues['USD-INR']['change']:.2f}%", delta_color="inverse")

    st.subheader("🔥 Commodities (MCX & Global)")
    r2 = st.columns(5)
    r2[0].metric("Gold MCX", f"₹{cues['Gold MCX']['price']:.0f}", f"{cues['Gold MCX']['change']:.2f}%")
    r2[1].metric("Silver MCX", f"₹{cues['Silver MCX']['price']:.0f}", f"{cues['Silver MCX']['change']:.2f}%")
    r2[2].metric("Gold COMEX", f"${cues['Gold COMEX']['price']:.1f}", f"{cues['Gold COMEX']['change']:.2f}%")
    r2[3].metric("Silver COMEX", f"${cues['Silver COMEX']['price']:.2f}", f"{cues['Silver COMEX']['change']:.2f}%")
    r2[4].metric("Brent Crude", f"${cues['Brent Crude']['price']:.2f}", f"{cues['Brent Crude']['change']:.2f}%", delta_color="inverse")

    st.subheader("🇺🇸 US Markets")
    r3 = st.columns(4)
    r3[0].metric("Dow Jones", f"{cues['Dow Jones']['price']:.0f}", f"{cues['Dow Jones']['change']:.2f}%")
    r3[1].metric("S&P 500", f"{cues['S&P 500']['price']:.0f}", f"{cues['S&P 500']['change']:.2f}%")
    r3[2].metric("Nasdaq", f"{cues['Nasdaq']['price']:.0f}", f"{cues['Nasdaq']['change']:.2f}%")
    r3[3].metric("Dollar Index", f"{cues['Dollar Index']['price']:.2f}", f"{cues['Dollar Index']['change']:.2f}%", delta_color="inverse")

with tab2:
    with st.spinner("Crunching Stock Math..."):
        df, daily_df = load_stock_data(ticker_input, period, interval)
        news_data = yf.Ticker(ticker_input).news

    if df.empty or len(daily_df) < 2:
        st.error("Data error. Check Ticker/Exchange.")
    else:
        # Technicals
        df['Date_Only'] = df['Date'].dt.date
        df['Typical'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['VWAP'] = df.groupby('Date_Only', group_keys=False).apply(lambda x: (x['Typical'] * x['Volume']).cumsum() / x['Volume'].cumsum())
        df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # VSA Logic
        df['Vol_Avg'] = df['Volume'].rolling(window=10).mean()
        last_vol, avg_vol = df['Volume'].iloc[-1], df['Vol_Avg'].iloc[-1]
        price_change = df['Close'].iloc[-1] - df['Close'].iloc[-2]
        
        if price_change > 0 and last_vol > avg_vol:
            v_title, v_action, v_color = "ACCUMULATION", "Price UP + Volume UP", "#00FF00"
            v_meaning = "Smart money is buying aggressively. High conviction move."
        elif price_change > 0 and last_vol < avg_vol:
            v_title, v_action, v_color = "WEAK RALLY (Bull Trap)", "Price UP + Volume DOWN", "#FFDC00"
            v_meaning = "Price is rising on low volume. Big players are NOT buying. Move might fail."
        elif price_change < 0 and last_vol > avg_vol:
            v_title, v_action, v_color = "DISTRIBUTION", "Price DOWN + Volume UP", "#FF4136"
            v_meaning = "Institutions are dumping shares. A downward trend may be starting."
        elif price_change < 0 and last_vol < avg_vol:
            v_title, v_action, v_color = "WEAK SELL-OFF (Shake-out)", "Price DOWN + Volume DOWN", "#FF851B"
            v_meaning = "Price dropping on low volume. Likely a temporary dip to scare retail."
        else:
            v_title, v_action, v_color = "NEUTRAL", "Stable Price/Volume", "#FFFFFF"
            v_meaning = "No clear trend. Market is undecided."

        # Pivot Targets Logic
        yest = daily_df.iloc[-2]
        y_H, y_L, y_C = float(yest['High']), float(yest['Low']), float(yest['Close'])
        P = (y_H + y_L + y_C) / 3
        R1, S1 = (2 * P) - y_L, (2 * P) - y_H
        R2, S2 = P + (y_H - y_L), P - (y_H - y_L)
        R3, S3 = R1 + (y_H - y_L), S1 - (y_H - y_L)
        R4, S4 = R2 + (y_H - y_L), S2 - (y_H - y_L)
        R5, S5 = R3 + (y_H - y_L), S3 - (y_H - y_L)

        levels = [S5, S4, S3, S2, S1, P, R1, R2, R3, R4, R5]
        if apply_duty: levels = [lvl * (1 + (duty_percentage / 100)) for lvl in levels]
        S5, S4, S3, S2, S1, P, R1, R2, R3, R4, R5 = levels

        cur, vwap, rsi_val = float(df['Close'].iloc[-1]), float(df['VWAP'].iloc[-1]), df['RSI'].iloc[-1]

        # Metrics Row
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Price", f"{currency}{cur:.2f}")
        m2.metric("VWAP", f"{currency}{vwap:.2f}")
        m3.metric("9 EMA", f"{currency}{df['EMA9'].iloc[-1]:.2f}")
        m4.metric("21 EMA", f"{currency}{df['EMA21'].iloc[-1]:.2f}")
        m5.metric("RSI (14)", f"{rsi_val:.2f}")
        m6.metric("Vol Ratio", f"{(last_vol/avg_vol):.2f}x")

        # VSA Translator Box
        st.markdown(f"""<div class="vsa-box" style="border-left: 10px solid {v_color};">
                <h3 style="color: {v_color}; margin-top:0;">🔍 Phase: {v_title}</h3>
                <p style="font-size: 15px; margin-bottom: 5px;"><b>Technicals:</b> {v_action}</p>
                <p style="font-size: 16px;"><b>Meaning:</b> {v_meaning}</p>
            </div>""", unsafe_allow_html=True)
        
        st.markdown("---")
        left, right = st.columns([1.6, 1])
        with left:
            st.subheader("📖 Execution Strategy")
            if cur > vwap:
                # SYNCED TARGETS: Target is now the NEXT resistance level
                target_level = R1 if cur < R1 else (R2 if cur < R2 else R3)
                st.success(f"**Trend: UP.** Buy Half near {currency}{cur:.2f} or EMA 9.")
                st.write(f"1. **Average Down:** At Support **{currency}{S1:.2f}**.")
                st.write(f"2. **Target:** Exit at Resistance **{currency}{target_level:.2f}**.")
            else:
                # SYNCED TARGETS: Target is now the NEXT support level
                target_level = S1 if cur > S1 else (S2 if cur > S2 else S3)
                st.error(f"**Trend: DOWN.** Short Half near {currency}{cur:.2f}.")
                st.write(f"1. **Average Up:** At Resistance **{currency}{R1:.2f}**.")
                st.write(f"2. **Target:** Cover at Support **{currency}{target_level:.2f}**.")
            
            st.markdown("---")
            st.subheader("🎲 Options Hedge")
            sb = 50 if cur > 1000 else 10
            atm = int(sb * round(cur/sb))
            st.info(f"**{'Bull' if cur > vwap else 'Bear'} Spread:** {atm} {'CE' if cur > vwap else 'PE'}")

            st.markdown("---")
            st.subheader("📰 Latest News")
            for n in news_data[:3]: st.markdown(f"- [{n.get('title')}]({n.get('link')})")

        with right:
            st.subheader("🎯 10 Targets")
            targets = {"R5": R5, "R4": R4, "R3": R3, "R2": R2, "R1": R1, "Pivot": P, "S1": S1, "S2": S2, "S3": S3, "S4": S4, "S5": S5}
            for k, v in targets.items():
                clr = "#00FF00" if "R" in k else "#FF4136" if "S" in k else "#FFFFFF"
                st.markdown(f"<p style='color:{clr}; font-size:18px;'><b>{k}:</b> {currency}{v:.2f}</p>", unsafe_allow_html=True)

        st.markdown("---")
        chart_df = df.tail(150)
        fig = go.Figure(data=[go.Candlestick(x=chart_df['Date'], open=chart_df['Open'], high=chart_df['High'], low=chart_df['Low'], close=chart_df['Close'], name='Price')])
        fig.add_trace(go.Scatter(x=chart_df['Date'], y=chart_df['VWAP'], line=dict(color='purple', width=2), name='VWAP'))
        fig.add_trace(go.Scatter(x=chart_df['Date'], y=chart_df['EMA9'], line=dict(color='#00FFFF', width=1), name='9 EMA'))
        fig.add_trace(go.Scatter(x=chart_df['Date'], y=chart_df['EMA21'], line=dict(color='#FF851B', width=1), name='21 EMA'))
        fig.update_layout(xaxis_rangeslider_visible=False, height=550, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)