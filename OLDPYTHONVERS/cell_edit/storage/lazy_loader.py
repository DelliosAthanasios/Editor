"""
Lazy loading system for efficient memory usage.
Loads cell data on-demand and manages memory pressure.
"""

import threading
import time
import weakref
from typing import Any, Dict, Optional, Callable, Set, Tuple
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
import pickle
import zlib

from core.coordinates import CellCoordinate, CellRange
from core.config import get_config
from core.events import get_event_manager, EventType
from storage.cell import Cell


class LoadState(Enum):
    """States for lazy-loaded data."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    EVICTED = "evicted"
    ERROR = "error"


@dataclass
class CellData:
    """Serializable cell data for lazy loading."""
    value: Any
    formula: Optional[str]
    format_data: Optional[Dict[str, Any]]
    cell_type: str
    version: int
    last_modified: float
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes."""
        return pickle.dumps(self)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'CellData':
        """Deserialize from bytes."""
        return pickle.loads(data)
    
    @classmethod
    def from_cell(cls, cell: Cell) -> 'CellData':
        """Create from a Cell instance."""
        format_data = cell.format.to_dict() if cell.format else None
        return cls(
            value=cell._value,
            formula=cell._formula,
            format_data=format_data,
            cell_type=cell.data_type,
            version=cell.version,
            last_modified=cell._last_modified
        )


class LazyCell:
    """Lazy-loaded cell wrapper."""
    
    def __init__(self, coord: CellCoordinate, loader: 'LazyLoader'):
        self.coord = coord
        self._loader = weakref.ref(loader)
        self._cell: Optional[Cell] = None
        self._state = LoadState.UNLOADED
        self._last_access = time.time()
        self._access_count = 0
        self._lock = threading.RLock()
    
    @property
    def cell(self) -> Optional[Cell]:
        """Get the actual cell, loading if necessary."""
        with self._lock:
            if self._state == LoadState.UNLOADED:
                self._load()
            elif self._state == LoadState.EVICTED:
                self._reload()
            
            self._last_access = time.time()
            self._access_count += 1
            return self._cell
    
    @property
    def is_loaded(self) -> bool:
        """Check if the cell is currently loaded."""
        return self._state == LoadState.LOADED and self._cell is not None
    
    @property
    def state(self) -> LoadState:
        """Get the current load state."""
        return self._state
    
    def evict(self) -> bool:
        """Evict the cell from memory."""
        with self._lock:
            if self._state == LoadState.LOADED and self._cell is not None:
                # Save cell data before evicting
                loader = self._loader()
                if loader:
                    loader._save_cell_data(self.coord, self._cell)
                
                self._cell = None
                self._state = LoadState.EVICTED
                return True
            return False
    
    def _load(self) -> None:
        """Load the cell data."""
        if self._state == LoadState.LOADING:
            return  # Already loading
        
        self._state = LoadState.LOADING
        try:
            loader = self._loader()
            if loader:
                self._cell = loader._load_cell_data(self.coord)
                self._state = LoadState.LOADED if self._cell else LoadState.ERROR
            else:
                self._state = LoadState.ERROR
        except Exception as e:
            print(f"Error loading cell {self.coord}: {e}")
            self._state = LoadState.ERROR
    
    def _reload(self) -> None:
        """Reload evicted cell data."""
        self._state = LoadState.UNLOADED
        self._load()


class LRUCache:
    """LRU cache for managing loaded cells."""
    
    def __init__(self, max_size: int):
        self.max_size = max_size
        self._cache: OrderedDict[CellCoordinate, LazyCell] = OrderedDict()
        self._lock = threading.RLock()
    
    def get(self, coord: CellCoordinate) -> Optional[LazyCell]:
        """Get a cell from cache."""
        with self._lock:
            if coord in self._cache:
                # Move to end (most recently used)
                lazy_cell = self._cache.pop(coord)
                self._cache[coord] = lazy_cell
                return lazy_cell
            return None
    
    def put(self, coord: CellCoordinate, lazy_cell: LazyCell) -> None:
        """Put a cell in cache."""
        with self._lock:
            if coord in self._cache:
                # Update existing
                self._cache.pop(coord)
            elif len(self._cache) >= self.max_size:
                # Evict least recently used
                oldest_coord, oldest_cell = self._cache.popitem(last=False)
                oldest_cell.evict()
            
            self._cache[coord] = lazy_cell
    
    def remove(self, coord: CellCoordinate) -> Optional[LazyCell]:
        """Remove a cell from cache."""
        with self._lock:
            return self._cache.pop(coord, None)
    
    def clear(self) -> None:
        """Clear all cached cells."""
        with self._lock:
            for lazy_cell in self._cache.values():
                lazy_cell.evict()
            self._cache.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        with self._lock:
            loaded_count = sum(1 for cell in self._cache.values() if cell.is_loaded)
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'loaded_count': loaded_count,
                'evicted_count': len(self._cache) - loaded_count
            }


