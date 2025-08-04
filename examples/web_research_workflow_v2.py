"""
Web Research Workflow v2

Demonstrates a complete workflow using real tools:
1. WebSearchTool for searching the web
2. ComposerTool for summarizing and generating reports

This example shows how to use the tools framework with real implementations.
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflown.core.config.central_config import get_config
from workflown.core.logging.logger import get_logger, LogLevel
from workflown.core.logging.handlers import ConsoleHandler, FileHandler, StructuredHandler
from workflown.core.logging.formatters import StandardFormatter, JSONFormatter, ColoredFormatter
from workflown.core.storage.filesystem_storage import FilesystemStorage
from workflown.core.execution.executor_registry import ExecutorRegistry
from workflown.core.execution.base_executor import BaseExecutor, ExecutorCapability
from workflown.core.execution.executor_registry import ExecutorRegistry
from workflown.core.planning.simple_planner import SimplePlanner
from workflown.core.dispatch.task_dispatcher import TaskDispatcher
from workflown.core.dispatch.base_dispatcher import DispatchContext
from workflown.core.workflows.base_workflow import BaseWorkflow, WorkflowState, WorkflowResult
from workflown.core.workflows.task import Task, TaskState, TaskPriority
from workflown.core.events.event_bus import EventBus
from workflown.core.events.event_types import create_workflow_started_event, create_task_started_event, create_task_completed_event

# Import tools
from tools import WebSearchTool, ComposerTool, tool_registry

async def setup_logging():
    """Set up logging for the workflow using central configuration."""
    from workflown.core.logging.config import setup_logging_from_config
    
    # Use centralized logging configuration
    logger = await setup_logging_from_config("WebResearchWorkflowV2")
    
    # Log the configuration being used
    from workflown.core.logging.config import get_logging_summary
    logging_summary = get_logging_summary()
    
    await logger.info("Logging configured from central config for WebResearchWorkflowV2", 
                     config_summary=logging_summary)
    
    return logger


class ToolBasedExecutor(BaseExecutor):
    """
    Executor that uses tools for task execution.
    
    This executor delegates task execution to appropriate tools
    based on task type and parameters.
    """
    
    def __init__(self, executor_id: str = None, config: Dict[str, Any] = None):
        super().__init__(
            executor_id=executor_id,
            name="ToolBasedExecutor",
            description="Executes tasks using specialized tools",
            capabilities=[
                ExecutorCapability.HTTP,
                ExecutorCapability.CUSTOM,
                ExecutorCapability.GENERIC
            ],
            max_concurrent_tasks=5,
            config=config
        )
        
        # Initialize tools
        self.web_search_tool = WebSearchTool(
            tool_id=f"{self.executor_id}_web_search",
            config=self.config.get("web_search", {})
        )
        
        self.composer_tool = ComposerTool(
            tool_id=f"{self.executor_id}_composer",
            config=self.config.get("composer", {})
        )
        
        # Register tools
        tool_registry.register_tool(self.web_search_tool)
        tool_registry.register_tool(self.composer_tool)
        
        # Task type to tool mapping
        self.task_handlers = {
            "web_search": self._execute_web_search,
            "summarize": self._execute_summarize,
            "compose_report": self._execute_compose_report,
            "analyze": self._execute_analyze
        }


    
    async def execute_task(self, task: Task) -> Any:
        """Execute a task using appropriate tools."""

        logger = get_logger(f"{self.name}.{self.executor_id}")
        
        await logger.info(f"Starting tool-based task: {task.task_id}", 
                         task_id=task.task_id, executor_id=self.executor_id)
        
        start_time = datetime.now()
        
        try:
            # Get the appropriate handler
            handler = self.task_handlers.get(task.task_type)
            await logger.info(f"Task type: {task.task_type}, Available handlers: {list(self.task_handlers.keys())}")
            if not handler:
                raise ValueError(f"Unsupported task type: {task.task_type}")
            
            # Execute the task
            result = await handler(task)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            await logger.info(f"Task completed: {task.task_id}", 
                             task_id=task.task_id, execution_time=execution_time)
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            await logger.error(f"Task failed: {task.task_id}", 
                              task_id=task.task_id, error=str(e), execution_time=execution_time)
            
            raise
    
    async def _execute_web_search(self, task: Task) -> Dict[str, Any]:
        """Execute web search task."""
        parameters = {
            "query": task.parameters.get("query", ""),
            "engine": task.parameters.get("engine", "duckduckgo"),
            "max_results": task.parameters.get("max_results", 10),
            "language": task.parameters.get("language", "en"),
            "region": task.parameters.get("region", "US")
        }
        
        logger = get_logger(f"{self.name}.{self.executor_id}")
        await logger.info(f"Executing web search with parameters: {parameters}")
        
        result = await self.web_search_tool.execute_with_tracking(parameters)
        
        await logger.info(f"Web search completed with success: {result.success}")
        await logger.info(f"Web search result keys: {list(result.__dict__.keys())}")
        await logger.info(f"Web search results count: {len(result.result) if result.result else 0}")
        
        if result.success:
            return {
                "success": True,
                "results": result.result,
                "metadata": result.metadata,
                "execution_time": result.execution_time
            }
        else:
            raise Exception(f"Web search failed: {result.errors}")
    
    async def _execute_summarize(self, task: Task) -> Dict[str, Any]:
        """Execute summarization task."""
        parameters = {
            "operation": "summarize",
            "content": task.parameters.get("content", ""),
            "format": task.parameters.get("format", "text"),
            "style": task.parameters.get("style", "formal"),
            "length": task.parameters.get("length", "medium")
        }
        
        result = await self.composer_tool.execute_with_tracking(parameters)
        
        if result.success:
            return {
                "success": True,
                "summary": result.result,
                "metadata": result.metadata,
                "execution_time": result.execution_time
            }
        else:
            raise Exception(f"Summarization failed: {result.errors}")
    
    async def _execute_compose_report(self, task: Task) -> Dict[str, Any]:
        """Execute report composition task."""
        parameters = {
            "operation": "compose_report",
            "content": task.parameters.get("content", ""),
            "format": task.parameters.get("format", "markdown"),
            "style": task.parameters.get("style", "formal"),
            "length": task.parameters.get("length", "long")
        }
        
        result = await self.composer_tool.execute_with_tracking(parameters)
        
        if result.success:
            return {
                "success": True,
                "report": result.result,
                "metadata": result.metadata,
                "execution_time": result.execution_time
            }
        else:
            raise Exception(f"Report composition failed: {result.errors}")
    
    async def _execute_analyze(self, task: Task) -> Dict[str, Any]:
        """Execute analysis task."""
        parameters = {
            "operation": "analyze",
            "content": task.parameters.get("content", ""),
            "format": task.parameters.get("format", "text"),
            "style": task.parameters.get("style", "technical"),
            "length": task.parameters.get("length", "medium")
        }
        
        result = await self.composer_tool.execute_with_tracking(parameters)
        
        if result.success:
            return {
                "success": True,
                "analysis": result.result,
                "metadata": result.metadata,
                "execution_time": result.execution_time
            }
        else:
            raise Exception(f"Analysis failed: {result.errors}")
    
    def can_handle_task(self, task: Task) -> bool:
        """Check if this executor can handle the given task."""
        return task.task_type in self.task_handlers
    
    def get_supported_task_types(self) -> List[str]:
        """Get list of supported task types."""
        return list(self.task_handlers.keys())
    
    async def cleanup(self):
        """Clean up executor resources."""
        await self.web_search_tool.cleanup()
        await self.composer_tool.cleanup()


class WebResearchWorkflowV2(BaseWorkflow):
    """
    Web Research Workflow using real tools.
    
    This workflow demonstrates how to use the tools framework
    for real-world research tasks.
    """
    
    def __init__(self, workflow_id: str = None, config: Dict[str, Any] = None):
        """Initialize the workflow."""
        super().__init__(
            workflow_id=workflow_id,
            config=config
        )
        
        # Set workflow metadata
        self.name = "WebResearchWorkflowV2"
        self.description = "Web research workflow using real tools"
        
        # Initialize components
        self.executor = None
        self.planner = None
        self.dispatcher = None
        self.storage = None
        self.event_bus = None
        
        # Workflow state
        self.search_results = []
        self.summary = ""
        self.final_report = ""
        self.start_time = None
    
    async def setup(self):
        """Set up workflow components."""
        logger = get_logger(f"{self.name}.{self.workflow_id}")
        
        await logger.info("Setting up WebResearchWorkflowV2", workflow_id=self.workflow_id)
        
        # Initialize storage
        storage_config = self.config.get("storage", {})
        storage_config["base_path"] = "./examples/data"
        self.storage = FilesystemStorage(
            config=storage_config
        )
        await self.storage.connect()
        
        # Initialize event bus
        self.event_bus = EventBus()
        
        # Initialize executor
        self.executor = ToolBasedExecutor(
            executor_id=f"{self.workflow_id}_executor",
            config=self.config.get("executor", {})
        )
        
        # Initialize planner
        self.planner = SimplePlanner(
            planner_id=f"{self.workflow_id}_planner",
            config=self.config.get("planner", {})
        )
        
        # Initialize executor registry
        self.executor_registry = ExecutorRegistry()
        self.executor_registry.register_executor(self.executor)
        
        # Initialize dispatcher
        self.dispatcher = TaskDispatcher(
            executor_registry=self.executor_registry,
            dispatcher_id=f"{self.workflow_id}_dispatcher",
            config=self.config.get("dispatcher", {})
        )
        
        # Register executor with dispatcher (now handled by registry)
        
        await logger.info("WebResearchWorkflowV2 setup completed", workflow_id=self.workflow_id)
    
    async def execute(self, context: Dict[str, Any]) -> WorkflowResult:
        """
        Execute the web research workflow.
        
        Args:
            context: Workflow context including:
                - query: Research query
                - max_results: Maximum search results
                - report_format: Output format for report
                
        Returns:
            WorkflowResult with execution results
        """
        logger = get_logger(f"{self.name}.{self.workflow_id}")
        
        query = context.get("query", "artificial intelligence")
        max_results = context.get("max_results", 5)
        report_format = context.get("report_format", "markdown")
        
        # Store query for later use
        self.query = query
        
        await logger.info("Starting web research workflow", 
                         workflow_id=self.workflow_id, query=query, max_results=max_results)
        
        # Set start time
        self.start_time = datetime.now()
        
        try:
            # Phase 1: Web Search
            await logger.info("Phase 1: Performing web search", workflow_id=self.workflow_id)
            
            search_task = Task(
                task_id=f"{self.workflow_id}_search",
                task_type="web_search",
                parameters={
                    "query": query,
                    "engine": "duckduckgo",
                    "max_results": max_results,
                    "language": "en",
                    "region": "US"
                },
                priority=TaskPriority.HIGH
            )
            
            search_result = await self.executor.execute_task(search_task)
            self.search_results = search_result["results"]
            
            await logger.info(f"Search completed: {len(self.search_results)} results found",
                             workflow_id=self.workflow_id, results_count=len(self.search_results))
            
            # Phase 2: Summarize Results
            await logger.info("Phase 2: Summarizing search results", workflow_id=self.workflow_id)
            
            # Prepare content for summarization
            content_for_summary = self._prepare_content_for_summary()
            
            summarize_task = Task(
                task_id=f"{self.workflow_id}_summarize",
                task_type="summarize",
                parameters={
                    "content": content_for_summary,
                    "format": "text",
                    "style": "formal",
                    "length": "medium"
                },
                priority=TaskPriority.NORMAL
            )
            
            summarize_result = await self.executor.execute_task(summarize_task)
            self.summary = summarize_result["summary"]
            
            await logger.info("Summarization completed", workflow_id=self.workflow_id)
            
            # Phase 3: Generate Final Report
            await logger.info("Phase 3: Generating final report", workflow_id=self.workflow_id)
            
            # Prepare content for report
            content_for_report = self._prepare_content_for_report()
            
            report_task = Task(
                task_id=f"{self.workflow_id}_report",
                task_type="compose_report",
                parameters={
                    "content": content_for_report,
                    "format": report_format,
                    "style": "formal",
                    "length": "long"
                },
                priority=TaskPriority.NORMAL
            )
            
            report_result = await self.executor.execute_task(report_task)
            self.final_report = report_result["report"]
            
            await logger.info("Report generation completed", workflow_id=self.workflow_id)
            
            # Save results
            await self._save_results(query, context)
            
            # Create workflow result
            execution_time = (datetime.now() - self.start_time).total_seconds()
            result = WorkflowResult(
                workflow_id=self.workflow_id,
                success=True,
                result={
                    "query": query,
                    "search_results": self.search_results,
                    "summary": self.summary,
                    "final_report": self.final_report,
                    "total_results": len(self.search_results)
                },
                metadata={
                    "phases_completed": 3,
                    "tools_used": ["WebSearchTool", "ComposerTool"],
                    "execution_time": execution_time
                },
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
            await logger.info("Web research workflow completed successfully", 
                             workflow_id=self.workflow_id, success=True)
            
            return result
            
        except Exception as e:
            await logger.error("Web research workflow failed", 
                              workflow_id=self.workflow_id, error=str(e))
            
            return WorkflowResult(
                workflow_id=self.workflow_id,
                success=False,
                result=None,
                metadata={"error": str(e)},
                execution_time=(datetime.now() - self.start_time).total_seconds(),
                timestamp=datetime.now()
            )
    
    def _prepare_content_for_summary(self) -> str:
        """Prepare search results for summarization."""
        content = "Search Results Summary:\n\n"
        
        for i, result in enumerate(self.search_results, 1):
            content += f"{i}. {result['title']}\n"
            content += f"   URL: {result['url']}\n"
            content += f"   Snippet: {result['snippet']}\n"
            content += f"   Relevance: {result.get('relevance', 0.0):.2f}\n\n"
        
        return content
    
    def _prepare_content_for_report(self) -> str:
        """Prepare content for final report generation."""
        content = f"Research Query: {self.query}\n\n"
        content += f"Summary: {self.summary}\n\n"
        content += "Detailed Search Results:\n\n"
        
        for i, result in enumerate(self.search_results, 1):
            content += f"## Result {i}: {result['title']}\n"
            content += f"**URL:** {result['url']}\n"
            content += f"**Relevance:** {result.get('relevance', 0.0):.2f}\n"
            content += f"**Summary:** {result['snippet']}\n\n"
        
        return content
    
    async def _save_results(self, query: str, context: Dict[str, Any]):
        """Save workflow results to storage."""
        results_data = {
            "workflow_id": self.workflow_id,
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "search_results": self.search_results,
            "summary": self.summary,
            "final_report": self.final_report,
            "context": context
        }
        
        filename = f"research_results_{self.workflow_id}_{int(time.time())}.json"
        await self.storage.store(filename, json.dumps(results_data, indent=2))
    
    async def cleanup(self):
        """Clean up workflow resources."""
        if self.executor:
            await self.executor.cleanup()
    
    async def pause(self) -> bool:
        """Pause the workflow execution."""
        # Implementation for pausing workflow
        await self.logger.info("Workflow paused", workflow_id=self.workflow_id)
        return True
    
    async def resume(self) -> bool:
        """Resume the workflow execution."""
        # Implementation for resuming workflow
        await self.logger.info("Workflow resumed", workflow_id=self.workflow_id)
        return True
    
    async def cancel(self) -> bool:
        """Cancel the workflow execution."""
        # Implementation for canceling workflow
        await self.logger.info("Workflow cancelled", workflow_id=self.workflow_id)
        return True





async def main():
    """Main function to run the web research workflow."""
    print("=" * 60)
    print("🌐 WEB RESEARCH WORKFLOW V2 - USING REAL TOOLS")
    print("=" * 60)
    
    # Set up logging
    logger = await setup_logging()
    
    try:
        # Configuration
        config = {
            "storage": {
                "base_path": "./examples/data"
            },
            "executor": {
                "web_search": {
                    "rate_limit_delay": 1.0,
                    "engine": "duckduckgo",
                    "max_retries": 3
                },
                "composer": {
                    "llm": {
                        "model": "gpt-4o-mini",
                        "max_tokens": 2000,
                        "temperature": 0.7
                    }
                }
            }
        }
        
        # Create workflow
        workflow = WebResearchWorkflowV2(config=config)
        
        # Set up workflow
        await workflow.setup()
        
        # Execute workflow
        context = {
            "query": "artificial intelligence trends 2024",
            "max_results": 5,
            "report_format": "markdown"
        }
        
        print(f"\n🔍 Starting research on: {context['query']}")
        print(f"📊 Max results: {context['max_results']}")
        print(f"📝 Report format: {context['report_format']}")
        
        result = await workflow.execute(context)
        
        if result.success:
            print("\n✅ Workflow completed successfully!")
            print(f"📈 Total results found: {result.result['total_results']}")
            print(f"⏱️  Execution time: {result.metadata['execution_time']:.2f}s")
            
            # Display summary
            print(f"\n📋 SUMMARY:")
            print("-" * 40)
            print(result.result['summary'])
            
            # Save report to file
            report_filename = f"research_report_{workflow.workflow_id}.md"
            with open(f"./examples/{report_filename}", "w") as f:
                f.write(result.result['final_report'])
            
            print(f"\n📄 Final report saved to: {report_filename}")
            
        else:
            print(f"\n❌ Workflow failed: {result.metadata.get('error', 'Unknown error')}")
        
        # Cleanup
        await workflow.cleanup()
        
    except Exception as e:
        print(f"\n❌ Example failed: {str(e)}")
        await logger.error(f"Example failed", error=str(e))


if __name__ == "__main__":
    asyncio.run(main()) 