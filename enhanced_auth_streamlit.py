# enhanced_auth_streamlit.py
# Integration of database authentication with your existing Streamlit app

import streamlit as st
import sqlite3
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class DatabaseAuthManager:
    """Database-powered authentication manager for Streamlit"""
    
    def __init__(self, db_path="inspection_system.db"):
        self.db_path = db_path
        self.session_timeout = 8 * 60 * 60  # 8 hours
        
        # Role capabilities (same as your current system but enhanced)
        self.role_capabilities = {
            "admin": {
                "can_upload": True,
                "can_process": True,
                "can_manage_users": True,
                "can_approve_defects": True,
                "can_view_all": True,
                "dashboard_type": "admin"
            },
            "property_developer": {
                "can_upload": False,
                "can_process": False,
                "can_manage_users": False,
                "can_approve_defects": True,
                "can_view_all": False,  # Only their portfolios
                "dashboard_type": "portfolio"
            },
            "project_manager": {
                "can_upload": True,
                "can_process": True,
                "can_manage_users": False,
                "can_approve_defects": True,
                "can_view_all": False,  # Only assigned projects
                "dashboard_type": "project"
            },
            "inspector": {
                "can_upload": True,
                "can_process": True,
                "can_manage_users": False,
                "can_approve_defects": False,
                "can_view_all": False,  # Only assigned buildings
                "dashboard_type": "inspector"
            },
            "builder": {
                "can_upload": False,
                "can_process": False,
                "can_manage_users": False,
                "can_approve_defects": False,
                "can_view_all": False,  # Only assigned defects
                "dashboard_type": "builder"
            }
        }
    
    def _hash_password(self, password: str) -> str:
        """Hash password with salt - same as your existing system"""
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
                # Update last login
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
        
        # Check session timeout
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
        
        # Clear application data
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
    
    def get_user_accessible_resources(self, resource_type: str) -> List[Dict]:
        """Get resources accessible to current user"""
        username = st.session_state.get("username", "")
        role = st.session_state.get("user_role", "")
        
        if not username:
            return []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if role == "admin":
                # Admin can access everything
                if resource_type == "portfolio":
                    cursor.execute('SELECT id, name, description FROM portfolios')
                elif resource_type == "project":
                    cursor.execute('SELECT id, name, description FROM projects')
                elif resource_type == "building":
                    cursor.execute('SELECT id, name, address FROM buildings')
            
            elif role == "property_developer":
                # Property developers can access their portfolios and child resources
                if resource_type == "portfolio":
                    cursor.execute('''
                        SELECT id, name, description FROM portfolios 
                        WHERE owner_username = ?
                    ''', (username,))
                elif resource_type == "project":
                    cursor.execute('''
                        SELECT p.id, p.name, p.description FROM projects p
                        JOIN portfolios po ON p.portfolio_id = po.id
                        WHERE po.owner_username = ?
                    ''', (username,))
                elif resource_type == "building":
                    cursor.execute('''
                        SELECT b.id, b.name, b.address FROM buildings b
                        JOIN projects p ON b.project_id = p.id
                        JOIN portfolios po ON p.portfolio_id = po.id
                        WHERE po.owner_username = ?
                    ''', (username,))
            
            else:
                # Other roles: check explicit permissions
                if resource_type == "portfolio":
                    cursor.execute('''
                        SELECT p.id, p.name, p.description FROM portfolios p
                        JOIN user_permissions up ON p.id = up.resource_id
                        WHERE up.username = ? AND up.resource_type = 'portfolio'
                    ''', (username,))
                elif resource_type == "project":
                    cursor.execute('''
                        SELECT p.id, p.name, p.description FROM projects p
                        JOIN user_permissions up ON p.id = up.resource_id
                        WHERE up.username = ? AND up.resource_type = 'project'
                    ''', (username,))
                elif resource_type == "building":
                    cursor.execute('''
                        SELECT b.id, b.name, b.address FROM buildings b
                        JOIN user_permissions up ON b.id = up.resource_id
                        WHERE up.username = ? AND up.resource_type = 'building'
                    ''', (username,))
            
            results = cursor.fetchall()
            conn.close()
            
            # Convert to list of dictionaries
            if resource_type == "portfolio":
                return [{"id": r[0], "name": r[1], "description": r[2]} for r in results]
            elif resource_type == "project":
                return [{"id": r[0], "name": r[1], "description": r[2]} for r in results]
            elif resource_type == "building":
                return [{"id": r[0], "name": r[1], "address": r[2]} for r in results]
            
            return []
            
        except Exception:
            return []

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
            🏢 Inspection Report System
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
            st.markdown("### 🔐 Login")
            
            username = st.text_input("👤 Username", placeholder="Enter your username")
            password = st.text_input("🔑 Password", type="password", placeholder="Enter your password")
            
            login_button = st.form_submit_button("🚀 Login", use_container_width=True, type="primary")
            
            if login_button:
                if username and password:
                    success, message = auth_manager.authenticate(username, password)
                    
                    if success:
                        auth_manager.create_session(username)
                        st.success(message)
                        time.sleep(1)  # Brief pause to show success message
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Please enter both username and password")
    
    # Enhanced demo credentials with role explanations
    with st.expander("🔑 Demo Credentials", expanded=False):
        st.info("""
        **Available Test Accounts:**
        
        **🔧 System Administrator:**
        - Username: `admin` | Password: `admin123`
        - Full system access, user management
        
        **🏗️ Property Developer:**
        - Username: `developer1` | Password: `dev123`
        - Portfolio view, defect approval, no uploads
        
        **📋 Project Manager:**
        - Username: `manager1` | Password: `mgr123`
        - Project management, data processing
        
        **🔍 Site Inspector:**
        - Username: `inspector1` | Password: `ins123`
        - Data upload and processing
        
        **👷 Builder:**
        - Username: `builder1` | Password: `build123`
        - Defect management, status updates
        """)
    
    # System status indicator
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 📊 Advanced Analytics
        - Portfolio-level dashboards
        - Cross-project reporting
        - Historical trend analysis
        """)
    
    with col2:
        st.markdown("""
        ### 🔄 Workflow Management
        - Defect lifecycle tracking
        - Digital approval process
        - Multi-user collaboration
        """)
    
    with col3:
        st.markdown("""
        ### 🔒 Role-Based Access
        - Granular permissions
        - Resource-level security
        - Audit trail logging
        """)

def show_enhanced_user_menu():
    """Enhanced user menu with database info and role-specific options"""
    
    auth_manager = get_auth_manager()
    
    if not auth_manager.is_session_valid():
        return False
    
    user = auth_manager.get_current_user()
    
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 👤 User Information")
        
        # Enhanced user info display
        st.markdown(f"""
        **Name:** {user['name']}  
        **Role:** {user['role'].replace('_', ' ').title()}  
        **Email:** {user['email']}  
        **Access:** {user['capabilities'].get('dashboard_type', 'standard').title()}
        """)
        
        # Role-specific capabilities display
        capabilities = user['capabilities']
        st.markdown("**Permissions:**")
        
        permissions = []
        if capabilities.get('can_upload'): permissions.append("📤 Upload Data")
        if capabilities.get('can_process'): permissions.append("⚙️ Process Data")
        if capabilities.get('can_approve_defects'): permissions.append("✅ Approve Defects")
        if capabilities.get('can_manage_users'): permissions.append("👥 Manage Users")
        if capabilities.get('can_view_all'): permissions.append("🌐 View All")
        
        for perm in permissions:
            st.caption(perm)
        
        # User actions
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔑 Change Password", use_container_width=True):
                st.session_state.show_password_change = True
        
        with col2:
            if st.button("🚪 Logout", use_container_width=True, type="primary"):
                auth_manager.logout()
                st.success("Logged out successfully!")
                st.rerun()
        
        # Resource access summary (for non-admin users)
        if user['role'] != 'admin':
            st.markdown("---")
            st.markdown("### 🏗️ Your Access")
            
            # Show accessible resources based on role
            if user['role'] == 'property_developer':
                portfolios = auth_manager.get_user_accessible_resources('portfolio')
                st.markdown(f"**Portfolios:** {len(portfolios)}")
                for portfolio in portfolios[:3]:  # Show first 3
                    st.caption(f"📋 {portfolio['name']}")
                if len(portfolios) > 3:
                    st.caption(f"... and {len(portfolios)-3} more")
            
            elif user['role'] in ['project_manager', 'inspector']:
                buildings = auth_manager.get_user_accessible_resources('building')
                st.markdown(f"**Buildings:** {len(buildings)}")
                for building in buildings[:3]:
                    st.caption(f"🏢 {building['name']}")
                if len(buildings) > 3:
                    st.caption(f"... and {len(buildings)-3} more")
        
        # Password change form (if requested)
        if st.session_state.get("show_password_change", False):
            st.markdown("---")
            st.markdown("### 🔑 Change Password")
            
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
                            # Here you would implement password change logic
                            st.success("Password change feature will be implemented")
                            st.session_state.show_password_change = False
                            st.rerun()
                
                with col2:
                    if st.form_submit_button("Cancel", use_container_width=True):
                        st.session_state.show_password_change = False
                        st.rerun()
    
    return True

def route_user_to_dashboard():
    """Route user to appropriate dashboard based on role"""
    
    user = get_auth_manager().get_current_user()
    dashboard_type = user.get('dashboard_type', 'inspector')
    
    if dashboard_type == 'portfolio':
        show_portfolio_dashboard()
    elif dashboard_type == 'project':
        show_project_dashboard()
    elif dashboard_type == 'builder':
        show_builder_dashboard()
    elif dashboard_type == 'admin':
        show_admin_dashboard()
    else:
        show_inspector_dashboard()

def show_portfolio_dashboard():
    """Dashboard for Property Developers"""
    st.markdown("### 🏗️ Portfolio Overview")
    
    auth_manager = get_auth_manager()
    portfolios = auth_manager.get_user_accessible_resources('portfolio')
    
    if portfolios:
        st.success(f"Managing {len(portfolios)} portfolio(s)")
        
        for portfolio in portfolios:
            with st.expander(f"📋 {portfolio['name']}", expanded=True):
                st.write(portfolio.get('description', 'No description available'))
                
                # Get projects in this portfolio
                projects = auth_manager.get_user_accessible_resources('project')
                # Filter projects for this portfolio (you'd need to modify the query)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Projects", len(projects))
                with col2:
                    st.metric("Buildings", "TBD")  # Calculate from database
                with col3:
                    st.metric("Pending Approvals", "TBD")  # Calculate from defects
                
                if st.button(f"View {portfolio['name']} Details", key=f"portfolio_{portfolio['id']}"):
                    st.session_state.selected_portfolio = portfolio['id']
                    # Navigate to detailed portfolio view
    else:
        st.info("No portfolios assigned to your account")

def show_project_dashboard():
    """Dashboard for Project Managers"""
    st.markdown("### 📋 Project Management")
    
    auth_manager = get_auth_manager()
    projects = auth_manager.get_user_accessible_resources('project')
    
    if projects:
        st.success(f"Managing {len(projects)} project(s)")
        # Show project management interface
    else:
        st.info("No projects assigned to your account")

def show_builder_dashboard():
    """Dashboard for Builders"""
    st.markdown("### 👷 Builder Workspace")
    
    auth_manager = get_auth_manager()
    buildings = auth_manager.get_user_accessible_resources('building')
    
    if buildings:
        st.success(f"Working on {len(buildings)} building(s)")
        # Show defect management interface
    else:
        st.info("No buildings assigned to your account")

def show_admin_dashboard():
    """Dashboard for System Administrators"""
    st.markdown("### 🔧 System Administration")
    st.success("Full system access granted")
    # Show admin interface

def show_inspector_dashboard():
    """Default dashboard for Inspectors - your current interface"""
    st.markdown("### 🔍 Inspection Management")
    # Your existing upload/process interface goes here
    st.info("Your existing inspection interface will be shown here")

# Helper function to check permissions throughout your app
def require_permission(action: str):
    """Decorator-like function to check permissions"""
    auth_manager = get_auth_manager()
    if not auth_manager.can_user_perform_action(action):
        st.error(f"You don't have permission to {action.replace('can_', '').replace('_', ' ')}")
        return False
    return True