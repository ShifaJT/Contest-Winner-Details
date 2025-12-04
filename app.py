import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ============================================
# CONFIGURATION - SET YOUR GOOGLE SHEET ID HERE
# ============================================
YOUR_SHEET_ID = "1E2qxc1kZttPQMmSXCVXFaQKVNLl_Nhe4uUPBrzf7B3U"

# ============================================
# GOOGLE SHEETS CONNECTION
# ============================================
@st.cache_resource
def connect_to_google_sheets():
    """Connect to Google Sheets using service_account.json"""
    try:
        # Load credentials from service_account.json file
        credentials = Credentials.from_service_account_file(
            'service_account.json',
            scopes=['https://www.googleapis.com/auth/spreadsheets',
                   'https://www.googleapis.com/auth/drive']
        )
        
        # Create Google Sheets client
        client = gspread.authorize(credentials)
        
        # Test the connection
        test_sheet = client.open_by_key(YOUR_SHEET_ID)
        sheet_title = test_sheet.title
        
        st.sidebar.success("✅ Connected to Google Sheets")
        st.sidebar.info(f"Sheet: {sheet_title}")
        return client
        
    except FileNotFoundError:
        st.error("❌ ERROR: 'service_account.json' file not found!")
        st.info("""
        Please make sure:
        1. You have downloaded the JSON file from Google Cloud Console
        2. It's named exactly: service_account.json
        3. It's in the same folder as app.py
        """)
        return None
    except Exception as e:
        st.error(f"❌ Connection failed: {str(e)}")
        st.info("""
        Common issues:
        1. Service account doesn't have access to the sheet
        2. Google Sheets API not enabled
        3. Invalid credentials
        """)
        return None

# ============================================
# LOAD DATA FROM GOOGLE SHEETS
# ============================================
@st.cache_data(ttl=300)
def load_google_sheet_data(client, sheet_name):
    """Load data from a specific sheet"""
    try:
        # Open the sheet
        sheet = client.open_by_key(YOUR_SHEET_ID)
        
        # Get the worksheet
        worksheet = sheet.worksheet(sheet_name)
        
        # Get all values
        data = worksheet.get_all_records()
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        return df
        
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"❌ Sheet '{sheet_name}' not found!")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error loading '{sheet_name}': {str(e)}")
        return pd.DataFrame()

# ============================================
# PROCESS DATE COLUMNS
# ============================================
def process_dates(df, date_columns):
    """Convert date columns to datetime format"""
    df = df.copy()
    for col in date_columns:
        if col in df.columns:
            # Try multiple date formats
            df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
    return df

# ============================================
# STREAMLIT APP STARTS HERE
# ============================================
st.set_page_config(
    page_title="Contest & Winner Dashboard",
    page_icon="🎯",
    layout="wide"
)

st.title("🎁 Contest & Winner Dashboard")
st.markdown("---")

# Display connection instructions at the top
st.info("""
**Make sure:** 
1. Your `service_account.json` file is in the same folder as this app
2. Google Sheet is shared with the service account email
3. Sheets are named: **'Contest Details'** and **'Winner Details'**
""")

# Connect to Google Sheets
gsheets_client = connect_to_google_sheets()

