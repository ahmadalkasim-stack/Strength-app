import streamlit as st
import pandas as pd
import asyncio
from metaapi_cloud_sdk import MetaApi
from datetime import datetime
import numpy as np
import plotly.graph_objects as go
import random

st.set_page_config(layout="wide", page_title="G4 LFX - Currency Dominance")
st.title("💰 G4 LFX - Currency Dominance IA")

# --- Secrets ---
try:
    TOKEN = st.secrets["METAAPI_TOKEN"]
    ACCOUNT_ID = st.secrets["METAAPI_ACCOUNT_ID"]
    st.sidebar.success("✅ MetaApi Connected")
except:
    st.sidebar.error("❌ Secrets tidak ditemukan!")

# --- Konfigurasi Pair (Sesuai gambar) ---
PAIRS_CONFIG = {
    "JPY": ["GBPJPY", "AUDJPY", "EURJPY", "CADJPY", "NZDJPY", "USDJPY", "CHFJPY"],
    "CHF": ["AUDCHF", "GBPCHF", "EURCHF", "NZDCHF", "CADCHF", "USDCHF", "CHFJPY"],
    "USD": ["AUDUSD", "USDCAD", "EURUSD", "GBPUSD", "NZDUSD", "USDCHF", "USDJPY"],
    "GBP": ["GBPAUD", "GBPNZD", "GBPCAD", "EURGBP", "GBPUSD", "GBPCHF", "GBPJPY"],
    "EUR": ["EURAUD", "EURNZD", "EURCAD", "EURGBP", "EURCHF", "EURUSD", "EURJPY"],
    "CAD": ["AUDCAD", "NZDCAD", "EURCAD", "GBPCAD", "CADCHF", "USDCAD", "CADJPY"],
    "NZD": ["AUDNZD", "NZDCAD", "NZDUSD", "NZDCHF", "EURNZD", "GBPNZD", "NZDJPY"],
    "AUD": ["AUDNZD", "AUDCAD", "AUDCHF", "AUDUSD", "EURAUD", "AUDJPY", "GBPAUD"]
}

# --- Fungsi Simulasi (menghasilkan data dengan variasi) ---
def generate_realistic_data():
    """Menghasilkan data untuk semua pair dengan variasi yang masuk akal."""
    np.random.seed(int(datetime.now().timestamp()) % 10000)
    data = {}
    # JPY
    data["GBPJPY"] = int(np.random.normal(1057, 50))
    data["AUDJPY"] = int(np.random.normal(973, 50))
    data["EURJPY"] = int(np.random.normal(964, 50))
    data["CADJPY"] = int(np.random.normal(602, 30))
    data["NZDJPY"] = int(np.random.normal(550, 30))
    data["USDJPY"] = int(np.random.normal(515, 25))
    data["CHFJPY"] = int(np.random.normal(420, 20))
    # CHF
    data["AUDCHF"] = int(np.random.normal(350, 20))
    data["GBPCHF"] = int(np.random.normal(286, 15))
    data["EURCHF"] = int(np.random.normal(266, 15))
    data["NZDCHF"] = int(np.random.normal(188, 10))
    data["CADCHF"] = int(np.random.normal(161, 10))
    data["USDCHF"] = int(np.random.normal(55, 5))
    # USD
    data["AUDUSD"] = int(np.random.normal(369, 20))
    data["USDCAD"] = int(np.random.normal(348, 20))
    data["EURUSD"] = int(np.random.normal(282, 15))
    data["GBPUSD"] = int(np.random.normal(261, 15))
    data["NZDUSD"] = int(np.random.normal(150, 10))
    # GBP
    data["GBPAUD"] = int(np.random.normal(870, 40))
    data["GBPNZD"] = int(np.random.normal(327, 20))
    data["GBPCAD"] = int(np.random.normal(105, 10))
    data["EURGBP"] = int(np.random.normal(2, 5))
    # EUR
    data["EURAUD"] = int(np.random.normal(630, 30))
    data["EURNZD"] = int(np.random.normal(230, 15))
    data["EURCAD"] = int(np.random.normal(1, 5))
    data["EURGBP"] = int(np.random.normal(2, 5))
    # CAD
    data["AUDCAD"] = int(np.random.normal(321, 20))
    data["NZDCAD"] = int(np.random.normal(38, 5))
    data["EURCAD"] = int(np.random.normal(1, 5))
    data["GBPCAD"] = int(np.random.normal(105, 10))
    # NZD
    data["AUDNZD"] = int(np.random.normal(229, 15))
    data["NZDCAD"] = int(np.random.normal(38, 5))
    data["NZDUSD"] = int(np.random.normal(150, 10))
    data["NZDCHF"] = int(np.random.normal(188, 10))
    # AUD
    data["AUDNZD"] = int(np.random.normal(229, 15))
    data["AUDCAD"] = int(np.random.normal(321, 20))
    data["AUDCHF"] = int(np.random.normal(350, 20))
    data["AUDUSD"] = int(np.random.normal(369, 20))
    data["EURAUD"] = int(np.random.normal(630, 30))
    data["AUDJPY"] = int(np.random.normal(973, 50))
    # Tambahkan noise
    for k in data:
        data[k] += int(np.random.normal(0, 10))
    return data

# --- Fungsi Async untuk data real ---
def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

async def get_real_data(pairs, tf):
    changes = {}
    async def fetch(pair):
        try:
            variants = [pair, pair+"m", pair+".m"]
            api = MetaApi(token=TOKEN)
            account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
            await account.connect()
            for sym in variants:
                try:
                    rates = await account.get_rates(sym, tf, 2)
                    if rates and len(rates) >= 2:
                        cp = rates[0]['close']
                        cn = rates[-1]['close']
                        mult = 100 if 'JPY' in pair else 10000
                        change = (cn - cp) * mult
                        await account.disconnect()
                        return pair, change
                except:
                    continue
            await account.disconnect()
            return pair, 0.0
        except:
            return pair, 0.0
    tasks = [fetch(p) for p in pairs]
    results = await asyncio.gather(*tasks)
    return dict(results)

