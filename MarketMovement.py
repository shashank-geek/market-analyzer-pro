import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Market Analyzer V17: Macro Playbook", layout="wide")
st.title("⚡ Market Analyzer Pro: Global Macro Strategist")

# --- 1. Global Macro Tracker (Optimized for Crude/DXY) ---
@st.cache_data(ttl=300)
def load_macro_cues():
    # ^NSEI (Nifty), BZ=F (Brent), DX-Y.NYB (Dollar Index)
    tickers = {"Nifty 50": "^NSEI", "Brent Crude": "BZ=F", "Dollar Index": "DX-Y.NYB"}
    macro_data = {}
    for name, ticker in tickers.items():
        try:
            hist = yf.Ticker(ticker).history(period="2d")
            if len(hist) >= 2:
                prev, curr = hist['Close'].iloc[-2], hist['Close'].iloc[-1]
                change = ((curr - prev) / prev) * 100
                macro_data[name] = {"price": curr, "change": change}
        except: macro_data[name] = {"price": 0.0, "change": 0.0}
    return macro_data

macro = load_macro_cues()
st.subheader("🌍 Global Market Pulse (Critical Cues)")
m1, m2, m3 = st.columns(3)
if macro:
    m1.metric("Nifty 50", f"₹{macro['Nifty 50']['price']:.0f}", f"{macro['Nifty 50']['change']:.2f}%")
    m2.metric("Brent Crude", f"${macro['Brent Crude']['price']:.2f}", f"{macro['Brent Crude']['change']:.2f}%", delta_color="inverse")
    m3.metric("Dollar Index", f"{macro['Dollar Index']['price']:.2f}", f"{macro['Dollar Index']['change']:.2f}%", delta_color="inverse")

# --- 2. Automated Market Warning ---
oil_price = macro.get('Brent Crude', {}).get('price', 0)
dxy_change = macro.get('Dollar Index', {}).get('change', 0)

if oil_price > 90 or dxy_change > 0.5:
    st.error(f"⚠️ **HIGH RISK ALERT:** Brent Crude at ${oil_price:.2f} and a strong Dollar are massive headwinds for Indian Equities. **Strictly avoid averaging down** if your stop loss hits.")

st.markdown("---")

# --- 3. Sidebar Controls ---
st.sidebar.header("Market Controls")
exchange = st.sidebar.radio("Market Exchange", ["NSE (India)", "BSE (India)", "US Markets"])
search_query = st.sidebar.text_input("🔍 Search Ticker", "RELIANCE")
interval = st.sidebar.selectbox("⏱️ Timeframe", ["1m", "5m", "15m", "30m", "1h", "1d"], index=2)

period_map = {"1m": "5d", "5m": "5d", "15m": "5d", "30m": "5d", "1h": "1mo", "1d": "6mo"}
period = period_map[interval]

apply_duty = st.sidebar.checkbox("Apply Custom Premium/Duty", value=False)
duty_percentage = st.sidebar.number_input("Duty %", value=6.0, step=0.1) if apply_duty else 0

if exchange == "NSE (India)":
    ticker_input = f"{search_query.upper().strip()}.NS" if not search_query.upper().endswith(".NS") else search_query.upper()
    currency = "₹"
elif exchange == "BSE (India)":
    ticker_input = f"{search_query.upper().strip()}.BO" if not search_query.upper().endswith(".BO") else search_query.upper()
    currency = "₹"
else:
    ticker_input = search_query.upper().strip()
    currency = "$"

# --- 4. Data Engine (V16 Core) ---
@st.cache_data(ttl=30) 
def load_market_data(ticker, period, interval):
    df = yf.download(ticker, period=period, interval=interval, progress=False)
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

df, daily_df = load_market_data(ticker_input, period, interval)

if df.empty or len(daily_df) < 2:
    st.error("Data fetch failed. Verify ticker or market hours.")
else:
    # --- Technical Calculations ---
    df['Date_Only'] = df['Date'].dt.date
    df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['VWAP'] = df.groupby('Date_Only').apply(lambda x: (x['Typical_Price'] * x['Volume']).cumsum() / x['Volume'].cumsum()).reset_index(level=0, drop=True)
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()

    # Pivots
    yest = daily_df.iloc[-2]
    P = (yest['High'] + yest['Low'] + yest['Close']) / 3
    R1, S1 = (2*P)-yest['Low'], (2*P)-yest['High']
    R2, S2 = P+(yest['High']-yest['Low']), P-(yest['High']-yest['Low'])

    current_price = float(df['Close'].iloc[-1])
    current_vwap = float(df['VWAP'].iloc[-1])
    is_bearish = current_price < current_vwap and df['EMA_9'].iloc[-1] < df['EMA_21'].iloc[-1]
    
    # --- UI Layout ---
    left, right = st.columns([1.5, 1])
    with left:
        st.subheader("🎲 Decisive Strategy")
        if is_bearish:
            st.error(f"📉 **TREND IS STRONGLY BEARISH:** Follow the 'Sell on Rise' strategy.")
            st.markdown(f"- **Short Entry:** Near {currency}{max(current_price, df['EMA_9'].iloc[-1]):.2f}")
            st.markdown(f"- **Cover Target:** {currency}{S1:.2f}")
            st.markdown(f"- **Stop Loss:** Close above VWAP ({currency}{current_vwap:.2f})")
        else:
            st.warning(f"🟡 **TREND IS NEUTRAL/VOLATILE:** With Oil > $100, avoid long positions unless price stays above {currency}{current_vwap:.2f}.")

    with right:
        st.subheader("🎯 Daily Pivot Targets")
        st.write(f"R2: {currency}{R2:.2f} | R1: {currency}{R1:.2f}")
        st.markdown(f"**Pivot (P): {currency}{P:.2f}**")
        st.write(f"S1: {currency}{S1:.2f} | S2: {currency}{S2:.2f}")

    # --- Chart ---
    chart_df = df.tail(150)
    fig = go.Figure(data=[go.Candlestick(x=chart_df['Date'], open=chart_df['Open'], high=chart_df['High'], low=chart_df['Low'], close=chart_df['Close'])])
    fig.add_trace(go.Scatter(x=chart_df['Date'], y=chart_df['VWAP'], line=dict(color='purple', width=2), name='VWAP'))
    fig.update_layout(xaxis_rangeslider_visible=False, height=500, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)