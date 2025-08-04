"""
Executor Registry

Manages registration and discovery of task executors.
"""

from typing import Dict, List, Optional, Set
from datetime import datetime
import asyncio

from .base_executor import BaseExecutor, ExecutorCapability, ExecutorStatus, ExecutorInfo
from ..workflows.task import Task


class ExecutorRegistry:
    """
    Registry for managing task executors.
    
    Provides executor registration, discovery, and assignment capabilities.
    """
    
    def __init__(self):
        """Initialize the executor registry."""
        self._executors: Dict[str, BaseExecutor] = {}
        self._executors_by_capability: Dict[ExecutorCapability, Set[str]] = {}
        self._executors_by_task_type: Dict[str, Set[str]] = {}
        self._created_at = datetime.now()
    
    def register_executor(self, executor: BaseExecutor) -> None:
        """
        Register an executor.
        
        Args:
            executor: Executor to register
        """
        executor_id = executor.executor_id
        
        # Store executor
        self._executors[executor_id] = executor
        
        # Index by capabilities
        for capability in executor.capabilities:
            if capability not in self._executors_by_capability:
                self._executors_by_capability[capability] = set()
            self._executors_by_capability[capability].add(executor_id)
        
        # Index by supported task types
        for task_type in executor.get_supported_task_types():
            if task_type not in self._executors_by_task_type:
                self._executors_by_task_type[task_type] = set()
            self._executors_by_task_type[task_type].add(executor_id)
    
    def unregister_executor(self, executor_id: str) -> bool:
        """
        Unregister an executor.
        
        Args:
            executor_id: ID of executor to unregister
            
        Returns:
            True if executor was found and removed
        """
        if executor_id not in self._executors:
            return False
        
        executor = self._executors[executor_id]
        
        # Remove from capability index
        for capability in executor.capabilities:
            if capability in self._executors_by_capability:
                self._executors_by_capability[capability].discard(executor_id)
                if not self._executors_by_capability[capability]:
                    del self._executors_by_capability[capability]
        
        # Remove from task type index
        for task_type in executor.get_supported_task_types():
            if task_type in self._executors_by_task_type:
                self._executors_by_task_type[task_type].discard(executor_id)
                if not self._executors_by_task_type[task_type]:
                    del self._executors_by_task_type[task_type]
        
        # Remove executor
        del self._executors[executor_id]
        return True
    
    def get_executor(self, executor_id: str) -> Optional[BaseExecutor]:
        """
        Get an executor by ID.
        
        Args:
            executor_id: Executor ID
            
        Returns:
            Executor instance or None if not found
        """
        return self._executors.get(executor_id)
    
    def get_all_executors(self) -> Dict[str, BaseExecutor]:
        """
        Get all registered executors.
        
        Returns:
            Dictionary of executor_id -> executor
        """
        return self._executors.copy()
    
    def get_available_executors(self) -> List[BaseExecutor]:
        """
        Get all available executors.
        
        Returns:
            List of available executors
        """
        return [
            executor for executor in self._executors.values()
            if executor.is_available()
        ]
    
    def get_executors_by_capability(self, capability: ExecutorCapability) -> List[BaseExecutor]:
        """
        Get executors with a specific capability.
        
        Args:
            capability: Required capability
            
        Returns:
            List of executors with the capability
        """
        executor_ids = self._executors_by_capability.get(capability, set())
        return [
            self._executors[executor_id]
            for executor_id in executor_ids
            if executor_id in self._executors
        ]
    
    def get_executors_for_task_type(self, task_type: str) -> List[BaseExecutor]:
        """
        Get executors that can handle a specific task type.
        
        Args:
            task_type: Task type
            
        Returns:
            List of compatible executors
        """
        executor_ids = self._executors_by_task_type.get(task_type, set())
        return [
            self._executors[executor_id]
            for executor_id in executor_ids
            if executor_id in self._executors
        ]
    
    def find_best_executor_for_task(self, task: Task) -> Optional[BaseExecutor]:
        """
        Find the best available executor for a task.
        
        Args:
            task: Task to find executor for
            
        Returns:
            Best executor for the task or None if none available
        """
        # Get executors that can handle this task type
        compatible_executors = self.get_executors_for_task_type(task.task_type)
        
        # Filter for available executors that can handle the task
        available_executors = [
            executor for executor in compatible_executors
            if executor.is_available() and executor.can_handle_task(task)
        ]
        
        if not available_executors:
            return None
        
        # Score executors and return the best one
        scored_executors = []
        for executor in available_executors:
            score = self._calculate_executor_score(executor, task)
            scored_executors.append((score, executor))
        
        # Sort by score (highest first) and return best executor
        scored_executors.sort(key=lambda x: x[0], reverse=True)
        return scored_executors[0][1]
    
    def _calculate_executor_score(self, executor: BaseExecutor, task: Task) -> float:
        """
        Calculate a score for how well an executor matches a task.
        
        Args:
            executor: Executor to score
            task: Task to match against
            
        Returns:
            Score from 0.0 to 1.0 (higher is better)
        """
        score = 0.0
        
        # Base score for being available
        if executor.is_available():
            score += 0.3
        
        # Score based on current load (lower load is better)
        load_ratio = len(executor.current_tasks) / executor.max_concurrent_tasks
        score += (1.0 - load_ratio) * 0.3
        
        # Score based on success rate
        total_tasks = executor.completed_tasks + executor.failed_tasks
        if total_tasks > 0:
            success_rate = executor.completed_tasks / total_tasks
            score += success_rate * 0.2
        else:
            score += 0.1  # New executor gets neutral score
        
        # Score based on task type specialization
        if task.task_type in executor.get_supported_task_types():
            score += 0.2
        
        return min(1.0, score)
    
    def get_registry_stats(self) -> Dict[str, any]:
        """
        Get registry statistics.
        
        Returns:
            Dictionary containing registry statistics
        """
        total_executors = len(self._executors)
        available_executors = len(self.get_available_executors())
        
        status_counts = {}
        for executor in self._executors.values():
            status = executor.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        capability_counts = {}
        for capability, executor_ids in self._executors_by_capability.items():
            capability_counts[capability.value] = len(executor_ids)
        
        task_type_counts = {}
        for task_type, executor_ids in self._executors_by_task_type.items():
            task_type_counts[task_type] = len(executor_ids)
        
        return {
            "total_executors": total_executors,
            "available_executors": available_executors,
            "status_distribution": status_counts,
            "capability_distribution": capability_counts,
            "task_type_distribution": task_type_counts,
            "created_at": self._created_at.isoformat()
        }
    
    def get_executor_infos(self) -> List[ExecutorInfo]:
        """
        Get information about all registered executors.
        
        Returns:
            List of ExecutorInfo objects
        """
        return [executor.get_info() for executor in self._executors.values()]
    
    async def start_all_executors(self) -> None:
        """Start all registered executors."""
        tasks = []
        for executor in self._executors.values():
            tasks.append(executor.start())
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stop_all_executors(self) -> None:
        """Stop all registered executors."""
        tasks = []
        for executor in self._executors.values():
            tasks.append(executor.stop())
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def cleanup_failed_executors(self) -> List[str]:
        """
        Remove executors that are in error state.
        
        Returns:
            List of removed executor IDs
        """
        failed_executor_ids = [
            executor_id for executor_id, executor in self._executors.items()
            if executor.status == ExecutorStatus.ERROR
        ]
        
        for executor_id in failed_executor_ids:
            self.unregister_executor(executor_id)
        
        return failed_executor_ids