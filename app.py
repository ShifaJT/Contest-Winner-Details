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
                
                # Fix dates - try to find date columns
                for col in contests.columns:
                    if 'date' in col.lower() or 'Date' in col:
                        contests[col] = pd.to_datetime(contests[col], errors='coerce', dayfirst=True)
                
                # Find start and end date columns
                start_date_col = None
                end_date_col = None
                
                for col in contests.columns:
                    col_lower = col.lower()
                    if 'start' in col_lower:
                        start_date_col = col
                    elif 'end' in col_lower:
                        end_date_col = col
                
                # If no specific date columns found, use first two date columns
                date_columns = [col for col in contests.columns if 'date' in col.lower()]
                if not start_date_col and date_columns:
                    start_date_col = date_columns[0]
                if not end_date_col and len(date_columns) > 1:
                    end_date_col = date_columns[1]
                
                # Add year and month columns for filtering
                if start_date_col and start_date_col in contests.columns:
                    contests['Start_Date'] = contests[start_date_col]
                    contests['Year'] = contests['Start_Date'].dt.year
                    contests['Month'] = contests['Start_Date'].dt.month_name()
                    contests['Month_Num'] = contests['Start_Date'].dt.month
                
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
                    if start_date_col and end_date_col and start_date_col in contests.columns and end_date_col in contests.columns:
                        current_running = contests[
                            (contests[start_date_col].dt.date <= today) & 
                            (contests[end_date_col].dt.date >= today)
                        ]
                        
                        if not current_running.empty:
                            st.subheader("🏃 Running Now")
                            for _, row in current_running.iterrows():
                                # Try to find camp name
                                camp_name = 'N/A'
                                for name_col in ['Camp Name', 'Campaign Name', 'Camp Description', 'Camp']:
                                    if name_col in row and pd.notna(row[name_col]):
                                        camp_name = row[name_col]
                                        break
                                
                                # Try to find camp type
                                camp_type = 'N/A'
                                for type_col in ['Camp Type', 'Type', 'Category']:
                                    if type_col in row and pd.notna(row[type_col]):
                                        camp_type = row[type_col]
                                        break
                                
                                # Try to find KAM
                                kam = 'N/A'
                                for kam_col in ['KAM', 'Owner', 'Manager']:
                                    if kam_col in row and pd.notna(row[kam_col]):
                                        kam = row[kam_col]
                                        break
                                
                                end_date = row[end_date_col] if end_date_col in row else 'N/A'
                                
                                st.markdown(f"""
                                **{camp_name}**
                                - Type: {camp_type}
                                - Ends: {end_date.strftime('%d %b') if hasattr(end_date, 'strftime') else end_date}
                                - KAM: {kam}
                                ---
                                """)
                        else:
                            st.info("No contests running today")
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
                    
                    # Find camp type column
                    camp_type_col = None
                    for col in ['Camp Type', 'Type', 'Category']:
                        if col in filtered_contests.columns:
                            camp_type_col = col
                            break
                    
                    with col2:
                        if camp_type_col:
                            camp_types = filtered_contests[camp_type_col].nunique()
                            st.metric("Campaign Types", camp_types)
                        else:
                            st.metric("Campaign Types", "N/A")
                    
                    # Find KAM column
                    kam_col = None
                    for col in ['KAM', 'Owner', 'Manager']:
                        if col in filtered_contests.columns:
                            kam_col = col
                            break
                    
                    with col3:
                        if kam_col:
                            kam_count = filtered_contests[kam_col].nunique()
                            st.metric("KAMs", kam_count)
                        else:
                            st.metric("KAMs", "N/A")
                    
                    # Display table - find relevant columns
                    possible_cols = []
                    
                    # Try to find camp name column
                    for name_col in ['Camp Name', 'Campaign Name', 'Camp Description', 'Camp']:
                        if name_col in filtered_contests.columns:
                            possible_cols.append(name_col)
                            break
                    
                    if camp_type_col:
                        possible_cols.append(camp_type_col)
                    
                    if start_date_col:
                        possible_cols.append(start_date_col)
                    
                    if end_date_col:
                        possible_cols.append(end_date_col)
                    
                    if kam_col:
                        possible_cols.append(kam_col)
                    
                    if possible_cols:
                        display_df = filtered_contests[possible_cols].copy()
                        
                        # Format dates
                        if start_date_col in display_df.columns:
                            display_df[start_date_col] = display_df[start_date_col].dt.strftime('%d-%m-%Y')
                        if end_date_col in display_df.columns:
                            display_df[end_date_col] = display_df[end_date_col].dt.strftime('%d-%m-%Y')
                        
                        # Rename columns for display
                        column_names = {
                            start_date_col: 'Start Date',
                            end_date_col: 'End Date',
                            kam_col: 'KAM'
                        }
                        display_df = display_df.rename(columns=column_names)
                        
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
