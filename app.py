import streamlit as st
import pandas as pd
from datetime import datetime, date
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

# App
st.set_page_config(page_title="Contest Check", layout="wide")
st.title("🎯 Contest Checker")
st.markdown("---")

# Connect
client = connect_sheets()

if client:
    try:
        sheet = client.open_by_key("1E2qxc1kZttPQMmSXCVXFaQKVNLl_Nhe4uUPBrzf7B3U")
        st.success("✅ Connected!")
        
        # ============================================
        # LOAD CONTEST DETAILS SHEET
        # ============================================
        try:
            contest_ws = sheet.worksheet("Contest Details")
            contest_data = contest_ws.get_all_records()
            contests = pd.DataFrame(contest_data)
            
            if not contests.empty:
                st.success(f"📋 {len(contests)} contests loaded from Contest Details")
                
                # Show columns for debugging
                with st.expander("📋 See Contest Data Columns"):
                    st.write("Available columns:", list(contests.columns))
                    st.write("First row sample:", contests.iloc[0].to_dict())
                
                # Fix dates - try to find date columns
                for col in contests.columns:
                    if 'date' in col.lower() or 'Date' in col:
                        try:
                            contests[col] = pd.to_datetime(contests[col], errors='coerce', dayfirst=True)
                        except:
                            continue
                
                # Find important columns
                camp_name_col = find_column(contests, ['Camp Name', 'Campaign Name', 'Camp Description', 'Camp'])
                camp_type_col = find_column(contests, ['Camp Type', 'Type', 'Category'])
                start_date_col = find_column(contests, ['Start Date', 'StartDate', 'Start'])
                end_date_col = find_column(contests, ['End Date', 'EndDate', 'End'])
                winner_date_col = find_column(contests, ['Winner Announcement Date', 'Winner Date', 'Announcement Date'])
                kam_col = find_column(contests, ['KAM', 'Owner', 'Manager', 'Responsible'])
                to_whom_col = find_column(contests, ['To Whom?', 'To Whom', 'Assigned To', 'Team'])
                
                # Add year and month columns for filtering
                if start_date_col:
                    contests['Start_Date'] = contests[start_date_col]
                    contests['Year'] = contests['Start_Date'].dt.year
                    contests['Month'] = contests['Start_Date'].dt.month_name()
                    contests['Month_Num'] = contests['Start_Date'].dt.month
                
                # ============================================
                # CURRENT CONTESTS - QUICK VIEW WITH DETAILS
                # ============================================
                st.header("📢 Current Contests (Quick View)")
                
                today = datetime.now().date()
                current_month = today.month
                current_year = today.year
                
                # Current month contests
                current_month_contests = contests[
                    (contests['Year'] == current_year) & 
                    (contests['Month_Num'] == current_month)
                ]
                
                if not current_month_contests.empty:
                    st.info(f"**This month ({today.strftime('%B %Y')}): {len(current_month_contests)} contests**")
                    
                    # Show current running contests
                    if start_date_col and end_date_col:
                        current_running = contests[
                            (contests[start_date_col].dt.date <= today) & 
                            (contests[end_date_col].dt.date >= today)
                        ]
                        
                        if not current_running.empty:
                            st.subheader("🏃 Running Now")
                            
                            # Create display dataframe
                            running_display_cols = []
                            if camp_name_col: running_display_cols.append(camp_name_col)
                            if camp_type_col: running_display_cols.append(camp_type_col)
                            if start_date_col: running_display_cols.append(start_date_col)
                            if end_date_col: running_display_cols.append(end_date_col)
                            if winner_date_col: running_display_cols.append(winner_date_col)
                            if kam_col: running_display_cols.append(kam_col)
                            if to_whom_col: running_display_cols.append(to_whom_col)
                            
                            if running_display_cols:
                                running_display = current_running[running_display_cols].copy()
                                
                                # Format dates
                                for date_col in [start_date_col, end_date_col, winner_date_col]:
                                    if date_col and date_col in running_display.columns:
                                        running_display[date_col] = running_display[date_col].dt.strftime('%d-%m-%Y')
                                
                                # Rename columns for display
                                rename_dict = {
                                    camp_name_col: 'Camp Name',
                                    camp_type_col: 'Camp Type',
                                    start_date_col: 'Start Date',
                                    end_date_col: 'End Date',
                                    winner_date_col: 'Winner Announcement Date',
                                    kam_col: 'KAM',
                                    to_whom_col: 'To Whom?'
                                }
                                running_display = running_display.rename(columns={k: v for k, v in rename_dict.items() if k})
                                
                                st.dataframe(running_display, use_container_width=True)
                            else:
                                # Show simple list if columns not found
                                for _, row in current_running.iterrows():
                                    camp_name = row[camp_name_col] if camp_name_col else 'N/A'
                                    camp_type = row[camp_type_col] if camp_type_col else 'N/A'
                                    start_date = row[start_date_col].strftime('%d-%m-%Y') if start_date_col and pd.notna(row.get(start_date_col)) else 'N/A'
                                    end_date = row[end_date_col].strftime('%d-%m-%Y') if end_date_col and pd.notna(row.get(end_date_col)) else 'N/A'
                                    
                                    st.markdown(f"""
                                    **{camp_name}**
                                    - Type: {camp_type}
                                    - Period: {start_date} to {end_date}
                                    ---
                                    """)
                        else:
                            st.info("No contests running today")
                    
                    # Upcoming this month
                    upcoming_this_month = contests[
                        (contests[start_date_col].dt.date > today) & 
                        (contests['Year'] == current_year) & 
                        (contests['Month_Num'] == current_month)
                    ] if start_date_col else pd.DataFrame()
                    
                    if not upcoming_this_month.empty:
                        st.subheader("📅 Upcoming This Month")
                        
                        # Create display dataframe for upcoming
                        upcoming_display_cols = []
                        if camp_name_col: upcoming_display_cols.append(camp_name_col)
                        if camp_type_col: upcoming_display_cols.append(camp_type_col)
                        if start_date_col: upcoming_display_cols.append(start_date_col)
                        if end_date_col: upcoming_display_cols.append(end_date_col)
                        if winner_date_col: upcoming_display_cols.append(winner_date_col)
                        if kam_col: upcoming_display_cols.append(kam_col)
                        if to_whom_col: upcoming_display_cols.append(to_whom_col)
                        
                        if upcoming_display_cols:
                            upcoming_display = upcoming_this_month[upcoming_display_cols].copy()
                            
                            # Format dates
                            for date_col in [start_date_col, end_date_col, winner_date_col]:
                                if date_col and date_col in upcoming_display.columns:
                                    upcoming_display[date_col] = upcoming_display[date_col].dt.strftime('%d-%m-%Y')
                            
                            # Rename columns for display
                            rename_dict = {
                                camp_name_col: 'Camp Name',
                                camp_type_col: 'Camp Type',
                                start_date_col: 'Start Date',
                                end_date_col: 'End Date',
                                winner_date_col: 'Winner Announcement Date',
                                kam_col: 'KAM',
                                to_whom_col: 'To Whom?'
                            }
                            upcoming_display = upcoming_display.rename(columns={k: v for k, v in rename_dict.items() if k})
                            
                            st.dataframe(upcoming_display, use_container_width=True)
                        else:
                            # Show simple list if columns not found
                            for _, row in upcoming_this_month.iterrows():
                                camp_name = row[camp_name_col] if camp_name_col else 'N/A'
                                camp_type = row[camp_type_col] if camp_type_col else 'N/A'
                                start_date = row[start_date_col].strftime('%d-%m-%Y') if start_date_col and pd.notna(row.get(start_date_col)) else 'N/A'
                                end_date = row[end_date_col].strftime('%d-%m-%Y') if end_date_col and pd.notna(row.get(end_date_col)) else 'N/A'
                                
                                st.markdown(f"""
                                **{camp_name}**
                                - Type: {camp_type}
                                - Starts: {start_date}
                                - Ends: {end_date}
                                ---
                                """)
                else:
                    st.info(f"No contests found for {today.strftime('%B %Y')}")
                
                # ============================================
                # FILTER CONTESTS BY DATE
                # ============================================
                st.markdown("---")
                st.header("🔍 Filter Contests")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Year filter
                    if 'Year' in contests.columns:
                        years = sorted(contests['Year'].dropna().unique(), reverse=True)
                        years = [int(y) for y in years if pd.notna(y)]
                        selected_year = st.selectbox(
                            "Select Year",
                            ["All Years"] + years,
                            index=0
                        )
                    else:
                        selected_year = "All Years"
                        st.warning("No year data available")
                    
                    # Month filter
                    months = [
                        "All Months", "January", "February", "March", "April", "May", "June",
                        "July", "August", "September", "October", "November", "December"
                    ]
                    selected_month = st.selectbox("Select Month", months, index=0)
                    
                with col2:
                    # Date range filter
                    st.subheader("Custom Date Range")
                    
                    if start_date_col:
                        min_date = contests[start_date_col].min().date()
                        max_date = contests[start_date_col].max().date()
                        
                        start_date = st.date_input(
                            "From Date",
                            value=datetime(current_year, current_month, 1).date(),
                            min_value=min_date,
                            max_value=max_date
                        )
                        
                        end_date = st.date_input(
                            "To Date",
                            value=today,
                            min_value=min_date,
                            max_value=max_date
                        )
                    else:
                        start_date = datetime(current_year, current_month, 1).date()
                        end_date = today
                        st.warning("Using default dates (no date column found)")
                
                # Apply filters
                filtered_contests = contests.copy()
                
                # Year filter
                if selected_year != "All Years" and 'Year' in filtered_contests.columns:
                    filtered_contests = filtered_contests[filtered_contests['Year'] == selected_year]
                
                # Month filter
                if selected_month != "All Months" and 'Month_Num' in filtered_contests.columns:
                    month_num = months.index(selected_month)  # Get month number (January=1)
                    filtered_contests = filtered_contests[filtered_contests['Month_Num'] == month_num]
                
                # Date range filter
                if start_date_col and end_date_col:
                    start_datetime = pd.Timestamp(start_date)
                    end_datetime = pd.Timestamp(end_date)
                    
                    filtered_contests = filtered_contests[
                        (filtered_contests[start_date_col] >= start_datetime) & 
                        (filtered_contests[end_date_col] <= end_datetime)
                    ]
                
                # Display results
                st.subheader(f"📊 Results: {len(filtered_contests)} contests found")
                
                if not filtered_contests.empty:
                    # Quick stats
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total", len(filtered_contests))
                    
                    with col2:
                        if camp_type_col:
                            camp_types = filtered_contests[camp_type_col].nunique()
                            st.metric("Campaign Types", camp_types)
                        else:
                            st.metric("Campaign Types", "N/A")
                    
                    with col3:
                        if kam_col:
                            kam_count = filtered_contests[kam_col].nunique()
                            st.metric("KAMs", kam_count)
                        else:
                            st.metric("KAMs", "N/A")
                    
                    # Create display dataframe with all requested columns
                    display_cols = []
                    
                    # Add all requested columns if available
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
                        
                        # Rename columns for display
                        rename_dict = {
                            camp_name_col: 'Camp Name',
                            camp_type_col: 'Camp Type',
                            start_date_col: 'Start Date',
                            end_date_col: 'End Date',
                            winner_date_col: 'Winner Announcement Date',
                            kam_col: 'KAM',
                            to_whom_col: 'To Whom?'
                        }
                        display_df = display_df.rename(columns={k: v for k, v in rename_dict.items() if k})
                        
                        st.dataframe(display_df, use_container_width=True, height=400)
                        
                        # Download button
                        csv = display_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "📥 Download Filtered Contests",
                            csv,
                            f"contests_{start_date}_to_{end_date}.csv",
                            "text/csv"
                        )
                    else:
                        st.dataframe(filtered_contests, use_container_width=True, height=400)
                else:
                    st.info("No contests found for selected filters")
            else:
                st.warning("No contests found in Contest Details sheet")
                
        except Exception as e:
            st.error(f"Error loading Contest Details: {str(e)}")
        
        # ============================================
        # LOAD WINNER DATA
        # ============================================
        st.markdown("---")
        st.header("🏆 Check Winners")
        
        # Try different possible sheet names
        winner_sheet_names = ['Winners Details ', 'Winner Details', 'Winners Details', 'Winner Details ']
        winner_sheet_found = None
        
        for sheet_name in winner_sheet_names:
            try:
                winner_ws = sheet.worksheet(sheet_name)
                winner_sheet_found = sheet_name
                break
            except:
                continue
        
        if winner_sheet_found:
            winner_ws = sheet.worksheet(winner_sheet_found)
            winner_data = winner_ws.get_all_records()
            winners = pd.DataFrame(winner_data)
            
            if not winners.empty:
                st.success(f"✅ {len(winners)} winners loaded from {winner_sheet_found}")
                
                # Winner search
                search_by = st.radio("Search by:", ["BZID", "Phone", "Name"], horizontal=True)
                
                if search_by == "BZID":
                    search_input = st.text_input("Enter BZID (businessid)", key="bzid")
                    column = 'businessid'
                elif search_by == "Phone":
                    search_input = st.text_input("Enter Phone Number", key="phone")
                    column = 'customer_phonenumber'
                else:
                    search_input = st.text_input("Enter Customer Name", key="name")
                    column = 'customer_firstname'
                
                if search_input and column in winners.columns:
                    # Clean column
                    winners[column] = winners[column].astype(str).fillna('')
                    
                    # Search
                    results = winners[winners[column].str.contains(search_input, case=False, na=False)]
                    
                    if not results.empty:
                        st.success(f"✅ Found {len(results)} win(s)")
                        
                        # Display each winner with contest details
                        for _, row in results.iterrows():
                            gift = str(row.get('Gift', 'N/A')).strip()
                            camp_desc = str(row.get('Camp Description', 'N/A')).strip()
                            contest_eligibility = str(row.get('Contest', 'N/A')).strip()
                            
                            # Get dates from winner data
                            start_date_val = row.get('Start Date', None)
                            end_date_val = row.get('End Date', None)
                            
                            # Format dates
                            if pd.notna(start_date_val) and hasattr(start_date_val, 'strftime'):
                                start_date_str = start_date_val.strftime('%d-%m-%Y')
                            else:
                                start_date_str = 'N/A'
                                
                            if pd.notna(end_date_val) and hasattr(end_date_val, 'strftime'):
                                end_date_str = end_date_val.strftime('%d-%m-%Y')
                            else:
                                end_date_str = 'N/A'
                            
                            # Display winner card
                            st.markdown(f"""
                            ### 🎁 {gift}
                            **📋 Contest Details:**
                            - **Camp Description:** {camp_desc}
                            - **Eligibility:** {contest_eligibility}
                            - **Duration:** {start_date_str} to {end_date_str}
                            
                            **👤 Winner Details:**
                            - **Customer:** {row.get('customer_firstname', 'N/A')}
                            - **Phone:** {row.get('customer_phonenumber', 'N/A')}
                            - **Store:** {row.get('business_displayname', 'N/A')}
                            - **BZID:** {row.get('businessid', 'N/A')}
                            - **Winner Date:** {row.get('Winner Announcement Date', 'N/A')}
                            
                            ---
                            """)
                    else:
                        st.warning("No wins found")
                        
                elif not search_input:
                    st.info("Enter BZID, Phone, or Name to search for winners")
                    
            else:
                st.warning("No winner data found")
        else:
            st.warning("Winner sheet not found")
            
    except Exception as e:
        st.error(f"Error: {str(e)}")
        
else:
    st.error("Connection failed")

# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%d %b %Y %H:%M')}")

if st.button("🔄 Refresh All Data"):
    st.rerun()
