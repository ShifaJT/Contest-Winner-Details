# contest_dashboard_gsheets.py
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go  # Fixed typo: "group.objects" to "graph_objects"
from io import BytesIO  # Fixed typo: "id" to "io"
import warnings
warnings.filterwarnings('ignore')  # Fixed typo: "warning" to "warnings"

# Page configuration
st.set_page_config(
    page_title="Contest & Winner Dashboard",  # Fixed typo: "Minner" to "Winner"
    page_icon="🏆",  # Fixed: Use trophy emoji
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #3B82F6;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #D1FAE5;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #10B981;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #DBEAFE;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #3B82F6;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #FEF3C7;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #F59E0B;
        margin: 1rem 0;
    }
    .card {
        background-color: #F3F4F6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        text-align: center;
        margin: 0.5rem;
    }
    .dataframe th {
        background-color: #3B82F6 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

class GoogleSheetsHandler:
    def __init__(self):
        self.scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
        ]
        self.sheet_id = "1E2qxc1kZttPQMmSXCVXFaQKVNLl_Nhe4uUPBrzf7B3U"
        
    def connect(self):
        """Connect to Google Sheets using credentials"""
        try:
            # For Streamlit Cloud, use secrets
            if 'GOOGLE_CREDENTIALS' in st.secrets:
                creds_dict = dict(st.secrets['GOOGLE_CREDENTIALS'])
                creds = Credentials.from_service_account_info(creds_dict, scopes=self.scope)
            else:
                # For local development - load from json file
                import json
                with open('google_credentials.json') as f:
                    creds_dict = json.load(f)
                creds = Credentials.from_service_account_info(creds_dict, scopes=self.scope)
            
            client = gspread.authorize(creds)
            return client.open_by_key(self.sheet_id)
        except Exception as e:
            st.error(f"Error connecting to Google Sheets: {e}")
            return None
    
    def get_sheet_data(self, sheet_name):
        """Get data from a specific sheet"""
        try:
            spreadsheet = self.connect()
            if spreadsheet:
                sheet = spreadsheet.worksheet(sheet_name)
                data = sheet.get_all_records()
                return pd.DataFrame(data)
            return pd.DataFrame()
        except Exception as e:
            st.error(f"Error getting data from {sheet_name}: {e}")
            return pd.DataFrame()

