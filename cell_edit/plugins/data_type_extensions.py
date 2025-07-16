"""
Provides mechanisms for plugins to register custom data types.
This allows the Cell Editor to understand and process new types of data.
"""

from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass, field

from .extension_points import register_extension, get_extensions, create_extension_point


# Define an extension point for custom data types
CUSTOM_DATA_TYPE_EXTENSION_POINT = create_extension_point(
    "custom_data_types",
    "Allows plugins to register custom data types and their handling logic."
)


@dataclass
class DataTypeInfo:
    """
    Represents information about a custom data type provided by a plugin.
    """
    name: str
    display_name: str
    description: str
    # Callable to validate if a value is of this type
    validator: Callable[[Any], bool]
    # Callable to convert a value to this type (e.g., from string)
    converter: Callable[[Any], Any]
    # Optional: Callable to format the value for display
    formatter: Optional[Callable[[Any], str]] = None
    # Optional: Callable to parse a string into the value
    parser: Optional[Callable[[str], Any]] = None
    # Optional: Default format string for display
    default_format: Optional[str] = None
    # Optional: Icon or visual representation
    icon: Optional[str] = None
    
    def __post_init__(self):
        if not callable(self.validator):
            raise ValueError("Data type validator must be a callable.")
        if not callable(self.converter):
            raise ValueError("Data type converter must be a callable.")


class DataTypeManager:
    """
    Manages the registration and retrieval of custom data types from plugins.
    """
    
    def __init__(self):
        self._registered_data_types: Dict[str, DataTypeInfo] = {}

    def register_data_type(self, plugin_name: str, data_type_info: DataTypeInfo) -> None:
        """
        Registers a custom data type from a plugin.
        """
        if not isinstance(data_type_info, DataTypeInfo):
            raise TypeError("data_type_info must be an instance of DataTypeInfo")
            
        if data_type_info.name in self._registered_data_types:
            raise ValueError(f"Data type \'{data_type_info.name}\' already registered.")
            
        self._registered_data_types[data_type_info.name] = data_type_info
        
        # Register with the extension point for discovery
        register_extension(
            CUSTOM_DATA_TYPE_EXTENSION_POINT.name,
            plugin_name,
            data_type_info.name,
            data_type_info
        )
        print(f"Custom data type \'{data_type_info.name}\' registered by plugin \'{plugin_name}\'")

    def unregister_data_type(self, data_type_name: str) -> None:
        """
        Unregisters a custom data type.
        """
        if data_type_name not in self._registered_data_types:
            print(f"Data type \'{data_type_name}\' not found.")
            return
            
        CUSTOM_DATA_TYPE_EXTENSION_POINT.unregister(data_type_name)
        del self._registered_data_types[data_type_name]
        print(f"Data type \'{data_type_name}\' unregistered.")

    def get_data_type(self, data_type_name: str) -> Optional[DataTypeInfo]:
        """
        Retrieves a registered data type.
        """
        return self._registered_data_types.get(data_type_name)

    def get_all_data_types(self) -> List[DataTypeInfo]:
        """
        Returns a list of all registered data types.
        """
        return list(self._registered_data_types.values())


# Global instance for DataTypeManager
_global_data_type_manager: Optional[DataTypeManager] = None

def get_data_type_manager() -> DataTypeManager:
    """
    Returns the global DataTypeManager instance.
    """
    global _global_data_type_manager
    if _global_data_type_manager is None:
        _global_data_type_manager = DataTypeManager()
    return _global_data_type_manager


