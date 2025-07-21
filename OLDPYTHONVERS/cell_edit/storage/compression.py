"""
Compression manager for memory optimization.
Provides various compression strategies for different data types.
"""

import zlib
import lzma
import pickle
import json
from typing import Any, Dict, Optional, Union, Tuple
from enum import Enum
from dataclasses import dataclass
import threading

from core.config import get_config


class CompressionType(Enum):
    """Available compression algorithms."""
    NONE = "none"
    ZLIB = "zlib"
    LZMA = "lzma"
    CUSTOM = "custom"


@dataclass
class CompressionResult:
    """Result of compression operation."""
    compressed_data: bytes
    original_size: int
    compressed_size: int
    compression_ratio: float
    algorithm: CompressionType
    
    @property
    def space_saved(self) -> int:
        """Get bytes saved by compression."""
        return self.original_size - self.compressed_size
    
    @property
    def is_beneficial(self) -> bool:
        """Check if compression was beneficial."""
        return self.compression_ratio < 0.9  # At least 10% reduction


class CompressionStrategy:
    """Base class for compression strategies."""
    
    def compress(self, data: Any) -> CompressionResult:
        """Compress data and return result."""
        raise NotImplementedError
    
    def decompress(self, compressed_data: bytes, algorithm: CompressionType) -> Any:
        """Decompress data."""
        raise NotImplementedError


class ZlibStrategy(CompressionStrategy):
    """Zlib compression strategy."""
    
    def __init__(self, level: int = 6):
        self.level = level
    
    def compress(self, data: Any) -> CompressionResult:
        """Compress using zlib."""
        # Serialize first
        if isinstance(data, (str, bytes)):
            serialized = data.encode('utf-8') if isinstance(data, str) else data
        else:
            serialized = pickle.dumps(data)
        
        original_size = len(serialized)
        compressed = zlib.compress(serialized, level=self.level)
        compressed_size = len(compressed)
        
        return CompressionResult(
            compressed_data=compressed,
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compressed_size / original_size,
            algorithm=CompressionType.ZLIB
        )
    
    def decompress(self, compressed_data: bytes, algorithm: CompressionType) -> Any:
        """Decompress using zlib."""
        if algorithm != CompressionType.ZLIB:
            raise ValueError(f"Expected ZLIB algorithm, got {algorithm}")
        
        decompressed = zlib.decompress(compressed_data)
        
        # Try to deserialize as pickle first, then as string
        try:
            return pickle.loads(decompressed)
        except (pickle.PickleError, EOFError):
            try:
                return decompressed.decode('utf-8')
            except UnicodeDecodeError:
                return decompressed


class LzmaStrategy(CompressionStrategy):
    """LZMA compression strategy for better compression ratios."""
    
    def __init__(self, preset: int = 6):
        self.preset = preset
    
    def compress(self, data: Any) -> CompressionResult:
        """Compress using LZMA."""
        # Serialize first
        if isinstance(data, (str, bytes)):
            serialized = data.encode('utf-8') if isinstance(data, str) else data
        else:
            serialized = pickle.dumps(data)
        
        original_size = len(serialized)
        compressed = lzma.compress(serialized, preset=self.preset)
        compressed_size = len(compressed)
        
        return CompressionResult(
            compressed_data=compressed,
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compressed_size / original_size,
            algorithm=CompressionType.LZMA
        )
    
    def decompress(self, compressed_data: bytes, algorithm: CompressionType) -> Any:
        """Decompress using LZMA."""
        if algorithm != CompressionType.LZMA:
            raise ValueError(f"Expected LZMA algorithm, got {algorithm}")
        
        decompressed = lzma.decompress(compressed_data)
        
        # Try to deserialize as pickle first, then as string
        try:
            return pickle.loads(decompressed)
        except (pickle.PickleError, EOFError):
            try:
                return decompressed.decode('utf-8')
            except UnicodeDecodeError:
                return decompressed


