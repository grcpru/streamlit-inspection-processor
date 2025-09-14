import streamlit as st
import pandas as pd
from io import BytesIO, StringIO
from datetime import datetime, timedelta
import pytz
import traceback
import zipfile
import hashlib
import time
import json
import os
import sqlite3
import uuid
from typing import Dict, List, Optional, Tuple

# Import data persistence module
from data_persistence import (
    DataPersistenceManager, 
    save_trade_mapping_to_database, 
    load_trade_mapping_from_database
)

# Try to import the professional report generators
WORD_REPORT_AVAILABLE = False
EXCEL_REPORT_AVAILABLE = False
WORD_IMPORT_ERROR = None
EXCEL_IMPORT_ERROR = None

try:
    from excel_report_generator import generate_professional_excel_report, generate_filename
    EXCEL_REPORT_AVAILABLE = True
except Exception as e:
    EXCEL_IMPORT_ERROR = str(e)

try:
    from docx import Document
    from word_report_generator import generate_professional_word_report
    WORD_REPORT_AVAILABLE = True
except Exception as e:
    WORD_IMPORT_ERROR = str(e)

# =============================================================================
# ENHANCED DATABASE AUTHENTICATION SYSTEM
# =============================================================================

class DatabaseAuthManager:
    """Database-powered authentication manager for Streamlit"""
    
    def __init__(self, db_path="inspection_system.db"):
        self.db_path = db_path
        self.session_timeout = 8 * 60 * 60  # 8 hours
        
        # Ensure database exists
        self._init_database_if_needed()
        
        # Role capabilities with enhanced permissions
        self.role_capabilities = {
            "admin": {
                "can_upload": True,
                "can_process": True,
                "can_manage_users": True,
                "can_approve_defects": True,
                "can_view_all": True,
                "can_generate_reports": True,
                "dashboard_type": "admin"
            },
            "property_developer": {
                "can_upload": False,
                "can_process": False,
                "can_manage_users": False,
                "can_approve_defects": True,
                "can_view_all": False,
                "can_generate_reports": True,  # Now can generate reports
                "dashboard_type": "portfolio"
            },
            "project_manager": {
                "can_upload": True,
                "can_process": True,
                "can_manage_users": False,
                "can_approve_defects": True,
                "can_view_all": False,
                "can_generate_reports": True,
                "dashboard_type": "project"
            },
            "inspector": {
                "can_upload": True,
                "can_process": True,
                "can_manage_users": False,
                "can_approve_defects": False,
                "can_view_all": False,
                "can_generate_reports": True,
                "dashboard_type": "inspector"
            },
            "builder": {
                "can_upload": False,
                "can_process": False,
                "can_manage_users": False,
                "can_approve_defects": False,
                "can_view_all": False,
                "can_generate_reports": True,  # Now can generate work reports
                "dashboard_type": "builder"
            }
        }
    
    def _init_database_if_needed(self):
        """Initialize database if it doesn't exist"""
        if not os.path.exists(self.db_path):
            st.error(f"Database not found! Please run: python complete_database_setup.py")
            st.stop()
    
    def _hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = "inspection_app_salt_2024"
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def authenticate(self, username: str, password: str) -> Tuple[bool, str]:
        """Authenticate user against database"""
        if not username or not password:
            return False, "Please enter username and password"
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            password_hash = self._hash_password(password)
            
            cursor.execute('''
                SELECT username, full_name, email, role, is_active
                FROM users 
                WHERE username = ? AND password_hash = ? AND is_active = 1
            ''', (username, password_hash))
            
            user_data = cursor.fetchone()
            
            if user_data:
                cursor.execute('''
                    UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?
                ''', (username,))
                conn.commit()
                conn.close()
                return True, "Login successful"
            else:
                conn.close()
                return False, "Invalid username or password"
                
        except Exception as e:
            return False, f"Database error: {str(e)}"
    
    def get_user_info(self, username: str) -> Optional[Dict]:
        """Get complete user information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT username, full_name, email, role, is_active, last_login
                FROM users WHERE username = ?
            ''', (username,))
            
            user_data = cursor.fetchone()
            conn.close()
            
            if user_data:
                return {
                    "username": user_data[0],
                    "full_name": user_data[1],
                    "email": user_data[2],
                    "role": user_data[3],
                    "is_active": user_data[4],
                    "last_login": user_data[5],
                    "capabilities": self.role_capabilities.get(user_data[3], {})
                }
            return None
        except Exception:
            return None
    
    def create_session(self, username: str):
        """Create Streamlit session with database user info"""
        user_info = self.get_user_info(username)
        
        if user_info:
            st.session_state.authenticated = True
            st.session_state.username = user_info["username"]
            st.session_state.user_name = user_info["full_name"]
            st.session_state.user_email = user_info["email"]
            st.session_state.user_role = user_info["role"]
            st.session_state.login_time = time.time()
            st.session_state.user_capabilities = user_info["capabilities"]
            st.session_state.dashboard_type = user_info["capabilities"].get("dashboard_type", "inspector")
    
    def is_session_valid(self) -> bool:
        """Check if current session is valid"""
        if not st.session_state.get("authenticated", False):
            return False
        
        if not st.session_state.get("login_time"):
            return False
        
        if time.time() - st.session_state.login_time > self.session_timeout:
            self.logout()
            return False
        
        return True
    
    def logout(self):
        """Logout current user"""
        auth_keys = [
            "authenticated", "username", "user_name", "user_email", 
            "user_role", "login_time", "user_capabilities", "dashboard_type"
        ]
        for key in auth_keys:
            if key in st.session_state:
                del st.session_state[key]
        
        app_keys = ["trade_mapping", "processed_data", "metrics", "step_completed", "report_images"]
        for key in app_keys:
            if key in st.session_state:
                del st.session_state[key]
    
    def get_current_user(self) -> Dict:
        """Get current user information"""
        return {
            "username": st.session_state.get("username", ""),
            "name": st.session_state.get("user_name", "User"),
            "email": st.session_state.get("user_email", ""),
            "role": st.session_state.get("user_role", "user"),
            "capabilities": st.session_state.get("user_capabilities", {}),
            "dashboard_type": st.session_state.get("dashboard_type", "inspector")
        }
    
    def can_user_perform_action(self, action: str) -> bool:
        """Check if current user can perform specific action"""
        capabilities = st.session_state.get("user_capabilities", {})
        return capabilities.get(action, False)
    
    def change_password(self, username, old_password, new_password):
        """Change user password"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            old_hash = self._hash_password(old_password)
            cursor.execute('''
                SELECT 1 FROM users WHERE username = ? AND password_hash = ?
            ''', (username, old_hash))
            
            if not cursor.fetchone():
                conn.close()
                return False, "Current password is incorrect"
            
            if len(new_password) < 6:
                conn.close()
                return False, "New password must be at least 6 characters"
            
            new_hash = self._hash_password(new_password)
            cursor.execute('''
                UPDATE users SET password_hash = ? WHERE username = ?
            ''', (new_hash, username))
            
            conn.commit()
            conn.close()
            
            return True, "Password changed successfully"
            
        except Exception as e:
            return False, f"Database error: {str(e)}"

# Initialize the enhanced auth manager
@st.cache_resource
def get_auth_manager():
    """Get singleton auth manager instance"""
    return DatabaseAuthManager()

