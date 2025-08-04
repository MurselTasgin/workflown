"""
Core Workflow Abstractions

This module provides abstract base classes and interfaces for workflows
and tasks in the enhanced agent framework.
"""

from .base_workflow import BaseWorkflow, WorkflowState, WorkflowResult
from .task import Task, TaskState, TaskResult, TaskDependency
from .execution_context import ExecutionContext, ContextManager

__all__ = [
    "BaseWorkflow",
    "WorkflowState",
    "WorkflowResult",
    "Task",
    "TaskState", 
    "TaskResult",
    "TaskDependency",
    "ExecutionContext",
    "ContextManager"
]