"""
Enhanced Permission Manager with Granular Permissions and Security Features
"""
import sqlite3
import time
from functools import wraps
from typing import Dict, List, Optional, Tuple
import streamlit as st


class PermissionManager:
    """Enhanced permission management with granular controls and audit logging"""
    
    def __init__(self, db_path="inspection_system.db"):
        self.db_path = db_path
        self.permission_definitions = {
            "admin": {
                "data.upload": True,
                "data.process": True,
                "data.view_all": True,
                "data.view_assigned": True,
                "reports.generate": True,
                "reports.excel": True,
                "reports.word": True,
                "reports.portfolio": True,
                "users.create": True,
                "users.edit": True,
                "users.delete": True,
                "users.view_all": True,
                "buildings.view_all": True,
                "buildings.edit_all": True,
                "system.admin": True,
                "defects.approve": True,
                "defects.update_status": True,
                "dashboard.admin": True
            },
            "property_developer": {
                "data.upload": False,
                "data.process": False,
                "data.view_assigned": True,  # Can view assigned buildings
                "data.view_all": False,
                "reports.generate": True,
                "reports.excel": True,
                "reports.word": True,
                "reports.portfolio": True,
                "users.create": False,
                "users.edit": False,
                "users.delete": False,
                "users.view_all": False,
                "buildings.view_assigned": True,
                "buildings.edit_assigned": False,
                "system.admin": False,
                "defects.approve": True,
                "defects.update_status": False,
                "dashboard.portfolio": True
            },
            "project_manager": {
                "data.upload": True,
                "data.process": True,
                "data.view_assigned": True,  # Can view assigned buildings
                "data.view_all": False,
                "reports.generate": True,
                "reports.excel": True,
                "reports.word": True,
                "reports.portfolio": False,
                "users.create": False,
                "users.edit": False,
                "users.delete": False,
                "users.view_team": True,
                "buildings.view_assigned": True,
                "buildings.edit_assigned": True,
                "system.admin": False,
                "defects.approve": True,
                "defects.update_status": True,
                "dashboard.project": True
            },
            "inspector": {
                "data.upload": True,         # SHOULD BE TRUE
                "data.process": True,        # SHOULD BE TRUE
                "data.view_assigned": True,  # SHOULD BE TRUE
                "data.view_all": False,
                "reports.generate": True,    # SHOULD BE TRUE
                "reports.excel": True,       # SHOULD BE TRUE
                "reports.word": True,        # SHOULD BE TRUE
                "reports.portfolio": False,
                "users.create": False,
                "users.edit": False,
                "users.delete": False,
                "users.view_all": False,
                "buildings.view_assigned": True,
                "buildings.edit_assigned": False,
                "system.admin": False,
                "defects.approve": False,
                "defects.update_status": False,
                "dashboard.inspector": True
            },
            "builder": {
                "data.upload": False,
                "data.process": False,
                "data.view_assigned": True,  # Can view their work assignments
                "data.view_all": False,
                "reports.generate": True,    # Can generate work reports
                "reports.excel": False,
                "reports.word": False,
                "reports.portfolio": False,
                "users.create": False,
                "users.edit": False,
                "users.delete": False,
                "users.view_all": False,
                "buildings.view_assigned": True,
                "buildings.edit_assigned": False,
                "system.admin": False,
                "defects.approve": False,
                "defects.update_status": True,
                "dashboard.builder": True
            }
        }
        self._init_audit_table()
    
    def _init_audit_table(self):
        """Initialize audit logging table"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource TEXT,
                    success BOOLEAN NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    details TEXT
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error initializing audit table: {e}")
    
    def has_permission(self, username: str, permission: str) -> bool:
        """Check if user has specific permission"""
        try:
            user_role = self._get_user_role(username)
            if not user_role:
                return False
            
            permissions = self.permission_definitions.get(user_role, {})
            return permissions.get(permission, False)
        except Exception as e:
            self.log_security_event(username, f"Permission check failed: {permission}", success=False, details=str(e))
            return False
    
    def _get_user_role(self, username: str) -> Optional[str]:
        """Get user role from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT role FROM users WHERE username = ? AND is_active = 1', (username,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except Exception:
            return None
    
    def get_user_permissions(self, username: str) -> Dict[str, bool]:
        """Get all permissions for a user"""
        user_role = self._get_user_role(username)
        if not user_role:
            return {}
        return self.permission_definitions.get(user_role, {})
    
    def log_user_action(self, username: str, action: str, resource: str = None, 
                       success: bool = True, details: str = None):
        """Log user action for audit trail"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO audit_log (username, action, resource, success, details)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, action, resource, success, details))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error logging action: {e}")
    
    def log_security_event(self, username: str, event: str, success: bool = True, details: str = None):
        """Log security-related events"""
        self.log_user_action(username, f"SECURITY: {event}", success=success, details=details)
    
    def get_accessible_buildings(self, username: str) -> List[Tuple]:
        """Get buildings accessible to user based on role and assignments"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            user_role = self._get_user_role(username)
            
            if not user_role:
                conn.close()
                return []
            
            if user_role == 'admin':
                # Admins see all buildings
                cursor.execute('''
                    SELECT DISTINCT 
                        pi.building_name,
                        COUNT(DISTINCT id2.unit_number) as total_units,
                        MAX(pi.processed_at) as last_inspection
                    FROM processed_inspections pi
                    LEFT JOIN inspection_defects id2 ON pi.id = id2.inspection_id
                    WHERE pi.is_active = 1
                    GROUP BY pi.building_name
                    ORDER BY pi.building_name
                ''')
            elif user_role in ['project_manager', 'property_developer']:
                # PMs and developers see assigned buildings
                cursor.execute('''
                    SELECT DISTINCT 
                        pi.building_name,
                        COUNT(DISTINCT id2.unit_number) as total_units,
                        MAX(pi.processed_at) as last_inspection
                    FROM processed_inspections pi
                    LEFT JOIN inspection_defects id2 ON pi.id = id2.inspection_id
                    LEFT JOIN user_building_assignments uba ON pi.building_name = uba.building_name
                    WHERE pi.is_active = 1 AND (uba.username = ? OR ? = 'admin')
                    GROUP BY pi.building_name
                    ORDER BY pi.building_name
                ''', (username, user_role))
            else:
                # Others see buildings they've processed
                cursor.execute('''
                    SELECT DISTINCT 
                        pi.building_name,
                        COUNT(DISTINCT id2.unit_number) as total_units,
                        MAX(pi.processed_at) as last_inspection
                    FROM processed_inspections pi
                    LEFT JOIN inspection_defects id2 ON pi.id = id2.inspection_id
                    WHERE pi.is_active = 1 AND pi.processed_by = ?
                    GROUP BY pi.building_name
                    ORDER BY pi.building_name
                ''', (username,))
            
            result = cursor.fetchall()
            conn.close()
            return result
        except Exception as e:
            print(f"Error getting accessible buildings: {e}")
            return []
    
    def can_access_building(self, username: str, building_name: str) -> bool:
        """Check if user can access specific building"""
        accessible_buildings = self.get_accessible_buildings(username)
        return any(building[0] == building_name for building in accessible_buildings)
    
    def validate_session(self, username: str) -> bool:
        """Validate current session"""
        if not st.session_state.get("authenticated", False):
            return False
        
        if st.session_state.get("username") != username:
            return False
        
        # Check session timeout (8 hours)
        login_time = st.session_state.get("login_time", 0)
        if time.time() - login_time > 8 * 60 * 60:
            self.log_security_event(username, "Session timeout")
            return False
        
        return True


