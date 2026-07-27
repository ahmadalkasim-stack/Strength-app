import streamlit as st
import asyncio
from metaapi_cloud_sdk import MetaApi

st.title("🔍 Test MetaApi Connection")

try:
    TOKEN = st.secrets["METAAPI_TOKEN"]
    ACCOUNT_ID = st.secrets["METAAPI_ACCOUNT_ID"]
    st.write("✅ Secrets ditemukan")
except:
    st.error("❌ Secrets tidak ditemukan")
    st.stop()

async def test_connection():
    try:
        api = MetaApi(token=TOKEN)
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        await account.connect()
        rates = await account.get_rates("EURUSD", "1h", 2)
        await account.disconnect()
        if rates and len(rates) >= 2:
            return f"✅ Berhasil! Harga terakhir EURUSD: {rates[-1]['close']}"
        else:
            return "❌ Tidak ada data"
    except Exception as e:
        return f"❌ Error: {str(e)[:100]}"

def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

if st.button("🔍 Test Koneksi"):
    with st.spinner("Menghubungi MetaApi..."):
        result = run_async(test_connection())
    st.write(result)
