# streamlit_app.py
# Building Inspection Report System – Full App (finished)

import os
import time
import json
import uuid
import hashlib
import sqlite3
import zipfile
import traceback
from io import BytesIO, StringIO
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import pytz
import streamlit as st

# ---------------------------------------------------------------------
# Data persistence helpers (your module)
# ---------------------------------------------------------------------
from data_persistence import (
    DataPersistenceManager,
    save_trade_mapping_to_database,
    load_trade_mapping_from_database,
)

# ---------------------------------------------------------------------
# Report generators (Excel required, Word optional)
# ---------------------------------------------------------------------
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
# AUTHENTICATION + ROLE CAPABILITIES
# =============================================================================

class DatabaseAuthManager:
    """Database-powered authentication manager for Streamlit"""

    def __init__(self, db_path="inspection_system.db"):
        self.db_path = db_path
        self.session_timeout = 8 * 60 * 60  # 8 hours

        self._init_database_if_needed()

        # Capability map (adds can_view_data to surface in sidebar)
        self.role_capabilities = {
            "admin": {
                "can_upload": True,
                "can_process": True,
                "can_manage_users": True,
                "can_approve_defects": True,
                "can_view_all": True,
                "can_view_data": True,
                "can_generate_reports": True,
                "dashboard_type": "admin",
            },
            "property_developer": {
                "can_upload": False,
                "can_process": False,
                "can_manage_users": False,
                "can_approve_defects": True,
                "can_view_all": False,
                "can_view_data": True,
                "can_generate_reports": True,
                "dashboard_type": "portfolio",
            },
            "project_manager": {
                "can_upload": True,
                "can_process": True,
                "can_manage_users": False,
                "can_approve_defects": True,
                "can_view_all": False,
                "can_view_data": True,
                "can_generate_reports": True,
                "dashboard_type": "project",
            },
            "inspector": {
                "can_upload": True,
                "can_process": True,
                "can_manage_users": False,
                "can_approve_defects": False,
                "can_view_all": False,
                "can_view_data": True,
                "can_generate_reports": True,
                "dashboard_type": "inspector",
            },
            "builder": {
                "can_upload": False,
                "can_process": False,
                "can_manage_users": False,
                "can_approve_defects": False,
                "can_view_all": False,
                "can_view_data": True,
                "can_generate_reports": True,
                "dashboard_type": "builder",
            },
        }

    def _init_database_if_needed(self):
        if not os.path.exists(self.db_path):
            st.error("Database not found! Please run: python complete_database_setup.py")
            st.stop()

    def _hash_password(self, password: str) -> str:
        salt = "inspection_app_salt_2024"
        return hashlib.sha256((password + salt).encode()).hexdigest()

    def authenticate(self, username: str, password: str) -> Tuple[bool, str]:
        if not username or not password:
            return False, "Please enter username and password"

        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            pw_hash = self._hash_password(password)
            cur.execute(
                """
                SELECT username, full_name, email, role, is_active
                FROM users
                WHERE username = ? AND password_hash = ? AND is_active = 1
                """,
                (username, pw_hash),
            )
            user_data = cur.fetchone()
            if user_data:
                cur.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?", (username,))
                conn.commit()
                conn.close()
                return True, "Login successful"
            conn.close()
            return False, "Invalid username or password"
        except Exception as e:
            return False, f"Database error: {e}"

    def get_user_info(self, username: str) -> Optional[Dict]:
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT username, full_name, email, role, is_active, last_login
                FROM users WHERE username = ?
                """,
                (username,),
            )
            row = cur.fetchone()
            conn.close()
            if row:
                return {
                    "username": row[0],
                    "full_name": row[1],
                    "email": row[2],
                    "role": row[3],
                    "is_active": row[4],
                    "last_login": row[5],
                    "capabilities": self.role_capabilities.get(row[3], {}),
                }
            return None
        except Exception:
            return None

    def create_session(self, username: str):
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
        if not st.session_state.get("authenticated", False):
            return False
        if not st.session_state.get("login_time"):
            return False
        if time.time() - st.session_state.login_time > self.session_timeout:
            self.logout()
            return False
        return True

    def logout(self):
        for k in [
            "authenticated",
            "username",
            "user_name",
            "user_email",
            "user_role",
            "login_time",
            "user_capabilities",
            "dashboard_type",
        ]:
            if k in st.session_state:
                del st.session_state[k]
        for k in ["trade_mapping", "processed_data", "metrics", "step_completed", "report_images"]:
            if k in st.session_state:
                del st.session_state[k]

    def get_current_user(self) -> Dict:
        return {
            "username": st.session_state.get("username", ""),
            "name": st.session_state.get("user_name", "User"),
            "email": st.session_state.get("user_email", ""),
            "role": st.session_state.get("user_role", "user"),
            "capabilities": st.session_state.get("user_capabilities", {}),
            "dashboard_type": st.session_state.get("dashboard_type", "inspector"),
        }

    def can_user_perform_action(self, action: str) -> bool:
        capabilities = st.session_state.get("user_capabilities", {})
        return bool(capabilities.get(action, False))

    def change_password(self, username, old_password, new_password):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            old_hash = self._hash_password(old_password)
            cur.execute(
                "SELECT 1 FROM users WHERE username = ? AND password_hash = ?",
                (username, old_hash),
            )
            if not cur.fetchone():
                conn.close()
                return False, "Current password is incorrect"
            if len(new_password) < 6:
                conn.close()
                return False, "New password must be at least 6 characters"
            new_hash = self._hash_password(new_password)
            cur.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_hash, username))
            conn.commit()
            conn.close()
            return True, "Password changed successfully"
        except Exception as e:
            return False, f"Database error: {e}"


@st.cache_resource
def get_auth_manager():
    return DatabaseAuthManager()

# =============================================================================
# LOGIN PAGE
# =============================================================================

def show_enhanced_login_page():
    st.markdown(
        """
    <div style="max-width: 400px; margin: 2rem auto; padding: 2rem; 
                background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h2 style="text-align: center; color: #1976d2; margin-bottom: 2rem;">
            Building Inspection Report System
        </h2>
        <h3 style="text-align: center; color: #666; margin-bottom: 2rem;">
            Please Login to Continue
        </h3>
    </div>
    """,
        unsafe_allow_html=True,
    )

    auth = get_auth_manager()
    with st.form("enhanced_login_form"):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### Login")
            u = st.text_input("Username", placeholder="Enter your username")
            p = st.text_input("Password", type="password", placeholder="Enter your password")
            if st.form_submit_button("Login", use_container_width=True, type="primary"):
                if u and p:
                    ok, msg = auth.authenticate(u, p)
                    if ok:
                        auth.create_session(u)
                        st.success(msg)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Please enter both username and password")

    with st.expander("Demo Credentials", expanded=False):
        st.info(
            """
        **System Administrator:** admin / admin123  
        **Property Developer:** developer1 / dev123  
        **Project Manager:** manager1 / mgr123  
        **Site Inspector:** inspector / inspector123  
        **Builder:** builder1 / build123
        """
        )

# =============================================================================
# SIDEBAR MENU
# =============================================================================

def show_enhanced_user_menu() -> bool:
    auth = get_auth_manager()
    if not auth.is_session_valid():
        return False

    user = auth.get_current_user()
    keyp = f"sidebar_{user['username']}_"

    with st.sidebar:
        st.markdown("---")
        st.markdown("### User Information")
        st.markdown(
            f"""
        **Name:** {user['name']}  
        **Role:** {user['role'].replace('_', ' ').title()}  
        **Email:** {user['email']}  
        **Access:** {user['capabilities'].get('dashboard_type', 'standard').title()}
        """
        )

        st.markdown("---")
        st.markdown("### Account")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Change Password", use_container_width=True):
                st.session_state.show_password_change = True
        with c2:
            if st.button("Logout", use_container_width=True, type="primary"):
                auth.logout()
                st.success("Logged out successfully!")
                st.rerun()

        if st.session_state.get("show_password_change", False):
            st.markdown("---")
            st.markdown("### Change Password")
            with st.form("password_change_form"):
                old = st.text_input("Current Password", type="password")
                new = st.text_input("New Password", type="password")
                confirm = st.text_input("Confirm New Password", type="password")
                c1, c2 = st.columns(2)
                with c1:
                    if st.form_submit_button("Update", use_container_width=True):
                        if new != confirm:
                            st.error("New passwords don't match")
                        elif len(new) < 6:
                            st.error("Password must be at least 6 characters")
                        else:
                            ok, msg = auth.change_password(user["username"], old, new)
                            if ok:
                                st.success(msg)
                                st.session_state.show_password_change = False
                                st.rerun()
                            else:
                                st.error(msg)
                with c2:
                    if st.form_submit_button("Cancel", use_container_width=True):
                        st.session_state.show_password_change = False
                        st.rerun()

        if user["role"] == "admin":
            st.markdown("---")
            st.markdown("### Administrator Access")
            st.success("🔑 **Full System Access**")
            try:
                conn = sqlite3.connect("inspection_system.db")
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
                active_users = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM projects")
                total_projects = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM buildings")
                total_buildings = cur.fetchone()[0]
                conn.close()
                st.markdown("### System Status")
                a, b = st.columns(2)
                with a:
                    st.metric("Active Users", active_users)
                    st.metric("Projects", total_projects)
                with b:
                    st.metric("Buildings", total_buildings)
            except Exception as e:
                st.caption(f"System metrics unavailable: {e}")
        else:
            st.markdown("---")
            st.markdown("### Your Access Rights")
            caps = user["capabilities"]
            ops = []
            if caps.get("can_upload"):
                ops.append("📤 Upload Data")
            if caps.get("can_process"):
                ops.append("⚙️ Process Data")
            if caps.get("can_view_data"):
                ops.append("👁️ View Data")
            if ops:
                st.markdown("**Data Operations:**")
                for p in ops:
                    st.success(p)
            if caps.get("can_generate_reports"):
                st.markdown("**Reports:**")
                st.success("📊 Generate Reports")
            defect_ops = []
            if caps.get("can_approve_defects"):
                defect_ops.append("✅ Approve Defects")
            if caps.get("can_update_defect_status"):
                defect_ops.append("🔄 Update Status")
            if defect_ops:
                st.markdown("**Defect Management:**")
                for p in defect_ops:
                    st.success(p)

        # Quick unit lookup
        if st.session_state.get("processed_data") is not None:
            st.markdown("---")
            st.header("Quick Unit Lookup")
            all_units = sorted(st.session_state.processed_data["Unit"].astype(str).unique())
            selected = st.selectbox(
                "Select Unit Number:",
                options=[""] + all_units,
                key=f"{keyp}unit_lookup",
            )
            if selected:
                unit_defects = lookup_unit_defects(st.session_state.processed_data, selected)
                if len(unit_defects) > 0:
                    st.markdown(f"**Unit {selected} Defects:**")
                    urgent_count = (unit_defects["Urgency"] == "Urgent").sum()
                    high_count = (unit_defects["Urgency"] == "High Priority").sum()
                    normal_count = (unit_defects["Urgency"] == "Normal").sum()
                    if urgent_count:
                        st.error(f"Urgent: {urgent_count}")
                    if high_count:
                        st.warning(f"High Priority: {high_count}")
                    if normal_count:
                        st.info(f"Normal: {normal_count}")
                    for _, d in unit_defects.iterrows():
                        icon = "🚨" if d["Urgency"] == "Urgent" else "⚠️" if d["Urgency"] == "High Priority" else "🔧"
                        st.caption(
                            f"{icon} {d['Room']} - {d['Component']} ({d['Trade']}) - Due: {d['PlannedCompletion']}"
                        )
                else:
                    st.success(f"Unit {selected} has no defects!")

        # Optional images for Word report (only if can upload)
        if get_auth_manager().can_user_perform_action("can_upload"):
            st.markdown("---")
            st.header("Word Report Images")
            st.markdown("Upload images to enhance your Word report (optional):")
            with st.expander("Upload Report Images", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    logo_upload = st.file_uploader("Company Logo", type=["png", "jpg", "jpeg"])
                with c2:
                    cover_upload = st.file_uploader("Cover Image", type=["png", "jpg", "jpeg"])
                if st.button("Save Images for Report"):
                    images_saved = 0
                    import tempfile
                    tmp = tempfile.gettempdir()
                    if logo_upload:
                        logo_path = os.path.join(tmp, f"logo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                        with open(logo_path, "wb") as f:
                            f.write(logo_upload.getbuffer())
                        st.session_state.report_images["logo"] = logo_path
                        images_saved += 1
                    if cover_upload:
                        cover_path = os.path.join(tmp, f"cover_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                        with open(cover_path, "wb") as f:
                            f.write(cover_upload.getbuffer())
                        st.session_state.report_images["cover"] = cover_path
                        images_saved += 1
                    st.success(f"{images_saved} image(s) saved!") if images_saved else st.info("No images uploaded.")
                current_images = [k for k, v in st.session_state.report_images.items() if v]
                if current_images:
                    st.info(f"Current images ready: {', '.join(current_images)}")

        st.markdown("---")
        if st.button("Reset All", help="Clear all data and start over"):
            for key in ["trade_mapping", "processed_data", "metrics", "step_completed", "building_info"]:
                if key in st.session_state:
                    if key == "step_completed":
                        st.session_state[key] = {"mapping": False, "processing": False}
                    elif key == "building_info":
                        st.session_state[key] = {
                            "name": "Professional Building Complex",
                            "address": "123 Professional Street\nMelbourne, VIC 3000",
                        }
                    else:
                        del st.session_state[key]
            st.rerun()

    return True

# =============================================================================
# DATA PIPELINE (PROCESS + PERSIST)
# =============================================================================

def process_inspection_data_with_persistence(df, mapping, building_info, username):
    processed_df, metrics = process_inspection_data(df, mapping, building_info)
    persistence_manager = DataPersistenceManager()
    ok, inspection_id = persistence_manager.save_processed_inspection(
        processed_df, metrics, username
    )
    st.session_state.processed_data = processed_df
    st.session_state.metrics = metrics
    st.session_state.step_completed["processing"] = True
    if ok:
        st.success(f"Data processed and saved! Building: {metrics['building_name']}")
    else:
        st.error(f"Data processing succeeded but database save failed: {inspection_id}")
    return processed_df, metrics, ok

def initialize_user_data():
    if st.session_state.processed_data is None:
        pm = DataPersistenceManager()
        processed_data, metrics = pm.load_latest_inspection()
        if processed_data is not None and metrics is not None:
            st.session_state.processed_data = processed_data
            st.session_state.metrics = metrics
            st.session_state.step_completed["processing"] = True
            return True
    return False

def load_trade_mapping():
    if len(st.session_state.trade_mapping) == 0:
        mapping_df = load_trade_mapping_from_database()
        if len(mapping_df) > 0:
            st.session_state.trade_mapping = mapping_df
            st.session_state.step_completed["mapping"] = True
            return True
    return False

# =============================================================================
# DASHBOARDS (ADMIN/DEV/PM/BUILDER)
# =============================================================================

def show_admin_dashboard():
    try:
        from enhanced_admin_management import show_enhanced_admin_dashboard
        show_enhanced_admin_dashboard()
    except Exception as e:
        st.error(f"Enhanced admin features not available: {e}")
        st.info("Using basic admin interface.")
        show_basic_admin_interface()

def show_basic_admin_interface():
    st.markdown("#### Basic User Administration")
    st.caption("This fallback appears if the enhanced admin module is not present.")
    try:
        conn = sqlite3.connect("inspection_system.db")
        cur = conn.cursor()
        cur.execute("SELECT username, full_name, role, is_active, last_login FROM users ORDER BY role, username")
        rows = cur.fetchall()
        conn.close()
        df = pd.DataFrame(rows, columns=["Username", "Full Name", "Role", "Active", "Last Login"])
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Unable to load users: {e}")

def show_enhanced_developer_dashboard():
    st.markdown("### Portfolio Executive Dashboard")
    pm = DataPersistenceManager()
    stats = pm.get_database_stats()
    with st.expander("System Status", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Inspections", stats.get("total_inspections", 0))
        with c2:
            st.metric("Active Inspections", stats.get("active_inspections", 0))
        with c3:
            st.metric("Total Defects", stats.get("total_defects", 0))

    if st.session_state.metrics is not None:
        metrics = st.session_state.metrics
        st.markdown("### Current Building Analysis")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Building", metrics["building_name"])
        with c2:
            st.metric("Total Units", metrics["total_units"])
        with c3:
            st.metric("Ready for Settlement", f"{metrics['ready_units']} ({metrics['ready_pct']:.1f}%)")
        with c4:
            st.metric("Urgent Issues", metrics["urgent_defects"])

        tab1, tab2, tab3 = st.tabs(["Trade Summary", "Unit Status", "Urgent Items"])
        with tab1:
            if len(metrics["summary_trade"]) > 0:
                st.dataframe(metrics["summary_trade"], use_container_width=True)
            else:
                st.info("No trade defects found")
        with tab2:
            if len(metrics["summary_unit"]) > 0:
                st.dataframe(metrics["summary_unit"], use_container_width=True)
            else:
                st.info("No unit defects found")
        with tab3:
            if len(metrics["urgent_defects_table"]) > 0:
                urgent_display = metrics["urgent_defects_table"].copy()
                urgent_display["PlannedCompletion"] = pd.to_datetime(
                    urgent_display["PlannedCompletion"]
                ).dt.strftime("%Y-%m-%d")
                st.dataframe(urgent_display, use_container_width=True)
                st.error(f"**{len(urgent_display)} URGENT defects require immediate attention!**")
            else:
                st.success("No urgent defects found!")

        st.markdown("---")
        st.markdown("### Executive Reports")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Generate Executive Summary", type="primary", use_container_width=True):
                try:
                    if EXCEL_REPORT_AVAILABLE:
                        excel_buffer = generate_professional_excel_report(
                            st.session_state.processed_data, metrics
                        )
                        filename = f"Executive_Summary_{metrics['building_name']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                        st.success("Executive summary generated!")
                        st.download_button(
                            "Download Executive Summary",
                            data=excel_buffer.getvalue(),
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )
                    else:
                        st.error("Excel report generator not available")
                except Exception as e:
                    st.error(f"Error generating executive summary: {e}")
        with c2:
            if st.button("Portfolio Analytics", type="secondary", use_container_width=True):
                st.info("Portfolio analytics report would be generated here")
    else:
        st.warning("No inspection data available. Contact your team to process inspection data.")

def show_enhanced_builder_dashboard():
    st.markdown("### Builder Workspace")
    pm = DataPersistenceManager()
    open_defects = pm.get_defects_by_status("open")
    if open_defects:
        st.success(f"You have {len(open_defects)} open defects to work on")
        df_cols = [
            "ID",
            "Inspection ID",
            "Unit",
            "Unit Type",
            "Room",
            "Component",
            "Trade",
            "Urgency",
            "Planned Completion",
            "Status",
            "Created At",
            "Building",
        ]
        df = pd.DataFrame(open_defects, columns=df_cols)
        urgent_df = df[df["Urgency"] == "Urgent"]
        high_priority_df = df[df["Urgency"] == "High Priority"]
        normal_df = df[df["Urgency"] == "Normal"]
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Urgent", len(urgent_df))
        with c2:
            st.metric("High Priority", len(high_priority_df))
        with c3:
            st.metric("Normal", len(normal_df))
        st.markdown("**Your Assigned Defects:**")
        display_df = df[
            ["Unit", "Room", "Component", "Trade", "Urgency", "Planned Completion", "Building"]
        ].copy()
        st.dataframe(display_df, use_container_width=True)

        st.markdown("---")
        st.markdown("### Work Reports")
        c1, c2, c3 = st.columns(3)

        with c1:
            if st.button("Today's Work List", type="primary", use_container_width=True):
                today_work = df[pd.to_datetime(df["Planned Completion"]) <= pd.Timestamp.now() + pd.Timedelta(days=1)]
                if len(today_work) > 0:
                    csv = today_work.to_csv(index=False)
                    st.download_button(
                        "Download Today's Work List",
                        data=csv,
                        file_name=f"today_work_list_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                else:
                    st.info("No work scheduled for today")

        with c2:
            if st.button("Weekly Schedule", type="secondary", use_container_width=True):
                week_work = df[pd.to_datetime(df["Planned Completion"]) <= pd.Timestamp.now() + pd.Timedelta(days=7)]
                if len(week_work) > 0:
                    csv = week_work.to_csv(index=False)
                    st.download_button(
                        "Download Weekly Schedule",
                        data=csv,
                        file_name=f"weekly_schedule_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                else:
                    st.info("No work scheduled for this week")

        with c3:
            if st.button("Priority Items", use_container_width=True):
                priority_work = df[df["Urgency"].isin(["Urgent", "High Priority"])]
                if len(priority_work) > 0:
                    csv = priority_work.to_csv(index=False)
                    st.download_button(
                        "Download Priority Items",
                        data=csv,
                        file_name=f"priority_items_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                else:
                    st.success("No priority items!")
    else:
        st.info("No open defects assigned. Check with your project manager.")

def show_enhanced_project_manager_dashboard():
    import sqlite3
    st.markdown("### Project Management Dashboard")
    pm = DataPersistenceManager()
    accessible_buildings = pm.get_buildings_for_user(st.session_state.username)
    if len(accessible_buildings) == 0:
        st.warning("No buildings assigned to your projects. Contact administrator for building access.")
        return

    st.markdown("#### Select Building to Manage")
    options, lookup = [], {}
    for b in accessible_buildings:
        try:
            building_id = b[0]
            building_name = b[1]
            total_units = b[3]
            project_name = b[4]
            last_inspection = b[5] if len(b) > 5 else "No data"
            display = f"{building_name} ({project_name}) - {total_units} units"
            options.append(display)
            lookup[display] = {
                "id": building_id,
                "name": building_name,
                "project": project_name,
                "units": total_units,
                "last_inspection": last_inspection,
            }
        except Exception:
            continue

    if not options:
        st.error("No valid building data available. Please check your database.")
        return

    chosen = st.selectbox("Choose building to manage:", options=options)
    if not chosen:
        return

    selected = lookup[chosen]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Building", selected["name"])
    with c2:
        st.metric("Project", selected["project"])
    with c3:
        st.metric("Total Units", selected["units"])
    with c4:
        try:
            d = str(selected["last_inspection"])
            st.metric("Last Inspection", d[:10] if len(d) > 10 else d)
        except Exception:
            st.metric("Last Inspection", "None")

    summary = get_manual_building_summary(selected["id"], pm.db_path)
    if summary:
        st.markdown("---")
        st.markdown("#### Building Management Overview")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Defects", summary.get("total_defects", 0))
        with c2:
            st.metric("Urgent Defects", summary.get("urgent_count", 0))
        with c3:
            total_defects = summary.get("total_defects", 0)
            total_units = summary.get("total_units", selected["units"])
            completion_rate = max(0, (1 - (total_defects / max(total_units * 10, 1))) * 100)
            st.metric("Completion Rate", f"{completion_rate:.1f}%")

        st.markdown("#### Management Actions")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("View Building Details", use_container_width=True):
                st.session_state.pm_view_building = selected["id"]
                st.info("Detailed building view would load here")
        with c2:
            if st.button("Generate Building Report", use_container_width=True):
                try:
                    conn = sqlite3.connect(pm.db_path)
                    cur = conn.cursor()
                    cur.execute(
                        """
                        SELECT id.unit_number, id.room, id.component, id.trade, 
                               id.urgency, id.planned_completion, id.status
                        FROM inspection_defects id
                        JOIN processed_inspections pi ON id.inspection_id = pi.id
                        WHERE pi.building_id = ? AND pi.is_active = 1
                        ORDER BY id.urgency, id.unit_number
                        """,
                        (selected["id"],),
                    )
                    rows = cur.fetchall()
                    conn.close()
                    if rows:
                        df = pd.DataFrame(
                            rows,
                            columns=[
                                "Unit",
                                "Room",
                                "Component",
                                "Trade",
                                "Urgency",
                                "Planned Completion",
                                "Status",
                            ],
                        )
                        csv = df.to_csv(index=False)
                        st.download_button(
                            "Download Building Report (CSV)",
                            data=csv,
                            file_name=f"building_report_{selected['name'].replace(' ', '_')}.csv",
                            mime="text/csv",
                            use_container_width=True,
                        )
                    else:
                        st.info("No defect data available for this building")
                except Exception as e:
                    st.error(f"Error generating report: {e}")

        st.markdown("#### Recent Defects Summary")
        try:
            conn = sqlite3.connect(pm.db_path)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id.urgency, COUNT(*) as count
                FROM inspection_defects id
                JOIN processed_inspections pi ON id.inspection_id = pi.id
                WHERE pi.building_id = ? AND pi.is_active = 1
                GROUP BY id.urgency
                ORDER BY CASE id.urgency 
                    WHEN 'Urgent' THEN 1 
                    WHEN 'High Priority' THEN 2 
                    ELSE 3 END
                """,
                (selected["id"],),
            )
            summary_rows = cur.fetchall()
            conn.close()
            if summary_rows:
                for urgency, count in summary_rows:
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

