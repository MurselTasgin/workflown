"""
Log Formatters

Various formatters for different log output formats.
"""

import json
from typing import Dict, Any
from datetime import datetime

from .logger import LogEntry, LogLevel


class LogFormatter:
    """Base class for log formatters."""
    
    def format(self, entry: LogEntry) -> str:
        """Format a log entry."""
        return entry.message


class StandardFormatter(LogFormatter):
    """Standard text formatter with timestamps and levels."""
    
    def __init__(
        self,
        fmt: str = None,
        datefmt: str = None,
        include_context: bool = True,
        include_location: bool = False
    ):
        """
        Initialize standard formatter.
        
        Args:
            fmt: Log format string
            datefmt: Date format string
            include_context: Whether to include context fields
            include_location: Whether to include file location info
        """
        self.fmt = fmt or "{timestamp} [{level:8}] {logger}: {message}"
        self.datefmt = datefmt or "%Y-%m-%d %H:%M:%S"
        self.include_context = include_context
        self.include_location = include_location
    
    def format(self, entry: LogEntry) -> str:
        """Format log entry as standard text."""
        # Format timestamp
        timestamp = entry.timestamp.strftime(self.datefmt)
        
        # Base formatting
        formatted = self.fmt.format(
            timestamp=timestamp,
            level=entry.level.name,
            logger=entry.logger_name,
            message=entry.message
        )
        
        # Add location info if requested
        if self.include_location and entry.module:
            location = f" ({entry.module}:{entry.function}:{entry.line_number})"
            formatted += location
        
        # Add context if available and requested
        if self.include_context and entry.context:
            context_str = self._format_context(entry.context)
            formatted += f" | {context_str}"
        
        # Add correlation ID if available
        if entry.correlation_id:
            formatted += f" [correlation_id={entry.correlation_id}]"
        
        # Add exception info if available
        if entry.exception:
            formatted += f"\nException: {entry.exception}"
            if entry.stack_trace:
                formatted += f"\n{entry.stack_trace}"
        
        return formatted
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary."""
        if not context:
            return ""
        
        items = []
        for key, value in context.items():
            if isinstance(value, (str, int, float, bool)):
                items.append(f"{key}={value}")
            else:
                items.append(f"{key}={str(value)[:50]}")
        
        return " ".join(items)


class JSONFormatter(LogFormatter):
    """JSON formatter for structured logging."""
    
    def __init__(
        self,
        indent: int = None,
        ensure_ascii: bool = False,
        include_all_fields: bool = True
    ):
        """
        Initialize JSON formatter.
        
        Args:
            indent: JSON indentation (None for compact)
            ensure_ascii: Whether to escape non-ASCII characters
            include_all_fields: Whether to include all log entry fields
        """
        self.indent = indent
        self.ensure_ascii = ensure_ascii
        self.include_all_fields = include_all_fields
    
    def format(self, entry: LogEntry) -> str:
        """Format log entry as JSON."""
        if self.include_all_fields:
            data = entry.to_dict()
        else:
            # Include only essential fields
            data = {
                "timestamp": entry.timestamp.isoformat(),
                "level": entry.level.name,
                "logger": entry.logger_name,
                "message": entry.message,
                "context": entry.context
            }
            
            if entry.correlation_id:
                data["correlation_id"] = entry.correlation_id
            
            if entry.exception:
                data["exception"] = entry.exception
        
        return json.dumps(
            data,
            indent=self.indent,
            ensure_ascii=self.ensure_ascii,
            default=self._json_serializer,
            separators=(',', ':') if self.indent is None else None
        )
    
    def _json_serializer(self, obj: Any) -> str:
        """JSON serializer for complex objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)


