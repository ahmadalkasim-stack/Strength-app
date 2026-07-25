import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(layout="wide")
st.title("📊 XAU vs DXY Strength Meter - All Timeframes")

def ambil_data():
    # Perpanjang ke 90 hari biar data weekly cukup
    end = datetime.now()
    start = end - timedelta(days=90)
    try:
        g = yf.download('GC=F', start, end, interval='5m', progress=False)
        d = yf.download('DX-Y.NYB', start, end, interval='5m', progress=False)
        if g.empty or d.empty:
            raise Exception("Data kosong")
        return pd.DataFrame({'XAU': g['Close'], 'DXY': d['Close']}).dropna()
    except:
        dates = pd.date_range(start, end, freq='5min')
        np.random.seed(42)
        xau = 1800 + np.cumsum(np.random.randn(len(dates))*2)
        dxy = 100 + np.cumsum(np.random.randn(len(dates))*0.1)
        return pd.DataFrame({'XAU': xau, 'DXY': dxy}, index=dates)

data = ambil_data()

if not data.empty:
    last = data.iloc[-1]
    col1, col2 = st.columns(2)
    col1.metric("💰 Emas", f"${last['XAU']:.2f}")
    col2.metric("📊 DXY", f"{last['DXY']:.2f}")

    def hitung(df):
        df = df.copy()
        df['XN'] = (df['XAU'] - df['XAU'].rolling(14).min()) / (df['XAU'].rolling(14).max() - df['XAU'].rolling(14).min()) * 100
        df['DN'] = (df['DXY'] - df['DXY'].rolling(14).min()) / (df['DXY'].rolling(14).max() - df['DXY'].rolling(14).min()) * 100
        df['S'] = df['XN'] - df['DN']
        return df

    # === RESAMPLE SEMUA TIMEFRAME ===
    # Weekly (Senin), Daily, 4H, 1H, 15min, 5min (data asli)
    mingguan = data.resample('W-MON').last().dropna()
    harian = data.resample('D').last().dropna()
    empat_jam = data.resample('4h').last().dropna()
    satu_jam = data.resample('1h').last().dropna()
    limabelas_menit = data.resample('15min').last().dropna()
    lima_menit = data  # data asli sudah 5 menit

    # Simpan dalam list untuk diproses bersama
    timeframes = [
        ('Mingguan', mingguan, 'purple'),
        ('Harian', harian, 'blue'),
        ('4 Jam', empat_jam, 'green'),
        ('1 Jam', satu_jam, 'orange'),
        ('15 Menit', limabelas_menit, 'red'),
        ('5 Menit', lima_menit, 'pink')
    ]

    # === SINYAL (Tampilkan 4 Timeframe Besar di Atas) ===
    st.subheader("📡 Sinyal Terkini")
    a, b, c, d = st.columns(4)
    for df, nama, col in zip([mingguan, harian, empat_jam, satu_jam], 
                             ['Mingguan', 'Harian', '4 Jam', '1 Jam'], 
                             [a, b, c, d]):
        if len(df) > 5:
            s = hitung(df)['S'].iloc[-1]
            if pd.isna(s):
                status = "⏳"
                display = "N/A"
            elif s > 20:
                status = "🟢 XAU"
                display = f"{s:.1f}"
            elif s < -20:
                status = "🔴 DXY"
                display = f"{s:.1f}"
            else:
                status = "⚪ Netral"
                display = f"{s:.1f}"
            col.metric(nama, display, status)

    # === GRAFIK (Semua 6 Timeframe Ditampilkan Vertikal) ===
    st.subheader("📈 Grafik Strength (Semua Timeframe)")

    for nama, df, warna in timeframes:
        if len(df) > 5:
            fig = go.Figure()
            s = hitung(df)
            fig.add_trace(go.Scatter(
                x=df.index, 
                y=s['S'], 
                mode='lines', 
                name=nama, 
                line=dict(color=warna, width=2)
            ))
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            
            # Tambahkan area hijau/merah otomatis
            fig.add_hrect(y0=20, y1=100, line_width=0, fillcolor="green", opacity=0.1)
            fig.add_hrect(y0=-100, y1=-20, line_width=0, fillcolor="red", opacity=0.1)
            
            fig.update_layout(
                height=220,  # Dikecilkan sedikit biar muat banyak
                margin=dict(l=10, r=10, t=30, b=10),
                title=nama,
                xaxis_title="",
                yaxis_title="Strength"
            )
            st.plotly_chart(fig, use_container_width=True)
