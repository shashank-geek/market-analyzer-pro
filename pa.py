import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Market Analyzer V8: Dynamic Trend", layout="wide")
st.title("⚡ Market Analyzer Pro: Dynamic Trend Engine")

# --- Sidebar Controls ---
st.sidebar.header("Market Controls")
exchange = st.sidebar.radio("Market Exchange", ["NSE (India)", "BSE (India)"])
search_query = st.sidebar.text_input("🔍 Search Ticker (e.g., BSE, GOLDBEES)", "BSE")

# Dynamic Timeframe Selection
interval = st.sidebar.selectbox("⏱️ Select Timeframe", ["1m", "5m", "15m", "30m", "1h", "1d"], index=1)

# Mapping intervals to valid yfinance periods
period_map = {"1m": "5d", "5m": "5d", "15m": "5d", "30m": "5d", "1h": "1mo", "1d": "6mo"}
period = period_map[interval]

st.sidebar.markdown("---")
apply_duty = st.sidebar.checkbox("Apply Custom Premium/Duty (e.g., 6% for Gold/Silver)", value=False)
duty_percentage = st.sidebar.number_input("Duty %", value=6.0, step=0.1) if apply_duty else 0

raw_ticker = search_query.upper().strip() if search_query else "BSE"
if exchange == "NSE (India)" and not raw_ticker.endswith(".NS"):
    ticker_input = f"{raw_ticker}.NS"
elif exchange == "BSE (India)" and not raw_ticker.endswith(".BO"):
    ticker_input = f"{raw_ticker}.BO"
else:
    ticker_input = raw_ticker

# --- Data Fetching ---
@st.cache_data(ttl=30) # 30-second cache for near real-time updates
def load_data(ticker, period, interval):
    # Fetch dynamic intraday data
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    # Fetch daily data strictly for absolute pivot targets
    daily = yf.download(ticker, period="5d", interval="1d", progress=False)
    
    for data in [df, daily]:
        if not data.empty:
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            data.reset_index(inplace=True)
            if 'Datetime' in data.columns:
                data.rename(columns={'Datetime': 'Date'}, inplace=True)
                data['Date'] = pd.to_datetime(data['Date']).dt.tz_localize(None)
    return df, daily

with st.spinner(f"Analyzing Live Price Action on {interval} timeframe..."):
    df, daily_df = load_data(ticker_input, period, interval)

if df.empty or daily_df.empty or len(daily_df) < 2:
    st.error("Data fetch failed. Ensure the market is open and the ticker is valid.")
