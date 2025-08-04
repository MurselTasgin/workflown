# Workflown

A modular workflow execution framework with pluggable components, event-driven architecture, and distributed execution capabilities.

## Features

- **Modular Architecture**: Pluggable components for executors, storage, and event handling
- **Event-Driven**: Asynchronous event bus for communication between components
- **Distributed Execution**: Support for distributed task execution across multiple executors
- **Flexible Configuration**: Centralized configuration management
- **Extensible**: Easy to add new executors, storage backends, and event handlers
- **Resilient**: Built-in error handling, circuit breakers, and graceful degradation
- **Observable**: Comprehensive logging and metrics collection

## Installation

### From Source

```bash
git clone https://github.com/workflown/workflown.git
cd workflown
pip install -e .
```

### Development Installation

```bash
pip install -e ".[dev]"
```

### With Examples

```bash
pip install -e ".[examples]"
```

## Quick Start

```python
import asyncio
from workflown import BaseWorkflow, Task, ExecutorRegistry

class SimpleWorkflow(BaseWorkflow):
    async def setup(self):
        # Initialize your workflow
        pass
    
    async def execute(self):
        # Define your workflow logic
        task = Task(
            task_id="example_task",
            task_type="python",
            parameters={"code": "print('Hello, Workflown!')"}
        )
        
        # Execute the task
        registry = ExecutorRegistry()
        executor = registry.get_executor("python")
        result = await executor.execute_task(task)
        
        return result

# Run the workflow
async def main():
    workflow = SimpleWorkflow()
    result = await workflow.run()
    print(f"Workflow completed: {result.success}")

asyncio.run(main())
```

## CLI Usage

```bash
# Run a workflow
workflown run examples/web_research_workflow.py

# List available executors
workflown list-executors

# List available workflows
workflown list

# Get help
workflown --help
```

## Architecture

### Core Components

- **Workflows**: Define the execution logic and task dependencies
- **Executors**: Handle task execution with different capabilities
- **Dispatchers**: Assign tasks to appropriate executors
- **Planners**: Create execution plans from workflow definitions
- **Storage**: Persist workflow state and results
- **Events**: Enable communication between components

### Component Hierarchy

```
BaseWorkflow
├── BaseExecutor
│   ├── TaskExecutor
│   ├── WebSearchExecutor
│   └── CustomExecutor
├── BaseDispatcher
│   └── TaskDispatcher
├── BasePlanner
│   └── SimplePlanner
├── BaseStorage
│   ├── FileSystemStorage
│   └── SQLiteStorage
└── EventBus
    ├── EventListener
    └── EventHandler
```

## Configuration

Workflown uses a centralized configuration system. Create a `.env` file or use environment variables:

```bash
# Core settings
WORKFLOWN_LOG_LEVEL=INFO
WORKFLOWN_MAX_CONCURRENT_TASKS=10
WORKFLOWN_TIMEOUT=300

# Executor settings
WORKFLOWN_ALLOW_SHELL=false
WORKFLOWN_PYTHON_TIMEOUT=30
WORKFLOWN_SHELL_TIMEOUT=60

# Storage settings
WORKFLOWN_STORAGE_TYPE=filesystem
WORKFLOWN_STORAGE_PATH=./data
```

## Examples

### Web Research Workflow

The included example demonstrates a web research workflow that:

1. Searches for information on a given topic
2. Summarizes the findings
3. Generates a comprehensive report

```bash
cd examples
python web_research_workflow.py
```

### Custom Executor

```python
from workflown import BaseExecutor, ExecutorCapability

class CustomExecutor(BaseExecutor):
    def __init__(self):
        super().__init__(
            executor_id="custom",
            name="Custom Executor",
            description="A custom task executor",
            capabilities=[ExecutorCapability.GENERIC]
        )
    
    async def execute_task(self, task):
        # Your custom execution logic
        return TaskResult(
            task_id=task.task_id,
            success=True,
            result="Custom execution completed"
        )
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black workflown/
isort workflown/
```

### Type Checking

```bash
mypy workflown/
```

### Linting

```bash
flake8 workflown/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [https://workflown.readthedocs.io/](https://workflown.readthedocs.io/)
- **Issues**: [https://github.com/workflown/workflown/issues](https://github.com/workflown/workflown/issues)
- **Discussions**: [https://github.com/workflown/workflown/discussions](https://github.com/workflown/workflown/discussions)
