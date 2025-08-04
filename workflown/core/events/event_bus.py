"""
Event Bus Implementation

Provides asynchronous event-driven communication between components.
"""

import asyncio
from typing import Dict, List, Any, Callable, Optional, Type
from dataclasses import dataclass
from datetime import datetime
import uuid
import weakref
from enum import Enum


class EventPriority(Enum):
    """Priority levels for events."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Event:
    """Base event class for the event system."""
    event_type: str
    source: str
    data: Dict[str, Any]
    timestamp: datetime
    event_id: str = None
    priority: EventPriority = EventPriority.NORMAL
    correlation_id: Optional[str] = None
    
    def __post_init__(self):
        if self.event_id is None:
            self.event_id = str(uuid.uuid4())


EventHandler = Callable[[Event], None]
AsyncEventHandler = Callable[[Event], asyncio.Task]


class EventBus:
    """
    Asynchronous event bus for component communication.
    
    Supports event publishing, subscription, filtering, and priority handling.
    """
    
    def __init__(self, max_queue_size: int = 1000):
        """
        Initialize the event bus.
        
        Args:
            max_queue_size: Maximum size of the event queue
        """
        self.max_queue_size = max_queue_size
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._async_handlers: Dict[str, List[AsyncEventHandler]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._is_running = False
        self._processor_task: Optional[asyncio.Task] = None
        self._event_history: List[Event] = []
        self._max_history_size = 1000
        
        # Weak references to avoid memory leaks
        self._weak_handlers: Dict[str, List] = {}
        
    async def start(self) -> None:
        """Start the event bus processor."""
        if self._is_running:
            return
            
        self._is_running = True
        self._processor_task = asyncio.create_task(self._process_events())
    
    async def stop(self) -> None:
        """Stop the event bus processor."""
        if not self._is_running:
            return
            
        self._is_running = False
        
        # Cancel processor task
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        # Clear remaining events
        while not self._event_queue.empty():
            try:
                self._event_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
    
    def subscribe(self, event_type: str, handler: EventHandler) -> str:
        """
        Subscribe to events of a specific type.
        
        Args:
            event_type: Type of events to listen for
            handler: Function to call when event occurs
            
        Returns:
            Subscription ID for unsubscribing
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        self._handlers[event_type].append(handler)
        subscription_id = f"{event_type}_{len(self._handlers[event_type])}"
        
        return subscription_id
    
    def subscribe_async(self, event_type: str, handler: AsyncEventHandler) -> str:
        """
        Subscribe to events with an async handler.
        
        Args:
            event_type: Type of events to listen for
            handler: Async function to call when event occurs
            
        Returns:
            Subscription ID for unsubscribing
        """
        if event_type not in self._async_handlers:
            self._async_handlers[event_type] = []
        
        self._async_handlers[event_type].append(handler)
        subscription_id = f"{event_type}_async_{len(self._async_handlers[event_type])}"
        
        return subscription_id
    
    def unsubscribe(self, event_type: str, handler: EventHandler) -> bool:
        """
        Unsubscribe a handler from events.
        
        Args:
            event_type: Type of events to stop listening for
            handler: Handler function to remove
            
        Returns:
            True if handler was found and removed, False otherwise
        """
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            return True
        
        if event_type in self._async_handlers and handler in self._async_handlers[event_type]:
            self._async_handlers[event_type].remove(handler)
            return True
        
        return False
    
    async def publish(self, event: Event) -> bool:
        """
        Publish an event to the bus.
        
        Args:
            event: Event to publish
            
        Returns:
            True if event was queued successfully, False otherwise
        """
        if not self._is_running:
            return False
        
        try:
            # Add to queue with priority handling
            await self._event_queue.put(event)
            return True
            
        except asyncio.QueueFull:
            # Handle queue full based on event priority
            if event.priority in [EventPriority.HIGH, EventPriority.CRITICAL]:
                # Try to make room by removing low priority events
                await self._make_room_for_priority_event(event)
                try:
                    await self._event_queue.put(event)
                    return True
                except asyncio.QueueFull:
                    return False
            return False
    
    async def publish_sync(self, event: Event) -> None:
        """
        Publish an event and process it synchronously.
        
        Args:
            event: Event to publish and process
        """
        await self._handle_event(event)
    
    def get_event_history(self, event_type: str = None, limit: int = 100) -> List[Event]:
        """
        Get recent event history.
        
        Args:
            event_type: Filter by event type (optional)
            limit: Maximum number of events to return
            
        Returns:
            List of recent events
        """
        events = self._event_history
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return events[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get event bus statistics.
        
        Returns:
            Dictionary containing statistics
        """
        return {
            "is_running": self._is_running,
            "queue_size": self._event_queue.qsize(),
            "max_queue_size": self.max_queue_size,
            "total_handlers": sum(len(handlers) for handlers in self._handlers.values()),
            "total_async_handlers": sum(len(handlers) for handlers in self._async_handlers.values()),
            "event_types": list(set(self._handlers.keys()) | set(self._async_handlers.keys())),
            "history_size": len(self._event_history)
        }
    
    async def _process_events(self) -> None:
        """Main event processing loop."""
        while self._is_running:
            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._handle_event(event)
                
            except asyncio.TimeoutError:
                # Continue loop - allows for clean shutdown
                continue
            except Exception as e:
                print(f"Error processing event: {e}")
    
    async def _handle_event(self, event: Event) -> None:
        """
        Handle a single event by calling all registered handlers.
        
        Args:
            event: Event to handle
        """
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history_size:
            self._event_history.pop(0)
        
        # Handle synchronous handlers
        if event.event_type in self._handlers:
            for handler in self._handlers[event.event_type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"Error in event handler: {e}")
        
        # Handle asynchronous handlers
        if event.event_type in self._async_handlers:
            tasks = []
            for handler in self._async_handlers[event.event_type]:
                try:
                    task = asyncio.create_task(handler(event))
                    tasks.append(task)
                except Exception as e:
                    print(f"Error creating async handler task: {e}")
            
            # Wait for all async handlers to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _make_room_for_priority_event(self, priority_event: Event) -> None:
        """
        Make room in the queue for a priority event by removing low priority events.
        
        Args:
            priority_event: High priority event that needs to be queued
        """
        # This is a simplified implementation
        # In a real implementation, you might want to maintain a priority queue
        try:
            # Try to remove one event to make room
            removed_event = self._event_queue.get_nowait()
            print(f"Removed event {removed_event.event_id} to make room for priority event")
        except asyncio.QueueEmpty:
            pass