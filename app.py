import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe
import json
import os

# ============================================
# CONFIGURATION
# ============================================

# Your Google Sheet ID
YOUR_SHEET_ID = "1E2qxc1kZttPQMmSXCVXFaQKVNLl_Nhe4uUPBrzf7B3U"

# Sheet names (check exact names in your Google Sheet)
SHEET_NAMES = {
    'contest': 'Contest Details',
    'winner': 'Winner Details'
}

@st.cache_resource
def get_google_sheet_client():
    """Authenticate and return Google Sheets client"""
    try:
        # Try to load from Streamlit secrets (for deployment)
        try:
            creds_dict = dict(st.secrets["google_sheets"])
            st.sidebar.success("Using Streamlit secrets")
        except:
            # Try to load from service_account.json file
            try:
                with open('service_account.json', 'r') as f:
                    creds_dict = json.load(f)
                st.sidebar.success("Using service_account.json file")
            except FileNotFoundError:
                st.sidebar.error("No credentials found")
                st.sidebar.info("""
                **Please add credentials:**
                1. Download service account JSON from Google Cloud
                2. Save as `service_account.json` in same folder
                3. Or add to Streamlit secrets for deployment
                """)
                return None
        
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        return client
        
    except Exception as e:
        st.sidebar.error(f"Auth error: {str(e)[:100]}")
        return None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_sheet_data(client, worksheet_name):
    """Load data from Google Sheets"""
    try:
        sheet = client.open_by_key(YOUR_SHEET_ID)
        
        # Try to find worksheet by name
        try:
            worksheet = sheet.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            # List available worksheets
            all_worksheets = sheet.worksheets()
            available_names = [ws.title for ws in all_worksheets]
            st.error(f"Worksheet '{worksheet_name}' not found.")
            st.info(f"Available sheets: {', '.join(available_names)}")
            return pd.DataFrame()
        
        df = get_as_dataframe(worksheet, evaluate_formulas=True, header=0)
        df = df.dropna(how='all')  # Remove empty rows
        return df
        
    except Exception as e:
        st.error(f"Error loading {worksheet_name}: {str(e)}")
        return pd.DataFrame()

# ============================================
# STREAMLIT APP
# ============================================

st.set_page_config(
    page_title="Contest Dashboard",
    page_icon="🎯",
    layout="wide"
)

st.title("🎁 Live Contest & Winner Dashboard")
st.markdown("---")

# Sidebar with instructions
with st.sidebar:
    st.header("🔧 Setup Instructions")
    
    with st.expander("Click for setup help", expanded=True):
        st.markdown("""
        ### 📋 **To get this working:**
        
        1. **Create Service Account:**
           - Go to [Google Cloud Console](https://console.cloud.google.com/)
           - Create project → Enable Sheets API
           - IAM & Admin → Service Accounts
           - Create new → Download JSON
        
        2. **Share Google Sheet:**
           - Open your sheet
           - Click Share
           - Add service account email
           - Set as Editor
        
        3. **Add credentials:**
           - Save JSON as `service_account.json`
           - Place in same folder as this app
        """)
    
    st.markdown("---")
    st.header("📊 Connection Status")

# Initialize Google Sheets client
client = get_google_sheet_client()

