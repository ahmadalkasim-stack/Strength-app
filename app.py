import streamlit as st
import asyncio
from metaapi_cloud_sdk import MetaApi

st.title("🔍 Cek Simbol MT5")

try:
    TOKEN = st.secrets["METAAPI_TOKEN"]
    ACCOUNT_ID = st.secrets["METAAPI_ACCOUNT_ID"]
    st.success("✅ Secrets ditemukan")
except:
    st.error("❌ Secrets tidak ditemukan")
    st.stop()

async def get_symbols():
    try:
        api = MetaApi(token=TOKEN)
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        # Ambil daftar simbol
        symbols = await account.get_symbols()
        if symbols:
            return [s['symbol'] for s in symbols]
        return []
    except Exception as e:
        return f"Error: {e}"

def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

if st.button("🔍 Ambil Daftar Simbol"):
    with st.spinner("Menghubungi MetaApi..."):
        result = run_async(get_symbols())
    
    if isinstance(result, str):
        st.error(f"❌ {result}")
    elif result:
        st.success(f"✅ {len(result)} simbol ditemukan")
        # Cari simbol yang mengandung EUR, USD, JPY, dll.
        keywords = ["EUR", "USD", "JPY", "GBP", "AUD", "NZD", "CAD", "CHF", "XAU", "BTC"]
        found = {}
        for kw in keywords:
            matched = [s for s in result if kw in s.upper()]
            if matched:
                found[kw] = matched[:5]  # tampilkan 5 pertama
        st.json(found)
        # Tampilkan 20 simbol pertama
        st.text("20 simbol pertama:")
        st.text(result[:20])
    else:
        st.warning("Tidak ada simbol ditemukan")
