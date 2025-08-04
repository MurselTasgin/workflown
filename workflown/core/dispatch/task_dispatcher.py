"""
Task Dispatcher Implementation

Implements intelligent task dispatching that assigns planned tasks to appropriate
executors based on capabilities, availability, and optimization strategies.
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from ..planning.base_planner import PlanningResult, TaskPlan
from ..execution.base_executor import BaseExecutor
from ..execution.executor_registry import ExecutorRegistry
from .base_dispatcher import (
    BaseDispatcher, DispatchResult, DispatchContext, ExecutorAssignment,
    ExecutorInfo, ExecutorStatus, DispatchStrategy
)


class TaskDispatcher(BaseDispatcher):
    """
    Intelligent task dispatcher that optimally assigns tasks to executors.
    
    Uses multiple strategies including capability matching, load balancing,
    and performance optimization to make assignment decisions.
    """
    
    def __init__(self, executor_registry: ExecutorRegistry, dispatcher_id: str = None, 
                 config: Dict[str, Any] = None):
        """
        Initialize the task dispatcher.
        
        Args:
            executor_registry: Registry of available executors
            dispatcher_id: Unique identifier for the dispatcher
            config: Configuration dictionary
        """
        super().__init__(dispatcher_id, config)
        self.executor_registry = executor_registry
        self._sync_executors_from_registry()
    
    def _sync_executors_from_registry(self) -> None:
        """Synchronize executor information from the registry."""
        for executor_id, executor in self.executor_registry.get_all_executors().items():
            executor_info = ExecutorInfo(
                executor_id=executor_id,
                executor_type=executor.__class__.__name__,
                capabilities=[cap.value for cap in executor.capabilities],
                current_load=len(executor.current_tasks),
                max_capacity=executor.max_concurrent_tasks,
                status=ExecutorStatus.AVAILABLE if executor.is_available() else ExecutorStatus.BUSY,
                performance_score=self._calculate_performance_score(executor),
                last_active=executor.last_activity,
                preferred_task_types=executor.get_supported_task_types(),
                metadata=executor.get_metadata()
            )
            self.register_executor(executor_info)
    
    def _calculate_performance_score(self, executor: BaseExecutor) -> float:
        """Calculate performance score for an executor."""
        total_tasks = executor.completed_tasks + executor.failed_tasks
        if total_tasks == 0:
            return 0.5  # Neutral score for new executors
        
        success_rate = executor.completed_tasks / total_tasks
        return success_rate
    
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
        try:
            # Step 1: Select dispatch strategy
            strategy = self.select_dispatch_strategy(planning_result, context)
            
            # Step 2: Pre-process tasks for dispatch
            processable_tasks = self._preprocess_tasks(planning_result.tasks)
            
            # Step 3: Get available executors
            available_executors = self.get_available_executors()
            
            if not available_executors:
                return self._create_no_executors_result(planning_result, context, strategy)
            
            # Step 4: Create assignments based on strategy
            assignments, unassigned = await self._create_assignments(
                processable_tasks, available_executors, strategy, context
            )
            
            # Step 5: Optimize assignments if configured
            if self.config.get("optimize_assignments", True):
                assignments = self._optimize_assignments(assignments, processable_tasks, available_executors)
            
            # Step 6: Calculate metrics
            total_time = self._calculate_total_time(assignments, processable_tasks)
            confidence = self._calculate_dispatch_confidence(assignments, unassigned, available_executors)
            
            # Step 7: Generate warnings
            warnings = self._generate_warnings(assignments, unassigned, context)
            
            # Create dispatch result
            result = DispatchResult(
                dispatch_id=f"dispatch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                plan_id=planning_result.plan_id,
                assignments=assignments,
                unassigned_tasks=[task.task_id for task in unassigned],
                dispatch_strategy=strategy,
                total_estimated_time=total_time,
                confidence=confidence,
                warnings=warnings,
                metadata={
                    "strategy_reason": self._get_strategy_reason(strategy, planning_result, context),
                    "executor_count": len(available_executors),
                    "task_count": len(processable_tasks),
                    "optimization_applied": self.config.get("optimize_assignments", True)
                }
            )
            
            # Validate and store
            validation_errors = self.validate_assignments(assignments, processable_tasks)
            if validation_errors:
                result.warnings.extend(validation_errors)
                result.confidence *= 0.8
            
            self.add_to_history(result)
            return result
            
        except Exception as e:
            return self._create_fallback_result(planning_result, context, str(e))
    
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
        # Find the original assignment
        original_assignment = None
        for result in self._dispatch_history:
            for assignment in result.assignments:
                if assignment.assignment_id == assignment_id:
                    original_assignment = assignment
                    break
            if original_assignment:
                break
        
        if not original_assignment:
            return None
        
        # Find alternative executors
        task_id = original_assignment.task_id
        current_executor_id = original_assignment.executor_id
        
        # Get task requirements
        required_capabilities = original_assignment.metadata.get("required_capabilities", [])
        available_executors = self.get_available_executors(required_capabilities)
        
        # Filter out current executor and find best alternative
        alternative_executors = [e for e in available_executors if e.executor_id != current_executor_id]
        
        if not alternative_executors:
            return None
        
        # Select best alternative based on suitability
        best_executor = max(alternative_executors, 
                           key=lambda e: self._calculate_reassignment_score(e, original_assignment, reason))
        
        # Create new assignment
        new_assignment = ExecutorAssignment(
            assignment_id=f"{assignment_id}_reassign_{datetime.now().strftime('%H%M%S')}",
            task_id=task_id,
            executor_id=best_executor.executor_id,
            assigned_at=datetime.now(),
            estimated_completion=datetime.now() + timedelta(seconds=300),  # Default estimate
            priority=original_assignment.priority,
            confidence=min(original_assignment.confidence * 0.9, 1.0),
            backup_executors=[e.executor_id for e in alternative_executors[:2] if e.executor_id != best_executor.executor_id],
            metadata={
                **original_assignment.metadata,
                "reassignment_reason": reason,
                "original_assignment": assignment_id,
                "reassigned_at": datetime.now().isoformat()
            }
        )
        
        # Update executor loads
        self.update_executor_status(current_executor_id, ExecutorStatus.AVAILABLE, 
                                   self._executor_registry[current_executor_id].current_load - 1)
        self.update_executor_status(best_executor.executor_id, ExecutorStatus.BUSY,
                                   best_executor.current_load + 1)
        
        return new_assignment
    
    def calculate_executor_suitability(self, task: TaskPlan, executor: ExecutorInfo) -> float:
        """
        Calculate how suitable an executor is for a specific task.
        
        Args:
            task: Task to be assigned
            executor: Executor to evaluate
            
        Returns:
            Suitability score (0.0 to 1.0)
        """
        if executor.status != ExecutorStatus.AVAILABLE:
            return 0.0
        
        score = 0.0
        
        # Capability matching (40% of score)
        capability_score = self._calculate_capability_match(task, executor)
        score += capability_score * 0.4
        
        # Load balancing (20% of score)
        load_score = max(0.0, 1.0 - (executor.current_load / executor.max_capacity))
        score += load_score * 0.2
        
        # Performance history (20% of score)
        score += executor.performance_score * 0.2
        
        # Task type preference (10% of score)
        preference_score = 1.0 if task.task_type in executor.preferred_task_types else 0.5
        score += preference_score * 0.1
        
        # Executor type matching (10% of score)
        type_score = self._calculate_executor_type_match(task, executor)
        score += type_score * 0.1
        
        return min(1.0, score)
    
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
        # Analyze characteristics
        task_count = len(planning_result.tasks)
        executor_count = len(self.get_available_executors())
        has_dependencies = any(task.dependencies for task in planning_result.tasks)
        has_priorities = any(task.priority > 1 for task in planning_result.tasks)
        has_deadlines = context.deadline is not None
        
        # Strategy selection logic
        if has_deadlines or has_priorities:
            return DispatchStrategy.PRIORITY_FIRST
        elif task_count > executor_count * 2:  # Heavy load
            return DispatchStrategy.LOAD_BALANCE
        elif has_dependencies:
            return DispatchStrategy.CAPABILITY_MATCH
        elif self.config.get("use_optimization", False):
            return DispatchStrategy.OPTIMAL_ASSIGNMENT
        else:
            return DispatchStrategy.ROUND_ROBIN
    
    def _preprocess_tasks(self, task_plans: List[TaskPlan]) -> List[TaskPlan]:
        """Preprocess tasks for dispatch (sorting, filtering, etc.)."""
        # Sort by priority and dependencies
        processed = sorted(task_plans, key=lambda t: (len(t.dependencies), -t.priority))
        return processed
    
    async def _create_assignments(self, tasks: List[TaskPlan], executors: List[ExecutorInfo],
                                 strategy: DispatchStrategy, context: DispatchContext) -> Tuple[List[ExecutorAssignment], List[TaskPlan]]:
        """Create task assignments based on strategy."""
        assignments = []
        unassigned = []
        executor_loads = {executor.executor_id: executor.current_load for executor in executors}
        
        for task in tasks:
            assignment = await self._assign_single_task(task, executors, executor_loads, strategy, context)
            
            if assignment:
                assignments.append(assignment)
                executor_loads[assignment.executor_id] += 1
            else:
                unassigned.append(task)
        
        return assignments, unassigned
    
    async def _assign_single_task(self, task: TaskPlan, executors: List[ExecutorInfo],
                                 executor_loads: Dict[str, int], strategy: DispatchStrategy,
                                 context: DispatchContext) -> Optional[ExecutorAssignment]:
        """Assign a single task to the best available executor."""
        suitable_executors = []
        
        for executor in executors:
            # Check if executor can handle the task
            if executor_loads[executor.executor_id] >= executor.max_capacity:
                continue
            
            # Check if executor supports the task type
            if task.task_type not in executor.preferred_task_types:
                continue
            
            # Calculate suitability
            suitability = self.calculate_executor_suitability(task, executor)
            if suitability > 0.1:  # Minimum threshold
                suitable_executors.append((executor, suitability))
        
        if not suitable_executors:
            return None
        
        # Select executor based on strategy
        selected_executor = self._select_executor_by_strategy(suitable_executors, strategy)
        
        # Create assignment
        assignment = ExecutorAssignment(
            assignment_id=f"assign_{task.task_id}_{datetime.now().strftime('%H%M%S')}",
            task_id=task.task_id,
            executor_id=selected_executor.executor_id,
            assigned_at=datetime.now(),
            estimated_completion=datetime.now() + timedelta(seconds=task.estimated_duration),
            priority=task.priority,
            confidence=suitable_executors[0][1],  # Use suitability as confidence
            backup_executors=[e[0].executor_id for e in suitable_executors[1:3]],  # Top 2 alternatives
            metadata={
                "task_type": task.task_type,
                "required_capabilities": task.required_capabilities,
                "required_tools": task.required_tools,
                "strategy_used": strategy.value,
                "suitability_score": suitable_executors[0][1]
            }
        )
        
        return assignment
    
    def _select_executor_by_strategy(self, suitable_executors: List[Tuple[ExecutorInfo, float]],
                                    strategy: DispatchStrategy) -> ExecutorInfo:
        """Select executor based on dispatch strategy."""
        if strategy == DispatchStrategy.CAPABILITY_MATCH:
            # Select executor with highest suitability
            return max(suitable_executors, key=lambda x: x[1])[0]
        
        elif strategy == DispatchStrategy.LOAD_BALANCE:
            # Select executor with lowest load
            return min(suitable_executors, key=lambda x: x[0].current_load)[0]
        
        elif strategy == DispatchStrategy.PRIORITY_FIRST:
            # Select highest performing executor
            return max(suitable_executors, key=lambda x: x[0].performance_score)[0]
        
        elif strategy == DispatchStrategy.ROUND_ROBIN:
            # Select first suitable executor (tasks already sorted)
            return suitable_executors[0][0]
        
        else:  # OPTIMAL_ASSIGNMENT
            # Weighted combination of factors
            def score(executor_suitability_tuple):
                executor, suitability = executor_suitability_tuple
                load_factor = 1.0 - (executor.current_load / executor.max_capacity)
                return suitability * 0.6 + executor.performance_score * 0.2 + load_factor * 0.2
            
            return max(suitable_executors, key=score)[0]
    
    def _optimize_assignments(self, assignments: List[ExecutorAssignment], 
                            tasks: List[TaskPlan], executors: List[ExecutorInfo]) -> List[ExecutorAssignment]:
        """Optimize assignments using local search or swapping."""
        if len(assignments) < 2:
            return assignments
        
        # Simple optimization - could be enhanced
        return assignments
    
    def _calculate_total_time(self, assignments: List[ExecutorAssignment], 
                            tasks: List[TaskPlan]) -> float:
        """Calculate total estimated execution time."""
        if not assignments:
            return 0.0
        
        task_map = {task.task_id: task for task in tasks}
        executor_times = {}
        
        for assignment in assignments:
            executor_id = assignment.executor_id
            task = task_map.get(assignment.task_id)
            
            if task:
                if executor_id not in executor_times:
                    executor_times[executor_id] = 0.0
                executor_times[executor_id] += task.estimated_duration
        
        # Return max time (bottleneck executor)
        return max(executor_times.values()) if executor_times else 0.0
    
    def _calculate_dispatch_confidence(self, assignments: List[ExecutorAssignment],
                                     unassigned: List[TaskPlan], executors: List[ExecutorInfo]) -> float:
        """Calculate confidence in the dispatch result."""
        if not assignments and unassigned:
            return 0.0
        
        base_confidence = 0.8
        
        # Penalty for unassigned tasks
        if unassigned:
            total_tasks = len(assignments) + len(unassigned)
            unassigned_penalty = (len(unassigned) / total_tasks) * 0.5
            base_confidence -= unassigned_penalty
        
        # Bonus for high-confidence assignments
        if assignments:
            avg_assignment_confidence = sum(a.confidence for a in assignments) / len(assignments)
            base_confidence += (avg_assignment_confidence - 0.5) * 0.2
        
        return max(0.1, min(1.0, base_confidence))
    
    def _generate_warnings(self, assignments: List[ExecutorAssignment], 
                          unassigned: List[TaskPlan], context: DispatchContext) -> List[str]:
        """Generate warnings about potential issues."""
        warnings = []
        
        if unassigned:
            warnings.append(f"{len(unassigned)} tasks could not be assigned to executors")
        
        return warnings
    
    def _get_strategy_reason(self, strategy: DispatchStrategy, planning_result: PlanningResult,
                           context: DispatchContext) -> str:
        """Get explanation for strategy selection."""
        reasons = {
            DispatchStrategy.PRIORITY_FIRST: "High priority tasks or deadline constraints detected",
            DispatchStrategy.LOAD_BALANCE: "Heavy task load requires load balancing",
            DispatchStrategy.CAPABILITY_MATCH: "Complex tasks require specific capabilities",
            DispatchStrategy.ROUND_ROBIN: "Simple round-robin for balanced distribution",
            DispatchStrategy.OPTIMAL_ASSIGNMENT: "Optimization enabled for best overall performance"
        }
        return reasons.get(strategy, "Default strategy selection")
    
    def _calculate_capability_match(self, task: TaskPlan, executor: ExecutorInfo) -> float:
        """Calculate how well executor capabilities match task requirements."""
        if not task.required_capabilities:
            return 1.0
        
        matched = sum(1 for cap in task.required_capabilities if cap in executor.capabilities)
        return matched / len(task.required_capabilities)
    
    def _calculate_executor_type_match(self, task: TaskPlan, executor: ExecutorInfo) -> float:
        """Calculate executor type suitability for task."""
        # Generic matching - can be enhanced for specific executor types
        return 1.0 if task.task_type in executor.preferred_task_types else 0.5
    
    def _calculate_reassignment_score(self, executor: ExecutorInfo, original_assignment: ExecutorAssignment,
                                    reason: str) -> float:
        """Calculate score for reassignment candidate."""
        base_score = executor.performance_score * 0.5
        load_score = (1.0 - executor.current_load / executor.max_capacity) * 0.3
        
        # Bonus for executors that weren't considered originally
        backup_bonus = 0.0 if executor.executor_id in original_assignment.backup_executors else 0.2
        
        return base_score + load_score + backup_bonus
    
    def _create_no_executors_result(self, planning_result: PlanningResult, 
                                   context: DispatchContext, strategy: DispatchStrategy) -> DispatchResult:
        """Create result when no executors are available."""
        return DispatchResult(
            dispatch_id=f"no_executors_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            plan_id=planning_result.plan_id,
            assignments=[],
            unassigned_tasks=[task.task_id for task in planning_result.tasks],
            dispatch_strategy=strategy,
            total_estimated_time=0.0,
            confidence=0.0,
            warnings=["No executors available for task assignment"],
            metadata={"error": "no_available_executors"}
        )
    
    def _create_fallback_result(self, planning_result: PlanningResult, 
                              context: DispatchContext, error: str) -> DispatchResult:
        """Create fallback result when dispatch fails."""
        return DispatchResult(
            dispatch_id=f"fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            plan_id=planning_result.plan_id,
            assignments=[],
            unassigned_tasks=[task.task_id for task in planning_result.tasks],
            dispatch_strategy=DispatchStrategy.ROUND_ROBIN,
            total_estimated_time=0.0,
            confidence=0.1,
            warnings=[f"Dispatch failed: {error}"],
            metadata={"fallback": True, "error": error}
        )