import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(layout="wide")
st.title("📊 XAU vs DXY Strength Meter")

# --- Ambil Data ---
def ambil_data():
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
    # --- Harga Terbaru ---
    last = data.iloc[-1]
    col1, col2 = st.columns(2)
    col1.metric("💰 Emas", f"${last['XAU']:.2f}")
    col2.metric("📊 DXY", f"{last['DXY']:.2f}")

    # --- Fungsi Hitung Strength ---
    def hitung(df):
        df = df.copy()
        df['XN'] = (df['XAU'] - df['XAU'].rolling(14).min()) / (df['XAU'].rolling(14).max() - df['XAU'].rolling(14).min()) * 100
        df['DN'] = (df['DXY'] - df['DXY'].rolling(14).min()) / (df['DXY'].rolling(14).max() - df['DXY'].rolling(14).min()) * 100
        df['S'] = df['XN'] - df['DN']
        return df

    # --- Resample Semua Timeframe ---
    mingguan = data.resample('W-MON').last().dropna()
    harian = data.resample('D').last().dropna()
    empat_jam = data.resample('4h').last().dropna()
    satu_jam = data.resample('1h').last().dropna()
    limabelas_menit = data.resample('15min').last().dropna()
    lima_menit = data  # data asli 5 menit

    timeframes = {
        'Mingguan': mingguan,
        'Harian': harian,
        '4 Jam': empat_jam,
        '1 Jam': satu_jam,
        '15 Menit': limabelas_menit,
        '5 Menit': lima_menit
    }

    # ================================================================
    # 🆕 BAGIAN SINYAL: DIAGRAM BATANG + BUY/SELL
    # ================================================================
    st.subheader("📡 Sinyal & Strength Semua Timeframe")

    # Kumpulkan data untuk diagram batang
    labels = []
    values = []
    colors = []
    sinyal_text = []

    for nama, df in timeframes.items():
        if len(df) > 5:
            s = hitung(df)['S'].iloc[-1]
            if pd.isna(s):
                s = 0
                warna = 'gray'
                sinyal = 'N/A'
            elif s > 20:
                warna = '#00cc00'  # Hijau terang
                sinyal = '🟢 BUY'
            elif s < -20:
                warna = '#ff3333'  # Merah terang
                sinyal = '🔴 SELL'
            else:
                warna = '#ffcc00'  # Kuning
                sinyal = '⚪ HOLD'
            
            labels.append(nama)
            values.append(s)
            colors.append(warna)
            sinyal_text.append(f"{sinyal}<br><b>{s:.1f}</b>")
        else:
            labels.append(nama)
            values.append(0)
            colors.append('gray')
            sinyal_text.append("⏳ No Data")

    # Buat diagram batang dengan Plotly
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=labels,
        y=values,
        marker_color=colors,
        text=sinyal_text,
        textposition='outside',
        textfont=dict(size=12, family='Arial Black'),
        hovertemplate='%{x}<br>Strength: %{y:.1f}<br>%{text}<extra></extra>'
    ))

    # Tambahkan garis bantu di 0, +20, -20
    fig_bar.add_hline(y=0, line_dash='dash', line_color='black', opacity=0.5)
    fig_bar.add_hline(y=20, line_dash='dot', line_color='green', opacity=0.3)
    fig_bar.add_hline(y=-20, line_dash='dot', line_color='red', opacity=0.3)

    # Atur tampilan diagram batang
    fig_bar.update_layout(
        height=400,
        margin=dict(l=10, r=10, t=40, b=10),
        title="Kekuatan Relatif (XAU vs DXY) per Timeframe",
        xaxis_title="Timeframe",
        yaxis_title="Skor Strength (-100 s.d. +100)",
        yaxis=dict(range=[-100, 100]),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )

    st.plotly_chart(fig_bar, use_container_width=True, config={'scrollZoom': False})

    # ================================================================
    # 📈 GRAFIK UTAMA (DROPDOWN) - Tidak berubah
    # ================================================================
    st.subheader("📈 Grafik Detail (Pilih Timeframe)")

    pilihan = st.selectbox(
        "Pilih timeframe untuk ditampilkan:",
        list(timeframes.keys()),
        index=2  # default 4 Jam
    )

    df_terpilih = timeframes[pilihan]
    if len(df_terpilih) > 5:
        s = hitung(df_terpilih)
        nilai_terakhir = s['S'].iloc[-1]
        if not pd.isna(nilai_terakhir):
            if nilai_terakhir > 20:
                status = "🟢 XAU Kuat (BUY)"
            elif nilai_terakhir < -20:
                status = "🔴 DXY Kuat (SELL)"
            else:
                status = "⚪ Netral (HOLD)"
            st.metric(f"Strength {pilihan}", f"{nilai_terakhir:.1f}", status)

        # Warna garis sesuai strength terakhir
        if nilai_terakhir > 20:
            warna_garis = '#00cc00'
        elif nilai_terakhir < -20:
            warna_garis = '#ff3333'
        else:
            warna_garis = '#ffcc00'

        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=df_terpilih.index,
            y=s['S'],
            mode='lines',
            name=pilihan,
            line=dict(color=warna_garis, width=2.5)
        ))
        fig_line.add_hline(y=0, line_dash="dash", line_color="gray")
        fig_line.add_hrect(y0=20, y1=100, line_width=0, fillcolor="green", opacity=0.1)
        fig_line.add_hrect(y0=-100, y1=-20, line_width=0, fillcolor="red", opacity=0.1)

        fig_line.update_layout(
            height=450,
            margin=dict(l=10, r=10, t=30, b=10),
            title=f"Detail Strength - {pilihan}",
            xaxis_title="Tanggal",
            yaxis_title="Skor (-100 s.d. +100)",
            xaxis=dict(rangeslider=dict(visible=True, thickness=0.05))
        )
        st.plotly_chart(fig_line, use_container_width=True, config={'scrollZoom': False})