def show_enhanced_login_page():
    """Enhanced login page with database authentication"""
    
    st.markdown("""
    <div style="max-width: 400px; margin: 2rem auto; padding: 2rem; 
                background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h2 style="text-align: center; color: #1976d2; margin-bottom: 2rem;">
            Building Inspection Report System
        </h2>
        <h3 style="text-align: center; color: #666; margin-bottom: 2rem;">
            Please Login to Continue
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    auth_manager = get_auth_manager()
    
    with st.form("enhanced_login_form"):
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("### Login")
            
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            login_button = st.form_submit_button("Login", use_container_width=True, type="primary")
            
            if login_button:
                if username and password:
                    success, message = auth_manager.authenticate(username, password)
                    
                    if success:
                        auth_manager.create_session(username)
                        st.success(message)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Please enter both username and password")
    
    # Demo credentials with role explanations
    with st.expander("Demo Credentials", expanded=False):
        st.info("""
        **Available Test Accounts:**
        
        **System Administrator:**
        - Username: `admin` | Password: `admin123`
        - Full system access, user management
        
        **Property Developer:**
        - Username: `developer1` | Password: `dev123`
        - Portfolio view, defect approval, can generate reports
        
        **Project Manager:**
        - Username: `manager1` | Password: `mgr123`
        - Project oversight, data processing
        
        **Site Inspector:**
        - Username: `inspector` | Password: `inspector123`
        - Data upload and processing
        
        **Builder:**
        - Username: `builder1` | Password: `build123`
        - Work reports, status updates
        """)

def show_enhanced_user_menu():
    """Enhanced user menu with role-specific content"""
    
    auth_manager = get_auth_manager()
    
    if not auth_manager.is_session_valid():
        return False
    
    user = auth_manager.get_current_user()
    
    # Create unique session key for this function
    sidebar_key_prefix = f"sidebar_{user['username']}_"
    
    with st.sidebar:
        st.markdown("---")
        st.markdown("### User Information")
        
        # Enhanced user info display
        st.markdown(f"""
        **Name:** {user['name']}  
        **Role:** {user['role'].replace('_', ' ').title()}  
        **Email:** {user['email']}  
        **Access:** {user['capabilities'].get('dashboard_type', 'standard').title()}
        """)
        
        # User account actions (for all users)
        st.markdown("---")
        st.markdown("### Account")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Change Password", use_container_width=True):
                st.session_state.show_password_change = True
        
        with col2:
            if st.button("Logout", use_container_width=True, type="primary"):
                auth_manager.logout()
                st.success("Logged out successfully!")
                st.rerun()
        
        # Password change form (if requested)
        if st.session_state.get("show_password_change", False):
            st.markdown("---")
            st.markdown("### Change Password")
            
            with st.form("password_change_form"):
                old_password = st.text_input("Current Password", type="password")
                new_password = st.text_input("New Password", type="password")
                confirm_password = st.text_input("Confirm New Password", type="password")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Update", use_container_width=True):
                        if new_password != confirm_password:
                            st.error("New passwords don't match")
                        elif len(new_password) < 6:
                            st.error("Password must be at least 6 characters")
                        else:
                            success, message = auth_manager.change_password(
                                user['username'], old_password, new_password
                            )
                            if success:
                                st.success(message)
                                st.session_state.show_password_change = False
                                st.rerun()
                            else:
                                st.error(message)
                
                with col2:
                    if st.form_submit_button("Cancel", use_container_width=True):
                        st.session_state.show_password_change = False
                        st.rerun()
        
        # Role-specific sidebar content - FIXED LOGIC
        if user['role'] == 'admin':
            # Admin sidebar content
            st.markdown("---") 
            st.markdown("### Administrator Access")
            st.success("🔑 **Full System Access**")
            
            # Simple admin metrics
            try:
                conn = sqlite3.connect("inspection_system.db")
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
                active_users = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM projects")
                total_projects = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM buildings") 
                total_buildings = cursor.fetchone()[0]
                
                conn.close()
                
                st.markdown("### System Status")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Active Users", active_users)
                    st.metric("Projects", total_projects)
                with col2:
                    st.metric("Buildings", total_buildings)
                    
            except Exception as e:
                st.caption(f"System metrics unavailable: {str(e)}")
        
        else:
            # Non-admin users: Show their specific permissions
            st.markdown("---") 
            st.markdown("### Your Access Rights")
            
            capabilities = user['capabilities']
            
            # Data Operations
            data_perms = []
            if capabilities.get('can_upload'):
                data_perms.append("📤 Upload Data")
            if capabilities.get('can_process'):
                data_perms.append("⚙️ Process Data")
            if capabilities.get('can_view_data'):
                data_perms.append("👁️ View Data")
            
            if data_perms:
                st.markdown("**Data Operations:**")
                for perm in data_perms:
                    st.success(perm)
            
            # Report Operations  
            if capabilities.get('can_generate_reports'):
                st.markdown("**Reports:**")
                st.success("📊 Generate Reports")
            
            # Defect Management
            defect_perms = []
            if capabilities.get('can_approve_defects'):
                defect_perms.append("✅ Approve Defects")
            if capabilities.get('can_update_defect_status'):
                defect_perms.append("🔄 Update Status")
            
            if defect_perms:
                st.markdown("**Defect Management:**")
                for perm in defect_perms:
                    st.success(perm)
        
        # Unit Lookup Section (only show if there's processed data)
        if hasattr(st.session_state, 'processed_data') and st.session_state.processed_data is not None:
            st.markdown("---")
            st.header("Quick Unit Lookup")
            
            # Get all unique units for dropdown
            all_units = sorted(st.session_state.processed_data["Unit"].unique())
            
            # Unit search
            selected_unit = st.selectbox(
                "Select Unit Number:",
                options=[""] + all_units,
                help="Quick lookup of defects for any unit",
                key=f"{sidebar_key_prefix}unit_lookup"
            )
            
            if selected_unit:
                unit_defects = lookup_unit_defects(st.session_state.processed_data, selected_unit)
                
                if len(unit_defects) > 0:
                    st.markdown(f"**Unit {selected_unit} Defects:**")
                    
                    # Count by urgency
                    urgent_count = len(unit_defects[unit_defects["Urgency"] == "Urgent"])
                    high_priority_count = len(unit_defects[unit_defects["Urgency"] == "High Priority"])
                    normal_count = len(unit_defects[unit_defects["Urgency"] == "Normal"])
                    
                    if urgent_count > 0:
                        st.error(f"Urgent: {urgent_count}")
                    if high_priority_count > 0:
                        st.warning(f"High Priority: {high_priority_count}")
                    if normal_count > 0:
                        st.info(f"Normal: {normal_count}")
                    
                    # Show defects in compact format
                    for _, defect in unit_defects.iterrows():
                        urgency_icon = "🚨" if defect["Urgency"] == "Urgent" else "⚠️" if defect["Urgency"] == "High Priority" else "🔧"
                        st.caption(f"{urgency_icon} {defect['Room']} - {defect['Component']} ({defect['Trade']}) - Due: {defect['PlannedCompletion']}")
                else:
                    st.success(f"Unit {selected_unit} has no defects!")
        
        # Word Report Images Section (only for users who can upload)
        if auth_manager.can_user_perform_action("can_upload"):
            st.markdown("---")
            st.header("Word Report Images")
            st.markdown("Upload images to enhance your Word report (optional):")
            
            with st.expander("Upload Report Images", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    logo_upload = st.file_uploader("Company Logo", type=['png', 'jpg', 'jpeg'], key=f"{sidebar_key_prefix}logo_upload")
                
                with col2:
                    cover_upload = st.file_uploader("Cover Image", type=['png', 'jpg', 'jpeg'], key=f"{sidebar_key_prefix}cover_upload")
                
                # Process uploaded images
                if st.button("Save Images for Report"):
                    images_saved = 0
                    
                    import tempfile
                    import os
                    
                    temp_dir = tempfile.gettempdir()
                    
                    if logo_upload:
                        logo_path = os.path.join(temp_dir, f"logo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                        with open(logo_path, "wb") as f:
                            f.write(logo_upload.getbuffer())
                        st.session_state.report_images["logo"] = logo_path
                        images_saved += 1
                    
                    if cover_upload:
                        cover_path = os.path.join(temp_dir, f"cover_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                        with open(cover_path, "wb") as f:
                            f.write(cover_upload.getbuffer())
                        st.session_state.report_images["cover"] = cover_path
                        images_saved += 1
                    
                    if images_saved > 0:
                        st.success(f"{images_saved} image(s) saved for Word report enhancement!")
                    else:
                        st.info("No images uploaded.")
                
                # Show current images status
                current_images = [k for k, v in st.session_state.report_images.items() if v is not None]
                if current_images:
                    st.info(f"Current images ready: {', '.join(current_images)}")
        
        # Reset button at the bottom
        st.markdown("---")
        if st.button("Reset All", help="Clear all data and start over"):
            for key in ["trade_mapping", "processed_data", "metrics", "step_completed", "building_info"]:
                if key in st.session_state:
                    if key == "step_completed":
                        st.session_state[key] = {"mapping": False, "processing": False}
                    elif key == "building_info":
                        st.session_state[key] = {
                            "name": "Professional Building Complex",
                            "address": "123 Professional Street\nMelbourne, VIC 3000"
                        }
                    else:
                        del st.session_state[key]
            st.rerun()
    
    return True

# =============================================================================
# DATA PROCESSING AND PERSISTENCE FUNCTIONS
# =============================================================================

def process_inspection_data_with_persistence(df, mapping, building_info, username):
    """Process data and automatically save to database"""
    
    # Process data (existing logic)
    processed_df, metrics = process_inspection_data(df, mapping, building_info)
    
    # Save to database immediately
    persistence_manager = DataPersistenceManager()
    success, inspection_id = persistence_manager.save_processed_inspection(
        processed_df, metrics, username
    )
    
    if success:
        st.success(f"Data processed and saved! Building: {metrics['building_name']}")
        # Update session state
        st.session_state.processed_data = processed_df
        st.session_state.metrics = metrics
        st.session_state.step_completed["processing"] = True
        return processed_df, metrics, True
    else:
        st.error(f"Data processing succeeded but database save failed: {inspection_id}")
        # Still update session state for current user
        st.session_state.processed_data = processed_df
        st.session_state.metrics = metrics
        st.session_state.step_completed["processing"] = True
        return processed_df, metrics, False

def initialize_user_data():
    """Load appropriate data based on user role"""
    user = get_auth_manager().get_current_user()
    
    # Always try to load latest data if session state is empty
    if st.session_state.processed_data is None:
        persistence_manager = DataPersistenceManager()
        processed_data, metrics = persistence_manager.load_latest_inspection()
        
        if processed_data is not None and metrics is not None:
            st.session_state.processed_data = processed_data
            st.session_state.metrics = metrics
            st.session_state.step_completed["processing"] = True
            return True
    
    return False

def load_trade_mapping():
    """Load trade mapping from database"""
    if len(st.session_state.trade_mapping) == 0:
        mapping_df = load_trade_mapping_from_database()
        if len(mapping_df) > 0:
            st.session_state.trade_mapping = mapping_df
            st.session_state.step_completed["mapping"] = True
            return True
    return False

# =============================================================================
# ROLE-SPECIFIC DASHBOARD FUNCTIONS
# =============================================================================

def show_admin_dashboard():
    """Complete admin dashboard with enhanced management capabilities"""
    try:
        from enhanced_admin_management import show_enhanced_admin_dashboard
        show_enhanced_admin_dashboard()
    except ImportError as e:
        st.error(f"Enhanced admin features not available: {str(e)}")
        st.info("Please ensure enhanced_admin_management.py is in your project folder")
        
        # Fallback to basic functionality
        st.markdown("### Basic Admin Interface")
        st.info("Using simplified admin interface. For full features, check file setup.")

def show_enhanced_developer_dashboard():
    """Enhanced Property Developer dashboard with report generation"""
    st.markdown("### Portfolio Executive Dashboard")
    
    # Show database debug info
    persistence_manager = DataPersistenceManager()
    stats = persistence_manager.get_database_stats()
    
    with st.expander("System Status", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Inspections", stats.get("total_inspections", 0))
        with col2:
            st.metric("Active Inspections", stats.get("active_inspections", 0))
        with col3:
            st.metric("Total Defects", stats.get("total_defects", 0))
    
    if st.session_state.metrics is not None:
        metrics = st.session_state.metrics
        
        # Executive summary
        st.markdown("### Current Building Analysis")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Building", metrics['building_name'])
        with col2:
            st.metric("Total Units", metrics['total_units'])
        with col3:
            st.metric("Ready for Settlement", f"{metrics['ready_units']} ({metrics['ready_pct']:.1f}%)")
        with col4:
            st.metric("Urgent Issues", metrics['urgent_defects'])
        
        # Summary tables (read-only)
        tab1, tab2, tab3 = st.tabs(["Trade Summary", "Unit Status", "Urgent Items"])
        
        with tab1:
            if len(metrics['summary_trade']) > 0:
                st.dataframe(metrics['summary_trade'], use_container_width=True)
            else:
                st.info("No trade defects found")
        
        with tab2:
            if len(metrics['summary_unit']) > 0:
                st.dataframe(metrics['summary_unit'], use_container_width=True)
            else:
                st.info("No unit defects found")
        
        with tab3:
            if len(metrics['urgent_defects_table']) > 0:
                urgent_display = metrics['urgent_defects_table'].copy()
                urgent_display["PlannedCompletion"] = pd.to_datetime(urgent_display["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
                st.dataframe(urgent_display, use_container_width=True)
                st.error(f"**{len(urgent_display)} URGENT defects require immediate attention!**")
            else:
                st.success("No urgent defects found!")
        
        # Unit lookup
        st.markdown("### Unit Lookup")
        all_units = sorted(st.session_state.processed_data["Unit"].unique())
        selected_unit = st.selectbox("Select Unit to View Details:", [""] + all_units, key="dev_unit_lookup")
        
        if selected_unit:
            unit_defects = lookup_unit_defects(st.session_state.processed_data, selected_unit)
            
            if len(unit_defects) > 0:
                st.markdown(f"**Unit {selected_unit} Defects:**")
                st.dataframe(unit_defects, use_container_width=True)
            else:
                st.success(f"Unit {selected_unit} has no defects!")
        
        # Executive Report Generation for Developers
        st.markdown("---")
        st.markdown("### Executive Reports")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Generate Executive Summary", type="primary", use_container_width=True):
                try:
                    if EXCEL_REPORT_AVAILABLE:
                        excel_buffer = generate_professional_excel_report(st.session_state.processed_data, metrics)
                        filename = f"Executive_Summary_{metrics['building_name']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                        
                        st.success("Executive summary generated!")
                        st.download_button(
                            "Download Executive Summary",
                            data=excel_buffer.getvalue(),
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    else:
                        st.error("Excel report generator not available")
                except Exception as e:
                    st.error(f"Error generating executive summary: {e}")
        
        with col2:
            if st.button("Portfolio Analytics", type="secondary", use_container_width=True):
                st.info("Portfolio analytics report would be generated here")
    
    else:
        st.warning("No inspection data available. Contact your team to process inspection data.")

def show_enhanced_builder_dashboard():
    """Enhanced Builder dashboard with work report generation"""
    st.markdown("### Builder Workspace")
    
    persistence_manager = DataPersistenceManager()
    
    # Get defects by status
    open_defects = persistence_manager.get_defects_by_status("open")
    
    if open_defects:
        st.success(f"You have {len(open_defects)} open defects to work on")
        
        # Convert to DataFrame for easier handling
        if open_defects:
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
        
        # Builder Work Reports
        st.markdown("---")
        st.markdown("### Work Reports")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Today's Work List", type="primary", use_container_width=True):
                # Filter today's work
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
                # Filter this week's work
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
                # Filter urgent and high priority
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
        
    else:
        st.info("No open defects assigned. Check with your project manager.")

# Fix for the sqlite3 import error in your Project Manager dashboard

def show_enhanced_project_manager_dashboard():
    """Enhanced Project Manager dashboard with building selection - Fixed sqlite3 import"""
    import sqlite3  # Add this import at the function level
    import pandas as pd
    
    st.markdown("### Project Management Dashboard")
    
    # Get buildings the project manager has access to
    persistence_manager = DataPersistenceManager()
    accessible_buildings = persistence_manager.get_buildings_for_user(st.session_state.username)
    
    if len(accessible_buildings) == 0:
        st.warning("No buildings assigned to your projects. Contact administrator for building access.")
        return
    
    # Building Selection Interface
    st.markdown("#### Select Building to Manage")
    
    # Create building options with project context
    building_options = []
    building_lookup = {}
    
    for building in accessible_buildings:
        # Safe unpacking to handle different number of returned columns
        try:
            if len(building) >= 5:
                building_id = building[0]
                building_name = building[1] 
                address = building[2]
                total_units = building[3]
                project_name = building[4]
                
                # Handle optional last_inspection column
                last_inspection = building[5] if len(building) > 5 else "No data"
                
                display_name = f"{building_name} ({project_name}) - {total_units} units"
                building_options.append(display_name)
                building_lookup[display_name] = {
                    'id': building_id,
                    'name': building_name,
                    'project': project_name,
                    'units': total_units,
                    'last_inspection': last_inspection
                }
            else:
                st.warning(f"Incomplete building data: {building}")
                continue
                
        except Exception as e:
            st.error(f"Error processing building data: {e}")
            continue
    
    if not building_options:
        st.error("No valid building data available. Please check your database.")
        return
    
    # Building selector
    selected_building_display = st.selectbox(
        "Choose building to manage:",
        options=building_options,
        help="Select a building to view detailed inspection data and management tools"
    )
    
    if selected_building_display:
        selected_building = building_lookup[selected_building_display]
        
        # Display building context
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Building", selected_building['name'])
        with col2:
            st.metric("Project", selected_building['project'])
        with col3:
            st.metric("Total Units", selected_building['units'])
        with col4:
            last_inspection = selected_building['last_inspection']
            if last_inspection and last_inspection != "No data":
                try:
                    if len(str(last_inspection)) > 10:
                        display_date = str(last_inspection)[:10]
                    else:
                        display_date = str(last_inspection)
                    st.metric("Last Inspection", display_date)
                except:
                    st.metric("Last Inspection", "No data")
            else:
                st.metric("Last Inspection", "None")
        
        # Load building-specific data with proper error handling
        try:
            # Check if method exists before calling
            if hasattr(persistence_manager, 'get_building_summary'):
                building_summary = persistence_manager.get_building_summary(selected_building['id'])
            else:
                # Manual building summary if method doesn't exist
                building_summary = get_manual_building_summary(selected_building['id'], persistence_manager.db_path)
            
            if building_summary:
                st.markdown("---")
                st.markdown("#### Building Management Overview")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Defects", building_summary.get('total_defects', 0))
                with col2:
                    st.metric("Urgent Defects", building_summary.get('urgent_count', 0))
                with col3:
                    total_defects = building_summary.get('total_defects', 0)
                    total_units = building_summary.get('total_units', selected_building['units'])
                    if total_units > 0:
                        completion_rate = max(0, (1 - (total_defects / (total_units * 10))) * 100)
                        st.metric("Completion Rate", f"{completion_rate:.1f}%")
                    else:
                        st.metric("Completion Rate", "0%")
                
                # Management Actions
                st.markdown("#### Management Actions")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("View Building Details", use_container_width=True):
                        st.session_state.pm_view_building = selected_building['id']
                        st.info("Detailed building view would load here")
                
                with col2:
                    if st.button("Generate Building Report", use_container_width=True):
                        try:
                            # Generate basic CSV report with proper import
                            conn = sqlite3.connect(persistence_manager.db_path)
                            cursor = conn.cursor()
                            
                            cursor.execute('''
                                SELECT id.unit_number, id.room, id.component, id.trade, 
                                       id.urgency, id.planned_completion, id.status
                                FROM inspection_defects id
                                JOIN processed_inspections pi ON id.inspection_id = pi.id
                                WHERE pi.building_id = ? AND pi.is_active = 1
                                ORDER BY id.urgency, id.unit_number
                            ''', (selected_building['id'],))
                            
                            defect_data = cursor.fetchall()
                            conn.close()
                            
                            if defect_data:
                                df = pd.DataFrame(defect_data, columns=[
                                    "Unit", "Room", "Component", "Trade", "Urgency", "Planned Completion", "Status"
                                ])
                                csv = df.to_csv(index=False)
                                
                                st.download_button(
                                    "Download Building Report (CSV)",
                                    data=csv,
                                    file_name=f"building_report_{selected_building['name'].replace(' ', '_')}.csv",
                                    mime="text/csv",
                                    use_container_width=True
                                )
                            else:
                                st.info("No defect data available for this building")
                                
                        except Exception as e:
                            st.error(f"Error generating report: {e}")
                
                # Show defect summary with proper error handling
                st.markdown("#### Recent Defects Summary")
                
                try:
                    conn = sqlite3.connect(persistence_manager.db_path)
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT id.urgency, COUNT(*) as count
                        FROM inspection_defects id
                        JOIN processed_inspections pi ON id.inspection_id = pi.id
                        WHERE pi.building_id = ? AND pi.is_active = 1
                        GROUP BY id.urgency
                        ORDER BY CASE id.urgency 
                            WHEN 'Urgent' THEN 1 
                            WHEN 'High Priority' THEN 2 
                            ELSE 3 END
                    ''', (selected_building['id'],))
                    
                    urgency_summary = cursor.fetchall()
                    conn.close()
                    
                    if urgency_summary:
                        for urgency, count in urgency_summary:
                            if urgency == "Urgent":
                                st.error(f"Urgent: {count} items")
                            elif urgency == "High Priority":
                                st.warning(f"High Priority: {count} items")
                            else:
                                st.info(f"{urgency}: {count} items")
                    else:
                        st.success("No defects found for this building!")
                        
                except Exception as e:
                    st.error(f"Error loading defect summary: {e}")
            
            else:
                st.warning("No inspection data available for this building yet.")
                
        except Exception as e:
            st.error(f"Error loading building data: {e}")
    
    else:
        st.info("Please select a building to manage.")

# Helper function to get building summary manually if method doesn't exist
def get_manual_building_summary(building_id: str, db_path: str) -> dict:
    """Manual building summary when DataPersistenceManager method doesn't exist"""
    import sqlite3
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get building info
        cursor.execute('''
            SELECT b.name, b.address, b.total_units
            FROM buildings b
            WHERE b.id = ?
        ''', (building_id,))
        
        building_info = cursor.fetchone()
        if not building_info:
            conn.close()
            return {}
        
        # Get defect counts
        cursor.execute('''
            SELECT COUNT(*) as total_defects
            FROM inspection_defects id
            JOIN processed_inspections pi ON id.inspection_id = pi.id
            WHERE pi.building_id = ? AND pi.is_active = 1
        ''', (building_id,))
        
        defect_result = cursor.fetchone()
        total_defects = defect_result[0] if defect_result else 0
        
        # Get urgent defects
        cursor.execute('''
            SELECT COUNT(*) as urgent_count
            FROM inspection_defects id
            JOIN processed_inspections pi ON id.inspection_id = pi.id
            WHERE pi.building_id = ? AND pi.is_active = 1 AND id.urgency = 'Urgent'
        ''', (building_id,))
        
        urgent_result = cursor.fetchone()
        urgent_count = urgent_result[0] if urgent_result else 0
        
        conn.close()
        
        return {
            'name': building_info[0],
            'address': building_info[1],
            'total_units': building_info[2],
            'total_defects': total_defects,
            'urgent_count': urgent_count
        }
        
    except Exception as e:
        print(f"Error getting manual building summary: {e}")
        return {}

# Support functions you'll need to implement:

def load_building_defects_paginated(building_id, page=1, urgency_filter="All"):
    """Load building defects with pagination"""
    try:
        persistence_manager = DataPersistenceManager()
        conn = sqlite3.connect(persistence_manager.db_path)
        cursor = conn.cursor()
        
        where_clause = "WHERE pi.building_id = ?"
        params = [building_id]
        
        if urgency_filter != "All":
            where_clause += " AND id.urgency = ?"
            params.append(urgency_filter)
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*)
            FROM inspection_defects id
            JOIN processed_inspections pi ON id.inspection_id = pi.id
            {where_clause} AND pi.is_active = 1
        """
        
        cursor.execute(count_query, params)
        total_rows = cursor.fetchone()[0]
        
        # Get paginated data
        page_size = 50
        offset = (page - 1) * page_size
        
        data_query = f"""
            SELECT id.unit_number, id.room, id.component, id.trade, 
                   id.urgency, id.planned_completion, id.status
            FROM inspection_defects id
            JOIN processed_inspections pi ON id.inspection_id = pi.id
            {where_clause} AND pi.is_active = 1
            ORDER BY 
                CASE id.urgency 
                    WHEN 'Urgent' THEN 1 
                    WHEN 'High Priority' THEN 2 
                    ELSE 3 
                END,
                id.unit_number
            LIMIT ? OFFSET ?
        """
        
        params.extend([page_size, offset])
        cursor.execute(data_query, params)
        
        data = cursor.fetchall()
        columns = ["Unit", "Room", "Component", "Trade", "Urgency", "Planned Completion", "Status"]
        
        conn.close()
        
        return {
            'data': pd.DataFrame(data, columns=columns),
            'total_rows': total_rows,
            'total_pages': (total_rows + page_size - 1) // page_size,
            'current_page': page,
            'page_size': page_size
        }
        
    except Exception as e:
        return {'error': str(e)}

def get_building_team_members(building_id):
    """Get team members with access to this building"""
    try:
        conn = sqlite3.connect("inspection_system.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT u.full_name, u.role, up.permission_level, u.last_login
            FROM users u
            JOIN user_permissions up ON u.username = up.username
            JOIN buildings b ON (
                (up.resource_type = 'building' AND up.resource_id = b.id) OR
                (up.resource_type = 'project' AND up.resource_id = b.project_id)
            )
            WHERE b.id = ? AND u.is_active = 1
            ORDER BY u.role, u.full_name
        """, (building_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'name': r[0],
                'role': r[1],
                'permission_level': r[2],
                'last_activity': r[3]
            }
            for r in results
        ]
        
    except Exception as e:
        print(f"Error getting team members: {e}")
        return []

