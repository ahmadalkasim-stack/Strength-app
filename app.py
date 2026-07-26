import streamlit as st
import pandas as pd
import asyncio
from metaapi_cloud_sdk import MetaApi
from datetime import datetime
import numpy as np

st.set_page_config(layout="wide", page_title="G4 LFX - Currency Strength")
st.title("📊 G4 LFX - Currency Strength Meter (Real-time)")

# --- Secrets ---
try:
    TOKEN = st.secrets["METAAPI_TOKEN"]
    ACCOUNT_ID = st.secrets["METAAPI_ACCOUNT_ID"]
except:
    st.error("❌ Secrets tidak ditemukan!")
    st.stop()

# --- Konfigurasi Pair ---
PAIRS = {
    "JPY": ["USDJPY", "EURJPY", "GBPJPY", "NZDJPY", "AUDJPY", "CHFJPY", "CADJPY"],
    "USD": ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCHF", "USDCAD", "USDJPY"],
    "EUR": ["EURUSD", "EURJPY", "EURGBP", "EURNZD", "EURAUD", "EURCHF", "EURCAD"],
    "GBP": ["GBPUSD", "GBPJPY", "EURGBP", "GBPNZD", "GBPAUD", "GBPCHF", "GBPCAD"],
    "AUD": ["AUDUSD", "AUDJPY", "EURAUD", "AUDNZD", "GBPAUD", "AUDCHF", "AUDCAD"],
    "NZD": ["NZDUSD", "NZDJPY", "EURNZD", "AUDNZD", "GBPNZD", "NZDCHF", "NZDCAD"],
    "CAD": ["USDCAD", "CADJPY", "EURCAD", "GBPCAD", "AUDCAD", "CADCHF", "NZDCAD"],
    "CHF": ["USDCHF", "CHFJPY", "EURCHF", "GBPCHF", "AUDCHF", "CADCHF", "NZDCHF"],
    "XAU": ["XAUUSD", "XAUJPY", "XAUGBP", "XAUEUR", "XAUAUD", "XAUNZD", "XAUCAD", "XAUCHF"],
    "BTC": ["BTCUSD", "BTCJPY", "BTCGBP", "BTCEUR", "BTCAUD", "BTCNZD", "BTCCAD", "BTCCHF"]
}

XAU_SYMBOLS = {
    "XAUUSD": "XAUUSD", "XAUJPY": "XAUJPY", "XAUGBP": "XAUGBP",
    "XAUEUR": "XAUEUR", "XAUAUD": "XAUAUD", "XAUNZD": "XAUNZD",
    "XAUCAD": "XAUCAD", "XAUCHF": "XAUCHF"
}

BTC_SYMBOLS = {
    "BTCUSD": "BTCUSD", "BTCJPY": "BTCJPY", "BTCGBP": "BTCGBP",
    "BTCEUR": "BTCEUR", "BTCAUD": "BTCAUD", "BTCNZD": "BTCNZD",
    "BTCCAD": "BTCCAD", "BTCCHF": "BTCCHF"
}

# --- Fungsi Async ---
def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

async def get_change(symbol, timeframe, count=2):
    try:
        api = MetaApi(token=TOKEN)
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        await account.connect()
        rates = await account.get_rates(symbol, timeframe, count)
        await account.disconnect()
        if rates and len(rates) >= 2:
            close_prev = rates[0]['close']
            close_now = rates[-1]['close']
            return ((close_now - close_prev) / close_prev) * 100
        return 0.0
    except:
        return 0.0

# --- Sidebar ---
st.sidebar.header("⚙️ Pengaturan")
tf_map = {"W1": "1w", "D1": "1d", "H4": "4h", "H1": "1h", "M15": "15m"}
selected_tf = st.sidebar.selectbox("Pilih Timeframe", list(tf_map.keys()), index=1)
tf_value = tf_map[selected_tf]

if st.sidebar.button("🔄 Refresh Data"):
    st.rerun()

st.sidebar.caption(f"🕒 Data: {selected_tf}")
st.sidebar.caption("🟢 BUY | 🔴 SELL | ⚪ HOLD")

# --- Ambil Data ---
st.info(f"⏳ Mengambil data untuk {selected_tf}...")

all_pairs = []
for currency, pair_list in PAIRS.items():
    all_pairs.extend(pair_list)

changes = {}
progress = st.progress(0)
all_symbols = {**XAU_SYMBOLS, **BTC_SYMBOLS}

for idx, pair in enumerate(all_pairs):
    if pair in all_symbols:
        symbol = all_symbols[pair]
    else:
        symbol = pair
    changes[pair] = run_async(get_change(symbol, tf_value, 2))
    progress.progress((idx + 1) / len(all_pairs))
progress.empty()
st.success("✅ Data berhasil diambil!")

