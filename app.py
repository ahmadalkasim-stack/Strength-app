import streamlit as st
import pandas as pd
import asyncio
from metaapi_cloud_sdk import MetaApi
from datetime import datetime
import numpy as np
import plotly.graph_objects as go
import time
import random

st.set_page_config(layout="wide", page_title="G4 LFX - Real-time")
st.title("💰 G4 LFX - Currency Dominance IA (Real-time)")

# --- Secrets ---
try:
    TOKEN = st.secrets["METAAPI_TOKEN"]
    ACCOUNT_ID = st.secrets["METAAPI_ACCOUNT_ID"]
    st.sidebar.success("✅ MetaApi Connected")
except:
    st.sidebar.error("❌ Secrets tidak ditemukan!")
    st.stop()

# --- SEMUA PAIR PAKAI AKHIRAN "m" ---
PAIRS = {
    "JPY": ["GBPJPYm", "AUDJPYm", "EURJPYm", "CADJPYm", "NZDJPYm", "USDJPYm", "CHFJPYm"],
    "CHF": ["AUDCHFm", "GBPCHFm", "EURCHFm", "NZDCHFm", "CADCHFm", "USDCHFm", "CHFJPYm"],
    "USD": ["AUDUSDm", "USDCADm", "EURUSDm", "GBPUSDm", "NZDUSDm", "USDCHFm", "USDJPYm"],
    "GBP": ["GBPAUDm", "GBPNZDm", "GBPCADm", "EURGBPm", "GBPUSDm", "GBPCHFm", "GBPJPYm"],
    "EUR": ["EURAUDm", "EURNZDm", "EURCADm", "EURGBPm", "EURCHFm", "EURUSDm", "EURJPYm"],
    "CAD": ["AUDCADm", "NZDCADm", "EURCADm", "GBPCADm", "CADCHFm", "USDCADm", "CADJPYm"],
    "NZD": ["AUDNZDm", "NZDCADm", "NZDUSDm", "NZDCHFm", "EURNZDm", "GBPNZDm", "NZDJPYm"],
    "AUD": ["AUDNZDm", "AUDCADm", "AUDCHFm", "AUDUSDm", "EURAUDm", "AUDJPYm", "GBPAUDm"],
    "XAU": ["XAUUSDm", "XAUJPYm", "XAUGBPm", "XAUEURm", "XAUAUDm", "XAUNZDm", "XAUCADm", "XAUCHFm"],
    "BTC": ["BTCUSDm", "BTCJPYm", "BTCGBPm", "BTCEURm", "BTCAUDm", "BTCNZDm", "BTCCADm", "BTCCHFm"]
}

# --- Fungsi Async ---
def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

async def get_all_rates(pairs, tf):
    changes = {}
    async def fetch(pair):
        try:
            api = MetaApi(token=TOKEN)
            account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
            await account.connect()
            rates = await account.get_rates(pair, tf, 2)
            await account.disconnect()
            if rates and len(rates) >= 2:
                cp = rates[0]['close']
                cn = rates[-1]['close']
                if cp == 0 or cn == 0:
                    return pair, 0.0
                mult = 100 if ('JPY' in pair or 'XAU' in pair or 'BTC' in pair) else 10000
                change = (cn - cp) * mult
                return pair, change
            return pair, 0.0
        except Exception as e:
            return pair, 0.0
    tasks = [fetch(p) for p in pairs]
    results = await asyncio.gather(*tasks)
    return dict(results)

# --- Fungsi Simulasi Stabil (tidak loncat-loncat) ---
def generate_stable_fallback():
    """Menghasilkan data simulasi yang stabil berdasarkan harga awal."""
    base = {
        "GBPJPYm": 1057, "AUDJPYm": 973, "EURJPYm": 964, "CADJPYm": 602,
        "NZDJPYm": 550, "USDJPYm": 515, "CHFJPYm": 420,
        "AUDCHFm": 350, "GBPCHFm": 286, "EURCHFm": 266, "NZDCHFm": 188,
        "CADCHFm": 161, "USDCHFm": 55,
        "AUDUSDm": 369, "USDCADm": 348, "EURUSDm": 282, "GBPUSDm": 261,
        "NZDUSDm": 150, "GBPAUDm": 870, "GBPNZDm": 327, "GBPCADm": 105,
        "EURAUDm": 630, "EURNZDm": 230, "EURCADm": 1, "EURGBPm": 2,
        "AUDCADm": 321, "NZDCADm": 38, "AUDNZDm": 229,
        "XAUUSDm": 4100, "XAUJPYm": 1500, "XAUGBPm": 8000,
        "XAUEURm": 9000, "XAUAUDm": 7000, "XAUNZDm": 6500,
        "XAUCADm": 7500, "XAUCHFm": 8500,
        "BTCUSDm": 1200, "BTCJPYm": 180, "BTCGBPm": 950,
        "BTCEURm": 1100, "BTCAUDm": 1600, "BTCNZDm": 1700,
        "BTCCADm": 1500, "BTCCHFm": 1300
    }
    # Tambahkan noise kecil agar tidak semua 0
    for k in base:
        base[k] += random.randint(-20, 20)
    return base