class CompactFormatter(LogFormatter):
    """Compact formatter for high-volume logging."""
    
    def __init__(
        self,
        include_timestamp: bool = True,
        include_level: bool = True,
        max_message_length: int = 200
    ):
        """
        Initialize compact formatter.
        
        Args:
            include_timestamp: Whether to include timestamp
            include_level: Whether to include log level
            max_message_length: Maximum message length
        """
        self.include_timestamp = include_timestamp
        self.include_level = include_level
        self.max_message_length = max_message_length
    
    def format(self, entry: LogEntry) -> str:
        """Format log entry compactly."""
        parts = []
        
        if self.include_timestamp:
            timestamp = entry.timestamp.strftime("%H:%M:%S")
            parts.append(timestamp)
        
        if self.include_level:
            level_abbrev = {
                LogLevel.DEBUG: "DBG",
                LogLevel.INFO: "INF",
                LogLevel.WARNING: "WRN",
                LogLevel.ERROR: "ERR",
                LogLevel.CRITICAL: "CRT"
            }
            parts.append(level_abbrev.get(entry.level, "UNK"))
        
        # Truncate message if too long
        message = entry.message
        if len(message) > self.max_message_length:
            message = message[:self.max_message_length - 3] + "..."
        
        parts.append(message)
        
        # Add key context fields
        if entry.context:
            key_fields = ["task_id", "workflow_id", "executor_id"]
            context_parts = []
            for field in key_fields:
                if field in entry.context:
                    value = str(entry.context[field])
                    if len(value) > 20:
                        value = value[:17] + "..."
                    context_parts.append(f"{field}={value}")
            
            if context_parts:
                parts.append(f"[{' '.join(context_parts)}]")
        
        return " ".join(parts)


class ColoredFormatter(StandardFormatter):
    """Colored formatter for terminal output."""
    
    def __init__(self, **kwargs):
        """Initialize colored formatter."""
        super().__init__(**kwargs)
        
        # ANSI color codes
        self.colors = {
            LogLevel.DEBUG: "\033[36m",    # Cyan
            LogLevel.INFO: "\033[32m",     # Green
            LogLevel.WARNING: "\033[33m",  # Yellow
            LogLevel.ERROR: "\033[31m",    # Red
            LogLevel.CRITICAL: "\033[35m", # Magenta
        }
        self.reset_color = "\033[0m"
        self.bold = "\033[1m"
    
    def format(self, entry: LogEntry) -> str:
        """Format log entry with colors."""
        # Get base formatted string
        formatted = super().format(entry)
        
        # Apply colors
        color = self.colors.get(entry.level, "")
        if color:
            # Color the entire line
            formatted = f"{color}{formatted}{self.reset_color}"
            
            # Make critical messages bold
            if entry.level == LogLevel.CRITICAL:
                formatted = f"{self.bold}{formatted}"
        
        return formatted


class SyslogFormatter(LogFormatter):
    """Syslog-compatible formatter."""
    
    def __init__(self, facility: str = "local0"):
        """
        Initialize syslog formatter.
        
        Args:
            facility: Syslog facility
        """
        self.facility = facility
        
        # Map log levels to syslog priorities
        self.priority_map = {
            LogLevel.DEBUG: 7,      # Debug
            LogLevel.INFO: 6,       # Info
            LogLevel.WARNING: 4,    # Warning
            LogLevel.ERROR: 3,      # Error
            LogLevel.CRITICAL: 2,   # Critical
        }
    
    def format(self, entry: LogEntry) -> str:
        """Format log entry for syslog."""
        priority = self.priority_map.get(entry.level, 6)
        
        # Syslog format: <priority>timestamp hostname program[pid]: message
        timestamp = entry.timestamp.strftime("%b %d %H:%M:%S")
        hostname = "workflown"
        program = entry.logger_name
        
        formatted = f"<{priority}>{timestamp} {hostname} {program}: {entry.message}"
        
        # Add context as structured data
        if entry.context:
            context_str = " ".join(f"{k}={v}" for k, v in entry.context.items())
            formatted += f" [{context_str}]"
        
        return formatted


class DevFormatter(StandardFormatter):
    """Development-friendly formatter with extra details."""
    
    def __init__(self):
        """Initialize development formatter."""
        super().__init__(
            fmt="{timestamp} [{level:8}] {logger} | {message}",
            datefmt="%H:%M:%S.%f",
            include_context=True,
            include_location=True
        )
    
    def format(self, entry: LogEntry) -> str:
        """Format log entry for development."""
        formatted = super().format(entry)
        
        # Add thread info for debugging concurrency issues
        if entry.thread_id:
            formatted += f" [thread={entry.thread_id[-4:]}]"
        
        return formatted