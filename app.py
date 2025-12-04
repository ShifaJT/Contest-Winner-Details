import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import gspread
from google.oauth2.service_account import Credentials
import re

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

# Function to detect date format
def detect_date_format(date_str):
    """Detect if date is DD-MM-YYYY or MM-DD-YYYY"""
    if pd.isna(date_str) or not isinstance(date_str, str):
        return None
    
    # Remove any time part
    date_str = str(date_str).split()[0]
    
    # Check if it's already a datetime object
    if isinstance(date_str, (datetime, pd.Timestamp)):
        return "already_datetime"
    
    # Check common date patterns
    dd_mm_yyyy_pattern = r'^\d{1,2}-\d{1,2}-\d{4}$'
    mm_dd_yyyy_pattern = r'^\d{1,2}-\d{1,2}-\d{4}$'
    dd_mm_yy_pattern = r'^\d{1,2}-\d{1,2}-\d{2}$'
    
    if re.match(dd_mm_yyyy_pattern, date_str) or re.match(dd_mm_yy_pattern, date_str):
        # Try to parse as DD-MM-YYYY first
        try:
            parts = date_str.split('-')
            if len(parts) == 3:
                day = int(parts[0])
                month = int(parts[1])
                year = int(parts[2])
                
                # If year is 2 digits, convert to 4 digits
                if year < 100:
                    year = 2000 + year
                
                # Validate if it's a valid date in DD-MM format
                if 1 <= month <= 12 and 1 <= day <= 31:
                    # Check if day could be a month (ambiguous)
                    if day <= 12 and month <= 12:
                        # Ambiguous case (e.g., 04-05-2025 could be April 5 or May 4)
                        return "ambiguous"
                    elif day > 12:
                        # Day > 12, so it must be DD-MM
                        return "dd_mm_yyyy"
                    else:
                        # Day <= 12, month <= 12, need to decide
                        # Look at other dates in the column to decide
                        return "ambiguous"
        except:
            pass
    
    return None

# Function to smart parse dates
def smart_to_datetime(series, sample_size=20):
    """Smart date parsing that detects format"""
    if series.empty:
        return pd.Series([pd.NaT] * len(series), index=series.index)
    
    result = pd.Series([pd.NaT] * len(series), index=series.index)
    
    # Take a sample to detect format
    sample = series.dropna().head(sample_size)
    if sample.empty:
        # Try to parse everything
        try:
            return pd.to_datetime(series, errors='coerce', dayfirst=True)
        except:
            try:
                return pd.to_datetime(series, errors='coerce', dayfirst=False)
            except:
                return result
    
    # Analyze sample dates
    formats_found = []
    for val in sample:
        fmt = detect_date_format(val)
        if fmt:
            formats_found.append(fmt)
    
    # Count format occurrences
    from collections import Counter
    format_counts = Counter(formats_found)
    
    # Determine best format
    best_format = None
    if format_counts:
        best_format = format_counts.most_common(1)[0][0]
    
    # Parse based on detected format
    if best_format == "dd_mm_yyyy":
        st.sidebar.info("📅 Detected date format: DD-MM-YYYY")
        return pd.to_datetime(series, errors='coerce', dayfirst=True)
    elif best_format == "already_datetime":
        return series
    else:
        # Try both formats and see which gives more valid dates
        try_dayfirst = pd.to_datetime(series, errors='coerce', dayfirst=True)
        try_monthfirst = pd.to_datetime(series, errors='coerce', dayfirst=False)
        
        # Count valid dates for each
        valid_dayfirst = try_dayfirst.notna().sum()
        valid_monthfirst = try_monthfirst.notna().sum()
        
        if valid_dayfirst > valid_monthfirst:
            st.sidebar.info("📅 Using DD-MM-YYYY format (more valid dates)")
            return try_dayfirst
        elif valid_monthfirst > valid_dayfirst:
            st.sidebar.info("📅 Using MM-DD-YYYY format (more valid dates)")
            return try_monthfirst
        else:
            # Equal valid dates, use dayfirst as default
            st.sidebar.warning("⚠️ Ambiguous dates, using DD-MM-YYYY format")
            return try_dayfirst

