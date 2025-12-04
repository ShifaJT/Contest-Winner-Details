import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# Google Sheets Setup
SHEET_NAMES = {
    'contest': 'Contest Details',  # Name of your Contest Details sheet
    'winner': 'Winner Details'     # Name of your Winner Details sheet
}

@st.cache_resource
def get_google_sheet_client():
    """Authenticate and return Google Sheets client"""
    # Upload your service account JSON file via Streamlit secrets or local file
    try:
        # Method 1: Using Streamlit secrets (Recommended for deployment)
        creds_dict = dict(st.secrets["google_sheets"])
    except:
        # Method 2: Using local JSON file
        import json
        with open('service_account.json', 'r') as f:
            creds_dict = json.load(f)
    
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(credentials)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_sheet_data(sheet_name, worksheet_name):
    """Load data from Google Sheets"""
    try:
        client = get_google_sheet_client()
        sheet = client.open(sheet_name)
        worksheet = sheet.worksheet(worksheet_name)
        df = get_as_dataframe(worksheet, evaluate_formulas=True)
        df = df.dropna(how='all')  # Remove empty rows
        return df
    except Exception as e:
        st.error(f"Error loading {worksheet_name}: {str(e)}")
        return pd.DataFrame()

# Streamlit App
st.set_page_config(
    page_title="Contest Dashboard",
    page_icon="🎯",
    layout="wide"
)

st.title("🎁 Live Contest & Winner Dashboard")
st.markdown("---")

# Configuration in sidebar
st.sidebar.header("🔧 Configuration")

# Google Sheet URL input
sheet_url = st.sidebar.text_input(
    "Google Sheet URL",
    placeholder="https://docs.google.com/spreadsheets/d/..."
)

# If URL provided, extract ID
if sheet_url:
    try:
        sheet_id = sheet_url.split('/d/')[1].split('/')[0]
        SHEET_ID = sheet_id
    except:
        st.sidebar.error("Invalid Google Sheet URL")
        SHEET_ID = None
else:
    # Or use sheet ID directly
    SHEET_ID = st.sidebar.text_input(
        "Google Sheet ID",
        placeholder="1ABC123..."
    )

