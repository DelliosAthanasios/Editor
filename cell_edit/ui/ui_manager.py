"""
UI Manager for coordinating all user interface components.
Provides high-level interface for UI operations and event handling.
"""

import threading
import time
from typing import Any, Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum

from core.interfaces import ISheet, IWorkbook
from core.coordinates import CellCoordinate, CellRange
from core.config import get_config
from core.events import get_event_manager, EventType
from ui.grid_widget import GridWidget, Selection, EditMode
from ui.viewport import ViewportMetrics
from ui.virtual_scroller import ScrollMode
from ui.cell_renderer import RenderingMode, RenderingContext


class UITheme(Enum):
    """UI themes."""
    LIGHT = "light"
    DARK = "dark"
    HIGH_CONTRAST = "high_contrast"
    CUSTOM = "custom"


class UIMode(Enum):
    """UI modes."""
    NORMAL = "normal"
    PRESENTATION = "presentation"
    PRINT_PREVIEW = "print_preview"
    FULL_SCREEN = "full_screen"


@dataclass
class UISettings:
    """UI configuration settings."""
    theme: UITheme = UITheme.LIGHT
    mode: UIMode = UIMode.NORMAL
    show_formula_bar: bool = True
    show_status_bar: bool = True
    show_sheet_tabs: bool = True
    show_rulers: bool = False
    enable_animations: bool = True
    enable_smooth_scrolling: bool = True
    enable_momentum_scrolling: bool = True
    auto_save_interval: int = 300  # seconds
    
    # Performance settings
    rendering_quality: RenderingMode = RenderingMode.NORMAL
    max_undo_levels: int = 100
    enable_spell_check: bool = False


@dataclass
class UIState:
    """Current UI state."""
    active_sheet: Optional[str] = None
    window_width: int = 1024
    window_height: int = 768
    is_fullscreen: bool = False
    zoom_level: float = 1.0
    last_activity: float = 0.0
    
    # Dialog states
    find_dialog_open: bool = False
    format_dialog_open: bool = False
    chart_dialog_open: bool = False


