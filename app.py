import streamlit as st
import pandas as pd
import asyncio
from metaapi_cloud_sdk import MetaApi
from datetime import datetime
import numpy as np
import plotly.graph_objects as go
import time

st.set_page_config(layout="wide", page_title="G4 LFX - Currency Dominance")
st.title("💰 G4 LFX - Currency Dominance IA")

# --- Secrets ---
try:
    TOKEN = st.secrets["METAAPI_TOKEN"]
    ACCOUNT_ID = st.secrets["METAAPI_ACCOUNT_ID"]
    st.sidebar.success("✅ MetaApi Connected")
except:
    st.sidebar.error("❌ Secrets tidak ditemukan!")
    st.stop()

# --- Konfigurasi Pair (base name tanpa akhiran) ---
PAIRS_BASE = {
    "JPY": ["GBPJPY", "AUDJPY", "EURJPY", "CADJPY", "NZDJPY", "USDJPY", "CHFJPY"],
    "CHF": ["AUDCHF", "GBPCHF", "EURCHF", "NZDCHF", "CADCHF", "USDCHF", "CHFJPY"],
    "USD": ["AUDUSD", "USDCAD", "EURUSD", "GBPUSD", "NZDUSD", "USDCHF", "USDJPY"],
    "GBP": ["GBPAUD", "GBPNZD", "GBPCAD", "EURGBP", "GBPUSD", "GBPCHF", "GBPJPY"],
    "EUR": ["EURAUD", "EURNZD", "EURCAD", "EURGBP", "EURCHF", "EURUSD", "EURJPY"],
    "CAD": ["AUDCAD", "NZDCAD", "EURCAD", "GBPCAD", "CADCHF", "USDCAD", "CADJPY"],
    "NZD": ["AUDNZD", "NZDCAD", "NZDUSD", "NZDCHF", "EURNZD", "GBPNZD", "NZDJPY"],
    "AUD": ["AUDNZD", "AUDCAD", "AUDCHF", "AUDUSD", "EURAUD", "AUDJPY", "GBPAUD"],
    "XAU": ["XAUUSD", "XAUJPY", "XAUGBP", "XAUEUR", "XAUAUD", "XAUNZD", "XAUCAD", "XAUCHF"],
    "BTC": ["BTCUSD", "BTCJPY", "BTCGBP", "BTCEUR", "BTCAUD", "BTCNZD", "BTCCAD", "BTCCHF"]
}

# --- Daftar variasi simbol yang akan dicoba ---
SYMBOL_VARIANTS = [
    "",           # tanpa akhiran
    "m",          # Exness
    ".m",         # Exness alternatif
    "pro",        # Pro
    "c",          # Copy
    "ecn",        # ECN
    "stp",        # STP
    "",           # uppercase (akan ditangani terpisah)
]

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
        return [s['symbol'] for s in symbols] if symbols else []
    except:
        return []

async def get_real_data(pairs, tf):
    changes = {}
    async def fetch(pair):
        # Buat daftar variasi simbol
        variants = []
        for suffix in SYMBOL_VARIANTS:
            variants.append(pair + suffix)
            variants.append(pair.upper() + suffix.upper())
        # Tambahkan variasi khusus untuk XAU & BTC
        if pair.startswith("XAU"):
            variants += ["GOLD", "XAUUSD", "XAUSPOT", "XAUUSDm", "XAUUSDpro"]
        if pair.startswith("BTC"):
            variants += ["BITCOIN", "BTCUSD", "BTCUSDm", "BTCUSDpro"]
        
        api = MetaApi(token=TOKEN)
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        await account.connect()
        for sym in variants:
            try:
                rates = await account.get_rates(sym, tf, 2)
                if rates and len(rates) >= 2:
                    cp = rates[0]['close']
                    cn = rates[-1]['close']
                    if cp == 0 or cn == 0:
                        continue
                    mult = 100 if ('JPY' in pair or 'XAU' in pair or 'BTC' in pair) else 10000
                    change = (cn - cp) * mult
                    await account.disconnect()
                    return pair, change
            except:
                continue
        await account.disconnect()
        return pair, 0.0
    tasks = [fetch(p) for p in pairs]
    results = await asyncio.gather(*tasks)
    return dict(results)

# --- Sidebar ---
st.sidebar.header("⚙️ Pengaturan")
tf_map = {"W1": "1w", "D1": "1d", "H4": "4h", "H1": "1h", "M15": "15m"}
selected_tf = st.sidebar.selectbox("Pilih Timeframe", list(tf_map.keys()), index=3)
tf_value = tf_map[selected_tf]

