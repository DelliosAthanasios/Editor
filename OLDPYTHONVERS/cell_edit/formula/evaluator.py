"""
Formula evaluator for executing parsed formulas with context resolution.
Handles cell references, ranges, and function calls with proper error handling.
"""

import threading
import time
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import operator

from core.coordinates import CellCoordinate, CellRange
from core.interfaces import ISheet
from formula.ast_parser import ASTNode, ASTNodeType
from formula.function_registry import get_function_registry
from formula.dependency_graph import DependencyType


class EvaluationContext:
    """Context for formula evaluation."""
    
    def __init__(self, sheet: ISheet, current_cell: Optional[CellCoordinate] = None):
        self.sheet = sheet
        self.current_cell = current_cell
        self.call_stack: List[CellCoordinate] = []
        self.volatile_functions = set()
        self.external_references = {}
        self.array_context = False
        self.calculation_mode = "automatic"  # automatic, manual
        
    def push_cell(self, coord: CellCoordinate) -> None:
        """Push a cell onto the call stack."""
        if coord in self.call_stack:
            cycle = self.call_stack[self.call_stack.index(coord):] + [coord]
            cycle_str = " -> ".join(str(c) for c in cycle)
            raise ValueError(f"Circular reference: {cycle_str}")
        self.call_stack.append(coord)
    
    def pop_cell(self) -> Optional[CellCoordinate]:
        """Pop a cell from the call stack."""
        return self.call_stack.pop() if self.call_stack else None
    
    def is_in_call_stack(self, coord: CellCoordinate) -> bool:
        """Check if a cell is in the call stack."""
        return coord in self.call_stack


