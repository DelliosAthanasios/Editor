"""
Provides utilities for stress testing the Cell Editor with large datasets.
Simulates operations on millions of cells to identify performance bottlenecks and stability issues.
"""

import random
import string
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.interfaces import IWorkbook, ISheet
from core.coordinates import CellCoordinate
from storage.cell import Cell


class StressTester:
    """
    A utility for stress testing the Cell Editor with various operations.
    """
    
    def __init__(self, workbook: IWorkbook):
        self.workbook = workbook

    def _generate_random_string(self, length: int) -> str:
        """
        Generates a random string of specified length.
        """
        letters = string.ascii_lowercase + string.digits
        return "".join(random.choice(letters) for i in range(length))

    def _generate_random_value(self) -> Any:
        """
        Generates a random cell value (string, int, float, boolean).
        """
        choice = random.randint(0, 3)
        if choice == 0:
            return random.randint(-10000, 10000)
        elif choice == 1:
            return round(random.uniform(-10000.0, 10000.0), 2)
        elif choice == 2:
            return self._generate_random_string(random.randint(5, 20))
        else:
            return random.choice([True, False])

    def populate_sheet(self, sheet_name: str, rows: int, cols: int, 
                       value_type: str = "random", 
                       formula_density: float = 0.1) -> Tuple[float, int]:
        """
        Populates a sheet with a large number of cells.
        
        Args:
            sheet_name (str): The name of the sheet to populate.
            rows (int): Number of rows.
            cols (int): Number of columns.
            value_type (str): Type of values to populate ("random", "string", "number").
            formula_density (float): Probability (0.0-1.0) of a cell containing a formula.
            
        Returns:
            Tuple[float, int]: (time_taken_seconds, cells_populated).
        """
        sheet = self.workbook.get_sheet(sheet_name)
        if not sheet:
            sheet = self.workbook.add_sheet(sheet_name)
            if not sheet:
                raise ValueError(f"Could not create sheet {sheet_name}")

        print(f"Populating sheet \'{sheet_name}\' with {rows}x{cols} cells...")
        start_time = time.perf_counter()
        populated_count = 0

        for r in range(rows):
            for c in range(cols):
                coord = CellCoordinate(r, c)
                
                # Decide if it's a formula or a value
                if random.random() < formula_density:
                    # Simple formula for stress testing
                    formula = f"=SUM(A{r+1}:B{r+1})" if r > 0 else "=1"
                    sheet.set_cell_formula(coord, formula)
                else:
                    value = None
                    if value_type == "random":
                        value = self._generate_random_value()
                    elif value_type == "string":
                        value = self._generate_random_string(random.randint(5, 20))
                    elif value_type == "number":
                        value = random.randint(1, 1000)
                    sheet.set_cell_value(coord, value)
                populated_count += 1
            if (r + 1) % 10000 == 0:
                print(f"  {r+1}/{rows} rows populated...")

        end_time = time.perf_counter()
        time_taken = end_time - start_time
        print(f"Finished populating {populated_count} cells in {time_taken:.2f} seconds.")
        return time_taken, populated_count

    def simulate_random_edits(self, sheet_name: str, num_edits: int, 
                              max_row: int, max_col: int) -> Tuple[float, int]:
        """
        Simulates random cell edits on a sheet.
        
        Args:
            sheet_name (str): The name of the sheet to edit.
            num_edits (int): Number of random edits to perform.
            max_row (int): Maximum row index to edit.
            max_col (int): Maximum column index to edit.
            
        Returns:
            Tuple[float, int]: (time_taken_seconds, edits_performed).
        """
        sheet = self.workbook.get_sheet(sheet_name)
        if not sheet:
            raise ValueError(f"Sheet {sheet_name} not found.")

        print(f"Simulating {num_edits} random edits on sheet \'{sheet_name}\'...")
        start_time = time.perf_counter()
        edits_performed = 0

        for _ in range(num_edits):
            r = random.randint(0, max_row)
            c = random.randint(0, max_col)
            coord = CellCoordinate(r, c)
            new_value = self._generate_random_value()
            sheet.set_cell_value(coord, new_value)
            edits_performed += 1
            if edits_performed % 10000 == 0:
                print(f"  {edits_performed}/{num_edits} edits performed...")

        end_time = time.perf_counter()
        time_taken = end_time - start_time
        print(f"Finished simulating {edits_performed} edits in {time_taken:.2f} seconds.")
        return time_taken, edits_performed

    def simulate_formula_recalculation(self, sheet_name: str, num_recalcs: int) -> Tuple[float, int]:
        """
        Simulates formula recalculations on a sheet.
        (This assumes the formula engine has a triggerable recalculation method).
        
        Args:
            sheet_name (str): The name of the sheet to recalculate.
            num_recalcs (int): Number of recalculations to perform.
            
        Returns:
            Tuple[float, int]: (time_taken_seconds, recalculations_performed).
        """
        sheet = self.workbook.get_sheet(sheet_name)
        if not sheet:
            raise ValueError(f"Sheet {sheet_name} not found.")

        print(f"Simulating {num_recalcs} formula recalculations on sheet \'{sheet_name}\'...")
        start_time = time.perf_counter()
        recalcs_performed = 0

        # In a real system, this would trigger the formula engine to recalculate the sheet
        # For now, we'll just simulate a delay.
        for _ in range(num_recalcs):
            # get_formula_engine().recalculate_sheet(sheet_name) # Hypothetical call
            time.sleep(0.001) # Simulate some work
            recalcs_performed += 1
            if recalcs_performed % 1000 == 0:
                print(f"  {recalcs_performed}/{num_recalcs} recalculations performed...")

        end_time = time.perf_counter()
        time_taken = end_time - start_time
        print(f"Finished simulating {recalcs_performed} recalculations in {time_taken:.2f} seconds.")
        return time_taken, recalcs_performed


