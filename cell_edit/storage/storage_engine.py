"""
Unified storage engine that combines sparse matrix, lazy loading, and compression.
Provides a high-level interface for efficient cell storage and retrieval.
"""

import threading
import time
from typing import Any, Dict, Iterator, Optional, Tuple, List
from dataclasses import dataclass

from core.interfaces import ICellStorage, ICell
from core.coordinates import CellCoordinate, CellRange
from core.config import get_config
from core.events import emit_cell_changed, emit_range_cleared
from storage.sparse_matrix import SparseMatrix
from storage.lazy_loader import LazyLoader
from storage.compression import CompressionManager, CompressionType
from storage.cell import Cell, CellFactory


@dataclass
class StorageStats:
    """Storage engine statistics."""
    cell_count: int
    memory_usage: Dict[str, int]
    compression_stats: Dict[str, Any]
    lazy_loading_stats: Dict[str, Any]
    sparse_matrix_stats: Dict[str, Any]
    performance_metrics: Dict[str, float]


class StorageEngine(ICellStorage):
    """
    Unified storage engine that provides efficient cell storage with:
    - Sparse matrix for memory efficiency
    - Lazy loading for large datasets
    - Compression for space optimization
    - Automatic memory management
    """
    
    def __init__(self, enable_lazy_loading: bool = True, enable_compression: bool = True):
        self._sparse_matrix = SparseMatrix(enable_compression=enable_compression)
        self._lazy_loader = LazyLoader() if enable_lazy_loading else None
        self._compression_manager = CompressionManager()
        
        self._enable_lazy_loading = enable_lazy_loading
        self._enable_compression = enable_compression
        
        # Configuration
        config = get_config()
        self._max_cells_in_memory = config.memory.max_cells_in_memory
        self._gc_threshold = config.memory.gc_threshold
        
        # Locks for thread safety
        self._lock = threading.RWLock() if hasattr(threading, 'RWLock') else threading.RLock()
        
        # Performance tracking
        self._operation_times = {
            'get_cell': [],
            'set_cell': [],
            'delete_cell': [],
            'get_range': []
        }
        self._last_gc_time = time.time()
        self._gc_interval = 300  # 5 minutes
        
        # Memory pressure monitoring
        self._memory_pressure_callbacks = []
        
        # Start background maintenance if lazy loading is enabled
        if self._lazy_loader:
            self._start_background_maintenance()
    
    def get_cell(self, coord: CellCoordinate) -> Optional[ICell]:
        """Get a cell at the specified coordinate."""
        start_time = time.time()
        
        try:
            with self._lock:
                # Try sparse matrix first (for recently accessed cells)
                cell = self._sparse_matrix.get_cell(coord)
                if cell:
                    return cell
                
                # Try lazy loader if enabled
                if self._lazy_loader:
                    cell = self._lazy_loader.get_cell(coord)
                    if cell:
                        # Add to sparse matrix for faster future access
                        self._sparse_matrix.set_cell(coord, cell)
                        return cell
                
                return None
        
        finally:
            elapsed = time.time() - start_time
            self._operation_times['get_cell'].append(elapsed)
            self._trim_performance_history('get_cell')
    
    def set_cell(self, coord: CellCoordinate, cell: ICell) -> None:
        """Set a cell at the specified coordinate."""
        if not isinstance(cell, Cell):
            raise TypeError("Cell must be an instance of storage.Cell")
        
        start_time = time.time()
        
        try:
            with self._lock:
                # Get old cell for change event
                old_cell = self.get_cell(coord)
                old_value = old_cell.value if old_cell else None
                
                # Set in sparse matrix
                self._sparse_matrix.set_cell(coord, cell)
                
                # Set in lazy loader if enabled
                if self._lazy_loader:
                    self._lazy_loader.set_cell(coord, cell)
                
                # Emit change event
                emit_cell_changed(coord, old_value, cell.value, self)
                
                # Check memory pressure
                self._check_memory_pressure()
        
        finally:
            elapsed = time.time() - start_time
            self._operation_times['set_cell'].append(elapsed)
            self._trim_performance_history('set_cell')
    
    def delete_cell(self, coord: CellCoordinate) -> bool:
        """Delete a cell at the specified coordinate."""
        start_time = time.time()
        
        try:
            with self._lock:
                # Get old cell for change event
                old_cell = self.get_cell(coord)
                old_value = old_cell.value if old_cell else None
                
                # Delete from sparse matrix
                deleted_from_matrix = self._sparse_matrix.delete_cell(coord)
                
                # Delete from lazy loader if enabled
                deleted_from_loader = False
                if self._lazy_loader:
                    deleted_from_loader = self._lazy_loader.delete_cell(coord)
                
                success = deleted_from_matrix or deleted_from_loader
                
                if success:
                    # Emit change event
                    emit_cell_changed(coord, old_value, None, self)
                
                return success
        
        finally:
            elapsed = time.time() - start_time
            self._operation_times['delete_cell'].append(elapsed)
            self._trim_performance_history('delete_cell')
    
    def get_cells_in_range(self, cell_range: CellRange) -> Iterator[Tuple[CellCoordinate, ICell]]:
        """Get all cells within the specified range."""
        start_time = time.time()
        
        try:
            with self._lock:
                # Get from sparse matrix first
                yielded_coords = set()
                
                for coord, cell in self._sparse_matrix.get_cells_in_range(cell_range):
                    yielded_coords.add(coord)
                    yield coord, cell
                
                # Get additional cells from lazy loader if enabled
                if self._lazy_loader:
                    lazy_cells = self._lazy_loader.get_cells_in_range(cell_range)
                    for coord, cell in lazy_cells.items():
                        if coord not in yielded_coords:
                            yield coord, cell
        
        finally:
            elapsed = time.time() - start_time
            self._operation_times['get_range'].append(elapsed)
            self._trim_performance_history('get_range')
    
    def get_used_range(self) -> Optional[CellRange]:
        """Get the range containing all non-empty cells."""
        with self._lock:
            # Get range from sparse matrix
            matrix_range = self._sparse_matrix.get_used_range()
            
            # If lazy loader is enabled, we might need to expand the range
            if self._lazy_loader and matrix_range:
                # For now, assume sparse matrix contains the authoritative range
                # In a full implementation, we'd need to track the global range
                pass
            
            return matrix_range
    
    def clear_range(self, cell_range: CellRange) -> None:
        """Clear all cells in the specified range."""
        with self._lock:
            # Clear from sparse matrix
            self._sparse_matrix.clear_range(cell_range)
            
            # Clear from lazy loader if enabled
            if self._lazy_loader:
                self._lazy_loader.evict_range(cell_range)
            
            # Emit range cleared event
            emit_range_cleared(cell_range, self)
    
    def get_memory_usage(self) -> Dict[str, int]:
        """Get memory usage statistics."""
        with self._lock:
            matrix_usage = self._sparse_matrix.get_memory_usage()
            
            usage = {
                'sparse_matrix': matrix_usage['total_size'],
                'cell_count': matrix_usage['cell_count'],
                'row_count': matrix_usage['row_count']
            }
            
            if self._lazy_loader:
                loader_stats = self._lazy_loader.get_statistics()
                usage.update({
                    'lazy_loader_cache': loader_stats.get('cache_stats', {}).get('size', 0),
                    'stored_data_size': loader_stats.get('stored_data_size', 0)
                })
            
            compression_stats = self._compression_manager.get_statistics()
            usage.update({
                'compression_savings': compression_stats.get('space_saved', 0),
                'total_size': sum(v for k, v in usage.items() if k.endswith('_size') or k in ['sparse_matrix'])
            })
            
            return usage
    
    def optimize_memory(self) -> Dict[str, Any]:
        """Optimize memory usage across all storage components."""
        results = {}
        
        with self._lock:
            # Optimize sparse matrix
            matrix_results = self._sparse_matrix.optimize_memory()
            results['sparse_matrix'] = matrix_results
            
            # Force garbage collection in lazy loader
            if self._lazy_loader:
                loader_results = self._lazy_loader.force_gc()
                results['lazy_loader'] = loader_results
            
            # Get updated memory usage
            results['memory_usage_after'] = self.get_memory_usage()
            
            return results
    
    def preload_range(self, cell_range: CellRange) -> int:
        """Preload cells in a range for better performance."""
        if not self._lazy_loader:
            return 0
        
        return self._lazy_loader.preload_range(cell_range)
    
    def evict_range(self, cell_range: CellRange) -> int:
        """Evict cells in a range to free memory."""
        evicted_count = 0
        
        with self._lock:
            # Evict from lazy loader
            if self._lazy_loader:
                evicted_count += self._lazy_loader.evict_range(cell_range)
            
            # Optionally remove from sparse matrix if memory pressure is high
            if self._is_memory_pressure_high():
                # Move cells to lazy loader and remove from sparse matrix
                for coord, cell in self._sparse_matrix.get_cells_in_range(cell_range):
                    if self._lazy_loader:
                        self._lazy_loader.set_cell(coord, cell)
                    self._sparse_matrix.delete_cell(coord)
                    evicted_count += 1
        
        return evicted_count
    
    def get_statistics(self) -> StorageStats:
        """Get comprehensive storage statistics."""
        with self._lock:
            memory_usage = self.get_memory_usage()
            compression_stats = self._compression_manager.get_statistics()
            
            lazy_loading_stats = {}
            if self._lazy_loader:
                lazy_loading_stats = self._lazy_loader.get_statistics()
            
            sparse_matrix_stats = self._sparse_matrix.get_statistics()
            
            # Calculate performance metrics
            performance_metrics = {}
            for operation, times in self._operation_times.items():
                if times:
                    performance_metrics[f'{operation}_avg_time'] = sum(times) / len(times)
                    performance_metrics[f'{operation}_max_time'] = max(times)
                    performance_metrics[f'{operation}_count'] = len(times)
                else:
                    performance_metrics[f'{operation}_avg_time'] = 0.0
                    performance_metrics[f'{operation}_max_time'] = 0.0
                    performance_metrics[f'{operation}_count'] = 0
            
            return StorageStats(
                cell_count=memory_usage['cell_count'],
                memory_usage=memory_usage,
                compression_stats=compression_stats,
                lazy_loading_stats=lazy_loading_stats,
                sparse_matrix_stats=sparse_matrix_stats,
                performance_metrics=performance_metrics
            )
    
    def add_memory_pressure_callback(self, callback: callable) -> None:
        """Add a callback to be called when memory pressure is detected."""
        self._memory_pressure_callbacks.append(callback)
    
    def remove_memory_pressure_callback(self, callback: callable) -> None:
        """Remove a memory pressure callback."""
        if callback in self._memory_pressure_callbacks:
            self._memory_pressure_callbacks.remove(callback)
    
    def _check_memory_pressure(self) -> None:
        """Check for memory pressure and take action if needed."""
        current_time = time.time()
        
        # Only check periodically to avoid overhead
        if current_time - self._last_gc_time < self._gc_interval:
            return
        
        if self._is_memory_pressure_high():
            # Trigger memory optimization
            self.optimize_memory()
            
            # Call registered callbacks
            for callback in self._memory_pressure_callbacks:
                try:
                    callback()
                except Exception as e:
                    print(f"Error in memory pressure callback: {e}")
            
            self._last_gc_time = current_time
    
    def _is_memory_pressure_high(self) -> bool:
        """Check if memory pressure is high."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            memory_percent = process.memory_percent()
            return memory_percent > self._gc_threshold * 100
        except ImportError:
            # Fallback to cell count heuristic
            memory_usage = self.get_memory_usage()
            return memory_usage['cell_count'] > self._max_cells_in_memory * 0.9
    
    def _trim_performance_history(self, operation: str, max_samples: int = 1000) -> None:
        """Trim performance history to prevent unbounded growth."""
        if len(self._operation_times[operation]) > max_samples:
            # Keep only the most recent samples
            self._operation_times[operation] = self._operation_times[operation][-max_samples//2:]
    
    def _start_background_maintenance(self) -> None:
        """Start background maintenance tasks."""
        # This would typically start a background thread for maintenance
        # For now, we'll rely on periodic checks during operations
        pass
    
    def clear(self) -> None:
        """Clear all storage."""
        with self._lock:
            self._sparse_matrix.clear()
            if self._lazy_loader:
                self._lazy_loader.clear()
            
            # Reset performance tracking
            for operation in self._operation_times:
                self._operation_times[operation].clear()
    
    def __len__(self) -> int:
        """Get the total number of cells."""
        return len(self._sparse_matrix)


# Factory function for creating storage engines
def create_storage_engine(config_override: Optional[Dict[str, Any]] = None) -> StorageEngine:
    """
    Create a storage engine with optional configuration override.
    
    Args:
        config_override: Optional configuration overrides
        
    Returns:
        Configured StorageEngine instance
    """
    config = get_config()
    
    # Apply overrides
    enable_lazy_loading = config.memory.lazy_loading_enabled
    enable_compression = config.memory.compression_enabled
    
    if config_override:
        enable_lazy_loading = config_override.get('lazy_loading', enable_lazy_loading)
        enable_compression = config_override.get('compression', enable_compression)
    
    return StorageEngine(
        enable_lazy_loading=enable_lazy_loading,
        enable_compression=enable_compression
    )

