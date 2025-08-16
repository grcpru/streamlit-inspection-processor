import streamlit as st
import pandas as pd
from io import BytesIO, StringIO
from datetime import datetime, timedelta
import pytz
import traceback
import zipfile
import hashlib
import hmac
import time
import json
import os

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
# STREAMLINED AUTHENTICATION SYSTEM
# =============================================================================

class StreamlinedAuthManager:
    """Simplified authentication manager - keeps security but removes complexity"""
    
    def __init__(self):
        self.users_file = "users.json"
        self.session_timeout = 8 * 60 * 60  # 8 hours in seconds
        
        # Simplified default users - removed unnecessary fields
        self.default_users = {
            "admin": {
                "password_hash": self._hash_password("admin123"),
                "role": "admin",
                "name": "System Administrator"
            },
            "inspector": {
                "password_hash": self._hash_password("inspector123"),
                "role": "user", 
                "name": "Site Inspector"
            }
        }
        
        self._load_users()
    
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
                    if "name" not in user_data and "full_name" in user_data:
                        # Migrate old format
                        migrated_users[username] = {
                            "password_hash": user_data["password_hash"],
                            "role": user_data["role"],
                            "name": user_data["full_name"]
                        }
                    elif "name" in user_data:
                        # Already new format
                        migrated_users[username] = {
                            "password_hash": user_data["password_hash"],
                            "role": user_data["role"],
                            "name": user_data["name"]
                        }
                    else:
                        # Handle any other cases
                        migrated_users[username] = {
                            "password_hash": user_data.get("password_hash", ""),
                            "role": user_data.get("role", "user"),
                            "name": user_data.get("name", user_data.get("full_name", username.title()))
                        }
                
                self.users = migrated_users
                # Save the migrated format
                self._save_users()
            else:
                self.users = self.default_users.copy()
                self._save_users()
        except Exception as e:
            st.error(f"Error loading users: {e}")
            self.users = self.default_users.copy()
    
    def _save_users(self):
        """Save users to file"""
        try:
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=2)
        except Exception as e:
            st.error(f"Error saving users: {e}")
    
    def authenticate(self, username, password):
        """Simple authentication - removed account lockout for small teams"""
        if not username or not password:
            return False, "Please enter username and password"
        
        if username not in self.users:
            return False, "Invalid username or password"
        
        user = self.users[username]
        
        # Simple password verification
        password_hash = self._hash_password(password)
        if password_hash != user["password_hash"]:
            return False, "Invalid username or password"
        
        # Success - no complex tracking needed for small teams
        return True, "Login successful"
    
    def create_session(self, username):
        """Create a simple session for user"""
        user = self.users[username]
        
        # Store minimal session data
        st.session_state.authenticated = True
        st.session_state.username = username
        st.session_state.user_role = user["role"]
        # Handle both old and new user data structures
        st.session_state.user_name = user.get("name", user.get("full_name", "User"))
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
        app_keys = ["trade_mapping", "processed_data", "metrics", "step_completed", "report_images"]
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

# Initialize authentication manager
auth_manager = StreamlinedAuthManager()

def show_login_page():
    """Simplified login page"""
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
    
    # Simple login form
    with st.form("login_form"):
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
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Please enter both username and password")
    
    # Demo credentials info (simplified)
    with st.expander("🔑 Demo Credentials", expanded=False):
        st.info("""
        **Demo Accounts:**
        
        **Administrator:**
        - Username: `admin`
        - Password: `admin123`
        
        **Inspector:**
        - Username: `inspector` 
        - Password: `inspector123`
        
        ⚠️ **Note:** These are shared team accounts - no password changes needed!
        """)
    
    # Simplified features preview
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 📊 Professional Reports
        - Excel workbooks with charts
        - Word documents with images
        - Comprehensive analytics
        """)
    
    with col2:
        st.markdown("""
        ### 🔧 Trade Mapping
        - 266+ component mappings
        - 10 trade categories
        - Automated classification
        """)
    
    with col3:
        st.markdown("""
        ### 🏠 Settlement Analysis
        - Unit readiness assessment
        - Defect rate calculations
        - Visual dashboards
        """)

def show_user_menu():
    """Simplified user menu in sidebar"""
    if not auth_manager.is_session_valid():
        return False
    
    user = auth_manager.get_current_user()
    
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 👤 User Information")
        
        # Simple user info display
        st.markdown(f"""
        **Name:** {user['name']}  
        **Role:** {user['role'].title()}  
        **Session:** Active
        """)
        
        # Simple user actions
        col1, col2 = st.columns(2)
        
        # with col1:
        #    if st.button("🔑 Change Password", use_container_width=True):
        #        st.session_state.show_password_change = True
        
        with col2:
            if st.button("🚪 Logout", use_container_width=True, type="primary"):
                auth_manager.logout()
                st.success("Logged out successfully!")
                st.rerun()
        
        # Simplified password change form
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
    
    return True

# Page configuration
st.set_page_config(
    page_title="Inspection Report Processor",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hide Streamlit Add this right after st.set_page_config()
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
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .success-box {
        background-color: #e8f5e8;
        border: 1px solid #4caf50;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .error-box {
        background-color: #ffebee;
        border: 1px solid #f44336;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .info-box {
        background-color: #e3f2fd;
        border: 1px solid #2196f3;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .download-section {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 10px;
        padding: 2rem;
        margin: 1rem 0;
    }
    
    .urgent-defect {
        background-color: #ffebee;
        border: 1px solid #f44336;
        border-radius: 5px;
        padding: 0.5rem;
        margin: 0.25rem 0;
    }
    
    .unit-lookup-container {
        background: linear-gradient(135deg, #e8f5e8 0%, #d4edda 100%);
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Check authentication
if not auth_manager.is_session_valid():
    show_login_page()
    st.stop()

# Show user menu and check if user is still logged in
if not show_user_menu():
    st.stop()

# Main application header (updated for streamlined auth)
user = auth_manager.get_current_user()
st.markdown(f"""
<div class="main-header">
    <h1>🏢 Inspection Report Processor</h1>
    <p>Essential Community Management</p>
    <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
        <span>👋 Welcome back, <strong>{user['name']}</strong>!</span>
        <span style="margin-left: 2rem;">🎭 Role: <strong>{user['role'].title()}</strong></span>
    </div>