# =============================================================================
# EXISTING DATA PROCESSING FUNCTIONS
# =============================================================================
def diagnose_database_content():
    """Diagnostic function to check what's actually in the database"""
    try:
        conn = sqlite3.connect("inspection_system.db")
        cursor = conn.cursor()
        
        print("=== DATABASE DIAGNOSTIC ===")
        
        # Check if inspection_items table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='inspection_items'
        """)
        items_table_exists = cursor.fetchone() is not None
        print(f"inspection_items table exists: {items_table_exists}")
        
        # Check inspection_items count
        if items_table_exists:
            cursor.execute("SELECT COUNT(*) FROM inspection_items")
            items_count = cursor.fetchone()[0]
            print(f"inspection_items records: {items_count}")
            
            if items_count > 0:
                cursor.execute("SELECT status_class, COUNT(*) FROM inspection_items GROUP BY status_class")
                items_by_status = cursor.fetchall()
                print("inspection_items by status:")
                for status, count in items_by_status:
                    print(f"  {status}: {count}")
        
        # Check inspection_defects count
        cursor.execute("SELECT COUNT(*) FROM inspection_defects")
        defects_count = cursor.fetchone()[0]
        print(f"inspection_defects records: {defects_count}")
        
        # Check latest inspection
        cursor.execute("""
            SELECT id, building_name, processed_at 
            FROM processed_inspections 
            WHERE is_active = 1 
            ORDER BY processed_at DESC 
            LIMIT 1
        """)
        latest_inspection = cursor.fetchone()
        if latest_inspection:
            inspection_id, building_name, processed_at = latest_inspection
            print(f"Latest inspection: {building_name} ({inspection_id}) at {processed_at}")
            
            # Check what data exists for this inspection
            if items_table_exists:
                cursor.execute("SELECT COUNT(*) FROM inspection_items WHERE inspection_id = ?", (inspection_id,))
                items_for_inspection = cursor.fetchone()[0]
                print(f"inspection_items for latest: {items_for_inspection}")
            
            cursor.execute("SELECT COUNT(*) FROM inspection_defects WHERE inspection_id = ?", (inspection_id,))
            defects_for_inspection = cursor.fetchone()[0]
            print(f"inspection_defects for latest: {defects_for_inspection}")
        else:
            print("No active inspections found")
        
        conn.close()
        print("=== END DIAGNOSTIC ===")
        
    except Exception as e:
        print(f"Diagnostic error: {e}")
  
def check_database_migration():
    """Check if database migration is needed and guide user"""
    
    try:
        from database_migration_script import check_migration_status, migrate_database
        
        if not check_migration_status():
            st.error("Database Migration Required!")
            st.warning("""
            Your database needs to be updated to store complete inspection data.
            This will fix the Excel report consistency issue.
            """)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Run Migration", type="primary"):
                    with st.spinner("Migrating database..."):
                        success = migrate_database()
                        
                    if success:
                        st.success("Migration completed! Please restart the app.")
                        st.info("After restart, upload a new CSV file to get complete data.")
                    else:
                        st.error("Migration failed. Check console for details.")
            
            with col2:
                if st.button("Skip (Not Recommended)"):
                    st.session_state.skip_migration = True
                    st.warning("Excel reports may be inconsistent until migration is completed.")
            
            if not st.session_state.get('skip_migration', False):
                st.stop()
    
    except ImportError:
        st.sidebar.error("Migration script not found. Please create database_migration_script.py")

# Add this near the beginning of your main app, after imports but before the main interface
if __name__ == "__main__":
    # Check migration status early
    check_database_migration()

def process_inspection_data(df, mapping, building_info):
    """Process the inspection data with enhanced metrics calculation including urgent defects"""
    df = df.copy()
    
    # Extract unit number using the same logic as working code
    if "Lot Details_Lot Number" in df.columns and df["Lot Details_Lot Number"].notna().any():
        df["Unit"] = df["Lot Details_Lot Number"].astype(str).str.strip()
    elif "Title Page_Lot number" in df.columns and df["Title Page_Lot number"].notna().any():
        df["Unit"] = df["Title Page_Lot number"].astype(str).str.strip()
    else:
        def extract_unit(audit_name):
            parts = str(audit_name).split("/")
            if len(parts) >= 3:
                candidate = parts[1].strip()
                if len(candidate) <= 6 and any(ch.isdigit() for ch in candidate):
                    return candidate
            return f"Unit_{hash(str(audit_name)) % 1000}"
        df["Unit"] = df["auditName"].apply(extract_unit) if "auditName" in df.columns else [f"Unit_{i}" for i in range(1, len(df) + 1)]

    # Derive unit type using the same logic as working code
    def derive_unit_type(row):
        unit_type = str(row.get("Pre-Settlement Inspection_Unit Type", "")).strip()
        townhouse_type = str(row.get("Pre-Settlement Inspection_Townhouse Type", "")).strip()
        apartment_type = str(row.get("Pre-Settlement Inspection_Apartment Type", "")).strip()
        
        if unit_type.lower() == "townhouse":
            return f"{townhouse_type} Townhouse" if townhouse_type else "Townhouse"
        elif unit_type.lower() == "apartment":
            return f"{apartment_type} Apartment" if apartment_type else "Apartment"
        elif unit_type:
            return unit_type
        else:
            return "Unknown Type"

    df["UnitType"] = df.apply(derive_unit_type, axis=1)

    # Get inspection columns
    inspection_cols = [
        c for c in df.columns if c.startswith("Pre-Settlement Inspection_") and not c.endswith("_notes")
    ]

    if not inspection_cols:
        inspection_cols = [c for c in df.columns if any(keyword in c.lower() for keyword in 
                          ['inspection', 'check', 'item', 'defect', 'issue', 'status'])]

    # Melt to long format
    long_df = df.melt(
        id_vars=["Unit", "UnitType"],
        value_vars=inspection_cols,
        var_name="InspectionItem",
        value_name="Status"
    )

    # Split into Room and Component
    parts = long_df["InspectionItem"].str.split("_", n=2, expand=True)
    if len(parts.columns) >= 3:
        long_df["Room"] = parts[1]
        long_df["Component"] = parts[2].str.replace(r"\.\d+$", "", regex=True)
        long_df["Component"] = long_df["Component"].apply(lambda x: x.split("_")[-1] if isinstance(x, str) else x)
    else:
        long_df["Room"] = "General"
        long_df["Component"] = long_df["InspectionItem"].str.replace("Pre-Settlement Inspection_", "")

    # Remove metadata rows
    metadata_rooms = ["Unit Type", "Building Type", "Townhouse Type", "Apartment Type"]
    metadata_components = ["Room Type"]
    long_df = long_df[~long_df["Room"].isin(metadata_rooms)]
    long_df = long_df[~long_df["Component"].isin(metadata_components)]

    # Classify status with enhanced urgency detection
    def classify_status(val):
        if pd.isna(val):
            return "Blank"
        val_str = str(val).strip().lower()
        if val_str in ["✓", "✔", "ok", "pass", "passed", "good", "satisfactory"]:
            return "OK"
        elif val_str in ["✗", "✘", "x", "fail", "failed", "not ok", "defect", "issue"]:
            return "Not OK"
        elif val_str == "":
            return "Blank"
        else:
            return "Not OK"

    def classify_urgency(val, component, room):
        """Classify defects by urgency level"""
        if pd.isna(val):
            return "Normal"
        
        val_str = str(val).strip().lower()
        component_str = str(component).lower()
        room_str = str(room).lower()
        
        # Urgent keywords
        urgent_keywords = ["urgent", "immediate", "safety", "hazard", "dangerous", "critical", "severe"]
        
        # Safety-critical components
        safety_components = ["fire", "smoke", "electrical", "gas", "water", "security", "lock", "door handle"]
        
        # Check for urgent keywords in the value
        if any(keyword in val_str for keyword in urgent_keywords):
            return "Urgent"
        
        # Check for safety-critical components
        if any(safety in component_str for safety in safety_components):
            return "High Priority"
        
        # Entry door issues are high priority
        if "entry" in room_str and "door" in component_str:
            return "High Priority"
            
        return "Normal"

    long_df["StatusClass"] = long_df["Status"].apply(classify_status)
    long_df["Urgency"] = long_df.apply(lambda row: classify_urgency(row["Status"], row["Component"], row["Room"]), axis=1)

    # Merge with trade mapping
    merged = long_df.merge(mapping, on=["Room", "Component"], how="left")
    
    # Fill missing trades with "Unknown Trade"
    merged["Trade"] = merged["Trade"].fillna("Unknown Trade")
    
    # Add planned completion dates
    def assign_planned_completion(urgency):
        base_date = datetime.now()
        if urgency == "Urgent":
            return base_date + timedelta(days=3)
        elif urgency == "High Priority":
            return base_date + timedelta(days=7)
        else:
            return base_date + timedelta(days=14)
    
    merged["PlannedCompletion"] = merged["Urgency"].apply(assign_planned_completion)
    
    final_df = merged[["Unit", "UnitType", "Room", "Component", "StatusClass", "Trade", "Urgency", "PlannedCompletion"]]
    
    # Calculate settlement readiness using defects per unit
    defects_per_unit = final_df[final_df["StatusClass"] == "Not OK"].groupby("Unit").size()
    
    ready_units = (defects_per_unit <= 2).sum() if len(defects_per_unit) > 0 else 0
    minor_work_units = ((defects_per_unit > 2) & (defects_per_unit <= 7)).sum() if len(defects_per_unit) > 0 else 0
    major_work_units = ((defects_per_unit > 7) & (defects_per_unit <= 15)).sum() if len(defects_per_unit) > 0 else 0
    extensive_work_units = (defects_per_unit > 15).sum() if len(defects_per_unit) > 0 else 0
    
    # Add units with zero defects to ready category
    units_with_defects = set(defects_per_unit.index)
    all_units = set(final_df["Unit"].dropna())
    units_with_no_defects = len(all_units - units_with_defects)
    ready_units += units_with_no_defects
    
    total_units = final_df["Unit"].nunique()
    
    # Extract building information
    sample_audit = df.loc[0, "auditName"] if "auditName" in df.columns and len(df) > 0 else ""
    if sample_audit:
        audit_parts = str(sample_audit).split("/")
        extracted_building_name = audit_parts[2].strip() if len(audit_parts) >= 3 else building_info["name"]
        extracted_inspection_date = audit_parts[0].strip() if len(audit_parts) >= 1 else building_info.get("date", datetime.now().strftime("%Y-%m-%d"))
    else:
        extracted_building_name = building_info["name"]
        extracted_inspection_date = building_info.get("date", datetime.now().strftime("%Y-%m-%d"))
    
    # Address information extraction
    location = ""
    area = ""
    region = ""
    
    if "Title Page_Site conducted_Location" in df.columns:
        location_series = df["Title Page_Site conducted_Location"].dropna()
        location = location_series.astype(str).str.strip().iloc[0] if len(location_series) > 0 else ""
    if "Title Page_Site conducted_Area" in df.columns:
        area_series = df["Title Page_Site conducted_Area"].dropna()
        area = area_series.astype(str).str.strip().iloc[0] if len(area_series) > 0 else ""
    if "Title Page_Site conducted_Region" in df.columns:
        region_series = df["Title Page_Site conducted_Region"].dropna()
        region = region_series.astype(str).str.strip().iloc[0] if len(region_series) > 0 else ""
    
    address_parts = [part for part in [location, area, region] if part]
    extracted_address = ", ".join(address_parts) if address_parts else building_info["address"]
    
    # Create comprehensive metrics
    defects_only = final_df[final_df["StatusClass"] == "Not OK"]
    
    # Enhanced metrics with urgency tracking
    urgent_defects = defects_only[defects_only["Urgency"] == "Urgent"]
    high_priority_defects = defects_only[defects_only["Urgency"] == "High Priority"]
    
    # Planned work calculations
    next_two_weeks = datetime.now() + timedelta(days=14)
    planned_work_2weeks = defects_only[defects_only["PlannedCompletion"] <= next_two_weeks]
    
    next_month = datetime.now() + timedelta(days=30)
    planned_work_month = defects_only[
        (defects_only["PlannedCompletion"] > next_two_weeks) & 
        (defects_only["PlannedCompletion"] <= next_month)
    ]
    
    metrics = {
        "building_name": extracted_building_name,
        "address": extracted_address,
        "inspection_date": extracted_inspection_date,
        "unit_types_str": ", ".join(sorted(final_df["UnitType"].astype(str).unique())),
        "total_units": total_units,
        "total_inspections": len(final_df),
        "total_defects": len(defects_only),
        "defect_rate": (len(defects_only) / len(final_df) * 100) if len(final_df) > 0 else 0.0,
        "avg_defects_per_unit": (len(defects_only) / max(total_units, 1)),
        "ready_units": ready_units,
        "minor_work_units": minor_work_units,
        "major_work_units": major_work_units,
        "extensive_work_units": extensive_work_units,
        "ready_pct": (ready_units / total_units * 100) if total_units > 0 else 0,
        "minor_pct": (minor_work_units / total_units * 100) if total_units > 0 else 0,
        "major_pct": (major_work_units / total_units * 100) if total_units > 0 else 0,
        "extensive_pct": (extensive_work_units / total_units * 100) if total_units > 0 else 0,
        "urgent_defects": len(urgent_defects),
        "high_priority_defects": len(high_priority_defects),
        "planned_work_2weeks": len(planned_work_2weeks),
        "planned_work_month": len(planned_work_month),
        "summary_trade": defects_only.groupby("Trade").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False) if len(defects_only) > 0 else pd.DataFrame(columns=["Trade", "DefectCount"]),
        "summary_unit": defects_only.groupby("Unit").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False) if len(defects_only) > 0 else pd.DataFrame(columns=["Unit", "DefectCount"]),
        "summary_room": defects_only.groupby("Room").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False) if len(defects_only) > 0 else pd.DataFrame(columns=["Room", "DefectCount"]),
        "urgent_defects_table": urgent_defects[["Unit", "Room", "Component", "Trade", "PlannedCompletion"]].copy() if len(urgent_defects) > 0 else pd.DataFrame(columns=["Unit", "Room", "Component", "Trade", "PlannedCompletion"]),
        "planned_work_2weeks_table": planned_work_2weeks[["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]].copy() if len(planned_work_2weeks) > 0 else pd.DataFrame(columns=["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]),
        "planned_work_month_table": planned_work_month[["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]].copy() if len(planned_work_month) > 0 else pd.DataFrame(columns=["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]),
        "component_details_summary": defects_only.groupby(["Trade", "Room", "Component"])["Unit"].apply(lambda s: ", ".join(sorted(s.astype(str).unique()))).reset_index().rename(columns={"Unit": "Units with Defects"}) if len(defects_only) > 0 else pd.DataFrame(columns=["Trade", "Room", "Component", "Units with Defects"])
    }
    
    return final_df, metrics

def lookup_unit_defects(processed_data, unit_number):
    """Lookup defect history for a specific unit"""
    if processed_data is None or unit_number is None:
        return pd.DataFrame()
    
    unit_data = processed_data[
        (processed_data["Unit"].astype(str).str.strip().str.lower() == str(unit_number).strip().lower()) &
        (processed_data["StatusClass"] == "Not OK")
    ].copy()
    
    if len(unit_data) > 0:
        # Sort by urgency and planned completion
        urgency_order = {"Urgent": 1, "High Priority": 2, "Normal": 3}
        unit_data["UrgencySort"] = unit_data["Urgency"].map(urgency_order).fillna(3)
        unit_data = unit_data.sort_values(["UrgencySort", "PlannedCompletion"])
        
        # Format planned completion dates
        unit_data["PlannedCompletion"] = pd.to_datetime(unit_data["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
        
        return unit_data[["Room", "Component", "Trade", "Urgency", "PlannedCompletion"]]
    
    return pd.DataFrame(columns=["Room", "Component", "Trade", "Urgency", "PlannedCompletion"])

def create_zip_package(excel_bytes, word_bytes, metrics):
    """Create a ZIP package containing both reports"""
    zip_buffer = BytesIO()
    
    mel_tz = pytz.timezone("Australia/Melbourne")
    timestamp = datetime.now(mel_tz).strftime("%Y%m%d_%H%M%S")
    
    # Generate professional filenames
    from excel_report_generator import generate_filename
    excel_filename = f"{generate_filename(metrics['building_name'], 'Excel')}.xlsx"
    word_filename = f"{generate_filename(metrics['building_name'], 'Word')}.docx" if word_bytes else None
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add Excel file
        zip_file.writestr(excel_filename, excel_bytes)
        
        # Add Word file if available
        if word_bytes and word_filename:
            zip_file.writestr(word_filename, word_bytes)
        
        # Add a summary text file
        summary_content = f"""Inspection Report Summary
