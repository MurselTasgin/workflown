"""
Base Tool Abstract Class

Defines the interface for all tools in the workflown framework.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Union
import uuid

# Mock logger for testing
class MockLogger:
    def __init__(self, name):
        self.name = name
    
    async def info(self, message, **kwargs):
        print(f"[INFO] {self.name}: {message}")
    
    async def warning(self, message, **kwargs):
        print(f"[WARNING] {self.name}: {message}")
    
    async def error(self, message, **kwargs):
        print(f"[ERROR] {self.name}: {message}")
    
    async def debug(self, message, **kwargs):
        print(f"[DEBUG] {self.name}: {message}")

def get_logger(name):
    return MockLogger(name)


class ToolCapability(Enum):
    """Capabilities that tools can have."""
    WEB_SEARCH = "web_search"
    TEXT_GENERATION = "text_generation"
    TEXT_SUMMARIZATION = "text_summarization"
    DATA_PROCESSING = "data_processing"
    FILE_OPERATIONS = "file_operations"
    HTTP_REQUESTS = "http_requests"
    CUSTOM = "custom"


@dataclass
class ToolResult:
    """Result of a tool execution."""
    tool_id: str
    success: bool
    result: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class BaseTool(ABC):
    """
    Abstract base class for all tools.
    
    Tools are specialized components that perform specific tasks.
    They follow a consistent interface and can be easily integrated
    into workflows and executors.
    """
    
    def __init__(
        self,
        tool_id: str = None,
        name: str = "BaseTool",
        description: str = "Abstract base tool",
        capabilities: List[ToolCapability] = None,
        config: Dict[str, Any] = None,
        max_concurrent_operations: int = 5
    ):
        """
        Initialize the tool.
        
        Args:
            tool_id: Unique identifier for the tool
            name: Human-readable name
            description: Tool description
            capabilities: List of tool capabilities
            config: Configuration dictionary
            max_concurrent_operations: Maximum concurrent operations
        Note: Subclasses should call self._initialize() at the appropriate time in their own __init__ if needed.
        """
        self.tool_id = tool_id or f"{name.lower()}_{uuid.uuid4().hex[:8]}"
        self.name = name
        self.description = description
        self.capabilities = capabilities or [ToolCapability.CUSTOM]
        self.config = config or {}
        self.max_concurrent_operations = max_concurrent_operations
        
        # State tracking
        self.status = "idle"
        self.current_operations = 0
        self.total_operations = 0
        self.successful_operations = 0
        self.failed_operations = 0
        self.last_activity = datetime.now()
        
        # Logging
        self.logger = get_logger(f"{self.name}.{self.tool_id}")
        
        # Initialize tool-specific components
        # self._initialize() # Removed as per edit hint
    
    def _initialize(self):
        """Initialize tool-specific components. Override in subclasses."""
        pass
    
    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the tool with given parameters.
        
        Args:
            parameters: Tool-specific parameters
            
        Returns:
            ToolResult containing execution results
        """
        pass
    
    def can_handle_operation(self, operation_type: str) -> bool:
        """
        Check if this tool can handle the given operation type.
        
        Args:
            operation_type: Type of operation to check
            
        Returns:
            True if tool can handle the operation
        """
        return operation_type in self.get_supported_operations()
    
    @abstractmethod
    def get_supported_operations(self) -> List[str]:
        """
        Get list of supported operation types.
        
        Returns:
            List of supported operation type strings
        """
        pass
    
    def get_capabilities(self) -> List[ToolCapability]:
        """
        Get list of tool capabilities.
        
        Returns:
            List of tool capabilities
        """
        return self.capabilities
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current tool status.
        
        Returns:
            Dictionary with tool status information
        """
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "status": self.status,
            "current_operations": self.current_operations,
            "max_concurrent_operations": self.max_concurrent_operations,
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "last_activity": self.last_activity.isoformat(),
            "capabilities": [cap.value for cap in self.capabilities]
        }
    
    async def _pre_execute(self, parameters: Dict[str, Any]) -> bool:
        """
        Pre-execution checks and setup.
        
        Args:
            parameters: Tool parameters
            
        Returns:
            True if execution can proceed
        """
        # Check capacity
        if self.current_operations >= self.max_concurrent_operations:
            await self.logger.warning(
                f"Tool at capacity: {self.current_operations}/{self.max_concurrent_operations}",
                tool_id=self.tool_id
            )
            return False
        
        # Update state
        self.current_operations += 1
        self.total_operations += 1
        self.status = "busy"
        self.last_activity = datetime.now()
        
        await self.logger.info(
            f"Starting tool execution: {self.name}",
            tool_id=self.tool_id,
            operation_count=self.current_operations
        )
        
        return True
    
    async def _post_execute(self, result: ToolResult):
        """
        Post-execution cleanup and state updates.
        
        Args:
            result: Execution result
        """
        # Update state
        self.current_operations -= 1
        if result.success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1
        
        # Update status
        if self.current_operations == 0:
            self.status = "idle"
        
        self.last_activity = datetime.now()
        
        await self.logger.info(
            f"Tool execution completed: {self.name}",
            tool_id=self.tool_id,
            success=result.success,
            execution_time=result.execution_time
        )
    
    async def execute_with_tracking(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute tool with full tracking and error handling.
        
        Args:
            parameters: Tool parameters
            
        Returns:
            ToolResult with execution results
        """
        start_time = datetime.now()
        
        try:
            # Pre-execution checks
            if not await self._pre_execute(parameters):
                return ToolResult(
                    tool_id=self.tool_id,
                    success=False,
                    result=None,
                    metadata={"error": "Tool at capacity"},
                    execution_time=0.0,
                    errors=["Tool at maximum capacity"]
                )
            
            # Execute tool
            result = await self.execute(parameters)
            
            # Update execution time
            result.execution_time = (datetime.now() - start_time).total_seconds()
            result.timestamp = datetime.now()
            
            # Post-execution cleanup
            await self._post_execute(result)
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            error_result = ToolResult(
                tool_id=self.tool_id,
                success=False,
                result=None,
                metadata={
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                execution_time=execution_time,
                errors=[str(e)]
            )
            
            # Update state even on error
            self.current_operations -= 1
            self.failed_operations += 1
            if self.current_operations == 0:
                self.status = "idle"
            
            await self.logger.error(
                f"Tool execution failed: {self.name}",
                tool_id=self.tool_id,
                error=str(e),
                execution_time=execution_time
            )
            
            return error_result
    
    async def cleanup(self):
        """Clean up tool resources."""
        await self.logger.info(f"Cleaning up tool: {self.name}", tool_id=self.tool_id)
        # Override in subclasses for specific cleanup 