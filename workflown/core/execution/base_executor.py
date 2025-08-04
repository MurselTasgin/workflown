"""
Base Executor Interface

Defines the interface for task executors in the workflow system.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import uuid

from ..workflows.task import Task, TaskResult


class ExecutorStatus(Enum):
    """Executor status states."""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class ExecutorCapability(Enum):
    """Types of executor capabilities."""
    GENERIC = "generic"
    PYTHON = "python"
    SHELL = "shell"
    HTTP = "http"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    CUSTOM = "custom"


@dataclass
class ExecutorInfo:
    """Information about an executor."""
    executor_id: str
    name: str
    description: str
    capabilities: List[ExecutorCapability]
    status: ExecutorStatus
    max_concurrent_tasks: int
    current_load: int
    supported_task_types: List[str]
    version: str
    metadata: Dict[str, Any]


class BaseExecutor(ABC):
    """
    Abstract base class for all task executors.
    
    Executors are responsible for actually running tasks. They can be
    specialized for different types of work (Python scripts, shell commands,
    HTTP requests, etc.) or generic.
    """
    
    def __init__(
        self,
        executor_id: str = None,
        name: str = "",
        description: str = "",
        capabilities: List[ExecutorCapability] = None,
        max_concurrent_tasks: int = 1,
        config: Dict[str, Any] = None
    ):
        """
        Initialize the executor.
        
        Args:
            executor_id: Unique identifier for the executor
            name: Human-readable name
            description: Executor description
            capabilities: List of executor capabilities
            max_concurrent_tasks: Maximum concurrent tasks
            config: Executor configuration
        """
        self.executor_id = executor_id or str(uuid.uuid4())
        self.name = name or f"Executor-{self.executor_id[:8]}"
        self.description = description
        self.capabilities = capabilities or [ExecutorCapability.GENERIC]
        self.max_concurrent_tasks = max_concurrent_tasks
        self.config = config or {}
        
        self.status = ExecutorStatus.IDLE
        self.current_tasks: Dict[str, Task] = {}
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        
        # Plugin system
        self.plugins: Dict[str, Any] = {}
        self.hooks: Dict[str, List[Callable]] = {
            "before_execute": [],
            "after_execute": [],
            "on_error": [],
            "on_success": []
        }
    
    @abstractmethod
    async def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a task and return the result.
        
        Args:
            task: Task to execute
            
        Returns:
            TaskResult containing execution results
        """
        pass
    
    @abstractmethod
    def can_handle_task(self, task: Task) -> bool:
        """
        Check if this executor can handle the given task.
        
        Args:
            task: Task to check
            
        Returns:
            True if executor can handle the task
        """
        pass
    
    def get_info(self) -> ExecutorInfo:
        """
        Get executor information.
        
        Returns:
            ExecutorInfo object
        """
        return ExecutorInfo(
            executor_id=self.executor_id,
            name=self.name,
            description=self.description,
            capabilities=self.capabilities,
            status=self.status,
            max_concurrent_tasks=self.max_concurrent_tasks,
            current_load=len(self.current_tasks),
            supported_task_types=self.get_supported_task_types(),
            version=self.get_version(),
            metadata=self.get_metadata()
        )
    
    def get_supported_task_types(self) -> List[str]:
        """
        Get list of supported task types.
        
        Returns:
            List of supported task type strings
        """
        # Default implementation - subclasses should override
        return ["generic"]
    
    def get_version(self) -> str:
        """
        Get executor version.
        
        Returns:
            Version string
        """
        return "1.0.0"
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get executor metadata.
        
        Returns:
            Metadata dictionary
        """
        return {
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "current_load": len(self.current_tasks)
        }
    
    def is_available(self) -> bool:
        """
        Check if executor is available for new tasks.
        
        Returns:
            True if available
        """
        return (
            self.status == ExecutorStatus.IDLE and
            len(self.current_tasks) < self.max_concurrent_tasks
        )
    
    def add_plugin(self, name: str, plugin: Any) -> None:
        """
        Add a plugin to the executor.
        
        Args:
            name: Plugin name
            plugin: Plugin instance
        """
        self.plugins[name] = plugin
    
    def remove_plugin(self, name: str) -> bool:
        """
        Remove a plugin from the executor.
        
        Args:
            name: Plugin name
            
        Returns:
            True if plugin was removed
        """
        if name in self.plugins:
            del self.plugins[name]
            return True
        return False
    
    def add_hook(self, event: str, callback: Callable) -> None:
        """
        Add a hook callback for an event.
        
        Args:
            event: Event name
            callback: Callback function
        """
        if event in self.hooks:
            self.hooks[event].append(callback)
    
    def remove_hook(self, event: str, callback: Callable) -> bool:
        """
        Remove a hook callback.
        
        Args:
            event: Event name
            callback: Callback function
            
        Returns:
            True if hook was removed
        """
        if event in self.hooks and callback in self.hooks[event]:
            self.hooks[event].remove(callback)
            return True
        return False
    
    async def _run_hooks(self, event: str, *args, **kwargs) -> None:
        """
        Run hooks for an event.
        
        Args:
            event: Event name
            *args: Hook arguments
            **kwargs: Hook keyword arguments
        """
        if event in self.hooks:
            for hook in self.hooks[event]:
                try:
                    if callable(hook):
                        if hasattr(hook, '__call__'):
                            await hook(*args, **kwargs)
                        else:
                            hook(*args, **kwargs)
                except Exception as e:
                    print(f"Hook error in {event}: {e}")
    
    async def start(self) -> None:
        """Start the executor."""
        self.status = ExecutorStatus.IDLE
        self.last_activity = datetime.now()
    
    async def stop(self) -> None:
        """Stop the executor."""
        # Cancel all running tasks
        for task_id, task in self.current_tasks.items():
            task.cancel("Executor shutdown")
        
        self.current_tasks.clear()
        self.status = ExecutorStatus.SHUTDOWN
        self.last_activity = datetime.now()
    
    def __str__(self) -> str:
        return f"{self.name} ({self.executor_id[:8]})"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name} [{self.status.value}]>"