"""
Core interfaces for the Cell Editor architecture.
These interfaces define the contracts for extensibility and modularity.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List, Iterator, Tuple
from .coordinates import CellCoordinate, CellRange


class ICell(ABC):
    """Interface for cell objects."""
    
    @property
    @abstractmethod
    def value(self) -> Any:
        """Get the computed value of the cell."""
        pass
    
    @value.setter
    @abstractmethod
    def value(self, value: Any) -> None:
        """Set the raw value of the cell."""
        pass
    
    @property
    @abstractmethod
    def formula(self) -> Optional[str]:
        """Get the formula string of the cell."""
        pass
    
    @formula.setter
    @abstractmethod
    def formula(self, formula: Optional[str]) -> None:
        """Set the formula string of the cell."""
        pass
    
    @property
    @abstractmethod
    def format(self) -> Optional[Dict[str, Any]]:
        """Get the formatting information of the cell."""
        pass
    
    @format.setter
    @abstractmethod
    def format(self, format_info: Optional[Dict[str, Any]]) -> None:
        """Set the formatting information of the cell."""
        pass
    
    @property
    @abstractmethod
    def data_type(self) -> str:
        """Get the data type of the cell."""
        pass
    
    @abstractmethod
    def is_empty(self) -> bool:
        """Check if the cell is empty."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear the cell content."""
        pass


class ICellStorage(ABC):
    """Interface for cell storage implementations."""
    
    @abstractmethod
    def get_cell(self, coord: CellCoordinate) -> Optional[ICell]:
        """Get a cell at the specified coordinate."""
        pass
    
    @abstractmethod
    def set_cell(self, coord: CellCoordinate, cell: ICell) -> None:
        """Set a cell at the specified coordinate."""
        pass
    
    @abstractmethod
    def delete_cell(self, coord: CellCoordinate) -> bool:
        """Delete a cell at the specified coordinate."""
        pass
    
    @abstractmethod
    def get_cells_in_range(self, cell_range: CellRange) -> Iterator[Tuple[CellCoordinate, ICell]]:
        """Get all cells within the specified range."""
        pass
    
    @abstractmethod
    def get_used_range(self) -> Optional[CellRange]:
        """Get the range containing all non-empty cells."""
        pass
    
    @abstractmethod
    def clear_range(self, cell_range: CellRange) -> None:
        """Clear all cells in the specified range."""
        pass
    
    @abstractmethod
    def get_memory_usage(self) -> Dict[str, int]:
        """Get memory usage statistics."""
        pass


class ISheet(ABC):
    """Interface for sheet objects."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the sheet name."""
        pass
    
    @name.setter
    @abstractmethod
    def name(self, name: str) -> None:
        """Set the sheet name."""
        pass
    
    @property
    @abstractmethod
    def storage(self) -> ICellStorage:
        """Get the cell storage for this sheet."""
        pass
    
    @abstractmethod
    def get_cell(self, coord: CellCoordinate) -> Optional[ICell]:
        """Get a cell at the specified coordinate."""
        pass
    
    @abstractmethod
    def set_cell(self, coord: CellCoordinate, cell: ICell) -> None:
        """Set a cell at the specified coordinate."""
        pass
    
    @abstractmethod
    def get_used_range(self) -> Optional[CellRange]:
        """Get the range containing all non-empty cells."""
        pass
    
    @abstractmethod
    def insert_rows(self, start_row: int, count: int) -> None:
        """Insert rows at the specified position."""
        pass
    
    @abstractmethod
    def insert_columns(self, start_col: int, count: int) -> None:
        """Insert columns at the specified position."""
        pass
    
    @abstractmethod
    def delete_rows(self, start_row: int, count: int) -> None:
        """Delete rows at the specified position."""
        pass
    
    @abstractmethod
    def delete_columns(self, start_col: int, count: int) -> None:
        """Delete columns at the specified position."""
        pass


class IWorkbook(ABC):
    """Interface for workbook objects."""
    
    @property
    @abstractmethod
    def sheets(self) -> List[ISheet]:
        """Get all sheets in the workbook."""
        pass
    
    @property
    @abstractmethod
    def active_sheet(self) -> Optional[ISheet]:
        """Get the currently active sheet."""
        pass
    
    @active_sheet.setter
    @abstractmethod
    def active_sheet(self, sheet: ISheet) -> None:
        """Set the currently active sheet."""
        pass
    
    @abstractmethod
    def add_sheet(self, name: str) -> ISheet:
        """Add a new sheet to the workbook."""
        pass
    
    @abstractmethod
    def remove_sheet(self, sheet: ISheet) -> bool:
        """Remove a sheet from the workbook."""
        pass
    
    @abstractmethod
    def get_sheet_by_name(self, name: str) -> Optional[ISheet]:
        """Get a sheet by its name."""
        pass
    
    @abstractmethod
    def rename_sheet(self, sheet: ISheet, new_name: str) -> bool:
        """Rename a sheet."""
        pass


class IFormulaEngine(ABC):
    """Interface for formula evaluation engines."""
    
    @abstractmethod
    def evaluate(self, formula: str, context: Dict[str, Any]) -> Any:
        """Evaluate a formula in the given context."""
        pass
    
    @abstractmethod
    def parse(self, formula: str) -> Any:
        """Parse a formula into an AST."""
        pass
    
    @abstractmethod
    def get_dependencies(self, formula: str) -> List[CellCoordinate]:
        """Get the cell dependencies of a formula."""
        pass
    
    @abstractmethod
    def register_function(self, name: str, func: callable) -> None:
        """Register a custom function."""
        pass


class IPlugin(ABC):
    """Interface for plugins."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the plugin name."""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Get the plugin version."""
        pass
    
    @abstractmethod
    def initialize(self, context: Dict[str, Any]) -> None:
        """Initialize the plugin."""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up the plugin resources."""
        pass

