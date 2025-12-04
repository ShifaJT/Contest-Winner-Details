import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json

# ============================================
# CONFIGURATION
# ============================================
YOUR_SHEET_ID = "1E2qxc1kZttPQMmSXCVXFaQKVNLl_Nhe4uUPBrzf7B3U"

# ============================================
# GOOGLE SHEETS CONNECTION FOR STREAMLIT CLOUD
# ============================================
@st.cache_resource
def connect_to_google_sheets():
    """Connect to Google Sheets - works for both local and Streamlit Cloud"""
    try:
        # For Streamlit Cloud: Use secrets.toml
        try:
            # Check if we're on Streamlit Cloud (has secrets)
            creds_dict = dict(st.secrets["google_sheets"])
            st.sidebar.success("✅ Using Streamlit Cloud credentials")
        except:
            # For local development: Use service_account.json file
            try:
                with open('service_account.json', 'r') as f:
                    creds_dict = json.load(f)
                st.sidebar.success("✅ Using local service_account.json")
            except FileNotFoundError:
                st.error("❌ No credentials found!")
                st.info("""
                **For Streamlit Cloud:**
                1. Add credentials to Streamlit secrets
                
                **For Local:**
                1. Place service_account.json in same folder
                """)
                return None
        
        # Create credentials
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets',
                   'https://www.googleapis.com/auth/drive']
        )
        
        # Create client
        client = gspread.authorize(credentials)
        
        # Test connection
        test_sheet = client.open_by_key(YOUR_SHEET_ID)
        sheet_title = test_sheet.title
        
        st.sidebar.success(f"✅ Connected to: {sheet_title}")
        return client
        
    except Exception as e:
        st.error(f"❌ Connection failed: {str(e)[:200]}")
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
        st.error(f"Error loading {sheet_name}: {str(e)}")
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

# Show instructions first
with st.expander("📋 Click here for setup instructions", expanded=True):
    st.markdown("""
    ### **To get this working on Streamlit Cloud:**
    
    1. **Create `.streamlit/secrets.toml` file**
    2. **Add your Google Sheets credentials** (see format below)
    3. **Share your Google Sheet** with the service account
    4. **Deploy to Streamlit Cloud**
    
    ### **secrets.toml format:**
    ```toml
    [google_sheets]
    type = "service_account"
    project_id = "your-project-id"
    private_key_id = "your-private-key-id"
    private_key = '''
    -----BEGIN PRIVATE KEY-----
    \nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDiFfGVgOwmZ8J7\nMY30yLCgoMl/YsfuSxbEZrYB2xmrqRTbQfjq3R/C/yCw9X15OM2WvkM+gXNhB7tw\nacopOvytvL/EFuYOX/bacr4ncTlscLdO2gbigYrLcoyLJyR0DjwddaHMy++FMYvc\npqXsaxd59v03SWZItF2sAvTx6oeEst9+B1E8tQ77KVMG1TGB2Q8zk98WcBJqWsJs\n33QbkBnOO6iI4xnZ7uRyFOcWgEct1gtmpIjHYFUt4SsB3xcR49KXTQ72qKYemaQw\n41QG79n2ykD/LnuefaXytaoGguVyyI3zFe1rKg3hC0ri7ChkyOPpB0L3Tueoeab7\n3WR8K3BzAgMBAAECggEAESvMfOfdR69ywGuLlg9WBuUfWKr2d11BneoVIb/zy6tc\nV6jDkIb53hQFdhs3C+lqB+xsbAdl7XUqYcfPIGGIBmQDBpAcqfPU6lNzqMg7LcbD\nzVvW0QY4ten9zaXL6XqZSz1/a/ADQZD5R+lqSbH6hvtg0P2kpJn6UVGqK+N9pnDQ\n6E9doC99TSwMPzRcR6hBu/jIAXw9x8CSBUddrz/azTXHPjWgaa3gdMim0p4Q9NF3\nQrWXAQEeCQb1ArZdJA5LkfJ6C88qoibYLS8hADXc7mR0qqUbBm+8SMkN03euFNC2\nTjGihPGtgfsp8vLxNRXb/b/AsXO2t0WEcruN+yaJoQKBgQDw9/o7UbEDb6LO+dWi\nA0T5bGO+9pkqUn/nFMrRwtYJoodLdplomo3/7tLv7h23/VdKxcoj+YMT+n0rv7O4\nxEuq7o9DABopvuabGofmHgu189DLNNrOmj5v3Rkd4hTAdESNVtKvVsgHYsTG5nIM\nJGkyIuhFO1dBBV18MC/git3m4QKBgQDwME0EqP9kJzDCEGm3QAKd58TdyjGD4R0j\nTe3A/mlDAeL9E0WSUlDqjDOB+6vLPdh4dgS1+90MA2E3xd225dxE9m0Z5Ittuady\nUIk+x/TSqN9UdSRz+hn9QGkpZJCgdKN44z26dmausQ4f5RTO3xZ6U0MZV6e3w7s1\nJWzupvvF0wKBgEtVq5SqCIZDe4nrz59UGFdGTLTiEaaKnlQXSwVjPVlLx7KPBI0Q\nbL6L4sSCFCZ2fLjytyyiEBnJ4SIxT7W/IMzywjU3LfbJKP1qwPvvfsfGzwsInjOj\nQ0vjurt99/DnKJtrfni0z9qHRW/NkfA73et/wFAMqk24qK5vvjgcEh3hAoGAVgbm\nvwGMn6GNzCQ2yQSrK0Vk9I9D1tldJ1T1EAfPScm2NDCf3X2QL8HRfP/YEy5uhw62\nNzwjevcG7gP3mleP4j9k6j46Vi2FtOL1lT/nB0Cm5MgkK0nr3xIf2EyFpILCPj0d\n0dgwhOcziOby4flzQpLp2HzVvHLlbW6fKocybDMCgYBCnEiz9PJDEfylgVDYZIt/\nIZf0hBBBhtyNDSeg0FdvcvvumX55FJuqK949BmRlkLITEzBLQyn30E5lo74FPMyc\nsu9vHAsqV1kF2KRn4/9+HwkubOg0K/zgFRCzhFE9j7i0mojyXoQTb/TpaH73YXkC\nGr+fbcfSb9MNz65tEJDYzw==\n
    -----END PRIVATE KEY-----
    '''
    client_email = "your-service-account@project.iam.gserviceaccount.com"
    client_id = "your-client-id"
    auth_uri = "https://accounts.google.com/o/oauth2/auth"
    token_uri = "https://oauth2.googleapis.com/token"
    auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
    client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
    universe_domain = "googleapis.com"
    ```
    """)

