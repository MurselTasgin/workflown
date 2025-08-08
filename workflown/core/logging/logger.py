"""
Core Logger Implementation

Provides structured logging with context tracking and multiple output formats.
"""

import asyncio
import json
import sys
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from datetime import datetime
from pathlib import Path
import traceback
import uuid
import threading


class LogLevel(IntEnum):
    """Log level enumeration with numeric values for comparison."""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: datetime
    level: LogLevel
    message: str
    logger_name: str
    module: str = ""
    function: str = ""
    line_number: int = 0
    thread_id: str = ""
    correlation_id: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[str] = None
    stack_trace: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "level_num": self.level.value,
            "message": self.message,
            "logger": self.logger_name,
            "module": self.module,
            "function": self.function,
            "line": self.line_number,
            "thread": self.thread_id,
            "correlation_id": self.correlation_id,
            "context": self.context,
            "exception": self.exception,
            "stack_trace": self.stack_trace
        }


class LogHandler:
    """Base class for log handlers."""
    
    def __init__(self, name: str, level: LogLevel = LogLevel.INFO):
        self.name = name
        self.level = level
        self.formatter = None
    
    def set_formatter(self, formatter):
        """Set the formatter for this handler."""
        self.formatter = formatter
    
    def should_handle(self, entry: LogEntry) -> bool:
        """Check if this handler should process the log entry."""
        return entry.level >= self.level
    
    async def handle(self, entry: LogEntry) -> None:
        """Handle a log entry."""
        if self.should_handle(entry):
            await self.emit(entry)
    
    async def emit(self, entry: LogEntry) -> None:
        """Emit a log entry (override in subclasses)."""
        pass
    
    def format(self, entry: LogEntry) -> str:
        """Format a log entry using the configured formatter."""
        if self.formatter:
            return self.formatter.format(entry)
        return entry.message