# --- Hitung Strength ---
currency_strength = {}
for currency, pair_list in PAIRS.items():
    total, count = 0, 0
    for pair in pair_list:
        if pair in changes:
            if pair.startswith("XAU") or pair.startswith("BTC"):
                total += changes[pair]
                count += 1
            else:
                if currency in pair[3:] or currency in pair.split("/")[-1]:
                    total -= changes[pair]
                else:
                    total += changes[pair]
                count += 1
    currency_strength[currency] = total / count if count > 0 else 0

threshold = 0.1
currency_status = {}
for curr, val in currency_strength.items():
    if val > threshold:
        currency_status[curr] = "STRONG"
    elif val < -threshold:
        currency_status[curr] = "WEAK"
    else:
        currency_status[curr] = "NEUTRAL"

# --- Tampilan ---
st.subheader(f"📊 Currency Strength Meter - {selected_tf}")

cols = st.columns(len(currency_status))
for idx, (curr, status) in enumerate(currency_status.items()):
    with cols[idx]:
        st.metric(curr, status, delta=f"{currency_strength[curr]:.2f}%", delta_color="normal")

st.divider()

def get_signal(pair, base, quote):
    base_strength = currency_strength.get(base, 0)
    quote_strength = currency_strength.get(quote, 0)
    if base_strength > threshold and quote_strength < -threshold:
        return "BUY", "green"
    elif base_strength < -threshold and quote_strength > threshold:
        return "SELL", "red"
    else:
        return "HOLD", "gray"

currencies_to_show = ["JPY", "USD", "EUR", "GBP", "AUD", "NZD", "CAD", "CHF"]

for currency in currencies_to_show:
    st.subheader(f"{'🟢' if currency_status[currency]=='STRONG' else '🔴' if currency_status[currency]=='WEAK' else '⚪'} {currency} - {currency_status[currency]}")
    pair_list = PAIRS[currency]
    cols = st.columns(4)
    for idx, pair in enumerate(pair_list):
        with cols[idx % 4]:
            if pair in changes:
                change = changes[pair]
                base = pair[:3]
                quote = pair[3:]
                if pair.startswith("XAU") or pair.startswith("BTC"):
                    base = pair[:3]
                    quote = pair[3:]
                signal, color = get_signal(pair, base, quote)
                st.markdown(f"**{pair}**")
                st.markdown(f"<span style='color:{color};font-weight:bold'>{signal}</span>", unsafe_allow_html=True)
                st.caption(f"Δ {change:.2f}%")
            else:
                st.markdown(f"**{pair}**")
                st.caption("N/A")
    st.divider()

# --- XAU Section ---
st.header("🟡 XAU - Special Section")
st.subheader(f"{'🟢' if currency_status.get('XAU','NEUTRAL')=='STRONG' else '🔴' if currency_status.get('XAU','NEUTRAL')=='WEAK' else '⚪'} XAU - {currency_status.get('XAU','NEUTRAL')}")
xau_pairs = PAIRS["XAU"]
cols = st.columns(4)
for idx, pair in enumerate(xau_pairs):
    with cols[idx % 4]:
        if pair in changes:
            change = changes[pair]
            base = "XAU"
            quote = pair[3:]
            signal, color = get_signal(pair, base, quote)
            st.markdown(f"**{pair}**")
            st.markdown(f"<span style='color:{color};font-weight:bold'>{signal}</span>", unsafe_allow_html=True)
            st.caption(f"Δ {change:.2f}%")
        else:
            st.markdown(f"**{pair}**")
            st.caption("N/A")
st.divider()

# --- BTC Section ---
st.header("🪙 BTC - Special Section")
st.subheader(f"{'🟢' if currency_status.get('BTC','NEUTRAL')=='STRONG' else '🔴' if currency_status.get('BTC','NEUTRAL')=='WEAK' else '⚪'} BTC - {currency_status.get('BTC','NEUTRAL')}")
btc_pairs = PAIRS["BTC"]
cols = st.columns(4)
for idx, pair in enumerate(btc_pairs):
    with cols[idx % 4]:
        if pair in changes:
            change = changes[pair]
            base = "BTC"
            quote = pair[3:]
            signal, color = get_signal(pair, base, quote)
            st.markdown(f"**{pair}**")
            st.markdown(f"<span style='color:{color};font-weight:bold'>{signal}</span>", unsafe_allow_html=True)
            st.caption(f"Δ {change:.2f}%")
        else:
            st.markdown(f"**{pair}**")
            st.caption("N/A")
st.divider()

# --- Footer ---
st.caption(f"🔄 Update: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
st.caption("📌 Sumber: MetaTrader via MetaApi Cloud")
st.caption("🟢 BUY | 🔴 SELL | ⚪ HOLD")
