import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Market Analyzer Pro V3", layout="wide", initial_sidebar_state="expanded")
st.title("📈 Market Analyzer Pro: The Ultimate Dashboard")

# --- Sidebar: Navigation & Controls ---
st.sidebar.header("🛠️ Navigation & Controls")

# 1. Exchange Toggle (Fixes the BSE/NSE issue)
exchange = st.sidebar.radio("1. Select Market Exchange", ["NSE (India)", "BSE (India)", "US / Global"])

# 2. Always-Visible Search Bar
search_query = st.sidebar.text_input("2. 🔍 Search Stock Ticker (e.g., TATASTEEL)", "")

# 3. Watchlist Dropdown
default_watchlist = ['GOLDBEES', 'SILVERBEES', 'RELIANCE', 'TCS', 'INFY']
selected_watchlist = st.sidebar.selectbox("3. Or pick from Watchlist", ["-- Select --"] + default_watchlist)

# Logic to determine which ticker to load
raw_ticker = ""
if search_query:
    raw_ticker = search_query.upper().strip()
elif selected_watchlist != "-- Select --":
    raw_ticker = selected_watchlist
else:
    raw_ticker = "GOLDBEES" # Default starting asset

# Automatically apply the correct suffix based on the exchange toggle
if exchange == "NSE (India)" and not raw_ticker.endswith(".NS"):
    ticker_input = f"{raw_ticker}.NS"
elif exchange == "BSE (India)" and not raw_ticker.endswith(".BO"):
    ticker_input = f"{raw_ticker}.BO"
else:
    ticker_input = raw_ticker

timeframe = st.sidebar.selectbox("Select Chart Timeframe", ["3mo", "6mo", "1y", "2y", "5y"], index=2)

st.sidebar.markdown("---")
st.sidebar.subheader("Asset Adjustments")
apply_duty = st.sidebar.checkbox("Apply Custom Premium/Duty to Levels")
duty_percentage = st.sidebar.number_input("Duty % (e.g., 6 for import duty)", value=6.0, step=0.1) if apply_duty else 0

# --- Fetch Data ---
@st.cache_data(ttl=3600)
def load_data(ticker, period):
    data = yf.download(ticker, period=period, progress=False)
    if not data.empty:
        data.reset_index(inplace=True)
    return data

@st.cache_data(ttl=3600)
def get_info(ticker):
    return yf.Ticker(ticker).info

with st.spinner(f"Pulling data for {ticker_input}..."):
    df = load_data(ticker_input, timeframe)
    try:
        info = get_info(ticker_input)
    except:
        info = {}

if df.empty:
    st.error(f"Could not fetch data for {ticker_input}. Please verify the symbol exists on the selected exchange.")
else:
    # --- Core Calculations ---
    current_price = df['Close'].iloc[-1].item()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    current_rsi = df['RSI'].iloc[-1].item() if not pd.isna(df['RSI'].iloc[-1].item()) else 50
    sma_50 = df['SMA_50'].iloc[-1].item()
    sma_200 = df['SMA_200'].iloc[-1].item()

    recent_low = df['Low'].tail(30).min().item()
    recent_high = df['High'].tail(30).max().item()
    
    # Adjust for duties (like the 6% import duty on gold/silver)
    if apply_duty:
        recent_low *= (1 + (duty_percentage / 100))
        recent_high *= (1 + (duty_percentage / 100))

    # --- Recommendation Engine Logic ---
    score = 0
    reasons = []

    if not pd.isna(sma_50) and not pd.isna(sma_200):
        if sma_50 > sma_200:
            score += 1
            reasons.append("Bullish Trend: 50-day SMA is above 200-day SMA.")
        else:
            score -= 1
            reasons.append("Bearish Trend: 50-day SMA is below 200-day SMA.")

    if current_rsi < 30:
        score += 2
        reasons.append(f"Oversold: RSI is very low at {current_rsi:.1f}, indicating a potential bounce.")
    elif current_rsi > 70:
        score -= 2
        reasons.append(f"Overbought: RSI is very high at {current_rsi:.1f}, indicating a potential pullback.")
    else:
        reasons.append(f"Neutral Momentum: RSI is sitting comfortably at {current_rsi:.1f}.")

    # Determine Signal
    if score >= 2: signal, color = "STRONG BUY 🟢", "green"
    elif score == 1: signal, color = "BUY ↗️", "lightgreen"
    elif score == 0: signal, color = "HOLD ⏸️", "gray"
    elif score == -1: signal, color = "SELL ↘️", "orange"
    else: signal, color = "STRONG SELL 🔴", "red"

    # --- UI LAYOUT ---
    st.header(f"{info.get('shortName', raw_ticker)} ({ticker_input})")
    st.markdown(f"<h2 style='color: {color};'>{signal}</h2>", unsafe_allow_html=True)
    st.metric("Current Price", f"₹{current_price:.2f}" if "India" in exchange else f"${current_price:.2f}")

    # --- Tabs Implementation ---
    tab1, tab2, tab3 = st.tabs(["📊 Technical Analysis", "🏦 Fundamentals", "🤖 AI Summary"])

    with tab1:
        st.subheader("Interactive Price Chart")
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df['Date'], open=df['Open'].squeeze(), high=df['High'].squeeze(), low=df['Low'].squeeze(), close=df['Close'].squeeze(), name='Price'))
        fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_50'].squeeze(), line=dict(color='blue', width=1), name='50 SMA'))
        fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_200'].squeeze(), line=dict(color='orange', width=1), name='200 SMA'))
        fig.add_hline(y=recent_low, line_dash="dot", line_color="green", annotation_text=f"Support: {recent_low:.2f}")
        fig.add_hline(y=recent_high, line_dash="dot", line_color="red", annotation_text=f"Resistance: {recent_high:.2f}")
        fig.update_layout(xaxis_rangeslider_visible=False, height=500, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Fundamental Health Panel")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Market Cap", f"{info.get('marketCap', 'N/A'):,}")
            st.metric("Trailing P/E", info.get('trailingPE', 'N/A'))
        with col2:
            st.metric("Profit Margin", f"{info.get('profitMargins', 0) * 100:.2f}%" if info.get('profitMargins') else 'N/A')
            st.metric("Return on Equity (ROE)", f"{info.get('returnOnEquity', 0) * 100:.2f}%" if info.get('returnOnEquity') else 'N/A')
        with col3:
            st.metric("52 Week High", f"₹{info.get('fiftyTwoWeekHigh', 'N/A')}")
            st.metric("52 Week Low", f"₹{info.get('fiftyTwoWeekLow', 'N/A')}")

    with tab3:
        st.subheader("🤖 Automated Analysis Summary")
        st.write(f"Based on the algorithmic indicators, the current recommendation for **{ticker_input}** is **{signal}**.")
        for reason in reasons:
            st.write(f"- {reason}")