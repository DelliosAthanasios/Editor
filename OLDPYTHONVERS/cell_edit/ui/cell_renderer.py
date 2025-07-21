"""
Cell renderer for efficient drawing of spreadsheet cells.
Handles text rendering, formatting, borders, and visual effects.
"""

import threading
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import colorsys

from core.coordinates import CellCoordinate
from core.config import get_config
from core.events import get_event_manager, EventType
from core.interfaces import ICell
from storage.cell import CellFormat, CellAlignment, CellBorder


class RenderingMode(Enum):
    """Rendering modes for different quality levels."""
    FAST = "fast"           # Minimal rendering for scrolling
    NORMAL = "normal"       # Standard quality
    HIGH_QUALITY = "high"   # High quality for printing/export


@dataclass
class RenderingContext:
    """Context for cell rendering."""
    mode: RenderingMode
    scale_factor: float = 1.0
    show_gridlines: bool = True
    show_formulas: bool = False
    highlight_errors: bool = True
    selection_color: str = "#4A90E2"
    grid_color: str = "#E0E0E0"
    text_color: str = "#000000"
    background_color: str = "#FFFFFF"
    font_family: str = "Arial"
    font_size: int = 11
    
    # Performance settings
    max_text_length: int = 1000
    enable_text_wrapping: bool = True
    enable_rich_formatting: bool = True


@dataclass
class CellRenderData:
    """Data needed to render a cell."""
    coordinate: CellCoordinate
    value: Any
    display_text: str
    format: Optional[CellFormat]
    is_selected: bool = False
    is_editing: bool = False
    is_error: bool = False
    x: int = 0
    y: int = 0
    width: int = 100
    height: int = 25


class TextRenderer:
    """Handles text rendering with formatting."""
    
    def __init__(self):
        self._font_cache: Dict[str, Any] = {}
        self._text_metrics_cache: Dict[str, Tuple[int, int]] = {}
    
    def measure_text(self, text: str, font_family: str, font_size: int, 
                    bold: bool = False, italic: bool = False) -> Tuple[int, int]:
        """Measure text dimensions."""
        cache_key = f"{text}:{font_family}:{font_size}:{bold}:{italic}"
        
        if cache_key in self._text_metrics_cache:
            return self._text_metrics_cache[cache_key]
        
        # Simplified text measurement (in a real implementation, this would use actual font metrics)
        char_width = font_size * 0.6  # Approximate character width
        char_height = font_size * 1.2  # Approximate character height
        
        width = int(len(text) * char_width)
        height = int(char_height)
        
        # Cache the result
        if len(self._text_metrics_cache) < 10000:
            self._text_metrics_cache[cache_key] = (width, height)
        
        return width, height
    
    def wrap_text(self, text: str, max_width: int, font_family: str, 
                 font_size: int) -> List[str]:
        """Wrap text to fit within specified width."""
        if not text:
            return [""]
        
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = f"{current_line} {word}".strip()
            width, _ = self.measure_text(test_line, font_family, font_size)
            
            if width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    # Word is too long, break it
                    lines.append(word)
        
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [""]
    
    def clear_cache(self) -> None:
        """Clear text rendering caches."""
        self._font_cache.clear()
        self._text_metrics_cache.clear()


class BorderRenderer:
    """Handles border rendering."""
    
    @staticmethod
    def get_border_style(border: CellBorder) -> Dict[str, Any]:
        """Get border style properties."""
        styles = {
            "none": {"width": 0, "style": "solid"},
            "thin": {"width": 1, "style": "solid"},
            "medium": {"width": 2, "style": "solid"},
            "thick": {"width": 3, "style": "solid"},
            "dashed": {"width": 1, "style": "dashed"},
            "dotted": {"width": 1, "style": "dotted"},
            "double": {"width": 3, "style": "double"}
        }
        
        return styles.get(border.style, styles["thin"])


