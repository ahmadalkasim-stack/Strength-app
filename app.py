import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import yfinance as yf
import time

st.set_page_config(layout="wide", page_title="G4 LFX - Currency Dominance")
st.title("💰 G4 LFX - Currency Dominance IA (Real Data from Yahoo)")

st.sidebar.info("📊 Mengambil data real dari Yahoo Finance (gratis)")

# --- PAIRS dengan ticker Yahoo Finance ---
PAIRS_TICKER = {
    "JPY": {"GBPJPY": "GBPJPY=X", "AUDJPY": "AUDJPY=X", "EURJPY": "EURJPY=X",
            "CADJPY": "CADJPY=X", "NZDJPY": "NZDJPY=X", "USDJPY": "USDJPY=X", "CHFJPY": "CHFJPY=X"},
    "CHF": {"AUDCHF": "AUDCHF=X", "GBPCHF": "GBPCHF=X", "EURCHF": "EURCHF=X",
            "NZDCHF": "NZDCHF=X", "CADCHF": "CADCHF=X", "USDCHF": "USDCHF=X", "CHFJPY": "CHFJPY=X"},
    "USD": {"AUDUSD": "AUDUSD=X", "USDCAD": "USDCAD=X", "EURUSD": "EURUSD=X",
            "GBPUSD": "GBPUSD=X", "NZDUSD": "NZDUSD=X", "USDCHF": "USDCHF=X", "USDJPY": "USDJPY=X"},
    "GBP": {"GBPAUD": "GBPAUD=X", "GBPNZD": "GBPNZD=X", "GBPCAD": "GBPCAD=X",
            "EURGBP": "EURGBP=X", "GBPUSD": "GBPUSD=X", "GBPCHF": "GBPCHF=X", "GBPJPY": "GBPJPY=X"},
    "EUR": {"EURAUD": "EURAUD=X", "EURNZD": "EURNZD=X", "EURCAD": "EURCAD=X",
            "EURGBP": "EURGBP=X", "EURCHF": "EURCHF=X", "EURUSD": "EURUSD=X", "EURJPY": "EURJPY=X"},
    "CAD": {"AUDCAD": "AUDCAD=X", "NZDCAD": "NZDCAD=X", "EURCAD": "EURCAD=X",
            "GBPCAD": "GBPCAD=X", "CADCHF": "CADCHF=X", "USDCAD": "USDCAD=X", "CADJPY": "CADJPY=X"},
    "NZD": {"AUDNZD": "AUDNZD=X", "NZDCAD": "NZDCAD=X", "NZDUSD": "NZDUSD=X",
            "NZDCHF": "NZDCHF=X", "EURNZD": "EURNZD=X", "GBPNZD": "GBPNZD=X", "NZDJPY": "NZDJPY=X"},
    "AUD": {"AUDNZD": "AUDNZD=X", "AUDCAD": "AUDCAD=X", "AUDCHF": "AUDCHF=X",
            "AUDUSD": "AUDUSD=X", "EURAUD": "EURAUD=X", "AUDJPY": "AUDJPY=X", "GBPAUD": "GBPAUD=X"}
}

# --- Ambil data dari Yahoo ---
def get_yahoo_data(ticker, period="5d", interval="1h"):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if not df.empty and len(df) >= 2:
            close_prev = df['Close'].iloc[-2]
            close_now = df['Close'].iloc[-1]
            if close_prev == 0:
                return 0.0
            # Hitung perubahan dalam pips
            if 'JPY' in ticker:
                mult = 100
            else:
                mult = 10000
            change = (close_now - close_prev) * mult
            return change
        return 0.0
    except:
        return 0.0

# --- Sidebar ---
st.sidebar.header("⚙️ Pengaturan")
tf_map = {"5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
selected_tf = st.sidebar.selectbox("Pilih Timeframe", list(tf_map.keys()), index=2)
tf_value = tf_map[selected_tf]

refresh_interval = st.sidebar.selectbox("⏱️ Refresh Interval", ["Off", "10 detik", "30 detik", "60 detik"], index=1)
if st.sidebar.button("🔄 Refresh Sekarang"):
    st.rerun()

st.sidebar.caption("🟢 ▲ = Naik | 🔴 ▼ = Turun")
st.sidebar.caption(f"⏱️ Update: {datetime.now().strftime('%H:%M:%S')}")

# --- Ambil Data Real dari Yahoo ---
changes = {}
all_pairs = []
for curr, plist in PAIRS_TICKER.items():
    for pair, ticker in plist.items():
        all_pairs.append((pair, ticker))

with st.spinner(f"⏳ Mengambil data real dari Yahoo ({selected_tf})..."):
    for pair, ticker in all_pairs:
        changes[pair] = get_yahoo_data(ticker, period="5d", interval=tf_value)

# Cek data real
real_count = len([v for v in changes.values() if abs(v) > 0.001])
if real_count > 0:
    st.sidebar.success(f"✅ Real: {real_count} pair")
else:
    st.sidebar.warning("⚠️ Data real 0 — Yahoo mungkin rate limit")
    # Fallback ke simulasi stabil
    np.random.seed(int(datetime.now().timestamp() / 10) % 10000)
    for pair, _ in all_pairs:
        if pair not in changes or changes[pair] == 0:
            changes[pair] = np.random.normal(0, 15)

# --- Hitung Strength ---
currency_strength_raw = {}
for curr, plist in PAIRS_TICKER.items():
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

currency_strength_norm = normalize_to_100(currency_strength_raw)

# --- Status ---
status = {}
for c in PAIRS_TICKER.keys():
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
        for p in PAIRS_TICKER[curr]:
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
sorted_curr = sorted(PAIRS_TICKER.keys(), key=lambda x: currency_strength_norm[x], reverse=True)
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
    interval = {"10 detik": 10, "30 detik": 30, "60 detik": 60}.get(refresh_interval, 10)
    time.sleep(interval)
    st.rerun()

st.caption(f"🔄 Update: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
st.caption("🟢 ▲ Naik | 🔴 ▼ Turun | Skor 0-100")
st.caption("📌 Sumber: Yahoo Finance (real-time)")
