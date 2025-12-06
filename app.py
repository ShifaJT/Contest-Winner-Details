import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
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

# Function to find column by possible names
def find_column(df, possible_names):
    """Find a column by possible names"""
    for name in possible_names:
        if name in df.columns:
            return name
    return None

# Function to safely convert to datetime - IMPROVED for DD-MM-YYYY format
def safe_to_datetime(series):
    """Safely convert series to datetime with multiple format attempts"""
    try:
        # First, ensure we're working with strings
        str_series = series.astype(str).str.strip()
        
        # Remove common issues
        str_series = str_series.replace(['NaT', 'NaN', 'nan', 'None', ''], pd.NA)
        
        # Try specific formats in order of likelihood
        formats_to_try = [
            '%d-%m-%Y',  # DD-MM-YYYY (your format)
            '%d/%m/%Y',  # DD/MM/YYYY
            '%Y-%m-%d',  # YYYY-MM-DD
            '%d %b %Y',  # DD MMM YYYY
            '%d %B %Y',  # DD Month YYYY
            '%m/%d/%Y',  # MM/DD/YYYY
            '%d-%m-%y',  # DD-MM-YY
            '%d/%m/%y',  # DD/MM/YY
        ]
        
        result = pd.Series([pd.NaT] * len(series), dtype='datetime64[ns]')
        
        for fmt in formats_to_try:
            try:
                parsed = pd.to_datetime(str_series, errors='coerce', format=fmt)
                # Fill in any NaNs we successfully parsed
                mask = parsed.notna() & result.isna()
                result[mask] = parsed[mask]
            except:
                continue
        
        # If we still have NaNs, try pandas' built-in parser with dayfirst=True
        if result.isna().any():
            final_try = pd.to_datetime(str_series, errors='coerce', dayfirst=True)
            mask = final_try.notna() & result.isna()
            result[mask] = final_try[mask]
        
        return result
    except Exception as e:
        return pd.NaT

# Function to determine contest status - IMPROVED
def get_contest_status(start_date, end_date, today):
    """Determine if contest is upcoming, running, or past"""
    try:
        # Handle NaT values
        if pd.isna(start_date) or pd.isna(end_date):
            return 'unknown'
        
        # Ensure we have datetime objects
        if not isinstance(start_date, (pd.Timestamp, datetime)):
            start_date = pd.to_datetime(start_date, errors='coerce')
        if not isinstance(end_date, (pd.Timestamp, datetime)):
            end_date = pd.to_datetime(end_date, errors='coerce')
        
        # Check again after conversion
        if pd.isna(start_date) or pd.isna(end_date):
            return 'unknown'
        
        # Get date objects
        start_date_obj = start_date.date() if hasattr(start_date, 'date') else pd.to_datetime(start_date).date()
        end_date_obj = end_date.date() if hasattr(end_date, 'date') else pd.to_datetime(end_date).date()
        
        # Determine status
        if start_date_obj > today:
            return 'upcoming'
        elif start_date_obj <= today <= end_date_obj:
            return 'running'
        else:
            return 'past'
    except Exception as e:
        return 'unknown'

# Function to create nice contest cards - IMPROVED
def create_contest_card(row, camp_name_col, camp_type_col, start_date_col, end_date_col,
                       winner_date_col, kam_col, to_whom_col, eligibility_col, status):
    """Create a nice looking contest card"""
    camp_name = row[camp_name_col] if camp_name_col and camp_name_col in row and pd.notna(row[camp_name_col]) else 'N/A'
    camp_type = row[camp_type_col] if camp_type_col and camp_type_col in row and pd.notna(row[camp_type_col]) else 'N/A'
    
    # Get contest eligibility
    contest_eligibility = row[eligibility_col] if eligibility_col and eligibility_col in row and pd.notna(row[eligibility_col]) else 'N/A'
   
    # Format start date
    start_date = 'N/A'
    if start_date_col and start_date_col in row and pd.notna(row[start_date_col]):
        try:
            if hasattr(row[start_date_col], 'strftime'):
                start_date = row[start_date_col].strftime('%d %b %Y')
            else:
                # Try to parse it
                parsed = pd.to_datetime(str(row[start_date_col]), errors='coerce', dayfirst=True)
                if not pd.isna(parsed):
                    start_date = parsed.strftime('%d %b %Y')
                else:
                    start_date = str(row[start_date_col])
        except:
            start_date = str(row[start_date_col])
   
    # Format end date
    end_date = 'N/A'
    if end_date_col and end_date_col in row and pd.notna(row[end_date_col]):
        try:
            if hasattr(row[end_date_col], 'strftime'):
                end_date = row[end_date_col].strftime('%d %b %Y')
            else:
                # Try to parse it
                parsed = pd.to_datetime(str(row[end_date_col]), errors='coerce', dayfirst=True)
                if not pd.isna(parsed):
                    end_date = parsed.strftime('%d %b %Y')
                else:
                    end_date = str(row[end_date_col])
        except:
            end_date = str(row[end_date_col])
   
    # Format winner date - IMPROVED
    winner_date = 'N/A'
    if winner_date_col and winner_date_col in row and pd.notna(row[winner_date_col]):
        try:
            if hasattr(row[winner_date_col], 'strftime'):
                winner_date = row[winner_date_col].strftime('%d %b %Y')
            else:
                # Try multiple parsing strategies
                date_str = str(row[winner_date_col]).strip()
                # Common date patterns
                patterns = ['%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%d %b %Y', '%d %B %Y', '%m/%d/%Y']
                
                parsed_date = None
                for pattern in patterns:
                    try:
                        parsed_date = datetime.strptime(date_str, pattern)
                        break
                    except:
                        continue
                
                if parsed_date:
                    winner_date = parsed_date.strftime('%d %b %Y')
                else:
                    # Last resort: try pandas parsing
                    parsed = pd.to_datetime(date_str, errors='coerce', dayfirst=True)
                    if not pd.isna(parsed):
                        winner_date = parsed.strftime('%d %b %Y')
                    else:
                        winner_date = date_str
        except Exception as e:
            winner_date = str(row[winner_date_col])
   
    kam = row[kam_col] if kam_col and kam_col in row and pd.notna(row[kam_col]) else 'N/A'
    to_whom = row[to_whom_col] if to_whom_col and to_whom_col in row and pd.notna(row[to_whom_col]) else 'N/A'
   
    # Calculate days left if contest is running
    days_left = ""
    if status == 'running' and end_date_col and end_date_col in row and pd.notna(row[end_date_col]):
        try:
            if hasattr(row[end_date_col], 'date'):
                end_date_obj = row[end_date_col].date()
            else:
                end_date_obj = pd.to_datetime(row[end_date_col], dayfirst=True).date()
            
            today = datetime.now().date()
            days_left_int = (end_date_obj - today).days
            if days_left_int >= 0:
                days_left = f"<br><strong>⏳ Days Left:</strong> {days_left_int} days"
        except:
            pass
   
    # Different styles based on status
    if status == 'running':
        gradient = "linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%)"  # Green for running
        badge = "🏃 RUNNING NOW"
    elif status == 'upcoming':
        gradient = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"  # Purple for upcoming
        badge = "📅 UPCOMING"
    else:  # past or unknown
        gradient = "linear-gradient(135deg, #9e9e9e 0%, #616161 100%)"  # Grey for past
        badge = "✅ COMPLETED"
   
    # Create card with contest eligibility
    card_html = f"""
    <div class="contest-card" style="
        background: {gradient};
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        position: relative;
    ">
        <div style="position: absolute; top: 10px; right: 10px; background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 12px; font-size: 12px;">
            {badge}
        </div>
        <h3 style="margin: 0 0 10px 0; color: white; padding-right: 80px;">{camp_name}</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div>
                <strong>🎯 Type:</strong> {camp_type}<br>
                <strong>📋 Eligibility:</strong> {contest_eligibility}<br>
                <strong>👤 KAM:</strong> {kam}<br>
                <strong>👥 Team:</strong> {to_whom}
            </div>
            <div>
                <strong>📅 Starts:</strong> {start_date}<br>
                <strong>🏁 Ends:</strong> {end_date}<br>
                <strong>🏆 Winner Date:</strong> {winner_date}
                {days_left}
            </div>
        </div>
    </div>
    """
    return card_html

