"""
Complete Secure UI Helper Components
"""
import streamlit as st
import pandas as pd
import sqlite3
from typing import Optional, Callable, Any, List, Dict
from permission_manager import get_permission_manager


class SecureUIComponents:
    """Secure UI components that check permissions before rendering"""
    
    def __init__(self):
        self.perm_manager = get_permission_manager()
        self.username = st.session_state.get("username")
    
    def secure_button(self, label: str, permission: str, 
                     key: str = None, help: str = None,
                     type: str = "secondary", use_container_width: bool = False,
                     disabled_message: str = None) -> bool:
        """Secure button that only renders if user has permission"""
        if not self.username:
            st.error("Authentication required")
            return False
        
        if not self.perm_manager.has_permission(self.username, permission):
            error_msg = disabled_message or f"You need '{permission}' permission to {label.lower()}"
            st.error(error_msg)
            return False
        
        return st.button(
            label, key=key, help=help, type=type, 
            use_container_width=use_container_width
        )
    
    def secure_file_uploader(self, label: str, permission: str,
                           type: list = None, key: str = None,
                           help: str = None, disabled_message: str = None):
        """Secure file uploader that checks upload permissions"""
        if not self.username:
            st.error("Authentication required")
            return None
        
        if not self.perm_manager.has_permission(self.username, permission):
            error_msg = disabled_message or f"You need '{permission}' permission to upload files"
            st.error(error_msg)
            return None
        
        return st.file_uploader(label, type=type, key=key, help=help)
    
    def secure_download_button(self, label: str, data: Any, file_name: str,
                             permission: str, mime: str = None,
                             key: str = None, help: str = None,
                             use_container_width: bool = False,
                             disabled_message: str = None) -> bool:
        """Secure download button with permission check"""
        if not self.username:
            st.error("Authentication required")
            return False
        
        if not self.perm_manager.has_permission(self.username, permission):
            error_msg = disabled_message or f"You need '{permission}' permission to download reports"
            st.error(error_msg)
            return False
        
        # Log download attempt
        self.perm_manager.log_user_action(
            self.username, f"DOWNLOAD_ATTEMPT: {file_name}"
        )
        
        return st.download_button(
            label, data=data, file_name=file_name, mime=mime,
            key=key, help=help, use_container_width=use_container_width
        )
    
    def secure_dataframe(self, data, permission: str,
                        use_container_width: bool = True,
                        height: int = None, hide_index: bool = True,
                        disabled_message: str = None):
        """Secure dataframe display with permission check"""
        if not self.username:
            st.error("Authentication required")
            return
        
        if not self.perm_manager.has_permission(self.username, permission):
            error_msg = disabled_message or f"You need '{permission}' permission to view this data"
            st.error(error_msg)
            return
        
        # Log data access
        self.perm_manager.log_user_action(
            self.username, f"DATA_VIEW: {type(data).__name__}"
        )
        
        st.dataframe(
            data, use_container_width=use_container_width,
            height=height, hide_index=hide_index
        )
    
    def secure_metric(self, label: str, value: Any, permission: str,
                     delta: str = None, delta_color: str = "normal",
                     help: str = None, disabled_message: str = None):
        """Secure metric display with permission check"""
        if not self.username:
            st.error("Authentication required")
            return
        
        if not self.perm_manager.has_permission(self.username, permission):
            error_msg = disabled_message or f"You need '{permission}' permission to view metrics"
            st.error(error_msg)
            return
        
        st.metric(label, value, delta=delta, delta_color=delta_color, help=help)
    
    def secure_tabs(self, tab_configs: list, default_permission: str = None):
        """Create secure tabs with permission checks"""
        if not self.username:
            st.error("Authentication required")
            return
        
        # Filter tabs based on permissions
        allowed_tabs = []
        tab_functions = []
        
        for config in tab_configs:
            required_permission = config.get('permission', default_permission)
            if not required_permission or self.perm_manager.has_permission(self.username, required_permission):
                allowed_tabs.append(config['name'])
                tab_functions.append(config['content_func'])
        
        if not allowed_tabs:
            st.error("You don't have permission to view any of these tabs")
            return
        
        # Create tabs
        tabs = st.tabs(allowed_tabs)
        
        # Render tab content
        for tab, content_func in zip(tabs, tab_functions):
            with tab:
                if callable(content_func):
                    content_func()
                else:
                    st.write(content_func)


def create_secure_ui():
    """Factory function to create secure UI components"""
    return SecureUIComponents()


def secure_section_header(title: str, permission: str, 
                         subtitle: str = None, show_permission_info: bool = False):
    """Create a secure section header with permission check"""
    username = st.session_state.get("username")
    
    if not username:
        st.error("Authentication required")
        return False
    
    perm_manager = get_permission_manager()
    
    if not perm_manager.has_permission(username, permission):
        st.error(f"Access denied: You need '{permission}' permission to view this section")
        
        if show_permission_info:
            with st.expander("Why can't I access this?"):
                st.info(f"This section requires the '{permission}' permission.")
                st.info("Contact your system administrator to request access.")
        
        return False
    
    # Show the header with security indicator
    st.markdown(f"""
    <div class="step-container">
        <div class="step-header">{title}</div>
        {f'<p style="color: #666; margin-top: 0.5rem;">{subtitle}</p>' if subtitle else ''}
        <p style="color: #4caf50; font-size: 0.8em; margin-top: 0.5rem;">🔒 Access Authorized</p>
    </div>
    """, unsafe_allow_html=True)
    
    return True


