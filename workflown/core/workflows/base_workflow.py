"""
Base Workflow Abstract Class

Defines the core interface for workflows in the framework.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import uuid
from datetime import datetime


class WorkflowState(Enum):
    """Workflow execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    workflow_id: str
    success: bool
    result: Any
    metadata: Dict[str, Any]
    execution_time: float
    timestamp: datetime
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class BaseWorkflow(ABC):
    """
    Abstract base class for all workflows.
    
    Workflows orchestrate the execution of multiple tasks and agents
    to accomplish complex objectives.
    """
    
    def __init__(self, workflow_id: str = None, config: Dict[str, Any] = None):
        """
        Initialize the workflow.
        
        Args:
            workflow_id: Unique identifier for the workflow
            config: Configuration dictionary
        """
        self.workflow_id = workflow_id or str(uuid.uuid4())
        self.config = config or {}
        self.state = WorkflowState.PENDING
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> WorkflowResult:
        """
        Execute the workflow.
        
        Args:
            context: Execution context and parameters
            
        Returns:
            WorkflowResult containing execution results
        """
        pass
    
    @abstractmethod
    async def pause(self) -> bool:
        """
        Pause workflow execution.
        
        Returns:
            True if paused successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def resume(self) -> bool:
        """
        Resume paused workflow execution.
        
        Returns:
            True if resumed successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def cancel(self) -> bool:
        """
        Cancel workflow execution.
        
        Returns:
            True if cancelled successfully, False otherwise
        """
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current workflow status.
        
        Returns:
            Dictionary containing status information
        """
        return {
            "workflow_id": self.workflow_id,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }