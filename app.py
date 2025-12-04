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
        
        # Load Contest Details
        contest_ws = sheet.worksheet("Contest Details")
        contest_data = contest_ws.get_all_records()
        contests = pd.DataFrame(contest_data)
        
        # Fix dates
        contests['Start Date'] = pd.to_datetime(contests['Start Date'], errors='coerce', dayfirst=True)
        contests['End Date'] = pd.to_datetime(contests['End Date'], errors='coerce', dayfirst=True)
        
        # Add year and month columns for filtering
        contests['Year'] = contests['Start Date'].dt.year
        contests['Month'] = contests['Start Date'].dt.month_name()
        contests['Month_Num'] = contests['Start Date'].dt.month
        
        if not contests.empty:
            st.success(f"📋 {len(contests)} contests loaded (2018-Present)")
            
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
                current_running = contests[
                    (contests['Start Date'].dt.date <= today) & 
                    (contests['End Date'].dt.date >= today)
                ]
                
                if not current_running.empty:
                    st.subheader("🏃 Running Now")
                    for _, row in current_running.iterrows():
                        st.markdown(f"""
                        **{row.get('Camp Name', 'N/A')}**
                        - Type: {row.get('Camp Type', 'N/A')}
                        - Ends: {row['End Date'].strftime('%d %b')}
                        - KAM: {row.get('KAM', 'N/A')}
                        ---
                        """)
                else:
                    st.info("No contests running today")
                
                # Upcoming this month
                upcoming_this_month = contests[
                    (contests['Start Date'].dt.date > today) & 
                    (contests['Year'] == current_year) & 
                    (contests['Month_Num'] == current_month)
                ]
                
                if not upcoming_this_month.empty:
                    st.subheader("📅 Upcoming This Month")
                    for _, row in upcoming_this_month.iterrows():
                        st.markdown(f"""
                        **{row.get('Camp Name', 'N/A')}**
                        - Starts: {row['Start Date'].strftime('%d %b')}
                        - Type: {row.get('Camp Type', 'N/A')}
                        ---
                        """)
            else:
                st.info(f"No contests found for {today.strftime('%B %Y')}")
            
            # ============================================
            # FIXED FILTER CONTESTS BY DATE - NO ERRORS
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
                
                min_date = contests['Start Date'].min().date()
                max_date = contests['Start Date'].max().date()
                
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
            
            # Apply filters - FIXED CODE (NO DATETIME/DATE COMPARISON ERROR)
            filtered_contests = contests.copy()
            
            # Year filter - FIXED
            if selected_year != "All Years":
                filtered_contests = filtered_contests[filtered_contests['Year'] == selected_year]
            
            # Month filter - FIXED
            if selected_month != "All Months":
                month_num = months.index(selected_month)  # Get month number (January=1)
                filtered_contests = filtered_contests[filtered_contests['Month_Num'] == month_num]
            
            # Date range filter - FIXED (no datetime/date comparison error)
            # Convert start_date and end_date to datetime for proper comparison
            start_datetime = pd.Timestamp(start_date)
            end_datetime = pd.Timestamp(end_date)
            
            # Filter using datetime comparison
            filtered_contests = filtered_contests[
                (filtered_contests['Start Date'] >= start_datetime) & 
                (filtered_contests['End Date'] <= end_datetime)
            ]
            
            # Display results
            st.subheader(f"📊 Results: {len(filtered_contests)} contests found")
            
            if not filtered_contests.empty:
                # Quick stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total", len(filtered_contests))
                with col2:
                    camp_types = filtered_contests['Camp Type'].nunique()
                    st.metric("Campaign Types", camp_types)
                with col3:
                    kam_count = filtered_contests['KAM'].nunique()
                    st.metric("KAMs", kam_count)
                
                # Display table
                display_cols = ['Merch ID', 'Camp Name', 'Camp Type', 'Start Date', 'End Date', 'KAM']
                display_cols = [col for col in display_cols if col in filtered_contests.columns]
                
                display_df = filtered_contests[display_cols].copy()
                
                # Format dates
                if 'Start Date' in display_df.columns:
                    display_df['Start Date'] = display_df['Start Date'].dt.strftime('%d-%m-%Y')
                if 'End Date' in display_df.columns:
                    display_df['End Date'] = display_df['End Date'].dt.strftime('%d-%m-%Y')
                
                st.dataframe(display_df, use_container_width=True, height=400)
                
                # Download button
                csv = display_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download Filtered Contests",
                    csv,
                    f"contests_{start_date}_to_{end_date}.csv",
                    "text/csv"
                )
                
                # Show campaign type breakdown
                with st.expander("📈 Campaign Type Breakdown"):
                    camp_stats = filtered_contests['Camp Type'].value_counts()
                    for camp_type, count in camp_stats.items():
                        st.write(f"**{camp_type}**: {count}")
            else:
                st.info("No contests found for selected filters")
        
        # ============================================
        # LOAD WINNER DATA WITH CONTEST INFO
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
                            # Get contest name from winner data
                            contest_name = row.get('Contest', 'N/A')
                            
                            # Find matching contest in contest details
                            contest_info = contests[
                                contests['Camp Name'].str.contains(contest_name, case=False, na=False)
                            ]
                            
                            # Prepare contest details
                            if not contest_info.empty:
                                contest_row = contest_info.iloc[0]
                                camp_desc = contest_row.get('Camp Description', 'N/A')
                                start_date = contest_row.get('Start Date', 'N/A')
                                end_date = contest_row.get('End Date', 'N/A')
                                
                                # Format dates if they exist
                                if pd.notna(start_date):
                                    start_date_str = start_date.strftime('%d-%m-%Y')
                                else:
                                    start_date_str = 'N/A'
                                    
                                if pd.notna(end_date):
                                    end_date_str = end_date.strftime('%d-%m-%Y')
                                else:
                                    end_date_str = 'N/A'
                            else:
                                camp_desc = 'Contest details not found'
                                start_date_str = 'N/A'
                                end_date_str = 'N/A'
                            
                            # Display winner card with contest info
                            st.markdown(f"""
                            **🎁 {row.get('Gift', 'N/A')}**
                            - **Contest:** {contest_name}
                            - **Camp Description:** {camp_desc}
                            - **Contest Duration:** {start_date_str} to {end_date_str}
                            - **Customer:** {row.get('customer_firstname', 'N/A')}
                            - **Phone:** {row.get('customer_phonenumber', 'N/A')}
                            - **Store:** {row.get('business_displayname', 'N/A')}
                            - **BZID:** {row.get('businessid', 'N/A')}
                            ---
                            """)
                    else:
                        st.warning("No wins found")
                        
                # If no search yet, show some stats
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
