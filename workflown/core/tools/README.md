# Workflown Tools System

The tools system provides a generic, extensible framework for managing and executing tools in workflows.

## Overview

The tools system consists of three main components:

1. **BaseTool** - Abstract base class for all tools
2. **ToolRegistry** - Central registry for tool discovery and management
3. **ToolMapper** - Intelligent mapping between tasks and tools

## Architecture

### BaseTool

All tools inherit from `BaseTool` and implement:

- `execute()` - Main execution method
- `get_supported_operations()` - List of supported operations
- `get_capabilities()` - Tool capabilities

### ToolRegistry

Manages tool registration and discovery:

- Register tools with metadata
- Find tools by task type, capability, or keyword
- Create tool instances
- Track tool statistics

### ToolMapper

Intelligent task-to-tool mapping using multiple strategies:

1. **Exact Match** - Direct task type matching
2. **Capability Match** - Match by tool capabilities
3. **Keyword Match** - Match by task description keywords
4. **Fallback** - Use generic tools

## Usage

### Creating a Custom Tool

```python
from workflown.core.tools.base_tool import BaseTool, ToolResult, ToolCapability

class MyCustomTool(BaseTool):
    def __init__(self, tool_id: str = None, config: Dict[str, Any] = None):
        super().__init__(
            tool_id=tool_id,
            name="MyCustomTool",
            description="My custom tool",
            capabilities=[ToolCapability.CUSTOM],
            config=config or {}
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        # Your tool logic here
        result = {"processed": parameters}
        
        return ToolResult(
            tool_id=self.tool_id,
            success=True,
            result=result
        )
    
    def get_supported_operations(self) -> List[str]:
        return ["my_operation"]
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def get_author(self) -> str:
        return "Your Name"
    
    def get_tags(self) -> List[str]:
        return ["custom", "processing"]
    
    def _get_required_parameters(self) -> List[str]:
        return ["input_data"]
    
    def _get_optional_parameters(self) -> List[str]:
        return ["max_results", "timeout"]
    
    def _get_parameter_descriptions(self) -> Dict[str, str]:
        return {
            "input_data": "Data to process",
            "max_results": "Maximum number of results",
            "timeout": "Execution timeout in seconds"
        }
    
    def _get_parameter_types(self) -> Dict[str, str]:
        return {
            "input_data": "string",
            "max_results": "integer",
            "timeout": "float"
        }
```

### Registering Tools

```python
from workflown.core.tools.tool_registry import ToolRegistry

registry = ToolRegistry()

# Register with automatic metadata extraction
tool_id = registry.register_tool_class(
    tool_class=MyCustomTool,
    config={"default_config": "value"}
)

# Or register with custom metadata (optional)
metadata = {
    "name": "My Tool",
    "description": "A custom tool",
    "task_types": ["my_task_type"],
    "capabilities": [ToolCapability.CUSTOM],
    "keywords": ["custom", "processing"]
}

tool_id = registry.register_tool_with_metadata(
    tool_class=MyCustomTool,
    metadata=metadata,  # Optional - will be extracted from tool if not provided
    config={"default_config": "value"}
)
```

### Mapping Tasks to Tools

```python
from workflown.core.tools.tool_mapper import ToolMapper

mapper = ToolMapper(registry)

mapping = mapper.map_task_to_tool(
    task_id="task_1",
    task_type="my_task_type",
    task_description="Process some data",
    task_parameters={"data": "example"}
)

if mapping:
    print(f"Mapped to tool: {mapping.selected_tool_id}")
    print(f"Confidence: {mapping.confidence}")
```

### Creating and Executing Tool Instances

```python
# Create tool instance
tool_instance = registry.create_tool_instance(
    tool_id=tool_id,
    instance_id="my_instance",
    config={"instance_config": "value"}
)

# Execute tool
result = await tool_instance.execute_with_tracking({
    "input_data": "example"
})

if result.success:
    print(f"Result: {result.result}")
else:
    print(f"Error: {result.errors}")
```

## Tool Capabilities

The system defines standard tool capabilities:

- `WEB_SEARCH` - Web search capabilities
- `TEXT_GENERATION` - Text generation
- `TEXT_SUMMARIZATION` - Text summarization
- `DATA_PROCESSING` - Data processing
- `FILE_OPERATIONS` - File operations
- `HTTP_REQUESTS` - HTTP requests
- `DATABASE_OPERATIONS` - Database operations
- `IMAGE_PROCESSING` - Image processing
- `AUDIO_PROCESSING` - Audio processing
- `VIDEO_PROCESSING` - Video processing
- `MACHINE_LEARNING` - Machine learning
- `CUSTOM` - Custom capabilities

## Configuration

Tools can be configured through:

1. **Default Configuration** - Set during registration
2. **Instance Configuration** - Set when creating instances
3. **Runtime Parameters** - Passed during execution

## Error Handling

The system provides comprehensive error handling:

- Tool capacity limits
- Execution timeouts
- Error tracking and reporting
- Graceful degradation

## Monitoring and Statistics

The system provides:

- Tool execution statistics
- Mapping success rates
- Performance metrics
- Registry statistics

## Best Practices

1. **Tool Design**
   - Keep tools focused on single responsibility
   - Use appropriate capabilities
   - Provide meaningful metadata

2. **Registration**
   - Register tools with comprehensive metadata
   - Use descriptive task types and keywords
   - Set appropriate default configurations

3. **Mapping**
   - Use specific task types for exact matching
   - Provide detailed task descriptions for keyword matching
   - Monitor mapping confidence scores

4. **Execution**
   - Handle errors gracefully
   - Implement proper cleanup
   - Monitor performance metrics 

## Tool Metadata Methods

The `BaseTool` class provides several methods for automatic metadata extraction:

### Required Methods

- `get_supported_operations()` - List of supported operation types
- `execute()` - Main execution method

### Optional Metadata Methods

- `get_version()` - Tool version (default: "1.0.0")
- `get_author()` - Tool author (default: "Unknown")
- `get_tags()` - Tool tags for categorization (default: [])
- `get_description()` - Detailed tool description

### Parameter Schema Methods

- `_get_required_parameters()` - List of required parameter names
- `_get_optional_parameters()` - List of optional parameter names
- `_get_parameter_descriptions()` - Parameter descriptions
- `_get_parameter_types()` - Parameter types

### Automatic Metadata Extraction

When registering a tool, the system automatically extracts:

1. **Basic Metadata** - name, description, capabilities
2. **Task Types** - from `get_supported_operations()`
3. **Keywords** - from name, capabilities, and operations
4. **Version Info** - from `get_version()` and `get_author()`
5. **Tags** - from `get_tags()`
6. **Parameter Schema** - from parameter methods

This eliminates the need to manually specify metadata when registering tools. 