=====================================
Building: {metrics['building_name']}
Address: {metrics['address']}
Inspection Date: {metrics['inspection_date']}
Report Generated: {datetime.now(mel_tz).strftime('%Y-%m-%d %H:%M:%S AEDT')}

Key Metrics:
- Total Units: {metrics['total_units']:,}
- Total Defects: {metrics['total_defects']:,}
- Defect Rate: {metrics['defect_rate']:.2f}%
- Ready for Settlement: {metrics['ready_units']} ({metrics['ready_pct']:.1f}%)
- Minor Work Required: {metrics['minor_work_units']} ({metrics['minor_pct']:.1f}%)
- Major Work Required: {metrics['major_work_units']} ({metrics['major_pct']:.1f}%)
- Extensive Work Required: {metrics['extensive_work_units']} ({metrics['extensive_pct']:.1f}%)
- Urgent Defects: {metrics['urgent_defects']}
- Planned Work (Next 2 Weeks): {metrics['planned_work_2weeks']}
- Planned Work (Next Month): {metrics['planned_work_month']}

Files Included:
- {excel_filename}
{'- ' + word_filename if word_bytes else '- Word report (not available)'}
- inspection_summary.txt (this file)
"""
        zip_file.writestr("inspection_summary.txt", summary_content)
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

# =============================================================================
# STREAMLIT APP CONFIGURATION AND INITIALIZATION
# =============================================================================

# Page configuration
st.set_page_config(
    page_title="Inspection Report Processor",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hide Streamlit styling
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
div[data-testid="stToolbar"] {
    visibility: hidden;
    height: 0%;
    position: fixed;
}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .step-container {
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        background-color: #fafafa;
    }
    
    .step-header {
        color: #1976d2;
        font-weight: bold;
        font-size: 1.2em;
        margin-bottom: 1rem;
    }
    
    .unit-lookup-container {
        background: linear-gradient(135deg, #e8f5e8 0%, #d4edda 100%);
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    .download-section {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 10px;
        padding: 2rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize enhanced authentication
auth_manager = get_auth_manager()

# Check authentication with database
if not auth_manager.is_session_valid():
    show_enhanced_login_page()
    st.stop()

# Initialize session state FIRST (move this section up)
if "trade_mapping" not in st.session_state:
    st.session_state.trade_mapping = pd.DataFrame(columns=["Room", "Component", "Trade"])
if "processed_data" not in st.session_state:
    st.session_state.processed_data = None
if "metrics" not in st.session_state:
    st.session_state.metrics = None
if "step_completed" not in st.session_state:
    st.session_state.step_completed = {"mapping": False, "processing": False}
if "building_info" not in st.session_state:
    st.session_state.building_info = {
        "name": "Professional Building Complex",
        "address": "123 Professional Street\nMelbourne, VIC 3000"
    }
if "report_images" not in st.session_state:
    st.session_state.report_images = {
        "logo": None,
        "cover": None,
    }

# Show enhanced user menu (now session state is initialized)
if not show_enhanced_user_menu():
    st.stop()

# Initialize user data (load from database if available)
data_loaded = initialize_user_data()
mapping_loaded = load_trade_mapping()

if data_loaded:
    st.info(f"Loaded inspection data for {st.session_state.metrics['building_name']}")

if mapping_loaded:
    st.info("Trade mapping loaded from database")

# Get current user info
user = auth_manager.get_current_user()

# Replace the admin workspace selection section in your streamlit_app.py with this:

if user['dashboard_type'] == 'admin':
    st.markdown(f"""
    <div class="main-header">
        <h1>Administrator Control Center</h1>
        <p>Complete System Management & Data Processing</p>
        <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
            <span>Welcome back, <strong>{user['name']}</strong>!</span>
            <span style="margin-left: 2rem;">Role: <strong>System Administrator</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # IMPROVED: Radio buttons instead of selectbox + button
    if 'admin_workspace' not in st.session_state:
        st.session_state.admin_workspace = "Data Processing"
    
    st.markdown("### Choose Your Workspace")
    
    workspace_choice = st.radio(
        "Select your admin interface:",
        ["Data Processing", "System Administration"],
        index=0 if st.session_state.admin_workspace == "Data Processing" else 1,
        horizontal=True,
        help="Data Processing: Upload and process inspection files | System Administration: User and system management"
    )
    
    # Auto-update session state when radio selection changes
    if workspace_choice != st.session_state.admin_workspace:
        st.session_state.admin_workspace = workspace_choice
        st.rerun()
    
    st.markdown("---")
    
    # Handle workspace selection
    if st.session_state.admin_workspace == "System Administration":
        try:
            show_admin_dashboard()
        except Exception as e:
            st.error(f"Admin dashboard error: {str(e)}")
            st.info("Falling back to basic admin interface")
            show_basic_admin_interface()
        
        # Stop here to prevent showing processing interface
        st.stop()
    
    else:  # Data Processing mode
        st.info("Full inspection processing interface with administrator privileges")
        # Continue to processing interface below (don't use st.stop())

