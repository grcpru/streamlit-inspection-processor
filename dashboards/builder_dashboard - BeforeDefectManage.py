"""
Builder Dashboard Module
"""
import streamlit as st
import pandas as pd                   # ✅ ADD
from datetime import datetime         # ✅ ADD
from .shared_components import get_corrected_database_stats
from permission_manager import get_permission_manager, check_permission_ui
from secure_ui_helpers import create_secure_ui, secure_section_header

class BuilderDashboard:
    def __init__(self):
        self.user = self.get_current_user()
    
    def get_current_user(self):
        return {
            "username": st.session_state.get("username", ""),
            "name": st.session_state.get("user_name", "Builder"),
            "email": st.session_state.get("user_email", ""),
            "role": st.session_state.get("user_role", "builder")
        }
    
    def show(self):
        """Main builder dashboard display"""
        st.markdown(f"""
        <div class="main-header">
            <h1>Builder Workspace</h1>
            <p>Work Management Interface</p>
            <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
                <span>Welcome back, <strong>{self.user['name']}</strong>!</span>
                <span style="margin-left: 2rem;">Role: <strong>Builder</strong></span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        self.show_work_assignments()
    
    def show_work_assignments(self):
        """Show builder work assignments"""
        st.markdown("### Your Work Assignments")
        
        try:
            from data_persistence import DataPersistenceManager
            persistence_manager = DataPersistenceManager()
            
            # Get open defects for builder
            open_defects = persistence_manager.get_defects_by_status("open")
            
            if open_defects:
                st.success(f"You have {len(open_defects)} open defects to work on")
                
                # Convert to DataFrame for easier handling
                df_cols = ["ID", "Inspection ID", "Unit", "Unit Type", "Room", "Component", 
                           "Trade", "Urgency", "Planned Completion", "Status", "Created At", "Building"]
                df = pd.DataFrame(open_defects, columns=df_cols)
                
                # Show defects by urgency
                urgent_df = df[df["Urgency"] == "Urgent"]
                high_priority_df = df[df["Urgency"] == "High Priority"]
                normal_df = df[df["Urgency"] == "Normal"]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Urgent", len(urgent_df))
                with col2:
                    st.metric("High Priority", len(high_priority_df))
                with col3:
                    st.metric("Normal", len(normal_df))
                
                # Show defects table
                st.markdown("**Your Assigned Defects:**")
                display_df = df[["Unit", "Room", "Component", "Trade", "Urgency", "Planned Completion", "Building"]].copy()
                st.dataframe(display_df, use_container_width=True)
                
                # Builder work reports
                self.show_work_reports(df)
            else:
                st.info("No open defects assigned. Check with your project manager.")
        
        except Exception as e:
            st.error(f"Error loading work assignments: {e}")
    
    def show_work_reports(self, df):
        """Show work report generation options"""
        st.markdown("---")
        st.markdown("### Work Reports")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Today's Work List", type="primary", use_container_width=True):
                today_work = df[pd.to_datetime(df["Planned Completion"]) <= pd.Timestamp.now() + pd.Timedelta(days=1)]
                if len(today_work) > 0:
                    csv = today_work.to_csv(index=False)
                    st.download_button(
                        "Download Today's Work List",
                        data=csv,
                        file_name=f"today_work_list_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.info("No work scheduled for today")
        
        with col2:
            if st.button("Weekly Schedule", type="secondary", use_container_width=True):
                week_work = df[pd.to_datetime(df["Planned Completion"]) <= pd.Timestamp.now() + pd.Timedelta(days=7)]
                if len(week_work) > 0:
                    csv = week_work.to_csv(index=False)
                    st.download_button(
                        "Download Weekly Schedule",
                        data=csv,
                        file_name=f"weekly_schedule_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.info("No work scheduled for this week")
        
        with col3:
            if st.button("Priority Items", use_container_width=True):
                priority_work = df[df["Urgency"].isin(["Urgent", "High Priority"])]
                if len(priority_work) > 0:
                    csv = priority_work.to_csv(index=False)
                    st.download_button(
                        "Download Priority Items",
                        data=csv,
                        file_name=f"priority_items_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.success("No priority items!")
