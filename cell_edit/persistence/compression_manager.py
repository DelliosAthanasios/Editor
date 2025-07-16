"""
Manages compression and decompression for persistence operations.
Provides various compression algorithms and handles data integrity.
"""

import zlib
import lzma
import bz2
from enum import Enum
from typing import Any, Callable, Dict, Optional, List


class CompressionAlgorithm(Enum):
    """
    Supported compression algorithms.
    """
    NONE = "none"
    ZLIB = "zlib"
    LZMA = "lzma"
    BZIP2 = "bzip2"


class PersistenceCompressionManager:
    """
    Handles compression and decompression of data for storage.
    """
    
    def __init__(self):
        self._compressors: Dict[CompressionAlgorithm, Callable[[bytes], bytes]] = {
            CompressionAlgorithm.NONE: lambda data: data,
            CompressionAlgorithm.ZLIB: zlib.compress,
            CompressionAlgorithm.LZMA: lzma.compress,
            CompressionAlgorithm.BZIP2: bz2.compress,
        }
        self._decompressors: Dict[CompressionAlgorithm, Callable[[bytes], bytes]] = {
            CompressionAlgorithm.NONE: lambda data: data,
            CompressionAlgorithm.ZLIB: zlib.decompress,
            CompressionAlgorithm.LZMA: lzma.decompress,
            CompressionAlgorithm.BZIP2: bz2.decompress,
        }

    def compress(self, data: bytes, algorithm: CompressionAlgorithm) -> bytes:
        """
        Compresses the given data using the specified algorithm.
        """
        if algorithm not in self._compressors:
            raise ValueError(f"Unsupported compression algorithm: {algorithm.value}")
        return self._compressors[algorithm](data)

    def decompress(self, data: bytes, algorithm: CompressionAlgorithm) -> bytes:
        """
        Decompresses the given data using the specified algorithm.
        """
        if algorithm not in self._decompressors:
            raise ValueError(f"Unsupported decompression algorithm: {algorithm.value}")
        return self._decompressors[algorithm](data)

    def get_supported_algorithms(self) -> List[CompressionAlgorithm]:
        """
        Returns a list of supported compression algorithms.
        """
        return list(self._compressors.keys())


# Global instance for PersistenceCompressionManager
_global_persistence_compression_manager: Optional[PersistenceCompressionManager] = None

def get_persistence_compression_manager() -> PersistenceCompressionManager:
    """
    Returns the global PersistenceCompressionManager instance.
    """
    global _global_persistence_compression_manager
    if _global_persistence_compression_manager is None:
        _global_persistence_compression_manager = PersistenceCompressionManager()
    return _global_persistence_compression_manager


