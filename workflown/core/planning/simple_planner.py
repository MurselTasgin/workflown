"""
Simple Planner Implementation

Basic planner that creates simple task plans from requirements.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from .base_planner import BasePlanner, PlanningResult, TaskPlan, PlanningStrategy
from ..workflows.task import TaskPriority


class SimplePlanner(BasePlanner):
    """
    Simple planner that creates basic task plans.
    
    Suitable for straightforward workflows without complex optimization needs.
    """
    
    def __init__(self, planner_id: str = None, config: Dict[str, Any] = None):
        """
        Initialize the simple planner.
        
        Args:
            planner_id: Unique identifier
            config: Planner configuration
        """
        super().__init__(planner_id, config)
        self.name = "SimplePlanner"
        self.version = "1.0.0"
    
    async def create_plan(
        self, 
        workflow_id: str,
        requirements: Dict[str, Any],
        constraints: Dict[str, Any] = None
    ) -> PlanningResult:
        """
        Create a simple plan from requirements.
        
        Args:
            workflow_id: Unique workflow identifier
            requirements: Workflow requirements
            constraints: Optional constraints
            
        Returns:
            PlanningResult containing the plan
        """
        constraints = constraints or {}
        
        # Extract tasks from requirements
        tasks = self._extract_tasks_from_requirements(requirements)
        
        # Select strategy
        strategy = self.select_strategy(requirements)
        
        # Process tasks based on strategy
        if strategy == PlanningStrategy.PARALLEL:
            tasks = self._plan_parallel_execution(tasks)
        elif strategy == PlanningStrategy.SEQUENTIAL:
            tasks = self._plan_sequential_execution(tasks)
        else:
            tasks = self._plan_optimized_execution(tasks)
        
        # Estimate durations
        for task in tasks:
            task.estimated_duration = self.estimate_task_duration(task)
        
        # Resolve dependencies
        tasks = self.resolve_dependencies(tasks)
        
        # Calculate total time
        total_time = self._calculate_total_time(tasks, strategy)
        
        # Calculate confidence
        confidence = self._calculate_confidence(tasks, requirements)
        
        # Check for issues
        warnings = self._generate_warnings(tasks, constraints)
        
        # Create result
        result = PlanningResult(
            plan_id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            tasks=tasks,
            strategy=strategy,
            estimated_total_time=total_time,
            confidence=confidence,
            metadata={
                "planner": self.name,
                "version": self.version,
                "requirements": requirements,
                "constraints": constraints
            },
            created_at=datetime.now(),
            warnings=warnings
        )
        
        # Validate plan
        validation_errors = self.validate_plan(result)
        if validation_errors:
            result.warnings.extend(validation_errors)
            result.confidence *= 0.7
        
        # Store in history
        self.add_to_history(result)
        
        return result
    
    def validate_plan(self, plan: PlanningResult) -> List[str]:
        """
        Validate a planning result.
        
        Args:
            plan: Planning result to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not plan.tasks:
            errors.append("Plan contains no tasks")
            return errors
        
        # Check for circular dependencies
        circular_tasks = self.detect_circular_dependencies(plan.tasks)
        if circular_tasks:
            errors.append(f"Circular dependencies detected in tasks: {circular_tasks}")
        
        # Check task completeness
        for task in plan.tasks:
            if not task.task_type:
                errors.append(f"Task {task.task_id} has no task_type")
            
            if not task.name:
                errors.append(f"Task {task.task_id} has no name")
        
        # Check dependency references
        task_ids = {task.task_id for task in plan.tasks}
        for task in plan.tasks:
            invalid_deps = [dep for dep in task.dependencies if dep not in task_ids]
            if invalid_deps:
                errors.append(f"Task {task.task_id} has invalid dependencies: {invalid_deps}")
        
        return errors
    
    def _extract_tasks_from_requirements(self, requirements: Dict[str, Any]) -> List[TaskPlan]:
        """Extract task plans from requirements."""
        tasks = []
        
        # Handle different requirement formats
        if "tasks" in requirements:
            # Direct task specification
            for i, task_req in enumerate(requirements["tasks"]):
                task = self._create_task_from_spec(task_req, i)
                tasks.append(task)
        
        elif "goals" in requirements:
            # Goal-based planning
            for i, goal in enumerate(requirements["goals"]):
                task = self._create_task_from_goal(goal, i)
                tasks.append(task)
        
        elif "commands" in requirements:
            # Command-based planning
            for i, command in enumerate(requirements["commands"]):
                task = self._create_task_from_command(command, i)
                tasks.append(task)
        
        else:
            # Generic single task
            task = TaskPlan(
                task_id=str(uuid.uuid4()),
                task_type="generic",
                name=requirements.get("name", "Generic Task"),
                description=requirements.get("description", "Generated generic task"),
                parameters=requirements.get("parameters", {}),
                priority=requirements.get("priority", TaskPriority.NORMAL.value)
            )
            tasks.append(task)
        
        return tasks
    
    def _create_task_from_spec(self, spec: Dict[str, Any], index: int) -> TaskPlan:
        """Create a task plan from a specification."""
        return TaskPlan(
            task_id=spec.get("task_id", str(uuid.uuid4())),
            task_type=spec.get("task_type", "generic"),
            name=spec.get("name", f"Task {index + 1}"),
            description=spec.get("description", ""),
            parameters=spec.get("parameters", {}),
            priority=spec.get("priority", TaskPriority.NORMAL.value),
            estimated_duration=spec.get("estimated_duration", 300.0),
            required_capabilities=spec.get("required_capabilities", []),
            required_tools=spec.get("required_tools", []),
            dependencies=spec.get("dependencies", []),
            tags=spec.get("tags", []),
            metadata=spec.get("metadata", {})
        )
    
    def _create_task_from_goal(self, goal: str, index: int) -> TaskPlan:
        """Create a task plan from a goal description."""
        return TaskPlan(
            task_id=str(uuid.uuid4()),
            task_type="generic",
            name=f"Goal {index + 1}",
            description=goal,
            parameters={"goal": goal}
        )
    
    def _create_task_from_command(self, command: Dict[str, Any], index: int) -> TaskPlan:
        """Create a task plan from a command specification."""
        if isinstance(command, str):
            # Simple shell command
            return TaskPlan(
                task_id=str(uuid.uuid4()),
                task_type="shell",
                name=f"Command {index + 1}",
                description=f"Execute: {command}",
                parameters={"command": command}
            )
        else:
            # Structured command
            return TaskPlan(
                task_id=str(uuid.uuid4()),
                task_type=command.get("type", "shell"),
                name=command.get("name", f"Command {index + 1}"),
                description=command.get("description", ""),
                parameters=command.get("parameters", {})
            )
    
    def _plan_sequential_execution(self, tasks: List[TaskPlan]) -> List[TaskPlan]:
        """Plan tasks for sequential execution."""
        for i in range(1, len(tasks)):
            # Each task depends on the previous one
            tasks[i].dependencies = [tasks[i-1].task_id]
        
        return tasks
    
    def _plan_parallel_execution(self, tasks: List[TaskPlan]) -> List[TaskPlan]:
        """Plan tasks for parallel execution."""
        # No dependencies between tasks (they can all run in parallel)
        for task in tasks:
            task.dependencies = []
        
        return tasks
    
    def _plan_optimized_execution(self, tasks: List[TaskPlan]) -> List[TaskPlan]:
        """Plan tasks with basic optimization."""
        # Group tasks by type and create some dependencies
        task_groups = {}
        for task in tasks:
            if task.task_type not in task_groups:
                task_groups[task.task_type] = []
            task_groups[task.task_type].append(task)
        
        # Make tasks of the same type sequential
        for task_type, group_tasks in task_groups.items():
            for i in range(1, len(group_tasks)):
                group_tasks[i].dependencies = [group_tasks[i-1].task_id]
        
        return tasks
    
    def _calculate_total_time(self, tasks: List[TaskPlan], strategy: PlanningStrategy) -> float:
        """Calculate estimated total execution time."""
        if not tasks:
            return 0.0
        
        if strategy == PlanningStrategy.PARALLEL:
            # All tasks run in parallel - total time is the longest task
            return max(task.estimated_duration for task in tasks)
        
        elif strategy == PlanningStrategy.SEQUENTIAL:
            # All tasks run sequentially - total time is sum of all tasks
            return sum(task.estimated_duration for task in tasks)
        
        else:
            # Optimized - calculate based on critical path
            critical_path = self.calculate_critical_path(tasks)
            task_map = {task.task_id: task for task in tasks}
            
            return sum(
                task_map[task_id].estimated_duration 
                for task_id in critical_path 
                if task_id in task_map
            )
    
    def _calculate_confidence(self, tasks: List[TaskPlan], requirements: Dict[str, Any]) -> float:
        """Calculate confidence in the plan."""
        base_confidence = 0.8
        
        # Reduce confidence for complex plans
        if len(tasks) > 10:
            base_confidence -= 0.1
        
        # Reduce confidence for tasks with many dependencies
        complex_tasks = [t for t in tasks if len(t.dependencies) > 3]
        if complex_tasks:
            base_confidence -= len(complex_tasks) * 0.05
        
        # Increase confidence for simple plans
        if all(t.task_type == "generic" for t in tasks):
            base_confidence += 0.1
        
        return max(0.1, min(1.0, base_confidence))
    
    def _generate_warnings(self, tasks: List[TaskPlan], constraints: Dict[str, Any]) -> List[str]:
        """Generate warnings about potential plan issues."""
        warnings = []
        
        # Check for very long tasks
        long_tasks = [t for t in tasks if t.estimated_duration > 3600]  # > 1 hour
        if long_tasks:
            warnings.append(f"{len(long_tasks)} tasks have very long estimated durations")
        
        # Check for deep dependency chains
        max_chain_length = max(len(t.dependencies) for t in tasks) if tasks else 0
        if max_chain_length > 5:
            warnings.append(f"Maximum dependency chain length is {max_chain_length}")
        
        # Check constraint violations
        if constraints:
            max_time = constraints.get("max_time")
            if max_time:
                total_time = sum(t.estimated_duration for t in tasks)
                if total_time > max_time:
                    warnings.append(f"Total estimated time ({total_time}s) exceeds constraint ({max_time}s)")
        
        return warnings