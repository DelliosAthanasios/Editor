"""
Core module for the scalable Cell Editor.
Contains fundamental interfaces and base classes.
"""

from core.interfaces import ICell, ISheet, IWorkbook, ICellStorage
from core.coordinates import CellCoordinate, CellRange
from core.events import CellChangeEvent, EventManager
from core.config import Config

__all__ = [
    'ICell', 'ISheet', 'IWorkbook', 'ICellStorage',
    'CellCoordinate', 'CellRange',
    'CellChangeEvent', 'EventManager',
    'Config'
]

