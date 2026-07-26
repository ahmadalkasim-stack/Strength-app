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

# --- Fungsi Simulasi Realistis dengan Distribusi Normal ---
def generate_smart_simulation():
    """Menghasilkan data dengan beberapa strong dan weak secara alami."""
    np.random.seed(int(datetime.now().timestamp()) % 10000)
    base = {
        # JPY pairs (cenderung positif agar JPY strong)
        "AUDJPY": np.random.normal(1100, 100), "GBPJPY": np.random.normal(900, 80),
        "EURJPY": np.random.normal(900, 80), "NZDJPY": np.random.normal(600, 60),
        "CADJPY": np.random.normal(600, 60), "USDJPY": np.random.normal(450, 40),
        "CHFJPY": np.random.normal(300, 30),
        # CHF pairs (cenderung positif)
        "AUDCHF": np.random.normal(450, 50), "EURCHF": np.random.normal(300, 30),
        "GBPCHF": np.random.normal(280, 30), "NZDCHF": np.random.normal(250, 30),
        "CADCHF": np.random.normal(200, 20), "USDCHF": np.random.normal(80, 10),
        # EUR pairs (cenderung negatif agar EUR weak)
        "EURAUD": np.random.normal(-900, 100), "EURCAD": np.random.normal(-50, 20),
        "EURGBP": np.random.normal(-40, 10), "EURUSD": np.random.normal(-300, 40),
        "EURCHF": np.random.normal(-300, 40), "EURJPY": np.random.normal(-900, 80),
        # USD pairs (netral)
        "AUDUSD": np.random.normal(300, 50), "USDCAD": np.random.normal(-300, 50),
        "GBPUSD": np.random.normal(200, 40), "NZDUSD": np.random.normal(-150, 30),
        "GBPAUD": np.random.normal(800, 80), "GBPNZD": np.random.normal(300, 40),
        "GBPCAD": np.random.normal(100, 20), "AUDCAD": np.random.normal(-300, 40),
        "NZDCAD": np.random.normal(-50, 20), "EURNZD": np.random.normal(-200, 30),
        # XAU & BTC (strong)
        "XAUUSD": np.random.normal(10000, 500), "XAUJPY": np.random.normal(1500, 100),
        "BTCUSD": np.random.normal(1200, 100)
    }
    # Tambahkan noise kecil
    for k in base:
        base[k] += np.random.normal(0, 20)
    return {k: int(v) for k, v in base.items()}

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
selected_tf = st.sidebar.selectbox("Pilih Timeframe", list(tf_map.keys()), index=1)
tf_value = tf_map[selected_tf]

refresh = st.sidebar.button("🔄 Refresh Data")
st.sidebar.caption("🟢 ▲ = Naik | 🔴 ▼ = Turun")

# --- Ambil Data ---
all_pairs = []
for pl in PAIRS_CONFIG.values():
    all_pairs.extend(pl)

changes = {}
with st.spinner("⏳ Mengambil data..."):
    try:
        real = run_async(get_real_data(all_pairs, tf_value))
        non_zero = {k:v for k,v in real.items() if abs(v) > 1}
        if non_zero:
            changes = real
            st.sidebar.success(f"✅ Real: {len(non_zero)} pair")
        else:
            st.sidebar.warning("⚠️ Real 0, pakai simulasi cerdas")
            changes = generate_smart_simulation()
    except:
        st.sidebar.error("❌ Gagal, pakai simulasi")
        changes = generate_smart_simulation()

# --- Hitung Strength dengan Ranking ---
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

