"""
Defines the binary file format for saving and loading Cell Editor workbooks.
Focuses on efficiency, compression, and extensibility.
"""

import struct
import zlib
from typing import Any, Dict, List, Tuple, Union, Optional

from core.coordinates import CellCoordinate, CellRange
from storage.cell import Cell
from storage.sparse_matrix import SparseMatrix
from core.interfaces import IWorkbook, ISheet


# File format version
FILE_FORMAT_VERSION = 1

# Magic number to identify Cell Editor files
MAGIC_NUMBER = b'CEF\x01' # Cell Editor File, version 1


class CellEditorFileFormat:
    """
    Handles the serialization and deserialization of Cell Editor workbooks
    to and from a custom binary file format.
    """
    
    def __init__(self):
        pass

    def save_workbook(self, workbook: IWorkbook, file_path: str) -> None:
        """
        Saves the entire workbook to a binary file.
        """
        with open(file_path, 'wb') as f:
            f.write(MAGIC_NUMBER)
            f.write(struct.pack('<H', FILE_FORMAT_VERSION)) # Write version as unsigned short
            
            # Write workbook metadata (e.g., number of sheets)
            num_sheets = len(workbook.get_sheet_names())
            f.write(struct.pack('<I', num_sheets)) # Write number of sheets as unsigned int
            
            for sheet_name in workbook.get_sheet_names():
                sheet = workbook.get_sheet(sheet_name)
                if sheet:
                    self._save_sheet(f, sheet)
                else:
                    # Handle case where sheet might have been removed during iteration
                    print(f"Warning: Sheet \'{sheet_name}\' not found during save.")

    def _save_sheet(self, f, sheet: ISheet) -> None:
        """
        Saves a single sheet to the file.
        """
        # Write sheet name length and name
        sheet_name_bytes = sheet.name.encode('utf-8')
        f.write(struct.pack('<H', len(sheet_name_bytes))) # Length of name
        f.write(sheet_name_bytes)
        
        # Get all non-empty cells from the sparse matrix
        cells_data = []
        used_range = sheet.get_used_range()
        if used_range is None:
            max_row = -1
            max_col = -1
        else:
            max_row = used_range.end.row
            max_col = used_range.end.col
        for r in range(max_row + 1):
            for c in range(max_col + 1):
                coord = CellCoordinate(r, c)
                cell = sheet.get_cell(coord)
                if cell and (cell.value is not None or cell.formula is not None):
                    cells_data.append((coord.row, coord.col, cell.value, cell.formula))
        
        # Serialize cells data
        serialized_cells = []
        for r, c, value, formula in cells_data:
            # Format: row (I), col (I), value_type (B), value_len (H), value_bytes, formula_len (H), formula_bytes
            value_bytes = b''
            value_type = 0 # 0: None, 1: int, 2: float, 3: str, 4: bool
            if value is None:
                value_type = 0
            elif isinstance(value, int):
                value_type = 1
                value_bytes = str(value).encode('utf-8')
            elif isinstance(value, float):
                value_type = 2
                value_bytes = str(value).encode('utf-8')
            elif isinstance(value, str):
                value_type = 3
                value_bytes = value.encode('utf-8')
            elif isinstance(value, bool):
                value_type = 4
                value_bytes = b'\x01' if value else b'\x00'
            
            formula_bytes = formula.encode('utf-8') if formula else b''
            
            serialized_cells.append(struct.pack('<IIBH', r, c, value_type, len(value_bytes)) + value_bytes + \
                                    struct.pack('<H', len(formula_bytes)) + formula_bytes)
                                    
        # Compress the serialized cells data
        compressed_data = zlib.compress(b''.join(serialized_cells))
        
        # Write compressed data length and data
        f.write(struct.pack('<I', len(compressed_data))) # Length of compressed data
        f.write(compressed_data)

    def load_workbook(self, file_path: str, workbook: IWorkbook) -> None:
        """
        Loads a workbook from a binary file.
        """
        with open(file_path, 'rb') as f:
            magic = f.read(len(MAGIC_NUMBER))
            if magic != MAGIC_NUMBER:
                raise ValueError("Invalid Cell Editor file format.")
            
            version = struct.unpack('<H', f.read(2))[0]
            if version > FILE_FORMAT_VERSION:
                raise ValueError(f"Unsupported file format version: {version}. Max supported: {FILE_FORMAT_VERSION}")
            
            num_sheets = struct.unpack('<I', f.read(4))[0]
            
            for _ in range(num_sheets):
                self._load_sheet(f, workbook)

    def _load_sheet(self, f, workbook: IWorkbook) -> None:
        """
        Loads a single sheet from the file.
        """
        sheet_name_len = struct.unpack('<H', f.read(2))[0]
        sheet_name = f.read(sheet_name_len).decode('utf-8')
        
        sheet = workbook.add_sheet(sheet_name) # Assuming add_sheet returns the sheet object
        if not sheet:
            print(f"Error: Could not add sheet \'{sheet_name}\' during load.")
            # Skip remaining data for this sheet to try and continue loading
            compressed_data_len = struct.unpack('<I', f.read(4))[0]
            f.read(compressed_data_len)
            return

        compressed_data_len = struct.unpack('<I', f.read(4))[0]
        compressed_data = f.read(compressed_data_len)
        
        decompressed_data = zlib.decompress(compressed_data)
        
        offset = 0
        while offset < len(decompressed_data):
            # Read cell data: row (I), col (I), value_type (B), value_len (H)
            header_len = struct.calcsize('<IIBH')
            r, c, value_type, value_len = struct.unpack('<IIBH', decompressed_data[offset:offset+header_len])
            offset += header_len
            
            value = None
            if value_type == 0: # None
                value = None
            elif value_type == 1: # int
                value = int(decompressed_data[offset:offset+value_len].decode('utf-8'))
            elif value_type == 2: # float
                value = float(decompressed_data[offset:offset+value_len].decode('utf-8'))
            elif value_type == 3: # str
                value = decompressed_data[offset:offset+value_len].decode('utf-8')
            elif value_type == 4: # bool
                value = True if decompressed_data[offset:offset+value_len] == b'\x01' else False
            offset += value_len
            
            # Read formula_len (H)
            formula_len = struct.unpack('<H', decompressed_data[offset:offset+struct.calcsize('<H')])[0]
            offset += struct.calcsize('<H')
            
            formula = None
            if formula_len > 0:
                formula = decompressed_data[offset:offset+formula_len].decode('utf-8')
            offset += formula_len
            
            # Set cell value and formula in the sheet
            coord = CellCoordinate(r, c)
            sheet.set_cell_value(coord, value)
            if formula:
                sheet.set_cell_formula(coord, formula)


