"""
Tool Mapper

Provides intelligent mapping between tasks and tools using the tool registry.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from .tool_registry import ToolRegistry
from .base_tool import ToolCapability
from ..logging.logger import get_logger


class MappingStrategy(Enum):
    """Strategies for tool mapping."""
    EXACT_MATCH = "exact_match"
    CAPABILITY_MATCH = "capability_match"
    KEYWORD_MATCH = "keyword_match"
    FALLBACK = "fallback"


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
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ToolMapper:
    """
    Tool mapper that maps tasks to appropriate tools.
    
    Uses the tool registry to find the best tool for each task.
    """
    
    def __init__(self, tool_registry: ToolRegistry):
        """
        Initialize the tool mapper.
        
        Args:
            tool_registry: Tool registry to use
        """
        self.tool_registry = tool_registry
        self.mapping_cache: Dict[str, TaskMapping] = {}
        self.logger = get_logger("ToolMapper")
        
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
        
        # Find candidates using different strategies
        candidates = []
        
        # Strategy 1: Exact task type match
        exact_matches = self.tool_registry.find_tools_for_task(task_type)
        candidates.extend(exact_matches)
        
        # Strategy 2: Capability-based matching
        if not candidates:
            capability_matches = self._find_by_capabilities(task_type, task_description)
            candidates.extend(capability_matches)
        
        # Strategy 3: Keyword-based matching
        if not candidates:
            keyword_matches = self._find_by_keywords(task_type, task_description)
            candidates.extend(keyword_matches)
        
        # Strategy 4: Fallback to generic tools
        if not candidates:
            fallback_matches = self._find_fallback_tools(task_type)
            candidates.extend(fallback_matches)
        
        if not candidates:
            self.logger.warning(f"No tools found for task {task_id} (type: {task_type})")
            return None
        
        # Select best candidate
        best_candidate = candidates[0]
        selected_tool_id = best_candidate["tool_id"]
        tool_class = best_candidate["tool_class"]
        score = best_candidate["score"]
        strategy = best_candidate.get("strategy", MappingStrategy.EXACT_MATCH)
        
        # Calculate confidence based on score and strategy
        confidence = self._calculate_confidence(score, strategy)
        
        # Create mapping
        mapping = TaskMapping(
            task_id=task_id,
            task_type=task_type,
            selected_tool_id=selected_tool_id,
            tool_class=tool_class,
            mapping_score=score,
            mapping_strategy=strategy,
            confidence=confidence,
            metadata=best_candidate.get("metadata", {})
        )
        
        # Cache the result
        self.mapping_cache[cache_key] = mapping
        
        self.logger.info(
            f"Mapped task {task_id} to tool {selected_tool_id} "
            f"(score: {score:.2f}, confidence: {confidence:.2f}, strategy: {strategy.value})"
        )
        
        return mapping
    
    def _find_by_capabilities(self, task_type: str, task_description: str) -> List[Dict[str, Any]]:
        """Find tools by matching capabilities to task requirements."""
        candidates = []
        
        # Map task types to capabilities
        task_capability_map = {
            "web_search": ToolCapability.WEB_SEARCH,
            "text_generation": ToolCapability.TEXT_GENERATION,
            "text_summarization": ToolCapability.TEXT_SUMMARIZATION,
            "data_processing": ToolCapability.DATA_PROCESSING,
            "file_operations": ToolCapability.FILE_OPERATIONS,
            "http_requests": ToolCapability.HTTP_REQUESTS,
            "database_operations": ToolCapability.DATABASE_OPERATIONS,
            "image_processing": ToolCapability.IMAGE_PROCESSING,
            "audio_processing": ToolCapability.AUDIO_PROCESSING,
            "video_processing": ToolCapability.VIDEO_PROCESSING,
            "machine_learning": ToolCapability.MACHINE_LEARNING,
        }
        
        required_capability = task_capability_map.get(task_type)
        if required_capability:
            tools = self.tool_registry.get_tools_by_capability(required_capability)
            for tool in tools:
                candidates.append({
                    "tool_id": tool.tool_id,
                    "tool_class": tool.__class__,
                    "score": 8.0,  # High score for capability match
                    "strategy": MappingStrategy.CAPABILITY_MATCH,
                    "metadata": {"capability": required_capability.value}
                })
        
        return candidates
    
    def _find_by_keywords(self, task_type: str, task_description: str) -> List[Dict[str, Any]]:
        """Find tools by matching keywords in task description."""
        candidates = []
        
        # Extract keywords from task description
        keywords = self._extract_keywords(task_description.lower())
        
        # Find tools that match keywords
        for tool_id, tool_class in self.tool_registry._tool_classes.items():
            tool_metadata = self._get_tool_metadata(tool_id)
            if tool_metadata:
                tool_keywords = tool_metadata.get("keywords", [])
                matches = sum(1 for keyword in keywords if keyword in tool_keywords)
                
                if matches > 0:
                    score = 5.0 + (matches * 1.0)  # Base score + bonus for matches
                    candidates.append({
                        "tool_id": tool_id,
                        "tool_class": tool_class,
                        "score": score,
                        "strategy": MappingStrategy.KEYWORD_MATCH,
                        "metadata": {"keyword_matches": matches}
                    })
        
        return candidates
    
    def _find_fallback_tools(self, task_type: str) -> List[Dict[str, Any]]:
        """Find generic/fallback tools for unknown task types."""
        candidates = []
        
        # Look for tools with CUSTOM capability
        tools = self.tool_registry.get_tools_by_capability(ToolCapability.CUSTOM)
        for tool in tools:
            candidates.append({
                "tool_id": tool.tool_id,
                "tool_class": tool.__class__,
                "score": 3.0,  # Lower score for fallback
                "strategy": MappingStrategy.FALLBACK,
                "metadata": {"fallback": True}
            })
        
        return candidates
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text."""
        # Simple keyword extraction - could be enhanced with NLP
        common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        words = text.split()
        keywords = [word for word in words if len(word) > 3 and word not in common_words]
        return keywords[:10]  # Limit to top 10 keywords
    
    def _get_tool_metadata(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a tool using the tool's get_metadata method."""
        if tool_id in self.tool_registry._tool_classes:
            tool_class = self.tool_registry._tool_classes[tool_id]
            # Create temporary instance to get metadata
            temp_tool = tool_class(tool_id="temp")
            return temp_tool.get_metadata()
        return None
    
    def _calculate_confidence(self, score: float, strategy: MappingStrategy) -> float:
        """Calculate confidence score based on mapping strategy and score."""
        base_confidence = min(score / 10.0, 1.0)
        
        # Adjust confidence based on strategy
        strategy_multipliers = {
            MappingStrategy.EXACT_MATCH: 1.0,
            MappingStrategy.CAPABILITY_MATCH: 0.9,
            MappingStrategy.KEYWORD_MATCH: 0.7,
            MappingStrategy.FALLBACK: 0.5
        }
        
        multiplier = strategy_multipliers.get(strategy, 0.5)
        return base_confidence * multiplier
    
    def get_mapping_statistics(self) -> Dict[str, Any]:
        """Get mapping statistics."""
        total_mappings = len(self.mapping_cache)
        successful_mappings = sum(1 for m in self.mapping_cache.values() if m.confidence > 0.5)
        
        strategy_counts = {}
        for mapping in self.mapping_cache.values():
            strategy = mapping.mapping_strategy.value
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        return {
            "total_mappings": total_mappings,
            "successful_mappings": successful_mappings,
            "success_rate": successful_mappings / total_mappings if total_mappings > 0 else 0,
            "average_confidence": sum(m.confidence for m in self.mapping_cache.values()) / total_mappings if total_mappings > 0 else 0,
            "strategy_distribution": strategy_counts
        }
    
    def clear_cache(self):
        """Clear the mapping cache."""
        self.mapping_cache.clear()
        self.logger.info("Cleared tool mapping cache")
    
    def get_mapping_for_task(self, task_id: str) -> Optional[TaskMapping]:
        """Get cached mapping for a specific task."""
        for mapping in self.mapping_cache.values():
            if mapping.task_id == task_id:
                return mapping
        return None
    
    def update_mapping(self, task_id: str, new_tool_id: str, reason: str = ""):
        """Manually update a task mapping."""
        # Find existing mapping
        for key, mapping in self.mapping_cache.items():
            if mapping.task_id == task_id:
                # Update the mapping
                mapping.selected_tool_id = new_tool_id
                mapping.mapping_strategy = MappingStrategy.FALLBACK
                mapping.confidence = 0.5  # Lower confidence for manual override
                mapping.metadata = mapping.metadata or {}
                mapping.metadata["manual_override"] = True
                mapping.metadata["override_reason"] = reason
                
                self.logger.info(f"Manually updated mapping for task {task_id} to tool {new_tool_id}")
                break 