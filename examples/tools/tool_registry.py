"""
Tool Registry

Manages and provides access to all available tools in the system.
"""

from typing import Dict, List, Any, Optional, Type
from .base_tool import BaseTool, ToolCapability
from .web_search_tool import WebSearchTool
from .composer_tool import ComposerTool


class ToolRegistry:
    """
    Registry for managing tools and their capabilities.
    
    Provides centralized access to tools and their metadata.
    """
    
    def __init__(self):
        """Initialize the tool registry."""
        self._tools: Dict[str, BaseTool] = {}
        self._tool_classes: Dict[str, Type[BaseTool]] = {
            "web_search": WebSearchTool,
            "composer": ComposerTool
        }
    
    def register_tool(self, tool: BaseTool) -> None:
        """
        Register a tool instance.
        
        Args:
            tool: Tool instance to register
        """
        self._tools[tool.tool_id] = tool
    
    def register_tool_class(self, name: str, tool_class: Type[BaseTool]) -> None:
        """
        Register a tool class.
        
        Args:
            name: Name for the tool class
            tool_class: Tool class to register
        """
        self._tool_classes[name] = tool_class
    
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
    
    async def cleanup_all_tools(self):
        """Clean up all registered tools."""
        for tool in self._tools.values():
            await tool.cleanup()
        self._tools.clear()


# Global tool registry instance
tool_registry = ToolRegistry() 