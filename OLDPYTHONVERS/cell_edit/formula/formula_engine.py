"""
Unified formula engine that combines parsing, dependency tracking, evaluation, and optimization.
Provides high-level interface for formula processing with incremental recalculation.
"""

import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from core.interfaces import IFormulaEngine, ISheet
from core.coordinates import CellCoordinate, CellRange
from core.config import get_config
from core.events import get_event_manager, EventType, CellChangeEvent
from formula.ast_parser import FormulaAST, ASTNode
from formula.dependency_graph import DependencyGraph, DependencyType, CircularDependencyError
from formula.function_registry import get_function_registry, FunctionRegistry
from formula.evaluator import FormulaEvaluator, EvaluationContext
from formula.optimizer import FormulaOptimizer, OptimizationResult


@dataclass
class CalculationResult:
    """Result of formula calculation."""
    coordinate: CellCoordinate
    value: Any
    calculation_time: float
    dependencies: List[Union[CellCoordinate, CellRange]]
    is_error: bool
    error_message: Optional[str] = None


@dataclass
class RecalculationStats:
    """Statistics from a recalculation cycle."""
    cells_calculated: int
    total_time: float
    errors: int
    circular_references: int
    optimizations_applied: int
    cache_hits: int
    parallel_calculations: int


class FormulaEngine(IFormulaEngine):
    """
    High-performance formula engine with:
    - Incremental recalculation
    - Dependency tracking
    - Parallel evaluation
    - Formula optimization
    - Circular dependency detection
    """
    
    def __init__(self, sheet: ISheet, enable_optimization: bool = True, 
                 enable_parallel: bool = True):
        self.sheet = sheet
        self.enable_optimization = enable_optimization
        self.enable_parallel = enable_parallel
        
        # Core components
        self.ast_parser = FormulaAST()
        self.dependency_graph = DependencyGraph()
        self.function_registry = get_function_registry()
        self.evaluator = FormulaEvaluator(
            enable_parallel=enable_parallel,
            max_workers=get_config().performance.max_worker_threads
        )
        self.optimizer = FormulaOptimizer() if enable_optimization else None
        
        # Caching
        self._formula_cache: Dict[str, ASTNode] = {}
        self._result_cache: Dict[CellCoordinate, Any] = {}
        self._optimization_cache: Dict[str, OptimizationResult] = {}
        
        # State management
        self._calculation_mode = "automatic"  # automatic, manual
        self._is_calculating = False
        self._calculation_lock = threading.RLock()
        
        # Performance tracking
        self._calculation_count = 0
        self._total_calculation_time = 0.0
        self._last_recalc_stats: Optional[RecalculationStats] = None
        
        # Thread pool for parallel calculations
        self._executor = ThreadPoolExecutor(
            max_workers=get_config().performance.max_worker_threads
        ) if enable_parallel else None
        
        # Subscribe to events
        event_manager = get_event_manager()
        event_manager.subscribe(EventType.CELL_VALUE_CHANGED, self._on_cell_changed)
        event_manager.subscribe(EventType.CELL_FORMULA_CHANGED, self._on_cell_changed)
    
    def evaluate(self, formula: str, context: Dict[str, Any]) -> Any:
        """Evaluate a formula in the given context."""
        try:
            # Parse formula
            ast = self.parse(formula)
            
            # Optimize if enabled
            if self.optimizer:
                optimization_result = self._get_or_create_optimization(formula, ast)
                ast = optimization_result.optimized_ast
            
            # Create evaluation context
            eval_context = EvaluationContext(
                sheet=self.sheet,
                current_cell=context.get('current_cell')
            )
            
            # Evaluate
            return self.evaluator.evaluate(ast, eval_context)
        
        except Exception as e:
            return f"#ERROR: {e}"
    
    def parse(self, formula: str) -> ASTNode:
        """Parse a formula into an AST."""
        if formula in self._formula_cache:
            return self._formula_cache[formula]
        
        ast = self.ast_parser.parse(formula)
        
        # Cache the result
        if len(self._formula_cache) < get_config().performance.formula_cache_size:
            self._formula_cache[formula] = ast
        
        return ast
    
    def get_dependencies(self, formula: str) -> List[Union[CellCoordinate, CellRange]]:
        """Get the cell dependencies of a formula."""
        ast = self.parse(formula)
        return ast.get_dependencies()
    
    def register_function(self, name: str, func: callable) -> None:
        """Register a custom function."""
        self.function_registry.register(
            name=name,
            func=func,
            category=self.function_registry.FunctionCategory.CUSTOM,
            description="Custom function",
            syntax=f"{name}(...)"
        )
    
    def set_cell_formula(self, coordinate: CellCoordinate, formula: str) -> CalculationResult:
        """Set a cell's formula and update dependencies."""
        start_time = time.time()
        
        try:
            # Parse and validate formula
            ast = self.parse(formula)
            if ast.node_type == ast.node_type.ERROR:
                return CalculationResult(
                    coordinate=coordinate,
                    value=ast.value,
                    calculation_time=time.time() - start_time,
                    dependencies=[],
                    is_error=True,
                    error_message=ast.value
                )
            
            # Get dependencies
            dependencies = self.get_dependencies(formula)
            
            # Update dependency graph
            self._update_dependencies(coordinate, dependencies)
            
            # Calculate value
            context = EvaluationContext(self.sheet, coordinate)
            
            # Optimize if enabled
            if self.optimizer:
                optimization_result = self._get_or_create_optimization(formula, ast)
                ast = optimization_result.optimized_ast
            
            value = self.evaluator.evaluate(ast, context)
            
            # Cache result
            self._result_cache[coordinate] = value
            
            # Trigger recalculation if in automatic mode
            if self._calculation_mode == "automatic":
                self._schedule_recalculation()
            
            return CalculationResult(
                coordinate=coordinate,
                value=value,
                calculation_time=time.time() - start_time,
                dependencies=dependencies,
                is_error=isinstance(value, str) and value.startswith('#')
            )
        
        except CircularDependencyError as e:
            return CalculationResult(
                coordinate=coordinate,
                value="#CIRCULAR!",
                calculation_time=time.time() - start_time,
                dependencies=[],
                is_error=True,
                error_message=str(e)
            )
        
        except Exception as e:
            return CalculationResult(
                coordinate=coordinate,
                value=f"#ERROR: {e}",
                calculation_time=time.time() - start_time,
                dependencies=[],
                is_error=True,
                error_message=str(e)
            )
    
    def calculate_cell(self, coordinate: CellCoordinate) -> CalculationResult:
        """Calculate a single cell."""
        start_time = time.time()
        
        try:
            cell = self.sheet.get_cell(coordinate)
            if not cell or not cell.formula:
                # No formula, return current value
                value = cell.value if cell else None
                return CalculationResult(
                    coordinate=coordinate,
                    value=value,
                    calculation_time=time.time() - start_time,
                    dependencies=[],
                    is_error=False
                )
            
            # Parse and evaluate formula
            ast = self.parse(cell.formula)
            dependencies = ast.get_dependencies()
            
            # Create evaluation context
            context = EvaluationContext(self.sheet, coordinate)
            
            # Optimize if enabled
            if self.optimizer:
                optimization_result = self._get_or_create_optimization(cell.formula, ast)
                ast = optimization_result.optimized_ast
            
            # Evaluate
            value = self.evaluator.evaluate(ast, context)
            
            # Update cell value
            cell.value = value
            
            # Cache result
            self._result_cache[coordinate] = value
            
            # Mark as clean in dependency graph
            self.dependency_graph.mark_clean(coordinate)
            
            return CalculationResult(
                coordinate=coordinate,
                value=value,
                calculation_time=time.time() - start_time,
                dependencies=dependencies,
                is_error=isinstance(value, str) and value.startswith('#')
            )
        
        except Exception as e:
            error_value = f"#ERROR: {e}"
            
            # Update cell with error
            cell = self.sheet.get_cell(coordinate)
            if cell:
                cell.value = error_value
            
            return CalculationResult(
                coordinate=coordinate,
                value=error_value,
                calculation_time=time.time() - start_time,
                dependencies=[],
                is_error=True,
                error_message=str(e)
            )
    
    def recalculate_all(self) -> RecalculationStats:
        """Recalculate all formulas in the sheet."""
        start_time = time.time()
        
        with self._calculation_lock:
            if self._is_calculating:
                # Already calculating, return previous stats
                return self._last_recalc_stats or RecalculationStats(0, 0, 0, 0, 0, 0, 0)
            
            self._is_calculating = True
            
            try:
                # Get calculation order
                calculation_order = self.dependency_graph.get_calculation_order()
                
                # Statistics
                cells_calculated = 0
                errors = 0
                circular_references = 0
                optimizations_applied = 0
                cache_hits = 0
                parallel_calculations = 0
                
                if self.enable_parallel and self._executor:
                    # Parallel calculation
                    results = self._calculate_parallel(calculation_order)
                    parallel_calculations = len(results)
                else:
                    # Sequential calculation
                    results = []
                    for coord in calculation_order:
                        result = self.calculate_cell(coord)
                        results.append(result)
                
                # Process results
                for result in results:
                    cells_calculated += 1
                    if result.is_error:
                        errors += 1
                        if "CIRCULAR" in str(result.value):
                            circular_references += 1
                
                # Count optimizations and cache hits
                optimizations_applied = len(self._optimization_cache)
                cache_hits = len(self._result_cache)
                
                total_time = time.time() - start_time
                
                stats = RecalculationStats(
                    cells_calculated=cells_calculated,
                    total_time=total_time,
                    errors=errors,
                    circular_references=circular_references,
                    optimizations_applied=optimizations_applied,
                    cache_hits=cache_hits,
                    parallel_calculations=parallel_calculations
                )
                
                self._last_recalc_stats = stats
                self._calculation_count += 1
                self._total_calculation_time += total_time
                
                return stats
            
            finally:
                self._is_calculating = False
    
    def recalculate_dirty(self) -> RecalculationStats:
        """Recalculate only dirty (changed) cells."""
        start_time = time.time()
        
        with self._calculation_lock:
            if self._is_calculating:
                return self._last_recalc_stats or RecalculationStats(0, 0, 0, 0, 0, 0, 0)
            
            self._is_calculating = True
            
            try:
                # Get recalculation plan (only dirty cells)
                recalc_plan = self.dependency_graph.get_recalculation_plan()
                
                if not recalc_plan:
                    # Nothing to recalculate
                    return RecalculationStats(0, 0, 0, 0, 0, 0, 0)
                
                # Calculate dirty cells
                results = []
                if self.enable_parallel and self._executor and len(recalc_plan) > 1:
                    results = self._calculate_parallel(recalc_plan)
                else:
                    for coord in recalc_plan:
                        result = self.calculate_cell(coord)
                        results.append(result)
                
                # Process results
                cells_calculated = len(results)
                errors = sum(1 for r in results if r.is_error)
                circular_references = sum(1 for r in results 
                                        if r.is_error and "CIRCULAR" in str(r.value))
                
                total_time = time.time() - start_time
                
                stats = RecalculationStats(
                    cells_calculated=cells_calculated,
                    total_time=total_time,
                    errors=errors,
                    circular_references=circular_references,
                    optimizations_applied=len(self._optimization_cache),
                    cache_hits=len(self._result_cache),
                    parallel_calculations=len(results) if self.enable_parallel else 0
                )
                
                self._last_recalc_stats = stats
                return stats
            
            finally:
                self._is_calculating = False
    
    def _calculate_parallel(self, coordinates: List[CellCoordinate]) -> List[CalculationResult]:
        """Calculate multiple cells in parallel."""
        if not self._executor:
            return [self.calculate_cell(coord) for coord in coordinates]
        
        # Submit calculation tasks
        futures = []
        for coord in coordinates:
            future = self._executor.submit(self.calculate_cell, coord)
            futures.append((coord, future))
        
        # Collect results
        results = []
        for coord, future in futures:
            try:
                result = future.result(timeout=get_config().performance.calculation_timeout)
                results.append(result)
            except Exception as e:
                # Create error result
                error_result = CalculationResult(
                    coordinate=coord,
                    value=f"#ERROR: {e}",
                    calculation_time=0.0,
                    dependencies=[],
                    is_error=True,
                    error_message=str(e)
                )
                results.append(error_result)
        
        return results
    
    def _update_dependencies(self, coordinate: CellCoordinate, 
                           dependencies: List[Union[CellCoordinate, CellRange]]) -> None:
        """Update the dependency graph for a cell."""
        # Remove old dependencies
        old_dependencies = self.dependency_graph.get_dependencies(coordinate)
        for dep in old_dependencies:
            self.dependency_graph.remove_dependency(coordinate, dep)
        
        # Add new dependencies
        for dep in dependencies:
            if isinstance(dep, CellRange):
                self.dependency_graph.add_dependency(coordinate, dep, DependencyType.RANGE)
            else:
                self.dependency_graph.add_dependency(coordinate, dep, DependencyType.DIRECT)
    
    def _get_or_create_optimization(self, formula: str, ast: ASTNode) -> OptimizationResult:
        """Get cached optimization or create new one."""
        if formula in self._optimization_cache:
            return self._optimization_cache[formula]
        
        optimization_result = self.optimizer.optimize(ast)
        
        # Cache the result
        if len(self._optimization_cache) < get_config().performance.formula_cache_size:
            self._optimization_cache[formula] = optimization_result
        
        return optimization_result
    
    def _schedule_recalculation(self) -> None:
        """Schedule a recalculation (for automatic mode)."""
        if self._calculation_mode == "automatic" and not self._is_calculating:
            # In a real implementation, this might use a timer or queue
            # For now, we'll just trigger immediate recalculation
            self.recalculate_dirty()
    
    def _on_cell_changed(self, event: CellChangeEvent) -> None:
        """Handle cell change events."""
        if hasattr(event, 'coordinate'):
            # Mark cell and dependents as dirty
            self.dependency_graph.mark_dirty(event.coordinate, propagate=True)
            
            # Clear cached result
            self._result_cache.pop(event.coordinate, None)
            
            # Schedule recalculation if in automatic mode
            if self._calculation_mode == "automatic":
                self._schedule_recalculation()
    
    def set_calculation_mode(self, mode: str) -> None:
        """Set calculation mode (automatic or manual)."""
        if mode in ["automatic", "manual"]:
            self._calculation_mode = mode
        else:
            raise ValueError("Mode must be 'automatic' or 'manual'")
    
    def get_calculation_mode(self) -> str:
        """Get current calculation mode."""
        return self._calculation_mode
    
    def clear_caches(self) -> None:
        """Clear all caches."""
        self._formula_cache.clear()
        self._result_cache.clear()
        self._optimization_cache.clear()
        self.evaluator.clear_cache()
        self.ast_parser.clear_cache()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive engine statistics."""
        return {
            'calculation_count': self._calculation_count,
            'total_calculation_time': self._total_calculation_time,
            'average_calculation_time': (
                self._total_calculation_time / max(1, self._calculation_count)
            ),
            'calculation_mode': self._calculation_mode,
            'is_calculating': self._is_calculating,
            'cache_sizes': {
                'formula_cache': len(self._formula_cache),
                'result_cache': len(self._result_cache),
                'optimization_cache': len(self._optimization_cache)
            },
            'last_recalc_stats': self._last_recalc_stats.__dict__ if self._last_recalc_stats else None,
            'dependency_graph_stats': self.dependency_graph.get_statistics(),
            'evaluator_stats': self.evaluator.get_statistics(),
            'optimizer_stats': self.optimizer.get_statistics() if self.optimizer else None,
            'function_count': len(self.function_registry.get_all_functions())
        }
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self._executor:
            self._executor.shutdown(wait=True)
        self.evaluator.cleanup()
        self.clear_caches()