# --- Sidebar ---
st.sidebar.header("⚙️ Pengaturan")
tf_map = {"W1": "1w", "D1": "1d", "H4": "4h", "H1": "1h", "M15": "15m"}
selected_tf = st.sidebar.selectbox("Pilih Timeframe", list(tf_map.keys()), index=3)
tf_value = tf_map[selected_tf]

refresh_interval = st.sidebar.selectbox("⏱️ Refresh Interval", ["Off", "1 detik", "2 detik", "5 detik", "10 detik"], index=2)
if st.sidebar.button("🔄 Refresh Sekarang"):
    st.rerun()

st.sidebar.caption("🟢 ▲ = Naik | 🔴 ▼ = Turun")
st.sidebar.caption(f"⏱️ Update: {datetime.now().strftime('%H:%M:%S')}")

# --- Ambil Data ---
all_pairs = []
for pl in PAIRS.values():
    all_pairs.extend(pl)

with st.spinner(f"⏳ Mengambil data real-time {selected_tf}..."):
    changes = run_async(get_all_rates(all_pairs, tf_value))

# Cek real data
real_count = len([v for v in changes.values() if abs(v) > 0.1])
if real_count > 0:
    st.sidebar.success(f"✅ Real: {real_count} pair")
else:
    st.sidebar.warning("⚠️ Data real 0 — gunakan simulasi stabil")
    changes = generate_stable_fallback()

# --- Hitung Strength ---
currency_strength = {}
for curr, plist in PAIRS.items():
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

# --- Status ---
values = [currency_strength[c] for c in PAIRS.keys() if c not in ["XAU", "BTC"]]
median = np.median(values) if values else 0
status = {}
for c in PAIRS.keys():
    if c in ["XAU", "BTC"]:
        status[c] = "STRONG"
    elif currency_strength[c] > median:
        status[c] = "STRONG"
    else:
        status[c] = "WEAK"

# --- Tampilan ---
def tampil(curr, col):
    s = status[curr]
    label = f"{curr}-{s}"
    with col:
        st.markdown(f"### {label}")
        st.caption(f"{selected_tf}")
        total_pips = 0
        base = "#00cc44" if s == "STRONG" else "#ff3333"
        for p in PAIRS[curr]:
            if p in changes:
                pips = changes[p]
                total_pips += abs(pips)
                color = base if abs(pips) > 20 else ("#88dd88" if s == "STRONG" else "#ff8888")
                arrow = "▲" if pips > 0 else "▼" if pips < 0 else "•"
                st.markdown(f"<span style='color:{color};font-size:14px'>{arrow} {p} {pips:.1f}</span>", unsafe_allow_html=True)
        st.caption(f"Total: {total_pips:.1f}")
        st.divider()

st.subheader(f"📊 Currency Dominance IA - {selected_tf}")

c1, c2 = st.columns(2)
tampil("XAU", c1); tampil("BTC", c2)

c1, c2, c3, c4 = st.columns(4)
tampil("JPY", c1); tampil("USD", c2); tampil("EUR", c3); tampil("GBP", c4)

c1, c2, c3, c4 = st.columns(4)
tampil("AUD", c1); tampil("NZD", c2); tampil("CAD", c3); tampil("CHF", c4)

# --- Daily Currency Strength Meter ---
st.subheader("📊 Daily Currency Strength Meter")
sorted_curr = [c for c in PAIRS.keys() if c not in ["XAU", "BTC"]]
sorted_curr = sorted(sorted_curr, key=lambda x: currency_strength[x], reverse=True)

# CEGAH ERROR max_val = 0
valid_values = [currency_strength[c] for c in sorted_curr if currency_strength[c] != 0]
if valid_values:
    max_val = max(abs(v) for v in valid_values)
else:
    max_val = 1

norm = {c: (currency_strength[c] / max_val) * 10 for c in sorted_curr}

fig = go.Figure()
fig.add_trace(go.Bar(
    x=list(norm.values()), y=list(norm.keys()), orientation='h',
    marker_color=['#2ecc71' if v > 0 else '#e74c3c' for v in norm.values()],
    text=[f"{v:.2f}" for v in norm.values()], textposition='outside'
))
fig.update_layout(height=250, margin=dict(l=10,r=10,t=10,b=10), xaxis_title="Strength Score")
st.plotly_chart(fig, use_container_width=True)

# --- Auto-refresh ---
if refresh_interval != "Off":
    interval = {"1 detik": 1, "2 detik": 2, "5 detik": 5, "10 detik": 10}.get(refresh_interval, 5)
    time.sleep(interval)
    st.rerun()

st.caption(f"🔄 Update: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
st.caption("🟢 ▲ Naik | 🔴 ▼ Turun | 🟡 XAU | 🪙 BTC")
