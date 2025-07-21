"""
Event system for reactive architecture.
Enables loose coupling between components through event-driven communication.
"""

from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import weakref
import threading
from core.coordinates import CellCoordinate, CellRange


class EventType(Enum):
    """Types of events in the system."""
    CELL_VALUE_CHANGED = "cell_value_changed"
    CELL_FORMULA_CHANGED = "cell_formula_changed"
    CELL_FORMAT_CHANGED = "cell_format_changed"
    CELL_DELETED = "cell_deleted"
    RANGE_CLEARED = "range_cleared"
    SHEET_ADDED = "sheet_added"
    SHEET_REMOVED = "sheet_removed"
    SHEET_RENAMED = "sheet_renamed"
    WORKBOOK_OPENED = "workbook_opened"
    WORKBOOK_SAVED = "workbook_saved"
    FORMULA_RECALCULATED = "formula_recalculated"
    DEPENDENCY_CHANGED = "dependency_changed"


@dataclass
class Event:
    """Base event class."""
    event_type: EventType
    source: Any
    timestamp: float
    data: Dict[str, Any]


@dataclass
class CellChangeEvent(Event):
    """Event for cell changes."""
    coordinate: CellCoordinate
    old_value: Any
    new_value: Any
    
    def __init__(self, coordinate: CellCoordinate, old_value: Any, new_value: Any, 
                 source: Any = None, data: Dict[str, Any] = None):
        import time
        super().__init__(
            event_type=EventType.CELL_VALUE_CHANGED,
            source=source,
            timestamp=time.time(),
            data=data or {}
        )
        self.coordinate = coordinate
        self.old_value = old_value
        self.new_value = new_value


@dataclass
class RangeChangeEvent(Event):
    """Event for range changes."""
    range: CellRange
    change_type: str  # 'clear', 'format', 'insert', 'delete'
    
    def __init__(self, range: CellRange, change_type: str, 
                 source: Any = None, data: Dict[str, Any] = None):
        import time
        super().__init__(
            event_type=EventType.RANGE_CLEARED,
            source=source,
            timestamp=time.time(),
            data=data or {}
        )
        self.range = range
        self.change_type = change_type


class EventManager:
    """Thread-safe event manager for the application."""
    
    def __init__(self):
        self._listeners: Dict[EventType, List[weakref.WeakMethod]] = {}
        self._lock = threading.RLock()
        self._event_queue: List[Event] = []
        self._processing = False
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """Subscribe to an event type."""
        with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            
            # Use weak reference to prevent memory leaks
            if hasattr(callback, '__self__'):
                # It's a bound method
                weak_callback = weakref.WeakMethod(callback, self._cleanup_callback)
            else:
                # It's a function - wrap it to make it compatible with WeakMethod
                weak_callback = weakref.ref(callback, self._cleanup_callback)
            
            self._listeners[event_type].append(weak_callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> bool:
        """Unsubscribe from an event type."""
        with self._lock:
            if event_type not in self._listeners:
                return False
            
            listeners = self._listeners[event_type]
            for i, weak_callback in enumerate(listeners):
                if weak_callback() == callback:
                    del listeners[i]
                    return True
            return False
    
    def emit(self, event: Event) -> None:
        """Emit an event to all subscribers."""
        with self._lock:
            self._event_queue.append(event)
            if not self._processing:
                self._process_events()
    
    def emit_sync(self, event: Event) -> None:
        """Emit an event synchronously."""
        self._notify_listeners(event)
    
    def _process_events(self) -> None:
        """Process queued events."""
        self._processing = True
        try:
            while self._event_queue:
                event = self._event_queue.pop(0)
                self._notify_listeners(event)
        finally:
            self._processing = False
    
    def _notify_listeners(self, event: Event) -> None:
        """Notify all listeners of an event."""
        if event.event_type not in self._listeners:
            return
        
        # Create a copy of listeners to avoid modification during iteration
        listeners = self._listeners[event.event_type][:]
        
        for weak_callback in listeners:
            callback = weak_callback()
            if callback is not None:
                try:
                    callback(event)
                except Exception as e:
                    # Log error but don't stop processing other listeners
                    print(f"Error in event listener: {e}")
            else:
                # Callback was garbage collected, remove it
                self._listeners[event.event_type].remove(weak_callback)
    
    def _cleanup_callback(self, weak_ref):
        """Clean up dead weak references."""
        with self._lock:
            for event_type, listeners in self._listeners.items():
                self._listeners[event_type] = [
                    listener for listener in listeners 
                    if listener() is not None
                ]
    
    def clear_listeners(self, event_type: Optional[EventType] = None) -> None:
        """Clear listeners for a specific event type or all events."""
        with self._lock:
            if event_type is None:
                self._listeners.clear()
            elif event_type in self._listeners:
                self._listeners[event_type].clear()
    
    def get_listener_count(self, event_type: EventType) -> int:
        """Get the number of active listeners for an event type."""
        with self._lock:
            if event_type not in self._listeners:
                return 0
            
            # Count only active listeners (not garbage collected)
            active_count = 0
            for weak_callback in self._listeners[event_type]:
                if weak_callback() is not None:
                    active_count += 1
            
            return active_count


# Global event manager instance
_global_event_manager = None


def get_event_manager() -> EventManager:
    """Get the global event manager instance."""
    global _global_event_manager
    if _global_event_manager is None:
        _global_event_manager = EventManager()
    return _global_event_manager


# Convenience functions for common events
def emit_cell_changed(coordinate: CellCoordinate, old_value: Any, new_value: Any, 
                     source: Any = None) -> None:
    """Emit a cell change event."""
    event = CellChangeEvent(coordinate, old_value, new_value, source)
    get_event_manager().emit(event)


def emit_range_cleared(range: CellRange, source: Any = None) -> None:
    """Emit a range cleared event."""
    event = RangeChangeEvent(range, 'clear', source)
    get_event_manager().emit(event)


def subscribe_to_cell_changes(callback: Callable[[CellChangeEvent], None]) -> None:
    """Subscribe to cell change events."""
    get_event_manager().subscribe(EventType.CELL_VALUE_CHANGED, callback)


def subscribe_to_range_changes(callback: Callable[[RangeChangeEvent], None]) -> None:
    """Subscribe to range change events."""
    get_event_manager().subscribe(EventType.RANGE_CLEARED, callback)

