"""
Implements incremental saving for workbooks.
This allows saving only changes made since the last save, improving performance for large files.
"""

import os
import json
import threading
from typing import Any, Dict, List, Optional, Tuple

from core.coordinates import CellCoordinate
from core.interfaces import IWorkbook, ISheet
from core.events import get_event_manager, EventType, CellChangeEvent, Event
from .file_format import CellEditorFileFormat


class IncrementalSaver:
    """
    Manages incremental saving of workbook changes.
    It tracks cell modifications and sheet additions/removals.
    """
    
    def __init__(self, workbook: IWorkbook, base_file_path: str):
        self.workbook = workbook
        self.base_file_path = base_file_path
        self._changes: Dict[str, Dict[CellCoordinate, Any]] = {}
        self._sheet_additions: List[str] = []
        self._sheet_removals: List[str] = []
        self._lock = threading.RLock()
        self._last_saved_state: Dict[str, Dict[CellCoordinate, Any]] = {}

        # Subscribe to relevant events
        get_event_manager().subscribe(EventType.CELL_VALUE_CHANGED, self._on_cell_changed)
        get_event_manager().subscribe(EventType.CELL_FORMULA_CHANGED, self._on_cell_changed)
        get_event_manager().subscribe(EventType.SHEET_ADDED, self._on_sheet_added)
        get_event_manager().subscribe(EventType.SHEET_REMOVED, self._on_sheet_removed)

        self._file_format = CellEditorFileFormat()
        self._load_initial_state()

    def _load_initial_state(self) -> None:
        """
        Loads the initial state of the workbook to establish a baseline for changes.
        This is a simplified approach; a full implementation would involve reading the entire workbook.
        """
        # For now, we'll just initialize an empty state. In a real app, this would load from disk.
        # This method is primarily for setting up the baseline for change tracking.
        print("IncrementalSaver: Initializing empty state for change tracking.")
        for sheet_name in self.workbook.get_sheet_names():
            self._last_saved_state[sheet_name] = {}
            sheet = self.workbook.get_sheet(sheet_name)
            if sheet:
                max_row, max_col = sheet.get_used_range()
                for r in range(max_row + 1):
                    for c in range(max_col + 1):
                        coord = CellCoordinate(r, c)
                        cell = sheet.get_cell(coord)
                        if cell:
                            self._last_saved_state[sheet_name][coord] = {
                                "value": cell.value,
                                "formula": cell.formula
                            }

    def _on_cell_changed(self, event: CellChangeEvent) -> None:
        """
        Records cell changes for incremental saving.
        """
        with self._lock:
            sheet_name = event.sheet_name
            coord = event.coordinate
            new_value = event.new_value
            new_formula = event.new_formula

            if sheet_name not in self._changes:
                self._changes[sheet_name] = {}
            
            # Store the current state of the cell (value and formula)
            self._changes[sheet_name][coord] = {
                "value": new_value,
                "formula": new_formula
            }
            print(f"IncrementalSaver: Recorded change for {sheet_name}!{coord.to_a1()}")

    def _on_sheet_added(self, event: Event) -> None:
        """
        Records sheet additions.
        """
        with self._lock:
            sheet_name = event.data['sheet_name']
            if sheet_name not in self._sheet_additions:
                self._sheet_additions.append(sheet_name)
            # If a sheet was removed and then added back, remove it from removals
            if sheet_name in self._sheet_removals:
                self._sheet_removals.remove(sheet_name)
            print(f"IncrementalSaver: Recorded sheet added: {sheet_name}")

    def _on_sheet_removed(self, event: Event) -> None:
        """
        Records sheet removals.
        """
        with self._lock:
            sheet_name = event.data['sheet_name']
            if sheet_name not in self._sheet_removals:
                self._sheet_removals.append(sheet_name)
            # If a sheet was added and then removed, remove it from additions
            if sheet_name in self._sheet_additions:
                self._sheet_additions.remove(sheet_name)
            # Also clear any pending changes for this sheet
            if sheet_name in self._changes:
                del self._changes[sheet_name]
            print(f"IncrementalSaver: Recorded sheet removed: {sheet_name}")

    def save_incremental(self) -> None:
        """
        Saves only the changes made since the last full or incremental save.
        This creates a patch file.
        """
        with self._lock:
            if not self._changes and not self._sheet_additions and not self._sheet_removals:
                print("IncrementalSaver: No changes to save.")
                return

            patch_data = {
                "version": FILE_FORMAT_VERSION,
                "changes": {},
                "sheet_additions": self._sheet_additions,
                "sheet_removals": self._sheet_removals
            }

            for sheet_name, cell_changes in self._changes.items():
                patch_data["changes"][sheet_name] = [
                    {
                        "row": coord.row,
                        "col": coord.col,
                        "value": change["value"],
                        "formula": change["formula"]
                    }
                    for coord, change in cell_changes.items()
                ]
            
            patch_file_path = self.base_file_path + ".patch"
            with open(patch_file_path, "w") as f:
                json.dump(patch_data, f, indent=2)
            
            print(f"IncrementalSaver: Saved incremental changes to {patch_file_path}")
            self._clear_changes()

    def apply_incremental_patch(self, patch_file_path: str) -> None:
        """
        Applies an incremental patch to the current workbook state.
        This should typically be done on a base file.
        """
        with self._lock:
            if not os.path.exists(patch_file_path):
                print(f"Patch file not found: {patch_file_path}")
                return

            with open(patch_file_path, "r") as f:
                patch_data = json.load(f)

            # Apply sheet removals first
            for sheet_name in patch_data.get("sheet_removals", []):
                self.workbook.remove_sheet(sheet_name)
                print(f"Applied patch: Removed sheet {sheet_name}")

            # Apply sheet additions
            for sheet_name in patch_data.get("sheet_additions", []):
                self.workbook.add_sheet(sheet_name)
                print(f"Applied patch: Added sheet {sheet_name}")

            # Apply cell changes
            for sheet_name, cell_changes in patch_data.get("changes", {}).items():
                sheet = self.workbook.get_sheet(sheet_name)
                if not sheet:
                    print(f"Warning: Sheet {sheet_name} not found when applying patch changes.")
                    continue
                for change in cell_changes:
                    coord = CellCoordinate(change["row"], change["col"])
                    sheet.set_cell_value(coord, change["value"])
                    if change["formula"] is not None:
                        sheet.set_cell_formula(coord, change["formula"])
                    print(f"Applied patch: {sheet_name}!{coord.to_a1()} = {change["value"]} (Formula: {change["formula"]})")
            
            print(f"Successfully applied patch from {patch_file_path}")
            # After applying, the current state becomes the new last_saved_state
            self._load_initial_state() # Re-scan current workbook state

    def _clear_changes(self) -> None:
        """
        Clears the recorded changes after a successful save.
        """
        self._changes.clear()
        self._sheet_additions.clear()
        self._sheet_removals.clear()
        # Update the last_saved_state to reflect the current workbook state
        self._load_initial_state()

    def cleanup(self) -> None:
        """
        Unsubscribes from events and cleans up resources.
        """
        get_event_manager().unsubscribe(EventType.CELL_VALUE_CHANGED, self._on_cell_changed)
        get_event_manager().unsubscribe(EventType.CELL_FORMULA_CHANGED, self._on_cell_changed)
        get_event_manager().unsubscribe(EventType.SHEET_ADDED, self._on_sheet_added)
        get_event_manager().unsubscribe(EventType.SHEET_REMOVED, self._on_sheet_removed)
        self._clear_changes()


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
            cell.set_formula(None) # Clear formula if value is set directly
            self._update_used_range(coordinate)
            get_event_manager().publish(EventType.CELL_VALUE_CHANGED, sheet_name=self.name, coordinate=coordinate, new_value=value, old_value=None)

        def set_cell_formula(self, coordinate: CellCoordinate, formula: str) -> None:
            cell = self._cells.get(coordinate)
            if not cell:
                cell = MockCell()
                self._cells[coordinate] = cell
            cell.set_formula(formula)
            cell.set_value(None) # Clear value if formula is set
            self._update_used_range(coordinate)
            get_event_manager().publish(EventType.CELL_FORMULA_CHANGED, sheet_name=self.name, coordinate=coordinate, new_formula=formula, old_formula=None)

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
            get_event_manager().publish(EventType.SHEET_ADDED, sheet_name=name)
            return sheet

        def remove_sheet(self, name: str) -> bool:
            if name in self._sheets:
                del self._sheets[name]
                get_event_manager().publish(EventType.SHEET_REMOVED, sheet_name=name)
                return True
            return False


    # Test incremental saving
    workbook = MockWorkbook()
    sheet1 = workbook.add_sheet("Sheet1")
    sheet1.set_cell_value(CellCoordinate(0, 0), "Initial Value")
    sheet1.set_cell_formula(CellCoordinate(0, 1), "=SUM(A1:A10)")

    saver = IncrementalSaver(workbook, "test_workbook.cef")

    # Make some changes
    sheet1.set_cell_value(CellCoordinate(0, 0), "Changed Value")
    sheet1.set_cell_value(CellCoordinate(1, 0), 123)
    sheet1.set_cell_formula(CellCoordinate(0, 1), "=AVERAGE(A1:A10)")

    sheet2 = workbook.add_sheet("Sheet2")
    sheet2.set_cell_value(CellCoordinate(0, 0), "New Sheet Data")

    saver.save_incremental()

    # Simulate loading a base file and applying patch
    # First, create a base file (e.g., a full save)
    file_format = CellEditorFileFormat()
    file_format.save_workbook(workbook, "test_workbook.cef")

    # Now, create a new workbook and apply the patch
    new_workbook = MockWorkbook()
    file_format.load_workbook("test_workbook.cef", new_workbook)

    # Simulate more changes to the original workbook for a second patch
    sheet1.set_cell_value(CellCoordinate(2, 2), "Another Change")
    workbook.remove_sheet("Sheet2")
    saver.save_incremental()

    # Apply the second patch to the new workbook
    saver_for_new_workbook = IncrementalSaver(new_workbook, "test_workbook.cef")
    saver_for_new_workbook.apply_incremental_patch("test_workbook.cef.patch")

    # Verify changes in new_workbook
    loaded_sheet1 = new_workbook.get_sheet("Sheet1")
    if loaded_sheet1:
        print(f"Loaded Sheet1 A1: {loaded_sheet1.get_cell(CellCoordinate(0, 0)).value}")
        print(f"Loaded Sheet1 B1 formula: {loaded_sheet1.get_cell(CellCoordinate(0, 1)).formula}")
        print(f"Loaded Sheet1 A2: {loaded_sheet1.get_cell(CellCoordinate(1, 0)).value}")
        print(f"Loaded Sheet1 C3: {loaded_sheet1.get_cell(CellCoordinate(2, 2)).value}")

    loaded_sheet2 = new_workbook.get_sheet("Sheet2")
    print(f"Is Sheet2 present in new_workbook? {loaded_sheet2 is not None}")

    # Clean up test files
    os.remove("test_workbook.cef")
    os.remove("test_workbook.cef.patch")
    saver.cleanup()
    saver_for_new_workbook.cleanup()


