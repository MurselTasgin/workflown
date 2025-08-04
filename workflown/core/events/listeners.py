"""
Event Listeners and Handlers

Provides base classes and interfaces for event handling in the framework.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Callable, Optional
import asyncio
from .event_bus import Event


class EventListener(ABC):
    """
    Abstract base class for event listeners.
    
    Event listeners can subscribe to specific event types and
    handle them when they occur.
    """
    
    def __init__(self, listener_id: str = None):
        """
        Initialize the event listener.
        
        Args:
            listener_id: Unique identifier for this listener
        """
        self.listener_id = listener_id or f"listener_{id(self)}"
        self.subscriptions: Dict[str, str] = {}  # event_type -> subscription_id
        self.is_active = False
    
    @abstractmethod
    def get_event_types(self) -> List[str]:
        """
        Get the list of event types this listener is interested in.
        
        Returns:
            List of event type strings
        """
        pass
    
    @abstractmethod
    async def handle_event(self, event: Event) -> None:
        """
        Handle an incoming event.
        
        Args:
            event: Event to handle
        """
        pass
    
    def should_handle_event(self, event: Event) -> bool:
        """
        Determine if this listener should handle the given event.
        
        Args:
            event: Event to check
            
        Returns:
            True if this listener should handle the event
        """
        return event.event_type in self.get_event_types()
    
    async def on_event_received(self, event: Event) -> None:
        """
        Called when an event is received. Checks if it should be handled.
        
        Args:
            event: Received event
        """
        if self.should_handle_event(event):
            try:
                await self.handle_event(event)
            except Exception as e:
                print(f"Error handling event {event.event_type} in {self.listener_id}: {e}")


class BaseEventHandler:
    """
    Base event handler with common functionality.
    
    Provides a simple implementation for handling events with
    callback functions.
    """
    
    def __init__(self, handler_id: str = None):
        """
        Initialize the event handler.
        
        Args:
            handler_id: Unique identifier for this handler
        """
        self.handler_id = handler_id or f"handler_{id(self)}"
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.async_handlers: Dict[str, List[Callable]] = {}
    
    def register_handler(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """
        Register a synchronous event handler.
        
        Args:
            event_type: Type of event to handle
            handler: Handler function
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def register_async_handler(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """
        Register an asynchronous event handler.
        
        Args:
            event_type: Type of event to handle
            handler: Async handler function
        """
        if event_type not in self.async_handlers:
            self.async_handlers[event_type] = []
        self.async_handlers[event_type].append(handler)
    
    def unregister_handler(self, event_type: str, handler: Callable) -> bool:
        """
        Unregister an event handler.
        
        Args:
            event_type: Type of event
            handler: Handler function to remove
            
        Returns:
            True if handler was found and removed
        """
        if event_type in self.event_handlers and handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
            return True
        
        if event_type in self.async_handlers and handler in self.async_handlers[event_type]:
            self.async_handlers[event_type].remove(handler)
            return True
        
        return False
    
    async def handle_event(self, event: Event) -> None:
        """
        Handle an event by calling registered handlers.
        
        Args:
            event: Event to handle
        """
        # Handle synchronous handlers
        if event.event_type in self.event_handlers:
            for handler in self.event_handlers[event.event_type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"Error in sync handler for {event.event_type}: {e}")
        
        # Handle asynchronous handlers
        if event.event_type in self.async_handlers:
            tasks = []
            for handler in self.async_handlers[event.event_type]:
                try:
                    task = asyncio.create_task(handler(event))
                    tasks.append(task)
                except Exception as e:
                    print(f"Error creating async handler task for {event.event_type}: {e}")
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_registered_event_types(self) -> List[str]:
        """
        Get list of event types that have registered handlers.
        
        Returns:
            List of event type strings
        """
        sync_types = set(self.event_handlers.keys())
        async_types = set(self.async_handlers.keys())
        return list(sync_types | async_types)


class LoggingEventListener(EventListener):
    """
    Event listener that logs all events.
    
    Useful for debugging and monitoring system activity.
    """
    
    def __init__(self, listener_id: str = "logging_listener", 
                 event_types: List[str] = None, log_level: str = "INFO"):
        """
        Initialize the logging event listener.
        
        Args:
            listener_id: Unique identifier for this listener
            event_types: List of event types to log (None for all)
            log_level: Logging level
        """
        super().__init__(listener_id)
        self.target_event_types = event_types
        self.log_level = log_level
    
    def get_event_types(self) -> List[str]:
        """Get event types to listen for."""
        if self.target_event_types:
            return self.target_event_types
        # Return common event types if none specified
        return [
            "system.startup",
            "system.shutdown", 
            "agent.task_started",
            "agent.task_completed",
            "model.inference_completed",
            "chat.message_received",
            "chat.message_sent"
        ]
    
    async def handle_event(self, event: Event) -> None:
        """
        Handle event by logging it.
        
        Args:
            event: Event to log
        """
        log_message = f"[{event.timestamp}] {event.event_type} from {event.source}"
        
        # Add relevant data
        if "error" in event.data:
            log_message += f" - ERROR: {event.data['error']}"
        elif "task_id" in event.data:
            log_message += f" - Task: {event.data['task_id']}"
        elif "message_id" in event.data:
            log_message += f" - Message: {event.data['message_id']}"
        
        print(f"📝 {log_message}")


class MetricsEventListener(EventListener):
    """
    Event listener that collects metrics from events.
    
    Tracks performance metrics and system statistics.
    """
    
    def __init__(self, listener_id: str = "metrics_listener"):
        """Initialize the metrics event listener."""
        super().__init__(listener_id)
        self.metrics: Dict[str, Any] = {
            "event_counts": {},
            "execution_times": [],
            "error_counts": {},
            "agent_activity": {},
            "model_usage": {}
        }
    
    def get_event_types(self) -> List[str]:
        """Get event types for metrics collection."""
        return [
            "agent.task_started",
            "agent.task_completed",
            "agent.task_failed",
            "model.inference_completed",
            "tool.executed",
            "system.error"
        ]
    
    async def handle_event(self, event: Event) -> None:
        """
        Handle event by collecting metrics.
        
        Args:
            event: Event to process for metrics
        """
        # Count events
        event_type = event.event_type
        if event_type not in self.metrics["event_counts"]:
            self.metrics["event_counts"][event_type] = 0
        self.metrics["event_counts"][event_type] += 1
        
        # Track execution times
        if "execution_time" in event.data:
            self.metrics["execution_times"].append({
                "event_type": event_type,
                "execution_time": event.data["execution_time"],
                "timestamp": event.timestamp
            })
        
        # Track errors
        if "error" in event.data or event_type.endswith("failed") or event_type.endswith("error"):
            if event_type not in self.metrics["error_counts"]:
                self.metrics["error_counts"][event_type] = 0
            self.metrics["error_counts"][event_type] += 1
        
        # Track agent activity
        if "agent_id" in event.data:
            agent_id = event.data["agent_id"]
            if agent_id not in self.metrics["agent_activity"]:
                self.metrics["agent_activity"][agent_id] = {"tasks": 0, "errors": 0}
            
            if event_type == "agent.task_completed":
                self.metrics["agent_activity"][agent_id]["tasks"] += 1
            elif event_type == "agent.task_failed":
                self.metrics["agent_activity"][agent_id]["errors"] += 1
        
        # Track model usage
        if "model_id" in event.data:
            model_id = event.data["model_id"]
            if model_id not in self.metrics["model_usage"]:
                self.metrics["model_usage"][model_id] = {"calls": 0, "total_time": 0.0}
            
            self.metrics["model_usage"][model_id]["calls"] += 1
            if "execution_time" in event.data:
                self.metrics["model_usage"][model_id]["total_time"] += event.data["execution_time"]
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of collected metrics.
        
        Returns:
            Dictionary containing metrics summary
        """
        return {
            "total_events": sum(self.metrics["event_counts"].values()),
            "event_types": len(self.metrics["event_counts"]),
            "total_errors": sum(self.metrics["error_counts"].values()),
            "active_agents": len(self.metrics["agent_activity"]),
            "active_models": len(self.metrics["model_usage"]),
            "avg_execution_time": (
                sum(item["execution_time"] for item in self.metrics["execution_times"]) / 
                len(self.metrics["execution_times"])
            ) if self.metrics["execution_times"] else 0.0
        }