if gsheets_client:
    # Show available sheets in sidebar
    try:
        sheet = gsheets_client.open_by_key(YOUR_SHEET_ID)
        all_sheets = [ws.title for ws in sheet.worksheets()]
        
        st.sidebar.header("📋 Available Sheets")
        for sheet_name in all_sheets:
            st.sidebar.text(f"• {sheet_name}")
    except:
        pass
    
    # Load data
    with st.spinner("Loading data from Google Sheets..."):
        contest_df = load_google_sheet_data(gsheets_client, 'Contest Details')
        winner_df = load_google_sheet_data(gsheets_client, 'Winner Details')
    
    # Check if data was loaded successfully
    if contest_df.empty:
        st.error("❌ Could not load Contest Details sheet!")
        st.stop()
    
    if winner_df.empty:
        st.warning("⚠️ Could not load Winner Details sheet. Some features may not work.")
    
    # Process contest dates
    contest_date_columns = ['Start Date', 'End Date', 'Winner Announcement Date']
    contest_df = process_dates(contest_df, contest_date_columns)
    
    # Process winner dates if available
    if not winner_df.empty:
        winner_date_columns = ['Start Date', 'End Date', 'Winner Announcement Date', 'Gift Sent Date']
        winner_df = process_dates(winner_df, winner_date_columns)
    
    # ============================================
    # TAB 1: CONTEST FILTERING
    # ============================================
    st.header("📅 Filter Contests by Date")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Filters")
        
        # Year filter
        if 'Start Date' in contest_df.columns:
            contest_df['Year'] = contest_df['Start Date'].dt.year
            years = sorted([int(y) for y in contest_df['Year'].dropna().unique() if pd.notna(y)])
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
        st.subheader("Date Range")
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
        
        # Display stats
        st.metric("📊 Contests Found", len(filtered_contest))
        
        # Campaign type stats
        if not filtered_contest.empty and 'Camp Type' in filtered_contest.columns:
            st.subheader("Campaign Types")
            camp_types = filtered_contest['Camp Type'].value_counts()
            for camp_type, count in camp_types.items():
                st.text(f"• {camp_type}: {count}")
    
    with col2:
        st.subheader("Contest Details")
        
        if not filtered_contest.empty:
            # Select columns to display
            display_columns = []
            possible_columns = ['Merch ID', 'Camp Name', 'Camp Type', 'Start Date', 'End Date', 'Winner Announcement Date', 'KAM']
            
            for col in possible_columns:
                if col in filtered_contest.columns:
                    display_columns.append(col)
            
            # Create display dataframe
            display_df = filtered_contest[display_columns].copy()
            
            # Format dates for display
            for date_col in ['Start Date', 'End Date', 'Winner Announcement Date']:
                if date_col in display_df.columns:
                    display_df[date_col] = display_df[date_col].dt.strftime('%d-%m-%Y')
            
            # Display the dataframe
            st.dataframe(
                display_df,
                use_container_width=True,
                height=400
            )
            
            # Download button
            csv_data = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Contests",
                data=csv_data,
                file_name=f"contests_{start_date}_to_{end_date}.csv",
                mime="text/csv"
            )
        else:
            st.info("No contests found for the selected filters")
    
    st.markdown("---")
    
    # ============================================
    # TAB 2: WINNER SEARCH
    # ============================================
    st.header("🏆 Search Winners")
    
    if not winner_df.empty:
        search_col1, search_col2 = st.columns([1, 3])
        
        with search_col1:
            st.subheader("Search Options")
            
            search_type = st.radio(
                "Search by:",
                ["BZID", "Phone", "Name", "Merch ID"],
                index=0
            )
            
            if search_type == "BZID":
                search_input = st.text_input("Enter BZID (businessid)")
                column_to_search = 'businessid'
            elif search_type == "Phone":
                search_input = st.text_input("Enter Phone Number")
                column_to_search = 'customer_phonenumber'
            elif search_type == "Name":
                search_input = st.text_input("Enter Customer Name")
                column_to_search = 'customer_firstname'
            else:  # Merch ID
                search_input = st.text_input("Enter Merch ID")
                column_to_search = 'Merch ID'
        
        with search_col2:
            st.subheader("Search Results")
            
            if search_input and column_to_search in winner_df.columns:
                # Search for the value
                if column_to_search in winner_df.columns:
                    # Convert to string for searching
                    winner_df[column_to_search] = winner_df[column_to_search].astype(str)
                    results = winner_df[winner_df[column_to_search].str.contains(search_input, case=False, na=False)]
                else:
                    results = pd.DataFrame()
                
                if not results.empty:
                    st.success(f"✅ Found {len(results)} record(s)")
                    
                    # Display summary
                    summary_columns = []
                    possible_summary_cols = ['Merch ID', 'Contest', 'Gift', 'Winner Announcement Date', 'customer_firstname']
                    
                    for col in possible_summary_cols:
                        if col in results.columns:
                            summary_columns.append(col)
                    
                    if summary_columns:
                        summary_df = results[summary_columns].copy()
                        
                        # Format dates
                        if 'Winner Announcement Date' in summary_df.columns:
                            summary_df['Winner Announcement Date'] = summary_df['Winner Announcement Date'].dt.strftime('%d-%m-%Y')
                        
                        st.dataframe(summary_df, use_container_width=True)
                        
                        # Show full details in expander
                        with st.expander("View Full Details"):
                            st.dataframe(results, use_container_width=True)
                        
                        # Download button
                        csv_results = results.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download Results",
                            data=csv_results,
                            file_name=f"winners_{search_input}.csv",
                            mime="text/csv"
                        )
                else:
                    st.warning("No records found for your search")
            else:
                st.info("👈 Enter search criteria to find winners")
    else:
        st.warning("Winner data not available. Could not load Winner Details sheet.")
    
    st.markdown("---")
    
    # ============================================
    # TAB 3: WINNERS IN SELECTED PERIOD
    # ============================================
    if st.checkbox("Show winners in selected contest period"):
        st.header("🏅 Winners in Selected Period")
        
        if not winner_df.empty and 'Merch ID' in winner_df.columns and 'Merch ID' in filtered_contest.columns:
            # Get contest IDs from filtered contests
            contest_ids = filtered_contest['Merch ID'].unique()
            
            # Filter winners by these contest IDs
            winners_in_period = winner_df[winner_df['Merch ID'].isin(contest_ids)]
            
            if not winners_in_period.empty:
                st.metric("Total Winners in Period", len(winners_in_period))
                
                # Show gift distribution
                if 'Gift' in winners_in_period.columns:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("🎁 Gift Distribution")
                        gift_counts = winners_in_period['Gift'].value_counts()
                        for gift, count in gift_counts.head(10).items():
                            st.text(f"• {gift}: {count}")
                    
                    with col2:
                        st.subheader("📋 Winner List")
                        
                        # Select columns to display
                        winner_display_cols = []
                        possible_winner_cols = ['Merch ID', 'businessid', 'Contest', 'Gift', 'Winner Announcement Date']
                        
                        for col in possible_winner_cols:
                            if col in winners_in_period.columns:
                                winner_display_cols.append(col)
                        
                        if winner_display_cols:
                            winner_display_df = winners_in_period[winner_display_cols].copy()
                            
                            # Format dates
                            if 'Winner Announcement Date' in winner_display_df.columns:
                                winner_display_df['Winner Announcement Date'] = winner_display_df['Winner Announcement Date'].dt.strftime('%d-%m-%Y')
                            
                            st.dataframe(
                                winner_display_df,
                                use_container_width=True,
                                height=300
                            )
            else:
                st.info("No winners found in the selected period")
    
    # ============================================
    # FOOTER
    # ============================================
    st.markdown("---")
    
    # Refresh button
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    # Footer info
    st.caption(f"📅 Data loaded: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
    st.caption(f"📊 Total contests: {len(contest_df)} | Total winners: {len(winner_df) if not winner_df.empty else 'N/A'}")
    
else:
    # Show setup instructions if not connected
    st.error("""
    ❌ **SETUP REQUIRED:**
    
    **Step 1: Get service_account.json**
    1. Go to [Google Cloud Console](https://console.cloud.google.com/)
    2. Create a new project
    3. Enable "Google Sheets API" and "Google Drive API"
    4. Go to "Service Accounts" → Create new service account
    5. Download JSON key file
    
    **Step 2: Save the file**
    1. Rename downloaded file to `service_account.json`
    2. Place it in the same folder as `app.py`
    
    **Step 3: Share your Google Sheet**
    1. Open your sheet: https://docs.google.com/spreadsheets/d/1E2qxc1kZttPQMmSXCVXFaQKVNLl_Nhe4uUPBrzf7B3U/edit
    2. Click "Share"
    3. Add the service account email (from the JSON file)
    4. Set permission to "Editor"
    
    **Step 4: Refresh this page**
    """)

# ============================================
# SIDEBAR HELP SECTION
# ============================================
with st.sidebar:
    st.markdown("---")
    st.header("❓ Help")
    
    with st.expander("Troubleshooting"):
        st.markdown("""
        **Common Issues:**
        
        **1. "service_account.json not found"**
        • Make sure file is in same folder as app.py
        • Check file name is exactly: service_account.json
        
        **2. "Permission denied"**
        • Share Google Sheet with service account email
        • Grant "Editor" permission
        
        **3. "Sheet not found"**
        • Check sheet names: 'Contest Details' and 'Winner Details'
        • Names must match exactly
        
        **4. Date issues**
        • Make sure dates are in dd-mm-yyyy format
        """)
    
    with st.expander("How to use"):
        st.markdown("""
        **1. Filter Contests**
        • Select year/month or date range
        • View contest details
        
        **2. Search Winners**
        • Search by BZID, Phone, Name, or Merch ID
        • View gift details
        
        **3. Download Data**
        • Use download buttons to export CSV
        """)
