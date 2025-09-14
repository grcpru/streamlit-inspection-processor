# enhanced_error_handling.py
"""
Enhanced error handling and dependency management for the inspection system
"""

import sys
import importlib
import warnings
from functools import wraps
from typing import Dict, Any, Optional, Callable
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DependencyManager:
    """Manages optional dependencies and graceful fallbacks"""
    
    def __init__(self):
        self.available_modules = {}
        self.check_dependencies()
    
    def check_dependencies(self):
        """Check availability of optional dependencies"""
        
        # Core dependencies (required)
        core_deps = {
            'streamlit': 'streamlit',
            'pandas': 'pandas',
            'sqlite3': 'sqlite3'  # Built-in, should always be available
        }
        
        # Optional dependencies for report generation
        optional_deps = {
            'matplotlib': 'matplotlib.pyplot',
            'seaborn': 'seaborn',
            'docx': 'docx',
            'xlsxwriter': 'xlsxwriter',
            'openpyxl': 'openpyxl',
            'pytz': 'pytz'
        }
        
        # Check core dependencies
        for name, module_path in core_deps.items():
            try:
                importlib.import_module(module_path)
                self.available_modules[name] = True
                logger.info(f"✓ Core dependency {name} available")
            except ImportError as e:
                self.available_modules[name] = False
                logger.error(f"✗ Critical dependency {name} missing: {e}")
                raise ImportError(f"Critical dependency {name} is required but not available: {e}")
        
        # Check optional dependencies
        for name, module_path in optional_deps.items():
            try:
                importlib.import_module(module_path)
                self.available_modules[name] = True
                logger.info(f"✓ Optional dependency {name} available")
            except ImportError:
                self.available_modules[name] = False
                logger.warning(f"⚠ Optional dependency {name} not available - some features may be limited")
    
    def is_available(self, module_name: str) -> bool:
        """Check if a module is available"""
        return self.available_modules.get(module_name, False)
    
    def require(self, module_name: str, feature_description: str = "this feature"):
        """Raise an informative error if a required module is not available"""
        if not self.is_available(module_name):
            raise ImportError(
                f"Module '{module_name}' is required for {feature_description}. "
                f"Please install it with: pip install {module_name}"
            )
    
    def get_status_report(self) -> Dict[str, Any]:
        """Get a status report of all dependencies"""
        report = {
            'core_dependencies': {},
            'optional_dependencies': {},
            'missing_dependencies': [],
            'available_features': []
        }
        
        core_modules = ['streamlit', 'pandas', 'sqlite3']
        optional_modules = ['matplotlib', 'seaborn', 'docx', 'xlsxwriter', 'openpyxl', 'pytz']
        
        for module in core_modules:
            status = self.available_modules.get(module, False)
            report['core_dependencies'][module] = status
            if not status:
                report['missing_dependencies'].append(module)
        
        for module in optional_modules:
            status = self.available_modules.get(module, False)
            report['optional_dependencies'][module] = status
            if not status:
                report['missing_dependencies'].append(module)
        
        # Determine available features
        if self.is_available('matplotlib'):
            report['available_features'].append('Data Visualization Charts')
        
        if self.is_available('docx'):
            report['available_features'].append('Professional Word Reports')
        
        if self.is_available('xlsxwriter') or self.is_available('openpyxl'):
            report['available_features'].append('Professional Excel Reports')
        
        return report

# Global dependency manager instance
deps = DependencyManager()

