import streamlit as st
import pandas as pd
import asyncio
from metaapi_cloud_sdk import MetaApi
from datetime import datetime
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="G4 LFX - Currency Dominance")
st.title("💰 G4 LFX - Currency Dominance IA")

# --- Secrets ---
try:
    TOKEN = st.secrets["METAAPI_TOKEN"]
    ACCOUNT_ID = st.secrets["METAAPI_ACCOUNT_ID"]
except:
    st.error("❌ Secrets tidak ditemukan!")
    st.stop()

# --- Konfigurasi Pair (SEMUA + "m") ---
PAIRS = {
    "JPY": ["AUDJPY", "GBPJPY", "EURJPY", "NZDJPY", "CADJPY", "USDJPY", "CHFJPY"],
    "CHF": ["AUDCHF", "EURCHF", "GBPCHF", "NZDCHF", "CADCHF", "USDCHF", "CHFJPY"],
    "USD": ["AUDUSD", "EURUSD", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"],
    "GBP": ["GBPAUD", "GBPNZD", "EURGBP", "GBPUSD", "GBPCHF", "GBPJPY"],
    "EUR": ["EURAUD", "EURCAD", "EURGBP", "EURUSD", "EURCHF", "EURJPY"],
    "CAD": ["USDCAD", "AUDCAD", "CADJPY", "CADCHF", "EURCAD", "NZDCAD", "GBPCAD"],
    "AUD": ["AUDUSD", "AUDJPY", "EURAUD", "AUDNZD", "GBPAUD", "AUDCHF", "AUDCAD"],
    "NZD": ["NZDUSD", "NZDJPY", "EURNZD", "AUDNZD", "GBPNZD", "NZDCHF", "NZDCAD"],
    "XAU": ["XAUUSD", "XAUJPY", "XAUGBP", "XAUEUR", "XAUAUD", "XAUNZD", "XAUCAD", "XAUCHF"],
    "BTC": ["BTCUSD", "BTCJPY", "BTCGBP", "BTCEUR", "BTCAUD", "BTCNZD", "BTCCAD", "BTCCHF"]
}

# --- Fungsi untuk menambahkan "m" di belakang simbol ---
def get_symbol_with_m(pair):
    """Tambahkan 'm' di belakang simbol jika belum ada."""
    if pair.endswith("m"):
        return pair
    return pair + "m"

# --- Daftar semua pair dengan "m" ---
all_pairs = []
for pair_list in PAIRS.values():
    for pair in pair_list:
        all_pairs.append(get_symbol_with_m(pair))

# --- Fungsi Async ---
def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

async def get_all_changes(pairs, tf_value):
    """Ambil perubahan semua pair secara paralel."""
    async def fetch_one(pair):
        try:
            symbol = get_symbol_with_m(pair)
            api = MetaApi(token=TOKEN)
            account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
            await account.connect()
            rates = await account.get_rates(symbol, tf_value, 2)
            await account.disconnect()
            if rates and len(rates) >= 2:
                close_prev = rates[0]['close']
                close_now = rates[-1]['close']
                # Konversi ke pips
                if 'JPY' in pair or 'XAU' in pair or 'BTC' in pair:
                    pip_multiplier = 100
                else:
                    pip_multiplier = 10000
                change_pips = (close_now - close_prev) * pip_multiplier
                return pair, change_pips
            else:
                return pair, 0.0
        except Exception as e:
            return pair, 0.0

    tasks = [fetch_one(pair) for pair in pairs]
    results = await asyncio.gather(*tasks)
    return dict(results)

# --- Sidebar ---
st.sidebar.header("⚙️ Pengaturan")
tf_map = {"W1": "1w", "D1": "1d", "H4": "4h", "H1": "1h", "M15": "15m"}
selected_tf = st.sidebar.selectbox("Pilih Timeframe", list(tf_map.keys()), index=1)
tf_value = tf_map[selected_tf]

if st.sidebar.button("🔄 Refresh Data"):
    st.rerun()

st.sidebar.caption(f"🕒 Data: {selected_tf}")
st.sidebar.caption("📌 Semua simbol menggunakan akhiran 'm'")

# --- Ambil Data ---
with st.spinner(f"⏳ Mengambil data {selected_tf}..."):
    changes = run_async(get_all_changes(all_pairs, tf_value))

# --- Hitung Strength per Currency ---
currency_strength = {}
for currency, pair_list in PAIRS.items():
    total, count = 0, 0
    for pair in pair_list:
        if pair in changes:
            if pair.startswith("XAU") or pair.startswith("BTC"):
                total += changes[pair]
                count += 1
            else:
                # Jika currency adalah quote (posisi kedua), balik tandanya
                if currency in pair[3:] or currency in pair.split("/")[-1]:
                    total -= changes[pair]
                else:
                    total += changes[pair]
                count += 1
    currency_strength[currency] = total / count if count > 0 else 0

# Tentukan Strong/Weak
threshold = 2.0  # dalam pip
currency_status = {}
for curr, val in currency_strength.items():
    if val > threshold:
        currency_status[curr] = "STRONG"
    elif val < -threshold:
        currency_status[curr] = "WEAK"
    else:
        currency_status[curr] = "NEUTRAL"

# --- Tampilan: Currency Dominance IA ---
st.subheader(f"📊 Currency Dominance IA - {selected_tf}")

# Urutan tampilan: Strong dulu, lalu Weak, lalu Neutral
ordered_currencies = []
for status in ["STRONG", "WEAK", "NEUTRAL"]:
    for curr, s in currency_status.items():
        if s == status and curr not in ["XAU", "BTC"]:
            ordered_currencies.append(curr)

# Tampilkan dalam 2 kolom
cols = st.columns(2)
col_idx = 0

for currency in ordered_currencies:
    status = currency_status[currency]
    label = f"{currency}-{status}"
    pair_list = PAIRS[currency]
    
    with cols[col_idx % 2]:
        st.markdown(f"### {label}")
        total_pips = 0
        for pair in pair_list:
            if pair in changes:
                pips = changes[pair]
                total_pips += abs(pips)
                if pips > 5:
                    color = "green"
                elif pips < -5:
                    color = "red"
                else:
                    color = "gray"
                st.markdown(f"<span style='color:{color};'>{pair} {pips:.0f}</span>", unsafe_allow_html=True)
        st.caption(f"Total: {total_pips:.0f}")
        st.divider()
    col_idx += 1

# --- Khusus XAU & BTC ---
st.subheader("🟡 XAU & 🪙 BTC - Special Section")
xau_status = currency_status.get("XAU", "NEUTRAL")
btc_status = currency_status.get("BTC", "NEUTRAL")

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"### XAU-{xau_status}")
    for pair in PAIRS["XAU"]:
        if pair in changes:
            pips = changes[pair]
            color = "gold" if pips > 5 else "orange" if pips < -5 else "gray"
            st.markdown(f"<span style='color:{color};font-weight:bold'>{pair} {pips:.0f}</span>", unsafe_allow_html=True)
