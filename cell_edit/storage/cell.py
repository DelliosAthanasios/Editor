"""
Optimized Cell implementation with memory efficiency and lazy evaluation.
"""

import weakref
from typing import Any, Optional, Dict, Union
from dataclasses import dataclass, field
from enum import Enum
import pickle
import zlib

from core.interfaces import ICell
from core.events import emit_cell_changed
from core.config import get_config


class CellType(Enum):
    """Cell data types for optimization."""
    EMPTY = "empty"
    NUMBER = "number"
    STRING = "string"
    BOOLEAN = "boolean"
    FORMULA = "formula"
    ERROR = "error"
    DATE = "date"
    ARRAY = "array"


class CellState(Enum):
    """Cell computation states."""
    CLEAN = "clean"          # Value is up to date
    DIRTY = "dirty"          # Needs recalculation
    CALCULATING = "calculating"  # Currently being calculated
    ERROR = "error"          # Calculation resulted in error


@dataclass
class CellFormat:
    """Cell formatting information."""
    font_family: Optional[str] = None
    font_size: Optional[int] = None
    font_bold: bool = False
    font_italic: bool = False
    font_color: Optional[str] = None
    background_color: Optional[str] = None
    border_style: Optional[str] = None
    number_format: Optional[str] = None
    alignment: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'font_family': self.font_family,
            'font_size': self.font_size,
            'font_bold': self.font_bold,
            'font_italic': self.font_italic,
            'font_color': self.font_color,
            'background_color': self.background_color,
            'border_style': self.border_style,
            'number_format': self.number_format,
            'alignment': self.alignment
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CellFormat':
        """Create from dictionary."""
        return cls(**data)


