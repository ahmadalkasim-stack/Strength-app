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

# --- Konfigurasi Pair ---
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

# --- Fungsi Simulasi Realistis (ada Strong & Weak) ---
def generate_realistic_data():
    """Menghasilkan data dengan beberapa strong dan weak secara alami."""
    base = {
        "AUDJPY": random.randint(800, 1200), "GBPJPY": random.randint(700, 1000),
        "EURJPY": random.randint(700, 1000), "NZDJPY": random.randint(400, 700),
        "CADJPY": random.randint(400, 700), "USDJPY": random.randint(300, 500),
        "CHFJPY": random.randint(200, 400),
        "AUDCHF": random.randint(300, 600), "EURCHF": random.randint(200, 400),
        "GBPCHF": random.randint(200, 400), "NZDCHF": random.randint(150, 350),
        "CADCHF": random.randint(100, 300), "USDCHF": random.randint(50, 150),
        "EURAUD": random.randint(600, 1000), "EURCAD": random.randint(20, 100),
        "EURGBP": random.randint(20, 80), "EURUSD": random.randint(200, 400),
        "EURCHF": random.randint(200, 400), "EURJPY": random.randint(700, 1000),
        "AUDUSD": random.randint(200, 500), "USDCAD": random.randint(200, 500),
        "GBPUSD": random.randint(200, 400), "NZDUSD": random.randint(100, 250),
        "GBPAUD": random.randint(600, 1000), "GBPNZD": random.randint(200, 400),
        "GBPCAD": random.randint(80, 200), "AUDCAD": random.randint(200, 400),
        "NZDCAD": random.randint(30, 100), "EURNZD": random.randint(150, 300),
        "XAUUSD": random.randint(9000, 11000), "XAUJPY": random.randint(1200, 1800),
        "BTCUSD": random.randint(1000, 1500), "GBPCHF": random.randint(200, 400),
        "NZDCHF": random.randint(150, 350), "CADCHF": random.randint(100, 300)
    }
    # Tambahkan +- 50 agar bergerak
    for k in base:
        base[k] += random.randint(-50, 50)
    return base

# --- Fungsi Async ---
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
            variants = [pair, pair+"m", pair+".m", pair+"pro"]
            api = MetaApi(token=TOKEN)
            account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
            await account.connect()
            for sym in variants:
                try:
                    rates = await account.get_rates(sym, tf, 2)
                    if rates and len(rates) >= 2:
                        cp = rates[0]['close']
                        cn = rates[-1]['close']
                        mult = 100 if ('JPY' in pair or 'XAU' in pair or 'BTC' in pair) else 10000
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
selected_tf = st.sidebar.selectbox("Pilih Timeframe", list(tf_map.keys()), index=4)
tf_value = tf_map[selected_tf]

refresh = st.sidebar.button("🔄 Refresh Data")
st.sidebar.caption("🟢 ▲ = Naik | 🔴 ▼ = Turun")

# --- Ambil Data ---
all_pairs = []
for pl in PAIRS_CONFIG.values():
    all_pairs.extend(pl)

# Coba real dulu, jika gagal pakai simulasi
changes = {}
with st.spinner("⏳ Mengambil data..."):
    try:
        real = run_async(get_real_data(all_pairs, tf_value))
        non_zero = {k:v for k,v in real.items() if abs(v) > 1}
        if non_zero:
            changes = real
            st.sidebar.success(f"✅ Real: {len(non_zero)} pair")
        else:
            st.sidebar.warning("⚠️ Real 0, pakai simulasi realistis")
            changes = generate_realistic_data()
    except:
        st.sidebar.error("❌ Gagal, pakai simulasi")
        changes = generate_realistic_data()

# --- Hitung Strength dengan normalisasi ---
currency_strength = {}
for curr, plist in PAIRS_CONFIG.items():
    total, cnt = 0, 0
    for p in plist:
        if p in changes:
            if p.startswith("XAU") or p.startswith("BTC"):
                total += changes[p]
                cnt += 1
            else:
                if curr in p[3:] or curr in p.split("/")[-1]:
                    total -= changes[p]
                else:
                    total += changes[p]
                cnt += 1
    currency_strength[curr] = total / cnt if cnt > 0 else 0