# Function to create nice contest cards
def create_contest_card(row, camp_name_col, camp_type_col, start_date_col, end_date_col, 
                       winner_date_col, kam_col, to_whom_col, is_running=False):
    """Create a nice looking contest card"""
    camp_name = row[camp_name_col] if camp_name_col and camp_name_col in row and pd.notna(row[camp_name_col]) else 'N/A'
    camp_type = row[camp_type_col] if camp_type_col and camp_type_col in row and pd.notna(row[camp_type_col]) else 'N/A'
    
    start_date = 'N/A'
    if start_date_col and start_date_col in row and pd.notna(row[start_date_col]):
        if hasattr(row[start_date_col], 'strftime'):
            start_date = row[start_date_col].strftime('%d %b %Y')
        else:
            start_date = str(row[start_date_col])
    
    end_date = 'N/A'
    if end_date_col and end_date_col in row and pd.notna(row[end_date_col]):
        if hasattr(row[end_date_col], 'strftime'):
            end_date = row[end_date_col].strftime('%d %b %Y')
        else:
            end_date = str(row[end_date_col])
    
    winner_date = 'N/A'
    if winner_date_col and winner_date_col in row and pd.notna(row[winner_date_col]):
        if hasattr(row[winner_date_col], 'strftime'):
            winner_date = row[winner_date_col].strftime('%d %b %Y')
        else:
            winner_date = str(row[winner_date_col])
    
    kam = row[kam_col] if kam_col and kam_col in row and pd.notna(row[kam_col]) else 'N/A'
    to_whom = row[to_whom_col] if to_whom_col and to_whom_col in row and pd.notna(row[to_whom_col]) else 'N/A'
    
    # Calculate days left if contest is running
    days_left = ""
    if is_running and end_date_col and end_date_col in row and pd.notna(row[end_date_col]):
        if hasattr(row[end_date_col], 'date'):
            end_date_obj = row[end_date_col].date()
            today = datetime.now().date()
            days_left_int = (end_date_obj - today).days
            if days_left_int >= 0:
                days_left = f"<br><strong>⏳ Days Left:</strong> {days_left_int} days"
    
    # Different gradient for running contests
    if is_running:
        gradient = "linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%)"  # Green for running
        badge = "🏃 RUNNING NOW"
    else:
        gradient = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"  # Purple for upcoming
        badge = "📅 UPCOMING"
    
    # Create card
    card_html = f"""
    <div style="
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
st.set_page_config(page_title="Contest Check", layout="wide")
st.title("🎯 Contest Checker")
st.markdown("---")

# Create navigation menu
st.sidebar.title("📊 Navigation")
section = st.sidebar.radio(
    "Go to:",
    ["🎯 Contest Dashboard", "🔍 Filter Contests", "🏆 Check Winners"]
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
        
        # Process contest data
        if not contests.empty:
            # Find important columns
            camp_name_col = find_column(contests, ['Camp Name', 'Campaign Name', 'Camp Description', 'Camp'])
            camp_type_col = find_column(contests, ['Camp Type', 'Type', 'Category'])
            start_date_col = find_column(contests, ['Start Date', 'StartDate', 'Start'])
            end_date_col = find_column(contests, ['End Date', 'EndDate', 'End'])
            winner_date_col = find_column(contests, ['Winner Announcement Date', 'Winner Date', 'Announcement Date'])
            kam_col = find_column(contests, ['KAM', 'Owner', 'Manager', 'Responsible'])
            to_whom_col = find_column(contests, ['To Whom?', 'To Whom', 'Assigned To', 'Team'])
            
            # Smart date parsing with format detection
            if start_date_col:
                contests[start_date_col] = smart_to_datetime(contests[start_date_col])
                contests['Start_Date'] = contests[start_date_col]
                contests['Year'] = contests['Start_Date'].dt.year
                contests['Month'] = contests['Start_Date'].dt.month_name()
                contests['Month_Num'] = contests['Start_Date'].dt.month
            
            if end_date_col:
                contests[end_date_col] = smart_to_datetime(contests[end_date_col])
            
            if winner_date_col:
                contests[winner_date_col] = smart_to_datetime(contests[winner_date_col])
            
            # Show date parsing stats
            if start_date_col:
                valid_dates = contests[start_date_col].notna().sum()
                total_dates = len(contests)
                st.sidebar.info(f"📊 Dates parsed: {valid_dates}/{total_dates}")
        
        # Process winner data with smart date parsing
        if not winners.empty:
            # Smart date parsing for winners
            if 'Start Date' in winners.columns:
                winners['Start Date'] = smart_to_datetime(winners['Start Date'])
            
            if 'End Date' in winners.columns:
                winners['End Date'] = smart_to_datetime(winners['End Date'])
            
            if 'Winner Announcement Date' in winners.columns:
                winners['Winner Announcement Date'] = smart_to_datetime(winners['Winner Announcement Date'])
        
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
                
                # Running contests
                running_contests = contests[
                    (contests[start_date_col].dt.date <= today) & 
                    (contests[end_date_col].dt.date >= today)
                ]
                
                # Upcoming contests (this month)
                upcoming_this_month = contests[
                    (contests[start_date_col].dt.date > today) & 
                    (contests['Year'] == current_year) & 
                    (contests['Month_Num'] == current_month)
                ]
                
                # Recently ended (last 7 days)
                recently_ended = contests[
                    (contests[end_date_col].dt.date < today) & 
                    (contests[end_date_col].dt.date >= (today - timedelta(days=7)))
                ]
                
                # Display stats in columns
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Contests", total_contests)
                
                with col2:
                    st.metric("Running Now", len(running_contests))
                
                with col3:
                    st.metric("Upcoming This Month", len(upcoming_this_month))
                
                with col4:
                    st.metric("Ended Last 7 Days", len(recently_ended))
                
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
                        if kam_col and kam_col in running_contests.columns:
                            running_kams = running_contests[kam_col].nunique()
                            st.metric("Active KAMs", running_kams)
                    
                    with stats_col3:
                        # Calculate average days left
                        if end_date_col and end_date_col in running_contests.columns:
                            try:
                                days_left_list = []
                                for _, row in running_contests.iterrows():
                                    if hasattr(row[end_date_col], 'date'):
                                        end_date_obj = row[end_date_col].date()
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
                            winner_date_col, kam_col, to_whom_col, is_running=True
                        )
                        st.markdown(card_html, unsafe_allow_html=True)
                else:
                    st.subheader("🏃 Currently Running Contests")
                    st.info("🎉 No contests running today! All caught up!")
                
                # ============================================
                # UPCOMING CONTESTS
                # ============================================
                if not upcoming_this_month.empty:
                    st.subheader("📅 Upcoming Contests (This Month)")
                    st.info(f"**Scheduled: {len(upcoming_this_month)} contest(s) this month**")
                    
                    # Show stats for upcoming contests
                    up_stats_col1, up_stats_col2 = st.columns(2)
                    
                    with up_stats_col1:
                        # Days to next contest
                        try:
                            next_contest_date = upcoming_this_month[start_date_col].min().date()
                            days_to_next = (next_contest_date - today).days
                            st.metric("Days to Next Contest", days_to_next if days_to_next > 0 else 0)
                        except:
                            st.metric("Days to Next Contest", "N/A")
                    
                    with up_stats_col2:
                        # Contest types in upcoming
                        if camp_type_col and camp_type_col in upcoming_this_month.columns:
                            upcoming_types = upcoming_this_month[camp_type_col].nunique()
                            st.metric("Upcoming Types", upcoming_types)
                    
                    st.markdown("---")
                    
                    # Show upcoming contest cards
                    for _, row in upcoming_this_month.iterrows():
                        card_html = create_contest_card(
                            row, camp_name_col, camp_type_col, start_date_col, end_date_col,
                            winner_date_col, kam_col, to_whom_col, is_running=False
                        )
                        st.markdown(card_html, unsafe_allow_html=True)
                else:
                    st.subheader("📅 Upcoming Contests (This Month)")
                    st.info("📭 No upcoming contests this month")
                
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
                            end_date = row[end_date_col].strftime('%d %b') if hasattr(row[end_date_col], 'strftime') else 'N/A'
                            
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
        # FILTER CONTESTS SECTION
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
                            min_date = contests[start_date_col].min().date()
                            max_date = contests[start_date_col].max().date()
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
                
                # Apply filters
                filtered_contests = contests.copy()
                
                # Date range filter
                if start_date_col and end_date_col:
                    # Filter by date range
                    filtered_contests = filtered_contests[
                        (filtered_contests[start_date_col].dt.date >= start_date) & 
                        (filtered_contests[end_date_col].dt.date <= end_date)
                    ]
                
                # Year filter
                if selected_year != "All Years" and 'Year' in filtered_contests.columns:
                    filtered_contests = filtered_contests[filtered_contests['Year'] == selected_year]
                
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
                    # Stats
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Contests", len(filtered_contests))
                    with col2:
                        if camp_type_col and camp_type_col in filtered_contests.columns:
                            unique_types = filtered_contests[camp_type_col].nunique()
                            st.metric("Campaign Types", unique_types)
                        else:
                            st.metric("Campaign Types", "N/A")
                    with col3:
                        if kam_col and kam_col in filtered_contests.columns:
                            unique_kams = filtered_contests[kam_col].nunique()
                            st.metric("KAMs Involved", unique_kams)
                        else:
                            st.metric("KAMs Involved", "N/A")
                    
                    # Show as cards or table based on toggle
                    view_mode = st.radio("View Mode:", ["Cards View", "Table View"], horizontal=True, key="contest_view")
                    
                    if view_mode == "Cards View":
                        st.markdown("---")
                        for _, row in filtered_contests.iterrows():
                            # Check if contest is currently running
                            is_running = False
                            if start_date_col and end_date_col:
                                try:
                                    start_dt = row[start_date_col].date() if hasattr(row[start_date_col], 'date') else None
                                    end_dt = row[end_date_col].date() if hasattr(row[end_date_col], 'date') else None
                                    if start_dt and end_dt and start_dt <= today <= end_dt:
                                        is_running = True
                                except:
                                    pass
                            
                            card_html = create_contest_card(
                                row, camp_name_col, camp_type_col, start_date_col, end_date_col,
                                winner_date_col, kam_col, to_whom_col, is_running=is_running
                            )
                            st.markdown(card_html, unsafe_allow_html=True)
                    else:
                        # Table view
                        display_cols = []
                        if camp_name_col: display_cols.append(camp_name_col)
                        if camp_type_col: display_cols.append(camp_type_col)
                        if start_date_col: display_cols.append(start_date_col)
                        if end_date_col: display_cols.append(end_date_col)
                        if winner_date_col: display_cols.append(winner_date_col)
                        if kam_col: display_cols.append(kam_col)
                        if to_whom_col: display_cols.append(to_whom_col)
                        
                        if display_cols:
                            display_df = filtered_contests[display_cols].copy()
                            
                            # Format dates
                            for date_col in [start_date_col, end_date_col, winner_date_col]:
                                if date_col and date_col in display_df.columns:
                                    display_df[date_col] = display_df[date_col].dt.strftime('%d-%m-%Y')
                            
                            st.dataframe(display_df, use_container_width=True, height=400)
                    
                    # Download button
                    if display_cols:
                        csv = filtered_contests[display_cols].to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "📥 Download Results",
                            csv,
                            f"contests_{start_date}_to_{end_date}.csv",
                            "text/csv",
                            key="contest_download"
                        )
                else:
                    st.info("No contests found for selected filters")
            else:
                st.warning("No contest data available")
        
        # ============================================
        # CHECK WINNERS SECTION WITH DATE FILTER
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
                    filtered_winners = filtered_winners[
                        (filtered_winners['Start Date'].dt.date >= winner_start_date) & 
                        (filtered_winners['End Date'].dt.date <= winner_end_date)
                    ]
                
                # Winner search section
                st.subheader("🔍 Search Winner")
                
                search_option = st.radio(
                    "Search by:",
                    ["BZID", "Phone Number", "Customer Name"],
                    horizontal=True,
                    key="winner_search_option"
                )
                
                if search_option == "BZID":
                    search_col = 'businessid'
                    placeholder = "Enter BZID (e.g., BZID-1304114892)"
                elif search_option == "Phone Number":
                    search_col = 'customer_phonenumber'
                    placeholder = "Enter phone number (e.g., 9709112026)"
                else:
                    search_col = 'customer_firstname'
                    placeholder = "Enter customer name"
                
                search_input = st.text_input(placeholder, key="winner_search_input")
                
                # Quick stats for filtered period
                st.subheader("📊 Quick Stats (for selected date range)")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Winners", len(filtered_winners))
                with col2:
                    if 'Gift' in filtered_winners.columns:
                        unique_gifts = filtered_winners['Gift'].nunique()
                        st.metric("Unique Prizes", unique_gifts)
                    else:
                        st.metric("Unique Prizes", 0)
                with col3:
                    if 'customer_firstname' in filtered_winners.columns:
                        unique_customers = filtered_winners['customer_firstname'].nunique()
                        st.metric("Unique Customers", unique_customers)
                    else:
                        st.metric("Unique Customers", 0)
                
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
                                            
                                            # Format dates
                                            start_date_str = 'N/A'
                                            end_date_str = 'N/A'
                                            
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
                                            
                                            st.markdown(f"""
                                            **Camp Description:** {camp_desc}  
                                            **Eligibility:** {contest_eligibility}  
                                            **Prize:** {gift}  
                                            **Contest Duration:** {start_date_str} to {end_date_str}
                                            """)
                                        
                                        with col2:
                                            # Winner Details
                                            st.markdown(f"""
                                            **Name:** {row.get('customer_firstname', 'N/A')}  
                                            **Phone:** {row.get('customer_phonenumber', 'N/A')}  
                                            **Store:** {row.get('business_displayname', 'N/A')}  
                                            **BZID:** {row.get('businessid', 'N/A')}  
                                            **Winner Date:** {row.get('Winner Announcement Date', 'N/A')}
                                            """)
                    else:
                        st.warning("No winners found for the search criteria in selected date range")
                elif search_input:
                    st.info("👆 Searching within filtered date range...")
                else:
                    st.info("👆 Enter search criteria above to find winners within selected date range")
                    
                    # Show sample of recent winners
                    if len(filtered_winners) > 0:
                        st.subheader("🎯 Recent Winners (in selected date range)")
                        recent_winners = filtered_winners.head(10)  # Show top 10
                        
                        for idx, (_, row) in enumerate(recent_winners.iterrows()):
                            with st.expander(f"{row.get('customer_firstname', 'N/A')} won {row.get('Gift', 'N/A')}", expanded=False):
                                st.markdown(f"""
                                **Contest:** {row.get('Camp Description', 'N/A')}  
                                **Date:** {row.get('Start Date', 'N/A')} to {row.get('End Date', 'N/A')}  
                                **Store:** {row.get('business_displayname', 'N/A')}
                                """)
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