class UIManager:
    """
    Central UI manager that coordinates all user interface components.
    Provides high-level interface for UI operations and manages component interactions.
    """
    
    def __init__(self, workbook: IWorkbook):
        self.workbook = workbook
        self.settings = UISettings()
        self.state = UIState()
        
        # UI Components
        self.grid_widgets: Dict[str, GridWidget] = {}
        self.active_grid: Optional[GridWidget] = None
        
        # Event callbacks
        self.on_cell_selected: Optional[Callable[[CellCoordinate], None]] = None
        self.on_cell_edited: Optional[Callable[[str, CellCoordinate, str], None]] = None
        self.on_selection_changed: Optional[Callable[[str, Selection], None]] = None
        self.on_sheet_changed: Optional[Callable[[str], None]] = None
        self.on_zoom_changed: Optional[Callable[[float], None]] = None
        
        # Threading
        self._lock = threading.RLock()
        self._update_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Performance tracking
        self._ui_updates = 0
        self._last_fps_check = time.time()
        self._current_fps = 0.0
        
        # Initialize with first sheet
        self._initialize_sheets()
        
        # Start update thread
        self._start_update_thread()
    
    def _initialize_sheets(self) -> None:
        """Initialize grid widgets for all sheets."""
        with self._lock:
            for sheet_name in self.workbook.get_sheet_names():
                sheet = self.workbook.get_sheet(sheet_name)
                if sheet:
                    grid = GridWidget(
                        sheet=sheet,
                        width=self.state.window_width,
                        height=self.state.window_height
                    )
                    
                    # Set up callbacks
                    grid.on_cell_selected = lambda coord: self._on_cell_selected(sheet_name, coord)
                    grid.on_cell_edited = lambda coord, value: self._on_cell_edited(sheet_name, coord, value)
                    grid.on_selection_changed = lambda sel: self._on_selection_changed(sheet_name, sel)
                    
                    self.grid_widgets[sheet_name] = grid
            
            # Set first sheet as active
            if self.grid_widgets:
                first_sheet = next(iter(self.grid_widgets.keys()))
                self.set_active_sheet(first_sheet)
    
    def set_active_sheet(self, sheet_name: str) -> bool:
        """Set the active sheet."""
        with self._lock:
            if sheet_name not in self.grid_widgets:
                return False
            
            old_sheet = self.state.active_sheet
            self.state.active_sheet = sheet_name
            self.active_grid = self.grid_widgets[sheet_name]
            
            # Update activity timestamp
            self.state.last_activity = time.time()
            
            # Notify callback
            if self.on_sheet_changed and old_sheet != sheet_name:
                self.on_sheet_changed(sheet_name)
            
            return True
    
    def get_active_sheet_name(self) -> Optional[str]:
        """Get the name of the active sheet."""
        return self.state.active_sheet
    
    def get_active_grid(self) -> Optional[GridWidget]:
        """Get the active grid widget."""
        return self.active_grid
    
    def resize_window(self, width: int, height: int) -> None:
        """Resize the UI window."""
        with self._lock:
            self.state.window_width = width
            self.state.window_height = height
            
            # Resize all grid widgets
            for grid in self.grid_widgets.values():
                grid.resize(width, height)
    
    def set_zoom(self, zoom_level: float) -> None:
        """Set zoom level for active sheet."""
        with self._lock:
            if not self.active_grid:
                return
            
            zoom_level = max(0.25, min(4.0, zoom_level))
            old_zoom = self.state.zoom_level
            self.state.zoom_level = zoom_level
            
            self.active_grid.set_zoom(zoom_level)
            
            # Notify callback
            if self.on_zoom_changed and old_zoom != zoom_level:
                self.on_zoom_changed(zoom_level)
    
    def zoom_in(self) -> None:
        """Zoom in by 25%."""
        current_zoom = self.state.zoom_level
        self.set_zoom(current_zoom * 1.25)
    
    def zoom_out(self) -> None:
        """Zoom out by 25%."""
        current_zoom = self.state.zoom_level
        self.set_zoom(current_zoom * 0.8)
    
    def zoom_to_fit(self) -> None:
        """Zoom to fit the current selection."""
        # Simplified implementation - zoom to 100%
        self.set_zoom(1.0)
    
    def select_cell(self, coordinate: CellCoordinate, sheet_name: Optional[str] = None) -> None:
        """Select a cell in the specified sheet."""
        with self._lock:
            if sheet_name and sheet_name != self.state.active_sheet:
                self.set_active_sheet(sheet_name)
            
            if self.active_grid:
                self.active_grid.select_cell(coordinate)
    
    def select_range(self, start: CellCoordinate, end: CellCoordinate, 
                    sheet_name: Optional[str] = None) -> None:
        """Select a range of cells."""
        with self._lock:
            if sheet_name and sheet_name != self.state.active_sheet:
                self.set_active_sheet(sheet_name)
            
            if self.active_grid:
                self.active_grid.select_range(start, end)
    
    def scroll_to_cell(self, coordinate: CellCoordinate, mode: ScrollMode = ScrollMode.SMOOTH,
                      sheet_name: Optional[str] = None) -> None:
        """Scroll to make a cell visible."""
        with self._lock:
            if sheet_name and sheet_name != self.state.active_sheet:
                self.set_active_sheet(sheet_name)
            
            if self.active_grid:
                self.active_grid.scroll_to_cell(coordinate, mode)
    
    def start_edit(self, coordinate: Optional[CellCoordinate] = None) -> None:
        """Start editing a cell."""
        with self._lock:
            if self.active_grid:
                self.active_grid.start_edit(coordinate)
    
    def end_edit(self, save_changes: bool = True, new_value: str = "") -> None:
        """End cell editing."""
        with self._lock:
            if self.active_grid:
                self.active_grid.end_edit(save_changes, new_value)
    
    def handle_key_press(self, key: str, modifiers: List[str] = None) -> bool:
        """Handle keyboard input."""
        with self._lock:
            self.state.last_activity = time.time()
            
            # Global shortcuts
            if modifiers and "Ctrl" in modifiers:
                if key == "z":
                    return self.undo()
                elif key == "y":
                    return self.redo()
                elif key == "c":
                    return self.copy()
                elif key == "v":
                    return self.paste()
                elif key == "x":
                    return self.cut()
                elif key == "f":
                    return self.show_find_dialog()
                elif key == "h":
                    return self.show_replace_dialog()
                elif key == "s":
                    return self.save()
                elif key == "o":
                    return self.open_file()
                elif key == "n":
                    return self.new_file()
                elif key == "=":
                    self.zoom_in()
                    return True
                elif key == "-":
                    self.zoom_out()
                    return True
                elif key == "0":
                    self.set_zoom(1.0)
                    return True
            
            # Function keys
            if key == "F11":
                self.toggle_fullscreen()
                return True
            
            # Pass to active grid
            if self.active_grid:
                return self.active_grid.handle_key_press(key, modifiers)
            
            return False
    
    def handle_mouse_click(self, x: int, y: int, button: str = "left", 
                          modifiers: List[str] = None) -> bool:
        """Handle mouse click."""
        with self._lock:
            self.state.last_activity = time.time()
            
            if self.active_grid:
                return self.active_grid.handle_mouse_click(x, y, button, modifiers)
            
            return False
    
    def handle_scroll(self, delta_x: int, delta_y: int, is_wheel: bool = True) -> None:
        """Handle scroll input."""
        with self._lock:
            self.state.last_activity = time.time()
            
            if self.active_grid:
                self.active_grid.handle_scroll(delta_x, delta_y, is_wheel)
    
    def set_theme(self, theme: UITheme) -> None:
        """Set UI theme."""
        with self._lock:
            self.settings.theme = theme
            self._apply_theme()
    
    def _apply_theme(self) -> None:
        """Apply the current theme to all components."""
        theme_colors = self._get_theme_colors()
        
        # Update rendering context for all grids
        for grid in self.grid_widgets.values():
            grid.rendering_context.text_color = theme_colors["text"]
            grid.rendering_context.background_color = theme_colors["background"]
            grid.rendering_context.grid_color = theme_colors["grid"]
            grid.rendering_context.selection_color = theme_colors["selection"]
            grid.cell_renderer.clear_cache()  # Force re-render
    
    def _get_theme_colors(self) -> Dict[str, str]:
        """Get colors for the current theme."""
        if self.settings.theme == UITheme.LIGHT:
            return {
                "text": "#000000",
                "background": "#FFFFFF",
                "grid": "#E0E0E0",
                "selection": "#4A90E2"
            }
        elif self.settings.theme == UITheme.DARK:
            return {
                "text": "#FFFFFF",
                "background": "#2D2D2D",
                "grid": "#404040",
                "selection": "#0078D4"
            }
        elif self.settings.theme == UITheme.HIGH_CONTRAST:
            return {
                "text": "#FFFFFF",
                "background": "#000000",
                "grid": "#FFFFFF",
                "selection": "#FFFF00"
            }
        else:
            # Default to light theme
            return self._get_theme_colors()
    
    def toggle_fullscreen(self) -> None:
        """Toggle fullscreen mode."""
        with self._lock:
            self.state.is_fullscreen = not self.state.is_fullscreen
            
            if self.state.is_fullscreen:
                self.settings.mode = UIMode.FULL_SCREEN
            else:
                self.settings.mode = UIMode.NORMAL
    
    def toggle_formulas(self) -> None:
        """Toggle formula display."""
        with self._lock:
            if self.active_grid:
                self.active_grid.toggle_formulas()
    
    def toggle_gridlines(self) -> None:
        """Toggle gridline display."""
        with self._lock:
            if self.active_grid:
                self.active_grid.toggle_gridlines()
    
    def set_freeze_panes(self, rows: int, columns: int) -> None:
        """Set freeze panes for active sheet."""
        with self._lock:
            if self.active_grid:
                self.active_grid.set_freeze_panes(rows, columns)
    
    # File operations (simplified implementations)
    def new_file(self) -> bool:
        """Create a new file."""
        # Implementation would create new workbook
        return True
    
    def open_file(self, filename: Optional[str] = None) -> bool:
        """Open a file."""
        # Implementation would open file dialog and load workbook
        return True
    
    def save(self, filename: Optional[str] = None) -> bool:
        """Save the current file."""
        # Implementation would save workbook
        return True
    
    def save_as(self, filename: str) -> bool:
        """Save with a new filename."""
        # Implementation would save workbook with new name
        return True
    
    # Edit operations (simplified implementations)
    def undo(self) -> bool:
        """Undo last operation."""
        # Implementation would use undo manager
        return True
    
    def redo(self) -> bool:
        """Redo last undone operation."""
        # Implementation would use undo manager
        return True
    
    def copy(self) -> bool:
        """Copy selection to clipboard."""
        # Implementation would copy selected cells
        return True
    
    def paste(self) -> bool:
        """Paste from clipboard."""
        # Implementation would paste clipboard content
        return True
    
    def cut(self) -> bool:
        """Cut selection to clipboard."""
        # Implementation would cut selected cells
        return True
    
    # Dialog operations (simplified implementations)
    def show_find_dialog(self) -> bool:
        """Show find dialog."""
        self.state.find_dialog_open = True
        return True
    
    def show_replace_dialog(self) -> bool:
        """Show find and replace dialog."""
        return True
    
    def show_format_dialog(self) -> bool:
        """Show format cells dialog."""
        self.state.format_dialog_open = True
        return True
    
    def show_chart_dialog(self) -> bool:
        """Show insert chart dialog."""
        self.state.chart_dialog_open = True
        return True
    
    def render(self) -> Dict[str, Any]:
        """Render the entire UI."""
        with self._lock:
            if not self.active_grid:
                return {"error": "No active sheet"}
            
            # Render active grid
            grid_render_data = self.active_grid.render()
            
            # Add UI chrome
            ui_data = {
                "grid": grid_render_data,
                "chrome": self._render_ui_chrome(),
                "dialogs": self._render_dialogs(),
                "theme": self.settings.theme.value,
                "mode": self.settings.mode.value,
                "state": {
                    "active_sheet": self.state.active_sheet,
                    "zoom_level": self.state.zoom_level,
                    "is_fullscreen": self.state.is_fullscreen
                }
            }
            
            self._ui_updates += 1
            return ui_data
    
    def _render_ui_chrome(self) -> Dict[str, Any]:
        """Render UI chrome (toolbars, status bar, etc.)."""
        chrome = {}
        
        if self.settings.show_formula_bar:
            chrome["formula_bar"] = {
                "visible": True,
                "height": 30,
                "content": self._get_formula_bar_content()
            }
        
        if self.settings.show_status_bar:
            chrome["status_bar"] = {
                "visible": True,
                "height": 25,
                "content": self._get_status_bar_content()
            }
        
        if self.settings.show_sheet_tabs:
            chrome["sheet_tabs"] = {
                "visible": True,
                "height": 30,
                "tabs": [
                    {
                        "name": name,
                        "active": name == self.state.active_sheet
                    }
                    for name in self.grid_widgets.keys()
                ]
            }
        
        return chrome
    
    def _render_dialogs(self) -> Dict[str, Any]:
        """Render open dialogs."""
        dialogs = {}
        
        if self.state.find_dialog_open:
            dialogs["find"] = {
                "visible": True,
                "title": "Find",
                "content": "Find dialog content"
            }
        
        if self.state.format_dialog_open:
            dialogs["format"] = {
                "visible": True,
                "title": "Format Cells",
                "content": "Format dialog content"
            }
        
        if self.state.chart_dialog_open:
            dialogs["chart"] = {
                "visible": True,
                "title": "Insert Chart",
                "content": "Chart dialog content"
            }
        
        return dialogs
    
    def _get_formula_bar_content(self) -> str:
        """Get formula bar content."""
        if not self.active_grid:
            return ""
        
        active_cell = self.active_grid.state.selection.active_cell
        sheet = self.workbook.get_sheet(self.state.active_sheet)
        
        if sheet:
            cell = sheet.get_cell(active_cell)
            if cell and cell.formula:
                return cell.formula
            elif cell and cell.value is not None:
                return str(cell.value)
        
        return ""
    
    def _get_status_bar_content(self) -> str:
        """Get status bar content."""
        if not self.active_grid:
            return "Ready"
        
        active_cell = self.active_grid.state.selection.active_cell
        cell_ref = active_cell.to_a1()
        
        # Add selection info
        selection = self.active_grid.state.selection
        if len(selection.ranges) == 1 and selection.ranges[0].is_single_cell():
            return f"Ready | {cell_ref}"
        else:
            cell_count = sum(len(list(r)) for r in selection.ranges)
            return f"Ready | {cell_count} cells selected"
    
    def _start_update_thread(self) -> None:
        """Start the UI update thread."""
        if self._update_thread and self._update_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()
    
    def _update_loop(self) -> None:
        """Main UI update loop."""
        target_fps = get_config().ui.target_fps
        frame_time = 1.0 / target_fps
        fps_counter = 0
        last_fps_check = time.time()
        
        while not self._stop_event.is_set():
            start_time = time.time()
            
            # Update FPS counter
            fps_counter += 1
            current_time = time.time()
            if current_time - last_fps_check >= 1.0:
                self._current_fps = fps_counter / (current_time - last_fps_check)
                fps_counter = 0
                last_fps_check = current_time
            
            # Sleep to maintain target FPS
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_time - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _on_cell_selected(self, sheet_name: str, coordinate: CellCoordinate) -> None:
        """Handle cell selection events."""
        if self.on_cell_selected:
            self.on_cell_selected(coordinate)
    
    def _on_cell_edited(self, sheet_name: str, coordinate: CellCoordinate, value: str) -> None:
        """Handle cell edit events."""
        if self.on_cell_edited:
            self.on_cell_edited(sheet_name, coordinate, value)
    
    def _on_selection_changed(self, sheet_name: str, selection: Selection) -> None:
        """Handle selection change events."""
        if self.on_selection_changed:
            self.on_selection_changed(sheet_name, selection)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get UI manager statistics."""
        with self._lock:
            stats = {
                "ui_updates": self._ui_updates,
                "current_fps": self._current_fps,
                "target_fps": get_config().ui.target_fps,
                "active_sheet": self.state.active_sheet,
                "sheet_count": len(self.grid_widgets),
                "settings": {
                    "theme": self.settings.theme.value,
                    "mode": self.settings.mode.value,
                    "rendering_quality": self.settings.rendering_quality.value
                },
                "state": {
                    "window_size": f"{self.state.window_width}x{self.state.window_height}",
                    "zoom_level": self.state.zoom_level,
                    "is_fullscreen": self.state.is_fullscreen,
                    "last_activity": self.state.last_activity
                }
            }
            
            # Add active grid stats
            if self.active_grid:
                stats["active_grid"] = self.active_grid.get_statistics()
            
            return stats
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self._stop_event.set()
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=1.0)
        
        # Clean up grid widgets
        for grid in self.grid_widgets.values():
            grid.cleanup()