</div>
""", unsafe_allow_html=True)

# Initialize session state
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
       # "summary_chart": None,
       # "trades_chart": None,
       # "settlement_chart": None
    }

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

    # Get inspection columns - SAME AS WORKING CODE
    inspection_cols = [
        c for c in df.columns if c.startswith("Pre-Settlement Inspection_") and not c.endswith("_notes")
    ]

    if not inspection_cols:
        inspection_cols = [c for c in df.columns if any(keyword in c.lower() for keyword in 
                          ['inspection', 'check', 'item', 'defect', 'issue', 'status'])]

    # Melt to long format - SAME AS WORKING CODE
    long_df = df.melt(
        id_vars=["Unit", "UnitType"],
        value_vars=inspection_cols,
        var_name="InspectionItem",
        value_name="Status"
    )

    # Split into Room and Component - SAME AS WORKING CODE
    parts = long_df["InspectionItem"].str.split("_", n=2, expand=True)
    if len(parts.columns) >= 3:
        long_df["Room"] = parts[1]
        long_df["Component"] = parts[2].str.replace(r"\.\d+$", "", regex=True)
        long_df["Component"] = long_df["Component"].apply(lambda x: x.split("_")[-1] if isinstance(x, str) else x)
    else:
        long_df["Room"] = "General"
        long_df["Component"] = long_df["InspectionItem"].str.replace("Pre-Settlement Inspection_", "")

    # Remove metadata rows - SAME AS WORKING CODE
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

    # Merge with trade mapping - SAME AS WORKING CODE
    merged = long_df.merge(mapping, on=["Room", "Component"], how="left")
    
    # Fill missing trades with "Unknown Trade"
    merged["Trade"] = merged["Trade"].fillna("Unknown Trade")
    
    # Add planned completion dates (simulated for demo - in real app this would come from data)
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
    
    # Extract building information using the same logic as working code
    sample_audit = df.loc[0, "auditName"] if "auditName" in df.columns and len(df) > 0 else ""
    if sample_audit:
        audit_parts = str(sample_audit).split("/")
        extracted_building_name = audit_parts[2].strip() if len(audit_parts) >= 3 else building_info["name"]
        extracted_inspection_date = audit_parts[0].strip() if len(audit_parts) >= 1 else building_info["date"]
    else:
        extracted_building_name = building_info["name"]
        extracted_inspection_date = building_info["date"]
    
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
    
    # Planned work in next 2 weeks (only items due within 14 days)
    next_two_weeks = datetime.now() + timedelta(days=14)
    planned_work_2weeks = defects_only[defects_only["PlannedCompletion"] <= next_two_weeks]
    
    # Planned work in next month (items due between 2 weeks and 1 month)
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

# Sidebar configuration
with st.sidebar:
    st.header("📋 Process Status")
    if st.session_state.step_completed["mapping"]:
        st.success("✅ Step 1: Mapping loaded")
        st.caption(f"{len(st.session_state.trade_mapping)} mapping entries")
    else:
        st.info("⏳ Step 1: Load mapping")
    
    if st.session_state.step_completed["processing"]:
        st.success("✅ Step 2: Data processed")
        if st.session_state.metrics:
            st.caption(f"{st.session_state.metrics['total_units']} units processed")
    else:
        st.info("⏳ Step 2: Process data")
    
    # Unit Lookup Section
    if st.session_state.processed_data is not None:
        st.markdown("---")
        st.header("🔍 Quick Unit Lookup")
        
        # Get all unique units for dropdown
        all_units = sorted(st.session_state.processed_data["Unit"].unique())
        
        # Unit search
        selected_unit = st.selectbox(
            "Select Unit Number:",
            options=[""] + all_units,
            help="Quick lookup of defects for any unit"
        )
        
        if selected_unit:
            unit_defects = lookup_unit_defects(st.session_state.processed_data, selected_unit)
            
            if len(unit_defects) > 0:
                st.markdown(f"**🏠 Unit {selected_unit} Defects:**")
                
                # Count by urgency
                urgent_count = len(unit_defects[unit_defects["Urgency"] == "Urgent"])
                high_priority_count = len(unit_defects[unit_defects["Urgency"] == "High Priority"])
                normal_count = len(unit_defects[unit_defects["Urgency"] == "Normal"])
                
                if urgent_count > 0:
                    st.error(f"🚨 {urgent_count} Urgent")
                if high_priority_count > 0:
                    st.warning(f"⚠️ {high_priority_count} High Priority")
                if normal_count > 0:
                    st.info(f"ℹ️ {normal_count} Normal")
                
                # Show defects in compact format
                for _, defect in unit_defects.iterrows():
                    urgency_icon = "🚨" if defect["Urgency"] == "Urgent" else "⚠️" if defect["Urgency"] == "High Priority" else "🔧"
                    st.caption(f"{urgency_icon} {defect['Room']} - {defect['Component']} ({defect['Trade']}) - Due: {defect['PlannedCompletion']}")
            else:
                st.success(f"✅ Unit {selected_unit} has no defects!")
    
    st.markdown("---")
    
    # Enhanced Word Report Images Section
    st.header("🖼️ Word Report Images")
    st.markdown("Upload images to enhance your Word report (optional):")
    
    with st.expander("📸 Upload Report Images", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            logo_upload = st.file_uploader("🏢 Company Logo", type=['png', 'jpg', 'jpeg'], key="logo_upload")
        
        with col2:
            cover_upload = st.file_uploader("📷 Cover Image", type=['png', 'jpg', 'jpeg'], key="cover_upload")
        
        # Process uploaded images
        if st.button("💾 Save Images for Report"):
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
                st.success(f"✅ {images_saved} image(s) saved for Word report enhancement!")
            else:
                st.info("ℹ️ No images uploaded.")
        
        # Show current images status
        current_images = [k for k, v in st.session_state.report_images.items() if v is not None]
        if current_images:
            st.info(f"📸 Current images ready: {', '.join(current_images)}")
    
    st.markdown("---")
    
    if st.button("🔄 Reset All", help="Clear all data and start over"):
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

# STEP 1: Load Master Trade Mapping
st.markdown("""
<div class="step-container">
    <div class="step-header">📋 Step 1: Load Master Trade Mapping</div>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("**Upload your trade mapping file or use the default template:**")
    
    # Check if mapping is empty and show warning
    if len(st.session_state.trade_mapping) == 0:
        st.markdown("""
        <div class="warning-box">
            ⚠️ <strong>Warning:</strong> Trade mapping is currently blank. Please load a mapping file or use the default template before uploading your inspection CSV.
        </div>
        """, unsafe_allow_html=True)

