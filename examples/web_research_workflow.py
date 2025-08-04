"""
Web Research Workflow Example

Demonstrates a complete workflow that:
1. Searches the web for information on a topic
2. Summarizes the search results
3. Composes a final report

This example shows planning, task execution, logging, and state management.
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
from workflown.core.planning.simple_planner import SimplePlanner
from workflown.core.dispatch.task_dispatcher import TaskDispatcher
from workflown.core.dispatch.base_dispatcher import DispatchContext
from workflown.core.workflows.base_workflow import BaseWorkflow, WorkflowState, WorkflowResult
from workflown.core.workflows.task import Task, TaskState, TaskPriority
from workflown.core.events.event_bus import EventBus
from workflown.core.events.event_types import create_workflow_started_event, create_task_started_event, create_task_completed_event


class WebSearchExecutor(BaseExecutor):
    """
    Specialized executor for web search tasks.
    
    In a real implementation, this would use actual web search APIs.
    For this example, it simulates web search with mock data.
    """
    
    def __init__(self, executor_id: str = None, config: Dict[str, Any] = None):
        super().__init__(
            executor_id=executor_id,
            name="WebSearchExecutor",
            description="Executes web search queries and returns results",
            capabilities=[ExecutorCapability.HTTP, ExecutorCapability.CUSTOM],
            max_concurrent_tasks=3,
            config=config
        )
        
        # Mock search results database
        self.mock_results = {
            "artificial intelligence": [
                {
                    "title": "What is Artificial Intelligence? - IBM",
                    "url": "https://www.ibm.com/cloud/learn/what-is-artificial-intelligence",
                    "snippet": "Artificial intelligence leverages computers and machines to mimic the problem-solving and decision-making capabilities of the human mind.",
                    "relevance": 0.95
                },
                {
                    "title": "AI Overview - Stanford University",
                    "url": "https://ai.stanford.edu/about/",
                    "snippet": "Stanford's AI research covers machine learning, robotics, natural language processing, and computer vision.",
                    "relevance": 0.92
                },
                {
                    "title": "The Future of AI - MIT Technology Review",
                    "url": "https://www.technologyreview.com/topic/artificial-intelligence/",
                    "snippet": "Exploring the latest developments in artificial intelligence and its impact on society and technology.",
                    "relevance": 0.88
                }
            ],
            "machine learning": [
                {
                    "title": "Machine Learning Explained - AWS",
                    "url": "https://aws.amazon.com/machine-learning/what-is-machine-learning/",
                    "snippet": "Machine learning is a method of data analysis that automates analytical model building.",
                    "relevance": 0.94
                },
                {
                    "title": "Introduction to ML - Coursera",
                    "url": "https://www.coursera.org/learn/machine-learning",
                    "snippet": "Learn machine learning fundamentals and practical applications.",
                    "relevance": 0.90
                }
            ]
        }
    
    async def execute_task(self, task: Task) -> Any:
        """Execute a web search task."""
        logger = get_logger(f"{self.name}.{self.executor_id}")
        
        await logger.info(f"Starting web search task: {task.task_id}", 
                         task_id=task.task_id, executor_id=self.executor_id)
        
        start_time = time.time()
        
        try:
            # Extract search parameters
            query = task.parameters.get("query", "")
            max_results = task.parameters.get("max_results", 5)
            
            if not query:
                raise ValueError("No search query provided")
            
            await logger.debug(f"Searching for: '{query}' (max_results: {max_results})",
                              query=query, max_results=max_results, task_id=task.task_id)
            
            # Simulate network delay
            await asyncio.sleep(1.0)
            
            # Get mock results
            query_lower = query.lower()
            results = []
            
            for key, mock_data in self.mock_results.items():
                if key in query_lower or any(word in key for word in query_lower.split()):
                    results.extend(mock_data[:max_results])
            
            # If no specific results, provide generic ones
            if not results:
                results = [
                    {
                        "title": f"Search Results for '{query}'",
                        "url": f"https://example.com/search?q={query.replace(' ', '+')}",
                        "snippet": f"Information about {query} from various sources.",
                        "relevance": 0.75
                    }
                ]
            
            # Sort by relevance and limit results
            results = sorted(results, key=lambda x: x["relevance"], reverse=True)[:max_results]
            
            execution_time = time.time() - start_time
            
            await logger.info(f"Web search completed: found {len(results)} results",
                             task_id=task.task_id, 
                             results_count=len(results),
                             execution_time=execution_time,
                             query=query)
            
            # Return structured results
            return {
                "query": query,
                "results": results,
                "total_results": len(results),
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            await logger.error(f"Web search failed: {str(e)}", 
                              exception=e, task_id=task.task_id, execution_time=execution_time)
            raise
    
    def can_handle_task(self, task: Task) -> bool:
        """Check if this executor can handle the task."""
        return task.task_type == "web_search"
    
    def get_supported_task_types(self) -> List[str]:
        """Get supported task types."""
        return ["web_search"]


class SummarizerExecutor(BaseExecutor):
    """
    Specialized executor for text summarization tasks.
    
    In a real implementation, this might use NLP libraries or AI APIs.
    For this example, it creates simple summaries.
    """
    
    def __init__(self, executor_id: str = None, config: Dict[str, Any] = None):
        super().__init__(
            executor_id=executor_id,
            name="SummarizerExecutor", 
            description="Summarizes text content and search results",
            capabilities=[ExecutorCapability.CUSTOM, ExecutorCapability.GENERIC],
            max_concurrent_tasks=2,
            config=config
        )
    
    async def execute_task(self, task: Task) -> Any:
        """Execute a summarization task."""
        logger = get_logger(f"{self.name}.{self.executor_id}")
        
        await logger.info(f"Starting summarization task: {task.task_id}",
                         task_id=task.task_id, executor_id=self.executor_id)
        
        start_time = time.time()
        
        try:
            # Extract summarization parameters
            search_results = task.parameters.get("search_results", {})
            summary_type = task.parameters.get("summary_type", "comprehensive")
            max_length = task.parameters.get("max_length", 500)
            
            if not search_results:
                raise ValueError("No search results provided for summarization")
            
            await logger.debug(f"Summarizing {len(search_results.get('results', []))} search results",
                              task_id=task.task_id, 
                              results_count=len(search_results.get('results', [])),
                              summary_type=summary_type)
            
            # Simulate processing time
            await asyncio.sleep(1.5)
            
            # Create summary based on search results
            query = search_results.get("query", "")
            results = search_results.get("results", [])
            
            if summary_type == "brief":
                summary = self._create_brief_summary(query, results)
            elif summary_type == "detailed":
                summary = self._create_detailed_summary(query, results)
            else:  # comprehensive
                summary = self._create_comprehensive_summary(query, results)
            
            # Truncate if needed
            if len(summary) > max_length:
                summary = summary[:max_length - 3] + "..."
            
            execution_time = time.time() - start_time
            
            await logger.info(f"Summarization completed: {len(summary)} characters",
                             task_id=task.task_id,
                             summary_length=len(summary),
                             execution_time=execution_time,
                             summary_type=summary_type)
            
            return {
                "query": query,
                "summary": summary,
                "summary_type": summary_type,
                "source_count": len(results),
                "character_count": len(summary),
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            await logger.error(f"Summarization failed: {str(e)}",
                              exception=e, task_id=task.task_id, execution_time=execution_time)
            raise
    
    def _create_brief_summary(self, query: str, results: List[Dict]) -> str:
        """Create a brief summary."""
        if not results:
            return f"No specific information found for '{query}'."
        
        top_result = results[0]
        return f"Brief summary for '{query}': {top_result['snippet']} (Source: {top_result['title']})"
    
    def _create_detailed_summary(self, query: str, results: List[Dict]) -> str:
        """Create a detailed summary."""
        if not results:
            return f"No detailed information available for '{query}'."
        
        summary_parts = [f"Detailed research summary for '{query}':"]
        
        for i, result in enumerate(results[:3], 1):
            summary_parts.append(f"{i}. {result['title']}: {result['snippet']}")
        
        if len(results) > 3:
            summary_parts.append(f"...and {len(results) - 3} additional sources.")
        
        return " ".join(summary_parts)
    
    def _create_comprehensive_summary(self, query: str, results: List[Dict]) -> str:
        """Create a comprehensive summary."""
        if not results:
            return f"No comprehensive information available for '{query}'."
        
        summary = f"Comprehensive research report on '{query}':\n\n"
        summary += f"Based on analysis of {len(results)} sources, here are the key findings:\n\n"
        
        for i, result in enumerate(results, 1):
            summary += f"{i}. {result['title']}\n"
            summary += f"   {result['snippet']}\n"
            summary += f"   Source: {result['url']}\n"
            summary += f"   Relevance: {result.get('relevance', 0.0):.2f}\n\n"
        
        summary += f"This research was compiled from {len(results)} sources with varying levels of relevance to the topic '{query}'."
        
        return summary
    
    def can_handle_task(self, task: Task) -> bool:
        """Check if this executor can handle the task."""
        return task.task_type == "summarize"
    
    def get_supported_task_types(self) -> List[str]:
        """Get supported task types."""
        return ["summarize"]


class ComposerExecutor(BaseExecutor):
    """
    Specialized executor for composing final reports.
    
    Takes summarized information and creates formatted reports.
    """
    
    def __init__(self, executor_id: str = None, config: Dict[str, Any] = None):
        super().__init__(
            executor_id=executor_id,
            name="ComposerExecutor",
            description="Composes final reports from summarized content",
            capabilities=[ExecutorCapability.GENERIC, ExecutorCapability.CUSTOM],
            max_concurrent_tasks=1,
            config=config
        )
    
    async def execute_task(self, task: Task) -> Any:
        """Execute a composition task."""
        logger = get_logger(f"{self.name}.{self.executor_id}")
        
        await logger.info(f"Starting composition task: {task.task_id}",
                         task_id=task.task_id, executor_id=self.executor_id)
        
        start_time = time.time()
        
        try:
            # Extract composition parameters
            summary_data = task.parameters.get("summary_data", {})
            report_format = task.parameters.get("format", "markdown")
            include_metadata = task.parameters.get("include_metadata", True)
            
            if not summary_data:
                raise ValueError("No summary data provided for composition")
                
            await logger.debug(f"Composing {report_format} report",
                              task_id=task.task_id,
                              format=report_format,
                              include_metadata=include_metadata)
            
            # Simulate composition time
            await asyncio.sleep(0.5)
            
            # Create formatted report
            if report_format == "json":
                report = self._create_json_report(summary_data, include_metadata)
            elif report_format == "html":
                report = self._create_html_report(summary_data, include_metadata)
            else:  # markdown (default)
                report = self._create_markdown_report(summary_data, include_metadata)
            
            execution_time = time.time() - start_time
            
            await logger.info(f"Composition completed: {len(report)} characters",
                             task_id=task.task_id,
                             report_length=len(report),
                             execution_time=execution_time,
                             format=report_format)
            
            return {
                "report": report,
                "format": report_format,
                "character_count": len(report),
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "query": summary_data.get("query", ""),
                    "source_count": summary_data.get("source_count", 0),
                    "summary_type": summary_data.get("summary_type", "")
                }
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            await logger.error(f"Composition failed: {str(e)}",
                              exception=e, task_id=task.task_id, execution_time=execution_time)
            raise
    
    def _create_markdown_report(self, summary_data: Dict, include_metadata: bool) -> str:
        """Create a markdown formatted report."""
        query = summary_data.get("query", "Unknown Topic")
        summary = summary_data.get("summary", "No summary available")
        
        report = f"# Research Report: {query}\n\n"
        report += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        if include_metadata:
            report += "## Metadata\n\n"
            report += f"- **Query:** {query}\n"
            report += f"- **Sources:** {summary_data.get('source_count', 0)}\n"
            report += f"- **Summary Type:** {summary_data.get('summary_type', 'N/A')}\n"
            report += f"- **Processing Time:** {summary_data.get('execution_time', 0):.2f}s\n\n"
        
        report += "## Summary\n\n"
        report += summary + "\n\n"
        report += "---\n"
        report += "*This report was generated automatically by the Workflown framework.*\n"
        
        return report
    
    def _create_html_report(self, summary_data: Dict, include_metadata: bool) -> str:
        """Create an HTML formatted report."""
        query = summary_data.get("query", "Unknown Topic")
        summary = summary_data.get("summary", "No summary available")
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Research Report: {query}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        .metadata {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .summary {{ line-height: 1.6; }}
        .footer {{ margin-top: 30px; font-style: italic; color: #666; }}
    </style>
</head>
<body>
    <h1>Research Report: {query}</h1>
    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
"""
        
        if include_metadata:
            html += f"""
    <div class="metadata">
        <h2>Metadata</h2>
        <ul>
            <li><strong>Query:</strong> {query}</li>
            <li><strong>Sources:</strong> {summary_data.get('source_count', 0)}</li>
            <li><strong>Summary Type:</strong> {summary_data.get('summary_type', 'N/A')}</li>
            <li><strong>Processing Time:</strong> {summary_data.get('execution_time', 0):.2f}s</li>
        </ul>
    </div>
"""
        
        html += f"""
    <h2>Summary</h2>
    <div class="summary">
        <p>{summary.replace(chr(10), '<br>')}</p>
    </div>
    
    <div class="footer">
        <p>This report was generated automatically by the Workflown framework.</p>
    </div>
</body>
</html>"""
        
        return html
    
    def _create_json_report(self, summary_data: Dict, include_metadata: bool) -> str:
        """Create a JSON formatted report."""
        report_data = {
            "title": f"Research Report: {summary_data.get('query', 'Unknown Topic')}",
            "generated": datetime.now().isoformat(),
            "summary": summary_data.get("summary", "No summary available")
        }
        
        if include_metadata:
            report_data["metadata"] = {
                "query": summary_data.get("query", ""),
                "source_count": summary_data.get("source_count", 0),
                "summary_type": summary_data.get("summary_type", ""),
                "execution_time": summary_data.get("execution_time", 0),
                "character_count": summary_data.get("character_count", 0)
            }
        
        report_data["generator"] = "Workflown Framework"
        
        return json.dumps(report_data, indent=2)
    
    def can_handle_task(self, task: Task) -> bool:
        """Check if this executor can handle the task."""
        return task.task_type == "compose"
    
    def get_supported_task_types(self) -> List[str]:
        """Get supported task types."""
        return ["compose"]


