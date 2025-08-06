#!/usr/bin/env python3
"""
Workflown Framework Search-Scrape-Summarize Workflow

Demonstrates proper use of the Workflown framework capabilities:
- BaseWorkflow for orchestration
- Task system with dependencies
- Component factory for tool creation
- Configuration management
- Event system for progress tracking

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
sys.path.insert(0, str(Path(__file__).parent / "tools"))
sys.path.insert(0, str(Path(__file__).parent / "tools" / "websearch"))

from workflown.core.workflows.base_workflow import BaseWorkflow, WorkflowResult, WorkflowState
from workflown.core.workflows.task import Task, TaskPriority, TaskState, TaskDependency, DependencyType
from workflown.core.config.component_factory import ComponentFactory, ComponentRegistry, ComponentSpec, ComponentType
from workflown.core.events.event_bus import EventBus, Event, EventPriority
from workflown.core.config.central_config import get_config

# Import tool registry and mapper
from tools.tool_registry import ToolRegistry
from tools.simple_tool_mapper import SimpleToolMapper, TaskMapping, MappingStrategy
from tools.base_tool import ToolCapability


class WorkflowExecutionEngine:
    """
    Generic workflow execution engine that handles:
    - Task dependency resolution
    - Automatic task execution based on dependencies
    - Result passing between tasks
    - Event-driven progress tracking
    - Intelligent tool mapping using enhanced registry
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
        
        # Configuration for result passing between tasks
        self.result_passing_config = {
            "web_scraping": {
                "input_from": "search_task",
                "input_field": "urls",
                "result_path": "result",
                "transform": lambda results: [item.get("url", "") for item in results[:3]]
            },
            "text_generation": {
                "input_from": "scrape_task", 
                "input_field": "content",
                "result_path": "result",
                "transform": lambda results: [item for item in results if not item.get('metadata', {}).get('error') and len(item.get('content', '')) > 100]
            }
        }
        
    async def execute_workflow(self, tasks: Dict[str, Task]) -> Dict[str, Any]:
        """
        Execute a workflow with automatic dependency resolution and result passing.
        
        Args:
            tasks: Dictionary of tasks to execute
            
        Returns:
            Dictionary containing all task results
        """
        print(f"🚀 Starting generic workflow execution with {len(tasks)} tasks")
        
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
            data={"task_id": task_id},
            timestamp=datetime.now()
        ))
        
        try:
            # Prepare task parameters with results from previous tasks
            parameters = self._prepare_task_parameters(task)
            
            # Execute task based on type
            result = await self._execute_task_by_type(task, parameters)
            
            # Store result and mark as completed
            self.task_results[task_id] = result
            self.completed_tasks.add(task_id)
            self.running_tasks.remove(task_id)
            
            task.complete(result, {"execution_engine": "generic"})
            
            await self.event_bus.publish(Event(
                event_type="task.completed",
                source="workflow_engine",
                data={
                    "task_id": task_id,
                    "result_size": len(str(result))
                },
                timestamp=datetime.now()
            ))
            
            print(f"✅ Task completed: {task_id}")
            
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
        
        if source_results:
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
            tool_mapper = SimpleToolMapper(self.tool_registry)
            
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
            # Execute the tool
            result = await tool_instance.execute(parameters)
            
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


