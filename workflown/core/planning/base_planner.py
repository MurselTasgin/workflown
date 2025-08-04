"""
Base Planner Interface

Defines the interface for workflow and task planners.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from ..workflows.task import Task, TaskPriority, DependencyType


class PlanningStrategy(Enum):
    """Planning strategies."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    OPTIMIZED = "optimized"
    CUSTOM = "custom"


@dataclass
class TaskPlan:
    """Plan for a single task."""
    task_id: str
    task_type: str
    name: str
    description: str
    parameters: Dict[str, Any]
    priority: int = TaskPriority.NORMAL.value
    estimated_duration: float = 300.0  # seconds
    required_capabilities: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanningResult:
    """Result of planning operation."""
    plan_id: str
    workflow_id: str
    tasks: List[TaskPlan]
    strategy: PlanningStrategy
    estimated_total_time: float
    confidence: float
    metadata: Dict[str, Any]
    created_at: datetime
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.plan_id:
            self.plan_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()


class BasePlanner(ABC):
    """
    Abstract base class for workflow and task planners.
    
    Planners are responsible for breaking down high-level workflow
    requirements into specific, executable tasks.
    """
    
    def __init__(self, planner_id: str = None, config: Dict[str, Any] = None):
        """
        Initialize the planner.
        
        Args:
            planner_id: Unique identifier for the planner
            config: Planner configuration
        """
        self.planner_id = planner_id or str(uuid.uuid4())
        self.config = config or {}
        self.created_at = datetime.now()
        self._planning_history: List[PlanningResult] = []
    
    @abstractmethod
    async def create_plan(
        self, 
        workflow_id: str,
        requirements: Dict[str, Any],
        constraints: Dict[str, Any] = None
    ) -> PlanningResult:
        """
        Create a plan for a workflow.
        
        Args:
            workflow_id: Unique workflow identifier
            requirements: Workflow requirements and objectives
            constraints: Optional planning constraints
            
        Returns:
            PlanningResult containing the generated plan
        """
        pass
    
    @abstractmethod
    def validate_plan(self, plan: PlanningResult) -> List[str]:
        """
        Validate a planning result.
        
        Args:
            plan: Planning result to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        pass
    
    def get_planning_history(self, limit: int = 100) -> List[PlanningResult]:
        """
        Get recent planning history.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of recent planning results
        """
        return self._planning_history[-limit:]
    
    def add_to_history(self, result: PlanningResult) -> None:
        """
        Add a planning result to history.
        
        Args:
            result: Planning result to store
        """
        self._planning_history.append(result)
        
        # Keep history limited
        max_history = self.config.get("max_history", 1000)
        if len(self._planning_history) > max_history:
            self._planning_history = self._planning_history[-max_history:]
    
    def select_strategy(self, requirements: Dict[str, Any]) -> PlanningStrategy:
        """
        Select the best planning strategy for requirements.
        
        Args:
            requirements: Workflow requirements
            
        Returns:
            Selected planning strategy
        """
        # Default implementation - subclasses should override
        if requirements.get("parallel", False):
            return PlanningStrategy.PARALLEL
        elif requirements.get("optimize", False):  
            return PlanningStrategy.OPTIMIZED
        else:
            return PlanningStrategy.SEQUENTIAL
    
    def estimate_task_duration(self, task_plan: TaskPlan) -> float:
        """
        Estimate duration for a task.
        
        Args:
            task_plan: Task plan to estimate
            
        Returns:
            Estimated duration in seconds
        """
        # Default estimation based on task type
        base_durations = {
            "python": 30.0,
            "shell": 60.0,
            "http": 10.0,
            "function": 15.0,
            "generic": 30.0
        }
        
        base_time = base_durations.get(task_plan.task_type, 60.0)
        
        # Adjust based on complexity indicators
        complexity_multiplier = 1.0
        
        if len(task_plan.parameters) > 5:
            complexity_multiplier *= 1.2
        
        if len(task_plan.dependencies) > 2:
            complexity_multiplier *= 1.1
        
        return base_time * complexity_multiplier
    
    def resolve_dependencies(self, tasks: List[TaskPlan]) -> List[TaskPlan]:
        """
        Resolve and validate task dependencies.
        
        Args:
            tasks: List of task plans
            
        Returns:
            List of tasks with resolved dependencies
        """
        task_ids = {task.task_id for task in tasks}
        
        # Validate dependencies exist
        for task in tasks:
            invalid_deps = [dep for dep in task.dependencies if dep not in task_ids]
            if invalid_deps:
                task.dependencies = [dep for dep in task.dependencies if dep in task_ids]
        
        return tasks
    
    def detect_circular_dependencies(self, tasks: List[TaskPlan]) -> List[str]:
        """
        Detect circular dependencies in task plans.
        
        Args:
            tasks: List of task plans
            
        Returns:
            List of task IDs involved in circular dependencies
        """
        # Build adjacency list
        graph = {}
        for task in tasks:
            graph[task.task_id] = task.dependencies
        
        # Use DFS to detect cycles
        visited = set()
        rec_stack = set()
        circular_tasks = []
        
        def has_cycle(node):
            if node in rec_stack:
                return True
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if has_cycle(neighbor):
                    circular_tasks.append(node)
                    return True
            
            rec_stack.remove(node)
            return False
        
        for task_id in graph:
            if task_id not in visited:
                has_cycle(task_id)
        
        return circular_tasks
    
    def calculate_critical_path(self, tasks: List[TaskPlan]) -> List[str]:
        """
        Calculate the critical path through task dependencies.
        
        Args:
            tasks: List of task plans
            
        Returns:
            List of task IDs in critical path order
        """
        # Build task lookup
        task_map = {task.task_id: task for task in tasks}
        
        # Calculate earliest start times
        earliest_start = {}
        
        def calculate_earliest_start(task_id):
            if task_id in earliest_start:
                return earliest_start[task_id]
            
            task = task_map[task_id]
            max_dep_end = 0.0
            
            for dep_id in task.dependencies:
                if dep_id in task_map:
                    dep_start = calculate_earliest_start(dep_id)
                    dep_duration = task_map[dep_id].estimated_duration
                    max_dep_end = max(max_dep_end, dep_start + dep_duration)
            
            earliest_start[task_id] = max_dep_end
            return max_dep_end
        
        # Calculate for all tasks
        for task in tasks:
            calculate_earliest_start(task.task_id)
        
        # Find critical path (longest path)
        # This is a simplified implementation
        sorted_tasks = sorted(tasks, key=lambda t: earliest_start[t.task_id])
        return [task.task_id for task in sorted_tasks]