with col2:
    st.markdown(f"### BTC-{btc_status}")
    for pair in PAIRS["BTC"]:
        if pair in changes:
            pips = changes[pair]
            color = "#f7931a" if pips > 5 else "#ff6b6b" if pips < -5 else "gray"
            st.markdown(f"<span style='color:{color};font-weight:bold'>{pair} {pips:.0f}</span>", unsafe_allow_html=True)

st.divider()

# --- Daily Currency Strength Meter ---
st.subheader("📊 Daily Currency Strength Meter")

# Ambil nilai strength untuk semua currency (kecuali XAU & BTC)
strength_values = {curr: currency_strength[curr] for curr in currency_strength if curr not in ["XAU", "BTC"]}
sorted_strength = sorted(strength_values.items(), key=lambda x: x[1], reverse=True)

currencies = [c[0] for c in sorted_strength]
values = [c[1] for c in sorted_strength]

fig = go.Figure()
fig.add_trace(go.Bar(
    x=values,
    y=currencies,
    orientation='h',
    marker_color=['#2ecc71' if v > 0 else '#e74c3c' if v < 0 else '#95a5a6' for v in values],
    text=[f"{v:.2f}" for v in values],
    textposition='outside'
))
fig.update_layout(
    height=300,
    margin=dict(l=10, r=10, t=20, b=10),
    xaxis_title="Strength Score",
    yaxis_title="Currency"
)
st.plotly_chart(fig, use_container_width=True)

# --- Footer ---
st.divider()
st.caption(f"🔄 Update: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
st.caption("📌 Sumber: MetaTrader via MetaApi Cloud (simbol + 'm')")
st.caption("🟢 Positif = Strong | 🔴 Negatif = Weak")
