import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Market Analyzer V16: Global Edition", layout="wide")
st.title("⚡ Market Analyzer Pro: Global Strategist")

# --- Sidebar Controls ---
st.sidebar.header("Market Controls")
exchange = st.sidebar.radio("Market Exchange", ["NSE (India)", "BSE (India)", "US Markets"])
search_query = st.sidebar.text_input("🔍 Search Ticker (e.g., RELIANCE, AAPL, SPY)", "AAPL" if exchange == "US Markets" else "RELIANCE")
interval = st.sidebar.selectbox("⏱️ Select Timeframe", ["1m", "5m", "15m", "30m", "1h", "1d"], index=2)

period_map = {"1m": "5d", "5m": "5d", "15m": "5d", "30m": "5d", "1h": "1mo", "1d": "6mo"}
period = period_map[interval]

st.sidebar.markdown("---")
apply_duty = st.sidebar.checkbox("Apply Custom Premium/Duty", value=False)
duty_percentage = st.sidebar.number_input("Duty %", value=6.0, step=0.1) if apply_duty else 0

# Exchange Logic & Currency
if exchange == "NSE (India)":
    raw_ticker = search_query.upper().strip() if search_query else "RELIANCE"
    ticker_input = f"{raw_ticker}.NS" if not raw_ticker.endswith(".NS") else raw_ticker
    currency = "₹"
elif exchange == "BSE (India)":
    raw_ticker = search_query.upper().strip() if search_query else "RELIANCE"
    ticker_input = f"{raw_ticker}.BO" if not raw_ticker.endswith(".BO") else raw_ticker
    currency = "₹"
else:
    ticker_input = search_query.upper().strip() if search_query else "AAPL"
    currency = "$"

# --- Data Fetching ---
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

@st.cache_data(ttl=300) 
def load_news(ticker):
    try:
        return yf.Ticker(ticker).news
    except:
        return []

with st.spinner(f"Compiling Global Strategy for {ticker_input}..."):
    df, daily_df = load_market_data(ticker_input, period, interval)
    news_data = load_news(ticker_input)

if df.empty or daily_df.empty or len(daily_df) < 2:
    st.error("Data fetch failed. Ensure the market is open and the ticker is valid.")
