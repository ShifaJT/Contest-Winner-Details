import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json

# Simple connection
def connect_sheets():
    try:
        # Get secrets
        creds_dict = dict(st.secrets["google_sheets"])
        
        # Create credentials
        scopes = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        return client
        
    except Exception as e:
        st.error(f"Error: {str(e)[:100]}")
        return None

# App
st.set_page_config(page_title="Contest Check", layout="centered")
st.title("🎯 Contest Checker")
st.markdown("---")

# Connect
client = connect_sheets()

if client:
    try:
        # Open sheet
        sheet = client.open_by_key("1E2qxc1kZttPQMmSXCVXFaQKVNLl_Nhe4uUPBrzf7B3U")
        st.success("✅ Connected!")
        
        # Get sheet names
        worksheets = sheet.worksheets()
        st.write(f"**Sheets found:** {[ws.title for ws in worksheets]}")
        
        # Load Contest Details
        try:
            contest_ws = sheet.worksheet("Contest Details")
            contest_data = contest_ws.get_all_records()
            contests = pd.DataFrame(contest_data)
            
            if not contests.empty:
                st.success(f"📋 {len(contests)} contests loaded")
                
                # Show current contests
                st.header("📢 Current Contests")
                
                # Fix dates
                contests['Start Date'] = pd.to_datetime(contests['Start Date'], errors='coerce', dayfirst=True)
                contests['End Date'] = pd.to_datetime(contests['End Date'], errors='coerce', dayfirst=True)
                
                today = datetime.now().date()
                
                # Current contests
                current = contests[
                    (contests['Start Date'].dt.date <= today) & 
                    (contests['End Date'].dt.date >= today)
                ]
                
                if not current.empty:
                    for _, row in current.iterrows():
                        st.write(f"**{row.get('Camp Name', 'N/A')}**")
                        st.write(f"Ends: {row['End Date'].strftime('%d %b')}")
                        st.write("---")
                else:
                    st.info("No contests running today")
            
        except Exception as e:
            st.error(f"Contest sheet error: {str(e)}")
        
        # Load Winner Details
        try:
            winner_ws = sheet.worksheet("Winner Details")
            winner_data = winner_ws.get_all_records()
            winners = pd.DataFrame(winner_data)
            
            if not winners.empty:
                st.success(f"🏆 {len(winners)} winners loaded")
                
                # Winner search
                st.header("🔍 Check Winner")
                
                search_by = st.selectbox("Search by", ["BZID", "Phone", "Name"])
                search_val = st.text_input("Enter value")
                
                if search_val:
                    if search_by == "BZID" and 'businessid' in winners.columns:
                        results = winners[winners['businessid'].astype(str).str.contains(search_val, case=False)]
                    elif search_by == "Phone" and 'customer_phonenumber' in winners.columns:
                        results = winners[winners['customer_phonenumber'].astype(str).str.contains(search_val, case=False)]
                    elif search_by == "Name" and 'customer_firstname' in winners.columns:
                        results = winners[winners['customer_firstname'].astype(str).str.contains(search_val, case=False)]
                    else:
                        results = pd.DataFrame()
                    
                    if not results.empty:
                        st.success(f"Found {len(results)} win(s)")
                        for _, row in results.head(5).iterrows():
                            st.write(f"**Gift:** {row.get('Gift', 'N/A')}")
                            st.write(f"**Contest:** {row.get('Contest', 'N/A')}")
                            st.write("---")
                    else:
                        st.warning("No wins found")
                        
        except Exception as e:
            st.warning(f"Winner sheet error: {str(e)}")
            
    except Exception as e:
        st.error(f"Sheet error: {str(e)}")
        
else:
    st.error("""
    ❌ Connection failed
    
    **Quick checks:**
    1. Sheet shared with: contest-fresh-dashboard@contest-details-dashboard.iam.gserviceaccount.com
    2. Secrets updated correctly
    3. Wait 2 minutes after sharing
    4. Refresh page
    """)

# Footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%H:%M')}")
if st.button("🔄 Refresh"):
    st.rerun()
