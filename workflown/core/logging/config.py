"""
Centralized Logging Configuration

Provides centralized logging setup using the central_config module.
Ensures physical logs are written to files with proper configuration.
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from workflown.core.config.central_config import get_config
from workflown.core.logging.logger import get_logger, LogLevel, configure_root_logger
from workflown.core.logging.handlers import ConsoleHandler, FileHandler, StructuredHandler
from workflown.core.logging.formatters import StandardFormatter, JSONFormatter, ColoredFormatter


class LoggingConfigurator:
    """
    Centralized logging configuration using central_config.
    
    Handles setup of console, file, and structured logging based on
    configuration from the central config module.
    """
    
    def __init__(self, config=None):
        """
        Initialize logging configurator.
        
        Args:
            config: Optional config instance (uses get_config() if None)
        """
        self.config = config or get_config()
        self.logging_config = self.config.get_logging_config()
        self._configured = False
    
    def _get_log_level(self) -> LogLevel:
        """Get log level from configuration."""
        level_str = self.logging_config.get("level", "INFO").upper()
        level_map = {
            "DEBUG": LogLevel.DEBUG,
            "INFO": LogLevel.INFO,
            "WARNING": LogLevel.WARNING,
            "ERROR": LogLevel.ERROR,
            "CRITICAL": LogLevel.CRITICAL
        }
        return level_map.get(level_str, LogLevel.INFO)
    
    def _ensure_log_directory(self, file_path: str) -> Path:
        """
        Ensure log directory exists.
        
        Args:
            file_path: Path to log file
            
        Returns:
            Path object for the log file
        """
        log_path = Path(file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return log_path
    
    async def setup_logging(self, logger_name: str = "workflown") -> Any:
        """
        Set up comprehensive logging based on central configuration.
        
        Args:
            logger_name: Name for the root logger
            
        Returns:
            Configured logger instance
        """
        if self._configured:
            return get_logger(logger_name)
        
        # Get configuration
        level = self._get_log_level()
        handlers = []
        
        # Console handler
        if self.logging_config.get("enable_console", True):
            console_handler = ConsoleHandler(
                name="console",
                level=level,
                colored=self.logging_config.get("colored_console", True)
            )
            
            # Use colored formatter for console
            if self.logging_config.get("colored_console", True):
                console_handler.set_formatter(ColoredFormatter(
                    fmt="{timestamp} [{level:8}] {logger}: {message}",
                    include_context=self.logging_config.get("include_context", True),
                    include_location=self.logging_config.get("include_location", False)
                ))
            else:
                console_handler.set_formatter(StandardFormatter(
                    fmt="{timestamp} [{level:8}] {logger}: {message}",
                    include_context=self.logging_config.get("include_context", True),
                    include_location=self.logging_config.get("include_location", False)
                ))
            
            handlers.append(console_handler)
        
        # File handler for physical logs
        if self.logging_config.get("enable_file", True):
            file_path = self.logging_config.get("file_path", "./logs/workflown.log")
            log_file = self._ensure_log_directory(file_path)
            
            file_handler = FileHandler(
                name="file",
                level=level,
                filename=str(log_file),
                max_size=self.logging_config.get("max_file_size", 10 * 1024 * 1024),
                backup_count=self.logging_config.get("backup_count", 5)
            )
            
            file_handler.set_formatter(StandardFormatter(
                fmt="{timestamp} [{level:8}] {logger}: {message}",
                include_context=self.logging_config.get("include_context", True),
                include_location=self.logging_config.get("include_location", True)
            ))
            
            handlers.append(file_handler)
        
        # Structured handler for machine-readable logs
        if self.logging_config.get("enable_structured", True):
            structured_path = self.logging_config.get("structured_file_path", "./logs/workflown-structured.log")
            structured_file = self._ensure_log_directory(structured_path)
            
            structured_handler = StructuredHandler(
                name="structured",
                level=level,
                filename=str(structured_file),
                max_size=self.logging_config.get("max_file_size", 10 * 1024 * 1024),
                backup_count=self.logging_config.get("backup_count", 5)
            )
            
            handlers.append(structured_handler)
        
        # Configure root logger
        root_logger = configure_root_logger(level, handlers)
        self._configured = True
        
                # Log configuration summary
        await root_logger.info("Logging system configured", 
                               handlers_count=len(handlers),
                               log_level=level.name,
                               file_logging=self.logging_config.get("enable_file", True),
                               structured_logging=self.logging_config.get("enable_structured", True),
                               console_logging=self.logging_config.get("enable_console", True))
        
        return root_logger
    
    async def setup_application_logging(self, app_name: str = "workflown") -> Any:
        """
        Set up application-specific logging with correlation ID support.
        
        Args:
            app_name: Application name for logging
            
        Returns:
            Configured logger instance
        """
        logger = await self.setup_logging(app_name)
        
        # Add application context
        logger.add_context(
            application=app_name,
            version="1.0.0",
            environment=self.config.get("framework.debug", False) and "development" or "production"
        )
        
        await logger.info("Application logging initialized", 
                         app_name=app_name,
                         config_source="central_config")
        
        return logger
    
    def get_logging_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current logging configuration.
        
        Returns:
            Dictionary containing logging configuration summary
        """
        return {
            "configured": self._configured,
            "level": self.logging_config.get("level", "INFO"),
            "handlers": {
                "console": self.logging_config.get("enable_console", True),
                "file": self.logging_config.get("enable_file", True),
                "structured": self.logging_config.get("enable_structured", True)
            },
            "file_paths": {
                "main": self.logging_config.get("file_path", "./logs/workflown.log"),
                "structured": self.logging_config.get("structured_file_path", "./logs/workflown-structured.log")
            },
            "options": {
                "colored_console": self.logging_config.get("colored_console", True),
                "include_location": self.logging_config.get("include_location", True),
                "include_context": self.logging_config.get("include_context", True),
                "max_file_size": self.logging_config.get("max_file_size", 10 * 1024 * 1024),
                "backup_count": self.logging_config.get("backup_count", 5)
            }
        }


