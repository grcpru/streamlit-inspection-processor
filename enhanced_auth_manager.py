import json
import os
import sqlite3
from datetime import datetime, timedelta
import pickle
import hashlib
import time
import streamlit as st

class EnhancedAuthManager:
    """Enhanced authentication manager with role-based permissions and data persistence"""
    
    def __init__(self):
        self.users_file = "users.json"
        self.reports_db = "reports.db"
        self.session_timeout = 8 * 60 * 60  # 8 hours
        
        # Define role permissions
        self.role_permissions = {
            "admin": {
                "can_upload": True,
                "can_process": True,
                "can_view_all_buildings": True,
                "can_manage_users": True,
                "can_delete_reports": True,
                "can_export_all": True,
                "description": "Full system access - can upload, process, and manage all data"
            },
            "inspector": {
                "can_upload": True,
                "can_process": True,
                "can_view_all_buildings": True,
                "can_manage_users": False,
                "can_delete_reports": False,
                "can_export_all": True,
                "description": "Upload and process inspection data for any building"
            },
            "builder": {
                "can_upload": False,
                "can_process": False,
                "can_view_all_buildings": False,  # Only assigned buildings
                "can_manage_users": False,
                "can_delete_reports": False,
                "can_export_all": False,
                "description": "View reports for assigned buildings only"
            },
            "project_manager": {
                "can_upload": True,
                "can_process": True,
                "can_view_all_buildings": False,  # Only assigned buildings
                "can_manage_users": False,
                "can_delete_reports": False,
                "can_export_all": True,
                "description": "Manage specific building projects"
            }
        }
        
        # Enhanced default users with building assignments
        self.default_users = {
            "admin": {
                "password_hash": self._hash_password("admin123"),
                "role": "admin",
                "name": "System Administrator",
                "assigned_buildings": ["*"],  # * means all buildings
                "created_date": datetime.now().isoformat()
            },
            "inspector": {
                "password_hash": self._hash_password("inspector123"),
                "role": "inspector", 
                "name": "Site Inspector",
                "assigned_buildings": ["*"],
                "created_date": datetime.now().isoformat()
            },
            "builder_abc": {
                "password_hash": self._hash_password("builder123"),
                "role": "builder",
                "name": "ABC Construction",
                "assigned_buildings": ["ABC Tower", "ABC Residences"],
                "created_date": datetime.now().isoformat()
            },
            "builder_xyz": {
                "password_hash": self._hash_password("builder456"),
                "role": "builder",
                "name": "XYZ Developments",
                "assigned_buildings": ["XYZ Plaza", "XYZ Heights"],
                "created_date": datetime.now().isoformat()
            },
            "pm_downtown": {
                "password_hash": self._hash_password("pm123"),
                "role": "project_manager",
                "name": "Downtown PM",
                "assigned_buildings": ["Downtown Complex", "Central Plaza"],
                "created_date": datetime.now().isoformat()
            }
        }
        
        self._load_users()
        self._init_reports_database()
    
    def _init_reports_database(self):
        """Initialize SQLite database for storing reports"""
        conn = sqlite3.connect(self.reports_db)
        cursor = conn.cursor()
        
        # Create reports table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                building_name TEXT NOT NULL,
                building_address TEXT,
                inspection_date TEXT,
                upload_date TEXT NOT NULL,
                uploaded_by TEXT NOT NULL,
                processed_data BLOB,
                metrics BLOB,
                trade_mapping BLOB,
                file_name TEXT,
                file_size INTEGER,
                status TEXT DEFAULT 'active',
                UNIQUE(building_name, inspection_date)
            )
        ''')
        
        # Create building access log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                building_name TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_report(self, building_name, building_address, inspection_date, 
                   processed_data, metrics, trade_mapping, uploaded_by, 
                   file_name=None, file_size=None):
        """Save a processed report to the database"""
        conn = sqlite3.connect(self.reports_db)
        cursor = conn.cursor()
        
        try:
            # Serialize data
            processed_data_blob = pickle.dumps(processed_data)
            metrics_blob = pickle.dumps(metrics)
            trade_mapping_blob = pickle.dumps(trade_mapping)
            
            # Insert or replace report
            cursor.execute('''
                INSERT OR REPLACE INTO reports 
                (building_name, building_address, inspection_date, upload_date, 
                 uploaded_by, processed_data, metrics, trade_mapping, 
                 file_name, file_size, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                building_name, building_address, inspection_date, 
                datetime.now().isoformat(), uploaded_by,
                processed_data_blob, metrics_blob, trade_mapping_blob,
                file_name, file_size, 'active'
            ))
            
            conn.commit()
            return True, "Report saved successfully"
            
        except Exception as e:
            return False, f"Error saving report: {str(e)}"
        finally:
            conn.close()
    
    def get_available_buildings(self, username):
        """Get list of buildings the user can access"""
        user = self.users.get(username)
        if not user:
            return []
        
        conn = sqlite3.connect(self.reports_db)
        cursor = conn.cursor()
        
        try:
            if "*" in user.get("assigned_buildings", []):
                # User can access all buildings
                cursor.execute('SELECT DISTINCT building_name FROM reports WHERE status = "active"')
            else:
                # User can only access assigned buildings
                assigned = user.get("assigned_buildings", [])
                if not assigned:
                    return []
                
                placeholders = ','.join(['?' for _ in assigned])
                cursor.execute(f'''
                    SELECT DISTINCT building_name FROM reports 
                    WHERE status = "active" AND building_name IN ({placeholders})
                ''', assigned)
            
            buildings = [row[0] for row in cursor.fetchall()]
            return sorted(buildings)
            
        except Exception as e:
            print(f"Error fetching buildings: {e}")
            return []
        finally:
            conn.close()
    
    def get_latest_report(self, building_name, username):
        """Get the latest report for a building (with permission check)"""
        if not self.can_access_building(username, building_name):
            return None, None, "Access denied to this building"
        
        conn = sqlite3.connect(self.reports_db)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT processed_data, metrics, trade_mapping, upload_date, uploaded_by, inspection_date
                FROM reports 
                WHERE building_name = ? AND status = "active"
                ORDER BY upload_date DESC 
                LIMIT 1
            ''', (building_name,))
            
            row = cursor.fetchone()
            if row:
                processed_data = pickle.loads(row[0])
                metrics = pickle.loads(row[1])
                trade_mapping = pickle.loads(row[2])
                
                # Log access
                self.log_access(username, building_name, "view_report")
                
                return (processed_data, metrics, trade_mapping), {
                    "upload_date": row[3],
                    "uploaded_by": row[4],
                    "inspection_date": row[5]
                }, None
            else:
                return None, None, "No reports found for this building"
                
        except Exception as e:
            return None, None, f"Error retrieving report: {str(e)}"
        finally:
            conn.close()
    
    def can_access_building(self, username, building_name):
        """Check if user can access a specific building"""
        user = self.users.get(username)
        if not user:
            return False
        
        assigned_buildings = user.get("assigned_buildings", [])
        return "*" in assigned_buildings or building_name in assigned_buildings
    
    def get_user_permissions(self, username):
        """Get user's role permissions"""
        user = self.users.get(username)
        if not user:
            return {}
        
        role = user.get("role", "")
        return self.role_permissions.get(role, {})
    
    def log_access(self, username, building_name, action):
        """Log user access to buildings"""
        conn = sqlite3.connect(self.reports_db)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO access_log (username, building_name, action, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (username, building_name, action, datetime.now().isoformat()))
            conn.commit()
        except Exception as e:
            print(f"Error logging access: {e}")
        finally:
            conn.close()
    
    def get_all_reports_summary(self, username):
        """Get summary of all reports user can access"""
        user = self.users.get(username)
        if not user:
            return []
        
        conn = sqlite3.connect(self.reports_db)
        cursor = conn.cursor()
        
        try:
            if "*" in user.get("assigned_buildings", []):
                cursor.execute('''
                    SELECT building_name, building_address, inspection_date, 
                           upload_date, uploaded_by, file_name
                    FROM reports 
                    WHERE status = "active"
                    ORDER BY upload_date DESC
                ''')
            else:
                assigned = user.get("assigned_buildings", [])
                if not assigned:
                    return []
                
                placeholders = ','.join(['?' for _ in assigned])
                cursor.execute(f'''
                    SELECT building_name, building_address, inspection_date, 
                           upload_date, uploaded_by, file_name
                    FROM reports 
                    WHERE status = "active" AND building_name IN ({placeholders})
                    ORDER BY upload_date DESC
                ''', assigned)
            
            reports = []
            for row in cursor.fetchall():
                reports.append({
                    "building_name": row[0],
                    "building_address": row[1],
                    "inspection_date": row[2],
                    "upload_date": row[3],
                    "uploaded_by": row[4],
                    "file_name": row[5]
                })
            
            return reports
            
        except Exception as e:
            print(f"Error fetching reports: {e}")
            return []
        finally:
            conn.close()
    
    def _hash_password(self, password):
        """Hash password using SHA-256 with salt"""
        salt = "inspection_app_salt_2024"
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def _load_users(self):
        """Load users from file or create default users"""
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    loaded_users = json.load(f)
                
                # Migrate old user format to new format if needed
                migrated_users = {}
                for username, user_data in loaded_users.items():
                    if "assigned_buildings" not in user_data:
                        # Add missing assigned_buildings field
                        if user_data.get("role") in ["admin", "inspector"]:
                            user_data["assigned_buildings"] = ["*"]
                        else:
                            user_data["assigned_buildings"] = []
                    
                    if "created_date" not in user_data:
                        user_data["created_date"] = datetime.now().isoformat()
                    
                    # Handle name field migration
                    if "name" not in user_data and "full_name" in user_data:
                        user_data["name"] = user_data["full_name"]
                        del user_data["full_name"]
                    elif "name" not in user_data:
                        user_data["name"] = username.title()
                    
                    migrated_users[username] = user_data
                
                self.users = migrated_users
                self._save_users()
            else:
                self.users = self.default_users.copy()
                self._save_users()
        except Exception as e:
            print(f"Error loading users: {e}")
            self.users = self.default_users.copy()
    
    def _save_users(self):
        """Save users to file"""
        try:
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=2)
        except Exception as e:
            print(f"Error saving users: {e}")
    
    def authenticate(self, username, password):
        """Simple authentication"""
        if not username or not password:
            return False, "Please enter username and password"
        
        if username not in self.users:
            return False, "Invalid username or password"
        
        user = self.users[username]
        
        # Simple password verification
        password_hash = self._hash_password(password)
        if password_hash != user["password_hash"]:
            return False, "Invalid username or password"
        
        return True, "Login successful"
    
    def create_session(self, username):
        """Create a simple session for user"""
        user = self.users[username]
        
        # Store minimal session data
        st.session_state.authenticated = True
        st.session_state.username = username
        st.session_state.user_role = user["role"]
        st.session_state.user_name = user.get("name", "User")
        st.session_state.login_time = time.time()
    
    def is_session_valid(self):
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
        # Clear authentication state
        auth_keys = ["authenticated", "username", "user_role", "user_name", "login_time"]
        for key in auth_keys:
            if key in st.session_state:
                del st.session_state[key]
        
        # Clear application data
        app_keys = ["trade_mapping", "processed_data", "metrics", "step_completed", "report_images", "current_building"]
        for key in app_keys:
            if key in st.session_state:
                del st.session_state[key]
    
    def get_current_user(self):
        """Get current user information"""
        return {
            "username": st.session_state.get("username", ""),
            "name": st.session_state.get("user_name", "User"),
            "role": st.session_state.get("user_role", "user")
        }
    
    def change_password(self, username, old_password, new_password):
        """Change user password"""
        if username not in self.users:
            return False, "User not found"
        
        # Verify old password
        old_hash = self._hash_password(old_password)
        if old_hash != self.users[username]["password_hash"]:
            return False, "Current password is incorrect"
        
        # Simple validation
        if len(new_password) < 6:
            return False, "New password must be at least 6 characters"
        
        # Update password
        self.users[username]["password_hash"] = self._hash_password(new_password)
        self._save_users()
        
        return True, "Password changed successfully"