class WorkflownLogger:
    """
    Comprehensive logger for the workflow system.
    
    Features:
    - Structured logging with context
    - Multiple handlers and formatters
    - Correlation ID tracking
    - Async-safe operation
    - Performance metrics
    """
    
    def __init__(
        self,
        name: str,
        level: LogLevel = LogLevel.INFO,
        correlation_id: str = None
    ):
        """
        Initialize the logger.
        
        Args:
            name: Logger name
            level: Minimum log level
            correlation_id: Optional correlation ID for request tracking
        """
        self.name = name
        self.level = level
        self.correlation_id = correlation_id or str(uuid.uuid4())
        
        # Handlers and context
        self.handlers: List[LogHandler] = []
        self.context: Dict[str, Any] = {}
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Metrics
        self.log_counts = {level: 0 for level in LogLevel}
        self.created_at = datetime.now()
    
    def add_handler(self, handler: LogHandler) -> None:
        """Add a log handler."""
        with self._lock:
            self.handlers.append(handler)
    
    def remove_handler(self, handler: LogHandler) -> None:
        """Remove a log handler."""
        with self._lock:
            if handler in self.handlers:
                self.handlers.remove(handler)
    
    def set_level(self, level: LogLevel) -> None:
        """Set the minimum log level."""
        self.level = level
    
    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for request tracking."""
        self.correlation_id = correlation_id
    
    def add_context(self, **kwargs) -> None:
        """Add context fields to all log entries."""
        self.context.update(kwargs)
    
    def remove_context(self, *keys) -> None:
        """Remove context fields."""
        for key in keys:
            self.context.pop(key, None)
    
    def clear_context(self) -> None:
        """Clear all context fields."""
        self.context.clear()
    
    async def log(
        self,
        level: LogLevel,
        message: str,
        exception: Exception = None,
        extra_context: Dict[str, Any] = None,
        **kwargs
    ) -> None:
        """
        Log a message at the specified level.
        
        Args:
            level: Log level
            message: Log message
            exception: Optional exception to log
            extra_context: Additional context for this log entry
            **kwargs: Additional context as keyword arguments
        """
        if level < self.level:
            return
        
        # Get caller information
        frame = sys._getframe(2)
        
        # Build context
        entry_context = {**self.context}
        if extra_context:
            entry_context.update(extra_context)
        if kwargs:
            entry_context.update(kwargs)
        
        # Create log entry
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            logger_name=self.name,
            module=frame.f_globals.get('__name__', ''),
            function=frame.f_code.co_name,
            line_number=frame.f_lineno,
            thread_id=str(threading.current_thread().ident),
            correlation_id=self.correlation_id,
            context=entry_context,
            exception=str(exception) if exception else None,
            stack_trace=traceback.format_exc() if exception else None
        )
        
        # Update metrics
        self.log_counts[level] += 1
        
        # Send to handlers
        await self._emit_to_handlers(entry)
    
    async def debug(self, message: str, **kwargs) -> None:
        """Log a debug message."""
        await self.log(LogLevel.DEBUG, message, **kwargs)
    
    async def info(self, message: str, **kwargs) -> None:
        """Log an info message."""
        await self.log(LogLevel.INFO, message, **kwargs)
    
    async def warning(self, message: str, **kwargs) -> None:
        """Log a warning message."""
        await self.log(LogLevel.WARNING, message, **kwargs)
    
    async def error(self, message: str, exception: Exception = None, **kwargs) -> None:
        """Log an error message."""
        await self.log(LogLevel.ERROR, message, exception=exception, **kwargs)
    
    async def critical(self, message: str, exception: Exception = None, **kwargs) -> None:
        """Log a critical message."""
        await self.log(LogLevel.CRITICAL, message, exception=exception, **kwargs)
    
    async def exception(self, message: str, **kwargs) -> None:
        """Log an exception with stack trace."""
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if exc_value:
            await self.log(LogLevel.ERROR, message, exception=exc_value, **kwargs)
        else:
            await self.error(message, **kwargs)
    
    async def task_started(self, task_id: str, task_type: str, **kwargs) -> None:
        """Log task start event."""
        await self.info(
            f"Task started: {task_id}",
            task_id=task_id,
            task_type=task_type,
            event_type="task_started",
            **kwargs
        )
    
    async def task_completed(self, task_id: str, execution_time: float, success: bool, **kwargs) -> None:
        """Log task completion event."""
        level = LogLevel.INFO if success else LogLevel.ERROR
        status = "completed" if success else "failed"
        
        await self.log(
            level,
            f"Task {status}: {task_id} (took {execution_time:.2f}s)",
            task_id=task_id,
            execution_time=execution_time,
            success=success,
            event_type="task_completed",
            **kwargs
        )
    
    async def workflow_started(self, workflow_id: str, workflow_type: str, **kwargs) -> None:
        """Log workflow start event."""
        await self.info(
            f"Workflow started: {workflow_id}",
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            event_type="workflow_started",
            **kwargs
        )
    
    async def workflow_completed(self, workflow_id: str, total_time: float, success: bool, **kwargs) -> None:
        """Log workflow completion event."""
        level = LogLevel.INFO if success else LogLevel.ERROR
        status = "completed" if success else "failed"
        
        await self.log(
            level,
            f"Workflow {status}: {workflow_id} (took {total_time:.2f}s)",
            workflow_id=workflow_id,
            total_time=total_time,
            success=success,
            event_type="workflow_completed",
            **kwargs
        )
    
    async def performance_metric(self, metric_name: str, value: float, unit: str = "", **kwargs) -> None:
        """Log a performance metric."""
        await self.info(
            f"Performance metric: {metric_name} = {value}{unit}",
            metric_name=metric_name,
            metric_value=value,
            metric_unit=unit,
            event_type="performance_metric",
            **kwargs
        )
    
    async def audit_log(self, action: str, resource: str, user: str = "", **kwargs) -> None:
        """Log an audit event."""
        await self.info(
            f"Audit: {user} performed {action} on {resource}",
            action=action,
            resource=resource,
            user=user,
            event_type="audit",
            **kwargs
        )
    
    async def _emit_to_handlers(self, entry: LogEntry) -> None:
        """Emit log entry to all handlers."""
        handlers = self.handlers.copy()  # Thread-safe copy
        
        if handlers:
            # Run handlers concurrently
            tasks = [handler.handle(entry) for handler in handlers]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get logger statistics."""
        return {
            "name": self.name,
            "level": self.level.name,
            "correlation_id": self.correlation_id,
            "handler_count": len(self.handlers),
            "log_counts": {level.name: count for level, count in self.log_counts.items()},
            "total_logs": sum(self.log_counts.values()),
            "created_at": self.created_at.isoformat(),
            "context_fields": list(self.context.keys())
        }
    
    def child(self, name: str, **context) -> 'WorkflownLogger':
        """Create a child logger with additional context."""
        child_name = f"{self.name}.{name}"
        child = WorkflownLogger(child_name, self.level, self.correlation_id)
        child.context = {**self.context, **context}
        child.handlers = self.handlers.copy()
        return child

    # ------------------------------------------------------------------
    # Sync helpers for use in non-async contexts
    # ------------------------------------------------------------------
    def _run_async_safely(self, coro) -> None:
        """Run or schedule an async logging coroutine without requiring await."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            # No running loop
            asyncio.run(coro)

    def info_sync(self, message: str, **kwargs) -> None:
        self._run_async_safely(self.info(message, **kwargs))

    def warning_sync(self, message: str, **kwargs) -> None:
        self._run_async_safely(self.warning(message, **kwargs))

    def error_sync(self, message: str, exception: Exception = None, **kwargs) -> None:
        self._run_async_safely(self.error(message, exception=exception, **kwargs))


# Global logger registry
_loggers: Dict[str, WorkflownLogger] = {}
_logger_lock = threading.Lock()


def get_logger(name: str, level: LogLevel = LogLevel.INFO) -> WorkflownLogger:
    """
    Get or create a logger instance.
    
    Args:
        name: Logger name
        level: Log level
        
    Returns:
        WorkflownLogger instance
    """
    with _logger_lock:
        if name not in _loggers:
            _loggers[name] = WorkflownLogger(name, level)
        return _loggers[name]


def configure_root_logger(level: LogLevel = LogLevel.INFO, handlers: List[LogHandler] = None) -> WorkflownLogger:
    """
    Configure the root logger.
    
    Args:
        level: Log level
        handlers: List of handlers to add
        
    Returns:
        Root logger instance
    """
    root = get_logger("workflown", level)
    
    if handlers:
        # Clear existing handlers
        root.handlers.clear()
        for handler in handlers:
            root.add_handler(handler)
    
    return root