# Initialize session state
if 'current_section' not in st.session_state:
    st.session_state.current_section = "🎯 Contest Dashboard"

# App
st.set_page_config(page_title="Contest Check", layout="wide", page_icon="🎯")
st.title("🎯 Jumbotail Contest Details Dashboard")
st.markdown("---")

# Add comprehensive CSS for both light and dark modes
st.markdown("""
<style>
    /* Base styles for all modes */
    .stApp {
        transition: background-color 0.3s ease, color 0.3s ease;
    }
    
    /* Common styles */
    .stRadio > div > label > div:first-child {
        background-color: #4CAF50 !important;
    }
    
    .gift-delivered {
        background-color: #4CAF50 !important;
        color: white !important;
        padding: 2px 8px !important;
        border-radius: 12px !important;
        font-size: 12px !important;
        font-weight: bold !important;
        display: inline-block !important;
    }
    
    .gift-pending {
        background-color: #FF9800 !important;
        color: white !important;
        padding: 2px 8px !important;
        border-radius: 12px !important;
        font-size: 12px !important;
        font-weight: bold !important;
        display: inline-block !important;
    }
    
    .gift-not-found {
        background-color: #F44336 !important;
        color: white !important;
        padding: 2px 8px !important;
        border-radius: 12px !important;
        font-size: 12px !important;
        font-weight: bold !important;
        display: inline-block !important;
    }
    
    /* Ensure contest cards have good contrast */
    .contest-card h3 {
        color: white !important;
    }
    
    .contest-card div {
        color: white !important;
    }
    
    /* Light mode overrides */
    [data-theme="light"] {
        background-color: #ffffff !important;
        color: #31333F !important;
    }
    
    [data-theme="light"] .stRadio > div {
        background-color: #f8f9fa !important;
        padding: 10px !important;
        border-radius: 5px !important;
        border: 1px solid #dee2e6 !important;
    }
    
    [data-theme="light"] .stDateInput > div > div > input {
        border: 2px solid #667eea !important;
        border-radius: 5px !important;
        background-color: white !important;
        color: #31333F !important;
    }
    
    [data-theme="light"] .stSelectbox > div > div > select {
        border: 2px solid #667eea !important;
        border-radius: 5px !important;
        background-color: white !important;
        color: #31333F !important;
    }
    
    [data-theme="light"] .stTextInput > div > div > input {
        background-color: white !important;
        color: #31333F !important;
        border: 1px solid #ccc !important;
    }
    
    [data-theme="light"] [data-testid="stMetricValue"],
    [data-theme="light"] [data-testid="stMetricLabel"] {
        color: #31333F !important;
    }
    
    /* Dark mode overrides */
    [data-theme="dark"] {
        background-color: #0E1117 !important;
        color: #FAFAFA !important;
    }
    
    [data-theme="dark"] .stRadio > div {
        background-color: #262730 !important;
        padding: 10px !important;
        border-radius: 5px !important;
        border: 1px solid #444 !important;
    }
    
    [data-theme="dark"] .stRadio > label {
        color: #FAFAFA !important;
    }
    
    [data-theme="dark"] .stDateInput > div > div > input {
        border: 2px solid #667eea !important;
        border-radius: 5px !important;
        background-color: #262730 !important;
        color: #FAFAFA !important;
    }
    
    [data-theme="dark"] .stSelectbox > div > div > select {
        border: 2px solid #667eea !important;
        border-radius: 5px !important;
        background-color: #262730 !important;
        color: #FAFAFA !important;
    }
    
    [data-theme="dark"] .stTextInput > div > div > input {
        background-color: #262730 !important;
        color: #FAFAFA !important;
        border: 1px solid #555 !important;
    }
    
    [data-theme="dark"] [data-testid="stMetricValue"],
    [data-theme="dark"] [data-testid="stMetricLabel"] {
        color: #FAFAFA !important;
    }
    
    [data-theme="dark"] .stDataFrame {
        background-color: #262730 !important;
        color: #FAFAFA !important;
    }
    
    [data-theme="dark"] .stDataFrame th {
        background-color: #1a1a24 !important;
        color: #FAFAFA !important;
    }
    
    [data-theme="dark"] .stDataFrame td {
        background-color: #262730 !important;
        color: #FAFAFA !important;
    }
    
    [data-theme="dark"] .stExpander > div > div {
        background-color: #262730 !important;
        color: #FAFAFA !important;
    }
    
    [data-theme="dark"] .stAlert {
        background-color: #262730 !important;
        color: #FAFAFA !important;
    }
    
    [data-theme="dark"] .stSuccess {
        background-color: #1a472a !important;
        color: #FAFAFA !important;
    }
    
    [data-theme="dark"] .stInfo {
        background-color: #1a3a5f !important;
        color: #FAFAFA !important;
    }
    
    [data-theme="dark"] .stWarning {
        background-color: #5d4037 !important;
        color: #FAFAFA !important;
    }
    
    [data-theme="dark"] .stError {
        background-color: #7f1d1d !important;
        color: #FAFAFA !important;
    }
    
    /* Force text color for all main content */
    .main .block-container {
        color: inherit !important;
    }
    
    h1, h2, h3, h4, h5, h6, p, div, span {
        color: inherit !important;
    }
    
    /* Ensure sidebar text is visible */
    .stSidebar {
        color: inherit !important;
    }
    
    .stSidebar * {
        color: inherit !important;
    }
</style>
""", unsafe_allow_html=True)

