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

# Function to safely convert to datetime
def safe_to_datetime(series):
    """Safely convert series to datetime"""
    try:
        return pd.to_datetime(series, errors='coerce', dayfirst=True)
    except:
        return pd.NaT

# Function to create nice contest cards
def create_contest_card(row, camp_name_col, camp_type_col, start_date_col, end_date_col, 
                       winner_date_col, kam_col, to_whom_col):
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
    
    # Create card
    card_html = f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    ">
        <h3 style="margin: 0 0 10px 0; color: white;">{camp_name}</h3>
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
            
            # Fix dates safely
            if start_date_col:
                contests[start_date_col] = safe_to_datetime(contests[start_date_col])
                contests['Start_Date'] = contests[start_date_col]
                contests['Year'] = contests['Start_Date'].dt.year
                contests['Month'] = contests['Start_Date'].dt.month_name()
                contests['Month_Num'] = contests['Start_Date'].dt.month
            
            if end_date_col:
                contests[end_date_col] = safe_to_datetime(contests[end_date_col])
            
            if winner_date_col:
                contests[winner_date_col] = safe_to_datetime(contests[winner_date_col])
        
        # Process winner data
        if not winners.empty:
            # Fix dates in winner data safely
            if 'Start Date' in winners.columns:
                winners['Start Date'] = safe_to_datetime(winners['Start Date'])
            if 'End Date' in winners.columns:
                winners['End Date'] = safe_to_datetime(winners['End Date'])
            if 'Winner Announcement Date' in winners.columns:
                winners['Winner Announcement Date'] = safe_to_datetime(winners['Winner Announcement Date'])
        
        today = datetime.now().date()
        current_month = today.month
        current_year = today.year
        
        # ============================================
        # CONTEST DASHBOARD SECTION
        # ============================================
        if section == "🎯 Contest Dashboard":
            st.header("📊 Contest Dashboard")
            
            if not contests.empty and start_date_col and end_date_col:
                # Current month contests
                current_month_contests = contests[
                    (contests['Year'] == current_year) & 
                    (contests['Month_Num'] == current_month)
                ]
                
                # ============================================
                # CURRENT RUNNING CONTESTS
                # ============================================
                st.subheader("🏃 Currently Running Contests")
                
                current_running = contests[
                    (contests[start_date_col].dt.date <= today) & 
                    (contests[end_date_col].dt.date >= today)
                ]
                
                if not current_running.empty:
                    # Show stats
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Active Contests", len(current_running))
                    with col2:
                        unique_types = current_running[camp_type_col].nunique() if camp_type_col else 0
                        st.metric("Campaign Types", unique_types)
                    with col3:
                        unique_kams = current_running[kam_col].nunique() if kam_col else 0
                        st.metric("Active KAMs", unique_kams)
                    
                    st.markdown("---")
                    
                    # Show contest cards
                    for _, row in current_running.iterrows():
                        card_html = create_contest_card(
                            row, camp_name_col, camp_type_col, start_date_col, end_date_col,
                            winner_date_col, kam_col, to_whom_col
                        )
                        st.markdown(card_html, unsafe_allow_html=True)
                else:
                    st.info("🎉 No contests running today! All caught up!")
                
                # ============================================
                # UPCOMING CONTESTS
                # ============================================
                st.subheader("📅 Upcoming Contests (This Month)")
                
                upcoming_this_month = contests[
                    (contests[start_date_col].dt.date > today) & 
                    (contests['Year'] == current_year) & 
                    (contests['Month_Num'] == current_month)
                ]
                
                if not upcoming_this_month.empty:
                    # Show stats
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Upcoming", len(upcoming_this_month))
                    with col2:
                        days_to_next = (upcoming_this_month[start_date_col].min().date() - today).days
                        st.metric("Days to Next", days_to_next if days_to_next > 0 else 0)
                    
                    st.markdown("---")
                    
                    # Show upcoming contests
                    for _, row in upcoming_this_month.iterrows():
                        card_html = create_contest_card(
                            row, camp_name_col, camp_type_col, start_date_col, end_date_col,
                            winner_date_col, kam_col, to_whom_col
                        )
                        st.markdown(card_html, unsafe_allow_html=True)
                else:
                    st.info("📭 No upcoming contests this month")
        
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
                    start_datetime = pd.Timestamp(start_date)
                    end_datetime = pd.Timestamp(end_date)
                    
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
                            card_html = create_contest_card(
                                row, camp_name_col, camp_type_col, start_date_col, end_date_col,
                                winner_date_col, kam_col, to_whom_col
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