# Auto-refresh interval
refresh_interval = st.sidebar.selectbox("⏱️ Refresh Interval", ["Off", "1 detik", "2 detik", "5 detik"], index=1)
auto_refresh = refresh_interval != "Off"

if st.sidebar.button("🔄 Refresh Sekarang"):
    st.rerun()

st.sidebar.caption("🟢 ▲ = Naik | 🔴 ▼ = Turun")

# --- Debug: Cek simbol yang tersedia ---
if st.sidebar.checkbox("🔍 Debug: Lihat Simbol Tersedia"):
    with st.spinner("Mengambil daftar simbol..."):
        symbols = run_async(get_symbol_list())
        if symbols:
            st.sidebar.success(f"✅ {len(symbols)} simbol ditemukan")
            # Cari simbol yang mengandung XAU, EUR, USD
            xau_symbols = [s for s in symbols if "XAU" in s.upper() or "GOLD" in s.upper()]
            eur_symbols = [s for s in symbols if "EURUSD" in s.upper()]
            st.sidebar.text(f"XAU symbols: {xau_symbols[:5]}")
            st.sidebar.text(f"EURUSD symbols: {eur_symbols[:5]}")
        else:
            st.sidebar.error("❌ Gagal mengambil daftar simbol")

# --- Ambil Data Real ---
all_pairs = []
for pl in PAIRS_BASE.values():
    all_pairs.extend(pl)

# Hapus duplikat
all_pairs = list(set(all_pairs))

with st.spinner(f"⏳ Mengambil data real-time {selected_tf}..."):
    changes = run_async(get_real_data(all_pairs, tf_value))

# Filter pair yang berhasil (> 0.1 pip)
non_zero = {k:v for k,v in changes.items() if abs(v) > 0.1}
if non_zero:
    st.sidebar.success(f"✅ Real: {len(non_zero)} pair")
    st.sidebar.info(f"Contoh: {list(non_zero.items())[:3]}")
else:
    st.sidebar.warning("⚠️ Data real 0 — simbol mungkin salah")
    st.sidebar.info("💡 Aktifkan 'Debug: Lihat Simbol Tersedia' untuk cek simbol yang benar")

# --- Jika semua 0, gunakan data simulasi agar tampilan tidak kosong ---
use_fallback = st.sidebar.checkbox("📊 Gunakan Simulasi (Jika Real 0)", value=True)

if not non_zero and use_fallback:
    st.sidebar.info("📊 Menggunakan data simulasi (fallback)")
    # Buat data simulasi sederhana
    np.random.seed(int(datetime.now().timestamp()) % 10000)
    for pair in all_pairs:
        if pair not in changes or changes[pair] == 0:
            changes[pair] = np.random.normal(0, 50)

# --- Hitung Strength ---
currency_strength = {}
for curr, plist in PAIRS_BASE.items():
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
values = [currency_strength[c] for c in PAIRS_BASE.keys() if c not in ["XAU", "BTC"]]
median = np.median(values) if values else 0
status_dict = {}
for curr in PAIRS_BASE.keys():
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
    plist = PAIRS_BASE[currency]
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
                st.markdown(f"<span style='color:{color};font-size:14px'>{arrow} {pair} {pips:.1f}</span>", unsafe_allow_html=True)
        st.caption(f"Total: {total_pips:.1f}")
        st.divider()

# --- Layout ---
st.subheader(f"📊 Currency Dominance IA - {selected_tf}")

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
sorted_curr = [c for c in PAIRS_BASE.keys() if c not in ["XAU", "BTC"]]
sorted_curr_sorted = sorted(sorted_curr, key=lambda x: currency_strength[x], reverse=True)

# Cegah error max_val = 0
max_val = max(abs(v) for v in currency_strength.values() if v != 0) if any(v != 0 for v in currency_strength.values()) else 1
if max_val == 0:
    max_val = 1

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

# --- Footer & Auto-refresh ---
st.caption(f"🔄 Update: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
st.caption("🟢 ▲ = Naik | 🔴 ▼ = Turun | 🟡 XAU | 🪙 BTC")

if auto_refresh:
    interval = {"1 detik": 1, "2 detik": 2, "5 detik": 5}.get(refresh_interval, 1)
    time.sleep(interval)
    st.rerun()
