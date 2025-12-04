import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ============================================
# CONFIGURATION
# ============================================
YOUR_SHEET_ID = "1E2qxc1kZttPQMmSXCVXFaQKVNLl_Nhe4uUPBrzf7B3U"

# ============================================
# GOOGLE SHEETS CONNECTION
# ============================================
@st.cache_resource
def connect_to_google_sheets():
    """Connect to Google Sheets"""
    try:
        # Load credentials from Streamlit secrets
        creds_dict = dict(st.secrets["google_sheets"])
        
        # Create credentials
        scopes = ['https://www.googleapis.com/auth/spreadsheets',
                 'https://www.googleapis.com/auth/drive']
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        
        # Test connection
        sheet = client.open_by_key(YOUR_SHEET_ID)
        st.sidebar.success("✅ Connected to Google Sheets")
        return client
        
    except Exception as e:
        st.error(f"❌ Connection failed: {str(e)[:100]}")
        return None

# ============================================
# LOAD DATA
# ============================================
@st.cache_data(ttl=300)
def load_sheet_data(client, sheet_name):
    """Load data from Google Sheets"""
    try:
        sheet = client.open_by_key(YOUR_SHEET_ID)
        worksheet = sheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        df = df.dropna(how='all')
        return df
    except Exception as e:
        st.error(f"Error loading '{sheet_name}': {str(e)}")
        return pd.DataFrame()

# ============================================
# MAIN APP
# ============================================
st.set_page_config(
    page_title="Contest Dashboard",
    page_icon="🎯",
    layout="wide"
)

st.title("🎁 Contest & Winner Dashboard")
st.markdown("---")

# Connect to Google Sheets
gsheets_client = connect_to_google_sheets()

