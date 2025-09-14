# admin_management.py
# Admin management functions for user, project, and permission management

import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from enhanced_admin_management import show_enhanced_admin_dashboard

class AdminManager:
    """Handles admin operations for user and project management"""
    
    def __init__(self, db_path="inspection_system.db"):
        self.db_path = db_path
    
    def _hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = "inspection_app_salt_2024"
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def get_all_users(self) -> List[Tuple]:
        """Get all users in the system"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT username, full_name, email, role, is_active, created_at, last_login
            FROM users
            ORDER BY role, username
        ''')
        
        users = cursor.fetchall()
        conn.close()
        return users
    
    def create_user(self, username: str, password: str, full_name: str, email: str, role: str, created_by: str) -> Tuple[bool, str]:
        """Create a new user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if username already exists
            cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                conn.close()
                return False, "Username already exists"
            
            password_hash = self._hash_password(password)
            
            cursor.execute('''
                INSERT INTO users (username, password_hash, full_name, email, role, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, password_hash, full_name, email, role, created_by))
            
            conn.commit()
            conn.close()
            return True, "User created successfully"
            
        except Exception as e:
            return False, f"Error creating user: {str(e)}"
    
    def update_user(self, username: str, full_name: str, email: str, role: str, is_active: bool) -> Tuple[bool, str]:
        """Update user information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users 
                SET full_name = ?, email = ?, role = ?, is_active = ?
                WHERE username = ?
            ''', (full_name, email, role, is_active, username))
            
            conn.commit()
            conn.close()
            return True, "User updated successfully"
            
        except Exception as e:
            return False, f"Error updating user: {str(e)}"
    
    def get_all_projects(self) -> List[Tuple]:
        """Get all projects with portfolio information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.id, p.name, p.description, p.status, p.manager_username, p.created_at,
                   po.name as portfolio_name, po.owner_username
            FROM projects p
            LEFT JOIN portfolios po ON p.portfolio_id = po.id
            ORDER BY po.name, p.name
        ''')
        
        projects = cursor.fetchall()
        conn.close()
        return projects
    
    def create_project(self, project_id: str, portfolio_id: str, name: str, description: str, manager_username: str) -> Tuple[bool, str]:
        """Create a new project"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if project ID already exists
            cursor.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
            if cursor.fetchone():
                conn.close()
                return False, "Project ID already exists"
            
            cursor.execute('''
                INSERT INTO projects (id, portfolio_id, name, description, manager_username)
                VALUES (?, ?, ?, ?, ?)
            ''', (project_id, portfolio_id, name, description, manager_username))
            
            conn.commit()
            conn.close()
            return True, "Project created successfully"
            
        except Exception as e:
            return False, f"Error creating project: {str(e)}"
    
    def get_all_buildings(self) -> List[Tuple]:
        """Get all buildings with project information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT b.id, b.name, b.address, b.total_units, b.building_type, b.created_at,
                   p.name as project_name, p.id as project_id
            FROM buildings b
            LEFT JOIN projects p ON b.project_id = p.id
            ORDER BY p.name, b.name
        ''')
        
        buildings = cursor.fetchall()
        conn.close()
        return buildings
    
    def create_building(self, building_id: str, project_id: str, name: str, address: str, total_units: int, building_type: str) -> Tuple[bool, str]:
        """Create a new building"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if building ID already exists
            cursor.execute("SELECT id FROM buildings WHERE id = ?", (building_id,))
            if cursor.fetchone():
                conn.close()
                return False, "Building ID already exists"
            
            cursor.execute('''
                INSERT INTO buildings (id, project_id, name, address, total_units, building_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (building_id, project_id, name, address, total_units, building_type))
            
            conn.commit()
            conn.close()
            return True, "Building created successfully"
            
        except Exception as e:
            return False, f"Error creating building: {str(e)}"
    
    def get_user_permissions(self, username: str) -> List[Tuple]:
        """Get all permissions for a specific user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT up.resource_type, up.resource_id, up.permission_level, up.granted_at, up.granted_by,
                   CASE 
                       WHEN up.resource_type = 'project' THEN p.name
                       WHEN up.resource_type = 'building' THEN b.name
                       WHEN up.resource_type = 'portfolio' THEN po.name
                       ELSE up.resource_id
                   END as resource_name
            FROM user_permissions up
            LEFT JOIN projects p ON up.resource_type = 'project' AND up.resource_id = p.id
            LEFT JOIN buildings b ON up.resource_type = 'building' AND up.resource_id = b.id
            LEFT JOIN portfolios po ON up.resource_type = 'portfolio' AND up.resource_id = po.id
            WHERE up.username = ?
            ORDER BY up.resource_type, resource_name
        ''', (username,))
        
        permissions = cursor.fetchall()
        conn.close()
        return permissions
    
    def grant_permission(self, username: str, resource_type: str, resource_id: str, permission_level: str, granted_by: str) -> Tuple[bool, str]:
        """Grant permission to a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_permissions 
                (username, resource_type, resource_id, permission_level, granted_by)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, resource_type, resource_id, permission_level, granted_by))
            
            conn.commit()
            conn.close()
            return True, "Permission granted successfully"
            
        except Exception as e:
            return False, f"Error granting permission: {str(e)}"
    
    def revoke_permission(self, username: str, resource_type: str, resource_id: str) -> Tuple[bool, str]:
        """Revoke permission from a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM user_permissions 
                WHERE username = ? AND resource_type = ? AND resource_id = ?
            ''', (username, resource_type, resource_id))
            
            conn.commit()
            conn.close()
            return True, "Permission revoked successfully"
            
        except Exception as e:
            return False, f"Error revoking permission: {str(e)}"
    
    def get_available_resources(self, resource_type: str) -> List[Tuple]:
        """Get available resources for permission assignment"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if resource_type == "project":
            cursor.execute("SELECT id, name FROM projects ORDER BY name")
        elif resource_type == "building":
            cursor.execute("SELECT id, name FROM buildings ORDER BY name")
        elif resource_type == "portfolio":
            cursor.execute("SELECT id, name FROM portfolios ORDER BY name")
        else:
            conn.close()
            return []
        
        resources = cursor.fetchall()
        conn.close()
        return resources

def show_admin_dashboard():
    """Main admin dashboard with navigation"""
    st.markdown("### System Administration Dashboard")
    
    # Navigation tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "User Management", 
        "Project Management", 
        "Building Management", 
        "Permission Management",
        "System Overview"
    ])
    
    admin_manager = AdminManager()
    
    with tab1:
        show_user_management(admin_manager)
    
    with tab2:
        show_project_management(admin_manager)
    
    with tab3:
        show_building_management(admin_manager)
    
    with tab4:
        show_permission_management(admin_manager)
    
    with tab5:
        show_system_overview(admin_manager)

def show_user_management(admin_manager):
    """User management interface"""
    st.markdown("#### User Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Current Users**")
        users = admin_manager.get_all_users()
        
        if users:
            users_df = pd.DataFrame(users, columns=[
                "Username", "Full Name", "Email", "Role", "Active", "Created", "Last Login"
            ])
            
            # Format the dataframe
            users_df["Active"] = users_df["Active"].map({1: "Yes", 0: "No"})
            users_df["Role"] = users_df["Role"].str.replace('_', ' ').str.title()
            
            st.dataframe(users_df, use_container_width=True)
        else:
            st.info("No users found")
    
    with col2:
        st.markdown("**Create New User**")
        
        with st.form("create_user_form"):
            username = st.text_input("Username", placeholder="e.g., john.smith")
            full_name = st.text_input("Full Name", placeholder="e.g., John Smith")
            email = st.text_input("Email", placeholder="e.g., john@company.com")
            password = st.text_input("Password", type="password", placeholder="Minimum 6 characters")
            role = st.selectbox("Role", [
                "property_developer", "project_manager", "inspector", "builder"
            ])
            
            if st.form_submit_button("Create User", type="primary"):
                if username and full_name and email and password:
                    if len(password) >= 6:
                        current_user = st.session_state.get("username", "admin")
                        success, message = admin_manager.create_user(
                            username, password, full_name, email, role, current_user
                        )
                        
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Password must be at least 6 characters")
                else:
                    st.error("Please fill all fields")

def show_project_management(admin_manager):
    """Project management interface"""
    st.markdown("#### Project Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Current Projects**")
        projects = admin_manager.get_all_projects()
        
        if projects:
            projects_df = pd.DataFrame(projects, columns=[
                "Project ID", "Name", "Description", "Status", "Manager", "Created", 
                "Portfolio", "Portfolio Owner"
            ])
            
            st.dataframe(projects_df, use_container_width=True)
        else:
            st.info("No projects found")
    
    with col2:
        st.markdown("**Create New Project**")
        
        with st.form("create_project_form"):
            project_id = st.text_input("Project ID", placeholder="e.g., project_downtown")
            portfolio_id = st.text_input("Portfolio ID", placeholder="e.g., portfolio_001", value="portfolio_001")
            project_name = st.text_input("Project Name", placeholder="e.g., Downtown Development")
            description = st.text_area("Description", placeholder="Project description...")
            
            # Get available managers (users with manager or admin role)
            users = admin_manager.get_all_users()
            managers = [user[0] for user in users if user[3] in ['project_manager', 'admin']]
            
            if managers:
                manager = st.selectbox("Project Manager", managers)
            else:
                st.warning("No project managers available")
                manager = None
            
            if st.form_submit_button("Create Project", type="primary"):
                if project_id and project_name and manager:
                    success, message = admin_manager.create_project(
                        project_id, portfolio_id, project_name, description, manager
                    )
                    
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("Please fill required fields")

def show_building_management(admin_manager):
    """Building management interface"""
    st.markdown("#### Building Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Current Buildings**")
        buildings = admin_manager.get_all_buildings()
        
        if buildings:
            buildings_df = pd.DataFrame(buildings, columns=[
                "Building ID", "Name", "Address", "Total Units", "Type", "Created", "Project", "Project ID"
            ])
            
            st.dataframe(buildings_df[["Project", "Name", "Address", "Total Units", "Type"]], use_container_width=True)
        else:
            st.info("No buildings found")
    
    with col2:
        st.markdown("**Create New Building**")
        
        with st.form("create_building_form"):
            building_id = st.text_input("Building ID", placeholder="e.g., building_tower_a")
            building_name = st.text_input("Building Name", placeholder="e.g., Tower A")
            address = st.text_area("Address", placeholder="Building address...")
            total_units = st.number_input("Total Units", min_value=1, value=100)
            building_type = st.selectbox("Building Type", [
                "Apartment", "Townhouse", "Mixed Use", "Commercial", "Other"
            ])
            
            # Get available projects
            projects = admin_manager.get_all_projects()
            project_options = [(p[0], p[1]) for p in projects]  # (id, name)
            
            if project_options:
                project_display = [f"{p[1]} ({p[0]})" for p in project_options]
                selected_project = st.selectbox("Project", project_display)
                project_id = project_options[project_display.index(selected_project)][0]
            else:
                st.warning("No projects available. Create a project first.")
                project_id = None
            
            if st.form_submit_button("Create Building", type="primary"):
                if building_id and building_name and address and project_id:
                    success, message = admin_manager.create_building(
                        building_id, project_id, building_name, address, total_units, building_type
                    )
                    
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("Please fill all required fields")

def show_permission_management(admin_manager):
    """Permission management interface"""
    st.markdown("#### Permission Management")
    
    # User selection
    users = admin_manager.get_all_users()
    user_options = [(user[0], f"{user[1]} ({user[0]})") for user in users]
    
    if user_options:
        selected_user_display = st.selectbox(
            "Select User to Manage Permissions", 
            [option[1] for option in user_options]
        )
        selected_username = user_options[[option[1] for option in user_options].index(selected_user_display)][0]
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"**Current Permissions for {selected_username}**")
            permissions = admin_manager.get_user_permissions(selected_username)
            
            if permissions:
                perm_df = pd.DataFrame(permissions, columns=[
                    "Resource Type", "Resource ID", "Permission Level", "Granted At", "Granted By", "Resource Name"
                ])
                
                # Display formatted permissions
                display_df = perm_df[["Resource Type", "Resource Name", "Permission Level", "Granted By"]].copy()
                display_df["Resource Type"] = display_df["Resource Type"].str.title()
                display_df["Permission Level"] = display_df["Permission Level"].str.title()
                
                st.dataframe(display_df, use_container_width=True)
                
                # Permission revocation
                st.markdown("**Revoke Permission**")
                if len(permissions) > 0:
                    perm_options = [f"{p[0]} - {p[5]} ({p[2]})" for p in permissions]
                    selected_perm = st.selectbox("Select Permission to Revoke", perm_options)
                    
                    if st.button("Revoke Permission", type="secondary"):
                        perm_index = perm_options.index(selected_perm)
                        resource_type = permissions[perm_index][0]
                        resource_id = permissions[perm_index][1]
                        
                        success, message = admin_manager.revoke_permission(
                            selected_username, resource_type, resource_id
                        )
                        
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
            else:
                st.info("No permissions assigned to this user")
        
        with col2:
            st.markdown("**Grant New Permission**")
            
            with st.form("grant_permission_form"):
                resource_type = st.selectbox("Resource Type", ["project", "building", "portfolio"])
                
                # Get available resources
                resources = admin_manager.get_available_resources(resource_type)
                
                if resources:
                    resource_options = [f"{r[1]} ({r[0]})" for r in resources]
                    selected_resource = st.selectbox("Resource", resource_options)
                    resource_id = resources[resource_options.index(selected_resource)][0]
                else:
                    st.warning(f"No {resource_type}s available")
                    resource_id = None
                
                permission_level = st.selectbox("Permission Level", ["read", "write", "admin"])
                
                if st.form_submit_button("Grant Permission", type="primary"):
                    if resource_id:
                        current_user = st.session_state.get("username", "admin")
                        success, message = admin_manager.grant_permission(
                            selected_username, resource_type, resource_id, permission_level, current_user
                        )
                        
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Please select a resource")
    
    else:
        st.warning("No users found in the system")

def show_system_overview(admin_manager):
    """System overview and statistics"""
    st.markdown("#### System Overview")
    
    # Get statistics
    users = admin_manager.get_all_users()
    projects = admin_manager.get_all_projects()
    buildings = admin_manager.get_all_buildings()
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Users", len(users))
    
    with col2:
        st.metric("Total Projects", len(projects))
    
    with col3:
        st.metric("Total Buildings", len(buildings))
    
    with col4:
        total_units = sum(building[3] for building in buildings if building[3])
        st.metric("Total Units", total_units)
    
    # User breakdown by role
    if users:
        st.markdown("**Users by Role**")
        role_counts = {}
        for user in users:
            role = user[3].replace('_', ' ').title()
            role_counts[role] = role_counts.get(role, 0) + 1
        
        role_df = pd.DataFrame(list(role_counts.items()), columns=["Role", "Count"])
        st.dataframe(role_df, use_container_width=True)
    
    # Recent activity
    st.markdown("**Recent Users**")
    if users:
        recent_users = sorted(users, key=lambda x: x[5] or '1900-01-01', reverse=True)[:5]
        recent_df = pd.DataFrame(recent_users, columns=[
            "Username", "Full Name", "Email", "Role", "Active", "Created", "Last Login"
        ])
        st.dataframe(recent_df[["Username", "Full Name", "Role", "Last Login"]], use_container_width=True)