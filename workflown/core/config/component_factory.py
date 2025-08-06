"""
Component Factory

Provides dynamic component instantiation and registry management.
"""

import importlib
import inspect
from typing import Dict, Any, Type, Optional, List
from abc import ABC
from dataclasses import dataclass
from enum import Enum


class ComponentType(Enum):
    """Types of components that can be created."""
    AGENT = "agent"
    TOOL = "tool"
    STORAGE = "storage"
    MODEL = "model"
    MEMORY = "memory"
    WORKFLOW = "workflow"


@dataclass
class ComponentSpec:
    """Specification for component creation."""
    name: str
    component_type: ComponentType
    class_path: str
    config: Dict[str, Any]
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class ComponentRegistry:
    """
    Registry for managing available components.
    
    Maintains a catalog of registered components and their specifications.
    """
    
    def __init__(self):
        """Initialize the component registry."""
        self._components: Dict[ComponentType, Dict[str, ComponentSpec]] = {
            component_type: {} for component_type in ComponentType
        }
        self._instances: Dict[str, Any] = {}
        
    def register_component(self, spec: ComponentSpec) -> bool:
        """
        Register a component specification.
        
        Args:
            spec: Component specification to register
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            # Validate the class path
            module_path, class_name = spec.class_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            component_class = getattr(module, class_name)
            
            # Verify it's a valid component class
            if not self._is_valid_component_class(component_class, spec.component_type):
                print(f"Invalid component class: {spec.class_path}")
                return False
            
            # Register the component
            self._components[spec.component_type][spec.name] = spec
            return True
            
        except Exception as e:
            print(f"Error registering component {spec.name}: {e}")
            return False
    
    def unregister_component(self, component_type: ComponentType, name: str) -> bool:
        """
        Unregister a component.
        
        Args:
            component_type: Type of component
            name: Name of component to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        if name in self._components[component_type]:
            del self._components[component_type][name]
            return True
        return False
    
    def get_component_spec(self, component_type: ComponentType, name: str) -> Optional[ComponentSpec]:
        """
        Get component specification by name.
        
        Args:
            component_type: Type of component
            name: Name of component
            
        Returns:
            Component specification or None if not found
        """
        return self._components[component_type].get(name)
    
    def list_components(self, component_type: ComponentType = None) -> Dict[ComponentType, List[str]]:
        """
        List available components.
        
        Args:
            component_type: Specific component type to list (optional)
            
        Returns:
            Dictionary mapping component types to lists of names
        """
        if component_type:
            return {component_type: list(self._components[component_type].keys())}
        
        return {
            comp_type: list(components.keys())
            for comp_type, components in self._components.items()
        }
    
    def _is_valid_component_class(self, cls: Type, component_type: ComponentType) -> bool:
        """
        Validate that a class is a valid component of the specified type.
        
        Args:
            cls: Class to validate
            component_type: Expected component type
            
        Returns:
            True if valid, False otherwise
        """
        # Import base classes to check inheritance
        try:
            if component_type == ComponentType.AGENT:
                from ..agents.base_agent import BaseAgent
                return issubclass(cls, BaseAgent)
            elif component_type == ComponentType.TOOL:
                # Try to import core BaseTool, fallback to checking for execute method
                try:
                    from ..tools.base_tool import BaseTool
                    return issubclass(cls, BaseTool)
                except ImportError:
                    # If core BaseTool doesn't exist, check if class has required methods
                    return hasattr(cls, 'execute') and callable(getattr(cls, 'execute'))
            elif component_type == ComponentType.STORAGE:
                from ..storage.base_storage import BaseStorage
                return issubclass(cls, BaseStorage)
            elif component_type == ComponentType.MODEL:
                from ..models.base_model import BaseModel
                return issubclass(cls, BaseModel)
            elif component_type == ComponentType.MEMORY:
                from ..memory.base_memory import BaseMemory
                return issubclass(cls, BaseMemory)
            # Add other component types as needed
            return False
            
        except Exception:
            return False


class ComponentFactory:
    """
    Factory for creating component instances.
    
    Uses the component registry to create instances of registered components
    with proper dependency injection and configuration.
    """
    
    def __init__(self, registry: ComponentRegistry):
        """
        Initialize the component factory.
        
        Args:
            registry: Component registry to use
        """
        self.registry = registry
        self._dependency_cache: Dict[str, Any] = {}
        
    def create_component(self, component_type: ComponentType, name: str, 
                        instance_id: str = None, override_config: Dict[str, Any] = None) -> Optional[Any]:
        """
        Create a component instance.
        
        Args:
            component_type: Type of component to create
            name: Name of component (from registry)
            instance_id: Optional instance identifier
            override_config: Optional configuration overrides
            
        Returns:
            Component instance or None if creation failed
        """
        try:
            # Get component specification
            spec = self.registry.get_component_spec(component_type, name)
            if not spec:
                print(f"Component not found: {component_type.value}/{name}")
                return None
            
            # Load the component class
            module_path, class_name = spec.class_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            component_class = getattr(module, class_name)
            
            # Prepare configuration
            config = spec.config.copy()
            if override_config:
                config.update(override_config)
            
            # Create instance
            if instance_id:
                # Try different parameter names for different component types
                if component_type == ComponentType.TOOL:
                    instance = component_class(tool_id=instance_id, config=config)
                else:
                    instance = component_class(component_id=instance_id, config=config)
            else:
                instance = component_class(config=config)
            
            return instance
            
        except Exception as e:
            print(f"Error creating component {component_type.value}/{name}: {e}")
            return None
    
    def create_with_dependencies(self, component_type: ComponentType, name: str,
                                instance_id: str = None) -> Optional[Any]:
        """
        Create a component instance with automatic dependency resolution.
        
        Args:
            component_type: Type of component to create
            name: Name of component
            instance_id: Optional instance identifier
            
        Returns:
            Component instance with dependencies injected
        """
        try:
            spec = self.registry.get_component_spec(component_type, name)
            if not spec:
                return None
            
            # Resolve dependencies
            dependencies = {}
            for dep_name in spec.dependencies:
                if dep_name not in self._dependency_cache:
                    # Try to create dependency (simplified - would need more sophisticated resolution)
                    print(f"Dependency {dep_name} not available in cache")
                    continue
                dependencies[dep_name] = self._dependency_cache[dep_name]
            
            # Create instance with dependencies
            instance = self.create_component(component_type, name, instance_id)
            if instance and hasattr(instance, 'inject_dependencies'):
                instance.inject_dependencies(dependencies)
            
            return instance
            
        except Exception as e:
            print(f"Error creating component with dependencies: {e}")
            return None
    
    def register_dependency(self, name: str, instance: Any) -> None:
        """
        Register a dependency instance for injection.
        
        Args:
            name: Name of the dependency
            instance: Instance to register
        """
        self._dependency_cache[name] = instance
    
    def clear_dependencies(self) -> None:
        """Clear all registered dependencies."""
        self._dependency_cache.clear()
    
    def batch_create(self, specs: List[tuple]) -> Dict[str, Any]:
        """
        Create multiple component instances in batch.
        
        Args:
            specs: List of (component_type, name, instance_id) tuples
            
        Returns:
            Dictionary mapping instance_id to created instances
        """
        instances = {}
        
        for spec_tuple in specs:
            if len(spec_tuple) == 3:
                component_type, name, instance_id = spec_tuple
            else:
                component_type, name = spec_tuple
                instance_id = f"{component_type.value}_{name}"
            
            instance = self.create_component(component_type, name, instance_id)
            if instance:
                instances[instance_id] = instance
        
        return instances