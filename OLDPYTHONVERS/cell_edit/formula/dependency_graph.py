"""
Dependency graph for tracking formula dependencies and enabling incremental recalculation.
Detects circular dependencies and optimizes calculation order.
"""

import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
import weakref

from core.coordinates import CellCoordinate, CellRange
from core.events import get_event_manager, EventType, CellChangeEvent


class DependencyType(Enum):
    """Types of dependencies."""
    DIRECT = "direct"           # A1 depends on B1
    RANGE = "range"             # A1 depends on B1:B10
    VOLATILE = "volatile"       # Depends on NOW(), RAND(), etc.
    EXTERNAL = "external"       # Depends on external data source


@dataclass
class DependencyEdge:
    """Edge in the dependency graph."""
    source: CellCoordinate
    target: Union[CellCoordinate, CellRange]
    dependency_type: DependencyType
    weight: float = 1.0  # For optimization
    metadata: Dict[str, Any] = field(default_factory=dict)


class DependencyNode:
    """Node in the dependency graph representing a cell."""
    
    def __init__(self, coordinate: CellCoordinate):
        self.coordinate = coordinate
        self.dependencies: Set[Union[CellCoordinate, CellRange]] = set()  # What this cell depends on
        self.dependents: Set[CellCoordinate] = set()  # What depends on this cell
        self.calculation_order: int = 0  # Topological order for calculation
        self.last_calculated: float = 0.0
        self.is_dirty: bool = False
        self.is_calculating: bool = False
        self.is_volatile: bool = False
        self.calculation_time: float = 0.0
        self._lock = threading.RLock()
    
    def add_dependency(self, target: Union[CellCoordinate, CellRange], 
                      dependency_type: DependencyType = DependencyType.DIRECT) -> None:
        """Add a dependency to another cell or range."""
        with self._lock:
            self.dependencies.add(target)
            if dependency_type == DependencyType.VOLATILE:
                self.is_volatile = True
    
    def remove_dependency(self, target: Union[CellCoordinate, CellRange]) -> None:
        """Remove a dependency."""
        with self._lock:
            self.dependencies.discard(target)
    
    def add_dependent(self, source: CellCoordinate) -> None:
        """Add a cell that depends on this cell."""
        with self._lock:
            self.dependents.add(source)
    
    def remove_dependent(self, source: CellCoordinate) -> None:
        """Remove a dependent cell."""
        with self._lock:
            self.dependents.discard(source)
    
    def mark_dirty(self) -> None:
        """Mark this cell as needing recalculation."""
        with self._lock:
            self.is_dirty = True
    
    def mark_clean(self) -> None:
        """Mark this cell as up to date."""
        with self._lock:
            self.is_dirty = False
            self.last_calculated = time.time()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get node statistics."""
        with self._lock:
            return {
                'coordinate': str(self.coordinate),
                'dependencies_count': len(self.dependencies),
                'dependents_count': len(self.dependents),
                'calculation_order': self.calculation_order,
                'is_dirty': self.is_dirty,
                'is_volatile': self.is_volatile,
                'last_calculated': self.last_calculated,
                'calculation_time': self.calculation_time
            }


class CircularDependencyError(Exception):
    """Raised when a circular dependency is detected."""
    
    def __init__(self, cycle: List[CellCoordinate]):
        self.cycle = cycle
        cycle_str = " -> ".join(str(coord) for coord in cycle)
        super().__init__(f"Circular dependency detected: {cycle_str}")


class DependencyGraph:
    """
    Dependency graph for tracking formula dependencies.
    Supports incremental recalculation and circular dependency detection.
    """
    
    def __init__(self):
        self._nodes: Dict[CellCoordinate, DependencyNode] = {}
        self._edges: List[DependencyEdge] = []
        self._calculation_order: List[CellCoordinate] = []
        self._dirty_cells: Set[CellCoordinate] = set()
        self._volatile_cells: Set[CellCoordinate] = set()
        
        # Thread safety
        self._lock = threading.RWLock() if hasattr(threading, 'RWLock') else threading.RLock()
        
        # Performance tracking
        self._recalculation_count = 0
        self._total_calculation_time = 0.0
        self._last_full_recalc = 0.0
        
        # Subscribe to cell change events
        event_manager = get_event_manager()
        event_manager.subscribe(EventType.CELL_VALUE_CHANGED, self._on_cell_changed)
        event_manager.subscribe(EventType.CELL_FORMULA_CHANGED, self._on_cell_changed)
    
    def add_cell(self, coordinate: CellCoordinate) -> DependencyNode:
        """Add a cell to the dependency graph."""
        with self._lock:
            if coordinate not in self._nodes:
                self._nodes[coordinate] = DependencyNode(coordinate)
            return self._nodes[coordinate]
    
    def remove_cell(self, coordinate: CellCoordinate) -> bool:
        """Remove a cell from the dependency graph."""
        with self._lock:
            if coordinate not in self._nodes:
                return False
            
            node = self._nodes[coordinate]
            
            # Remove all dependencies
            for dependency in list(node.dependencies):
                self.remove_dependency(coordinate, dependency)
            
            # Remove all dependents
            for dependent in list(node.dependents):
                self.remove_dependency(dependent, coordinate)
            
            # Remove from dirty and volatile sets
            self._dirty_cells.discard(coordinate)
            self._volatile_cells.discard(coordinate)
            
            # Remove from calculation order
            if coordinate in self._calculation_order:
                self._calculation_order.remove(coordinate)
            
            del self._nodes[coordinate]
            return True
    
    def add_dependency(self, source: CellCoordinate, 
                      target: Union[CellCoordinate, CellRange],
                      dependency_type: DependencyType = DependencyType.DIRECT) -> None:
        """Add a dependency relationship."""
        with self._lock:
            # Ensure source node exists
            source_node = self.add_cell(source)
            
            # Handle range dependencies
            if isinstance(target, CellRange):
                source_node.add_dependency(target, dependency_type)
                
                # Add dependency to each cell in the range
                for coord in target:
                    target_node = self.add_cell(coord)
                    target_node.add_dependent(source)
            else:
                # Single cell dependency
                target_node = self.add_cell(target)
                source_node.add_dependency(target, dependency_type)
                target_node.add_dependent(source)
            
            # Add edge
            edge = DependencyEdge(source, target, dependency_type)
            self._edges.append(edge)
            
            # Mark as volatile if needed
            if dependency_type == DependencyType.VOLATILE:
                self._volatile_cells.add(source)
            
            # Check for circular dependencies
            if isinstance(target, CellCoordinate):
                cycle = self._detect_cycle(source)
                if cycle:
                    # Remove the dependency we just added
                    self.remove_dependency(source, target)
                    raise CircularDependencyError(cycle)
            
            # Invalidate calculation order
            self._calculation_order.clear()
            
            # Mark source as dirty
            self.mark_dirty(source)
    
    def remove_dependency(self, source: CellCoordinate, 
                         target: Union[CellCoordinate, CellRange]) -> bool:
        """Remove a dependency relationship."""
        with self._lock:
            if source not in self._nodes:
                return False
            
            source_node = self._nodes[source]
            
            # Remove from source node
            source_node.remove_dependency(target)
            
            # Handle range dependencies
            if isinstance(target, CellRange):
                for coord in target:
                    if coord in self._nodes:
                        self._nodes[coord].remove_dependent(source)
            else:
                if target in self._nodes:
                    self._nodes[target].remove_dependent(source)
            
            # Remove edge
            self._edges = [edge for edge in self._edges 
                          if not (edge.source == source and edge.target == target)]
            
            # Invalidate calculation order
            self._calculation_order.clear()
            
            return True
    
    def get_dependencies(self, coordinate: CellCoordinate) -> Set[Union[CellCoordinate, CellRange]]:
        """Get all dependencies of a cell."""
        with self._lock:
            if coordinate in self._nodes:
                return self._nodes[coordinate].dependencies.copy()
            return set()
    
    def get_dependents(self, coordinate: CellCoordinate) -> Set[CellCoordinate]:
        """Get all cells that depend on the given cell."""
        with self._lock:
            if coordinate in self._nodes:
                return self._nodes[coordinate].dependents.copy()
            return set()
    
    def mark_dirty(self, coordinate: CellCoordinate, propagate: bool = True) -> None:
        """Mark a cell and optionally its dependents as dirty."""
        with self._lock:
            if coordinate not in self._nodes:
                return
            
            node = self._nodes[coordinate]
            node.mark_dirty()
            self._dirty_cells.add(coordinate)
            
            if propagate:
                # Recursively mark dependents as dirty
                for dependent in node.dependents:
                    self.mark_dirty(dependent, propagate=True)
    
    def mark_clean(self, coordinate: CellCoordinate) -> None:
        """Mark a cell as clean (up to date)."""
        with self._lock:
            if coordinate in self._nodes:
                self._nodes[coordinate].mark_clean()
                self._dirty_cells.discard(coordinate)
    
    def get_dirty_cells(self) -> Set[CellCoordinate]:
        """Get all cells that need recalculation."""
        with self._lock:
            return self._dirty_cells.copy()
    
    def get_calculation_order(self) -> List[CellCoordinate]:
        """Get the optimal order for calculating cells."""
        with self._lock:
            if not self._calculation_order:
                self._calculation_order = self._topological_sort()
            return self._calculation_order.copy()
    
    def get_recalculation_plan(self) -> List[CellCoordinate]:
        """Get the order for recalculating only dirty cells."""
        with self._lock:
            if not self._dirty_cells:
                return []
            
            # Get full calculation order
            full_order = self.get_calculation_order()
            
            # Filter to only dirty cells, maintaining order
            dirty_order = [coord for coord in full_order if coord in self._dirty_cells]
            
            # Add volatile cells (they always need recalculation)
            for coord in self._volatile_cells:
                if coord not in dirty_order:
                    dirty_order.append(coord)
            
            return dirty_order
    
    def _detect_cycle(self, start: CellCoordinate) -> Optional[List[CellCoordinate]]:
        """Detect circular dependencies using DFS."""
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(coord: CellCoordinate) -> Optional[List[CellCoordinate]]:
            if coord in rec_stack:
                # Found cycle, return path from cycle start
                cycle_start = path.index(coord)
                return path[cycle_start:] + [coord]
            
            if coord in visited:
                return None
            
            visited.add(coord)
            rec_stack.add(coord)
            path.append(coord)
            
            if coord in self._nodes:
                for dependency in self._nodes[coord].dependencies:
                    if isinstance(dependency, CellCoordinate):
                        cycle = dfs(dependency)
                        if cycle:
                            return cycle
            
            rec_stack.remove(coord)
            path.pop()
            return None
        
        return dfs(start)
    
    def _topological_sort(self) -> List[CellCoordinate]:
        """Perform topological sort to determine calculation order."""
        # Kahn's algorithm
        in_degree = defaultdict(int)
        
        # Calculate in-degrees
        for coord in self._nodes:
            in_degree[coord] = 0
        
        for edge in self._edges:
            if isinstance(edge.target, CellCoordinate):
                in_degree[edge.target] += 1
            else:  # Range dependency
                for coord in edge.target:
                    if coord in self._nodes:
                        in_degree[coord] += 1
        
        # Initialize queue with nodes having no dependencies
        queue = deque([coord for coord, degree in in_degree.items() if degree == 0])
        result = []
        order = 0
        
        while queue:
            coord = queue.popleft()
            result.append(coord)
            
            # Update calculation order in node
            if coord in self._nodes:
                self._nodes[coord].calculation_order = order
                order += 1
            
            # Reduce in-degree of dependents
            if coord in self._nodes:
                for dependent in self._nodes[coord].dependents:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        
        # Check for cycles
        if len(result) != len(self._nodes):
            # There are cycles, but we'll return partial order
            # Cycles should be detected earlier in add_dependency
            pass
        
        return result
    
    def _on_cell_changed(self, event: CellChangeEvent) -> None:
        """Handle cell change events."""
        if hasattr(event, 'coordinate'):
            self.mark_dirty(event.coordinate, propagate=True)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get dependency graph statistics."""
        with self._lock:
            return {
                'total_cells': len(self._nodes),
                'total_edges': len(self._edges),
                'dirty_cells': len(self._dirty_cells),
                'volatile_cells': len(self._volatile_cells),
                'recalculation_count': self._recalculation_count,
                'total_calculation_time': self._total_calculation_time,
                'average_calculation_time': (
                    self._total_calculation_time / max(1, self._recalculation_count)
                ),
                'last_full_recalc': self._last_full_recalc,
                'has_calculation_order': bool(self._calculation_order)
            }
    
    def get_node_statistics(self) -> List[Dict[str, Any]]:
        """Get statistics for all nodes."""
        with self._lock:
            return [node.get_stats() for node in self._nodes.values()]
    
    def clear(self) -> None:
        """Clear the entire dependency graph."""
        with self._lock:
            self._nodes.clear()
            self._edges.clear()
            self._calculation_order.clear()
            self._dirty_cells.clear()
            self._volatile_cells.clear()
            self._recalculation_count = 0
            self._total_calculation_time = 0.0
    
    def export_graph(self) -> Dict[str, Any]:
        """Export the graph structure for visualization or debugging."""
        with self._lock:
            nodes = []
            edges = []
            
            for coord, node in self._nodes.items():
                nodes.append({
                    'id': str(coord),
                    'coordinate': coord.to_a1(),
                    'is_dirty': node.is_dirty,
                    'is_volatile': node.is_volatile,
                    'calculation_order': node.calculation_order,
                    'dependencies_count': len(node.dependencies),
                    'dependents_count': len(node.dependents)
                })
            
            for edge in self._edges:
                edges.append({
                    'source': str(edge.source),
                    'target': str(edge.target),
                    'type': edge.dependency_type.value,
                    'weight': edge.weight
                })
            
            return {
                'nodes': nodes,
                'edges': edges,
                'statistics': self.get_statistics()
            }