def get_manual_building_summary(building_id: str, db_path: str) -> dict:
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT b.name, b.address, b.total_units FROM buildings b WHERE b.id = ?",
            (building_id,),
        )
        info = cur.fetchone()
        if not info:
            conn.close()
            return {}
        cur.execute(
            """
            SELECT COUNT(*) FROM inspection_defects id
            JOIN processed_inspections pi ON id.inspection_id = pi.id
            WHERE pi.building_id = ? AND pi.is_active = 1
            """,
            (building_id,),
        )
        total_defects = cur.fetchone()[0]
        cur.execute(
            """
            SELECT COUNT(*) FROM inspection_defects id
            JOIN processed_inspections pi ON id.inspection_id = pi.id
            WHERE pi.building_id = ? AND pi.is_active = 1 AND id.urgency = 'Urgent'
            """,
            (building_id,),
        )
        urgent = cur.fetchone()[0]
        conn.close()
        return {
            "name": info[0],
            "address": info[1],
            "total_units": info[2],
            "total_defects": total_defects,
            "urgent_count": urgent,
        }
    except Exception as e:
        print(f"Error summary: {e}")
        return {}

def load_building_defects_paginated(building_id, page=1, urgency_filter="All"):
    try:
        pm = DataPersistenceManager()
        conn = sqlite3.connect(pm.db_path)
        cur = conn.cursor()
        where_clause = "WHERE pi.building_id = ?"
        params = [building_id]
        if urgency_filter != "All":
            where_clause += " AND id.urgency = ?"
            params.append(urgency_filter)
        cur.execute(
            f"""
            SELECT COUNT(*)
            FROM inspection_defects id
            JOIN processed_inspections pi ON id.inspection_id = pi.id
            {where_clause} AND pi.is_active = 1
            """,
            params,
        )
        total_rows = cur.fetchone()[0]
        page_size = 50
        offset = (page - 1) * page_size
        cur.execute(
            f"""
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
            """,
            params + [page_size, offset],
        )
        rows = cur.fetchall()
        conn.close()
        columns = [
            "Unit",
            "Room",
            "Component",
            "Trade",
            "Urgency",
            "Planned Completion",
            "Status",
        ]
        return {
            "data": pd.DataFrame(rows, columns=columns),
            "total_rows": total_rows,
            "total_pages": (total_rows + page_size - 1) // page_size,
            "current_page": page,
            "page_size": page_size,
        }
    except Exception as e:
        return {"error": str(e)}

