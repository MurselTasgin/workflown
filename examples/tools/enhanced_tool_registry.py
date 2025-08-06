"""
Enhanced Tool Registry

Provides dynamic tool registration with metadata, capabilities, and intelligent
task-to-tool mapping based on semantic matching.
"""

import re
from typing import Dict, List, Any, Optional, Type, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

from base_tool import BaseTool, ToolCapability


class ToolCategory(Enum):
    """Categories of tools."""
    SEARCH = "search"
    PROCESSING = "processing"
    GENERATION = "generation"
    ANALYSIS = "analysis"
    TRANSFORMATION = "transformation"
    VALIDATION = "validation"
    INTEGRATION = "integration"


@dataclass
class ToolMetadata:
    """Metadata for a tool."""
    name: str
    description: str
    version: str = "1.0.0"
    author: str = "Unknown"
    category: ToolCategory = ToolCategory.PROCESSING
    capabilities: List[ToolCapability] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    supported_operations: List[str] = field(default_factory=list)
    task_types: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if isinstance(self.capabilities, str):
            self.capabilities = [ToolCapability(c) for c in self.capabilities.split(",")]
        if isinstance(self.category, str):
            self.category = ToolCategory(self.category)


@dataclass
class ToolRegistration:
    """Complete tool registration information."""
    tool_id: str
    tool_class: Type[BaseTool]
    metadata: ToolMetadata
    config: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    priority: int = 100  # Lower number = higher priority
    dependencies: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)


