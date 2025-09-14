# Enhanced admin_management.py with full CRUD operations
# Complete user, project, and building management with permissions

import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime
from typing import List, Dict, Tuple, Optional

class EnhancedAdminManager:
    """Enhanced admin operations with full CRUD capabilities"""
    
    def __init__(self, db_path="inspection_system.db"):
        self.db_path = db_path
    
    def _hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = "inspection_app_salt_2024"
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    # =================== USER MANAGEMENT ===================
    
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
    
    def delete_user(self, username: str) -> Tuple[bool, str]:
        """Delete a user (soft delete by deactivating)"""
        try:
            if username == 'admin':
                return False, "Cannot delete admin user"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Soft delete by deactivating
            cursor.execute('UPDATE users SET is_active = 0 WHERE username = ?', (username,))
            
            # Also revoke all permissions
            cursor.execute('DELETE FROM user_permissions WHERE username = ?', (username,))
            
            conn.commit()
            conn.close()
            return True, f"User {username} deactivated successfully"
            
        except Exception as e:
            return False, f"Error deleting user: {str(e)}"
    
    def reset_user_password(self, username: str, new_password: str) -> Tuple[bool, str]:
        """Reset user password"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            password_hash = self._hash_password(new_password)
            cursor.execute('UPDATE users SET password_hash = ? WHERE username = ?', (password_hash, username))
            
            conn.commit()
            conn.close()
            return True, f"Password reset for {username}"
            
        except Exception as e:
            return False, f"Error resetting password: {str(e)}"
    
    # =================== PROJECT MANAGEMENT ===================
    
    def get_all_projects(self) -> List[Tuple]:
        """Get all projects with portfolio information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.id, p.name, p.description, p.status, p.manager_username, p.created_at,
                   COALESCE(po.name, 'Default Portfolio') as portfolio_name, 
                   COALESCE(po.owner_username, 'admin') as portfolio_owner
            FROM projects p
            LEFT JOIN portfolios po ON p.portfolio_id = po.id
            ORDER BY portfolio_name, p.name
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
    
    def update_project(self, project_id: str, name: str, description: str, status: str, manager_username: str) -> Tuple[bool, str]:
        """Update project information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE projects 
                SET name = ?, description = ?, status = ?, manager_username = ?
                WHERE id = ?
            ''', (name, description, status, manager_username, project_id))
            
            conn.commit()
            conn.close()
            return True, "Project updated successfully"
            
        except Exception as e:
            return False, f"Error updating project: {str(e)}"
    
    def delete_project(self, project_id: str) -> Tuple[bool, str]:
        """Delete a project and its associated data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check for associated buildings
            cursor.execute('SELECT COUNT(*) FROM buildings WHERE project_id = ?', (project_id,))
            building_count = cursor.fetchone()[0]
            
            if building_count > 0:
                conn.close()
                return False, f"Cannot delete project with {building_count} buildings. Delete buildings first."
            
            # Delete project permissions
            cursor.execute('DELETE FROM user_permissions WHERE resource_type = ? AND resource_id = ?', ('project', project_id))
            
            # Delete project
            cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
            
            conn.commit()
            conn.close()
            return True, "Project deleted successfully"
            
        except Exception as e:
            return False, f"Error deleting project: {str(e)}"
    
    # =================== BUILDING MANAGEMENT ===================
    
    def get_all_buildings(self) -> List[Tuple]:
        """Get all buildings with project information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT b.id, b.name, b.address, b.total_units, b.building_type, b.created_at,
                   COALESCE(p.name, 'No Project') as project_name, 
                   COALESCE(p.id, '') as project_id
            FROM buildings b
            LEFT JOIN projects p ON b.project_id = p.id
            ORDER BY project_name, b.name
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
    
    def update_building(self, building_id: str, name: str, address: str, total_units: int, building_type: str) -> Tuple[bool, str]:
        """Update building information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE buildings 
                SET name = ?, address = ?, total_units = ?, building_type = ?
                WHERE id = ?
            ''', (name, address, total_units, building_type, building_id))
            
            conn.commit()
            conn.close()
            return True, "Building updated successfully"
            
        except Exception as e:
            return False, f"Error updating building: {str(e)}"
    
    def delete_building(self, building_id: str) -> Tuple[bool, str]:
        """Delete a building and its associated data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check for associated inspections
            cursor.execute('SELECT COUNT(*) FROM processed_inspections WHERE building_id = ?', (building_id,))
            inspection_count = cursor.fetchone()[0]
            
            if inspection_count > 0:
                # Soft delete - keep data but mark as inactive
                cursor.execute('DELETE FROM user_permissions WHERE resource_type = ? AND resource_id = ?', ('building', building_id))
                cursor.execute('UPDATE processed_inspections SET is_active = 0 WHERE building_id = ?', (building_id,))
                message = f"Building marked as inactive (had {inspection_count} inspections)"
            else:
                # Hard delete if no inspections
                cursor.execute('DELETE FROM user_permissions WHERE resource_type = ? AND resource_id = ?', ('building', building_id))
                cursor.execute('DELETE FROM buildings WHERE id = ?', (building_id,))
                message = "Building deleted successfully"
            
            conn.commit()
            conn.close()
            return True, message
            
        except Exception as e:
            return False, f"Error deleting building: {str(e)}"
    
    # =================== PERMISSION MANAGEMENT ===================
    
    def get_user_permissions(self, username: str) -> List[Tuple]:
        """Get all permissions for a specific user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT up.resource_type, up.resource_id, up.permission_level, up.granted_at, up.granted_by,
                   CASE 
                       WHEN up.resource_type = 'project' THEN COALESCE(p.name, up.resource_id)
                       WHEN up.resource_type = 'building' THEN COALESCE(b.name, up.resource_id)
                       WHEN up.resource_type = 'portfolio' THEN COALESCE(po.name, up.resource_id)
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
        
        try:
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
        except Exception as e:
            conn.close()
            return []

def show_enhanced_admin_dashboard():
    """Enhanced admin dashboard with full CRUD operations"""
    st.markdown("### Enhanced System Administration")
    
    # Navigation tabs with session state support
    if 'admin_tab' not in st.session_state:
        st.session_state.admin_tab = "User Management"
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "User Management", 
        "Project Management", 
        "Building Management", 
        "Permission Management",
        "System Overview"
    ])
    
    admin_manager = EnhancedAdminManager()
    
    # Handle tab selection from sidebar
    selected_tab = st.session_state.get('admin_tab', 'User Management')
    
    with tab1:
        if selected_tab == "User Management" or not selected_tab:
            show_enhanced_user_management(admin_manager)
        else:
            show_enhanced_user_management(admin_manager)
    
    with tab2:
        if selected_tab == "Project Management":
            show_enhanced_project_management(admin_manager)
        else:
            show_enhanced_project_management(admin_manager)
    
    with tab3:
        if selected_tab == "Building Management":
            show_enhanced_building_management(admin_manager)
        else:
            show_enhanced_building_management(admin_manager)
    
    with tab4:
        if selected_tab == "Permission Management":
            show_enhanced_permission_management(admin_manager)
        else:
            show_enhanced_permission_management(admin_manager)
    
    with tab5:
        if selected_tab == "System Overview":
            show_system_overview(admin_manager)
        else:
            show_system_overview(admin_manager)

def show_enhanced_user_management(admin_manager):
    """Enhanced user management with full CRUD"""
    st.markdown("#### Complete User Management")
    
    # User list with actions
    users = admin_manager.get_all_users()
    
    if users:
        st.markdown("**Current Users**")
        users_df = pd.DataFrame(users, columns=[
            "Username", "Full Name", "Email", "Role", "Active", "Created", "Last Login"
        ])
        users_df["Active"] = users_df["Active"].map({1: "Active", 0: "Inactive"})
        users_df["Role"] = users_df["Role"].str.replace('_', ' ').str.title()
        
        # Select user for editing/deleting
        col1, col2 = st.columns([3, 1])
        with col1:
            st.dataframe(users_df, use_container_width=True)
        
        with col2:
            st.markdown("**User Actions**")
            selected_user = st.selectbox("Select User:", [u[0] for u in users])
            
            if st.button("Edit User", use_container_width=True):
                st.session_state.edit_user = selected_user
            
            if st.button("Reset Password", use_container_width=True):
                st.session_state.reset_password_user = selected_user
            
            if selected_user != 'admin':
                if st.button("Delete User", use_container_width=True, type="secondary"):
                    success, message = admin_manager.delete_user(selected_user)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
        
        # Edit user form
        if st.session_state.get("edit_user"):
            user_to_edit = st.session_state.edit_user
            user_data = next((u for u in users if u[0] == user_to_edit), None)
            
            if user_data:
                st.markdown(f"**Editing User: {user_to_edit}**")
                with st.form("edit_user_form"):
                    full_name = st.text_input("Full Name", value=user_data[1])
                    email = st.text_input("Email", value=user_data[2])
                    role = st.selectbox("Role", [
                        "admin", "property_developer", "project_manager", "inspector", "builder"
                    ], index=["admin", "property_developer", "project_manager", "inspector", "builder"].index(user_data[3]))
                    is_active = st.checkbox("Active", value=bool(user_data[4]))
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Update User", type="primary"):
                            success, message = admin_manager.update_user(user_to_edit, full_name, email, role, is_active)
                            if success:
                                st.success(message)
                                del st.session_state.edit_user
                                st.rerun()
                            else:
                                st.error(message)
                    with col2:
                        if st.form_submit_button("Cancel"):
                            del st.session_state.edit_user
                            st.rerun()
        
        # Reset password form
        if st.session_state.get("reset_password_user"):
            user_to_reset = st.session_state.reset_password_user
            st.markdown(f"**Reset Password for: {user_to_reset}**")
            with st.form("reset_password_form"):
                new_password = st.text_input("New Password", type="password", placeholder="Enter new password")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm new password")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Reset Password", type="primary"):
                        if new_password == confirm_password and len(new_password) >= 6:
                            success, message = admin_manager.reset_user_password(user_to_reset, new_password)
                            if success:
                                st.success(message)
                                del st.session_state.reset_password_user
                                st.rerun()
                            else:
                                st.error(message)
                        else:
                            st.error("Passwords don't match or too short (min 6 chars)")
                with col2:
                    if st.form_submit_button("Cancel"):
                        del st.session_state.reset_password_user
                        st.rerun()
    
    # Create new user form
    st.markdown("---")
    st.markdown("**Create New User**")
    with st.form("create_user_form"):
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("Username", placeholder="e.g., john.smith")
            full_name = st.text_input("Full Name", placeholder="e.g., John Smith")
            email = st.text_input("Email", placeholder="e.g., john@company.com")
        with col2:
            password = st.text_input("Password", type="password", placeholder="Minimum 6 characters")
            role = st.selectbox("Role", [
                "property_developer", "project_manager", "inspector", "builder", "admin"
            ])
            
        if st.form_submit_button("Create User", type="primary", use_container_width=True):
            if username and full_name and email and password:
                if len(password) >= 6:
                    current_user = st.session_state.get("username", "admin")
                    success, message = admin_manager.create_user(username, password, full_name, email, role, current_user)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("Password must be at least 6 characters")
            else:
                st.error("Please fill all fields")

def show_enhanced_project_management(admin_manager):
    """Enhanced project management with full CRUD"""
    st.markdown("#### Complete Project Management")
    
    projects = admin_manager.get_all_projects()
    
    if projects:
        st.markdown("**Current Projects**")
        projects_df = pd.DataFrame(projects, columns=[
            "ID", "Name", "Description", "Status", "Manager", "Created", "Portfolio", "Portfolio Owner"
        ])
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.dataframe(projects_df, use_container_width=True)
        
        with col2:
            st.markdown("**Project Actions**")
            selected_project = st.selectbox("Select Project:", [p[0] for p in projects])
            
            if st.button("Edit Project", use_container_width=True):
                st.session_state.edit_project = selected_project
            
            if st.button("Delete Project", use_container_width=True, type="secondary"):
                success, message = admin_manager.delete_project(selected_project)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        
        # Edit project form
        if st.session_state.get("edit_project"):
            project_to_edit = st.session_state.edit_project
            project_data = next((p for p in projects if p[0] == project_to_edit), None)
            
            if project_data:
                st.markdown(f"**Editing Project: {project_to_edit}**")
                with st.form("edit_project_form"):
                    name = st.text_input("Project Name", value=project_data[1])
                    description = st.text_area("Description", value=project_data[2] or "")
                    status = st.selectbox("Status", ["active", "completed", "cancelled"], 
                                        index=["active", "completed", "cancelled"].index(project_data[3]) if project_data[3] in ["active", "completed", "cancelled"] else 0)
                    
                    # Get available managers
                    users = admin_manager.get_all_users()
                    managers = [user[0] for user in users if user[3] in ['project_manager', 'admin']]
                    current_manager_index = managers.index(project_data[4]) if project_data[4] in managers else 0
                    manager = st.selectbox("Project Manager", managers, index=current_manager_index)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Update Project", type="primary"):
                            success, message = admin_manager.update_project(project_to_edit, name, description, status, manager)
                            if success:
                                st.success(message)
                                del st.session_state.edit_project
                                st.rerun()
                            else:
                                st.error(message)
                    with col2:
                        if st.form_submit_button("Cancel"):
                            del st.session_state.edit_project
                            st.rerun()
    
    # Create new project form
    st.markdown("---")
    st.markdown("**Create New Project**")
    with st.form("create_project_form"):
        col1, col2 = st.columns(2)
        with col1:
            project_id = st.text_input("Project ID", placeholder="e.g., project_downtown")
            project_name = st.text_input("Project Name", placeholder="e.g., Downtown Development")
            description = st.text_area("Description", placeholder="Project description...")
        with col2:
            portfolio_id = st.text_input("Portfolio ID", value="portfolio_001", help="Default portfolio")
            
            # Get available managers
            users = admin_manager.get_all_users()
            managers = [user[0] for user in users if user[3] in ['project_manager', 'admin']]
            manager = st.selectbox("Project Manager", managers) if managers else None
        
        if st.form_submit_button("Create Project", type="primary", use_container_width=True):
            if project_id and project_name and manager:
                success, message = admin_manager.create_project(project_id, portfolio_id, project_name, description, manager)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.error("Please fill required fields")

def show_enhanced_building_management(admin_manager):
    """Enhanced building management with full CRUD"""
    st.markdown("#### Complete Building Management")
    
    buildings = admin_manager.get_all_buildings()
    
    if buildings:
        st.markdown("**Current Buildings**")
        buildings_df = pd.DataFrame(buildings, columns=[
            "ID", "Name", "Address", "Units", "Type", "Created", "Project", "Project ID"
        ])
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.dataframe(buildings_df[["Project", "Name", "Address", "Units", "Type", "Created"]], use_container_width=True)
        
        with col2:
            st.markdown("**Building Actions**")
            selected_building = st.selectbox("Select Building:", [b[0] for b in buildings])
            
            if st.button("Edit Building", use_container_width=True):
                st.session_state.edit_building = selected_building
            
            if st.button("Delete Building", use_container_width=True, type="secondary"):
                success, message = admin_manager.delete_building(selected_building)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        
        # Edit building form
        if st.session_state.get("edit_building"):
            building_to_edit = st.session_state.edit_building
            building_data = next((b for b in buildings if b[0] == building_to_edit), None)
            
            if building_data:
                st.markdown(f"**Editing Building: {building_to_edit}**")
                with st.form("edit_building_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        name = st.text_input("Building Name", value=building_data[1])
                        address = st.text_area("Address", value=building_data[2] or "")
                    with col2:
                        total_units = st.number_input("Total Units", value=building_data[3] or 0, min_value=0)
                        building_type = st.selectbox("Building Type", 
                                                   ["Apartment", "Townhouse", "Mixed Use", "Commercial", "Other"],
                                                   index=["Apartment", "Townhouse", "Mixed Use", "Commercial", "Other"].index(building_data[4]) if building_data[4] in ["Apartment", "Townhouse", "Mixed Use", "Commercial", "Other"] else 0)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Update Building", type="primary"):
                            success, message = admin_manager.update_building(building_to_edit, name, address, total_units, building_type)
                            if success:
                                st.success(message)
                                del st.session_state.edit_building
                                st.rerun()
                            else:
                                st.error(message)
                    with col2:
                        if st.form_submit_button("Cancel"):
                            del st.session_state.edit_building
                            st.rerun()
    else:
        st.info("No buildings found. Create a building to get started.")
    
    # Create new building form
    st.markdown("---")
    st.markdown("**Create New Building**")
    with st.form("create_building_form"):
        col1, col2 = st.columns(2)
        with col1:
            building_id = st.text_input("Building ID", placeholder="e.g., building_tower_a")
            building_name = st.text_input("Building Name", placeholder="e.g., Tower A")
            address = st.text_area("Address", placeholder="Building address...")
        with col2:
            total_units = st.number_input("Total Units", min_value=1, value=100)
            building_type = st.selectbox("Building Type", ["Apartment", "Townhouse", "Mixed Use", "Commercial", "Other"])
            
            # Get available projects
            projects = admin_manager.get_all_projects()
            if projects:
                project_display = [f"{p[1]} ({p[0]})" for p in projects]
                selected_project = st.selectbox("Project", project_display)
                project_id = projects[project_display.index(selected_project)][0]
            else:
                st.warning("No projects available. Create a project first.")
                project_id = None
        
        if st.form_submit_button("Create Building", type="primary", use_container_width=True):
            if building_id and building_name and address and project_id:
                success, message = admin_manager.create_building(building_id, project_id, building_name, address, total_units, building_type)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.error("Please fill all required fields")

def show_enhanced_permission_management(admin_manager):
    """Enhanced permission management with full control"""
    st.markdown("#### Complete Permission Management")
    
    # User selection
    users = admin_manager.get_all_users()
    user_options = [(user[0], f"{user[1]} ({user[0]})") for user in users]
    
    if user_options:
        selected_user_display = st.selectbox("Select User to Manage Permissions", [option[1] for option in user_options])
        selected_username = user_options[[option[1] for option in user_options].index(selected_user_display)][0]
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"**Current Permissions for {selected_username}**")
            permissions = admin_manager.get_user_permissions(selected_username)
            
            if permissions:
                perm_df = pd.DataFrame(permissions, columns=[
                    "Resource Type", "Resource ID", "Permission Level", "Granted At", "Granted By", "Resource Name"
                ])
                
                # Display formatted permissions with actions
                display_df = perm_df[["Resource Type", "Resource Name", "Permission Level", "Granted By"]].copy()
                display_df["Resource Type"] = display_df["Resource Type"].str.title()
                display_df["Permission Level"] = display_df["Permission Level"].str.title()
                
                st.dataframe(display_df, use_container_width=True)
                
                # Bulk permission actions
                st.markdown("**Permission Actions**")
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    if st.button("Grant Full Access", help="Grant admin access to all resources"):
                        resources_granted = 0
                        for resource_type in ["project", "building", "portfolio"]:
                            available_resources = admin_manager.get_available_resources(resource_type)
                            for resource_id, resource_name in available_resources:
                                admin_manager.grant_permission(selected_username, resource_type, resource_id, "admin", st.session_state.get("username", "admin"))
                                resources_granted += 1
                        st.success(f"Granted admin access to {resources_granted} resources")
                        st.rerun()
                
                with col_b:
                    if st.button("Revoke All", type="secondary"):
                        revoked_count = 0
                        for perm in permissions:
                            admin_manager.revoke_permission(selected_username, perm[0], perm[1])
                            revoked_count += 1
                        st.success(f"Revoked {revoked_count} permissions")
                        st.rerun()
                
                with col_c:
                    # Individual permission revocation
                    if len(permissions) > 0:
                        perm_options = [f"{p[0]} - {p[5]} ({p[2]})" for p in permissions]
                        selected_perm = st.selectbox("Select to Revoke:", perm_options, key="revoke_select")
                        
                        if st.button("Revoke Selected", type="secondary"):
                            perm_index = perm_options.index(selected_perm)
                            resource_type = permissions[perm_index][0]
                            resource_id = permissions[perm_index][1]
                            
                            success, message = admin_manager.revoke_permission(selected_username, resource_type, resource_id)
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
            else:
                st.info("No permissions assigned to this user")
                
                # Quick setup for new users
                st.markdown("**Quick Permission Setup**")
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("Basic User Setup", help="Read access to default resources"):
                        admin_manager.grant_permission(selected_username, "portfolio", "portfolio_001", "read", st.session_state.get("username", "admin"))
                        admin_manager.grant_permission(selected_username, "project", "project_default", "read", st.session_state.get("username", "admin"))
                        st.success("Basic permissions granted")
                        st.rerun()
                
                with col_b:
                    if st.button("Manager Setup", help="Write access to default resources"):
                        admin_manager.grant_permission(selected_username, "portfolio", "portfolio_001", "write", st.session_state.get("username", "admin"))
                        admin_manager.grant_permission(selected_username, "project", "project_default", "write", st.session_state.get("username", "admin"))
                        admin_manager.grant_permission(selected_username, "building", "building_default", "write", st.session_state.get("username", "admin"))
                        st.success("Manager permissions granted")
                        st.rerun()
        
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
                
                if st.form_submit_button("Grant Permission", type="primary", use_container_width=True):
                    if resource_id:
                        current_user = st.session_state.get("username", "admin")
                        success, message = admin_manager.grant_permission(selected_username, resource_type, resource_id, permission_level, current_user)
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
    st.markdown("#### System Overview & Analytics")
    
    # Get statistics
    users = admin_manager.get_all_users()
    projects = admin_manager.get_all_projects()
    buildings = admin_manager.get_all_buildings()
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        active_users = len([u for u in users if u[4] == 1])
        st.metric("Active Users", active_users, delta=f"{len(users)} total")
    
    with col2:
        st.metric("Total Projects", len(projects))
    
    with col3:
        st.metric("Total Buildings", len(buildings))
    
    with col4:
        total_units = sum(building[3] for building in buildings if building[3])
        st.metric("Total Units", total_units)
    
    # Detailed analytics
    col1, col2 = st.columns(2)
    
    with col1:
        # User breakdown by role
        if users:
            st.markdown("**Users by Role**")
            role_counts = {}
            for user in users:
                role = user[3].replace('_', ' ').title()
                role_counts[role] = role_counts.get(role, 0) + 1
            
            role_df = pd.DataFrame(list(role_counts.items()), columns=["Role", "Count"])
            st.dataframe(role_df, use_container_width=True)
        
        # Project status breakdown
        if projects:
            st.markdown("**Projects by Status**")
            status_counts = {}
            for project in projects:
                status = project[3].title()
                status_counts[status] = status_counts.get(status, 0) + 1
            
            status_df = pd.DataFrame(list(status_counts.items()), columns=["Status", "Count"])
            st.dataframe(status_df, use_container_width=True)
    
    with col2:
        # Recent activity
        st.markdown("**Recent Users**")
        if users:
            # Sort by last login, then created date
            recent_users = sorted(users, key=lambda x: x[6] or x[5] or '1900-01-01', reverse=True)[:5]
            recent_df = pd.DataFrame(recent_users, columns=[
                "Username", "Full Name", "Email", "Role", "Active", "Created", "Last Login"
            ])
            st.dataframe(recent_df[["Username", "Full Name", "Role", "Last Login"]], use_container_width=True)
        
        # Building types breakdown
        if buildings:
            st.markdown("**Buildings by Type**")
            type_counts = {}
            for building in buildings:
                btype = building[4] or "Unknown"
                type_counts[btype] = type_counts.get(btype, 0) + 1
            
            type_df = pd.DataFrame(list(type_counts.items()), columns=["Type", "Count"])
            st.dataframe(type_df, use_container_width=True)
    
    # System health indicators
    st.markdown("---")
    st.markdown("**System Health**")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        inactive_users = len([u for u in users if u[4] == 0])
        if inactive_users == 0:
            st.success("All users active")
        else:
            st.warning(f"{inactive_users} inactive users")
    
    with col2:
        # Check for users without permissions
        users_without_permissions = []
        for user in users:
            if user[3] != 'admin':  # Skip admin users
                perms = admin_manager.get_user_permissions(user[0])
                if not perms:
                    users_without_permissions.append(user[0])
        
        if not users_without_permissions:
            st.success("All users have permissions")
        else:
            st.warning(f"{len(users_without_permissions)} users need permissions")
    
    with col3:
        # Check for projects without managers
        projects_without_managers = len([p for p in projects if not p[4]])
        if projects_without_managers == 0:
            st.success("All projects have managers")
        else:
            st.warning(f"{projects_without_managers} projects need managers")
    
    with col4:
        # Check for buildings without projects
        buildings_without_projects = len([b for b in buildings if not b[7]])
        if buildings_without_projects == 0:
            st.success("All buildings assigned")
        else:
            st.warning(f"{buildings_without_projects} unassigned buildings")
    
    # Data export options
    st.markdown("---")
    st.markdown("**Data Export**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Export Users", use_container_width=True):
            users_df = pd.DataFrame(users, columns=["Username", "Full Name", "Email", "Role", "Active", "Created", "Last Login"])
            csv = users_df.to_csv(index=False)
            st.download_button("Download Users CSV", csv, "users_export.csv", "text/csv")
    
    with col2:
        if st.button("Export Projects", use_container_width=True):
            projects_df = pd.DataFrame(projects, columns=["ID", "Name", "Description", "Status", "Manager", "Created", "Portfolio", "Portfolio Owner"])
            csv = projects_df.to_csv(index=False)
            st.download_button("Download Projects CSV", csv, "projects_export.csv", "text/csv")
    
    with col3:
        if st.button("Export Buildings", use_container_width=True):
            buildings_df = pd.DataFrame(buildings, columns=["ID", "Name", "Address", "Units", "Type", "Created", "Project", "Project ID"])
            csv = buildings_df.to_csv(index=False)
            st.download_button("Download Buildings CSV", csv, "buildings_export.csv", "text/csv")