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
        # LOAD CONTEST DATA FROM WINNERS SHEET
        # ============================================
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
                
                # Show column names for reference
                with st.expander("📋 See Available Columns"):
                    st.write("Columns in data:", list(winners.columns))
                
                # Fix dates in winners data
                if 'Start Date' in winners.columns:
                    winners['Start Date'] = pd.to_datetime(winners['Start Date'], errors='coerce', dayfirst=True)
                if 'End Date' in winners.columns:
                    winners['End Date'] = pd.to_datetime(winners['End Date'], errors='coerce', dayfirst=True)
                
                # Create a unique contests list from winners data
                contest_columns = ['Camp Description', 'Contest', 'Gift', 'Start Date', 'End Date']
                available_contest_cols = [col for col in contest_columns if col in winners.columns]
                
                if available_contest_cols:
                    # Get unique contests
                    unique_contests = winners[available_contest_cols].drop_duplicates()
                    st.info(f"📋 Found {len(unique_contests)} unique contests in winners data")
                
                # ============================================
                # CURRENT CONTESTS - QUICK VIEW
                # ============================================
                st.header("📢 Current Contests (Quick View)")
                
                today = datetime.now().date()
                current_month = today.month
                current_year = today.year
                
                if 'Start Date' in winners.columns:
                    # Current month contests
                    current_month_contests = winners[
                        (winners['Start Date'].dt.year == current_year) & 
                        (winners['Start Date'].dt.month == current_month)
                    ]
                    
                    if not current_month_contests.empty:
                        st.info(f"**This month ({today.strftime('%B %Y')}): {len(current_month_contests['Camp Description'].unique())} contests**")
                        
                        # Show current running contests
                        if 'End Date' in winners.columns:
                            current_running = winners[
                                (winners['Start Date'].dt.date <= today) & 
                                (winners['End Date'].dt.date >= today)
                            ]
                            
                            if not current_running.empty:
                                st.subheader("🏃 Running Now")
                                for camp_desc in current_running['Camp Description'].unique()[:5]:  # Show top 5
                                    camp_data = current_running[current_running['Camp Description'] == camp_desc].iloc[0]
                                    st.markdown(f"""
                                    **{camp_desc}**
                                    - Gift: {camp_data.get('Gift', 'N/A')}
                                    - Ends: {camp_data['End Date'].strftime('%d %b') if pd.notna(camp_data.get('End Date')) else 'N/A'}
                                    ---
                                    """)
                            else:
                                st.info("No contests running today")
                        
                        # Upcoming this month
                        upcoming_this_month = winners[
                            (winners['Start Date'].dt.date > today) & 
                            (winners['Start Date'].dt.year == current_year) & 
                            (winners['Start Date'].dt.month == current_month)
                        ]
                        
                        if not upcoming_this_month.empty:
                            st.subheader("📅 Upcoming This Month")
                            for camp_desc in upcoming_this_month['Camp Description'].unique()[:5]:
                                camp_data = upcoming_this_month[upcoming_this_month['Camp Description'] == camp_desc].iloc[0]
                                st.markdown(f"""
                                **{camp_desc}**
                                - Gift: {camp_data.get('Gift', 'N/A')}
                                - Starts: {camp_data['Start Date'].strftime('%d %b') if pd.notna(camp_data.get('Start Date')) else 'N/A'}
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
                    if 'Start Date' in winners.columns:
                        winners['Year'] = winners['Start Date'].dt.year
                        years = sorted(winners['Year'].dropna().unique(), reverse=True)
                        years = [int(y) for y in years if pd.notna(y)]
                        selected_year = st.selectbox(
                            "Select Year",
                            ["All Years"] + years,
                            index=0
                        )
                    else:
                        selected_year = "All Years"
                        st.warning("No date column for filtering")
                    
                    # Month filter
                    months = [
                        "All Months", "January", "February", "March", "April", "May", "June",
                        "July", "August", "September", "October", "November", "December"
                    ]
                    selected_month = st.selectbox("Select Month", months, index=0)
                    
                with col2:
                    # Date range filter
                    st.subheader("Custom Date Range")
                    
                    if 'Start Date' in winners.columns:
                        min_date = winners['Start Date'].min().date()
                        max_date = winners['Start Date'].max().date()
                        
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
                        st.warning("No date column found")
                        start_date = today
                        end_date = today
                
                # Apply filters
                filtered_contests = winners.copy()
                
                # Year filter
                if selected_year != "All Years" and 'Year' in filtered_contests.columns:
                    filtered_contests = filtered_contests[filtered_contests['Year'] == selected_year]
                
                # Month filter
                if selected_month != "All Months" and 'Start Date' in filtered_contests.columns:
                    month_num = months.index(selected_month)  # Get month number (January=1)
                    filtered_contests = filtered_contests[filtered_contests['Start Date'].dt.month == month_num]
                
                # Date range filter
                if 'Start Date' in filtered_contests.columns and 'End Date' in filtered_contests.columns:
                    start_datetime = pd.Timestamp(start_date)
                    end_datetime = pd.Timestamp(end_date)
                    
                    filtered_contests = filtered_contests[
                        (filtered_contests['Start Date'] >= start_datetime) & 
                        (filtered_contests['End Date'] <= end_datetime)
                    ]
                
                # Get unique contests from filtered results
                if 'Camp Description' in filtered_contests.columns:
                    unique_filtered_contests = filtered_contests[['Camp Description', 'Contest', 'Gift', 'Start Date', 'End Date']].drop_duplicates()
                    
                    # Display results
                    st.subheader(f"📊 Results: {len(unique_filtered_contests)} contests found")
                    
                    if not unique_filtered_contests.empty:
                        # Quick stats
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Contests", len(unique_filtered_contests))
                        with col2:
                            unique_gifts = unique_filtered_contests['Gift'].nunique()
                            st.metric("Unique Gifts", unique_gifts)
                        with col3:
                            total_winners = len(filtered_contests)
                            st.metric("Total Winners", total_winners)
                        
                        # Display table
                        display_df = unique_filtered_contests.copy()
                        
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
                    else:
                        st.info("No contests found for selected filters")
                
                # ============================================
                # CHECK WINNERS
                # ============================================
                st.markdown("---")
                st.header("🏆 Check Winners")
                
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
                            
                            # Get dates
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
                            
                            # Show additional details in expander
                            with st.expander("📄 View Full Details"):
                                st.write(row.to_dict())
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