class EnhancedToolRegistry:
    """
    Enhanced tool registry with metadata and intelligent mapping.
    
    Provides dynamic tool registration with rich metadata, capabilities,
    and intelligent task-to-tool mapping based on semantic matching.
    """
    
    def __init__(self):
        """Initialize the enhanced tool registry."""
        self._registrations: Dict[str, ToolRegistration] = {}
        self._tool_instances: Dict[str, BaseTool] = {}
        self._metadata_index: Dict[str, List[str]] = {}  # keyword -> tool_ids
        self._capability_index: Dict[ToolCapability, List[str]] = {}  # capability -> tool_ids
        self._task_type_index: Dict[str, List[str]] = {}  # task_type -> tool_ids
        
    def register_tool(
        self,
        tool_class: Type[BaseTool],
        metadata: ToolMetadata,
        config: Dict[str, Any] = None,
        priority: int = 100,
        dependencies: List[str] = None,
        alternatives: List[str] = None
    ) -> str:
        """
        Register a tool with metadata.
        
        Args:
            tool_class: Tool class to register
            metadata: Tool metadata
            config: Default configuration
            priority: Tool priority (lower = higher priority)
            dependencies: List of tool dependencies
            alternatives: List of alternative tool IDs
            
        Returns:
            Tool ID
        """
        tool_id = f"{metadata.name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
        
        registration = ToolRegistration(
            tool_id=tool_id,
            tool_class=tool_class,
            metadata=metadata,
            config=config or {},
            priority=priority,
            dependencies=dependencies or [],
            alternatives=alternatives or []
        )
        
        self._registrations[tool_id] = registration
        
        # Update indexes
        self._update_indexes(tool_id, metadata)
        
        print(f"🔧 Registered tool: {metadata.name} (ID: {tool_id})")
        return tool_id
    
    def _update_indexes(self, tool_id: str, metadata: ToolMetadata):
        """Update search indexes for the tool."""
        print(f"🔧 Updating indexes for tool: {metadata.name} (ID: {tool_id})")
        print(f"   • Task types: {metadata.task_types}")
        print(f"   • Capabilities: {[cap.value for cap in metadata.capabilities]}")
        print(f"   • Keywords: {metadata.keywords[:3]}...")  # Show first 3 keywords
        
        # Update keyword index
        for keyword in metadata.keywords:
            if keyword not in self._metadata_index:
                self._metadata_index[keyword] = []
            self._metadata_index[keyword].append(tool_id)
        
        # Update capability index
        for capability in metadata.capabilities:
            if capability not in self._capability_index:
                self._capability_index[capability] = []
            self._capability_index[capability].append(tool_id)
        
        # Update task type index
        for task_type in metadata.task_types:
            if task_type not in self._task_type_index:
                self._task_type_index[task_type] = []
            self._task_type_index[task_type].append(tool_id)
        
        print(f"   ✅ Indexes updated. Task type index now has: {list(self._task_type_index.keys())}")
    
    def unregister_tool(self, tool_id: str) -> bool:
        """
        Unregister a tool.
        
        Args:
            tool_id: Tool ID to unregister
            
        Returns:
            True if unregistered successfully
        """
        if tool_id in self._registrations:
            registration = self._registrations[tool_id]
            
            # Remove from indexes
            self._remove_from_indexes(tool_id, registration.metadata)
            
            # Remove registration
            del self._registrations[tool_id]
            
            # Remove instance if exists
            if tool_id in self._tool_instances:
                del self._tool_instances[tool_id]
            
            print(f"🗑️  Unregistered tool: {registration.metadata.name}")
            return True
        return False
    
    def _remove_from_indexes(self, tool_id: str, metadata: ToolMetadata):
        """Remove tool from search indexes."""
        # Remove from keyword index
        for keyword in metadata.keywords:
            if keyword in self._metadata_index and tool_id in self._metadata_index[keyword]:
                self._metadata_index[keyword].remove(tool_id)
                if not self._metadata_index[keyword]:
                    del self._metadata_index[keyword]
        
        # Remove from capability index
        for capability in metadata.capabilities:
            if capability in self._capability_index and tool_id in self._capability_index[capability]:
                self._capability_index[capability].remove(tool_id)
                if not self._capability_index[capability]:
                    del self._capability_index[capability]
        
        # Remove from task type index
        for task_type in metadata.task_types:
            if task_type in self._task_type_index and tool_id in self._task_type_index[task_type]:
                self._task_type_index[task_type].remove(tool_id)
                if not self._task_type_index[task_type]:
                    del self._task_type_index[task_type]
    
    def create_tool_instance(self, tool_id: str, instance_id: str = None, config: Dict[str, Any] = None) -> Optional[BaseTool]:
        """
        Create a tool instance.
        
        Args:
            tool_id: Tool ID to create instance for
            instance_id: Optional instance ID
            config: Optional configuration overrides
            
        Returns:
            Tool instance or None if not found
        """
        if tool_id not in self._registrations:
            print(f"❌ Tool ID {tool_id} not found in registry")
            return None
        
        registration = self._registrations[tool_id]
        
        try:
            # Merge configurations
            final_config = registration.config.copy()
            if config:
                final_config.update(config)
            
            # Create instance
            instance_id = instance_id or f"{tool_id}_instance_{uuid.uuid4().hex[:8]}"
            print(f"🔧 Creating tool instance: {registration.metadata.name} (ID: {instance_id})")
            
            tool_instance = registration.tool_class(
                tool_id=instance_id,
                config=final_config
            )
            
            # Store instance
            self._tool_instances[instance_id] = tool_instance
            
            print(f"✅ Successfully created tool instance: {registration.metadata.name}")
            return tool_instance
            
        except Exception as e:
            print(f"❌ Failed to create tool instance for {tool_id}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def find_tools_for_task(
        self,
        task_type: str,
        task_description: str = "",
        required_capabilities: List[ToolCapability] = None,
        keywords: List[str] = None,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find tools suitable for a given task.
        
        Args:
            task_type: Type of task
            task_description: Description of the task
            required_capabilities: Required tool capabilities
            keywords: Keywords to match
            max_results: Maximum number of results
            
        Returns:
            List of tool matches with scores
        """
        candidates = []
        
        # Get tools by task type
        task_type_tools = self._task_type_index.get(task_type, [])
        
        for tool_id in task_type_tools:
            if tool_id not in self._registrations:
                continue
            
            registration = self._registrations[tool_id]
            score = self._calculate_match_score(
                registration, task_type, task_description, required_capabilities, keywords
            )
            
            if score > 0:
                candidates.append({
                    "tool_id": tool_id,
                    "registration": registration,
                    "score": score,
                    "metadata": registration.metadata
                })
        
        # Sort by score (highest first) and priority (lowest first)
        candidates.sort(key=lambda x: (-x["score"], x["registration"].priority))
        
        return candidates[:max_results]
    
    def _calculate_match_score(
        self,
        registration: ToolRegistration,
        task_type: str,
        task_description: str,
        required_capabilities: List[ToolCapability] = None,
        keywords: List[str] = None
    ) -> float:
        """Calculate match score for a tool against a task."""
        score = 0.0
        
        # Task type match (highest weight)
        if task_type in registration.metadata.task_types:
            score += 10.0
        
        # Capability match
        if required_capabilities:
            for capability in required_capabilities:
                if capability in registration.metadata.capabilities:
                    score += 5.0
        
        # Keyword match
        if keywords and task_description:
            task_text = f"{task_type} {task_description}".lower()
            for keyword in keywords:
                if keyword.lower() in task_text:
                    score += 2.0
            
            # Check tool keywords against task description
            for keyword in registration.metadata.keywords:
                if keyword.lower() in task_text:
                    score += 1.0
        
        # Tag match
        if task_description:
            task_text = task_description.lower()
            for tag in registration.metadata.tags:
                if tag.lower() in task_text:
                    score += 0.5
        
        return score
    
    def get_tool_metadata(self, tool_id: str) -> Optional[ToolMetadata]:
        """Get tool metadata."""
        if tool_id in self._registrations:
            return self._registrations[tool_id].metadata
        return None
    
    def search_tools(
        self,
        query: str,
        category: ToolCategory = None,
        capabilities: List[ToolCapability] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search tools by query.
        
        Args:
            query: Search query
            category: Filter by category
            capabilities: Filter by capabilities
            max_results: Maximum results
            
        Returns:
            List of matching tools
        """
        results = []
        query_lower = query.lower()
        
        for tool_id, registration in self._registrations.items():
            if not registration.is_active:
                continue
            
            # Category filter
            if category and registration.metadata.category != category:
                continue
            
            # Capability filter
            if capabilities:
                if not any(cap in registration.metadata.capabilities for cap in capabilities):
                    continue
            
            # Search in metadata
            score = 0.0
            metadata = registration.metadata
            
            # Name match
            if query_lower in metadata.name.lower():
                score += 5.0
            
            # Description match
            if query_lower in metadata.description.lower():
                score += 3.0
            
            # Keyword match
            for keyword in metadata.keywords:
                if query_lower in keyword.lower():
                    score += 2.0
            
            # Tag match
            for tag in metadata.tags:
                if query_lower in tag.lower():
                    score += 1.0
            
            if score > 0:
                results.append({
                    "tool_id": tool_id,
                    "registration": registration,
                    "score": score,
                    "metadata": metadata
                })
        
        # Sort by score
        results.sort(key=lambda x: -x["score"])
        return results[:max_results]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        total_tools = len(self._registrations)
        active_tools = sum(1 for r in self._registrations.values() if r.is_active)
        
        categories = {}
        capabilities = {}
        
        for registration in self._registrations.values():
            category = registration.metadata.category.value
            categories[category] = categories.get(category, 0) + 1
            
            for capability in registration.metadata.capabilities:
                cap_name = capability.value
                capabilities[cap_name] = capabilities.get(cap_name, 0) + 1
        
        return {
            "total_tools": total_tools,
            "active_tools": active_tools,
            "categories": categories,
            "capabilities": capabilities,
            "indexed_keywords": len(self._metadata_index),
            "indexed_capabilities": len(self._capability_index),
            "indexed_task_types": len(self._task_type_index)
        }
    
    def list_tools(self, category: ToolCategory = None, active_only: bool = True) -> List[Dict[str, Any]]:
        """List all tools with optional filtering."""
        tools = []
        
        for tool_id, registration in self._registrations.items():
            if active_only and not registration.is_active:
                continue
            
            if category and registration.metadata.category != category:
                continue
            
            tools.append({
                "tool_id": tool_id,
                "name": registration.metadata.name,
                "description": registration.metadata.description,
                "category": registration.metadata.category.value,
                "capabilities": [cap.value for cap in registration.metadata.capabilities],
                "task_types": registration.metadata.task_types,
                "priority": registration.priority,
                "is_active": registration.is_active
            })
        
        return tools
    
    async def cleanup_all_instances(self):
        """Clean up all tool instances."""
        for instance in self._tool_instances.values():
            await instance.cleanup()
        self._tool_instances.clear()


# Global enhanced tool registry instance (singleton)
_enhanced_tool_registry_instance = None

def get_enhanced_tool_registry():
    """Get the singleton enhanced tool registry instance."""
    global _enhanced_tool_registry_instance
    if _enhanced_tool_registry_instance is None:
        _enhanced_tool_registry_instance = EnhancedToolRegistry()
        print(f"🔧 Created enhanced tool registry instance: {id(_enhanced_tool_registry_instance)}")
    return _enhanced_tool_registry_instance

# For backward compatibility (lazy initialization)
def enhanced_tool_registry():
    return get_enhanced_tool_registry() 