class ContestDashboard:
    def __init__(self):
        self.gs_handler = GoogleSheetsHandler()
        self.load_data()
    
    def load_data(self):
        """Load data from Google Sheets"""
        with st.spinner("Loading data from Google Sheets..."):
            # Load Contest Details
            self.contest_df = self.gs_handler.get_sheet_data("Contest Details")
            
            # Load Winner Details
            self.winner_df = self.gs_handler.get_sheet_data("Winner Details")
            
            # Clean and prepare data
            self.clean_data()
    
    def clean_data(self):
        """Clean and prepare the data"""
        # Convert date columns to datetime
        date_columns_contest = ['Start Date', 'End Date', 'Winner Announcement Date']
        date_columns_winner = ['Start Date', 'End Date', 'Winner Announcement Date', 'Gift Sent Date', 
                              'Old Lucky winner - Date']
        
        for col in date_columns_contest:
            if col in self.contest_df.columns:
                self.contest_df[col] = pd.to_datetime(self.contest_df[col], errors='coerce', dayfirst=True)
        
        for col in date_columns_winner:
            if col in self.winner_df.columns:
                self.winner_df[col] = pd.to_datetime(self.winner_df[col], errors='coerce', dayfirst=True)
        
        # Add duration column to contest
        if 'Start Date' in self.contest_df.columns and 'End Date' in self.contest_df.columns:
            self.contest_df['Duration (days)'] = (self.contest_df['End Date'] - self.contest_df['Start Date']).dt.days + 1
        
        # Clean businessid column
        if 'businessid' in self.winner_df.columns:
            self.winner_df['businessid'] = self.winner_df['businessid'].astype(str).str.strip()
    
    def get_running_contests(self, start_date, end_date):
        """Get contests running in selected date range"""
        if self.contest_df.empty:
            return pd.DataFrame()
        
        mask = (
            (self.contest_df['Start Date'] <= pd.Timestamp(end_date)) & 
            (self.contest_df['End Date'] >= pd.Timestamp(start_date))
        )
        return self.contest_df[mask].sort_values('Start Date')
    
    def get_business_history(self, business_id):
        """Get contest history for a specific business ID"""
        if self.winner_df.empty:
            return pd.DataFrame()
        
        mask = self.winner_df['businessid'].astype(str).str.contains(business_id, na=False)
        return self.winner_df[mask].sort_values('Winner Announcement Date', ascending=False)
    
    def get_monthly_summary(self, year, month):
        """Get monthly contest summary"""
        if self.contest_df.empty:
            return pd.DataFrame()
        
        mask = (
            (self.contest_df['Start Date'].dt.year == year) & 
            (self.contest_df['Start Date'].dt.month == month)
        )
        return self.contest_df[mask]
    
    def create_dashboard(self):
        """Main dashboard function"""
        
        # Header
        st.markdown('<h1 class="main-header">🏆 Contest & Winner Dashboard</h1>', 
                   unsafe_allow_html=True)
        
        # Data Status
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Contest Records", len(self.contest_df))
        with col2:
            st.metric("Winner Records", len(self.winner_df))
        
        if self.contest_df.empty or self.winner_df.empty:
            st.warning("⚠️ Some data may not have loaded properly. Check Google Sheets connection.")
        
        # Sidebar
        with st.sidebar:
            st.markdown("### 🔍 Navigation")
            app_mode = st.selectbox(
                "Select View",
                ["📊 Dashboard Overview", 
                 "📅 Contest Calendar", 
                 "🏆 Winner Lookup",
                 "📈 Analytics",
                 "🔍 Advanced Search",
                 "⚙️ Data Management"]
            )
            
            st.markdown("---")
            st.markdown("### 📅 Quick Date Filters")
            
            # Quick date filters
            today = datetime.now().date()
            date_options = {
                "Today": (today, today),
                "Last 7 Days": (today - timedelta(days=6), today),
                "This Month": (today.replace(day=1), today),
                "Last Month": ((today.replace(day=1) - timedelta(days=1)).replace(day=1), 
                              today.replace(day=1) - timedelta(days=1)),
                "Next 30 Days": (today, today + timedelta(days=30))
            }
            
            selected_range = st.selectbox("Select Time Period", list(date_options.keys()))
            start_date, end_date = date_options[selected_range]
            
            # Custom date range
            st.markdown("**Or select custom range:**")
            col1, col2 = st.columns(2)
            with col1:
                custom_start = st.date_input("From", start_date)
            with col2:
                custom_end = st.date_input("To", end_date)
            
            st.markdown("---")
            st.markdown("### 🔧 Tools")
            
            if st.button("🔄 Refresh Data from Sheets"):
                self.load_data()
                st.success("Data refreshed!")
                st.rerun()
            
            if st.button("📥 Export Current View"):
                self.export_current_view(app_mode)
            
            st.markdown("---")
            st.markdown("### 📊 Quick Stats")
            active = len(self.get_running_contests(custom_start, custom_end))
            st.metric("Active Contests", active)
            
            if not self.winner_df.empty and 'businessid' in self.winner_df.columns:
                unique_businesses = self.winner_df['businessid'].nunique()
                st.metric("Unique Winners", unique_businesses)
        
        # Main content based on selection
        if app_mode == "📊 Dashboard Overview":
            self.show_dashboard_overview(custom_start, custom_end)
        elif app_mode == "📅 Contest Calendar":
            self.show_contest_calendar(custom_start, custom_end)
        elif app_mode == "🏆 Winner Lookup":
            self.show_winner_lookup()
        elif app_mode == "📈 Analytics":
            self.show_analytics()
        elif app_mode == "🔍 Advanced Search":
            self.show_advanced_search()
        elif app_mode == "⚙️ Data Management":
            self.show_data_management()
    
    def show_dashboard_overview(self, start_date, end_date):
        """Show dashboard overview"""
        
        # Stats row
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="stat-card">', unsafe_allow_html=True)
            active_contests = len(self.get_running_contests(start_date, end_date))
            st.metric("Active Contests", active_contests)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="stat-card">', unsafe_allow_html=True)
            if not self.contest_df.empty:
                upcoming = len(self.contest_df[self.contest_df['Start Date'] > pd.Timestamp(end_date)])
                st.metric("Upcoming", upcoming)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="stat-card">', unsafe_allow_html=True)
            if not self.contest_df.empty and 'Duration (days)' in self.contest_df.columns:
                avg_duration = self.contest_df['Duration (days)'].mean()
                st.metric("Avg Duration", f"{avg_duration:.1f} days")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Running contests
        st.markdown(f'### 📋 Contests Running ({start_date} to {end_date})')
        running_contests = self.get_running_contests(start_date, end_date)
        
        if not running_contests.empty:
            # Display summary table
            display_cols = ['Merch ID', 'Camp Name', 'Camp Type', 'Start Date', 
                          'End Date', 'KAM', 'To Whom?']
            
            # Filter to available columns
            available_cols = [col for col in display_cols if col in running_contests.columns]
            
            st.dataframe(
                running_contests[available_cols],
                use_container_width=True,
                column_config={
                    "Start Date": st.column_config.DateColumn("Start Date"),
                    "End Date": st.column_config.DateColumn("End Date"),
                }
            )
            
            # Detailed view
            st.markdown("### 🔍 Contest Details")
            selected_contest = st.selectbox(
                "Select contest for details:",
                running_contests['Camp Name'].tolist()
            )
            
            if selected_contest:
                contest_details = running_contests[running_contests['Camp Name'] == selected_contest].iloc[0]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                    **Merch ID:** {contest_details.get('Merch ID', 'N/A')}  
                    **Camp Type:** {contest_details.get('Camp Type', 'N/A')}  
                    **KAM:** {contest_details.get('KAM', 'N/A')}  
                    **Target Audience:** {contest_details.get('To Whom?', 'N/A')}
                    """)
                
                with col2:
                    st.markdown(f"""
                    **Start Date:** {contest_details.get('Start Date', 'N/A')}  
                    **End Date:** {contest_details.get('End Date', 'N/A')}  
                    **Duration:** {contest_details.get('Duration (days)', 'N/A')} days  
                    **Winner Announcement:** {contest_details.get('Winner Announcement Date', 'N/A')}
                    """)
            
            # Download button
            csv = running_contests.to_csv(index=False)
            st.download_button(
                label="📥 Download Running Contests",
                data=csv,
                file_name=f"running_contests_{start_date}_to_{end_date}.csv",
                mime="text/csv"
            )
        else:
            st.info("No contests running in the selected date range.")
        
        # Recent winners
        st.markdown("### 🏆 Recent Winners")
        if not self.winner_df.empty:
            recent_cols = ['businessid', 'customer_firstname', 'business_displayname', 
                          'Contest', 'Gift', 'Winner Announcement Date']
            available_recent_cols = [col for col in recent_cols if col in self.winner_df.columns]
            
            recent_winners = self.winner_df.sort_values('Winner Announcement Date', ascending=False).head(10)
            st.dataframe(
                recent_winners[available_recent_cols],
                use_container_width=True
            )
    
    def show_contest_calendar(self, start_date, end_date):
        """Show contest calendar view"""
        st.markdown(f'### 📅 Contest Calendar ({start_date} to {end_date})')
        
        # Filter contests
        contests_in_range = self.get_running_contests(start_date, end_date)
        
        if not contests_in_range.empty:
            # Gantt chart
            fig = px.timeline(
                contests_in_range,
                x_start="Start Date",
                x_end="End Date",
                y="Camp Name",
                color="Camp Type",
                hover_name="Camp Name",
                hover_data={
                    "KAM": True,
                    "To Whom?": True,
                    "Duration (days)": True,
                },
                title="Contest Timeline"
            )
            fig.update_layout(
                height=400,
                xaxis_title="Date",
                yaxis_title="Contest",
                showlegend=True
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Detailed table with filtering
            st.markdown("### 📋 Filter and Explore")
            
            # Add filters
            col1, col2, col3 = st.columns(3)
            with col1:
                camp_types = ["All"] + sorted(contests_in_range['Camp Type'].unique().tolist())
                selected_type = st.selectbox("Filter by Camp Type", camp_types)
            
            with col2:
                kams = ["All"] + sorted(contests_in_range['KAM'].dropna().unique().tolist())
                selected_kam = st.selectbox("Filter by KAM", kams)
            
            with col3:
                audiences = ["All"] + sorted(contests_in_range['To Whom?'].dropna().unique().tolist())
                selected_audience = st.selectbox("Filter by Audience", audiences)
            
            # Apply filters
            filtered_df = contests_in_range.copy()
            if selected_type != "All":
                filtered_df = filtered_df[filtered_df['Camp Type'] == selected_type]
            if selected_kam != "All":
                filtered_df = filtered_df[filtered_df['KAM'] == selected_kam]
            if selected_audience != "All":
                filtered_df = filtered_df[filtered_df['To Whom?'] == selected_audience]
            
            st.dataframe(
                filtered_df,
                use_container_width=True,
                hide_index=True
            )
            
            # Export filtered data
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Filtered Data",
                data=csv,
                file_name=f"filtered_contests_{start_date}_to_{end_date}.csv",
                mime="text/csv"
            )
        else:
            st.info("No contests found in the selected date range.")
    
    def show_winner_lookup(self):
        """Show business ID lookup"""
        st.markdown("### 🔍 Business Winner Lookup")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            # Business ID search
            business_id = st.text_input("Enter Business ID (BZID-XXXXXX or partial):", 
                                       "BZID-1304470286")
            
            search_button = st.button("🔍 Search", type="primary")
            
            if search_button and business_id:
                with st.spinner("Searching..."):
                    history = self.get_business_history(business_id)
                    
                    if not history.empty:
                        st.success(f"✅ Found {len(history)} winning records")
                        
                        # Display quick stats
                        total_wins = len(history)
                        first_win = history['Winner Announcement Date'].min()
                        last_win = history['Winner Announcement Date'].max()
                        
                        st.markdown(f"""
                        <div class="success-box">
                        <strong>📊 Business Summary:</strong><br>
                        • Total Wins: {total_wins}<br>
                        • First Win: {first_win.strftime('%d-%b-%Y') if pd.notna(first_win) else 'N/A'}<br>
                        • Last Win: {last_win.strftime('%d-%b-%Y') if pd.notna(last_win) else 'N/A'}<br>
                        • Customer: {history.iloc[0].get('customer_firstname', 'N/A')}<br>
                        • Business: {history.iloc[0].get('business_displayname', 'N/A')}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Download button
                        csv = history.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Winner History",
                            data=csv,
                            file_name=f"{business_id}_history.csv",
                            mime="text/csv"
                        )
                    else:
                        st.error("❌ No records found for this Business ID")
        
        with col2:
            if 'history' in locals() and not history.empty:
                # Display history in a nice format
                st.markdown(f"### 🏆 Winning History for {business_id}")
                
                # Summary metrics
                summary_cols = st.columns(4)
                with summary_cols[0]:
                    st.metric("Total Wins", len(history))
                with summary_cols[1]:
                    unique_contests = history['Contest'].nunique()
                    st.metric("Unique Contests", unique_contests)
                with summary_cols[2]:
                    total_gifts = history['Gift'].nunique()
                    st.metric("Different Gifts", total_gifts)
                with summary_cols[3]:
                    if 'Gift Sent Date' in history.columns:
                        pending = history['Gift Sent Date'].isna().sum()
                        st.metric("Pending Gifts", pending)
                
                # Display history table
                display_cols = ['Winner Announcement Date', 'Contest', 'Gift', 
                              'Camp Description', 'Gift Sent Date', 'Owner']
                available_display_cols = [col for col in display_cols if col in history.columns]
                
                st.dataframe(
                    history[available_display_cols],
                    use_container_width=True,
                    column_config={
                        "Winner Announcement Date": st.column_config.DateColumn("Announcement Date"),
                        "Gift Sent Date": st.column_config.DateColumn("Gift Sent Date"),
                    }
                )
                
                # Visualization
                if len(history) > 1:
                    history['YearMonth'] = history['Winner Announcement Date'].dt.strftime('%Y-%m')
                    monthly_wins = history.groupby('YearMonth').size().reset_index(name='Wins')
                    
                    fig = px.bar(
                        monthly_wins,
                        x='YearMonth',
                        y='Wins',
                        title='Wins Timeline',
                        labels={'YearMonth': 'Month', 'Wins': 'Number of Wins'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
    
    def show_analytics(self):
        """Show analytics dashboard"""
        st.markdown("### 📈 Contest Analytics")
        
        if self.contest_df.empty:
            st.warning("No contest data available for analytics")
            return
        
        # KPIs
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            contest_types = self.contest_df['Camp Type'].nunique()
            st.metric("Contest Types", contest_types)
        
        with col2:
            if 'Duration (days)' in self.contest_df.columns:
                avg_duration = self.contest_df['Duration (days)'].mean()
                st.metric("Avg Duration", f"{avg_duration:.1f} days")
        
        with col3:
            kam_count = self.contest_df['KAM'].nunique()
            st.metric("KAMs Involved", kam_count)
        
        with col4:
            audience_count = self.contest_df['To Whom?'].nunique()
            st.metric("Audience Types", audience_count)
        
        # Visualizations
        col1, col2 = st.columns(2)
        
        with col1:
            # Contest type distribution
            if 'Camp Type' in self.contest_df.columns:
                type_dist = self.contest_df['Camp Type'].value_counts()
                fig1 = px.pie(
                    values=type_dist.values,
                    names=type_dist.index,
                    title="Contest Type Distribution",
                    hole=0.3
                )
                st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Monthly trend
            if 'Start Date' in self.contest_df.columns:
                self.contest_df['Month'] = self.contest_df['Start Date'].dt.to_period('M').astype(str)
                monthly = self.contest_df.groupby('Month').size().reset_index(name='Count')
                if not monthly.empty:
                    fig2 = px.line(
                        monthly,
                        x='Month',
                        y='Count',
                        title="Monthly Contest Trend",
                        markers=True
                    )
                    fig2.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig2, use_container_width=True)
        
        # KAM performance
        st.markdown("### 👥 KAM Performance")
        if 'KAM' in self.contest_df.columns:
            kam_stats = self.contest_df.groupby('KAM').agg({
                'Merch ID': 'count',
                'Duration (days)': 'mean'
            }).round(1).rename(columns={'Merch ID': 'Contests Managed'})
            
            st.dataframe(
                kam_stats,
                use_container_width=True
            )
    
    def show_advanced_search(self):
        """Show advanced search options"""
        st.markdown("### 🔍 Advanced Search")
        
        tab1, tab2, tab3 = st.tabs(["Search Contests", "Search Winners", "Cross Reference"])
        
        with tab1:
            st.markdown("#### Search Contests")
            
            col1, col2 = st.columns(2)
            with col1:
                search_term = st.text_input("Search in Camp Name/Description:")
            with col2:
                kam_filter = st.multiselect(
                    "Filter by KAM:",
                    options=self.contest_df['KAM'].unique().tolist() if 'KAM' in self.contest_df.columns else []
                )
            
            # Search results
            if search_term:
                mask = (
                    self.contest_df['Camp Name'].str.contains(search_term, case=False, na=False) |
                    self.contest_df['Camp Type'].str.contains(search_term, case=False, na=False)
                )
                results = self.contest_df[mask]
                
                if not results.empty:
                    st.success(f"Found {len(results)} contests")
                    st.dataframe(results, use_container_width=True)
                else:
                    st.info("No contests found")
        
        with tab2:
            st.markdown("#### Search Winners")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                winner_search = st.text_input("Search by Customer Name:")
            with col2:
                gift_search = st.text_input("Search by Gift:")
            with col3:
                contest_search = st.text_input("Search by Contest:")
            
            if winner_search or gift_search or contest_search:
                mask = pd.Series(False, index=self.winner_df.index)
                
                if winner_search:
                    mask = mask | (
                        self.winner_df['customer_firstname'].str.contains(winner_search, case=False, na=False) |
                        self.winner_df['business_displayname'].str.contains(winner_search, case=False, na=False)
                    )
                
                if gift_search:
                    mask = mask | self.winner_df['Gift'].str.contains(gift_search, case=False, na=False)
                
                if contest_search:
                    mask = mask | self.winner_df['Contest'].str.contains(contest_search, case=False, na=False)
                
                results = self.winner_df[mask]
                
                if not results.empty:
                    st.success(f"Found {len(results)} winner records")
                    st.dataframe(results, use_container_width=True)
                else:
                    st.info("No winner records found")
        
        with tab3:
            st.markdown("#### Cross Reference")
            st.info("Compare contest data with winner data")
            
            # Show contests with winners
            if not self.contest_df.empty and not self.winner_df.empty:
                contests_with_winners = self.contest_df[
                    self.contest_df['Merch ID'].isin(self.winner_df['Merch ID'])
                ]
                
                st.metric("Contests with Winners", len(contests_with_winners))
                
                if len(contests_with_winners) > 0:
                    st.dataframe(
                        contests_with_winners[['Merch ID', 'Camp Name', 'Start Date', 'End Date']],
                        use_container_width=True
                    )
    
    def show_data_management(self):
        """Show data upload/management section"""
        st.markdown("### ⚙️ Data Management")
        
        tab1, tab2 = st.tabs(["📊 Data Preview", "🔍 Data Quality"])
        
        with tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Contest Data Preview")
                if not self.contest_df.empty:
                    st.dataframe(self.contest_df.head(), use_container_width=True)
                    st.caption(f"Total rows: {len(self.contest_df)}")
                else:
                    st.warning("No contest data loaded")
            
            with col2:
                st.markdown("#### Winner Data Preview")
                if not self.winner_df.empty:
                    st.dataframe(self.winner_df.head(), use_container_width=True)
                    st.caption(f"Total rows: {len(self.winner_df)}")
                else:
                    st.warning("No winner data loaded")
        
        with tab2:
            st.markdown("#### Data Quality Check")
            
            if st.button("Run Quality Checks"):
                with st.spinner("Analyzing data quality..."):
                    issues = []
                    
                    # Check contest data
                    if not self.contest_df.empty:
                        # Missing dates
                        missing_dates = self.contest_df[
                            self.contest_df['Start Date'].isna() | 
                            self.contest_df['End Date'].isna()
                        ]
                        if len(missing_dates) > 0:
                            issues.append(f"❌ {len(missing_dates)} contests with missing dates")
                        
                        # Invalid date ranges
                        invalid_dates = self.contest_df[
                            self.contest_df['Start Date'] > self.contest_df['End Date']
                        ]
                        if len(invalid_dates) > 0:
                            issues.append(f"❌ {len(invalid_dates)} contests with invalid date range")
                    
                    # Check winner data
                    if not self.winner_df.empty:
                        # Missing business IDs
                        if 'businessid' in self.winner_df.columns:
                            missing_bzid = self.winner_df[self.winner_df['businessid'].isna()]
                            if len(missing_bzid) > 0:
                                issues.append(f"❌ {len(missing_bzid)} winners with missing Business ID")
                        
                        # Missing gift sent dates
                        if 'Gift Sent Date' in self.winner_df.columns:
                            pending_gifts = self.winner_df[self.winner_df['Gift Sent Date'].isna()]
                            if len(pending_gifts) > 0:
                                issues.append(f"⚠️ {len(pending_gifts)} gifts not yet sent")
                    
                    if issues:
                        st.warning("### Issues Found")
                        for issue in issues:
                            st.write(issue)
                    else:
                        st.success("✅ All data quality checks passed!")
    
    def export_current_view(self, view_name):
        """Export current view data"""
        st.info(f"Exporting {view_name}...")
        # Implementation would depend on what data to export

def main():
    dashboard = ContestDashboard()
    dashboard.create_dashboard()

if __name__ == "__main__":
    main()
