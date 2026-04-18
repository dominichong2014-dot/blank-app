import streamlit as st
import alpaca_trade_api as tradeapi
import anthropic
import time

# --- 1. SETUP & SECRETS ---
# This looks for keys in your Streamlit Settings > Secrets
try:
    ALPACA_KEY = st.secrets["ALPACA_KEY"]
    ALPACA_SECRET = st.secrets["ALPACA_SECRET"]
    CLAUDE_KEY = st.secrets["CLAUDE_KEY"]
except:
    st.error("⚠️ Secrets not found! Please add ALPACA_KEY, ALPACA_SECRET, and CLAUDE_KEY to your Streamlit App Settings.")
    st.stop()

# Initialize the "Market" and the "Brain"
alpaca = tradeapi.REST(ALPACA_KEY, ALPACA_SECRET, "https://paper-api.alpaca.markets", api_version='v2')
claude = anthropic.Anthropic(api_key=CLAUDE_KEY)

# --- 2. THE DASHBOARD UI ---
st.title("🤖 Claude AI Stock Trader")
st.markdown("Automated trading using AI analysis.")

# Sidebar for settings
ticker = st.sidebar.text_input("Stock Ticker", value="NVDA").upper()
trade_qty = st.sidebar.number_input("Shares per trade", min_value=1, value=1)
wait_time = st.sidebar.slider("Check every (minutes)", 1, 60, 5)

# Session State to keep the bot running
if "bot_active" not in st.session_state:
    st.session_state.bot_active = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 START BOT", use_container_width=True, type="primary"):
        st.session_state.bot_active = True
with col2:
    if st.button("🛑 STOP BOT", use_container_width=True):
        st.session_state.bot_active = False

# --- 3. THE AUTOMATION LOOP ---
status_window = st.empty()
log_window = st.container()

if st.session_state.bot_active:
    status_window.success(f"Running: Trading {ticker} every {wait_time} minutes.")
    
    while st.session_state.bot_active:
        # Check if the market is actually open (It is currently Saturday!)
        clock = alpaca.get_clock()
        if not clock.is_open:
            status_window.warning("Market is currently CLOSED. Waiting for opening bell...")
            time.sleep(60)
            st.rerun()

        try:
            # Step A: Get current price
            price = alpaca.get_latest_trade(ticker).price
            
            # Step B: Ask Claude for a decision
            with log_window:
                st.write(f"🔍 Analyzing {ticker} at **${price}**...")
            
            prompt = f"The price of {ticker} is ${price}. Should I BUY, SELL, or HOLD? Reply with only the word."
            
            response = claude.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=10,
                messages=[{"role": "user", "content": prompt}]
            )
            decision = response.content[0].text.strip().upper()
            
            # Step C: Execute based on AI Decision
            if "BUY" in decision:
                alpaca.submit_order(symbol=ticker, qty=trade_qty, side='buy', type='market', time_in_force='gtc')
                st.toast(f"✅ Bought {trade_qty} shares of {ticker}!", icon="💰")
            elif "SELL" in decision:
                try:
                    alpaca.submit_order(symbol=ticker, qty=trade_qty, side='sell', type='market', time_in_force='gtc')
                    st.toast(f"📉 Sold {trade_qty} shares of {ticker}!", icon="🔥")
                except:
                    log_window.error("Tried to sell, but no position found.")
            else:
                log_window.info(f"Claude says: **HOLD**. No trade made.")

            # Step D: Wait and Rerun
            time.sleep(wait_time * 60)
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")
            st.session_state.bot_active = False
            break
else:
    status_window.info("Bot is IDLE. Press Start to begin.")