if client:
    st.sidebar.success("✅ Connected to Google Sheets API")
    
    # Load data
    with st.spinner("Loading data from Google Sheets..."):
        contest_df = load_sheet_data(client, SHEET_NAMES['contest'])
        winner_df = load_sheet_data(client, SHEET_NAMES['winner'])
    
    # Check if data was loaded
    if not contest_df.empty and not winner_df.empty:
        st.sidebar.success(f"✅ Contest data: {len(contest_df)} rows")
        st.sidebar.success(f"✅ Winner data: {len(winner_df)} rows")
        
        # Show available columns
        with st.sidebar.expander("View data columns"):
            st.write("**Contest columns:**", list(contest_df.columns))
            st.write("**Winner columns:**", list(winner_df.columns))
        
        # Process contest data
        contest_df = contest_df.copy()
        date_columns_contest = ['Start Date', 'End Date', 'Winner Announcement Date']
        
        for col in date_columns_contest:
            if col in contest_df.columns:
                # Convert dates - try multiple formats
                contest_df[col] = pd.to_datetime(
                    contest_df[col], 
                    errors='coerce', 
                    dayfirst=True,
                    format='mixed'
                )
        
        # Process winner data
        winner_df = winner_df.copy()
        date_columns_winner = ['Start Date', 'End Date', 'Winner Announcement Date', 'Gift Sent Date']
        
        for col in date_columns_winner:
            if col in winner_df.columns:
                winner_df[col] = pd.to_datetime(
                    winner_df[col], 
                    errors='coerce', 
                    dayfirst=True,
                    format='mixed'
                )
        
        # --- FILTER CONTESTS SECTION ---
        st.header("📅 Filter Contests by Date")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Year filter
            if 'Start Date' in contest_df.columns:
                contest_df['Year'] = contest_df['Start Date'].dt.year
                years = sorted([int(y) for y in contest_df['Year'].dropna().unique() if not pd.isna(y)])
            else:
                years = []
            
            selected_year = st.selectbox(
                "Select Year",
                ["All Years"] + years,
                index=0
            )
            
            # Month filter
            months = ["All Months", "January", "February", "March", "April", "May", "June", 
                     "July", "August", "September", "October", "November", "December"]
            selected_month = st.selectbox("Select Month", months, index=0)
            
            # Date range filter
            st.subheader("Custom Date Range")
            if 'Start Date' in contest_df.columns and contest_df['Start Date'].notna().any():
                min_date = contest_df['Start Date'].min()
                max_date = contest_df['Start Date'].max()
                if pd.isna(min_date):
                    min_date = pd.Timestamp('2018-01-01')
                if pd.isna(max_date):
                    max_date = pd.Timestamp.today()
            else:
                min_date = pd.Timestamp('2018-01-01')
                max_date = pd.Timestamp.today()
            
            start_date = st.date_input("From Date", value=min_date.date())
            end_date = st.date_input("To Date", value=max_date.date())
            
            # Apply filters
            filtered_contest = contest_df.copy()
            
            # Date range filter
            if 'Start Date' in filtered_contest.columns:
                filtered_contest = filtered_contest[
                    (filtered_contest['Start Date'].dt.date >= start_date) & 
                    (filtered_contest['End Date'].dt.date <= end_date)
                ]
            
            # Year filter
            if selected_year != "All Years" and 'Year' in filtered_contest.columns:
                filtered_contest = filtered_contest[filtered_contest['Year'] == int(selected_year)]
            
            # Month filter
            if selected_month != "All Months" and 'Start Date' in filtered_contest.columns:
                filtered_contest = filtered_contest[
                    filtered_contest['Start Date'].dt.month_name() == selected_month
                ]
            
            st.metric("📊 Contests Found", len(filtered_contest))
            
            if not filtered_contest.empty and 'Camp Type' in filtered_contest.columns:
                st.subheader("Campaign Types")
                camp_types = filtered_contest['Camp Type'].value_counts()
                for camp_type, count in camp_types.head(5).items():
                    st.caption(f"**{camp_type}**: {count}")
        
        with col2:
            st.header("🎯 Contest List")
            
            if not filtered_contest.empty:
                # Display contests
                display_cols = []
                for col in ['Merch ID', 'Camp Name', 'Camp Type', 'Start Date', 'End Date', 'Winner Announcement Date', 'KAM']:
                    if col in filtered_contest.columns:
                        display_cols.append(col)
                
                display_df = filtered_contest[display_cols].copy()
                
                # Format dates for display
                for date_col in ['Start Date', 'End Date', 'Winner Announcement Date']:
                    if date_col in display_df.columns:
                        display_df[date_col] = display_df[date_col].dt.strftime('%d-%m-%Y')
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    height=400
                )
                
                # Download button
                csv = display_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Contests",
                    data=csv,
                    file_name=f"contests_{start_date}_to_{end_date}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No contests found for selected filters")
        
        st.markdown("---")
        
        # --- WINNER SEARCH SECTION ---
        st.header("🏆 Search Winners")
        
        search_col1, search_col2 = st.columns([1, 3])
        
        with search_col1:
            search_type = st.radio(
                "Search by:",
                ["BZID (businessid)", "Customer Phone", "Customer Name", "Merch ID"]
            )
            
            search_value = st.text_input("Enter search value", key="search_input")
        
        with search_col2:
            if search_value:
                if search_type == "BZID (businessid)" and 'businessid' in winner_df.columns:
                    results = winner_df[winner_df['businessid'].astype(str).str.contains(str(search_value), case=False, na=False)]
                elif search_type == "Customer Phone" and 'customer_phonenumber' in winner_df.columns:
                    results = winner_df[winner_df['customer_phonenumber'].astype(str).str.contains(str(search_value), case=False, na=False)]
                elif search_type == "Customer Name" and 'customer_firstname' in winner_df.columns:
                    results = winner_df[winner_df['customer_firstname'].astype(str).str.contains(str(search_value), case=False, na=False)]
                elif search_type == "Merch ID" and 'Merch ID' in winner_df.columns:
                    results = winner_df[winner_df['Merch ID'].astype(str).str.contains(str(search_value), case=False, na=False)]
                else:
                    results = pd.DataFrame()
                
                if not results.empty:
                    st.success(f"✅ Found {len(results)} record(s)")
                    
                    # Show summary
                    summary_cols = []
                    for col in ['Merch ID', 'Contest', 'Gift', 'Winner Announcement Date', 'customer_firstname']:
                        if col in results.columns:
                            summary_cols.append(col)
                    
                    if summary_cols:
                        summary_df = results[summary_cols].copy()
                        if 'Winner Announcement Date' in summary_df.columns:
                            summary_df['Winner Announcement Date'] = summary_df['Winner Announcement Date'].dt.strftime('%d-%m-%Y')
                        
                        st.dataframe(summary_df, use_container_width=True)
                        
                        # Full details
                        with st.expander("View Full Details"):
                            st.dataframe(results, use_container_width=True)
                        
                        # Download
                        csv_data = results.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download Results",
                            data=csv_data,
                            file_name=f"winners_search_{search_value}.csv",
                            mime="text/csv"
                        )
                else:
                    st.warning("No records found")
            else:
                st.info("Enter search value to find winners")
        
        # --- REFRESH BUTTON ---
        st.markdown("---")
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
        
        # --- FOOTER ---
        st.caption(f"📅 Data loaded: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
        
    else:
        st.error("Could not load data from Google Sheets")
        st.info("""
        **Possible issues:**
        1. Sheet names don't match: Should be 'Contest Details' and 'Winner Details'
        2. Service account doesn't have access to the sheet
        3. Sheets are empty or have different structure
        """)
        
else:
    st.warning("Waiting for Google Sheets credentials...")
    st.info("""
    **Quick setup:**
    
    1. Download service account JSON from Google Cloud Console
    2. Save it as `service_account.json` in the same folder
    3. Share your Google Sheet with the service account email
    4. Refresh this page
    
    **OR** paste your credentials directly in the code (not recommended for production)
    """)

# Requirements file
st.sidebar.markdown("---")
st.sidebar.caption("Requirements: streamlit, pandas, gspread")