with col2:
    # Download default template
    default_mapping = """Room,Component,Trade
Apartment Entry Door,Door Handle,Doors
Apartment Entry Door,Door Locks and Keys,Doors
Apartment Entry Door,Paint,Painting
Apartment Entry Door,Self Latching,Doors
Apartment SOU Door,Fire Compliance Tag,Doors
Balcony,Balustrade,Carpentry & Joinery
Balcony,Drainage Point,Plumbing
Balcony,GPO (if applicable),Electrical
Balcony,Glass,Windows
Balcony,Glass Sliding Door,Windows
Balcony,Tiles,Flooring - Tiles
Bathroom,Bathtub (if applicable),Plumbing
Bathroom,Ceiling,Painting
Bathroom,Doors,Doors
Bathroom,Exhaust Fan,Electrical
Bathroom,GPO,Electrical
Bathroom,Light Fixtures,Electrical
Bathroom,Mirror,Carpentry & Joinery
Bathroom,Shower,Plumbing
Bathroom,Sink,Plumbing
Bathroom,Skirting,Carpentry & Joinery
Bathroom,Tiles,Flooring - Tiles
Bathroom,Toilet,Plumbing
Bathroom,Walls,Painting
Bathroom / Laundry,Bathroom_Ceiling,Painting
Bathroom / Laundry,Bathroom_Doors,Doors
Bathroom / Laundry,Bathroom_Exhaust Fan,Electrical
Bathroom / Laundry,Bathroom_GPO,Electrical
Bathroom / Laundry,Bathroom_Light Fixtures,Electrical
Bathroom / Laundry,Bathroom_Mirror,Carpentry & Joinery
Bathroom / Laundry,Bathroom_Shower,Plumbing
Bathroom / Laundry,Bathroom_Sink,Plumbing
Bathroom / Laundry,Bathroom_Skirting,Carpentry & Joinery
Bathroom / Laundry,Bathroom_Tiles,Flooring - Tiles
Bathroom / Laundry,Bathroom_Toilet,Plumbing
Bathroom / Laundry,Bathroom_Walls,Painting
Bathroom / Laundry,Ceiling,Painting
Bathroom / Laundry,Cold/Hot Water Outlets,Plumbing
Bathroom / Laundry,Doors,Doors
Bathroom / Laundry,Drainage,Plumbing
Bathroom / Laundry,Exhaust Fan,Electrical
Bathroom / Laundry,GPO,Electrical
Bathroom / Laundry,Laundry Section_Cold/Hot Water Outlets,Plumbing
Bathroom / Laundry,Laundry Section_Doors,Doors
Bathroom / Laundry,Laundry Section_Drainage,Plumbing
Bathroom / Laundry,Laundry Section_Exhaust Fan,Electrical
Bathroom / Laundry,Laundry Section_GPO,Electrical
Bathroom / Laundry,Laundry Section_Laundry Sink,Plumbing
Bathroom / Laundry,Laundry Section_Light Fixtures,Electrical
Bathroom / Laundry,Laundry Section_Skirting,Carpentry & Joinery
Bathroom / Laundry,Laundry Section_Tiles,Flooring - Tiles
Bathroom / Laundry,Laundry Section_Walls,Painting
Bathroom / Laundry,Laundry Sink (if applicable),Plumbing
Bathroom / Laundry,Light Fixtures,Electrical
Bathroom / Laundry,Mirror,Carpentry & Joinery
Bathroom / Laundry,Shower,Plumbing
Bathroom / Laundry,Sink,Plumbing
Bathroom / Laundry,Skirting,Carpentry & Joinery
Bathroom / Laundry,Tiles,Flooring - Tiles
Bathroom / Laundry,Toilet,Plumbing
Bathroom / Laundry,Walls,Painting
Bathroom / Laundry,Laundry Sink,Plumbing
Bedroom,Carpets,Flooring - Carpets
Bedroom,Ceiling,Painting
Bedroom,Doors,Doors
Bedroom,GPO,Electrical
Bedroom,Light Fixtures,Electrical
Bedroom,Network Router,Electrical
Bedroom,Network Router (if applicable),Electrical
Bedroom,Skirting,Carpentry & Joinery
Bedroom,Sliding Glass Door (if applicable),Windows
Bedroom,Walls,Painting
Bedroom,Wardrobe,Carpentry & Joinery
Bedroom,Windows,Windows
Bedroom 1,Carpets,Flooring - Carpets
Bedroom 1,Ceiling,Painting
Bedroom 1,Doors,Doors
Bedroom 1,GPO,Electrical
Bedroom 1,Light Fixtures,Electrical
Bedroom 1,Network Router (if applicable),Electrical
Bedroom 1,Skirting,Carpentry & Joinery
Bedroom 1,Walls,Doors
Bedroom 1,Wardrobe,Carpentry & Joinery
Bedroom 1,Windows,Windows
Bedroom 1 w/Ensuite,Bathtub (if applicable),Plumbing
Bedroom 1 w/Ensuite,Carpets,Flooring - Carpets
Bedroom 1 w/Ensuite,Ceiling,Painting
Bedroom 1 w/Ensuite,Doors,Doors
Bedroom 1 w/Ensuite,Exhaust Fan,Electrical
Bedroom 1 w/Ensuite,GPO,Electrical
Bedroom 1 w/Ensuite,Light Fixtures,Electrical
Bedroom 1 w/Ensuite,Mirror,Carpentry & Joinery
Bedroom 1 w/Ensuite,Network Router (if applicable),Electrical
Bedroom 1 w/Ensuite,Shower,Plumbing
Bedroom 1 w/Ensuite,Sink,Plumbing
Bedroom 1 w/Ensuite,Skirting,Carpentry & Joinery
Bedroom 1 w/Ensuite,Tiles,Flooring - Tiles
Bedroom 1 w/Ensuite,Toilet,Plumbing
Bedroom 1 w/Ensuite,Walls,Painting
Bedroom 1 w/Ensuite,Wardrobe,Carpentry & Joinery
Bedroom 1 w/Ensuite,Windows,Windows
Bedroom 2,Carpets,Flooring - Carpets
Bedroom 2,Ceiling,Painting
Bedroom 2,Doors,Doors
Bedroom 2,GPO,Electrical
Bedroom 2,Light Fixtures,Electrical
Bedroom 2,Network Router (if applicable),Electrical
Bedroom 2,Skirting,Carpentry & Joinery
Bedroom 2,Sliding Glass Door (if applicable),Windows
Bedroom 2,Walls,Painting
Bedroom 2,Wardrobe,Carpentry & Joinery
Bedroom 2,Windows,Windows
Bedroom 2 w/Ensuite,Bathtub (if applicable),Plumbing
Bedroom 2 w/Ensuite,Carpets,Flooring - Carpets
Bedroom 2 w/Ensuite,Ceiling,Painting
Bedroom 2 w/Ensuite,Doors,Doors
Bedroom 2 w/Ensuite,Exhaust Fan,Electrical
Bedroom 2 w/Ensuite,GPO,Electrical
Bedroom 2 w/Ensuite,Light Fixtures,Electrical
Bedroom 2 w/Ensuite,Mirror,Carpentry & Joinery
Bedroom 2 w/Ensuite,Network Router (if applicable),Electrical
Bedroom 2 w/Ensuite,Shower,Plumbing
Bedroom 2 w/Ensuite,Sink,Plumbing
Bedroom 2 w/Ensuite,Skirting,Carpentry & Joinery
Bedroom 2 w/Ensuite,Tiles,Flooring - Tiles
Bedroom 2 w/Ensuite,Toilet,Plumbing
Bedroom 2 w/Ensuite,Walls,Painting
Bedroom 2 w/Ensuite,Wardrobe,Carpentry & Joinery
Bedroom 2 w/Ensuite,Windows,Windows
Bedroom 3,Carpets,Flooring - Carpets
Bedroom 3,Ceiling,Painting
Bedroom 3,Doors,Doors
Bedroom 3,GPO,Electrical
Bedroom 3,Light Fixtures,Electrical
Bedroom 3,Network Router (if applicable),Electrical
Bedroom 3,Skirting,Carpentry & Joinery
Bedroom 3,Sliding Glass Door (if applicable),Windows
Bedroom 3,Walls,Painting
Bedroom 3,Wardrobe,Carpentry & Joinery
Bedroom 3,Windows,Windows
Bedroom w/Ensuite,Bathtub (if applicable),Plumbing
Bedroom w/Ensuite,Carpets,Flooring - Carpets
Bedroom w/Ensuite,Ceiling,Painting
Bedroom w/Ensuite,Doors,Doors
Bedroom w/Ensuite,Exhaust Fan,Electrical
Bedroom w/Ensuite,GPO,Electrical
Bedroom w/Ensuite,Light Fixtures,Electrical
Bedroom w/Ensuite,Mirror,Carpentry & Joinery
Bedroom w/Ensuite,Network Router (if applicable),Electrical
Bedroom w/Ensuite,Shower,Plumbing
Bedroom w/Ensuite,Sink,Plumbing
Bedroom w/Ensuite,Skirting,Carpentry & Joinery
Bedroom w/Ensuite,Sliding Glass Door (if applicable),Windows
Bedroom w/Ensuite,Tiles,Flooring - Tiles
Bedroom w/Ensuite,Toilet,Plumbing
Bedroom w/Ensuite,Walls,Painting
Bedroom w/Ensuite,Wardrobe,Carpentry & Joinery
Bedroom w/Ensuite,Windows,Windows
Butler's Pantry,Cabinets/Shelving,Carpentry & Joinery
Butler's Pantry,Ceiling,Painting
Butler's Pantry,Flooring,Flooring - Timber
Butler's Pantry,GPO,Electrical
Butler's Pantry,Light Fixtures,Electrical
Butler's Pantry,Sink,Plumbing
Butler's Pantry (if applicable),Cabinets/Shelving,Carpentry & Joinery
Butler's Pantry (if applicable),Ceiling,Painting
Butler's Pantry (if applicable),Flooring,Flooring - Timber
Butler's Pantry (if applicable),GPO,Electrical
Butler's Pantry (if applicable),Light Fixtures,Electrical
Butler's Pantry (if applicable),Sink,Plumbing
Corridor,Ceiling,Painting
Corridor,Flooring,Flooring - Timber
Corridor,Intercom,Electrical
Corridor,Light Fixtures,Electrical
Corridor,Skirting,Carpentry & Joinery
Corridor,Walls,Painting
Dining & Living Room Area,Ceiling,Painting
Dining & Living Room Area,Flooring,Flooring - Timber
Dining & Living Room Area,GPO,Electrical
Dining & Living Room Area,Light Fixtures,Electrical
Dining & Living Room Area,Skirting,Carpentry & Joinery
Dining & Living Room Area,Walls,Painting
Dining & Living Room Area,Windows (if applicable),Windows
Downstairs Bathroom,Ceiling,Painting
Downstairs Bathroom,Doors,Doors
Downstairs Bathroom,Exhaust Fan,Electrical
Downstairs Bathroom,GPO,Electrical
Downstairs Bathroom,Light Fixtures,Electrical
Downstairs Bathroom,Mirror,Carpentry & Joinery
Downstairs Bathroom,Shower,Plumbing
Downstairs Bathroom,Sink,Plumbing
Downstairs Bathroom,Skirting,Carpentry & Joinery
Downstairs Bathroom,Tiles,Flooring - Tiles
Downstairs Bathroom,Toilet,Plumbing
Downstairs Bathroom,Walls,Painting
Downstairs Toilet (if applicable),Ceiling,Painting
Downstairs Toilet (if applicable),Doors,Doors
Downstairs Toilet (if applicable),Exhaust Fan,Electrical
Downstairs Toilet (if applicable),Light Fixtures,Electrical
Downstairs Toilet (if applicable),Sink,Plumbing
Downstairs Toilet (if applicable),Skirting,Carpentry & Joinery
Downstairs Toilet (if applicable),Tiles,Flooring - Tiles
Downstairs Toilet (if applicable),Toilet,Plumbing
Downstairs Toilet (if applicable),Walls,Painting
Kitchen Area,Cabinets,Carpentry & Joinery
Kitchen Area,Ceiling,Painting
Kitchen Area,Dishwasher,Plumbing
Kitchen Area,Dishwasher (if applicable),Plumbing
Kitchen Area,Flooring,Flooring - Timber
Kitchen Area,GPO,Electrical
Kitchen Area,Kitchen Sink,Plumbing
Kitchen Area,Kitchen Table Tops,Carpentry & Joinery
Kitchen Area,Light Fixtures,Electrical
Kitchen Area,Rangehood,Appliances
Kitchen Area,Splashbacks,Painting
Kitchen Area,Stovetop and Oven,Appliances
Laundry Room,Cold/Hot Water Outlets,Plumbing
Laundry Room,Doors,Doors
Laundry Room,Drainage,Plumbing
Laundry Room,Exhaust Fan,Electrical
Laundry Room,GPO,Electrical
Laundry Room,Laundry Sink,Plumbing
Laundry Room,Light Fixtures,Electrical
Laundry Room,Skirting,Carpentry & Joinery
Laundry Room,Tiles,Flooring - Tiles
Laundry Room,Walls,Painting
Laundry Room,Windows (if applicable),Windows
Laundry Section,Cold/Hot Water Outlets,Plumbing
Laundry Section,Doors,Doors
Laundry Section,Drainage,Plumbing
Laundry Section,Exhaust Fan,Electrical
Laundry Section,GPO,Electrical
Laundry Section,Laundry Sink,Plumbing
Laundry Section,Light Fixtures,Electrical
Laundry Section,Skirting,Carpentry & Joinery
Laundry Section,Tiles,Flooring - Tiles
Laundry Section,Walls,Painting
Staircase,Ceiling,Painting
Staircase,Light Fixtures,Electrical
Staircase,Railing (if applicable),Carpentry & Joinery
Staircase,Skirting,Carpentry & Joinery
Staircase,Staircase,Carpentry & Joinery
Staircase,Walls,Painting
Study Area (if applicable),Desk,Carpentry & Joinery
Study Area (if applicable),GPO,Electrical
Study Area (if applicable),Light Fixtures,Electrical
Study Area (if applicable),Skirting,Carpentry & Joinery
Study Area (if applicable),Walls,Painting
Upstair Corridor,Ceiling,Painting
Upstair Corridor,Flooring,Flooring - Timber
Upstair Corridor,Light Fixtures,Electrical
Upstair Corridor,Skirting,Carpentry & Joinery
Upstair Corridor,Walls,Painting
Upstairs Bathroom,Bathtub (if applicable),Plumbing
Upstairs Bathroom,Ceiling,Painting
Upstairs Bathroom,Doors,Doors
Upstairs Bathroom,Exhaust Fan,Electrical
Upstairs Bathroom,GPO,Electrical
Upstairs Bathroom,Light Fixtures,Electrical
Upstairs Bathroom,Mirror,Carpentry & Joinery
Upstairs Bathroom,Shower,Plumbing
Upstairs Bathroom,Sink,Plumbing
Upstairs Bathroom,Skirting,Carpentry & Joinery
Upstairs Bathroom,Tiles,Flooring - Tiles
Upstairs Bathroom,Toilet,Plumbing
Upstairs Bathroom,Walls,Painting"""
    
    st.download_button(
        "📥 Download Template",
        data=default_mapping,
        file_name="trade_mapping_template.csv",
        mime="text/csv",
        help="Download a comprehensive mapping template"
    )