def requires_permission(permission: str):
    """Decorator to enforce permissions on functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get username from session state
            username = st.session_state.get("username")
            if not username:
                raise PermissionError("Authentication required")
            
            # Get permission manager
            perm_manager = get_permission_manager()
            
            # Check permission
            if not perm_manager.has_permission(username, permission):
                perm_manager.log_security_event(
                    username, 
                    f"Permission denied: {permission}", 
                    success=False
                )
                raise PermissionError(f"Permission denied: {permission}")
            
            # Log successful access
            perm_manager.log_user_action(username, f"Accessed: {func.__name__}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def requires_building_access(building_name_param: str):
    """Decorator to enforce building-level access"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            username = st.session_state.get("username")
            if not username:
                raise PermissionError("Authentication required")
            
            # Get building name from kwargs
            building_name = kwargs.get(building_name_param)
            if not building_name:
                raise PermissionError("Building name required")
            
            perm_manager = get_permission_manager()
            
            if not perm_manager.can_access_building(username, building_name):
                perm_manager.log_security_event(
                    username, 
                    f"Building access denied: {building_name}", 
                    success=False
                )
                raise PermissionError(f"Access denied to building: {building_name}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


@st.cache_resource
def get_permission_manager():
    """Get singleton permission manager instance"""
    return PermissionManager()


def validate_session_middleware():
    """Middleware to validate session on each request"""
    if not st.session_state.get("authenticated", False):
        st.error("Authentication required")
        st.stop()
    
    username = st.session_state.get("username")
    if not username:
        st.error("Invalid session")
        st.stop()
    
    perm_manager = get_permission_manager()
    if not perm_manager.validate_session(username):
        st.error("Session expired or invalid")
        # Clear session
        for key in ["authenticated", "username", "user_name", "user_email", "user_role", "login_time"]:
            if key in st.session_state:
                del st.session_state[key]
        st.stop()


def check_permission_ui(permission: str, error_message: str = None) -> bool:
    """UI helper to check permission and show error if denied"""
    username = st.session_state.get("username")
    if not username:
        st.error("Authentication required")
        return False
    
    perm_manager = get_permission_manager()
    if not perm_manager.has_permission(username, permission):
        error_msg = error_message or f"You don't have permission to {permission.replace('.', ' ')}"
        st.error(error_msg)
        perm_manager.log_security_event(username, f"UI permission denied: {permission}", success=False)
        return False
    
    return True


def show_permission_summary():
    """Show current user's permissions (for debugging/admin)"""
    username = st.session_state.get("username")
    if not username:
        return
    
    perm_manager = get_permission_manager()
    permissions = perm_manager.get_user_permissions(username)
    
    if permissions:
        with st.expander("Your Permissions", expanded=False):
            granted = [perm for perm, allowed in permissions.items() if allowed]
            denied = [perm for perm, allowed in permissions.items() if not allowed]
            
            if granted:
                st.success(f"**Granted ({len(granted)}):** " + ", ".join(granted))
            if denied:
                st.info(f"**Denied ({len(denied)}):** " + ", ".join(denied))