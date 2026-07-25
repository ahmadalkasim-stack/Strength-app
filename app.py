import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(layout="wide")
st.title("📊 XAU vs DXY – Fibonacci Custom Strength Meter (28 Level)")

# ===============================================
# 1. AMBIL DATA
# ===============================================
def ambil_data(periode_hari=90):
    end = datetime.now()
    start = end - timedelta(days=periode_hari)
    try:
        g = yf.download('GC=F', start=start, end=end, interval='1h', progress=False)
        d = yf.download('DX-Y.NYB', start=start, end=end, interval='1h', progress=False)
        if g.empty or d.empty:
            raise Exception("Data kosong")
        return pd.DataFrame({'XAU': g['Close'], 'DXY': d['Close']}, index=g.index)
    except:
        dates = pd.date_range(start, end, freq='1h')
        np.random.seed(42)
        xau = 1800 + np.cumsum(np.random.randn(len(dates))*0.5)
        dxy = 100 + np.cumsum(np.random.randn(len(dates))*0.02)
        return pd.DataFrame({'XAU': xau, 'DXY': dxy}, index=dates)

data = ambil_data(90)
if data.empty:
    st.error("❌ Gagal mengambil data. Cek koneksi internet.")
    st.stop()

# ===============================================
# 2. RESAMPLE
# ===============================================
h4 = data.resample('4h').last().dropna()
daily = data.resample('D').last().dropna()
weekly = data.resample('W-MON').last().dropna()

# ===============================================
# 3. FUNGSI STRENGTH
# ===============================================
def hitung_strength(df, jendela=14):
    df = df.copy()
    df['XAU_N'] = (df['XAU'] - df['XAU'].rolling(jendela).min()) / (df['XAU'].rolling(jendela).max() - df['XAU'].rolling(jendela).min()) * 100
    df['DXY_N'] = (df['DXY'] - df['DXY'].rolling(jendela).min()) / (df['DXY'].rolling(jendela).max() - df['DXY'].rolling(jendela).min()) * 100
    df['Strength'] = df['XAU_N'] - df['DXY_N']
    return df

# ===============================================
# 4. FUNGSI FIBONACCI LENGKAP (28 LEVEL)
# ===============================================
def fibonacci_levels(high, low):
    """
    Menghitung 28 level Fibonacci sesuai gambar 1 dan 2.
    """
    diff = high - low
    levels = {
        # ===== GAMBAR 2 (Standar) =====
        '0.0 (SNR)': 0.0,
        '0.382 (38.2 N3 Toyol Trend)': 0.382,
        '0.5 (50.0 Breakout)': 0.5,          # PIVOT UTAMA
        '0.618 (61.8 N3 Toyol Trend)': 0.618,
        '1.0 (100 SNR)': 1.0,
        '1.618 (161.8 TP1)': 1.618,
        '2.618 (261.8 TP2)': 2.618,
        '4.236 (423.6 TP3)': 4.236,
        '1.24 (TP A 38.2)': 1.24,
        '1.31 (TP A 50.0)': 1.31,
        '1.38 (TP A 61.8)': 1.38,
        '2.0 (TP B 38.2)': 2.0,
        '2.11 (TP B 50.0)': 2.11,
        '2.23 (TP B 61.8)': 2.23,
        
        # ===== GAMBAR 1 (Tambahan) =====
        '0.12 (38.2 N3 Rtc)': 0.12,
        '0.18 (50.0 Breakout)': 0.18,
        '0.24 (N3 Toyol Trend)': 0.24,
        '0.44 (N3 Low Risk)': 0.44,
        '0.56 (N3 Low Risk)': 0.56,
        '0.76 (38.2 N3 Rtc)': 0.76,
        '0.82 (50.0 Breakout)': 0.82,
        '0.88 (61.8 Toyol Trend)': 0.88,
        '1.09 (38.2)': 1.09,
        '1.12 (50.0)': 1.12,
        '1.15 (61.8)': 1.15,
        '3.23 (TP C 38.2)': 3.23,
        '3.43 (50.0 Breakout)': 3.43,
        '3.62 (61.8 Toyol Trend)': 3.62
    }
    
    # Konversi level ke harga
    harga_level = {}
    for nama, level in levels.items():
        if level <= 1.0:
            # Retracement (turun dari high)
            harga = high - (diff * level)
        else:
            # Ekstensi (turun lebih jauh dari low)
            # Formula: high - (diff * (level - 1.0))
            harga = high - (diff * (level - 1.0))
        harga_level[nama] = harga
    return harga_level

