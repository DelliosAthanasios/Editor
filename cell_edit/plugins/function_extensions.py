"""
Provides mechanisms for plugins to register custom functions that can be used in formulas.
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass

from .extension_points import register_extension, get_extensions, create_extension_point
from ..formula.function_registry import FunctionRegistry, get_function_registry


# Define an extension point for custom formula functions
CUSTOM_FORMULA_FUNCTION_EXTENSION_POINT = create_extension_point(
    "custom_formula_functions",
    "Allows plugins to register custom functions that can be used in spreadsheet formulas."
)


@dataclass
class CustomFunctionInfo:
    """
    Represents information about a custom function provided by a plugin.
    """
    name: str
    function: Callable
    description: str
    category: str = "Custom"
    args_info: Optional[List[Dict[str, str]]] = None
    
    def __post_init__(self):
        if not callable(self.function):
            raise ValueError("Custom function must be a callable.")


class CustomFunctionManager:
    """
    Manages the registration and retrieval of custom functions from plugins.
    Integrates with the core formula engine's FunctionRegistry.
    """
    
    def __init__(self, function_registry: FunctionRegistry):
        self._function_registry = function_registry
        self._registered_custom_functions: Dict[str, CustomFunctionInfo] = {}
        
        # Register a hook to load custom functions when plugins are loaded
        # get_hook_system().register("plugin_loaded", self._on_plugin_loaded)
        # get_hook_system().register("plugin_unloaded", self._on_plugin_unloaded)

    def register_custom_function(self, plugin_name: str, func_info: CustomFunctionInfo) -> None:
        """
        Registers a custom function from a plugin.
        This function will be available in the formula engine.
        """
        if not isinstance(func_info, CustomFunctionInfo):
            raise TypeError("func_info must be an instance of CustomFunctionInfo")
            
        if func_info.name in self._registered_custom_functions:
            raise ValueError(f"Custom function \'{func_info.name}\' already registered.")
            
        # Register with the core formula registry
        self._function_registry.register_function(
            func_info.name,
            func_info.function,
            description=func_info.description,
            category=func_info.category,
            args_info=func_info.args_info
        )
        
        self._registered_custom_functions[func_info.name] = func_info
        
        # Register with the extension point for discovery
        register_extension(
            CUSTOM_FORMULA_FUNCTION_EXTENSION_POINT.name,
            plugin_name,
            func_info.name,
            func_info
        )
        print(f"Custom function \'{func_info.name}\' registered by plugin \'{plugin_name}\'")

    def unregister_custom_function(self, func_name: str) -> None:
        """
        Unregisters a custom function.
        """
        if func_name not in self._registered_custom_functions:
            print(f"Custom function \'{func_name}\' not found.")
            return
            
        self._function_registry.unregister_function(func_name)
        CUSTOM_FORMULA_FUNCTION_EXTENSION_POINT.unregister(func_name)
        del self._registered_custom_functions[func_name]
        print(f"Custom function \'{func_name}\' unregistered.")

    def get_custom_function(self, func_name: str) -> Optional[CustomFunctionInfo]:
        """
        Retrieves a registered custom function.
        """
        return self._registered_custom_functions.get(func_name)

    def get_all_custom_functions(self) -> List[CustomFunctionInfo]:
        """
        Returns a list of all registered custom functions.
        """
        return list(self._registered_custom_functions.values())

    def _on_plugin_loaded(self, plugin_info: Any) -> None:
        """
        Callback when a plugin is loaded. Placeholder for future direct plugin integration.
        Plugins would typically register their functions during their setup phase.
        """
        print(f"[CustomFunctionManager] Plugin \'{plugin_info.name}\' loaded. Custom functions should be registered now.")

    def _on_plugin_unloaded(self, plugin_info: Any) -> None:
        """
        Callback when a plugin is unloaded. Unregisters all functions from that plugin.
        """
        print(f"[CustomFunctionManager] Plugin \'{plugin_info.name}\' unloaded. Unregistering its custom functions.")
        functions_to_unregister = [
            func.extension_id for func in CUSTOM_FORMULA_FUNCTION_EXTENSION_POINT.get_extensions_by_plugin(plugin_info.name)
        ]
        for func_name in functions_to_unregister:
            self.unregister_custom_function(func_name)


# Global instance for CustomFunctionManager
_global_custom_function_manager: Optional[CustomFunctionManager] = None

def get_custom_function_manager() -> CustomFunctionManager:
    """
    Returns the global CustomFunctionManager instance.
    """
    global _global_custom_function_manager
    if _global_custom_function_manager is None:
        _global_custom_function_manager = CustomFunctionManager(get_function_registry())
    return _global_custom_function_manager


