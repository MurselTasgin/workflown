"""
Tool Mapping Functions

Provides intelligent mapping between tasks and tools using the enhanced tool registry.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from enhanced_tool_registry import EnhancedToolRegistry, ToolCategory, ToolMetadata
from base_tool import ToolCapability


class MappingStrategy(Enum):
    """Strategies for tool mapping."""
    EXACT_MATCH = "exact_match"
    SEMANTIC_MATCH = "semantic_match"
    CAPABILITY_MATCH = "capability_match"
    KEYWORD_MATCH = "keyword_match"
    HYBRID = "hybrid"


@dataclass
class TaskMapping:
    """Result of task-to-tool mapping."""
    task_id: str
    task_type: str
    selected_tool_id: str
    tool_metadata: ToolMetadata
    mapping_score: float
    mapping_strategy: MappingStrategy
    alternatives: List[str] = None
    confidence: float = 0.0


class ToolMapper:
    """
    Intelligent tool mapper that maps tasks to appropriate tools.
    
    Uses the enhanced tool registry to find the best tool for each task
    based on various matching strategies.
    """
    
    def __init__(self, tool_registry: EnhancedToolRegistry):
        """
        Initialize the tool mapper.
        
        Args:
            tool_registry: Enhanced tool registry to use
        """
        self.tool_registry = tool_registry
        self.mapping_cache: Dict[str, TaskMapping] = {}
        
    def map_task_to_tool(
        self,
        task_id: str,
        task_type: str,
        task_description: str = "",
        task_parameters: Dict[str, Any] = None,
        required_capabilities: List[ToolCapability] = None,
        strategy: MappingStrategy = MappingStrategy.HYBRID,
        fallback_to_alternatives: bool = True
    ) -> Optional[TaskMapping]:
        """
        Map a task to the best available tool.
        
        Args:
            task_id: Task identifier
            task_type: Type of task
            task_description: Description of the task
            task_parameters: Task parameters
            required_capabilities: Required tool capabilities
            strategy: Mapping strategy to use
            fallback_to_alternatives: Whether to try alternatives if primary fails
            
        Returns:
            TaskMapping or None if no suitable tool found
        """
        # Check cache first
        cache_key = f"{task_id}_{task_type}_{strategy.value}"
        if cache_key in self.mapping_cache:
            return self.mapping_cache[cache_key]
        
        # Find candidates based on strategy
        candidates = self._find_candidates(
            task_type, task_description, required_capabilities, strategy
        )
        
        if not candidates:
            print(f"⚠️  No tools found for task {task_id} (type: {task_type})")
            return None
        
        # Select best candidate
        best_candidate = candidates[0]
        selected_tool_id = best_candidate["tool_id"]
        registration = best_candidate["registration"]
        score = best_candidate["score"]
        
        # Calculate confidence based on score and number of candidates
        confidence = min(score / 10.0, 1.0) if score > 0 else 0.0
        
        # Get alternatives
        alternatives = []
        if len(candidates) > 1:
            alternatives = [c["tool_id"] for c in candidates[1:3]]  # Top 2 alternatives
        
        # Create mapping
        mapping = TaskMapping(
            task_id=task_id,
            task_type=task_type,
            selected_tool_id=selected_tool_id,
            tool_metadata=registration.metadata,
            mapping_score=score,
            mapping_strategy=strategy,
            alternatives=alternatives,
            confidence=confidence
        )
        
        # Cache the result
        self.mapping_cache[cache_key] = mapping
        
        print(f"🔗 Mapped task {task_id} to tool {registration.metadata.name} (score: {score:.2f}, confidence: {confidence:.2f})")
        
        return mapping
    
    def _find_candidates(
        self,
        task_type: str,
        task_description: str,
        required_capabilities: List[ToolCapability],
        strategy: MappingStrategy
    ) -> List[Dict[str, Any]]:
        """Find candidate tools based on the specified strategy."""
        
        if strategy == MappingStrategy.EXACT_MATCH:
            return self._exact_match_candidates(task_type)
        elif strategy == MappingStrategy.SEMANTIC_MATCH:
            return self._semantic_match_candidates(task_type, task_description)
        elif strategy == MappingStrategy.CAPABILITY_MATCH:
            return self._capability_match_candidates(required_capabilities)
        elif strategy == MappingStrategy.KEYWORD_MATCH:
            return self._keyword_match_candidates(task_description)
        elif strategy == MappingStrategy.HYBRID:
            return self._hybrid_match_candidates(task_type, task_description, required_capabilities)
        else:
            return []
    
    def _exact_match_candidates(self, task_type: str) -> List[Dict[str, Any]]:
        """Find candidates by exact task type match."""
        print(f"🔍 Looking for tools with task type: {task_type}")
        print(f"📋 Available task types in registry: {list(self.tool_registry._task_type_index.keys())}")
        print(f"🔧 Registry ID: {id(self.tool_registry)}")
        print(f"🔧 Registry registrations: {len(self.tool_registry._registrations)}")
        
        candidates = self.tool_registry.find_tools_for_task(
            task_type=task_type,
            max_results=5
        )
        
        print(f"🎯 Found {len(candidates)} candidates for task type '{task_type}'")
        for candidate in candidates:
            print(f"   • {candidate['tool_id']} - {candidate['metadata'].name} (score: {candidate['score']})")
        
        return candidates
    
    def _semantic_match_candidates(self, task_type: str, task_description: str) -> List[Dict[str, Any]]:
        """Find candidates by semantic matching."""
        # Extract keywords from task description
        keywords = self._extract_keywords(task_description)
        
        candidates = self.tool_registry.find_tools_for_task(
            task_type=task_type,
            task_description=task_description,
            keywords=keywords,
            max_results=5
        )
        return candidates
    
    def _capability_match_candidates(self, required_capabilities: List[ToolCapability]) -> List[Dict[str, Any]]:
        """Find candidates by capability matching."""
        if not required_capabilities:
            return []
        
        candidates = []
        for capability in required_capabilities:
            capability_tools = self.tool_registry.search_tools(
                query=capability.value,
                capabilities=[capability],
                max_results=3
            )
            candidates.extend(capability_tools)
        
        # Remove duplicates and sort by score
        unique_candidates = {}
        for candidate in candidates:
            tool_id = candidate["tool_id"]
            if tool_id not in unique_candidates or candidate["score"] > unique_candidates[tool_id]["score"]:
                unique_candidates[tool_id] = candidate
        
        return sorted(unique_candidates.values(), key=lambda x: -x["score"])
    
    def _keyword_match_candidates(self, task_description: str) -> List[Dict[str, Any]]:
        """Find candidates by keyword matching."""
        keywords = self._extract_keywords(task_description)
        
        candidates = []
        for keyword in keywords:
            keyword_tools = self.tool_registry.search_tools(
                query=keyword,
                max_results=3
            )
            candidates.extend(keyword_tools)
        
        # Remove duplicates and sort by score
        unique_candidates = {}
        for candidate in candidates:
            tool_id = candidate["tool_id"]
            if tool_id not in unique_candidates or candidate["score"] > unique_candidates[tool_id]["score"]:
                unique_candidates[tool_id] = candidate
        
        return sorted(unique_candidates.values(), key=lambda x: -x["score"])
    
    def _hybrid_match_candidates(
        self,
        task_type: str,
        task_description: str,
        required_capabilities: List[ToolCapability]
    ) -> List[Dict[str, Any]]:
        """Find candidates using hybrid matching strategy."""
        all_candidates = []
        
        # Try exact match first
        exact_candidates = self._exact_match_candidates(task_type)
        all_candidates.extend(exact_candidates)
        
        # Add semantic matches
        semantic_candidates = self._semantic_match_candidates(task_type, task_description)
        all_candidates.extend(semantic_candidates)
        
        # Add capability matches if specified
        if required_capabilities:
            capability_candidates = self._capability_match_candidates(required_capabilities)
            all_candidates.extend(capability_candidates)
        
        # Remove duplicates and sort by score
        unique_candidates = {}
        for candidate in all_candidates:
            tool_id = candidate["tool_id"]
            if tool_id not in unique_candidates or candidate["score"] > unique_candidates[tool_id]["score"]:
                unique_candidates[tool_id] = candidate
        
        return sorted(unique_candidates.values(), key=lambda x: -x["score"])
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        if not text:
            return []
        
        # Simple keyword extraction (could be enhanced with NLP)
        words = text.lower().split()
        # Filter out common stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        return keywords[:10]  # Limit to top 10 keywords
    
    def map_workflow_tasks(self, tasks: Dict[str, Any]) -> Dict[str, TaskMapping]:
        """
        Map all tasks in a workflow to appropriate tools.
        
        Args:
            tasks: Dictionary of tasks with their metadata
            
        Returns:
            Dictionary mapping task IDs to TaskMapping objects
        """
        mappings = {}
        
        for task_id, task_info in tasks.items():
            task_type = task_info.get("task_type", "generic")
            task_description = task_info.get("description", "")
            task_parameters = task_info.get("parameters", {})
            required_capabilities = task_info.get("required_capabilities", [])
            
            # Convert capability strings to ToolCapability objects
            capabilities = []
            for cap_str in required_capabilities:
                try:
                    capabilities.append(ToolCapability(cap_str))
                except ValueError:
                    print(f"⚠️  Unknown capability: {cap_str}")
            
            mapping = self.map_task_to_tool(
                task_id=task_id,
                task_type=task_type,
                task_description=task_description,
                task_parameters=task_parameters,
                required_capabilities=capabilities
            )
            
            if mapping:
                mappings[task_id] = mapping
            else:
                print(f"❌ Failed to map task {task_id}")
        
        return mappings
    
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
            "strategy_distribution": strategy_counts,
            "average_confidence": sum(m.confidence for m in self.mapping_cache.values()) / total_mappings if total_mappings > 0 else 0
        }
    
    def clear_cache(self):
        """Clear the mapping cache."""
        self.mapping_cache.clear()
        print("🗑️  Cleared tool mapping cache")


# Global tool mapper instance (will be created dynamically)
tool_mapper = None

def get_tool_mapper(registry=None):
    """Get or create a tool mapper instance."""
    global tool_mapper
    if tool_mapper is None or registry is not None:
        from enhanced_tool_registry import get_enhanced_tool_registry
        tool_mapper = ToolMapper(registry or get_enhanced_tool_registry())
    return tool_mapper 