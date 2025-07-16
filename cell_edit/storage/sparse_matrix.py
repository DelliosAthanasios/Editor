"""
Sparse matrix implementation for efficient cell storage.
Only stores non-empty cells to minimize memory usage.
"""

import threading
from typing import Any, Dict, Iterator, Optional, Tuple, Set
from collections import defaultdict
import bisect
import weakref

from core.interfaces import ICellStorage, ICell
from core.coordinates import CellCoordinate, CellRange
from core.config import get_config
from storage.cell import Cell


class SparseRow:
    """Sparse row implementation using sorted list for efficient access."""
    
    def __init__(self):
        self._columns: Dict[int, Cell] = {}
        self._sorted_cols: list = []  # Sorted list of column indices
        self._lock = threading.RLock()
    
    def set_cell(self, col: int, cell: Cell) -> None:
        """Set a cell in this row."""
        with self._lock:
            if col not in self._columns:
                bisect.insort(self._sorted_cols, col)
            self._columns[col] = cell
    
    def get_cell(self, col: int) -> Optional[Cell]:
        """Get a cell from this row."""
        with self._lock:
            return self._columns.get(col)
    
    def delete_cell(self, col: int) -> bool:
        """Delete a cell from this row."""
        with self._lock:
            if col in self._columns:
                del self._columns[col]
                self._sorted_cols.remove(col)
                return True
            return False
    
    def get_used_columns(self) -> list:
        """Get list of used column indices."""
        with self._lock:
            return self._sorted_cols.copy()
    
    def get_min_col(self) -> Optional[int]:
        """Get minimum used column index."""
        with self._lock:
            return self._sorted_cols[0] if self._sorted_cols else None
    
    def get_max_col(self) -> Optional[int]:
        """Get maximum used column index."""
        with self._lock:
            return self._sorted_cols[-1] if self._sorted_cols else None
    
    def is_empty(self) -> bool:
        """Check if row is empty."""
        with self._lock:
            return len(self._columns) == 0
    
    def clear(self) -> None:
        """Clear all cells in this row."""
        with self._lock:
            self._columns.clear()
            self._sorted_cols.clear()
    
    def get_cells_in_range(self, start_col: int, end_col: int) -> Iterator[Tuple[int, Cell]]:
        """Get all cells in column range."""
        with self._lock:
            # Find start and end indices in sorted list
            start_idx = bisect.bisect_left(self._sorted_cols, start_col)
            end_idx = bisect.bisect_right(self._sorted_cols, end_col)
            
            for i in range(start_idx, end_idx):
                col = self._sorted_cols[i]
                yield col, self._columns[col]
    
    def get_memory_usage(self) -> Dict[str, int]:
        """Get memory usage statistics."""
        import sys
        with self._lock:
            cell_memory = sum(cell.get_memory_usage()['total_size'] for cell in self._columns.values())
            return {
                'row_overhead': sys.getsizeof(self) + sys.getsizeof(self._columns) + sys.getsizeof(self._sorted_cols),
                'cell_memory': cell_memory,
                'cell_count': len(self._columns),
                'total_size': sys.getsizeof(self) + sys.getsizeof(self._columns) + sys.getsizeof(self._sorted_cols) + cell_memory
            }


