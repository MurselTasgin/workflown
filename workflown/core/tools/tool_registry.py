"""
Tool Registry

Manages and provides access to all available tools in the system.
"""

from typing import Dict, List, Any, Optional, Type
from datetime import datetime
import uuid

from .base_tool import BaseTool, ToolCapability
from ..logging.logger import get_logger


class ToolRegistry:
    """
    Registry for managing tools and their capabilities.
    
    Provides centralized access to tools and their metadata.
    """
    
    def __init__(self):
        """Initialize the tool registry."""
        self._tools: Dict[str, BaseTool] = {}
        self._tool_classes: Dict[str, Type[BaseTool]] = {}
        self._tool_default_configs: Dict[str, Dict[str, Any]] = {}
        
        # Enhanced registry features
        self._metadata_index: Dict[str, List[str]] = {}  # keyword -> tool_ids
        self._capability_index: Dict[ToolCapability, List[str]] = {}  # capability -> tool_ids
        self._task_type_index: Dict[str, List[str]] = {}  # task_type -> tool_ids
        
        # Logging
        self.logger = get_logger("ToolRegistry")
        
        # Use sync helper because we're in a non-async context
        self.logger.info_sync(f"Initialized ToolRegistry instance: {id(self)}")
    
    def register_tool(self, tool: BaseTool) -> None:
        """
        Register a tool instance.
        
        Args:
            tool: Tool instance to register
        """
        self._tools[tool.tool_id] = tool
        self.logger.info_sync(f"Registered tool instance: {tool.name} ({tool.tool_id})")
    
    def register_tool_class(self, name: str, tool_class: Type[BaseTool]) -> None:
        """
        Register a tool class.
        
        Args:
            name: Name for the tool class
            tool_class: Tool class to register
        """
        self._tool_classes[name] = tool_class
        self.logger.info_sync(f"Registered tool class: {name}")
    
    def register_tool_with_metadata(self, tool_class: Type[BaseTool], metadata: Dict[str, Any] = None, config: Dict[str, Any] = None) -> str:
        """
        Register a tool with metadata for enhanced functionality.
        
        Args:
            tool_class: Tool class to register
            metadata: Tool metadata (optional - will be extracted from tool if not provided)
            config: Default configuration
            
        Returns:
            Tool ID
        """
        tool_id = f"{metadata.get('name', 'tool').lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
        
        # Store tool class with metadata
        self._tool_classes[tool_id] = tool_class
        # Persist default config for later instance creation
        self._tool_default_configs[tool_id] = config or {}
        
        # If metadata not provided, extract it from the tool class
        if metadata is None:
            # Create a temporary instance to extract metadata
            temp_tool = tool_class(tool_id="temp", config=config or {})
            metadata = temp_tool.get_metadata()
        
        # Update indexes
        self._update_indexes(tool_id, metadata)
        
        self.logger.info_sync(f"Registered tool: {metadata.get('name', 'Unknown')} (ID: {tool_id})")
        return tool_id
    
    def register_tool_class(self, tool_class: Type[BaseTool], config: Dict[str, Any] = None) -> str:
        """
        Register a tool class with automatic metadata extraction.
        
        Args:
            tool_class: Tool class to register
            config: Default configuration
            
        Returns:
            Tool ID
        """
        # Create temporary instance to extract metadata
        temp_tool = tool_class(tool_id="temp", config=config or {})
        metadata = temp_tool.get_metadata()
        
        return self.register_tool_with_metadata(tool_class, metadata, config)
    
    def _update_indexes(self, tool_id: str, metadata: Dict[str, Any]):
        """Update search indexes for the tool."""
        # Update keyword index
        keywords = metadata.get('keywords', [])
        for keyword in keywords:
            if keyword not in self._metadata_index:
                self._metadata_index[keyword] = []
            self._metadata_index[keyword].append(tool_id)
        
        # Update capability index
        capabilities = metadata.get('capabilities', [])
        for capability in capabilities:
            if capability not in self._capability_index:
                self._capability_index[capability] = []
            self._capability_index[capability].append(tool_id)
        
        # Update task type index
        task_types = metadata.get('task_types', [])
        for task_type in task_types:
            if task_type not in self._task_type_index:
                self._task_type_index[task_type] = []
            self._task_type_index[task_type].append(tool_id)
        
        self.logger.info_sync(f"Indexes updated. Task type index now has: {list(self._task_type_index.keys())}")
    
    def get_tool(self, tool_id: str) -> Optional[BaseTool]:
        """
        Get a tool by ID.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_id)
    
    def get_tool_class(self, name: str) -> Optional[Type[BaseTool]]:
        """
        Get a tool class by name.
        
        Args:
            name: Tool class name
            
        Returns:
            Tool class or None if not found
        """
        return self._tool_classes.get(name)
    
    def create_tool(self, name: str, tool_id: str = None, config: Dict[str, Any] = None) -> Optional[BaseTool]:
        """
        Create a tool instance.
        
        Args:
            name: Tool class name
            tool_id: Tool identifier (optional)
            config: Tool configuration (optional)
            
        Returns:
            Tool instance or None if class not found
        """
        tool_class = self.get_tool_class(name)
        if tool_class:
            tool = tool_class(tool_id=tool_id, config=config or {})
            self.register_tool(tool)
            return tool
        return None
    
    def create_tool_instance(self, tool_id: str, instance_id: str = None, config: Dict[str, Any] = None) -> Optional[BaseTool]:
        """
        Create a tool instance from registered tool class.
        
        Args:
            tool_id: Tool ID to create instance for
            instance_id: Optional instance ID
            config: Optional configuration overrides
            
        Returns:
            Tool instance or None if not found
        """
        if tool_id not in self._tool_classes:
            self.logger.error_sync(f"Tool ID {tool_id} not found in registry")
            return None
        
        tool_class = self._tool_classes[tool_id]
        
        try:
            # Create instance
            instance_id = instance_id or f"{tool_id}_instance"
            self.logger.info_sync(f"Creating tool instance: {tool_id} (ID: {instance_id})")
            
            # Merge default config from registration with provided overrides
            default_cfg = self._tool_default_configs.get(tool_id, {})
            merged_config = {**default_cfg, **(config or {})}
            
            tool_instance = tool_class(
                tool_id=instance_id,
                config=merged_config
            )
            
            self.logger.info_sync(f"Successfully created tool instance: {tool_id}")
            return tool_instance
            
        except Exception as e:
            self.logger.error_sync(f"Failed to create tool instance for {tool_id}: {e}")
            return None
    
    def get_all_tools(self) -> List[BaseTool]:
        """
        Get all registered tools.
        
        Returns:
            List of all tool instances
        """
        return list(self._tools.values())
    
    def get_tools_by_capability(self, capability: ToolCapability) -> List[BaseTool]:
        """
        Get tools with specific capability.
        
        Args:
            capability: Tool capability to filter by
            
        Returns:
            List of tools with the specified capability
        """
        return [
            tool for tool in self._tools.values()
            if capability in tool.get_capabilities()
        ]
    
    def get_tools_by_operation(self, operation: str) -> List[BaseTool]:
        """
        Get tools that support a specific operation.
        
        Args:
            operation: Operation type to filter by
            
        Returns:
            List of tools that support the operation
        """
        return [
            tool for tool in self._tools.values()
            if tool.can_handle_operation(operation)
        ]
    
    def get_available_tool_classes(self) -> List[str]:
        """
        Get list of available tool class names.
        
        Returns:
            List of available tool class names
        """
        return list(self._tool_classes.keys())
    
    def find_tools_for_task(self, task_type: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Find tools suitable for a given task type.
        
        Args:
            task_type: Type of task
            max_results: Maximum number of results
            
        Returns:
            List of tool matches with scores
        """
        candidates = []
        
        # Get tools by task type
        task_type_tools = self._task_type_index.get(task_type, [])
        
        for tool_id in task_type_tools:
            if tool_id in self._tool_classes:
                candidates.append({
                    "tool_id": tool_id,
                    "tool_class": self._tool_classes[tool_id],
                    "score": 10.0,  # Exact match gets highest score
                    "metadata": {"name": tool_id, "task_types": [task_type]}
                })
        
        # Sort by score (highest first)
        candidates.sort(key=lambda x: -x["score"])
        
        return candidates[:max_results]
    
    def get_tool_status(self) -> Dict[str, Any]:
        """
        Get status of all tools.
        
        Returns:
            Dictionary with tool status information
        """
        return {
            "total_tools": len(self._tools),
            "available_classes": len(self._tool_classes),
            "tools": [tool.get_status() for tool in self._tools.values()]
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        total_tools = len(self._tool_classes)
        total_instances = len(self._tools)
        
        categories = {}
        capabilities = {}
        
        # Count by task types
        for task_type, tool_ids in self._task_type_index.items():
            categories[task_type] = len(tool_ids)
        
        # Count by capabilities
        for capability, tool_ids in self._capability_index.items():
            # Handle both enum values and strings
            if hasattr(capability, 'value'):
                capabilities[capability.value] = len(tool_ids)
            else:
                capabilities[capability] = len(tool_ids)
        
        return {
            "total_tools": total_tools,
            "total_instances": total_instances,
            "categories": categories,
            "capabilities": capabilities,
            "indexed_keywords": len(self._metadata_index),
            "indexed_capabilities": len(self._capability_index),
            "indexed_task_types": len(self._task_type_index)
        }
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools."""
        tools = []
        
        for tool_id, tool_class in self._tool_classes.items():
            tools.append({
                "tool_id": tool_id,
                "name": tool_class.__name__,
                "description": getattr(tool_class, '__doc__', 'No description'),
                "task_types": self._task_type_index.get(tool_id, [])
            })
        
        return tools
    
    async def cleanup_all_instances(self):
        """Clean up all tool instances."""
        for instance in self._tools.values():
            await instance.cleanup()
        self._tools.clear()
        self.logger.info_sync("Cleaned up all tool instances")