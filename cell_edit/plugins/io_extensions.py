"""
Provides mechanisms for plugins to register custom import/export formats.
This allows the Cell Editor to support various file types beyond its native format.
"""

from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass, field
from enum import Enum

from .extension_points import register_extension, get_extensions, create_extension_point


class IOType(Enum):
    """Type of I/O operation."""
    IMPORT = "import"
    EXPORT = "export"


# Define an extension point for custom I/O formats
CUSTOM_IO_EXTENSION_POINT = create_extension_point(
    "custom_io_formats",
    "Allows plugins to register custom import/export formats."
)


@dataclass
class IOFormatInfo:
    """
    Represents information about a custom I/O format provided by a plugin.
    """
    format_id: str
    display_name: str
    file_extensions: List[str]
    io_type: IOType
    # Callable to handle the import/export logic
    handler: Callable[[Any, str, Optional[Dict[str, Any]]], Any]
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not callable(self.handler):
            raise ValueError("I/O handler must be a callable.")
        if not self.file_extensions:
            raise ValueError("File extensions cannot be empty.")


class IOExtensionManager:
    """
    Manages the registration and retrieval of custom I/O formats from plugins.
    """
    
    def __init__(self__(self):
        self._registered_formats: Dict[str, IOFormatInfo] = {}

    def register_io_format(self, plugin_name: str, format_info: IOFormatInfo) -> None:
        """
        Registers a custom I/O format from a plugin.
        """
        if not isinstance(format_info, IOFormatInfo):
            raise TypeError("format_info must be an instance of IOFormatInfo")
            
        if format_info.format_id in self._registered_formats:
            raise ValueError(f"I/O format with ID \'{format_info.format_id}\' already registered.")
            
        self._registered_formats[format_info.format_id] = format_info
        
        # Register with the extension point for discovery
        register_extension(
            CUSTOM_IO_EXTENSION_POINT.name,
            plugin_name,
            format_info.format_id,
            format_info
        )
        print(f"Custom I/O format \'{format_info.format_id}\' registered by plugin \'{plugin_name}\'")

    def unregister_io_format(self, format_id: str) -> None:
        """
        Unregisters a custom I/O format.
        """
        if format_id not in self._registered_formats:
            print(f"I/O format \'{format_id}\' not found.")
            return
            
        CUSTOM_IO_EXTENSION_POINT.unregister(format_id)
        del self._registered_formats[format_id]
        print(f"I/O format \'{format_id}\' unregistered.")

    def get_io_format(self, format_id: str) -> Optional[IOFormatInfo]:
        """
        Retrieves a registered I/O format by its ID.
        """
        return self._registered_formats.get(format_id)

    def get_formats_by_type(self, io_type: IOType) -> List[IOFormatInfo]:
        """
        Returns a list of all registered formats of a specific type (import/export).
        """
        return [
            fmt for fmt in self._registered_formats.values() 
            if fmt.io_type == io_type
        ]
        
    def get_format_by_extension(self, extension: str, io_type: IOType) -> Optional[IOFormatInfo]:
        """
        Retrieves an I/O format by file extension and type.
        """
        for fmt in self._registered_formats.values():
            if io_type == fmt.io_type and extension.lower() in [ext.lower() for ext in fmt.file_extensions]:
                return fmt
        return None


# Global instance for IOExtensionManager
_global_io_extension_manager: Optional[IOExtensionManager] = None

def get_io_extension_manager() -> IOExtensionManager:
    """
    Returns the global IOExtensionManager instance.
    """
    global _global_io_extension_manager
    if _global_io_extension_manager is None:
        _global_io_extension_manager = IOExtensionManager()
    return _global_io_extension_manager


