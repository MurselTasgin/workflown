"""
Task Representation

Defines the structure and lifecycle of tasks in the workflow system.
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid


class TaskState(Enum):
    """Task execution states."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class DependencyType(Enum):
    """Types of task dependencies."""
    SEQUENTIAL = "sequential"  # Must complete before this task starts
    PARALLEL = "parallel"      # Can run in parallel but must complete before this finishes
    RESOURCE = "resource"      # Shared resource dependency
    DATA = "data"             # Data dependency


@dataclass
class TaskDependency:
    """Represents a dependency between tasks."""
    dependency_id: str
    dependency_type: DependencyType
    required: bool = True
    condition: Optional[str] = None  # Optional condition for dependency


@dataclass
class TaskResult:
    """Result of task execution."""
    task_id: str
    success: bool
    result: Any
    metadata: Dict[str, Any]
    execution_time: float
    timestamp: datetime
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class TaskMetrics:
    """Performance metrics for task execution."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    retry_count: int = 0


class Task:
    """
    Represents a single task in the workflow system.
    
    Tasks are the basic unit of work that can be executed by executors.
    They support dependencies, priorities, retries, and detailed tracking.
    """
    
    def __init__(
        self,
        task_id: str = None,
        name: str = "",
        description: str = "",
        task_type: str = "generic",
        parameters: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        timeout: float = 300.0,
        tags: List[str] = None
    ):
        """
        Initialize a task.
        
        Args:
            task_id: Unique identifier for the task
            name: Human-readable name
            description: Task description
            task_type: Type/category of the task
            parameters: Task parameters
            priority: Task priority level
            max_retries: Maximum retry attempts
            timeout: Task timeout in seconds
            tags: Optional tags for categorization
        """
        self.task_id = task_id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.task_type = task_type
        self.parameters = parameters or {}
        self.priority = priority
        self.max_retries = max_retries
        self.timeout = timeout
        self.tags = tags or []
        
        # State management
        self.state = TaskState.PENDING
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
        # Dependencies
        self.dependencies: List[TaskDependency] = []
        self.dependents: Set[str] = set()
        
        # Execution tracking
        self.assigned_executor: Optional[str] = None
        self.execution_context: Dict[str, Any] = {}
        self.result: Optional[TaskResult] = None
        self.metrics = TaskMetrics()
        
        # Retry management
        self.retry_count = 0
        self.last_error: Optional[str] = None
        
    def add_dependency(self, dependency: TaskDependency) -> None:
        """
        Add a dependency to this task.
        
        Args:
            dependency: Task dependency to add
        """
        self.dependencies.append(dependency)
        self.updated_at = datetime.now()
    
    def remove_dependency(self, dependency_id: str) -> bool:
        """
        Remove a dependency from this task.
        
        Args:
            dependency_id: ID of dependency to remove
            
        Returns:
            True if dependency was found and removed
        """
        for i, dep in enumerate(self.dependencies):
            if dep.dependency_id == dependency_id:
                self.dependencies.pop(i)
                self.updated_at = datetime.now()
                return True
        return False
    
    def add_dependent(self, task_id: str) -> None:
        """
        Add a task that depends on this task.
        
        Args:
            task_id: ID of dependent task
        """
        self.dependents.add(task_id)
        self.updated_at = datetime.now()
    
    def remove_dependent(self, task_id: str) -> bool:
        """
        Remove a dependent task.
        
        Args:
            task_id: ID of dependent task to remove
            
        Returns:
            True if dependent was found and removed
        """
        if task_id in self.dependents:
            self.dependents.remove(task_id)
            self.updated_at = datetime.now()
            return True
        return False
    
    def can_start(self, completed_tasks: Set[str]) -> bool:
        """
        Check if this task can start based on dependencies.
        
        Args:
            completed_tasks: Set of completed task IDs
            
        Returns:
            True if task can start, False otherwise
        """
        if self.state != TaskState.PENDING:
            return False
        
        # Check all required dependencies
        for dep in self.dependencies:
            if dep.required and dep.dependency_type == DependencyType.SEQUENTIAL:
                if dep.dependency_id not in completed_tasks:
                    return False
        
        return True
    
    def start(self, executor_id: str = None, context: Dict[str, Any] = None) -> None:
        """
        Start task execution.
        
        Args:
            executor_id: ID of executor executing the task
            context: Execution context
        """
        self.state = TaskState.RUNNING
        self.assigned_executor = executor_id
        self.execution_context = context or {}
        self.metrics.start_time = datetime.now()
        self.updated_at = datetime.now()
    
    def complete(self, result: Any, metadata: Dict[str, Any] = None) -> None:
        """
        Mark task as completed.
        
        Args:
            result: Task execution result
            metadata: Optional result metadata
        """
        self.state = TaskState.COMPLETED
        self.metrics.end_time = datetime.now()
        
        if self.metrics.start_time:
            self.metrics.execution_time = (
                self.metrics.end_time - self.metrics.start_time
            ).total_seconds()
        
        self.result = TaskResult(
            task_id=self.task_id,
            success=True,
            result=result,
            metadata=metadata or {},
            execution_time=self.metrics.execution_time,
            timestamp=self.metrics.end_time
        )
        self.updated_at = datetime.now()
    
    def fail(self, error: str, retry: bool = True) -> None:
        """
        Mark task as failed.
        
        Args:
            error: Error message
            retry: Whether to attempt retry
        """
        self.last_error = error
        self.retry_count += 1
        
        if retry and self.retry_count <= self.max_retries:
            self.state = TaskState.PENDING
        else:
            self.state = TaskState.FAILED
            self.metrics.end_time = datetime.now()
            
            if self.metrics.start_time:
                self.metrics.execution_time = (
                    self.metrics.end_time - self.metrics.start_time
                ).total_seconds()
            
            self.result = TaskResult(
                task_id=self.task_id,
                success=False,
                result=None,
                metadata={"error": error, "retry_count": self.retry_count},
                execution_time=self.metrics.execution_time,
                timestamp=self.metrics.end_time,
                errors=[error]
            )
        
        self.updated_at = datetime.now()
    
    def cancel(self, reason: str = "") -> None:
        """
        Cancel task execution.
        
        Args:
            reason: Reason for cancellation
        """
        self.state = TaskState.CANCELLED
        self.metrics.end_time = datetime.now()
        
        if self.metrics.start_time:
            self.metrics.execution_time = (
                self.metrics.end_time - self.metrics.start_time
            ).total_seconds()
        
        self.result = TaskResult(
            task_id=self.task_id,
            success=False,
            result=None,
            metadata={"cancelled": True, "reason": reason},
            execution_time=self.metrics.execution_time,
            timestamp=self.metrics.end_time
        )
        self.updated_at = datetime.now()
    
    def block(self, reason: str = "") -> None:
        """
        Block task execution.
        
        Args:
            reason: Reason for blocking
        """
        self.state = TaskState.BLOCKED
        self.execution_context["blocked_reason"] = reason
        self.updated_at = datetime.now()
    
    def unblock(self) -> None:
        """Unblock task execution."""
        if self.state == TaskState.BLOCKED:
            self.state = TaskState.PENDING
            if "blocked_reason" in self.execution_context:
                del self.execution_context["blocked_reason"]
            self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert task to dictionary representation.
        
        Returns:
            Dictionary representation of the task
        """
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type,
            "parameters": self.parameters,
            "priority": self.priority.value,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "assigned_executor": self.assigned_executor,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "tags": self.tags,
            "dependencies": [
                {
                    "dependency_id": dep.dependency_id,
                    "dependency_type": dep.dependency_type.value,
                    "required": dep.required,
                    "condition": dep.condition
                }
                for dep in self.dependencies
            ],
            "dependents": list(self.dependents),
            "result": self.result.__dict__ if self.result else None,
            "metrics": {
                "start_time": self.metrics.start_time.isoformat() if self.metrics.start_time else None,
                "end_time": self.metrics.end_time.isoformat() if self.metrics.end_time else None,
                "execution_time": self.metrics.execution_time,
                "retry_count": self.metrics.retry_count
            }
        }