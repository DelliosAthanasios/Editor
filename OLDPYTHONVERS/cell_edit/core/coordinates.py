"""
Coordinate system for efficient cell addressing.
Supports both traditional A1 notation and numeric coordinates.
"""

import re
from typing import Tuple, Iterator, Optional
from dataclasses import dataclass


@dataclass(frozen=True)
class CellCoordinate:
    """Immutable cell coordinate with efficient hashing."""
    
    row: int  # 0-based
    col: int  # 0-based
    
    def __post_init__(self):
        if self.row < 0 or self.col < 0:
            raise ValueError("Row and column must be non-negative")
        if self.row >= 1048576 or self.col >= 16384:  # Excel limits
            raise ValueError("Row or column exceeds maximum limits")
    
    @classmethod
    def from_a1(cls, a1_notation: str) -> 'CellCoordinate':
        """Create coordinate from A1 notation (e.g., 'A1', 'BC123')."""
        match = re.match(r'^([A-Z]+)(\d+)$', a1_notation.upper())
        if not match:
            raise ValueError(f"Invalid A1 notation: {a1_notation}")
        
        col_str, row_str = match.groups()
        row = int(row_str) - 1  # Convert to 0-based
        col = cls._col_str_to_int(col_str)
        
        return cls(row, col)
    
    @staticmethod
    def _col_str_to_int(col_str: str) -> int:
        """Convert column string to 0-based integer."""
        result = 0
        for char in col_str:
            result = result * 26 + (ord(char) - ord('A') + 1)
        return result - 1
    
    @staticmethod
    def _int_to_col_str(col_int: int) -> str:
        """Convert 0-based integer to column string."""
        result = ""
        col_int += 1  # Convert to 1-based for calculation
        while col_int > 0:
            col_int -= 1  # Adjust for 0-based alphabet
            result = chr(col_int % 26 + ord('A')) + result
            col_int //= 26
        return result
    
    def to_a1(self) -> str:
        """Convert to A1 notation."""
        col_str = self._int_to_col_str(self.col)
        return f"{col_str}{self.row + 1}"
    
    def offset(self, row_offset: int, col_offset: int) -> 'CellCoordinate':
        """Create a new coordinate with the given offset."""
        return CellCoordinate(self.row + row_offset, self.col + col_offset)
    
    def __str__(self) -> str:
        return self.to_a1()
    
    def __repr__(self) -> str:
        return f"CellCoordinate({self.row}, {self.col})"


@dataclass(frozen=True)
class CellRange:
    """Immutable cell range with efficient iteration."""
    
    start: CellCoordinate
    end: CellCoordinate
    
    def __post_init__(self):
        if self.start.row > self.end.row or self.start.col > self.end.col:
            raise ValueError("Start coordinate must be <= end coordinate")
    
    @classmethod
    def from_a1(cls, a1_range: str) -> 'CellRange':
        """Create range from A1 notation (e.g., 'A1:B10')."""
        if ':' not in a1_range:
            # Single cell range
            coord = CellCoordinate.from_a1(a1_range)
            return cls(coord, coord)
        
        start_str, end_str = a1_range.split(':', 1)
        start = CellCoordinate.from_a1(start_str)
        end = CellCoordinate.from_a1(end_str)
        
        return cls(start, end)
    
    @classmethod
    def from_coordinates(cls, start_row: int, start_col: int, 
                        end_row: int, end_col: int) -> 'CellRange':
        """Create range from numeric coordinates."""
        start = CellCoordinate(start_row, start_col)
        end = CellCoordinate(end_row, end_col)
        return cls(start, end)
    
    def to_a1(self) -> str:
        """Convert to A1 notation."""
        if self.start == self.end:
            return self.start.to_a1()
        return f"{self.start.to_a1()}:{self.end.to_a1()}"
    
    def contains(self, coord: CellCoordinate) -> bool:
        """Check if the range contains the given coordinate."""
        return (self.start.row <= coord.row <= self.end.row and
                self.start.col <= coord.col <= self.end.col)
    
    def intersects(self, other: 'CellRange') -> bool:
        """Check if this range intersects with another range."""
        return not (self.end.row < other.start.row or 
                   self.start.row > other.end.row or
                   self.end.col < other.start.col or 
                   self.start.col > other.end.col)
    
    def intersection(self, other: 'CellRange') -> Optional['CellRange']:
        """Get the intersection of this range with another range."""
        if not self.intersects(other):
            return None
        
        start_row = max(self.start.row, other.start.row)
        start_col = max(self.start.col, other.start.col)
        end_row = min(self.end.row, other.end.row)
        end_col = min(self.end.col, other.end.col)
        
        return CellRange.from_coordinates(start_row, start_col, end_row, end_col)
    
    def union(self, other: 'CellRange') -> 'CellRange':
        """Get the union of this range with another range."""
        start_row = min(self.start.row, other.start.row)
        start_col = min(self.start.col, other.start.col)
        end_row = max(self.end.row, other.end.row)
        end_col = max(self.end.col, other.end.col)
        
        return CellRange.from_coordinates(start_row, start_col, end_row, end_col)
    
    def expand(self, rows: int, cols: int) -> 'CellRange':
        """Expand the range by the given number of rows and columns."""
        return CellRange.from_coordinates(
            max(0, self.start.row - rows),
            max(0, self.start.col - cols),
            self.end.row + rows,
            self.end.col + cols
        )
    
    @property
    def row_count(self) -> int:
        """Get the number of rows in the range."""
        return self.end.row - self.start.row + 1
    
    @property
    def col_count(self) -> int:
        """Get the number of columns in the range."""
        return self.end.col - self.start.col + 1
    
    @property
    def cell_count(self) -> int:
        """Get the total number of cells in the range."""
        return self.row_count * self.col_count
    
    def __iter__(self) -> Iterator[CellCoordinate]:
        """Iterate over all coordinates in the range."""
        for row in range(self.start.row, self.end.row + 1):
            for col in range(self.start.col, self.end.col + 1):
                yield CellCoordinate(row, col)
    
    def iter_by_rows(self) -> Iterator[Iterator[CellCoordinate]]:
        """Iterate over coordinates row by row."""
        for row in range(self.start.row, self.end.row + 1):
            yield (CellCoordinate(row, col) 
                   for col in range(self.start.col, self.end.col + 1))
    
    def iter_by_cols(self) -> Iterator[Iterator[CellCoordinate]]:
        """Iterate over coordinates column by column."""
        for col in range(self.start.col, self.end.col + 1):
            yield (CellCoordinate(row, col) 
                   for row in range(self.start.row, self.end.row + 1))
    
    def __str__(self) -> str:
        return self.to_a1()
    
    def __repr__(self) -> str:
        return f"CellRange({self.start!r}, {self.end!r})"


# Utility functions for coordinate operations
def parse_range_or_coordinate(text: str) -> Tuple[CellCoordinate, Optional[CellCoordinate]]:
    """Parse a text that could be either a single coordinate or a range."""
    if ':' in text:
        range_obj = CellRange.from_a1(text)
        return range_obj.start, range_obj.end
    else:
        coord = CellCoordinate.from_a1(text)
        return coord, None


def get_column_range(col: int, start_row: int = 0, end_row: int = 1048575) -> CellRange:
    """Get a range representing an entire column."""
    return CellRange.from_coordinates(start_row, col, end_row, col)


def get_row_range(row: int, start_col: int = 0, end_col: int = 16383) -> CellRange:
    """Get a range representing an entire row."""
    return CellRange.from_coordinates(row, start_col, row, end_col)

