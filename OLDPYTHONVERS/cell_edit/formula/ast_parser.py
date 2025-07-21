"""
Abstract Syntax Tree (AST) parser for formula expressions.
Converts formula strings into structured AST for efficient evaluation.
"""

import re
import operator
from typing import Any, List, Optional, Union, Dict, Tuple
from enum import Enum
from dataclasses import dataclass
import ast

from core.coordinates import CellCoordinate, CellRange


class ASTNodeType(Enum):
    """Types of AST nodes."""
    LITERAL = "literal"           # Numbers, strings, booleans
    CELL_REFERENCE = "cell_ref"   # A1, B2, etc.
    RANGE_REFERENCE = "range_ref" # A1:B10
    FUNCTION_CALL = "function"    # SUM(), AVERAGE(), etc.
    BINARY_OP = "binary_op"       # +, -, *, /, ^, etc.
    UNARY_OP = "unary_op"         # -, +
    COMPARISON = "comparison"     # =, <>, <, >, <=, >=
    LOGICAL = "logical"           # AND, OR, NOT
    ARRAY = "array"               # {1,2,3}
    ERROR = "error"               # #ERROR!, #DIV/0!, etc.


@dataclass
class ASTNode:
    """AST node representing a part of a formula."""
    node_type: ASTNodeType
    value: Any = None
    children: List['ASTNode'] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.metadata is None:
            self.metadata = {}
    
    def add_child(self, child: 'ASTNode') -> None:
        """Add a child node."""
        self.children.append(child)
    
    def get_dependencies(self) -> List[Union[CellCoordinate, CellRange]]:
        """Get all cell/range dependencies in this subtree."""
        dependencies = []
        
        if self.node_type == ASTNodeType.CELL_REFERENCE:
            dependencies.append(CellCoordinate.from_a1(self.value))
        elif self.node_type == ASTNodeType.RANGE_REFERENCE:
            dependencies.append(CellRange.from_a1(self.value))
        
        # Recursively get dependencies from children
        for child in self.children:
            dependencies.extend(child.get_dependencies())
        
        return dependencies
    
    def __repr__(self) -> str:
        if self.children:
            children_repr = f", children={len(self.children)}"
        else:
            children_repr = ""
        return f"ASTNode({self.node_type.value}, {self.value!r}{children_repr})"


class TokenType(Enum):
    """Token types for lexical analysis."""
    NUMBER = "number"
    STRING = "string"
    BOOLEAN = "boolean"
    CELL_REF = "cell_ref"
    RANGE_REF = "range_ref"
    FUNCTION = "function"
    OPERATOR = "operator"
    COMPARISON = "comparison"
    LOGICAL = "logical"
    LPAREN = "lparen"
    RPAREN = "rparen"
    COMMA = "comma"
    SEMICOLON = "semicolon"
    LBRACE = "lbrace"
    RBRACE = "rbrace"
    ERROR = "error"
    EOF = "eof"


@dataclass
class Token:
    """Token for lexical analysis."""
    type: TokenType
    value: str
    position: int


class FormulaLexer:
    """Lexical analyzer for formula expressions."""
    
    # Regular expressions for token matching
    TOKEN_PATTERNS = [
        (TokenType.NUMBER, r'\d+\.?\d*([eE][+-]?\d+)?'),
        (TokenType.STRING, r'"([^"\\]|\\.)*"'),
        (TokenType.BOOLEAN, r'\b(TRUE|FALSE)\b'),
        (TokenType.RANGE_REF, r'[A-Z]+\d+:[A-Z]+\d+'),
        (TokenType.CELL_REF, r'[A-Z]+\d+'),
        (TokenType.FUNCTION, r'[A-Z_][A-Z0-9_]*(?=\()'),
        (TokenType.COMPARISON, r'(<>|<=|>=|=|<|>)'),
        (TokenType.LOGICAL, r'\b(AND|OR|NOT)\b'),
        (TokenType.OPERATOR, r'[+\-*/^%]'),
        (TokenType.LPAREN, r'\('),
        (TokenType.RPAREN, r'\)'),
        (TokenType.COMMA, r','),
        (TokenType.SEMICOLON, r';'),
        (TokenType.LBRACE, r'\{'),
        (TokenType.RBRACE, r'\}'),
        (TokenType.ERROR, r'#[A-Z0-9_!]+'),
    ]
    
    def __init__(self):
        # Compile patterns for efficiency
        self._compiled_patterns = [
            (token_type, re.compile(pattern, re.IGNORECASE))
            for token_type, pattern in self.TOKEN_PATTERNS
        ]
    
    def tokenize(self, formula: str) -> List[Token]:
        """Tokenize a formula string."""
        if not formula.startswith('='):
            # Not a formula, treat as literal
            return [Token(TokenType.STRING, formula, 0)]
        
        # Remove the leading '='
        formula = formula[1:].strip()
        tokens = []
        position = 0
        
        while position < len(formula):
            # Skip whitespace
            if formula[position].isspace():
                position += 1
                continue
            
            # Try to match each pattern
            matched = False
            for token_type, pattern in self._compiled_patterns:
                match = pattern.match(formula, position)
                if match:
                    value = match.group(0)
                    tokens.append(Token(token_type, value, position))
                    position = match.end()
                    matched = True
                    break
            
            if not matched:
                # Unknown character, treat as error
                tokens.append(Token(TokenType.ERROR, formula[position], position))
                position += 1
        
        tokens.append(Token(TokenType.EOF, "", position))
        return tokens


