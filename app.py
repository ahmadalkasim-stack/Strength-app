import streamlit as st
import pandas as pd
import asyncio
from metaapi_cloud_sdk import MetaApi
from datetime import datetime
import numpy as np
import plotly.graph_objects as go
import time

st.set_page_config(layout="wide", page_title="G4 LFX - Currency Dominance")
st.title("💰 G4 LFX - Currency Dominance IA - REAL-TIME")

# --- Secrets ---
try:
    TOKEN = st.secrets["METAAPI_TOKEN"]
    ACCOUNT_ID = st.secrets["METAAPI_ACCOUNT_ID"]
    st.sidebar.success("✅ MetaApi Connected")
except:
    st.sidebar.error("❌ Secrets tidak ditemukan!")
    st.stop()

# --- Konfigurasi Pair (semua pakai akhiran "m") ---
PAIRS_CONFIG = {
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

async def get_real_data(pairs, tf):
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
                mult = 100 if ('JPY' in pair or 'XAU' in pair or 'BTC' in pair) else 10000
                change = (cn - cp) * mult
                return pair, change
            else:
                return pair, 0.0
        except:
            return pair, 0.0
    tasks = [fetch(p) for p in pairs]
    results = await asyncio.gather(*tasks)
    return dict(results)

# --- Sidebar ---
st.sidebar.header("⚙️ Pengaturan")
tf_map = {"W1": "1w", "D1": "1d", "H4": "4h", "H1": "1h", "M15": "15m"}
selected_tf = st.sidebar.selectbox("Pilih Timeframe", list(tf_map.keys()), index=3)
tf_value = tf_map[selected_tf]

auto_refresh = st.sidebar.checkbox("🔄 Auto-Refresh (1 detik)", value=True)
if st.sidebar.button("🔄 Refresh Sekarang"):
    st.rerun()

st.sidebar.caption("🟢 ▲ = Naik | 🔴 ▼ = Turun")
st.sidebar.caption(f"⏱️ Update: {datetime.now().strftime('%H:%M:%S')}")

# --- Ambil Data Real ---
all_pairs = []
for pl in PAIRS_CONFIG.values():
    all_pairs.extend(pl)

with st.spinner(f"⏳ Mengambil data real-time {selected_tf}..."):
    changes = run_async(get_real_data(all_pairs, tf_value))

# Filter pair yang berhasil (> 1 pip)
non_zero = {k:v for k,v in changes.items() if abs(v) > 1}
if non_zero:
    st.sidebar.success(f"✅ Real: {len(non_zero)} pair")
else:
    st.sidebar.warning("⚠️ Data real 0 (mungkin simbol salah atau market tutup)")

# --- Hitung Strength ---
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

# --- Tentukan status ---
values = [currency_strength[c] for c in PAIRS_CONFIG.keys() if c not in ["XAU", "BTC"]]
median = np.median(values) if values else 0
status_dict = {}
for curr in PAIRS_CONFIG.keys():
    if curr in ["XAU", "BTC"]:
        status_dict[curr] = "STRONG"
    elif currency_strength[curr] > median:
        status_dict[curr] = "STRONG"
    else:
        status_dict[curr] = "WEAK"

# --- Fungsi tampilan ---
def tampilkan_currency(currency, col):
    status = status_dict[currency]
    label = f"{currency}-{status}"
    plist = PAIRS_CONFIG[currency]
    with col:
        st.markdown(f"### {label}")
        st.caption(f"{selected_tf}")
        total_pips = 0
        base_color = "#00cc44" if status == "STRONG" else "#ff3333"
        for pair in plist:
            if pair in changes:
                pips = changes[pair]
                total_pips += abs(pips)
                if abs(pips) > 20:
                    color = base_color
                else:
                    color = "#88dd88" if status == "STRONG" else "#ff8888"
                arrow = "▲" if pips > 0 else "▼" if pips < 0 else "•"
                st.markdown(f"<span style='color:{color};font-size:14px'>{arrow} {pair} {pips:.0f}</span>", unsafe_allow_html=True)
        st.caption(f"Total: {total_pips:.0f}")
        st.divider()

# --- Layout ---
st.subheader(f"📊 Currency Dominance IA - {selected_tf} (Real-time)")

col1, col2 = st.columns(2)
tampilkan_currency("XAU", col1)
tampilkan_currency("BTC", col2)

col1, col2, col3, col4 = st.columns(4)
tampilkan_currency("JPY", col1)
tampilkan_currency("USD", col2)
tampilkan_currency("EUR", col3)
tampilkan_currency("GBP", col4)

col1, col2, col3, col4 = st.columns(4)
tampilkan_currency("AUD", col1)
tampilkan_currency("NZD", col2)
tampilkan_currency("CAD", col3)
tampilkan_currency("CHF", col4)

# --- Daily Currency Strength Meter ---
st.subheader("📊 Daily Currency Strength Meter")
sorted_curr = [c for c in PAIRS_CONFIG.keys() if c not in ["XAU", "BTC"]]
sorted_curr_sorted = sorted(sorted_curr, key=lambda x: currency_strength[x], reverse=True)
max_val = max(abs(v) for v in currency_strength.values() if v != 0) if currency_strength else 1
normalized = {c: (currency_strength[c] / max_val) * 10 for c in sorted_curr_sorted}
currs = [c[0] for c in normalized.items()]
vals = [c[1] for c in normalized.items()]

fig = go.Figure()
fig.add_trace(go.Bar(
    x=vals, y=currs, orientation='h',
    marker_color=['#2ecc71' if v > 0 else '#e74c3c' for v in vals],
    text=[f"{v:.2f}" for v in vals], textposition='outside'
))
fig.update_layout(height=250, margin=dict(l=10,r=10,t=10,b=10), xaxis_title="Strength Score")
st.plotly_chart(fig, use_container_width=True)

# --- Auto-refresh setiap 1 detik ---
if auto_refresh:
    time.sleep(1)
    st.rerun()

st.caption(f"🔄 Update terakhir: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
st.caption("🟢 ▲ = Naik | 🔴 ▼ = Turun | 🟡 XAU | 🪙 BTC")
