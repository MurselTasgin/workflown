"""
Configuration Manager

Handles loading, validation, and management of configuration files.
"""

import yaml
import json
import os
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ConfigFormat(Enum):
    """Supported configuration file formats."""
    YAML = "yaml"
    JSON = "json"


@dataclass
class ConfigSection:
    """Represents a configuration section with validation."""
    name: str
    data: Dict[str, Any]
    required_fields: List[str] = None
    optional_fields: List[str] = None
    
    def __post_init__(self):
        if self.required_fields is None:
            self.required_fields = []
        if self.optional_fields is None:
            self.optional_fields = []
    
    def validate(self) -> List[str]:
        """
        Validate the configuration section.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required fields
        for field in self.required_fields:
            if field not in self.data:
                errors.append(f"Missing required field '{field}' in section '{self.name}'")
        
        return errors


class ConfigManager:
    """
    Manages configuration loading, validation, and access.
    
    Supports YAML and JSON configuration files with environment variable
    substitution and validation.
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.config_data: Dict[str, Any] = {}
        self.sections: Dict[str, ConfigSection] = {}
        self.env_prefix = "ENHANCED_AGENT_"
        
    def load_config(self, config_file: str, format_type: ConfigFormat = None) -> bool:
        """
        Load configuration from a file.
        
        Args:
            config_file: Path to configuration file
            format_type: Format of the configuration file
            
        Returns:
            True if loading successful, False otherwise
        """
        try:
            file_path = self.config_dir / config_file
            
            if not file_path.exists():
                print(f"Configuration file not found: {file_path}")
                return False
            
            # Auto-detect format if not specified
            if format_type is None:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    format_type = ConfigFormat.YAML
                elif file_path.suffix.lower() == '.json':
                    format_type = ConfigFormat.JSON
                else:
                    print(f"Unknown configuration file format: {file_path}")
                    return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                if format_type == ConfigFormat.YAML:
                    data = yaml.safe_load(f)
                else:  # JSON
                    data = json.load(f)
            
            # Substitute environment variables
            data = self._substitute_env_vars(data)
            
            # Merge with existing configuration
            self._merge_config(data)
            
            return True
            
        except Exception as e:
            print(f"Error loading configuration from {config_file}: {e}")
            return False
    
    def load_all_configs(self) -> bool:
        """
        Load all configuration files from the config directory.
        
        Returns:
            True if all files loaded successfully, False otherwise
        """
        if not self.config_dir.exists():
            print(f"Configuration directory not found: {self.config_dir}")
            return False
        
        success = True
        
        # Load configuration files in specific order
        config_files = [
            "default.yaml",
            "agents.yaml", 
            "tools.yaml",
            "storage.yaml",
            "models.yaml"
        ]
        
        for config_file in config_files:
            file_path = self.config_dir / config_file
            if file_path.exists():
                if not self.load_config(config_file):
                    success = False
            else:
                print(f"Optional configuration file not found: {config_file}")
        
        return success
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key (supports dot notation).
        
        Args:
            key: Configuration key (e.g., 'database.host')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config_data
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value by key (supports dot notation).
        
        Args:
            key: Configuration key (e.g., 'database.host')  
            value: Value to set
        """
        keys = key.split('.')
        config = self.config_data
        
        # Navigate to parent dictionary
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the final value
        config[keys[-1]] = value
    
    def get_section(self, section_name: str) -> Optional[Dict[str, Any]]:
        """
        Get an entire configuration section.
        
        Args:
            section_name: Name of the configuration section
            
        Returns:
            Dictionary containing section data or None
        """
        return self.config_data.get(section_name)
    
    def validate_config(self) -> List[str]:
        """
        Validate all configuration sections.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        for section in self.sections.values():
            section_errors = section.validate()
            errors.extend(section_errors)
        
        return errors
    
    def _substitute_env_vars(self, data: Any) -> Any:
        """
        Recursively substitute environment variables in configuration data.
        
        Args:
            data: Configuration data to process
            
        Returns:
            Data with environment variables substituted
        """
        if isinstance(data, dict):
            return {k: self._substitute_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._substitute_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith('${') and data.endswith('}'):
            # Extract environment variable name
            env_var = data[2:-1]
            return os.getenv(env_var, data)  # Return original if env var not found
        else:
            return data
    
    def _merge_config(self, new_data: Dict[str, Any]) -> None:
        """
        Merge new configuration data with existing data.
        
        Args:
            new_data: New configuration data to merge
        """
        def merge_dicts(target: Dict[str, Any], source: Dict[str, Any]) -> None:
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    merge_dicts(target[key], value)
                else:
                    target[key] = value
        
        merge_dicts(self.config_data, new_data)