class WebResearchWorkflow(BaseWorkflow):
    """
    Complete web research workflow that demonstrates:
    1. Planning phase - breaking down the research request
    2. Execution phase - web search, summarization, composition
    3. Logging and monitoring throughout
    """
    
    def __init__(self, workflow_id: str = None, config: Dict[str, Any] = None):
        super().__init__(workflow_id, config)
        self.logger = get_logger(f"WebResearchWorkflow.{self.workflow_id}")
        
        # Initialize components
        self.storage = None
        self.event_bus = None
        self.planner = None
        self.dispatcher = None
        self.executor_registry = None
        
    async def setup(self):
        """Set up the workflow components."""
        await self.logger.info("Setting up web research workflow", workflow_id=self.workflow_id)
        
        # Initialize storage
        self.storage = FilesystemStorage(config={"base_path": "./examples/data"})
        await self.storage.connect()
        await self.logger.debug("Storage initialized", storage_type="filesystem")
        
        # Initialize event bus
        self.event_bus = EventBus()
        await self.event_bus.start()
        await self.logger.debug("Event bus started")
        
        # Initialize executor registry and add specialized executors
        self.executor_registry = ExecutorRegistry()
        
        # Register our specialized executors
        web_search_executor = WebSearchExecutor("web-search-1")
        summarizer_executor = SummarizerExecutor("summarizer-1")
        composer_executor = ComposerExecutor("composer-1")
        
        await web_search_executor.start()
        await summarizer_executor.start()
        await composer_executor.start()
        
        self.executor_registry.register_executor(web_search_executor)
        self.executor_registry.register_executor(summarizer_executor)
        self.executor_registry.register_executor(composer_executor)
        
        await self.logger.info("Registered specialized executors",
                              executor_count=len(self.executor_registry.get_all_executors()))
        
        # Initialize planner and dispatcher
        self.planner = SimplePlanner(config={"optimize_assignments": True})
        self.dispatcher = TaskDispatcher(self.executor_registry, config={"optimize_assignments": True})
        
        await self.logger.info("Workflow setup complete", workflow_id=self.workflow_id)
    
    async def execute(self, context: Dict[str, Any]) -> WorkflowResult:
        """Execute the web research workflow."""
        start_time = time.time()
        self.state = WorkflowState.RUNNING
        self.started_at = datetime.now()
        
        await self.logger.workflow_started(self.workflow_id, "web_research", **context)
        
        # Publish workflow started event
        if self.event_bus:
            event = create_workflow_started_event(self.workflow_id, "web_research")
            await self.event_bus.publish(event)
        
        try:
            # Phase 1: Planning
            await self.logger.info("=== PHASE 1: PLANNING ===", workflow_id=self.workflow_id)
            planning_result = await self._planning_phase(context)
            
            # Phase 2: Task Dispatch
            await self.logger.info("=== PHASE 2: TASK DISPATCH ===", workflow_id=self.workflow_id)
            dispatch_result = await self._dispatch_phase(planning_result, context)
            
            # Phase 3: Task Execution
            await self.logger.info("=== PHASE 3: TASK EXECUTION ===", workflow_id=self.workflow_id)
            execution_results = await self._execution_phase(dispatch_result)
            
            # Phase 4: Result Composition
            await self.logger.info("=== PHASE 4: RESULT COMPOSITION ===", workflow_id=self.workflow_id)
            final_result = await self._composition_phase(execution_results, context)
            
            # Complete workflow
            self.state = WorkflowState.COMPLETED
            self.completed_at = datetime.now()
            execution_time = time.time() - start_time
            
            await self.logger.workflow_completed(self.workflow_id, execution_time, True)
            
            # Store workflow result
            if self.storage:
                workflow_data = {
                    "workflow_id": self.workflow_id,
                    "state": self.state.value,
                    "execution_time": execution_time,
                    "final_result": final_result,
                    "context": context,
                    "completed_at": self.completed_at.isoformat()
                }
                await self.storage.store_workflow(self.workflow_id, workflow_data)
                await self.logger.debug("Workflow result stored", workflow_id=self.workflow_id)
            
            return WorkflowResult(
                workflow_id=self.workflow_id,
                success=True,
                result=final_result,
                metadata={
                    "execution_time": execution_time,
                    "task_count": len(planning_result.tasks) if planning_result else 0,
                    "context": context
                },
                execution_time=execution_time,
                timestamp=self.completed_at
            )
            
        except Exception as e:
            # Handle workflow failure
            self.state = WorkflowState.FAILED
            self.completed_at = datetime.now()
            execution_time = time.time() - start_time
            
            await self.logger.workflow_completed(self.workflow_id, execution_time, False)
            await self.logger.error("Workflow execution failed", exception=e, workflow_id=self.workflow_id)
            
            return WorkflowResult(
                workflow_id=self.workflow_id,
                success=False,
                result=None,
                metadata={"error": str(e), "execution_time": execution_time},
                execution_time=execution_time,
                timestamp=self.completed_at,
                errors=[str(e)]
            )
    
    async def _planning_phase(self, context: Dict[str, Any]):
        """Phase 1: Create execution plan."""
        await self.logger.info("Creating execution plan", workflow_id=self.workflow_id)
        
        # Extract research requirements
        query = context.get("query", "artificial intelligence")
        max_results = context.get("max_results", 5)
        summary_type = context.get("summary_type", "comprehensive")
        output_format = context.get("output_format", "markdown")
        
        await self.logger.debug("Planning parameters extracted",
                               query=query, max_results=max_results, 
                               summary_type=summary_type, output_format=output_format)
        
        # Define workflow requirements for the planner
        requirements = {
            "name": "Web Research Workflow",
            "description": f"Research '{query}' and create a {summary_type} summary",
            "tasks": [
                {
                    "name": "Web Search",
                    "task_type": "web_search",
                    "description": f"Search the web for information about '{query}'",
                    "parameters": {
                        "query": query,
                        "max_results": max_results
                    },
                    "priority": 3,
                    "estimated_duration": 120.0
                },
                {
                    "name": "Summarize Results",
                    "task_type": "summarize", 
                    "description": f"Create a {summary_type} summary of search results",
                    "parameters": {
                        "summary_type": summary_type,
                        "max_length": 1000
                    },
                    "dependencies": ["web_search_task"],  # Will be updated with actual task IDs
                    "priority": 2,
                    "estimated_duration": 90.0
                },
                {
                    "name": "Compose Report",
                    "task_type": "compose",
                    "description": f"Create final {output_format} report",
                    "parameters": {
                        "format": output_format,
                        "include_metadata": True
                    },
                    "dependencies": ["summarize_task"],  # Will be updated with actual task IDs
                    "priority": 1,
                    "estimated_duration": 60.0
                }
            ]
        }
        
        # Create plan using the planner
        planning_result = await self.planner.create_plan(
            workflow_id=self.workflow_id,
            requirements=requirements,
            constraints={"max_time": 600}  # 10 minute timeout
        )
        
        await self.logger.info("Planning completed",
                              workflow_id=self.workflow_id,
                              task_count=len(planning_result.tasks),
                              estimated_time=planning_result.estimated_total_time,
                              confidence=planning_result.confidence,
                              strategy=planning_result.strategy.value)
        
        # Log detailed task information
        for i, task in enumerate(planning_result.tasks, 1):
            await self.logger.debug(f"Task {i} planned: {task.name}",
                                   task_id=task.task_id,
                                   task_type=task.task_type,
                                   estimated_duration=task.estimated_duration,
                                   dependencies=task.dependencies,
                                   priority=task.priority)
        
        if planning_result.warnings:
            for warning in planning_result.warnings:
                await self.logger.warning(f"Planning warning: {warning}", workflow_id=self.workflow_id)
        
        return planning_result
    
    async def _dispatch_phase(self, planning_result, context: Dict[str, Any]):
        """Phase 2: Dispatch tasks to executors."""
        await self.logger.info("Dispatching tasks to executors", workflow_id=self.workflow_id)
        
        # Create dispatch context
        dispatch_context = DispatchContext(
            session_id=self.workflow_id,
            deadline=datetime.now() + timedelta(minutes=10),
            quality_requirements={"min_confidence": 0.7},
            environment=context
        )
        
        # Dispatch tasks
        dispatch_result = await self.dispatcher.dispatch(planning_result, dispatch_context)
        
        await self.logger.info("Task dispatch completed",
                              workflow_id=self.workflow_id,
                              assigned_tasks=len(dispatch_result.assignments),
                              unassigned_tasks=len(dispatch_result.unassigned_tasks),
                              strategy=dispatch_result.dispatch_strategy.value,
                              confidence=dispatch_result.confidence,
                              estimated_time=dispatch_result.total_estimated_time)
        
        # Log assignment details
        for assignment in dispatch_result.assignments:
            await self.logger.debug("Task assigned",
                                   task_id=assignment.task_id,
                                   executor_id=assignment.executor_id,
                                   confidence=assignment.confidence,
                                   estimated_completion=assignment.estimated_completion.isoformat())
        
        if dispatch_result.unassigned_tasks:
            await self.logger.warning(f"Unassigned tasks: {dispatch_result.unassigned_tasks}",
                                     workflow_id=self.workflow_id)
        
        if dispatch_result.warnings:
            for warning in dispatch_result.warnings:
                await self.logger.warning(f"Dispatch warning: {warning}", workflow_id=self.workflow_id)
        
        return dispatch_result
    
    async def _execution_phase(self, dispatch_result):
        """Phase 3: Execute tasks in dependency order."""
        await self.logger.info("Starting task execution phase", workflow_id=self.workflow_id)
        
        execution_results = {}
        task_map = {assignment.task_id: assignment for assignment in dispatch_result.assignments}
        
        # For this example, we'll execute tasks sequentially based on dependencies
        # In a real implementation, this would handle parallel execution
        
        for assignment in dispatch_result.assignments:
            executor = self.executor_registry.get_executor(assignment.executor_id)
            if not executor:
                await self.logger.error(f"Executor not found: {assignment.executor_id}",
                                       task_id=assignment.task_id)
                continue
            
            # Create task object (in a real implementation, this would come from the planner)
            task = Task(
                task_id=assignment.task_id,
                name=f"Task-{assignment.task_id}",
                task_type=assignment.metadata.get("task_type", "generic"),
                parameters=self._build_task_parameters(assignment, execution_results)
            )
            
            # Execute task
            await self.logger.task_started(task.task_id, task.task_type, executor_id=assignment.executor_id)
            
            if self.event_bus:
                event = create_task_started_event(task.task_id, task.task_type, assignment.executor_id)
                await self.event_bus.publish(event)
            
            try:
                start_time = time.time()
                result = await executor.execute_task(task)
                execution_time = time.time() - start_time
                
                execution_results[task.task_id] = result
                
                await self.logger.task_completed(task.task_id, execution_time, True, 
                                                result_summary=str(result)[:100])
                
                if self.event_bus:
                    event = create_task_completed_event(task.task_id, execution_time, True, str(result)[:100])
                    await self.event_bus.publish(event)
                
                # Store task result
                if self.storage:
                    await self.storage.store_execution_result(task.task_id, {
                        "task_id": task.task_id,
                        "success": True,
                        "result": result,
                        "execution_time": execution_time,
                        "executor_id": assignment.executor_id,
                        "timestamp": datetime.now().isoformat()
                    })
                
            except Exception as e:
                execution_time = time.time() - start_time
                await self.logger.task_completed(task.task_id, execution_time, False)
                await self.logger.error(f"Task execution failed: {task.task_id}", exception=e)
                
                if self.event_bus:
                    event = create_task_completed_event(task.task_id, execution_time, False, str(e))
                    await self.event_bus.publish(event)
        
        await self.logger.info("Task execution phase completed",
                              workflow_id=self.workflow_id,
                              completed_tasks=len(execution_results))
        
        return execution_results
    
    def _build_task_parameters(self, assignment, execution_results: Dict[str, Any]) -> Dict[str, Any]:
        """Build task parameters based on assignment and previous results."""
        task_type = assignment.metadata.get("task_type", "generic")
        
        if task_type == "web_search":
            # First task - use original parameters from assignment metadata
            return assignment.metadata.get("parameters", {})
        
        elif task_type == "summarize":
            # Second task - needs results from web search
            search_results = None
            for task_id, result in execution_results.items():
                if isinstance(result, dict) and "query" in result and "results" in result:
                    search_results = result
                    break
            
            params = assignment.metadata.get("parameters", {})
            params["search_results"] = search_results
            return params
        
        elif task_type == "compose":
            # Third task - needs results from summarization
            summary_data = None
            for task_id, result in execution_results.items():
                if isinstance(result, dict) and "summary" in result:
                    summary_data = result
                    break
            
            params = assignment.metadata.get("parameters", {})
            params["summary_data"] = summary_data
            return params
        
        else:
            return assignment.metadata.get("parameters", {})
    
    async def _composition_phase(self, execution_results: Dict[str, Any], context: Dict[str, Any]):
        """Phase 4: Compose final workflow result."""
        await self.logger.info("Composing final workflow result", workflow_id=self.workflow_id)
        
        # Extract results from each phase
        search_result = None
        summary_result = None
        composition_result = None
        
        for task_id, result in execution_results.items():
            if isinstance(result, dict):
                if "query" in result and "results" in result:
                    search_result = result
                elif "summary" in result:
                    summary_result = result
                elif "report" in result:
                    composition_result = result
        
        # Compose final result
        final_result = {
            "workflow_id": self.workflow_id,
            "query": context.get("query", "unknown"),
            "execution_summary": {
                "total_tasks": len(execution_results),
                "search_results_found": search_result.get("total_results", 0) if search_result else 0,
                "summary_length": summary_result.get("character_count", 0) if summary_result else 0,
                "final_report_length": composition_result.get("character_count", 0) if composition_result else 0
            },
            "results": {
                "search": search_result,
                "summary": summary_result,
                "composition": composition_result
            },
            "metadata": {
                "completed_at": datetime.now().isoformat(),
                "context": context
            }
        }
        
        # If we have a final report, make it easily accessible
        if composition_result and "report" in composition_result:
            final_result["final_report"] = composition_result["report"]
            final_result["report_format"] = composition_result.get("format", "unknown")
        
        await self.logger.info("Final workflow result composed",
                              workflow_id=self.workflow_id,
                              search_results=final_result["execution_summary"]["search_results_found"],
                              summary_length=final_result["execution_summary"]["summary_length"],
                              report_length=final_result["execution_summary"]["final_report_length"])
        
        return final_result
    
    async def pause(self) -> bool:
        """Pause workflow execution."""
        self.state = WorkflowState.PAUSED
        await self.logger.info("Workflow paused", workflow_id=self.workflow_id)
        return True
    
    async def resume(self) -> bool:
        """Resume workflow execution."""
        self.state = WorkflowState.RUNNING
        await self.logger.info("Workflow resumed", workflow_id=self.workflow_id)
        return True
    
    async def cancel(self) -> bool:
        """Cancel workflow execution."""
        self.state = WorkflowState.CANCELLED
        await self.logger.info("Workflow cancelled", workflow_id=self.workflow_id)
        return True
    
    async def cleanup(self):
        """Clean up workflow resources."""
        await self.logger.info("Cleaning up workflow resources", workflow_id=self.workflow_id)
        
        if self.event_bus:
            await self.event_bus.stop()
        
        if self.storage:
            await self.storage.disconnect()
        
        if self.executor_registry:
            await self.executor_registry.stop_all_executors()


