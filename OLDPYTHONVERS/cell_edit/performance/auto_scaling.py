"""
Provides auto-scaling mechanisms for managing resources based on workload.
This is conceptual for a desktop application, focusing on dynamic resource allocation.
"""

import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.config import get_config
from performance.monitoring import get_performance_monitor


class AutoScaler:
    """
    Dynamically adjusts application resources (e.g., thread pools, cache sizes)
    based on real-time performance metrics and workload.
    """
    
    def __init__(self, check_interval_seconds: float = 5.0):
        self.check_interval = check_interval_seconds
        self._monitor = get_performance_monitor()
        self._config = get_config()

        self._scaling_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()

        self._cpu_threshold_high = self._config.get("performance.autoscale.cpu_threshold_high", 80.0)
        self._cpu_threshold_low = self._config.get("performance.autoscale.cpu_threshold_low", 30.0)
        self._memory_threshold_high = self._config.get("performance.autoscale.memory_threshold_high", 90.0)
        self._memory_threshold_low = self._config.get("performance.autoscale.memory_threshold_low", 50.0)

        self._max_worker_threads = self._config.get("performance.autoscale.max_worker_threads", 8)
        self._min_worker_threads = self._config.get("performance.autoscale.min_worker_threads", 2)
        self._current_worker_threads = self._config.get("performance.worker_threads", 4)

        print("AutoScaler initialized.")

    def start(self) -> None:
        """
        Starts the auto-scaling monitoring thread.
        """
        with self._lock:
            if self._scaling_thread and self._scaling_thread.is_alive():
                print("Auto-scaler is already running.")
                return
            
            self._stop_event.clear()
            self._scaling_thread = threading.Thread(target=self._scaling_loop)
            self._scaling_thread.daemon = True
            self._scaling_thread.start()
            print("Auto-scaler started.")

    def stop(self) -> None:
        """
        Stops the auto-scaling monitoring thread.
        """
        with self._lock:
            if self._scaling_thread and self._scaling_thread.is_alive():
                self._stop_event.set()
                self._scaling_thread.join(timeout=self.check_interval + 1)
                print("Auto-scaler stopped.")
            else:
                print("Auto-scaler is not running.")

    def _scaling_loop(self) -> None:
        """
        The main loop for checking metrics and adjusting resources.
        """
        while not self._stop_event.is_set():
            time.sleep(self.check_interval)
            if self._stop_event.is_set():
                break

            metrics = self._monitor.get_metrics()
            cpu_usage = metrics.get("cpu_usage_percent", 0.0)
            memory_usage_mb = metrics.get("memory_usage_mb", 0.0)
            total_memory_mb = psutil.virtual_memory().total / (1024 * 1024)
            memory_percent = (memory_usage_mb / total_memory_mb) * 100 if total_memory_mb > 0 else 0.0

            print(f"AutoScaler: Current CPU: {cpu_usage:.2f}%, Memory: {memory_percent:.2f}% ({memory_usage_mb:.2f}MB)")

            # Scale worker threads based on CPU usage
            if cpu_usage > self._cpu_threshold_high and self._current_worker_threads < self._max_worker_threads:
                self._current_worker_threads = min(self._current_worker_threads + 1, self._max_worker_threads)
                print(f"AutoScaler: Scaling UP worker threads to {self._current_worker_threads}")
                self._apply_resource_change()
            elif cpu_usage < self._cpu_threshold_low and self._current_worker_threads > self._min_worker_threads:
                self._current_worker_threads = max(self._current_worker_threads - 1, self._min_worker_threads)
                print(f"AutoScaler: Scaling DOWN worker threads to {self._current_worker_threads}")
                self._apply_resource_change()

            # Future: Scale cache sizes based on memory usage
            # if memory_percent > self._memory_threshold_high:
            #     print("AutoScaler: Memory usage high, consider reducing cache sizes.")
            # elif memory_percent < self._memory_threshold_low:
            #     print("AutoScaler: Memory usage low, consider increasing cache sizes.")

    def _apply_resource_change(self) -> None:
        """
        Applies the calculated resource changes to the application.
        This would involve updating actual thread pools, cache configurations, etc.
        """
        # In a real application, this would interact with a global thread pool manager
        # or update configuration values that are then picked up by relevant components.
        self._config.set("performance.worker_threads", self._current_worker_threads)
        print(f"  (Resource change applied: performance.worker_threads = {self._current_worker_threads})")
        # Trigger an event so other components can react to the change
        # get_event_manager().publish(EventType.RESOURCE_SCALED, new_worker_threads=self._current_worker_threads)

    def cleanup(self) -> None:
        """
        Stops the auto-scaler and cleans up resources.
        """
        self.stop()


# Global instance for AutoScaler
_global_auto_scaler: Optional[AutoScaler] = None

def get_auto_scaler(check_interval_seconds: float = 5.0) -> AutoScaler:
    """
    Returns the global AutoScaler instance.
    """
    global _global_auto_scaler
    if _global_auto_scaler is None:
        _global_auto_scaler = AutoScaler(check_interval_seconds)
    return _global_auto_scaler


# Example Usage (requires psutil to be installed: pip install psutil)
if __name__ == '__main__':
    # Mock get_config and get_performance_monitor for standalone testing
    class MockConfig:
        def __init__(self):
            self._config = {
                "performance.autoscale.cpu_threshold_high": 80.0,
                "performance.autoscale.cpu_threshold_low": 30.0,
                "performance.autoscale.memory_threshold_high": 90.0,
                "performance.autoscale.memory_threshold_low": 50.0,
                "performance.autoscale.max_worker_threads": 8,
                "performance.autoscale.min_worker_threads": 2,
                "performance.worker_threads": 4,
            }
        def get(self, key, default=None):
            return self._config.get(key, default)
        def set(self, key, value):
            self._config[key] = value

    class MockPerformanceMonitor:
        def __init__(self):
            self._cpu_usage = 50.0
            self._memory_usage_mb = 1024.0 # 1GB

        def get_metrics(self):
            # Simulate fluctuating CPU/memory usage
            self._cpu_usage = max(0, min(100, self._cpu_usage + random.uniform(-5, 5)))
            self._memory_usage_mb = max(512, min(4096, self._memory_usage_mb + random.uniform(-100, 100)))
            return {
                "cpu_usage_percent": self._cpu_usage,
                "memory_usage_mb": self._memory_usage_mb,
                "fps": 60.0,
                "event_rates": {}
            }

    import random
    import os
    import sys

    # Temporarily replace global functions for testing
    sys.modules["__main__"].get_config = lambda: MockConfig()
    sys.modules["__main__"].get_performance_monitor = lambda: MockPerformanceMonitor()

    # Ensure psutil is available for the example to run
    try:
        import psutil
    except ImportError:
        print("psutil not installed. Please install it (pip install psutil) to run this example.")
        sys.exit(1)

    scaler = AutoScaler(check_interval_seconds=1.0)
    scaler.start()

    print("Running auto-scaler for 10 seconds...")
    time.sleep(10)

    scaler.stop()
    print("Auto-scaler stopped.")
    scaler.cleanup()


