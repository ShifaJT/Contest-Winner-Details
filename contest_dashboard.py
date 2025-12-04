import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe
import json

# ============================================
# CONFIGURATION - SET THESE VALUES ONCE
# ============================================

# 1. Your Google Sheet ID (from the URL: https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit)
YOUR_SHEET_ID = "1E2qxc1kZttPQMmSXCVXFaQKVNLl_Nhe4uUPBrzf7B3U"  # Replace with your actual Sheet ID

# 2. Sheet names in your Google Sheet
SHEET_NAMES = {
    'contest': 'Contest Details',
    'winner': 'Winner Details'
}

# 3. Service account credentials (paste your credentials below)
SERVICE_ACCOUNT_CREDS = {
  "type": "service_account",
  "project_id": "contest-details-dashboard",
  "private_key_id": "fabac761caec15286e55ec0986e2c5ed551dee1d",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCsRV9HKcRjONJS\n0e81U9G1B019DCh8Y62NVBikbUdN2no8cJ8TSqIanaT+Vk7Ft/26/2PGr59iWjIW\niiQW0hrWDJcNrYWbUlavnw/XAsiBYJDdOdZcoJj4WY7wrjzvvhButKYLOAPxrleV\nsaByXJGgNVLbP8BmOjPAixnUIeW5Mdja7/GK57t5AZTZ5wuBIUeM811SQdHEjHvu\n04EmheeELMSQrmkhf/oJ1PJCOXY16/n3nkWiRv4RZLNIYOiz+qzQrZ16yKx4GCyK\ny46V1m7Ut+3qPaMWnxlg4cfjSVqPPC1xbtfLPvW2ZA7mvsNaoUD4SaKfOnnB334d\n24g2sIUzAgMBAAECggEAOzRAMVnGV39AsRvbBM3ApWFUHSSfiVhMXeTH70JrHfN2\nzOy7jsq4eUMyYAJTYhoAhlKc/LyAnzF2Q07IZltgw61iAF5hK2cZyZN1wyP+uo/w\nWUc2R3EeAUPuHwMSiCYeyZ0l73cZy+ZpzVVVWdg8Z/3LcvQu8DMSdBqaDtBzfbh2\ndJK87i0c+9b/rPrFEHcNgpm2OVxQe+H6FZK5+4gqp1QQuGklm4QcJYoBCMJmD1ZV\nHOxAMONZCcTNEKKtp11PuqY0WswM2jKU+Aav7lkTzx94rcq0fZR3okpZ01zSMsdt\np7noWhuwlu2BPbbNr+JLcW/UG5Ai/VBB2Q8XFsm3qQKBgQDXkCnnGyvB6H/TV2h5\n42usSH4EgVjf4GNOuDRZbsH1hvaFXaK9cOeU7QWrw0dVFysUh/X4nW9x8+F2jqwG\nVJtKXQyWIiMKaIvSREq3zu9SFxobdfrfA/42ItZgpFKQFz6CFNdTK8kOoKh7SQec\nJGQdWfd0CDk0z1aXZ/NJ3skP5wKBgQDMljhPdtCdLk2ugXpOVktj2ZdbQkrpXUjm\nYnOmidsVrFhJuBOdivQrTuj01S0Kz7VyBXKpo+Hs62atCnRmmDcUQME9h1t5DH9H\nmAlhkZhsLS77R0TpMP/Tppc0q3gqXppnXhjgG+KrPCwID1TAdDf8jlZNPWzsXaWK\nxwllnWYm1QKBgEb3p1P2lglYyfyCIls+jAxEMXi6PNA3x3n7GwD2fdSfgjmWAiXs\nLdHR1rQdrjZNUlmICWq4KiCR8gBeKDRNVnK8/4/N3Utn7+Bhq1eoQRH9mRLBXL5f\nSin4fiuC7cuSW3nn8pvnJmIyckVkXaUCNhOTsuv4aR0BxbhC+M2xEvCxAoGBAIxc\nZ8fFCX09PliCRoomVFTt/RTEV6bhtFkzpIrWu7OT6YKyQursYXaxDcyj0OJA/Qh8\nSl2urRshqfEAYjndJrTDdJClJBHZjB1vZshE3qEhIsGM9O9UCcCI4+Zj2e6ftylB\n+qkPGKVIhCEHe6sKUTr54KXfhbJo0WF0CrNnmKT9AoGAJjwQ07y519Q3YP2fR+nQ\nt/Q4wCPzT81A/CK108U7SetALsriRXQQNHf/G/BVG09J6EO9q3KtNiXRtPJDqvpu\ny/2bySKUwxvb7ZhdflLK0HZshvQEYbDQNazY+yyI+FOQMSEttP/Iv8l/oPCJW6CP\n5kbZVw3n8DInklFGkcaU0uw=\n-----END PRIVATE KEY-----\n",
  "client_email": "contest-details-dashboard@contest-details-dashboard.iam.gserviceaccount.com",
  "client_id": "102614805686865649760",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/contest-details-dashboard%40contest-details-dashboard.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

# ============================================
# DON'T MODIFY BELOW THIS LINE
# ============================================

@st.cache_resource
def get_google_sheet_client():
    """Authenticate and return Google Sheets client with predefined credentials"""
    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Use the predefined credentials
        credentials = Credentials.from_service_account_info(SERVICE_ACCOUNT_CREDS, scopes=scopes)
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"Authentication failed: {str(e)}")
        return None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_sheet_data(worksheet_name):
    """Load data from Google Sheets"""
    try:
        client = get_google_sheet_client()
        if not client:
            return pd.DataFrame()
            
        sheet = client.open_by_key(YOUR_SHEET_ID)
        worksheet = sheet.worksheet(worksheet_name)
        df = get_as_dataframe(worksheet, evaluate_formulas=True)
        df = df.dropna(how='all')  # Remove empty rows
        return df
    except Exception as e:
        st.error(f"Error loading {worksheet_name}: {str(e)}")
        return pd.DataFrame()