class CustomStrategy(CompressionStrategy):
    """Custom compression strategy for specific data types."""
    
    def compress(self, data: Any) -> CompressionResult:
        """Compress using custom logic based on data type."""
        original_data = data
        
        # Handle different data types
        if isinstance(data, str):
            # For strings, use simple encoding optimizations
            if data.isdigit():
                # Store numbers as integers
                serialized = str(int(data)).encode('utf-8')
            elif self._is_repeated_pattern(data):
                # Store repeated patterns efficiently
                serialized = self._compress_pattern(data)
            else:
                serialized = data.encode('utf-8')
        
        elif isinstance(data, (int, float)):
            # Store numbers efficiently
            serialized = json.dumps(data).encode('utf-8')
        
        elif isinstance(data, (list, tuple)) and all(isinstance(x, (int, float)) for x in data):
            # Numeric arrays - use efficient encoding
            serialized = self._compress_numeric_array(data)
        
        else:
            # Fallback to pickle
            serialized = pickle.dumps(data)
        
        # Apply zlib compression to the optimized serialization
        original_size = len(serialized)
        compressed = zlib.compress(serialized, level=6)
        compressed_size = len(compressed)
        
        return CompressionResult(
            compressed_data=compressed,
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compressed_size / original_size,
            algorithm=CompressionType.CUSTOM
        )
    
    def decompress(self, compressed_data: bytes, algorithm: CompressionType) -> Any:
        """Decompress using custom logic."""
        if algorithm != CompressionType.CUSTOM:
            raise ValueError(f"Expected CUSTOM algorithm, got {algorithm}")
        
        # First decompress with zlib
        decompressed = zlib.decompress(compressed_data)
        
        # Try different deserialization methods
        try:
            # Try JSON first (for simple types)
            return json.loads(decompressed.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        
        try:
            # Try pickle
            return pickle.loads(decompressed)
        except (pickle.PickleError, EOFError):
            pass
        
        try:
            # Try as string
            return decompressed.decode('utf-8')
        except UnicodeDecodeError:
            return decompressed
    
    def _is_repeated_pattern(self, text: str, min_length: int = 3) -> bool:
        """Check if string has repeated patterns."""
        if len(text) < min_length * 2:
            return False
        
        for pattern_len in range(min_length, len(text) // 2 + 1):
            pattern = text[:pattern_len]
            if text == pattern * (len(text) // pattern_len) + pattern[:len(text) % pattern_len]:
                return True
        
        return False
    
    def _compress_pattern(self, text: str) -> bytes:
        """Compress repeated patterns."""
        # Find the shortest repeating pattern
        for pattern_len in range(1, len(text) // 2 + 1):
            pattern = text[:pattern_len]
            if text == pattern * (len(text) // pattern_len) + pattern[:len(text) % pattern_len]:
                # Store as pattern + count
                count = len(text) // pattern_len
                remainder = text[count * pattern_len:]
                compressed_data = {
                    'type': 'pattern',
                    'pattern': pattern,
                    'count': count,
                    'remainder': remainder
                }
                return json.dumps(compressed_data).encode('utf-8')
        
        # No pattern found, return as-is
        return text.encode('utf-8')
    
    def _compress_numeric_array(self, data: Union[list, tuple]) -> bytes:
        """Compress numeric arrays efficiently."""
        # Convert to list for JSON serialization
        array_data = list(data)
        
        # Check if it's a simple range
        if len(array_data) > 2 and self._is_arithmetic_sequence(array_data):
            compressed_data = {
                'type': 'arithmetic_sequence',
                'start': array_data[0],
                'step': array_data[1] - array_data[0],
                'count': len(array_data)
            }
            return json.dumps(compressed_data).encode('utf-8')
        
        # Store as regular array
        return json.dumps(array_data).encode('utf-8')
    
    def _is_arithmetic_sequence(self, data: list) -> bool:
        """Check if list is an arithmetic sequence."""
        if len(data) < 3:
            return False
        
        step = data[1] - data[0]
        for i in range(2, len(data)):
            if abs((data[i] - data[i-1]) - step) > 1e-10:  # Allow for floating point errors
                return False
        
        return True


class CompressionManager:
    """
    Central compression manager that selects optimal compression strategies.
    """
    
    def __init__(self):
        self._strategies = {
            CompressionType.ZLIB: ZlibStrategy(),
            CompressionType.LZMA: LzmaStrategy(),
            CompressionType.CUSTOM: CustomStrategy()
        }
        self._lock = threading.RLock()
        self._stats = {
            'compressions': 0,
            'decompressions': 0,
            'total_original_size': 0,
            'total_compressed_size': 0,
            'algorithm_usage': {alg.value: 0 for alg in CompressionType}
        }
    
    def compress(self, data: Any, preferred_algorithm: Optional[CompressionType] = None) -> CompressionResult:
        """
        Compress data using the best available algorithm.
        
        Args:
            data: Data to compress
            preferred_algorithm: Preferred compression algorithm
            
        Returns:
            CompressionResult with compressed data and statistics
        """
        with self._lock:
            config = get_config()
            
            if not config.memory.compression_enabled:
                # Return uncompressed data
                serialized = pickle.dumps(data)
                return CompressionResult(
                    compressed_data=serialized,
                    original_size=len(serialized),
                    compressed_size=len(serialized),
                    compression_ratio=1.0,
                    algorithm=CompressionType.NONE
                )
            
            # Try different algorithms and pick the best one
            best_result = None
            algorithms_to_try = []
            
            if preferred_algorithm and preferred_algorithm in self._strategies:
                algorithms_to_try.append(preferred_algorithm)
            else:
                # Try algorithms in order of preference
                algorithms_to_try = [CompressionType.CUSTOM, CompressionType.ZLIB, CompressionType.LZMA]
            
            for algorithm in algorithms_to_try:
                if algorithm in self._strategies:
                    try:
                        result = self._strategies[algorithm].compress(data)
                        
                        if best_result is None or result.compression_ratio < best_result.compression_ratio:
                            best_result = result
                        
                        # If we get good compression, use it
                        if result.compression_ratio < 0.7:
                            break
                    
                    except Exception as e:
                        print(f"Compression failed with {algorithm}: {e}")
                        continue
            
            if best_result is None:
                # Fallback to uncompressed
                serialized = pickle.dumps(data)
                best_result = CompressionResult(
                    compressed_data=serialized,
                    original_size=len(serialized),
                    compressed_size=len(serialized),
                    compression_ratio=1.0,
                    algorithm=CompressionType.NONE
                )
            
            # Update statistics
            self._stats['compressions'] += 1
            self._stats['total_original_size'] += best_result.original_size
            self._stats['total_compressed_size'] += best_result.compressed_size
            self._stats['algorithm_usage'][best_result.algorithm.value] += 1
            
            return best_result
    
    def decompress(self, compressed_data: bytes, algorithm: CompressionType) -> Any:
        """
        Decompress data using the specified algorithm.
        
        Args:
            compressed_data: Compressed data bytes
            algorithm: Algorithm used for compression
            
        Returns:
            Decompressed data
        """
        with self._lock:
            self._stats['decompressions'] += 1
            
            if algorithm == CompressionType.NONE:
                return pickle.loads(compressed_data)
            
            if algorithm not in self._strategies:
                raise ValueError(f"Unknown compression algorithm: {algorithm}")
            
            return self._strategies[algorithm].decompress(compressed_data, algorithm)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get compression statistics."""
        with self._lock:
            stats = self._stats.copy()
            
            if stats['total_original_size'] > 0:
                stats['overall_compression_ratio'] = stats['total_compressed_size'] / stats['total_original_size']
                stats['space_saved'] = stats['total_original_size'] - stats['total_compressed_size']
            else:
                stats['overall_compression_ratio'] = 1.0
                stats['space_saved'] = 0
            
            return stats
    
    def reset_statistics(self) -> None:
        """Reset compression statistics."""
        with self._lock:
            self._stats = {
                'compressions': 0,
                'decompressions': 0,
                'total_original_size': 0,
                'total_compressed_size': 0,
                'algorithm_usage': {alg.value: 0 for alg in CompressionType}
            }
    
    def benchmark_algorithms(self, test_data: Any) -> Dict[CompressionType, CompressionResult]:
        """Benchmark all algorithms on test data."""
        results = {}
        
        for algorithm, strategy in self._strategies.items():
            try:
                result = strategy.compress(test_data)
                results[algorithm] = result
            except Exception as e:
                print(f"Benchmark failed for {algorithm}: {e}")
        
        return results


# Global compression manager instance
_global_compression_manager = None


def get_compression_manager() -> CompressionManager:
    """Get the global compression manager instance."""
    global _global_compression_manager
    if _global_compression_manager is None:
        _global_compression_manager = CompressionManager()
    return _global_compression_manager


def compress_data(data: Any, algorithm: Optional[CompressionType] = None) -> CompressionResult:
    """Convenience function to compress data."""
    return get_compression_manager().compress(data, algorithm)


def decompress_data(compressed_data: bytes, algorithm: CompressionType) -> Any:
    """Convenience function to decompress data."""
    return get_compression_manager().decompress(compressed_data, algorithm)