async def setup_logging():
    """Set up comprehensive logging for the example using central configuration."""
    from workflown.core.logging.config import setup_logging_from_config
    
    # Use centralized logging configuration
    logger = await setup_logging_from_config("workflown")
    
    # Log the configuration being used
    from workflown.core.logging.config import get_logging_summary
    logging_summary = get_logging_summary()
    
    await logger.info("Logging configured from central config", 
                     config_summary=logging_summary)
    
    return logger


async def main():
    """
    Main example function that demonstrates the complete workflow.
    """
    print("🚀 Starting Web Research Workflow Example")
    print("=" * 60)
    
    # Set up logging
    logger = await setup_logging()
    await logger.info("=== WORKFLOWN WEB RESEARCH EXAMPLE STARTED ===")
    
    try:
        # Create workflow instance
        workflow = WebResearchWorkflow(
            workflow_id="web-research-example-001",
            config={"timeout": 600}
        )
        
        # Set up workflow components
        await workflow.setup()
        
        # Define research context
        research_context = {
            "query": "artificial intelligence machine learning",
            "max_results": 3,
            "summary_type": "comprehensive",
            "output_format": "markdown",
            "user_id": "example_user",
            "session_id": "demo_session_001"
        }
        
        await logger.info("Starting workflow execution", **research_context)
        
        # Execute workflow
        result = await workflow.execute(research_context)
        
        # Display results
        print("\n" + "=" * 60)
        print("🎉 WORKFLOW EXECUTION COMPLETED")
        print("=" * 60)
        
        if result.success:
            print(f"✅ Workflow completed successfully in {result.execution_time:.2f} seconds")
            print(f"📊 Tasks executed: {result.metadata.get('task_count', 0)}")
            
            if "final_report" in result.result:
                print("\n📄 FINAL REPORT:")
                print("-" * 40)
                print(result.result["final_report"][:500] + "..." if len(result.result["final_report"]) > 500 else result.result["final_report"])
            
            print(f"\n📈 EXECUTION SUMMARY:")
            summary = result.result.get("execution_summary", {})
            print(f"   • Search Results Found: {summary.get('search_results_found', 0)}")
            print(f"   • Summary Length: {summary.get('summary_length', 0)} characters")
            print(f"   • Final Report Length: {summary.get('final_report_length', 0)} characters")
            
        else:
            print(f"❌ Workflow failed: {result.errors}")
        
        # Clean up
        await workflow.cleanup()
        
        print(f"\n📋 Check logs in ./examples/logs/ for detailed execution traces")
        
        await logger.info("=== WORKFLOWN EXAMPLE COMPLETED ===", 
                         success=result.success, 
                         execution_time=result.execution_time)
    
    except Exception as e:
        await logger.error("Example execution failed", exception=e)
        print(f"\n❌ Example failed: {str(e)}")
        raise


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())