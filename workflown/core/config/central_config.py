"""
Central Configuration Module

Provides centralized configuration management with environment variable support,
validation, and type conversion for the workflow execution framework.
"""

import os
from typing import Any, Dict, Optional, Union, List, Type
from dataclasses import dataclass, field
from pathlib import Path
import yaml
import json
from dotenv import load_dotenv


@dataclass
class ConfigSpec:
    """Configuration specification for validation and type conversion."""
    key: str
    default: Any
    required: bool = False
    data_type: Type = str
    description: str = ""
    validator: Optional[callable] = None
    env_var: Optional[str] = None


class CentralConfig:
    """
    Central configuration manager with environment variable support.
    
    Handles loading from .env files, YAML configs, and provides
    typed access to configuration values with validation.
    """
    
    def __init__(self, env_file: str = ".env", config_dir: str = "config"):
        """
        Initialize the central configuration.
        
        Args:
            env_file: Path to environment file
            config_dir: Directory containing configuration files
        """
        self.env_file = env_file
        self.config_dir = Path(config_dir)
        self.config_data: Dict[str, Any] = {}
        self.env_vars: Dict[str, str] = {}
        
        # Configuration specifications
        self.config_specs: Dict[str, ConfigSpec] = {}
        
        # Load environment variables first
        self._load_env_vars()
        
        # Register default configuration specs
        self._register_default_specs()
    
    def _load_env_vars(self) -> None:
        """Load environment variables from .env file and system."""
        # Search for .env file from current directory up to project root
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = None
        
        # Walk up the directory tree to find project root (where .env should be)
        while current_dir != os.path.dirname(current_dir):  # Stop at filesystem root
            env_path = os.path.join(current_dir, self.env_file)
            if os.path.exists(env_path):
                project_root = current_dir
                print(f"Found .env file at: {env_path}")
                load_dotenv(env_path)
                break
            current_dir = os.path.dirname(current_dir)
        
        if not project_root:
            print(f"Warning: No .env file found. Searched from {os.path.dirname(os.path.abspath(__file__))} up to filesystem root")
        
        # Store all environment variables
        self.env_vars = dict(os.environ)
    
    def _register_default_specs(self) -> None:
        """Register default configuration specifications."""
        # Framework Configuration
        self.register_config_spec(ConfigSpec(
            key="framework.debug",
            default=False,
            required=False,
            data_type=bool,
            description="Enable debug mode",
            env_var="DEBUG_MODE"
        ))
        
        self.register_config_spec(ConfigSpec(
            key="framework.log_level",
            default="INFO",
            required=False,
            data_type=str,
            description="Logging level",
            env_var="LOG_LEVEL",
            validator=lambda x: x.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        ))
        
        self.register_config_spec(ConfigSpec(
            key="framework.max_concurrent_tasks",
            default=10,
            required=False,
            data_type=int,
            description="Maximum concurrent tasks",
            env_var="MAX_CONCURRENT_TASKS",
            validator=lambda x: x > 0
        ))
        
        # Database Configuration
        self.register_config_spec(ConfigSpec(
            key="database.url",
            default="sqlite:///workflown.db",
            required=False,
            data_type=str,
            description="Database connection URL",
            env_var="DATABASE_URL"
        ))
        
        self.register_config_spec(ConfigSpec(
            key="database.pool_size",
            default=10,
            required=False,
            data_type=int,
            description="Database connection pool size",
            env_var="DATABASE_POOL_SIZE",
            validator=lambda x: x > 0
        ))
        
        # Storage Configuration
        self.register_config_spec(ConfigSpec(
            key="storage.backend",
            default="filesystem",
            required=False,
            data_type=str,
            description="Storage backend type",
            env_var="STORAGE_BACKEND",
            validator=lambda x: x in ["filesystem", "s3", "azure", "gcs"]
        ))
        
        self.register_config_spec(ConfigSpec(
            key="storage.path",
            default="./data",
            required=False,
            data_type=str,
            description="Storage path or bucket name",
            env_var="STORAGE_PATH"
        ))
        
        # API Configuration
        self.register_config_spec(ConfigSpec(
            key="api.host",
            default="localhost",
            required=False,
            data_type=str,
            description="API server host",
            env_var="API_HOST"
        ))
        
        self.register_config_spec(ConfigSpec(
            key="api.port",
            default=8000,
            required=False,
            data_type=int,
            description="API server port",
            env_var="API_PORT",
            validator=lambda x: 1024 <= x <= 65535
        ))
        
        # Security Configuration
        self.register_config_spec(ConfigSpec(
            key="security.secret_key",
            default="",
            required=False,
            data_type=str,
            description="Secret key for encryption and tokens",
            env_var="SECRET_KEY"
        ))
        
        self.register_config_spec(ConfigSpec(
            key="security.token_expiry",
            default=3600,
            required=False,
            data_type=int,
            description="Token expiry time in seconds",
            env_var="TOKEN_EXPIRY",
            validator=lambda x: x > 0
        ))
        
        # Azure OpenAI Configuration
        self.register_config_spec(ConfigSpec(
            key="azure_openai.api_key",
            default="",
            required=False,
            data_type=str,
            description="Azure OpenAI API key",
            env_var="AZURE_OPENAI_API_KEY"
        ))
        
        self.register_config_spec(ConfigSpec(
            key="azure_openai.endpoint",
            default="",
            required=False,
            data_type=str,
            description="Azure OpenAI endpoint URL",
            env_var="AZURE_OPENAI_ENDPOINT"
        ))
        
        self.register_config_spec(ConfigSpec(
            key="azure_openai.deployment_name",
            default="gpt-4o-mini",
            required=False,
            data_type=str,
            description="Azure OpenAI deployment name",
            env_var="AZURE_OPENAI_DEPLOYMENT_NAME"
        ))
        
        self.register_config_spec(ConfigSpec(
            key="azure_openai.model_name",
            default="gpt-4o-mini",
            required=False,
            data_type=str,
            description="Azure OpenAI model name",
            env_var="AZURE_OPENAI_MODEL_NAME"
        ))
        
        self.register_config_spec(ConfigSpec(
            key="azure_openai.api_version",
            default="2024-02-15-preview",
            required=False,
            data_type=str,
            description="Azure OpenAI API version",
            env_var="AZURE_OPENAI_API_VERSION"
        ))
        
        self.register_config_spec(ConfigSpec(
            key="azure_openai.max_tokens",
            default=2000,
            required=False,
            data_type=int,
            description="Maximum tokens for Azure OpenAI requests",
            env_var="AZURE_OPENAI_MAX_TOKENS",
            validator=lambda x: x > 0
        ))
        
        self.register_config_spec(ConfigSpec(
            key="azure_openai.temperature",
            default=0.7,
            required=False,
            data_type=float,
            description="Temperature for Azure OpenAI requests",
            env_var="AZURE_OPENAI_TEMPERATURE",
            validator=lambda x: 0.0 <= x <= 2.0
        ))
        
        # Search API Configuration
        self.register_config_spec(ConfigSpec(
            key="search.serpapi_key",
            default="",
            required=False,
            data_type=str,
            description="SerpAPI key for web search",
            env_var="SERPAPI_KEY"
        ))
        
        self.register_config_spec(ConfigSpec(
            key="search.default_engine",
            default="duckduckgo",
            required=False,
            data_type=str,
            description="Default search engine (duckduckgo, serpapi)",
            env_var="SEARCH_DEFAULT_ENGINE"
        ))
        
        # Logging Configuration
        self.register_config_spec(ConfigSpec(
            key="logging.level",
            default="INFO",
            required=False,
            data_type=str,
            description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
            env_var="LOG_LEVEL",
            validator=lambda x: x.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        ))
        
        self.register_config_spec(ConfigSpec(
            key="logging.enable_console",
            default=True,
            required=False,
            data_type=bool,
            description="Enable console logging",
            env_var="LOG_ENABLE_CONSOLE"
        ))
        
        self.register_config_spec(ConfigSpec(
            key="logging.enable_file",
            default=True,
            required=False,
            data_type=bool,
            description="Enable file logging",
            env_var="LOG_ENABLE_FILE"
        ))
        
        self.register_config_spec(ConfigSpec(
            key="logging.enable_structured",
            default=True,
            required=False,
            data_type=bool,
            description="Enable structured JSON logging",
            env_var="LOG_ENABLE_STRUCTURED"
        ))
        
        self.register_config_spec(ConfigSpec(
            key="logging.file_path",
            default="./logs/workflown.log",
            required=False,
            data_type=str,
            description="Path to log file",
            env_var="LOG_FILE_PATH"
        ))
        
        self.register_config_spec(ConfigSpec(
            key="logging.structured_file_path",
            default="./logs/workflown-structured.log",
            required=False,
            data_type=str,
            description="Path to structured log file",
            env_var="LOG_STRUCTURED_FILE_PATH"
        ))
        
        self.register_config_spec(ConfigSpec(
            key="logging.max_file_size",
            default=10 * 1024 * 1024,  # 10MB
            required=False,
            data_type=int,
            description="Maximum log file size in bytes",
            env_var="LOG_MAX_FILE_SIZE",
            validator=lambda x: x > 0
        ))
        
        self.register_config_spec(ConfigSpec(
            key="logging.backup_count",
            default=5,
            required=False,
            data_type=int,
            description="Number of backup log files to keep",
            env_var="LOG_BACKUP_COUNT",
            validator=lambda x: x >= 0
        ))
        
        self.register_config_spec(ConfigSpec(
            key="logging.include_location",
            default=True,
            required=False,
            data_type=bool,
            description="Include file location in log messages",
            env_var="LOG_INCLUDE_LOCATION"
        ))
        
        self.register_config_spec(ConfigSpec(
            key="logging.include_context",
            default=True,
            required=False,
            data_type=bool,
            description="Include context in log messages",
            env_var="LOG_INCLUDE_CONTEXT"
        ))
        
        self.register_config_spec(ConfigSpec(
            key="logging.colored_console",
            default=True,
            required=False,
            data_type=bool,
            description="Use colored output in console",
            env_var="LOG_COLORED_CONSOLE"
        ))
        
        self.register_config_spec(ConfigSpec(
            key="logging.correlation_id_header",
            default="X-Correlation-ID",
            required=False,
            data_type=str,
            description="HTTP header name for correlation ID",
            env_var="LOG_CORRELATION_ID_HEADER"
        ))
    
    def register_config_spec(self, spec: ConfigSpec) -> None:
        """
        Register a configuration specification.
        
        Args:
            spec: Configuration specification to register
        """
        self.config_specs[spec.key] = spec
    
    def load_config(self, config_file: str = None) -> bool:
        """
        Load configuration from files and environment variables.
        
        Args:
            config_file: Specific config file to load (optional)
            
        Returns:
            True if loading successful, False otherwise
        """
        try:
            # Load from YAML files if no specific file specified
            if config_file is None:
                config_files = [
                    "default.yaml",
                    "database.yaml",
                    "storage.yaml",
                    "api.yaml",
                    "security.yaml"
                ]
                
                for file_name in config_files:
                    file_path = self.config_dir / file_name
                    if file_path.exists():
                        self._load_yaml_file(file_path)
            else:
                file_path = self.config_dir / config_file
                if file_path.exists():
                    self._load_yaml_file(file_path)
            
            # Override with environment variables
            self._apply_env_overrides()
            
            # Validate configuration
            return self._validate_config()
            
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return False
    
    def _load_yaml_file(self, file_path: Path) -> None:
        """
        Load configuration from a YAML file.
        
        Args:
            file_path: Path to YAML file
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            if data:
                self._merge_config(data)
    
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
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        for spec in self.config_specs.values():
            if spec.env_var and spec.env_var in self.env_vars:
                env_value = self.env_vars[spec.env_var]
                
                # Convert to appropriate type
                try:
                    if spec.data_type == bool:
                        converted_value = env_value.lower() in ('true', '1', 'yes', 'on')
                    elif spec.data_type == int:
                        converted_value = int(env_value)
                    elif spec.data_type == float:
                        converted_value = float(env_value)
                    else:
                        converted_value = env_value
                    
                    # Set the value using dot notation
                    self._set_nested_value(spec.key, converted_value)
                    
                except (ValueError, TypeError) as e:
                    print(f"Error converting environment variable {spec.env_var}: {e}")
    
    def _set_nested_value(self, key: str, value: Any) -> None:
        """
        Set a nested configuration value using dot notation.
        
        Args:
            key: Dot-separated key (e.g., 'azure_openai.api_key')
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
    
    def _validate_config(self) -> bool:
        """
        Validate configuration against registered specifications.
        
        Returns:
            True if validation passes, False otherwise
        """
        errors = []
        
        for spec in self.config_specs.values():
            value = self.get(spec.key)
            
            # Check required values
            if spec.required and (value is None or value == ""):
                errors.append(f"Required configuration missing: {spec.key}")
                continue
            
            # Skip validation for empty optional values
            if not spec.required and (value is None or value == ""):
                continue
            
            # Type validation
            if value is not None and not isinstance(value, spec.data_type):
                try:
                    # Try to convert
                    if spec.data_type == bool:
                        value = str(value).lower() in ('true', '1', 'yes', 'on')
                    else:
                        value = spec.data_type(value)
                    self._set_nested_value(spec.key, value)
                except (ValueError, TypeError):
                    errors.append(f"Invalid type for {spec.key}: expected {spec.data_type.__name__}")
                    continue
            
            # Custom validation
            if spec.validator and value is not None:
                try:
                    if not spec.validator(value):
                        errors.append(f"Validation failed for {spec.key}: {value}")
                except Exception as e:
                    errors.append(f"Validator error for {spec.key}: {e}")
        
        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        return True
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key (supports dot notation).
        
        Args:
            key: Configuration key (e.g., 'azure_openai.api_key')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        # Check if we have a spec for this key
        if key in self.config_specs:
            spec = self.config_specs[key]
            default = spec.default if default is None else default
        
        keys = key.split('.')
        value = self.config_data
        
        try:
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                    if value is None:
                        return default
                else:
                    return default
            return value
        except (KeyError, TypeError, AttributeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value by key (supports dot notation).
        
        Args:
            key: Configuration key (e.g., 'azure_openai.api_key')
            value: Value to set
        """
        self._set_nested_value(key, value)
    
    def get_section(self, section_name: str) -> Dict[str, Any]:
        """
        Get an entire configuration section.
        
        Args:
            section_name: Name of the configuration section
            
        Returns:
            Dictionary containing section data
        """
        return self.config_data.get(section_name, {})
    
    def get_database_config(self) -> Dict[str, Any]:
        """
        Get database configuration as a dictionary.
        
        Returns:
            Dictionary containing database configuration
        """
        return {
            "url": self.get("database.url"),
            "pool_size": self.get("database.pool_size")
        }
    
    def get_storage_config(self) -> Dict[str, Any]:
        """
        Get storage configuration as a dictionary.
        
        Returns:
            Dictionary containing storage configuration
        """
        return {
            "backend": self.get("storage.backend"),
            "path": self.get("storage.path")
        }
    
    def get_api_config(self) -> Dict[str, Any]:
        """
        Get API configuration as a dictionary.
        
        Returns:
            Dictionary containing API configuration
        """
        return {
            "host": self.get("api.host"),
            "port": self.get("api.port")
        }
    
    def get_security_config(self) -> Dict[str, Any]:
        """
        Get security configuration as a dictionary.
        
        Returns:
            Dictionary containing security configuration
        """
        return {
            "secret_key": self.get("security.secret_key"),
            "token_expiry": self.get("security.token_expiry")
        }
    
    def get_azure_openai_config(self) -> Dict[str, Any]:
        """
        Get Azure OpenAI configuration as a dictionary.
        
        Returns:
            Dictionary containing Azure OpenAI configuration
        """
        return {
            "api_key": self.get("azure_openai.api_key"),
            "endpoint": self.get("azure_openai.endpoint"),
            "deployment_name": self.get("azure_openai.deployment_name"),
            "model_name": self.get("azure_openai.model_name"),
            "api_version": self.get("azure_openai.api_version"),
            "max_tokens": self.get("azure_openai.max_tokens"),
            "temperature": self.get("azure_openai.temperature")
        }
    
    def get_search_config(self) -> Dict[str, Any]:
        """
        Get search API configuration as a dictionary.
        
        Returns:
            Dictionary containing search API configuration
        """
        return {
            "serpapi_key": self.get("search.serpapi_key"),
            "default_engine": self.get("search.default_engine")
        }
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        Get logging configuration as a dictionary.
        
        Returns:
            Dictionary containing logging configuration
        """
        return {
            "level": self.get("logging.level"),
            "enable_console": self.get("logging.enable_console"),
            "enable_file": self.get("logging.enable_file"),
            "enable_structured": self.get("logging.enable_structured"),
            "file_path": self.get("logging.file_path"),
            "structured_file_path": self.get("logging.structured_file_path"),
            "max_file_size": self.get("logging.max_file_size"),
            "backup_count": self.get("logging.backup_count"),
            "include_location": self.get("logging.include_location"),
            "include_context": self.get("logging.include_context"),
            "colored_console": self.get("logging.colored_console"),
            "correlation_id_header": self.get("logging.correlation_id_header")
        }
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current configuration.
        
        Returns:
            Dictionary containing configuration summary
        """
        return {
            "framework": {
                "debug": self.get("framework.debug"),
                "log_level": self.get("framework.log_level"),
                "max_concurrent_tasks": self.get("framework.max_concurrent_tasks")
            },
            "database": {
                "url": self.get("database.url"),
                "pool_size": self.get("database.pool_size")
            },
            "storage": {
                "backend": self.get("storage.backend"),
                "path": self.get("storage.path")
            },
            "api": {
                "host": self.get("api.host"),
                "port": self.get("api.port")
            },
            "security": {
                "secret_key": "***" if self.get("security.secret_key") else None,
                "token_expiry": self.get("security.token_expiry")
            },
            "azure_openai": {
                "api_key": "***" if self.get("azure_openai.api_key") else None,
                "endpoint": self.get("azure_openai.endpoint"),
                "deployment_name": self.get("azure_openai.deployment_name"),
                "model_name": self.get("azure_openai.model_name"),
                "api_version": self.get("azure_openai.api_version"),
                "max_tokens": self.get("azure_openai.max_tokens"),
                "temperature": self.get("azure_openai.temperature")
            },
            "logging": {
                "level": self.get("logging.level"),
                "enable_console": self.get("logging.enable_console"),
                "enable_file": self.get("logging.enable_file"),
                "enable_structured": self.get("logging.enable_structured"),
                "file_path": self.get("logging.file_path"),
                "structured_file_path": self.get("logging.structured_file_path"),
                "max_file_size": self.get("logging.max_file_size"),
                "backup_count": self.get("logging.backup_count"),
                "include_location": self.get("logging.include_location"),
                "include_context": self.get("logging.include_context"),
                "colored_console": self.get("logging.colored_console")
            }
        }


# Global configuration instance
_central_config = None


def get_config() -> CentralConfig:
    """
    Get the global configuration instance.
    
    Returns:
        CentralConfig instance
    """
    global _central_config
    if _central_config is None:
        _central_config = CentralConfig()
        _central_config.load_config()
    return _central_config


def reload_config() -> CentralConfig:
    """
    Reload the global configuration.
    
    Returns:
        Reloaded CentralConfig instance
    """
    global _central_config
    _central_config = CentralConfig()
    _central_config.load_config()
    return _central_config