# Upload mapping file
mapping_file = st.file_uploader("Choose trade mapping CSV", type=["csv"], key="mapping_upload")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📄 Load Default Mapping", type="secondary"):
        st.session_state.trade_mapping = pd.read_csv(StringIO(default_mapping))
        st.session_state.step_completed["mapping"] = True
        st.success("Default mapping loaded!")
        st.rerun()

with col2:
    if mapping_file is not None:
        if st.button("📤 Load Uploaded Mapping", type="primary"):
            try:
                st.session_state.trade_mapping = pd.read_csv(mapping_file)
                st.session_state.step_completed["mapping"] = True
                st.success(f"Mapping loaded: {len(st.session_state.trade_mapping)} entries")
                st.rerun()
            except Exception as e:
                st.error(f"Error loading mapping: {e}")

with col3:
    if st.button("🗑️ Clear Mapping"):
        st.session_state.trade_mapping = pd.DataFrame(columns=["Room", "Component", "Trade"])
        st.session_state.step_completed["mapping"] = False
        st.rerun()

# Display current mapping
if len(st.session_state.trade_mapping) > 0:
    st.markdown("**Current Trade Mapping:**")
    st.dataframe(st.session_state.trade_mapping, use_container_width=True, height=200)
else:
    st.info("No trade mapping loaded. Please load the default template or upload your own mapping file.")

