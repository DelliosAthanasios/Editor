"""
Function registry for managing built-in and custom functions.
Provides extensible function system with type checking and documentation.
"""

import math
import statistics
import re
from typing import Any, Callable, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import inspect
import threading

from core.coordinates import CellCoordinate, CellRange


class FunctionCategory(Enum):
    """Categories of functions."""
    MATH = "math"
    STATISTICAL = "statistical"
    LOGICAL = "logical"
    TEXT = "text"
    DATE_TIME = "date_time"
    LOOKUP = "lookup"
    FINANCIAL = "financial"
    ENGINEERING = "engineering"
    INFORMATION = "information"
    CUSTOM = "custom"


@dataclass
class FunctionInfo:
    """Information about a registered function."""
    name: str
    func: Callable
    category: FunctionCategory
    description: str
    syntax: str
    examples: List[str]
    min_args: int
    max_args: Optional[int]  # None for unlimited
    is_volatile: bool = False  # Function result changes even with same inputs
    is_array_function: bool = False  # Function can return arrays
    
    def validate_args(self, args: List[Any]) -> bool:
        """Validate argument count."""
        arg_count = len(args)
        if arg_count < self.min_args:
            return False
        if self.max_args is not None and arg_count > self.max_args:
            return False
        return True


class FunctionRegistry:
    """Registry for managing spreadsheet functions."""
    
    def __init__(self):
        self._functions: Dict[str, FunctionInfo] = {}
        self._lock = threading.RLock()
        self._register_builtin_functions()
    
    def register(self, name: str, func: Callable, category: FunctionCategory,
                description: str, syntax: str, examples: List[str] = None,
                min_args: int = 0, max_args: Optional[int] = None,
                is_volatile: bool = False, is_array_function: bool = False) -> None:
        """Register a function."""
        with self._lock:
            if examples is None:
                examples = []
            
            # Auto-detect argument count if not specified
            if min_args == 0 and max_args is None:
                try:
                    sig = inspect.signature(func)
                    params = [p for p in sig.parameters.values() 
                             if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
                    min_args = len([p for p in params if p.default == p.empty])
                    if any(p.kind == p.VAR_POSITIONAL for p in sig.parameters.values()):
                        max_args = None  # *args present
                    else:
                        max_args = len(params)
                except Exception:
                    pass  # Use defaults
            
            func_info = FunctionInfo(
                name=name.upper(),
                func=func,
                category=category,
                description=description,
                syntax=syntax,
                examples=examples,
                min_args=min_args,
                max_args=max_args,
                is_volatile=is_volatile,
                is_array_function=is_array_function
            )
            
            self._functions[name.upper()] = func_info
    
    def unregister(self, name: str) -> bool:
        """Unregister a function."""
        with self._lock:
            name = name.upper()
            if name in self._functions:
                del self._functions[name]
                return True
            return False
    
    def get_function(self, name: str) -> Optional[FunctionInfo]:
        """Get function information."""
        with self._lock:
            return self._functions.get(name.upper())
    
    def call_function(self, name: str, args: List[Any]) -> Any:
        """Call a registered function."""
        with self._lock:
            func_info = self.get_function(name)
            if not func_info:
                raise ValueError(f"Unknown function: {name}")
            
            if not func_info.validate_args(args):
                arg_count = len(args)
                if func_info.max_args is None:
                    expected = f"at least {func_info.min_args}"
                elif func_info.min_args == func_info.max_args:
                    expected = str(func_info.min_args)
                else:
                    expected = f"{func_info.min_args}-{func_info.max_args}"
                raise ValueError(f"Function {name} expects {expected} arguments, got {arg_count}")
            
            try:
                return func_info.func(*args)
            except Exception as e:
                return f"#ERROR: {e}"
    
    def get_functions_by_category(self, category: FunctionCategory) -> List[FunctionInfo]:
        """Get all functions in a category."""
        with self._lock:
            return [func for func in self._functions.values() if func.category == category]
    
    def get_all_functions(self) -> List[FunctionInfo]:
        """Get all registered functions."""
        with self._lock:
            return list(self._functions.values())
    
    def get_function_names(self) -> List[str]:
        """Get all function names."""
        with self._lock:
            return list(self._functions.keys())
    
    def _register_builtin_functions(self) -> None:
        """Register built-in functions."""
        
        # Math functions
        self.register("SUM", self._sum, FunctionCategory.MATH,
                     "Adds all numbers in a range or list",
                     "SUM(number1, [number2], ...)",
                     ["SUM(A1:A10)", "SUM(1,2,3,4,5)"],
                     min_args=1)
        
        self.register("AVERAGE", self._average, FunctionCategory.STATISTICAL,
                     "Returns the average of numbers",
                     "AVERAGE(number1, [number2], ...)",
                     ["AVERAGE(A1:A10)", "AVERAGE(1,2,3,4,5)"],
                     min_args=1)
        
        self.register("COUNT", self._count, FunctionCategory.STATISTICAL,
                     "Counts the number of cells that contain numbers",
                     "COUNT(value1, [value2], ...)",
                     ["COUNT(A1:A10)", "COUNT(1,2,3,\"text\")"],
                     min_args=1)
        
        self.register("MAX", self._max, FunctionCategory.STATISTICAL,
                     "Returns the largest value",
                     "MAX(number1, [number2], ...)",
                     ["MAX(A1:A10)", "MAX(1,2,3,4,5)"],
                     min_args=1)
        
        self.register("MIN", self._min, FunctionCategory.STATISTICAL,
                     "Returns the smallest value",
                     "MIN(number1, [number2], ...)",
                     ["MIN(A1:A10)", "MIN(1,2,3,4,5)"],
                     min_args=1)
        
        # Logical functions
        self.register("IF", self._if, FunctionCategory.LOGICAL,
                     "Returns one value if condition is true, another if false",
                     "IF(logical_test, value_if_true, [value_if_false])",
                     ["IF(A1>10,\"High\",\"Low\")", "IF(B1=0,\"Zero\",B1)"],
                     min_args=2, max_args=3)
        
        self.register("AND", self._and, FunctionCategory.LOGICAL,
                     "Returns TRUE if all arguments are TRUE",
                     "AND(logical1, [logical2], ...)",
                     ["AND(A1>0, B1<10)", "AND(TRUE, FALSE)"],
                     min_args=1)
        
        self.register("OR", self._or, FunctionCategory.LOGICAL,
                     "Returns TRUE if any argument is TRUE",
                     "OR(logical1, [logical2], ...)",
                     ["OR(A1>0, B1<10)", "OR(TRUE, FALSE)"],
                     min_args=1)
        
        self.register("NOT", self._not, FunctionCategory.LOGICAL,
                     "Reverses the logic of its argument",
                     "NOT(logical)",
                     ["NOT(A1>10)", "NOT(TRUE)"],
                     min_args=1, max_args=1)
        
        # Text functions
        self.register("CONCATENATE", self._concatenate, FunctionCategory.TEXT,
                     "Joins several text strings into one",
                     "CONCATENATE(text1, [text2], ...)",
                     ["CONCATENATE(A1,\" \",B1)", "CONCATENATE(\"Hello\",\" \",\"World\")"],
                     min_args=1)
        
        self.register("LEN", self._len, FunctionCategory.TEXT,
                     "Returns the length of a text string",
                     "LEN(text)",
                     ["LEN(A1)", "LEN(\"Hello World\")"],
                     min_args=1, max_args=1)
        
        self.register("UPPER", self._upper, FunctionCategory.TEXT,
                     "Converts text to uppercase",
                     "UPPER(text)",
                     ["UPPER(A1)", "UPPER(\"hello\")"],
                     min_args=1, max_args=1)
        
        self.register("LOWER", self._lower, FunctionCategory.TEXT,
                     "Converts text to lowercase",
                     "LOWER(text)",
                     ["LOWER(A1)", "LOWER(\"HELLO\")"],
                     min_args=1, max_args=1)
        
        # Lookup functions
        self.register("VLOOKUP", self._vlookup, FunctionCategory.LOOKUP,
                     "Looks up a value in the first column and returns a value in the same row",
                     "VLOOKUP(lookup_value, table_array, col_index_num, [range_lookup])",
                     ["VLOOKUP(A1,B1:D10,3,FALSE)", "VLOOKUP(\"Apple\",A1:C100,2,TRUE)"],
                     min_args=3, max_args=4)
        
        self.register("INDEX", self._index, FunctionCategory.LOOKUP,
                     "Returns a value from a table based on row and column numbers",
                     "INDEX(array, row_num, [column_num])",
                     ["INDEX(A1:C10,5,2)", "INDEX(A1:A10,3)"],
                     min_args=2, max_args=3)
        
        self.register("MATCH", self._match, FunctionCategory.LOOKUP,
                     "Returns the position of a value in an array",
                     "MATCH(lookup_value, lookup_array, [match_type])",
                     ["MATCH(\"Apple\",A1:A10,0)", "MATCH(100,B1:B20,1)"],
                     min_args=2, max_args=3)
        
        # Math functions
        self.register("ABS", self._abs, FunctionCategory.MATH,
                     "Returns the absolute value of a number",
                     "ABS(number)",
                     ["ABS(-5)", "ABS(A1)"],
                     min_args=1, max_args=1)
        
        self.register("ROUND", self._round, FunctionCategory.MATH,
                     "Rounds a number to a specified number of digits",
                     "ROUND(number, num_digits)",
                     ["ROUND(3.14159,2)", "ROUND(A1,0)"],
                     min_args=2, max_args=2)
        
        self.register("SQRT", self._sqrt, FunctionCategory.MATH,
                     "Returns the square root of a number",
                     "SQRT(number)",
                     ["SQRT(16)", "SQRT(A1)"],
                     min_args=1, max_args=1)
        
        self.register("POWER", self._power, FunctionCategory.MATH,
                     "Returns the result of a number raised to a power",
                     "POWER(number, power)",
                     ["POWER(2,3)", "POWER(A1,2)"],
                     min_args=2, max_args=2)
        
        # Information functions
        self.register("ISNUMBER", self._isnumber, FunctionCategory.INFORMATION,
                     "Returns TRUE if the value is a number",
                     "ISNUMBER(value)",
                     ["ISNUMBER(A1)", "ISNUMBER(\"123\")"],
                     min_args=1, max_args=1)
        
        self.register("ISTEXT", self._istext, FunctionCategory.INFORMATION,
                     "Returns TRUE if the value is text",
                     "ISTEXT(value)",
                     ["ISTEXT(A1)", "ISTEXT(123)"],
                     min_args=1, max_args=1)
        
        self.register("ISBLANK", self._isblank, FunctionCategory.INFORMATION,
                     "Returns TRUE if the value is blank",
                     "ISBLANK(value)",
                     ["ISBLANK(A1)", "ISBLANK(\"\")"],
                     min_args=1, max_args=1)
    
    # Built-in function implementations
    def _sum(self, *args) -> Union[float, str]:
        """Sum function implementation."""
        try:
            total = 0
            for arg in args:
                if isinstance(arg, (list, tuple)):
                    total += sum(x for x in arg if isinstance(x, (int, float)))
                elif isinstance(arg, (int, float)):
                    total += arg
            return total
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _average(self, *args) -> Union[float, str]:
        """Average function implementation."""
        try:
            numbers = []
            for arg in args:
                if isinstance(arg, (list, tuple)):
                    numbers.extend(x for x in arg if isinstance(x, (int, float)))
                elif isinstance(arg, (int, float)):
                    numbers.append(arg)
            
            if not numbers:
                return "#DIV/0!"
            
            return sum(numbers) / len(numbers)
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _count(self, *args) -> Union[int, str]:
        """Count function implementation."""
        try:
            count = 0
            for arg in args:
                if isinstance(arg, (list, tuple)):
                    count += sum(1 for x in arg if isinstance(x, (int, float)))
                elif isinstance(arg, (int, float)):
                    count += 1
            return count
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _max(self, *args) -> Union[float, str]:
        """Max function implementation."""
        try:
            numbers = []
            for arg in args:
                if isinstance(arg, (list, tuple)):
                    numbers.extend(x for x in arg if isinstance(x, (int, float)))
                elif isinstance(arg, (int, float)):
                    numbers.append(arg)
            
            if not numbers:
                return "#N/A"
            
            return max(numbers)
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _min(self, *args) -> Union[float, str]:
        """Min function implementation."""
        try:
            numbers = []
            for arg in args:
                if isinstance(arg, (list, tuple)):
                    numbers.extend(x for x in arg if isinstance(x, (int, float)))
                elif isinstance(arg, (int, float)):
                    numbers.append(arg)
            
            if not numbers:
                return "#N/A"
            
            return min(numbers)
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _if(self, condition, value_if_true, value_if_false=None):
        """IF function implementation."""
        try:
            if condition:
                return value_if_true
            else:
                return value_if_false if value_if_false is not None else False
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _and(self, *args) -> Union[bool, str]:
        """AND function implementation."""
        try:
            return all(bool(arg) for arg in args)
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _or(self, *args) -> Union[bool, str]:
        """OR function implementation."""
        try:
            return any(bool(arg) for arg in args)
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _not(self, arg) -> Union[bool, str]:
        """NOT function implementation."""
        try:
            return not bool(arg)
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _concatenate(self, *args) -> Union[str, str]:
        """CONCATENATE function implementation."""
        try:
            return ''.join(str(arg) for arg in args)
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _len(self, text) -> Union[int, str]:
        """LEN function implementation."""
        try:
            return len(str(text))
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _upper(self, text) -> Union[str, str]:
        """UPPER function implementation."""
        try:
            return str(text).upper()
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _lower(self, text) -> Union[str, str]:
        """LOWER function implementation."""
        try:
            return str(text).lower()
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _vlookup(self, lookup_value, table_array, col_index_num, range_lookup=True):
        """VLOOKUP function implementation."""
        try:
            if not isinstance(table_array, list) or not table_array:
                return "#N/A"
            
            col_index = int(col_index_num) - 1  # Convert to 0-based
            if col_index < 0 or col_index >= len(table_array[0]):
                return "#REF!"
            
            for row in table_array:
                if len(row) > col_index:
                    if range_lookup:
                        # Approximate match
                        if row[0] <= lookup_value:
                            return row[col_index]
                    else:
                        # Exact match
                        if row[0] == lookup_value:
                            return row[col_index]
            
            return "#N/A"
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _index(self, array, row_num, column_num=1):
        """INDEX function implementation."""
        try:
            if not isinstance(array, list):
                return "#REF!"
            
            row_idx = int(row_num) - 1  # Convert to 0-based
            col_idx = int(column_num) - 1  # Convert to 0-based
            
            if row_idx < 0 or row_idx >= len(array):
                return "#REF!"
            
            row = array[row_idx]
            if isinstance(row, list):
                if col_idx < 0 or col_idx >= len(row):
                    return "#REF!"
                return row[col_idx]
            else:
                if col_idx != 0:
                    return "#REF!"
                return row
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _match(self, lookup_value, lookup_array, match_type=1):
        """MATCH function implementation."""
        try:
            if not isinstance(lookup_array, list):
                return "#N/A"
            
            match_type = int(match_type)
            
            for i, value in enumerate(lookup_array):
                if match_type == 0:  # Exact match
                    if value == lookup_value:
                        return i + 1  # Convert to 1-based
                elif match_type == 1:  # Less than or equal
                    if value <= lookup_value:
                        continue
                    else:
                        return i  # Previous index (1-based)
                elif match_type == -1:  # Greater than or equal
                    if value >= lookup_value:
                        return i + 1  # Convert to 1-based
            
            return "#N/A"
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _abs(self, number) -> Union[float, str]:
        """ABS function implementation."""
        try:
            return abs(float(number))
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _round(self, number, num_digits) -> Union[float, str]:
        """ROUND function implementation."""
        try:
            return round(float(number), int(num_digits))
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _sqrt(self, number) -> Union[float, str]:
        """SQRT function implementation."""
        try:
            num = float(number)
            if num < 0:
                return "#NUM!"
            return math.sqrt(num)
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _power(self, number, power) -> Union[float, str]:
        """POWER function implementation."""
        try:
            return float(number) ** float(power)
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _isnumber(self, value) -> bool:
        """ISNUMBER function implementation."""
        return isinstance(value, (int, float))
    
    def _istext(self, value) -> bool:
        """ISTEXT function implementation."""
        return isinstance(value, str)
    
    def _isblank(self, value) -> bool:
        """ISBLANK function implementation."""
        return value is None or value == ""


# Global function registry instance
_global_function_registry = None


def get_function_registry() -> FunctionRegistry:
    """Get the global function registry instance."""
    global _global_function_registry
    if _global_function_registry is None:
        _global_function_registry = FunctionRegistry()
    return _global_function_registry


def register_function(name: str, func: Callable, category: FunctionCategory = FunctionCategory.CUSTOM,
                     description: str = "", syntax: str = "", examples: List[str] = None,
                     **kwargs) -> None:
    """Convenience function to register a function."""
    registry = get_function_registry()
    registry.register(name, func, category, description, syntax, examples, **kwargs)

