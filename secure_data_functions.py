"""
Complete Secure Data Processing Functions
Create this as secure_data_functions.py
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from permission_manager import requires_permission, get_permission_manager
from data_persistence import DataPersistenceManager


@requires_permission("data.process")
def secure_process_inspection_data_with_persistence(df, mapping, building_info, username):
    """Secure version of process_inspection_data_with_persistence"""
    perm_manager = get_permission_manager()
    
    try:
        perm_manager.log_user_action(username, "DATA_PROCESSING_START", 
                                   resource=building_info.get('name', 'Unknown'))
        
        # Import the original processing function
        from streamlit_app4 import process_inspection_data
        processed_df, metrics = process_inspection_data(df, mapping, building_info)
        
        # Check building access for existing buildings
        building_name = metrics.get('building_name')
        if building_name:
            user_role = st.session_state.get("user_role")
            if user_role not in ['admin'] and not perm_manager.can_access_building(username, building_name):
                perm_manager.log_security_event(
                    username, f"NEW_BUILDING_CREATED: {building_name}", 
                    success=True, details="User created new building data"
                )
        
        # Save to database
        persistence_manager = DataPersistenceManager()
        success, inspection_id = persistence_manager.save_processed_inspection(
            processed_df, metrics, username
        )
        
        if success:
            perm_manager.log_user_action(
                username, "DATA_PROCESSING_SUCCESS", 
                resource=building_name, success=True,
                details=f"Processed {len(processed_df)} records"
            )
            
            st.success(f"Data processed and saved! Building: {metrics['building_name']}")
            st.session_state.processed_data = processed_df
            st.session_state.metrics = metrics
            st.session_state.step_completed["processing"] = True
            return processed_df, metrics, True
        else:
            perm_manager.log_user_action(
                username, "DATA_PROCESSING_SAVE_FAILED", 
                resource=building_name, success=False,
                details=f"Save failed: {inspection_id}"
            )
            st.error(f"Data processing succeeded but database save failed: {inspection_id}")
            return processed_df, metrics, False
    
    except Exception as e:
        perm_manager.log_user_action(
            username, "DATA_PROCESSING_ERROR", 
            resource=building_info.get('name', 'Unknown'),
            success=False, details=str(e)
        )
        raise e


def secure_initialize_user_data():
    """Secure version of initialize_user_data with access control"""
    username = st.session_state.get("username")
    if not username:
        return False
    
    perm_manager = get_permission_manager()
    
    # Check permission
    if not perm_manager.has_permission(username, "data.view_assigned"):
        return False
    
    if st.session_state.processed_data is None:
        try:
            persistence_manager = DataPersistenceManager()
            
            user_role = st.session_state.get("user_role")
            if user_role == 'admin':
                # Admins can load any data
                processed_data, metrics = persistence_manager.load_latest_inspection()
            else:
                # Other users: load from accessible buildings only
                accessible_buildings = perm_manager.get_accessible_buildings(username)
                if accessible_buildings:
                    building_name = accessible_buildings[0][0]  # Most recent
                    processed_data, metrics = persistence_manager.load_inspection_by_building(building_name)
                else:
                    processed_data, metrics = None, None
            
            if processed_data is not None and metrics is not None:
                building_name = metrics.get('building_name')
                if building_name and not perm_manager.can_access_building(username, building_name):
                    perm_manager.log_security_event(
                        username, f"DATA_ACCESS_DENIED: {building_name}",
                        success=False
                    )
                    return False
                
                perm_manager.log_user_action(username, "DATA_LOADED", resource=building_name)
                
                st.session_state.processed_data = processed_data
                st.session_state.metrics = metrics
                st.session_state.step_completed["processing"] = True
                return True
        
        except Exception as e:
            perm_manager.log_user_action(
                username, "DATA_LOAD_ERROR", 
                success=False, details=str(e)
            )
            return False
    
    return False


def secure_load_trade_mapping():
    """Secure version of load_trade_mapping"""
    username = st.session_state.get("username")
    if not username:
        return False
    
    perm_manager = get_permission_manager()
    
    if not perm_manager.has_permission(username, "data.upload"):
        return False
    
    if len(st.session_state.trade_mapping) == 0:
        try:
            from data_persistence import load_trade_mapping_from_database
            mapping_df = load_trade_mapping_from_database()
            
            if len(mapping_df) > 0:
                perm_manager.log_user_action(
                    username, "TRADE_MAPPING_LOADED",
                    details=f"Loaded {len(mapping_df)} mappings"
                )
                
                st.session_state.trade_mapping = mapping_df
                st.session_state.step_completed["mapping"] = True
                return True
        
        except Exception as e:
            perm_manager.log_user_action(
                username, "TRADE_MAPPING_LOAD_ERROR",
                success=False, details=str(e)
            )
    
    return False


def secure_lookup_unit_defects(processed_data, unit_number, building_name=None):
    """Secure version of lookup_unit_defects with building access check"""
    username = st.session_state.get("username")
    perm_manager = get_permission_manager()
    
    # Check basic permission
    if not perm_manager.has_permission(username, "data.view_assigned"):
        raise PermissionError("You don't have permission to view unit data")
    
    if processed_data is None or unit_number is None:
        return pd.DataFrame()
    
    # Extract building name from metrics if not provided
    if not building_name and st.session_state.metrics:
        building_name = st.session_state.metrics.get('building_name')
    
    # Check building access
    if building_name and not perm_manager.can_access_building(username, building_name):
        raise PermissionError(f"You don't have access to building: {building_name}")
    
    # Log unit lookup
    perm_manager.log_user_action(
        username, "UNIT_LOOKUP", 
        resource=f"{building_name}/{unit_number}" if building_name else unit_number
    )
    
    # Original lookup logic
    unit_data = processed_data[
        (processed_data["Unit"].astype(str).str.strip().str.lower() == str(unit_number).strip().lower()) &
        (processed_data["StatusClass"] == "Not OK")
    ].copy()
    
    if len(unit_data) > 0:
        urgency_order = {"Urgent": 1, "High Priority": 2, "Normal": 3}
        unit_data["UrgencySort"] = unit_data["Urgency"].map(urgency_order).fillna(3)
        unit_data = unit_data.sort_values(["UrgencySort", "PlannedCompletion"])
        
        unit_data["PlannedCompletion"] = pd.to_datetime(unit_data["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
        
        return unit_data[["Room", "Component", "Trade", "Urgency", "PlannedCompletion"]]
    
    return pd.DataFrame(columns=["Room", "Component", "Trade", "Urgency", "PlannedCompletion"])


def validate_user_session():
    """Middleware to validate user session before any operation"""
    username = st.session_state.get("username")
    if not username or not st.session_state.get("authenticated", False):
        st.error("Authentication required")
        st.stop()
    
    perm_manager = get_permission_manager()
    if not perm_manager.validate_session(username):
        st.error("Session expired or invalid")
        st.stop()


def log_page_access(page_name: str):
    """Log page access for audit trail"""
    username = st.session_state.get("username")
    if username:
        perm_manager = get_permission_manager()
        perm_manager.log_user_action(username, f"PAGE_ACCESS: {page_name}")


@requires_permission("reports.generate")
def secure_generate_excel_report(processed_data, metrics):
    """Secure Excel report generation"""
    username = st.session_state.get("username")
    perm_manager = get_permission_manager()
    
    # Check Excel-specific permission
    if not perm_manager.has_permission(username, "reports.excel"):
        raise PermissionError("You don't have permission to generate Excel reports")
    
    # Check building access
    building_name = metrics.get('building_name') if metrics else None
    if building_name and not perm_manager.can_access_building(username, building_name):
        raise PermissionError(f"You don't have access to building: {building_name}")
    
    perm_manager.log_user_action(username, "EXCEL_REPORT_START", resource=building_name)
    
    try:
        from excel_report_generator import generate_professional_excel_report
        result = generate_professional_excel_report(processed_data, metrics)
        
        perm_manager.log_user_action(username, "EXCEL_REPORT_SUCCESS", resource=building_name)
        return result
    
    except Exception as e:
        perm_manager.log_user_action(
            username, "EXCEL_REPORT_ERROR", 
            resource=building_name, success=False, details=str(e)
        )
        raise e


@requires_permission("reports.generate")
def secure_generate_word_report(processed_data, metrics, report_images):
    """Secure Word report generation"""
    username = st.session_state.get("username")
    perm_manager = get_permission_manager()
    
    # Check Word-specific permission
    if not perm_manager.has_permission(username, "reports.word"):
        raise PermissionError("You don't have permission to generate Word reports")
    
    # Check building access
    building_name = metrics.get('building_name') if metrics else None
    if building_name and not perm_manager.can_access_building(username, building_name):
        raise PermissionError(f"You don't have access to building: {building_name}")
    
    perm_manager.log_user_action(username, "WORD_REPORT_START", resource=building_name)
    
    try:
        from word_report_generator import generate_professional_word_report
        result = generate_professional_word_report(processed_data, metrics, report_images)
        
        perm_manager.log_user_action(username, "WORD_REPORT_SUCCESS", resource=building_name)
        return result
    
    except Exception as e:
        perm_manager.log_user_action(
            username, "WORD_REPORT_ERROR", 
            resource=building_name, success=False, details=str(e)
        )
        raise e


def check_data_access_permission(operation_type="view"):
    """Helper to check data access permissions"""
    username = st.session_state.get("username")
    if not username:
        return False
    
    perm_manager = get_permission_manager()
    
    permission_map = {
        "view": "data.view_assigned",
        "upload": "data.upload",
        "process": "data.process",
        "edit": "data.edit"
    }
    
    required_permission = permission_map.get(operation_type, "data.view_assigned")
    return perm_manager.has_permission(username, required_permission)


def secure_building_selector(buildings_list, key_suffix=""):
    """Secure building selector that only shows accessible buildings"""
    username = st.session_state.get("username")
    if not username:
        st.error("Authentication required")
        return None
    
    perm_manager = get_permission_manager()
    accessible_buildings = perm_manager.get_accessible_buildings(username)
    
    if not accessible_buildings:
        st.warning("No buildings assigned to your account")
        return None
    
    # Filter buildings list to only accessible ones
    accessible_names = [building[0] for building in accessible_buildings]
    filtered_buildings = [b for b in buildings_list if b in accessible_names]
    
    if not filtered_buildings:
        st.warning("None of the available buildings are accessible to you")
        return None
    
    selected = st.selectbox(
        "Select Building:",
        options=filtered_buildings,
        key=f"secure_building_select_{key_suffix}",
        help="Only buildings you have access to are shown"
    )
    
    if selected:
        perm_manager.log_user_action(username, "BUILDING_SELECTED", resource=selected)
    
    return selected


def validate_file_access(file_path_or_name, operation="read"):
    """Validate file access permissions"""
    username = st.session_state.get("username")
    if not username:
        return False
    
    perm_manager = get_permission_manager()
    
    # Log file access attempt
    perm_manager.log_user_action(
        username, f"FILE_ACCESS_{operation.upper()}", 
        resource=file_path_or_name
    )
    
    # Basic permission check
    if operation == "read":
        return perm_manager.has_permission(username, "data.view_assigned")
    elif operation == "write":
        return perm_manager.has_permission(username, "data.upload")
    elif operation == "delete":
        return perm_manager.has_permission(username, "system.admin")
    
    return False