# Streamlit App
st.set_page_config(
    page_title="Contest Dashboard",
    page_icon="🎯",
    layout="wide"
)

st.title("🎁 Live Contest & Winner Dashboard")
st.markdown("---")

# Display connection status
st.sidebar.header("🔗 Connection Status")
st.sidebar.info(f"Connected to Google Sheet")

# Load data
with st.spinner("Loading data from Google Sheets..."):
    contest_df = load_sheet_data(SHEET_NAMES['contest'])
    winner_df = load_sheet_data(SHEET_NAMES['winner'])

if not contest_df.empty and not winner_df.empty:
    # Clean and parse dates
    contest_df = contest_df.copy()
    winner_df = winner_df.copy()
    
    # Convert date columns
    date_columns_contest = ['Start Date', 'End Date', 'Winner Announcement Date']
    date_columns_winner = ['Start Date', 'End Date', 'Winner Announcement Date', 'Gift Sent Date']
    
    for col in date_columns_contest:
        if col in contest_df.columns:
            contest_df[col] = pd.to_datetime(contest_df[col], errors='coerce', dayfirst=True)
    
    for col in date_columns_winner:
        if col in winner_df.columns:
            winner_df[col] = pd.to_datetime(winner_df[col], errors='coerce', dayfirst=True)
    
    # --- MAIN APP ---
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("📅 Filter Contests")
        
        # Year filter
        if 'Start Date' in contest_df.columns:
            contest_df['Year'] = contest_df['Start Date'].dt.year
            years = sorted(contest_df['Year'].dropna().unique().astype(int))
        else:
            years = []
            contest_df['Year'] = None
        
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
        st.subheader("Custom Date Range")
        if 'Start Date' in contest_df.columns:
            start_date = st.date_input(
                "Start Date",
                value=contest_df['Start Date'].min().date()
            )
            end_date = st.date_input(
                "End Date",
                value=contest_df['Start Date'].max().date()
            )
        else:
            start_date = st.date_input("Start Date", value=datetime.now().date())
            end_date = st.date_input("End Date", value=datetime.now().date())
        
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
        
        # Display contest count
        st.metric("Contests Found", len(filtered_contest))
        
        # Quick stats
        if not filtered_contest.empty and 'Camp Type' in filtered_contest.columns:
            st.subheader("📊 Quick Stats")
            camp_types = filtered_contest['Camp Type'].value_counts()
            for camp_type, count in camp_types.items():
                st.caption(f"**{camp_type}**: {count}")
    
    with col2:
        st.header("🎯 Contest Details")
        
        if not filtered_contest.empty:
            # Display contests
            display_cols = []
            for col in ['Merch ID', 'Camp Name', 'Camp Type', 'Start Date', 'End Date', 'Winner Announcement Date', 'KAM']:
                if col in filtered_contest.columns:
                    display_cols.append(col)
            
            display_df = filtered_contest[display_cols].copy()
            
            # Format dates
            if 'Start Date' in display_df.columns:
                display_df['Start Date'] = display_df['Start Date'].dt.strftime('%d-%m-%Y')
            if 'End Date' in display_df.columns:
                display_df['End Date'] = display_df['End Date'].dt.strftime('%d-%m-%Y')
            if 'Winner Announcement Date' in display_df.columns:
                display_df['Winner Announcement Date'] = display_df['Winner Announcement Date'].dt.strftime('%d-%m-%Y')
            
            st.dataframe(
                display_df,
                use_container_width=True,
                height=400
            )
            
            # Download button for filtered contests
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Filtered Contests",
                data=csv,
                file_name=f"contests_{start_date}_to_{end_date}.csv",
                mime="text/csv"
            )
        else:
            st.info("No contests found for selected filters")
    
    st.markdown("---")
    
    # --- WINNER SEARCH SECTION ---
    st.header("🏆 Winner Search")
    
    search_col1, search_col2 = st.columns([1, 3])
    
    with search_col1:
        search_type = st.radio(
            "Search by",
            ["BZID (businessid)", "Customer Phone", "Customer Name", "Merch ID"]
        )
        
        if search_type == "BZID (businessid)":
            search_value = st.text_input("Enter BZID", key="bzid_search")
            if search_value and 'businessid' in winner_df.columns:
                results = winner_df[winner_df['businessid'] == search_value]
            else:
                results = pd.DataFrame()
        
        elif search_type == "Customer Phone":
            search_value = st.text_input("Enter Phone Number", key="phone_search")
            if search_value and 'customer_phonenumber' in winner_df.columns:
                results = winner_df[winner_df['customer_phonenumber'] == search_value]
            else:
                results = pd.DataFrame()
        
        elif search_type == "Customer Name":
            search_value = st.text_input("Enter Customer Name", key="name_search")
            if search_value and 'customer_firstname' in winner_df.columns:
                results = winner_df[
                    winner_df['customer_firstname'].str.contains(str(search_value), case=False, na=False)
                ]
            else:
                results = pd.DataFrame()
        
        else:  # Merch ID
            search_value = st.text_input("Enter Merch ID", key="merch_search")
            if search_value and 'Merch ID' in winner_df.columns:
                results = winner_df[winner_df['Merch ID'] == search_value]
            else:
                results = pd.DataFrame()
    
    with search_col2:
        if 'search_value' in locals() and search_value:
            if not results.empty:
                st.success(f"✅ Found {len(results)} record(s)")
                
                # Display summary
                summary_cols = []
                for col in ['Merch ID', 'Contest', 'Gift', 'Winner Announcement Date', 'Gift Sent Date', 'customer_firstname']:
                    if col in results.columns:
                        summary_cols.append(col)
                
                if summary_cols:
                    summary_df = results[summary_cols].copy()
                    
                    # Format dates
                    for date_col in ['Winner Announcement Date', 'Gift Sent Date']:
                        if date_col in summary_df.columns:
                            summary_df[date_col] = summary_df[date_col].dt.strftime('%d-%m-%Y')
                    
                    st.dataframe(summary_df, use_container_width=True)
                    
                    # Expand for full details
                    with st.expander("📋 View Full Details"):
                        st.dataframe(results, use_container_width=True)
                    
                    # Download results
                    csv_results = results.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Winner Details",
                        data=csv_results,
                        file_name=f"winner_{search_value}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No matching columns found in winner data")
            else:
                st.warning("No records found")
        else:
            st.info("👈 Enter search criteria to find winners")
    
    # --- WINNERS IN DATE RANGE ---
    st.markdown("---")
    
    if st.checkbox("👥 Show all winners in selected contest date range"):
        st.header("🏅 Winners in Selected Period")
        
        # Get contest IDs in filtered range
        if 'Merch ID' in filtered_contest.columns and 'Merch ID' in winner_df.columns:
            contest_ids = filtered_contest['Merch ID'].unique()
            winners_in_range = winner_df[winner_df['Merch ID'].isin(contest_ids)]
            
            if not winners_in_range.empty:
                st.metric("Total Winners", len(winners_in_range))
                
                # Group by gift type
                if 'Gift' in winners_in_range.columns:
                    gift_counts = winners_in_range['Gift'].value_counts().head(10)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("🎁 Top 10 Gifts")
                        for gift, count in gift_counts.items():
                            st.write(f"**{gift}**: {count}")
                    
                    with col2:
                        st.subheader("📋 Winner List")
                        display_cols = []
                        for col in ['Merch ID', 'businessid', 'Contest', 'Gift', 'Winner Announcement Date']:
                            if col in winners_in_range.columns:
                                display_cols.append(col)
                        
                        if display_cols:
                            display_winners = winners_in_range[display_cols].copy()
                            if 'Winner Announcement Date' in display_winners.columns:
                                display_winners['Winner Announcement Date'] = display_winners['Winner Announcement Date'].dt.strftime('%d-%m-%Y')
                            
                            st.dataframe(
                                display_winners,
                                use_container_width=True,
                                height=300
                            )
                else:
                    st.info("No gift information available")
            else:
                st.info("No winners found in selected period")
        else:
            st.warning("Merch ID column not found in one of the datasets")
    
    # --- DATA REFRESH ---
    st.markdown("---")
    if st.button("🔄 Refresh Data from Google Sheets"):
        st.cache_data.clear()
        st.rerun()
    
    # --- FOOTER ---
    st.caption(f"📊 Data loaded from Google Sheets | Last update: {datetime.now().strftime('%d-%m-%Y %H:%M')}")
    st.caption(f"📋 Total Contests: {len(contest_df)} | Total Winners: {len(winner_df)}")
    
elif not contest_df.empty:
    st.error("Contest data loaded but winner data could not be loaded. Check sheet names.")
elif not winner_df.empty:
    st.error("Winner data loaded but contest data could not be loaded. Check sheet names.")
else:
    st.error("""
    ❌ Could not load data. Please check:
    
    1. **Service Account Credentials** - Make sure they're correctly pasted in the code
    2. **Google Sheet ID** - Make sure it's correct and the sheet is shared with the service account
    3. **Sheet Names** - Make sure your sheets are named exactly as specified
    4. **Permissions** - Service account has access to the sheet
    
    **To fix:**
    - Share your Google Sheet with: `contest-details-dashboard@contest-details-dashboard.iam.gserviceaccount.com`
    - Make sure sheet names match: 'Contest Details' and 'Winner Details'
    """)