class SearchScrapeSummarizeWorkflow(BaseWorkflow):
    """
    Search-Scrape-Summarize workflow using Workflown framework.
    
    This workflow demonstrates proper use of:
    - Task orchestration with dependencies
    - Component factory for tool management
    - Event-driven progress tracking
    - Configuration management
    - Error handling and recovery
    """
    
    def __init__(self, workflow_id: str = None, config: Dict[str, Any] = None):
        super().__init__(workflow_id, config)
        
        # Initialize framework components
        self.event_bus = EventBus()
        self.component_registry = ComponentRegistry()
        self.component_factory = ComponentFactory(self.component_registry)
        
        # Workflow configuration
        self.query = self.config.get("query", "Agentic AI frameworks in 2025")
        self.max_urls = self.config.get("max_urls", 5)
        self.scrape_limit = self.config.get("scrape_limit", 3)
        
        # Task tracking
        self.tasks = {}
        self.results = {}
        
        # Setup event listeners
        self._setup_event_listeners()
        
        # Initialize and populate tool registry
        self.tool_registry = ToolRegistry()
        self._register_tools()
        
        print(f"🔧 Workflow using registry instance: {id(self.tool_registry)}")
        
        # Create execution engine with the populated registry
        self.execution_engine = WorkflowExecutionEngine(self.event_bus, self.component_factory, self.tool_registry)
    
    def _setup_event_listeners(self):
        """Setup event listeners for workflow monitoring."""
        
        def on_task_started(event: Event):
            task_id = event.data.get("task_id")
            print(f"📝 Task started: {task_id}")
        
        def on_task_completed(event: Event):
            task_id = event.data.get("task_id")
            print(f"✅ Task completed: {task_id}")
        
        def on_task_failed(event: Event):
            task_id = event.data.get("task_id")
            error = event.data.get("error", "Unknown error")
            print(f"❌ Task failed: {task_id} - {error}")
        
        # Register event listeners
        self.event_bus.subscribe("task.started", on_task_started)
        self.event_bus.subscribe("task.completed", on_task_completed)
        self.event_bus.subscribe("task.failed", on_task_failed)
    
    def _register_tools(self):
        """Register tools with metadata in the tool registry."""
        from tools.websearch.googlesearch_python_search import GoogleSearchPythonTool
        from tools.webpage_parser import WebPageParserTool
        from tools.composer_tool import ComposerTool
        
        # Register Google Search Python Tool
        google_search_metadata = {
            "name": "Google Search Python",
            "description": "Performs web searches using googlesearch-python library",
            "task_types": ["web_search", "search", "url_discovery"],
            "capabilities": [ToolCapability.WEB_SEARCH, ToolCapability.HTTP_REQUESTS],
            "keywords": ["google", "search", "web", "urls", "results", "query"]
        }
        
        self.tool_registry.register_tool_with_metadata(
            tool_class=GoogleSearchPythonTool,
            metadata=google_search_metadata,
            config={
                "pause_between_requests": 2.0,
                "safe": "off",
                "max_retries": 2
            }
        )
        
        # Register Web Page Parser Tool
        webpage_parser_metadata = {
            "name": "Web Page Parser",
            "description": "Scrapes and parses web pages to extract content",
            "task_types": ["web_scraping", "content_extraction", "data_processing"],
            "capabilities": [ToolCapability.HTTP_REQUESTS, ToolCapability.DATA_PROCESSING],
            "keywords": ["webpage", "parser", "scraper", "content", "extraction"]
        }
        
        self.tool_registry.register_tool_with_metadata(
            tool_class=WebPageParserTool,
            metadata=webpage_parser_metadata,
            config={
                "request_timeout": 15,
                "max_content_length": 200000,
                "rate_limit_delay": 1.5,
                "max_retries": 2,
                "min_content_length": 200
            }
        )
        
        # Register LLM Composer Tool
        composer_metadata = {
            "name": "LLM Composer",
            "description": "Generates text content using Large Language Models",
            "task_types": ["text_generation", "summarization", "content_creation"],
            "capabilities": [ToolCapability.TEXT_GENERATION, ToolCapability.TEXT_SUMMARIZATION],
            "keywords": ["llm", "generation", "text", "composer", "ai"]
        }
        
        self.tool_registry.register_tool_with_metadata(
            tool_class=ComposerTool,
            metadata=composer_metadata,
            config={
                "provider": "azure_openai",
                "max_tokens": 2000,
                "temperature": 0.7
            }
        )
        
        # Print registration summary
        stats = self.tool_registry.get_statistics()
        print(f"\n✅ Tool registration completed!")
        print(f"📊 Registry Statistics:")
        print(f"   • Total tools: {stats['total_tools']}")
        print(f"   • Categories: {stats['categories']}")
        print(f"   • Capabilities: {stats['capabilities']}")
        
        # List all registered tools
        print(f"\n📋 Registered Tools:")
        tools = self.tool_registry.list_tools()
        for tool in tools:
            print(f"   • {tool['name']} - {tool['description'][:60]}...")
    
    def _register_components(self):
        """Register workflow components with the factory."""
        # This method is now deprecated - tools are registered via tool_registry
        pass
    
    async def execute(self, context: Dict[str, Any]) -> WorkflowResult:
        """
        Execute the search-scrape-summarize workflow using the generic execution engine.
        
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
            
            print(f"🚀 Starting Workflown Search-Scrape-Summarize Workflow")
            print(f"Query: '{self.query}'")
            print(f"Workflow ID: {self.workflow_id}")
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
        
        # Task 1: Web Search
        search_task = Task(
            task_id="search_task",
            name="Web Search",
            description=f"Search the web for: {self.query}",
            task_type="web_search",
            parameters={
                "query": self.query,
                "max_results": self.max_urls,
                "language": "en",
                "region": "US"
            },
            priority=TaskPriority.HIGH,
            timeout=30.0
        )
        self.tasks["search_task"] = search_task
        
        # Task 2: Web Scraping (depends on search)
        scrape_task = Task(
            task_id="scrape_task",
            name="Web Scraping",
            description="Scrape content from search result URLs",
            task_type="web_scraping",
            parameters={
                "urls": [],  # Will be populated from search results
                "extract_links": False,
                "extract_images": False,
                "strategy": "auto"
            },
            priority=TaskPriority.NORMAL,
            timeout=60.0
        )
        
        # Add dependency: scraping depends on search completion
        scrape_dependency = TaskDependency(
            dependency_id="search_task",
            dependency_type=DependencyType.SEQUENTIAL,
            required=True
        )
        scrape_task.add_dependency(scrape_dependency)
        self.tasks["scrape_task"] = scrape_task
        
        # Task 3: Content Summarization (depends on scraping)
        summarize_task = Task(
            task_id="summarize_task",
            name="Content Summarization",
            description="Generate summary using LLM",
            task_type="text_generation",
            parameters={
                "task": "combine",
                "content": [],  # Will be populated from scraping results
                "query": self.query,
                "format": "text",
                "include_sources": True
            },
            priority=TaskPriority.CRITICAL,
            timeout=45.0
        )
        
        # Add dependency: summarization depends on scraping completion
        summarize_dependency = TaskDependency(
            dependency_id="scrape_task",
            dependency_type=DependencyType.SEQUENTIAL,
            required=True
        )
        summarize_task.add_dependency(summarize_dependency)
        self.tasks["summarize_task"] = summarize_task
        
        print(f"📋 Created {len(self.tasks)} workflow tasks with dependencies")
    
    async def _collect_final_results(self, task_results: Dict[str, Any]) -> Dict[str, Any]:
        """Collect and structure final workflow results."""
        
        return {
            "query": self.query,
            "search_results": task_results.get("search_task", []),
            "scraped_content": task_results.get("scrape_task", []),
            "final_summary": task_results.get("summarize_task", ""),
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


class DataAnalysisWorkflow(BaseWorkflow):
    """
    Example of a different workflow type using the same generic execution engine.
    
    This demonstrates how the WorkflowExecutionEngine can be reused for different
    workflow types with different task configurations.
    """
    
    def __init__(self, workflow_id: str = None, config: Dict[str, Any] = None):
        super().__init__(workflow_id, config)
        
        # Initialize framework components
        self.event_bus = EventBus()
        self.component_registry = ComponentRegistry()
        self.component_factory = ComponentFactory(self.component_registry)
        
        # Workflow configuration
        self.dataset_path = self.config.get("dataset_path", "sample_data.csv")
        self.analysis_type = self.config.get("analysis_type", "trend_analysis")
        
        # Task tracking
        self.tasks = {}
        self.results = {}
        
        # Setup event listeners
        self._setup_event_listeners()
        
        # Register components
        self._register_components()
        
        # Create execution engine with custom result passing config
        self.execution_engine = WorkflowExecutionEngine(self.event_bus, self.component_factory)
        self._setup_custom_result_passing()
    
    def _setup_event_listeners(self):
        """Setup event listeners for workflow monitoring."""
        
        def on_task_started(event: Event):
            task_id = event.data.get("task_id")
            print(f"📊 Data analysis task started: {task_id}")
        
        def on_task_completed(event: Event):
            task_id = event.data.get("task_id")
            print(f"✅ Data analysis task completed: {task_id}")
        
        def on_task_failed(event: Event):
            task_id = event.data.get("task_id")
            error = event.data.get("error", "Unknown error")
            print(f"❌ Data analysis task failed: {task_id} - {error}")
        
        # Register event listeners
        self.event_bus.subscribe("task.started", on_task_started)
        self.event_bus.subscribe("task.completed", on_task_completed)
        self.event_bus.subscribe("task.failed", on_task_failed)
    
    def _register_components(self):
        """Register data analysis components."""
        # This would register data analysis tools
        # For now, we'll use the same tools but with different configurations
        pass
    
    def _setup_custom_result_passing(self):
        """Setup custom result passing configuration for data analysis workflow."""
        # Example: Configure how data flows between analysis steps
        self.execution_engine.add_result_passing_config(
            "data_processing",
            {
                "input_from": "data_collection",
                "input_field": "raw_data",
                "result_path": "result",
                "transform": lambda results: results.get("data", [])
            }
        )
        
        self.execution_engine.add_result_passing_config(
            "data_visualization",
            {
                "input_from": "data_processing",
                "input_field": "processed_data",
                "result_path": "result",
                "transform": lambda results: results.get("processed_data", [])
            }
        )
    
    async def execute(self, context: Dict[str, Any]) -> WorkflowResult:
        """Execute the data analysis workflow."""
        execution_start = time.time()
        self.state = WorkflowState.RUNNING
        self.started_at = datetime.now()
        
        # Start the event bus
        await self.event_bus.start()
        
        try:
            print(f"🚀 Starting Data Analysis Workflow")
            print(f"Dataset: {self.dataset_path}")
            print(f"Analysis Type: {self.analysis_type}")
            print(f"Workflow ID: {self.workflow_id}")
            print("=" * 60)
            
            # Create workflow tasks
            await self._create_analysis_tasks()
            
            # Execute using generic engine
            task_results = await self.execution_engine.execute_workflow(self.tasks)
            
            # Collect results
            final_result = {
                "dataset_path": self.dataset_path,
                "analysis_type": self.analysis_type,
                "task_results": task_results,
                "execution_stats": self.execution_engine.get_execution_stats()
            }
            
            # Success
            execution_time = time.time() - execution_start
            self.state = WorkflowState.COMPLETED
            self.completed_at = datetime.now()
            
            await self.event_bus.publish(Event(
                event_type="workflow.completed",
                source="data_analysis_workflow",
                data={
                    "workflow_id": self.workflow_id,
                    "execution_time": execution_time,
                    "analysis_type": self.analysis_type
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
                    "analysis_type": self.analysis_type,
                    "execution_time": execution_time,
                    "tasks_executed": len(self.tasks),
                    "framework": "workflown"
                },
                execution_time=execution_time,
                timestamp=self.completed_at
            )
            
        except Exception as e:
            # Failure handling
            execution_time = time.time() - execution_start
            self.state = WorkflowState.FAILED
            self.completed_at = datetime.now()
            
            await self.event_bus.publish(Event(
                event_type="workflow.failed",
                source="data_analysis_workflow",
                data={
                    "workflow_id": self.workflow_id,
                    "error": str(e),
                    "execution_time": execution_time
                },
                timestamp=datetime.now()
            ))
            
            await self.event_bus.stop()
            
            return WorkflowResult(
                workflow_id=self.workflow_id,
                success=False,
                result=None,
                metadata={"analysis_type": self.analysis_type, "execution_time": execution_time},
                execution_time=execution_time,
                timestamp=self.completed_at,
                errors=[str(e)]
            )
    
    async def _create_analysis_tasks(self):
        """Create data analysis tasks with dependencies."""
        
        # Task 1: Data Collection
        collection_task = Task(
            task_id="data_collection",
            name="Data Collection",
            description=f"Collect data from {self.dataset_path}",
            task_type="data_collection",
            parameters={
                "source": self.dataset_path,
                "format": "csv"
            },
            priority=TaskPriority.HIGH,
            timeout=30.0
        )
        self.tasks["data_collection"] = collection_task
        
        # Task 2: Data Processing (depends on collection)
        processing_task = Task(
            task_id="data_processing",
            name="Data Processing",
            description="Process and clean the collected data",
            task_type="data_processing",
            parameters={
                "raw_data": [],  # Will be populated from collection results
                "cleaning_rules": ["remove_duplicates", "handle_missing"]
            },
            priority=TaskPriority.NORMAL,
            timeout=60.0
        )
        
        # Add dependency
        processing_dependency = TaskDependency(
            dependency_id="data_collection",
            dependency_type=DependencyType.SEQUENTIAL,
            required=True
        )
        processing_task.add_dependency(processing_dependency)
        self.tasks["data_processing"] = processing_task
        
        # Task 3: Data Visualization (depends on processing)
        visualization_task = Task(
            task_id="data_visualization",
            name="Data Visualization",
            description="Create visualizations from processed data",
            task_type="data_visualization",
            parameters={
                "processed_data": [],  # Will be populated from processing results
                "chart_types": ["line", "bar", "scatter"]
            },
            priority=TaskPriority.CRITICAL,
            timeout=45.0
        )
        
        # Add dependency
        visualization_dependency = TaskDependency(
            dependency_id="data_processing",
            dependency_type=DependencyType.SEQUENTIAL,
            required=True
        )
        visualization_task.add_dependency(visualization_dependency)
        self.tasks["data_visualization"] = visualization_task
        
        print(f"📊 Created {len(self.tasks)} data analysis tasks with dependencies")
    
    async def pause(self) -> bool:
        """Pause workflow execution."""
        if self.state == WorkflowState.RUNNING:
            self.state = WorkflowState.PAUSED
            await self.event_bus.publish(Event(
                event_type="workflow.paused",
                source="data_analysis_workflow",
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
                source="data_analysis_workflow",
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
                source="data_analysis_workflow",
                data={"workflow_id": self.workflow_id},
                timestamp=datetime.now()
            ))
            return True
        return False


async def main():
    """Main function to run the Workflown-based workflow."""
    
    # Get query from command line or use default
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "Agentic AI frameworks in 2025"
    
    print(f"🚀 Workflown Framework Search-Scrape-Summarize Test")
    print(f"Query: '{query}'")
    print()
    
    try:
        # Create workflow with configuration
        workflow_config = {
            "query": query,
            "max_urls": 5,
            "scrape_limit": 3
        }
        
        workflow = SearchScrapeSummarizeWorkflow(config=workflow_config)
        
        # Execute workflow
        context = {"query": query}
        result = await workflow.execute(context)
        
        # Display results
        if result.success:
            print(f"\n{'=' * 60}")
            print(f"🎉 WORKFLOW COMPLETED SUCCESSFULLY")
            print(f"{'=' * 60}")
            
            # Display execution metrics
            print(f"📊 Execution Metrics:")
            print(f"   • Workflow ID: {result.workflow_id}")
            print(f"   • Execution Time: {result.execution_time:.2f} seconds")
            print(f"   • Tasks Executed: {result.metadata.get('tasks_executed', 0)}")
            print(f"   • Framework: {result.metadata.get('framework', 'unknown')}")
            
            # Display final summary
            final_summary = result.result.get("final_summary", "")
            if final_summary:
                print(f"\n📋 FINAL SUMMARY:")
                print(f"{'─' * 60}")
                # Display first 800 characters
                display_summary = final_summary[:800]
                if len(final_summary) > 800:
                    display_summary += "\\n\\n[Summary truncated for display...]"
                print(display_summary)
                print(f"{'─' * 60}")
            
            # Display workflow metadata
            workflow_meta = result.result.get("workflow_metadata", {})
            if workflow_meta:
                print(f"\n🔧 Workflow Metadata:")
                print(f"   • Component Registry: {workflow_meta.get('component_registry_size', 0)} components")
                print(f"   • Framework Version: {workflow_meta.get('framework_version', 'unknown')}")
                
                timestamps = workflow_meta.get("execution_timestamps", {})
                if timestamps.get("started") and timestamps.get("completed"):
                    print(f"   • Started: {timestamps['started']}")
                    print(f"   • Completed: {timestamps['completed']}")
        
        else:
            print(f"\n❌ WORKFLOW FAILED")
            print(f"Errors: {result.errors}")
            return 1
        
        return 0
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Install with: pip install googlesearch-python beautifulsoup4")
        return 1
    except Exception as e:
        print(f"❌ Workflow error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)