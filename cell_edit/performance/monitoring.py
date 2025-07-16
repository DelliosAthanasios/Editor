"""
Provides real-time performance monitoring capabilities for the Cell Editor.
Collects and visualizes metrics like CPU usage, memory, FPS, and event rates.
"""

import time
import threading
import psutil # Requires psutil to be installed
from collections import deque
from typing import Any, Callable, Dict, List, Optional, Tuple

from performance.profiling import MemoryProfiler, CPUProfiler
from core.events import get_event_manager, EventType


class PerformanceMonitor:
    """
    Collects and provides real-time performance metrics.
    """
    
    def __init__(self, update_interval_seconds: float = 1.0, history_size: int = 60):
        self.update_interval = update_interval_seconds
        self.history_size = history_size
        
        self._cpu_usage_history = deque(maxlen=history_size)
        self._memory_usage_history = deque(maxlen=history_size)
        self._fps_history = deque(maxlen=history_size) # For UI FPS
        self._event_rate_history: Dict[EventType, deque] = {}

        self._last_frame_time = time.perf_counter()
        self._frame_count = 0
        self._event_counts: Dict[EventType, int] = {}

        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()

        # Subscribe to relevant events for event rate monitoring
        for event_type in EventType:
            self._event_rate_history[event_type] = deque(maxlen=history_size)
            self._event_counts[event_type] = 0
            get_event_manager().subscribe(event_type, self._on_event_triggered)

    def _on_event_triggered(self, event_type: EventType, *args, **kwargs) -> None:
        """
        Increments the counter for a specific event type.
        """
        with self._lock:
            self._event_counts[event_type] += 1

    def start(self) -> None:
        """
        Starts the performance monitoring thread.
        """
        with self._lock:
            if self._monitor_thread and self._monitor_thread.is_alive():
                print("Performance monitor is already running.")
                return
            
            self._stop_event.clear()
            self._monitor_thread = threading.Thread(target=self._monitor_loop)
            self._monitor_thread.daemon = True
            self._monitor_thread.start()
            print("Performance monitoring started.")

    def stop(self) -> None:
        """
        Stops the performance monitoring thread.
        """
        with self._lock:
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._stop_event.set()
                self._monitor_thread.join(timeout=self.update_interval + 1)
                print("Performance monitoring stopped.")
            else:
                print("Performance monitor is not running.")

    def _monitor_loop(self) -> None:
        """
        The main loop for collecting system metrics.
        """
        process = psutil.Process(os.getpid())
        while not self._stop_event.is_set():
            with self._lock:
                # CPU Usage (percentage)
                cpu_percent = process.cpu_percent(interval=None) # Non-blocking
                self._cpu_usage_history.append(cpu_percent)

                # Memory Usage (MB)
                memory_info = process.memory_info()
                rss_mb = memory_info.rss / (1024 * 1024) # Resident Set Size
                self._memory_usage_history.append(rss_mb)

                # Event Rates
                for event_type in EventType:
                    rate = self._event_counts[event_type] / self.update_interval
                    self._event_rate_history[event_type].append(rate)
                    self._event_counts[event_type] = 0 # Reset for next interval

            time.sleep(self.update_interval)

    def record_frame(self) -> None:
        """
        Call this method at the end of each UI frame to calculate FPS.
        """
        with self._lock:
            self._frame_count += 1
            current_time = time.perf_counter()
            elapsed_time = current_time - self._last_frame_time
            if elapsed_time >= self.update_interval:
                fps = self._frame_count / elapsed_time
                self._fps_history.append(fps)
                self._frame_count = 0
                self._last_frame_time = current_time

    def get_metrics(self) -> Dict[str, Any]:
        """
        Returns the latest collected performance metrics.
        """
        with self._lock:
            metrics = {
                "cpu_usage_percent": self._cpu_usage_history[-1] if self._cpu_usage_history else 0.0,
                "memory_usage_mb": self._memory_usage_history[-1] if self._memory_usage_history else 0.0,
                "fps": self._fps_history[-1] if self._fps_history else 0.0,
                "event_rates": {event_type.value: self._event_rate_history[event_type][-1] 
                                for event_type in EventType if self._event_rate_history[event_type]}
            }
            return metrics

    def get_history(self) -> Dict[str, List[float]]:
        """
        Returns the historical performance metrics.
        """
        with self._lock:
            history = {
                "cpu_usage_percent": list(self._cpu_usage_history),
                "memory_usage_mb": list(self._memory_usage_history),
                "fps": list(self._fps_history),
                "event_rates": {event_type.value: list(self._event_rate_history[event_type]) 
                                for event_type in EventType}
            }
            return history

    def cleanup(self) -> None:
        """
        Stops the monitor and cleans up resources.
        """
        self.stop()
        for event_type in EventType:
            get_event_manager().unsubscribe(event_type, self._on_event_triggered)


# Global instance for PerformanceMonitor
_global_performance_monitor: Optional[PerformanceMonitor] = None

def get_performance_monitor(update_interval_seconds: float = 1.0, history_size: int = 60) -> PerformanceMonitor:
    """
    Returns the global PerformanceMonitor instance.
    """
    global _global_performance_monitor
    if _global_performance_monitor is None:
        _global_performance_monitor = PerformanceMonitor(update_interval_seconds, history_size)
    return _global_performance_monitor


# Example Usage (requires psutil to be installed: pip install psutil)
if __name__ == '__main__':
    # Mock EventManager and EventType for standalone testing
    class MockEventManager:
        def __init__(self):
            self._subscribers = {}

        def subscribe(self, event_type, handler):
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)

        def unsubscribe(self, event_type, handler):
            if event_type in self._subscribers and handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)

        def publish(self, event_type, *args, **kwargs):
            if event_type in self._subscribers:
                for handler in self._subscribers[event_type]:
                    handler(event_type, *args, **kwargs)

    class MockEventType:
        CELL_VALUE_CHANGED = "cell_value_changed"
        SHEET_ADDED = "sheet_added"
        # Add other event types as needed for testing

    # Replace global event manager for testing
    # In a real app, you'd ensure get_event_manager() returns the actual one
    # For this test, we'll just use a local mock
    _mock_event_manager = MockEventManager()
    _mock_event_type = MockEventType()

    # To make the example runnable without actual event manager setup
    # This is a hack for standalone execution, not for production code
    import sys
    sys.modules["__main__"].get_event_manager = lambda: _mock_event_manager
    sys.modules["__main__"].EventType = _mock_event_type

    monitor = PerformanceMonitor(update_interval_seconds=0.5, history_size=10)
    monitor.start()

    print("Monitoring performance for 5 seconds...")
    for i in range(10):
        time.sleep(0.5) # Simulate main loop work
        monitor.record_frame() # Simulate UI frame rendering
        
        # Simulate some events
        if i % 2 == 0:
            _mock_event_manager.publish(_mock_event_type.CELL_VALUE_CHANGED, sheet_name="Sheet1", coordinate=(0,0), new_value="test")
        if i % 3 == 0:
            _mock_event_manager.publish(_mock_event_type.SHEET_ADDED, sheet_name=f"Sheet{i}")

        metrics = monitor.get_metrics()
        print(f"CPU: {metrics["cpu_usage_percent"]:.2f}%, Mem: {metrics["memory_usage_mb"]:.2f}MB, FPS: {metrics["fps"]:.2f}")
        # print(f"  Event Rates: {metrics["event_rates"]}")

    monitor.stop()
    print("Monitoring stopped.")
    print("Final Metrics:", monitor.get_metrics())
    print("Historical CPU:", monitor.get_history()["cpu_usage_percent"])
    monitor.cleanup()