def get_building_team_members(building_id):
    try:
        conn = sqlite3.connect("inspection_system.db")
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT u.full_name, u.role, up.permission_level, u.last_login
            FROM users u
            JOIN user_permissions up ON u.username = up.username
            JOIN buildings b ON (
                (up.resource_type = 'building' AND up.resource_id = b.id) OR
                (up.resource_type = 'project' AND up.resource_id = b.project_id)
            )
            WHERE b.id = ? AND u.is_active = 1
            ORDER BY u.role, u.full_name
            """,
            (building_id,),
        )
        results = cur.fetchall()
        conn.close()
        return [
            {"name": r[0], "role": r[1], "permission_level": r[2], "last_activity": r[3]} for r in results
        ]
    except Exception as e:
        print(f"Error team members: {e}")
        return []

# =============================================================================
# PROCESSOR (CSV → LONG FORM → METRICS)
# =============================================================================

def process_inspection_data(df, mapping, building_info):
    df = df.copy()

    # Unit
    if "Lot Details_Lot Number" in df.columns and df["Lot Details_Lot Number"].notna().any():
        df["Unit"] = df["Lot Details_Lot Number"].astype(str).str.strip()
    elif "Title Page_Lot number" in df.columns and df["Title Page_Lot number"].notna().any():
        df["Unit"] = df["Title Page_Lot number"].astype(str).str.strip()
    else:
        def extract_unit(audit_name):
            parts = str(audit_name).split("/")
            if len(parts) >= 3:
                cand = parts[1].strip()
                if len(cand) <= 6 and any(ch.isdigit() for ch in cand):
                    return cand
            return f"Unit_{hash(str(audit_name)) % 1000}"
        df["Unit"] = (
            df["auditName"].apply(extract_unit)
            if "auditName" in df.columns
            else [f"Unit_{i}" for i in range(1, len(df) + 1)]
        )

    # Unit type
    def derive_unit_type(row):
        unit_type = str(row.get("Pre-Settlement Inspection_Unit Type", "")).strip()
        townhouse_type = str(row.get("Pre-Settlement Inspection_Townhouse Type", "")).strip()
        apartment_type = str(row.get("Pre-Settlement Inspection_Apartment Type", "")).strip()
        if unit_type.lower() == "townhouse":
            return f"{townhouse_type} Townhouse" if townhouse_type else "Townhouse"
        elif unit_type.lower() == "apartment":
            return f"{apartment_type} Apartment" if apartment_type else "Apartment"
        return unit_type or "Unknown Type"

    df["UnitType"] = df.apply(derive_unit_type, axis=1)

    # Inspection columns
    inspection_cols = [
        c for c in df.columns if c.startswith("Pre-Settlement Inspection_") and not c.endswith("_notes")
    ]
    if not inspection_cols:
        inspection_cols = [
            c
            for c in df.columns
            if any(k in c.lower() for k in ["inspection", "check", "item", "defect", "issue", "status"])
        ]

    # Melt
    long_df = df.melt(
        id_vars=["Unit", "UnitType"],
        value_vars=inspection_cols,
        var_name="InspectionItem",
        value_name="Status",
    )

    # Split to room/component
    parts = long_df["InspectionItem"].str.split("_", n=2, expand=True)
    if len(parts.columns) >= 3:
        long_df["Room"] = parts[1]
        long_df["Component"] = parts[2].str.replace(r"\.\d+$", "", regex=True)
        long_df["Component"] = long_df["Component"].apply(lambda x: x.split("_")[-1] if isinstance(x, str) else x)
    else:
        long_df["Room"] = "General"
        long_df["Component"] = long_df["InspectionItem"].str.replace("Pre-Settlement Inspection_", "")

    # Remove meta rows
    metadata_rooms = ["Unit Type", "Building Type", "Townhouse Type", "Apartment Type"]
    metadata_components = ["Room Type"]
    long_df = long_df[~long_df["Room"].isin(metadata_rooms)]
    long_df = long_df[~long_df["Component"].isin(metadata_components)]

    # Status/Urgency
    def classify_status(val):
        if pd.isna(val) or str(val).strip() == "":
            return "Blank"
        s = str(val).strip().lower()
        if s in ["✓", "✔", "ok", "pass", "passed", "good", "satisfactory"]:
            return "OK"
        return "Not OK"

    def classify_urgency(val, component, room):
        if pd.isna(val):
            return "Normal"
        v = str(val).strip().lower()
        comp = str(component).lower()
        rm = str(room).lower()
        urgent_kw = ["urgent", "immediate", "safety", "hazard", "dangerous", "critical", "severe"]
        safety_comps = ["fire", "smoke", "electrical", "gas", "water", "security", "lock", "door handle"]
        if any(k in v for k in urgent_kw):
            return "Urgent"
        if any(s in comp for s in safety_comps):
            return "High Priority"
        if "entry" in rm and "door" in comp:
            return "High Priority"
        return "Normal"

    long_df["StatusClass"] = long_df["Status"].apply(classify_status)
    long_df["Urgency"] = long_df.apply(
        lambda r: classify_urgency(r["Status"], r["Component"], r["Room"]), axis=1
    )

    # Trade mapping
    merged = long_df.merge(mapping, on=["Room", "Component"], how="left")
    merged["Trade"] = merged["Trade"].fillna("Unknown Trade")

    # Planned completion
    def assign_planned_completion(urgency):
        base = datetime.now()
        if urgency == "Urgent":
            return base + timedelta(days=3)
        if urgency == "High Priority":
            return base + timedelta(days=7)
        return base + timedelta(days=14)

    merged["PlannedCompletion"] = merged["Urgency"].apply(assign_planned_completion)

    final_df = merged[
        ["Unit", "UnitType", "Room", "Component", "StatusClass", "Trade", "Urgency", "PlannedCompletion"]
    ]

    # Settlement readiness
    defects_only = final_df[final_df["StatusClass"] == "Not OK"]
    defects_per_unit = defects_only.groupby("Unit").size() if len(defects_only) > 0 else pd.Series(dtype=int)
    ready_units = (defects_per_unit <= 2).sum() if len(defects_per_unit) > 0 else 0
    minor_work_units = ((defects_per_unit > 2) & (defects_per_unit <= 7)).sum() if len(defects_per_unit) > 0 else 0
    major_work_units = ((defects_per_unit > 7) & (defects_per_unit <= 15)).sum() if len(defects_per_unit) > 0 else 0
    extensive_work_units = (defects_per_unit > 15).sum() if len(defects_per_unit) > 0 else 0

    units_with_defects = set(defects_per_unit.index)
    all_units = set(final_df["Unit"].dropna())
    units_with_no_defects = len(all_units - units_with_defects)
    ready_units += units_with_no_defects
    total_units = final_df["Unit"].nunique()

    # building info extraction
    sample_audit = df.loc[0, "auditName"] if "auditName" in df.columns and len(df) > 0 else ""
    if sample_audit:
        ap = str(sample_audit).split("/")
        extracted_building_name = ap[2].strip() if len(ap) >= 3 else building_info["name"]
        extracted_inspection_date = ap[0].strip() if len(ap) >= 1 else building_info.get(
            "date", datetime.now().strftime("%Y-%m-%d")
        )
    else:
        extracted_building_name = building_info["name"]
        extracted_inspection_date = building_info.get("date", datetime.now().strftime("%Y-%m-%d"))

    # address
    loc, area, region = "", "", ""
    if "Title Page_Site conducted_Location" in df.columns:
        s = df["Title Page_Site conducted_Location"].dropna()
        loc = s.astype(str).str.strip().iloc[0] if len(s) > 0 else ""
    if "Title Page_Site conducted_Area" in df.columns:
        s = df["Title Page_Site conducted_Area"].dropna()
        area = s.astype(str).str.strip().iloc[0] if len(s) > 0 else ""
    if "Title Page_Site conducted_Region" in df.columns:
        s = df["Title Page_Site conducted_Region"].dropna()
        region = s.astype(str).str.strip().iloc[0] if len(s) > 0 else ""
    addr_parts = [p for p in [loc, area, region] if p]
    extracted_address = ", ".join(addr_parts) if addr_parts else building_info["address"]

    # metrics
    urgent_defects = defects_only[defects_only["Urgency"] == "Urgent"]
    high_priority_defects = defects_only[defects_only["Urgency"] == "High Priority"]

    next_two_weeks = datetime.now() + timedelta(days=14)
    planned_work_2w = defects_only[defects_only["PlannedCompletion"] <= next_two_weeks]

    next_month = datetime.now() + timedelta(days=30)
    planned_work_m = defects_only[
        (defects_only["PlannedCompletion"] > next_two_weeks)
        & (defects_only["PlannedCompletion"] <= next_month)
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
        "planned_work_2weeks": len(planned_work_2w),
        "planned_work_month": len(planned_work_m),
        "summary_trade": defects_only.groupby("Trade")
        .size()
        .reset_index(name="DefectCount")
        .sort_values("DefectCount", ascending=False)
        if len(defects_only) > 0
        else pd.DataFrame(columns=["Trade", "DefectCount"]),
        "summary_unit": defects_only.groupby("Unit")
        .size()
        .reset_index(name="DefectCount")
        .sort_values("DefectCount", ascending=False)
        if len(defects_only) > 0
        else pd.DataFrame(columns=["Unit", "DefectCount"]),
        "summary_room": defects_only.groupby("Room")
        .size()
        .reset_index(name="DefectCount")
        .sort_values("DefectCount", ascending=False)
        if len(defects_only) > 0
        else pd.DataFrame(columns=["Room", "DefectCount"]),
        "urgent_defects_table": urgent_defects[
            ["Unit", "Room", "Component", "Trade", "PlannedCompletion"]
        ].copy()
        if len(urgent_defects) > 0
        else pd.DataFrame(columns=["Unit", "Room", "Component", "Trade", "PlannedCompletion"]),
        "planned_work_2weeks_table": planned_work_2w[
            ["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]
        ].copy()
        if len(planned_work_2w) > 0
        else pd.DataFrame(
            columns=["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]
        ),
        "planned_work_month_table": planned_work_m[
            ["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]
        ].copy()
        if len(planned_work_m) > 0
        else pd.DataFrame(
            columns=["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]
        ),
        "component_details_summary": defects_only.groupby(["Trade", "Room", "Component"])["Unit"]
        .apply(lambda s: ", ".join(sorted(s.astype(str).unique())))
        .reset_index()
        .rename(columns={"Unit": "Units with Defects"})
        if len(defects_only) > 0
        else pd.DataFrame(columns=["Trade", "Room", "Component", "Units with Defects"]),
    }
    return final_df, metrics

def lookup_unit_defects(processed_data, unit_number):
    if processed_data is None or unit_number is None:
        return pd.DataFrame()
    unit_data = processed_data[
        (processed_data["Unit"].astype(str).str.strip().str.lower() == str(unit_number).strip().lower())
        & (processed_data["StatusClass"] == "Not OK")
    ].copy()
    if len(unit_data) > 0:
        order = {"Urgent": 1, "High Priority": 2, "Normal": 3}
        unit_data["UrgencySort"] = unit_data["Urgency"].map(order).fillna(3)
        unit_data = unit_data.sort_values(["UrgencySort", "PlannedCompletion"])
        unit_data["PlannedCompletion"] = pd.to_datetime(unit_data["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
        return unit_data[["Room", "Component", "Trade", "Urgency", "PlannedCompletion"]]
    return pd.DataFrame(columns=["Room", "Component", "Trade", "Urgency", "PlannedCompletion"])

def create_zip_package(excel_bytes, word_bytes, metrics):
    zip_buffer = BytesIO()
    mel_tz = pytz.timezone("Australia/Melbourne")
    timestamp = datetime.now(mel_tz).strftime("%Y%m%d_%H%M%S")
    excel_filename = f"{generate_filename(metrics['building_name'], 'Excel')}.xlsx"
    word_filename = f"{generate_filename(metrics['building_name'], 'Word')}.docx" if word_bytes else None
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(excel_filename, excel_bytes)
        if word_bytes and word_filename:
            zf.writestr(word_filename, word_bytes)
        summary = f"""Inspection Report Summary
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
        zf.writestr("inspection_summary.txt", summary)
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