elif user['dashboard_type'] == 'portfolio':
    # Property Developer Dashboard with report generation
    st.markdown(f"""
    <div class="main-header">
        <h1>Portfolio Management Dashboard</h1>
        <p>Property Developer Interface</p>
        <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
            <span>Welcome back, <strong>{user['name']}</strong>!</span>
            <span style="margin-left: 2rem;">Role: <strong>Property Developer</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    show_enhanced_developer_dashboard()
    st.stop()

elif user['dashboard_type'] == 'builder':
    # Builder Dashboard with work reports
    st.markdown(f"""
    <div class="main-header">
        <h1>Builder Workspace</h1>
        <p>Work Management Interface</p>
        <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
            <span>Welcome back, <strong>{user['name']}</strong>!</span>
            <span style="margin-left: 2rem;">Role: <strong>Builder</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    show_enhanced_builder_dashboard()
    st.stop()

elif user['dashboard_type'] == 'project':
    # Project Manager Dashboard
    st.markdown(f"""
    <div class="main-header">
        <h1>Project Management Dashboard</h1>
        <p>Project Manager Interface</p>
        <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
            <span>Welcome back, <strong>{user['name']}</strong>!</span>
            <span style="margin-left: 2rem;">Role: <strong>Project Manager</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    show_enhanced_project_manager_dashboard()
    st.stop()

# Add this fallback function somewhere before the main routing (add it after your imports)
def show_basic_admin_interface():
    """Basic admin interface when enhanced version fails"""
    st.markdown("### Basic System Administration")
    
    # Show system stats
    try:
        from data_persistence import DataPersistenceManager
        persistence_manager = DataPersistenceManager()
        integrity_report = persistence_manager.validate_data_integrity()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("System Health", "OK" if integrity_report['healthy'] else "Issues")
        with col2:
            st.metric("Active Users", integrity_report['stats'].get('active_users', 0))
        with col3:
            st.metric("Buildings", integrity_report['stats'].get('total_buildings', 0))
        
        if not integrity_report['healthy']:
            st.error("System Issues Detected:")
            for issue in integrity_report['issues']:
                st.warning(f"• {issue}")
        
        # Basic user management
        st.markdown("### User Management")
        st.info("Basic user management available. Install enhanced_admin_management.py for full features.")
        
    except Exception as e:
        st.error(f"Unable to load admin interface: {str(e)}")
        st.info("Please check that all required modules are available.")

# For Inspectors and Admins - show full processing interface
# (Admins fall through to here and get BOTH admin tools AND full processing)
st.markdown(f"""
<div class="main-header">
    <h1>Inspection Report Processor</h1>
    <p>Professional Data Processing Interface</p>
    <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
        <span>Welcome back, <strong>{user['name']}</strong>!</span>
        <span style="margin-left: 2rem;">Role: <strong>{user['role'].replace('_', ' ').title()}</strong></span>
    </div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# MAIN APPLICATION INTERFACE (INSPECTORS AND ADMINS)
# =============================================================================

# Sidebar configuration with permission-based content
with st.sidebar:
    st.header("Process Status")
    
    # Show status based on permissions
    if st.session_state.step_completed.get("mapping", False):
        st.success("Step 1: Mapping loaded")
        st.caption(f"{len(st.session_state.trade_mapping)} mapping entries")
    else:
        if auth_manager.can_user_perform_action("can_upload"):
            st.info("Step 1: Load mapping")
        else:
            st.info("Mapping managed by your team")
    
    if st.session_state.step_completed.get("processing", False):
        st.success("Step 2: Data processed")
        if st.session_state.metrics:
            st.caption(f"{st.session_state.metrics['total_units']} units processed")
    else:
        if auth_manager.can_user_perform_action("can_process"):
            st.info("Step 2: Process data")
        else:
            st.info("Data processed by your team")
    
    # Unit Lookup Section
    if st.session_state.processed_data is not None:
        st.markdown("---")
        st.header("Quick Unit Lookup")
        
        # Get all unique units for dropdown
        all_units = sorted(st.session_state.processed_data["Unit"].unique())
        
        # Unit search
        selected_unit = st.selectbox(
            "Select Unit Number:",
            options=[""] + all_units,
            help="Quick lookup of defects for any unit",
            key="main_sidebar_unit_lookup"
        )
        
        if selected_unit:
            unit_defects = lookup_unit_defects(st.session_state.processed_data, selected_unit)
            
            if len(unit_defects) > 0:
                st.markdown(f"**Unit {selected_unit} Defects:**")
                
                # Count by urgency
                urgent_count = len(unit_defects[unit_defects["Urgency"] == "Urgent"])
                high_priority_count = len(unit_defects[unit_defects["Urgency"] == "High Priority"])
                normal_count = len(unit_defects[unit_defects["Urgency"] == "Normal"])
                
                if urgent_count > 0:
                    st.error(f"Urgent: {urgent_count}")
                if high_priority_count > 0:
                    st.warning(f"High Priority: {high_priority_count}")
                if normal_count > 0:
                    st.info(f"Normal: {normal_count}")
                
                # Show defects in compact format
                for _, defect in unit_defects.iterrows():
                    urgency_icon = "🚨" if defect["Urgency"] == "Urgent" else "⚠️" if defect["Urgency"] == "High Priority" else "🔧"
                    st.caption(f"{urgency_icon} {defect['Room']} - {defect['Component']} ({defect['Trade']}) - Due: {defect['PlannedCompletion']}")
            else:
                st.success(f"Unit {selected_unit} has no defects!")
    
    st.markdown("---")


# STEP 1: Load Master Trade Mapping (with permission check)
if auth_manager.can_user_perform_action('can_upload'):
    st.markdown("""
    <div class="step-container">
        <div class="step-header">Step 1: Load Master Trade Mapping</div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Upload your trade mapping file or use the default template:**")
        
        # Check if mapping is empty and show warning
        if len(st.session_state.trade_mapping) == 0:
            st.warning("Trade mapping is currently blank. Please load a mapping file or use the default template before uploading your inspection CSV.")
    
    with col2:
        # Download default template
        default_mapping = """Room,Component,Trade
Apartment Entry Door,Door Handle,Doors
Apartment Entry Door,Door Locks and Keys,Doors
Apartment Entry Door,Paint,Painting
Balcony,Balustrade,Carpentry & Joinery
Balcony,Drainage Point,Plumbing
Bathroom,Bathtub (if applicable),Plumbing
Bathroom,Ceiling,Painting
Bathroom,Exhaust Fan,Electrical
Bathroom,Tiles,Flooring - Tiles
Kitchen Area,Cabinets,Carpentry & Joinery
Kitchen Area,Kitchen Sink,Plumbing
Kitchen Area,Stovetop and Oven,Appliances
Bedroom,Carpets,Flooring - Carpets
Bedroom,Windows,Windows
Bedroom,Light Fixtures,Electrical"""
        
        st.download_button(
            "Download Template",
            data=default_mapping,
            file_name="trade_mapping_template.csv",
            mime="text/csv",
            help="Download a comprehensive mapping template"
        )
    
    # Upload mapping file
    mapping_file = st.file_uploader("Choose trade mapping CSV", type=["csv"], key="mapping_upload")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Load Default Mapping", type="secondary"):
            st.session_state.trade_mapping = pd.read_csv(StringIO(default_mapping))
            st.session_state.step_completed["mapping"] = True
            save_trade_mapping_to_database(st.session_state.trade_mapping, user['username'])
            st.success("Default mapping loaded!")
            st.rerun()
    
    with col2:
        if mapping_file is not None:
            if st.button("Load Uploaded Mapping", type="primary"):
                try:
                    st.session_state.trade_mapping = pd.read_csv(mapping_file)
                    st.session_state.step_completed["mapping"] = True
                    save_trade_mapping_to_database(st.session_state.trade_mapping, user['username'])
                    st.success(f"Mapping loaded: {len(st.session_state.trade_mapping)} entries")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error loading mapping: {e}")
    
    with col3:
        if st.button("Clear Mapping"):
            st.session_state.trade_mapping = pd.DataFrame(columns=["Room", "Component", "Trade"])
            st.session_state.step_completed["mapping"] = False
            st.rerun()
    
    # Display current mapping
    if len(st.session_state.trade_mapping) > 0:
        st.markdown("**Current Trade Mapping:**")
        st.dataframe(st.session_state.trade_mapping, use_container_width=True, height=200)
    else:
        st.info("No trade mapping loaded. Please load the default template or upload your own mapping file.")

else:
    st.markdown("""
    <div class="step-container">
        <div class="step-header">Trade Mapping Information</div>
    </div>
    """, unsafe_allow_html=True)
    
    if len(st.session_state.trade_mapping) > 0:
        st.info(f"Trade mapping available: {len(st.session_state.trade_mapping)} entries")
        st.dataframe(st.session_state.trade_mapping, use_container_width=True, height=200)
    else:
        st.warning("No trade mapping loaded. Contact your team administrator.")

# STEP 2: Upload and Process Data (with permission check)
if auth_manager.can_user_perform_action('can_upload') and auth_manager.can_user_perform_action('can_process'):
    st.markdown("""
    <div class="step-container">
        <div class="step-header">Step 2: Upload Inspection Data</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Upload inspection data
    uploaded_csv = st.file_uploader("Choose inspection CSV file", type=["csv"], key="inspection_upload")
    
    # Check if mapping is loaded before allowing CSV upload
    if len(st.session_state.trade_mapping) == 0:
        st.warning("Please load your trade mapping first before uploading the inspection CSV file.")
        st.stop()
    
    if uploaded_csv is not None:
        if st.button("Process Inspection Data", type="primary", use_container_width=True):
            try:
                with st.spinner("Processing inspection data..."):
                    # Load and process data
                    df = pd.read_csv(uploaded_csv)
                    
                    # Use default building info for processing
                    building_info = {
                        "name": st.session_state.building_info["name"],
                        "address": st.session_state.building_info["address"],
                        "date": datetime.now().strftime("%Y-%m-%d")
                    }
                    
                    # Process and save to database
                    processed_df, metrics, saved = process_inspection_data_with_persistence(
                        df, st.session_state.trade_mapping, building_info, user['username']
                    )
                    
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Error processing data: {e}")
                st.code(traceback.format_exc())

else:
    # Show appropriate message based on permissions
    st.markdown("""
    <div class="step-container">
        <div class="step-header">Inspection Data Status</div>
    </div>
    """, unsafe_allow_html=True)
    
    if not auth_manager.can_user_perform_action('can_upload'):
        st.info("Data upload is managed by your team. Contact an inspector or project manager to upload new inspection data.")
    elif not auth_manager.can_user_perform_action('can_process'):
        st.info("Data processing is managed by your team. Contact a project manager or administrator.")
    
    if st.session_state.processed_data is not None:
        st.success("Inspection data has been processed and is available for viewing.")
    else:
        st.warning("No inspection data available. Contact your team to process inspection data.")

# Continue with results display...
# STEP 3: Show Results and Download Options
if st.session_state.processed_data is not None and st.session_state.metrics is not None:
    st.markdown("""
    <div class="step-container">
        <div class="step-header">Step 3: Analysis Results & Downloads</div>
    </div>
    """, unsafe_allow_html=True)
    
    metrics = st.session_state.metrics
    
    # Building Information Section
    st.markdown("### Building Information (Auto-Detected)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        **Building Name:** {metrics['building_name']}  
        **Inspection Date:** {metrics['inspection_date']}  
        **Total Units:** {metrics['total_units']:,} units
        """)
    
    with col2:
        st.markdown(f"""
        **Address:** {metrics['address']}  
        **Unit Types:** {metrics['unit_types_str']}
        """)
    
    st.markdown("---")
    
    # Key Metrics Dashboard
    st.subheader("Key Metrics Dashboard")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Units", f"{metrics['total_units']:,}", help="Total number of units inspected")
    
    with col2:
        st.metric("Total Defects", f"{metrics['total_defects']:,}", delta=f"{metrics['defect_rate']:.1f}% rate")
    
    with col3:
        st.metric("Ready Units", f"{metrics['ready_units']}", delta=f"{metrics['ready_pct']:.1f}%")
    
    with col4:
        st.metric("Avg Defects/Unit", f"{metrics['avg_defects_per_unit']:.1f}", help="Average number of defects per unit")
    
    with col5:
        completion_efficiency = (metrics['ready_units'] / metrics['total_units'] * 100) if metrics['total_units'] > 0 else 0
        st.metric("Completion Efficiency", f"{completion_efficiency:.1f}%", help="Percentage of units ready for immediate handover")
    
    # Enhanced Unit Lookup in Main Area
    st.markdown("---")
    st.markdown("""
    <div class="unit-lookup-container">
        <h3 style="text-align: center; margin-bottom: 1rem;">Unit Defect Lookup</h3>
        <p style="text-align: center;">Quickly search for any unit's complete defect history</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Get all unique units for search
        all_units = sorted(st.session_state.processed_data["Unit"].unique())
        
        # Enhanced unit search with autocomplete
        search_unit = st.selectbox(
            "Enter or Select Unit Number:",
            options=[""] + all_units,
            help="Type to search or select from dropdown",
            key="main_unit_search"
        )
        
        if search_unit:
            unit_defects = lookup_unit_defects(st.session_state.processed_data, search_unit)
            
            if len(unit_defects) > 0:
                st.markdown(f"### Unit {search_unit} - Complete Defect Report")
                
                # Summary metrics for this unit
                col1, col2, col3, col4 = st.columns(4)
                
                urgent_count = len(unit_defects[unit_defects["Urgency"] == "Urgent"])
                high_priority_count = len(unit_defects[unit_defects["Urgency"] == "High Priority"])
                normal_count = len(unit_defects[unit_defects["Urgency"] == "Normal"])
                total_defects = len(unit_defects)
                
                with col1:
                    st.metric("Urgent", urgent_count)
                with col2:
                    st.metric("High Priority", high_priority_count)
                with col3:
                    st.metric("Normal", normal_count)
                with col4:
                    st.metric("Total Defects", total_defects)
                
                # Detailed defect table
                st.markdown("**Detailed Defect List:**")
                
                # Format the data for display
                display_data = unit_defects.copy()
                display_data["Urgency"] = display_data["Urgency"].apply(
                    lambda x: f"🚨 {x}" if x == "Urgent" 
                    else f"⚠️ {x}" if x == "High Priority" 
                    else f"🔧 {x}"
                )
                
                st.dataframe(display_data, use_container_width=True)
                
                # Unit status summary
                if urgent_count > 0:
                    st.error(f"**HIGH ATTENTION REQUIRED** - {urgent_count} urgent defect(s) need immediate attention!")
                elif high_priority_count > 0:
                    st.warning(f"**PRIORITY WORK** - {high_priority_count} high priority defect(s) to address")
                elif normal_count > 0:
                    st.info(f"**STANDARD WORK** - {normal_count} normal defect(s) to complete")
                
            else:
                st.success(f"**Unit {search_unit} is DEFECT-FREE!**")
                st.balloons()
    
    # Summary Tables Section
    st.markdown("---")
    st.subheader("Summary Tables")
    
    # Create tabs for different summary views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Trade Summary", 
        "Unit Summary", 
        "Room Summary", 
        "Urgent Defects", 
        "Planned Work"
    ])
    
    with tab1:
        st.markdown("**Trade-wise defect breakdown - Shows which trades have the most issues**")
        if len(metrics['summary_trade']) > 0:
            st.dataframe(metrics['summary_trade'], use_container_width=True)
        else:
            st.info("No trade defects found")
    
    with tab2:
        st.markdown("**Unit-wise defect breakdown - Shows which units need the most attention**")
        if len(metrics['summary_unit']) > 0:
            st.dataframe(metrics['summary_unit'], use_container_width=True)
        else:
            st.info("No unit defects found")
    
    with tab3:
        st.markdown("**Room-wise defect breakdown - Shows which room types have the most issues**")
        if len(metrics['summary_room']) > 0:
            st.dataframe(metrics['summary_room'], use_container_width=True)
        else:
            st.info("No room defects found")
    
    with tab4:
        st.markdown("**URGENT DEFECTS - These require immediate attention!**")
        if len(metrics['urgent_defects_table']) > 0:
            urgent_display = metrics['urgent_defects_table'].copy()
            urgent_display["PlannedCompletion"] = pd.to_datetime(urgent_display["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
            st.dataframe(urgent_display, use_container_width=True)
            st.error(f"**{len(urgent_display)} URGENT defects require immediate attention!**")
        else:
            st.success("No urgent defects found!")
    
    with tab5:
        st.markdown("**Planned Defect Work Schedule**")
        
        # Sub-tabs for different time periods
        subtab1, subtab2 = st.tabs(["Next 2 Weeks", "Next Month"])
        
        with subtab1:
            st.markdown(f"**Work planned for completion in the next 2 weeks ({metrics['planned_work_2weeks']} items)**")
            st.info("Shows defects due within the next 14 days")
            if len(metrics['planned_work_2weeks_table']) > 0:
                planned_2weeks = metrics['planned_work_2weeks_table'].copy()
                planned_2weeks["PlannedCompletion"] = pd.to_datetime(planned_2weeks["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
                st.dataframe(planned_2weeks, use_container_width=True)
            else:
                st.success("No work planned for the next 2 weeks")
        
        with subtab2:
            st.markdown(f"**Work planned for completion between 2 weeks and 1 month ({metrics['planned_work_month']} items)**")
            st.info("Shows defects due between days 15-30 from today")
            if len(metrics['planned_work_month_table']) > 0:
                planned_month = metrics['planned_work_month_table'].copy()
                planned_month["PlannedCompletion"] = pd.to_datetime(planned_month["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
                st.dataframe(planned_month, use_container_width=True)
            else:
                st.success("No work planned for this period")
    
    # STEP 4: Download Options (only for users with upload permissions)
        
    if auth_manager.can_user_perform_action("can_upload"):
        st.markdown("""
        <div class="step-container">
            <div class="step-header">Step 4: Download Reports</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Complete report package
        st.markdown("""
        <div class="download-section">
            <h3 style="text-align: center; margin-bottom: 1rem;">Complete Report Package</h3>
            <p style="text-align: center;">Download both Excel and Word reports together in a convenient package.</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Generate Complete Package", type="primary", use_container_width=True):
                try:
                    with st.spinner("Generating complete report package..."):
                        # Generate Excel using professional generator
                        if EXCEL_REPORT_AVAILABLE:
                            excel_buffer = generate_professional_excel_report(st.session_state.processed_data, metrics)
                            excel_bytes = excel_buffer.getvalue()
                        else:
                            st.error("Excel generator not available")
                            st.stop()
                                    
                        # Generate Word if available
                        word_bytes = None
                        if WORD_REPORT_AVAILABLE:
                            try:
                                # Try enhanced version first, fallback to basic version
                                try:
                                    doc = generate_professional_word_report(
                                        st.session_state.processed_data, 
                                        metrics, 
                                        st.session_state.report_images
                                    )
                                except TypeError:
                                    # Fallback to old version without images
                                    doc = generate_professional_word_report(
                                        st.session_state.processed_data, 
                                        metrics
                                    )
                                buf = BytesIO()
                                doc.save(buf)
                                buf.seek(0)
                                word_bytes = buf.getvalue()
                            except Exception as e:
                                st.warning(f"Word report could not be generated: {e}")
                        
                        # Create ZIP package with professional filenames
                        zip_bytes = create_zip_package(excel_bytes, word_bytes, metrics)
                        
                        # Generate professional package filename
                        zip_filename = f"{generate_filename(metrics['building_name'], 'Package')}.zip"
                        
                        st.success("Complete report package generated!")
                        st.download_button(
                            "Download Complete Package (ZIP)",
                            data=zip_bytes,
                            file_name=zip_filename,
                            mime="application/zip",
                            use_container_width=True,
                            help="Contains Excel report, Word report (if available), and summary text file"
                        )
                        
                        # Show package contents
                        st.info(f"Package includes: Excel report, {'Word report, ' if word_bytes else ''}and summary file")
                        
                except Exception as e:
                    st.error(f"Error generating package: {e}")
                    st.code(traceback.format_exc())
        
        # Individual download options
        st.markdown("---")
        st.subheader("Individual Downloads")
        
        col1, col2 = st.columns(2)
        
        # Excel Download
        with col1:
            st.markdown("### Excel Report")
            st.write("Comprehensive Excel workbook with multiple sheets, charts, and detailed analysis.")
            
            if st.button("Generate Excel Report", type="secondary", use_container_width=True):
                try:
                    with st.spinner("Generating professional Excel report..."):
                        if EXCEL_REPORT_AVAILABLE:
                            excel_bytes = generate_professional_excel_report(st.session_state.processed_data, metrics)
                            
                            # Generate professional filename
                            filename = f"{generate_filename(metrics['building_name'], 'Excel')}.xlsx"
                            
                            st.success("Professional Excel report generated!")
                            st.download_button(
                                "Download Excel Report",
                                data=excel_bytes,
                                file_name=filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                        else:
                            st.error("Excel generator not available")
                            if EXCEL_IMPORT_ERROR:
                                st.code(f"Import error: {EXCEL_IMPORT_ERROR}")
                except Exception as e:
                    st.error(f"Error generating Excel: {e}")
                    st.code(traceback.format_exc())
        
        # Word Download
        with col2:
            st.markdown("### Word Report")
            
            if not WORD_REPORT_AVAILABLE:
                st.warning("Word generator not available")
                if WORD_IMPORT_ERROR:
                    with st.expander("Error Details"):
                        st.code(f"Import error: {WORD_IMPORT_ERROR}")
            else:
                st.write("Enhanced professional Word document with executive summary, visual analysis, actionable recommendations, and your custom images.")
                
                # Show image status for Word report
                current_images = [k for k, v in st.session_state.report_images.items() if v is not None]
                if current_images:
                    st.info(f"Will include: {', '.join(current_images)}")
                else:
                    st.info("Tip: Upload images in the sidebar to enhance your Word report!")
                
                if st.button("Generate Word Report", type="secondary", use_container_width=True):
                    try:
                        with st.spinner("Generating Word report with your images..."):
                            # Try enhanced version first, fallback to basic version
                            try:
                                doc = generate_professional_word_report(
                                    st.session_state.processed_data, 
                                    metrics, 
                                    st.session_state.report_images
                                )
                                success_message = "Enhanced Word report generated with your images!"
                            except TypeError:
                                # Fallback to old version without images
                                doc = generate_professional_word_report(
                                    st.session_state.processed_data, 
                                    metrics
                                )
                                success_message = "Word report generated (basic version - update word_report_generator.py for image support)"
                            
                            # Save to bytes
                            buf = BytesIO()
                            doc.save(buf)
                            buf.seek(0)
                            word_bytes = buf.getvalue()
                            
                            # Generate professional filename
                            filename = f"{generate_filename(metrics['building_name'], 'Word')}.docx"
                            
                            st.success(success_message)
                            st.download_button(
                                "Download Enhanced Word Report",
                                data=word_bytes,
                                file_name=filename,
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                use_container_width=True
                            )
                    except Exception as e:
                        st.error(f"Error generating Word: {e}")
                        st.code(traceback.format_exc())

    else:
        # Show read-only info for non-upload users
        st.markdown("""
        <div class="step-container">
            <div class="step-header">Report Information</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("Reports can be generated by users with upload permissions. Contact your team administrator to download the latest reports.")
        
    # STEP 4: Download Options (enhanced permission logic)
    if auth_manager.can_user_perform_action("can_generate_reports"):
        st.markdown("""
        <div class="step-container">
            <div class="step-header">Step 4: Generate Reports</div>
        </div>
        """, unsafe_allow_html=True)
        
        user_role = user['role']
        can_customize = auth_manager.can_user_perform_action("can_customize_reports")
        
        if user_role == 'builder':
            # Builder-specific reports
            st.markdown("### Work Reports")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("My Work List", type="primary"):
                    # Generate builder work list
                    pass
            with col2:
                if st.button("Completed Tasks"):
                    # Generate completed work report
                    pass
            with col3:
                if st.button("Weekly Schedule"):
                    # Generate weekly schedule
                    pass
        
        elif user_role == 'property_developer':
            # Executive reports for developers
            st.markdown("### Executive Reports")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Portfolio Summary", type="primary"):
                    # Generate executive summary
                    pass
            with col2:
                if st.button("Settlement Readiness Report"):
                    # Generate readiness report
                    pass
        
        else:
            # Full report suite for admins, managers, inspectors
            st.markdown("### Complete Report Package")
            # Your existing report generation code here
            
    else:
        st.info("Report generation not available for your role. Contact your project manager.")    

else:
    # Show upload section with enhanced UI (only for users with upload permissions)
    if auth_manager.can_user_perform_action("can_upload"):
        st.markdown("""
        <div class="step-container">
            <div class="step-header">Ready to Process Your Data</div>
        </div>
        """, unsafe_allow_html=True)
        
        if uploaded_csv is not None:
            try:
                preview_df = pd.read_csv(uploaded_csv)
                
                # Enhanced success message with file info
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.success(f"Rows: {len(preview_df):,}")
                with col2:
                    st.success(f"Columns: {len(preview_df.columns)}")
                with col3:
                    file_size = uploaded_csv.size / 1024  # Convert to KB
                    st.success(f"Size: {file_size:.1f} KB")
                
                # Enhanced preview with column analysis
                with st.expander("Data Preview & Analysis", expanded=True):
                    # Show column information
                    st.markdown("**Column Information:**")
                    col_info = pd.DataFrame({
                        'Column': preview_df.columns,
                        'Type': [str(dtype) for dtype in preview_df.dtypes],
                        'Non-Null': [preview_df[col].notna().sum() for col in preview_df.columns],
                        'Null %': [f"{(preview_df[col].isna().sum() / len(preview_df) * 100):.1f}%" for col in preview_df.columns]
                    })
                    st.dataframe(col_info, use_container_width=True, height=200)
                    
                    st.markdown("**Data Sample:**")
                    st.dataframe(preview_df.head(10), use_container_width=True)
                    st.caption(f"Showing first 10 rows of {len(preview_df):,} total rows")
                    
                    # Data quality indicators
                    missing_data_pct = (preview_df.isna().sum().sum() / (len(preview_df) * len(preview_df.columns))) * 100
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if missing_data_pct < 5:
                            st.success(f"Data Quality: Excellent ({missing_data_pct:.1f}% missing)")
                        elif missing_data_pct < 15:
                            st.warning(f"Data Quality: Good ({missing_data_pct:.1f}% missing)")
                        else:
                            st.error(f"Data Quality: Poor ({missing_data_pct:.1f}% missing)")
                    
                    with col2:
                        duplicate_rows = preview_df.duplicated().sum()
                        if duplicate_rows == 0:
                            st.success("No Duplicates")
                        else:
                            st.warning(f"{duplicate_rows} Duplicates")
                    
                    with col3:
                        required_cols = ['Unit', 'Room', 'Component', 'StatusClass']
                        missing_cols = [col for col in required_cols if col not in preview_df.columns]
                        if not missing_cols:
                            st.success("All Required Columns")
                        else:
                            st.info(f"Will auto-generate: {', '.join(missing_cols)}")
                
            except Exception as e:
                st.error(f"Error reading CSV: {e}")
        else:
            st.markdown("""
            <div style="background-color: #e3f2fd; border: 1px solid #2196f3; border-radius: 5px; padding: 1rem; margin: 1rem 0;">
                <h4>Ready to Upload Your Inspection Data</h4>
                <p>Please upload your iAuditor CSV file to begin processing. The system will:</p>
                <ul>
                    <li>Validate the data quality</li>
                    <li>Apply trade mapping</li>
                    <li>Generate comprehensive analytics</li>
                    <li>Create professional reports</li>
                    <li>Identify urgent defects</li>
                    <li>Track planned work schedules</li>
                    <li>Enable quick unit lookups</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
    else:
        # Show info for non-upload users
        st.markdown("""
        <div class="step-container">
            <div class="step-header">Data Processing Information</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("Data processing is handled by your team. Once inspection data is processed, you'll be able to view all analytics and reports here.")

# Enhanced Footer with database authentication info
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 2rem; border-radius: 10px; margin-top: 2rem;">
    <h4 style="color: #2E3A47; margin-bottom: 1rem;">Professional Inspection Report Processor v4.0</h4>
    <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap;">
        <div><strong>Excel Reports:</strong> Multi-sheet analysis</div>
        <div><strong>Word Reports:</strong> Executive summaries</div>
        <div><strong>Urgent Tracking:</strong> Priority defects</div>
        <div><strong>Unit Lookup:</strong> Instant defect search</div>
        <div><strong>Work Planning:</strong> Scheduled completion dates</div>
        <div><strong>Database Security:</strong> Role-based access</div>
    </div>
    <p style="margin-top: 1rem; color: #666; font-size: 0.9em;">
        Built with Streamlit • Powered by SQLite Database • Role-Based Authentication • Logged in as: {user['name']} ({user['role'].replace('_', ' ').title()})
    </p>
</div>
""", unsafe_allow_html=True)