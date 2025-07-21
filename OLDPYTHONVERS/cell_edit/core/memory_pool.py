"""
Memory pool for efficient object allocation and reuse.
Reduces garbage collection pressure and improves performance.
"""

import threading
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
from collections import deque
import weakref
import gc

T = TypeVar('T')


class ObjectPool(Generic[T]):
    """Generic object pool for efficient object reuse."""
    
    def __init__(self, factory: callable, max_size: int = 1000, 
                 reset_func: Optional[callable] = None):
        """
        Initialize object pool.
        
        Args:
            factory: Function to create new objects
            max_size: Maximum number of objects to keep in pool
            reset_func: Function to reset object state before reuse
        """
        self._factory = factory
        self._max_size = max_size
        self._reset_func = reset_func
        self._pool: deque = deque()
        self._lock = threading.Lock()
        self._created_count = 0
        self._reused_count = 0
    
    def acquire(self) -> T:
        """Acquire an object from the pool."""
        with self._lock:
            if self._pool:
                obj = self._pool.popleft()
                if self._reset_func:
                    self._reset_func(obj)
                self._reused_count += 1
                return obj
            else:
                obj = self._factory()
                self._created_count += 1
                return obj
    
    def release(self, obj: T) -> None:
        """Release an object back to the pool."""
        with self._lock:
            if len(self._pool) < self._max_size:
                self._pool.append(obj)
    
    def clear(self) -> None:
        """Clear all objects from the pool."""
        with self._lock:
            self._pool.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """Get pool statistics."""
        with self._lock:
            return {
                'pool_size': len(self._pool),
                'max_size': self._max_size,
                'created_count': self._created_count,
                'reused_count': self._reused_count,
                'hit_ratio': self._reused_count / max(1, self._created_count + self._reused_count)
            }


class CellPool:
    """Specialized pool for cell objects."""
    
    def __init__(self, max_size: int = 10000):
        from ..storage.cell import Cell  # Import here to avoid circular imports
        
        def create_cell():
            return Cell()
        
        def reset_cell(cell):
            cell.clear()
        
        self._pool = ObjectPool(create_cell, max_size, reset_cell)
    
    def acquire_cell(self):
        """Acquire a cell from the pool."""
        return self._pool.acquire()
    
    def release_cell(self, cell) -> None:
        """Release a cell back to the pool."""
        self._pool.release(cell)
    
    def get_stats(self) -> Dict[str, int]:
        """Get pool statistics."""
        return self._pool.get_stats()


class MemoryManager:
    """Central memory manager for the application."""
    
    def __init__(self):
        self._pools: Dict[str, ObjectPool] = {}
        self._lock = threading.RLock()
        self._memory_limit = 1024 * 1024 * 1024  # 1GB default
        self._gc_threshold = 0.8
        self._monitoring_enabled = True
        
        # Weak references to track allocated objects
        self._tracked_objects: weakref.WeakSet = weakref.WeakSet()
    
    def register_pool(self, name: str, pool: ObjectPool) -> None:
        """Register an object pool."""
        with self._lock:
            self._pools[name] = pool
    
    def get_pool(self, name: str) -> Optional[ObjectPool]:
        """Get a registered object pool."""
        with self._lock:
            return self._pools.get(name)
    
    def set_memory_limit(self, limit_bytes: int) -> None:
        """Set the memory limit for the application."""
        self._memory_limit = limit_bytes
    
    def set_gc_threshold(self, threshold: float) -> None:
        """Set the garbage collection threshold (0.0 to 1.0)."""
        self._gc_threshold = max(0.0, min(1.0, threshold))
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage statistics."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        pool_stats = {}
        with self._lock:
            for name, pool in self._pools.items():
                pool_stats[name] = pool.get_stats()
        
        return {
            'rss': memory_info.rss,  # Resident Set Size
            'vms': memory_info.vms,  # Virtual Memory Size
            'percent': process.memory_percent(),
            'limit': self._memory_limit,
            'tracked_objects': len(self._tracked_objects),
            'pools': pool_stats
        }
    
    def check_memory_pressure(self) -> bool:
        """Check if memory usage is above threshold."""
        try:
            usage = self.get_memory_usage()
            return usage['rss'] > (self._memory_limit * self._gc_threshold)
        except:
            return False
    
    def force_gc(self) -> Dict[str, int]:
        """Force garbage collection and return statistics."""
        # Clear all pools first
        with self._lock:
            for pool in self._pools.values():
                pool.clear()
        
        # Run garbage collection
        collected = gc.collect()
        
        return {
            'collected_objects': collected,
            'remaining_objects': len(gc.get_objects())
        }
    
    def track_object(self, obj: Any) -> None:
        """Track an object for memory monitoring."""
        if self._monitoring_enabled:
            self._tracked_objects.add(obj)
    
    def enable_monitoring(self, enabled: bool = True) -> None:
        """Enable or disable memory monitoring."""
        self._monitoring_enabled = enabled
        if not enabled:
            self._tracked_objects.clear()
    
    def cleanup(self) -> None:
        """Clean up all resources."""
        with self._lock:
            for pool in self._pools.values():
                pool.clear()
            self._pools.clear()
        self._tracked_objects.clear()


# Global memory manager instance
_global_memory_manager = None


def get_memory_manager() -> MemoryManager:
    """Get the global memory manager instance."""
    global _global_memory_manager
    if _global_memory_manager is None:
        _global_memory_manager = MemoryManager()
        
        # Register default pools
        cell_pool = CellPool()
        _global_memory_manager.register_pool('cells', cell_pool._pool)
    
    return _global_memory_manager


def acquire_cell():
    """Convenience function to acquire a cell from the global pool."""
    manager = get_memory_manager()
    cell_pool = manager.get_pool('cells')
    if cell_pool:
        return cell_pool.acquire()
    else:
        # Fallback to direct creation
        from ..storage.cell import Cell
        return Cell()


def release_cell(cell) -> None:
    """Convenience function to release a cell to the global pool."""
    manager = get_memory_manager()
    cell_pool = manager.get_pool('cells')
    if cell_pool:
        cell_pool.release(cell)


# Context manager for automatic object release
class PooledObject:
    """Context manager for automatic object release to pool."""
    
    def __init__(self, pool: ObjectPool):
        self._pool = pool
        self._obj = None
    
    def __enter__(self):
        self._obj = self._pool.acquire()
        return self._obj
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._obj is not None:
            self._pool.release(self._obj)
            self._obj = None

