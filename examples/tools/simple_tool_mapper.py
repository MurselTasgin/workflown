"""
Simple Tool Mapper

Provides intelligent mapping between tasks and tools using the object-based tool registry.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from tool_registry import ToolRegistry
from base_tool import ToolCapability


class MappingStrategy(Enum):
    """Strategies for tool mapping."""
    EXACT_MATCH = "exact_match"
    CAPABILITY_MATCH = "capability_match"
    KEYWORD_MATCH = "keyword_match"


@dataclass
class TaskMapping:
    """Result of task-to-tool mapping."""
    task_id: str
    task_type: str
    selected_tool_id: str
    tool_class: Any
    mapping_score: float
    mapping_strategy: MappingStrategy
    confidence: float = 0.0


class SimpleToolMapper:
    """
    Simple tool mapper that maps tasks to appropriate tools.
    
    Uses the object-based tool registry to find the best tool for each task.
    """
    
    def __init__(self, tool_registry: ToolRegistry):
        """
        Initialize the tool mapper.
        
        Args:
            tool_registry: Tool registry to use
        """
        self.tool_registry = tool_registry
        self.mapping_cache: Dict[str, TaskMapping] = {}
        
    def map_task_to_tool(
        self,
        task_id: str,
        task_type: str,
        task_description: str = "",
        task_parameters: Dict[str, Any] = None
    ) -> Optional[TaskMapping]:
        """
        Map a task to the best available tool.
        
        Args:
            task_id: Task identifier
            task_type: Type of task
            task_description: Description of the task
            task_parameters: Task parameters
            
        Returns:
            TaskMapping or None if no suitable tool found
        """
        # Check cache first
        cache_key = f"{task_id}_{task_type}"
        if cache_key in self.mapping_cache:
            return self.mapping_cache[cache_key]
        
        # Find candidates
        candidates = self.tool_registry.find_tools_for_task(task_type)
        
        if not candidates:
            print(f"⚠️  No tools found for task {task_id} (type: {task_type})")
            return None
        
        # Select best candidate
        best_candidate = candidates[0]
        selected_tool_id = best_candidate["tool_id"]
        tool_class = best_candidate["tool_class"]
        score = best_candidate["score"]
        
        # Calculate confidence based on score
        confidence = min(score / 10.0, 1.0) if score > 0 else 0.0
        
        # Create mapping
        mapping = TaskMapping(
            task_id=task_id,
            task_type=task_type,
            selected_tool_id=selected_tool_id,
            tool_class=tool_class,
            mapping_score=score,
            mapping_strategy=MappingStrategy.EXACT_MATCH,
            confidence=confidence
        )
        
        # Cache the result
        self.mapping_cache[cache_key] = mapping
        
        print(f"🔗 Mapped task {task_id} to tool {selected_tool_id} (score: {score:.2f}, confidence: {confidence:.2f})")
        
        return mapping
    
    def get_mapping_statistics(self) -> Dict[str, Any]:
        """Get mapping statistics."""
        total_mappings = len(self.mapping_cache)
        successful_mappings = sum(1 for m in self.mapping_cache.values() if m.confidence > 0.5)
        
        return {
            "total_mappings": total_mappings,
            "successful_mappings": successful_mappings,
            "success_rate": successful_mappings / total_mappings if total_mappings > 0 else 0,
            "average_confidence": sum(m.confidence for m in self.mapping_cache.values()) / total_mappings if total_mappings > 0 else 0
        }
    
    def clear_cache(self):
        """Clear the mapping cache."""
        self.mapping_cache.clear()
        print("🗑️  Cleared tool mapping cache") 