class ColorUtils:
    """Utilities for color manipulation."""
    
    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def rgb_to_hex(r: int, g: int, b: int) -> str:
        """Convert RGB to hex color."""
        return f"#{r:02x}{g:02x}{b:02x}"
    
    @staticmethod
    def lighten_color(hex_color: str, factor: float) -> str:
        """Lighten a color by the specified factor."""
        r, g, b = ColorUtils.hex_to_rgb(hex_color)
        h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
        
        # Increase lightness
        l = min(1.0, l + factor)
        
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return ColorUtils.rgb_to_hex(int(r*255), int(g*255), int(b*255))
    
    @staticmethod
    def darken_color(hex_color: str, factor: float) -> str:
        """Darken a color by the specified factor."""
        return ColorUtils.lighten_color(hex_color, -factor)


class CellRenderer:
    """
    High-performance cell renderer for spreadsheet cells.
    Handles text, formatting, borders, and visual effects.
    """
    
    def __init__(self):
        self.text_renderer = TextRenderer()
        self._lock = threading.RLock()
        
        # Rendering statistics
        self._cells_rendered = 0
        self._total_render_time = 0.0
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Render cache
        self._render_cache: Dict[str, Any] = {}
        self._cache_enabled = True
        self._cache_max_size = 5000
    
    def render_cell(self, cell_data: CellRenderData, context: RenderingContext) -> Dict[str, Any]:
        """Render a single cell and return drawing instructions."""
        with self._lock:
            self._cells_rendered += 1
            
            # Check cache
            cache_key = self._get_cache_key(cell_data, context)
            if self._cache_enabled and cache_key in self._render_cache:
                self._cache_hits += 1
                return self._render_cache[cache_key]
            
            self._cache_misses += 1
            
            # Render the cell
            render_data = self._render_cell_internal(cell_data, context)
            
            # Cache the result
            if self._cache_enabled and len(self._render_cache) < self._cache_max_size:
                self._render_cache[cache_key] = render_data
            
            return render_data
    
    def _render_cell_internal(self, cell_data: CellRenderData, context: RenderingContext) -> Dict[str, Any]:
        """Internal cell rendering implementation."""
        render_data = {
            "coordinate": cell_data.coordinate,
            "bounds": {
                "x": cell_data.x,
                "y": cell_data.y,
                "width": cell_data.width,
                "height": cell_data.height
            },
            "background": self._render_background(cell_data, context),
            "borders": self._render_borders(cell_data, context),
            "text": self._render_text(cell_data, context),
            "selection": self._render_selection(cell_data, context) if cell_data.is_selected else None,
            "error_indicator": self._render_error_indicator(cell_data, context) if cell_data.is_error else None
        }
        
        return render_data
    
    def _render_background(self, cell_data: CellRenderData, context: RenderingContext) -> Dict[str, Any]:
        """Render cell background."""
        bg_color = context.background_color
        
        # Apply cell format background color
        if cell_data.format and cell_data.format.background_color:
            bg_color = cell_data.format.background_color
        
        # Special handling for errors
        if cell_data.is_error and context.highlight_errors:
            bg_color = ColorUtils.lighten_color("#FF0000", 0.8)
        
        return {
            "color": bg_color,
            "x": cell_data.x,
            "y": cell_data.y,
            "width": cell_data.width,
            "height": cell_data.height
        }
    
    def _render_borders(self, cell_data: CellRenderData, context: RenderingContext) -> List[Dict[str, Any]]:
        """Render cell borders."""
        borders = []
        
        # Grid lines
        if context.show_gridlines:
            # Right border
            borders.append({
                "type": "line",
                "x1": cell_data.x + cell_data.width,
                "y1": cell_data.y,
                "x2": cell_data.x + cell_data.width,
                "y2": cell_data.y + cell_data.height,
                "color": context.grid_color,
                "width": 1,
                "style": "solid"
            })
            
            # Bottom border
            borders.append({
                "type": "line",
                "x1": cell_data.x,
                "y1": cell_data.y + cell_data.height,
                "x2": cell_data.x + cell_data.width,
                "y2": cell_data.y + cell_data.height,
                "color": context.grid_color,
                "width": 1,
                "style": "solid"
            })
        
        # Custom borders from cell format
        if cell_data.format and context.enable_rich_formatting:
            if cell_data.format.border_top:
                style = BorderRenderer.get_border_style(cell_data.format.border_top)
                borders.append({
                    "type": "line",
                    "x1": cell_data.x,
                    "y1": cell_data.y,
                    "x2": cell_data.x + cell_data.width,
                    "y2": cell_data.y,
                    "color": cell_data.format.border_top.color or "#000000",
                    "width": style["width"],
                    "style": style["style"]
                })
            
            if cell_data.format.border_bottom:
                style = BorderRenderer.get_border_style(cell_data.format.border_bottom)
                borders.append({
                    "type": "line",
                    "x1": cell_data.x,
                    "y1": cell_data.y + cell_data.height,
                    "x2": cell_data.x + cell_data.width,
                    "y2": cell_data.y + cell_data.height,
                    "color": cell_data.format.border_bottom.color or "#000000",
                    "width": style["width"],
                    "style": style["style"]
                })
            
            if cell_data.format.border_left:
                style = BorderRenderer.get_border_style(cell_data.format.border_left)
                borders.append({
                    "type": "line",
                    "x1": cell_data.x,
                    "y1": cell_data.y,
                    "x2": cell_data.x,
                    "y2": cell_data.y + cell_data.height,
                    "color": cell_data.format.border_left.color or "#000000",
                    "width": style["width"],
                    "style": style["style"]
                })
            
            if cell_data.format.border_right:
                style = BorderRenderer.get_border_style(cell_data.format.border_right)
                borders.append({
                    "type": "line",
                    "x1": cell_data.x + cell_data.width,
                    "y1": cell_data.y,
                    "x2": cell_data.x + cell_data.width,
                    "y2": cell_data.y + cell_data.height,
                    "color": cell_data.format.border_right.color or "#000000",
                    "width": style["width"],
                    "style": style["style"]
                })
        
        return borders
    
    def _render_text(self, cell_data: CellRenderData, context: RenderingContext) -> Optional[Dict[str, Any]]:
        """Render cell text."""
        if not cell_data.display_text:
            return None
        
        # Truncate text if too long
        text = cell_data.display_text
        if len(text) > context.max_text_length:
            text = text[:context.max_text_length] + "..."
        
        # Get text properties
        font_family = context.font_family
        font_size = context.font_size
        text_color = context.text_color
        bold = False
        italic = False
        
        # Apply cell format
        if cell_data.format and context.enable_rich_formatting:
            if cell_data.format.font_family:
                font_family = cell_data.format.font_family
            if cell_data.format.font_size:
                font_size = cell_data.format.font_size
            if cell_data.format.font_color:
                text_color = cell_data.format.font_color
            bold = cell_data.format.bold
            italic = cell_data.format.italic
        
        # Calculate text position and alignment
        text_x, text_y = self._calculate_text_position(
            cell_data, text, font_family, font_size, context
        )
        
        # Handle text wrapping
        lines = [text]
        if context.enable_text_wrapping and cell_data.format and cell_data.format.wrap_text:
            available_width = cell_data.width - 8  # Padding
            lines = self.text_renderer.wrap_text(text, available_width, font_family, font_size)
        
        return {
            "text": text,
            "lines": lines,
            "x": text_x,
            "y": text_y,
            "font_family": font_family,
            "font_size": font_size,
            "color": text_color,
            "bold": bold,
            "italic": italic,
            "alignment": cell_data.format.alignment if cell_data.format else CellAlignment.LEFT
        }
    
    def _calculate_text_position(self, cell_data: CellRenderData, text: str, 
                               font_family: str, font_size: int, context: RenderingContext) -> Tuple[int, int]:
        """Calculate text position based on alignment."""
        text_width, text_height = self.text_renderer.measure_text(text, font_family, font_size)
        
        # Default to left alignment
        alignment = CellAlignment.LEFT
        if cell_data.format and cell_data.format.alignment:
            alignment = cell_data.format.alignment
        
        # Horizontal alignment
        if alignment == CellAlignment.LEFT:
            text_x = cell_data.x + 4  # Small padding
        elif alignment == CellAlignment.CENTER:
            text_x = cell_data.x + (cell_data.width - text_width) // 2
        elif alignment == CellAlignment.RIGHT:
            text_x = cell_data.x + cell_data.width - text_width - 4  # Small padding
        else:
            text_x = cell_data.x + 4
        
        # Vertical alignment (center for now)
        text_y = cell_data.y + (cell_data.height - text_height) // 2
        
        return text_x, text_y
    
    def _render_selection(self, cell_data: CellRenderData, context: RenderingContext) -> Dict[str, Any]:
        """Render selection highlight."""
        return {
            "type": "selection",
            "x": cell_data.x,
            "y": cell_data.y,
            "width": cell_data.width,
            "height": cell_data.height,
            "color": context.selection_color,
            "alpha": 0.3
        }
    
    def _render_error_indicator(self, cell_data: CellRenderData, context: RenderingContext) -> Dict[str, Any]:
        """Render error indicator."""
        return {
            "type": "error_triangle",
            "x": cell_data.x + cell_data.width - 8,
            "y": cell_data.y,
            "size": 8,
            "color": "#FF0000"
        }
    
    def _get_cache_key(self, cell_data: CellRenderData, context: RenderingContext) -> str:
        """Generate cache key for cell rendering."""
        # Create a hash of the relevant rendering data
        key_parts = [
            str(cell_data.coordinate),
            cell_data.display_text,
            str(cell_data.is_selected),
            str(cell_data.is_editing),
            str(cell_data.is_error),
            str(cell_data.width),
            str(cell_data.height),
            context.mode.value,
            str(context.scale_factor),
            str(context.show_gridlines),
            str(context.show_formulas)
        ]
        
        # Add format information if available
        if cell_data.format:
            key_parts.extend([
                cell_data.format.font_family or "",
                str(cell_data.format.font_size or 0),
                cell_data.format.font_color or "",
                str(cell_data.format.bold),
                str(cell_data.format.italic),
                cell_data.format.background_color or "",
                str(cell_data.format.alignment.value if cell_data.format.alignment else "")
            ])
        
        return "|".join(key_parts)
    
    def render_batch(self, cells: List[CellRenderData], context: RenderingContext) -> List[Dict[str, Any]]:
        """Render multiple cells efficiently."""
        results = []
        
        for cell_data in cells:
            render_data = self.render_cell(cell_data, context)
            results.append(render_data)
        
        return results
    
    def clear_cache(self) -> None:
        """Clear the render cache."""
        with self._lock:
            self._render_cache.clear()
            self.text_renderer.clear_cache()
    
    def set_cache_enabled(self, enabled: bool) -> None:
        """Enable or disable render caching."""
        self._cache_enabled = enabled
        if not enabled:
            self.clear_cache()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get renderer statistics."""
        with self._lock:
            cache_hit_rate = (
                self._cache_hits / max(1, self._cache_hits + self._cache_misses)
            )
            
            return {
                "cells_rendered": self._cells_rendered,
                "total_render_time": self._total_render_time,
                "average_render_time": (
                    self._total_render_time / max(1, self._cells_rendered)
                ),
                "cache_size": len(self._render_cache),
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "cache_hit_rate": cache_hit_rate,
                "cache_enabled": self._cache_enabled
            }

