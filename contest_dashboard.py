# contest_dashboard.py
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="Contest & Winner Dashboard",
    page_icon="🏆",
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
            # Load credentials from file
            creds = Credentials.from_service_account_file(
                "google_credentials.json", 
                scopes=self.scope
            )
            
            client = gspread.authorize(creds)
            spreadsheet = client.open_by_key(self.sheet_id)
            return spreadsheet
        except Exception as e:
            st.error(f"Error connecting to Google Sheets: {e}")
            st.info("Make sure 'google_credentials.json' is in the same folder and Google Sheet is shared with the service account.")
            return None
    
    def get_sheet_data(self, sheet_name):
        """Get data from a specific sheet"""
        try:
            spreadsheet = self.connect()
            if spreadsheet:
                sheet = spreadsheet.worksheet(sheet_name)
                data = sheet.get_all_records()
                df = pd.DataFrame(data)
                return df
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
        try:
            # Convert date columns to datetime for Contest Details
            if not self.contest_df.empty:
                date_columns_contest = ['Start Date', 'End Date', 'Winner Announcement Date']
                for col in date_columns_contest:
                    if col in self.contest_df.columns:
                        self.contest_df[col] = pd.to_datetime(self.contest_df[col], errors='coerce', dayfirst=True)
                
                # Add duration column
                if 'Start Date' in self.contest_df.columns and 'End Date' in self.contest_df.columns:
                    self.contest_df['Duration (days)'] = (self.contest_df['End Date'] - self.contest_df['Start Date']).dt.days + 1
            
            # Convert date columns for Winner Details
            if not self.winner_df.empty:
                date_columns_winner = ['Start Date', 'End Date', 'Winner Announcement Date', 'Gift Sent Date']
                for col in date_columns_winner:
                    if col in self.winner_df.columns:
                        self.winner_df[col] = pd.to_datetime(self.winner_df[col], errors='coerce', dayfirst=True)
                
                # Clean businessid column
                if 'businessid' in self.winner_df.columns:
                    self.winner_df['businessid'] = self.winner_df['businessid'].astype(str).str.strip()
        except Exception as e:
            st.warning(f"Some data cleaning issues: {e}")
    
    def get_running_contests(self, start_date, end_date):
        """Get contests running in selected date range"""
        if self.contest_df.empty or 'Start Date' not in self.contest_df.columns or 'End Date' not in self.contest_df.columns:
            return pd.DataFrame()
        
        try:
            mask = (
                (self.contest_df['Start Date'] <= pd.Timestamp(end_date)) & 
                (self.contest_df['End Date'] >= pd.Timestamp(start_date))
            )
            return self.contest_df[mask].sort_values('Start Date')
        except:
            return pd.DataFrame()
    
    def get_business_history(self, business_id):
        """Get contest history for a specific business ID"""
        if self.winner_df.empty or 'businessid' not in self.winner_df.columns:
            return pd.DataFrame()
        
        try:
            mask = self.winner_df['businessid'].astype(str).str.contains(str(business_id), na=False)
            results = self.winner_df[mask]
            if 'Winner Announcement Date' in results.columns:
                return results.sort_values('Winner Announcement Date', ascending=False)
            return results
        except:
            return pd.DataFrame()
    
    def create_dashboard(self):
        """Main dashboard function"""
        
        # Header
        st.markdown('<h1 class="main-header">🏆 Contest & Winner Dashboard</h1>', 
                   unsafe_allow_html=True)
        
        # Data Status
        col1, col2 = st.columns(2)
        with col1:
            contest_count = len(self.contest_df) if not self.contest_df.empty else 0
            st.metric("Contest Records", contest_count)
        with col2:
            winner_count = len(self.winner_df) if not self.winner_df.empty else 0
            st.metric("Winner Records", winner_count)
        
        if self.contest_df.empty or self.winner_df.empty:
            st.warning("⚠️ Some data may not have loaded properly. Click Refresh button.")
        
        # Sidebar
        with st.sidebar:
            st.markdown("### 🔍 Navigation")
            app_mode = st.selectbox(
                "Select View",
                ["📊 Dashboard Overview", 
                 "📅 Contest Calendar", 
                 "🏆 Winner Lookup",
                 "📈 Analytics",
                 "🔍 Advanced Search"]
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
            
            if st.button("🔄 Refresh Data"):
                self.load_data()
                st.success("Data refreshed!")
                st.rerun()
            
            if st.button("📊 Show Raw Data"):
                st.session_state.show_raw_data = True
            
            st.markdown("---")
            st.markdown("### 📊 Quick Stats")
            active = len(self.get_running_contests(custom_start, custom_end))
            st.metric("Active Contests", active)
            
            if not self.winner_df.empty and 'businessid' in self.winner_df.columns:
                unique_businesses = self.winner_df['businessid'].nunique()
                st.metric("Unique Winners", unique_businesses)
        
        # Check if we should show raw data
        if hasattr(st.session_state, 'show_raw_data') and st.session_state.show_raw_data:
            st.subheader("📋 Raw Data Preview")
            tab1, tab2 = st.tabs(["Contest Data", "Winner Data"])
            with tab1:
                if not self.contest_df.empty:
                    st.dataframe(self.contest_df)
                else:
                    st.info("No contest data available")
            with tab2:
                if not self.winner_df.empty:
                    st.dataframe(self.winner_df)
                else:
                    st.info("No winner data available")
            
            if st.button("Hide Raw Data"):
                st.session_state.show_raw_data = False
                st.rerun()
            return
        
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
            if not self.contest_df.empty and 'Start Date' in self.contest_df.columns:
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
            
            if 'Start Date' in available_cols and 'End Date' in available_cols:
                st.dataframe(
                    running_contests[available_cols],
                    use_container_width=True,
                    column_config={
                        "Start Date": st.column_config.DateColumn("Start Date"),
                        "End Date": st.column_config.DateColumn("End Date"),
                    }
                )
            else:
                st.dataframe(running_contests[available_cols], use_container_width=True)
            
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
            
            if available_recent_cols:
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
        
        if not contests_in_range.empty and 'Start Date' in contests_in_range.columns and 'End Date' in contests_in_range.columns:
            # Try to create Gantt chart if we have required columns
            if 'Camp Name' in contests_in_range.columns and 'Camp Type' in contests_in_range.columns:
                try:
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
                except Exception as e:
                    st.info("Could not create timeline chart. Showing table instead.")
            
            # Detailed table with filtering
            st.markdown("### 📋 Contest Details")
            
            # Add filters
            filter_cols = st.columns(3)
            with filter_cols[0]:
                if 'Camp Type' in contests_in_range.columns:
                    camp_types = ["All"] + sorted(contests_in_range['Camp Type'].dropna().unique().tolist())
                    selected_type = st.selectbox("Filter by Camp Type", camp_types)
            
            with filter_cols[1]:
                if 'KAM' in contests_in_range.columns:
                    kams = ["All"] + sorted(contests_in_range['KAM'].dropna().unique().tolist())
                    selected_kam = st.selectbox("Filter by KAM", kams)
            
            with filter_cols[2]:
                if 'To Whom?' in contests_in_range.columns:
                    audiences = ["All"] + sorted(contests_in_range['To Whom?'].dropna().unique().tolist())
                    selected_audience = st.selectbox("Filter by Audience", audiences)
            
            # Apply filters
            filtered_df = contests_in_range.copy()
            if 'selected_type' in locals() and selected_type != "All":
                filtered_df = filtered_df[filtered_df['Camp Type'] == selected_type]
            if 'selected_kam' in locals() and selected_kam != "All":
                filtered_df = filtered_df[filtered_df['KAM'] == selected_kam]
            if 'selected_audience' in locals() and selected_audience != "All":
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
            business_id = st.text_input("Enter Business ID (e.g., BZID-1304470286):", 
                                       "")
            
            search_button = st.button("🔍 Search", type="primary")
            
            if search_button and business_id:
                with st.spinner("Searching..."):
                    history = self.get_business_history(business_id)
                    
                    if not history.empty:
                        st.success(f"✅ Found {len(history)} winning records")
                        
                        # Display quick stats
                        total_wins = len(history)
                        
                        # Try to get first and last win dates
                        first_win = "N/A"
                        last_win = "N/A"
                        if 'Winner Announcement Date' in history.columns:
                            first_win_date = history['Winner Announcement Date'].min()
                            last_win_date = history['Winner Announcement Date'].max()
                            if pd.notna(first_win_date):
                                first_win = first_win_date.strftime('%d-%b-%Y')
                            if pd.notna(last_win_date):
                                last_win = last_win_date.strftime('%d-%b-%Y')
                        
                        # Get customer and business names
                        customer_name = history.iloc[0].get('customer_firstname', 'N/A') if len(history) > 0 else 'N/A'
                        business_name = history.iloc[0].get('business_displayname', 'N/A') if len(history) > 0 else 'N/A'
                        
                        st.markdown(f"""
                        <div class="success-box">
                        <strong>📊 Business Summary:</strong><br>
                        • Total Wins: {total_wins}<br>
                        • First Win: {first_win}<br>
                        • Last Win: {last_win}<br>
                        • Customer: {customer_name}<br>
                        • Business: {business_name}
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
                st.markdown(f"### 🏆 Winning History")
                
                # Summary metrics
                summary_cols = st.columns(3)
                with summary_cols[0]:
                    st.metric("Total Wins", len(history))
                with summary_cols[1]:
                    if 'Contest' in history.columns:
                        unique_contests = history['Contest'].nunique()
                        st.metric("Unique Contests", unique_contests)
                with summary_cols[2]:
                    if 'Gift' in history.columns:
                        total_gifts = history['Gift'].nunique()
                        st.metric("Different Gifts", total_gifts)
                
                # Display history table
                display_cols = ['Winner Announcement Date', 'Contest', 'Gift', 
                              'Camp Description', 'Gift Sent Date', 'Owner']
                available_display_cols = [col for col in display_cols if col in history.columns]
                
                if available_display_cols:
                    column_config = {}
                    if 'Winner Announcement Date' in available_display_cols:
                        column_config['Winner Announcement Date'] = st.column_config.DateColumn("Announcement Date")
                    if 'Gift Sent Date' in available_display_cols:
                        column_config['Gift Sent Date'] = st.column_config.DateColumn("Gift Sent Date")
                    
                    st.dataframe(
                        history[available_display_cols],
                        use_container_width=True,
                        column_config=column_config if column_config else None
                    )
    
    def show_analytics(self):
        """Show analytics dashboard"""
        st.markdown("### 📈 Contest Analytics")
        
        if self.contest_df.empty:
            st.warning("No contest data available for analytics")
            return
        
        # KPIs
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if 'Camp Type' in self.contest_df.columns:
                contest_types = self.contest_df['Camp Type'].nunique()
                st.metric("Contest Types", contest_types)
        
        with col2:
            if 'Duration (days)' in self.contest_df.columns:
                avg_duration = self.contest_df['Duration (days)'].mean()
                st.metric("Avg Duration", f"{avg_duration:.1f} days")
        
        with col3:
            if 'KAM' in self.contest_df.columns:
                kam_count = self.contest_df['KAM'].nunique()
                st.metric("KAMs Involved", kam_count)
        
        with col4:
            if 'To Whom?' in self.contest_df.columns:
                audience_count = self.contest_df['To Whom?'].nunique()
                st.metric("Audience Types", audience_count)
        
        # Visualizations - only if we have data
        if 'Camp Type' in self.contest_df.columns and not self.contest_df['Camp Type'].empty:
            col1, col2 = st.columns(2)
            
            with col1:
                # Contest type distribution
                type_dist = self.contest_df['Camp Type'].value_counts()
                if not type_dist.empty:
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
        
        tab1, tab2 = st.tabs(["Search Contests", "Search Winners"])
        
        with tab1:
            st.markdown("#### Search Contests")
            
            col1, col2 = st.columns(2)
            with col1:
                search_term = st.text_input("Search in Camp Name/Type:", key="contest_search")
            with col2:
                if not self.contest_df.empty and 'KAM' in self.contest_df.columns:
                    kam_options = ["All"] + sorted(self.contest_df['KAM'].dropna().unique().tolist())
                    kam_filter = st.selectbox("Filter by KAM:", kam_options, key="contest_kam")
            
            if search_term:
                mask = (
                    self.contest_df['Camp Name'].astype(str).str.contains(search_term, case=False, na=False) |
                    self.contest_df['Camp Type'].astype(str).str.contains(search_term, case=False, na=False)
                )
                results = self.contest_df[mask]
                
                # Apply KAM filter
                if 'kam_filter' in locals() and kam_filter != "All":
                    results = results[results['KAM'] == kam_filter]
                
                if not results.empty:
                    st.success(f"Found {len(results)} contests")
                    st.dataframe(results, use_container_width=True)
                else:
                    st.info("No contests found")
        
        with tab2:
            st.markdown("#### Search Winners")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                winner_search = st.text_input("Search by Customer Name:", key="winner_name")
            with col2:
                gift_search = st.text_input("Search by Gift:", key="gift_search")
            with col3:
                contest_search = st.text_input("Search by Contest:", key="winner_contest")
            
            if winner_search or gift_search or contest_search:
                mask = pd.Series(False, index=self.winner_df.index)
                
                if winner_search:
                    if 'customer_firstname' in self.winner_df.columns:
                        mask = mask | self.winner_df['customer_firstname'].astype(str).str.contains(winner_search, case=False, na=False)
                    if 'business_displayname' in self.winner_df.columns:
                        mask = mask | self.winner_df['business_displayname'].astype(str).str.contains(winner_search, case=False, na=False)
                
                if gift_search and 'Gift' in self.winner_df.columns:
                    mask = mask | self.winner_df['Gift'].astype(str).str.contains(gift_search, case=False, na=False)
                
                if contest_search and 'Contest' in self.winner_df.columns:
                    mask = mask | self.winner_df['Contest'].astype(str).str.contains(contest_search, case=False, na=False)
                
                results = self.winner_df[mask]
                
                if not results.empty:
                    st.success(f"Found {len(results)} winner records")
                    st.dataframe(results, use_container_width=True)
                else:
                    st.info("No winner records found")

def main():
    # Initialize dashboard
    dashboard = ContestDashboard()
    dashboard.create_dashboard()

if __name__ == "__main__":
    main()
