"""
Administrator Dashboard Module - FIXED
"""
import streamlit as st
from .shared_components import show_system_status_widget, show_unit_lookup_widget
from permission_manager import get_permission_manager, check_permission_ui
from secure_ui_helpers import create_secure_ui, secure_section_header

class AdminDashboard:
    def __init__(self):
        self.user = {
            "username": st.session_state.get("username", ""),
            "name": st.session_state.get("user_name", "Admin"),
            "email": st.session_state.get("user_email", ""),
            "role": st.session_state.get("user_role", "admin"),
        }

    def show(self, force_workspace=None):
        """
        Show admin dashboard with optional forced workspace
        
        Args:
            force_workspace: If provided, skip workspace selection and go directly to this workspace
        """
        st.markdown(f"""
        <div class="main-header">
            <h1>Administrator Control Center</h1>
            <p>Complete System Management & Data Processing</p>
            <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
                <span>Welcome back, <strong>{self.user['name']}</strong>!</span>
                <span style="margin-left: 2rem;">Role: <strong>System Administrator</strong></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # If force_workspace is provided, use it directly
        if force_workspace:
            current_workspace = force_workspace
            # Store it in session state for consistency
            st.session_state.admin_workspace = force_workspace
        else:
            # Show workspace selection only if not forced
            if "admin_workspace" not in st.session_state:
                st.session_state.admin_workspace = "Data Processing"

            st.markdown("### Choose Your Workspace")
            workspace_choice = st.radio(
                "Select your admin interface:",
                ["Data Processing", "System Administration"],
                index=0 if st.session_state.admin_workspace == "Data Processing" else 1,
                horizontal=True,
                help="Data Processing: Upload and process inspection files | System Administration: User and system management"
            )
            
            if workspace_choice != st.session_state.admin_workspace:
                st.session_state.admin_workspace = workspace_choice
                st.rerun()
            
            current_workspace = st.session_state.admin_workspace

        st.markdown("---")

        # Route to appropriate workspace
        if current_workspace == "System Administration":
            self.show_system_administration()
        else:
            self.show_data_processing()

    def show_system_administration(self):
        """System administration interface"""
        try:
            from enhanced_admin_management import show_enhanced_admin_dashboard
            show_enhanced_admin_dashboard()
        except ImportError:
            self.show_basic_admin_interface()

    def show_basic_admin_interface(self):
        """Basic admin interface fallback"""
        st.markdown("### Basic System Administration")
        
        show_system_status_widget()
        
        # Basic user management info
        st.markdown("### User Management")
        st.info("Basic user management available. Install enhanced_admin_management.py for full features.")
        
        # Show current system state
        if st.session_state.processed_data is not None:
            st.markdown("### Current System Data")
            metrics = st.session_state.metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Building", metrics.get('building_name', 'N/A'))
            with col2:
                st.metric("Total Units", metrics.get('total_units', 0))
            with col3:
                st.metric("Total Defects", metrics.get('total_defects', 0))

    def show_data_processing(self):
        """Data processing interface for admins"""
        st.info("Full inspection processing interface with administrator privileges")
        
        # IMPORTANT: Set flag to trigger full processing interface in main app
        st.session_state.admin_needs_full_processing = True
        
        # Show unit lookup if data exists
        if st.session_state.processed_data is not None:
            show_unit_lookup_widget(st.session_state.processed_data, "admin_")
        
        # Display admin-specific processing info
        st.markdown("#### Administrator Processing Capabilities")
        st.success("✓ Upload inspection data")
        st.success("✓ Process all file types")
        st.success("✓ Generate all report types")
        st.success("✓ Access all system functions")
        
        if st.session_state.processed_data is None:
            st.warning("No inspection data loaded. Use the main interface above to upload and process data.")