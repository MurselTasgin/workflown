"""
Base Tool Abstract Class

Defines the interface for all tools in the workflown framework.
"""

from abc import ABC, abstractmethod
import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Union
import uuid

from ..logging.logger import get_logger


class ToolCapability(Enum):
    """Capabilities that tools can have."""
    WEB_SEARCH = "web_search"
    TEXT_GENERATION = "text_generation"
    TEXT_SUMMARIZATION = "text_summarization"
    DATA_PROCESSING = "data_processing"
    FILE_OPERATIONS = "file_operations"
    HTTP_REQUESTS = "http_requests"
    DATABASE_OPERATIONS = "database_operations"
    IMAGE_PROCESSING = "image_processing"
    AUDIO_PROCESSING = "audio_processing"
    VIDEO_PROCESSING = "video_processing"
    MACHINE_LEARNING = "machine_learning"
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
        #self._initialize()
        
        # Execution context from the most recent execute_with_tracking() call
        self._current_execution_context: Dict[str, Any] = {}
    
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
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get tool metadata for registration.
        
        Returns:
            Dictionary containing tool metadata
        """
        return {
            "name": self.name,
            "description": self.description,
            "task_types": self.get_supported_operations(),
            "capabilities": [cap.value for cap in self.capabilities],
            "keywords": self._get_keywords(),
            "version": self.get_version(),
            "author": self.get_author(),
            "tags": self.get_tags()
        }
    
    def get_parameters(self) -> Dict[str, Any]:
        """
        Get tool parameter schema.
        
        Returns:
            Dictionary containing parameter definitions
        """
        return {
            "required_parameters": self._get_required_parameters(),
            "optional_parameters": self._get_optional_parameters(),
            "parameter_descriptions": self._get_parameter_descriptions(),
            "parameter_types": self._get_parameter_types()
        }
    
    def get_description(self) -> str:
        """
        Get detailed tool description.
        
        Returns:
            Detailed description of the tool
        """
        return self.description
    
    def get_version(self) -> str:
        """
        Get tool version.
        
        Returns:
            Version string
        """
        return "1.0.0"
    
    def get_author(self) -> str:
        """
        Get tool author.
        
        Returns:
            Author string
        """
        return "Unknown"
    
    def get_tags(self) -> List[str]:
        """
        Get tool tags for categorization.
        
        Returns:
            List of tags
        """
        return []
    
    def _get_keywords(self) -> List[str]:
        """
        Get keywords for tool discovery.
        
        Returns:
            List of keywords
        """
        # Default implementation - subclasses should override
        keywords = [self.name.lower()]
        keywords.extend([cap.value for cap in self.capabilities])
        keywords.extend(self.get_supported_operations())
        return list(set(keywords))
    
    def _get_required_parameters(self) -> List[str]:
        """
        Get list of required parameters.
        
        Returns:
            List of required parameter names
        """
        return []
    
    def _get_optional_parameters(self) -> List[str]:
        """
        Get list of optional parameters.
        
        Returns:
            List of optional parameter names
        """
        return []
    
    def _get_parameter_descriptions(self) -> Dict[str, str]:
        """
        Get parameter descriptions.
        
        Returns:
            Dictionary of parameter descriptions
        """
        return {}
    
    def _get_parameter_types(self) -> Dict[str, str]:
        """
        Get parameter types.
        
        Returns:
            Dictionary of parameter types
        """
        return {}
    
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
    
    async def execute_with_tracking(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        """
        Execute tool with full tracking and error handling.
        
        Args:
            parameters: Tool parameters
            context: Optional execution context (e.g., task_id, task_type)
            
        Returns:
            ToolResult with execution results
        """
        start_time = datetime.now()
        context = context or {}
        # Capture context for nested/tool-internal calls
        self._current_execution_context = dict(context)
        
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
            
            # Persist inputs if enabled
            try:
                if self._is_persistence_enabled(parameters, context) and self._should_persist_inputs(parameters, context):
                    self.persist_inputs(parameters, context)
            except Exception:
                # Do not fail execution due to persistence errors
                pass

            # Execute tool
            result = await self.execute(parameters)
            
            # Update execution time
            result.execution_time = (datetime.now() - start_time).total_seconds()
            result.timestamp = datetime.now()
            
            # Persist outputs if enabled
            try:
                if self._is_persistence_enabled(parameters, context) and self._should_persist_outputs(parameters, context):
                    self.persist_outputs(result, parameters, context)
            except Exception:
                # Do not fail execution due to persistence errors
                pass

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

    # ---------------------------------------------------------------------
    # Result display (can be overridden by tools)
    # ---------------------------------------------------------------------
    def display_result(self, task_id: str, result: Any, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Display execution result for this tool. Tools may override
        `_display_result_body` to customize body rendering while keeping
        a consistent header/footer.

        Args:
            task_id: The task identifier
            result: The execution result payload
            context: Optional additional context (e.g., {"task_type": "web_search"})
        """
        context = context or {}
        task_type = context.get("task_type", ",".join(self.get_supported_operations()) or self.name)

        print(f"\n{'=' * 60}")
        print(f"🎯 TASK COMPLETED: {task_id} ({task_type})")
        print(f"⏱️  Completed at: {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'=' * 60}")

        try:
            self._display_result_body(result, context)
        except Exception as _e:
            # Fallback generic rendering
            print(f"   • Result type: {type(result).__name__}")
            print(f"   • Result: {result}")

        print(f"{'=' * 60}")

    def _display_result_body(self, result: Any, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Default generic result rendering. Subclasses should override this
        for tool-specific presentation.
        """
        print(f"   • Result type: {type(result).__name__}")
        print(f"   • Result: {result}")

    # ---------------------------------------------------------------------
    # Persistence (inputs/outputs)
    # ---------------------------------------------------------------------
    def _is_persistence_enabled(self, parameters: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None) -> bool:
        parameters = parameters or {}
        persistence_cfg = self.config.get("persistence") or {}
        # Allow flat keys too
        enabled = self.config.get("persistence_enabled")
        if enabled is None:
            enabled = persistence_cfg.get("enabled")
        if enabled is None:
            # Allow enabling via parameters
            p_param = parameters.get("persistence") or {}
            enabled = p_param.get("enabled", False)
        return bool(enabled)

    def _should_persist_inputs(self, parameters: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None) -> bool:
        parameters = parameters or {}
        persistence_cfg = self.config.get("persistence") or {}
        value = self.config.get("persist_inputs")
        if value is None:
            value = persistence_cfg.get("persist_inputs")
        if value is None:
            p_param = parameters.get("persistence") or {}
            value = p_param.get("persist_inputs", True)
        return bool(value)

    def _should_persist_outputs(self, parameters: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None) -> bool:
        parameters = parameters or {}
        persistence_cfg = self.config.get("persistence") or {}
        value = self.config.get("persist_outputs")
        if value is None:
            value = persistence_cfg.get("persist_outputs")
        if value is None:
            p_param = parameters.get("persistence") or {}
            value = p_param.get("persist_outputs", True)
        return bool(value)

    def _resolve_persistence_dirs(self, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Path]:
        parameters = parameters or {}
        p_cfg = self.config.get("persistence") or {}
        p_param = parameters.get("persistence") or {}

        base_path = (
            self.config.get("persistence_base_path")
            or p_cfg.get("base_path")
            or p_param.get("base_path")
            or os.path.join("logs", "persistence")
        )
        inputs_subdir = (
            self.config.get("persistence_inputs_subdir")
            or p_cfg.get("inputs_subdir")
            or p_param.get("inputs_subdir")
            or "inputs"
        )
        outputs_subdir = (
            self.config.get("persistence_outputs_subdir")
            or p_cfg.get("outputs_subdir")
            or p_param.get("outputs_subdir")
            or "outputs"
        )

        tool_dir = Path(base_path) / self.name
        inputs_dir = tool_dir / inputs_subdir
        outputs_dir = tool_dir / outputs_subdir
        return {"tool_dir": tool_dir, "inputs_dir": inputs_dir, "outputs_dir": outputs_dir}

    def persist_inputs(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> None:
        context = context or {}
        dirs = self._resolve_persistence_dirs(parameters)
        os.makedirs(dirs["inputs_dir"], exist_ok=True)

        task_id = context.get("task_id", "no_task")
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        file_name = f"{timestamp_str}_{task_id}_inputs.json"
        file_path = dirs["inputs_dir"] / file_name

        payload = {
            "tool_id": self.tool_id,
            "tool_name": self.name,
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "parameters": self._safe_serialize(parameters),
            "context": self._safe_serialize(context or {}),
        }
        self._write_json_file(file_path, payload)

    def persist_outputs(self, result: ToolResult, parameters: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None) -> None:
        parameters = parameters or {}
        context = context or {}
        dirs = self._resolve_persistence_dirs(parameters)
        os.makedirs(dirs["outputs_dir"], exist_ok=True)

        task_id = context.get("task_id", "no_task")
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        file_name = f"{timestamp_str}_{task_id}_outputs.json"
        file_path = dirs["outputs_dir"] / file_name

        payload = {
            "tool_id": self.tool_id,
            "tool_name": self.name,
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "success": result.success,
            "result": self._safe_serialize(result.result),
            "metadata": self._safe_serialize(result.metadata),
            "errors": self._safe_serialize(result.errors),
            "warnings": self._safe_serialize(result.warnings),
            "execution_time": result.execution_time,
        }
        self._write_json_file(file_path, payload)

    def _write_json_file(self, path: Path, data: Dict[str, Any]) -> None:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            # Swallow errors to avoid impacting the main execution path
            pass

    def _safe_serialize(self, obj: Any) -> Any:
        try:
            json.dumps(obj)
            return obj
        except Exception:
            # Attempt to convert complex objects
            if isinstance(obj, dict):
                return {str(k): self._safe_serialize(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple, set)):
                return [self._safe_serialize(v) for v in obj]
            return str(obj)