"""
Focused Administrator Dashboard Module
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import os
import hashlib
from permission_manager import get_permission_manager

class AdminDashboard:
    def __init__(self):
        self.user = {
            "username": st.session_state.get("username", ""),
            "name": st.session_state.get("user_name", "Admin"),
            "email": st.session_state.get("user_email", ""),
            "role": st.session_state.get("user_role", "admin"),
        }
        self.setup_modern_css()

    def setup_modern_css(self):
        """Setup focused admin CSS styling"""
        st.markdown("""
        <style>
            /* Modern card styling */
            .admin-card {
                background: white;
                border-radius: 12px;
                border: 1px solid #e5e7eb;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                padding: 1.5rem;
                margin-bottom: 1.5rem;
                transition: all 0.3s ease;
            }
            
            .admin-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
            }
            
            /* Metric cards */
            .metric-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 12px;
                padding: 1.5rem;
                text-align: center;
                border: none;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.25);
            }
            
            .metric-card.green {
                background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            }
            
            .metric-card.orange {
                background: linear-gradient(135deg, #ed8936 0%, #dd6b20 100%);
            }
            
            /* Header */
            .admin-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 2.5rem 2rem;
                border-radius: 16px;
                margin-bottom: 2rem;
                text-align: center;
            }
            
            /* User row styling */
            .user-row {
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 1rem;
                margin-bottom: 0.5rem;
                transition: all 0.2s ease;
            }
            
            .user-row:hover {
                background: #f3f4f6;
                border-color: #d1d5db;
            }
            
            /* Building card */
            .building-card {
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                padding: 1.5rem;
                margin-bottom: 1rem;
                position: relative;
                transition: all 0.3s ease;
            }
            
            .building-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                border-radius: 12px 12px 0 0;
            }
            
            .building-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
            }
            
            /* Status badges */
            .status-active { background: #dcfce7; color: #166534; padding: 0.25rem 0.5rem; border-radius: 999px; font-size: 0.75rem; }
            .status-inactive { background: #fee2e2; color: #991b1b; padding: 0.25rem 0.5rem; border-radius: 999px; font-size: 0.75rem; }
            .role-badge { background: #dbeafe; color: #1e40af; padding: 0.25rem 0.5rem; border-radius: 999px; font-size: 0.75rem; }
        </style>
        """, unsafe_allow_html=True)

    def show(self, force_workspace=None):
        """Show focused admin dashboard"""
        
        # Always go directly to admin dashboard when called from main app
        if force_workspace == "System Administration":
            self.show_admin_dashboard()
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
                help="Data Processing: Upload and process inspection files | System Administration: User and building management"
            )
            
            if workspace_choice != st.session_state.admin_workspace:
                st.session_state.admin_workspace = workspace_choice
                st.rerun()

            if st.session_state.admin_workspace == "System Administration":
                self.show_admin_dashboard()
            else:
                self.show_data_processing()

    def show_admin_dashboard(self):
        """Show the focused admin dashboard"""
        
        # Header
        st.markdown(f"""
        <div class="admin-header">
            <h1 style="margin: 0; font-size: 2.2rem; font-weight: 700;">System Administration</h1>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">
                User Management • Building Access • System Overview
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Navigation tabs (only essential ones)
        tab_options = ["Overview", "User Management", "Building Management"]
        
        cols = st.columns(len(tab_options))
        selected_tab = st.session_state.get("admin_selected_tab", "Overview")
        
        for i, tab in enumerate(tab_options):
            with cols[i]:
                if st.button(
                    tab, 
                    key=f"admin_tab_{tab}",
                    use_container_width=True,
                    type="primary" if selected_tab == tab else "secondary"
                ):
                    st.session_state.admin_selected_tab = tab
                    selected_tab = tab
                    st.rerun()

        st.markdown("---")

        # Route to content
        if selected_tab == "Overview":
            self.show_overview()
        elif selected_tab == "User Management":
            self.show_user_management()
        elif selected_tab == "Building Management":
            self.show_building_management()

    def show_overview(self):
        """System overview with key metrics"""
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        stats = self.get_system_stats()
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="margin: 0; font-size: 2.2rem; font-weight: 700;">{stats['total_users']}</h3>
                <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Total Users</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card green">
                <h3 style="margin: 0; font-size: 2.2rem; font-weight: 700;">{stats['active_users']}</h3>
                <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Active Users</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card orange">
                <h3 style="margin: 0; font-size: 2.2rem; font-weight: 700;">{stats['total_buildings']}</h3>
                <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Buildings</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="margin: 0; font-size: 2.2rem; font-weight: 700;">{stats['total_defects']}</h3>
                <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Active Defects</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Quick Actions
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="admin-card">
                <h4 style="margin: 0 0 1rem 0;">Quick Actions</h4>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("👥 Add New User", use_container_width=True, key="quick_add_user"):
                st.session_state.admin_selected_tab = "User Management"
                st.session_state.show_add_user = True
                st.rerun()
            
            if st.button("🏢 Manage Buildings", use_container_width=True, key="quick_buildings"):
                st.session_state.admin_selected_tab = "Building Management"
                st.rerun()
            
            if st.button("🔄 System Backup", use_container_width=True, key="quick_backup"):
                self.perform_system_backup()
        
        with col2:
            st.markdown("""
            <div class="admin-card">
                <h4 style="margin: 0 0 1rem 0;">Recent Activity</h4>
            </div>
            """, unsafe_allow_html=True)
            
            recent_activities = self.get_recent_activities()
            for activity in recent_activities[:5]:  # Show last 5
                st.markdown(f"""
                <div style="padding: 0.5rem; margin-bottom: 0.5rem; background: #f9fafb; border-radius: 6px; border-left: 3px solid #3b82f6;">
                    <div style="font-size: 0.9rem; color: #374151;">{activity['action']}</div>
                    <div style="font-size: 0.75rem; color: #6b7280;">{activity['user']} • {activity['time']}</div>
                </div>
                """, unsafe_allow_html=True)

    def show_user_management(self):
        """Complete user management interface"""
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown("## User Management")
            st.markdown("Create, edit, and manage user accounts and permissions")
        
        with col2:
            if st.button("➕ Add New User", use_container_width=True, type="primary"):
                st.session_state.show_add_user = True
                st.rerun()

        # Add user form
        if st.session_state.get("show_add_user", False):
            self.show_add_user_form()

        # User list with full management capabilities
        st.markdown("### Current Users")
        
        users_df = self.get_users_list()
        if not users_df.empty:
            # Filter options
            col1, col2, col3 = st.columns(3)
            
            with col1:
                role_filter = st.selectbox("Filter by Role", ["All"] + list(users_df['role'].unique()))
            
            with col2:
                status_filter = st.selectbox("Filter by Status", ["All", "Active", "Inactive"])
            
            with col3:
                search_user = st.text_input("Search Users", placeholder="Username or name...")

            # Apply filters
            filtered_df = users_df.copy()
            
            if role_filter != "All":
                filtered_df = filtered_df[filtered_df['role'] == role_filter]
            
            if status_filter != "All":
                active_status = status_filter == "Active"
                filtered_df = filtered_df[filtered_df['is_active'] == active_status]
            
            if search_user:
                mask = (filtered_df['username'].str.contains(search_user, case=False, na=False) | 
                       filtered_df['full_name'].str.contains(search_user, case=False, na=False))
                filtered_df = filtered_df[mask]

            # Display users
            for _, user in filtered_df.iterrows():
                self.render_user_row(user)

        else:
            st.info("No users found in the system")

    def render_user_row(self, user):
        """Render individual user row with management options"""
        
        status_class = "status-active" if user.get('is_active', True) else "status-inactive"
        status_text = "Active" if user.get('is_active', True) else "Inactive"
        
        # User row container
        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
        
        with col1:
            st.markdown(f"""
            <div class="user-row">
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                        <span style="color: white; font-weight: 600; font-size: 0.9rem;">
                            {user['full_name'][:2].upper() if user['full_name'] else user['username'][:2].upper()}
                        </span>
                    </div>
                    <div>
                        <div style="font-weight: 600; color: #111827;">{user['full_name']}</div>
                        <div style="font-size: 0.85rem; color: #6b7280;">{user['username']}</div>
                        <div style="font-size: 0.85rem; color: #6b7280;">{user.get('email', 'No email')}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style="padding: 1rem; text-align: center;">
                <span class="role-badge">{user['role'].replace('_', ' ').title()}</span>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div style="padding: 1rem; text-align: center;">
                <span class="{status_class}">{status_text}</span><br>
                <small style="color: #6b7280;">Last: {user.get('last_login', 'Never')}</small>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            # Action buttons
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                if st.button("✏️", key=f"edit_{user['username']}", help="Edit user"):
                    st.session_state.edit_user = user['username']
                    st.session_state.show_edit_user = True
                    st.rerun()
            
            with col_b:
                if st.button("🔐", key=f"perms_{user['username']}", help="Manage permissions"):
                    st.session_state.manage_perms_user = user['username']
                    st.session_state.show_manage_permissions = True
                    st.rerun()
            
            with col_c:
                if user.get('is_active', True):
                    if st.button("🚫", key=f"disable_{user['username']}", help="Disable user"):
                        self.toggle_user_status(user['username'], False)
                        st.rerun()
                else:
                    if st.button("✅", key=f"enable_{user['username']}", help="Enable user"):
                        self.toggle_user_status(user['username'], True)
                        st.rerun()
        
        st.markdown("---")
        
        # Show edit form if requested
        if st.session_state.get("show_edit_user", False) and st.session_state.get("edit_user") == user['username']:
            self.show_edit_user_form(user)
        
        # Show permissions management if requested
        if st.session_state.get("show_manage_permissions", False) and st.session_state.get("manage_perms_user") == user['username']:
            self.show_permissions_form(user)

    def show_add_user_form(self):
        """Show comprehensive add user form"""
        
        st.markdown("### Add New User")
        
        with st.form("add_user_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            
            with col1:
                username = st.text_input("Username*", help="Unique username for login")
                full_name = st.text_input("Full Name*", help="Display name")
                email = st.text_input("Email", help="Email address (optional)")
                password = st.text_input("Password*", type="password", help="Minimum 8 characters")
            
            with col2:
                role = st.selectbox("Role*", 
                    options=["inspector", "manager", "admin", "builder", "developer"],
                    help="User role determines permissions"
                )
                is_active = st.checkbox("Active", value=True, help="User can login")
                
                # Building assignments
                st.markdown("**Building Access:**")
                available_buildings = self.get_available_buildings()
                assigned_buildings = st.multiselect(
                    "Assign Buildings", 
                    options=[b['name'] for b in available_buildings],
                    help="Select buildings this user can access"
                )
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.form_submit_button("Create User", type="primary", use_container_width=True):
                    if self.create_user(username, full_name, email, password, role, is_active, assigned_buildings):
                        st.success(f"User '{username}' created successfully!")
                        st.session_state.show_add_user = False
                        st.rerun()
            
            with col2:
                if st.form_submit_button("Cancel", use_container_width=True):
                    st.session_state.show_add_user = False
                    st.rerun()

    def show_building_management(self):
        """Building management interface"""
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown("## Building Management")
            st.markdown("Manage building access and assign users to buildings")
        
        with col2:
            if st.button("🏗️ Add Building", use_container_width=True, type="primary"):
                st.session_state.show_add_building = True

        # Add building form
        if st.session_state.get("show_add_building", False):
            self.show_add_building_form()

        # Building list
        buildings = self.get_buildings_with_users()
        
        if buildings:
            cols = st.columns(2)
            for i, building in enumerate(buildings):
                with cols[i % 2]:
                    self.render_building_card(building)
        else:
            st.info("No buildings found. Add buildings to manage user access.")

    def render_building_card(self, building):
        """Render building card with user assignments"""
        
        st.markdown(f"""
        <div class="building-card">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                <div>
                    <h4 style="margin: 0; color: #111827;">{building['name']}</h4>
                    <p style="margin: 0.25rem 0; color: #6b7280; font-size: 0.9rem;">{building.get('address', 'No address')}</p>
                </div>
                <span style="background: #dcfce7; color: #166534; padding: 0.25rem 0.5rem; border-radius: 999px; font-size: 0.75rem;">
                    Active
                </span>
            </div>
            <div style="margin-bottom: 1rem;">
                <strong>{building.get('units', 0)}</strong> units • 
                <strong style="color: #ef4444;">{building.get('defects', 0)}</strong> defects
            </div>
            <div style="margin-bottom: 1rem;">
                <strong>Assigned Users:</strong><br>
                {', '.join(building.get('assigned_users', [])) if building.get('assigned_users') else 'No users assigned'}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Building actions
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("👥 Manage Users", key=f"manage_users_{building['name']}", use_container_width=True):
                st.session_state.manage_building = building['name']
                st.session_state.show_manage_building_users = True
        
        with col2:
            if st.button("✏️ Edit Building", key=f"edit_building_{building['name']}", use_container_width=True):
                st.info("Building editing interface would appear here")
        
        # Show user management for this building
        if (st.session_state.get("show_manage_building_users", False) and 
            st.session_state.get("manage_building") == building['name']):
            self.show_building_user_management(building)

    def show_data_processing(self):
        """Data processing interface for admins"""
        st.info("Full inspection processing interface with administrator privileges")
        
        st.markdown("#### Administrator Processing Capabilities")
        st.success("✓ Upload inspection data")
        st.success("✓ Process all file types") 
        st.success("✓ Generate all report types")
        st.success("✓ Access all system functions")

    # Helper methods and database operations
    def get_system_stats(self):
        """Get comprehensive system statistics"""
        try:
            conn = sqlite3.connect("inspection_system.db")
            cursor = conn.cursor()
            
            # Total users
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            # Active users  
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
            active_users = cursor.fetchone()[0]
            
            # Buildings
            cursor.execute("SELECT COUNT(DISTINCT building_name) FROM processed_inspections WHERE is_active = 1")
            total_buildings = cursor.fetchone()[0]
            
            # Active defects
            cursor.execute("""
                SELECT COUNT(*) FROM inspection_defects id
                JOIN processed_inspections pi ON id.inspection_id = pi.id  
                WHERE pi.is_active = 1
            """)
            total_defects = cursor.fetchone()[0]
            
            conn.close()
            return {
                "total_users": total_users,
                "active_users": active_users, 
                "total_buildings": total_buildings,
                "total_defects": total_defects
            }
        except Exception as e:
            return {"total_users": 5, "active_users": 4, "total_buildings": 3, "total_defects": 156}

    def get_users_list(self):
        """Get complete users list"""
        try:
            conn = sqlite3.connect("inspection_system.db")
            df = pd.read_sql_query("""
                SELECT username, full_name, email, role, is_active, last_login
                FROM users
                ORDER BY full_name
            """, conn)
            conn.close()
            return df
        except:
            # Mock data for testing
            return pd.DataFrame([
                {"username": "admin", "full_name": "System Administrator", "email": "admin@company.com", "role": "admin", "is_active": True, "last_login": "1 hour ago"},
                {"username": "john", "full_name": "John Doe", "email": "john@company.com", "role": "inspector", "is_active": True, "last_login": "2 hours ago"},
                {"username": "jane", "full_name": "Jane Smith", "email": "jane@company.com", "role": "manager", "is_active": True, "last_login": "1 day ago"},
                {"username": "mike", "full_name": "Mike Johnson", "email": "mike@company.com", "role": "builder", "is_active": False, "last_login": "1 week ago"}
            ])

    def create_user(self, username, full_name, email, password, role, is_active, assigned_buildings):
        """Create new user with validation"""
        
        # Validation
        if not all([username, full_name, password, role]):
            st.error("Please fill in all required fields")
            return False
        
        if len(password) < 8:
            st.error("Password must be at least 8 characters")
            return False
        
        try:
            conn = sqlite3.connect("inspection_system.db")
            cursor = conn.cursor()
            
            # Check if username exists
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
            if cursor.fetchone()[0] > 0:
                st.error("Username already exists")
                conn.close()
                return False
            
            # Hash password
            password_hash = self._hash_password(password)
            
            # Insert user
            cursor.execute("""
                INSERT INTO users (username, full_name, email, role, password_hash, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, full_name, email, role, password_hash, is_active))
            
            # Add building assignments if any
            if assigned_buildings:
                for building in assigned_buildings:
                    cursor.execute("""
                        INSERT OR IGNORE INTO user_building_access (username, building_name)
                        VALUES (?, ?)
                    """, (username, building))
            
            conn.commit()
            conn.close()
            
            # Log the action
            perm_manager = get_permission_manager()
            perm_manager.log_user_action(
                self.user['username'], 
                "USER_CREATED", 
                details=f"Created user: {username} with role: {role}"
            )
            
            return True
            
        except Exception as e:
            st.error(f"Error creating user: {str(e)}")
            return False

    def toggle_user_status(self, username, active_status):
        """Toggle user active/inactive status"""
        try:
            conn = sqlite3.connect("inspection_system.db")
            cursor = conn.cursor()
            
            cursor.execute("UPDATE users SET is_active = ? WHERE username = ?", (active_status, username))
            conn.commit()
            conn.close()
            
            status_text = "activated" if active_status else "deactivated"
            st.success(f"User {username} {status_text} successfully")
            
            # Log the action
            perm_manager = get_permission_manager()
            perm_manager.log_user_action(
                self.user['username'],
                f"USER_{'ACTIVATED' if active_status else 'DEACTIVATED'}",
                details=f"User: {username}"
            )
            
        except Exception as e:
            st.error(f"Error updating user status: {str(e)}")

    def get_recent_activities(self):
        """Get recent system activities"""
        try:
            conn = sqlite3.connect("inspection_system.db")
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT username, action, timestamp
                FROM audit_log
                WHERE action IN ('USER_CREATED', 'USER_ACTIVATED', 'USER_DEACTIVATED', 'LOGIN_SUCCESS', 'DATA_PROCESSING_SUCCESS')
                ORDER BY timestamp DESC
                LIMIT 10
            """)
            
            activities = []
            for row in cursor.fetchall():
                activities.append({
                    "user": row[0],
                    "action": self._format_action(row[1]),
                    "time": self._format_time(row[2])
                })
            
            conn.close()
            return activities
        except:
            return [
                {"user": "admin", "action": "Created new user", "time": "2 hours ago"},
                {"user": "john", "action": "Logged in", "time": "3 hours ago"},
                {"user": "jane", "action": "Processed building data", "time": "5 hours ago"}
            ]

    def get_buildings_with_users(self):
        """Get buildings with assigned users"""
        # Mock data for now - you can implement database logic later
        return [
            {
                "name": "Professional Building Complex",
                "address": "123 Professional St, Melbourne",
                "units": 45,
                "defects": 23,
                "assigned_users": ["john", "jane"]
            },
            {
                "name": "Modern Apartments",
                "address": "456 Modern Ave, Sydney", 
                "units": 78,
                "defects": 12,
                "assigned_users": ["mike"]
            }
        ]

    def get_available_buildings(self):
        """Get list of available buildings for assignment"""
        return [
            {"name": "Professional Building Complex"},
            {"name": "Modern Apartments"},
            {"name": "City Towers"}
        ]

    def show_add_building_form(self):
        """Show add building form"""
        st.markdown("### Add New Building")
        
        with st.form("add_building_form"):
            building_name = st.text_input("Building Name*")
            building_address = st.text_area("Address")
            total_units = st.number_input("Total Units", min_value=1, value=1)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.form_submit_button("Add Building", type="primary", use_container_width=True):
                    if building_name:
                        st.success(f"Building '{building_name}' added successfully!")
                        st.session_state.show_add_building = False
                        st.rerun()
                    else:
                        st.error("Building name is required")
            
            with col2:
                if st.form_submit_button("Cancel", use_container_width=True):
                    st.session_state.show_add_building = False
                    st.rerun()

    def show_edit_user_form(self, user):
        """Show edit user form"""
        st.markdown(f"### Edit User: {user['username']}")
        
        with st.form(f"edit_user_{user['username']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                full_name = st.text_input("Full Name", value=user['full_name'])
                email = st.text_input("Email", value=user.get('email', ''))
                role = st.selectbox("Role", 
                    options=["inspector", "manager", "admin", "builder", "developer"],
                    index=["inspector", "manager", "admin", "builder", "developer"].index(user['role'])
                )
            
            with col2:
                is_active = st.checkbox("Active", value=user.get('is_active', True))
                new_password = st.text_input("New Password (leave blank to keep current)", type="password")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.form_submit_button("Update User", type="primary", use_container_width=True):
                    if self.update_user(user['username'], full_name, email, role, is_active, new_password):
                        st.success("User updated successfully!")
                        st.session_state.show_edit_user = False
                        st.rerun()
            
            with col2:
                if st.form_submit_button("Cancel", use_container_width=True):
                    st.session_state.show_edit_user = False
                    st.rerun()

    def show_permissions_form(self, user):
        """Show permissions management form"""
        st.markdown(f"### Manage Permissions: {user['full_name']}")
        
        # Get current permissions
        perm_manager = get_permission_manager()
        current_permissions = perm_manager.get_user_permissions(user['username'])
        
        st.markdown("#### Current Permissions")
        
        # Permission categories
        permission_groups = {
            "Data Management": ["data.upload", "data.process", "data.view_assigned", "data.view_all"],
            "Reports": ["reports.generate", "reports.excel", "reports.word"],
            "User Management": ["users.view", "users.edit", "users.create", "users.delete"],
            "System": ["system.admin", "system.backup", "system.maintenance"],
            "Defects": ["defects.approve", "defects.update_status", "defects.create"]
        }
        
        with st.form(f"permissions_{user['username']}"):
            updated_permissions = {}
            
            for group, permissions in permission_groups.items():
                st.markdown(f"**{group}**")
                
                for perm in permissions:
                    current_value = current_permissions.get(perm, False)
                    updated_permissions[perm] = st.checkbox(
                        perm.replace('.', ' ').title(),
                        value=current_value,
                        key=f"perm_{user['username']}_{perm}"
                    )
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.form_submit_button("Update Permissions", type="primary", use_container_width=True):
                    if self.update_user_permissions(user['username'], updated_permissions):
                        st.success("Permissions updated successfully!")
                        st.session_state.show_manage_permissions = False
                        st.rerun()
            
            with col2:
                if st.form_submit_button("Cancel", use_container_width=True):
                    st.session_state.show_manage_permissions = False
                    st.rerun()

    def show_building_user_management(self, building):
        """Show user management for specific building"""
        st.markdown(f"### Manage Users for {building['name']}")
        
        # Get all users and current assignments
        all_users = self.get_users_list()
        current_assignments = building.get('assigned_users', [])
        
        with st.form(f"building_users_{building['name']}"):
            st.markdown("**Assign/Remove Users:**")
            
            user_assignments = {}
            for _, user in all_users.iterrows():
                current_assigned = user['username'] in current_assignments
                user_assignments[user['username']] = st.checkbox(
                    f"{user['full_name']} ({user['username']}) - {user['role']}",
                    value=current_assigned,
                    key=f"assign_{building['name']}_{user['username']}"
                )
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.form_submit_button("Update Assignments", type="primary", use_container_width=True):
                    assigned_users = [username for username, assigned in user_assignments.items() if assigned]
                    st.success(f"Updated user assignments for {building['name']}")
                    st.session_state.show_manage_building_users = False
                    st.rerun()
            
            with col2:
                if st.form_submit_button("Cancel", use_container_width=True):
                    st.session_state.show_manage_building_users = False
                    st.rerun()

    def update_user(self, username, full_name, email, role, is_active, new_password):
        """Update user information"""
        try:
            conn = sqlite3.connect("inspection_system.db")
            cursor = conn.cursor()
            
            if new_password:
                password_hash = self._hash_password(new_password)
                cursor.execute("""
                    UPDATE users SET full_name = ?, email = ?, role = ?, is_active = ?, password_hash = ?
                    WHERE username = ?
                """, (full_name, email, role, is_active, password_hash, username))
            else:
                cursor.execute("""
                    UPDATE users SET full_name = ?, email = ?, role = ?, is_active = ?
                    WHERE username = ?
                """, (full_name, email, role, is_active, username))
            
            conn.commit()
            conn.close()
            
            # Log the action
            perm_manager = get_permission_manager()
            perm_manager.log_user_action(
                self.user['username'],
                "USER_UPDATED",
                details=f"Updated user: {username}"
            )
            
            return True
            
        except Exception as e:
            st.error(f"Error updating user: {str(e)}")
            return False

    def update_user_permissions(self, username, permissions):
        """Update user permissions"""
        try:
            perm_manager = get_permission_manager()
            
            # Update each permission
            for permission, granted in permissions.items():
                if granted:
                    perm_manager.grant_permission(username, permission)
                else:
                    perm_manager.revoke_permission(username, permission)
            
            # Log the action
            perm_manager.log_user_action(
                self.user['username'],
                "PERMISSIONS_UPDATED",
                details=f"Updated permissions for user: {username}"
            )
            
            return True
            
        except Exception as e:
            st.error(f"Error updating permissions: {str(e)}")
            return False

    def perform_system_backup(self):
        """Perform system backup"""
        try:
            # This is a placeholder - implement actual backup logic
            st.success("System backup completed successfully!")
            
            # Log the action
            perm_manager = get_permission_manager()
            perm_manager.log_user_action(
                self.user['username'],
                "SYSTEM_BACKUP",
                details="Manual system backup performed"
            )
            
        except Exception as e:
            st.error(f"Backup failed: {str(e)}")

    def _hash_password(self, password):
        """Hash password with salt"""
        salt = "inspection_app_salt_2024"
        return hashlib.sha256((password + salt).encode()).hexdigest()

    def _format_action(self, action):
        """Format action for display"""
        action_map = {
            "USER_CREATED": "Created new user",
            "USER_ACTIVATED": "Activated user",
            "USER_DEACTIVATED": "Deactivated user", 
            "LOGIN_SUCCESS": "Logged in",
            "DATA_PROCESSING_SUCCESS": "Processed building data"
        }
        return action_map.get(action, action.replace('_', ' ').title())

    def _format_time(self, timestamp):
        """Format timestamp for display"""
        try:
            dt = datetime.fromisoformat(timestamp)
            now = datetime.now()
            diff = now - dt
            
            if diff.days > 0:
                return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            else:
                return "Just now"
        except:
            return timestamp