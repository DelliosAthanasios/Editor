"""
Formula optimizer for improving evaluation performance.
Implements various optimization techniques including constant folding,
dead code elimination, and expression simplification.
"""

import copy
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from formula.function_registry import get_function_registry
from formula.ast_parser import ASTNode, ASTNodeType


class OptimizationType(Enum):
    """Types of optimizations."""
    CONSTANT_FOLDING = "constant_folding"
    DEAD_CODE_ELIMINATION = "dead_code_elimination"
    EXPRESSION_SIMPLIFICATION = "expression_simplification"
    FUNCTION_INLINING = "function_inlining"
    COMMON_SUBEXPRESSION = "common_subexpression"
    ALGEBRAIC_SIMPLIFICATION = "algebraic_simplification"


@dataclass
class OptimizationResult:
    """Result of optimization process."""
    original_ast: ASTNode
    optimized_ast: ASTNode
    optimizations_applied: List[OptimizationType]
    performance_improvement: float  # Estimated improvement ratio
    size_reduction: int  # Reduction in AST node count


class FormulaOptimizer:
    """
    Formula optimizer that applies various optimization techniques
    to improve evaluation performance and reduce memory usage.
    """
    
    def __init__(self, enable_all: bool = True):
        self.function_registry = get_function_registry()
        
        # Optimization settings
        self.optimizations_enabled = {
            OptimizationType.CONSTANT_FOLDING: enable_all,
            OptimizationType.DEAD_CODE_ELIMINATION: enable_all,
            OptimizationType.EXPRESSION_SIMPLIFICATION: enable_all,
            OptimizationType.FUNCTION_INLINING: False,  # Can be risky
            OptimizationType.COMMON_SUBEXPRESSION: enable_all,
            OptimizationType.ALGEBRAIC_SIMPLIFICATION: enable_all,
        }
        
        # Statistics
        self._optimization_count = 0
        self._total_nodes_before = 0
        self._total_nodes_after = 0
        
        # Cache for common subexpressions
        self._subexpression_cache: Dict[str, ASTNode] = {}
    
    def optimize(self, ast: ASTNode) -> OptimizationResult:
        """Optimize an AST and return the result."""
        original_ast = copy.deepcopy(ast)
        optimized_ast = copy.deepcopy(ast)
        applied_optimizations = []
        
        original_size = self._count_nodes(original_ast)
        
        # Apply optimizations in order
        if self.optimizations_enabled[OptimizationType.CONSTANT_FOLDING]:
            optimized_ast = self._constant_folding(optimized_ast)
            applied_optimizations.append(OptimizationType.CONSTANT_FOLDING)
        
        if self.optimizations_enabled[OptimizationType.ALGEBRAIC_SIMPLIFICATION]:
            optimized_ast = self._algebraic_simplification(optimized_ast)
            applied_optimizations.append(OptimizationType.ALGEBRAIC_SIMPLIFICATION)
        
        if self.optimizations_enabled[OptimizationType.EXPRESSION_SIMPLIFICATION]:
            optimized_ast = self._expression_simplification(optimized_ast)
            applied_optimizations.append(OptimizationType.EXPRESSION_SIMPLIFICATION)
        
        if self.optimizations_enabled[OptimizationType.DEAD_CODE_ELIMINATION]:
            optimized_ast = self._dead_code_elimination(optimized_ast)
            applied_optimizations.append(OptimizationType.DEAD_CODE_ELIMINATION)
        
        if self.optimizations_enabled[OptimizationType.COMMON_SUBEXPRESSION]:
            optimized_ast = self._common_subexpression_elimination(optimized_ast)
            applied_optimizations.append(OptimizationType.COMMON_SUBEXPRESSION)
        
        optimized_size = self._count_nodes(optimized_ast)
        size_reduction = original_size - optimized_size
        
        # Estimate performance improvement
        performance_improvement = self._estimate_performance_improvement(
            original_ast, optimized_ast, applied_optimizations
        )
        
        # Update statistics
        self._optimization_count += 1
        self._total_nodes_before += original_size
        self._total_nodes_after += optimized_size
        
        return OptimizationResult(
            original_ast=original_ast,
            optimized_ast=optimized_ast,
            optimizations_applied=applied_optimizations,
            performance_improvement=performance_improvement,
            size_reduction=size_reduction
        )
    
    def _constant_folding(self, ast: ASTNode) -> ASTNode:
        """Fold constant expressions into single values."""
        # Recursively optimize children first
        for i, child in enumerate(ast.children):
            ast.children[i] = self._constant_folding(child)
        
        # Check if this node can be folded
        if self._can_fold_constants(ast):
            try:
                result = self._evaluate_constant_expression(ast)
                return ASTNode(ASTNodeType.LITERAL, result)
            except Exception:
                # If evaluation fails, return original
                pass
        
        return ast
    
    def _can_fold_constants(self, ast: ASTNode) -> bool:
        """Check if a node contains only constants and can be folded."""
        if ast.node_type == ASTNodeType.LITERAL:
            return True
        
        if ast.node_type in [ASTNodeType.CELL_REFERENCE, ASTNodeType.RANGE_REFERENCE]:
            return False
        
        if ast.node_type == ASTNodeType.FUNCTION_CALL:
            # Only fold if function is not volatile and all args are constants
            func_info = self.function_registry.get_function(ast.value)
            if func_info and func_info.is_volatile:
                return False
            
            return all(self._can_fold_constants(child) for child in ast.children)
        
        if ast.node_type in [ASTNodeType.BINARY_OP, ASTNodeType.UNARY_OP, 
                            ASTNodeType.COMPARISON, ASTNodeType.LOGICAL]:
            return all(self._can_fold_constants(child) for child in ast.children)
        
        if ast.node_type == ASTNodeType.ARRAY:
            return all(self._can_fold_constants(child) for child in ast.children)
        
        return False
    
    def _evaluate_constant_expression(self, ast: ASTNode) -> Any:
        """Evaluate a constant expression."""
        if ast.node_type == ASTNodeType.LITERAL:
            return ast.value
        
        if ast.node_type == ASTNodeType.BINARY_OP:
            left = self._evaluate_constant_expression(ast.children[0])
            right = self._evaluate_constant_expression(ast.children[1])
            
            op = ast.value
            if op == '+':
                return left + right
            elif op == '-':
                return left - right
            elif op == '*':
                return left * right
            elif op == '/':
                if right == 0:
                    raise ValueError("Division by zero")
                return left / right
            elif op == '^':
                return left ** right
            elif op == '%':
                return left % right
        
        elif ast.node_type == ASTNodeType.UNARY_OP:
            operand = self._evaluate_constant_expression(ast.children[0])
            op = ast.value
            if op == '+':
                return +operand
            elif op == '-':
                return -operand
        
        elif ast.node_type == ASTNodeType.COMPARISON:
            left = self._evaluate_constant_expression(ast.children[0])
            right = self._evaluate_constant_expression(ast.children[1])
            
            op = ast.value
            if op == '=':
                return left == right
            elif op == '<>':
                return left != right
            elif op == '<':
                return left < right
            elif op == '>':
                return left > right
            elif op == '<=':
                return left <= right
            elif op == '>=':
                return left >= right
        
        elif ast.node_type == ASTNodeType.LOGICAL:
            op = ast.value.upper()
            if op == 'NOT':
                operand = self._evaluate_constant_expression(ast.children[0])
                return not bool(operand)
            elif op == 'AND':
                return all(bool(self._evaluate_constant_expression(child)) 
                          for child in ast.children)
            elif op == 'OR':
                return any(bool(self._evaluate_constant_expression(child)) 
                          for child in ast.children)
        
        elif ast.node_type == ASTNodeType.FUNCTION_CALL:
            args = [self._evaluate_constant_expression(child) for child in ast.children]
            return self.function_registry.call_function(ast.value, args)
        
        elif ast.node_type == ASTNodeType.ARRAY:
            return [self._evaluate_constant_expression(child) for child in ast.children]
        
        raise ValueError(f"Cannot evaluate node type: {ast.node_type}")
    
    def _algebraic_simplification(self, ast: ASTNode) -> ASTNode:
        """Apply algebraic simplifications."""
        # Recursively optimize children first
        for i, child in enumerate(ast.children):
            ast.children[i] = self._algebraic_simplification(child)
        
        if ast.node_type == ASTNodeType.BINARY_OP:
            return self._simplify_binary_operation(ast)
        elif ast.node_type == ASTNodeType.UNARY_OP:
            return self._simplify_unary_operation(ast)
        
        return ast
    
    def _simplify_binary_operation(self, ast: ASTNode) -> ASTNode:
        """Simplify binary operations."""
        if len(ast.children) != 2:
            return ast
        
        left = ast.children[0]
        right = ast.children[1]
        op = ast.value
        
        # Identity operations
        if op == '+':
            # x + 0 = x, 0 + x = x
            if self._is_zero(right):
                return left
            if self._is_zero(left):
                return right
        
        elif op == '-':
            # x - 0 = x
            if self._is_zero(right):
                return left
            # x - x = 0 (if x is a simple reference)
            if self._nodes_equal(left, right):
                return ASTNode(ASTNodeType.LITERAL, 0)
        
        elif op == '*':
            # x * 0 = 0, 0 * x = 0
            if self._is_zero(left) or self._is_zero(right):
                return ASTNode(ASTNodeType.LITERAL, 0)
            # x * 1 = x, 1 * x = x
            if self._is_one(right):
                return left
            if self._is_one(left):
                return right
        
        elif op == '/':
            # x / 1 = x
            if self._is_one(right):
                return left
            # x / x = 1 (if x is a simple reference)
            if self._nodes_equal(left, right):
                return ASTNode(ASTNodeType.LITERAL, 1)
        
        elif op == '^':
            # x ^ 0 = 1
            if self._is_zero(right):
                return ASTNode(ASTNodeType.LITERAL, 1)
            # x ^ 1 = x
            if self._is_one(right):
                return left
            # 1 ^ x = 1
            if self._is_one(left):
                return ASTNode(ASTNodeType.LITERAL, 1)
        
        return ast
    
    def _simplify_unary_operation(self, ast: ASTNode) -> ASTNode:
        """Simplify unary operations."""
        if len(ast.children) != 1:
            return ast
        
        operand = ast.children[0]
        op = ast.value
        
        # Double negation: -(-x) = x
        if op == '-' and operand.node_type == ASTNodeType.UNARY_OP and operand.value == '-':
            return operand.children[0]
        
        # Unary plus: +x = x
        if op == '+':
            return operand
        
        return ast
    
    def _expression_simplification(self, ast: ASTNode) -> ASTNode:
        """Simplify expressions using logical rules."""
        # Recursively optimize children first
        for i, child in enumerate(ast.children):
            ast.children[i] = self._expression_simplification(child)
        
        if ast.node_type == ASTNodeType.LOGICAL:
            return self._simplify_logical_expression(ast)
        elif ast.node_type == ASTNodeType.FUNCTION_CALL:
            return self._simplify_function_call(ast)
        
        return ast
    
    def _simplify_logical_expression(self, ast: ASTNode) -> ASTNode:
        """Simplify logical expressions."""
        op = ast.value.upper()
        
        if op == 'AND':
            # Remove TRUE literals, return FALSE if any FALSE found
            simplified_children = []
            for child in ast.children:
                if self._is_true(child):
                    continue  # Skip TRUE literals
                elif self._is_false(child):
                    return ASTNode(ASTNodeType.LITERAL, False)  # AND with FALSE = FALSE
                else:
                    simplified_children.append(child)
            
            if not simplified_children:
                return ASTNode(ASTNodeType.LITERAL, True)  # All were TRUE
            elif len(simplified_children) == 1:
                return simplified_children[0]
            else:
                ast.children = simplified_children
        
        elif op == 'OR':
            # Remove FALSE literals, return TRUE if any TRUE found
            simplified_children = []
            for child in ast.children:
                if self._is_false(child):
                    continue  # Skip FALSE literals
                elif self._is_true(child):
                    return ASTNode(ASTNodeType.LITERAL, True)  # OR with TRUE = TRUE
                else:
                    simplified_children.append(child)
            
            if not simplified_children:
                return ASTNode(ASTNodeType.LITERAL, False)  # All were FALSE
            elif len(simplified_children) == 1:
                return simplified_children[0]
            else:
                ast.children = simplified_children
        
        elif op == 'NOT':
            if len(ast.children) == 1:
                child = ast.children[0]
                # NOT(TRUE) = FALSE, NOT(FALSE) = TRUE
                if self._is_true(child):
                    return ASTNode(ASTNodeType.LITERAL, False)
                elif self._is_false(child):
                    return ASTNode(ASTNodeType.LITERAL, True)
                # NOT(NOT(x)) = x
                elif (child.node_type == ASTNodeType.LOGICAL and 
                      child.value.upper() == 'NOT' and len(child.children) == 1):
                    return child.children[0]
        
        return ast
    
    def _simplify_function_call(self, ast: ASTNode) -> ASTNode:
        """Simplify function calls."""
        func_name = ast.value
        
        # IF function simplification
        if func_name == 'IF' and len(ast.children) >= 2:
            condition = ast.children[0]
            
            if self._is_true(condition):
                # IF(TRUE, x, y) = x
                return ast.children[1]
            elif self._is_false(condition):
                # IF(FALSE, x, y) = y (or FALSE if no else clause)
                if len(ast.children) >= 3:
                    return ast.children[2]
                else:
                    return ASTNode(ASTNodeType.LITERAL, False)
        
        return ast
    
    def _dead_code_elimination(self, ast: ASTNode) -> ASTNode:
        """Remove dead code (unreachable expressions)."""
        # For now, this is mainly handled by other optimizations
        # In a more complex system, this would analyze control flow
        return ast
    
    def _common_subexpression_elimination(self, ast: ASTNode) -> ASTNode:
        """Eliminate common subexpressions."""
        # This is a simplified version - a full implementation would
        # require more sophisticated analysis
        return ast
    
    def _is_zero(self, node: ASTNode) -> bool:
        """Check if a node represents zero."""
        return (node.node_type == ASTNodeType.LITERAL and 
                isinstance(node.value, (int, float)) and 
                node.value == 0)
    
    def _is_one(self, node: ASTNode) -> bool:
        """Check if a node represents one."""
        return (node.node_type == ASTNodeType.LITERAL and 
                isinstance(node.value, (int, float)) and 
                node.value == 1)
    
    def _is_true(self, node: ASTNode) -> bool:
        """Check if a node represents TRUE."""
        return (node.node_type == ASTNodeType.LITERAL and 
                node.value is True)
    
    def _is_false(self, node: ASTNode) -> bool:
        """Check if a node represents FALSE."""
        return (node.node_type == ASTNodeType.LITERAL and 
                node.value is False)
    
    def _nodes_equal(self, node1: ASTNode, node2: ASTNode) -> bool:
        """Check if two nodes are structurally equal."""
        if node1.node_type != node2.node_type:
            return False
        if node1.value != node2.value:
            return False
        if len(node1.children) != len(node2.children):
            return False
        
        return all(self._nodes_equal(c1, c2) 
                  for c1, c2 in zip(node1.children, node2.children))
    
    def _count_nodes(self, ast: ASTNode) -> int:
        """Count the number of nodes in an AST."""
        count = 1  # Count this node
        for child in ast.children:
            count += self._count_nodes(child)
        return count
    
    def _estimate_performance_improvement(self, original: ASTNode, optimized: ASTNode,
                                        optimizations: List[OptimizationType]) -> float:
        """Estimate performance improvement from optimizations."""
        original_complexity = self._calculate_complexity(original)
        optimized_complexity = self._calculate_complexity(optimized)
        
        if original_complexity == 0:
            return 1.0
        
        improvement = (original_complexity - optimized_complexity) / original_complexity
        return max(0.0, improvement)
    
    def _calculate_complexity(self, ast: ASTNode) -> int:
        """Calculate computational complexity of an AST."""
        complexity = 1
        
        # Different node types have different costs
        if ast.node_type == ASTNodeType.FUNCTION_CALL:
            complexity += 10  # Function calls are expensive
        elif ast.node_type in [ASTNodeType.BINARY_OP, ASTNodeType.COMPARISON]:
            complexity += 2
        elif ast.node_type == ASTNodeType.CELL_REFERENCE:
            complexity += 3  # Cell lookup cost
        elif ast.node_type == ASTNodeType.RANGE_REFERENCE:
            complexity += 20  # Range processing is expensive
        
        # Add complexity of children
        for child in ast.children:
            complexity += self._calculate_complexity(child)
        
        return complexity
    
    def enable_optimization(self, optimization_type: OptimizationType, enabled: bool = True) -> None:
        """Enable or disable a specific optimization."""
        self.optimizations_enabled[optimization_type] = enabled
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get optimizer statistics."""
        total_reduction = self._total_nodes_before - self._total_nodes_after
        reduction_ratio = (total_reduction / max(1, self._total_nodes_before))
        
        return {
            'optimization_count': self._optimization_count,
            'total_nodes_before': self._total_nodes_before,
            'total_nodes_after': self._total_nodes_after,
            'total_reduction': total_reduction,
            'reduction_ratio': reduction_ratio,
            'enabled_optimizations': [opt.value for opt, enabled in 
                                    self.optimizations_enabled.items() if enabled]
        }