# Example Usage (requires a mock IWorkbook and ISheet implementation)
if __name__ == '__main__':
    class MockCell(Cell):
        def __init__(self, value=None, formula=None):
            super().__init__()
            self._value = value
            self._formula = formula

        @property
        def value(self):
            return self._value

        @property
        def formula(self):
            return self._formula

    class MockSheet(ISheet):
        def __init__(self, name):
            self.name = name
            self._cells = SparseMatrix()
            self._max_row = -1
            self._max_col = -1

        def get_name(self) -> str:
            return self.name

        def get_cell(self, coordinate: CellCoordinate) -> Optional[Cell]:
            return self._cells.get(coordinate.row, coordinate.col)

        def set_cell_value(self, coordinate: CellCoordinate, value: Any) -> None:
            cell = self._cells.get(coordinate.row, coordinate.col)
            if not cell:
                cell = MockCell()
                self._cells.set(coordinate.row, coordinate.col, cell)
            cell._value = value # Directly set for mock
            self._update_used_range(coordinate)

        def set_cell_formula(self, coordinate: CellCoordinate, formula: str) -> None:
            cell = self._cells.get(coordinate.row, coordinate.col)
            if not cell:
                cell = MockCell()
                self._cells.set(coordinate.row, coordinate.col, cell)
            cell._formula = formula # Directly set for mock
            self._update_used_range(coordinate)

        def get_used_range(self) -> Tuple[int, int]:
            return self._max_row, self._max_col

        def _update_used_range(self, coordinate: CellCoordinate):
            if coordinate.row > self._max_row:
                self._max_row = coordinate.row
            if coordinate.col > self._max_col:
                self._max_col = coordinate.col

        def clear_all_cells(self) -> None:
            self._cells = SparseMatrix()
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


    # Test saving and loading
    workbook = MockWorkbook()
    sheet1 = workbook.add_sheet("Sheet1")
    sheet1.set_cell_value(CellCoordinate(0, 0), "Hello")
    sheet1.set_cell_formula(CellCoordinate(0, 1), "=SUM(A1:A10)")
    sheet1.set_cell_value(CellCoordinate(1, 0), 123)
    sheet1.set_cell_value(CellCoordinate(2, 2), 45.67)
    sheet1.set_cell_value(CellCoordinate(3, 0), True)

    sheet2 = workbook.add_sheet("AnotherSheet")
    sheet2.set_cell_value(CellCoordinate(5, 5), "Test")

    file_format = CellEditorFileFormat()
    test_file = "test_workbook.cef"
    file_format.save_workbook(workbook, test_file)
    print(f"Workbook saved to {test_file}")

    # Load workbook
    loaded_workbook = MockWorkbook()
    file_format.load_workbook(test_file, loaded_workbook)
    print(f"Workbook loaded from {test_file}")

    loaded_sheet1 = loaded_workbook.get_sheet("Sheet1")
    if loaded_sheet1:
        print(f"Sheet1 A1: {loaded_sheet1.get_cell(CellCoordinate(0, 0)).value}")
        print(f"Sheet1 B1 formula: {loaded_sheet1.get_cell(CellCoordinate(0, 1)).formula}")
        print(f"Sheet1 A2: {loaded_sheet1.get_cell(CellCoordinate(1, 0)).value}")
        print(f"Sheet1 C3: {loaded_sheet1.get_cell(CellCoordinate(2, 2)).value}")
        print(f"Sheet1 A4: {loaded_sheet1.get_cell(CellCoordinate(3, 0)).value}")

    loaded_sheet2 = loaded_workbook.get_sheet("AnotherSheet")
    if loaded_sheet2:
        print(f"AnotherSheet F6: {loaded_sheet2.get_cell(CellCoordinate(5, 5)).value}")

    # Clean up test file
    import os
    os.remove(test_file)