# Threshold dinamis: ambil median dari semua strength
vals = [v for c, v in currency_strength.items() if c not in ["XAU", "BTC"]]
if vals:
    median = np.median(vals)
    threshold = max(50, abs(median) * 0.5)  # threshold adaptif
else:
    threshold = 50

currency_status = {}
for curr, val in currency_strength.items():
    if val > threshold:
        currency_status[curr] = "STRONG"
    elif val < -threshold:
        currency_status[curr] = "WEAK"
    else:
        currency_status[curr] = "NEUTRAL"

# --- Tampilan Compact 2 Kolom ---
st.subheader(f"📊 Currency Dominance IA - {selected_tf}")

# Urutan: Strong, Weak, Neutral
ordered = []
for status in ["STRONG", "WEAK", "NEUTRAL"]:
    for curr, s in currency_status.items():
        if s == status and curr not in ["XAU", "BTC"]:
            ordered.append(curr)

cols = st.columns(2)
col_idx = 0

for currency in ordered:
    status = currency_status[currency]
    label = f"{currency}-{status}"
    plist = PAIRS_CONFIG[currency]
    with cols[col_idx % 2]:
        st.markdown(f"### {label}")
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
    col_idx += 1

# --- XAU & BTC ---
st.subheader("🟡 XAU & 🪙 BTC - Special Section")
c1, c2 = st.columns(2)
with c1:
    xau_status = currency_status.get("XAU", "NEUTRAL")
    st.markdown(f"### XAU-{xau_status}")
    for p in PAIRS_CONFIG["XAU"]:
        if p in changes:
            pips = changes[p]
            color = "#FFD700" if pips > 20 else "#FF8C00" if pips < -20 else "#888"
            arrow = "▲" if pips > 20 else "▼" if pips < -20 else "•"
            st.markdown(f"<span style='color:{color};font-weight:bold'>{arrow} {p} {pips:.0f}</span>", unsafe_allow_html=True)
with c2:
    btc_status = currency_status.get("BTC", "NEUTRAL")
    st.markdown(f"### BTC-{btc_status}")
    for p in PAIRS_CONFIG["BTC"]:
        if p in changes:
            pips = changes[p]
            color = "#f7931a" if pips > 20 else "#ff6b6b" if pips < -20 else "#888"
            arrow = "▲" if pips > 20 else "▼" if pips < -20 else "•"
            st.markdown(f"<span style='color:{color};font-weight:bold'>{arrow} {p} {pips:.0f}</span>", unsafe_allow_html=True)

st.divider()

# --- Daily Currency Strength Meter (Normalisasi) ---
st.subheader("📊 Daily Currency Strength Meter")
sv = {c: currency_strength[c] for c in currency_strength if c not in ["XAU", "BTC"]}
# Normalisasi ke skala -100..100
max_val = max(abs(v) for v in sv.values()) if sv else 1
normalized = {c: (v / max_val) * 100 for c, v in sv.items()}
sorted_sv = sorted(normalized.items(), key=lambda x: x[1], reverse=True)
currs = [c[0] for c in sorted_sv]
vals = [c[1] for c in sorted_sv]

fig = go.Figure()
fig.add_trace(go.Bar(
    x=vals, y=currs, orientation='h',
    marker_color=['#2ecc71' if v > 0 else '#e74c3c' for v in vals],
    text=[f"{v:.1f}" for v in vals], textposition='outside'
))
fig.update_layout(height=250, margin=dict(l=10,r=10,t=10,b=10), xaxis_title="Strength Score", xaxis=dict(range=[-100, 100]))
st.plotly_chart(fig, use_container_width=True)

st.caption(f"🔄 Update: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
st.caption("🟢 ▲ Naik | 🔴 ▼ Turun | 🟡 XAU | 🪙 BTC")