class FormulaEvaluator:
    """
    High-performance formula evaluator with support for:
    - Cell and range references
    - Function calls
    - Parallel evaluation
    - Error handling
    - Array formulas
    """
    
    # Binary operators
    BINARY_OPERATORS = {
        '+': operator.add,
        '-': operator.sub,
        '*': operator.mul,
        '/': operator.truediv,
        '^': operator.pow,
        '%': operator.mod,
    }
    
    # Comparison operators
    COMPARISON_OPERATORS = {
        '=': operator.eq,
        '<>': operator.ne,
        '<': operator.lt,
        '>': operator.gt,
        '<=': operator.le,
        '>=': operator.ge,
    }
    
    # Unary operators
    UNARY_OPERATORS = {
        '+': operator.pos,
        '-': operator.neg,
    }
    
    def __init__(self, enable_parallel: bool = True, max_workers: int = 4):
        self.function_registry = get_function_registry()
        self.enable_parallel = enable_parallel
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers) if enable_parallel else None
        self._lock = threading.RLock()
        
        # Performance tracking
        self._evaluation_count = 0
        self._total_evaluation_time = 0.0
        self._error_count = 0
        
        # Caching
        self._result_cache: Dict[str, Any] = {}
        self._cache_enabled = True
        self._cache_max_size = 10000
    
    def evaluate(self, ast: ASTNode, context: EvaluationContext) -> Any:
        """Evaluate an AST node in the given context."""
        start_time = time.time()
        
        try:
            self._evaluation_count += 1
            
            # Check cache first
            if self._cache_enabled and context.current_cell:
                cache_key = f"{context.current_cell}:{hash(str(ast))}"
                if cache_key in self._result_cache:
                    return self._result_cache[cache_key]
            
            result = self._evaluate_node(ast, context)
            
            # Cache result
            if self._cache_enabled and context.current_cell:
                cache_key = f"{context.current_cell}:{hash(str(ast))}"
                if len(self._result_cache) < self._cache_max_size:
                    self._result_cache[cache_key] = result
            
            return result
        
        except Exception as e:
            self._error_count += 1
            return f"#ERROR: {e}"
        
        finally:
            elapsed = time.time() - start_time
            self._total_evaluation_time += elapsed
    
    def _evaluate_node(self, node: ASTNode, context: EvaluationContext) -> Any:
        """Evaluate a single AST node."""
        if node.node_type == ASTNodeType.LITERAL:
            return node.value
        
        elif node.node_type == ASTNodeType.CELL_REFERENCE:
            return self._evaluate_cell_reference(node.value, context)
        
        elif node.node_type == ASTNodeType.RANGE_REFERENCE:
            return self._evaluate_range_reference(node.value, context)
        
        elif node.node_type == ASTNodeType.FUNCTION_CALL:
            return self._evaluate_function_call(node, context)
        
        elif node.node_type == ASTNodeType.BINARY_OP:
            return self._evaluate_binary_op(node, context)
        
        elif node.node_type == ASTNodeType.UNARY_OP:
            return self._evaluate_unary_op(node, context)
        
        elif node.node_type == ASTNodeType.COMPARISON:
            return self._evaluate_comparison(node, context)
        
        elif node.node_type == ASTNodeType.LOGICAL:
            return self._evaluate_logical(node, context)
        
        elif node.node_type == ASTNodeType.ARRAY:
            return self._evaluate_array(node, context)
        
        elif node.node_type == ASTNodeType.ERROR:
            return node.value
        
        else:
            return f"#ERROR: Unknown node type: {node.node_type}"
    
    def _evaluate_cell_reference(self, cell_ref: str, context: EvaluationContext) -> Any:
        """Evaluate a cell reference."""
        try:
            coord = CellCoordinate.from_a1(cell_ref)
            
            # Check for circular reference
            if context.is_in_call_stack(coord):
                return "#CIRCULAR!"
            
            # Get cell from sheet
            cell = context.sheet.get_cell(coord)
            if cell is None or cell.is_empty():
                return 0  # Empty cells evaluate to 0 in calculations
            
            # If cell has a formula, evaluate it recursively
            if cell.formula:
                context.push_cell(coord)
                try:
                    # This would require the formula engine to parse and evaluate
                    # For now, return the computed value
                    return cell.value
                finally:
                    context.pop_cell()
            else:
                return cell.value
        
        except Exception as e:
            return f"#REF: {e}"
    
    def _evaluate_range_reference(self, range_ref: str, context: EvaluationContext) -> List[List[Any]]:
        """Evaluate a range reference."""
        try:
            cell_range = CellRange.from_a1(range_ref)
            result = []
            
            # Build 2D array from range
            for row in range(cell_range.start.row, cell_range.end.row + 1):
                row_data = []
                for col in range(cell_range.start.col, cell_range.end.col + 1):
                    coord = CellCoordinate(row, col)
                    cell = context.sheet.get_cell(coord)
                    
                    if cell is None or cell.is_empty():
                        row_data.append(0)
                    elif cell.formula:
                        # Evaluate formula recursively
                        context.push_cell(coord)
                        try:
                            row_data.append(cell.value)
                        finally:
                            context.pop_cell()
                    else:
                        row_data.append(cell.value)
                
                result.append(row_data)
            
            return result
        
        except Exception as e:
            return f"#REF: {e}"
    
    def _evaluate_function_call(self, node: ASTNode, context: EvaluationContext) -> Any:
        """Evaluate a function call."""
        func_name = node.value
        
        # Evaluate arguments
        args = []
        for arg_node in node.children:
            arg_value = self._evaluate_node(arg_node, context)
            
            # Flatten ranges for function arguments
            if isinstance(arg_value, list):
                if all(isinstance(row, list) for row in arg_value):
                    # 2D array (range) - flatten to 1D
                    flattened = []
                    for row in arg_value:
                        flattened.extend(row)
                    args.append(flattened)
                else:
                    # 1D array
                    args.append(arg_value)
            else:
                args.append(arg_value)
        
        # Call function
        try:
            result = self.function_registry.call_function(func_name, args)
            
            # Mark as volatile if needed
            func_info = self.function_registry.get_function(func_name)
            if func_info and func_info.is_volatile:
                context.volatile_functions.add(func_name)
            
            return result
        
        except Exception as e:
            return f"#NAME: {e}"
    
    def _evaluate_binary_op(self, node: ASTNode, context: EvaluationContext) -> Any:
        """Evaluate a binary operation."""
        if len(node.children) != 2:
            return "#ERROR: Binary operation requires 2 operands"
        
        left = self._evaluate_node(node.children[0], context)
        right = self._evaluate_node(node.children[1], context)
        
        # Handle errors in operands
        if isinstance(left, str) and left.startswith('#'):
            return left
        if isinstance(right, str) and right.startswith('#'):
            return right
        
        op = node.value
        if op not in self.BINARY_OPERATORS:
            return f"#ERROR: Unknown operator: {op}"
        
        try:
            # Handle string concatenation with &
            if op == '&':
                return str(left) + str(right)
            
            # Convert to numbers for arithmetic
            if not isinstance(left, (int, float)):
                if isinstance(left, str) and left.replace('.', '').replace('-', '').isdigit():
                    left = float(left)
                else:
                    return "#VALUE!"
            
            if not isinstance(right, (int, float)):
                if isinstance(right, str) and right.replace('.', '').replace('-', '').isdigit():
                    right = float(right)
                else:
                    return "#VALUE!"
            
            # Handle division by zero
            if op == '/' and right == 0:
                return "#DIV/0!"
            
            result = self.BINARY_OPERATORS[op](left, right)
            
            # Convert integer results when appropriate
            if isinstance(result, float) and result.is_integer():
                return int(result)
            
            return result
        
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _evaluate_unary_op(self, node: ASTNode, context: EvaluationContext) -> Any:
        """Evaluate a unary operation."""
        if len(node.children) != 1:
            return "#ERROR: Unary operation requires 1 operand"
        
        operand = self._evaluate_node(node.children[0], context)
        
        # Handle errors in operand
        if isinstance(operand, str) and operand.startswith('#'):
            return operand
        
        op = node.value
        if op not in self.UNARY_OPERATORS:
            return f"#ERROR: Unknown unary operator: {op}"
        
        try:
            # Convert to number
            if not isinstance(operand, (int, float)):
                if isinstance(operand, str) and operand.replace('.', '').replace('-', '').isdigit():
                    operand = float(operand)
                else:
                    return "#VALUE!"
            
            result = self.UNARY_OPERATORS[op](operand)
            
            # Convert integer results when appropriate
            if isinstance(result, float) and result.is_integer():
                return int(result)
            
            return result
        
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _evaluate_comparison(self, node: ASTNode, context: EvaluationContext) -> Any:
        """Evaluate a comparison operation."""
        if len(node.children) != 2:
            return "#ERROR: Comparison requires 2 operands"
        
        left = self._evaluate_node(node.children[0], context)
        right = self._evaluate_node(node.children[1], context)
        
        # Handle errors in operands
        if isinstance(left, str) and left.startswith('#'):
            return left
        if isinstance(right, str) and right.startswith('#'):
            return right
        
        op = node.value
        if op not in self.COMPARISON_OPERATORS:
            return f"#ERROR: Unknown comparison operator: {op}"
        
        try:
            # Type coercion for comparison
            if type(left) != type(right):
                # Try to convert to numbers
                try:
                    if isinstance(left, str):
                        left = float(left)
                    if isinstance(right, str):
                        right = float(right)
                except ValueError:
                    # Keep as strings for string comparison
                    left = str(left)
                    right = str(right)
            
            return self.COMPARISON_OPERATORS[op](left, right)
        
        except Exception as e:
            return f"#ERROR: {e}"
    
    def _evaluate_logical(self, node: ASTNode, context: EvaluationContext) -> Any:
        """Evaluate a logical operation."""
        op = node.value.upper()
        
        if op == "NOT":
            if len(node.children) != 1:
                return "#ERROR: NOT requires 1 operand"
            
            operand = self._evaluate_node(node.children[0], context)
            if isinstance(operand, str) and operand.startswith('#'):
                return operand
            
            return not bool(operand)
        
        elif op in ["AND", "OR"]:
            if len(node.children) < 1:
                return f"#ERROR: {op} requires at least 1 operand"
            
            results = []
            for child in node.children:
                result = self._evaluate_node(child, context)
                if isinstance(result, str) and result.startswith('#'):
                    return result
                results.append(bool(result))
            
            if op == "AND":
                return all(results)
            else:  # OR
                return any(results)
        
        else:
            return f"#ERROR: Unknown logical operator: {op}"
    
    def _evaluate_array(self, node: ASTNode, context: EvaluationContext) -> List[Any]:
        """Evaluate an array literal."""
        result = []
        for child in node.children:
            value = self._evaluate_node(child, context)
            result.append(value)
        return result
    
    def evaluate_parallel(self, formulas: List[Tuple[ASTNode, EvaluationContext]]) -> List[Any]:
        """Evaluate multiple formulas in parallel."""
        if not self.enable_parallel or not self._executor:
            # Fall back to sequential evaluation
            return [self.evaluate(ast, context) for ast, context in formulas]
        
        # Submit tasks to thread pool
        futures = []
        for ast, context in formulas:
            future = self._executor.submit(self.evaluate, ast, context)
            futures.append(future)
        
        # Collect results
        results = []
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append(f"#ERROR: {e}")
        
        return results
    
    def clear_cache(self) -> None:
        """Clear the result cache."""
        with self._lock:
            self._result_cache.clear()
    
    def set_cache_enabled(self, enabled: bool) -> None:
        """Enable or disable result caching."""
        self._cache_enabled = enabled
        if not enabled:
            self.clear_cache()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get evaluator statistics."""
        with self._lock:
            return {
                'evaluation_count': self._evaluation_count,
                'total_evaluation_time': self._total_evaluation_time,
                'average_evaluation_time': (
                    self._total_evaluation_time / max(1, self._evaluation_count)
                ),
                'error_count': self._error_count,
                'error_rate': self._error_count / max(1, self._evaluation_count),
                'cache_size': len(self._result_cache),
                'cache_enabled': self._cache_enabled,
                'parallel_enabled': self.enable_parallel,
                'max_workers': self.max_workers
            }
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self._executor:
            self._executor.shutdown(wait=True)
        self.clear_cache()