class LazyLoader:
    """
    Lazy loading system for cell data.
    Manages memory pressure by loading/unloading cells on demand.
    """
    
    def __init__(self, storage_backend: Optional[Callable] = None):
        self._storage_backend = storage_backend
        self._cache = LRUCache(get_config().memory.cell_cache_size)
        self._cell_data: Dict[CellCoordinate, bytes] = {}  # Compressed cell data
        self._lock = threading.RWLock() if hasattr(threading, 'RWLock') else threading.RLock()
        
        # Statistics
        self._load_count = 0
        self._hit_count = 0
        self._eviction_count = 0
        
        # Memory pressure monitoring
        self._memory_pressure_threshold = get_config().memory.gc_threshold
        self._last_gc_time = time.time()
        self._gc_interval = 60  # seconds
        
        # Subscribe to memory pressure events
        event_manager = get_event_manager()
        event_manager.subscribe(EventType.CELL_VALUE_CHANGED, self._on_cell_changed)
    
    def get_cell(self, coord: CellCoordinate) -> Optional[Cell]:
        """Get a cell, loading lazily if needed."""
        self._load_count += 1
        
        # Check cache first
        lazy_cell = self._cache.get(coord)
        if lazy_cell:
            self._hit_count += 1
            return lazy_cell.cell
        
        # Check if we have stored data
        with self._lock:
            if coord in self._cell_data:
                # Create lazy cell and add to cache
                lazy_cell = LazyCell(coord, self)
                self._cache.put(coord, lazy_cell)
                return lazy_cell.cell
        
        return None
    
    def set_cell(self, coord: CellCoordinate, cell: Cell) -> None:
        """Set a cell with lazy loading support."""
        # Create lazy cell
        lazy_cell = LazyCell(coord, self)
        lazy_cell._cell = cell
        lazy_cell._state = LoadState.LOADED
        
        # Add to cache
        self._cache.put(coord, lazy_cell)
        
        # Save compressed data
        self._save_cell_data(coord, cell)
        
        # Check memory pressure
        self._check_memory_pressure()
    
    def delete_cell(self, coord: CellCoordinate) -> bool:
        """Delete a cell."""
        with self._lock:
            # Remove from cache
            lazy_cell = self._cache.remove(coord)
            
            # Remove stored data
            if coord in self._cell_data:
                del self._cell_data[coord]
                return True
            
            return lazy_cell is not None
    
    def get_cells_in_range(self, cell_range: CellRange) -> Dict[CellCoordinate, Cell]:
        """Get all cells in a range, loading as needed."""
        result = {}
        
        with self._lock:
            for coord in cell_range:
                if coord in self._cell_data:
                    cell = self.get_cell(coord)
                    if cell:
                        result[coord] = cell
        
        return result
    
    def preload_range(self, cell_range: CellRange) -> int:
        """Preload cells in a range for better performance."""
        loaded_count = 0
        
        for coord in cell_range:
            if self.get_cell(coord):
                loaded_count += 1
        
        return loaded_count
    
    def evict_range(self, cell_range: CellRange) -> int:
        """Evict cells in a range to free memory."""
        evicted_count = 0
        
        for coord in cell_range:
            lazy_cell = self._cache.get(coord)
            if lazy_cell and lazy_cell.evict():
                evicted_count += 1
        
        return evicted_count
    
    def force_gc(self) -> Dict[str, int]:
        """Force garbage collection of unused cells."""
        stats = {'evicted': 0, 'freed_memory': 0}
        
        # Get memory usage before
        import psutil
        import os
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss
        
        # Evict least recently used cells
        cache_stats = self._cache.get_stats()
        target_evictions = max(0, cache_stats['loaded_count'] - cache_stats['max_size'] // 2)
        
        with self._lock:
            coords_to_evict = []
            for coord, lazy_cell in self._cache._cache.items():
                if lazy_cell.is_loaded and len(coords_to_evict) < target_evictions:
                    coords_to_evict.append(coord)
            
            for coord in coords_to_evict:
                lazy_cell = self._cache.get(coord)
                if lazy_cell and lazy_cell.evict():
                    stats['evicted'] += 1
        
        # Get memory usage after
        memory_after = process.memory_info().rss
        stats['freed_memory'] = max(0, memory_before - memory_after)
        
        self._eviction_count += stats['evicted']
        self._last_gc_time = time.time()
        
        return stats
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get loader statistics."""
        cache_stats = self._cache.get_stats()
        
        with self._lock:
            stored_data_size = sum(len(data) for data in self._cell_data.values())
        
        return {
            'load_count': self._load_count,
            'hit_count': self._hit_count,
            'hit_ratio': self._hit_count / max(1, self._load_count),
            'eviction_count': self._eviction_count,
            'cache_stats': cache_stats,
            'stored_data_count': len(self._cell_data),
            'stored_data_size': stored_data_size,
            'last_gc_time': self._last_gc_time
        }
    
    def _save_cell_data(self, coord: CellCoordinate, cell: Cell) -> None:
        """Save cell data in compressed format."""
        try:
            cell_data = CellData.from_cell(cell)
            serialized = cell_data.to_bytes()
            
            # Compress if beneficial
            config = get_config()
            if config.memory.compression_enabled:
                compressed = zlib.compress(serialized, level=config.storage.compression_level)
                if len(compressed) < len(serialized) * 0.8:
                    serialized = compressed
            
            with self._lock:
                self._cell_data[coord] = serialized
        
        except Exception as e:
            print(f"Error saving cell data for {coord}: {e}")
    
    def _load_cell_data(self, coord: CellCoordinate) -> Optional[Cell]:
        """Load cell data from storage."""
        try:
            with self._lock:
                if coord not in self._cell_data:
                    return None
                
                data = self._cell_data[coord]
            
            # Try to decompress
            try:
                decompressed = zlib.decompress(data)
                data = decompressed
            except zlib.error:
                pass  # Data wasn't compressed
            
            # Deserialize
            cell_data = CellData.from_bytes(data)
            
            # Create cell
            from storage.cell import CellFormat
            cell_format = CellFormat.from_dict(cell_data.format_data) if cell_data.format_data else None
            
            cell = Cell(
                value=cell_data.value,
                formula=cell_data.formula,
                cell_format=cell_format
            )
            
            return cell
        
        except Exception as e:
            print(f"Error loading cell data for {coord}: {e}")
            return None
    
    def _check_memory_pressure(self) -> None:
        """Check and respond to memory pressure."""
        # Only check periodically to avoid overhead
        current_time = time.time()
        if current_time - self._last_gc_time < self._gc_interval:
            return
        
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            memory_percent = process.memory_percent()
            
            if memory_percent > self._memory_pressure_threshold * 100:
                # High memory pressure, force GC
                self.force_gc()
        
        except ImportError:
            # psutil not available, use basic heuristic
            cache_stats = self._cache.get_stats()
            if cache_stats['loaded_count'] > cache_stats['max_size'] * 0.9:
                self.force_gc()
    
    def _on_cell_changed(self, event) -> None:
        """Handle cell change events."""
        # Update stored data when cell changes
        if hasattr(event, 'coordinate') and hasattr(event, 'source'):
            coord = event.coordinate
            if isinstance(event.source, Cell):
                self._save_cell_data(coord, event.source)
    
    def clear(self) -> None:
        """Clear all loaded and stored data."""
        self._cache.clear()
        with self._lock:
            self._cell_data.clear()
        
        self._load_count = 0
        self._hit_count = 0
        self._eviction_count = 0