# Connect to Google Sheets
gsheets_client = connect_to_google_sheets()

if gsheets_client:
    # Load data
    with st.spinner("Loading data from Google Sheets..."):
        contest_df = load_sheet_data(gsheets_client, 'Contest Details')
        winner_df = load_sheet_data(gsheets_client, 'Winner Details')
    
    # Check if data loaded
    if contest_df.empty:
        st.error("❌ Could not load Contest Details!")
        st.stop()
    
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
    
    # ============================================
    # INTERFACE
    # ============================================
    
    # Tab 1: Contest Filtering
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
        
        st.metric("Contests Found", len(filtered_contest))
    
    with col2:
        # Display contests
        if not filtered_contest.empty:
            display_cols = ['Merch ID', 'Camp Name', 'Camp Type', 'Start Date', 'End Date', 'Winner Announcement Date']
            display_cols = [col for col in display_cols if col in filtered_contest.columns]
            
            display_df = filtered_contest[display_cols].copy()
            
            # Format dates
            for date_col in ['Start Date', 'End Date', 'Winner Announcement Date']:
                if date_col in display_df.columns:
                    display_df[date_col] = display_df[date_col].dt.strftime('%d-%m-%Y')
            
            st.dataframe(display_df, use_container_width=True, height=400)
            
            # Download
            csv_data = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download Contests",
                csv_data,
                f"contests_{start_date}_to_{end_date}.csv",
                "text/csv"
            )
        else:
            st.info("No contests found")
    
    st.markdown("---")
    
    # Tab 2: Winner Search
    if not winner_df.empty:
        st.header("🏆 Search Winners")
        
        search_type = st.radio("Search by:", ["BZID", "Phone", "Name", "Merch ID"])
        
        if search_type == "BZID":
            search_input = st.text_input("Enter BZID")
            column = 'businessid'
        elif search_type == "Phone":
            search_input = st.text_input("Enter Phone")
            column = 'customer_phonenumber'
        elif search_type == "Name":
            search_input = st.text_input("Enter Name")
            column = 'customer_firstname'
        else:
            search_input = st.text_input("Enter Merch ID")
            column = 'Merch ID'
        
        if search_input and column in winner_df.columns:
            results = winner_df[winner_df[column].astype(str).str.contains(search_input, case=False, na=False)]
            
            if not results.empty:
                st.success(f"Found {len(results)} records")
                
                summary_cols = ['Merch ID', 'Contest', 'Gift', 'Winner Announcement Date', 'customer_firstname']
                summary_cols = [col for col in summary_cols if col in results.columns]
                
                summary_df = results[summary_cols].copy()
                
                if 'Winner Announcement Date' in summary_df.columns:
                    summary_df['Winner Announcement Date'] = summary_df['Winner Announcement Date'].dt.strftime('%d-%m-%Y')
                
                st.dataframe(summary_df, use_container_width=True)
            else:
                st.warning("No results found")
    
    # Refresh button
    st.markdown("---")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    # Footer
    st.caption(f"Last updated: {datetime.now().strftime('%d-%m-%Y %H:%M')}")