# Create navigation menu with radio buttons
st.sidebar.title("📊 Navigation")
section = st.sidebar.radio(
    "Go to:",
    ["🎯 Contest Dashboard", "🔍 Filter Contests", "🏆 Check Winners"],
    index=0  # Default to Contest Dashboard
)

# Connect to Google Sheets
client = connect_sheets()

if client:
    try:
        sheet = client.open_by_key("1E2qxc1kZttPQMmSXCVXFaQKVNLl_Nhe4uUPBrzf7B3U")
       
        # Load data once and cache it
        @st.cache_data(ttl=300)
        def load_contest_data():
            contest_ws = sheet.worksheet("Contest Details")
            contest_data = contest_ws.get_all_records()
            contests = pd.DataFrame(contest_data)
            return contests
       
        @st.cache_data(ttl=300)
        def load_winner_data():
            winner_sheet_names = ['Winners Details ', 'Winner Details', 'Winners Details', 'Winner Details ']
            for sheet_name in winner_sheet_names:
                try:
                    winner_ws = sheet.worksheet(sheet_name)
                    winner_data = winner_ws.get_all_records()
                    winners = pd.DataFrame(winner_data)
                    return winners, sheet_name
                except:
                    continue
            return pd.DataFrame(), None
       
        # Load data
        contests = load_contest_data()
        winners, winner_sheet_name = load_winner_data()
       
        if not contests.empty:
            st.sidebar.success(f"✅ {len(contests)} contests loaded")
        if not winners.empty:
            st.sidebar.success(f"✅ {len(winners)} winners loaded")
       
        # Process contest data - IMPROVED DATE HANDLING
        if not contests.empty:
            # Find important columns
            camp_name_col = find_column(contests, ['Camp Name', 'Campaign Name', 'Camp Description', 'Camp'])
            camp_type_col = find_column(contests, ['Camp Type', 'Type', 'Category'])
            start_date_col = find_column(contests, ['Start Date', 'StartDate', 'Start'])
            end_date_col = find_column(contests, ['End Date', 'EndDate', 'End'])
            
            # IMPROVED: Better winner date column detection
            winner_date_col = find_column(contests, [
                'Winner Announcement Date', 
                'Winner Date', 
                'Announcement Date',
                'Winner Announcement',
                'Winner Ann Date',
                'Winner_Announcement_Date'
            ])
            
            kam_col = find_column(contests, ['KAM', 'Owner', 'Manager', 'Responsible'])
            to_whom_col = find_column(contests, ['To Whom?', 'To Whom', 'Assigned To', 'Team'])
            eligibility_col = find_column(contests, ['Contest Eligiblity', 'Contest Eligibility', 'Eligibility', 'Contest Eligiblity '])
           
            # Fix dates safely - IMPROVED for DD-MM-YYYY format
            if start_date_col:
                contests[start_date_col] = safe_to_datetime(contests[start_date_col])
                contests['Start_Date'] = contests[start_date_col]
                # Extract year and month with error handling
                contests['Year'] = contests['Start_Date'].dt.year.where(contests['Start_Date'].notna(), pd.NA)
                contests['Month'] = contests['Start_Date'].dt.month_name().where(contests['Start_Date'].notna(), pd.NA)
                contests['Month_Num'] = contests['Start_Date'].dt.month.where(contests['Start_Date'].notna(), pd.NA)
           
            if end_date_col:
                contests[end_date_col] = safe_to_datetime(contests[end_date_col])
           
            if winner_date_col:
                contests[winner_date_col] = safe_to_datetime(contests[winner_date_col])
       
        # Process winner data - IMPROVED
        if not winners.empty:
            # Fix dates in winner data safely
            date_cols = ['Start Date', 'End Date', 'Winner Announcement Date']
            for col in date_cols:
                if col in winners.columns:
                    winners[col] = safe_to_datetime(winners[col])
            
            # Find Gift Status column (handle different possible names)
            gift_status_col = find_column(winners, ['Gift Status', 'GiftStatus', 'Status', 'Delivery Status', 'Gift_Status'])
       
        today = datetime.now().date()
        current_month = today.month
        current_year = today.year
       
        # ============================================
        # CONTEST DASHBOARD SECTION
        # ============================================
        if section == "🎯 Contest Dashboard":
            st.header("📊 Contest Dashboard")
           
            if not contests.empty and start_date_col and end_date_col:
                # ============================================
                # DASHBOARD STATS
                # ============================================
                st.subheader("📈 Quick Overview")
               
                # Calculate stats
                total_contests = len(contests)
               
                # Current month contests
                current_month_contests = contests[
                    (contests['Year'] == current_year) &
                    (contests['Month_Num'] == current_month)
                ]
               
                # Calculate contest status for all contests - IMPROVED
                contests['Status'] = 'unknown'
                for idx, row in contests.iterrows():
                    start_val = row[start_date_col] if start_date_col in row else None
                    end_val = row[end_date_col] if end_date_col in row else None
                    contests.at[idx, 'Status'] = get_contest_status(start_val, end_val, today)
               
                # Get contests by status - IMPROVED running contests detection
                running_contests = contests[contests['Status'] == 'running'].copy()
                upcoming_contests = contests[contests['Status'] == 'upcoming'].copy()
                past_contests = contests[contests['Status'] == 'past'].copy()
               
                # FIX: Direct calculation of running contests to ensure accuracy
                if start_date_col and end_date_col:
                    # Ensure dates are datetime objects
                    if not pd.api.types.is_datetime64_any_dtype(contests[start_date_col]):
                        contests[start_date_col] = safe_to_datetime(contests[start_date_col])
                    if not pd.api.types.is_datetime64_any_dtype(contests[end_date_col]):
                        contests[end_date_col] = safe_to_datetime(contests[end_date_col])
                    
                    # Clear and recalculate running contests
                    running_mask = (
                        pd.notna(contests[start_date_col]) & 
                        pd.notna(contests[end_date_col]) &
                        (contests[start_date_col].dt.date <= today) & 
                        (contests[end_date_col].dt.date >= today)
                    )
                    running_contests = contests[running_mask].copy()
                    running_contests['Status'] = 'running'
                    
                    # Update other statuses
                    upcoming_mask = (
                        pd.notna(contests[start_date_col]) & 
                        (contests[start_date_col].dt.date > today)
                    )
                    upcoming_contests = contests[upcoming_mask].copy()
                    upcoming_contests['Status'] = 'upcoming'
                    
                    past_mask = (
                        pd.notna(contests[end_date_col]) & 
                        (contests[end_date_col].dt.date < today)
                    )
                    past_contests = contests[past_mask].copy()
                    past_contests['Status'] = 'past'
               
                # Recently ended (last 7 days)
                recently_ended = contests[
                    (contests['Status'] == 'past') &
                    pd.notna(contests[end_date_col]) &
                    (contests[end_date_col].dt.date >= (today - timedelta(days=7)))
                ]
               
                # Display stats in columns
                col1, col2, col3, col4 = st.columns(4)
               
                with col1:
                    st.metric("Total Contests", total_contests)
               
                with col2:
                    st.metric("Running Now", len(running_contests))
               
                with col3:
                    st.metric("Upcoming", len(upcoming_contests))
               
                with col4:
                    st.metric("Past/Completed", len(past_contests))
               
                # ============================================
                # ONGOING CONTESTS
                # ============================================
                if not running_contests.empty:
                    st.subheader("🏃 Currently Running Contests")
                    st.info(f"**Active now: {len(running_contests)} contest(s)**")
                   
                    # Show stats for running contests
                    stats_col1, stats_col2, stats_col3 = st.columns(3)
                   
                    with stats_col1:
                        if camp_type_col and camp_type_col in running_contests.columns:
                            running_types = running_contests[camp_type_col].nunique()
                            st.metric("Campaign Types", running_types)
                   
                    with stats_col2:
                        if eligibility_col and eligibility_col in running_contests.columns:
                            running_eligibilities = running_contests[eligibility_col].nunique()
                            st.metric("Eligibility Types", running_eligibilities)
                   
                    with stats_col3:
                        # Calculate average days left
                        if end_date_col and end_date_col in running_contests.columns:
                            try:
                                days_left_list = []
                                for _, row in running_contests.iterrows():
                                    if pd.notna(row[end_date_col]):
                                        if hasattr(row[end_date_col], 'date'):
                                            end_date_obj = row[end_date_col].date()
                                        else:
                                            end_date_obj = pd.to_datetime(row[end_date_col]).date()
                                        days_left = (end_date_obj - today).days
                                        if days_left >= 0:
                                            days_left_list.append(days_left)
                               
                                if days_left_list:
                                    avg_days_left = sum(days_left_list) // len(days_left_list)
                                    st.metric("Avg Days Left", avg_days_left)
                                else:
                                    st.metric("Avg Days Left", "N/A")
                            except:
                                st.metric("Avg Days Left", "N/A")
                   
                    st.markdown("---")
                   
                    # Show running contest cards
                    for _, row in running_contests.iterrows():
                        card_html = create_contest_card(
                            row, camp_name_col, camp_type_col, start_date_col, end_date_col,
                            winner_date_col, kam_col, to_whom_col, eligibility_col, status='running'
                        )
                        st.markdown(card_html, unsafe_allow_html=True)
                else:
                    st.subheader("🏃 Currently Running Contests")
                    st.info("🎉 No contests running today! All caught up!")
               
                # ============================================
                # UPCOMING CONTESTS
                # ============================================
                if not upcoming_contests.empty:
                    st.subheader("📅 Upcoming Contests")
                    st.info(f"**Scheduled: {len(upcoming_contests)} contest(s)**")
                   
                    # Group by month for better organization
                    upcoming_contests['Month_Year'] = upcoming_contests[start_date_col].dt.strftime('%B %Y')
                    months_sorted = sorted(upcoming_contests['Month_Year'].unique(), 
                                          key=lambda x: datetime.strptime(x, '%B %Y'))
                    
                    for month_year in months_sorted:
                        month_contests = upcoming_contests[upcoming_contests['Month_Year'] == month_year]
                        
                        st.markdown(f"### 📅 {month_year}")
                        
                        # Show stats for this month's contests
                        up_stats_col1, up_stats_col2 = st.columns(2)
                        
                        with up_stats_col1:
                            # Days to next contest in this month
                            try:
                                next_contest_date = month_contests[start_date_col].min().date()
                                days_to_next = (next_contest_date - today).days
                                st.metric("Days to First Contest", days_to_next if days_to_next > 0 else 0)
                            except:
                                st.metric("Days to First Contest", "N/A")
                        
                        with up_stats_col2:
                            # Contest eligibilities in this month
                            if eligibility_col and eligibility_col in month_contests.columns:
                                upcoming_eligibilities = month_contests[eligibility_col].nunique()
                                st.metric("Eligibility Types", upcoming_eligibilities)
                        
                        st.markdown("---")
                        
                        # Show this month's contest cards
                        for _, row in month_contests.iterrows():
                            card_html = create_contest_card(
                                row, camp_name_col, camp_type_col, start_date_col, end_date_col,
                                winner_date_col, kam_col, to_whom_col, eligibility_col, status='upcoming'
                            )
                            st.markdown(card_html, unsafe_allow_html=True)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                else:
                    st.subheader("📅 Upcoming Contests")
                    st.info("📭 No upcoming contests")
               
                # ============================================
                # RECENTLY ENDED CONTESTS
                # ============================================
                if not recently_ended.empty:
                    st.subheader("✅ Recently Ended Contests (Last 7 Days)")
                   
                    # Show in a compact grid
                    cols = st.columns(3)
                    for idx, (_, row) in enumerate(recently_ended.head(9).iterrows()):  # Show max 9
                        with cols[idx % 3]:
                            camp_name = row[camp_name_col] if camp_name_col else 'N/A'
                            camp_type = row[camp_type_col] if camp_type_col else 'N/A'
                            end_date = 'N/A'
                            if pd.notna(row[end_date_col]):
                                if hasattr(row[end_date_col], 'strftime'):
                                    end_date = row[end_date_col].strftime('%d %b')
                                else:
                                    end_date = str(row[end_date_col])
                           
                            st.markdown(f"""
                            <div style="
                                background: #f0f2f6;
                                border-radius: 8px;
                                padding: 15px;
                                margin: 5px 0;
                                border-left: 4px solid #764ba2;
                            ">
                                <strong>{camp_name}</strong><br>
                                <small>Type: {camp_type}</small><br>
                                <small>Ended: {end_date}</small>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.subheader("✅ Recently Ended Contests (Last 7 Days)")
                    st.info("No contests ended in the last 7 days")
       
        # ============================================
        # FILTER CONTESTS SECTION - FIXED
        # ============================================
        elif section == "🔍 Filter Contests":
            st.header("🔍 Filter Contests")
           
            if not contests.empty:
                # Date Range Filter Section
                st.subheader("📅 Select Date Range")
               
                col1, col2 = st.columns(2)
               
                with col1:
                    # Get min and max dates safely
                    if start_date_col and pd.notna(contests[start_date_col]).any():
                        try:
                            # Convert to date objects for the date input
                            valid_dates = contests[start_date_col].dropna()
                            min_date = valid_dates.min().date()
                            max_date = valid_dates.max().date()
                        except:
                            min_date = date(current_year, 1, 1)
                            max_date = today
                    else:
                        min_date = date(current_year, 1, 1)
                        max_date = today
                   
                    start_date = st.date_input(
                        "From Date",
                        value=date(current_year, current_month, 1),
                        min_value=min_date,
                        max_value=max_date,
                        key="contest_start_date"
                    )
               
                with col2:
                    end_date = st.date_input(
                        "To Date",
                        value=today,
                        min_value=min_date,
                        max_value=max_date,
                        key="contest_end_date"
                    )
               
                # Additional Filters
                st.subheader("🔍 Additional Filters")
                col1, col2, col3 = st.columns(3)
               
                with col1:
                    # Year filter
                    if 'Year' in contests.columns and pd.notna(contests['Year']).any():
                        years = sorted(contests['Year'].dropna().unique(), reverse=True)
                        years = [int(y) for y in years if pd.notna(y)]
                        selected_year = st.selectbox(
                            "Select Year",
                            ["All Years"] + years,
                            index=0,
                            key="contest_year"
                        )
                    else:
                        selected_year = "All Years"
               
                with col2:
                    # Month filter
                    months = [
                        "All Months", "January", "February", "March", "April", "May", "June",
                        "July", "August", "September", "October", "November", "December"
                    ]
                    selected_month = st.selectbox("Select Month", months, index=0, key="contest_month")
               
                with col3:
                    # Camp Type filter
                    if camp_type_col and pd.notna(contests[camp_type_col]).any():
                        camp_types = ["All Types"] + sorted(contests[camp_type_col].dropna().unique().tolist())
                        selected_type = st.selectbox("Campaign Type", camp_types, index=0, key="contest_type")
                    else:
                        selected_type = "All Types"
               
                # Apply filters - FIXED DATE FILTERING LOGIC
                filtered_contests = contests.copy()
               
                # Debug: Show raw data for troubleshooting
                if st.checkbox("🔧 Show debug info (for troubleshooting)"):
                    st.write(f"Total contests: {len(contests)}")
                    if start_date_col and start_date_col in contests.columns:
                        st.write(f"Sample start dates (first 10):")
                        sample_data = contests.head(10).copy()
                        display_cols = []
                        if camp_name_col: display_cols.append(camp_name_col)
                        if start_date_col: display_cols.append(start_date_col)
                        if end_date_col: display_cols.append(end_date_col)
                        st.write(sample_data[display_cols])
                       
                        # Show data types
                        st.write("**Date column data types:**")
                        st.write(f"Start Date type: {type(contests[start_date_col].iloc[0]) if len(contests) > 0 else 'N/A'}")
                        st.write(f"End Date type: {type(contests[end_date_col].iloc[0]) if len(contests) > 0 else 'N/A'}")
                       
                        # Show specific contest you mentioned
                        target_contest = "CAMP-334434"
                        if camp_name_col:
                            specific_contest = contests[contests[camp_name_col].astype(str).str.contains(target_contest)]
                            if not specific_contest.empty:
                                st.write(f"**Specific contest ({target_contest}):**")
                                st.write(specific_contest[[camp_name_col, start_date_col, end_date_col]])
               
                # Date range filter - FIXED
                if start_date_col and end_date_col:
                    # Make sure we have datetime objects
                    if not pd.api.types.is_datetime64_any_dtype(filtered_contests[start_date_col]):
                        filtered_contests[start_date_col] = safe_to_datetime(filtered_contests[start_date_col])
                    if not pd.api.types.is_datetime64_any_dtype(filtered_contests[end_date_col]):
                        filtered_contests[end_date_col] = safe_to_datetime(filtered_contests[end_date_col])
                   
                    # Filter by date range - FIXED LOGIC
                    # We want contests that overlap with the selected date range
                    date_mask = (
                        # Contests that start within the range
                        (
                            (filtered_contests[start_date_col].dt.date >= start_date) &
                            (filtered_contests[start_date_col].dt.date <= end_date)
                        ) |
                        # Contests that end within the range
                        (
                            (filtered_contests[end_date_col].dt.date >= start_date) &
                            (filtered_contests[end_date_col].dt.date <= end_date)
                        ) |
                        # Contests that span the entire range
                        (
                            (filtered_contests[start_date_col].dt.date <= start_date) &
                            (filtered_contests[end_date_col].dt.date >= end_date)
                        )
                    )
                   
                    # Apply the filter
                    filtered_contests = filtered_contests[date_mask]
               
                # Year filter
                if selected_year != "All Years" and 'Year' in filtered_contests.columns:
                    filtered_contests = filtered_contests[filtered_contests['Year'] == int(selected_year)]
               
                # Month filter
                if selected_month != "All Months" and 'Month_Num' in filtered_contests.columns:
                    month_num = months.index(selected_month)
                    filtered_contests = filtered_contests[filtered_contests['Month_Num'] == month_num]
               
                # Camp Type filter
                if selected_type != "All Types" and camp_type_col and camp_type_col in filtered_contests.columns:
                    filtered_contests = filtered_contests[filtered_contests[camp_type_col] == selected_type]
               
                # Display results
                st.subheader(f"📊 Results: {len(filtered_contests)} contests found")
               
                if not filtered_contests.empty:
                    # Calculate status for filtered contests
                    filtered_contests['Status'] = filtered_contests.apply(
                        lambda row: get_contest_status(row[start_date_col], row[end_date_col], today), 
                        axis=1
                    )
                    
                    # Stats
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Contests", len(filtered_contests))
                    with col2:
                        running_count = len(filtered_contests[filtered_contests['Status'] == 'running'])
                        st.metric("Running", running_count)
                    with col3:
                        upcoming_count = len(filtered_contests[filtered_contests['Status'] == 'upcoming'])
                        st.metric("Upcoming", upcoming_count)
                   
                    # Show as cards or table based on toggle
                    view_mode = st.radio("View Mode:", ["Cards View", "Table View"], horizontal=True, key="contest_view")
                   
                    if view_mode == "Cards View":
                        st.markdown("---")
                        for _, row in filtered_contests.iterrows():
                            card_html = create_contest_card(
                                row, camp_name_col, camp_type_col, start_date_col, end_date_col,
                                winner_date_col, kam_col, to_whom_col, eligibility_col, status=row['Status']
                            )
                            st.markdown(card_html, unsafe_allow_html=True)
                    else:
                        # Table view
                        display_cols = []
                        if camp_name_col: display_cols.append(camp_name_col)
                        if camp_type_col: display_cols.append(camp_type_col)
                        if eligibility_col: display_cols.append(eligibility_col)
                        if start_date_col: display_cols.append(start_date_col)
                        if end_date_col: display_cols.append(end_date_col)
                        if winner_date_col: display_cols.append(winner_date_col)
                        if kam_col: display_cols.append(kam_col)
                        if to_whom_col: display_cols.append(to_whom_col)
                       
                        if display_cols:
                            display_df = filtered_contests[display_cols + ['Status']].copy()
                           
                            # Format dates
                            for date_col in [start_date_col, end_date_col, winner_date_col]:
                                if date_col and date_col in display_df.columns:
                                    display_df[date_col] = display_df[date_col].apply(
                                        lambda x: x.strftime('%d-%m-%Y') if pd.notna(x) and hasattr(x, 'strftime') else str(x)
                                    )
                           
                            st.dataframe(display_df, use_container_width=True, height=400)
                   
                    # Download button
                    if display_cols:
                        csv = filtered_contests[display_cols + ['Status']].to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "📥 Download Results",
                            csv,
                            f"contests_{start_date}_to_{end_date}.csv",
                            "text/csv",
                            key="contest_download"
                        )
                else:
                    st.info("No contests found for selected filters")
                    
                    # Show troubleshooting help
                    if st.checkbox("🛠️ Show troubleshooting tips", key="troubleshoot"):
                        st.markdown("""
                        **Common reasons why no contests are found:**
                        1. **Date format mismatch**: Your sheet might use DD-MM-YYYY format while the app expects a different format
                        2. **Date parsing issues**: Check if dates in your sheet are properly formatted
                        3. **Date range too narrow**: Try selecting a wider date range
                        4. **Month/Year filters**: Try removing month/year filters
                        5. **Date overlap**: The contest might not overlap with your selected date range
                        
                        **Quick fixes:**
                        - Try selecting "All Years" and "All Months"
                        - Try a wider date range (e.g., whole month)
                        - Check if your contest dates are in DD-MM-YYYY format (like 08-12-2025)
                        """)
                        
                        if start_date_col in contests.columns:
                            st.write("**Sample dates from your sheet (first 5):**")
                            sample_dates = contests.head(5).copy()
                            display_sample = []
                            if camp_name_col: display_sample.append(camp_name_col)
                            if start_date_col: display_sample.append(start_date_col)
                            if end_date_col: display_sample.append(end_date_col)
                            st.write(sample_dates[display_sample])
                            
                            # Check for the specific contest you mentioned
                            search_term = "CAMP-334434"
                            if camp_name_col:
                                matching = contests[contests[camp_name_col].astype(str).str.contains(search_term, case=False, na=False)]
                                if not matching.empty:
                                    st.write(f"**Found contest '{search_term}':**")
                                    st.write(matching[[camp_name_col, start_date_col, end_date_col]])
    else:
        st.warning("No contest data available")
       
        # ============================================
        # CHECK WINNERS SECTION
        # ============================================
        elif section == "🏆 Check Winners":
            st.header("🏆 Check Winners")
           
            if not winners.empty and winner_sheet_name:
                st.success(f"✅ Loaded {len(winners)} winners from {winner_sheet_name}")
               
                # Date Range Filter for Winners
                st.subheader("📅 Filter by Contest Date Range")
               
                col1, col2 = st.columns(2)
               
                with col1:
                    # Get min and max dates from winners data
                    if 'Start Date' in winners.columns and pd.notna(winners['Start Date']).any():
                        try:
                            winner_min_date = winners['Start Date'].min().date()
                            winner_max_date = winners['Start Date'].max().date()
                        except:
                            winner_min_date = date(2023, 1, 1)
                            winner_max_date = today
                    else:
                        winner_min_date = date(2023, 1, 1)
                        winner_max_date = today
                   
                    winner_start_date = st.date_input(
                        "From Contest Start Date",
                        value=date(current_year, current_month, 1),
                        min_value=winner_min_date,
                        max_value=winner_max_date,
                        key="winner_start_date"
                    )
               
                with col2:
                    winner_end_date = st.date_input(
                        "To Contest End Date",
                        value=today,
                        min_value=winner_min_date,
                        max_value=winner_max_date,
                        key="winner_end_date"
                    )
               
                # Apply date filter to winners
                filtered_winners = winners.copy()
               
                if 'Start Date' in filtered_winners.columns and 'End Date' in filtered_winners.columns:
                    # Make sure dates are datetime
                    if not pd.api.types.is_datetime64_any_dtype(filtered_winners['Start Date']):
                        filtered_winners['Start Date'] = safe_to_datetime(filtered_winners['Start Date'])
                    if not pd.api.types.is_datetime64_any_dtype(filtered_winners['End Date']):
                        filtered_winners['End Date'] = safe_to_datetime(filtered_winners['End Date'])
                    
                    # Filter by date range (overlap)
                    date_mask = (
                        # Winners with contests starting in range
                        (
                            (filtered_winners['Start Date'].dt.date >= winner_start_date) &
                            (filtered_winners['Start Date'].dt.date <= winner_end_date)
                        ) |
                        # Winners with contests ending in range
                        (
                            (filtered_winners['End Date'].dt.date >= winner_start_date) &
                            (filtered_winners['End Date'].dt.date <= winner_end_date)
                        ) |
                        # Winners with contests spanning the range
                        (
                            (filtered_winners['Start Date'].dt.date <= winner_start_date) &
                            (filtered_winners['End Date'].dt.date >= winner_end_date)
                        )
                    )
                    filtered_winners = filtered_winners[date_mask]
                
                # Gift Status Statistics
                st.subheader("📊 Gift Delivery Status (for selected date range)")
                
                if gift_status_col and gift_status_col in filtered_winners.columns:
                    gift_stats = filtered_winners[gift_status_col].value_counts()
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Winners", len(filtered_winners))
                    with col2:
                        delivered = gift_stats.get('Delivered', 0)
                        st.metric("Delivered", delivered)
                    with col3:
                        pending = len(filtered_winners) - delivered
                        st.metric("Pending", pending)
                    with col4:
                        if 'Delivered' in gift_stats:
                            delivery_rate = (delivered / len(filtered_winners)) * 100
                            st.metric("Delivery Rate", f"{delivery_rate:.1f}%")
                        else:
                            st.metric("Delivery Rate", "0%")
                else:
                    st.metric("Total Winners", len(filtered_winners))
                
                st.markdown("---")
                
                # Winner search section
                st.subheader("🔍 Search Winner")
                
                # Use radio buttons for search option
                search_option = st.radio(
                    "Search by:",
                    ["BZID", "Phone Number", "Customer Name", "Gift Status"],
                    horizontal=True,
                    key="winner_search_option"
                )
                
                # Create a highlighted search area
                with st.container():
                    if search_option == "BZID":
                        search_col = 'businessid'
                        placeholder = "Enter BZID (e.g., BZID-1304114892)"
                    elif search_option == "Phone Number":
                        search_col = 'customer_phonenumber'
                        placeholder = "Enter phone number (e.g., 9709112026)"
                    elif search_option == "Gift Status":
                        search_col = gift_status_col if gift_status_col else 'Gift Status'
                        placeholder = "Enter status (e.g., Delivered, Pending)"
                    else:
                        search_col = 'customer_firstname'
                        placeholder = "Enter customer name"
                    
                    # Use a form for better UX
                    with st.form(key="search_form"):
                        # Add clear label and instructions
                        st.markdown(f"**Please enter the {search_option} to search:**")
                        
                        # Create a more visible input field
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            search_input = st.text_input(
                                "",
                                placeholder=placeholder,
                                key="winner_search_input",
                                label_visibility="collapsed"
                            )
                        with col2:
                            search_submitted = st.form_submit_button("🔍 Search", use_container_width=True)
                
                # Process search
                if search_input and search_col in filtered_winners.columns:
                    # Clean and search within filtered winners
                    filtered_winners[search_col] = filtered_winners[search_col].astype(str).fillna('')
                    results = filtered_winners[filtered_winners[search_col].str.contains(search_input.strip(), case=False, na=False)]
                   
                    if not results.empty:
                        st.success(f"✅ Found {len(results)} winner(s) in selected date range")
                       
                        # Group by customer to show all contests they won
                        if 'customer_firstname' in results.columns and 'businessid' in results.columns:
                            grouped_results = results.groupby(['customer_firstname', 'businessid'])
                           
                            for (cust_name, bzid), group in grouped_results:
                                with st.expander(f"👤 {cust_name} (BZID: {bzid}) - {len(group)} win(s)", expanded=True):
                                    for idx, (_, row) in enumerate(group.iterrows()):
                                        st.markdown(f"---")
                                        st.markdown(f"**Win #{idx+1}**")
                                       
                                        col1, col2 = st.columns([2, 1])
                                       
                                        with col1:
                                            # Contest Details
                                            camp_desc = str(row.get('Camp Description', 'N/A')).strip()
                                            contest_eligibility = str(row.get('Contest', 'N/A')).strip()
                                            gift = str(row.get('Gift', 'N/A')).strip()
                                           
                                            # Get dates from winner data
                                            start_date_val = row.get('Start Date', None)
                                            end_date_val = row.get('End Date', None)
                                            winner_date_val = row.get('Winner Announcement Date', None)
                                           
                                            # Format dates
                                            start_date_str = 'N/A'
                                            end_date_str = 'N/A'
                                            winner_date_str = 'N/A'
                                           
                                            if pd.notna(start_date_val):
                                                if hasattr(start_date_val, 'strftime'):
                                                    start_date_str = start_date_val.strftime('%d-%m-%Y')
                                                else:
                                                    start_date_str = str(start_date_val)
                                           
                                            if pd.notna(end_date_val):
                                                if hasattr(end_date_val, 'strftime'):
                                                    end_date_str = end_date_val.strftime('%d-%m-%Y')
                                                else:
                                                    end_date_str = str(end_date_val)
                                            
                                            if pd.notna(winner_date_val):
                                                if hasattr(winner_date_val, 'strftime'):
                                                    winner_date_str = winner_date_val.strftime('%d-%m-%Y')
                                                else:
                                                    winner_date_str = str(winner_date_val)
                                           
                                            st.markdown(f"""
                                            **Camp Description:** {camp_desc}  
                                            **Eligibility:** {contest_eligibility}  
                                            **Prize:** {gift}  
                                            **Contest Duration:** {start_date_str} to {end_date_str}
                                            """)
                                       
                                        with col2:
                                            # Winner Details with Gift Status
                                            winner_name = row.get('customer_firstname', 'N/A')
                                            phone = row.get('customer_phonenumber', 'N/A')
                                            store = row.get('business_displayname', 'N/A')
                                            bzid_val = row.get('businessid', 'N/A')
                                            
                                            st.markdown(f"""
                                            **Name:** {winner_name}  
                                            **Phone:** {phone}  
                                            **Store:** {store}  
                                            **BZID:** {bzid_val}  
                                            **Winner Date:** {winner_date_str}
                                            """)
                                            
                                            # Display Gift Status with badge
                                            if gift_status_col and gift_status_col in row:
                                                gift_status_val = row[gift_status_col]
                                                if pd.notna(gift_status_val) and str(gift_status_val).strip():
                                                    gift_status_str = str(gift_status_val).strip()
                                                    gift_status_lower = gift_status_str.lower()
                                                    if 'delivered' in gift_status_lower:
                                                        gift_status_class = "gift-delivered"
                                                    elif 'pending' in gift_status_lower or 'not' in gift_status_lower:
                                                        gift_status_class = "gift-pending"
                                                    else:
                                                        gift_status_class = "gift-not-found"
                                                    
                                                    st.markdown(f"**Gift Status:** <span class='{gift_status_class}'>{gift_status_str}</span>", unsafe_allow_html=True)
                                                else:
                                                    st.markdown("**Gift Status:** N/A")
                    else:
                        st.warning("⚠️ No winners found for the search criteria in selected date range")
                else:
                    st.info("👆 Enter search criteria above to find winners within selected date range")
                   
                    # Show sample of recent winners with Gift Status
                    if len(filtered_winners) > 0:
                        st.subheader("🎯 Recent Winners (in selected date range)")
                        recent_winners = filtered_winners.head(10)  # Show top 10
                       
                        for idx, (_, row) in enumerate(recent_winners.iterrows()):
                            # Get gift status value
                            gift_status_val = row.get(gift_status_col, 'N/A') if gift_status_col else 'N/A'
                            
                            # Determine badge color
                            if gift_status_val == 'Delivered':
                                badge_color = "🟢"
                            elif gift_status_val == 'Pending':
                                badge_color = "🟡"
                            else:
                                badge_color = "🔴"
                            
                            with st.expander(f"{badge_color} {row.get('customer_firstname', 'N/A')} won {row.get('Gift', 'N/A')} - Status: {gift_status_val}", expanded=False):
                                st.markdown(f"""
                                **Contest:** {row.get('Camp Description', 'N/A')}  
                                **Date:** {row.get('Start Date', 'N/A')} to {row.get('End Date', 'N/A')}  
                                **Store:** {row.get('business_displayname', 'N/A')}  
                                **Gift Status:** **{gift_status_val}**
                                """)
                
                # Download winners data
                if len(filtered_winners) > 0:
                    st.markdown("---")
                    st.subheader("📥 Download Winners Data")
                    
                    # Create a downloadable CSV
                    download_cols = [
                        'Camp Description', 'Contest', 'Gift', 'Start Date', 'End Date',
                        'businessid', 'customer_customerid', 'customer_phonenumber',
                        'customer_firstname', 'business_displayname', 'address_addresslocality',
                        'Winner Announcement Date'
                    ]
                    
                    # Add Gift Status column if available
                    if gift_status_col and gift_status_col in filtered_winners.columns:
                        download_cols.append(gift_status_col)
                    
                    # Filter to only available columns
                    available_cols = [col for col in download_cols if col in filtered_winners.columns]
                    download_df = filtered_winners[available_cols].copy()
                    
                    # Format dates for download
                    for date_col in ['Start Date', 'End Date', 'Winner Announcement Date']:
                        if date_col in download_df.columns:
                            download_df[date_col] = download_df[date_col].apply(
                                lambda x: x.strftime('%d-%m-%Y') if pd.notna(x) and hasattr(x, 'strftime') else str(x)
                            )
                    
                    csv_data = download_df.to_csv(index=False).encode('utf-8')
                    
                    st.download_button(
                        "📥 Download Winners List",
                        csv_data,
                        f"winners_{winner_start_date}_to_{winner_end_date}.csv",
                        "text/csv",
                        key="winners_download"
                    )
            else:
                st.warning("No winner data available")
       
    except Exception as e:
        st.error(f"Error: {str(e)}")
       
else:
    st.error("Connection failed")

# ============================================
# FOOTER
# ============================================
st.sidebar.markdown("---")
st.sidebar.caption(f"Last updated: {datetime.now().strftime('%d %b %Y %H:%M')}")

if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()