def show_permissions_debug():
    """Debug helper to show current user permissions"""
    username = st.session_state.get("username")
    if not username:
        st.error("Not authenticated")
        return
    
    perm_manager = get_permission_manager()
    permissions = perm_manager.get_user_permissions(username)
    
    st.markdown("#### Current User Permissions")
    col1, col2 = st.columns(2)
    
    granted = [perm for perm, allowed in permissions.items() if allowed]
    denied = [perm for perm, allowed in permissions.items() if not allowed]
    
    with col1:
        st.success(f"**Granted ({len(granted)}):**")
        for perm in granted:
            st.write(f"✅ {perm}")
    
    with col2:
        st.info(f"**Denied ({len(denied)}):**")
        for perm in denied:
            st.write(f"❌ {perm}")


def audit_trail_viewer(username: str = None, limit: int = 50):
    """View audit trail (admin only)"""
    current_username = st.session_state.get("username")
    if not current_username:
        st.error("Authentication required")
        return
    
    perm_manager = get_permission_manager()
    
    if not perm_manager.has_permission(current_username, "system.admin"):
        st.error("Admin permission required to view audit logs")
        return
    
    try:
        conn = sqlite3.connect("inspection_system.db")
        cursor = conn.cursor()
        
        if username:
            cursor.execute('''
                SELECT username, action, resource, success, timestamp, details
                FROM audit_log 
                WHERE username = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (username, limit))
        else:
            cursor.execute('''
                SELECT username, action, resource, success, timestamp, details
                FROM audit_log 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        if results:
            df = pd.DataFrame(results, columns=[
                'Username', 'Action', 'Resource', 'Success', 'Timestamp', 'Details'
            ])
            
            # Enhanced filtering
            col1, col2, col3 = st.columns(3)
            with col1:
                filter_user = st.selectbox("Filter by User:", ["All"] + list(df['Username'].unique()))
            with col2:
                filter_action = st.selectbox("Filter by Action:", ["All"] + list(df['Action'].unique()))
            with col3:
                show_failures_only = st.checkbox("Show Failures Only")
            
            # Apply filters
            filtered_df = df.copy()
            if filter_user != "All":
                filtered_df = filtered_df[filtered_df['Username'] == filter_user]
            if filter_action != "All":
                filtered_df = filtered_df[filtered_df['Action'] == filter_action]
            if show_failures_only:
                filtered_df = filtered_df[filtered_df['Success'] == False]
            
            # Color code by success/failure
            def highlight_failures(row):
                if not row['Success']:
                    return ['background-color: #ffebee'] * len(row)
                elif 'SECURITY' in str(row['Action']):
                    return ['background-color: #fff3e0'] * len(row)
                return [''] * len(row)
            
            st.dataframe(
                filtered_df.style.apply(highlight_failures, axis=1), 
                use_container_width=True,
                height=400
            )
            
            # Summary stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Events", len(filtered_df))
            with col2:
                failures = len(filtered_df[filtered_df['Success'] == False])
                st.metric("Failures", failures)
            with col3:
                security_events = len(filtered_df[filtered_df['Action'].str.contains('SECURITY', na=False)])
                st.metric("Security Events", security_events)
        else:
            st.info("No audit log entries found")
            
    except Exception as e:
        st.error(f"Error loading audit logs: {e}")


def show_user_activity_summary():
    """Show current user's recent activity"""
    username = st.session_state.get("username")
    if not username:
        return
    
    with st.expander("My Recent Activity", expanded=False):
        try:
            conn = sqlite3.connect("inspection_system.db")
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT action, resource, timestamp, success
                FROM audit_log 
                WHERE username = ?
                ORDER BY timestamp DESC 
                LIMIT 10
            ''', (username,))
            
            results = cursor.fetchall()
            conn.close()
            
            if results:
                for action, resource, timestamp, success in results:
                    status_icon = "✅" if success else "❌"
                    resource_text = f" ({resource})" if resource else ""
                    st.caption(f"{status_icon} {action}{resource_text} - {timestamp}")
            else:
                st.info("No recent activity")
        
        except Exception as e:
            st.caption(f"Activity log unavailable: {e}")


def show_building_access_control():
    """Show building access control interface (admin only)"""
    username = st.session_state.get("username")
    perm_manager = get_permission_manager()
    
    if not perm_manager.has_permission(username, "system.admin"):
        st.error("Admin permission required")
        return
    
    st.markdown("### Building Access Control")
    
    try:
        conn = sqlite3.connect("inspection_system.db")
        cursor = conn.cursor()
        
        # Get all users and buildings
        cursor.execute("SELECT username, full_name, role FROM users WHERE is_active = 1")
        users = cursor.fetchall()
        
        cursor.execute("SELECT DISTINCT building_name FROM processed_inspections WHERE is_active = 1")
        buildings = cursor.fetchall()
        
        # Show current assignments
        cursor.execute('''
            SELECT uba.username, u.full_name, uba.building_name, uba.assigned_at
            FROM user_building_assignments uba
            JOIN users u ON uba.username = u.username
            WHERE uba.is_active = 1
            ORDER BY uba.building_name, u.full_name
        ''')
        assignments = cursor.fetchall()
        
        conn.close()
        
        if assignments:
            st.markdown("#### Current Building Assignments")
            df_assignments = pd.DataFrame(assignments, columns=[
                'Username', 'Full Name', 'Building', 'Assigned Date'
            ])
            st.dataframe(df_assignments, use_container_width=True)
        
        # Add new assignment form
        st.markdown("#### Add Building Assignment")
        with st.form("add_assignment"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                user_options = [f"{user[0]} ({user[1]})" for user in users]
                selected_user = st.selectbox("Select User:", user_options)
            
            with col2:
                building_options = [building[0] for building in buildings]
                selected_building = st.selectbox("Select Building:", building_options)
            
            with col3:
                if st.form_submit_button("Add Assignment", use_container_width=True):
                    if selected_user and selected_building:
                        try:
                            actual_username = selected_user.split(" (")[0]
                            
                            conn = sqlite3.connect("inspection_system.db")
                            cursor = conn.cursor()
                            
                            cursor.execute('''
                                INSERT OR REPLACE INTO user_building_assignments 
                                (username, building_name, assigned_by)
                                VALUES (?, ?, ?)
                            ''', (actual_username, selected_building, username))
                            
                            conn.commit()
                            conn.close()
                            
                            perm_manager.log_user_action(
                                username, "BUILDING_ASSIGNMENT_ADDED",
                                resource=f"{actual_username} -> {selected_building}"
                            )
                            
                            st.success(f"Assignment added: {actual_username} -> {selected_building}")
                            st.rerun()
                        
                        except Exception as e:
                            st.error(f"Error adding assignment: {e}")
    
    except Exception as e:
        st.error(f"Error loading building access data: {e}")


def show_security_dashboard():
    """Show security dashboard for admins"""
    username = st.session_state.get("username")
    perm_manager = get_permission_manager()
    
    if not perm_manager.has_permission(username, "system.admin"):
        st.error("Admin permission required")
        return
    
    st.markdown("### Security Dashboard")
    
    try:
        conn = sqlite3.connect("inspection_system.db")
        cursor = conn.cursor()
        
        # Security metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
            active_users = cursor.fetchone()[0]
            st.metric("Active Users", active_users)
        
        with col2:
            cursor.execute('''
                SELECT COUNT(*) FROM audit_log 
                WHERE timestamp > datetime('now', '-24 hour')
            ''')
            daily_activity = cursor.fetchone()[0]
            st.metric("24h Activity", daily_activity)
        
        with col3:
            cursor.execute('''
                SELECT COUNT(*) FROM audit_log 
                WHERE action LIKE '%FAILED%' 
                AND timestamp > datetime('now', '-24 hour')
            ''')
            daily_failures = cursor.fetchone()[0]
            if daily_failures > 10:
                st.error(f"Failures: {daily_failures}")
            else:
                st.metric("24h Failures", daily_failures)
        
        with col4:
            cursor.execute('''
                SELECT COUNT(*) FROM audit_log 
                WHERE action LIKE '%SECURITY%' 
                AND timestamp > datetime('now', '-24 hour')
            ''')
            security_events = cursor.fetchone()[0]
            if security_events > 5:
                st.warning(f"Security: {security_events}")
            else:
                st.metric("24h Security", security_events)
        
        conn.close()
        
        # Recent security events
        st.markdown("#### Recent Security Events")
        cursor = sqlite3.connect("inspection_system.db").cursor()
        cursor.execute('''
            SELECT username, action, timestamp, details, success
            FROM audit_log 
            WHERE action LIKE '%SECURITY%' OR action LIKE '%LOGIN%' OR success = 0
            ORDER BY timestamp DESC 
            LIMIT 20
        ''')
        
        security_events = cursor.fetchall()
        
        if security_events:
            df_security = pd.DataFrame(security_events, columns=[
                'Username', 'Action', 'Timestamp', 'Details', 'Success'
            ])
            
            # Highlight failures in red
            def highlight_security(row):
                if not row['Success']:
                    return ['background-color: #ffebee'] * len(row)
                return [''] * len(row)
            
            st.dataframe(
                df_security.style.apply(highlight_security, axis=1),
                use_container_width=True
            )
        else:
            st.success("No recent security events")
    
    except Exception as e:
        st.error(f"Error loading security dashboard: {e}")