class CellAlignment(Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"

class CellBorder(Enum):
    SOLID = "solid"
    DASHED = "dashed"
    NONE = "none"

class Cell(ICell):
    """
    Memory-efficient cell implementation with lazy evaluation.
    Uses slots to reduce memory overhead and supports compression.
    """
    
    __slots__ = (
        '_value', '_formula', '_format', '_cell_type', '_state',
        '_compressed_data', '_dependencies', '_dependents', 
        '_last_modified', '_version'
    )
    
    def __init__(self, value: Any = None, formula: Optional[str] = None, 
                 cell_format: Optional[CellFormat] = None):
        self._value = value
        self._formula = formula
        self._format = cell_format
        self._cell_type = self._determine_type(value, formula)
        self._state = CellState.CLEAN
        self._compressed_data: Optional[bytes] = None
        self._dependencies: Optional[set] = None
        self._dependents: Optional[weakref.WeakSet] = None
        self._last_modified = 0
        self._version = 1
    
    @property
    def value(self) -> Any:
        """Get the computed value of the cell."""
        if self._state == CellState.DIRTY and self._formula:
            # Trigger recalculation if needed
            self._recalculate()
        
        if self._compressed_data and self._value is None:
            # Decompress value if needed
            self._decompress_value()
        
        return self._value
    
    @value.setter
    def value(self, new_value: Any) -> None:
        """Set the raw value of the cell."""
        old_value = self._value
        self._value = new_value
        self._formula = None  # Clear formula when setting value directly
        self._cell_type = self._determine_type(new_value, None)
        self._state = CellState.CLEAN
        self._compressed_data = None
        self._increment_version()
        
        # Emit change event
        # Note: coordinate would need to be passed from the sheet level
        # emit_cell_changed(coordinate, old_value, new_value, self)
    
    @property
    def formula(self) -> Optional[str]:
        """Get the formula string of the cell."""
        return self._formula
    
    @formula.setter
    def formula(self, new_formula: Optional[str]) -> None:
        """Set the formula string of the cell."""
        if new_formula != self._formula:
            self._formula = new_formula
            self._cell_type = CellType.FORMULA if new_formula else self._determine_type(self._value, None)
            self._state = CellState.DIRTY if new_formula else CellState.CLEAN
            self._increment_version()
    
    @property
    def format(self) -> Optional[CellFormat]:
        """Get the formatting information of the cell."""
        return self._format
    
    @format.setter
    def format(self, format_info: Optional[CellFormat]) -> None:
        """Set the formatting information of the cell."""
        self._format = format_info
        self._increment_version()
    
    @property
    def data_type(self) -> str:
        """Get the data type of the cell."""
        return self._cell_type.value
    
    @property
    def state(self) -> CellState:
        """Get the current computation state."""
        return self._state
    
    @property
    def version(self) -> int:
        """Get the cell version for change tracking."""
        return self._version
    
    def is_empty(self) -> bool:
        """Check if the cell is empty."""
        return (self._value is None and 
                self._formula is None and 
                self._cell_type == CellType.EMPTY)
    
    def clear(self) -> None:
        """Clear the cell content."""
        old_value = self._value
        self._value = None
        self._formula = None
        self._format = None
        self._cell_type = CellType.EMPTY
        self._state = CellState.CLEAN
        self._compressed_data = None
        self._dependencies = None
        if self._dependents:
            self._dependents.clear()
        self._increment_version()
    
    def add_dependency(self, cell: 'Cell') -> None:
        """Add a dependency to another cell."""
        if self._dependencies is None:
            self._dependencies = set()
        self._dependencies.add(cell)
        
        # Add this cell as a dependent of the other cell
        if cell._dependents is None:
            cell._dependents = weakref.WeakSet()
        cell._dependents.add(self)
    
    def remove_dependency(self, cell: 'Cell') -> None:
        """Remove a dependency to another cell."""
        if self._dependencies:
            self._dependencies.discard(cell)
        
        if cell._dependents:
            cell._dependents.discard(self)
    
    def get_dependencies(self) -> set:
        """Get all cell dependencies."""
        return self._dependencies.copy() if self._dependencies else set()
    
    def get_dependents(self) -> set:
        """Get all dependent cells."""
        return set(self._dependents) if self._dependents else set()
    
    def mark_dirty(self) -> None:
        """Mark this cell and its dependents as dirty."""
        if self._state != CellState.DIRTY:
            self._state = CellState.DIRTY
            
            # Recursively mark dependents as dirty
            if self._dependents:
                for dependent in list(self._dependents):  # Create list to avoid modification during iteration
                    dependent.mark_dirty()
    
    def compress(self) -> bool:
        """Compress cell data to save memory."""
        config = get_config()
        if not config.memory.compression_enabled:
            return False
        
        if self._value is not None and self._compressed_data is None:
            try:
                # Serialize and compress the value
                serialized = pickle.dumps(self._value)
                compressed = zlib.compress(serialized, level=config.storage.compression_level)
                
                # Only compress if it actually saves space
                if len(compressed) < len(serialized) * 0.8:
                    self._compressed_data = compressed
                    self._value = None  # Clear uncompressed value
                    return True
            except Exception:
                pass  # Compression failed, keep uncompressed
        
        return False
    
    def decompress(self) -> bool:
        """Decompress cell data."""
        if self._compressed_data and self._value is None:
            try:
                decompressed = zlib.decompress(self._compressed_data)
                self._value = pickle.loads(decompressed)
                return True
            except Exception:
                pass  # Decompression failed
        return False
    
    def get_memory_usage(self) -> Dict[str, int]:
        """Get memory usage statistics for this cell."""
        import sys
        
        usage = {
            'base_size': sys.getsizeof(self),
            'value_size': sys.getsizeof(self._value) if self._value is not None else 0,
            'formula_size': sys.getsizeof(self._formula) if self._formula else 0,
            'format_size': sys.getsizeof(self._format) if self._format else 0,
            'compressed_size': len(self._compressed_data) if self._compressed_data else 0,
            'dependencies_size': sys.getsizeof(self._dependencies) if self._dependencies else 0,
        }
        
        usage['total_size'] = sum(usage.values())
        return usage
    
    def _determine_type(self, value: Any, formula: Optional[str]) -> CellType:
        """Determine the cell type based on value and formula."""
        if formula:
            return CellType.FORMULA
        elif value is None:
            return CellType.EMPTY
        elif isinstance(value, bool):
            return CellType.BOOLEAN
        elif isinstance(value, (int, float)):
            return CellType.NUMBER
        elif isinstance(value, str):
            if value.startswith('#') and value.endswith('!'):
                return CellType.ERROR
            return CellType.STRING
        elif isinstance(value, (list, tuple)):
            return CellType.ARRAY
        else:
            return CellType.STRING  # Default fallback
    
    def _recalculate(self) -> None:
        """Recalculate the cell value from formula."""
        if not self._formula or self._state == CellState.CALCULATING:
            return
        
        self._state = CellState.CALCULATING
        try:
            # This would be handled by the formula engine
            # For now, just mark as clean
            self._state = CellState.CLEAN
        except Exception as e:
            self._value = f"#ERROR: {e}"
            self._cell_type = CellType.ERROR
            self._state = CellState.ERROR
    
    def _decompress_value(self) -> None:
        """Internal method to decompress value."""
        if self._compressed_data and self._value is None:
            self.decompress()
    
    def _increment_version(self) -> None:
        """Increment the cell version."""
        self._version += 1
        import time
        self._last_modified = time.time()
    
    def __repr__(self) -> str:
        if self._formula:
            return f"Cell(formula='{self._formula}', type={self._cell_type.value})"
        elif self._value is not None:
            return f"Cell(value={self._value!r}, type={self._cell_type.value})"
        else:
            return f"Cell(empty)"
    
    def __str__(self) -> str:
        if self._formula:
            return self._formula
        elif self._value is not None:
            return str(self._value)
        else:
            return ""


class CellFactory:
    """Factory for creating optimized cell instances."""
    
    @staticmethod
    def create_empty_cell() -> Cell:
        """Create an empty cell."""
        return Cell()
    
    @staticmethod
    def create_value_cell(value: Any) -> Cell:
        """Create a cell with a value."""
        return Cell(value=value)
    
    @staticmethod
    def create_formula_cell(formula: str) -> Cell:
        """Create a cell with a formula."""
        return Cell(formula=formula)
    
    @staticmethod
    def create_formatted_cell(value: Any = None, formula: Optional[str] = None,
                            cell_format: Optional[CellFormat] = None) -> Cell:
        """Create a cell with formatting."""
        return Cell(value=value, formula=formula, cell_format=cell_format)

