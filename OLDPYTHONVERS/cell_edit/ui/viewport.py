"""
Viewport management for efficient rendering of large spreadsheets.
Handles visible area calculation and cell visibility determination.
"""

import threading
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

from core.coordinates import CellCoordinate, CellRange
from core.config import get_config


class ViewportState(Enum):
    """Viewport states."""
    IDLE = "idle"
    SCROLLING = "scrolling"
    RESIZING = "resizing"
    UPDATING = "updating"


@dataclass
class ViewportMetrics:
    """Viewport size and position metrics."""
    width: int
    height: int
    scroll_x: int
    scroll_y: int
    cell_width: int = 100
    cell_height: int = 25
    header_height: int = 30
    row_header_width: int = 60
    
    @property
    def content_width(self) -> int:
        """Width available for cell content."""
        return self.width - self.row_header_width
    
    @property
    def content_height(self) -> int:
        """Height available for cell content."""
        return self.height - self.header_height
    
    @property
    def visible_columns(self) -> int:
        """Number of visible columns."""
        return (self.content_width // self.cell_width) + 2  # +2 for partial cells
    
    @property
    def visible_rows(self) -> int:
        """Number of visible rows."""
        return (self.content_height // self.cell_height) + 2  # +2 for partial cells
    
    @property
    def first_visible_column(self) -> int:
        """First visible column index."""
        return max(0, self.scroll_x // self.cell_width)
    
    @property
    def first_visible_row(self) -> int:
        """First visible row index."""
        return max(0, self.scroll_y // self.cell_height)
    
    @property
    def last_visible_column(self) -> int:
        """Last visible column index."""
        return min(
            get_config().limits.max_columns - 1,
            self.first_visible_column + self.visible_columns
        )
    
    @property
    def last_visible_row(self) -> int:
        """Last visible row index."""
        return min(
            get_config().limits.max_rows - 1,
            self.first_visible_row + self.visible_rows
        )


@dataclass
class CellPosition:
    """Position of a cell in the viewport."""
    coordinate: CellCoordinate
    x: int
    y: int
    width: int
    height: int
    is_visible: bool
    is_partially_visible: bool


class Viewport:
    """
    Viewport for managing the visible area of a large spreadsheet.
    Handles efficient calculation of visible cells and their positions.
    """
    
    def __init__(self, metrics: ViewportMetrics):
        self.metrics = metrics
        self.state = ViewportState.IDLE
        self._lock = threading.RLock()
        
        # Caching
        self._visible_range_cache: Optional[CellRange] = None
        self._cell_positions_cache: Dict[CellCoordinate, CellPosition] = {}
        self._cache_valid = False
        
        # Performance tracking
        self._update_count = 0
        self._cache_hits = 0
        self._cache_misses = 0
    
    def update_metrics(self, metrics: ViewportMetrics) -> None:
        """Update viewport metrics."""
        with self._lock:
            old_metrics = self.metrics
            self.metrics = metrics
            
            # Invalidate cache if significant changes
            if (old_metrics.scroll_x != metrics.scroll_x or
                old_metrics.scroll_y != metrics.scroll_y or
                old_metrics.width != metrics.width or
                old_metrics.height != metrics.height):
                self._invalidate_cache()
            
            self._update_count += 1
    
    def get_visible_range(self) -> CellRange:
        """Get the range of visible cells."""
        with self._lock:
            if self._cache_valid and self._visible_range_cache:
                self._cache_hits += 1
                return self._visible_range_cache
            
            self._cache_misses += 1
            
            start = CellCoordinate(
                self.metrics.first_visible_row,
                self.metrics.first_visible_column
            )
            end = CellCoordinate(
                self.metrics.last_visible_row,
                self.metrics.last_visible_column
            )
            
            visible_range = CellRange(start, end)
            self._visible_range_cache = visible_range
            self._cache_valid = True
            
            return visible_range
    
    def get_extended_range(self, buffer_rows: int = 10, buffer_cols: int = 5) -> CellRange:
        """Get an extended range including buffer cells for smooth scrolling."""
        visible_range = self.get_visible_range()
        
        start = CellCoordinate(
            max(0, visible_range.start.row - buffer_rows),
            max(0, visible_range.start.col - buffer_cols)
        )
        end = CellCoordinate(
            min(get_config().limits.max_rows - 1, visible_range.end.row + buffer_rows),
            min(get_config().limits.max_columns - 1, visible_range.end.col + buffer_cols)
        )
        
        return CellRange(start, end)
    
    def get_cell_position(self, coordinate: CellCoordinate) -> Optional[CellPosition]:
        """Get the position of a cell in the viewport."""
        with self._lock:
            # Check cache first
            if coordinate in self._cell_positions_cache:
                self._cache_hits += 1
                return self._cell_positions_cache[coordinate]
            
            self._cache_misses += 1
            
            # Calculate position
            x = (coordinate.col * self.metrics.cell_width) - self.metrics.scroll_x + self.metrics.row_header_width
            y = (coordinate.row * self.metrics.cell_height) - self.metrics.scroll_y + self.metrics.header_height
            
            # Check visibility
            is_visible = (
                x >= self.metrics.row_header_width and
                x < self.metrics.width and
                y >= self.metrics.header_height and
                y < self.metrics.height
            )
            
            is_partially_visible = (
                x + self.metrics.cell_width > self.metrics.row_header_width and
                x < self.metrics.width and
                y + self.metrics.cell_height > self.metrics.header_height and
                y < self.metrics.height
            )
            
            position = CellPosition(
                coordinate=coordinate,
                x=x,
                y=y,
                width=self.metrics.cell_width,
                height=self.metrics.cell_height,
                is_visible=is_visible,
                is_partially_visible=is_partially_visible
            )
            
            # Cache the result
            if len(self._cell_positions_cache) < get_config().performance.viewport_cache_size:
                self._cell_positions_cache[coordinate] = position
            
            return position
    
    def get_visible_cells(self) -> List[CellPosition]:
        """Get positions of all visible cells."""
        visible_range = self.get_visible_range()
        positions = []
        
        for row in range(visible_range.start.row, visible_range.end.row + 1):
            for col in range(visible_range.start.col, visible_range.end.col + 1):
                coord = CellCoordinate(row, col)
                position = self.get_cell_position(coord)
                if position and position.is_partially_visible:
                    positions.append(position)
        
        return positions
    
    def is_cell_visible(self, coordinate: CellCoordinate) -> bool:
        """Check if a cell is visible in the viewport."""
        position = self.get_cell_position(coordinate)
        return position.is_partially_visible if position else False
    
    def scroll_to_cell(self, coordinate: CellCoordinate) -> ViewportMetrics:
        """Scroll to make a cell visible."""
        with self._lock:
            # Calculate required scroll position
            target_x = coordinate.col * self.metrics.cell_width
            target_y = coordinate.row * self.metrics.cell_height
            
            # Adjust to center the cell if possible
            center_x = target_x - (self.metrics.content_width // 2)
            center_y = target_y - (self.metrics.content_height // 2)
            
            # Clamp to valid scroll range
            max_scroll_x = max(0, (get_config().limits.max_columns * self.metrics.cell_width) - self.metrics.content_width)
            max_scroll_y = max(0, (get_config().limits.max_rows * self.metrics.cell_height) - self.metrics.content_height)
            
            new_scroll_x = max(0, min(center_x, max_scroll_x))
            new_scroll_y = max(0, min(center_y, max_scroll_y))
            
            # Update metrics
            new_metrics = ViewportMetrics(
                width=self.metrics.width,
                height=self.metrics.height,
                scroll_x=new_scroll_x,
                scroll_y=new_scroll_y,
                cell_width=self.metrics.cell_width,
                cell_height=self.metrics.cell_height,
                header_height=self.metrics.header_height,
                row_header_width=self.metrics.row_header_width
            )
            
            self.update_metrics(new_metrics)
            return new_metrics
    
    def get_cell_at_point(self, x: int, y: int) -> Optional[CellCoordinate]:
        """Get the cell coordinate at a specific point."""
        # Adjust for headers
        content_x = x - self.metrics.row_header_width
        content_y = y - self.metrics.header_height
        
        if content_x < 0 or content_y < 0:
            return None
        
        # Calculate cell coordinates
        col = (content_x + self.metrics.scroll_x) // self.metrics.cell_width
        row = (content_y + self.metrics.scroll_y) // self.metrics.cell_height
        
        # Validate bounds
        if (col >= get_config().limits.max_columns or 
            row >= get_config().limits.max_rows):
            return None
        
        return CellCoordinate(row, col)
    
    def _invalidate_cache(self) -> None:
        """Invalidate all caches."""
        self._visible_range_cache = None
        self._cell_positions_cache.clear()
        self._cache_valid = False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get viewport statistics."""
        with self._lock:
            cache_hit_rate = (
                self._cache_hits / max(1, self._cache_hits + self._cache_misses)
            )
            
            return {
                'state': self.state.value,
                'metrics': {
                    'width': self.metrics.width,
                    'height': self.metrics.height,
                    'scroll_x': self.metrics.scroll_x,
                    'scroll_y': self.metrics.scroll_y,
                    'visible_columns': self.metrics.visible_columns,
                    'visible_rows': self.metrics.visible_rows,
                    'first_visible_column': self.metrics.first_visible_column,
                    'first_visible_row': self.metrics.first_visible_row
                },
                'performance': {
                    'update_count': self._update_count,
                    'cache_hits': self._cache_hits,
                    'cache_misses': self._cache_misses,
                    'cache_hit_rate': cache_hit_rate,
                    'cached_positions': len(self._cell_positions_cache)
                }
            }


class ViewportManager:
    """
    Manager for multiple viewports (e.g., frozen panes).
    Handles coordination between different viewport areas.
    """
    
    def __init__(self):
        self.main_viewport: Optional[Viewport] = None
        self.frozen_viewports: Dict[str, Viewport] = {}
        self._lock = threading.RLock()
        
        # Freeze pane settings
        self.freeze_rows = 0
        self.freeze_columns = 0
        self.freeze_enabled = False
    
    def set_main_viewport(self, viewport: Viewport) -> None:
        """Set the main viewport."""
        with self._lock:
            self.main_viewport = viewport
    
    def enable_freeze_panes(self, rows: int = 0, columns: int = 0) -> None:
        """Enable freeze panes with specified rows and columns."""
        with self._lock:
            self.freeze_rows = rows
            self.freeze_columns = columns
            self.freeze_enabled = True
            self._update_frozen_viewports()
    
    def disable_freeze_panes(self) -> None:
        """Disable freeze panes."""
        with self._lock:
            self.freeze_enabled = False
            self.frozen_viewports.clear()
    
    def _update_frozen_viewports(self) -> None:
        """Update frozen viewport configurations."""
        if not self.main_viewport or not self.freeze_enabled:
            return
        
        main_metrics = self.main_viewport.metrics
        
        # Create frozen viewports
        if self.freeze_rows > 0:
            # Top frozen area
            frozen_metrics = ViewportMetrics(
                width=main_metrics.width,
                height=self.freeze_rows * main_metrics.cell_height + main_metrics.header_height,
                scroll_x=main_metrics.scroll_x,
                scroll_y=0,
                cell_width=main_metrics.cell_width,
                cell_height=main_metrics.cell_height,
                header_height=main_metrics.header_height,
                row_header_width=main_metrics.row_header_width
            )
            self.frozen_viewports['top'] = Viewport(frozen_metrics)
        
        if self.freeze_columns > 0:
            # Left frozen area
            frozen_metrics = ViewportMetrics(
                width=self.freeze_columns * main_metrics.cell_width + main_metrics.row_header_width,
                height=main_metrics.height,
                scroll_x=0,
                scroll_y=main_metrics.scroll_y,
                cell_width=main_metrics.cell_width,
                cell_height=main_metrics.cell_height,
                header_height=main_metrics.header_height,
                row_header_width=main_metrics.row_header_width
            )
            self.frozen_viewports['left'] = Viewport(frozen_metrics)
        
        if self.freeze_rows > 0 and self.freeze_columns > 0:
            # Top-left corner frozen area
            frozen_metrics = ViewportMetrics(
                width=self.freeze_columns * main_metrics.cell_width + main_metrics.row_header_width,
                height=self.freeze_rows * main_metrics.cell_height + main_metrics.header_height,
                scroll_x=0,
                scroll_y=0,
                cell_width=main_metrics.cell_width,
                cell_height=main_metrics.cell_height,
                header_height=main_metrics.header_height,
                row_header_width=main_metrics.row_header_width
            )
            self.frozen_viewports['corner'] = Viewport(frozen_metrics)
    
    def get_all_visible_cells(self) -> Dict[str, List[CellPosition]]:
        """Get visible cells from all viewports."""
        with self._lock:
            result = {}
            
            if self.main_viewport:
                result['main'] = self.main_viewport.get_visible_cells()
            
            for name, viewport in self.frozen_viewports.items():
                result[name] = viewport.get_visible_cells()
            
            return result
    
    def get_viewport_for_cell(self, coordinate: CellCoordinate) -> Optional[Viewport]:
        """Get the appropriate viewport for a cell."""
        with self._lock:
            if not self.freeze_enabled:
                return self.main_viewport
            
            # Check if cell is in frozen area
            if (coordinate.row < self.freeze_rows and 
                coordinate.col < self.freeze_columns and
                'corner' in self.frozen_viewports):
                return self.frozen_viewports['corner']
            elif (coordinate.row < self.freeze_rows and 
                  'top' in self.frozen_viewports):
                return self.frozen_viewports['top']
            elif (coordinate.col < self.freeze_columns and 
                  'left' in self.frozen_viewports):
                return self.frozen_viewports['left']
            else:
                return self.main_viewport
    
    def update_scroll(self, scroll_x: int, scroll_y: int) -> None:
        """Update scroll position for all viewports."""
        with self._lock:
            if self.main_viewport:
                new_metrics = ViewportMetrics(
                    width=self.main_viewport.metrics.width,
                    height=self.main_viewport.metrics.height,
                    scroll_x=scroll_x,
                    scroll_y=scroll_y,
                    cell_width=self.main_viewport.metrics.cell_width,
                    cell_height=self.main_viewport.metrics.cell_height,
                    header_height=self.main_viewport.metrics.header_height,
                    row_header_width=self.main_viewport.metrics.row_header_width
                )
                self.main_viewport.update_metrics(new_metrics)
                
                # Update frozen viewports
                if self.freeze_enabled:
                    self._update_frozen_viewports()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics for all viewports."""
        with self._lock:
            stats = {
                'freeze_enabled': self.freeze_enabled,
                'freeze_rows': self.freeze_rows,
                'freeze_columns': self.freeze_columns,
                'viewport_count': 1 + len(self.frozen_viewports)
            }
            
            if self.main_viewport:
                stats['main_viewport'] = self.main_viewport.get_statistics()
            
            for name, viewport in self.frozen_viewports.items():
                stats[f'frozen_{name}'] = viewport.get_statistics()
            
            return stats