# STEP 2: Upload and Process Data
st.markdown("""
<div class="step-container">
    <div class="step-header">📊 Step 2: Upload Inspection Data</div>
</div>
""", unsafe_allow_html=True)

# Upload inspection data first
uploaded_csv = st.file_uploader("Choose inspection CSV file", type=["csv"], key="inspection_upload")

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

# Check if mapping is loaded before allowing CSV upload
if len(st.session_state.trade_mapping) == 0:
    st.warning("⚠️ Please load your trade mapping first before uploading the inspection CSV file.")
    st.stop()

if uploaded_csv is not None:
    if st.button("🔄 Process Inspection Data", type="primary", use_container_width=True):
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
                
                processed_df, metrics = process_inspection_data(df, st.session_state.trade_mapping, building_info)
                
                # Store in session state
                st.session_state.processed_data = processed_df
                st.session_state.metrics = metrics
                st.session_state.step_completed["processing"] = True
                
                st.success(f"✅ Successfully processed {len(df)} inspection records!")
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ Error processing data: {e}")
            st.code(traceback.format_exc())

# STEP 3: Show Results and Download Options
if st.session_state.processed_data is not None and st.session_state.metrics is not None:
    st.markdown("""
    <div class="step-container">
        <div class="step-header">📈 Step 3: Analysis Results & Downloads</div>
    </div>
    """, unsafe_allow_html=True)
    
    metrics = st.session_state.metrics
    
    # Building Information Section (Auto-Detected from CSV)
    st.markdown("### 🏢 Building Information (Auto-Detected)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        **🏢 Building Name:** {metrics['building_name']}  
        **📅 Inspection Date:** {metrics['inspection_date']}  
        **🏠 Total Units:** {metrics['total_units']:,} units
        """)
    
    with col2:
        st.markdown(f"""
        **📍 Address:** {metrics['address']}  
        **🏗️ Unit Types:** {metrics['unit_types_str']}
        """)
    
    st.markdown("---")
    
    # Key Metrics Dashboard - Updated with "Completion Efficiency"
    st.subheader("📊 Key Metrics Dashboard")
    
    # Create metrics in a more visually appealing way
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "🏠 Total Units", 
            f"{metrics['total_units']:,}",
            help="Total number of units inspected"
        )
    
    with col2:
        st.metric(
            "🚨 Total Defects", 
            f"{metrics['total_defects']:,}",
            delta=f"{metrics['defect_rate']:.1f}% rate"
        )
    
    with col3:
        st.metric(
            "✅ Ready Units", 
            f"{metrics['ready_units']}",
            delta=f"{metrics['ready_pct']:.1f}%"
        )
    
    with col4:
        st.metric(
            "📊 Avg Defects/Unit", 
            f"{metrics['avg_defects_per_unit']:.1f}",
            help="Average number of defects per unit"
        )
    
    with col5:
        completion_efficiency = (metrics['ready_units'] / metrics['total_units'] * 100) if metrics['total_units'] > 0 else 0
        st.metric(
            "🎯 Completion Efficiency", 
            f"{completion_efficiency:.1f}%",
            help="Percentage of units ready for immediate handover"
        )
    
    # Enhanced Unit Lookup in Main Area
    st.markdown("---")
    st.markdown("""
    <div class="unit-lookup-container">
        <h3 style="text-align: center; margin-bottom: 1rem;">🔍 Unit Defect Lookup</h3>
        <p style="text-align: center;">Quickly search for any unit's complete defect history</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Get all unique units for search
        all_units = sorted(st.session_state.processed_data["Unit"].unique())
        
        # Enhanced unit search with autocomplete
        search_unit = st.selectbox(
            "🏠 Enter or Select Unit Number:",
            options=[""] + all_units,
            help="Type to search or select from dropdown",
            key="main_unit_search"
        )
        
        if search_unit:
            unit_defects = lookup_unit_defects(st.session_state.processed_data, search_unit)
            
            if len(unit_defects) > 0:
                st.markdown(f"### 📋 Unit {search_unit} - Complete Defect Report")
                
                # Summary metrics for this unit
                col1, col2, col3, col4 = st.columns(4)
                
                urgent_count = len(unit_defects[unit_defects["Urgency"] == "Urgent"])
                high_priority_count = len(unit_defects[unit_defects["Urgency"] == "High Priority"])
                normal_count = len(unit_defects[unit_defects["Urgency"] == "Normal"])
                total_defects = len(unit_defects)
                
                with col1:
                    st.metric("🚨 Urgent", urgent_count)
                with col2:
                    st.metric("⚠️ High Priority", high_priority_count)
                with col3:
                    st.metric("🔧 Normal", normal_count)
                with col4:
                    st.metric("📊 Total Defects", total_defects)
                
                # Detailed defect table
                st.markdown("**📋 Detailed Defect List:**")
                
                # Format the data for display
                display_data = unit_defects.copy()
                display_data["Urgency"] = display_data["Urgency"].apply(
                    lambda x: f"🚨 {x}" if x == "Urgent" 
                    else f"⚠️ {x}" if x == "High Priority" 
                    else f"🔧 {x}"
                )
                
                st.dataframe(
                    display_data,
                    use_container_width=True,
                    column_config={
                        "Room": st.column_config.TextColumn("🚪 Room", width="medium"),
                        "Component": st.column_config.TextColumn("🔧 Component", width="medium"),
                        "Trade": st.column_config.TextColumn("👷 Trade", width="medium"),
                        "Urgency": st.column_config.TextColumn("⚡ Priority", width="small"),
                        "PlannedCompletion": st.column_config.DateColumn("📅 Due Date", width="small")
                    }
                )
                
                # Unit status summary
                if urgent_count > 0:
                    st.error(f"🚨 **HIGH ATTENTION REQUIRED** - {urgent_count} urgent defect(s) need immediate attention!")
                elif high_priority_count > 0:
                    st.warning(f"⚠️ **PRIORITY WORK** - {high_priority_count} high priority defect(s) to address")
                elif normal_count > 0:
                    st.info(f"🔧 **STANDARD WORK** - {normal_count} normal defect(s) to complete")
                
            else:
                st.success(f"🎉 **Unit {search_unit} is DEFECT-FREE!** ✅")
                st.balloons()
    
    
    # Summary Tables Section - Enhanced as per Nelson's feedback
    st.markdown("---")
    st.subheader("📋 Summary Tables")
    
    # Create tabs for different summary views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔧 Trade Summary", 
        "🏠 Unit Summary", 
        "🚪 Room Summary", 
        "🚨 Urgent Defects", 
        "📅 Planned Work"
    ])
    
    with tab1:
        st.markdown("**Trade-wise defect breakdown - Shows which trades have the most issues**")
        if len(metrics['summary_trade']) > 0:
            st.dataframe(
                metrics['summary_trade'], 
                use_container_width=True,
                column_config={
                    "Trade": st.column_config.TextColumn("👷 Trade Category", width="large"),
                    "DefectCount": st.column_config.NumberColumn("🚨 Defect Count", width="medium")
                }
            )
        else:
            st.info("No trade defects found")
    
    with tab2:
        st.markdown("**Unit-wise defect breakdown - Shows which units need the most attention**")
        if len(metrics['summary_unit']) > 0:
            st.dataframe(
                metrics['summary_unit'], 
                use_container_width=True,
                column_config={
                    "Unit": st.column_config.TextColumn("🏠 Unit Number", width="medium"),
                    "DefectCount": st.column_config.NumberColumn("🚨 Defect Count", width="medium")
                }
            )
        else:
            st.info("No unit defects found")
    
    with tab3:
        st.markdown("**Room-wise defect breakdown - Shows which room types have the most issues**")
        if len(metrics['summary_room']) > 0:
            st.dataframe(
                metrics['summary_room'], 
                use_container_width=True,
                column_config={
                    "Room": st.column_config.TextColumn("🚪 Room Type", width="large"),
                    "DefectCount": st.column_config.NumberColumn("🚨 Defect Count", width="medium")
                }
            )
        else:
            st.info("No room defects found")
    
    with tab4:
        st.markdown("**🚨 URGENT DEFECTS - These require immediate attention!**")
        if len(metrics['urgent_defects_table']) > 0:
            # Style urgent defects with warning colors
            urgent_display = metrics['urgent_defects_table'].copy()
            urgent_display["PlannedCompletion"] = pd.to_datetime(urgent_display["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
            
            st.dataframe(
                urgent_display,
                use_container_width=True,
                column_config={
                    "Unit": st.column_config.TextColumn("🏠 Unit", width="small"),
                    "Room": st.column_config.TextColumn("🚪 Room", width="medium"),
                    "Component": st.column_config.TextColumn("🔧 Component", width="medium"),
                    "Trade": st.column_config.TextColumn("👷 Trade", width="medium"),
                    "PlannedCompletion": st.column_config.TextColumn("📅 Due Date", width="small")
                }
            )
            
            if len(urgent_display) > 0:
                st.error(f"⚠️ **{len(urgent_display)} URGENT defects require immediate attention!**")
        else:
            st.success("✅ No urgent defects found!")
    
    with tab5:
        st.markdown("**📅 Planned Defect Work Schedule**")
        
        # Sub-tabs for different time periods
        subtab1, subtab2 = st.tabs(["📆 Next 2 Weeks", "📅 Next Month"])
        
        with subtab1:
            st.markdown(f"**Work planned for completion in the next 2 weeks ({metrics['planned_work_2weeks']} items)**")
            st.info("📅 Shows defects due within the next 14 days")
            if len(metrics['planned_work_2weeks_table']) > 0:
                planned_2weeks = metrics['planned_work_2weeks_table'].copy()
                planned_2weeks["PlannedCompletion"] = pd.to_datetime(planned_2weeks["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
                planned_2weeks["Urgency"] = planned_2weeks["Urgency"].apply(
                    lambda x: f"🚨 {x}" if x == "Urgent" 
                    else f"⚠️ {x}" if x == "High Priority" 
                    else f"🔧 {x}"
                )
                
                st.dataframe(
                    planned_2weeks,
                    use_container_width=True,
                    column_config={
                        "Unit": st.column_config.TextColumn("🏠 Unit", width="small"),
                        "Room": st.column_config.TextColumn("🚪 Room", width="medium"),
                        "Component": st.column_config.TextColumn("🔧 Component", width="medium"),
                        "Trade": st.column_config.TextColumn("👷 Trade", width="medium"),
                        "Urgency": st.column_config.TextColumn("⚡ Priority", width="small"),
                        "PlannedCompletion": st.column_config.TextColumn("📅 Due Date", width="small")
                    }
                )
            else:
                st.success("✅ No work planned for the next 2 weeks")
        
        with subtab2:
            st.markdown(f"**Work planned for completion between 2 weeks and 1 month ({metrics['planned_work_month']} items)**")
            st.info("📅 Shows defects due between days 15-30 from today")
            if len(metrics['planned_work_month_table']) > 0:
                planned_month = metrics['planned_work_month_table'].copy()
                planned_month["PlannedCompletion"] = pd.to_datetime(planned_month["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
                planned_month["Urgency"] = planned_month["Urgency"].apply(
                    lambda x: f"🚨 {x}" if x == "Urgent" 
                    else f"⚠️ {x}" if x == "High Priority" 
                    else f"🔧 {x}"
                )
                
                st.dataframe(
                    planned_month,
                    use_container_width=True,
                    column_config={
                        "Unit": st.column_config.TextColumn("🏠 Unit", width="small"),
                        "Room": st.column_config.TextColumn("🚪 Room", width="medium"),
                        "Component": st.column_config.TextColumn("🔧 Component", width="medium"),
                        "Trade": st.column_config.TextColumn("👷 Trade", width="medium"),
                        "Urgency": st.column_config.TextColumn("⚡ Priority", width="small"),
                        "PlannedCompletion": st.column_config.TextColumn("📅 Due Date", width="small")
                    }
                )
            else:
                st.success("✅ No work planned for this period")
    
    # STEP 4: Download Options
    st.markdown("""
    <div class="step-container">
        <div class="step-header">📥 Step 4: Download Reports</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Always show both download options
    st.markdown("""
    <div class="download-section">
        <h3 style="text-align: center; margin-bottom: 1rem;">📦 Complete Report Package</h3>
        <p style="text-align: center;">Download both Excel and Word reports together in a convenient package.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("📦 Generate Complete Package", type="primary", use_container_width=True):
            try:
                with st.spinner("Generating complete report package..."):
                # Generate Excel using professional generator
                    if EXCEL_REPORT_AVAILABLE:
                        excel_buffer = generate_professional_excel_report(st.session_state.processed_data, metrics)
                        excel_bytes = excel_buffer.getvalue()  # Convert BytesIO to bytes
                    else:
                        st.error("❌ Excel generator not available")
                        st.stop()
                                
                    # Generate Word if available
                    word_bytes = None
                    if WORD_REPORT_AVAILABLE:
                        try:
                            from word_report_generator import generate_professional_word_report
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
                    from excel_report_generator import generate_filename
                    zip_filename = f"{generate_filename(metrics['building_name'], 'Package')}.zip"
                    
                    st.success("✅ Complete report package generated!")
                    st.download_button(
                        "📥 Download Complete Package (ZIP)",
                        data=zip_bytes,
                        file_name=zip_filename,
                        mime="application/zip",
                        use_container_width=True,
                        help="Contains Excel report, Word report (if available), and summary text file"
                    )
                    
                    # Show package contents
                    st.info(f"📋 Package includes: Excel report, {'Word report, ' if word_bytes else ''}and summary file")
                    
            except Exception as e:
                st.error(f"❌ Error generating package: {e}")
                st.code(traceback.format_exc())
    
    # Individual download options
    st.markdown("---")
    st.subheader("Individual Downloads")
    
    col1, col2 = st.columns(2)
    
    # Excel Download
    with col1:
        st.markdown("### 📊 Excel Report")
        st.write("Comprehensive Excel workbook with multiple sheets, charts, and detailed analysis.")
        
        if st.button("📊 Generate Excel Report", type="secondary", use_container_width=True):
            try:
                with st.spinner("Generating professional Excel report..."):
                    if EXCEL_REPORT_AVAILABLE:
                        excel_bytes = generate_professional_excel_report(st.session_state.processed_data, metrics)
                        
                        # Generate professional filename
                        from excel_report_generator import generate_filename
                        filename = f"{generate_filename(metrics['building_name'], 'Excel')}.xlsx"
                        
                        st.success("✅ Professional Excel report generated!")
                        st.download_button(
                            "📥 Download Excel Report",
                            data=excel_bytes,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    else:
                        st.error("❌ Excel generator not available")
                        if EXCEL_IMPORT_ERROR:
                            st.code(f"Import error: {EXCEL_IMPORT_ERROR}")
            except Exception as e:
                st.error(f"❌ Error generating Excel: {e}")
                st.code(traceback.format_exc())
    
    # Word Download
    with col2:
        st.markdown("### 📄 Word Report")
        
        if not WORD_REPORT_AVAILABLE:
            st.warning("Word generator not available")
            if WORD_IMPORT_ERROR:
                with st.expander("📋 Error Details"):
                    st.code(f"Import error: {WORD_IMPORT_ERROR}")
        else:
            st.write("Enhanced professional Word document with executive summary, visual analysis, actionable recommendations, and your custom images.")
            
            # Show image status for Word report
            current_images = [k for k, v in st.session_state.report_images.items() if v is not None]
            if current_images:
                st.info(f"📸 Will include: {', '.join(current_images)}")
            else:
                st.info("💡 Tip: Upload images in the sidebar to enhance your Word report!")
            
            if st.button("📄 Generate Word Report", type="secondary", use_container_width=True):
                try:
                    with st.spinner("Generating Word report with your images..."):
                        # Re-import to avoid stale import issues
                        from word_report_generator import generate_professional_word_report
                        
                        # Try enhanced version first, fallback to basic version
                        try:
                            doc = generate_professional_word_report(
                                st.session_state.processed_data, 
                                metrics, 
                                st.session_state.report_images
                            )
                            success_message = "✅ Enhanced Word report generated with your images!"
                        except TypeError:
                            # Fallback to old version without images
                            doc = generate_professional_word_report(
                                st.session_state.processed_data, 
                                metrics
                            )
                            success_message = "✅ Word report generated (basic version - update word_report_generator.py for image support)"
                        
                        # Save to bytes
                        buf = BytesIO()
                        doc.save(buf)
                        buf.seek(0)
                        word_bytes = buf.getvalue()
                        
                        # Generate professional filename
                        from excel_report_generator import generate_filename
                        filename = f"{generate_filename(metrics['building_name'], 'Word')}.docx"
                        
                        st.success(success_message)
                        st.download_button(
                            "📥 Download Enhanced Word Report",
                            data=word_bytes,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True
                        )
                except Exception as e:
                    st.error(f"❌ Error generating Word: {e}")
                    st.code(traceback.format_exc())
    
    # Report Statistics
    st.markdown("---")
    st.subheader("📈 Report Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 Total Sheets (Excel)", "7+", help="Executive Summary, Settlement Readiness, Trade Summary, etc.")
    
    with col2:
        st.metric("📊 Enhanced Tables", "5", help="Trade, Unit, Room, Urgent Defects, Planned Work summaries")
    
    with col3:
        total_records = len(st.session_state.processed_data) if st.session_state.processed_data is not None else 0
        st.metric("📄 Data Records", f"{total_records:,}", help="Total inspection records processed")
    
    with col4:
        file_size_est = "2-5 MB" if total_records > 1000 else "< 2 MB"
        st.metric("💾 Est. File Size", file_size_est, help="Estimated size of generated reports")

else:
    # Show upload section with enhanced UI
    st.markdown("""
    <div class="step-container">
        <div class="step-header">📤 Ready to Process Your Data</div>
    </div>
    """, unsafe_allow_html=True)
    
    if uploaded_csv is not None:
        try:
            preview_df = pd.read_csv(uploaded_csv)
            
            # Enhanced success message with file info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.success(f"📊 **Rows:** {len(preview_df):,}")
            with col2:
                st.success(f"📋 **Columns:** {len(preview_df.columns)}")
            with col3:
                file_size = uploaded_csv.size / 1024  # Convert to KB
                st.success(f"💾 **Size:** {file_size:.1f} KB")
            
            # Enhanced preview with column analysis
            with st.expander("👀 Data Preview & Analysis", expanded=True):
                # Show column information
                st.markdown("**📋 Column Information:**")
                col_info = pd.DataFrame({
                    'Column': preview_df.columns,
                    'Type': [str(dtype) for dtype in preview_df.dtypes],
                    'Non-Null': [preview_df[col].notna().sum() for col in preview_df.columns],
                    'Null %': [f"{(preview_df[col].isna().sum() / len(preview_df) * 100):.1f}%" for col in preview_df.columns]
                })
                st.dataframe(col_info, use_container_width=True, height=200)
                
                st.markdown("**📊 Data Sample:**")
                st.dataframe(preview_df.head(10), use_container_width=True)
                st.caption(f"Showing first 10 rows of {len(preview_df):,} total rows")
                
                # Data quality indicators
                missing_data_pct = (preview_df.isna().sum().sum() / (len(preview_df) * len(preview_df.columns))) * 100
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if missing_data_pct < 5:
                        st.success(f"✅ Data Quality: Excellent ({missing_data_pct:.1f}% missing)")
                    elif missing_data_pct < 15:
                        st.warning(f"⚠️ Data Quality: Good ({missing_data_pct:.1f}% missing)")
                    else:
                        st.error(f"❌ Data Quality: Poor ({missing_data_pct:.1f}% missing)")
                
                with col2:
                    duplicate_rows = preview_df.duplicated().sum()
                    if duplicate_rows == 0:
                        st.success("✅ No Duplicates")
                    else:
                        st.warning(f"⚠️ {duplicate_rows} Duplicates")
                
                with col3:
                    required_cols = ['Unit', 'Room', 'Component', 'StatusClass']
                    missing_cols = [col for col in required_cols if col not in preview_df.columns]
                    if not missing_cols:
                        st.success("✅ All Required Columns")
                    else:
                        st.info(f"ℹ️ Will auto-generate: {', '.join(missing_cols)}")
            
        except Exception as e:
            st.error(f"❌ Error reading CSV: {e}")
            st.markdown("""
            <div class="error-box">
                <strong>Common issues:</strong>
                <ul>
                    <li>File encoding problems (try saving as UTF-8)</li>
                    <li>Corrupted file</li>
                    <li>Unsupported CSV format</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="info-box">
            <h4>📤 Ready to Upload Your Inspection Data</h4>
            <p>Please upload your iAuditor CSV file to begin processing. The system will:</p>
            <ul>
                <li>✅ Validate the data quality</li>
                <li>🔄 Apply trade mapping</li>
                <li>📊 Generate comprehensive analytics</li>
                <li>📋 Create professional reports</li>
                <li>🚨 Identify urgent defects</li>
                <li>📅 Track planned work schedules</li>
                <li>🔍 Enable quick unit lookups</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# Enhanced Footer with streamlined user info
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 2rem; border-radius: 10px; margin-top: 2rem;">
    <h4 style="color: #2E3A47; margin-bottom: 1rem;">🏢 Professional Inspection Report Processor v2.1</h4>
    <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap;">
        <div><strong>📊 Excel Reports:</strong> Multi-sheet analysis</div>
        <div><strong>📄 Word Reports:</strong> Executive summaries</div>
        <div><strong>🚨 Urgent Tracking:</strong> Priority defects</div>
        <div><strong>🔍 Unit Lookup:</strong> Instant defect search</div>
        <div><strong>📅 Work Planning:</strong> Scheduled completion dates</div>
        <div><strong>🔒 Secure Processing:</strong> Authenticated access</div>
    </div>
    <p style="margin-top: 1rem; color: #666; font-size: 0.9em;">
        Built with Streamlit • Powered by Python • Updated search unit • Logged in as: {user['name']}
    </p>
</div>
""", unsafe_allow_html=True)