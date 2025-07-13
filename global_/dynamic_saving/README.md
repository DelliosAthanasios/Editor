# Dynamic Saving Module

This package provides a modular, optimized, and extensible dynamic (auto) saving system for editor tabs, supporting both the main editor and canvas, and robust for large files.

## Structure
- `core.py`: Core logic for dynamic saving, including background saving for large files.
- `qt_adapter.py`: PyQt5-specific wiring to connect editor signals to the dynamic saver.
- `utils.py`: Utility functions for file writing, hashing, and chunked writing.
- `strategies.py`: Pluggable saving strategies (e.g., chunked, incremental).
- `__init__.py`: Convenient imports.

## Usage

### For PyQt5-based editors (main editor or canvas):
```python
from global_.dynamic_saving import enable_dynamic_saving_for_qt
# ...
enable_dynamic_saving_for_qt(main_window, save_interval_ms=2000)
```

## Extending
- Add new saving strategies in `strategies.py` and use them in `core.py` as needed.
- Utilities for atomic and chunked writes are in `utils.py`.

## Large File Handling
- Files >2MB are saved in a background thread to avoid UI blocking.
- Chunked writing is available for very large files.

## Error Handling
- Errors during saving are logged to the console. 