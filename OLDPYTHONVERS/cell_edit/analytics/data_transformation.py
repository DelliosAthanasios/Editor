"""
Provides mechanisms for defining and executing data transformation pipelines.
Enables users to clean, reshape, and enrich data within the Cell Editor.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import threading

from core.interfaces import ISheet, IWorkbook
from core.coordinates import CellRange, CellCoordinate
from storage.cell import Cell


class TransformationType(Enum):
    """Types of data transformation steps."""
    CLEAN_MISSING = "clean_missing"
    FILL_MISSING = "fill_missing"
    REMOVE_DUPLICATES = "remove_duplicates"
    CONVERT_TYPE = "convert_type"
    APPLY_FUNCTION = "apply_function"
    PIVOT = "pivot"
    UNPIVOT = "unpivot"
    MERGE_COLUMNS = "merge_columns"
    SPLIT_COLUMN = "split_column"
    FILTER_ROWS = "filter_rows"
    SORT_DATA = "sort_data"
    CUSTOM_SCRIPT = "custom_script"


@dataclass
class TransformationStep:
    """
    Defines a single step in a data transformation pipeline.
    """
    step_id: str
    transformation_type: TransformationType
    target_range: Optional[CellRange] = None
    # Parameters specific to each transformation type
    params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class TransformationResult:
    """
    Result of executing a transformation step.
    """
    success: bool
    message: str
    transformed_cells: List[CellCoordinate] = field(default_factory=list)
    new_rows: int = 0
    new_cols: int = 0


class DataTransformer:
    """
    Manages and executes data transformation pipelines on spreadsheet data.
    """
    
    def __init__(self, workbook: IWorkbook):
        self.workbook = workbook
        self._pipelines: Dict[str, List[TransformationStep]] = {}
        self._lock = threading.RLock()

    def add_pipeline(self, pipeline_id: str, steps: List[TransformationStep]) -> None:
        """
        Adds a new transformation pipeline.
        """
        with self._lock:
            if pipeline_id in self._pipelines:
                raise ValueError(f"Pipeline with ID \'{pipeline_id}\' already exists.")
            self._pipelines[pipeline_id] = steps
            print(f"Transformation pipeline \'{pipeline_id}\' added with {len(steps)} steps.")

    def get_pipeline(self, pipeline_id: str) -> Optional[List[TransformationStep]]:
        """
        Retrieves a transformation pipeline by its ID.
        """
        with self._lock:
            return self._pipelines.get(pipeline_id)

    def execute_pipeline(self, sheet_name: str, pipeline_id: str) -> List[TransformationResult]:
        """
        Executes a transformation pipeline on a specified sheet.
        """
        with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline \'{pipeline_id}\' not found.")
            
            sheet = self.workbook.get_sheet(sheet_name)
            if not sheet:
                raise ValueError(f"Sheet \'{sheet_name}\' not found.")
            
            results: List[TransformationResult] = []
            print(f"Executing pipeline \'{pipeline_id}\' on sheet \'{sheet_name}\'")
            
            for i, step in enumerate(pipeline):
                print(f"  Executing step {i+1}: {step.transformation_type.value}")
                result = self._execute_step(sheet, step)
                results.append(result)
                if not result.success:
                    print(f"  Step {i+1} failed: {result.message}. Aborting pipeline.")
                    break
            
            print(f"Pipeline \'{pipeline_id}\' execution finished.")
            return results

    def _execute_step(self, sheet: ISheet, step: TransformationStep) -> TransformationResult:
        """
        Executes a single transformation step.
        This is a simplified implementation; real transformations would be complex.
        """
        try:
            if step.transformation_type == TransformationType.CLEAN_MISSING:
                # Example: Set empty cells to None
                transformed_cells = []
                for row in range(sheet.get_used_range()[0] + 1):
                    for col in range(sheet.get_used_range()[1] + 1):
                        coord = CellCoordinate(row, col)
                        cell = sheet.get_cell(coord)
                        if cell and (cell.value is None or str(cell.value).strip() == ""):
                            sheet.set_cell_value(coord, None)
                            transformed_cells.append(coord)
                return TransformationResult(success=True, message="Missing values cleaned.", transformed_cells=transformed_cells)
            
            elif step.transformation_type == TransformationType.REMOVE_DUPLICATES:
                # Example: Remove duplicate rows based on a column
                # This is a simplified example. A real implementation would involve more complex logic
                # and potentially using pandas for efficiency.
                column_index = step.params.get("column_index")
                if column_index is None:
                    return TransformationResult(success=False, message="column_index parameter is required for REMOVE_DUPLICATES.")

                rows_to_keep = []
                seen_values = set()
                max_row, _ = sheet.get_used_range()

                for r in range(max_row + 1):
                    cell_value = sheet.get_cell(CellCoordinate(r, column_index)).value
                    if cell_value not in seen_values:
                        seen_values.add(cell_value)
                        rows_to_keep.append(r)
                
                # Reconstruct the sheet with unique rows
                # This is a very inefficient way to do it for large sheets, but demonstrates the concept.
                # A proper implementation would involve creating a new sheet or more advanced row manipulation.
                new_sheet_data = []
                for r in rows_to_keep:
                    row_data = []
                    for c in range(sheet.get_used_range()[1] + 1):
                        cell = sheet.get_cell(CellCoordinate(r, c))
                        row_data.append(cell.value)
                    new_sheet_data.append(row_data)
                
                # Clear existing sheet and write new data
                sheet.clear_all_cells()
                transformed_cells = []
                for r_idx, row_values in enumerate(new_sheet_data):
                    for c_idx, value in enumerate(row_values):
                        coord = CellCoordinate(r_idx, c_idx)
                        sheet.set_cell_value(coord, value)
                        transformed_cells.append(coord)

                return TransformationResult(success=True, message="Duplicate rows removed.", transformed_cells=transformed_cells)

            elif step.transformation_type == TransformationType.CONVERT_TYPE:
                # Placeholder for type conversion
                return TransformationResult(success=True, message="Type conversion not fully implemented.")

            elif step.transformation_type == TransformationType.APPLY_FUNCTION:
                # Placeholder for applying a custom function
                return TransformationResult(success=True, message="Apply function not fully implemented.")

            elif step.transformation_type == TransformationType.FILTER_ROWS:
                # Placeholder for filtering rows
                return TransformationResult(success=True, message="Filter rows not fully implemented.")

            elif step.transformation_type == TransformationType.SORT_DATA:
                # Placeholder for sorting data
                return TransformationResult(success=True, message="Sort data not fully implemented.")

            elif step.transformation_type == TransformationType.CUSTOM_SCRIPT:
                # Placeholder for custom script execution
                return TransformationResult(success=True, message="Custom script execution not fully implemented.")

            else:
                return TransformationResult(success=False, message=f"Unknown transformation type: {step.transformation_type.value}")

        except Exception as e:
            return TransformationResult(success=False, message=f"Error during transformation: {e}")

    def remove_pipeline(self, pipeline_id: str) -> bool:
        """
        Removes a transformation pipeline.
        """
        with self._lock:
            if pipeline_id in self._pipelines:
                del self._pipelines[pipeline_id]
                print(f"Transformation pipeline \'{pipeline_id}\' removed.")
                return True
            return False


# Global instance for DataTransformer
_global_data_transformer: Optional[DataTransformer] = None

def get_data_transformer(workbook: IWorkbook) -> DataTransformer:
    """
    Returns the global DataTransformer instance.
    """
    global _global_data_transformer
    if _global_data_transformer is None:
        _global_data_transformer = DataTransformer(workbook)
    return _global_data_transformer