def handle_errors(default_return=None, log_errors=True):
    """Decorator for consistent error handling across the application"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"Error in {func.__name__}: {str(e)}")
                    logger.debug(f"Full traceback: {traceback.format_exc()}")
                
                # Return default or re-raise based on error type
                if isinstance(e, (ImportError, ModuleNotFoundError)):
                    # For import errors, provide helpful message
                    logger.error(f"Import error in {func.__name__}: {str(e)}")
                    if default_return is not None:
                        return default_return
                elif isinstance(e, (sqlite3.Error, sqlite3.DatabaseError)):
                    # For database errors, provide context
                    logger.error(f"Database error in {func.__name__}: {str(e)}")
                    if default_return is not None:
                        return default_return
                else:
                    # For other errors, log and optionally return default
                    logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                    if default_return is not None:
                        return default_return
                
                # Re-raise if no default provided
                raise
        return wrapper
    return decorator

def safe_import(module_name: str, feature_name: str = None):
    """Safely import a module with informative error messages"""
    try:
        return importlib.import_module(module_name)
    except ImportError as e:
        feature_desc = feature_name or f"features requiring {module_name}"
        logger.warning(f"Could not import {module_name}: {feature_desc} will not be available")
        return None

# Safe imports for optional dependencies
def get_matplotlib():
    """Get matplotlib with graceful fallback"""
    if deps.is_available('matplotlib'):
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')  # Use non-GUI backend for Streamlit
            return plt
        except ImportError:
            logger.warning("matplotlib import failed despite being marked as available")
    return None

def get_seaborn():
    """Get seaborn with graceful fallback"""
    if deps.is_available('seaborn'):
        try:
            import seaborn as sns
            return sns
        except ImportError:
            logger.warning("seaborn import failed despite being marked as available")
    return None

def get_docx():
    """Get python-docx with graceful fallback"""
    if deps.is_available('docx'):
        try:
            from docx import Document
            return Document
        except ImportError:
            logger.warning("python-docx import failed despite being marked as available")
    return None

def get_xlsxwriter():
    """Get xlsxwriter with graceful fallback"""
    if deps.is_available('xlsxwriter'):
        try:
            import xlsxwriter
            return xlsxwriter
        except ImportError:
            logger.warning("xlsxwriter import failed despite being marked as available")
    return None

class DatabaseManager:
    """Enhanced database manager with connection pooling and error recovery"""
    
    def __init__(self, db_path: str = "inspection_system.db"):
        self.db_path = db_path
        self.connection_timeout = 30.0
        self.max_retries = 3
    
    @handle_errors(default_return=None)
    def get_connection(self, timeout: Optional[float] = None):
        """Get database connection with timeout and error handling"""
        timeout = timeout or self.connection_timeout
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=timeout)
            conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys
            return conn
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                logger.warning(f"Database is locked, retrying...")
                raise
            else:
                logger.error(f"Database connection error: {e}")
                raise
    
    @handle_errors(default_return=(False, "Database operation failed"))
    def execute_with_retry(self, query: str, params: tuple = (), retries: int = None):
        """Execute database query with retry logic"""
        retries = retries or self.max_retries
        
        for attempt in range(retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    conn.commit()
                    return True, "Success"
            
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < retries - 1:
                    logger.warning(f"Database locked, retry {attempt + 1}/{retries}")
                    import time
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    logger.error(f"Database error after {attempt + 1} attempts: {e}")
                    return False, str(e)
            
            except Exception as e:
                logger.error(f"Unexpected database error: {e}")
                return False, str(e)
        
        return False, f"Failed after {retries} attempts"
    
    def check_database_health(self) -> Dict[str, Any]:
        """Check database health and return diagnostics"""
        health_report = {
            'accessible': False,
            'tables_exist': False,
            'foreign_keys_enabled': False,
            'error_messages': []
        }
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if database is accessible
                cursor.execute("SELECT 1")
                health_report['accessible'] = True
                
                # Check if required tables exist
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN ('users', 'buildings', 'processed_inspections')
                """)
                tables = [row[0] for row in cursor.fetchall()]
                health_report['tables_exist'] = len(tables) >= 3
                health_report['existing_tables'] = tables
                
                # Check foreign keys
                cursor.execute("PRAGMA foreign_keys")
                fk_enabled = cursor.fetchone()[0]
                health_report['foreign_keys_enabled'] = bool(fk_enabled)
                
                # Get database size
                import os
                if os.path.exists(self.db_path):
                    health_report['database_size_mb'] = os.path.getsize(self.db_path) / (1024 * 1024)
                
        except Exception as e:
            health_report['error_messages'].append(str(e))
            logger.error(f"Database health check failed: {e}")
        
        return health_report

def create_error_report(error: Exception, context: str = "") -> Dict[str, Any]:
    """Create comprehensive error report for debugging"""
    return {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'context': context,
        'timestamp': str(datetime.now()),
        'traceback': traceback.format_exc(),
        'dependencies': deps.get_status_report(),
        'python_version': sys.version
    }

def validate_user_input(data: Dict[str, Any], required_fields: list, field_types: Dict[str, type] = None) -> Dict[str, Any]:
    """Validate user input data with comprehensive checks"""
    validation_result = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    field_types = field_types or {}
    
    # Check required fields
    for field in required_fields:
        if field not in data or data[field] is None:
            validation_result['errors'].append(f"Missing required field: {field}")
            validation_result['valid'] = False
        elif data[field] == "":
            validation_result['errors'].append(f"Empty required field: {field}")
            validation_result['valid'] = False
    
    # Check field types
    for field, expected_type in field_types.items():
        if field in data and data[field] is not None:
            if not isinstance(data[field], expected_type):
                try:
                    # Attempt type conversion
                    data[field] = expected_type(data[field])
                    validation_result['warnings'].append(f"Converted {field} to {expected_type.__name__}")
                except (ValueError, TypeError):
                    validation_result['errors'].append(f"Invalid type for {field}: expected {expected_type.__name__}")
                    validation_result['valid'] = False
    
    return validation_result

# Context manager for safe database operations
class SafeDatabaseOperation:
    """Context manager for safe database operations with automatic cleanup"""
    
    def __init__(self, db_path: str = "inspection_system.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
    
    def __enter__(self):
        try:
            self.conn = sqlite3.connect(self.db_path, timeout=30.0)
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.cursor = self.conn.cursor()
            return self.cursor
        except Exception as e:
            logger.error(f"Failed to establish database connection: {e}")
            if self.conn:
                self.conn.close()
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Error occurred, rollback transaction
            if self.conn:
                self.conn.rollback()
                logger.error(f"Database operation failed, rolled back: {exc_val}")
        else:
            # Success, commit transaction
            if self.conn:
                self.conn.commit()
        
        # Always close connection
        if self.conn:
            self.conn.close()

# Export main components
__all__ = [
    'DependencyManager',
    'deps',
    'handle_errors',
    'safe_import',
    'get_matplotlib',
    'get_seaborn',
    'get_docx',
    'get_xlsxwriter',
    'DatabaseManager',
    'create_error_report',
    'validate_user_input',
    'SafeDatabaseOperation'
]