if gsheets_client:
    # Load data
    with st.spinner("📥 Loading data from Google Sheets..."):
        contest_df = load_sheet_data(gsheets_client, 'Contest Details')
        winner_df = load_sheet_data(gsheets_client, 'Winner Details')
    
    # Check if data loaded
    if contest_df.empty:
        st.error("❌ Could not load 'Contest Details' sheet!")
        st.info("""
        **Make sure:**
        1. Sheet is named exactly: **Contest Details**
        2. Google Sheet is shared with: contest-dashboard@contest-details-dashboard.iam.gserviceaccount.com
        3. Permission is set to **Editor**
        """)
        st.stop()
    
    if winner_df.empty:
        st.warning("⚠️ Could not load 'Winner Details' sheet")
    else:
        st.sidebar.success(f"✅ Winner data loaded: {len(winner_df)} rows")
    
    # Process dates
    def process_dates(df, date_cols):
        df = df.copy()
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
        return df
    
    contest_df = process_dates(contest_df, ['Start Date', 'End Date', 'Winner Announcement Date'])
    
    if not winner_df.empty:
        winner_df = process_dates(winner_df, ['Start Date', 'End Date', 'Winner Announcement Date', 'Gift Sent Date'])
    
    st.sidebar.success(f"✅ Contest data loaded: {len(contest_df)} rows")
    
    # ============================================
    # CONTEST FILTERING
    # ============================================
    st.header("📅 Filter Contests")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Year filter
        contest_df['Year'] = contest_df['Start Date'].dt.year
        years = sorted([int(y) for y in contest_df['Year'].dropna().unique() if pd.notna(y)])
        
        selected_year = st.selectbox("Select Year", ["All Years"] + years)
        
        # Month filter
        months = ["All Months", "January", "February", "March", "April", "May", "June", 
                 "July", "August", "September", "October", "November", "December"]
        selected_month = st.selectbox("Select Month", months)
        
        # Date range
        min_date = contest_df['Start Date'].min().date()
        max_date = contest_df['Start Date'].max().date()
        
        start_date = st.date_input("From Date", min_date)
        end_date = st.date_input("To Date", max_date)
        
        # Apply filters
        filtered_contest = contest_df.copy()
        
        # Date filter
        filtered_contest = filtered_contest[
            (filtered_contest['Start Date'].dt.date >= start_date) & 
            (filtered_contest['End Date'].dt.date <= end_date)
        ]
        
        # Year filter
        if selected_year != "All Years":
            filtered_contest = filtered_contest[filtered_contest['Year'] == int(selected_year)]
        
        # Month filter
        if selected_month != "All Months":
            filtered_contest = filtered_contest[
                filtered_contest['Start Date'].dt.month_name() == selected_month
            ]
        
        st.metric("📊 Contests Found", len(filtered_contest))
        
        # Campaign type stats
        if not filtered_contest.empty and 'Camp Type' in filtered_contest.columns:
            st.subheader("Campaign Types")
            camp_types = filtered_contest['Camp Type'].value_counts()
            for camp_type, count in camp_types.items():
                st.write(f"**{camp_type}**: {count}")
    
    with col2:
        # Display contests
        if not filtered_contest.empty:
            display_cols = ['Merch ID', 'Camp Name', 'Camp Type', 'Start Date', 'End Date', 'Winner Announcement Date', 'KAM']
            display_cols = [col for col in display_cols if col in filtered_contest.columns]
            
            display_df = filtered_contest[display_cols].copy()
            
            # Format dates
            for date_col in ['Start Date', 'End Date', 'Winner Announcement Date']:
                if date_col in display_df.columns:
                    display_df[date_col] = display_df[date_col].dt.strftime('%d-%m-%Y')
            
            st.dataframe(display_df, use_container_width=True, height=400)
            
            # Download button
            csv_data = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Contests",
                csv_data,
                f"contests_{start_date}_to_{end_date}.csv",
                "text/csv"
            )
        else:
            st.info("No contests found for selected filters")
    
    st.markdown("---")
    
    # ============================================
    # WINNER SEARCH
    # ============================================
    st.header("🏆 Search Winners")
    
    if not winner_df.empty:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            search_type = st.radio("Search by:", ["BZID", "Phone", "Name", "Merch ID"])
            
            if search_type == "BZID":
                search_input = st.text_input("Enter BZID", key="bzid")
                column = 'businessid'
            elif search_type == "Phone":
                search_input = st.text_input("Enter Phone", key="phone")
                column = 'customer_phonenumber'
            elif search_type == "Name":
                search_input = st.text_input("Enter Name", key="name")
                column = 'customer_firstname'
            else:
                search_input = st.text_input("Enter Merch ID", key="merch")
                column = 'Merch ID'
        
        with col2:
            if search_input and column in winner_df.columns:
                # Search
                winner_df[column] = winner_df[column].astype(str)
                results = winner_df[winner_df[column].str.contains(search_input, case=False, na=False)]
                
                if not results.empty:
                    st.success(f"✅ Found {len(results)} record(s)")
                    
                    # Show summary
                    summary_cols = ['Merch ID', 'Contest', 'Gift', 'Winner Announcement Date', 'customer_firstname']
                    summary_cols = [col for col in summary_cols if col in results.columns]
                    
                    summary_df = results[summary_cols].copy()
                    
                    # Format dates
                    if 'Winner Announcement Date' in summary_df.columns:
                        summary_df['Winner Announcement Date'] = summary_df['Winner Announcement Date'].dt.strftime('%d-%m-%Y')
                    
                    st.dataframe(summary_df, use_container_width=True)
                    
                    # Download
                    csv_results = results.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download Results",
                        csv_results,
                        f"winners_{search_input}.csv",
                        "text/csv"
                    )
                else:
                    st.warning("No results found")
            else:
                st.info("👈 Enter search criteria to find winners")
    else:
        st.warning("Winner data not available")
    
    # ============================================
    # WINNERS IN PERIOD
    # ============================================
    if st.checkbox("Show winners in selected contest period"):
        st.header("🏅 Winners in Selected Period")
        
        if not winner_df.empty and 'Merch ID' in winner_df.columns:
            contest_ids = filtered_contest['Merch ID'].unique()
            winners_in_period = winner_df[winner_df['Merch ID'].isin(contest_ids)]
            
            if not winners_in_period.empty:
                st.metric("Total Winners", len(winners_in_period))
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'Gift' in winners_in_period.columns:
                        st.subheader("🎁 Top Gifts")
                        gift_counts = winners_in_period['Gift'].value_counts().head(10)
                        for gift, count in gift_counts.items():
                            st.write(f"**{gift}**: {count}")
                
                with col2:
                    st.subheader("📋 Winner List")
                    display_cols = ['Merch ID', 'businessid', 'Contest', 'Gift', 'Winner Announcement Date']
                    display_cols = [col for col in display_cols if col in winners_in_period.columns]
                    
                    if display_cols:
                        display_df = winners_in_period[display_cols].copy()
                        
                        if 'Winner Announcement Date' in display_df.columns:
                            display_df['Winner Announcement Date'] = display_df['Winner Announcement Date'].dt.strftime('%d-%m-%Y')
                        
                        st.dataframe(display_df, use_container_width=True, height=300)
            else:
                st.info("No winners found in selected period")
    
    # ============================================
    # FOOTER
    # ============================================
    st.markdown("---")
    
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    st.caption(f"📅 Last updated: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
    
else:
    st.error("""
    ❌ **Cannot connect to Google Sheets!**
    
    **Please make sure:**
    1. You have created `.streamlit/secrets.toml` with your credentials
    2. Google Sheet is shared with: **contest-dashboard@contest-details-dashboard.iam.gserviceaccount.com**
    3. Permission is set to **Editor**
    4. Refresh the app after sharing
    """)

# Sidebar info
st.sidebar.markdown("---")
st.sidebar.info("**Connected to:**\n`1E2qxc1kZttPQMmSXCVXFaQKVNLl_Nhe4uUPBrzf7B3U`")
