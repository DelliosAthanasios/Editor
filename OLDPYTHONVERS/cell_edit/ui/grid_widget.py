"""
Grid widget for the main spreadsheet display.
Combines viewport, scroller, and renderer for complete grid functionality.
"""

import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from dataclasses import dataclass
from enum import Enum

from core.coordinates import CellCoordinate, CellRange
from core.interfaces import ISheet
from core.config import get_config
from core.events import get_event_manager, EventType, CellChangeEvent
from storage.cell import Cell
from ui.viewport import Viewport, ViewportManager, ViewportMetrics
from ui.virtual_scroller import VirtualScroller, ScrollEvent, ScrollMode
from ui.cell_renderer import CellRenderer, CellRenderData, RenderingContext, RenderingMode


class SelectionMode(Enum):
    """Selection modes."""
    SINGLE_CELL = "single_cell"
    RANGE = "range"
    MULTIPLE_RANGES = "multiple_ranges"
    ROW = "row"
    COLUMN = "column"


class EditMode(Enum):
    """Edit modes."""
    VIEW = "view"
    EDIT = "edit"
    FORMULA_BAR = "formula_bar"


@dataclass
class Selection:
    """Represents a selection in the grid."""
    ranges: List[CellRange]
    active_cell: CellCoordinate
    mode: SelectionMode
    
    def contains(self, coordinate: CellCoordinate) -> bool:
        """Check if a coordinate is in the selection."""
        return any(coord in cell_range for cell_range in self.ranges)
    
    def get_all_cells(self) -> Set[CellCoordinate]:
        """Get all cells in the selection."""
        cells = set()
        for cell_range in self.ranges:
            cells.update(cell_range)
        return cells


@dataclass
class GridState:
    """Current state of the grid."""
    selection: Selection
    edit_mode: EditMode
    editing_cell: Optional[CellCoordinate]
    show_formulas: bool
    show_gridlines: bool
    zoom_level: float
    freeze_rows: int
    freeze_columns: int


