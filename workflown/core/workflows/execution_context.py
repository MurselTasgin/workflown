"""
Execution Context Management

Provides context management for workflow and task execution.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class ExecutionContext:
    """Represents the execution context for workflows and tasks."""
    context_id: str
    workflow_id: Optional[str] = None
    task_id: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.context_id is None:
            self.context_id = str(uuid.uuid4())
    
    def set_variable(self, key: str, value: Any) -> None:
        """Set a variable in the context."""
        self.variables[key] = value
        self.updated_at = datetime.now()
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a variable from the context."""
        return self.variables.get(key, default)
    
    def has_variable(self, key: str) -> bool:
        """Check if a variable exists in the context."""
        return key in self.variables
    
    def remove_variable(self, key: str) -> bool:
        """Remove a variable from the context."""
        if key in self.variables:
            del self.variables[key]
            self.updated_at = datetime.now()
            return True
        return False
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata in the context."""
        self.metadata[key] = value
        self.updated_at = datetime.now()
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata from the context."""
        return self.metadata.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "context_id": self.context_id,
            "workflow_id": self.workflow_id,
            "task_id": self.task_id,
            "variables": self.variables,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class ContextManager:
    """
    Manages execution contexts for workflows and tasks.
    
    Provides context creation, storage, and retrieval functionality.
    """
    
    def __init__(self):
        """Initialize the context manager."""
        self.contexts: Dict[str, ExecutionContext] = {}
        self.active_contexts: List[str] = []
    
    def create_context(self, workflow_id: str = None, task_id: str = None) -> ExecutionContext:
        """
        Create a new execution context.
        
        Args:
            workflow_id: Optional workflow ID
            task_id: Optional task ID
            
        Returns:
            New execution context
        """
        context = ExecutionContext(
            context_id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            task_id=task_id
        )
        
        self.contexts[context.context_id] = context
        self.active_contexts.append(context.context_id)
        
        return context
    
    def get_context(self, context_id: str) -> Optional[ExecutionContext]:
        """
        Get an execution context by ID.
        
        Args:
            context_id: Context ID
            
        Returns:
            Execution context or None if not found
        """
        return self.contexts.get(context_id)
    
    def update_context(self, context_id: str, **kwargs) -> bool:
        """
        Update an execution context.
        
        Args:
            context_id: Context ID
            **kwargs: Variables to update
            
        Returns:
            True if update successful, False otherwise
        """
        context = self.get_context(context_id)
        if not context:
            return False
        
        for key, value in kwargs.items():
            context.set_variable(key, value)
        
        return True
    
    def remove_context(self, context_id: str) -> bool:
        """
        Remove an execution context.
        
        Args:
            context_id: Context ID
            
        Returns:
            True if removal successful, False otherwise
        """
        if context_id in self.contexts:
            del self.contexts[context_id]
            if context_id in self.active_contexts:
                self.active_contexts.remove(context_id)
            return True
        return False
    
    def get_active_contexts(self) -> List[ExecutionContext]:
        """
        Get all active execution contexts.
        
        Returns:
            List of active contexts
        """
        return [self.contexts[cid] for cid in self.active_contexts if cid in self.contexts]
    
    def get_contexts_by_workflow(self, workflow_id: str) -> List[ExecutionContext]:
        """
        Get all contexts for a specific workflow.
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            List of contexts for the workflow
        """
        return [
            context for context in self.contexts.values()
            if context.workflow_id == workflow_id
        ]
    
    def get_contexts_by_task(self, task_id: str) -> List[ExecutionContext]:
        """
        Get all contexts for a specific task.
        
        Args:
            task_id: Task ID
            
        Returns:
            List of contexts for the task
        """
        return [
            context for context in self.contexts.values()
            if context.task_id == task_id
        ]
    
    def clear_contexts(self, workflow_id: str = None) -> int:
        """
        Clear contexts, optionally filtered by workflow.
        
        Args:
            workflow_id: Optional workflow ID to filter by
            
        Returns:
            Number of contexts cleared
        """
        contexts_to_remove = []
        
        for context_id, context in self.contexts.items():
            if workflow_id is None or context.workflow_id == workflow_id:
                contexts_to_remove.append(context_id)
        
        for context_id in contexts_to_remove:
            self.remove_context(context_id)
        
        return len(contexts_to_remove)
    
    def get_context_stats(self) -> Dict[str, Any]:
        """
        Get context manager statistics.
        
        Returns:
            Dictionary containing statistics
        """
        return {
            "total_contexts": len(self.contexts),
            "active_contexts": len(self.active_contexts),
            "contexts_by_workflow": len(set(c.workflow_id for c in self.contexts.values() if c.workflow_id)),
            "contexts_by_task": len(set(c.task_id for c in self.contexts.values() if c.task_id))
        } 