# Global configurator instance
_logging_configurator = None


async def setup_logging_from_config(logger_name: str = "workflown") -> Any:
    """
    Set up logging using central configuration.
    
    Args:
        logger_name: Name for the logger
        
    Returns:
        Configured logger instance
    """
    global _logging_configurator
    if _logging_configurator is None:
        _logging_configurator = LoggingConfigurator()
    
    return await _logging_configurator.setup_logging(logger_name)


async def setup_application_logging_from_config(app_name: str = "workflown") -> Any:
    """
    Set up application logging using central configuration.
    
    Args:
        app_name: Application name
        
    Returns:
        Configured logger instance
    """
    global _logging_configurator
    if _logging_configurator is None:
        _logging_configurator = LoggingConfigurator()
    
    return await _logging_configurator.setup_application_logging(app_name)


def get_logging_summary() -> Dict[str, Any]:
    """
    Get logging configuration summary.
    
    Returns:
        Dictionary containing logging configuration summary
    """
    global _logging_configurator
    if _logging_configurator is None:
        _logging_configurator = LoggingConfigurator()
    
    return _logging_configurator.get_logging_summary()


def create_logging_config_yaml() -> str:
    """
    Create a sample logging configuration YAML.
    
    Returns:
        YAML string with logging configuration
    """
    return """# Logging Configuration
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  enable_console: true
  enable_file: true
  enable_structured: true
  file_path: "./logs/workflown.log"
  structured_file_path: "./logs/workflown-structured.log"
  max_file_size: 10485760  # 10MB in bytes
  backup_count: 5
  include_location: true
  include_context: true
  colored_console: true
  correlation_id_header: "X-Correlation-ID"
""" 