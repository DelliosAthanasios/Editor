"""
Provides data validation and constraint mechanisms for spreadsheet cells.
Ensures data integrity and guides user input.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import re
import threading

from core.coordinates import CellRange, CellCoordinate
from core.interfaces import ISheet, IWorkbook
from core.events import get_event_manager, EventType, CellChangeEvent


class ValidationType(Enum):
    """Types of data validation rules."""
    ANY_VALUE = "any_value"
    WHOLE_NUMBER = "whole_number"
    DECIMAL = "decimal"
    LIST = "list"
    DATE = "date"
    TIME = "time"
    TEXT_LENGTH = "text_length"
    CUSTOM = "custom"


class ValidationOperator(Enum):
    """Operators for data validation rules."""
    BETWEEN = "between"
    NOT_BETWEEN = "not_between"
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"


class ErrorAlertStyle(Enum):
    """Styles for error alerts."""
    STOP = "stop"       # Prevents invalid data entry
    WARNING = "warning" # Warns but allows invalid data
    INFORMATION = "information" # Informs but allows invalid data


@dataclass
class ValidationRule:
    """
    Defines a single data validation rule.
    """
    rule_id: str
    validation_type: ValidationType
    operator: Optional[ValidationOperator] = None
    value1: Any = None
    value2: Any = None  # Used for BETWEEN/NOT_BETWEEN
    source_list: Optional[List[str]] = None # Used for LIST
    custom_formula: Optional[str] = None # Used for CUSTOM
    
    input_message_title: Optional[str] = None
    input_message_body: Optional[str] = None
    error_alert_style: ErrorAlertStyle = ErrorAlertStyle.STOP
    error_alert_title: Optional[str] = None
    error_alert_body: Optional[str] = None

    def validate(self, value: Any, sheet: ISheet, cell_coord: CellCoordinate) -> Tuple[bool, Optional[str]]:
        """
        Validates a given value against this rule.
        Returns (is_valid, error_message).
        """
        if self.validation_type == ValidationType.ANY_VALUE:
            return True, None
        
        if self.validation_type == ValidationType.WHOLE_NUMBER:
            try:
                num_value = int(value)
                if not self._check_operator(num_value):
                    return False, self.error_alert_body or f"Value must be a whole number {self.operator.value} {self.value1} (and {self.value2})."
            except (ValueError, TypeError):
                return False, self.error_alert_body or "Value must be a whole number."
        
        elif self.validation_type == ValidationType.DECIMAL:
            try:
                num_value = float(value)
                if not self._check_operator(num_value):
                    return False, self.error_alert_body or f"Value must be a decimal number {self.operator.value} {self.value1} (and {self.value2})."
            except (ValueError, TypeError):
                return False, self.error_alert_body or "Value must be a decimal number."
        
        elif self.validation_type == ValidationType.LIST:
            if self.source_list is None or value not in self.source_list:
                return False, self.error_alert_body or f"Value must be one of: {', '.join(self.source_list or [])}."
        
        elif self.validation_type == ValidationType.DATE:
            # Simplified date validation, would need proper date parsing
            try:
                # Attempt to parse as date (e.g., YYYY-MM-DD)
                re.match(r"^\d{4}-\d{2}-\d{2}$", str(value))
                # Further validation with operator would require date comparison
                return True, None
            except Exception:
                return False, self.error_alert_body or "Value must be a valid date (YYYY-MM-DD)."
        
        elif self.validation_type == ValidationType.TIME:
            # Simplified time validation
            try:
                re.match(r"^\d{2}:\d{2}(:\d{2})?$", str(value))
                return True, None
            except Exception:
                return False, self.error_alert_body or "Value must be a valid time (HH:MM or HH:MM:SS)."
        
        elif self.validation_type == ValidationType.TEXT_LENGTH:
            text_len = len(str(value))
            if not self._check_operator(text_len):
                return False, self.error_alert_body or f"Text length must be {self.operator.value} {self.value1} (and {self.value2})."
        
        elif self.validation_type == ValidationType.CUSTOM:
            # For custom formulas, we would need to evaluate the formula in the context of the cell
            # This is a placeholder and requires integration with the formula engine
            # For now, always return valid for custom rules
            print(f"Custom validation rule \'{self.custom_formula}\' not fully implemented for evaluation.")
            return True, None
            
        return True, None

    def _check_operator(self, num_value: Union[int, float]) -> bool:
        """
        Helper to check numeric/length operators.
        """
        if self.operator == ValidationOperator.BETWEEN:
            return self.value1 <= num_value <= self.value2
        elif self.operator == ValidationOperator.NOT_BETWEEN:
            return not (self.value1 <= num_value <= self.value2)
        elif self.operator == ValidationOperator.EQUAL:
            return num_value == self.value1
        elif self.operator == ValidationOperator.NOT_EQUAL:
            return num_value != self.value1
        elif self.operator == ValidationOperator.GREATER_THAN:
            return num_value > self.value1
        elif self.operator == ValidationOperator.LESS_THAN:
            return num_value < self.value1
        elif self.operator == ValidationOperator.GREATER_THAN_OR_EQUAL:
            return num_value >= self.value1
        elif self.operator == ValidationOperator.LESS_THAN_OR_EQUAL:
            return num_value <= self.value1
        return True


@dataclass
class ValidationResult:
    """
    Result of a data validation check.
    """
    is_valid: bool
    message: Optional[str] = None
    rule_id: Optional[str] = None
    alert_style: ErrorAlertStyle = ErrorAlertStyle.STOP


class DataValidator:
    """
    Manages data validation rules applied to cells or ranges.
    """
    
    def __init__(self):
        # Maps sheet_name -> { CellCoordinate -> List[ValidationRule] }
        self._rules_by_sheet: Dict[str, Dict[CellCoordinate, List[ValidationRule]]] = {}
        # Maps sheet_name -> { CellRange -> List[ValidationRule] } (for range-based rules)
        self._range_rules_by_sheet: Dict[str, Dict[CellRange, List[ValidationRule]]] = {}
        self._lock = threading.RLock()

    def add_rule(self, sheet_name: str, target_range: CellRange, rule: ValidationRule) -> None:
        """
        Adds a data validation rule to a specified range of cells.
        """
        with self._lock:
            if sheet_name not in self._rules_by_sheet:
                self._rules_by_sheet[sheet_name] = {}
            if sheet_name not in self._range_rules_by_sheet:
                self._range_rules_by_sheet[sheet_name] = {}
            
            # For simplicity, we'll store rules per cell for now, but a range-based storage
            # would be more efficient for large ranges.
            # For now, iterate through the range and apply to each cell.
            for row in range(target_range.start.row, target_range.end.row + 1):
                for col in range(target_range.start.col, target_range.end.col + 1):
                    coord = CellCoordinate(row, col)
                    if coord not in self._rules_by_sheet[sheet_name]:
                        self._rules_by_sheet[sheet_name][coord] = []
                    self._rules_by_sheet[sheet_name][coord].append(rule)
            
            # Also store the rule for the range itself (for UI to display range rules)
            if target_range not in self._range_rules_by_sheet[sheet_name]:
                self._range_rules_by_sheet[sheet_name][target_range] = []
            self._range_rules_by_sheet[sheet_name][target_range].append(rule)
            
            print(f"Added validation rule \'{rule.rule_id}\' to {sheet_name}!{target_range.to_a1()}")

    def remove_rule(self, sheet_name: str, rule_id: str) -> bool:
        """
        Removes a data validation rule by its ID from a sheet.
        Note: This removes all instances of the rule with this ID.
        """
        with self._lock:
            if sheet_name not in self._rules_by_sheet:
                return False
            
            removed = False
            # Remove from cell-specific rules
            for coord in list(self._rules_by_sheet[sheet_name].keys()):
                original_len = len(self._rules_by_sheet[sheet_name][coord])
                self._rules_by_sheet[sheet_name][coord] = [
                    r for r in self._rules_by_sheet[sheet_name][coord] if r.rule_id != rule_id
                ]
                if len(self._rules_by_sheet[sheet_name][coord]) < original_len:
                    removed = True
                if not self._rules_by_sheet[sheet_name][coord]:
                    del self._rules_by_sheet[sheet_name][coord]
            
            # Remove from range-specific rules
            for cell_range in list(self._range_rules_by_sheet[sheet_name].keys()):
                original_len = len(self._range_rules_by_sheet[sheet_name][cell_range])
                self._range_rules_by_sheet[sheet_name][cell_range] = [
                    r for r in self._range_rules_by_sheet[sheet_name][cell_range] if r.rule_id != rule_id
                ]
                if len(self._range_rules_by_sheet[sheet_name][cell_range]) < original_len:
                    removed = True
                if not self._range_rules_by_sheet[sheet_name][cell_range]:
                    del self._range_rules_by_sheet[sheet_name][cell_range]
            
            if removed:
                print(f"Removed validation rule \'{rule_id}\' from sheet \'{sheet_name}\'")
            return removed

    def get_rules_for_cell(self, sheet_name: str, coordinate: CellCoordinate) -> List[ValidationRule]:
        """
        Retrieves all validation rules applicable to a specific cell.
        """
        with self._lock:
            if sheet_name not in self._rules_by_sheet:
                return []
            return self._rules_by_sheet[sheet_name].get(coordinate, [])

    def validate_cell(self, sheet: ISheet, coordinate: CellCoordinate, value: Any) -> ValidationResult:
        """
        Validates a cell's value against all applicable rules.
        """
        rules = self.get_rules_for_cell(sheet.name, coordinate)
        
        for rule in rules:
            is_valid, message = rule.validate(value, sheet, coordinate)
            if not is_valid:
                return ValidationResult(
                    is_valid=False,
                    message=message,
                    rule_id=rule.rule_id,
                    alert_style=rule.error_alert_style
                )
        
        return ValidationResult(is_valid=True)

    def get_all_rules(self) -> Dict[str, Dict[CellRange, List[ValidationRule]]]:
        """
        Returns all registered rules, grouped by sheet and range.
        """
        with self._lock:
            return self._range_rules_by_sheet

    def clear_rules(self, sheet_name: str) -> None:
        """
        Clears all validation rules from a specific sheet.
        """
        with self._lock:
            if sheet_name in self._rules_by_sheet:
                del self._rules_by_sheet[sheet_name]
            if sheet_name in self._range_rules_by_sheet:
                del self._range_rules_by_sheet[sheet_name]
            print(f"Cleared all validation rules from sheet \'{sheet_name}\'")


# Global instance for DataValidator
_global_data_validator: Optional[DataValidator] = None

def get_data_validator() -> DataValidator:
    """
    Returns the global DataValidator instance.
    """
    global _global_data_validator
    if _global_data_validator is None:
        _global_data_validator = DataValidator()
    return _global_data_validator


# Custom exception for validation errors
class ValidationError(Exception):
    """Raised when a data validation rule fails."""
    pass