else:
    # --- 1. Indicators: VWAP & EMAs ---
    # VWAP (resets daily for intraday charts)
    if interval != "1d":
        df['Date_Only'] = df['Date'].dt.date
        df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['VP'] = df['Typical_Price'] * df['Volume']
        df['VWAP'] = df.groupby('Date_Only')['VP'].cumsum() / df.groupby('Date_Only')['Volume'].cumsum()
    else:
        df['VWAP'] = df['Close'].rolling(window=20).mean() # Fallback for daily charts

    # 9 and 21 Exponential Moving Averages for fast trend detection
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()

    # --- 2. Calculate 5 Supports & 5 Resistances (Daily Pivots) ---
    yest = daily_df.iloc[-2]
    yest_H, yest_L, yest_C = float(yest['High']), float(yest['Low']), float(yest['Close'])
    
    P = (yest_H + yest_L + yest_C) / 3
    R1 = (2 * P) - yest_L
    S1 = (2 * P) - yest_H
    R2 = P + (yest_H - yest_L)
    S2 = P - (yest_H - yest_L)
    R3 = R1 + (yest_H - yest_L)
    S3 = S1 - (yest_H - yest_L)
    R4 = R2 + (yest_H - yest_L)
    S4 = S2 - (yest_H - yest_L)
    R5 = R3 + (yest_H - yest_L)
    S5 = S3 - (yest_H - yest_L)

    levels = [P, R1, S1, R2, S2, R3, S3, R4, S4, R5, S5]
    if apply_duty:
        levels = [lvl * (1 + (duty_percentage / 100)) for lvl in levels]
    P, R1, S1, R2, S2, R3, S3, R4, S4, R5, S5 = levels

    # --- 3. Live Price Action Engine ---
    current_price = float(df['Close'].iloc[-1])
    current_vwap = float(df['VWAP'].iloc[-1])
    ema_9 = float(df['EMA_9'].iloc[-1])
    ema_21 = float(df['EMA_21'].iloc[-1])

    if apply_duty:
        current_vwap *= (1 + (duty_percentage / 100))
        ema_9 *= (1 + (duty_percentage / 100))
        ema_21 *= (1 + (duty_percentage / 100))

    # Determine the Trend
    trend = "SIDEWAYS (CHOPPY) 🟡"
    trend_color = "#FFDC00"
    logic = "The 9 EMA and 21 EMA are tangled, and price is hugging the VWAP. Avoid trading until a clear breakout occurs."
    entry_zone = "No Trade Zone"

    # Bullish logic: Fast EMA > Slow EMA, and Price > VWAP
    if ema_9 > ema_21 and current_price > current_vwap:
        trend = "BULLISH UPTREND 🟢"
        trend_color = "#00FF00"
        logic = f"Price is above VWAP, and the fast 9 EMA has crossed above the 21 EMA. Buyers are in control on the {interval} timeframe."
        entry_zone = f"Buy on pullbacks toward the 9 EMA (₹{ema_9:.2f}) or VWAP (₹{current_vwap:.2f})."
    
    # Bearish logic: Fast EMA < Slow EMA, and Price < VWAP
    elif ema_9 < ema_21 and current_price < current_vwap:
        trend = "BEARISH DOWNTREND 🔴"
        trend_color = "#FF4136"
        logic = f"Price is below VWAP, and the fast 9 EMA has crossed below the 21 EMA. Sellers are dominating on the {interval} timeframe."
        entry_zone = f"Short on rallies toward the 9 EMA (₹{ema_9:.2f}) or VWAP (₹{current_vwap:.2f})."

    # --- UI Dashboard ---
    st.header(f"Live Market State: {trend}")
    st.markdown(f"**Selected Timeframe:** {interval} candles")
    
    st.info(f"**Current Price Action Logic:** {logic}")
    st.success(f"**Optimal Entry Zone:** {entry_zone}")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Price", f"₹{current_price:.2f}")
    col2.metric("9 EMA (Fast Trend)", f"₹{ema_9:.2f}")
    col3.metric("21 EMA (Slow Trend)", f"₹{ema_21:.2f}")
    col4.metric("VWAP (Fair Value)", f"₹{current_vwap:.2f}")

    # --- 10 Target Matrix ---
    st.markdown("---")
    st.subheader("🎯 Institutional Support & Resistance Targets")
    st.caption("These levels are calculated using Daily Floor Pivots and remain static for the trading session, regardless of your chosen timeframe.")
    
    col_r, col_c, col_s = st.columns([1, 1, 1])
    with col_r:
        st.markdown("<h4 style='color: #FF4136;'>5 Resistance Targets</h4>", unsafe_allow_html=True)
        st.write(f"**R5:** ₹{R5:.2f} *(Extreme Breakout)*")
        st.write(f"**R4:** ₹{R4:.2f}")
        st.write(f"**R3:** ₹{R3:.2f}")
        st.write(f"**R2:** ₹{R2:.2f}")
        st.write(f"**R1:** ₹{R1:.2f} *(First Target)*")
    
    with col_c:
        st.markdown("<h4>Central Level</h4>", unsafe_allow_html=True)
        st.write(f"**Central Pivot (P):** ₹{P:.2f}")
        
    with col_s:
        st.markdown("<h4 style='color: #00FF00;'>5 Support Targets</h4>", unsafe_allow_html=True)
        st.write(f"**S1:** ₹{S1:.2f} *(First Pullback)*")
        st.write(f"**S2:** ₹{S2:.2f}")
        st.write(f"**S3:** ₹{S3:.2f}")
        st.write(f"**S4:** ₹{S4:.2f}")
        st.write(f"**S5:** ₹{S5:.2f} *(Extreme Washout)*")

    # --- Interactive Chart ---
    
    st.markdown("---")
    st.subheader(f"Live Chart ({interval} timeframe)")
    
    # Trim dataframe for cleaner charting if too long
    chart_df = df.tail(150)
    
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=chart_df['Date'], open=chart_df['Open'], high=chart_df['High'], low=chart_df['Low'], close=chart_df['Close'], name='Price'))
    
    # EMAs and VWAP
    fig.add_trace(go.Scatter(x=chart_df['Date'], y=chart_df['EMA_9'], line=dict(color='#00FFFF', width=1.5), name='9 EMA'))
    fig.add_trace(go.Scatter(x=chart_df['Date'], y=chart_df['EMA_21'], line=dict(color='#FF851B', width=1.5), name='21 EMA'))
    fig.add_trace(go.Scatter(x=chart_df['Date'], y=chart_df['VWAP'], line=dict(color='purple', width=2), name='VWAP'))
    
    # Only plot the most immediate levels to avoid clutter
    fig.add_hline(y=R1, line_dash="dot", line_color="rgba(255, 65, 54, 0.5)", annotation_text="R1")
    fig.add_hline(y=S1, line_dash="dot", line_color="rgba(0, 255, 0, 0.5)", annotation_text="S1")

    fig.update_layout(xaxis_rangeslider_visible=False, height=600, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)