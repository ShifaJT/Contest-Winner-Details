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

# Function to find matching contest
def find_contest_details(winner_row, contests_df):
    """Find matching contest details for a winner"""
    gift = str(winner_row.get('Gift', '')).strip()
    businessid = str(winner_row.get('businessid', '')).strip()
    
    # Try different matching strategies
    if not contests_df.empty:
        # Try to match by any column containing the gift
        for col in contests_df.columns:
            if contests_df[col].dtype == 'object':  # Only check string columns
                try:
                    matches = contests_df[contests_df[col].astype(str).str.contains(gift, case=False, na=False)]
                    if not matches.empty:
                        return matches.iloc[0]
                except:
                    continue
        
        # Try partial matching
        for idx, contest_row in contests_df.iterrows():
            for col in contests_df.columns:
                if pd.notna(contest_row.get(col, None)):
                    if gift.lower() in str(contest_row[col]).lower():
                        return contest_row
    
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
        
        # Load Contest Details
        contest_ws = sheet.worksheet("Contest Details")
        contest_data = contest_ws.get_all_records()
        contests = pd.DataFrame(contest_data)
        
        # Show columns for debugging
        with st.expander("📋 Debug: See Contest Data Columns"):
            st.write("Available columns in contest data:", list(contests.columns))
            st.write("First few rows:")
            st.dataframe(contests.head())
        
        # Fix dates - try different possible date column names
        date_columns = []
        for col in contests.columns:
            if 'date' in col.lower() or 'Date' in col:
                date_columns.append(col)
        
        for date_col in date_columns:
            if date_col in contests.columns:
                contests[date_col] = pd.to_datetime(contests[date_col], errors='coerce', dayfirst=True)
        
        # Find start and end date columns
        start_date_col = None
        end_date_col = None
        
        for col in contests.columns:
            if 'start' in col.lower():
                start_date_col = col
            elif 'end' in col.lower():
                end_date_col = col
        
        # If no specific date columns found, use first two date columns
        if not start_date_col and date_columns:
            start_date_col = date_columns[0]
        if not end_date_col and len(date_columns) > 1:
            end_date_col = date_columns[1]
        
        # Add year and month columns for filtering if we have start date
        if start_date_col and start_date_col in contests.columns:
            contests['Start Date'] = contests[start_date_col]
            contests['Year'] = contests['Start Date'].dt.year
            contests['Month'] = contests['Start Date'].dt.month_name()
            contests['Month_Num'] = contests['Start Date'].dt.month
        
        if not contests.empty:
            st.success(f"📋 {len(contests)} contests loaded")
            
            # ============================================
            # CURRENT CONTESTS - QUICK VIEW
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
                        for _, row in current_running.iterrows():
                            camp_name = row.get('Camp Name', row.get('Camp Name', 'N/A'))
                            camp_type = row.get('Camp Type', row.get('Camp Type', 'N/A'))
                            kam = row.get('KAM', row.get('KAM', 'N/A'))
                            end_date = row.get(end_date_col, 'N/A')
                            
                            st.markdown(f"""
                            **{camp_name}**
                            - Type: {camp_type}
                            - Ends: {end_date.strftime('%d %b') if hasattr(end_date, 'strftime') else end_date}
                            - KAM: {kam}
                            ---
                            """)
                    else:
                        st.info("No contests running today")
                
                # Upcoming this month
                upcoming_this_month = contests[
                    (contests[start_date_col].dt.date > today) & 
                    (contests['Year'] == current_year) & 
                    (contests['Month_Num'] == current_month)
                ]
                
                if not upcoming_this_month.empty:
                    st.subheader("📅 Upcoming This Month")
                    for _, row in upcoming_this_month.iterrows():
                        camp_name = row.get('Camp Name', row.get('Camp Name', 'N/A'))
                        camp_type = row.get('Camp Type', row.get('Camp Type', 'N/A'))
                        start_date = row.get(start_date_col, 'N/A')
                        
                        st.markdown(f"""
                        **{camp_name}**
                        - Starts: {start_date.strftime('%d %b') if hasattr(start_date, 'strftime') else start_date}
                        - Type: {camp_type}
                        ---
                        """)
            else:
                st.info(f"No contests found for {today.strftime('%B %Y')}")
            
            # ============================================
            # FIXED FILTER CONTESTS BY DATE
            # ============================================
            st.markdown("---")
            st.header("🔍 Filter Contests")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Year filter
                years = sorted(contests['Year'].dropna().unique(), reverse=True)
                years = [int(y) for y in years if pd.notna(y)]
                selected_year = st.selectbox(
                    "Select Year",
                    ["All Years"] + years,
                    index=0
                )
                
                # Month filter
                months = [
                    "All Months", "January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December"
                ]
                selected_month = st.selectbox("Select Month", months, index=0)
                
            with col2:
                # Date range filter
                st.subheader("Custom Date Range")
                
                if start_date_col and start_date_col in contests.columns:
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
                    st.warning("No date column found in contest data")
                    start_date = today
                    end_date = today
            
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
            if start_date_col and end_date_col and start_date_col in filtered_contests.columns and end_date_col in filtered_contests.columns:
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
                    if 'Camp Type' in filtered_contests.columns:
                        camp_types = filtered_contests['Camp Type'].nunique()
                        st.metric("Campaign Types", camp_types)
                    else:
                        st.metric("Campaign Types", "N/A")
                with col3:
                    if 'KAM' in filtered_contests.columns:
                        kam_count = filtered_contests['KAM'].nunique()
                        st.metric("KAMs", kam_count)
                    else:
                        st.metric("KAMs", "N/A")
                
                # Display table - find relevant columns
                possible_cols = ['Merch ID', 'Camp Name', 'Camp Type', start_date_col, end_date_col, 'KAM']
                display_cols = []
                
                for col in possible_cols:
                    if col and col in filtered_contests.columns:
                        display_cols.append(col)
                
                if display_cols:
                    display_df = filtered_contests[display_cols].copy()
                    
                    # Format dates
                    if start_date_col in display_df.columns:
                        display_df[start_date_col] = display_df[start_date_col].dt.strftime('%d-%m-%Y')
                    if end_date_col in display_df.columns:
                        display_df[end_date_col] = display_df[end_date_col].dt.strftime('%d-%m-%Y')
                    
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
                st.success(f"✅ {len(winners)} winners loaded")
                
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
                            
                            # Find matching contest
                            contest_info = find_contest_details(row, contests)
                            
                            # Prepare contest details
                            if contest_info is not None:
                                # Find camp name from available columns
                                camp_name = 'N/A'
                                for name_col in ['Camp Name', 'Camp Name', 'Campaign Name', 'Name']:
                                    if name_col in contest_info:
                                        camp_name = contest_info[name_col]
                                        break
                                
                                # Find camp description from available columns
                                camp_desc = 'N/A'
                                for desc_col in ['Camp Description', 'Description', 'Details', 'Camp Details']:
                                    if desc_col in contest_info:
                                        camp_desc = contest_info[desc_col]
                                        break
                                
                                # Get dates
                                start_date = contest_info.get(start_date_col, None) if start_date_col else None
                                end_date = contest_info.get(end_date_col, None) if end_date_col else None
                                
                                # Format dates
                                if pd.notna(start_date) and hasattr(start_date, 'strftime'):
                                    start_date_str = start_date.strftime('%d-%m-%Y')
                                else:
                                    start_date_str = str(start_date) if start_date else 'N/A'
                                    
                                if pd.notna(end_date) and hasattr(end_date, 'strftime'):
                                    end_date_str = end_date.strftime('%d-%m-%Y')
                                else:
                                    end_date_str = str(end_date) if end_date else 'N/A'
                            else:
                                camp_name = 'N/A'
                                camp_desc = 'N/A'
                                start_date_str = 'N/A'
                                end_date_str = 'N/A'
                            
                            # Display winner card
                            st.markdown(f"""
                            ### 🎁 {gift}
                            **📋 Contest Details:**
                            - **Camp Name:** {camp_name}
                            - **Description:** {camp_desc}
                            - **Duration:** {start_date_str} to {end_date_str}
                            
                            **👤 Winner Details:**
                            - **Customer:** {row.get('customer_firstname', 'N/A')}
                            - **Phone:** {row.get('customer_phonenumber', 'N/A')}
                            - **Store:** {row.get('business_displayname', 'N/A')}
                            - **BZID:** {row.get('businessid', 'N/A')}
                            
                            ---
                            """)
                    else:
                        st.warning("No wins found")
                        
                elif not search_input:
                    st.info("Enter BZID, Phone, or Name to search for winners")
                    
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