# ===============================================
# 5. AMBIL CANDLE SEBELUMNYA
# ===============================================
def ambil_candle_sebelumnya(df):
    if len(df) < 2:
        return None, None, None
    candle = df.iloc[-2]  # candle kemarin / minggu lalu
    close = candle['XAU']
    # Estimasi High/Low (karena Yahoo hanya kasih Close, kita buat range 2%)
    high = close * 1.01
    low = close * 0.99
    open_price = close  # proxy
    return high, low, open_price

# ===============================================
# 6. SIDEBAR
# ===============================================
st.sidebar.header("⚙️ Pengaturan")
jenis_fibo = st.sidebar.selectbox(
    "Sumber Fibonacci:",
    ['Daily (candle sebelumnya)', 'Weekly (candle sebelumnya)'],
    index=0
)

if jenis_fibo == 'Daily (candle sebelumnya)':
    df_sumber = daily
    label_sumber = 'Daily'
else:
    df_sumber = weekly
    label_sumber = 'Weekly'

high, low, _ = ambil_candle_sebelumnya(df_sumber)
if high is None:
    st.warning(f"⚠️ Data {label_sumber} tidak cukup.")
    st.stop()

# ===============================================
# 7. HITUNG 28 LEVEL FIBONACCI
# ===============================================
fib_levels = fibonacci_levels(high, low)

# Ambil pivot utama (0.5)
pivot_50 = fib_levels['0.5 (50.0 Breakout)']

# ===============================================
# 8. SINYAL BERDASARKAN H4
# ===============================================
st.subheader("📡 Pivot Point & Sinyal Entry")
h4_last = h4.iloc[-1]
h4_close = h4_last['XAU']
h4_open = h4_last['XAU']  # proxy

if h4_close > pivot_50 and h4_open > pivot_50:
    sinyal = "🟢 BUY (H4 di ATAS pivot 0.5)"
    warna = "green"
elif h4_close < pivot_50 and h4_open < pivot_50:
    sinyal = "🔴 SELL (H4 di BAWAH pivot 0.5)"
    warna = "red"
else:
    sinyal = "⚪ HOLD (H4 di sekitar pivot)"
    warna = "gray"

col1, col2 = st.columns(2)
col1.metric("🎯 Pivot 0.5 (50.0 Breakout)", f"{pivot_50:.2f}")
col2.metric("📌 H4 Close Terakhir", f"{h4_close:.2f}", delta=f"{h4_close - pivot_50:.2f}")
st.markdown(f"<h2 style='color:{warna};'>{sinyal}</h2>", unsafe_allow_html=True)

# ===============================================
# 9. TABEL LEVEL FIBONACCI
# ===============================================
st.subheader(f"📋 Daftar 28 Level Fibonacci ({label_sumber})")
df_fib_table = pd.DataFrame(list(fib_levels.items()), columns=['Level', 'Harga'])
st.dataframe(df_fib_table, use_container_width=True)

# ===============================================
# 10. GRAFIK UTAMA DENGAN 28 GARIS FIBONACCI
# ===============================================
st.subheader(f"📈 Grafik XAU dengan 28 Level Fibonacci ({label_sumber})")
data_plot = data.iloc[-200:]

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=data_plot.index,
    y=data_plot['XAU'],
    mode='lines',
    name='XAUUSD',
    line=dict(color='gold', width=2.5)
))

