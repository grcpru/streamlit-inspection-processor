# streamlit_app.py
import os
import time
import json
import uuid
import pytz
import zipfile
import hashlib
import sqlite3
import traceback
import pandas as pd
import streamlit as st

from io import BytesIO, StringIO
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# ──────────────────────────────────────────────────────────────────────────────
# 0) PAGE CONFIG – must be called before any UI
# ──────────────────────────────────────────────────────────────────────────────
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
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────────────
# 1) OPTIONAL MODULES (guarded imports)
# ──────────────────────────────────────────────────────────────────────────────
EXCEL_REPORT_AVAILABLE = False
WORD_REPORT_AVAILABLE = False
EXCEL_IMPORT_ERROR = None
WORD_IMPORT_ERROR = None

try:
    from excel_report_generator import generate_professional_excel_report, generate_filename
    EXCEL_REPORT_AVAILABLE = True
except Exception as e:
    EXCEL_IMPORT_ERROR = str(e)

def _fallback_generate_filename(building_name: str, tag: str) -> str:
    slug = "".join(ch if ch.isalnum() else "_" for ch in building_name).strip("_")
    return f"{slug}_{tag}_{datetime.now().strftime('%Y%m%d')}"

if not EXCEL_REPORT_AVAILABLE:
    generate_filename = _fallback_generate_filename  # type: ignore

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
except Exception as e:
    PORTFOLIO_ANALYTICS_AVAILABLE = False
    PORTFOLIO_ANALYTICS_ERROR = str(e)

# Data persistence (optional, fail gracefully)
try:
    from data_persistence import (
        DataPersistenceManager,
        save_trade_mapping_to_database,
        load_trade_mapping_from_database,
    )
except Exception:
    DataPersistenceManager = None  # type: ignore
    def save_trade_mapping_to_database(df, username):  # type: ignore
        return False
    def load_trade_mapping_from_database():  # type: ignore
        return pd.DataFrame(columns=["Room", "Component", "Trade"])

# ──────────────────────────────────────────────────────────────────────────────
# 2) SHARED UTILITIES
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_MAPPING_CSV = """Room,Component,Trade
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
Bedroom,Light Fixtures,Electrical
"""

