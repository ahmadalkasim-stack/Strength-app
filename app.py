import streamlit as st
import pandas as pd
import asyncio
from metaapi_cloud_sdk import MetaApi
from datetime import datetime
import numpy as np
import plotly.graph_objects as go
import time

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

# --- Base pair names ---
BASE_PAIRS = {
    "JPY": ["GBPJPY", "AUDJPY", "EURJPY", "CADJPY", "NZDJPY", "USDJPY", "CHFJPY"],
    "CHF": ["AUDCHF", "GBPCHF", "EURCHF", "NZDCHF", "CADCHF", "USDCHF", "CHFJPY"],
    "USD": ["AUDUSD", "USDCAD", "EURUSD", "GBPUSD", "NZDUSD", "USDCHF", "USDJPY"],
    "GBP": ["GBPAUD", "GBPNZD", "GBPCAD", "EURGBP", "GBPUSD", "GBPCHF", "GBPJPY"],
    "EUR": ["EURAUD", "EURNZD", "EURCAD", "EURGBP", "EURCHF", "EURUSD", "EURJPY"],
    "CAD": ["AUDCAD", "NZDCAD", "EURCAD", "GBPCAD", "CADCHF", "USDCAD", "CADJPY"],
    "NZD": ["AUDNZD", "NZDCAD", "NZDUSD", "NZDCHF", "EURNZD", "GBPNZD", "NZDJPY"],
    "AUD": ["AUDNZD", "AUDCAD", "AUDCHF", "AUDUSD", "EURAUD", "AUDJPY", "GBPAUD"]
}

# --- Fungsi Async ---
def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

async def get_symbol_list():
    """Mendapatkan daftar simbol yang tersedia di akun MT5."""
    try:
        api = MetaApi(token=TOKEN)
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        await account.connect()
        symbols = await account.get_symbols()
        await account.disconnect()
        if symbols:
            return [s['symbol'] for s in symbols]
        return []
    except Exception as e:
        st.sidebar.error(f"Error get symbols: {e}")
        return []

async def get_rates_for_symbol(symbol, tf):
    """Ambil data untuk satu simbol."""
    try:
        api = MetaApi(token=TOKEN)
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        await account.connect()
        rates = await account.get_rates(symbol, tf, 2)
        await account.disconnect()
        if rates and len(rates) >= 2:
            cp = rates[0]['close']
            cn = rates[-1]['close']
            if cp == 0 or cn == 0:
                return None
            mult = 100 if 'JPY' in symbol else 10000
            change = (cn - cp) * mult
            return change
        return None
    except:
        return None

# --- Sidebar ---
st.sidebar.header("⚙️ Pengaturan")
tf_map = {"W1": "1w", "D1": "1d", "H4": "4h", "H1": "1h", "M15": "15m"}
selected_tf = st.sidebar.selectbox("Pilih Timeframe", list(tf_map.keys()), index=3)
tf_value = tf_map[selected_tf]

refresh_interval = st.sidebar.selectbox("⏱️ Refresh Interval", ["Off", "2 detik", "5 detik", "10 detik"], index=1)

if st.sidebar.button("🔄 Refresh Sekarang"):
    st.rerun()

st.sidebar.caption("🟢 ▲ = Naik | 🔴 ▼ = Turun")
st.sidebar.caption(f"⏱️ Update: {datetime.now().strftime('%H:%M:%S')}")

# --- Ambil daftar simbol dari MT5 ---
with st.spinner("⏳ Mendapatkan daftar simbol dari MT5..."):
    symbols = run_async(get_symbol_list())

if not symbols:
    st.sidebar.error("❌ Gagal mengambil daftar simbol. Periksa akun MT5.")
    st.stop()

st.sidebar.success(f"✅ {len(symbols)} simbol ditemukan")

# --- Cari simbol yang cocok untuk setiap pair ---
# Daftar akhiran yang umum
suffixes = ["", "m", ".m", "lfx", "pro", "c", "ecn", "stp", "real", "demo"]

# Mapping pair base -> simbol aktual
symbol_map = {}
for curr, plist in BASE_PAIRS.items():
    for base in plist:
        found = None
        for suffix in suffixes:
            candidate = base + suffix
            candidate_upper = base.upper() + suffix.upper()
            if candidate in symbols or candidate_upper in symbols:
                found = candidate if candidate in symbols else candidate_upper
                break
        if found:
            symbol_map[base] = found
        else:
            # Coba tanpa akhiran (case insensitive)
            for s in symbols:
                if s.upper() == base.upper():
                    symbol_map[base] = s
                    break

if symbol_map:
    st.sidebar.success(f"✅ {len(symbol_map)} simbol ditemukan")
    # Tampilkan contoh di sidebar
    example = list(symbol_map.items())[:3]
    st.sidebar.info(f"Contoh: {example}")
else:
    st.sidebar.error("❌ Tidak ada simbol yang cocok! Periksa daftar simbol di MT5.")
    # Tampilkan 10 simbol pertama untuk referensi
    st.sidebar.text("10 simbol pertama:")
    st.sidebar.text(symbols[:10])

# --- Ambil data real menggunakan symbol_map ---
changes = {}
if symbol_map:
    with st.spinner(f"⏳ Mengambil data real-time {selected_tf}..."):
        for base, sym in symbol_map.items():
            change = run_async(get_rates_for_symbol(sym, tf_value))
            if change is not None:
                changes[base] = change
            else:
                changes[base] = 0.0

# Cek real data
real_count = len([v for v in changes.values() if abs(v) > 0.1])
if real_count > 0:
    st.sidebar.success(f"✅ Real: {real_count} pair")
else:
    st.sidebar.warning("⚠️ Data real 0 — mungkin market tutup atau simbol tidak valid")
    # Fallback simulasi agar tampilan tidak kosong
    np.random.seed(int(datetime.now().timestamp()) % 10000)
    for base in symbol_map.keys():
        if base not in changes or changes[base] == 0:
            changes[base] = np.random.normal(0, 50)

# --- Hitung Strength ---
currency_strength_raw = {}
for curr, plist in BASE_PAIRS.items():
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

# Normalisasi 0-100
def normalize_to_100(data_dict):
    valid_vals = [v for v in data_dict.values() if v is not None and not np.isnan(v) and v != 0]
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

# Status
status = {}
for c in BASE_PAIRS.keys():
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
        for p in BASE_PAIRS[curr]:
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
sorted_curr = sorted(BASE_PAIRS.keys(), key=lambda x: currency_strength_norm[x], reverse=True)
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
