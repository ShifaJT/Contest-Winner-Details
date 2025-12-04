import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ============================================
# SIMPLE CONNECTION
# ============================================
def connect_google_sheets():
    try:
        # Get secrets
        secrets = st.secrets["google_sheets"]
        
        # Create credentials
        creds_dict = {
            "type": secrets["type"],
            "project_id": secrets["project_id"],
            "private_key_id": secrets["private_key_id"],
            "private_key": secrets["private_key"],
            "client_email": secrets["client_email"],
            "client_id": secrets["client_id"],
            "auth_uri": secrets["auth_uri"],
            "token_uri": secrets["token_uri"],
            "auth_provider_x509_cert_url": secrets["auth_provider_x509_cert_url"],
            "client_x509_cert_url": secrets["client_x509_cert_url"],
            "universe_domain": secrets["universe_domain"]
        }
        
        # Authorize
        scopes = ['https://www.googleapis.com/auth/spreadsheets']
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        
        return client
        
    except Exception as e:
        st.error(f"Connection error: {str(e)[:100]}")
        return None

# ============================================
# SIMPLE APP
# ============================================
st.set_page_config(page_title="Contest Checker", layout="centered")
st.title("🎯 Contest Checker")
st.markdown("---")

# Connect
client = connect_google_sheets()

if not client:
    st.error("❌ Cannot connect. Check secrets and sharing.")
    st.stop()

try:
    # Open sheet
    sheet = client.open_by_key("1E2qxc1kZttPQMmSXCVXFaQKVNLl_Nhe4uUPBrzf7B3U")
    st.success("✅ Connected to Google Sheets")
    
    # Load Contest Details
    try:
        contest_ws = sheet.worksheet("Contest Details")
        contest_data = contest_ws.get_all_records()
        contests = pd.DataFrame(contest_data)
        st.info(f"📋 Loaded {len(contests)} contests")
    except:
        st.error("❌ 'Contest Details' sheet not found!")
        contests = pd.DataFrame()
    
    # Load Winner Details
    try:
        winner_ws = sheet.worksheet("Winner Details")
        winner_data = winner_ws.get_all_records()
        winners = pd.DataFrame(winner_data)
        st.info(f"🏆 Loaded {len(winners)} winners")
    except:
        st.warning("⚠️ 'Winner Details' sheet not found")
        winners = pd.DataFrame()
    
    # ============================================
    # CURRENT CONTESTS
    # ============================================
    if not contests.empty:
        st.header("📢 Current Contests")
        
        # Fix dates
        contests['Start Date'] = pd.to_datetime(contests['Start Date'], errors='coerce', dayfirst=True)
        contests['End Date'] = pd.to_datetime(contests['End Date'], errors='coerce', dayfirst=True)
        
        today = datetime.now().date()
        
        # Find current contests
        current = contests[
            (contests['Start Date'].dt.date <= today) & 
            (contests['End Date'].dt.date >= today)
        ].copy()
        
        if not current.empty:
            current['End Date'] = current['End Date'].dt.strftime('%d %b')
            
            for _, row in current.iterrows():
                st.markdown(f"""
                **{row.get('Camp Name', 'N/A')}**
                - Type: {row.get('Camp Type', 'N/A')}
                - Ends: {row['End Date']}
                - KAM: {row.get('KAM', 'N/A')}
                ---
                """)
        else:
            st.info("No contests running today")
        
        # ============================================
        # UPCOMING CONTESTS (Next 7 days)
        # ============================================
        upcoming = contests[
            (contests['Start Date'].dt.date > today) & 
            (contests['Start Date'].dt.date <= (today + pd.Timedelta(days=7)))
        ].copy()
        
        if not upcoming.empty:
            st.header("📅 Starting Soon")
            upcoming['Start Date'] = upcoming['Start Date'].dt.strftime('%d %b')
            
            for _, row in upcoming.iterrows():
                st.markdown(f"""
                **{row.get('Camp Name', 'N/A')}**
                - Type: {row.get('Camp Type', 'N/A')}
                - Starts: {row['Start Date']}
                ---
                """)
    
    # ============================================
    # WINNER SEARCH
    # ============================================
    if not winners.empty:
        st.header("🏆 Check Winner")
        
        search_option = st.radio("Search by:", ["BZID", "Phone", "Name"], horizontal=True)
        
        if search_option == "BZID":
            search_input = st.text_input("Enter BZID")
            column = 'businessid'
        elif search_option == "Phone":
            search_input = st.text_input("Enter Phone Number")
            column = 'customer_phonenumber'
        else:
            search_input = st.text_input("Enter Customer Name")
            column = 'customer_firstname'
        
        if search_input and column in winners.columns:
            # Clean the column for searching
            winners[column] = winners[column].astype(str).fillna('')
            
            # Search
            results = winners[winners[column].str.contains(search_input, case=False, na=False)]
            
            if not results.empty:
                st.success(f"✅ Found {len(results)} win(s)")
                
                for _, row in results.iterrows():
                    st.markdown(f"""
                    **🎁 {row.get('Gift', 'N/A')}**
                    - Contest: {row.get('Contest', 'N/A')}
                    - Customer: {row.get('customer_firstname', 'N/A')}
                    - Phone: {row.get('customer_phonenumber', 'N/A')}
                    - Store: {row.get('business_displayname', 'N/A')}
                    ---
                    """)
            else:
                st.warning("No wins found for this search")
    
    # ============================================
    # ALL CONTESTS TABLE
    # ============================================
    if not contests.empty:
        with st.expander("📋 View All Contests"):
            # Simple table
            table_cols = ['Camp Name', 'Camp Type', 'Start Date', 'End Date', 'KAM']
            table_cols = [col for col in table_cols if col in contests.columns]
            
            display_df = contests[table_cols].copy()
            
            # Format dates
            if 'Start Date' in display_df.columns:
                display_df['Start Date'] = display_df['Start Date'].dt.strftime('%d-%m-%Y')
            if 'End Date' in display_df.columns:
                display_df['End Date'] = display_df['End Date'].dt.strftime('%d-%m-%Y')
            
            st.dataframe(display_df, height=300)
            
            # Download button
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download All Contests",
                csv,
                "all_contests.csv",
                "text/csv"
            )
    
except Exception as e:
    st.error(f"Error: {str(e)}")
    st.info("""
    **Common fixes:**
    1. Share sheet with: contest-fresh-dashboard@contest-details-dashboard.iam.gserviceaccount.com
    2. Wait 1 minute after sharing
    3. Refresh this page
    """)

# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.caption(f"Last check: {datetime.now().strftime('%d %b %H:%M')}")

if st.button("🔄 Refresh Data"):
    st.rerun()