# Ranking untuk menentukan Strong/Weak (top 3 strong, bottom 3 weak)
currencies = [c for c in currency_strength if c not in ["XAU", "BTC"]]
if currencies:
    sorted_vals = sorted(currencies, key=lambda x: currency_strength[x], reverse=True)
    strong_count = max(2, len(sorted_vals) // 3)
    weak_count = max(2, len(sorted_vals) // 3)
    strong_set = set(sorted_vals[:strong_count])
    weak_set = set(sorted_vals[-weak_count:])
else:
    strong_set, weak_set = set(), set()

currency_status = {}
for curr in currency_strength:
    if curr in ["XAU", "BTC"]:
        continue
    if curr in strong_set:
        currency_status[curr] = "STRONG"
    elif curr in weak_set:
        currency_status[curr] = "WEAK"
    else:
        currency_status[curr] = "NEUTRAL"

# Status untuk XAU & BTC
for special in ["XAU", "BTC"]:
    if special in currency_strength:
        if currency_strength[special] > 0:
            currency_status[special] = "STRONG"
        else:
            currency_status[special] = "WEAK"

# --- Tampilan 3 Kolom (lebih compact) ---
st.subheader(f"📊 Currency Dominance IA - {selected_tf}")

# Urutan: Strong, Weak, Neutral
ordered = []
for status in ["STRONG", "WEAK", "NEUTRAL"]:
    for curr, s in currency_status.items():
        if s == status and curr not in ["XAU", "BTC"]:
            ordered.append(curr)

cols = st.columns(3)  # 3 kolom agar lebih padat
col_idx = 0

for currency in ordered:
    status = currency_status[currency]
    label = f"{currency}-{status}"
    plist = PAIRS_CONFIG[currency]
    with cols[col_idx % 3]:
        st.markdown(f"### {label}")
        total_pips = 0
        for pair in plist:
            if pair in changes:
                pips = changes[pair]
                total_pips += abs(pips)
                # Gradasi warna: hijau terang jika positif besar, merah jika negatif besar
                if pips > 50:
                    color = "#00cc44"
                    arrow = "▲▲"
                elif pips > 10:
                    color = "#88dd88"
                    arrow = "▲"
                elif pips < -50:
                    color = "#ff3333"
                    arrow = "▼▼"
                elif pips < -10:
                    color = "#ff8888"
                    arrow = "▼"
                else:
                    color = "#888888"
                    arrow = "•"
                st.markdown(f"<span style='color:{color};font-size:13px'>{arrow} {pair} {pips:.0f}</span>", unsafe_allow_html=True)
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
            color = "#FFD700" if pips > 20 else "#FF8C00" if pips < -20 else "#888"
            arrow = "▲" if pips > 20 else "▼" if pips < -20 else "•"
            st.markdown(f"<span style='color:{color};font-weight:bold;font-size:14px'>{arrow} {p} {pips:.0f}</span>", unsafe_allow_html=True)
with c2:
    btc_status = currency_status.get("BTC", "NEUTRAL")
    st.markdown(f"### BTC-{btc_status}")
    for p in PAIRS_CONFIG["BTC"]:
        if p in changes:
            pips = changes[p]
            color = "#f7931a" if pips > 20 else "#ff6b6b" if pips < -20 else "#888"
            arrow = "▲" if pips > 20 else "▼" if pips < -20 else "•"
            st.markdown(f"<span style='color:{color};font-weight:bold;font-size:14px'>{arrow} {p} {pips:.0f}</span>", unsafe_allow_html=True)

st.divider()

# --- Daily Currency Strength Meter (lebih kecil) ---
st.subheader("📊 Daily Currency Strength Meter")
sv = {c: currency_strength[c] for c in currency_strength if c not in ["XAU", "BTC"]}
max_abs = max(abs(v) for v in sv.values()) if sv else 1
normalized = {c: (v / max_abs) * 100 for c, v in sv.items()}
sorted_sv = sorted(normalized.items(), key=lambda x: x[1], reverse=True)
currs = [c[0] for c in sorted_sv]
vals = [c[1] for c in sorted_sv]

fig = go.Figure()
fig.add_trace(go.Bar(
    x=vals, y=currs, orientation='h',
    marker_color=['#2ecc71' if v > 0 else '#e74c3c' for v in vals],
    text=[f"{v:.1f}" for v in vals], textposition='outside'
))
fig.update_layout(height=200, margin=dict(l=10,r=10,t=10,b=10), xaxis_title="Strength Score", xaxis=dict(range=[-100, 100]))
st.plotly_chart(fig, use_container_width=True)

st.caption(f"🔄 Update: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
st.caption("🟢 ▲ = Naik | 🔴 ▼ = Turun | 🟡 XAU | 🪙 BTC")