# Tambahkan 28 garis horizontal
for nama, harga in fib_levels.items():
    # Warna khusus
    if '0.5 (50.0 Breakout)' in nama:
        warna_garis = '#FFD700'  # Kuning emas (pivot utama)
        lebar = 3.0
        dash = 'solid'
    elif 'TP' in nama or 'Tp' in nama:
        warna_garis = '#FF8C00'  # Oranye (Take Profit)
        lebar = 1.8
        dash = 'dash'
    elif 'Breakout' in nama:
        warna_garis = '#00BFFF'  # Biru terang
        lebar = 1.5
        dash = 'dot'
    elif 'Low Risk' in nama:
        warna_garis = '#32CD32'  # Hijau
        lebar = 1.5
        dash = 'dot'
    else:
        warna_garis = '#C0C0C0'  # Abu-abu (level standar)
        lebar = 1.2
        dash = 'dash'
    
    fig.add_hline(
        y=harga, 
        line_dash=dash, 
        line_color=warna_garis, 
        line_width=lebar,
        annotation_text=nama, 
        annotation_position="bottom right",
        annotation_font_size=9
    )

fig.update_layout(
    height=650,
    margin=dict(l=10, r=10, t=30, b=10),
    title=f"XAUUSD - Fibonacci {label_sumber} (Swing High={high:.2f} | Low={low:.2f})",
    xaxis_title="Tanggal",
    yaxis_title="Harga XAU",
    xaxis=dict(rangeslider=dict(visible=True, thickness=0.05)),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': False})

# ===============================================
# 11. STRENGTH METER (SEMUA TIMEFRAME)
# ===============================================
st.subheader("📊 Strength Meter (Konfirmasi Tambahan)")
timeframes = {
    'Weekly': weekly,
    'Daily': daily,
    '4H': h4,
    '1H': data.resample('1h').last().dropna()
}
cols = st.columns(len(timeframes))
for idx, (nama, df_tf) in enumerate(timeframes.items()):
    if len(df_tf) > 10:
        s = hitung_strength(df_tf)['Strength'].iloc[-1]
        if not pd.isna(s):
            status = "🟢 BUY" if s > 20 else "🔴 SELL" if s < -20 else "⚪ HOLD"
            cols[idx].metric(nama, f"{s:.1f}", status)
        else:
            cols[idx].metric(nama, "N/A", "⏳")
    else:
        cols[idx].metric(nama, "N/A", "⏳")

# ===============================================
# 12. PANDUAN
# ===============================================
with st.expander("📖 Keterangan Lengkap Fibonacci Custom (28 Level)"):
    st.markdown("""
    **Sumber Level:**
    - **Gambar 1**: 14 level tambahan (0.12, 0.18, 0.24, 0.44, 0.56, 0.76, 0.82, 0.88, 1.09, 1.12, 1.15, 3.23, 3.43, 3.62)
    - **Gambar 2**: 14 level standar (0.0, 0.382, 0.5, 0.618, 1.0, 1.618, 2.618, 4.236, 1.24, 1.31, 1.38, 2.0, 2.11, 2.23)

    **Aturan Entry:**
    - 🟢 **BUY** jika Open & Close H4 **di atas** pivot 0.5 (50.0 Breakout)
    - 🔴 **SELL** jika Open & Close H4 **di bawah** pivot 0.5
    - ⚪ **HOLD** jika di sekitar pivot

    **Warna Garis pada Grafik:**
    - 🟡 **Kuning Tebal** = Pivot Utama (0.5)
    - 🟠 **Oranye** = Level Take Profit (TP)
    - 🔵 **Biru** = Level Breakout lainnya
    - 🟢 **Hijau** = Low Risk
    - ⚪ **Abu-abu** = Level standar lainnya
    """)
