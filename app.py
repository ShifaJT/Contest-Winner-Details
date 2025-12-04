import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Contest Check", layout="centered")
st.title("🎯 Contest Checker")
st.markdown("---")

# Simple message
st.info("""
**App is being updated...**

1. ✅ New service account created
2. ✅ Google Sheet shared
3. ✅ Secrets updated

**Next:** Wait 2 minutes for Google permissions to update, then refresh.
""")

st.markdown("---")
st.caption(f"Last check: {datetime.now().strftime('%H:%M:%S')}")
