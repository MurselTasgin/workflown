#!/usr/bin/env python3
"""
Workflown Framework Web Research Workflow Example

Demonstrates proper use of the Workflown framework capabilities:
- BaseWorkflow for orchestration
- Task system with dependencies
- Component factory for tool creation
- Configuration management
- Event system for progress tracking
- Generic tool registry and mapping
- Tool definitions with automatic metadata extraction
- Web search, webpage scraping, and content composition workflow

This workflow performs:
1. Web Search: Searches for URLs based on the query
2. Web Scraping: Scrapes content from URLs found in step 1
3. Content Composition: Composes and summarizes the scraped content

Usage:
    python examples/test_workflown_workflow.py [query]

Example:
    python examples/test_workflown_workflow.py "Agentic AI frameworks in 2025"
"""

import asyncio
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict, deque

# Add workflown to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflown.core.workflows.base_workflow import BaseWorkflow, WorkflowResult, WorkflowState
from workflown.core.workflows.task import Task, TaskPriority, TaskState, TaskDependency, DependencyType
from workflown.core.config.component_factory import ComponentFactory, ComponentRegistry, ComponentSpec, ComponentType
from workflown.core.events.event_bus import EventBus, Event, EventPriority
from workflown.core.config.central_config import get_config

# Import tool registry and mapper from workflown
from workflown.core.tools.tool_registry import ToolRegistry
from workflown.core.tools.tool_mapper import ToolMapper, TaskMapping, MappingStrategy
from workflown.core.tools.base_tool import BaseTool, ToolResult, ToolCapability

# Import toolbox tools
from toolbox.web_search_tool import WebSearchTool
from toolbox.webpage_parser import WebPageParserTool
from toolbox.composer_tool import ComposerTool


