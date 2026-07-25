import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(layout="wide")
st.title("XAU vs DXY Strength Meter")

def ambil_data():
    end = datetime.now()
    start = end - timedelta(days=30)
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
    c1, c2 = st.columns(2)
    c1.metric("Emas", f"${last['XAU']:.2f}")
    c2.metric("DXY", f"{last['DXY']:.2f}")

    def hitung(df):
        df = df.copy()
        df['XN'] = (df['XAU'] - df['XAU'].rolling(14).min()) / (df['XAU'].rolling(14).max() - df['XAU'].rolling(14).min()) * 100
        df['DN'] = (df['DXY'] - df['DXY'].rolling(14).min()) / (df['DXY'].rolling(14).max() - df['DXY'].rolling(14).min()) * 100
        df['S'] = df['XN'] - df['DN']
        return df

    h = data.resample('D').last().dropna()
    f4 = data.resample('4h').last().dropna()
    o1 = data.resample('1h').last().dropna()

    st.subheader("Sinyal")
    a,b,c = st.columns(3)
    for df, nama, col in zip([h,f4,o1], ['Harian','4Jam','1Jam'], [a,b,c]):
        if len(df)>10:
            s = hitung(df)['S'].iloc[-1]
            status = "XAU" if s>20 else "DXY" if s<-20 else "Netral"
            col.metric(nama, f"{s:.1f}", status)

    fig = go.Figure()
    for df, nama in zip([h,f4,o1], ['Harian','4Jam','1Jam']):
        if len(df)>10:
            fig.add_trace(go.Scatter(x=df.index, y=hitung(df)['S'], mode='lines', name=nama))
    fig.add_hline(y=0)
    st.plotly_chart(fig, use_container_width=True)
