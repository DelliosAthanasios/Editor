"""
Manages the loading, unloading, and lifecycle of plugins.
Plugins extend the Cell Editor's functionality dynamically.
"""

import importlib.util
import sys
import os
import threading
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass, field

from plugins.extension_points import get_extension_point_manager
from plugins.hook_system import get_hook_system


@dataclass
class PluginInfo:
    """Information about a loaded plugin."""
    name: str
    version: str
    author: str
    description: str
    path: str
    is_loaded: bool = False
    module: Optional[Any] = None
    errors: List[str] = field(default_factory=list)


class PluginManager:
    """
    Manages the discovery, loading, activation, and deactivation of plugins.
    """
    
    def __init__(self, plugin_dirs: Optional[List[str]] = None):
        self._plugin_dirs = plugin_dirs if plugin_dirs is not None else []
        self._available_plugins: Dict[str, PluginInfo] = {}
        self._loaded_plugins: Dict[str, PluginInfo] = {}
        self._lock = threading.RLock()
        
        self.extension_point_manager = get_extension_point_manager()
        self.hook_system = get_hook_system()
        
        self._discover_plugins()
    
    def add_plugin_directory(self, path: str) -> None:
        """Add a directory to search for plugins."""
        with self._lock:
            if path not in self._plugin_dirs:
                self._plugin_dirs.append(path)
                self._discover_plugins()
    
    def _discover_plugins(self) -> None:
        """Discover plugins in the configured directories."""
        with self._lock:
            for plugin_dir in self._plugin_dirs:
                if not os.path.isdir(plugin_dir):
                    continue
                
                for item_name in os.listdir(plugin_dir):
                    item_path = os.path.join(plugin_dir, item_name)
                    
                    # Assume each subdirectory is a plugin for now
                    if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "__init__.py")):
                        plugin_name = item_name
                        if plugin_name not in self._available_plugins:
                            self._available_plugins[plugin_name] = PluginInfo(
                                name=plugin_name,
                                version="0.1.0", # Default, should be read from plugin metadata
                                author="Unknown",
                                description="",
                                path=item_path
                            )
    
    def get_available_plugins(self) -> List[PluginInfo]:
        """Get a list of all discovered plugins."""
        with self._lock:
            return list(self._available_plugins.values())
            
    def get_loaded_plugins(self) -> List[PluginInfo]:
        """Get a list of all currently loaded plugins."""
        with self._lock:
            return list(self._loaded_plugins.values())
            
    def load_plugin(self, plugin_name: str) -> Optional[PluginInfo]:
        """Load a specific plugin by name."""
        with self._lock:
            if plugin_name not in self._available_plugins:
                print(f"Plugin \'{plugin_name}\' not found.")
                return None
            
            if plugin_name in self._loaded_plugins:
                print(f"Plugin \'{plugin_name}\' is already loaded.")
                return self._loaded_plugins[plugin_name]
            
            plugin_info = self._available_plugins[plugin_name]
            plugin_path = plugin_info.path
            
            try:
                # Add plugin path to sys.path for module discovery
                if plugin_path not in sys.path:
                    sys.path.insert(0, plugin_path)
                
                # Import the plugin module
                spec = importlib.util.spec_from_file_location(plugin_name, os.path.join(plugin_path, "__init__.py"))
                if spec is None or spec.loader is None:
                    raise ImportError(f"Could not find spec for plugin module {plugin_name}")
                
                module = importlib.util.module_from_spec(spec)
                sys.modules[plugin_name] = module
                spec.loader.exec_module(module)
                
                # Check for a 'setup' function in the plugin module
                if hasattr(module, "setup") and callable(module.setup):
                    module.setup(self) # Pass plugin manager for registration
                
                plugin_info.module = module
                plugin_info.is_loaded = True
                self._loaded_plugins[plugin_name] = plugin_info
                
                print(f"Plugin \'{plugin_name}\' loaded successfully.")
                self.hook_system.call("plugin_loaded", plugin_info)
                return plugin_info
                
            except Exception as e:
                plugin_info.is_loaded = False
                plugin_info.errors.append(str(e))
                print(f"Error loading plugin \'{plugin_name}\': {e}")
                return None
            finally:
                # Clean up sys.path if added
                if plugin_path in sys.path:
                    sys.path.remove(plugin_path)
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a specific plugin by name."""
        with self._lock:
            if plugin_name not in self._loaded_plugins:
                print(f"Plugin \'{plugin_name}\' is not loaded.")
                return False
            
            plugin_info = self._loaded_plugins[plugin_name]
            
            try:
                # Call 'teardown' function if exists
                if hasattr(plugin_info.module, "teardown") and callable(plugin_info.module.teardown):
                    plugin_info.module.teardown(self)
                
                # Unregister all extensions and hooks from this plugin
                self.extension_point_manager.unregister_all_from_plugin(plugin_name)
                # TODO: Unregister hooks specifically registered by this plugin
                
                # Remove module from sys.modules
                if plugin_name in sys.modules:
                    del sys.modules[plugin_name]
                
                plugin_info.is_loaded = False
                del self._loaded_plugins[plugin_name]
                
                print(f"Plugin \'{plugin_name}\' unloaded successfully.")
                self.hook_system.call("plugin_unloaded", plugin_info)
                return True
                
            except Exception as e:
                plugin_info.errors.append(str(e))
                print(f"Error unloading plugin \'{plugin_name}\': {e}")
                return False
    
    def reload_plugin(self, plugin_name: str) -> Optional[PluginInfo]:
        """Reload a plugin."""
        with self._lock:
            self.unload_plugin(plugin_name)
            return self.load_plugin(plugin_name)
            
    def cleanup(self) -> None:
        """Unload all loaded plugins and clean up resources."""
        with self._lock:
            for plugin_name in list(self._loaded_plugins.keys()):
                self.unload_plugin(plugin_name)
            self._available_plugins.clear()
            self._plugin_dirs.clear()
            self.extension_point_manager.unregister_all_from_plugin("*") # Clear all
            self.hook_system.clear_all_hooks()


# Global instance of PluginManager
_global_plugin_manager: Optional[PluginManager] = None

def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager instance."""
    global _global_plugin_manager
    if _global_plugin_manager is None:
        # Initialize with default plugin directory (e.g., a 'plugins' folder in the app root)
        default_plugin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins_data")
        os.makedirs(default_plugin_dir, exist_ok=True)
        _global_plugin_manager = PluginManager(plugin_dirs=[default_plugin_dir])
    return _global_plugin_manager


