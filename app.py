import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# Simple connection
def connect_sheets():
    try:
        creds_dict = dict(st.secrets["google_sheets"])
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
        sheet = client.open_by_key("1E2qxc1kZttPQMmSXCVXFaQKVNLl_Nhe4uUPBrzf7B3U")
        st.success("✅ Connected!")
        
        # Get ALL sheet names
        worksheets = sheet.worksheets()
        sheet_names = [ws.title for ws in worksheets]
        st.write(f"**Available sheets:** {sheet_names}")
        
        # Load Contest Details
        if 'Contest Details' in sheet_names:
            contest_ws = sheet.worksheet("Contest Details")
            contest_data = contest_ws.get_all_records()
            contests = pd.DataFrame(contest_data)
            
            if not contests.empty:
                st.success(f"📋 {len(contests)} contests loaded")
                
                # Fix dates
                contests['Start Date'] = pd.to_datetime(contests['Start Date'], errors='coerce', dayfirst=True)
                contests['End Date'] = pd.to_datetime(contests['End Date'], errors='coerce', dayfirst=True)
                
                # ============================================
                # CURRENT CONTESTS
                # ============================================
                st.header("📢 Current Contests")
                
                today = datetime.now().date()
                
                # Find current contests
                current = contests[
                    (contests['Start Date'].dt.date <= today) & 
                    (contests['End Date'].dt.date >= today)
                ]
                
                if not current.empty:
                    for _, row in current.iterrows():
                        st.markdown(f"""
                        **{row.get('Camp Name', 'N/A')}**
                        - Type: {row.get('Camp Type', 'N/A')}
                        - Ends: {row['End Date'].strftime('%d %b')}
                        - KAM: {row.get('KAM', 'N/A')}
                        ---
                        """)
                else:
                    st.info("No contests running today")
                
                # ============================================
                # UPCOMING CONTESTS
                # ============================================
                upcoming = contests[
                    (contests['Start Date'].dt.date > today) & 
                    (contests['Start Date'].dt.date <= (today + pd.Timedelta(days=7)))
                ]
                
                if not upcoming.empty:
                    st.header("📅 Starting Soon")
                    
                    for _, row in upcoming.iterrows():
                        st.markdown(f"""
                        **{row.get('Camp Name', 'N/A')}**
                        - Type: {row.get('Camp Type', 'N/A')}
                        - Starts: {row['Start Date'].strftime('%d %b')}
                        ---
                        """)
                
                # ============================================
                # ALL CONTESTS
                # ============================================
                with st.expander("📋 View All Contests"):
                    # Simple table
                    table_cols = ['Merch ID', 'Camp Name', 'Camp Type', 'Start Date', 'End Date', 'KAM']
                    table_cols = [col for col in table_cols if col in contests.columns]
                    
                    display_df = contests[table_cols].copy()
                    
                    # Format dates
                    if 'Start Date' in display_df.columns:
                        display_df['Start Date'] = display_df['Start Date'].dt.strftime('%d-%m-%Y')
                    if 'End Date' in display_df.columns:
                        display_df['End Date'] = display_df['End Date'].dt.strftime('%d-%m-%Y')
                    
                    st.dataframe(display_df, height=300)
                    
                    # Download
                    csv = display_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download All Contests",
                        csv,
                        "all_contests.csv",
                        "text/csv"
                    )
        
        # ============================================
        # LOAD WINNER DATA
        # ============================================
        # Try different possible sheet names
        winner_sheet_names = ['Winners Details ', 'Winner Details', 'Winners Details', 'Winner Details ']
        winner_sheet_found = None
        
        for sheet_name in winner_sheet_names:
            if sheet_name in sheet_names:
                winner_sheet_found = sheet_name
                break
        
        if winner_sheet_found:
            winner_ws = sheet.worksheet(winner_sheet_found)
            winner_data = winner_ws.get_all_records()
            winners = pd.DataFrame(winner_data)
            
            if not winners.empty:
                st.success(f"🏆 {len(winners)} winners loaded from '{winner_sheet_found}'")
                
                # ============================================
                # WINNER SEARCH
                # ============================================
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
                        st.success(f"✅ Found {len(results)} win(s)")
                        
                        # Show results
                        for _, row in results.iterrows():
                            st.markdown(f"""
                            **🎁 {row.get('Gift', 'N/A')}**
                            - Contest: {row.get('Contest', 'N/A')}
                            - Customer: {row.get('customer_firstname', 'N/A')}
                            - Phone: {row.get('customer_phonenumber', 'N/A')}
                            - Store: {row.get('business_displayname', 'N/A')}
                            ---
                            """)
                            
                        # Show all in table
                        with st.expander("📊 View All Matching Results"):
                            show_cols = ['businessid', 'customer_firstname', 'customer_phonenumber', 'Contest', 'Gift']
                            show_cols = [col for col in show_cols if col in results.columns]
                            st.dataframe(results[show_cols])
                    else:
                        st.warning("No wins found")
                        
        else:
            st.warning("Winner sheet not found. Looking for: 'Winners Details ', 'Winner Details', etc.")
            
    except Exception as e:
        st.error(f"Error: {str(e)}")
        
else:
    st.error("Connection failed")

# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%H:%M')}")

if st.button("🔄 Refresh"):
    st.rerun()
