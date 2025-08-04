# Workflown Framework Examples

This directory contains comprehensive examples demonstrating the Workflown workflow execution framework.

## Web Research Workflow Example

The **Web Research Workflow** (`web_research_workflow.py`) demonstrates a complete end-to-end workflow that:

1. **Searches the web** for information on a given topic
2. **Summarizes** the search results using different strategies  
3. **Composes** a final report in multiple formats (Markdown, HTML, JSON)

### Key Features Demonstrated

✅ **Complete Workflow Lifecycle**
- Planning phase with task dependency management
- Task dispatching to specialized executors
- Parallel/sequential task execution
- Result composition and storage

✅ **Comprehensive Logging & Debugging**
- Structured logging with correlation IDs
- Multiple log handlers (console, file, structured JSON)
- Performance metrics and execution tracing
- Color-coded console output

✅ **Specialized Executors**
- `WebSearchExecutor` - Mock web search with realistic results
- `SummarizerExecutor` - Text summarization with different strategies
- `ComposerExecutor` - Report composition in multiple formats

✅ **Event-Driven Architecture**
- Event bus for component communication
- Workflow and task lifecycle events
- Real-time status updates

✅ **Persistent Storage**
- File-based storage for workflow state
- Task result persistence
- Automatic cleanup and organization

✅ **Error Handling & Recovery**
- Comprehensive exception handling
- Graceful failure modes
- Resource cleanup

## Running the Examples

### Basic Example

```bash
cd examples
python run_example.py
```

This runs the web research workflow with default parameters:
- **Query**: "artificial intelligence machine learning"
- **Results**: 3 search results
- **Summary**: Comprehensive
- **Format**: Markdown

### Custom Example

```bash
cd examples  
python run_example.py custom
```

This runs a customized version with:
- **Query**: "machine learning applications in healthcare"
- **Results**: 2 search results  
- **Summary**: Brief
- **Format**: HTML (saved to file)

### Direct Execution

```bash
cd examples
python web_research_workflow.py
```

## Example Output

### Console Output
```
🚀 Starting Web Research Workflow Example
============================================================
2024-01-15 10:30:15 [    INFO] workflown: === WORKFLOWN WEB RESEARCH EXAMPLE STARTED ===
2024-01-15 10:30:15 [    INFO] WebResearchWorkflow.web-research-example-001: Setting up web research workflow
2024-01-15 10:30:15 [   DEBUG] WebResearchWorkflow.web-research-example-001: Storage initialized
2024-01-15 10:30:15 [   DEBUG] WebResearchWorkflow.web-research-example-001: Event bus started
2024-01-15 10:30:15 [    INFO] WebResearchWorkflow.web-research-example-001: Registered specialized executors
2024-01-15 10:30:15 [    INFO] WebResearchWorkflow.web-research-example-001: Workflow setup complete
2024-01-15 10:30:15 [    INFO] WebResearchWorkflow.web-research-example-001: Workflow started: web-research-example-001
2024-01-15 10:30:15 [    INFO] WebResearchWorkflow.web-research-example-001: === PHASE 1: PLANNING ===
...
```

### Final Report Sample
```markdown
# Research Report: artificial intelligence machine learning

**Generated:** 2024-01-15 10:32:45

## Metadata

- **Query:** artificial intelligence machine learning
- **Sources:** 3
- **Summary Type:** comprehensive
- **Processing Time:** 1.50s

## Summary

Comprehensive research report on 'artificial intelligence machine learning':

Based on analysis of 3 sources, here are the key findings:

1. What is Artificial Intelligence? - IBM
   Artificial intelligence leverages computers and machines to mimic the problem-solving and decision-making capabilities of the human mind.
   Source: https://www.ibm.com/cloud/learn/what-is-artificial-intelligence
   Relevance: 0.95
...
```

## File Structure After Running

```
examples/
├── data/                          # Workflow data storage
│   ├── workflows/                 # Workflow state files
│   ├── tasks/                     # Task data
│   ├── results/                   # Execution results
│   └── temp/                      # Temporary files
├── logs/                          # Comprehensive logging
│   ├── workflown-example.log      # Standard text logs
│   ├── workflown-structured.log   # JSON structured logs
│   └── workflown-example.log.1    # Rotated log files
├── web_research_workflow.py       # Main example implementation
├── run_example.py                 # Simple runner script
└── README.md                      # This file
```

## Code Architecture Highlights

### Workflow Definition
```python
class WebResearchWorkflow(BaseWorkflow):
    async def execute(self, context: Dict[str, Any]) -> WorkflowResult:
        # Phase 1: Planning
        planning_result = await self._planning_phase(context)
        
        # Phase 2: Task Dispatch  
        dispatch_result = await self._dispatch_phase(planning_result, context)
        
        # Phase 3: Task Execution
        execution_results = await self._execution_phase(dispatch_result)
        
        # Phase 4: Result Composition
        final_result = await self._composition_phase(execution_results, context)
```

### Specialized Executors
```python
class WebSearchExecutor(BaseExecutor):
    async def execute_task(self, task: Task) -> Any:
        # Mock web search implementation
        query = task.parameters.get("query", "")
        results = await self._perform_search(query)
        return {"query": query, "results": results}

class SummarizerExecutor(BaseExecutor):
    async def execute_task(self, task: Task) -> Any:
        # Text summarization implementation
        search_results = task.parameters.get("search_results", {})
        summary = await self._create_summary(search_results)
        return {"summary": summary}
```

### Comprehensive Logging
```python
# Workflow-level logging
await self.logger.workflow_started(self.workflow_id, "web_research")

# Task-level logging  
await self.logger.task_started(task.task_id, task.task_type, executor_id=executor_id)
await self.logger.task_completed(task.task_id, execution_time, success)

# Performance metrics
await self.logger.performance_metric("search_results_found", len(results))

# Structured context logging
await logger.info("Planning completed", 
                  task_count=len(tasks), 
                  estimated_time=total_time,
                  confidence=confidence)
```

## Learning Outcomes

This example demonstrates:

1. **Framework Architecture** - How components work together
2. **Task Orchestration** - Planning, dispatching, and execution
3. **Extensibility** - Creating custom executors for specific needs
4. **Observability** - Comprehensive logging and monitoring
5. **Error Handling** - Graceful failure and recovery
6. **State Management** - Persistent storage and workflow state
7. **Event-Driven Design** - Loose coupling through events

## Next Steps

- Examine the log files to understand execution flow
- Modify the example to add new task types
- Create your own specialized executors
- Experiment with different workflow patterns
- Add monitoring and alerting capabilities

The example serves as a foundation for building production workflows in any domain!