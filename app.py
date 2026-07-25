import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="XAU vs DXY", layout="wide")
st.title("📊 Strength Meter XAU vs DXY")

@st.cache_data(ttl=120)
def ambil_data():
    end = datetime.now()
    start = end - timedelta(days=30)
    emas = yf.download('GC=F', start=start, end=end, interval='5m', progress=False)['Close']
    dxy = yf.download('DX-Y.NYB', start=start, end=end, interval='5m', progress=False)['Close']
    return pd.DataFrame({'XAU': emas, 'DXY': dxy}).dropna()

data = ambil_data()
if not data.empty:
    last = data.iloc[-1]
    col1, col2 = st.columns(2)
    col1.metric("💰 Emas", f"${last['XAU']:.2f}")
    col2.metric("📊 DXY", f"{last['DXY']:.2f}")

    def hitung_strength(df):
        df = df.copy()
        df['XAU_N'] = (df['XAU'] - df['XAU'].rolling(14).min()) / (df['XAU'].rolling(14).max() - df['XAU'].rolling(14).min()) * 100
        df['DXY_N'] = (df['DXY'] - df['DXY'].rolling(14).min()) / (df['DXY'].rolling(14).max() - df['DXY'].rolling(14).min()) * 100
        df['Strength'] = df['XAU_N'] - df['DXY_N']
        return df

    d_harian = data.resample('D').last().dropna()
    d_4h = data.resample('4h').last().dropna()
    d_1h = data.resample('1h').last().dropna()

    st.subheader("📡 Sinyal")
    c1, c2, c3 = st.columns(3)
    for df, nama, col in zip([d_harian, d_4h, d_1h], ['Harian', '4 Jam', '1 Jam'], [c1, c2, c3]):
        if len(df) > 10:
            s = hitung_strength(df)
            val = s['Strength'].iloc[-1]
            status = "🟢 XAU" if val > 20 else "🔴 DXY" if val < -20 else "⚪ Netral"
            col.metric(nama, f"{val:.1f}", status)

    st.subheader("📈 Grafik Strength")
    fig = go.Figure()
    for df, nama in zip([d_harian, d_4h, d_1h], ['Harian', '4 Jam', '1 Jam']):
        if len(df) > 10:
            s = hitung_strength(df)
            fig.add_trace(go.Scatter(x=df.index, y=s['Strength'], mode='lines', name=nama))
    fig.add_hline(y=0)
    st.plotly_chart(fig, use_container_width=True)