class FormulaParser:
    """Recursive descent parser for formula expressions."""
    
    # Operator precedence (higher number = higher precedence)
    PRECEDENCE = {
        'OR': 1,
        'AND': 2,
        '=': 3, '<>': 3, '<': 3, '>': 3, '<=': 3, '>=': 3,
        '+': 4, '-': 4,
        '*': 5, '/': 5, '%': 5,
        '^': 6,
        'UNARY': 7,  # Unary + and -
    }
    
    def __init__(self):
        self.lexer = FormulaLexer()
        self.tokens = []
        self.position = 0
        self.current_token = None
    
    def parse(self, formula: str) -> ASTNode:
        """Parse a formula string into an AST."""
        try:
            self.tokens = self.lexer.tokenize(formula)
            self.position = 0
            self.current_token = self.tokens[0] if self.tokens else None
            
            if not self.tokens or self.tokens[0].type == TokenType.STRING:
                # Literal value
                value = formula[1:] if formula.startswith('=') else formula
                return ASTNode(ASTNodeType.LITERAL, value)
            
            ast = self.parse_expression()
            
            if self.current_token.type != TokenType.EOF:
                raise SyntaxError(f"Unexpected token: {self.current_token.value}")
            
            return ast
        
        except Exception as e:
            # Return error node
            return ASTNode(ASTNodeType.ERROR, str(e))
    
    def parse_expression(self) -> ASTNode:
        """Parse a complete expression."""
        return self.parse_logical_or()
    
    def parse_logical_or(self) -> ASTNode:
        """Parse logical OR expressions."""
        left = self.parse_logical_and()
        
        while self.current_token and self.current_token.value.upper() == 'OR':
            op = self.current_token.value.upper()
            self.advance()
            right = self.parse_logical_and()
            left = ASTNode(ASTNodeType.LOGICAL, op, [left, right])
        
        return left
    
    def parse_logical_and(self) -> ASTNode:
        """Parse logical AND expressions."""
        left = self.parse_comparison()
        
        while self.current_token and self.current_token.value.upper() == 'AND':
            op = self.current_token.value.upper()
            self.advance()
            right = self.parse_comparison()
            left = ASTNode(ASTNodeType.LOGICAL, op, [left, right])
        
        return left
    
    def parse_comparison(self) -> ASTNode:
        """Parse comparison expressions."""
        left = self.parse_addition()
        
        while (self.current_token and 
               self.current_token.type == TokenType.COMPARISON):
            op = self.current_token.value
            self.advance()
            right = self.parse_addition()
            left = ASTNode(ASTNodeType.COMPARISON, op, [left, right])
        
        return left
    
    def parse_addition(self) -> ASTNode:
        """Parse addition and subtraction."""
        left = self.parse_multiplication()
        
        while (self.current_token and 
               self.current_token.value in ['+', '-']):
            op = self.current_token.value
            self.advance()
            right = self.parse_multiplication()
            left = ASTNode(ASTNodeType.BINARY_OP, op, [left, right])
        
        return left
    
    def parse_multiplication(self) -> ASTNode:
        """Parse multiplication, division, and modulo."""
        left = self.parse_exponentiation()
        
        while (self.current_token and 
               self.current_token.value in ['*', '/', '%']):
            op = self.current_token.value
            self.advance()
            right = self.parse_exponentiation()
            left = ASTNode(ASTNodeType.BINARY_OP, op, [left, right])
        
        return left
    
    def parse_exponentiation(self) -> ASTNode:
        """Parse exponentiation (right-associative)."""
        left = self.parse_unary()
        
        if (self.current_token and 
            self.current_token.value == '^'):
            op = self.current_token.value
            self.advance()
            right = self.parse_exponentiation()  # Right-associative
            return ASTNode(ASTNodeType.BINARY_OP, op, [left, right])
        
        return left
    
    def parse_unary(self) -> ASTNode:
        """Parse unary expressions."""
        if (self.current_token and 
            self.current_token.value in ['+', '-']):
            op = self.current_token.value
            self.advance()
            operand = self.parse_unary()
            return ASTNode(ASTNodeType.UNARY_OP, op, [operand])
        
        if (self.current_token and 
            self.current_token.value.upper() == 'NOT'):
            op = self.current_token.value.upper()
            self.advance()
            operand = self.parse_unary()
            return ASTNode(ASTNodeType.LOGICAL, op, [operand])
        
        return self.parse_primary()
    
    def parse_primary(self) -> ASTNode:
        """Parse primary expressions."""
        if not self.current_token:
            raise SyntaxError("Unexpected end of formula")
        
        token = self.current_token
        
        if token.type == TokenType.NUMBER:
            self.advance()
            try:
                value = int(token.value) if '.' not in token.value else float(token.value)
                return ASTNode(ASTNodeType.LITERAL, value)
            except ValueError:
                return ASTNode(ASTNodeType.ERROR, f"Invalid number: {token.value}")
        
        elif token.type == TokenType.STRING:
            self.advance()
            # Remove quotes
            value = token.value[1:-1] if token.value.startswith('"') else token.value
            return ASTNode(ASTNodeType.LITERAL, value)
        
        elif token.type == TokenType.BOOLEAN:
            self.advance()
            value = token.value.upper() == 'TRUE'
            return ASTNode(ASTNodeType.LITERAL, value)
        
        elif token.type == TokenType.CELL_REF:
            self.advance()
            return ASTNode(ASTNodeType.CELL_REFERENCE, token.value.upper())
        
        elif token.type == TokenType.RANGE_REF:
            self.advance()
            return ASTNode(ASTNodeType.RANGE_REFERENCE, token.value.upper())
        
        elif token.type == TokenType.FUNCTION:
            return self.parse_function_call()
        
        elif token.type == TokenType.LPAREN:
            self.advance()  # consume '('
            expr = self.parse_expression()
            if not self.current_token or self.current_token.type != TokenType.RPAREN:
                raise SyntaxError("Missing closing parenthesis")
            self.advance()  # consume ')'
            return expr
        
        elif token.type == TokenType.LBRACE:
            return self.parse_array()
        
        elif token.type == TokenType.ERROR:
            self.advance()
            return ASTNode(ASTNodeType.ERROR, token.value)
        
        else:
            raise SyntaxError(f"Unexpected token: {token.value}")
    
    def parse_function_call(self) -> ASTNode:
        """Parse function calls."""
        func_name = self.current_token.value.upper()
        self.advance()  # consume function name
        
        if not self.current_token or self.current_token.type != TokenType.LPAREN:
            raise SyntaxError(f"Expected '(' after function {func_name}")
        
        self.advance()  # consume '('
        
        args = []
        if self.current_token.type != TokenType.RPAREN:
            args.append(self.parse_expression())
            
            while (self.current_token and 
                   self.current_token.type == TokenType.COMMA):
                self.advance()  # consume ','
                args.append(self.parse_expression())
        
        if not self.current_token or self.current_token.type != TokenType.RPAREN:
            raise SyntaxError(f"Missing closing parenthesis for function {func_name}")
        
        self.advance()  # consume ')'
        
        return ASTNode(ASTNodeType.FUNCTION_CALL, func_name, args)
    
    def parse_array(self) -> ASTNode:
        """Parse array literals."""
        self.advance()  # consume '{'
        
        elements = []
        if self.current_token.type != TokenType.RBRACE:
            elements.append(self.parse_expression())
            
            while (self.current_token and 
                   self.current_token.type in [TokenType.COMMA, TokenType.SEMICOLON]):
                separator = self.current_token.value
                self.advance()
                elements.append(self.parse_expression())
        
        if not self.current_token or self.current_token.type != TokenType.RBRACE:
            raise SyntaxError("Missing closing brace for array")
        
        self.advance()  # consume '}'
        
        return ASTNode(ASTNodeType.ARRAY, None, elements)
    
    def advance(self) -> None:
        """Move to the next token."""
        self.position += 1
        if self.position < len(self.tokens):
            self.current_token = self.tokens[self.position]
        else:
            self.current_token = None


class FormulaAST:
    """High-level interface for formula AST operations."""
    
    def __init__(self):
        self.parser = FormulaParser()
        self._cache = {}  # Cache parsed ASTs
    
    def parse(self, formula: str, use_cache: bool = True) -> ASTNode:
        """Parse a formula into an AST."""
        if use_cache and formula in self._cache:
            return self._cache[formula]
        
        ast = self.parser.parse(formula)
        
        if use_cache:
            self._cache[formula] = ast
        
        return ast
    
    def get_dependencies(self, formula: str) -> List[Union[CellCoordinate, CellRange]]:
        """Get all dependencies from a formula."""
        ast = self.parse(formula)
        return ast.get_dependencies()
    
    def is_valid(self, formula: str) -> bool:
        """Check if a formula is syntactically valid."""
        ast = self.parse(formula)
        return ast.node_type != ASTNodeType.ERROR
    
    def clear_cache(self) -> None:
        """Clear the AST cache."""
        self._cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            'cached_formulas': len(self._cache),
            'cache_size_bytes': sum(len(formula) for formula in self._cache.keys())
        }