if SHEET_ID:
    # Load data
    with st.spinner("Loading data from Google Sheets..."):
        contest_df = load_sheet_data(SHEET_ID, SHEET_NAMES['contest'])
        winner_df = load_sheet_data(SHEET_ID, SHEET_NAMES['winner'])
    
    if not contest_df.empty:
        # Clean and parse dates
        contest_df = contest_df.copy()
        winner_df = winner_df.copy()
        
        # Convert date columns (try multiple formats)
        date_columns_contest = ['Start Date', 'End Date', 'Winner Announcement Date']
        date_columns_winner = ['Start Date', 'End Date', 'Winner Announcement Date', 'Gift Sent Date']
        
        for col in date_columns_contest:
            if col in contest_df.columns:
                contest_df[col] = pd.to_datetime(contest_df[col], errors='coerce', dayfirst=True)
        
        for col in date_columns_winner:
            if col in winner_df.columns:
                winner_df[col] = pd.to_datetime(winner_df[col], errors='coerce', dayfirst=True)
        
        # --- MAIN APP ---
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.header("📅 Filter Contests")
            
            # Year filter
            contest_df['Year'] = contest_df['Start Date'].dt.year
            years = sorted(contest_df['Year'].dropna().unique().astype(int))
            
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
            start_date = st.date_input(
                "Start Date",
                value=contest_df['Start Date'].min().date()
            )
            end_date = st.date_input(
                "End Date",
                value=contest_df['Start Date'].max().date()
            )
            
            # Apply filters
            filtered_contest = contest_df.copy()
            
            # Date range filter
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
            
            # Display contest count
            st.metric("Contests Found", len(filtered_contest))
            
            # Quick stats
            if not filtered_contest.empty:
                st.subheader("📊 Quick Stats")
                camp_types = filtered_contest['Camp Type'].value_counts()
                for camp_type, count in camp_types.items():
                    st.caption(f"**{camp_type}**: {count}")
        
        with col2:
            st.header("🎯 Contest Details")
            
            if not filtered_contest.empty:
                # Display contests
                display_cols = ['Merch ID', 'Camp Name', 'Camp Type', 
                              'Start Date', 'End Date', 'Winner Announcement Date', 'KAM']
                
                display_df = filtered_contest[display_cols].copy()
                display_df['Start Date'] = display_df['Start Date'].dt.strftime('%d-%m-%Y')
                display_df['End Date'] = display_df['End Date'].dt.strftime('%d-%m-%Y')
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    height=400
                )
                
                # Download button for filtered contests
                csv = display_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Filtered Contests",
                    data=csv,
                    file_name=f"contests_{start_date}_to_{end_date}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No contests found for selected filters")
        
        st.markdown("---")
        
        # --- WINNER SEARCH SECTION ---
        st.header("🏆 Winner Search")
        
        search_col1, search_col2 = st.columns([1, 3])
        
        with search_col1:
            search_type = st.radio(
                "Search by",
                ["BZID (businessid)", "Customer Phone", "Customer Name", "Merch ID"]
            )
            
            if search_type == "BZID (businessid)":
                search_value = st.text_input("Enter BZID", key="bzid_search")
                if search_value:
                    results = winner_df[winner_df['businessid'] == search_value]
            
            elif search_type == "Customer Phone":
                search_value = st.text_input("Enter Phone Number", key="phone_search")
                if search_value:
                    results = winner_df[winner_df['customer_phonenumber'] == search_value]
            
            elif search_type == "Customer Name":
                search_value = st.text_input("Enter Customer Name", key="name_search")
                if search_value:
                    results = winner_df[
                        winner_df['customer_firstname'].str.contains(search_value, case=False, na=False)
                    ]
            
            else:  # Merch ID
                search_value = st.text_input("Enter Merch ID", key="merch_search")
                if search_value:
                    results = winner_df[winner_df['Merch ID'] == search_value]
        
        with search_col2:
            if 'search_value' in locals() and search_value:
                if not results.empty:
                    st.success(f"✅ Found {len(results)} record(s)")
                    
                    # Display summary
                    summary_cols = ['Merch ID', 'Contest', 'Gift', 
                                  'Winner Announcement Date', 'Gift Sent Date', 'customer_firstname']
                    summary_df = results[summary_cols].copy()
                    
                    # Format dates
                    for date_col in ['Winner Announcement Date', 'Gift Sent Date']:
                        if date_col in summary_df.columns:
                            summary_df[date_col] = summary_df[date_col].dt.strftime('%d-%m-%Y')
                    
                    st.dataframe(summary_df, use_container_width=True)
                    
                    # Expand for full details
                    with st.expander("📋 View Full Details"):
                        st.dataframe(results, use_container_width=True)
                    
                    # Download results
                    csv_results = results.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Winner Details",
                        data=csv_results,
                        file_name=f"winner_{search_value}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No records found")
            else:
                st.info("👈 Enter search criteria to find winners")
        
        # --- WINNERS IN DATE RANGE ---
        st.markdown("---")
        
        if st.checkbox("👥 Show all winners in selected contest date range"):
            st.header("🏅 Winners in Selected Period")
            
            # Get contest IDs in filtered range
            contest_ids = filtered_contest['Merch ID'].unique()
            winners_in_range = winner_df[winner_df['Merch ID'].isin(contest_ids)]
            
            if not winners_in_range.empty:
                st.metric("Total Winners", len(winners_in_range))
                
                # Group by gift type
                gift_counts = winners_in_range['Gift'].value_counts().head(10)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("🎁 Top 10 Gifts")
                    for gift, count in gift_counts.items():
                        st.write(f"**{gift}**: {count}")
                
                with col2:
                    st.subheader("📋 Winner List")
                    display_winners = winners_in_range[['Merch ID', 'businessid', 'Contest', 
                                                       'Gift', 'Winner Announcement Date']].copy()
                    display_winners['Winner Announcement Date'] = display_winners['Winner Announcement Date'].dt.strftime('%d-%m-%Y')
                    
                    st.dataframe(
                        display_winners,
                        use_container_width=True,
                        height=300
                    )
            else:
                st.info("No winners found in selected period")
        
        # --- DATA REFRESH ---
        st.markdown("---")
        if st.button("🔄 Refresh Data from Google Sheets"):
            st.cache_data.clear()
            st.rerun()
        
        # --- FOOTER ---
        st.caption(f"📊 Data loaded from Google Sheets | Last update: {datetime.now().strftime('%d-%m-%Y %H:%M')}")
        st.caption("ℹ️ Contact support for data issues")
        
    else:
        st.error("Could not load contest data. Check sheet name and permissions.")
else:
    st.info("👈 Please enter Google Sheet ID/URL in the sidebar to begin")