else:
    # --- 1. Indicators & Pivots ---
    if interval != "1d":
        df['Date_Only'] = df['Date'].dt.date
        df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['VP'] = df['Typical_Price'] * df['Volume']
        df['VWAP'] = df.groupby('Date_Only').apply(lambda x: (x['Typical_Price'] * x['Volume']).cumsum() / x['Volume'].cumsum()).reset_index(level=0, drop=True)
    else:
        df['VWAP'] = df['Close'].rolling(window=20).mean()

    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()

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

    levels = [S5, S4, S3, S2, S1, P, R1, R2, R3, R4, R5]
    if apply_duty:
        levels = [lvl * (1 + (duty_percentage / 100)) for lvl in levels]
    S5, S4, S3, S2, S1, P, R1, R2, R3, R4, R5 = levels

    current_price = float(df['Close'].iloc[-1])
    current_vwap = float(df['VWAP'].iloc[-1])
    ema_9 = float(df['EMA_9'].iloc[-1])
    ema_21 = float(df['EMA_21'].iloc[-1])

    if apply_duty:
        current_vwap *= (1 + (duty_percentage / 100))
        ema_9 *= (1 + (duty_percentage / 100))
        ema_21 *= (1 + (duty_percentage / 100))

    above_levels = [lvl for lvl in levels if lvl > current_price]
    below_levels = [lvl for lvl in levels if lvl < current_price]
    
    next_res = above_levels[0] if above_levels else current_price * 1.02 
    next_sup = below_levels[-1] if below_levels else current_price * 0.98 
    deep_res = above_levels[1] if len(above_levels) > 1 else next_res * 1.02
    deep_sup = below_levels[-2] if len(below_levels) > 1 else next_sup * 0.98

    is_bullish = current_price > current_vwap and ema_9 > ema_21
    is_bearish = current_price < current_vwap and ema_9 < ema_21
    is_sideways = not is_bullish and not is_bearish

    # --- Global Options Strike Rounding ---
    def nearest_strike(price, base=10):
        return int(base * round(float(price)/base))
    
    if exchange == "US Markets":
        strike_base = 5 if current_price > 100 else 1
    else:
        strike_base = 50 if current_price > 1000 else 10
        
    atm_strike = nearest_strike(current_price, strike_base)
    raw_call_strike = nearest_strike(next_res, strike_base)
    raw_put_strike = nearest_strike(next_sup, strike_base)

    otm_call_strike = raw_call_strike if raw_call_strike > atm_strike else atm_strike + strike_base
    otm_put_strike = raw_put_strike if raw_put_strike < atm_strike else atm_strike - strike_base

    # --- UI Dashboard ---
    st.header(f"Strategy Dashboard: {ticker_input}")
    
    col_p, col_v, col_e1, col_e2 = st.columns(4)
    col_p.metric("Current Price", f"{currency}{current_price:.2f}")
    col_v.metric("VWAP (Fair Value)", f"{currency}{current_vwap:.2f}")
    col_e1.metric("9 EMA (Fast Trend)", f"{currency}{ema_9:.2f}")
    col_e2.metric("21 EMA (Slow Trend)", f"{currency}{ema_21:.2f}")

    st.markdown("---")
    
    left_col, right_col = st.columns([1.5, 1])

    with left_col:
        st.subheader("🎲 Options & Hedging Execution")
        
        if is_bullish:
            st.markdown(f"**<span style='color: #00FF00;'>BULLISH PLAY</span>**", unsafe_allow_html=True)
            st.success(f"**🔥 Aggressive (Naked Call):** Buy the **{currency}{atm_strike} Call**.")
            st.info(f"**🛡️ Hedged (Bull Call Spread):** Buy the **{currency}{atm_strike} Call** AND Sell the **{currency}{otm_call_strike} Call**.")
        elif is_bearish:
            st.markdown(f"**<span style='color: #FF4136;'>BEARISH PLAY</span>**", unsafe_allow_html=True)
            st.error(f"**🔥 Aggressive (Naked Put):** Buy the **{currency}{atm_strike} Put**.")
            st.info(f"**🛡️ Hedged (Bear Put Spread):** Buy the **{currency}{atm_strike} Put** AND Sell the **{currency}{otm_put_strike} Put**.")
        else:
            st.markdown(f"**<span style='color: #FFDC00;'>SIDEWAYS RANGE PLAY</span>**", unsafe_allow_html=True)
            st.warning(f"**🛑 High Theta Decay:** DO NOT buy naked Calls or Puts.")
            st.info(f"**🛡️ Hedged (Credit Spread):** Sell the **{currency}{otm_call_strike} Call** and Sell the **{currency}{otm_put_strike} Put** to collect premium.")

        st.markdown("---")

        st.subheader("📖 How to Trade This Right Now (Equity)")
        
        if is_bullish:
            st.markdown(f"### The Trend is **UP**. You should be looking to **BUY**.")
            st.success(f"**Step 1 (First Entry):** Buy half of your position near the current price ({currency}{current_price:.2f}) or on a dip to the 9 EMA ({currency}{ema_9:.2f}).")
            st.success(f"**Step 2 (Average Down Safely):** Only buy the second half if it drops to strong support at **{currency}{next_sup:.2f}**.")
            st.success(f"**Step 3 (Take Profit):** Start selling when the price reaches **{currency}{next_res:.2f}**. Hold a runner for **{currency}{deep_res:.2f}**.")
            st.error(f"**Step 4 (Bail Out):** If it collapses below **{currency}{deep_sup:.2f}**, cut your losses and exit.")
            
        elif is_bearish:
            st.markdown(f"### The Trend is **DOWN**. You should be looking to **SHORT SELL**.")
            st.error(f"**Step 1 (First Entry):** Short sell half of your position near the current price ({currency}{current_price:.2f}).")
            st.error(f"**Step 2 (Average Up Safely):** Short the second half if it rallies to strong resistance at **{currency}{next_res:.2f}**.")
            st.error(f"**Step 3 (Take Profit):** Buy back to cover when the price drops to **{currency}{next_sup:.2f}**.")
            st.success(f"**Step 4 (Bail Out):** If the price surges above **{currency}{deep_res:.2f}**, cut your losses and exit.")
            
        else:
            st.markdown(f"### The Trend is **SIDEWAYS**. You should **PLAY THE RANGE**.")
            st.warning(f"**The Buy Plan:** Wait for the price to drop to the floor at **{currency}{next_sup:.2f}**. Buy there. Sell when it bounces back to VWAP ({currency}{current_vwap:.2f}).")
            st.warning(f"**The Short Plan:** Wait for the price to rise to the ceiling at **{currency}{next_res:.2f}**. Short sell there. Cover when it drops back to VWAP ({currency}{current_vwap:.2f}).")

    with right_col:
        st.subheader("🗺️ The Master Map")
        st.write(f"**R5:** {currency}{R5:.2f} | **R4:** {currency}{R4:.2f} | **R3:** {currency}{R3:.2f}")
        st.write(f"**R2:** {currency}{R2:.2f} *(Major Ceiling)*")
        st.write(f"**R1:** {currency}{R1:.2f} *(Immediate Ceiling)*")
        st.markdown(f"<div style='background-color:#333; padding:5px; border-radius:5px; margin: 10px 0;'><b>Central Pivot (P): {currency}{P:.2f}</b></div>", unsafe_allow_html=True)
        st.write(f"**S1:** {currency}{S1:.2f} *(Immediate Floor)*")
        st.write(f"**S2:** {currency}{S2:.2f} *(Major Floor)*")
        st.write(f"**S3:** {currency}{S3:.2f} | **S4:** {currency}{S4:.2f} | **S5:** {currency}{S5:.2f}")
        
        st.markdown("---")
        
        st.subheader("📰 Sentiment Engine")
        if news_data:
            for article in news_data[:3]: 
                title = article.get('title', 'No Title')
                link = article.get('link', '#')
                st.markdown(f"- [{title}]({link})")
        else:
            st.write("No news catalysts detected.")

    # --- Interactive Chart ---
    
    st.markdown("---")
    st.subheader(f"Live Chart Verification ({interval})")
    
    chart_df = df.tail(150)
    fig = go.Figure()
    
    fig.add_trace(go.Candlestick(x=chart_df['Date'], open=chart_df['Open'], high=chart_df['High'], low=chart_df['Low'], close=chart_df['Close'], name='Price'))
    fig.add_trace(go.Scatter(x=chart_df['Date'], y=chart_df['EMA_9'], line=dict(color='#00FFFF', width=1.5), name='9 EMA'))
    fig.add_trace(go.Scatter(x=chart_df['Date'], y=chart_df['EMA_21'], line=dict(color='#FF851B', width=1.5), name='21 EMA'))
    fig.add_trace(go.Scatter(x=chart_df['Date'], y=chart_df['VWAP'], line=dict(color='purple', width=2), name='VWAP'))
    
    fig.add_hline(y=next_res, line_dash="solid", line_color="green", annotation_text=f"Res: {currency}{next_res:.2f}")
    fig.add_hline(y=next_sup, line_dash="solid", line_color="red", annotation_text=f"Sup: {currency}{next_sup:.2f}")

    fig.update_layout(xaxis_rangeslider_visible=False, height=500, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)