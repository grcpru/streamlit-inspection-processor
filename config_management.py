# config_management.py
"""
Configuration Management System for Inspection Application
Centralizes all configurable values and provides environment-specific settings
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

class ConfigManager:
    """Centralized configuration management"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self._load_default_config()
        self._load_user_config()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration values"""
        return {
            # Database Configuration
            "database": {
                "path": "inspection_system.db",
                "connection_timeout": 30.0,
                "max_retries": 3,
                "enable_foreign_keys": True
            },
            
            # Application Configuration
            "app": {
                "name": "Professional Inspection Report Processor",
                "version": "4.0",
                "session_timeout": 8 * 60 * 60,  # 8 hours
                "debug_mode": False,
                "log_level": "INFO"
            },
            
            # Authentication Configuration
            "auth": {
                "password_salt": "inspection_app_salt_2024",
                "min_password_length": 6,
                "session_timeout": 8 * 60 * 60,  # 8 hours
                "max_login_attempts": 5
            },
            
            # Report Configuration
            "reports": {
                "excel": {
                    "enabled": True,
                    "template_path": None,
                    "max_file_size_mb": 50
                },
                "word": {
                    "enabled": True,
                    "include_charts": True,
                    "chart_dpi": 300,
                    "max_file_size_mb": 100
                },
                "output_directory": "reports",
                "temp_directory": "temp"
            },
            
            # File Upload Configuration
            "uploads": {
                "max_file_size_mb": 25,
                "allowed_extensions": [".csv"],
                "temp_directory": "uploads/temp",
                "auto_cleanup_hours": 24
            },
            
            # UI Configuration
            "ui": {
                "page_title": "Inspection Report Processor",
                "page_icon": "🏢",
                "layout": "wide",
                "sidebar_state": "expanded",
                "theme": {
                    "primary_color": "#1976d2",
                    "background_color": "#ffffff",
                    "secondary_background_color": "#f0f2f6"
                }
            },
            
            # Data Processing Configuration
            "processing": {
                "default_building_name": "Professional Building Complex",
                "default_address": "123 Professional Street\nMelbourne, VIC 3000",
                "urgency_thresholds": {
                    "urgent_keywords": ["urgent", "immediate", "safety", "hazard", "dangerous", "critical"],
                    "safety_components": ["fire", "smoke", "electrical", "gas", "water", "security", "lock"]
                },
                "settlement_readiness": {
                    "ready_threshold": 2,      # 0-2 defects
                    "minor_threshold": 7,      # 3-7 defects  
                    "major_threshold": 15      # 8-15 defects, 15+ is extensive
                }
            },
            
            # Visualization Configuration
            "visualization": {
                "colors": {
                    "primary": "#6B91B5",
                    "secondary": "#A68B6E", 
                    "accent": "#8BC88B",
                    "warning": "#E6A373",
                    "danger": "#D68B8B",
                    "success": "#9DD49D"
                },
                "chart_settings": {
                    "figsize": [12, 8],
                    "dpi": 300,
                    "style": "seaborn-v0_8",
                    "font_family": "Segoe UI"
                }
            },
            
            # Logging Configuration
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file_path": "logs/inspection_app.log",
                "max_file_size_mb": 10,
                "backup_count": 5
            },
            
            # Feature Flags
            "features": {
                "enhanced_admin": True,
                "word_reports": True,
                "excel_reports": True,
                "data_visualization": True,
                "email_notifications": False,  # Future feature
                "api_integration": False,      # Future feature
                "mobile_responsive": True
            }
        }
    
    def _load_user_config(self):
        """Load user-specific configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    self._merge_config(self.config, user_config)
                print(f"Loaded user configuration from {self.config_file}")
            except Exception as e:
                print(f"Warning: Could not load user config: {e}")
    
    def _merge_config(self, base: Dict, override: Dict):
        """Recursively merge configuration dictionaries"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def get(self, key_path: str, default=None):
        """Get configuration value using dot notation (e.g., 'database.path')"""
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any):
        """Set configuration value using dot notation"""
        keys = key_path.split('.')
        config = self.config
        
        # Navigate to parent key
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # Set final value
        config[keys[-1]] = value
    
    def save_user_config(self):
        """Save current configuration to user config file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_file) if os.path.dirname(self.config_file) else '.', exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False
    
    def create_directories(self):
        """Create required directories based on configuration"""
        directories_to_create = [
            self.get('reports.output_directory', 'reports'),
            self.get('reports.temp_directory', 'temp'),
            self.get('uploads.temp_directory', 'uploads/temp'),
            os.path.dirname(self.get('logging.file_path', 'logs/app.log'))
        ]
        
        for directory in directories_to_create:
            if directory:
                try:
                    os.makedirs(directory, exist_ok=True)
                    print(f"Created directory: {directory}")
                except Exception as e:
                    print(f"Warning: Could not create directory {directory}: {e}")
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration and return validation report"""
        validation_report = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check database path
        db_path = self.get('database.path')
        if not db_path:
            validation_report['errors'].append("Database path not specified")
            validation_report['valid'] = False
        
        # Check password requirements
        min_password_length = self.get('auth.min_password_length', 6)
        if min_password_length < 6:
            validation_report['warnings'].append("Password minimum length is less than 6 characters")
        
        # Check file size limits
        max_upload_size = self.get('uploads.max_file_size_mb', 25)
        if max_upload_size > 100:
            validation_report['warnings'].append("Upload file size limit is very large (>100MB)")
        
        # Check directory paths
        directories = [
            self.get('reports.output_directory'),
            self.get('uploads.temp_directory'),
            os.path.dirname(self.get('logging.file_path', ''))
        ]
        
        for directory in directories:
            if directory and not os.path.exists(directory):
                validation_report['warnings'].append(f"Directory does not exist: {directory}")
        
        return validation_report
    
    def get_environment_config(self) -> str:
        """Detect and return current environment (development/production)"""
        if os.environ.get('STREAMLIT_ENV') == 'production':
            return 'production'
        elif self.get('app.debug_mode', False):
            return 'development'
        else:
            return 'production'  # Default to production for safety
    
    def update_for_environment(self, environment: str):
        """Update configuration based on environment"""
        if environment == 'development':
            self.set('app.debug_mode', True)
            self.set('logging.level', 'DEBUG')
            self.set('database.connection_timeout', 10.0)
        elif environment == 'production':
            self.set('app.debug_mode', False)
            self.set('logging.level', 'INFO')
            self.set('database.connection_timeout', 30.0)
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database-specific configuration"""
        return {
            'path': self.get('database.path'),
            'connection_timeout': self.get('database.connection_timeout'),
            'max_retries': self.get('database.max_retries'),
            'enable_foreign_keys': self.get('database.enable_foreign_keys')
        }
    
    def get_streamlit_config(self) -> Dict[str, Any]:
        """Get Streamlit-specific configuration"""
        return {
            'page_title': self.get('ui.page_title'),
            'page_icon': self.get('ui.page_icon'),
            'layout': self.get('ui.layout'),
            'initial_sidebar_state': self.get('ui.sidebar_state')
        }