@st.cache_data
def get_corrected_database_stats(db_path="inspection_system.db"):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(DISTINCT building_name)
            FROM processed_inspections
            WHERE is_active=1
        """)
        active = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(DISTINCT building_name) FROM processed_inspections")
        total = cur.fetchone()[0] or 0
        cur.execute("""
            SELECT COUNT(*)
            FROM inspection_defects id
            JOIN processed_inspections pi ON id.inspection_id = pi.id
            WHERE pi.is_active=1
        """)
        defects = cur.fetchone()[0] or 0
        conn.close()
        return {"total_inspections": total, "active_inspections": active, "total_defects": defects}
    except Exception:
        return {"total_inspections": 0, "active_inspections": 0, "total_defects": 0}

@st.cache_data
def load_master_trade_mapping() -> pd.DataFrame:
    try:
        if os.path.exists("MasterTradeMapping.csv"):
            return pd.read_csv("MasterTradeMapping.csv")
        if os.path.exists("/mnt/data/MasterTradeMapping.csv"):
            return pd.read_csv("/mnt/data/MasterTradeMapping.csv")
        return pd.read_csv(StringIO(DEFAULT_MAPPING_CSV))
    except Exception as e:
        st.error(f"Error loading master mapping: {e}")
        return pd.read_csv(StringIO(DEFAULT_MAPPING_CSV))

def lookup_unit_defects(processed_data: pd.DataFrame, unit_number: str) -> pd.DataFrame:
    if processed_data is None or unit_number is None:
        return pd.DataFrame()
    unit = str(unit_number).strip().lower()
    df = processed_data[
        (processed_data["Unit"].astype(str).str.strip().str.lower() == unit) &
        (processed_data["StatusClass"] == "Not OK")
    ].copy()
    if df.empty:
        return pd.DataFrame(columns=["Room", "Component", "Trade", "Urgency", "PlannedCompletion"])
    urgency_order = {"Urgent": 1, "High Priority": 2, "Normal": 3}
    df["UrgencySort"] = df["Urgency"].map(urgency_order).fillna(3)
    df = df.sort_values(["UrgencySort", "PlannedCompletion"])
    df["PlannedCompletion"] = pd.to_datetime(df["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
    return df[["Room", "Component", "Trade", "Urgency", "PlannedCompletion"]]

def _classify_status(val: str) -> str:
    if pd.isna(val):
        return "Blank"
    s = str(val).strip().lower()
    if s in {"✓", "✔", "ok", "pass", "passed", "good", "satisfactory"}:
        return "OK"
    if s in {"✗", "✘", "x", "fail", "failed", "not ok", "defect", "issue"}:
        return "Not OK"
    if s == "":
        return "Blank"
    return "Not OK"

def _classify_urgency(val: str, component: str, room: str) -> str:
    if pd.isna(val):
        return "Normal"
    v = str(val).strip().lower()
    component = str(component).lower()
    room = str(room).lower()
    urgent_keywords = ["urgent", "immediate", "safety", "hazard", "dangerous", "critical", "severe"]
    safety_components = ["fire", "smoke", "electrical", "gas", "water", "security", "lock", "door handle"]
    if any(k in v for k in urgent_keywords):
        return "Urgent"
    if any(s in component for s in safety_components):
        return "High Priority"
    if "entry" in room and "door" in component:
        return "High Priority"
    return "Normal"

def process_inspection_data(df: pd.DataFrame, mapping: pd.DataFrame, building_info: Dict) -> Tuple[pd.DataFrame, Dict]:
    df = df.copy()

    # Unit extraction
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
        if "auditName" in df.columns:
            df["Unit"] = df["auditName"].apply(extract_unit)
        else:
            df["Unit"] = [f"Unit_{i}" for i in range(1, len(df) + 1)]

    # Unit type
    def derive_unit_type(row):
        unit_type = str(row.get("Pre-Settlement Inspection_Unit Type", "")).strip().lower()
        townhouse_type = str(row.get("Pre-Settlement Inspection_Townhouse Type", "")).strip()
        apt_type = str(row.get("Pre-Settlement Inspection_Apartment Type", "")).strip()
        if unit_type == "townhouse":
            return f"{townhouse_type} Townhouse" if townhouse_type else "Townhouse"
        if unit_type == "apartment":
            return f"{apt_type} Apartment" if apt_type else "Apartment"
        return row.get("Pre-Settlement Inspection_Unit Type", "") or "Unknown Type"

    df["UnitType"] = df.apply(derive_unit_type, axis=1)

    # Inspection columns
    inspection_cols = [c for c in df.columns if c.startswith("Pre-Settlement Inspection_") and not c.endswith("_notes")]
    if not inspection_cols:
        inspection_cols = [c for c in df.columns if any(k in c.lower() for k in ["inspection", "check", "item", "defect", "issue", "status"])]

    long_df = df.melt(
        id_vars=["Unit", "UnitType"],
        value_vars=inspection_cols,
        var_name="InspectionItem",
        value_name="Status"
    )

    parts = long_df["InspectionItem"].str.split("_", n=2, expand=True)
    if parts.shape[1] >= 3:
        long_df["Room"] = parts[1]
        comp = parts[2].str.replace(r"\.\d+$", "", regex=True)
        long_df["Component"] = comp.apply(lambda x: x.split("_")[-1] if isinstance(x, str) else x)
    else:
        long_df["Room"] = "General"
        long_df["Component"] = long_df["InspectionItem"].str.replace("Pre-Settlement Inspection_", "")

    # Drop metadata-like rows
    long_df = long_df[~long_df["Room"].isin(["Unit Type", "Building Type", "Townhouse Type", "Apartment Type"])]
    long_df = long_df[~long_df["Component"].isin(["Room Type"])]

    long_df["StatusClass"] = long_df["Status"].apply(_classify_status)
    long_df["Urgency"] = long_df.apply(lambda r: _classify_urgency(r["Status"], r["Component"], r["Room"]), axis=1)

    merged = long_df.merge(mapping, on=["Room", "Component"], how="left")
    merged["Trade"] = merged["Trade"].fillna("Unknown Trade")

    def plan_date(urgency: str):
        base = datetime.now()
        if urgency == "Urgent":
            return base + timedelta(days=3)
        if urgency == "High Priority":
            return base + timedelta(days=7)
        return base + timedelta(days=14)

    merged["PlannedCompletion"] = merged["Urgency"].apply(plan_date)

    final_df = merged[["Unit", "UnitType", "Room", "Component", "StatusClass", "Trade", "Urgency", "PlannedCompletion"]]

    defects_only = final_df[final_df["StatusClass"] == "Not OK"]
    defects_per_unit = defects_only.groupby("Unit").size() if not defects_only.empty else pd.Series(dtype=int)

    ready_units = (defects_per_unit <= 2).sum() if not defects_per_unit.empty else 0
    minor_work_units = ((defects_per_unit > 2) & (defects_per_unit <= 7)).sum() if not defects_per_unit.empty else 0
    major_work_units = ((defects_per_unit > 7) & (defects_per_unit <= 15)).sum() if not defects_per_unit.empty else 0
    extensive_work_units = (defects_per_unit > 15).sum() if not defects_per_unit.empty else 0

    units_with_defects = set(defects_per_unit.index)
    all_units = set(final_df["Unit"].dropna())
    ready_units += len(all_units - units_with_defects)

    total_units = final_df["Unit"].nunique()

    # Building info extraction
    sample_audit = df.loc[0, "auditName"] if "auditName" in df.columns and len(df) > 0 else ""
    if sample_audit:
        audit_parts = str(sample_audit).split("/")
        extracted_building_name = audit_parts[2].strip() if len(audit_parts) >= 3 else building_info.get("name", "Building")
        extracted_inspection_date = audit_parts[0].strip() if len(audit_parts) >= 1 else building_info.get("date", datetime.now().strftime("%Y-%m-%d"))
    else:
        extracted_building_name = building_info.get("name", "Building")
        extracted_inspection_date = building_info.get("date", datetime.now().strftime("%Y-%m-%d"))

    def first_nonempty(col_name: str) -> str:
        if col_name in df.columns:
            s = df[col_name].dropna().astype(str).str.strip()
            if not s.empty:
                return s.iloc[0]
        return ""

    location = first_nonempty("Title Page_Site conducted_Location")
    area = first_nonempty("Title Page_Site conducted_Area")
    region = first_nonempty("Title Page_Site conducted_Region")
    address_parts = [p for p in [location, area, region] if p]
    extracted_address = ", ".join(address_parts) if address_parts else building_info.get("address", "")

    urgent_defects = defects_only[defects_only["Urgency"] == "Urgent"]
    high_priority_defects = defects_only[defects_only["Urgency"] == "High Priority"]

    next_two_weeks = datetime.now() + timedelta(days=14)
    planned_work_2w = defects_only[defects_only["PlannedCompletion"] <= next_two_weeks]

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
        "defect_rate": (len(defects_only) / len(final_df) * 100) if len(final_df) else 0.0,
        "avg_defects_per_unit": (len(defects_only) / max(total_units, 1)),
        "ready_units": ready_units,
        "minor_work_units": minor_work_units,
        "major_work_units": major_work_units,
        "extensive_work_units": extensive_work_units,
        "ready_pct": (ready_units / total_units * 100) if total_units else 0.0,
        "minor_pct": (minor_work_units / total_units * 100) if total_units else 0.0,
        "major_pct": (major_work_units / total_units * 100) if total_units else 0.0,
        "extensive_pct": (extensive_work_units / total_units * 100) if total_units else 0.0,
        "urgent_defects": len(urgent_defects),
        "high_priority_defects": len(high_priority_defects),
        "planned_work_2weeks": len(planned_work_2w),
        "planned_work_month": len(planned_work_month),
        "summary_trade": defects_only.groupby("Trade").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False) if not defects_only.empty else pd.DataFrame(columns=["Trade", "DefectCount"]),
        "summary_unit": defects_only.groupby("Unit").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False) if not defects_only.empty else pd.DataFrame(columns=["Unit", "DefectCount"]),
        "summary_room": defects_only.groupby("Room").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False) if not defects_only.empty else pd.DataFrame(columns=["Room", "DefectCount"]),
        "urgent_defects_table": urgent_defects[["Unit", "Room", "Component", "Trade", "PlannedCompletion"]].copy() if not urgent_defects.empty else pd.DataFrame(columns=["Unit", "Room", "Component", "Trade", "PlannedCompletion"]),
        "planned_work_2weeks_table": planned_work_2w[["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]].copy() if not planned_work_2w.empty else pd.DataFrame(columns=["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]),
        "planned_work_month_table": planned_work_month[["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]].copy() if not planned_work_month.empty else pd.DataFrame(columns=["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]),
        "component_details_summary": defects_only.groupby(["Trade", "Room", "Component"])["Unit"].apply(lambda s: ", ".join(sorted(s.astype(str).unique()))).reset_index().rename(columns={"Unit": "Units with Defects"}) if not defects_only.empty else pd.DataFrame(columns=["Trade", "Room", "Component", "Units with Defects"]),
    }
    return final_df, metrics

def create_zip_package(excel_bytes: bytes, word_bytes: Optional[bytes], metrics: Dict) -> bytes:
    zip_buffer = BytesIO()
    mel_tz = pytz.timezone("Australia/Melbourne")
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        excel_filename = f"{generate_filename(metrics['building_name'], 'Excel')}.xlsx"
        zf.writestr(excel_filename, excel_bytes)
        if word_bytes:
            word_filename = f"{generate_filename(metrics['building_name'], 'Word')}.docx"
            zf.writestr(word_filename, word_bytes)
        summary = f"""Inspection Report Summary
