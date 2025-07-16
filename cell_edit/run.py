import sys
from core.coordinates import CellCoordinate
from core.interfaces import ISheet, IWorkbook
from storage.cell import Cell
from storage.sparse_matrix import SparseMatrix
from ui.ui_manager import UIManager

# Minimal in-memory Sheet implementation
class SimpleSheet(ISheet):
    def __init__(self, name):
        self._name = name
        self._storage = SparseMatrix()
    @property
    def name(self):
        return self._name
    @name.setter
    def name(self, name):
        self._name = name
    @property
    def storage(self):
        return self._storage
    def get_cell(self, coord):
        return self._storage.get_cell(coord)
    def set_cell(self, coord, cell):
        self._storage.set_cell(coord, cell)
    def get_used_range(self):
        return self._storage.get_used_range()
    def insert_rows(self, start_row, count):
        pass
    def insert_columns(self, start_col, count):
        pass
    def delete_rows(self, start_row, count):
        pass
    def delete_columns(self, start_col, count):
        pass

# Minimal in-memory Workbook implementation
class SimpleWorkbook(IWorkbook):
    def __init__(self):
        self._sheets = []
        self._active_sheet = None
    @property
    def sheets(self):
        return self._sheets
    @property
    def active_sheet(self):
        return self._active_sheet
    @active_sheet.setter
    def active_sheet(self, sheet):
        self._active_sheet = sheet
    def add_sheet(self, name):
        sheet = SimpleSheet(name)
        self._sheets.append(sheet)
        if not self._active_sheet:
            self._active_sheet = sheet
        return sheet
    def remove_sheet(self, sheet):
        if sheet in self._sheets:
            self._sheets.remove(sheet)
            if self._active_sheet == sheet:
                self._active_sheet = self._sheets[0] if self._sheets else None
            return True
        return False
    def get_sheet_by_name(self, name):
        for sheet in self._sheets:
            if sheet.name == name:
                return sheet
        return None
    def rename_sheet(self, sheet, new_name):
        if sheet in self._sheets:
            sheet.name = new_name
            return True
        return False
    def get_sheet_names(self):
        return [sheet.name for sheet in self._sheets]
    def get_sheet(self, name):
        return self.get_sheet_by_name(name)

if __name__ == "__main__":
    # Create a workbook and a default sheet
    workbook = SimpleWorkbook()
    sheet = workbook.add_sheet("Sheet1")
    # Add some sample values
    sheet.set_cell(CellCoordinate(0, 0), Cell(value="Hello"))
    sheet.set_cell(CellCoordinate(0, 1), Cell(value="World"))
    sheet.set_cell(CellCoordinate(1, 0), Cell(value="42"))
    sheet.set_cell(CellCoordinate(1, 1), Cell(value="=A1 & ' ' & B1"))
    # Launch the UIManager (logic only)
    ui_manager = UIManager(workbook)
    print("Cell Editor v2 started. UIManager initialized.")
    print("Sheets:", workbook.get_sheet_names())
    print("A1 value:", sheet.get_cell(CellCoordinate(0, 0)).value) 