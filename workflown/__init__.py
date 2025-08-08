"""
Workflown - A modular workflow execution framework

A flexible and extensible framework for building and executing complex workflows
with pluggable components, event-driven architecture, and distributed execution capabilities.
"""

__version__ = "0.1.0"
__author__ = "Workflown Team"
__email__ = "contact@workflown.dev"

# Core imports
from .core.config.central_config import CentralConfig
from .core.execution.executor_registry import ExecutorRegistry
from .core.workflows.base_workflow import BaseWorkflow
from .core.workflows.task import Task, TaskResult, TaskState, TaskPriority
from .core.execution.base_executor import BaseExecutor, ExecutorCapability, ExecutorStatus

# Event system
from .core.events.event_bus import EventBus, Event
from .core.events.event_types import EventType, SystemEvent, TaskEvent, ExecutorEvent, WorkflowEvent

# Dispatch system
from .core.dispatch.base_dispatcher import BaseDispatcher, DispatchResult, ExecutorAssignment

# Planning system
from .core.planning.base_planner import BasePlanner, PlanningResult, TaskPlan

# Storage system
from .core.storage.base_storage import BaseStorage

# Tools system
from .core.tools.base_tool import BaseTool, ToolResult, ToolCapability
from .core.tools.tool_registry import ToolRegistry
from .core.tools.tool_mapper import ToolMapper, TaskMapping, MappingStrategy

# Logging
from .core.logging.logger import get_logger

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    
    # Core components
    "CentralConfig",
    "ExecutorRegistry",
    "BaseWorkflow",
    "Task",
    "TaskResult", 
    "TaskState",
    "TaskPriority",
    "BaseExecutor",
    "ExecutorCapability",
    "ExecutorStatus",
    
    # Event system
    "EventBus",
    "Event",
    "EventType",
    "SystemEvent",
    "TaskEvent",
    "ExecutorEvent",
    "WorkflowEvent",
    
    # Dispatch system
    "BaseDispatcher",
    "DispatchResult",
    "ExecutorAssignment",
    
    # Planning system
    "BasePlanner",
    "PlanningResult",
    "TaskPlan",
    
    # Storage system
    "BaseStorage",
    
    # Tools system
    "BaseTool",
    "ToolResult",
    "ToolCapability",
    "ToolRegistry",
    "ToolMapper",
    "TaskMapping",
    "MappingStrategy",
    
    # Logging
    "get_logger",
]


def get_version() -> str:
    """Get the current version of workflown."""
    return __version__


def get_info() -> dict:
    """Get information about the workflown package."""
    return {
        "name": "workflown",
        "version": __version__,
        "author": __author__,
        "email": __email__,
        "description": "A modular workflow execution framework with pluggable components",
    } 