=====================================
Building: {metrics['building_name']}
Address: {metrics['address']}
Inspection Date: {metrics['inspection_date']}
Report Generated: {datetime.now(mel_tz).strftime('%Y-%m-%d %H:%M:%S %Z')}

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
"""
        zf.writestr("inspection_summary.txt", summary)
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

# ──────────────────────────────────────────────────────────────────────────────
# 3) AUTHENTICATION
# ──────────────────────────────────────────────────────────────────────────────
class DatabaseAuthManager:
    def __init__(self, db_path="inspection_system.db"):
        self.db_path = db_path
        self.session_timeout = 8 * 60 * 60
        if not os.path.exists(self.db_path):
            st.error("Database not found! Please run: python complete_database_setup.py")
            st.stop()
        self.role_capabilities = {
            "admin": {
                "can_upload": True, "can_process": True, "can_manage_users": True,
                "can_approve_defects": True, "can_view_all": True, "can_generate_reports": True,
                "dashboard_type": "admin",
            },
            "property_developer": {
                "can_upload": False, "can_process": False, "can_manage_users": False,
                "can_approve_defects": True, "can_view_all": False, "can_generate_reports": True,
                "dashboard_type": "portfolio",
            },
            "project_manager": {
                "can_upload": True, "can_process": True, "can_manage_users": False,
                "can_approve_defects": True, "can_view_all": False, "can_generate_reports": True,
                "dashboard_type": "project",
            },
            "inspector": {
                "can_upload": True, "can_process": True, "can_manage_users": False,
                "can_approve_defects": False, "can_view_all": False, "can_generate_reports": True,
                "dashboard_type": "inspector",
            },
            "builder": {
                "can_upload": False, "can_process": False, "can_manage_users": False,
                "can_approve_defects": False, "can_view_all": False, "can_generate_reports": True,
                "dashboard_type": "builder",
            },
        }

    def _hash(self, password: str) -> str:
        salt = "inspection_app_salt_2024"
        return hashlib.sha256((password + salt).encode()).hexdigest()

    def authenticate(self, username: str, password: str) -> Tuple[bool, str]:
        if not username or not password:
            return False, "Please enter username and password"
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT username, full_name, email, role, is_active
                FROM users
                WHERE username=? AND password_hash=? AND is_active=1
                """,
                (username, self._hash(password)),
            )
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE username=?", (username,))
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
                "SELECT username, full_name, email, role, is_active, last_login FROM users WHERE username=?",
                (username,),
            )
            r = cur.fetchone()
            conn.close()
            if not r:
                return None
            return {
                "username": r[0],
                "full_name": r[1],
                "email": r[2],
                "role": r[3],
                "is_active": r[4],
                "last_login": r[5],
                "capabilities": self.role_capabilities.get(r[3], {}),
            }
        except Exception:
            return None

    def create_session(self, username: str):
        info = self.get_user_info(username)
        if info:
            st.session_state.authenticated = True
            st.session_state.username = info["username"]
            st.session_state.user_name = info["full_name"]
            st.session_state.user_email = info["email"]
            st.session_state.user_role = info["role"]
            st.session_state.login_time = time.time()
            st.session_state.user_capabilities = info["capabilities"]
            st.session_state.dashboard_type = info["capabilities"].get("dashboard_type", "inspector")

    def is_session_valid(self) -> bool:
        if not st.session_state.get("authenticated"):
            return False
        if not st.session_state.get("login_time"):
            return False
        if time.time() - st.session_state.login_time > self.session_timeout:
            self.logout()
            return False
        return True

    def logout(self):
        for k in [
            "authenticated","username","user_name","user_email",
            "user_role","login_time","user_capabilities","dashboard_type",
            "trade_mapping","processed_data","metrics","step_completed","report_images",
        ]:
            st.session_state.pop(k, None)

    def get_current_user(self) -> Dict:
        return {
            "username": st.session_state.get("username", ""),
            "name": st.session_state.get("user_name", "User"),
            "email": st.session_state.get("user_email", ""),
            "role": st.session_state.get("user_role", "user"),
            "capabilities": st.session_state.get("user_capabilities", {}),
            "dashboard_type": st.session_state.get("dashboard_type", "inspector"),
        }

    def can_user(self, action: str) -> bool:
        return st.session_state.get("user_capabilities", {}).get(action, False)

    def change_password(self, username, old_password, new_password):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE username=? AND password_hash=?", (username, self._hash(old_password)))
            if not cur.fetchone():
                conn.close()
                return False, "Current password is incorrect"
            if len(new_password) < 6:
                conn.close()
                return False, "New password must be at least 6 characters"
            cur.execute("UPDATE users SET password_hash=? WHERE username=?", (self._hash(new_password), username))
            conn.commit()
            conn.close()
            return True, "Password changed successfully"
        except Exception as e:
            return False, f"Database error: {e}"

