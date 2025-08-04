"""
Base Dispatcher Abstract Class

Defines the core interface for dispatchers that assign tasks to executors.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid
from ..planning.base_planner import PlanningResult, TaskPlan
from ..workflows.task import Task, TaskPriority, TaskState


class DispatchStrategy(Enum):
    """Strategies for dispatching tasks to executors."""
    ROUND_ROBIN = "round_robin"        # Distribute tasks evenly
    CAPABILITY_MATCH = "capability_match"  # Match tasks to executor capabilities
    LOAD_BALANCE = "load_balance"      # Balance based on executor workload
    PRIORITY_FIRST = "priority_first"  # Prioritize high-priority tasks
    OPTIMAL_ASSIGNMENT = "optimal"     # Optimize for overall efficiency


class ExecutorStatus(Enum):
    """Status of executors for task assignment."""
    AVAILABLE = "available"
    BUSY = "busy"
    OVERLOADED = "overloaded"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


@dataclass
class ExecutorInfo:
    """Information about an executor for dispatch decisions."""
    executor_id: str
    executor_type: str
    capabilities: List[str]
    current_load: int
    max_capacity: int
    status: ExecutorStatus
    performance_score: float  # 0.0 to 1.0
    last_active: datetime
    preferred_task_types: List[str] = field(default_factory=list)
    blacklisted_task_types: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutorAssignment:
    """Represents an assignment of a task to an executor."""
    assignment_id: str
    task_id: str
    executor_id: str
    assigned_at: datetime
    estimated_completion: datetime
    priority: int
    confidence: float  # Confidence in the assignment quality
    backup_executors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DispatchResult:
    """Result of the dispatch process."""
    dispatch_id: str
    plan_id: str
    assignments: List[ExecutorAssignment]
    unassigned_tasks: List[str]
    dispatch_strategy: DispatchStrategy
    total_estimated_time: float
    confidence: float
    warnings: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DispatchContext:
    """Context for dispatch decisions."""
    session_id: Optional[str] = None
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    resource_constraints: Dict[str, Any] = field(default_factory=dict)
    deadline: Optional[datetime] = None
    quality_requirements: Dict[str, Any] = field(default_factory=dict)
    cost_constraints: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, Any] = field(default_factory=dict)


class BaseDispatcher(ABC):
    """
    Abstract base class for task dispatchers.
    
    Dispatchers are responsible for taking planned tasks and assigning them
    to appropriate executors based on capabilities, availability, and strategy.
    """
    
    def __init__(self, dispatcher_id: str = None, config: Dict[str, Any] = None):
        """
        Initialize the dispatcher.
        
        Args:
            dispatcher_id: Unique identifier for the dispatcher
            config: Configuration dictionary
        """
        self.dispatcher_id = dispatcher_id or str(uuid.uuid4())
        self.config = config or {}
        self.created_at = datetime.now()
        
        # Executor registry
        self._executor_registry: Dict[str, ExecutorInfo] = {}
        
        # Dispatch history
        self._dispatch_history: List[DispatchResult] = []
        self._max_history = config.get("max_history", 1000) if config else 1000
    
    @abstractmethod
    async def dispatch(self, planning_result: PlanningResult, 
                      context: DispatchContext) -> DispatchResult:
        """
        Dispatch tasks from a planning result to available executors.
        
        Args:
            planning_result: Result from the planner containing tasks
            context: Dispatch context with constraints and preferences
            
        Returns:
            DispatchResult with executor assignments
        """
        pass
    
    @abstractmethod
    async def reassign_task(self, assignment_id: str, reason: str,
                           context: DispatchContext) -> Optional[ExecutorAssignment]:
        """
        Reassign a task to a different executor.
        
        Args:
            assignment_id: ID of the assignment to change
            reason: Reason for reassignment
            context: Updated dispatch context
            
        Returns:
            New ExecutorAssignment if successful, None otherwise
        """
        pass
    
    @abstractmethod
    def calculate_executor_suitability(self, task: TaskPlan, executor: ExecutorInfo) -> float:
        """
        Calculate how suitable an executor is for a specific task.
        
        Args:
            task: Task to be assigned
            executor: Executor to evaluate
            
        Returns:
            Suitability score (0.0 to 1.0)
        """
        pass
    
    @abstractmethod
    def select_dispatch_strategy(self, planning_result: PlanningResult,
                                context: DispatchContext) -> DispatchStrategy:
        """
        Select the best dispatch strategy for the given context.
        
        Args:
            planning_result: Planning result with tasks
            context: Dispatch context
            
        Returns:
            Selected DispatchStrategy
        """
        pass
    
    def register_executor(self, executor_info: ExecutorInfo) -> None:
        """
        Register an executor for task assignment.
        
        Args:
            executor_info: Information about the executor
        """
        self._executor_registry[executor_info.executor_id] = executor_info
    
    def unregister_executor(self, executor_id: str) -> bool:
        """
        Unregister an executor.
        
        Args:
            executor_id: ID of executor to remove
            
        Returns:
            True if executor was found and removed
        """
        if executor_id in self._executor_registry:
            del self._executor_registry[executor_id]
            return True
        return False
    
    def get_executor_info(self, executor_id: str) -> Optional[ExecutorInfo]:
        """
        Get information about a specific executor.
        
        Args:
            executor_id: Executor ID
            
        Returns:
            ExecutorInfo or None if not found
        """
        return self._executor_registry.get(executor_id)
    
    def get_all_executors(self) -> List[ExecutorInfo]:
        """
        Get information about all registered executors.
        
        Returns:
            List of ExecutorInfo objects
        """
        return list(self._executor_registry.values())
    
    def get_available_executors(self, required_capabilities: List[str] = None) -> List[ExecutorInfo]:
        """
        Get available executors, optionally filtered by capabilities.
        
        Args:
            required_capabilities: Optional list of required capabilities
            
        Returns:
            List of available ExecutorInfo objects
        """
        available = [
            executor for executor in self._executor_registry.values()
            if executor.status == ExecutorStatus.AVAILABLE
        ]
        
        if required_capabilities:
            available = [
                executor for executor in available
                if all(cap in executor.capabilities for cap in required_capabilities)
            ]
        
        return available
    
    def update_executor_status(self, executor_id: str, status: ExecutorStatus, 
                              current_load: int = None) -> bool:
        """
        Update an executor's status and load.
        
        Args:
            executor_id: Executor ID
            status: New status
            current_load: Optional new load value
            
        Returns:
            True if update was successful
        """
        if executor_id in self._executor_registry:
            executor = self._executor_registry[executor_id]
            executor.status = status
            executor.last_active = datetime.now()
            
            if current_load is not None:
                executor.current_load = current_load
            
            return True
        return False
    
    def validate_assignments(self, assignments: List[ExecutorAssignment], 
                           tasks: List[TaskPlan]) -> List[str]:
        """
        Validate a set of task assignments.
        
        Args:
            assignments: List of assignments to validate
            tasks: List of task plans
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check that all assigned tasks exist
        task_ids = {task.task_id for task in tasks}
        for assignment in assignments:
            if assignment.task_id not in task_ids:
                errors.append(f"Assignment {assignment.assignment_id} references unknown task {assignment.task_id}")
        
        # Check that all assigned executors exist
        executor_ids = set(self._executor_registry.keys())
        for assignment in assignments:
            if assignment.executor_id not in executor_ids:
                errors.append(f"Assignment {assignment.assignment_id} references unknown executor {assignment.executor_id}")
        
        # Check for duplicate task assignments
        assigned_tasks = set()
        for assignment in assignments:
            if assignment.task_id in assigned_tasks:
                errors.append(f"Task {assignment.task_id} is assigned multiple times")
            assigned_tasks.add(assignment.task_id)
        
        # Check executor capacity constraints
        executor_loads = {}
        for assignment in assignments:
            executor_id = assignment.executor_id
            if executor_id not in executor_loads:
                executor_loads[executor_id] = 0
            executor_loads[executor_id] += 1
        
        for executor_id, load in executor_loads.items():
            if executor_id in self._executor_registry:
                executor = self._executor_registry[executor_id]
                if load > executor.max_capacity:
                    errors.append(f"Executor {executor_id} overloaded: {load}/{executor.max_capacity}")
        
        return errors
    
    def add_to_history(self, result: DispatchResult) -> None:
        """
        Add a dispatch result to history.
        
        Args:
            result: Dispatch result to store
        """
        self._dispatch_history.append(result)
        
        # Keep history limited
        if len(self._dispatch_history) > self._max_history:
            self._dispatch_history = self._dispatch_history[-self._max_history:]
    
    def get_dispatch_history(self, limit: int = 100) -> List[DispatchResult]:
        """
        Get recent dispatch history.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of recent dispatch results
        """
        return self._dispatch_history[-limit:]
    
    def get_dispatch_statistics(self) -> Dict[str, Any]:
        """
        Get dispatcher statistics.
        
        Returns:
            Dictionary containing statistics
        """
        total_dispatches = len(self._dispatch_history)
        
        if total_dispatches == 0:
            return {
                "total_dispatches": 0,
                "average_confidence": 0.0,
                "strategy_distribution": {},
                "success_rate": 0.0
            }
        
        # Calculate statistics
        total_confidence = sum(result.confidence for result in self._dispatch_history)
        avg_confidence = total_confidence / total_dispatches
        
        strategy_counts = {}
        successful_dispatches = 0
        
        for result in self._dispatch_history:
            strategy = result.dispatch_strategy.value
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            
            # Consider a dispatch successful if most tasks were assigned
            total_tasks = len(result.assignments) + len(result.unassigned_tasks)
            if total_tasks > 0 and len(result.assignments) / total_tasks >= 0.8:
                successful_dispatches += 1
        
        success_rate = successful_dispatches / total_dispatches
        
        return {
            "total_dispatches": total_dispatches,
            "average_confidence": avg_confidence,
            "strategy_distribution": strategy_counts,
            "success_rate": success_rate,
            "registered_executors": len(self._executor_registry),
            "available_executors": len(self.get_available_executors())
        }