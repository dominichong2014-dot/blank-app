import streamlit as st
import alpaca_trade_api as tradeapi
import anthropic
import time

# --- 1. SETUP & SECRETS ---
ALPACA_KEY = st.secrets["ALPACA_KEY"]
ALPACA_SECRET = st.secrets["ALPACA_SECRET"]
CLAUDE_KEY = st.secrets["CLAUDE_KEY"]

alpaca = tradeapi.REST(ALPACA_KEY, ALPACA_SECRET, "https://paper-api.alpaca.markets", api_version='v2')
client = anthropic.Anthropic(api_key=CLAUDE_KEY)

# --- 2. APP INTERFACE ---
st.title("🚀 Auto-Compounding AI Trader")
st.write("This bot automatically reinvests 100% of your account balance.")

st.sidebar.header("Bot Control")
# We list 4 stocks here
watch_list = ["NVDA", "AAPL", "TSLA", "MSFT"]
check_interval = st.sidebar.slider("Check every (minutes)", 1, 60, 5)

if "bot_active" not in st.session_state:
    st.session_state.bot_active = False

col1, col2 = st.sidebar.columns(2)
if col1.button("🚀 START"):
    st.session_state.bot_active = True
if col2.button("🛑 STOP"):
    st.session_state.bot_active = False

# --- 3. THE TRADING BRAIN ---
def get_claude_advice(ticker, price):
    prompt = f"The current price of {ticker} is ${price}. Should I BUY, SELL, or HOLD? Answer in one word only."
    message = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip().upper()

# --- 4. THE MAIN LOOP ---
status_box = st.empty()
log_box = st.container()

if st.session_state.bot_active:
    while st.session_state.bot_active:
        # Check if market is open
        if not alpaca.get_clock().is_open:
            status_box.warning("🌙 Market is CLOSED. Waiting...")
            time.sleep(60)
            continue

        # --- NEW: CALCULATE BUDGET AUTOMATICALLY ---
        account = alpaca.get_account()
        total_cash = float(account.cash) # How much money you have right now
        num_stocks = len(watch_list)
        
        # Divide your money by 4
        auto_invest_amount = round(total_cash / num_stocks, 2)
        
        status_box.success(f"✅ Active. Budget per stock: ${auto_invest_amount}")
        
        for ticker in watch_list:
            try:
                price = float(alpaca.get_latest_trade(ticker).price)
                decision = get_claude_advice(ticker, price)
                
                log_box.write(f"🔍 {ticker}: ${price} | Claude says: **{decision}**")

                if "BUY" in decision and auto_invest_amount > 1.0:
                    alpaca.submit_order(
                        symbol=ticker,
                        notional=auto_invest_amount, 
                        side='buy',
                        type='market',
                        time_in_force='day'
                    )
                    log_box.success(f"💸 Auto-Bought ${auto_invest_amount} of {ticker}")

                elif "SELL" in decision:
                    # Logic to sell whatever amount you have
                    alpaca.close_position(ticker)
                    log_box.error(f"💰 Sold all {ticker} positions.")

            except Exception as e:
                log_box.error(f"Error with {ticker}: {e}")

        time.sleep(check_interval * 60)