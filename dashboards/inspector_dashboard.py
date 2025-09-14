"""
Inspector Dashboard Module
"""
import streamlit as st
from .shared_components import show_unit_lookup_widget
from permission_manager import get_permission_manager, check_permission_ui
from secure_ui_helpers import create_secure_ui, secure_section_header

class InspectorDashboard:
    def __init__(self):
        self.user = self.get_current_user()
    
    def get_current_user(self):
        return {
            "username": st.session_state.get("username", ""),
            "name": st.session_state.get("user_name", "Inspector"),
            "email": st.session_state.get("user_email", ""),
            "role": st.session_state.get("user_role", "inspector")
        }
    
    def show(self):
        """Main inspector dashboard - full processing interface"""
        st.markdown(f"""
        <div class="main-header">
            <h1>Inspection Report Processor</h1>
            <p>Professional Data Processing Interface</p>
            <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
                <span>Welcome back, <strong>{self.user['name']}</strong>!</span>
                <span style="margin-left: 2rem;">Role: <strong>Inspector</strong></span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # IMPORTANT: Set flag to trigger full processing interface in main app
        st.session_state.inspector_needs_full_processing = True
        
        # Show processing capabilities
        st.markdown("### Your Processing Capabilities")
        col1, col2 = st.columns(2)
        
        with col1:
            st.success("✓ Upload inspection CSV files")
            st.success("✓ Load and manage trade mappings")
            st.success("✓ Process inspection data")
        
        with col2:
            st.success("✓ Generate Excel reports")
            st.success("✓ Generate Word reports") 
            st.success("✓ Unit defect lookup")
        
        # Show unit lookup if data exists
        if st.session_state.processed_data is not None:
            st.markdown("---")
            show_unit_lookup_widget(st.session_state.processed_data, "inspector_")
        else:
            st.info("Upload and process your inspection data using the interface above to get started.")