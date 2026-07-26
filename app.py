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

# --- Konfigurasi Pair (format simbol Exness) ---
# Exness biasanya pakai akhiran "m" atau ".m"
# Kita coba kedua format
PAIRS_CONFIG = {
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

# --- Data Simulasi (agar tampilan tetap terlihat seperti screenshot) ---
def generate_simulated_data():
    """Menghasilkan data simulasi mirip screenshot."""
    sim_data = {
        "AUDJPY": 1108, "GBPJPY": 915, "EURJPY": 915, "NZDJPY": 635,
        "CADJPY": 598, "USDJPY": 454, "CHFJPY": 309,
        "AUDCHF": 465, "EURCHF": 298, "GBPCHF": 276, "NZDCHF": 270,
        "CADCHF": 202, "USDCHF": 75,
        "EURAUD": 898, "EURCAD": 46, "EURGBP": 37, "EURUSD": 293,
        "AUDUSD": 368, "USDCAD": 348, "GBPUSD": 261, "NZDUSD": 150,
        "GBPAUD": 870, "GBPNZD": 327, "GBPCAD": 105,
        "XAUUSD": 10498, "XAUJPY": 1509, "BTCUSD": 1250
    }
    return sim_data

# --- Fungsi Async untuk ambil data real ---
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
            # Coba beberapa format simbol: tanpa akhiran, "m", ".m"
            symbol_variants = [pair, pair + "m", pair + ".m"]
            api = MetaApi(token=TOKEN)
            account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
            await account.connect()
            for sym in symbol_variants:
                try:
                    rates = await account.get_rates(sym, tf_value, 2)
                    if rates and len(rates) >= 2:
                        close_prev = rates[0]['close']
                        close_now = rates[-1]['close']
                        if 'JPY' in pair or 'XAU' in pair or 'BTC' in pair:
                            pip_multiplier = 100
                        else:
                            pip_multiplier = 10000
                        change_pips = (close_now - close_prev) * pip_multiplier
                        await account.disconnect()
                        return pair, change_pips
                except:
                    continue
            await account.disconnect()
            return pair, 0.0
        except:
            return pair, 0.0

    tasks = [fetch_one(pair) for pair in pairs]
    results = await asyncio.gather(*tasks)
    return dict(results)

# --- Sidebar ---
st.sidebar.header("⚙️ Pengaturan")
tf_map = {"W1": "1w", "D1": "1d", "H4": "4h", "H1": "1h", "M15": "15m"}
selected_tf = st.sidebar.selectbox("Pilih Timeframe", list(tf_map.keys()), index=1)
tf_value = tf_map[selected_tf]

use_simulasi = st.sidebar.checkbox("📊 Gunakan Data Simulasi (Jika Real Gagal)", value=True)

if st.sidebar.button("🔄 Refresh Data"):
    st.rerun()

st.sidebar.caption(f"🕒 Data: {selected_tf}")

# --- Ambil Data ---
all_pairs = []
for pair_list in PAIRS_CONFIG.values():
    all_pairs.extend(pair_list)

changes = {}

with st.spinner(f"⏳ Mengambil data {selected_tf}..."):
    try:
        real_changes = run_async(get_all_changes(all_pairs, tf_value))
        # Cek apakah ada data real yang tidak 0
        non_zero = {k: v for k, v in real_changes.items() if abs(v) > 1}
        if non_zero:
            changes = real_changes
            st.success(f"✅ Data real-time: {len(non_zero)} pair bergerak")
        else:
            if use_simulasi:
                changes = generate_simulated_data()
                st.info("📊 Menggunakan data simulasi (karena real-time 0 atau market tutup)")
            else:
                changes = real_changes
    except:
        if use_simulasi:
            changes = generate_simulated_data()
            st.info("📊 Menggunakan data simulasi (koneksi MetaApi gagal)")

# --- Hitung Strength per Currency ---
currency_strength = {}
for currency, pair_list in PAIRS_CONFIG.items():
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

# Tentukan Strong/Weak (threshold 20 pip)
threshold = 20.0
currency_status = {}
for curr, val in currency_strength.items():
    if val > threshold:
        currency_status[curr] = "STRONG"
    elif val < -threshold:
        currency_status[curr] = "WEAK"
    else:
        currency_status[curr] = "NEUTRAL"

# --- TAMPILAN PERSIS SCREENSHOT ---
st.subheader(f"📊 Currency Dominance IA - {selected_tf}")

# Urutan: Strong dulu (JPY, CHF), lalu Weak (EUR, CAD), lalu Neutral
order_strong = ["JPY", "CHF", "USD", "GBP"]
order_weak = ["EUR", "CAD", "AUD", "NZD"]
ordered_currencies = []

# Ambil Strong dulu
for curr in order_strong:
    if curr in currency_status and currency_status[curr] == "STRONG":
        ordered_currencies.append(curr)
# Ambil Weak
for curr in order_weak:
    if curr in currency_status and currency_status[curr] == "WEAK":
        ordered_currencies.append(curr)
# Ambil sisanya (Neutral)
for curr in currency_status:
    if curr not in ordered_currencies and curr not in ["XAU", "BTC"]:
        ordered_currencies.append(curr)

# Tampilkan dalam 2 kolom
cols = st.columns(2)
col_idx = 0

for currency in ordered_currencies:
    status = currency_status[currency]
    label = f"{currency}-{status}"
    pair_list = PAIRS_CONFIG[currency]
    
    with cols[col_idx % 2]:
        st.markdown(f"### {label}")
        total_pips = 0
        for pair in pair_list:
            if pair in changes:
                pips = changes[pair]
                total_pips += abs(pips)
                if pips > 20:
                    color = "green"
                elif pips < -20:
                    color = "red"
                else:
                    color = "gray"
                st.markdown(f"<span style='color:{color};font-size:16px'>{pair} {pips:.0f}</span>", unsafe_allow_html=True)
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
    for pair in PAIRS_CONFIG["XAU"]:
        if pair in changes:
            pips = changes[pair]
            if pips > 20:
                color = "gold"
            elif pips < -20:
                color = "orange"
            else:
                color = "gray"
            st.markdown(f"<span style='color:{color};font-weight:bold;font-size:16px'>{pair} {pips:.0f}</span>", unsafe_allow_html=True)
with col2:
    st.markdown(f"### BTC-{btc_status}")
    for pair in PAIRS_CONFIG["BTC"]:
        if pair in changes:
            pips = changes[pair]
            if pips > 20:
                color = "#f7931a"
            elif pips < -20:
                color = "#ff6b6b"
            else:
                color = "gray"
            st.markdown(f"<span style='color:{color};font-weight:bold;font-size:16px'>{pair} {pips:.0f}</span>", unsafe_allow_html=True)

st.divider()

# --- Daily Currency Strength Meter (Horizontal Bar Chart) ---
st.subheader("📊 Daily Currency Strength Meter")

# Ambil nilai strength untuk semua currency (kecuali XAU & BTC)
strength_values = {curr: currency_strength[curr] for curr in currency_strength if curr not in ["XAU", "BTC"]}
# Urutkan dari terbesar ke terkecil
sorted_strength = sorted(strength_values.items(), key=lambda x: x[1], reverse=True)

currencies = [c[0] for c in sorted_strength]
values = [c[1] for c in sorted_strength]

fig = go.Figure()
fig.add_trace(go.Bar(
    x=values,
    y=currencies,
    orientation='h',
    marker_color=['#2ecc71' if v > 20 else '#e74c3c' if v < -20 else '#95a5a6' for v in values],
    text=[f"{v:.1f}" for v in values],
    textposition='outside'
))
fig.update_layout(
    height=350,
    margin=dict(l=10, r=10, t=20, b=10),
    xaxis_title="Strength Score",
    yaxis_title="Currency",
    xaxis=dict(range=[-100, 100])
)
st.plotly_chart(fig, use_container_width=True)

# --- Footer ---
st.divider()
st.caption(f"🔄 Update: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
st.caption("📌 Sumber: MetaTrader via MetaApi Cloud + Simulasi")
st.caption("🟢 Positif = Strong | 🔴 Negatif = Weak")
