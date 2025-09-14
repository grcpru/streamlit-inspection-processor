"""
Data Persistence Module for Inspection System - COMPLETE VERSION (updated)
Handles all database operations for processed inspection data
"""

import sqlite3
import json
import uuid
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import os

def safe_json_serializer(obj):
    """Custom JSON serializer that handles datetime and other objects"""
    if hasattr(obj, 'strftime'):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(obj, pd.Timestamp):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    return str(obj)

def restore_numeric_values(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Restore numeric values that were converted to strings during JSON serialization"""
    numeric_fields = [
        'total_units', 'total_inspections', 'total_defects', 'defect_rate',
        'avg_defects_per_unit', 'ready_units', 'minor_work_units', 
        'major_work_units', 'extensive_work_units', 'ready_pct', 
        'minor_pct', 'major_pct', 'extensive_pct', 'urgent_defects',
        'high_priority_defects', 'planned_work_2weeks', 'planned_work_month'
    ]
    
    for field in numeric_fields:
        if field in metrics and isinstance(metrics[field], str):
            try:
                # Try to convert to int first
                if '.' not in metrics[field]:
                    metrics[field] = int(metrics[field])
                else:
                    metrics[field] = float(metrics[field])
            except (ValueError, TypeError):
                # If conversion fails, leave as is
                pass
    
    return metrics

class DataPersistenceManager:
    """Manages saving and loading processed inspection data to/from database"""
    
    def __init__(self, db_path="inspection_system.db"):
        self.db_path = db_path
        self.ensure_database_exists()
        self.ensure_tables_exist()
    
    def ensure_database_exists(self):
        """Ensure database file exists and is accessible"""
        if not os.path.exists(self.db_path):
            print(f"Warning: Database {self.db_path} not found!")
            print("Please run: python complete_database_setup.py")
            # Create minimal database as fallback
            self._create_minimal_database()
    
    def _create_minimal_database(self):
        """Create minimal database structure as fallback"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create basic users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    role TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')
            
            # Create basic portfolios and projects
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolios (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    owner_username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    portfolio_id TEXT,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'active',
                    manager_username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS buildings (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    name TEXT NOT NULL,
                    address TEXT,
                    total_units INTEGER DEFAULT 0,
                    building_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert default data
            cursor.execute('''
                INSERT OR IGNORE INTO portfolios (id, name, description)
                VALUES ('portfolio_001', 'Default Portfolio', 'Default development portfolio')
            ''')
            
            cursor.execute('''
                INSERT OR IGNORE INTO projects (id, portfolio_id, name, description)
                VALUES ('project_default', 'portfolio_001', 'Default Project', 'Default inspection project')
            ''')
            
            cursor.execute('''
                INSERT OR IGNORE INTO buildings (id, project_id, name, address, total_units, building_type)
                VALUES ('building_default', 'project_default', 'Default Building', 'Default Address', 0, 'Mixed Use')
            ''')
            
            conn.commit()
            conn.close()
            print("Created minimal database structure")
            
        except Exception as e:
            print(f"Error creating minimal database: {e}")
    
    def ensure_tables_exist(self):
        """Ensure all required tables exist with correct schema"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Main processed inspections table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_inspections (
                    id TEXT PRIMARY KEY,
                    building_name TEXT NOT NULL,
                    address TEXT,
                    inspection_date DATE,
                    uploaded_by TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    metrics_json TEXT,
                    building_id TEXT,
                    FOREIGN KEY (uploaded_by) REFERENCES users(username),
                    FOREIGN KEY (building_id) REFERENCES buildings(id)
                )
            ''')
            
            # Complete inspection items table (OK + Not OK + Blank)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inspection_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inspection_id TEXT NOT NULL,
                    unit_number TEXT,
                    unit_type TEXT,
                    room TEXT,
                    component TEXT,
                    trade TEXT,
                    status_class TEXT CHECK (status_class IN ('OK', 'Not OK', 'Blank')),
                    urgency TEXT CHECK (urgency IN ('Normal', 'High Priority', 'Urgent')),
                    planned_completion DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (inspection_id) REFERENCES processed_inspections(id)
                )
            ''')
            
            # Legacy defects table (backward compatibility)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inspection_defects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inspection_id TEXT,
                    unit_number TEXT,
                    unit_type TEXT,
                    room TEXT,
                    component TEXT,
                    trade TEXT,
                    urgency TEXT CHECK (urgency IN ('Normal', 'High Priority', 'Urgent')),
                    planned_completion DATE,
                    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'assigned', 'in_progress', 'completed', 'approved', 'rejected')),
                    assigned_to TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (inspection_id) REFERENCES processed_inspections(id),
                    FOREIGN KEY (assigned_to) REFERENCES users(username)
                )
            ''')
            
            # Trade mappings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trade_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room TEXT,
                    component TEXT,
                    trade TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    UNIQUE(room, component)
                )
            ''')
            
            # User permissions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    resource_type TEXT CHECK (resource_type IN ('project', 'building', 'portfolio')),
                    resource_id TEXT,
                    permission_level TEXT CHECK (permission_level IN ('read', 'write', 'admin')),
                    granted_by TEXT,
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (username) REFERENCES users(username),
                    FOREIGN KEY (granted_by) REFERENCES users(username),
                    UNIQUE(username, resource_type, resource_id)
                )
            ''')
            
            # Indexes
            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_items_inspection ON inspection_items(inspection_id)',
                'CREATE INDEX IF NOT EXISTS idx_items_unit ON inspection_items(unit_number)',
                'CREATE INDEX IF NOT EXISTS idx_items_status ON inspection_items(status_class)',
                'CREATE INDEX IF NOT EXISTS idx_items_urgency ON inspection_items(urgency)',
                'CREATE INDEX IF NOT EXISTS idx_defects_inspection ON inspection_defects(inspection_id)',
                'CREATE INDEX IF NOT EXISTS idx_defects_unit ON inspection_defects(unit_number)',
                'CREATE INDEX IF NOT EXISTS idx_defects_status ON inspection_defects(status)',
                'CREATE INDEX IF NOT EXISTS idx_defects_urgency ON inspection_defects(urgency)',
                'CREATE INDEX IF NOT EXISTS idx_inspections_active ON processed_inspections(is_active)',
                'CREATE INDEX IF NOT EXISTS idx_inspections_building ON processed_inspections(building_id)',
                'CREATE INDEX IF NOT EXISTS idx_permissions_user ON user_permissions(username)',
                'CREATE INDEX IF NOT EXISTS idx_permissions_resource ON user_permissions(resource_type, resource_id)'
            ]
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error ensuring tables exist: {e}")
            if 'conn' in locals():
                conn.close()

    # ------------------ SAVE ------------------

    def save_processed_inspection(self, processed_data: pd.DataFrame, metrics: Dict[str, Any], username: str) -> Tuple[bool, str]:
        """Save processed inspection data to database - COMPLETE VERSION"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            inspection_id = str(uuid.uuid4())
            
            print(f"\n=== SAVING INSPECTION DATA ===")
            print(f"Total processed_data rows: {len(processed_data)}")
            if len(processed_data) > 0 and "StatusClass" in processed_data.columns:
                status_breakdown = processed_data["StatusClass"].value_counts()
                print("Status breakdown:")
                for status, count in status_breakdown.items():
                    print(f"  {status}: {count}")
            
            # Find or create building
            building_id = self._get_or_create_building(cursor, metrics)
            
            # Save main inspection record
            cursor.execute('''
                INSERT INTO processed_inspections 
                (id, building_name, address, inspection_date, uploaded_by, metrics_json, building_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                inspection_id,
                metrics.get('building_name', 'Unknown Building'),
                metrics.get('address', 'Unknown Address'),
                metrics.get('inspection_date', datetime.now().strftime('%Y-%m-%d')),
                username,
                json.dumps(metrics, default=safe_json_serializer),
                building_id
            ))
            print(f"Saved main inspection record with ID: {inspection_id}")
            
            # Save ALL inspection items
            print(f"Saving {len(processed_data)} complete inspection items...")
            for _, item in processed_data.iterrows():
                planned_completion = None
                if "PlannedCompletion" in item and pd.notna(item.get("PlannedCompletion")):
                    if hasattr(item["PlannedCompletion"], 'strftime'):
                        planned_completion = item["PlannedCompletion"].strftime("%Y-%m-%d")
                    else:
                        planned_completion = str(item["PlannedCompletion"])
                
                cursor.execute('''
                    INSERT INTO inspection_items 
                    (inspection_id, unit_number, unit_type, room, component, trade, 
                     status_class, urgency, planned_completion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    inspection_id,
                    str(item.get("Unit", "Unknown")),
                    str(item.get("UnitType", "Unknown")),
                    str(item.get("Room", "Unknown")),
                    str(item.get("Component", "Unknown")),
                    str(item.get("Trade", "Unknown Trade")),
                    str(item.get("StatusClass", "Blank")),
                    str(item.get("Urgency", "Normal")),
                    planned_completion
                ))
            
            # Also save defects for backward compatibility
            if "StatusClass" in processed_data.columns:
                defects = processed_data[processed_data["StatusClass"] == "Not OK"]
            else:
                defects = processed_data.iloc[0:0]
            print(f"Also saving {len(defects)} defects to legacy table...")
            for _, defect in defects.iterrows():
                planned_completion = None
                if "PlannedCompletion" in defect and pd.notna(defect.get("PlannedCompletion")):
                    if hasattr(defect["PlannedCompletion"], 'strftime'):
                        planned_completion = defect["PlannedCompletion"].strftime("%Y-%m-%d")
                    else:
                        planned_completion = str(defect["PlannedCompletion"])
                
                cursor.execute('''
                    INSERT INTO inspection_defects 
                    (inspection_id, unit_number, unit_type, room, component, trade, urgency, planned_completion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    inspection_id,
                    str(defect.get("Unit", "Unknown")),
                    str(defect.get("UnitType", "Unknown")),
                    str(defect.get("Room", "Unknown")),
                    str(defect.get("Component", "Unknown")),
                    str(defect.get("Trade", "Unknown Trade")),
                    str(defect.get("Urgency", "Normal")),
                    planned_completion
                ))
            
            # Update building unit count
            total_units = metrics.get('total_units', 0)
            if total_units and total_units > 0:
                cursor.execute('UPDATE buildings SET total_units = ? WHERE id = ?', (total_units, building_id))
            
            # Mark previous inspections as inactive
            cursor.execute('UPDATE processed_inspections SET is_active = 0 WHERE building_id = ? AND id != ?', (building_id, inspection_id))
            
            conn.commit()
            print("SUCCESS: Complete inspection data saved!")
            return True, inspection_id
            
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"ERROR saving inspection data: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Database error: {str(e)}"
        finally:
            if conn:
                conn.close()

    def _get_or_create_building(self, cursor, metrics: Dict[str, Any]) -> str:
        """Find existing building or create new one with error handling"""
        building_name = metrics.get('building_name', 'Unknown Building')
        address = metrics.get('address', 'Unknown Address')
        
        try:
            cursor.execute('SELECT id FROM buildings WHERE name = ? AND address = ?', (building_name, address))
            result = cursor.fetchone()
            if result:
                return result[0]
            
            building_id = f"building_{building_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}"
            counter = 1
            original_id = building_id
            while True:
                cursor.execute('SELECT id FROM buildings WHERE id = ?', (building_id,))
                if not cursor.fetchone():
                    break
                building_id = f"{original_id}_{counter}"
                counter += 1
            
            cursor.execute('SELECT id FROM projects LIMIT 1')
            project_result = cursor.fetchone()
            project_id = project_result[0] if project_result else 'project_default'
            
            cursor.execute('''
                INSERT INTO buildings (id, project_id, name, address, total_units, building_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (building_id, project_id, building_name, address, 0, 'Mixed Use'))
            
            return building_id
            
        except Exception as e:
            print(f"Error in _get_or_create_building: {e}")
            return 'building_default'

    # ------------------ LOAD ------------------

    def has_complete_items(self, inspection_id: str) -> bool:
        """Check whether an inspection has full items saved (not just defects)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(1) FROM inspection_items WHERE inspection_id = ?', (inspection_id,))
            count = cursor.fetchone()[0]
            return count and count > 0
        except Exception:
            return False
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def load_latest_inspection(self) -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, Any]]]:
        """Load the most recent active inspection with COMPLETE data when available"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Latest active inspection
            cursor.execute('''
                SELECT id, building_name, address, inspection_date, metrics_json, uploaded_by
                FROM processed_inspections 
                WHERE is_active = 1 
                ORDER BY processed_at DESC 
                LIMIT 1
            ''')
            inspection = cursor.fetchone()
            if not inspection:
                print("No active inspection found in database")
                return None, None
            
            inspection_id, building_name, address, inspection_date, metrics_json, uploaded_by = inspection
            
            # Try COMPLETE path first (inspection_items)
            cursor.execute('''
                SELECT unit_number, unit_type, room, component, trade, status_class, urgency, planned_completion
                FROM inspection_items 
                WHERE inspection_id = ?
                ORDER BY unit_number, room, component
            ''', (inspection_id,))
            complete_items = cursor.fetchall()
            
            if complete_items:
                print(f"SUCCESS: Loading {len(complete_items)} COMPLETE inspection items")
                processed_data = pd.DataFrame(
                    complete_items,
                    columns=["Unit", "UnitType", "Room", "Component", "Trade", "StatusClass", "Urgency", "PlannedCompletion"]
                )
                processed_data["PlannedCompletion"] = pd.to_datetime(processed_data["PlannedCompletion"], errors='coerce')
                
                # metrics base
                metrics = json.loads(metrics_json) if metrics_json else {}
                metrics = restore_numeric_values(metrics)
                metrics["data_completeness"] = "complete"
                metrics["completeness_message"] = "Loaded full inspection items (OK + Not OK) from database."
                metrics["loaded_source"] = "inspection_items"
                
                # Recompute key metrics from actual data
                self._recompute_metrics_from_processed(processed_data, metrics)
            
            else:
                # Fallback to legacy defects table
                print("WARNING: No complete data found, falling back to defects-only data")
                cursor.execute('''
                    SELECT unit_number, unit_type, room, component, trade, urgency, planned_completion, status
                    FROM inspection_defects 
                    WHERE inspection_id = ?
                    ORDER BY unit_number, urgency
                ''', (inspection_id,))
                defects = cursor.fetchall()
                
                if defects:
                    processed_data = pd.DataFrame(
                        defects,
                        columns=["Unit", "UnitType", "Room", "Component", "Trade", "Urgency", "PlannedCompletion", "Status"]
                    )
                    processed_data["StatusClass"] = "Not OK"  # Legacy rows are defects only
                    processed_data["PlannedCompletion"] = pd.to_datetime(processed_data["PlannedCompletion"], errors='coerce')
                    
                    metrics = json.loads(metrics_json) if metrics_json else {}
                    metrics = restore_numeric_values(metrics)
                    metrics["data_completeness"] = "defects_only"
                    metrics["completeness_message"] = (
                        "Only defect rows were found for the latest inspection. "
                        "OK/Blank rows are missing, so totals/percentages may differ. "
                        "Re-upload the original CSV to regenerate the full dataset (OK + Not OK)."
                    )
                    metrics["loaded_source"] = "inspection_defects"
                    
                    self._recompute_metrics_from_processed(processed_data, metrics)
                else:
                    print("No inspection data found")
                    processed_data = pd.DataFrame(columns=[
                        "Unit", "UnitType", "Room", "Component", "Trade", "StatusClass", "Urgency", "PlannedCompletion"
                    ])
                    metrics = json.loads(metrics_json) if metrics_json else {}
                    metrics = restore_numeric_values(metrics)
                    metrics["data_completeness"] = "empty"
                    metrics["completeness_message"] = "No items available for the latest inspection."
                    metrics["loaded_source"] = "none"
            
            print(f"LOADED: {building_name} with {len(processed_data)} total inspection items (source: {metrics.get('loaded_source')})")
            return processed_data, metrics
            
        except Exception as e:
            print(f"Database load error: {e}")
            return None, None
        finally:
            if conn:
                conn.close()

    # ------------------ METRICS RECOMP ------------------

    def _recompute_metrics_from_processed(self, processed_data: pd.DataFrame, metrics: Dict[str, Any]) -> None:
        """Recalculate metrics and summary tables from processed_data"""
        if len(processed_data) == 0:
            return
        
        # Separate OK and Not OK items
        defects_only = processed_data[processed_data["StatusClass"] == "Not OK"]
        ok_items = processed_data[processed_data["StatusClass"] == "OK"]
        
        total_inspections = len(processed_data)
        total_defects = len(defects_only)
        
        metrics.update({
            'total_inspections': total_inspections,
            'total_defects': total_defects,
            'defect_rate': (total_defects / total_inspections * 100) if total_inspections > 0 else 0.0,
            'avg_defects_per_unit': (total_defects / max(processed_data["Unit"].nunique(), 1)),
        })
        
        # Settlement readiness bands
        if total_defects > 0:
            defects_per_unit = defects_only.groupby("Unit").size()
            ready_units = (defects_per_unit <= 2).sum() if len(defects_per_unit) > 0 else 0
            minor_work_units = ((defects_per_unit > 2) & (defects_per_unit <= 7)).sum() if len(defects_per_unit) > 0 else 0
            major_work_units = ((defects_per_unit > 7) & (defects_per_unit <= 15)).sum() if len(defects_per_unit) > 0 else 0
            extensive_work_units = (defects_per_unit > 15).sum() if len(defects_per_unit) > 0 else 0
            
            # Add units with zero defects to ready category
            units_with_defects = set(defects_per_unit.index)
            all_units = set(processed_data["Unit"].dropna())
            units_with_no_defects = len(all_units - units_with_defects)
            ready_units += units_with_no_defects
            
            total_units = processed_data["Unit"].nunique()
            metrics.update({
                'ready_units': ready_units,
                'minor_work_units': minor_work_units,
                'major_work_units': major_work_units,
                'extensive_work_units': extensive_work_units,
                'ready_pct': (ready_units / total_units * 100) if total_units > 0 else 0,
                'minor_pct': (minor_work_units / total_units * 100) if total_units > 0 else 0,
                'major_pct': (major_work_units / total_units * 100) if total_units > 0 else 0,
                'extensive_pct': (extensive_work_units / total_units * 100) if total_units > 0 else 0,
            })
        else:
            metrics.update({
                'ready_units': processed_data["Unit"].nunique(),
                'minor_work_units': 0,
                'major_work_units': 0,
                'extensive_work_units': 0,
                'ready_pct': 100 if processed_data["Unit"].nunique() > 0 else 0,
                'minor_pct': 0,
                'major_pct': 0,
                'extensive_pct': 0,
            })
        
        # Summaries based on defects
        if len(defects_only) > 0:
            metrics['summary_trade'] = defects_only.groupby("Trade").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False)
            metrics['summary_unit'] = defects_only.groupby("Unit").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False)
            metrics['summary_room'] = defects_only.groupby("Room").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False)
            
            urgent_defects = defects_only[defects_only["Urgency"] == "Urgent"]
            metrics['urgent_defects_table'] = urgent_defects[["Unit", "Room", "Component", "Trade", "PlannedCompletion"]].copy() if len(urgent_defects) > 0 else pd.DataFrame(columns=["Unit", "Room", "Component", "Trade", "PlannedCompletion"])
            
            next_two_weeks = datetime.now() + timedelta(days=14)
            next_month = datetime.now() + timedelta(days=30)
            
            planned_work_2weeks = defects_only[pd.to_datetime(defects_only["PlannedCompletion"], errors='coerce') <= next_two_weeks]
            planned_work_month = defects_only[
                (pd.to_datetime(defects_only["PlannedCompletion"], errors='coerce') > next_two_weeks) & 
                (pd.to_datetime(defects_only["PlannedCompletion"], errors='coerce') <= next_month)
            ]
            
            metrics['planned_work_2weeks_table'] = planned_work_2weeks[["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]].copy() if len(planned_work_2weeks) > 0 else pd.DataFrame(columns=["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"])
            metrics['planned_work_month_table'] = planned_work_month[["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]].copy() if len(planned_work_month) > 0 else pd.DataFrame(columns=["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"])
            
            metrics['component_details_summary'] = defects_only.groupby(["Trade", "Room", "Component"])["Unit"].apply(lambda s: ", ".join(sorted(s.astype(str).unique()))).reset_index().rename(columns={"Unit": "Units with Defects"})
            
            metrics['urgent_defects'] = len(urgent_defects)
            metrics['high_priority_defects'] = len(defects_only[defects_only["Urgency"] == "High Priority"])
            metrics['planned_work_2weeks'] = len(planned_work_2weeks)
            metrics['planned_work_month'] = len(planned_work_month)
        else:
            empty_columns = {
                'summary_trade': ["Trade", "DefectCount"],
                'summary_unit': ["Unit", "DefectCount"], 
                'summary_room': ["Room", "DefectCount"],
                'urgent_defects_table': ["Unit", "Room", "Component", "Trade", "PlannedCompletion"],
                'planned_work_2weeks_table': ["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"],
                'planned_work_month_table': ["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"],
                'component_details_summary': ["Trade", "Room", "Component", "Units with Defects"]
            }
            for key, columns in empty_columns.items():
                metrics[key] = pd.DataFrame(columns=columns)
            metrics.update({
                'urgent_defects': 0,
                'high_priority_defects': 0,
                'planned_work_2weeks': 0,
                'planned_work_month': 0
            })

    # ------------------ QUERIES / STATS ------------------

    def get_all_inspections(self) -> List[Tuple]:
        """Get list of all inspections with error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, building_name, address, inspection_date, uploaded_by, processed_at, is_active
                FROM processed_inspections 
                ORDER BY processed_at DESC
            ''')
            inspections = cursor.fetchall()
            return inspections
        except Exception as e:
            print(f"Error getting all inspections: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_defects_by_status(self, status: str = "open") -> List[Tuple]:
        """Get defects filtered by status with error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT d.*, p.building_name 
                FROM inspection_defects d
                JOIN processed_inspections p ON d.inspection_id = p.id
                WHERE d.status = ? AND p.is_active = 1
                ORDER BY 
                    CASE d.urgency 
                        WHEN 'Urgent' THEN 1 
                        WHEN 'High Priority' THEN 2 
                        ELSE 3 
                    END,
                    d.planned_completion
            ''', (status,))
            defects = cursor.fetchall()
            return defects
        except Exception as e:
            print(f"Error getting defects by status: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics for debugging with error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            stats = {}
            # Count inspections
            try:
                cursor.execute("SELECT COUNT(*) FROM processed_inspections")
                stats["total_inspections"] = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM processed_inspections WHERE is_active = 1")
                stats["active_inspections"] = cursor.fetchone()[0]
            except:
                stats["total_inspections"] = 0
                stats["active_inspections"] = 0
            # Count defects
            try:
                cursor.execute("SELECT COUNT(*) FROM inspection_defects")
                stats["total_defects"] = cursor.fetchone()[0]
            except:
                stats["total_defects"] = 0
            # Recent inspections
            try:
                cursor.execute('''
                    SELECT building_name, inspection_date, uploaded_by, processed_at 
                    FROM processed_inspections 
                    ORDER BY processed_at DESC 
                    LIMIT 5
                ''')
                stats["recent_inspections"] = cursor.fetchall()
            except:
                stats["recent_inspections"] = []
            return stats
        except Exception as e:
            return {"error": str(e)}
        finally:
            if conn:
                conn.close()
    
    def get_building_summary(self, building_id: str) -> Dict:
        """Get building summary with basic stats and error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT b.name, b.address, b.total_units,
                    pi.inspection_date, pi.processed_at
                FROM buildings b
                LEFT JOIN processed_inspections pi ON b.id = pi.building_id AND pi.is_active = 1
                WHERE b.id = ?
            ''', (building_id,))
            building_info = cursor.fetchone()
            if not building_info:
                return {}
            cursor.execute('''
                SELECT COUNT(*) as total_defects
                FROM inspection_defects id
                JOIN processed_inspections pi ON id.inspection_id = pi.id
                WHERE pi.building_id = ? AND pi.is_active = 1
            ''', (building_id,))
            defect_result = cursor.fetchone()
            total_defects = defect_result[0] if defect_result else 0
            cursor.execute('''
                SELECT COUNT(*) as urgent_count
                FROM inspection_defects id
                JOIN processed_inspections pi ON id.inspection_id = pi.id
                WHERE pi.building_id = ? AND pi.is_active = 1 AND id.urgency = 'Urgent'
            ''', (building_id,))
            urgent_result = cursor.fetchone()
            urgent_count = urgent_result[0] if urgent_result else 0
            return {
                'name': building_info[0],
                'address': building_info[1],
                'total_units': building_info[2],
                'inspection_date': building_info[3],
                'processed_at': building_info[4],
                'total_defects': total_defects,
                'urgent_count': urgent_count
            }
        except Exception as e:
            print(f"Error getting building summary: {e}")
            return {}
        finally:
            if conn:
                conn.close()

# ------------------ TRADE MAPPING HELPERS ------------------

def save_trade_mapping_to_database(mapping_df: pd.DataFrame, username: str, db_path: str = "inspection_system.db") -> bool:
    """Save trade mapping to database with error handling"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room TEXT,
                component TEXT,
                trade TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                UNIQUE(room, component)
            )
        ''')
        cursor.execute('UPDATE trade_mappings SET is_active = 0')
        for _, row in mapping_df.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO trade_mappings (room, component, trade, created_by)
                VALUES (?, ?, ?, ?)
            ''', (row["Room"], row["Component"], row["Trade"], username))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving trade mapping: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def load_trade_mapping_from_database(db_path: str = "inspection_system.db") -> pd.DataFrame:
    """Load active trade mapping from database with error handling"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT room, component, trade 
            FROM trade_mappings 
            WHERE is_active = 1
            ORDER BY room, component
        ''')
        mappings = cursor.fetchall()
        if mappings:
            return pd.DataFrame(mappings, columns=["Room", "Component", "Trade"])
        else:
            return pd.DataFrame(columns=["Room", "Component", "Trade"])
    except Exception as e:
        print(f"Error loading trade mapping: {e}")
        return pd.DataFrame(columns=["Room", "Component", "Trade"])
    finally:
        if conn:
            conn.close()
