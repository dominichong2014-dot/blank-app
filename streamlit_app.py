import streamlit as st
import alpaca_trade_api as tradeapi
import anthropic
import time

# --- 1. SETUP & SECRETS ---
# These pull from your Streamlit "Secrets" dashboard
ALPACA_KEY = st.secrets["ALPACA_KEY"]
ALPACA_SECRET = st.secrets["ALPACA_SECRET"]
CLAUDE_KEY = st.secrets["CLAUDE_KEY"]

# Connect to the "Waiters" (APIs)
# We use the paper-api link for safe practice
alpaca = tradeapi.REST(ALPACA_KEY, ALPACA_SECRET, "https://paper-api.alpaca.markets", api_version='v2')
client = anthropic.Anthropic(api_key=CLAUDE_KEY)

# --- 2. THE APP INTERFACE ---
st.title("🤖 Multi-Stock AI Trader")
st.write("Invests a set dollar amount into multiple companies based on Claude's advice.")

# Settings Sidebar
st.sidebar.header("Trading Settings")
watch_list = st.sidebar.text_input("Stocks (comma separated)", "NVDA,AAPL,TSLA,MSFT").split(",")
invest_amount = st.sidebar.number_input("Dollars per trade ($)", min_value=1.0, value=2.0)
check_interval = st.sidebar.slider("Check every (minutes)", 1, 60, 5)

# Start/Stop Logic
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
        clock = alpaca.get_clock()
        
        if not clock.is_open:
            status_box.warning("🌙 Market is CLOSED. Waiting...")
            time.sleep(60)
            continue

        status_box.success("✅ Bot is ACTIVE and Scanning...")
        
        # LOOP THROUGH EACH STOCK
        for ticker in watch_list:
            ticker = ticker.strip() # Clean up spaces
            try:
                # Get current price
                price = float(alpaca.get_latest_trade(ticker).price)
                
                # Ask Claude
                decision = get_claude_advice(ticker, price)
                
                log_box.write(f"🔍 {ticker}: ${price} | Claude says: **{decision}**")

                if "BUY" in decision:
                    alpaca.submit_order(
                        symbol=ticker,
                        notional=invest_amount, # Invests exactly $2.00
                        side='buy',
                        type='market',
                        time_in_force='day'
                    )
                    log_box.success(f"💸 Bought ${invest_amount} of {ticker}")

                elif "SELL" in decision:
                    # Only sells if you actually own it
                    try:
                        alpaca.submit_order(
                            symbol=ticker,
                            notional=invest_amount,
                            side='sell',
                            type='market',
                            time_in_force='day'
                        )
                        log_box.error(f"💰 Sold ${invest_amount} of {ticker}")
                    except:
                        log_box.info(f"Skipped Sell: No {ticker} shares owned.")

            except Exception as e:
                log_box.error(f"Error with {ticker}: {e}")

        time.sleep(check_interval * 60)
else:
    status_box.info("😴 Bot is currently IDLE.")