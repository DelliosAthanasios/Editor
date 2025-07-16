"""
Provides seamless integration with Pandas DataFrames for advanced data manipulation.
Enables two-way binding between spreadsheet data and Pandas DataFrames.
"""

import pandas as pd
from typing import Any, Dict, List, Optional, Tuple

from core.coordinates import CellRange, CellCoordinate
from core.interfaces import ISheet, IWorkbook
from core.events import get_event_manager, EventType, CellChangeEvent
from storage.cell import Cell


class PandasIntegration:
    """
    Manages the two-way binding and interaction between Cell Editor sheets and Pandas DataFrames.
    """
    
    def __init__(self, workbook: IWorkbook):
        self.workbook = workbook
        self._sheet_to_df_map: Dict[str, pd.DataFrame] = {}
        self._df_to_sheet_map: Dict[int, str] = {} # Map DataFrame ID to sheet name
        self._lock = threading.RLock()
        
        # Subscribe to cell change events to update DataFrames
        get_event_manager().subscribe(EventType.CELL_VALUE_CHANGED, self._on_cell_changed)
        get_event_manager().subscribe(EventType.CELL_FORMULA_CHANGED, self._on_cell_changed)

    def sheet_to_dataframe(self, sheet_name: str, header: bool = True) -> Optional[pd.DataFrame]:
        """
        Converts a specified sheet into a Pandas DataFrame.
        
        Args:
            sheet_name (str): The name of the sheet to convert.
            header (bool): If True, the first row is treated as the header.
            
        Returns:
            Optional[pd.DataFrame]: The Pandas DataFrame, or None if the sheet is not found.
        """
        with self._lock:
            sheet = self.workbook.get_sheet(sheet_name)
            if not sheet:
                print(f"Sheet \'{sheet_name}\' not found.")
                return None
            
            # Determine the used range of the sheet
            max_row, max_col = sheet.get_used_range()
            if max_row < 0 or max_col < 0:
                return pd.DataFrame() # Empty sheet

            data = []
            for r in range(max_row + 1):
                row_data = []
                for c in range(max_col + 1):
                    cell = sheet.get_cell(CellCoordinate(r, c))
                    row_data.append(cell.value if cell else None)
                data.append(row_data)
            
            df = pd.DataFrame(data)
            
            if header and not df.empty:
                # Set the first row as header and remove it from data
                df.columns = df.iloc[0]
                df = df[1:].reset_index(drop=True)
            
            self._sheet_to_df_map[sheet_name] = df
            self._df_to_sheet_map[id(df)] = sheet_name
            return df

    def dataframe_to_sheet(self, df: pd.DataFrame, sheet_name: str, start_row: int = 0, start_col: int = 0) -> bool:
        """
        Writes a Pandas DataFrame to a specified sheet, starting at a given cell.
        
        Args:
            df (pd.DataFrame): The DataFrame to write.
            sheet_name (str): The name of the target sheet.
            start_row (int): The starting row index in the sheet.
            start_col (int): The starting column index in the sheet.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        with self._lock:
            sheet = self.workbook.get_sheet(sheet_name)
            if not sheet:
                print(f"Sheet \'{sheet_name}\' not found. Creating new sheet.")
                sheet = self.workbook.add_sheet(sheet_name)
                if not sheet:
                    print(f"Failed to create sheet \'{sheet_name}\".")
                    return False
            
            # Write header
            for c_idx, col_name in enumerate(df.columns):
                sheet.set_cell_value(CellCoordinate(start_row, start_col + c_idx), str(col_name))
            
            # Write data
            for r_idx, row in df.iterrows():
                for c_idx, value in enumerate(row):
                    sheet.set_cell_value(CellCoordinate(start_row + 1 + r_idx, start_col + c_idx), value)
            
            # Update internal map
            self._sheet_to_df_map[sheet_name] = df
            self._df_to_sheet_map[id(df)] = sheet_name
            
            # Trigger a recalculation for the sheet if needed
            get_event_manager().publish(EventType.SHEET_DATA_CHANGED, sheet_name=sheet_name)
            
            return True

    def get_dataframe_for_sheet(self, sheet_name: str) -> Optional[pd.DataFrame]:
        """
        Retrieves the associated DataFrame for a given sheet.
        """
        with self._lock:
            return self._sheet_to_df_map.get(sheet_name)

    def _on_cell_changed(self, event: CellChangeEvent) -> None:
        """
        Internal handler for cell change events to update associated DataFrames.
        This is a simplified one-way sync for now (sheet to DF).
        Full two-way binding would require more complex change tracking and merging.
        """
        with self._lock:
            sheet_name = event.sheet_name
            if sheet_name in self._sheet_to_df_map:
                df = self._sheet_to_df_map[sheet_name]
                coord = event.coordinate
                
                # Assuming the DataFrame was created with header=True, so data starts at row 1
                df_row = coord.row - 1 # Adjust for header row
                df_col = coord.col
                
                if df_row >= 0 and df_row < len(df) and df_col >= 0 and df_col < len(df.columns):
                    # Get the column name from the DataFrame's header
                    col_name = df.columns[df_col]
                    
                    # Update the DataFrame cell
                    # Use .loc for label-based indexing to avoid SettingWithCopyWarning
                    df.loc[df_row, col_name] = event.new_value
                    print(f"DataFrame for sheet \'{sheet_name}\' updated at ({df_row}, {df_col}) to {event.new_value}")
                else:
                    print(f"Cell change at {coord.to_a1()} is outside current DataFrame bounds for sheet \'{sheet_name}\\'")

    def cleanup(self) -> None:
        """
        Cleans up resources and unsubscribes from events.
        """
        get_event_manager().unsubscribe(EventType.CELL_VALUE_CHANGED, self._on_cell_changed)
        get_event_manager().unsubscribe(EventType.CELL_FORMULA_CHANGED, self._on_cell_changed)
        self._sheet_to_df_map.clear()
        self._df_to_sheet_map.clear()


# Global instance for PandasIntegration
_global_pandas_integration: Optional[PandasIntegration] = None

def get_pandas_integration(workbook: IWorkbook) -> PandasIntegration:
    """
    Returns the global PandasIntegration instance.
    """
    global _global_pandas_integration
    if _global_pandas_integration is None:
        _global_pandas_integration = PandasIntegration(workbook)
    return _global_pandas_integration


