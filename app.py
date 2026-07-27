import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import time

st.set_page_config(layout="wide", page_title="G4 LFX - Currency Dominance")
st.title("💰 G4 LFX - Currency Dominance IA")

st.sidebar.info("📊 Mode Simulasi Stabil - Data bergerak halus")

# --- PAIRS ---
PAIRS = {
    "JPY": ["GBPJPY", "AUDJPY", "EURJPY", "CADJPY", "NZDJPY", "USDJPY", "CHFJPY"],
    "CHF": ["AUDCHF", "GBPCHF", "EURCHF", "NZDCHF", "CADCHF", "USDCHF", "CHFJPY"],
    "USD": ["AUDUSD", "USDCAD", "EURUSD", "GBPUSD", "NZDUSD", "USDCHF", "USDJPY"],
    "GBP": ["GBPAUD", "GBPNZD", "GBPCAD", "EURGBP", "GBPUSD", "GBPCHF", "GBPJPY"],
    "EUR": ["EURAUD", "EURNZD", "EURCAD", "EURGBP", "EURCHF", "EURUSD", "EURJPY"],
    "CAD": ["AUDCAD", "NZDCAD", "EURCAD", "GBPCAD", "CADCHF", "USDCAD", "CADJPY"],
    "NZD": ["AUDNZD", "NZDCAD", "NZDUSD", "NZDCHF", "EURNZD", "GBPNZD", "NZDJPY"],
    "AUD": ["AUDNZD", "AUDCAD", "AUDCHF", "AUDUSD", "EURAUD", "AUDJPY", "GBPAUD"]
}

# --- Generate data simulasi stabil (bergerak halus) ---
def generate_stable_data():
    # Gunakan seed berdasarkan waktu agar berubah setiap refresh
    np.random.seed(int(datetime.now().timestamp() / 2) % 10000)
    data = {}
    for plist in PAIRS.values():
        for p in plist:
            # Pergerakan kecil antara -10 sampai +10
            data[p] = np.random.normal(0, 15)
    return data

# --- Normalisasi 0-100 ---
def normalize_to_100(data_dict):
    valid_vals = [v for v in data_dict.values() if v is not None and not np.isnan(v)]
    if not valid_vals:
        return {k: 50.0 for k in data_dict.keys()}
    min_val = min(valid_vals)
    max_val = max(valid_vals)
    if max_val == min_val:
        return {k: 50.0 for k in data_dict.keys()}
    result = {}
    for k, v in data_dict.items():
        if v is None or np.isnan(v):
            result[k] = 50.0
        else:
            result[k] = ((v - min_val) / (max_val - min_val)) * 100
    return result

# --- Sidebar ---
st.sidebar.header("⚙️ Pengaturan")
tf_map = {"W1": "1w", "D1": "1d", "H4": "4h", "H1": "1h", "M15": "15m"}
selected_tf = st.sidebar.selectbox("Pilih Timeframe", list(tf_map.keys()), index=3)
refresh_interval = st.sidebar.selectbox("⏱️ Refresh Interval", ["Off", "2 detik", "5 detik", "10 detik"], index=1)
if st.sidebar.button("🔄 Refresh Sekarang"):
    st.rerun()

st.sidebar.caption("🟢 ▲ = Naik | 🔴 ▼ = Turun")
st.sidebar.caption(f"⏱️ Update: {datetime.now().strftime('%H:%M:%S')}")
st.sidebar.success("✅ Data simulasi stabil berjalan")

# --- Ambil Data Simulasi ---
changes = generate_stable_data()

# --- Hitung Strength ---
currency_strength_raw = {}
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
    currency_strength_raw[curr] = total / cnt if cnt > 0 else 0.0

currency_strength_norm = normalize_to_100(currency_strength_raw)

# --- Status ---
status = {}
for c in PAIRS.keys():
    if currency_strength_norm[c] >= 50:
        status[c] = "STRONG"
    else:
        status[c] = "WEAK"

# --- Tampilan ---
def tampil(curr, col):
    s = status[curr]
    score = currency_strength_norm[curr]
    label = f"{curr}-{s} ({score:.1f})"
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

st.subheader(f"📊 Currency Dominance IA - {selected_tf} (0-100)")

c1, c2, c3, c4 = st.columns(4)
tampil("JPY", c1); tampil("USD", c2); tampil("EUR", c3); tampil("GBP", c4)

c1, c2, c3, c4 = st.columns(4)
tampil("AUD", c1); tampil("NZD", c2); tampil("CAD", c3); tampil("CHF", c4)

# --- Daily Currency Strength Meter ---
st.subheader("📊 Daily Currency Strength Meter (0-100)")
sorted_curr = sorted(PAIRS.keys(), key=lambda x: currency_strength_norm[x], reverse=True)
values = [currency_strength_norm[c] for c in sorted_curr]

fig = go.Figure()
fig.add_trace(go.Bar(
    x=values, y=sorted_curr, orientation='h',
    marker_color=['#2ecc71' if v >= 50 else '#e74c3c' for v in values],
    text=[f"{v:.1f}" for v in values], textposition='outside'
))
fig.update_layout(
    height=250,
    margin=dict(l=10,r=10,t=10,b=10),
    xaxis_title="Strength (0-100)",
    xaxis=dict(range=[0, 100])
)
st.plotly_chart(fig, use_container_width=True)

# --- Auto-refresh ---
if refresh_interval != "Off":
    interval = {"2 detik": 2, "5 detik": 5, "10 detik": 10}.get(refresh_interval, 2)
    time.sleep(interval)
    st.rerun()

st.caption(f"🔄 Update: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
st.caption("🟢 ▲ Naik | 🔴 ▼ Turun | Skor 0-100")
st.caption("📌 Mode Simulasi - Data bergerak halus")