# --- Sidebar ---
st.sidebar.header("⚙️ Pengaturan")
tf_map = {"W1": "1w", "D1": "1d", "H4": "4h", "H1": "1h", "M15": "15m"}
selected_tf = st.sidebar.selectbox("Pilih Timeframe", list(tf_map.keys()), index=1)
tf_value = tf_map[selected_tf]

refresh = st.sidebar.button("🔄 Refresh Data")
st.sidebar.caption("🟢 ▲ = Naik | 🔴 ▼ = Turun")

# --- Ambil Data ---
all_pairs = []
for pl in PAIRS_CONFIG.values():
    all_pairs.extend(pl)

changes = {}
with st.spinner(f"⏳ Mengambil data {selected_tf}..."):
    try:
        real = run_async(get_real_data(all_pairs, tf_value))
        non_zero = {k:v for k,v in real.items() if abs(v) > 1}
        if non_zero:
            changes = real
            st.sidebar.success(f"✅ Real: {len(non_zero)} pair")
        else:
            st.sidebar.warning("⚠️ Real 0, pakai simulasi")
            changes = generate_realistic_data()
    except:
        st.sidebar.error("❌ Gagal, pakai simulasi")
        changes = generate_realistic_data()

# --- Hitung Strength per Currency ---
currency_strength = {}
for curr, plist in PAIRS_CONFIG.items():
    total, cnt = 0, 0
    for p in plist:
        if p in changes:
            if p.startswith(curr):
                total += changes[p]
                cnt += 1
            elif p.endswith(curr) or curr in p[3:]:
                total -= changes[p]
                cnt += 1
    currency_strength[curr] = total / cnt if cnt > 0 else 0

# --- Tentukan status STRONG/WEAK (berdasarkan median) ---
values = [currency_strength[c] for c in PAIRS_CONFIG.keys()]
median = np.median(values) if values else 0
strong_set = set()
weak_set = set()
for curr, val in currency_strength.items():
    if val > median:
        strong_set.add(curr)
    else:
        weak_set.add(curr)

# --- Tampilan: 2 Kolom (Strong di kiri, Weak di kanan) ---
st.subheader(f"📊 Currency Dominance IA - {selected_tf}")

# Urutkan currency berdasarkan strength (dari tertinggi ke terendah)
sorted_curr = sorted(currency_strength.items(), key=lambda x: x[1], reverse=True)
ordered_currencies = [c[0] for c in sorted_curr]

# Bagi menjadi strong dan weak sesuai status
strong_list = [c for c in ordered_currencies if c in strong_set]
weak_list = [c for c in ordered_currencies if c in weak_set]

cols = st.columns(2)

# Kolom kiri: Strong
with cols[0]:
    for currency in strong_list:
        label = f"{currency}-STRONG"
        st.markdown(f"### {label}")
        st.caption(f"{selected_tf}")
        plist = PAIRS_CONFIG[currency]
        total_pips = 0
        for pair in plist:
            if pair in changes:
                pips = changes[pair]
                total_pips += abs(pips)
                if pips > 20:
                    color = "#00cc44"
                    arrow = "▲"
                elif pips < -20:
                    color = "#ff3333"
                    arrow = "▼"
                else:
                    color = "#888888"
                    arrow = "•"
                st.markdown(f"<span style='color:{color};font-size:14px'>{arrow} {pair} {pips:.0f}</span>", unsafe_allow_html=True)
        st.caption(f"Total: {total_pips:.0f}")
        st.divider()

# Kolom kanan: Weak
with cols[1]:
    for currency in weak_list:
        label = f"{currency}-WEAK"
        st.markdown(f"### {label}")
        st.caption(f"{selected_tf}")
        plist = PAIRS_CONFIG[currency]
        total_pips = 0
        for pair in plist:
            if pair in changes:
                pips = changes[pair]
                total_pips += abs(pips)
                if pips > 20:
                    color = "#00cc44"
                    arrow = "▲"
                elif pips < -20:
                    color = "#ff3333"
                    arrow = "▼"
                else:
                    color = "#888888"
                    arrow = "•"
                st.markdown(f"<span style='color:{color};font-size:14px'>{arrow} {pair} {pips:.0f}</span>", unsafe_allow_html=True)
        st.caption(f"Total: {total_pips:.0f}")
        st.divider()

# --- Daily Currency Strength Meter ---
st.subheader("📊 Daily Currency Strength Meter")

# Normalisasi ke skala 0-10 (seperti gambar)
max_val = max(abs(v) for v in currency_strength.values()) if currency_strength else 1
normalized = {c: (currency_strength[c] / max_val) * 10 for c in ordered_currencies}
sorted_norm = sorted(normalized.items(), key=lambda x: x[1], reverse=True)
currs = [c[0] for c in sorted_norm]
vals = [c[1] for c in sorted_norm]

fig = go.Figure()
fig.add_trace(go.Bar(
    x=vals, y=currs, orientation='h',
    marker_color=['#2ecc71' if v > 0 else '#e74c3c' for v in vals],
    text=[f"{v:.2f}" for v in vals], textposition='outside'
))
fig.update_layout(height=250, margin=dict(l=10,r=10,t=10,b=10), xaxis_title="Strength Score")
st.plotly_chart(fig, use_container_width=True)

# --- Footer ---
st.caption(f"🔄 Update: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
st.caption("🟢 ▲ = Naik | 🔴 ▼ = Turun")