# Global configuration instance
config = ConfigManager()

def init_application():
    """Initialize application with configuration"""
    # Create required directories
    config.create_directories()
    
    # Validate configuration
    validation = config.validate_config()
    if not validation['valid']:
        print("Configuration validation errors:")
        for error in validation['errors']:
            print(f"  ERROR: {error}")
        return False
    
    if validation['warnings']:
        print("Configuration warnings:")
        for warning in validation['warnings']:
            print(f"  WARNING: {warning}")
    
    # Set environment-specific settings
    environment = config.get_environment_config()
    config.update_for_environment(environment)
    
    print(f"Application initialized in {environment} mode")
    return True


# Convenience functions for common configuration access
def get_db_path() -> str:
    """Get database path"""
    return config.get('database.path', 'inspection_system.db')

def get_session_timeout() -> int:
    """Get session timeout in seconds"""
    return config.get('auth.session_timeout', 8 * 60 * 60)

def get_upload_config() -> Dict[str, Any]:
    """Get upload configuration"""
    return {
        'max_size_mb': config.get('uploads.max_file_size_mb', 25),
        'allowed_extensions': config.get('uploads.allowed_extensions', ['.csv']),
        'temp_directory': config.get('uploads.temp_directory', 'uploads/temp')
    }

def get_report_config() -> Dict[str, Any]:
    """Get report generation configuration"""
    return {
        'excel_enabled': config.get('reports.excel.enabled', True),
        'word_enabled': config.get('reports.word.enabled', True),
        'include_charts': config.get('reports.word.include_charts', True),
        'chart_dpi': config.get('reports.word.chart_dpi', 300),
        'output_directory': config.get('reports.output_directory', 'reports')
    }

def is_feature_enabled(feature_name: str) -> bool:
    """Check if a feature is enabled"""
    return config.get(f'features.{feature_name}', False)

def get_color_palette() -> Dict[str, str]:
    """Get UI color palette"""
    return config.get('visualization.colors', {})

def get_processing_config() -> Dict[str, Any]:
    """Get data processing configuration"""
    return {
        'urgency_keywords': config.get('processing.urgency_thresholds.urgent_keywords', []),
        'safety_components': config.get('processing.urgency_thresholds.safety_components', []),
        'ready_threshold': config.get('processing.settlement_readiness.ready_threshold', 2),
        'minor_threshold': config.get('processing.settlement_readiness.minor_threshold', 7),
        'major_threshold': config.get('processing.settlement_readiness.major_threshold', 15)
    }


# Example configuration file generator
def create_sample_config_file(filename: str = "config.json"):
    """Create a sample configuration file for users to customize"""
    sample_config = {
        "database": {
            "path": "inspection_system.db",
            "connection_timeout": 30.0
        },
        "app": {
            "name": "My Inspection System",
            "debug_mode": False
        },
        "reports": {
            "output_directory": "my_reports",
            "excel": {
                "enabled": True
            },
            "word": {
                "enabled": True,
                "include_charts": True
            }
        },
        "ui": {
            "page_title": "Custom Inspection Reports",
            "theme": {
                "primary_color": "#1976d2"
            }
        },
        "features": {
            "enhanced_admin": True,
            "data_visualization": True
        }
    }
    
    try:
        with open(filename, 'w') as f:
            json.dump(sample_config, f, indent=2)
        print(f"Sample configuration file created: {filename}")
        print("Customize this file to override default settings.")
        return True
    except Exception as e:
        print(f"Error creating sample config: {e}")
        return False


if __name__ == "__main__":
    print("Configuration Management System")
    print("=" * 40)
    
    # Test configuration loading
    print("Testing configuration loading...")
    
    # Print key configuration values
    print(f"Database path: {get_db_path()}")
    print(f"Session timeout: {get_session_timeout()} seconds")
    print(f"Excel reports enabled: {is_feature_enabled('excel_reports')}")
    print(f"Word reports enabled: {is_feature_enabled('word_reports')}")
    
    # Validate configuration
    validation = config.validate_config()
    if validation['valid']:
        print("Configuration is valid!")
    else:
        print("Configuration has errors:")
        for error in validation['errors']:
            print(f"  - {error}")
    
    # Create sample config file
    create_sample_config_file("sample_config.json")
    
    print("\nConfiguration system ready!")