@st.cache_resource
def get_auth_manager():
    return DatabaseAuthManager()

def show_login():
    st.markdown(
        """
        <div style="max-width: 420px; margin: 2rem auto; padding: 2rem;
                    background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h2 style="text-align: center; color: #1976d2; margin-bottom: 1rem;">
                Building Inspection Report System
            </h2>
            <h3 style="text-align: center; color: #666; margin-bottom: 1.25rem;">
                Please Login to Continue
            </h3>
        </div>
        """,
        unsafe_allow_html=True,
    )
    auth = get_auth_manager()
    with st.form("login_form"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login", use_container_width=True, type="primary"):
            ok, msg = auth.authenticate(u, p)
            if ok:
                auth.create_session(u)
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    with st.expander("Demo Credentials"):
        st.info(
            """
            **System Administrator:**  admin / admin123  
            **Property Developer:**    developer1 / dev123  
            **Project Manager:**       manager1 / mgr123  
            **Site Inspector:**        inspector / inspector123  
            **Builder:**               builder1 / build123
            """
        )

def show_user_sidebar() -> bool:
    auth = get_auth_manager()
    if not auth.is_session_valid():
        return False

    user = auth.get_current_user()
    key_prefix = f"sb_{user['username']}_"

    with st.sidebar:
        st.markdown("---")
        st.markdown("### User Information")
        st.markdown(
            f"**Name:** {user['name']}  \n"
            f"**Role:** {user['role'].replace('_',' ').title()}  \n"
            f"**Email:** {user['email']}  \n"
            f"**Access:** {user['capabilities'].get('dashboard_type','standard').title()}"
        )

        st.markdown("---")
        st.markdown("### Account")
        col1, col2 = st.columns(2)
        if col1.button("Change Password", use_container_width=True):
            st.session_state.show_pw = True
        if col2.button("Logout", use_container_width=True, type="primary"):
            auth.logout()
            st.success("Logged out successfully!")
            st.rerun()

        if st.session_state.get("show_pw"):
            st.markdown("---")
            st.markdown("### Change Password")
            with st.form("pw_form"):
                old_pw = st.text_input("Current Password", type="password")
                new_pw = st.text_input("New Password", type="password")
                conf_pw = st.text_input("Confirm New Password", type="password")
                u1, u2 = st.columns(2)
                if u1.form_submit_button("Update", use_container_width=True):
                    if new_pw != conf_pw:
                        st.error("New passwords don't match")
                    elif len(new_pw) < 6:
                        st.error("Password must be at least 6 characters")
                    else:
                        ok, msg = auth.change_password(user["username"], old_pw, new_pw)
                        if ok:
                            st.success(msg)
                            st.session_state.show_pw = False
                            st.rerun()
                        else:
                            st.error(msg)
                if u2.form_submit_button("Cancel", use_container_width=True):
                    st.session_state.show_pw = False
                    st.rerun()

        # Quick lookup only if processed data exists
        if st.session_state.get("processed_data") is not None:
            st.markdown("---")
            st.header("Quick Unit Lookup")
            units = sorted(st.session_state.processed_data["Unit"].astype(str).unique())
            chosen = st.selectbox("Select Unit:", [""] + units, key=f"{key_prefix}unit")
            if chosen:
                ud = lookup_unit_defects(st.session_state.processed_data, chosen)
                if not ud.empty:
                    urgent = (ud["Urgency"] == "Urgent").sum()
                    hi = (ud["Urgency"] == "High Priority").sum()
                    normal = (ud["Urgency"] == "Normal").sum()
                    if urgent: st.error(f"Urgent: {urgent}")
                    if hi: st.warning(f"High Priority: {hi}")
                    if normal: st.info(f"Normal: {normal}")
                    for _, r in ud.iterrows():
                        icon = "🚨" if r["Urgency"] == "Urgent" else "⚠️" if r["Urgency"] == "High Priority" else "🔧"
                        st.caption(f"{icon} {r['Room']} - {r['Component']} ({r['Trade']}) – Due: {r['PlannedCompletion']}")
                else:
                    st.success(f"Unit {chosen} has no defects!")

        st.markdown("---")
        if st.button("Reset All", help="Clear all data and start over"):
            for k in ["trade_mapping","processed_data","metrics","step_completed","building_info"]:
                if k == "step_completed":
                    st.session_state[k] = {"mapping": False, "processing": False}
                elif k == "building_info":
                    st.session_state[k] = {"name":"Professional Building Complex","address":"123 Professional Street\nMelbourne, VIC 3000"}
                else:
                    st.session_state.pop(k, None)
            st.rerun()

    return True

# ──────────────────────────────────────────────────────────────────────────────
# 4) SESSION DEFAULTS
# ──────────────────────────────────────────────────────────────────────────────
if "trade_mapping" not in st.session_state:
    st.session_state.trade_mapping = pd.DataFrame(columns=["Room", "Component", "Trade"])
if "processed_data" not in st.session_state:
    st.session_state.processed_data = None
if "metrics" not in st.session_state:
    st.session_state.metrics = None
if "step_completed" not in st.session_state:
    st.session_state.step_completed = {"mapping": False, "processing": False}
if "building_info" not in st.session_state:
    st.session_state.building_info = {"name": "Professional Building Complex", "address": "123 Professional Street\nMelbourne, VIC 3000"}
if "report_images" not in st.session_state:
    st.session_state.report_images = {"logo": None, "cover": None}

# ──────────────────────────────────────────────────────────────────────────────
# 5) AUTH GATE
# ──────────────────────────────────────────────────────────────────────────────
auth = get_auth_manager()
if not auth.is_session_valid():
    show_login()
    st.stop()

user = auth.get_current_user()
if not show_user_sidebar():
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# 6) OPTIONAL INITIAL LOADS
# ──────────────────────────────────────────────────────────────────────────────
def initialize_user_data():
    if st.session_state.processed_data is not None:
        return False
    if DataPersistenceManager is None:
        return False
    try:
        persistence = DataPersistenceManager()
        processed, metrics = persistence.load_latest_inspection()
        if processed is not None and metrics is not None:
            st.session_state.processed_data = processed
            st.session_state.metrics = metrics
            st.session_state.step_completed["processing"] = True
            return True
    except Exception:
        return False
    return False

def load_trade_mapping_from_db_if_empty():
    if len(st.session_state.trade_mapping) > 0:
        return False
    try:
        df = load_trade_mapping_from_database()
        if len(df) > 0:
            st.session_state.trade_mapping = df
            st.session_state.step_completed["mapping"] = True
            return True
    except Exception:
        pass
    return False

if initialize_user_data():
    st.info(f"Loaded inspection data for {st.session_state.metrics['building_name']}")
if load_trade_mapping_from_db_if_empty():
    st.info("Trade mapping loaded from database")

# ──────────────────────────────────────────────────────────────────────────────
# 6.5) DASHBOARD ROUTER / ADMIN SWITCH
# ──────────────────────────────────────────────────────────────────────────────
def show_basic_admin_interface():
    st.markdown("### Basic System Administration")
    try:
        stats = get_corrected_database_stats()
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Total Buildings Processed", stats.get("total_inspections", 0))
        with col2: st.metric("Active Buildings", stats.get("active_inspections", 0))
        with col3: st.metric("Total Defects", stats.get("total_defects", 0))
    except Exception as e:
        st.caption(f"System metrics unavailable: {e}")
    st.info("Basic user management available. Install `dashboards/admin_dashboard.py` for full features.")

def route_to_dashboard(dashboard_type: str):
    try:
        if dashboard_type == 'admin':
            from dashboards.admin_dashboard import AdminDashboard
            AdminDashboard().show()
        elif dashboard_type == 'portfolio':
            from dashboards.developer_dashboard import DeveloperDashboard
            DeveloperDashboard().show()
        elif dashboard_type == 'project':
            from dashboards.project_manager_dashboard import ProjectManagerDashboard
            ProjectManagerDashboard().show()
        elif dashboard_type == 'builder':
            from dashboards.builder_dashboard import BuilderDashboard
            BuilderDashboard().show()
        else:
            st.error(f"Unknown dashboard type: {dashboard_type}")
            st.info("Please contact your administrator to verify your role configuration.")
    except ImportError as e:
        st.error(f"Dashboard module not found: {e}")
        if dashboard_type == 'admin':
            show_basic_admin_interface()
        else:
            st.info("No inspection data available. Contact your team to process data.")
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")
        if dashboard_type == 'admin':
            show_basic_admin_interface()

# ADMIN: let the admin choose right here (no dependency on admin_dashboard.py)
if user['dashboard_type'] == 'admin':
    st.markdown("## Choose Your Workspace")
    if 'admin_workspace' not in st.session_state:
        st.session_state.admin_workspace = "Data Processing"

    choice = st.radio(
        "Select your admin interface:",
        ["Data Processing", "System Administration"],
        index=0 if st.session_state.admin_workspace == "Data Processing" else 1,
        horizontal=True,
        key="admin_workspace_radio_root",   # <-- add this key
    )

    if choice != st.session_state.admin_workspace:
        st.session_state.admin_workspace = choice
        st.rerun()

    st.markdown("---")
    if st.session_state.admin_workspace == "System Administration":
        route_to_dashboard('admin')
        st.stop()

# Non-admin non-inspector roles → route out
if user['dashboard_type'] in ['portfolio', 'project', 'builder']:
    route_to_dashboard(user['dashboard_type'])
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# 7) HEADER (Inspector & Admin “Data Processing” from here on)
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="main-header">
        <h1>Inspection Report Processor</h1>
        <p>Professional Data Processing Interface</p>
        <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
            <span>Welcome back, <strong>{user['name']}</strong>!</span>
            <span style="margin-left: 2rem;">Role: <strong>{user['role'].replace("_"," ").title()}</strong></span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────────────
# 8) STEP 1 – TRADE MAPPING
# ──────────────────────────────────────────────────────────────────────────────
if auth.can_user("can_upload"):
    st.markdown('<div class="step-container"><div class="step-header">Step 1: Load Master Trade Mapping</div></div>', unsafe_allow_html=True)
    c1, c2 = st.columns([2,1])
    with c1:
        if len(st.session_state.trade_mapping) == 0:
            st.warning("Trade mapping is blank. Load a mapping file or use the default template.")
    with c2:
        st.download_button(
            "Download Template",
            data=DEFAULT_MAPPING_CSV,
            file_name="trade_mapping_template.csv",
            mime="text/csv",
            help="Download a comprehensive mapping template",
        )

    mapping_file = st.file_uploader("Choose trade mapping CSV", type=["csv"], key="mapping_upload")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Load Master Mapping", type="secondary"):
            try:
                master = load_master_trade_mapping()
                st.session_state.trade_mapping = master
                st.session_state.step_completed["mapping"] = True
                try:
                    save_trade_mapping_to_database(master, user["username"])
                except Exception:
                    pass
                trades = master["Trade"].nunique()
                rooms = master["Room"].nunique()
                st.success(f"Master mapping loaded! {len(master)} entries covering {trades} trades and {rooms} room types")
                st.rerun()
            except Exception as e:
                st.error(f"Error loading master mapping: {e}")

    with c2:
        master = load_master_trade_mapping()
        st.download_button(
            "Download Master Template",
            data=master.to_csv(index=False).encode("utf-8"),
            file_name="MasterTradeMapping_Complete.csv",
            mime="text/csv",
            help=f"Download complete mapping template ({len(master)} entries)",
        )

    with c3:
        if st.button("Clear Mapping"):
            st.session_state.trade_mapping = pd.DataFrame(columns=["Room", "Component", "Trade"])
            st.session_state.step_completed["mapping"] = False
            st.rerun()

    if mapping_file is not None:
        try:
            st.session_state.trade_mapping = pd.read_csv(mapping_file)
            st.session_state.step_completed["mapping"] = True
            st.success(f"Uploaded mapping with {len(st.session_state.trade_mapping)} rows")
        except Exception as e:
            st.error(f"Failed to read mapping: {e}")

    if len(st.session_state.trade_mapping) > 0:
        st.markdown("**Current Trade Mapping:**")
        st.dataframe(st.session_state.trade_mapping, use_container_width=True, height=200)
    else:
        st.info("No trade mapping loaded. Please load the default template or upload your own mapping file.")

else:
    st.markdown('<div class="step-container"><div class="step-header">Trade Mapping Information</div></div>', unsafe_allow_html=True)
    if len(st.session_state.trade_mapping) > 0:
        st.info(f"Trade mapping available: {len(st.session_state.trade_mapping)} entries")
        st.dataframe(st.session_state.trade_mapping, use_container_width=True, height=200)
    else:
        st.warning("No trade mapping loaded. Contact your team administrator.")

# ──────────────────────────────────────────────────────────────────────────────
# 9) STEP 2 – UPLOAD & PROCESS
# ──────────────────────────────────────────────────────────────────────────────
def process_inspection_data_with_persistence(df, mapping, building_info, username):
    processed_df, metrics = process_inspection_data(df, mapping, building_info)
    saved = False
    if DataPersistenceManager is not None:
        try:
            persistence = DataPersistenceManager()
            success, inspection_id = persistence.save_processed_inspection(processed_df, metrics, username)
            saved = bool(success)
            if not success:
                st.warning(f"Database save failed: {inspection_id}")
        except Exception as e:
            st.warning(f"Database save error: {e}")
    st.session_state.processed_data = processed_df
    st.session_state.metrics = metrics
    st.session_state.step_completed["processing"] = True
    return processed_df, metrics, saved

if auth.can_user("can_upload") and auth.can_user("can_process"):
    st.markdown('<div class="step-container"><div class="step-header">Step 2: Upload Inspection Data</div></div>', unsafe_allow_html=True)
    uploaded_csv = st.file_uploader("Choose inspection CSV file", type=["csv"], key="inspection_upload")

    if len(st.session_state.trade_mapping) == 0:
        st.warning("Please load your trade mapping first before uploading the inspection CSV file.")
        st.stop()

    if uploaded_csv is not None and st.button("Process Inspection Data", type="primary", use_container_width=True):
        try:
            with st.spinner("Processing inspection data..."):
                df = pd.read_csv(uploaded_csv)
                building_info = {
                    "name": st.session_state.building_info["name"],
                    "address": st.session_state.building_info["address"],
                    "date": datetime.now().strftime("%Y-%m-%d"),
                }
                process_inspection_data_with_persistence(df, st.session_state.trade_mapping, building_info, user["username"])
                st.rerun()
        except Exception as e:
            st.error(f"Error processing data: {e}")
            st.code(traceback.format_exc())
else:
    st.markdown('<div class="step-container"><div class="step-header">Inspection Data Status</div></div>', unsafe_allow_html=True)
    if not auth.can_user("can_upload"):
        st.info("Data upload is managed by your team.")
    elif not auth.can_user("can_process"):
        st.info("Data processing is managed by your team.")
    if st.session_state.processed_data is not None:
        st.success("Inspection data has been processed and is available for viewing.")
    else:
        st.warning("No inspection data available. Contact your team to process inspection data.")

# ──────────────────────────────────────────────────────────────────────────────
# 10) STEP 3 – RESULTS & LOOKUP
# ──────────────────────────────────────────────────────────────────────────────
if st.session_state.processed_data is not None and st.session_state.metrics is not None:
    st.markdown('<div class="step-container"><div class="step-header">Step 3: Analysis Results & Downloads</div></div>', unsafe_allow_html=True)
    metrics = st.session_state.metrics

    st.markdown("### Building Information (Auto-Detected)")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Building Name:** {metrics['building_name']}  \n**Inspection Date:** {metrics['inspection_date']}  \n**Total Units:** {metrics['total_units']:,} units")
    with c2:
        st.markdown(f"**Address:** {metrics['address']}  \n**Unit Types:** {metrics['unit_types_str']}")

    st.markdown("---")
    st.subheader("Key Metrics Dashboard")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.metric("Total Units", f"{metrics['total_units']:,}")
    with c2: st.metric("Total Defects", f"{metrics['total_defects']:,}", delta=f"{metrics['defect_rate']:.1f}% rate")
    with c3: st.metric("Ready Units", f"{metrics['ready_units']}", delta=f"{metrics['ready_pct']:.1f}%")
    with c4: st.metric("Avg Defects/Unit", f"{metrics['avg_defects_per_unit']:.1f}")
    with c5:
        completion_eff = (metrics['ready_units'] / metrics['total_units'] * 100) if metrics['total_units'] else 0
        st.metric("Completion Efficiency", f"{completion_eff:.1f}%")

    st.markdown("---")
    st.markdown(
        """
        <div class="unit-lookup-container">
            <h3 style="text-align: center; margin-bottom: 1rem;">Unit Defect Lookup</h3>
            <p style="text-align: center;">Quickly search for any unit's complete defect history</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _, mid, _ = st.columns([1,2,1])
    with mid:
        units = sorted(st.session_state.processed_data["Unit"].astype(str).unique())
        chosen = st.selectbox("Enter or Select Unit Number:", options=[""] + units, key="unit_search")
        if chosen:
            ud = lookup_unit_defects(st.session_state.processed_data, chosen)
            if not ud.empty:
                st.markdown(f"### Unit {chosen} - Complete Defect Report")
                c1, c2, c3, c4 = st.columns(4)
                urgent = (ud["Urgency"] == "Urgent").sum()
                highp = (ud["Urgency"] == "High Priority").sum()
                normal = (ud["Urgency"] == "Normal").sum()
                total = len(ud)
                with c1: st.metric("Urgent", urgent)
                with c2: st.metric("High Priority", highp)
                with c3: st.metric("Normal", normal)
                with c4: st.metric("Total Defects", total)
                display = ud.copy()
                display["Urgency"] = display["Urgency"].map(lambda x: "🚨 "+x if x=="Urgent" else "⚠️ "+x if x=="High Priority" else "🔧 "+x)
                st.dataframe(display, use_container_width=True)
                if urgent > 0:
                    st.error(f"**HIGH ATTENTION REQUIRED** – {urgent} urgent defect(s)!")
                elif highp > 0:
                    st.warning(f"**PRIORITY WORK** – {highp} high priority defect(s)")
                elif normal > 0:
                    st.info(f"**STANDARD WORK** – {normal} items")
            else:
                st.success(f"**Unit {chosen} is DEFECT-FREE!**")
                st.balloons()

    st.markdown("---")
    st.subheader("Summary Tables")
    t1, t2, t3, t4, t5 = st.tabs(["Trade Summary","Unit Summary","Room Summary","Urgent Defects","Planned Work"])
    with t1:
        st.markdown("**Trade-wise defect breakdown**")
        df = metrics["summary_trade"]
        if len(df) > 0:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No trade defects found")

    with t2:
        st.markdown("**Unit-wise defect breakdown**")
        df = metrics["summary_unit"]
        if len(df) > 0:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No unit defects found")
    with t3:
        st.markdown("**Room-wise defect breakdown**")
        df = metrics["summary_room"]
        if len(df) > 0:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No room defects found")
    with t4:
        st.markdown("**URGENT DEFECTS – Immediate attention**")
        df = metrics["urgent_defects_table"]
        if len(df):
            dd = df.copy()
            dd["PlannedCompletion"] = pd.to_datetime(dd["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
            st.dataframe(dd, use_container_width=True)
            st.error(f"**{len(dd)} URGENT defects require immediate attention!**")
        else:
            st.success("No urgent defects found!")
    with t5:
        st.markdown("**Planned Defect Work Schedule**")
        s1, s2 = st.tabs(["Next 2 Weeks","Next Month"])
        with s1:
            df = metrics["planned_work_2weeks_table"]
            st.markdown(f"**Due in next 14 days ({len(df)})**")
            if len(df):
                dd = df.copy()
                dd["PlannedCompletion"] = pd.to_datetime(dd["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
                st.dataframe(dd, use_container_width=True)
            else:
                st.success("No work planned for the next 2 weeks")
        with s2:
            df = metrics["planned_work_month_table"]
            st.markdown(f"**Due days 15–30 ({len(df)})**")
            if len(df):
                dd = df.copy()
                dd["PlannedCompletion"] = pd.to_datetime(dd["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
                st.dataframe(dd, use_container_width=True)
            else:
                st.success("No work planned for this period")

# ──────────────────────────────────────────────────────────────────────────────
# 11) STEP 4 – REPORTS
# ──────────────────────────────────────────────────────────────────────────────
if st.session_state.processed_data is not None and st.session_state.metrics is not None:
    st.markdown('<div class="step-container"><div class="step-header">Step 4: Generate & Download Reports</div></div>', unsafe_allow_html=True)
    if auth.can_user("can_generate_reports") or auth.can_user("can_upload"):
        metrics = st.session_state.metrics
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("### Complete Package")
            st.write("Excel + Word reports in a single ZIP file")
            if st.button("Generate Complete Package", type="primary", use_container_width=True):
                try:
                    with st.spinner("Generating complete report package..."):
                        if not EXCEL_REPORT_AVAILABLE:
                            st.error(f"Excel generator not available: {EXCEL_IMPORT_ERROR or 'module missing'}")
                            st.stop()
                        excel_buffer_or_bytes = generate_professional_excel_report(st.session_state.processed_data, metrics)
                        excel_bytes = excel_buffer_or_bytes.getvalue() if hasattr(excel_buffer_or_bytes, "getvalue") else excel_buffer_or_bytes
                        word_bytes = None
                        if WORD_REPORT_AVAILABLE:
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
                        zip_bytes = create_zip_package(excel_bytes, word_bytes, metrics)
                        zip_filename = f"{generate_filename(metrics['building_name'], 'Package')}.zip"
                        st.success("Complete package generated!")
                        st.download_button("Download Complete Package", data=zip_bytes, file_name=zip_filename, mime="application/zip", use_container_width=True)
                except Exception as e:
                    st.error(f"Error generating package: {e}")

        with c2:
            st.markdown("### Individual Reports")
            if st.button("Generate Excel Report", type="secondary", use_container_width=True):
                try:
                    with st.spinner("Generating Excel report..."):
                        if not EXCEL_REPORT_AVAILABLE:
                            st.error(f"Excel generator not available: {EXCEL_IMPORT_ERROR or 'module missing'}")
                        else:
                            excel_buffer_or_bytes = generate_professional_excel_report(st.session_state.processed_data, metrics)
                            excel_bytes = excel_buffer_or_bytes.getvalue() if hasattr(excel_buffer_or_bytes, "getvalue") else excel_buffer_or_bytes
                            filename = f"{generate_filename(metrics['building_name'], 'Excel')}.xlsx"
                            st.success("Excel report generated!")
                            st.download_button("Download Excel Report", data=excel_bytes, file_name=filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                except Exception as e:
                    st.error(f"Error generating Excel: {e}")

            if WORD_REPORT_AVAILABLE:
                if st.button("Generate Word Report", type="secondary", use_container_width=True):
                    try:
                        with st.spinner("Generating Word report..."):
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
                            st.success("Word report generated!")
                            st.download_button("Download Word Report", data=word_bytes, file_name=filename, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
                    except Exception as e:
                        st.error(f"Error generating Word: {e}")
            else:
                st.warning(f"Word generator not available: {WORD_IMPORT_ERROR or 'module missing'}")

# ──────────────────────────────────────────────────────────────────────────────
# 12) FOOTER
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"""
    <div style="text-align: center; padding: 1.5rem; background: #f8f9fa; border-radius: 8px; margin-top: 2rem;">
        <h4 style="color: #2c3e50; margin-bottom: 1rem;">Professional Inspection Report Processor v4.0</h4>
        <div style="display: flex; justify-content: center; gap: 1.5rem; flex-wrap: wrap; margin-bottom: 1rem;">
            <span><strong>Excel Reports:</strong> Multi-sheet analysis</span>
            <span><strong>Word Reports:</strong> Executive summaries</span>
            <span><strong>Urgent Tracking:</strong> Priority defects</span>
            <span><strong>Unit Lookup:</strong> Instant search</span>
        </div>
        <p style="color: #666; font-size: 0.9em;">
            Logged in as: <strong>{user['name']}</strong> ({user['role'].replace('_', ' ').title()})
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)