# ---- UI: Latest Building banner --------------------------------------------
def render_latest_building_banner():
    """Render a consistent 'Building Information (Auto-Detected)' card
    based on st.session_state.metrics (latest inspection snapshot)."""
    metrics = st.session_state.get("metrics")
    if not metrics:
        return

    # Robust date formatting (handles strings / timestamps)
    try:
        dt = pd.to_datetime(metrics.get("inspection_date", None), errors="coerce")
        date_str = dt.strftime("%-d %b %Y") if pd.notna(dt) else str(metrics.get("inspection_date", ""))
    except Exception:
        # Windows doesn't support %-d; fall back to %d
        try:
            date_str = pd.to_datetime(metrics.get("inspection_date", None), errors="coerce").strftime("%d %b %Y")
        except Exception:
            date_str = str(metrics.get("inspection_date", ""))

    building_name = metrics.get("building_name", "")
    total_units = metrics.get("total_units", "")
    address = metrics.get("address", "")
    unit_types = metrics.get("unit_types_str", "")

    st.markdown(
        f"""
<div style="border:1px solid #e0e0e0; border-radius:12px; padding:16px; background:#fbfcfe; margin: 0 0 1rem 0;">
  <div style="font-weight:700; color:#1f4e78; margin-bottom:8px;">🏢 Building Information (Auto-Detected)</div>

  <div style="line-height:1.7;">
    <div>🏢 <b>Building Name:</b> {building_name}</div>
    <div>📅 <b>Inspection Date:</b> {date_str}</div>
    <div>🏠 <b>Total Units:</b> {total_units} units</div>
    <div style="margin-top:6px;">📍 <b>Address:</b> {address}</div>
    <div>🏗️ <b>Unit Types:</b> {unit_types}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
# ---------------------------------------------------------------------------

# ---- helper: normalize Word output to bytes ----
def _as_docx_bytes(doc_or_bytes):
    """Return raw .docx bytes from either a python-docx Document or bytes-like input."""
    if isinstance(doc_or_bytes, (bytes, bytearray, memoryview)):
        return bytes(doc_or_bytes)

    # Lazy import to avoid hard dependency when Word generator is disabled
    try:
        from docx.document import Document as _DocxDocument
    except Exception:
        _DocxDocument = None

    # python-docx Document -> BytesIO
    if _DocxDocument and isinstance(doc_or_bytes, _DocxDocument):
        from io import BytesIO
        bio = BytesIO()
        doc_or_bytes.save(bio)
        return bio.getvalue()

    # Generic "has .save()" fallback
    if hasattr(doc_or_bytes, "save"):
        from io import BytesIO
        bio = BytesIO()
        doc_or_bytes.save(bio)
        return bio.getvalue()

    raise TypeError(f"Unsupported Word report object: {type(doc_or_bytes)}")

def diagnose_database_content():
    try:
        conn = sqlite3.connect("inspection_system.db")
        cur = conn.cursor()
        print("=== DATABASE DIAGNOSTIC ===")
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='inspection_items'")
        items_table_exists = cur.fetchone() is not None
        print(f"inspection_items table exists: {items_table_exists}")
        if items_table_exists:
            cur.execute("SELECT COUNT(*) FROM inspection_items")
            items_count = cur.fetchone()[0]
            print(f"inspection_items records: {items_count}")
            if items_count > 0:
                cur.execute("SELECT status_class, COUNT(*) FROM inspection_items GROUP BY status_class")
                for status, count in cur.fetchall():
                    print(f"  {status}: {count}")
        cur.execute("SELECT COUNT(*) FROM inspection_defects")
        defects_count = cur.fetchone()[0]
        print(f"inspection_defects records: {defects_count}")
        cur.execute(
            """
            SELECT id, building_name, processed_at 
            FROM processed_inspections 
            WHERE is_active = 1 
            ORDER BY processed_at DESC 
            LIMIT 1
            """
        )
        latest = cur.fetchone()
        if latest:
            insp_id, bname, processed_at = latest
            print(f"Latest inspection: {bname} ({insp_id}) at {processed_at}")
            if items_table_exists:
                cur.execute("SELECT COUNT(*) FROM inspection_items WHERE inspection_id = ?", (insp_id,))
                print(f"inspection_items for latest: {cur.fetchone()[0]}")
            cur.execute("SELECT COUNT(*) FROM inspection_defects WHERE inspection_id = ?", (insp_id,))
            print(f"inspection_defects for latest: {cur.fetchone()[0]}")
        else:
            print("No active inspections found")
        conn.close()
        print("=== END DIAGNOSTIC ===")
    except Exception as e:
        print(f"Diagnostic error: {e}")

def check_database_migration():
    try:
        from database_migration_script import check_migration_status, migrate_database
        if not check_migration_status():
            st.error("Database Migration Required!")
            st.warning(
                "Your database needs to be updated to store complete inspection data."
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Run Migration", type="primary"):
                    with st.spinner("Migrating database..."):
                        ok = migrate_database()
                    if ok:
                        st.success("Migration completed! Please restart the app.")
                        st.stop()
                    else:
                        st.error("Migration failed. Check console for details.")
            with c2:
                if st.button("Skip (Not Recommended)"):
                    st.session_state.skip_migration = True
            if not st.session_state.get("skip_migration", False):
                st.stop()
    except Exception:
        # migration script not present – silently ignore in this build
        pass

# =============================================================================
# PAGE CONFIG + STYLES
# =============================================================================

st.set_page_config(
    page_title="Inspection Report Processor",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
div[data-testid="stToolbar"] { visibility: hidden; height: 0%; position: fixed; }
.main-header {
    text-align: center; padding: 2rem 0;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white; border-radius: 10px; margin-bottom: 2rem;
}
.step-container { border: 2px solid #e0e0e0; border-radius: 10px;
    padding: 1.5rem; margin: 1rem 0; background-color: #fafafa; }
.step-header { color: #1976d2; font-weight: bold; font-size: 1.2em; margin-bottom: 1rem; }
.unit-lookup-container { background: linear-gradient(135deg, #e8f5e8 0%, #d4edda 100%);
    border-radius: 10px; padding: 1.5rem; margin: 1rem 0; }
.download-section { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    border-radius: 10px; padding: 2rem; margin: 1rem 0; }
</style>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# AUTH / SESSION INIT
# =============================================================================

auth_manager = get_auth_manager()
if not auth_manager.is_session_valid():
    show_enhanced_login_page()
    st.stop()

# session defaults
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
        "address": "123 Professional Street\nMelbourne, VIC 3000",
    }
if "report_images" not in st.session_state:
    st.session_state.report_images = {"logo": None, "cover": None}

# Sidebar (with actions & quick lookup)
if not show_enhanced_user_menu():
    st.stop()

# Try to preload any persisted data/mapping
if initialize_user_data():
    st.info(f"Loaded inspection data for {st.session_state.metrics['building_name']}")
if load_trade_mapping():
    st.info("Trade mapping loaded from database")

user = auth_manager.get_current_user()

# =============================================================================
# ADMIN / DEV / PM / BUILDER ROUTING
# =============================================================================

if user["dashboard_type"] == "admin":
    st.markdown(
        f"""
    <div class="main-header">
        <h1>Administrator Control Center</h1>
        <p>Complete System Management & Data Processing</p>
        <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
            <span>Welcome back, <strong>{user['name']}</strong>!</span>
            <span style="margin-left: 2rem;">Role: <strong>System Administrator</strong></span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    if "admin_workspace" not in st.session_state:
        st.session_state.admin_workspace = "Data Processing"

    st.markdown("### Choose Your Workspace")
    choice = st.radio(
        "Select your admin interface:",
        ["Data Processing", "System Administration"],
        index=0 if st.session_state.admin_workspace == "Data Processing" else 1,
        horizontal=True,
        help="Data Processing: Upload and process inspection files | System Administration: User and system management",
    )
    if choice != st.session_state.admin_workspace:
        st.session_state.admin_workspace = choice
        st.rerun()

    st.markdown("---")
    if st.session_state.admin_workspace == "System Administration":
        show_admin_dashboard()
        st.stop()
    else:
        st.info("Full inspection processing interface with administrator privileges")

elif user["dashboard_type"] == "portfolio":
    st.markdown(
        f"""
    <div class="main-header">
        <h1>Portfolio Management Dashboard</h1>
        <p>Property Developer Interface</p>
        <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
            <span>Welcome back, <strong>{user['name']}</strong>!</span>
            <span style="margin-left: 2rem;">Role: <strong>Property Developer</strong></span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    show_enhanced_developer_dashboard()
    st.stop()

elif user["dashboard_type"] == "project":
    st.markdown(
        f"""
    <div class="main-header">
        <h1>Project Management Dashboard</h1>
        <p>Project Manager Interface</p>
        <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
            <span>Welcome back, <strong>{user['name']}</strong>!</span>
            <span style="margin-left: 2rem;">Role: <strong>Project Manager</strong></span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    show_enhanced_project_manager_dashboard()
    st.stop()

elif user["dashboard_type"] == "builder":
    st.markdown(
        f"""
    <div class="main-header">
        <h1>Builder Workspace</h1>
        <p>Work Management Interface</p>
        <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
            <span>Welcome back, <strong>{user['name']}</strong>!</span>
            <span style="margin-left: 2rem;">Role: <strong>Builder</strong></span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    show_enhanced_builder_dashboard()
    st.stop()

else:
    # INSPECTOR (default)
    st.markdown(
        f"""
    <div class="main-header">
        <h1>Inspection Processing</h1>
        <p>Inspector Interface</p>
        <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
            <span>Welcome back, <strong>{user['name']}</strong>!</span>
            <span style="margin-left: 2rem;">Role: <strong>Inspector</strong></span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

# =============================================================================
# PROCESSING INTERFACE (shown for roles that can upload/process)
# =============================================================================

def can_process_now() -> bool:
    caps = user["capabilities"]
    return bool(caps.get("can_upload") or caps.get("can_process"))

def show_processing_interface():
    st.markdown("## Processing Pipeline")

    # Step 0 – Building Info (optional override)
    with st.expander("🏢 Building Info", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Building Name", value=st.session_state.building_info["name"])
        with col2:
            address = st.text_area("Address", value=st.session_state.building_info["address"], height=80)
        if st.button("Save Building Info"):
            st.session_state.building_info["name"] = name.strip() or "Unnamed Building"
            st.session_state.building_info["address"] = address.strip() or "Unknown Address"
            st.success("Building info saved to session")

    # Step 1 – Trade Mapping
    st.markdown("### Step 1 — Trade Mapping")
    col1, col2 = st.columns([2, 1])
    with col1:
        mapping_file = st.file_uploader("Upload Trade Mapping CSV (Room, Component, Trade)", type=["csv"])
        if mapping_file:
            try:
                mdf = pd.read_csv(mapping_file).rename(
                    columns={c: c.strip() for c in pd.read_csv(mapping_file, nrows=0).columns}
                )
                required = {"Room", "Component", "Trade"}
                if not required.issubset(set(mdf.columns)):
                    st.error("Mapping must have columns: Room, Component, Trade")
                else:
                    st.session_state.trade_mapping = mdf[["Room", "Component", "Trade"]].copy()
                    st.session_state.step_completed["mapping"] = True
                    st.success("Trade mapping loaded from file")
            except Exception as e:
                st.error(f"Failed to read mapping: {e}")
        if len(st.session_state.trade_mapping) > 0:
            st.dataframe(st.session_state.trade_mapping.head(20), use_container_width=True, height=250)
    with col2:
        if st.button("Save Mapping to Database", use_container_width=True, disabled=len(st.session_state.trade_mapping) == 0):
            try:
                ok = save_trade_mapping_to_database(st.session_state.trade_mapping)
                st.success("Mapping saved to DB" if ok else "Mapping save returned False")
            except Exception as e:
                st.error(f"Error saving mapping: {e}")
        if st.button("Load Mapping from DB", use_container_width=True):
            try:
                df = load_trade_mapping_from_database()
                if len(df) > 0:
                    st.session_state.trade_mapping = df
                    st.session_state.step_completed["mapping"] = True
                    st.success("Mapping loaded from DB")
                else:
                    st.info("No mapping in DB yet")
            except Exception as e:
                st.error(f"Error loading mapping: {e}")

    # Step 2 – Upload CSV
    st.markdown("### Step 2 — Upload iAuditor CSV")
    uploaded_csv = st.file_uploader("Upload CSV", type=["csv"], key="inspection_csv")
    if uploaded_csv is not None:
        try:
            df = pd.read_csv(uploaded_csv)
            st.session_state.uploaded_raw_df = df
            st.success(f"Loaded {len(df):,} rows")
            st.dataframe(df.head(20), use_container_width=True, height=250)
        except Exception as e:
            st.error(f"Failed to read CSV: {e}")

    # Step 3 – Process & Persist
    st.markdown("### Step 3 — Process & Save")
    disabled = not (st.session_state.get("uploaded_raw_df") is not None and len(st.session_state.trade_mapping) > 0)
    if st.button("⚙️ Process Inspection Data", type="primary", disabled=disabled):
        try:
            _ = process_inspection_data_with_persistence(
                st.session_state.uploaded_raw_df,
                st.session_state.trade_mapping,
                st.session_state.building_info,
                st.session_state.username,
            )
        except Exception as e:
            st.error(f"Processing failed: {e}")
            st.exception(e)

    # Step 4 – Preview metrics & data
    if st.session_state.get("processed_data") is not None:
        st.markdown("### Step 4 — Preview Results")
        metrics = st.session_state.metrics
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Inspections", metrics["total_inspections"])
        with c2:
            st.metric("Total Defects", metrics["total_defects"])
        with c3:
            st.metric("Ready Units", f"{metrics['ready_units']} ({metrics['ready_pct']:.1f}%)")
        with c4:
            st.metric("Urgent Defects", metrics["urgent_defects"])
        st.dataframe(st.session_state.processed_data.head(50), use_container_width=True, height=350)

        st.markdown("### Step 5 — Download Reports")
        d1, d2, d3 = st.columns(3)
        excel_bytes = None
        with d1:
            if st.button("Generate Excel Report", use_container_width=True, disabled=not EXCEL_REPORT_AVAILABLE):
                try:
                    excel_buffer = generate_professional_excel_report(st.session_state.processed_data, metrics)
                    excel_bytes = excel_buffer.getvalue()
                    st.session_state._last_excel = excel_bytes
                    st.success("Excel ready below")
                except Exception as e:
                    st.error(f"Excel generation failed: {e}")
        with d2:
            if st.button(
                "Generate Word Report",
                use_container_width=True,
                disabled=not WORD_REPORT_AVAILABLE,
            ):
                try:
                    word_obj = generate_professional_word_report(
                        st.session_state.processed_data,
                        metrics,
                        st.session_state.report_images,  # optional images
                    )
                    # Normalize to raw bytes for Streamlit
                    word_bytes = _as_docx_bytes(word_obj)
                    st.session_state._last_word = word_bytes
                    st.success("Word ready below")
                except Exception as e:
                    st.error(f"Word generation failed: {e}")
        with d3:
            st.caption("Tip: you can zip both once generated")

        # download buttons if available
        if st.session_state.get("_last_excel"):
            st.download_button(
                "⬇️ Download Excel",
                data=st.session_state._last_excel,
                file_name=f"{generate_filename(metrics['building_name'], 'Excel')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        if st.session_state.get("_last_word"):
            st.download_button(
                "⬇️ Download Word",
                data=st.session_state._last_word,  # <-- bytes now
                file_name=f"{generate_filename(metrics['building_name'], 'Word')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

        if st.session_state.get("_last_excel") or st.session_state.get("_last_word"):
            if st.button("Create ZIP Package", use_container_width=True):
                zip_bytes = create_zip_package(
                    st.session_state.get("_last_excel", b""),
                    st.session_state.get("_last_word", None),
                    metrics,
                )
                st.download_button(
                    "⬇️ Download ZIP",
                    data=zip_bytes,
                    file_name=f"{generate_filename(metrics['building_name'], 'ZIP')}.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

# Show processing UI for roles that can
if can_process_now():
    show_processing_interface()
else:
    # For read-only roles, still show a friendly message if no dashboard already shown
    if user["dashboard_type"] not in {"admin", "portfolio", "project", "builder"}:
        st.info("You have read-only access. Ask your inspector/project manager to process the latest CSV.")

# =============================================================================
# OPTIONAL: Diagnostics & Migration Buttons
# =============================================================================

with st.sidebar:
    if st.button("Diagnose Database"):
        diagnose_database_content()
    check_database_migration()
