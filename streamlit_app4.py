# =============================================================================
# RUN THE SECURE APPLICATION
# =============================================================================

# Execute the main application
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

# Enhanced Security Imports
from permission_manager import (
    get_permission_manager, 
    validate_session_middleware,
    check_permission_ui,
    requires_permission
)
from secure_ui_helpers import (
    create_secure_ui,
    secure_section_header,
    show_permissions_debug,
    audit_trail_viewer,
    show_user_activity_summary
)

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

try:
    from portfolio_analytics import generate_portfolio_analytics_report
    PORTFOLIO_ANALYTICS_AVAILABLE = True
    PORTFOLIO_ANALYTICS_ERROR = None
except ImportError as e:
    PORTFOLIO_ANALYTICS_AVAILABLE = False
    PORTFOLIO_ANALYTICS_ERROR = str(e)

# =============================================================================
# STREAMLIT APP CONFIGURATION - MUST BE FIRST
# =============================================================================

st.set_page_config(
    page_title="Secure Inspection Report Processor",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state IMMEDIATELY after page config
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

# Hide Streamlit styling
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Enhanced CSS for professional styling with security indicators
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
    
    .security-header {
        color: #d32f2f;
        font-weight: bold;
        font-size: 1.1em;
        margin-bottom: 1rem;
    }
    
    .permission-denied {
        background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
        border: 2px solid #f44336;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .security-success {
        background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%);
        border: 2px solid #4caf50;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
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

# =============================================================================
# ENHANCED AUTHENTICATION SYSTEM
# =============================================================================

class EnhancedDatabaseAuthManager:
    """Enhanced authentication manager with integrated permission system"""
    
    def __init__(self, db_path="inspection_system.db"):
        self.db_path = db_path
        self.session_timeout = 8 * 60 * 60  # 8 hours
        self._init_database_if_needed()
    
    def _init_database_if_needed(self):
        """Initialize database if it doesn't exist"""
        if not os.path.exists(self.db_path):
            st.error(f"Database not found! Please run: python enhanced_database_setup.py")
            st.stop()
    
    def _hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = "inspection_app_salt_2024"
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def authenticate(self, username: str, password: str) -> Tuple[bool, str]:
        """Enhanced authenticate with audit logging"""
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
                
                # Log successful login
                perm_manager = get_permission_manager()
                perm_manager.log_user_action(username, "LOGIN_SUCCESS", success=True)
                
                conn.close()
                return True, "Login successful"
            else:
                # Log failed login attempt
                perm_manager = get_permission_manager()
                perm_manager.log_security_event(
                    username, "LOGIN_FAILED", success=False, 
                    details="Invalid credentials"
                )
                conn.close()
                return False, "Invalid username or password"
                
        except Exception as e:
            perm_manager = get_permission_manager()
            perm_manager.log_security_event(
                username, "LOGIN_ERROR", success=False, details=str(e)
            )
            return False, f"Database error: {str(e)}"
    
    def get_user_info(self, username: str) -> Optional[Dict]:
        """Get complete user information with permissions"""
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
                perm_manager = get_permission_manager()
                permissions = perm_manager.get_user_permissions(username)
                
                return {
                    "username": user_data[0],
                    "full_name": user_data[1],
                    "email": user_data[2],
                    "role": user_data[3],
                    "is_active": user_data[4],
                    "last_login": user_data[5],
                    "permissions": permissions
                }
            return None
        except Exception as e:
            return None
    
    def create_session(self, username: str):
        """Create enhanced Streamlit session"""
        user_info = self.get_user_info(username)
        
        if user_info:
            st.session_state.authenticated = True
            st.session_state.username = user_info["username"]
            st.session_state.user_name = user_info["full_name"]
            st.session_state.user_email = user_info["email"]
            st.session_state.user_role = user_info["role"]
            st.session_state.login_time = time.time()
            st.session_state.user_permissions = user_info["permissions"]
            
            # Determine dashboard type from permissions
            permissions = user_info["permissions"]
            if permissions.get("dashboard.admin"):
                dashboard_type = "admin"
            elif permissions.get("dashboard.portfolio"):
                dashboard_type = "portfolio"
            elif permissions.get("dashboard.project"):
                dashboard_type = "project"
            elif permissions.get("dashboard.builder"):
                dashboard_type = "builder"
            else:
                dashboard_type = "inspector"
            
            st.session_state.dashboard_type = dashboard_type
    
    def is_session_valid(self) -> bool:
        """Enhanced session validation"""
        if not st.session_state.get("authenticated", False):
            return False
        
        username = st.session_state.get("username")
        if not username:
            return False
        
        if not st.session_state.get("login_time"):
            return False
        
        if time.time() - st.session_state.login_time > self.session_timeout:
            perm_manager = get_permission_manager()
            perm_manager.log_security_event(username, "SESSION_TIMEOUT")
            self.logout()
            return False
        
        return True
    
    def logout(self):
        """Enhanced logout with audit logging"""
        username = st.session_state.get("username")
        if username:
            perm_manager = get_permission_manager()
            perm_manager.log_user_action(username, "LOGOUT")
        
        auth_keys = [
            "authenticated", "username", "user_name", "user_email", 
            "user_role", "login_time", "user_permissions", "dashboard_type"
        ]
        for key in auth_keys:
            if key in st.session_state:
                del st.session_state[key]
    
    def get_current_user(self) -> Dict:
        """Get current user with enhanced info"""
        return {
            "username": st.session_state.get("username", ""),
            "name": st.session_state.get("user_name", "User"),
            "email": st.session_state.get("user_email", ""),
            "role": st.session_state.get("user_role", "user"),
            "permissions": st.session_state.get("user_permissions", {}),
            "dashboard_type": st.session_state.get("dashboard_type", "inspector")
        }
    
    def has_permission(self, permission: str) -> bool:
        """Check if current user has permission"""
        username = st.session_state.get("username")
        if not username:
            return False
        perm_manager = get_permission_manager()
        return perm_manager.has_permission(username, permission)
    
    def can_user_perform_action(self, action: str) -> bool:
        """Backward compatibility wrapper"""
        action_mapping = {
            "can_upload": "data.upload",
            "can_process": "data.process", 
            "can_manage_users": "users.edit",
            "can_approve_defects": "defects.approve",
            "can_view_all": "data.view_all",
            "can_generate_reports": "reports.generate",
            "can_view_data": "data.view_assigned",
            "can_update_defect_status": "defects.update_status"
        }
        
        permission = action_mapping.get(action, action)
        return self.has_permission(permission)
    
    def change_password(self, username, old_password, new_password):
        """Enhanced password change with audit logging"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            old_hash = self._hash_password(old_password)
            cursor.execute('''
                SELECT 1 FROM users WHERE username = ? AND password_hash = ?
            ''', (username, old_hash))
            
            if not cursor.fetchone():
                perm_manager = get_permission_manager()
                perm_manager.log_security_event(
                    username, "PASSWORD_CHANGE_FAILED", success=False,
                    details="Current password incorrect"
                )
                conn.close()
                return False, "Current password is incorrect"
            
            if len(new_password) < 8:  # Enhanced requirement
                conn.close()
                return False, "New password must be at least 8 characters"
            
            new_hash = self._hash_password(new_password)
            cursor.execute('''
                UPDATE users SET password_hash = ? WHERE username = ?
            ''', (new_hash, username))
            
            conn.commit()
            conn.close()
            
            perm_manager = get_permission_manager()
            perm_manager.log_security_event(username, "PASSWORD_CHANGED", success=True)
            
            return True, "Password changed successfully"
            
        except Exception as e:
            perm_manager = get_permission_manager()
            perm_manager.log_security_event(
                username, "PASSWORD_CHANGE_ERROR", success=False, details=str(e)
            )
            return False, f"Database error: {str(e)}"

@st.cache_resource
def get_auth_manager():
    """Get singleton enhanced auth manager instance"""
    return EnhancedDatabaseAuthManager()

# =============================================================================
# SECURE UI FUNCTIONS
# =============================================================================

def show_secure_login_page():
    """Enhanced secure login page"""
    
    st.markdown("""
    <div style="max-width: 400px; margin: 2rem auto; padding: 2rem; 
                background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h2 style="text-align: center; color: #1976d2; margin-bottom: 2rem;">
            🏢 Secure Building Inspection System
        </h2>
        <h3 style="text-align: center; color: #666; margin-bottom: 2rem;">
            Authentication Required
        </h3>
        <p style="text-align: center; color: #999; font-size: 0.9em;">
            🔒 Enhanced Security • 📋 Audit Logging • 🛡️ Role-Based Access
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    auth_manager = get_auth_manager()
    perm_manager = get_permission_manager()
    
    # Enhanced rate limiting
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = 0
    if 'last_attempt_time' not in st.session_state:
        st.session_state.last_attempt_time = 0
    
    # Check rate limiting
    time_since_last = time.time() - st.session_state.last_attempt_time
    if st.session_state.login_attempts >= 5 and time_since_last < 300:  # 5 minutes
        remaining_time = 300 - time_since_last
        st.error(f"Too many failed attempts. Try again in {int(remaining_time/60)}:{int(remaining_time%60):02d}")
        return
    elif time_since_last >= 300:
        st.session_state.login_attempts = 0  # Reset after timeout
    
    with st.form("secure_login_form"):
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("### Secure Login")
            
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            # Enhanced captcha after failed attempts
            if st.session_state.login_attempts >= 3:
                import random
                if 'captcha_answer' not in st.session_state:
                    st.session_state.captcha_num1 = random.randint(1, 10)
                    st.session_state.captcha_num2 = random.randint(1, 10)
                    st.session_state.captcha_answer = st.session_state.captcha_num1 + st.session_state.captcha_num2
                
                captcha_input = st.number_input(
                    f"Security Check: {st.session_state.captcha_num1} + {st.session_state.captcha_num2} = ?",
                    min_value=0, max_value=20, value=0, step=1
                )
                st.caption("Complete the math problem above to continue")
            
            login_button = st.form_submit_button("🔒 Secure Login", use_container_width=True, type="primary")
            
            if login_button:
                st.session_state.last_attempt_time = time.time()
                
                # Validate captcha if required
                if st.session_state.login_attempts >= 3:
                    if captcha_input != st.session_state.captcha_answer:
                        st.error("Incorrect security answer")
                        if 'captcha_answer' in st.session_state:
                            del st.session_state.captcha_answer
                        return
                
                if username and password:
                    success, message = auth_manager.authenticate(username, password)
                    
                    if success:
                        auth_manager.create_session(username)
                        st.session_state.login_attempts = 0
                        
                        if 'captcha_answer' in st.session_state:
                            del st.session_state.captcha_answer
                        
                        perm_manager.log_user_action(username, "LOGIN_SUCCESS_UI")
                        
                        st.success("🔒 Secure login successful!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.session_state.login_attempts += 1
                        
                        # Log failed attempt with details
                        perm_manager.log_security_event(
                            username, "LOGIN_FAILED_UI", success=False,
                            details=f"Attempt {st.session_state.login_attempts}/5"
                        )
                        
                        st.error(f"❌ {message}")
                        if 'captcha_answer' in st.session_state:
                            del st.session_state.captcha_answer
                else:
                    st.warning("Please enter both username and password")
    
    # Enhanced demo credentials section
    with st.expander("Demo Credentials & Security Info", expanded=False):
        st.warning("**Security Notice:** These are demo accounts for testing only!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("""
            **High-Level Access:**
            
            **System Administrator:**
            - Username: `admin` | Password: `admin123`
            - Full system access, user management
            
            **Property Developer:**
            - Username: `developer1` | Password: `dev123`
            - Portfolio view, financial analytics
            """)
        
        with col2:
            st.info("""
            **Operational Access:**
            
            **Project Manager:**
            - Username: `manager1` | Password: `mgr123`
            - Project oversight, assigned buildings
            
            **Site Inspector:**
            - Username: `inspector` | Password: `inspector123`
            - Data processing, report generation
            
            **Builder:**
            - Username: `builder1` | Password: `build123`
            - Work lists, status updates
            """)
        
        st.error("""
        **Security Features Active:**
        - ✅ Role-based permissions
        - ✅ Building access control  
        - ✅ Comprehensive audit logging
        - ✅ Session timeout protection
        - ✅ Rate limiting (5 attempts max)
        - ✅ Enhanced password requirements
        """)

def show_clean_user_sidebar():
    """Clean, minimal sidebar with only essential information"""
    
    auth_manager = get_auth_manager()
    
    if not auth_manager.is_session_valid():
        return False
    
    user = auth_manager.get_current_user()
    perm_manager = get_permission_manager()
    
    with st.sidebar:
        # Clean CSS for sidebar
        st.markdown("""
        <style>
            .sidebar-profile {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 1.5rem;
                border-radius: 12px;
                margin-bottom: 1.5rem;
                text-align: center;
                position: relative;
                overflow: hidden;
            }
            
            .sidebar-profile::before {
                content: '';
                position: absolute;
                top: -50%;
                right: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
                animation: pulse 4s ease-in-out infinite;
            }
            
            .profile-avatar {
                width: 60px;
                height: 60px;
                background: rgba(255, 255, 255, 0.2);
                border-radius: 50%;
                margin: 0 auto 0.75rem;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.5rem;
                font-weight: bold;
                position: relative;
                z-index: 1;
            }
            
            .session-status {
                background: rgba(16, 185, 129, 0.1);
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 8px;
                padding: 0.75rem;
                margin-bottom: 1rem;
                text-align: center;
            }
            
            .quick-action-btn {
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 0.75rem;
                margin-bottom: 0.5rem;
                width: 100%;
                text-align: left;
                transition: all 0.2s ease;
                cursor: pointer;
            }
            
            .quick-action-btn:hover {
                border-color: #3b82f6;
                background: #f0f9ff;
                transform: translateY(-1px);
            }
        </style>
        """, unsafe_allow_html=True)
        
        # Clean user profile section
        initials = ''.join([word[0].upper() for word in user['name'].split()[:2]])
        role_display = user['role'].replace('_', ' ').title()
        
        st.markdown(f"""
        <div class="sidebar-profile">
            <div class="profile-avatar">
                {initials}
            </div>
            <h3 style="margin: 0; font-size: 1.1rem; position: relative; z-index: 1;">{user['name']}</h3>
            <p style="margin: 0.25rem 0 0 0; font-size: 0.85rem; opacity: 0.8; position: relative; z-index: 1;">{role_display}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Session status (minimal)
        login_time = st.session_state.get('login_time', 0)
        if login_time:
            session_minutes = int((time.time() - login_time) / 60)
            if session_minutes < 60:
                session_display = f"{session_minutes}m"
            else:
                session_display = f"{session_minutes // 60}h {session_minutes % 60}m"
            
            st.markdown(f"""
            <div class="session-status">
                <div style="color: #10b981; font-weight: 500; display: flex; align-items: center; justify-content: center;">
                    <span style="margin-right: 0.5rem;">✓</span>
                    Active Session: {session_display}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Quick actions (context-sensitive and organized)
        st.markdown("### Quick Actions")
        
        # Data actions
        if perm_manager.has_permission(user['username'], "data.upload") or perm_manager.has_permission(user['username'], "data.process"):
            st.markdown("**Data Management**")
            
            if perm_manager.has_permission(user['username'], "data.upload"):
                if st.button("📁 Upload Data", use_container_width=True, key="sidebar_upload"):
                    st.session_state.sidebar_action = "upload"
                    st.rerun()
            
            if perm_manager.has_permission(user['username'], "data.process"):
                if st.button("⚙️ Process Data", use_container_width=True, key="sidebar_process"):
                    st.session_state.sidebar_action = "process"
                    st.rerun()
        
        # Report actions
        if perm_manager.has_permission(user['username'], "reports.generate"):
            st.markdown("**Reports**")
            
            if st.button("📊 Generate Report", use_container_width=True, key="sidebar_report"):
                st.session_state.sidebar_action = "report"
                st.rerun()
        
        # Admin actions
        if perm_manager.has_permission(user['username'], "system.admin"):
            st.markdown("**Administration**")
            
            if st.button("👥 Manage Users", use_container_width=True, key="sidebar_users"):
                st.session_state.admin_selected_tab = "Users"
                st.rerun()
            
            if st.button("🔒 Security Log", use_container_width=True, key="sidebar_security"):
                st.session_state.show_audit_log = True
                st.rerun()
        
        # Unit lookup (only if data exists and clean presentation)
        if (perm_manager.has_permission(user['username'], "data.view_assigned") and 
            st.session_state.processed_data is not None):
            
            st.markdown("---")
            st.markdown("### Unit Lookup")
            
            all_units = sorted(st.session_state.processed_data["Unit"].astype(str).unique())
            
            # Limit to reasonable number for sidebar
            display_units = all_units[:15] if len(all_units) > 15 else all_units
            
            selected_unit = st.selectbox(
                "Select Unit:",
                options=[""] + display_units,
                key="sidebar_unit_lookup",
                label_visibility="collapsed"
            )
            
            if selected_unit:
                try:
                    building_name = st.session_state.metrics.get('building_name') if st.session_state.metrics else None
                    
                    # Check building access
                    if building_name and not perm_manager.can_access_building(user['username'], building_name):
                        st.error("No access to this building")
                    else:
                        unit_defects = lookup_unit_defects(st.session_state.processed_data, selected_unit)
                        
                        if len(unit_defects) > 0:
                            urgent = len(unit_defects[unit_defects["Urgency"] == "Urgent"])
                            high = len(unit_defects[unit_defects["Urgency"] == "High Priority"])
                            normal = len(unit_defects[unit_defects["Urgency"] == "Normal"])
                            
                            # Clean status display
                            status_color = "#fef2f2" if urgent > 0 else "#fefce8" if high > 0 else "#f0fdf4"
                            border_color = "#fca5a5" if urgent > 0 else "#fcd34d" if high > 0 else "#a7f3d0"
                            
                            st.markdown(f"""
                            <div style="background: {status_color}; border: 1px solid {border_color}; 
                                        border-radius: 8px; padding: 0.75rem; margin-top: 0.5rem;">
                                <div style="font-weight: 600; margin-bottom: 0.5rem; color: #374151;">
                                    Unit {selected_unit}
                                </div>
                                {f'<div style="color: #dc2626; font-size: 0.85rem;">🚨 {urgent} Urgent</div>' if urgent > 0 else ''}
                                {f'<div style="color: #d97706; font-size: 0.85rem;">⚠️ {high} High Priority</div>' if high > 0 else ''}
                                {f'<div style="color: #059669; font-size: 0.85rem;">🔧 {normal} Normal</div>' if normal > 0 else ''}
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div style="background: #f0fdf4; border: 1px solid #a7f3d0; 
                                        border-radius: 8px; padding: 0.75rem; margin-top: 0.5rem; text-align: center;">
                                <div style="color: #059669; font-weight: 500;">
                                    ✅ Unit {selected_unit}
                                </div>
                                <div style="color: #065f46; font-size: 0.85rem;">
                                    No defects found!
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                
                except Exception as e:
                    st.error(f"Error: {str(e)[:50]}...")
        
        # Settings and logout section (always at bottom)
        st.markdown("---")
        
        # Account settings
        if st.button("⚙️ Account Settings", use_container_width=True, key="sidebar_settings"):
            st.session_state.show_user_settings = True
            st.rerun()
        
        # Show settings modal if requested
        if st.session_state.get("show_user_settings", False):
            show_user_settings_modal(user, auth_manager, perm_manager)
        
        # Logout button (prominent)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Sign Out", use_container_width=True, type="primary", key="sidebar_logout"):
            perm_manager.log_user_action(user['username'], "LOGOUT_SIDEBAR")
            auth_manager.logout()
            st.success("Signed out successfully!")
            st.rerun()
    
    return True

def show_user_settings_modal(user, auth_manager, perm_manager):
    """Show user settings in a clean modal-style interface"""
    
    st.markdown("---")
    st.markdown("### Account Settings")
    
    # Password change section
    with st.expander("🔒 Change Password", expanded=False):
        with st.form("password_change_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            # Password strength indicator
            if new_password:
                strength = calculate_password_strength(new_password)
                strength_color = "#ef4444" if strength < 3 else "#f59e0b" if strength < 4 else "#10b981"
                strength_text = "Weak" if strength < 3 else "Medium" if strength < 4 else "Strong"
                
                st.markdown(f"""
                <div style="background: rgba(16, 185, 129, 0.1); border-radius: 6px; padding: 0.5rem; margin: 0.5rem 0;">
                    <small style="color: {strength_color};">Password Strength: <strong>{strength_text}</strong></small>
                </div>
                """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.form_submit_button("Update Password", use_container_width=True):
                    if not all([current_password, new_password, confirm_password]):
                        st.error("All fields are required")
                    elif new_password != confirm_password:
                        st.error("New passwords don't match")
                    elif len(new_password) < 8:
                        st.error("Password must be at least 8 characters")
                    else:
                        success, message = auth_manager.change_password(
                            user['username'], current_password, new_password
                        )
                        if success:
                            st.success(message)
                            st.session_state.show_user_settings = False
                            st.rerun()
                        else:
                            st.error(message)
            
            with col2:
                if st.form_submit_button("Cancel", use_container_width=True):
                    st.session_state.show_user_settings = False
                    st.rerun()
    
    # User info section (read-only)
    st.markdown("**Account Information**")
    st.text_input("Username", value=user['username'], disabled=True)
    st.text_input("Full Name", value=user['name'], disabled=True)
    st.text_input("Email", value=user['email'], disabled=True)
    st.text_input("Role", value=user['role'].replace('_', ' ').title(), disabled=True)
    
    # Close settings
    if st.button("Close Settings", use_container_width=True):
        st.session_state.show_user_settings = False
        st.rerun()

def calculate_password_strength(password):
    """Calculate password strength score"""
    score = 0
    if len(password) >= 8: score += 1
    if any(c.isupper() for c in password): score += 1
    if any(c.islower() for c in password): score += 1
    if any(c.isdigit() for c in password): score += 1
    if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password): score += 1
    return score

def show_secure_user_menu():
    """Enhanced user menu with security features"""
    
    auth_manager = get_auth_manager()
    
    if not auth_manager.is_session_valid():
        return False
    
    user = auth_manager.get_current_user()
    perm_manager = get_permission_manager()
    
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 👤 User Information")
        
        # User info with security indicators
        st.markdown(f"""
        **Name:** {user['name']}  
        **Role:** {user['role'].replace('_', ' ').title()}  
        **Email:** {user['email']}  
        """)
        
        # Session info
        login_time = st.session_state.get('login_time', 0)
        if login_time:
            session_age = int((time.time() - login_time) / 60)
            if session_age < 60:
                st.caption(f"🕒 Session: {session_age} minutes")
            else:
                st.caption(f"🕒 Session: {session_age // 60}h {session_age % 60}m")
        
        # Security status
        st.markdown("---")
        st.markdown("### 🔒 Security Status")
        
        accessible_buildings = perm_manager.get_accessible_buildings(user['username'])
        
        st.success("✅ Authenticated")
        st.success("✅ Session Valid")
        st.info(f"🏢 Buildings: {len(accessible_buildings)}")
        
        # Show accessible buildings
        if accessible_buildings:
            with st.expander("Your Buildings", expanded=False):
                for building in accessible_buildings:
                    building_name = building[0]
                    units = building[1] if len(building) > 1 else "Unknown"
                    st.write(f"📍 {building_name} ({units} units)")
        
        # Account actions
        st.markdown("---")
        st.markdown("### ⚙️ Account")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔑 Change Password", use_container_width=True):
                st.session_state.show_password_change = True
        
        with col2:
            if st.button("🚪 Logout", use_container_width=True, type="primary"):
                perm_manager.log_user_action(user['username'], "LOGOUT_REQUESTED")
                auth_manager.logout()
                st.success("Logged out successfully!")
                st.rerun()
        
        # Enhanced password change form
        if st.session_state.get("show_password_change", False):
            st.markdown("---")
            st.markdown("### 🔑 Change Password")
            
            with st.form("secure_password_change"):
                old_password = st.text_input("Current Password", type="password")
                new_password = st.text_input("New Password", type="password", 
                                           help="Must be at least 8 characters")
                confirm_password = st.text_input("Confirm New Password", type="password")
                
                # Password strength indicator
                if new_password:
                    strength = 0
                    if len(new_password) >= 8: strength += 1
                    if any(c.isupper() for c in new_password): strength += 1
                    if any(c.islower() for c in new_password): strength += 1
                    if any(c.isdigit() for c in new_password): strength += 1
                    if any(c in "!@#$%^&*" for c in new_password): strength += 1
                    
                    if strength < 2:
                        st.error("❌ Weak password")
                    elif strength < 4:
                        st.warning("⚠️ Medium password")
                    else:
                        st.success("✅ Strong password")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Update", use_container_width=True):
                        if new_password != confirm_password:
                            st.error("New passwords don't match")
                        elif len(new_password) < 8:
                            st.error("Password must be at least 8 characters")
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
        
        # Role-specific quick actions with permission checks
        st.markdown("---")
        st.markdown("### ⚡ Quick Actions")
        
        if perm_manager.has_permission(user['username'], "data.upload"):
            if st.button("📁 Process New Data", use_container_width=True):
                perm_manager.log_user_action(user['username'], "QUICK_ACTION: Process Data")
                st.rerun()
        
        if perm_manager.has_permission(user['username'], "reports.generate"):
            if st.button("📊 Generate Reports", use_container_width=True):
                perm_manager.log_user_action(user['username'], "QUICK_ACTION: Generate Reports")
                st.rerun()
        
        if perm_manager.has_permission(user['username'], "system.admin"):
            if st.button("⚙️ System Admin", use_container_width=True):
                perm_manager.log_user_action(user['username'], "QUICK_ACTION: System Admin")
                st.rerun()
        
        # Secure Unit Lookup
        if (perm_manager.has_permission(user['username'], "data.view_assigned") and 
            st.session_state.processed_data is not None):
            
            st.markdown("---")
            st.markdown("### 🔍 Quick Unit Lookup")
            
            all_units = sorted(st.session_state.processed_data["Unit"].astype(str).unique())
            
            selected_unit = st.selectbox(
                "Select Unit Number:",
                options=[""] + all_units,
                help="Quick lookup of defects for any unit",
                key="sidebar_secure_unit_lookup"
            )
            
            if selected_unit:
                try:
                    building_name = st.session_state.metrics.get('building_name') if st.session_state.metrics else None
                    
                    # Check building access
                    if building_name and not perm_manager.can_access_building(user['username'], building_name):
                        st.error("❌ No access to this building")
                    else:
                        unit_defects = lookup_unit_defects(st.session_state.processed_data, selected_unit)
                        
                        if len(unit_defects) > 0:
                            st.markdown(f"**Unit {selected_unit}:**")
                            
                            urgent_count = len(unit_defects[unit_defects["Urgency"] == "Urgent"])
                            high_priority_count = len(unit_defects[unit_defects["Urgency"] == "High Priority"])
                            normal_count = len(unit_defects[unit_defects["Urgency"] == "Normal"])
                            
                            if urgent_count > 0:
                                st.error(f"🚨 Urgent: {urgent_count}")
                            if high_priority_count > 0:
                                st.warning(f"⚠️ High Priority: {high_priority_count}")
                            if normal_count > 0:
                                st.info(f"🔧 Normal: {normal_count}")
                            
                            # Show first few defects
                            for _, defect in unit_defects.head(3).iterrows():
                                urgency_icon = "🚨" if defect["Urgency"] == "Urgent" else "⚠️" if defect["Urgency"] == "High Priority" else "🔧"
                                st.caption(f"{urgency_icon} {defect['Room']} - {defect['Component']}")
                            
                            if len(unit_defects) > 3:
                                st.caption(f"... and {len(unit_defects) - 3} more")
                        else:
                            st.success(f"✅ Unit {selected_unit} - No defects!")
                
                except Exception as e:
                    st.error(f"Error loading unit data: {e}")
        
        # Admin debug section
        if perm_manager.has_permission(user['username'], "system.admin"):
            st.markdown("---")
            st.markdown("### 🔧 Admin Tools")
            
            if st.button("📋 View Audit Log", use_container_width=True):
                st.session_state.show_audit_log = True
                st.rerun()
            
            if st.button("👥 User Permissions", use_container_width=True):
                st.session_state.show_permissions_debug = True
                st.rerun()
        
        # Activity summary
        show_user_activity_summary()
        
        # Secure reset with enhanced confirmation
        st.markdown("---")
        if st.button("Reset All Data", help="Clear all data and start over"):
            if st.session_state.get('confirm_reset', False):
                perm_manager.log_user_action(user['username'], "DATA_RESET_CONFIRMED")
                
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
                
                st.session_state.confirm_reset = False
                st.rerun()
            else:
                st.session_state.confirm_reset = True
                st.warning("Click again to confirm reset")
    
    return True

# =============================================================================
# SECURE DATA PROCESSING FUNCTIONS
# =============================================================================

@requires_permission("data.process")
def secure_process_inspection_data_with_persistence(df, mapping, building_info, username):
    """Secure version of process_inspection_data_with_persistence"""
    perm_manager = get_permission_manager()
    
    try:
        perm_manager.log_user_action(username, "DATA_PROCESSING_START", 
                                   resource=building_info.get('name', 'Unknown'))
        
        processed_df, metrics = process_inspection_data(df, mapping, building_info)
        
        # Check building access for existing buildings
        building_name = metrics.get('building_name')
        if building_name:
            user_role = st.session_state.get("user_role")
            if user_role not in ['admin'] and not perm_manager.can_access_building(username, building_name):
                perm_manager.log_security_event(
                    username, f"NEW_BUILDING_CREATED: {building_name}", 
                    success=True, details="User created new building data"
                )
        
        persistence_manager = DataPersistenceManager()
        success, inspection_id = persistence_manager.save_processed_inspection(
            processed_df, metrics, username
        )
        
        if success:
            perm_manager.log_user_action(
                username, "DATA_PROCESSING_SUCCESS", 
                resource=building_name, success=True,
                details=f"Processed {len(processed_df)} records"
            )
            
            st.success(f"Data processed and saved! Building: {metrics['building_name']}")
            st.session_state.processed_data = processed_df
            st.session_state.metrics = metrics
            st.session_state.step_completed["processing"] = True
            return processed_df, metrics, True
        else:
            perm_manager.log_user_action(
                username, "DATA_PROCESSING_SAVE_FAILED", 
                resource=building_name, success=False,
                details=f"Save failed: {inspection_id}"
            )
            st.error(f"Data processing succeeded but database save failed: {inspection_id}")
            return processed_df, metrics, False
    
    except Exception as e:
        perm_manager.log_user_action(
            username, "DATA_PROCESSING_ERROR", 
            resource=building_info.get('name', 'Unknown'),
            success=False, details=str(e)
        )
        raise e

def secure_initialize_user_data():
    """Secure version of initialize_user_data with access control"""
    username = st.session_state.get("username")
    if not username:
        return False
    
    perm_manager = get_permission_manager()
    
    if not perm_manager.has_permission(username, "data.view_assigned"):
        return False
    
    if st.session_state.processed_data is None:
        try:
            persistence_manager = DataPersistenceManager()
            
            user_role = st.session_state.get("user_role")
            if user_role == 'admin':
                processed_data, metrics = persistence_manager.load_latest_inspection()
            else:
                accessible_buildings = perm_manager.get_accessible_buildings(username)
                if accessible_buildings:
                    building_name = accessible_buildings[0][0]
                    processed_data, metrics = persistence_manager.load_inspection_by_building(building_name)
                else:
                    processed_data, metrics = None, None
            
            if processed_data is not None and metrics is not None:
                building_name = metrics.get('building_name')
                if building_name and not perm_manager.can_access_building(username, building_name):
                    perm_manager.log_security_event(
                        username, f"DATA_ACCESS_DENIED: {building_name}",
                        success=False
                    )
                    return False
                
                perm_manager.log_user_action(username, "DATA_LOADED", resource=building_name)
                
                st.session_state.processed_data = processed_data
                st.session_state.metrics = metrics
                st.session_state.step_completed["processing"] = True
                return True
        
        except Exception as e:
            perm_manager.log_user_action(
                username, "DATA_LOAD_ERROR", 
                success=False, details=str(e)
            )
            return False
    
    return False

def secure_load_trade_mapping():
    """Secure version of load_trade_mapping"""
    username = st.session_state.get("username")
    if not username:
        return False
    
    perm_manager = get_permission_manager()
    
    if not perm_manager.has_permission(username, "data.upload"):
        return False
    
    if len(st.session_state.trade_mapping) == 0:
        try:
            mapping_df = load_trade_mapping_from_database()
            
            if len(mapping_df) > 0:
                perm_manager.log_user_action(
                    username, "TRADE_MAPPING_LOADED",
                    details=f"Loaded {len(mapping_df)} mappings"
                )
                
                st.session_state.trade_mapping = mapping_df
                st.session_state.step_completed["mapping"] = True
                return True
        
        except Exception as e:
            perm_manager.log_user_action(
                username, "TRADE_MAPPING_LOAD_ERROR",
                success=False, details=str(e)
            )
    
    return False

# =============================================================================
# ORIGINAL UTILITY FUNCTIONS (UNCHANGED)
# =============================================================================

def get_corrected_database_stats(db_path="inspection_system.db"):
    """Get corrected database statistics that count unique buildings"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(DISTINCT building_name) 
            FROM processed_inspections 
            WHERE is_active = 1
        ''')
        active_inspections = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(DISTINCT building_name) 
            FROM processed_inspections
        ''')
        total_inspections = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) 
            FROM inspection_defects id
            JOIN processed_inspections pi ON id.inspection_id = pi.id
            WHERE pi.is_active = 1
        ''')
        total_defects = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_inspections': total_inspections,
            'active_inspections': active_inspections,
            'total_defects': total_defects
        }
        
    except Exception as e:
        print(f"Error getting corrected stats: {e}")
        return {'total_inspections': 0, 'active_inspections': 0, 'total_defects': 0}

def lookup_unit_defects(processed_data, unit_number):
    """Lookup defect history for a specific unit"""
    if processed_data is None or unit_number is None:
        return pd.DataFrame()
    
    unit_data = processed_data[
        (processed_data["Unit"].astype(str).str.strip().str.lower() == str(unit_number).strip().lower()) &
        (processed_data["StatusClass"] == "Not OK")
    ].copy()
    
    if len(unit_data) > 0:
        urgency_order = {"Urgent": 1, "High Priority": 2, "Normal": 3}
        unit_data["UrgencySort"] = unit_data["Urgency"].map(urgency_order).fillna(3)
        unit_data = unit_data.sort_values(["UrgencySort", "PlannedCompletion"])
        
        unit_data["PlannedCompletion"] = pd.to_datetime(unit_data["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
        
        return unit_data[["Room", "Component", "Trade", "Urgency", "PlannedCompletion"]]
    
    return pd.DataFrame(columns=["Room", "Component", "Trade", "Urgency", "PlannedCompletion"])

def load_master_trade_mapping():
    """Load the comprehensive MasterTradeMapping.csv data"""
    try:
        if os.path.exists("MasterTradeMapping.csv"):
            return pd.read_csv("MasterTradeMapping.csv")
        else:
            st.warning("MasterTradeMapping.csv not found in project folder")
            basic_mapping = """Room,Component,Trade
Apartment Entry Door,Door Handle,Doors
Apartment Entry Door,Door Locks and Keys,Doors
Balcony,Balustrade,Carpentry & Joinery
Bathroom,Tiles,Flooring - Tiles
Kitchen Area,Cabinets,Carpentry & Joinery"""
            return pd.read_csv(StringIO(basic_mapping))
    except Exception as e:
        st.error(f"Error loading master mapping: {e}")
        return pd.DataFrame(columns=["Room", "Component", "Trade"])

def process_inspection_data(df, mapping, building_info):
    """Process the inspection data with enhanced metrics calculation"""
    df = df.copy()
    
    # Extract unit number
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

    # Derive unit type
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

    # Classify status and urgency
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
        
        urgent_keywords = ["urgent", "immediate", "safety", "hazard", "dangerous", "critical", "severe"]
        safety_components = ["fire", "smoke", "electrical", "gas", "water", "security", "lock", "door handle"]
        
        if any(keyword in val_str for keyword in urgent_keywords):
            return "Urgent"
        
        if any(safety in component_str for safety in safety_components):
            return "High Priority"
        
        if "entry" in room_str and "door" in component_str:
            return "High Priority"
            
        return "Normal"

    long_df["StatusClass"] = long_df["Status"].apply(classify_status)
    long_df["Urgency"] = long_df.apply(lambda row: classify_urgency(row["Status"], row["Component"], row["Room"]), axis=1)

    # Merge with trade mapping
    merged = long_df.merge(mapping, on=["Room", "Component"], how="left")
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
    
    # Calculate metrics
    defects_per_unit = final_df[final_df["StatusClass"] == "Not OK"].groupby("Unit").size()
    
    ready_units = (defects_per_unit <= 2).sum() if len(defects_per_unit) > 0 else 0
    minor_work_units = ((defects_per_unit > 2) & (defects_per_unit <= 7)).sum() if len(defects_per_unit) > 0 else 0
    major_work_units = ((defects_per_unit > 7) & (defects_per_unit <= 15)).sum() if len(defects_per_unit) > 0 else 0
    extensive_work_units = (defects_per_unit > 15).sum() if len(defects_per_unit) > 0 else 0
    
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
    urgent_defects = defects_only[defects_only["Urgency"] == "Urgent"]
    high_priority_defects = defects_only[defects_only["Urgency"] == "High Priority"]
    
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

def create_zip_package(excel_bytes, word_bytes, metrics):
    """Create a ZIP package containing both reports"""
    zip_buffer = BytesIO()
    
    mel_tz = pytz.timezone("Australia/Melbourne")
    timestamp = datetime.now(mel_tz).strftime("%Y%m%d_%H%M%S")
    
    from excel_report_generator import generate_filename
    excel_filename = f"{generate_filename(metrics['building_name'], 'Excel')}.xlsx"
    word_filename = f"{generate_filename(metrics['building_name'], 'Word')}.docx" if word_bytes else None
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(excel_filename, excel_bytes)
        
        if word_bytes and word_filename:
            zip_file.writestr(word_filename, word_bytes)
        
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
- Urgent Defects: {metrics['urgent_defects']}

Files Included:
- {excel_filename}
{'- ' + word_filename if word_bytes else '- Word report (not available)'}
- inspection_summary.txt (this file)
"""
        zip_file.writestr("inspection_summary.txt", summary_content)
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

# =============================================================================
# SECURE MAIN APPLICATION LOGIC
# =============================================================================

def main():
    """Main application with enhanced security"""
    
    # Security initialization
    auth_manager = get_auth_manager()
    
    # Check authentication
    if not auth_manager.is_session_valid():
        show_secure_login_page()
        st.stop()
    
    # Show secure user menu
    if not show_secure_user_menu():
        st.stop()
    
    # Initialize user data securely
    try:
        data_loaded = secure_initialize_user_data()
        mapping_loaded = secure_load_trade_mapping()
        
        if data_loaded:
            building_name = st.session_state.metrics.get('building_name', 'Unknown')
            st.info(f"Loaded inspection data for {building_name}")
        
        if mapping_loaded:
            st.info("Trade mapping loaded from database")
    
    except PermissionError as e:
        st.error(f"Data loading failed: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Initialization error: {e}")
    
    # Get current user
    user = auth_manager.get_current_user()
    perm_manager = get_permission_manager()
    
    # Log page access
    perm_manager.log_user_action(user['username'], "PAGE_ACCESS: Main Application")
    
    # Show admin audit log if requested
    if st.session_state.get('show_audit_log', False):
        if perm_manager.has_permission(user['username'], "system.admin"):
            st.markdown("---")
            st.markdown("### System Audit Log")
            
            if st.button("Close Audit Log"):
                st.session_state.show_audit_log = False
                st.rerun()
            
            audit_trail_viewer(limit=100)
            st.markdown("---")
        else:
            st.session_state.show_audit_log = False
    
    # Show permissions debug if requested (admin only)
    if st.session_state.get('show_permissions_debug', False):
        if perm_manager.has_permission(user['username'], "system.admin"):
            st.markdown("---")
            st.markdown("### User Permissions Debug")
            
            if st.button("Close Debug View"):
                st.session_state.show_permissions_debug = False
                st.rerun()
            
            show_permissions_debug()
            st.markdown("---")
        else:
            st.session_state.show_permissions_debug = False
    
    # Main application routing based on dashboard type
    if user['dashboard_type'] == 'inspector':
        show_corrected_inspector_interface()
    
    elif user['dashboard_type'] == 'admin':
        show_secure_admin_interface()
    
    else:
        # For other roles, load their specific dashboards
        show_role_specific_dashboard(user)

def show_corrected_inspector_interface():
    """Corrected inspector interface with proper CSV error handling"""
    
    username = st.session_state.get("username")
    ui = create_secure_ui()
    perm_manager = get_permission_manager()
    
    # Main header (no permission needed to see this)
    st.markdown(f"""
    <div class="main-header">
        <h1>Secure Inspection Report Processor</h1>
        <p>Professional Data Processing Interface</p>
        <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
            <span>Welcome back, <strong>{st.session_state.user_name}</strong>!</span>
            <span style="margin-left: 2rem;">Role: <strong>Inspector</strong></span>
            <span style="margin-left: 2rem;">Security: <strong>Enhanced</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # STEP 1: Trade Mapping Section
    st.markdown("""
    <div class="step-container">
        <div class="step-header">Step 1: Load Master Trade Mapping</div>
        <p style="color: #666;">Upload your trade mapping file or use the default template</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Trade mapping management:**")
        
        if len(st.session_state.trade_mapping) == 0:
            st.warning("Trade mapping is currently blank. Please load a mapping file or use the default template.")
        else:
            st.success(f"Trade mapping loaded: {len(st.session_state.trade_mapping)} entries")
    
    with col2:
        # Template downloads - NO PERMISSION NEEDED (they're just templates)
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
            help="Download a comprehensive mapping template",
            use_container_width=True
        )
    
    # File upload - CHECK PERMISSION HERE
    if perm_manager.has_permission(username, "data.upload"):
        mapping_file = st.file_uploader(
            "Choose trade mapping CSV", 
            type=["csv"], 
            key="mapping_upload",
            help="Upload your custom trade mapping file"
        )
        
        if mapping_file is not None:
            try:
                # Enhanced CSV reading with error handling
                mapping_df = safe_read_csv(mapping_file, "Trade Mapping")
                if mapping_df is not None:
                    st.session_state.trade_mapping = mapping_df
                    st.session_state.step_completed["mapping"] = True
                    
                    save_trade_mapping_to_database(st.session_state.trade_mapping, username)
                    perm_manager.log_user_action(username, "TRADE_MAPPING_UPLOADED", 
                                               details=f"Uploaded {len(mapping_df)} mappings")
                    
                    st.success(f"Trade mapping loaded successfully! {len(mapping_df)} entries loaded.")
                    st.rerun()
            except Exception as e:
                st.error(f"Error loading mapping file: {e}")
    else:
        st.info("Upload custom mapping files requires data upload permission. You can still download and use templates.")
    
    # Action buttons with individual permission checks
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if perm_manager.has_permission(username, "data.upload"):
            if st.button("Load Master Mapping", type="secondary", use_container_width=True):
                try:
                    master_mapping = load_master_trade_mapping()
                    st.session_state.trade_mapping = master_mapping
                    st.session_state.step_completed["mapping"] = True
                    
                    save_trade_mapping_to_database(st.session_state.trade_mapping, username)
                    
                    trades = master_mapping['Trade'].nunique()
                    rooms = master_mapping['Room'].nunique() 
                    st.success(f"Master mapping loaded! {len(master_mapping)} entries covering {trades} trades and {rooms} room types")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error loading master mapping: {e}")
        else:
            st.button("Load Master Mapping", disabled=True, use_container_width=True,
                     help="Requires data upload permission")
    
    with col2:
        try:
            master_mapping = load_master_trade_mapping()
            template_csv = master_mapping.to_csv(index=False)
            
            st.download_button(
                "Download Master Template",
                data=template_csv,
                file_name="MasterTradeMapping_Complete.csv", 
                mime="text/csv",
                help=f"Download complete mapping template ({len(master_mapping)} entries)",
                use_container_width=True
            )
        except Exception:
            st.info("Master template not available")
    
    with col3:
        if perm_manager.has_permission(username, "data.upload"):
            if st.button("Clear Mapping", use_container_width=True):
                st.session_state.trade_mapping = pd.DataFrame(columns=["Room", "Component", "Trade"])
                st.session_state.step_completed["mapping"] = False
                st.rerun()
        else:
            st.button("Clear Mapping", disabled=True, use_container_width=True,
                     help="Requires data upload permission")
    
    # Display current mapping
    if len(st.session_state.trade_mapping) > 0:
        st.markdown("**Current Trade Mapping:**")
        if perm_manager.has_permission(username, "data.view_assigned"):
            st.dataframe(st.session_state.trade_mapping, use_container_width=True, height=200)
        else:
            st.error("You need data view permission to see the current mapping")
    else:
        st.info("No trade mapping loaded. Please load the default template or upload your own mapping file.")
    
    # STEP 2: Upload and Process Data
    st.markdown("""
    <div class="step-container">
        <div class="step-header">Step 2: Upload Inspection Data</div>
        <p style="color: #666;">Upload your inspection CSV file for processing</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if mapping is loaded
    if len(st.session_state.trade_mapping) == 0:
        st.warning("Please load your trade mapping first before uploading the inspection CSV file.")
        return
    
    # File upload and processing - CHECK PERMISSION HERE
    if perm_manager.has_permission(username, "data.upload"):
        uploaded_csv = st.file_uploader(
            "Choose inspection CSV file", 
            type=["csv"], 
            key="inspection_upload",
            help="Upload your iAuditor CSV file for processing"
        )
        
        if uploaded_csv is not None:
            # Show file preview with enhanced error handling
            try:
                # Use the safe CSV reader
                preview_df = safe_read_csv(uploaded_csv, "Inspection Data", preview_only=True)
                
                if preview_df is not None:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.success(f"Rows: {len(preview_df):,}")
                    with col2:
                        st.success(f"Columns: {len(preview_df.columns)}")
                    with col3:
                        file_size = uploaded_csv.size / 1024
                        st.success(f"Size: {file_size:.1f} KB")
                    
                    # Show preview
                    with st.expander("Preview Data", expanded=False):
                        st.dataframe(preview_df.head(10), use_container_width=True)
                    
                    # Processing button - CHECK PERMISSION HERE
                    if perm_manager.has_permission(username, "data.process"):
                        if st.button("Process Inspection Data", type="primary", use_container_width=True):
                            try:
                                with st.spinner("Processing inspection data securely..."):
                                    # Read the full CSV file safely
                                    df = safe_read_csv(uploaded_csv, "Inspection Data")
                                    
                                    if df is not None:
                                        building_info = {
                                            "name": st.session_state.building_info["name"],
                                            "address": st.session_state.building_info["address"],
                                            "date": datetime.now().strftime("%Y-%m-%d")
                                        }
                                        
                                        processed_df, metrics, saved = secure_process_inspection_data_with_persistence(
                                            df, st.session_state.trade_mapping, building_info, username
                                        )
                                        
                                        st.rerun()
                                    
                            except PermissionError as e:
                                st.error(f"Permission denied: {e}")
                            except Exception as e:
                                st.error(f"Error processing data: {e}")
                                st.code(traceback.format_exc())
                    else:
                        st.error("You need data processing permission to process inspection data")
                
            except Exception as e:
                st.error(f"Error reading CSV file: {e}")
    else:
        st.error("You need data upload permission to upload inspection files")
        st.info("Contact your administrator to request data upload permissions")
    
    # STEP 3: Results
    if (st.session_state.processed_data is not None and 
        st.session_state.metrics is not None and 
        perm_manager.has_permission(username, "data.view_assigned")):
        
        show_corrected_results_interface()

def safe_read_csv(uploaded_file, file_type, preview_only=False):
    """Safely read CSV file with comprehensive error handling"""
    
    try:
        # Reset file pointer to beginning
        uploaded_file.seek(0)
        
        # Read file content as string first to check if it's empty
        content = uploaded_file.read()
        
        if not content:
            st.error(f"The {file_type} file is empty. Please upload a valid CSV file.")
            return None
        
        # Reset file pointer again
        uploaded_file.seek(0)
        
        # Try to detect encoding
        try:
            # Try UTF-8 first
            content_str = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                # Try latin-1 as fallback
                content_str = content.decode('latin-1')
            except UnicodeDecodeError:
                # Try cp1252 as another fallback
                content_str = content.decode('cp1252')
        
        # Check if content has actual data
        lines = content_str.strip().split('\n')
        if len(lines) < 2:
            st.error(f"The {file_type} file must have at least a header row and one data row.")
            return None
        
        # Reset file pointer one more time
        uploaded_file.seek(0)
        
        # Try different CSV reading approaches
        try:
            # Standard approach
            df = pd.read_csv(uploaded_file)
        except pd.errors.EmptyDataError:
            st.error(f"The {file_type} file appears to be empty or has no parseable data.")
            return None
        except pd.errors.ParserError as e:
            # Try with different parameters
            uploaded_file.seek(0)
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8', sep=',')
            except:
                uploaded_file.seek(0)
                try:
                    df = pd.read_csv(uploaded_file, encoding='latin-1', sep=',')
                except:
                    st.error(f"Could not parse the {file_type} file. Please ensure it's a valid CSV format.")
                    st.error(f"Parser error: {str(e)}")
                    return None
        
        # Validate the dataframe
        if df is None or len(df) == 0:
            st.error(f"The {file_type} file contains no data rows.")
            return None
        
        if len(df.columns) == 0:
            st.error(f"The {file_type} file contains no columns.")
            return None
        
        # For preview, return only first 20 rows
        if preview_only:
            return df.head(20)
        
        # Check for reasonable file size (not too large)
        if len(df) > 50000:
            st.warning(f"Large file detected ({len(df):,} rows). Processing may take some time.")
        
        st.success(f"Successfully loaded {file_type}: {len(df):,} rows, {len(df.columns)} columns")
        
        return df
        
    except Exception as e:
        st.error(f"Unexpected error reading {file_type} file: {str(e)}")
        
        # Provide helpful debugging information
        st.markdown("**Debugging Information:**")
        st.write(f"File name: {uploaded_file.name}")
        st.write(f"File size: {uploaded_file.size} bytes")
        
        # Show first few lines of the file for debugging
        try:
            uploaded_file.seek(0)
            first_lines = uploaded_file.read(500).decode('utf-8', errors='ignore')
            st.text_area("First 500 characters of file:", first_lines, height=100)
        except:
            st.write("Could not display file content for debugging")
        
        return None

def show_corrected_results_interface():
    """Show results interface with corrected permission logic"""
    
    username = st.session_state.get("username")
    perm_manager = get_permission_manager()
    metrics = st.session_state.metrics
    
    st.markdown("""
    <div class="step-container">
        <div class="step-header">Step 3: Analysis Results & Downloads</div>
        <p style="color: #666;">View processed data and generate reports</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Building Information (no permission needed to see building info)
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
    
    # Key Metrics Dashboard (check view permission)
    if perm_manager.has_permission(username, "data.view_assigned"):
        st.subheader("Key Metrics Dashboard")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Units", f"{metrics['total_units']:,}")
        with col2:
            st.metric("Total Defects", f"{metrics['total_defects']:,}", delta=f"{metrics['defect_rate']:.1f}% rate")
        with col3:
            st.metric("Ready Units", f"{metrics['ready_units']}", delta=f"{metrics['ready_pct']:.1f}%")
        with col4:
            st.metric("Avg Defects/Unit", f"{metrics['avg_defects_per_unit']:.1f}")
        with col5:
            completion_efficiency = (metrics['ready_units'] / metrics['total_units'] * 100) if metrics['total_units'] > 0 else 0
            st.metric("Completion Efficiency", f"{completion_efficiency:.1f}%")
    else:
        st.error("You need data view permission to see metrics")
    
    # Unit Lookup (check view permission)
    st.markdown("---")
    if perm_manager.has_permission(username, "data.view_assigned"):
        st.markdown("""
        <div class="unit-lookup-container">
            <h3 style="text-align: center; margin-bottom: 1rem;">Unit Defect Lookup</h3>
            <p style="text-align: center;">Quickly search for any unit's complete defect history</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            all_units = sorted(st.session_state.processed_data["Unit"].astype(str).unique())
            
            search_unit = st.selectbox(
                "Enter or Select Unit Number:",
                options=[""] + all_units,
                help="Type to search or select from dropdown",
                key="corrected_unit_search"
            )
            
            if search_unit:
                unit_defects = lookup_unit_defects(st.session_state.processed_data, search_unit)
                
                if len(unit_defects) > 0:
                    st.markdown(f"### Unit {search_unit} - Complete Defect Report")
                    
                    # Summary metrics
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
                    
                    # Status assessment
                    if urgent_count > 0:
                        st.error(f"**HIGH ATTENTION REQUIRED** - {urgent_count} urgent defect(s) need immediate attention!")
                    elif high_priority_count > 0:
                        st.warning(f"**PRIORITY WORK** - {high_priority_count} high priority defect(s) to address")
                    elif normal_count > 0:
                        st.info(f"**STANDARD WORK** - {normal_count} normal defect(s) to complete")
                    
                    st.markdown("**Detailed Defect List:**")
                    st.dataframe(unit_defects, use_container_width=True)
                
                else:
                    st.success(f"**Unit {search_unit} is DEFECT-FREE!**")
    else:
        st.error("You need data view permission to use unit lookup")
    
    # Summary Tables Section
    st.markdown("---")
    st.subheader("Summary Tables")
    
    if perm_manager.has_permission(username, "data.view_assigned"):
        # Create tabs normally (no individual permission checks needed)
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Trade Summary", 
            "Unit Summary", 
            "Room Summary", 
            "Urgent Defects", 
            "Planned Work"
        ])
        
        with tab1:
            st.markdown("**Trade-wise defect breakdown**")
            if len(metrics['summary_trade']) > 0:
                st.dataframe(metrics['summary_trade'], use_container_width=True)
            else:
                st.info("No trade defects found")
        
        with tab2:
            st.markdown("**Unit-wise defect breakdown**")
            if len(metrics['summary_unit']) > 0:
                st.dataframe(metrics['summary_unit'], use_container_width=True)
            else:
                st.info("No unit defects found")
        
        with tab3:
            st.markdown("**Room-wise defect breakdown**")
            if len(metrics['summary_room']) > 0:
                st.dataframe(metrics['summary_room'], use_container_width=True)
            else:
                st.info("No room defects found")
        
        with tab4:
            st.markdown("**URGENT DEFECTS - Immediate attention required!**")
            if len(metrics['urgent_defects_table']) > 0:
                urgent_display = metrics['urgent_defects_table'].copy()
                urgent_display["PlannedCompletion"] = pd.to_datetime(urgent_display["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
                st.dataframe(urgent_display, use_container_width=True)
                st.error(f"**{len(urgent_display)} URGENT defects require immediate attention!**")
            else:
                st.success("No urgent defects found!")
        
        with tab5:
            st.markdown("**Planned Defect Work Schedule**")
            
            subtab1, subtab2 = st.tabs(["Next 2 Weeks", "Next Month"])
            
            with subtab1:
                st.markdown(f"**Work planned for next 2 weeks ({metrics['planned_work_2weeks']} items)**")
                if len(metrics['planned_work_2weeks_table']) > 0:
                    planned_2weeks = metrics['planned_work_2weeks_table'].copy()
                    planned_2weeks["PlannedCompletion"] = pd.to_datetime(planned_2weeks["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
                    st.dataframe(planned_2weeks, use_container_width=True)
                else:
                    st.success("No work planned for the next 2 weeks")
            
            with subtab2:
                st.markdown(f"**Work planned for next month ({metrics['planned_work_month']} items)**")
                if len(metrics['planned_work_month_table']) > 0:
                    planned_month = metrics['planned_work_month_table'].copy()
                    planned_month["PlannedCompletion"] = pd.to_datetime(planned_month["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
                    st.dataframe(planned_month, use_container_width=True)
                else:
                    st.success("No work planned for this period")
    else:
        st.error("You need data view permission to see summary tables")
    
    # STEP 4: Report Generation
    st.markdown("""
    <div class="step-container">
        <div class="step-header">Step 4: Generate & Download Reports</div>
        <p style="color: #666;">Create professional reports with audit logging</p>
    </div>
    """, unsafe_allow_html=True)
    
    show_corrected_report_generation(username, perm_manager, metrics)

def show_corrected_report_generation(username, perm_manager, metrics):
    """Show report generation with corrected permission logic"""
    
    # Check if user has ANY report generation permission
    can_generate_reports = perm_manager.has_permission(username, "reports.generate")
    
    if not can_generate_reports:
        st.error("You need report generation permission to create reports")
        return
    
    st.subheader("Professional Report Generation")
    
    col1, col2 = st.columns(2)
    
    # Complete Package
    with col1:
        st.markdown("### Complete Package")
        st.write("Excel + Word reports in a single ZIP file")
        
        # Check individual permissions for package
        can_excel = perm_manager.has_permission(username, "reports.excel")
        can_word = perm_manager.has_permission(username, "reports.word")
        
        if can_excel or can_word:
            if st.button("Generate Complete Package", type="primary", use_container_width=True):
                try:
                    with st.spinner("Generating report package..."):
                        perm_manager.log_user_action(username, "REPORT_PACKAGE_START", resource=metrics['building_name'])
                        
                        excel_bytes = None
                        word_bytes = None
                        
                        # Generate Excel if permitted and available
                        if can_excel and EXCEL_REPORT_AVAILABLE:
                            excel_buffer = generate_professional_excel_report(st.session_state.processed_data, metrics)
                            excel_bytes = excel_buffer.getvalue()
                        
                        # Generate Word if permitted and available
                        if can_word and WORD_REPORT_AVAILABLE:
                            try:
                                doc = generate_professional_word_report(
                                    st.session_state.processed_data, 
                                    metrics, 
                                    st.session_state.report_images
                                )
                                buf = BytesIO()
                                doc.save(buf)
                                buf.seek(0)
                                word_bytes = buf.getvalue()
                            except Exception as e:
                                st.warning(f"Word report generation failed: {e}")
                        
                        if excel_bytes or word_bytes:
                            zip_bytes = create_zip_package(excel_bytes, word_bytes, metrics)
                            zip_filename = f"{generate_filename(metrics['building_name'], 'Package')}.zip"
                            
                            perm_manager.log_user_action(username, "REPORT_PACKAGE_SUCCESS", resource=metrics['building_name'])
                            
                            st.success("Report package generated!")
                            st.download_button(
                                "Download Complete Package",
                                data=zip_bytes,
                                file_name=zip_filename,
                                mime="application/zip",
                                use_container_width=True
                            )
                        else:
                            st.error("No reports could be generated with your current permissions")
                
                except Exception as e:
                    st.error(f"Error generating package: {e}")
        else:
            st.error("You need Excel or Word report permissions to generate packages")
    
    # Individual Reports
    with col2:
        st.markdown("### Individual Reports")
        
        # Excel Report
        if perm_manager.has_permission(username, "reports.excel"):
            if st.button("Generate Excel Report", type="secondary", use_container_width=True):
                try:
                    with st.spinner("Generating Excel report..."):
                        if EXCEL_REPORT_AVAILABLE:
                            perm_manager.log_user_action(username, "EXCEL_REPORT_START", resource=metrics['building_name'])
                            
                            excel_bytes = generate_professional_excel_report(st.session_state.processed_data, metrics)
                            filename = f"{generate_filename(metrics['building_name'], 'Excel')}.xlsx"
                            
                            perm_manager.log_user_action(username, "EXCEL_REPORT_SUCCESS", resource=metrics['building_name'])
                            
                            st.success("Excel report generated!")
                            st.download_button(
                                "Download Excel Report",
                                data=excel_bytes,
                                file_name=filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                        else:
                            st.error("Excel generator not available")
                except Exception as e:
                    st.error(f"Error generating Excel: {e}")
        else:
            st.button("Generate Excel Report", disabled=True, use_container_width=True, 
                     help="Requires Excel report permission")
        
        # Word Report
        if perm_manager.has_permission(username, "reports.word"):
            if WORD_REPORT_AVAILABLE:
                if st.button("Generate Word Report", type="secondary", use_container_width=True):
                    try:
                        with st.spinner("Generating Word report..."):
                            perm_manager.log_user_action(username, "WORD_REPORT_START", resource=metrics['building_name'])
                            
                            doc = generate_professional_word_report(
                                st.session_state.processed_data, 
                                metrics, 
                                st.session_state.report_images
                            )
                            buf = BytesIO()
                            doc.save(buf)
                            buf.seek(0)
                            word_bytes = buf.getvalue()
                            filename = f"{generate_filename(metrics['building_name'], 'Word')}.docx"
                            
                            perm_manager.log_user_action(username, "WORD_REPORT_SUCCESS", resource=metrics['building_name'])
                            
                            st.success("Word report generated!")
                            st.download_button(
                                "Download Word Report",
                                data=word_bytes,
                                file_name=filename,
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                use_container_width=True
                            )
                    except Exception as e:
                        st.error(f"Error generating Word: {e}")
            else:
                st.warning("Word generator not available")
        else:
            st.button("Generate Word Report", disabled=True, use_container_width=True,
                     help="Requires Word report permission")

def show_secure_admin_interface():
    """Secure admin interface with modern design"""
    
    username = st.session_state.get("username")
    perm_manager = get_permission_manager()
    
    if not perm_manager.has_permission(username, "system.admin"):
        st.error("System administrator permission required")
        return
    
    # Use the modern dashboard
    try:
        from dashboards.admin_dashboard import AdminDashboard  # Keep this import
        dashboard = AdminDashboard()
        
        # Simple admin mode selection
        admin_mode = st.radio(
            "",
            ["Dashboard", "Data Processing"],
            index=0,
            horizontal=True,
            label_visibility="collapsed"
        )
        
        if admin_mode == "Data Processing":
            st.info("Full inspection processing interface with administrator privileges")
            show_corrected_inspector_interface()
        else:
            dashboard.show(force_workspace="System Administration")
    
    except ImportError as e:
        st.error(f"Admin dashboard not available: {e}")
        show_fallback_admin_interface()

def main():
    """Main application with enhanced security and clean design"""
    
    # Security initialization
    auth_manager = get_auth_manager()
    
    # Check authentication
    if not auth_manager.is_session_valid():
        show_secure_login_page()
        st.stop()
    
    # Show clean user sidebar (UPDATED)
    if not show_clean_user_sidebar():
        st.stop()
    
    # Initialize user data securely
    try:
        data_loaded = secure_initialize_user_data()
        mapping_loaded = secure_load_trade_mapping()
        
        if data_loaded:
            building_name = st.session_state.metrics.get('building_name', 'Unknown')
            st.info(f"Loaded inspection data for {building_name}")
        
        if mapping_loaded:
            st.info("Trade mapping loaded from database")
    
    except PermissionError as e:
        st.error(f"Data loading failed: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Initialization error: {e}")
    
    # Get current user
    user = auth_manager.get_current_user()
    perm_manager = get_permission_manager()
    
    # Log page access
    perm_manager.log_user_action(user['username'], "PAGE_ACCESS: Main Application")
    
    # Handle sidebar actions
    if st.session_state.get('sidebar_action'):
        handle_sidebar_actions(st.session_state.sidebar_action, user, perm_manager)
        st.session_state.sidebar_action = None
    
    # Show admin audit log if requested
    if st.session_state.get('show_audit_log', False):
        if perm_manager.has_permission(user['username'], "system.admin"):
            st.markdown("---")
            st.markdown("### System Audit Log")
            
            if st.button("Close Audit Log"):
                st.session_state.show_audit_log = False
                st.rerun()
            
            audit_trail_viewer(limit=100)
            st.markdown("---")
        else:
            st.session_state.show_audit_log = False
    
    # Show permissions debug if requested (admin only)
    if st.session_state.get('show_permissions_debug', False):
        if perm_manager.has_permission(user['username'], "system.admin"):
            st.markdown("---")
            st.markdown("### User Permissions Debug")
            
            if st.button("Close Debug View"):
                st.session_state.show_permissions_debug = False
                st.rerun()
            
            show_permissions_debug()
            st.markdown("---")
        else:
            st.session_state.show_permissions_debug = False
    
    # Main application routing based on dashboard type
    if user['dashboard_type'] == 'inspector':
        show_corrected_inspector_interface()
    
    elif user['dashboard_type'] == 'admin':
        show_secure_admin_interface()
    
    else:
        # For other roles, load their specific dashboards
        show_role_specific_dashboard(user)

def handle_sidebar_actions(action, user, perm_manager):
    """Handle actions triggered from the clean sidebar"""
    
    if action == "upload":
        if perm_manager.has_permission(user['username'], "data.upload"):
            st.info("Upload interface activated. Please use the file uploader below.")
        else:
            st.error("You don't have permission to upload data")
    
    elif action == "process":
        if perm_manager.has_permission(user['username'], "data.process"):
            if st.session_state.processed_data is None:
                st.warning("No data available to process. Please upload data first.")
            else:
                st.info("Data processing interface is now active.")
        else:
            st.error("You don't have permission to process data")
    
    elif action == "report":
        if perm_manager.has_permission(user['username'], "reports.generate"):
            if st.session_state.processed_data is None:
                st.warning("No data available for reports. Please upload and process data first.")
            else:
                st.success("Report generation interface is now active.")
        else:
            st.error("You don't have permission to generate reports")

def show_fallback_admin_interface():
    """Fallback admin interface if modern dashboard fails"""
    
    st.markdown("### System Administration")
    st.info("Using fallback admin interface. Please check that admin_dashboard.py is properly configured.")
    
    # Basic stats
    try:
        stats = get_corrected_database_stats()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Buildings", stats.get("total_inspections", 0))
        with col2:
            st.metric("Active Buildings", stats.get("active_inspections", 0))
        with col3:
            st.metric("Total Defects", stats.get("total_defects", 0))
    
    except Exception as e:
        st.error(f"Error loading system stats: {e}")
    
    # Basic controls
    st.markdown("### Basic Controls")
    if st.button("View System Status"):
        st.info("System is operational")
    
    if st.button("Export Data"):
        st.info("Data export would be available in full version")

def show_system_admin_interface():
    """System administration interface - FIXED"""
    try:
        from dashboards.admin_dashboard import AdminDashboard
        dashboard = AdminDashboard()
        # Force the System Administration workspace, skip workspace selection
        dashboard.show(force_workspace="System Administration")
    except ImportError:
        st.info("Loading basic system administration...")
        
        # Basic system stats
        stats = get_corrected_database_stats()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Buildings", stats.get("total_inspections", 0))
        with col2:
            st.metric("Active Buildings", stats.get("active_inspections", 0))
        with col3:
            st.metric("Total Defects", stats.get("total_defects", 0))

def show_security_management_interface():
    """Security management interface for admins"""
    
    username = st.session_state.get("username")
    perm_manager = get_permission_manager()
    
    st.markdown("### Security Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Audit Trail")
        if st.button("View Full Audit Log", use_container_width=True):
            st.session_state.show_full_audit = True
        
        if st.button("Export Security Report", use_container_width=True):
            # Generate security report
            try:
                conn = sqlite3.connect("inspection_system.db")
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT username, action, success, timestamp
                    FROM audit_log 
                    WHERE action LIKE '%SECURITY%' OR action LIKE '%LOGIN%'
                    ORDER BY timestamp DESC 
                    LIMIT 1000
                ''')
                
                results = cursor.fetchall()
                conn.close()
                
                if results:
                    import pandas as pd
                    df = pd.DataFrame(results, columns=['Username', 'Action', 'Success', 'Timestamp'])
                    csv = df.to_csv(index=False)
                    
                    st.download_button(
                        "Download Security Report",
                        data=csv,
                        file_name=f"security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.info("No security events found")
            
            except Exception as e:
                st.error(f"Error generating security report: {e}")
    
    with col2:
        st.markdown("#### System Health")
        
        # Check for suspicious activity
        try:
            conn = sqlite3.connect("inspection_system.db")
            cursor = conn.cursor()
            
            # Failed logins in last hour
            cursor.execute('''
                SELECT COUNT(*) FROM audit_log 
                WHERE action = 'LOGIN_FAILED' 
                AND timestamp > datetime('now', '-1 hour')
            ''')
            recent_failures = cursor.fetchone()[0]
            
            # Permission denials in last hour
            cursor.execute('''
                SELECT COUNT(*) FROM audit_log 
                WHERE action LIKE '%PERMISSION_DENIED%' 
                AND timestamp > datetime('now', '-1 hour')
            ''')
            permission_denials = cursor.fetchone()[0]
            
            conn.close()
            
            if recent_failures > 10:
                st.error(f"⚠️ High login failures: {recent_failures} in last hour")
            elif recent_failures > 0:
                st.warning(f"Login failures: {recent_failures} in last hour")
            else:
                st.success("✅ No recent login failures")
            
            if permission_denials > 5:
                st.error(f"⚠️ High permission denials: {permission_denials} in last hour")
            elif permission_denials > 0:
                st.warning(f"Permission denials: {permission_denials} in last hour")
            else:
                st.success("✅ No recent permission issues")
        
        except Exception as e:
            st.error(f"Error checking security status: {e}")
    
    # Show full audit if requested
    if st.session_state.get('show_full_audit', False):
        st.markdown("---")
        st.markdown("### Full System Audit Trail")
        
        if st.button("Close Full Audit"):
            st.session_state.show_full_audit = False
            st.rerun()
        
        audit_trail_viewer(limit=500)

def show_role_specific_dashboard(user):
    """Show role-specific dashboard for non-inspector/admin users"""
    
    try:
        if user['dashboard_type'] == 'portfolio':
            from dashboards.developer_dashboard import DeveloperDashboard
            dashboard = DeveloperDashboard()
            dashboard.show()
        
        elif user['dashboard_type'] == 'project':
            from dashboards.project_manager_dashboard import ProjectManagerDashboard
            dashboard = ProjectManagerDashboard()
            dashboard.show()
        
        elif user['dashboard_type'] == 'builder':
            from dashboards.builder_dashboard import BuilderDashboard
            dashboard = BuilderDashboard()
            dashboard.show()
        
        else:
            st.error(f"Unknown dashboard type: {user['dashboard_type']}")
            show_fallback_dashboard(user)
    
    except ImportError as e:
        st.error(f"Dashboard module not found: {e}")
        show_fallback_dashboard(user)
    
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")
        show_fallback_dashboard(user)

def show_fallback_dashboard(user):
    """Fallback dashboard for when specific dashboards fail"""
    
    st.info("Using fallback interface. Please ensure all dashboard files are properly installed.")
    
    if st.session_state.metrics is not None:
        st.markdown("### Building Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Building", st.session_state.metrics['building_name'])
        with col2:
            st.metric("Total Units", st.session_state.metrics['total_units'])
        with col3:
            st.metric("Urgent Issues", st.session_state.metrics['urgent_defects'])
    else:
        st.info("No inspection data available. Contact your team to process data.")

# =============================================================================
# MAIN APPLICATION ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    try:
        main()
        
        # Enhanced Footer with security indicators
        st.markdown("---")
        user = st.session_state.get("user_name", "Guest")
        role = st.session_state.get("user_role", "").replace('_', ' ').title()
        
        st.markdown(f"""
        <div style="text-align: center; padding: 1.5rem; background: #f8f9fa; border-radius: 8px; margin-top: 2rem;">
            <h4 style="color: #2c3e50; margin-bottom: 1rem;">🏢 Secure Inspection Report Processor v4.0</h4>
            <div style="display: flex; justify-content: center; gap: 1.5rem; flex-wrap: wrap; margin-bottom: 1rem;">
                <span><strong>Excel Reports:</strong> Multi-sheet analysis</span>
                <span><strong>Word Reports:</strong> Executive summaries</span>
                <span><strong>Security:</strong> Role-based access</span>
                <span><strong>Audit:</strong> Complete logging</span>
            </div>
            <div style="display: flex; justify-content: center; gap: 2rem; margin-bottom: 1rem;">
                <span style="color: #4caf50;">🔒 Authenticated: <strong>{user}</strong></span>
                <span style="color: #2196f3;">👤 Role: <strong>{role}</strong></span>
                <span style="color: #ff9800;">🕒 Session: Active</span>
            </div>
            <p style="color: #666; font-size: 0.9em;">
                Enhanced Security • Granular Permissions • Complete Audit Trail • Building Access Control
            </p>
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Application error: {e}")
        st.code(traceback.format_exc())


# =============================================================================
# ADDITIONAL SECURE INTERFACES (for completeness)
# =============================================================================

def show_secure_file_preview(uploaded_file, permission="data.view_assigned"):
    """Show secure file preview with permission check"""
    username = st.session_state.get("username")
    perm_manager = get_permission_manager()
    
    if not perm_manager.has_permission(username, permission):
        st.error("You don't have permission to preview files")
        return
    
    try:
        preview_df = pd.read_csv(uploaded_file)
        
        # Enhanced success message with file info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.success(f"Rows: {len(preview_df):,}")
        with col2:
            st.success(f"Columns: {len(preview_df.columns)}")
        with col3:
            file_size = uploaded_file.size / 1024
            st.success(f"Size: {file_size:.1f} KB")
        
        # Log file preview
        perm_manager.log_user_action(username, "FILE_PREVIEW", 
                                   details=f"{uploaded_file.name} - {len(preview_df)} rows")
        
        # Enhanced preview with security
        with st.expander("Secure Data Preview & Analysis", expanded=True):
            st.markdown("**Column Information:**")
            col_info = pd.DataFrame({
                'Column': preview_df.columns,
                'Type': [str(dtype) for dtype in preview_df.dtypes],
                'Non-Null': [preview_df[col].notna().sum() for col in preview_df.columns],
                'Null %': [f"{(preview_df[col].isna().sum() / len(preview_df) * 100):.1f}%" for col in preview_df.columns]
            })
            st.dataframe(col_info, use_container_width=True, height=200)
            
            st.markdown("**Data Sample (First 10 rows):**")
            st.dataframe(preview_df.head(10), use_container_width=True)
            st.caption(f"Showing first 10 rows of {len(preview_df):,} total rows • Data access logged")
            
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
                st.success("Access: Authorized")
                st.caption("File access logged")
    
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        perm_manager.log_user_action(username, "FILE_PREVIEW_ERROR", 
                                   success=False, details=str(e))

def show_secure_upload_interface():
    """Show secure upload interface with enhanced checks"""
    
    username = st.session_state.get("username")
    ui = create_secure_ui()
    
    # Upload inspection data with security
    uploaded_csv = ui.secure_file_uploader(
        "Choose inspection CSV file", 
        "data.upload",
        type=["csv"], 
        key="secure_inspection_upload",
        help="Upload your iAuditor CSV file for secure processing",
        disabled_message="You need data upload permission to upload inspection files"
    )
    
    if uploaded_csv is not None:
        # Show secure preview
        show_secure_file_preview(uploaded_csv)
        
        # Process button with enhanced security
        if ui.secure_button("🔒 Process Inspection Data Securely", "data.process", 
                           type="primary", use_container_width=True):
            try:
                with st.spinner("Processing inspection data securely..."):
                    df = pd.read_csv(uploaded_csv)
                    
                    building_info = {
                        "name": st.session_state.building_info["name"],
                        "address": st.session_state.building_info["address"],
                        "date": datetime.now().strftime("%Y-%m-%d")
                    }
                    
                    processed_df, metrics, saved = secure_process_inspection_data_with_persistence(
                        df, st.session_state.trade_mapping, building_info, username
                    )
                    
                    st.rerun()
                    
            except PermissionError as e:
                st.error(f"🔒 Permission denied: {e}")
            except Exception as e:
                st.error(f"Error processing data: {e}")
                st.code(traceback.format_exc())
    else:
        # Show upload guidance
        st.markdown("""
        <div style="background-color: #e3f2fd; border: 1px solid #2196f3; border-radius: 5px; padding: 1rem; margin: 1rem 0;">
            <h4>🔒 Secure Upload Ready</h4>
            <p>Please upload your iAuditor CSV file to begin secure processing. The system will:</p>
            <ul>
                <li>✅ Validate your permissions</li>
                <li>✅ Log all data access</li>
                <li>✅ Verify data quality</li>
                <li>✅ Apply trade mapping securely</li>
                <li>✅ Generate comprehensive analytics</li>
                <li>✅ Create audited professional reports</li>
                <li>✅ Track urgent defects with alerts</li>
                <li>✅ Enable secure unit lookups</li>
            </ul>
            <p style="color: #666; font-size: 0.9em;">All operations are logged and secured with role-based permissions.</p>
        </div>
        """, unsafe_allow_html=True)