class GridWidget:
    """
    Main grid widget that combines all components for spreadsheet display.
    Handles user interaction, selection, editing, and rendering coordination.
    """
    
    def __init__(self, sheet: ISheet, width: int = 800, height: int = 600):
        self.sheet = sheet
        
        # Initialize components
        self.viewport_manager = ViewportManager()
        self.cell_renderer = CellRenderer()
        
        # Create main viewport
        metrics = ViewportMetrics(width=width, height=height, scroll_x=0, scroll_y=0)
        self.main_viewport = Viewport(metrics)
        self.viewport_manager.set_main_viewport(self.main_viewport)
        
        # Create virtual scroller
        self.scroller = VirtualScroller(self.main_viewport, self._on_scroll_update)
        
        # Grid state
        self.state = GridState(
            selection=Selection(
                ranges=[CellRange(CellCoordinate(0, 0), CellCoordinate(0, 0))],
                active_cell=CellCoordinate(0, 0),
                mode=SelectionMode.SINGLE_CELL
            ),
            edit_mode=EditMode.VIEW,
            editing_cell=None,
            show_formulas=False,
            show_gridlines=True,
            zoom_level=1.0,
            freeze_rows=0,
            freeze_columns=0
        )
        
        # Rendering context
        self.rendering_context = RenderingContext(
            mode=RenderingMode.NORMAL,
            show_gridlines=self.state.show_gridlines,
            show_formulas=self.state.show_formulas
        )
        
        # Event callbacks
        self.on_cell_selected: Optional[Callable[[CellCoordinate], None]] = None
        self.on_cell_edited: Optional[Callable[[CellCoordinate, str], None]] = None
        self.on_selection_changed: Optional[Callable[[Selection], None]] = None
        
        # Threading
        self._lock = threading.RLock()
        self._render_lock = threading.RLock()
        
        # Performance tracking
        self._render_count = 0
        self._last_render_time = 0.0
        self._interaction_count = 0
        
        # Subscribe to events
        event_manager = get_event_manager()
        event_manager.subscribe(EventType.CELL_VALUE_CHANGED, self._on_cell_changed)
        event_manager.subscribe(EventType.CELL_FORMULA_CHANGED, self._on_cell_changed)
    
    def resize(self, width: int, height: int) -> None:
        """Resize the grid widget."""
        with self._lock:
            new_metrics = ViewportMetrics(
                width=width,
                height=height,
                scroll_x=self.main_viewport.metrics.scroll_x,
                scroll_y=self.main_viewport.metrics.scroll_y,
                cell_width=self.main_viewport.metrics.cell_width,
                cell_height=self.main_viewport.metrics.cell_height,
                header_height=self.main_viewport.metrics.header_height,
                row_header_width=self.main_viewport.metrics.row_header_width
            )
            
            self.main_viewport.update_metrics(new_metrics)
            self.viewport_manager.update_scroll(new_metrics.scroll_x, new_metrics.scroll_y)
    
    def set_zoom(self, zoom_level: float) -> None:
        """Set zoom level."""
        with self._lock:
            zoom_level = max(0.25, min(4.0, zoom_level))  # Clamp zoom
            self.state.zoom_level = zoom_level
            
            # Update cell dimensions
            base_width = get_config().ui.default_cell_width
            base_height = get_config().ui.default_cell_height
            
            new_cell_width = int(base_width * zoom_level)
            new_cell_height = int(base_height * zoom_level)
            
            new_metrics = ViewportMetrics(
                width=self.main_viewport.metrics.width,
                height=self.main_viewport.metrics.height,
                scroll_x=self.main_viewport.metrics.scroll_x,
                scroll_y=self.main_viewport.metrics.scroll_y,
                cell_width=new_cell_width,
                cell_height=new_cell_height,
                header_height=self.main_viewport.metrics.header_height,
                row_header_width=self.main_viewport.metrics.row_header_width
            )
            
            self.main_viewport.update_metrics(new_metrics)
            
            # Update rendering context
            self.rendering_context.scale_factor = zoom_level
    
    def scroll_to_cell(self, coordinate: CellCoordinate, mode: ScrollMode = ScrollMode.SMOOTH) -> None:
        """Scroll to make a cell visible."""
        self.scroller.scroll_to_cell(coordinate.row, coordinate.col, mode)
    
    def select_cell(self, coordinate: CellCoordinate, extend_selection: bool = False) -> None:
        """Select a single cell."""
        with self._lock:
            self._interaction_count += 1
            
            if extend_selection and self.state.selection.mode == SelectionMode.RANGE:
                # Extend current selection
                current_range = self.state.selection.ranges[0]
                new_range = CellRange(current_range.start, coordinate)
                self.state.selection.ranges = [new_range]
            else:
                # New selection
                self.state.selection = Selection(
                    ranges=[CellRange(coordinate, coordinate)],
                    active_cell=coordinate,
                    mode=SelectionMode.SINGLE_CELL
                )
            
            # Scroll to cell if not visible
            if not self.main_viewport.is_cell_visible(coordinate):
                self.scroll_to_cell(coordinate)
            
            # Notify callback
            if self.on_cell_selected:
                self.on_cell_selected(coordinate)
            if self.on_selection_changed:
                self.on_selection_changed(self.state.selection)
    
    def select_range(self, start: CellCoordinate, end: CellCoordinate) -> None:
        """Select a range of cells."""
        with self._lock:
            self._interaction_count += 1
            
            cell_range = CellRange(start, end)
            self.state.selection = Selection(
                ranges=[cell_range],
                active_cell=start,
                mode=SelectionMode.RANGE
            )
            
            # Scroll to start cell if not visible
            if not self.main_viewport.is_cell_visible(start):
                self.scroll_to_cell(start)
            
            # Notify callback
            if self.on_selection_changed:
                self.on_selection_changed(self.state.selection)
    
    def select_row(self, row: int) -> None:
        """Select an entire row."""
        with self._lock:
            start = CellCoordinate(row, 0)
            end = CellCoordinate(row, get_config().limits.max_columns - 1)
            
            self.state.selection = Selection(
                ranges=[CellRange(start, end)],
                active_cell=start,
                mode=SelectionMode.ROW
            )
            
            if self.on_selection_changed:
                self.on_selection_changed(self.state.selection)
    
    def select_column(self, col: int) -> None:
        """Select an entire column."""
        with self._lock:
            start = CellCoordinate(0, col)
            end = CellCoordinate(get_config().limits.max_rows - 1, col)
            
            self.state.selection = Selection(
                ranges=[CellRange(start, end)],
                active_cell=start,
                mode=SelectionMode.COLUMN
            )
            
            if self.on_selection_changed:
                self.on_selection_changed(self.state.selection)
    
    def start_edit(self, coordinate: Optional[CellCoordinate] = None) -> None:
        """Start editing a cell."""
        with self._lock:
            if coordinate is None:
                coordinate = self.state.selection.active_cell
            
            self.state.edit_mode = EditMode.EDIT
            self.state.editing_cell = coordinate
            
            # Select the cell being edited
            self.select_cell(coordinate)
    
    def end_edit(self, save_changes: bool = True, new_value: str = "") -> None:
        """End cell editing."""
        with self._lock:
            if self.state.edit_mode != EditMode.EDIT or not self.state.editing_cell:
                return
            
            if save_changes and new_value and self.on_cell_edited:
                self.on_cell_edited(self.state.editing_cell, new_value)
            
            self.state.edit_mode = EditMode.VIEW
            self.state.editing_cell = None
    
    def handle_key_press(self, key: str, modifiers: List[str] = None) -> bool:
        """Handle keyboard input."""
        if modifiers is None:
            modifiers = []
        
        with self._lock:
            current_cell = self.state.selection.active_cell
            
            # Navigation keys
            if key == "ArrowUp":
                new_cell = CellCoordinate(max(0, current_cell.row - 1), current_cell.col)
                self.select_cell(new_cell, "Shift" in modifiers)
                return True
            
            elif key == "ArrowDown":
                max_row = get_config().limits.max_rows - 1
                new_cell = CellCoordinate(min(max_row, current_cell.row + 1), current_cell.col)
                self.select_cell(new_cell, "Shift" in modifiers)
                return True
            
            elif key == "ArrowLeft":
                new_cell = CellCoordinate(current_cell.row, max(0, current_cell.col - 1))
                self.select_cell(new_cell, "Shift" in modifiers)
                return True
            
            elif key == "ArrowRight":
                max_col = get_config().limits.max_columns - 1
                new_cell = CellCoordinate(current_cell.row, min(max_col, current_cell.col + 1))
                self.select_cell(new_cell, "Shift" in modifiers)
                return True
            
            # Page navigation
            elif key == "PageUp":
                self.scroller.page_up()
                return True
            
            elif key == "PageDown":
                self.scroller.page_down()
                return True
            
            elif key == "Home":
                if "Ctrl" in modifiers:
                    self.select_cell(CellCoordinate(0, 0))
                else:
                    self.select_cell(CellCoordinate(current_cell.row, 0))
                return True
            
            elif key == "End":
                if "Ctrl" in modifiers:
                    # Go to last used cell (simplified)
                    self.select_cell(CellCoordinate(100, 100))
                else:
                    # Go to end of row (simplified)
                    self.select_cell(CellCoordinate(current_cell.row, 100))
                return True
            
            # Edit keys
            elif key == "F2":
                self.start_edit()
                return True
            
            elif key == "Enter":
                if self.state.edit_mode == EditMode.EDIT:
                    self.end_edit(save_changes=True)
                else:
                    # Move down
                    max_row = get_config().limits.max_rows - 1
                    new_cell = CellCoordinate(min(max_row, current_cell.row + 1), current_cell.col)
                    self.select_cell(new_cell)
                return True
            
            elif key == "Escape":
                if self.state.edit_mode == EditMode.EDIT:
                    self.end_edit(save_changes=False)
                return True
            
            elif key == "Delete":
                # Delete cell contents
                if self.on_cell_edited:
                    for cell_range in self.state.selection.ranges:
                        for coord in cell_range:
                            self.on_cell_edited(coord, "")
                return True
            
            # View toggles
            elif key == "F9" and "Ctrl" in modifiers:
                self.toggle_formulas()
                return True
            
            return False
    
    def handle_mouse_click(self, x: int, y: int, button: str = "left", 
                          modifiers: List[str] = None) -> bool:
        """Handle mouse click."""
        if modifiers is None:
            modifiers = []
        
        with self._lock:
            # Get cell at click position
            coordinate = self.main_viewport.get_cell_at_point(x, y)
            if not coordinate:
                return False
            
            if button == "left":
                if "Shift" in modifiers:
                    # Extend selection
                    self.select_range(self.state.selection.active_cell, coordinate)
                elif "Ctrl" in modifiers:
                    # Add to selection (simplified - just select new cell for now)
                    self.select_cell(coordinate)
                else:
                    # Normal selection
                    self.select_cell(coordinate)
                
                return True
            
            elif button == "right":
                # Context menu (not implemented)
                return True
            
            return False
    
    def handle_scroll(self, delta_x: int, delta_y: int, is_wheel: bool = True) -> None:
        """Handle scroll input."""
        scroll_event = ScrollEvent(
            delta_x=delta_x,
            delta_y=delta_y,
            direction=ScrollDirection.BOTH,
            timestamp=time.time(),
            is_wheel=is_wheel
        )
        
        self.scroller.handle_scroll(scroll_event)
    
    def toggle_formulas(self) -> None:
        """Toggle formula display."""
        with self._lock:
            self.state.show_formulas = not self.state.show_formulas
            self.rendering_context.show_formulas = self.state.show_formulas
            self.cell_renderer.clear_cache()  # Clear cache to force re-render
    
    def toggle_gridlines(self) -> None:
        """Toggle gridline display."""
        with self._lock:
            self.state.show_gridlines = not self.state.show_gridlines
            self.rendering_context.show_gridlines = self.state.show_gridlines
            self.cell_renderer.clear_cache()
    
    def set_freeze_panes(self, rows: int, columns: int) -> None:
        """Set freeze panes."""
        with self._lock:
            self.state.freeze_rows = rows
            self.state.freeze_columns = columns
            
            if rows > 0 or columns > 0:
                self.viewport_manager.enable_freeze_panes(rows, columns)
            else:
                self.viewport_manager.disable_freeze_panes()
    
    def render(self) -> Dict[str, Any]:
        """Render the grid and return drawing instructions."""
        with self._render_lock:
            start_time = time.time()
            self._render_count += 1
            
            # Get all visible cells from all viewports
            all_visible_cells = self.viewport_manager.get_all_visible_cells()
            
            render_data = {
                "viewports": {},
                "headers": self._render_headers(),
                "selection": self._render_selection(),
                "editing": self._render_editing_indicator(),
                "metadata": {
                    "render_time": 0.0,
                    "cell_count": 0,
                    "viewport_count": len(all_visible_cells)
                }
            }
            
            total_cells = 0
            
            # Render each viewport
            for viewport_name, cell_positions in all_visible_cells.items():
                cell_render_data = []
                
                for position in cell_positions:
                    cell = self.sheet.get_cell(position.coordinate)
                    
                    # Determine display text
                    display_text = ""
                    is_error = False
                    
                    if cell and not cell.is_empty():
                        if self.state.show_formulas and cell.formula:
                            display_text = cell.formula
                        else:
                            display_text = str(cell.value) if cell.value is not None else ""
                            is_error = isinstance(cell.value, str) and cell.value.startswith('#')
                    
                    # Check if cell is selected
                    is_selected = self.state.selection.contains(position.coordinate)
                    is_editing = (self.state.editing_cell == position.coordinate and 
                                self.state.edit_mode == EditMode.EDIT)
                    
                    cell_data = CellRenderData(
                        coordinate=position.coordinate,
                        value=cell.value if cell else None,
                        display_text=display_text,
                        format=cell.format if cell else None,
                        is_selected=is_selected,
                        is_editing=is_editing,
                        is_error=is_error,
                        x=position.x,
                        y=position.y,
                        width=position.width,
                        height=position.height
                    )
                    
                    cell_render_data.append(cell_data)
                
                # Render cells for this viewport
                rendered_cells = self.cell_renderer.render_batch(cell_render_data, self.rendering_context)
                render_data["viewports"][viewport_name] = rendered_cells
                total_cells += len(rendered_cells)
            
            # Update metadata
            render_time = time.time() - start_time
            self._last_render_time = render_time
            
            render_data["metadata"]["render_time"] = render_time
            render_data["metadata"]["cell_count"] = total_cells
            
            return render_data
    
    def _render_headers(self) -> Dict[str, Any]:
        """Render row and column headers."""
        visible_range = self.main_viewport.get_visible_range()
        metrics = self.main_viewport.metrics
        
        headers = {
            "columns": [],
            "rows": []
        }
        
        # Column headers
        for col in range(visible_range.start.col, visible_range.end.col + 1):
            x = (col * metrics.cell_width) - metrics.scroll_x + metrics.row_header_width
            if x >= metrics.row_header_width and x < metrics.width:
                headers["columns"].append({
                    "index": col,
                    "text": CellCoordinate.col_to_a1(col),
                    "x": x,
                    "y": 0,
                    "width": metrics.cell_width,
                    "height": metrics.header_height
                })
        
        # Row headers
        for row in range(visible_range.start.row, visible_range.end.row + 1):
            y = (row * metrics.cell_height) - metrics.scroll_y + metrics.header_height
            if y >= metrics.header_height and y < metrics.height:
                headers["rows"].append({
                    "index": row,
                    "text": str(row + 1),
                    "x": 0,
                    "y": y,
                    "width": metrics.row_header_width,
                    "height": metrics.cell_height
                })
        
        return headers
    
    def _render_selection(self) -> List[Dict[str, Any]]:
        """Render selection highlights."""
        selections = []
        
        for cell_range in self.state.selection.ranges:
            # Get visible part of selection
            visible_range = self.main_viewport.get_visible_range()
            
            # Calculate intersection
            start_row = max(cell_range.start.row, visible_range.start.row)
            end_row = min(cell_range.end.row, visible_range.end.row)
            start_col = max(cell_range.start.col, visible_range.start.col)
            end_col = min(cell_range.end.col, visible_range.end.col)
            
            if start_row <= end_row and start_col <= end_col:
                metrics = self.main_viewport.metrics
                
                x = (start_col * metrics.cell_width) - metrics.scroll_x + metrics.row_header_width
                y = (start_row * metrics.cell_height) - metrics.scroll_y + metrics.header_height
                width = (end_col - start_col + 1) * metrics.cell_width
                height = (end_row - start_row + 1) * metrics.cell_height
                
                selections.append({
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "color": self.rendering_context.selection_color,
                    "alpha": 0.3
                })
        
        return selections
    
    def _render_editing_indicator(self) -> Optional[Dict[str, Any]]:
        """Render editing cell indicator."""
        if self.state.edit_mode != EditMode.EDIT or not self.state.editing_cell:
            return None
        
        position = self.main_viewport.get_cell_position(self.state.editing_cell)
        if not position or not position.is_visible:
            return None
        
        return {
            "x": position.x,
            "y": position.y,
            "width": position.width,
            "height": position.height,
            "color": "#00FF00",
            "style": "dashed",
            "width": 2
        }
    
    def _on_scroll_update(self, x: int, y: int) -> None:
        """Handle scroll updates from virtual scroller."""
        # Update viewport manager
        self.viewport_manager.update_scroll(x, y)
    
    def _on_cell_changed(self, event: CellChangeEvent) -> None:
        """Handle cell change events."""
        # Clear render cache for changed cell
        self.cell_renderer.clear_cache()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get grid widget statistics."""
        with self._lock:
            return {
                "state": {
                    "selection_mode": self.state.selection.mode.value,
                    "edit_mode": self.state.edit_mode.value,
                    "show_formulas": self.state.show_formulas,
                    "show_gridlines": self.state.show_gridlines,
                    "zoom_level": self.state.zoom_level,
                    "freeze_rows": self.state.freeze_rows,
                    "freeze_columns": self.state.freeze_columns
                },
                "performance": {
                    "render_count": self._render_count,
                    "last_render_time": self._last_render_time,
                    "interaction_count": self._interaction_count
                },
                "viewport_stats": self.viewport_manager.get_statistics(),
                "scroller_stats": self.scroller.get_statistics(),
                "renderer_stats": self.cell_renderer.get_statistics()
            }
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.scroller.stop()
        self.cell_renderer.clear_cache()

