"""
Event Types and Definitions

Defines standard event types used throughout the workflow execution framework.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime
from .event_bus import Event


class EventType(Enum):
    """Standard event types in the framework."""
    
    # System Events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    SYSTEM_CONFIG_UPDATED = "system.config_updated"
    
    # Task Events
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    TASK_PAUSED = "task.paused"
    TASK_RESUMED = "task.resumed"
    
    # Executor Events
    EXECUTOR_REGISTERED = "executor.registered"
    EXECUTOR_STARTED = "executor.started"
    EXECUTOR_STOPPED = "executor.stopped"
    EXECUTOR_ERROR = "executor.error"
    
    # Schedule Events
    SCHEDULE_CREATED = "schedule.created"
    SCHEDULE_UPDATED = "schedule.updated"
    SCHEDULE_DELETED = "schedule.deleted"
    SCHEDULE_TRIGGERED = "schedule.triggered"
    
    # Workflow Events
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_PAUSED = "workflow.paused"
    WORKFLOW_RESUMED = "workflow.resumed"
    
    # Storage Events
    STORAGE_CONNECTED = "storage.connected"
    STORAGE_DISCONNECTED = "storage.disconnected"
    STORAGE_ERROR = "storage.error"
    STORAGE_OPERATION = "storage.operation"
    
    # Resource Events
    RESOURCE_ALLOCATED = "resource.allocated"
    RESOURCE_RELEASED = "resource.released"
    RESOURCE_EXHAUSTED = "resource.exhausted"
    RESOURCE_ERROR = "resource.error"


@dataclass
class SystemEvent(Event):
    """System-level events."""
    
    def __init__(self, event_type: EventType, source: str, data: Dict[str, Any], 
                 correlation_id: Optional[str] = None):
        super().__init__(
            event_type=event_type.value,
            source=source,
            data=data,
            timestamp=datetime.now(),
            correlation_id=correlation_id
        )


@dataclass
class TaskEvent(Event):
    """Task-related events."""
    
    def __init__(self, event_type: EventType, task_id: str, data: Dict[str, Any], 
                 correlation_id: Optional[str] = None):
        super().__init__(
            event_type=event_type.value,
            source=f"task.{task_id}",
            data={**data, "task_id": task_id},
            timestamp=datetime.now(),
            correlation_id=correlation_id
        )


@dataclass
class ExecutorEvent(Event):
    """Executor-related events."""
    
    def __init__(self, event_type: EventType, executor_id: str, data: Dict[str, Any], 
                 correlation_id: Optional[str] = None):
        super().__init__(
            event_type=event_type.value,
            source=f"executor.{executor_id}",
            data={**data, "executor_id": executor_id},
            timestamp=datetime.now(),
            correlation_id=correlation_id
        )


@dataclass
class ScheduleEvent(Event):
    """Schedule-related events."""
    
    def __init__(self, event_type: EventType, schedule_id: str, data: Dict[str, Any], 
                 correlation_id: Optional[str] = None):
        super().__init__(
            event_type=event_type.value,
            source=f"schedule.{schedule_id}",
            data={**data, "schedule_id": schedule_id},
            timestamp=datetime.now(),
            correlation_id=correlation_id
        )


@dataclass
class ResourceEvent(Event):
    """Resource-related events."""
    
    def __init__(self, event_type: EventType, resource_id: str, data: Dict[str, Any], 
                 correlation_id: Optional[str] = None):
        super().__init__(
            event_type=event_type.value,
            source=f"resource.{resource_id}",
            data={**data, "resource_id": resource_id},
            timestamp=datetime.now(),
            correlation_id=correlation_id
        )


@dataclass
class WorkflowEvent(Event):
    """Workflow-related events."""
    
    def __init__(self, event_type: EventType, workflow_id: str, data: Dict[str, Any], 
                 correlation_id: Optional[str] = None):
        super().__init__(
            event_type=event_type.value,
            source=f"workflow.{workflow_id}",
            data={**data, "workflow_id": workflow_id},
            timestamp=datetime.now(),
            correlation_id=correlation_id
        )




# Helper functions for creating common events
def create_system_startup_event() -> SystemEvent:
    """Create a system startup event."""
    return SystemEvent(
        event_type=EventType.SYSTEM_STARTUP,
        source="system",
        data={"timestamp": datetime.now().isoformat()}
    )


def create_system_shutdown_event() -> SystemEvent:
    """Create a system shutdown event."""
    return SystemEvent(
        event_type=EventType.SYSTEM_SHUTDOWN,
        source="system",
        data={"timestamp": datetime.now().isoformat()}
    )


def create_task_started_event(task_id: str, task_type: str, executor_id: str = None) -> TaskEvent:
    """Create a task started event."""
    return TaskEvent(
        event_type=EventType.TASK_STARTED,
        task_id=task_id,
        data={
            "task_type": task_type,
            "executor_id": executor_id,
            "started_at": datetime.now().isoformat()
        }
    )


def create_task_completed_event(task_id: str, execution_time: float, 
                               success: bool, result: str = None) -> TaskEvent:
    """Create a task completed event."""
    return TaskEvent(
        event_type=EventType.TASK_COMPLETED,
        task_id=task_id,
        data={
            "execution_time": execution_time,
            "success": success,
            "result": result,
            "completed_at": datetime.now().isoformat()
        }
    )


def create_workflow_started_event(workflow_id: str, workflow_type: str) -> WorkflowEvent:
    """Create a workflow started event."""
    return WorkflowEvent(
        event_type=EventType.WORKFLOW_STARTED,
        workflow_id=workflow_id,
        data={
            "workflow_type": workflow_type,
            "started_at": datetime.now().isoformat()
        }
    )