class WorkflowExecutionEngine:
    """
    Generic workflow execution engine that handles:
    - Task dependency resolution
    - Automatic task execution based on dependencies
    - Result passing between tasks
    - Event-driven progress tracking
    - Intelligent tool mapping using enhanced registry
    - Real-time result display
    """
    
    def __init__(self, event_bus: EventBus, component_factory: ComponentFactory, tool_registry: ToolRegistry):
        self.event_bus = event_bus
        self.component_factory = component_factory
        self.tool_registry = tool_registry
        self.execution_context: Dict[str, Any] = {}
        self.task_results: Dict[str, Any] = {}
        self.completed_tasks: Set[str] = set()
        self.running_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        
        # Task-to-tool mappings
        self.task_mappings: Dict[str, TaskMapping] = {}
        
        # Real-time display callback
        self.result_display_callback = None
        
        # Progress tracking
        self.total_tasks = 0
        self.current_step = 0
        
        # Configuration for result passing between tasks
        self.result_passing_config = {}
    
    def set_result_display_callback(self, callback):
        """Set callback function for real-time result display."""
        self.result_display_callback = callback
    
    def _display_task_result(self, task_id: str, task_type: str, result: Any):
        """Display task result via external callback if set (no default printing)."""
        if self.result_display_callback:
            self.result_display_callback(task_id, task_type, result)
    
    def _extract_urls_from_search_results(self, search_results: List[Dict[str, Any]]) -> List[str]:
        """Extract URLs from web search results."""
        urls = []
        
        for result in search_results:
            # Handle different result formats
            if isinstance(result, dict):
                # Check for URL in various possible fields
                url = result.get('url') or result.get('link') or result.get('href')
                if url:
                    urls.append(url)
            elif hasattr(result, 'url'):
                urls.append(result.url)
        
        # If no URLs found, provide a fallback
        if not urls:
            urls = ["https://example.com"]
        
        return urls
    
    # Removed: Composition input preparation should be handled inside ComposerTool
        
    async def execute_workflow(self, tasks: Dict[str, Task]) -> Dict[str, Any]:
        """
        Execute a workflow with automatic dependency resolution and result passing.
        
        Args:
            tasks: Dictionary of tasks to execute
            
        Returns:
            Dictionary containing all task results
        """
        self.total_tasks = len(tasks)
        self.current_step = 0
        
        print(f"🚀 Starting workflow execution with {self.total_tasks} tasks")
        print(f"📊 Progress: 0/{self.total_tasks} tasks completed")
        
        # Initialize task states
        for task in tasks.values():
            task.state = TaskState.PENDING
        
        # Execute tasks until all are completed or failed
        while len(self.completed_tasks) + len(self.failed_tasks) < len(tasks):
            # Find ready tasks (dependencies satisfied)
            ready_tasks = self._find_ready_tasks(tasks)
            
            if not ready_tasks and len(self.running_tasks) == 0:
                # Deadlock or no more tasks can run
                remaining = set(tasks.keys()) - self.completed_tasks - self.failed_tasks
                raise Exception(f"Workflow deadlock: tasks {remaining} cannot start")
            
            # Execute ready tasks
            for task_id in ready_tasks:
                await self._execute_task(tasks[task_id])
            
            # Wait a bit for tasks to complete
            if self.running_tasks:
                await asyncio.sleep(0.1)
        
        print(f"✅ Workflow execution completed: {len(self.completed_tasks)} successful, {len(self.failed_tasks)} failed")
        return self.task_results
    
    def _find_ready_tasks(self, tasks: Dict[str, Task]) -> List[str]:
        """Find tasks that are ready to execute (dependencies satisfied)."""
        ready_tasks = []
        
        for task_id, task in tasks.items():
            if (task.state == TaskState.PENDING and 
                task_id not in self.running_tasks and
                task_id not in self.completed_tasks and
                task_id not in self.failed_tasks):
                
                # Check if all dependencies are satisfied
                if self._are_dependencies_satisfied(task):
                    ready_tasks.append(task_id)
        
        return ready_tasks
    
    def _are_dependencies_satisfied(self, task: Task) -> bool:
        """Check if all dependencies for a task are satisfied."""
        for dependency in task.dependencies:
            if dependency.required and dependency.dependency_id not in self.completed_tasks:
                return False
        return True
    
    async def _execute_task(self, task: Task):
        """Execute a single task and handle result passing."""
        task_id = task.task_id
        
        # Mark task as running
        task.start()
        self.running_tasks.add(task_id)
        
        await self.event_bus.publish(Event(
            event_type="task.started",
            source="workflow_engine",
            data={"task_id": task_id, "task_type": task.task_type},
            timestamp=datetime.now()
        ))
        
        try:
            # Update progress
            self.current_step += 1
            
            # Prepare task parameters with results from previous tasks
            parameters = self._prepare_task_parameters(task)
            
            # Execute task based on type
            result = await self._execute_task_by_type(task, parameters)
            
            # Store result and mark as completed
            self.task_results[task_id] = result
            self.completed_tasks.add(task_id)
            self.running_tasks.remove(task_id)
            
            task.complete(result, {"execution_engine": "generic"})
            
            # Display result immediately
            self._display_task_result(task_id, task.task_type, result)
            
            # Show progress update
            print(f"📊 Progress: {self.current_step}/{self.total_tasks} tasks completed")
            
            # Show next steps if available
            if self.current_step < self.total_tasks:
                remaining_tasks = self.total_tasks - self.current_step
                print(f"⏭️  Next: {remaining_tasks} task(s) remaining")
            
            await self.event_bus.publish(Event(
                event_type="task.completed",
                source="workflow_engine",
                data={
                    "task_id": task_id,
                    "result_size": len(str(result))
                },
                timestamp=datetime.now()
            ))
            
        except Exception as e:
            # Mark task as failed
            self.failed_tasks.add(task_id)
            self.running_tasks.remove(task_id)
            
            task.fail(str(e), retry=False)
            
            await self.event_bus.publish(Event(
                event_type="task.failed",
                source="workflow_engine",
                data={
                    "task_id": task_id,
                    "error": str(e)
                },
                timestamp=datetime.now()
            ))
            
            print(f"❌ Task failed: {task_id} - {e}")
            raise
    
    def _prepare_task_parameters(self, task: Task) -> Dict[str, Any]:
        """Prepare task parameters by injecting results from previous tasks using configuration."""
        parameters = task.parameters.copy()
        
        # Get configuration for this task type
        config = self.result_passing_config.get(task.task_type)
        if not config:
            return parameters
        
        # Get results from the specified source task
        source_task_id = config["input_from"]
        source_results = self.task_results.get(source_task_id)
        
        if source_results is not None:  # Changed from 'if source_results:' to handle empty lists
            # Apply transformation if specified
            transform_func = config.get("transform")
            if transform_func:
                transformed_data = transform_func(source_results)
            else:
                # Default: extract from result path
                result_path = config.get("result_path", "result")
                transformed_data = source_results.get(result_path, source_results)
            
            # Inject into the specified parameter field
            input_field = config["input_field"]
            parameters[input_field] = transformed_data
            
            print(f"🔗 Injected {len(transformed_data) if isinstance(transformed_data, list) else 1} items from {source_task_id} to {task.task_id}")
        
        return parameters
    
    async def _execute_task_by_type(self, task: Task, parameters: Dict[str, Any]) -> Any:
        """Execute task based on its type using the tool registry."""
        
        # Get or create task mapping
        if task.task_id not in self.task_mappings:
            # Create tool mapper
            tool_mapper = ToolMapper(self.tool_registry)
            
            print(f"🔧 Using registry instance: {id(self.tool_registry)}")
            print(f"🔧 Registry has {len(self.tool_registry._tool_classes)} tool classes")
            print(f"🔧 Registry task types: {list(self.tool_registry._task_type_index.keys())}")
            
            mapping = tool_mapper.map_task_to_tool(
                task_id=task.task_id,
                task_type=task.task_type,
                task_description=task.description,
                task_parameters=parameters
            )
            
            if not mapping:
                raise Exception(f"No suitable tool found for task {task.task_id} (type: {task.task_type})")
            
            self.task_mappings[task.task_id] = mapping
            print(f"🔗 Mapped task {task.task_id} to tool {mapping.selected_tool_id}")
        
        mapping = self.task_mappings[task.task_id]
        
        # Create tool instance using tool registry
        tool_instance = self.tool_registry.create_tool_instance(
            tool_id=mapping.selected_tool_id,
            instance_id=f"{task.task_id}_instance",
            config=parameters
        )
        
        if not tool_instance:
            raise Exception(f"Failed to create tool instance for task {task.task_id}")
        
        try:
            # Execute the tool with tracking (enables input/output persistence)
            result = await tool_instance.execute_with_tracking(
                parameters,
                context={"task_id": task.task_id, "task_type": task.task_type}
            )

            # Display result using tool-specific renderer
            try:
                tool_instance.display_result(
                    task_id=task.task_id,
                    result=result.result,
                    context={"task_type": task.task_type}
                )
            except Exception as _e:
                # Non-fatal: continue even if display fails
                pass

            if not result.success:
                raise Exception(f"Tool execution failed: {result.errors}")

            return result.result

        finally:
            # Cleanup tool instance
            await tool_instance.cleanup()
    
    def add_result_passing_config(self, task_type: str, config: Dict[str, Any]):
        """Add or update result passing configuration for a task type."""
        self.result_passing_config[task_type] = config
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return {
            "total_tasks": len(self.task_results) + len(self.failed_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "running_tasks": len(self.running_tasks),
            "success_rate": len(self.completed_tasks) / (len(self.completed_tasks) + len(self.failed_tasks)) if (len(self.completed_tasks) + len(self.failed_tasks)) > 0 else 0,
            "tool_mappings": len(self.task_mappings)
        }


class GenericWorkflowExample(BaseWorkflow):
    """
    Web research workflow example using Workflown framework.
    
    This workflow demonstrates proper use of:
    - Task orchestration with dependencies
    - Component factory for tool management
    - Event-driven progress tracking
    - Configuration management
    - Error handling and recovery
    - Generic tool registry and mapping
    - Web search, webpage scraping, and content composition
    
    Workflow Steps:
    1. Web Search: Searches for URLs based on the query
    2. Web Scraping: Scrapes content from URLs found in step 1
    3. Content Composition: Composes and summarizes the scraped content
    """
    
    def __init__(self, workflow_id: str = None, config: Dict[str, Any] = None):
        super().__init__(workflow_id, config)
        
        # Initialize framework components
        self.event_bus = EventBus()
        self.component_registry = ComponentRegistry()
        self.component_factory = ComponentFactory(self.component_registry)
        
        # Workflow configuration
        self.query = self.config.get("query", "Example workflow query")
        self.max_tasks = self.config.get("max_tasks", 3)
        self.task_types = self.config.get("task_types", ["web_search", "webpage_parse", "compose"])
        
        # Task tracking
        self.tasks = {}
        self.results = {}
        
        # Setup event listeners
        self._setup_event_listeners()
        
        # Initialize and populate tool registry
        self.tool_registry = ToolRegistry()
        
        # Tools will be registered externally (e.g., in main) to allow per-run configuration like persistence
        # self._register_tools(tool_list=[WebSearchTool, WebPageParserTool, ComposerTool])
        
        print(f"🔧 Workflow using registry instance: {id(self.tool_registry)}")
        
        # Create execution engine with the populated registry
        self.execution_engine = WorkflowExecutionEngine(self.event_bus, self.component_factory, self.tool_registry)
    
    def _setup_event_listeners(self):
        """Setup event listeners for workflow monitoring."""
        
        def on_task_started(event: Event):
            task_id = event.data.get("task_id")
            task_type = event.data.get("task_type", "unknown")
            print(f"\n🚀 Starting task: {task_id} ({task_type})")
            print(f"   ⏱️  {datetime.now().strftime('%H:%M:%S')}")
        
        def on_task_completed(event: Event):
            task_id = event.data.get("task_id")
            result_size = event.data.get("result_size", 0)
            print(f"✅ Task completed: {task_id} (result size: {result_size} chars)")
            print(f"   ⏱️  {datetime.now().strftime('%H:%M:%S')}")
        
        def on_task_failed(event: Event):
            task_id = event.data.get("task_id")
            error = event.data.get("error", "Unknown error")
            print(f"❌ Task failed: {task_id} - {error}")
            print(f"   ⏱️  {datetime.now().strftime('%H:%M:%S')}")
        
        # Register event listeners
        self.event_bus.subscribe("task.started", on_task_started)
        self.event_bus.subscribe("task.completed", on_task_completed)
        self.event_bus.subscribe("task.failed", on_task_failed)
    
    def _register_tools(self, tool_list: Optional[List[Any]] = None):
        """Register tools with automatic metadata extraction."""
        tool_list = tool_list or [WebSearchTool, WebPageParserTool, ComposerTool]
        for tool in tool_list:
            tool_id = tool.__name__
            self.tool_registry.register_tool_class(
                tool_class=tool,
                config={"default_config": "value1"}
            )
            print(f"✅ Registered {tool.__name__} with ID: {tool_id}")

        
        # Show registration summary
        stats = self.tool_registry.get_statistics()
        print(f"\n📊 Tool Registration Summary:")
        print(f"   • Total tools: {stats['total_tools']}")
        print(f"   • Categories: {stats['categories']}")
        print(f"   • Capabilities: {stats['capabilities']}")
        
        # List all registered tools
        print(f"\n📋 Registered Tools:")
        tools = self.tool_registry.list_tools()
        for tool in tools:
            print(f"   • {tool['name']} - {tool['description'][:60]}...")
            print(f"     Task types: {tool['task_types']}")
    
    def _register_components(self):
        """Register workflow components with the factory."""
        # This method is now deprecated - tools are registered via tool_registry
        pass
    
    async def execute(self, context: Dict[str, Any]) -> WorkflowResult:
        """
        Execute the web research workflow using the generic execution engine.
        
        This workflow performs:
        1. Web Search: Searches for URLs based on the query using WebSearchTool
        2. Web Scraping: Scrapes content from URLs found in step 1 using WebPageParserTool
        3. Content Composition: Composes and summarizes the scraped content using ComposerTool
        
        Args:
            context: Execution context with parameters
            
        Returns:
            WorkflowResult with final summary
        """
        execution_start = time.time()
        self.state = WorkflowState.RUNNING
        self.started_at = datetime.now()
        
        # Start the event bus
        await self.event_bus.start()
        
        try:
            # Override query from context if provided
            if context.get("query"):
                self.query = context["query"]
            
            print(f"🚀 Starting Workflown Web Research Workflow")
            print(f"Query: '{self.query}'")
            print(f"Workflow ID: {self.workflow_id}")
            print(f"Steps: Web Search → Web Scraping → Content Composition")
            print("=" * 60)
            print(f"📋 Real-time progress and results will be displayed below:")
            print("=" * 60)
            
            # Step 1: Create workflow tasks with dependencies
            await self._create_workflow_tasks()
            
            # Step 2: Execute workflow using generic engine
            task_results = await self.execution_engine.execute_workflow(self.tasks)
            
            # Step 3: Collect and validate results
            final_result = await self._collect_final_results(task_results)
            
            # Success
            execution_time = time.time() - execution_start
            self.state = WorkflowState.COMPLETED
            self.completed_at = datetime.now()
            
            await self.event_bus.publish(Event(
                event_type="workflow.completed",
                source="workflow",
                data={
                    "workflow_id": self.workflow_id,
                    "execution_time": execution_time,
                    "query": self.query
                },
                timestamp=datetime.now()
            ))
            
            # Stop the event bus
            await self.event_bus.stop()
            
            return WorkflowResult(
                workflow_id=self.workflow_id,
                success=True,
                result=final_result,
                metadata={
                    "query": self.query,
                    "execution_time": execution_time,
                    "tasks_executed": len(self.tasks),
                    "framework": "workflown"
                },
                execution_time=execution_time,
                timestamp=self.completed_at
            )
            
        except Exception as e:
            # Failure
            execution_time = time.time() - execution_start
            self.state = WorkflowState.FAILED
            self.completed_at = datetime.now()
            
            await self.event_bus.publish(Event(
                event_type="workflow.failed",
                source="workflow",
                data={
                    "workflow_id": self.workflow_id,
                    "error": str(e),
                    "execution_time": execution_time
                },
                timestamp=datetime.now()
            ))
            
            # Stop the event bus
            await self.event_bus.stop()
            
            return WorkflowResult(
                workflow_id=self.workflow_id,
                success=False,
                result=None,
                metadata={"query": self.query, "execution_time": execution_time},
                execution_time=execution_time,
                timestamp=self.completed_at,
                errors=[str(e)]
            )
    
    async def _create_workflow_tasks(self):
        """Create workflow tasks with proper dependencies."""
        
        # Create specific web research tasks
        for i, task_type in enumerate(self.task_types[:self.max_tasks]):
            task_id = f"task_{i+1}"
            
            # Set parameters based on task type
            if task_type == "web_search":
                parameters = {
                    "query": self.query,
                    "max_results": 5,
                    "engine": "duckduckgo"
                }
            elif task_type == "webpage_parse":
                parameters = {
                    "urls": [],  # Will be populated from web search results
                    "strategy": "readability",
                    "extract_links": False,
                    "extract_images": False,
                    "max_content_length": 5000
                }
            elif task_type == "compose":
                parameters = {
                    "task": "summarize",
                    "content": "Sample content",  # Will be populated from scraping results
                    "format": "text",
                    "max_length": 2000,  # Increased from 1000 to 2000 for longer summaries
                    "min_length": 1000,  # Added minimum length requirement
                    "query": f"Provide a comprehensive summary of the following content about: {self.query}. Include key points, main themes, and important details. The summary should be detailed and informative."
                }
            else:
                parameters = {
                    "query": self.query,
                    "task_index": i + 1,
                    "max_results": 5
                }
            
            task = Task(
                task_id=task_id,
                name=f"Task {i+1}",
                description=f"Web research task: {task_type}",
                task_type=task_type,
                parameters=parameters,
                priority=TaskPriority.NORMAL,
                timeout=30.0
            )
            
            # Add dependency if not the first task
            if i > 0:
                dependency = TaskDependency(
                    dependency_id=f"task_{i}",
                    dependency_type=DependencyType.SEQUENTIAL,
                    required=True
                )
                task.add_dependency(dependency)
            
            self.tasks[task_id] = task
        
        print(f"📋 Created {len(self.tasks)} web research tasks with dependencies")
    
    async def _collect_final_results(self, task_results: Dict[str, Any]) -> Dict[str, Any]:
        """Collect and structure final workflow results."""
        
        return {
            "query": self.query,
            "task_results": task_results,
            "workflow_metadata": {
                "workflow_id": self.workflow_id,
                "execution_timestamps": {
                    "started": self.started_at.isoformat() if self.started_at else None,
                    "completed": self.completed_at.isoformat() if self.completed_at else None
                },
                "tasks_executed": list(self.tasks.keys()),
                "component_registry_size": len(self.component_registry.list_components()),
                "framework_version": "workflown-1.0"
            }
        }
    
    async def pause(self) -> bool:
        """Pause workflow execution."""
        if self.state == WorkflowState.RUNNING:
            self.state = WorkflowState.PAUSED
            await self.event_bus.publish(Event(
                event_type="workflow.paused",
                source="workflow",
                data={"workflow_id": self.workflow_id},
                timestamp=datetime.now()
            ))
            return True
        return False
    
    async def resume(self) -> bool:
        """Resume paused workflow execution."""
        if self.state == WorkflowState.PAUSED:
            self.state = WorkflowState.RUNNING
            await self.event_bus.publish(Event(
                event_type="workflow.resumed",
                source="workflow",
                data={"workflow_id": self.workflow_id},
                timestamp=datetime.now()
            ))
            return True
        return False
    
    async def cancel(self) -> bool:
        """Cancel workflow execution."""
        if self.state in [WorkflowState.RUNNING, WorkflowState.PAUSED]:
            self.state = WorkflowState.CANCELLED
            self.completed_at = datetime.now()
            
            # Cancel all pending tasks
            for task in self.tasks.values():
                if task.state in [TaskState.PENDING, TaskState.RUNNING]:
                    task.cancel("Workflow cancelled")
            
            await self.event_bus.publish(Event(
                event_type="workflow.cancelled",
                source="workflow",
                data={"workflow_id": self.workflow_id},
                timestamp=datetime.now()
            ))
            return True
        return False

 
async def main():
    """Main function to run the Workflown-based web research workflow."""
    
    # Get query from command line or use default
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "Agentic AI frameworks in 2025"
    
    print(f"🚀 Workflown Framework Web Research Workflow Example")
    print(f"Query: '{query}'")
    print(f"Workflow Steps: Web Search → Web Scraping → Content Composition")
    print()
    
    try:
        # Create workflow with configuration
        workflow_config = {
            "query": query,
            "max_tasks": 3,
            "task_types": ["web_search", "webpage_parse", "compose"]
        }
        
        # Initialize workflow ------------------------------------------------------------
        workflow = GenericWorkflowExample(config=workflow_config)


        # Register tools ------------------------------------------------------------------
        tool1_id = workflow.tool_registry.register_tool_class(
            tool_class=WebSearchTool,
            config={"default_config": "value1",
                    "persistence": {
                        "enabled": True,
                        "base_path": "logs/persistence",
                        "inputs_subdir": "inputs",
                        "outputs_subdir": "outputs",
                        "persist_inputs": True,
                        "persist_outputs": True
                    }
                    }
        )
        print(f"✅ Registered WebSearchTool with ID: {tool1_id}")
        
        # Register TaskType2Tool
        tool2_id = workflow.tool_registry.register_tool_class(
            tool_class=WebPageParserTool,
            config={"default_config": "value2",
                    "persistence": {
                        "enabled": True,
                        "base_path": "logs/persistence",
                        "inputs_subdir": "inputs",
                        "outputs_subdir": "outputs",
                        "persist_inputs": True,
                        "persist_outputs": True
                    }
                    }
        )
        print(f"✅ Registered WebPageParserTool with ID: {tool2_id}")
        
        # Register TaskType3Tool
        tool3_id = workflow.tool_registry.register_tool_class(
            tool_class=ComposerTool,
            config={"default_config": "value3",
                    "persistence": {
                        "enabled": True,
                        "base_path": "logs/persistence",
                        "inputs_subdir": "inputs",
                        "outputs_subdir": "outputs",
                        "persist_inputs": True,
                        "persist_outputs": True
                    }
                    }
        )
        print(f"✅ Registered ComposerTool with ID: {tool3_id}")


        # Set result passing config ------------------------------------------------------

        workflow.execution_engine.result_passing_config = {
            "web_search": {
                "input_from": None,  # No input dependency
                "input_field": "query",
                "result_path": "result",
                "transform": lambda results: results
            },
            "webpage_parse": {
                "input_from": "task_1", 
                "input_field": "urls",
                "result_path": "result",
                "transform": workflow.execution_engine._extract_urls_from_search_results
            },
            "compose": {
                "input_from": "task_2",
                "input_field": "content",
                "result_path": "result",
                # Let ComposerTool handle preparation/cleaning
                "transform": lambda results: results
            }
        }


        # Execute workflow --------------------------------------------------------------
        context = {"query": query}
        result = await workflow.execute(context)
        
        # Display final summary
        if result.success:
            print(f"\n{'=' * 60}")
            print(f"🎉 WORKFLOW COMPLETED SUCCESSFULLY")
            print(f"{'=' * 60}")
            
            # Display execution metrics
            print(f"📊 Final Execution Summary:")
            print(f"   • Workflow ID: {result.workflow_id}")
            print(f"   • Total Execution Time: {result.execution_time:.2f} seconds")
            print(f"   • Tasks Executed: {result.metadata.get('tasks_executed', 0)}")
            print(f"   • Framework: {result.metadata.get('framework', 'unknown')}")
            
            # Show execution stats from engine
            if hasattr(workflow, 'execution_engine'):
                stats = workflow.execution_engine.get_execution_stats()
                print(f"   • Success Rate: {stats.get('success_rate', 0):.1%}")
                print(f"   • Tool Mappings: {stats.get('tool_mappings', 0)}")
            
            # Display workflow metadata
            if hasattr(result, 'result') and isinstance(result.result, dict):
                workflow_meta = result.result.get("workflow_metadata", {})
                if workflow_meta:
                    print(f"\n🔧 Workflow Metadata:")
                    print(f"   • Component Registry: {workflow_meta.get('component_registry_size', 0)} components")
                    print(f"   • Framework Version: {workflow_meta.get('framework_version', 'unknown')}")
                    
                    timestamps = workflow_meta.get("execution_timestamps", {})
                    if timestamps.get("started") and timestamps.get("completed"):
                        print(f"   • Started: {timestamps['started']}")
                        print(f"   • Completed: {timestamps['completed']}")
            
            print(f"\n✅ All tasks completed successfully!")
            print(f"📋 Results were displayed in real-time during execution.")
            print(f"{'=' * 60}")
        
        else:
            print(f"\n❌ WORKFLOW FAILED")
            print(f"Errors: {result.errors}")
            return 1
        
        return 0
        
    except Exception as e:
        print(f"❌ Workflow error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)