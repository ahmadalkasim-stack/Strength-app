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

# --- Fungsi untuk menghasilkan data simulasi yang bervariasi (bergerak) ---
def generate_moving_data():
    """Menghasilkan data simulasi dengan pergerakan acak (+/-) agar terlihat hidup."""
    base_data = {
        "AUDJPY": 1108, "GBPJPY": 915, "EURJPY": 915, "NZDJPY": 635,
        "CADJPY": 598, "USDJPY": 454, "CHFJPY": 309,
        "AUDCHF": 465, "EURCHF": 298, "GBPCHF": 276, "NZDCHF": 270,
        "CADCHF": 202, "USDCHF": 75,
        "EURAUD": 898, "EURCAD": 46, "EURGBP": 37, "EURUSD": 293,
        "EURCHF": 298, "EURJPY": 915,
        "AUDUSD": 368, "USDCAD": 348, "GBPUSD": 261, "NZDUSD": 150,
        "GBPAUD": 870, "GBPNZD": 327, "GBPCAD": 105,
        "XAUUSD": 10498, "XAUJPY": 1509, "BTCUSD": 1250,
        "GBPCHF": 276, "NZDCHF": 270, "CADCHF": 202,
        "AUDCAD": 321, "NZDCAD": 38, "EURNZD": 230
    }
    # Tambahkan variasi acak (-50 s/d +50) agar bergerak
    for key in base_data:
        base_data[key] += random.randint(-50, 50)
    return base_data

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
selected_tf = st.sidebar.selectbox("Pilih Timeframe", list(tf_map.keys()), index=3)  # default H1
tf_value = tf_map[selected_tf]

use_simulasi = st.sidebar.checkbox("📊 Mode Simulasi (Pergerakan)", value=True)
refresh = st.sidebar.button("🔄 Refresh Data")

# --- Ambil Data ---
all_pairs = []
for pl in PAIRS_CONFIG.values():
    all_pairs.extend(pl)

changes = {}

if refresh or not use_simulasi:
    with st.spinner("⏳ Mengambil data real..."):
        try:
            real = run_async(get_real_data(all_pairs, tf_value))
            non_zero = {k:v for k,v in real.items() if abs(v) > 1}
            if non_zero:
                changes = real
                st.sidebar.success(f"✅ Real: {len(non_zero)} pair")
            else:
                st.sidebar.warning("⚠️ Real 0, pakai simulasi bergerak")
                changes = generate_moving_data()
        except:
            st.sidebar.error("❌ Gagal, pakai simulasi")
            changes = generate_moving_data()
else:
    changes = generate_moving_data()
    st.sidebar.info("📊 Simulasi (bergerak)")

# --- Hitung Strength ---
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

# Threshold lebih tinggi agar tidak semua WEAK
threshold = 50.0
currency_status = {}
for curr, val in currency_strength.items():
    if val > threshold:
        currency_status[curr] = "STRONG"
    elif val < -threshold:
        currency_status[curr] = "WEAK"
    else:
        currency_status[curr] = "NEUTRAL"

# --- Tampilan Compact ---
st.subheader(f"📊 Currency Dominance IA - {selected_tf}")

# Urutan tampilan: Strong dulu, Weak, Neutral
ordered = []
for status in ["STRONG", "WEAK", "NEUTRAL"]:
    for curr, s in currency_status.items():
        if s == status and curr not in ["XAU", "BTC"]:
            ordered.append(curr)

# 2 kolom, grid rapi
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
                # WARNA: Hijau jika positif (BUY), Merah jika negatif (SELL)
                if pips > 20:
                    color = "#00cc44"  # hijau terang
                    arrow = "▲"
                elif pips < -20:
                    color = "#ff3333"  # merah terang
                    arrow = "▼"
                else:
                    color = "#888888"  # abu-abu
                    arrow = "•"
                st.markdown(f"<span style='color:{color};font-size:14px'>{arrow} {pair} {pips:.0f}</span>", unsafe_allow_html=True)
        st.caption(f"Total: {total_pips:.0f}")
        st.divider()
    col_idx += 1

# --- XAU & BTC (2 kolom sejajar) ---
st.subheader("🟡 XAU & 🪙 BTC - Special Section")
c1, c2 = st.columns(2)

with c1:
    xau_status = currency_status.get("XAU", "NEUTRAL")
    st.markdown(f"### XAU-{xau_status}")
    for p in PAIRS_CONFIG["XAU"]:
        if p in changes:
            pips = changes[p]
            color = "#FFD700" if pips > 20 else "#FF8C00" if pips < -20 else "#888888"
            arrow = "▲" if pips > 20 else "▼" if pips < -20 else "•"
            st.markdown(f"<span style='color:{color};font-weight:bold;font-size:15px'>{arrow} {p} {pips:.0f}</span>", unsafe_allow_html=True)

with c2:
    btc_status = currency_status.get("BTC", "NEUTRAL")
    st.markdown(f"### BTC-{btc_status}")
    for p in PAIRS_CONFIG["BTC"]:
        if p in changes:
            pips = changes[p]
            color = "#f7931a" if pips > 20 else "#ff6b6b" if pips < -20 else "#888888"
            arrow = "▲" if pips > 20 else "▼" if pips < -20 else "•"
            st.markdown(f"<span style='color:{color};font-weight:bold;font-size:15px'>{arrow} {p} {pips:.0f}</span>", unsafe_allow_html=True)

st.divider()

# --- Daily Currency Strength Meter (Compact) ---
st.subheader("📊 Daily Currency Strength Meter")
sv = {c: currency_strength[c] for c in currency_strength if c not in ["XAU", "BTC"]}
sorted_sv = sorted(sv.items(), key=lambda x: x[1], reverse=True)
currs = [c[0] for c in sorted_sv]
vals = [c[1] for c in sorted_sv]

fig = go.Figure()
fig.add_trace(go.Bar(
    x=vals, y=currs, orientation='h',
    marker_color=['#2ecc71' if v > 0 else '#e74c3c' for v in vals],
    text=[f"{v:.1f}" for v in vals], textposition='outside'
))
fig.update_layout(height=250, margin=dict(l=10,r=10,t=10,b=10), xaxis_title="Strength Score")
st.plotly_chart(fig, use_container_width=True)

# --- Footer ---
st.caption(f"🔄 Update: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
st.caption("🟢 ▲ = Naik (BUY) | 🔴 ▼ = Turun (SELL) | 🟡 XAU | 🪙 BTC")