class SparseMatrix(ICellStorage):
    """
    Sparse matrix implementation for efficient cell storage.
    Uses a two-level dictionary structure: row -> column -> cell.
    """
    
    def __init__(self, enable_compression: bool = True):
        self._rows: Dict[int, SparseRow] = {}
        self._sorted_rows: list = []  # Sorted list of row indices
        self._lock = threading.RWLock() if hasattr(threading, 'RWLock') else threading.RLock()
        self._enable_compression = enable_compression
        self._cell_count = 0
        self._memory_usage_cache = None
        self._cache_dirty = True
        
        # Statistics
        self._access_count = 0
        self._hit_count = 0
        
        # Clustering for spatial locality
        self._clusters: Dict[Tuple[int, int], Set[CellCoordinate]] = defaultdict(set)
        self._cluster_size = 100  # Cells per cluster
    
    def get_cell(self, coord: CellCoordinate) -> Optional[ICell]:
        """Get a cell at the specified coordinate."""
        self._access_count += 1
        
        with self._lock:
            row = self._rows.get(coord.row)
            if row:
                cell = row.get_cell(coord.col)
                if cell:
                    self._hit_count += 1
                    return cell
        
        return None
    
    def set_cell(self, coord: CellCoordinate, cell: ICell) -> None:
        """Set a cell at the specified coordinate."""
        if not isinstance(cell, Cell):
            raise TypeError("Cell must be an instance of storage.Cell")
        
        with self._lock:
            # Get or create row
            if coord.row not in self._rows:
                self._rows[coord.row] = SparseRow()
                bisect.insort(self._sorted_rows, coord.row)
            
            row = self._rows[coord.row]
            
            # Check if cell already exists
            existing_cell = row.get_cell(coord.col)
            if existing_cell is None:
                self._cell_count += 1
            
            row.set_cell(coord.col, cell)
            
            # Update clustering
            self._update_cluster(coord)
            
            # Compress cell if enabled and beneficial
            if self._enable_compression:
                cell.compress()
            
            self._cache_dirty = True
    
    def delete_cell(self, coord: CellCoordinate) -> bool:
        """Delete a cell at the specified coordinate."""
        with self._lock:
            row = self._rows.get(coord.row)
            if row and row.delete_cell(coord.col):
                self._cell_count -= 1
                
                # Remove empty row
                if row.is_empty():
                    del self._rows[coord.row]
                    self._sorted_rows.remove(coord.row)
                
                # Update clustering
                self._remove_from_cluster(coord)
                
                self._cache_dirty = True
                return True
        
        return False
    
    def get_cells_in_range(self, cell_range: CellRange) -> Iterator[Tuple[CellCoordinate, ICell]]:
        """Get all cells within the specified range."""
        with self._lock:
            # Find start and end row indices
            start_row_idx = bisect.bisect_left(self._sorted_rows, cell_range.start.row)
            end_row_idx = bisect.bisect_right(self._sorted_rows, cell_range.end.row)
            
            for i in range(start_row_idx, end_row_idx):
                row_num = self._sorted_rows[i]
                row = self._rows[row_num]
                
                for col_num, cell in row.get_cells_in_range(cell_range.start.col, cell_range.end.col):
                    coord = CellCoordinate(row_num, col_num)
                    yield coord, cell
    
    def get_used_range(self) -> Optional[CellRange]:
        """Get the range containing all non-empty cells."""
        with self._lock:
            if not self._sorted_rows:
                return None
            
            min_row = self._sorted_rows[0]
            max_row = self._sorted_rows[-1]
            
            min_col = float('inf')
            max_col = float('-inf')
            
            for row_num in self._sorted_rows:
                row = self._rows[row_num]
                row_min_col = row.get_min_col()
                row_max_col = row.get_max_col()
                
                if row_min_col is not None:
                    min_col = min(min_col, row_min_col)
                if row_max_col is not None:
                    max_col = max(max_col, row_max_col)
            
            if min_col == float('inf'):
                return None
            
            return CellRange.from_coordinates(min_row, min_col, max_row, max_col)
    
    def clear_range(self, cell_range: CellRange) -> None:
        """Clear all cells in the specified range."""
        coords_to_delete = []
        
        # Collect coordinates to delete
        for coord, _ in self.get_cells_in_range(cell_range):
            coords_to_delete.append(coord)
        
        # Delete cells
        for coord in coords_to_delete:
            self.delete_cell(coord)
    
    def get_memory_usage(self) -> Dict[str, int]:
        """Get memory usage statistics."""
        if not self._cache_dirty and self._memory_usage_cache:
            return self._memory_usage_cache.copy()
        
        with self._lock:
            import sys
            
            # Calculate row overhead
            row_overhead = sum(row.get_memory_usage()['row_overhead'] for row in self._rows.values())
            
            # Calculate cell memory
            cell_memory = sum(row.get_memory_usage()['cell_memory'] for row in self._rows.values())
            
            # Calculate structure overhead
            structure_overhead = (
                sys.getsizeof(self._rows) +
                sys.getsizeof(self._sorted_rows) +
                sys.getsizeof(self._clusters)
            )
            
            usage = {
                'structure_overhead': structure_overhead,
                'row_overhead': row_overhead,
                'cell_memory': cell_memory,
                'cell_count': self._cell_count,
                'row_count': len(self._rows),
                'total_size': structure_overhead + row_overhead + cell_memory,
                'hit_ratio': self._hit_count / max(1, self._access_count),
                'compression_enabled': self._enable_compression
            }
            
            self._memory_usage_cache = usage
            self._cache_dirty = False
            
            return usage.copy()
    
    def optimize_memory(self) -> Dict[str, int]:
        """Optimize memory usage by compressing cells and cleaning up."""
        compressed_count = 0
        freed_memory = 0
        
        with self._lock:
            for row in self._rows.values():
                for col, cell in row._columns.items():
                    if cell.compress():
                        compressed_count += 1
                        # Estimate freed memory (rough approximation)
                        freed_memory += cell.get_memory_usage().get('compressed_size', 0)
        
        # Force cache refresh
        self._cache_dirty = True
        
        return {
            'compressed_cells': compressed_count,
            'estimated_freed_memory': freed_memory
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics about the sparse matrix."""
        with self._lock:
            memory_usage = self.get_memory_usage()
            
            # Calculate density
            used_range = self.get_used_range()
            if used_range:
                total_possible_cells = used_range.cell_count
                density = self._cell_count / total_possible_cells if total_possible_cells > 0 else 0
            else:
                density = 0
            
            return {
                'cell_count': self._cell_count,
                'row_count': len(self._rows),
                'density': density,
                'memory_usage': memory_usage,
                'access_count': self._access_count,
                'hit_ratio': self._hit_count / max(1, self._access_count),
                'cluster_count': len(self._clusters),
                'used_range': used_range.to_a1() if used_range else None
            }
    
    def _update_cluster(self, coord: CellCoordinate) -> None:
        """Update clustering information for spatial locality."""
        cluster_row = coord.row // self._cluster_size
        cluster_col = coord.col // self._cluster_size
        cluster_key = (cluster_row, cluster_col)
        
        self._clusters[cluster_key].add(coord)
    
    def _remove_from_cluster(self, coord: CellCoordinate) -> None:
        """Remove coordinate from clustering information."""
        cluster_row = coord.row // self._cluster_size
        cluster_col = coord.col // self._cluster_size
        cluster_key = (cluster_row, cluster_col)
        
        if cluster_key in self._clusters:
            self._clusters[cluster_key].discard(coord)
            if not self._clusters[cluster_key]:
                del self._clusters[cluster_key]
    
    def get_cluster_info(self, coord: CellCoordinate) -> Set[CellCoordinate]:
        """Get all coordinates in the same cluster as the given coordinate."""
        cluster_row = coord.row // self._cluster_size
        cluster_col = coord.col // self._cluster_size
        cluster_key = (cluster_row, cluster_col)
        
        return self._clusters.get(cluster_key, set()).copy()
    
    def clear(self) -> None:
        """Clear all cells from the matrix."""
        with self._lock:
            self._rows.clear()
            self._sorted_rows.clear()
            self._clusters.clear()
            self._cell_count = 0
            self._access_count = 0
            self._hit_count = 0
            self._cache_dirty = True
    
    def __len__(self) -> int:
        """Get the number of cells in the matrix."""
        return self._cell_count
    
    def __contains__(self, coord: CellCoordinate) -> bool:
        """Check if a coordinate has a cell."""
        return self.get_cell(coord) is not None


# Thread-safe RWLock implementation for Python versions that don't have it
if not hasattr(threading, 'RWLock'):
    class RWLock:
        """Simple read-write lock implementation."""
        
        def __init__(self):
            self._read_ready = threading.Condition(threading.RLock())
            self._readers = 0
        
        def acquire_read(self):
            self._read_ready.acquire()
            try:
                self._readers += 1
            finally:
                self._read_ready.release()
        
        def release_read(self):
            self._read_ready.acquire()
            try:
                self._readers -= 1
                if self._readers == 0:
                    self._read_ready.notifyAll()
            finally:
                self._read_ready.release()
        
        def acquire_write(self):
            self._read_ready.acquire()
            while self._readers > 0:
                self._read_ready.wait()
        
        def release_write(self):
            self._read_ready.release()
        
        def __enter__(self):
            self.acquire_write()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.release_write()
    
    threading.RWLock = RWLock