# Example Usage (requires a mock IWorkbook and ISheet implementation)
if __name__ == '__main__':
    class MockCell:
        def __init__(self, value=None, formula=None):
            self._value = value
            self._formula = formula

        @property
        def value(self):
            return self._value

        @property
        def formula(self):
            return self._formula

        def set_value(self, value):
            self._value = value

        def set_formula(self, formula):
            self._formula = formula

    class MockSheet(ISheet):
        def __init__(self, name):
            self.name = name
            self._cells: Dict[CellCoordinate, MockCell] = {}
            self._max_row = -1
            self._max_col = -1

        def get_name(self) -> str:
            return self.name

        def get_cell(self, coordinate: CellCoordinate) -> Optional[Cell]:
            return self._cells.get(coordinate)

        def set_cell_value(self, coordinate: CellCoordinate, value: Any) -> None:
            cell = self._cells.get(coordinate)
            if not cell:
                cell = MockCell()
                self._cells[coordinate] = cell
            cell.set_value(value)
            self._update_used_range(coordinate)

        def set_cell_formula(self, coordinate: CellCoordinate, formula: str) -> None:
            cell = self._cells.get(coordinate)
            if not cell:
                cell = MockCell()
                self._cells[coordinate] = cell
            cell.set_formula(formula)
            self._update_used_range(coordinate)

        def get_used_range(self) -> Tuple[int, int]:
            return self._max_row, self._max_col

        def _update_used_range(self, coordinate: CellCoordinate):
            if coordinate.row > self._max_row:
                self._max_row = coordinate.row
            if coordinate.col > self._max_col:
                self._max_col = coordinate.col

        def clear_all_cells(self) -> None:
            self._cells.clear()
            self._max_row = -1
            self._max_col = -1

    class MockWorkbook(IWorkbook):
        def __init__(self):
            self._sheets: Dict[str, ISheet] = {}

        def get_sheet(self, name: str) -> Optional[ISheet]:
            return self._sheets.get(name)

        def get_sheet_names(self) -> List[str]:
            return list(self._sheets.keys())

        def add_sheet(self, name: str) -> ISheet:
            if name in self._sheets:
                raise ValueError(f"Sheet \'{name}\' already exists.")
            sheet = MockSheet(name)
            self._sheets[name] = sheet
            return sheet

        def remove_sheet(self, name: str) -> bool:
            if name in self._sheets:
                del self._sheets[name]
                return True
            return False

    # Setup
    mock_workbook = MockWorkbook()
    tester = StressTester(mock_workbook)

    # Test 1: Populate a large sheet
    sheet_name = "LargeSheet"
    rows = 100000 # 100k rows
    cols = 10 # 10 columns
    total_cells = rows * cols
    print(f"\n--- Test 1: Populating {total_cells} cells ---")
    time_taken, populated_count = tester.populate_sheet(sheet_name, rows, cols, formula_density=0.05)
    print(f"Populated {populated_count} cells in {time_taken:.2f} seconds.")

    # Test 2: Simulate random edits
    num_edits = 50000 # 50k edits
    print(f"\n--- Test 2: Simulating {num_edits} random edits ---")
    time_taken, edits_performed = tester.simulate_random_edits(sheet_name, num_edits, rows - 1, cols - 1)
    print(f"Performed {edits_performed} edits in {time_taken:.2f} seconds.")

    # Test 3: Simulate formula recalculations
    num_recalcs = 10000 # 10k recalculations
    print(f"\n--- Test 3: Simulating {num_recalcs} formula recalculations ---")
    time_taken, recalcs_performed = tester.simulate_formula_recalculation(sheet_name, num_recalcs)
    print(f"Performed {recalcs_performed} recalculations in {time_taken:.2f} seconds.")

    print("\nStress testing complete.")


