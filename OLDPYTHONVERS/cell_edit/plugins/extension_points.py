"""
Defines extension points where plugins can register their functionalities.
This allows for a modular and extensible architecture.
"""

import threading
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar
from dataclasses import dataclass, field


T = TypeVar("T")


@dataclass
class Extension:
    """Represents an extension registered at an extension point."""
    plugin_name: str
    extension_id: str
    instance: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExtensionPoint:
    """
    An extension point where plugins can register extensions.
    Provides methods to register, unregister, and retrieve extensions.
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._extensions: List[Extension] = []
        self._lock = threading.RLock()
        
    def register(self, plugin_name: str, extension_id: str, instance: Any, 
                 metadata: Optional[Dict[str, Any]] = None) -> Extension:
        """Register an extension at this extension point."""
        with self._lock:
            if self.get_extension(extension_id):
                raise ValueError(f"Extension with ID \'{extension_id}\' already registered at point \'{self.name}\'")
            
            if metadata is None:
                metadata = {}
            
            extension = Extension(plugin_name, extension_id, instance, metadata)
            self._extensions.append(extension)
            return extension
    
    def unregister(self, extension_id: str) -> bool:
        """Unregister an extension by its ID."""
        with self._lock:
            original_len = len(self._extensions)
            self._extensions = [ext for ext in self._extensions if ext.extension_id != extension_id]
            return len(self._extensions) < original_len
    
    def get_extension(self, extension_id: str) -> Optional[Extension]:
        """Get a specific extension by its ID."""
        with self._lock:
            for ext in self._extensions:
                if ext.extension_id == extension_id:
                    return ext
            return None
    
    def get_extensions(self) -> List[Extension]:
        """Get all registered extensions at this point."""
        with self._lock:
            return list(self._extensions) # Return a copy to prevent external modification
    
    def get_extensions_by_plugin(self, plugin_name: str) -> List[Extension]:
        """Get all extensions registered by a specific plugin."""
        with self._lock:
            return [ext for ext in self._extensions if ext.plugin_name == plugin_name]
    
    def clear(self) -> None:
        """Clear all extensions from this point."""
        with self._lock:
            self._extensions.clear()
    
    def __len__(self) -> int:
        return len(self._extensions)
    
    def __repr__(self) -> str:
        return f"ExtensionPoint(name=\'{self.name}\', extensions={len(self._extensions)})"


class ExtensionPointManager:
    """
    Manages all extension points in the application.
    """
    
    def __init__(self):
        self._extension_points: Dict[str, ExtensionPoint] = {}
        self._lock = threading.RLock()
        
    def create_extension_point(self, name: str, description: str = "") -> ExtensionPoint:
        """Create and register a new extension point."""
        with self._lock:
            if name in self._extension_points:
                raise ValueError(f"Extension point \'{name}\' already exists.")
            ep = ExtensionPoint(name, description)
            self._extension_points[name] = ep
            return ep
    
    def get_extension_point(self, name: str) -> Optional[ExtensionPoint]:
        """Get an existing extension point by name."""
        with self._lock:
            return self._extension_points.get(name)
    
    def register_extension(self, extension_point_name: str, plugin_name: str, 
                           extension_id: str, instance: Any, 
                           metadata: Optional[Dict[str, Any]] = None) -> Extension:
        """Register an extension to a specific extension point."""
        with self._lock:
            ep = self.get_extension_point(extension_point_name)
            if not ep:
                raise ValueError(f"Extension point \'{extension_point_name}\' not found.")
            return ep.register(plugin_name, extension_id, instance, metadata)
    
    def unregister_extension(self, extension_point_name: str, extension_id: str) -> bool:
        """Unregister an extension from a specific extension point."""
        with self._lock:
            ep = self.get_extension_point(extension_point_name)
            if not ep:
                return False
            return ep.unregister(extension_id)
    
    def unregister_all_from_plugin(self, plugin_name: str) -> None:
        """Unregister all extensions registered by a specific plugin."""
        with self._lock:
            for ep in self._extension_points.values():
                ep._extensions = [ext for ext in ep._extensions if ext.plugin_name != plugin_name]
    
    def get_all_extension_points(self) -> List[ExtensionPoint]:
        """Get all registered extension points."""
        with self._lock:
            return list(self._extension_points.values())


# Global instance of ExtensionPointManager
_global_extension_point_manager: Optional[ExtensionPointManager] = None

def get_extension_point_manager() -> ExtensionPointManager:
    """Get the global extension point manager instance."""
    global _global_extension_point_manager
    if _global_extension_point_manager is None:
        _global_extension_point_manager = ExtensionPointManager()
    return _global_extension_point_manager


def register_extension(extension_point_name: str, plugin_name: str, 
                       extension_id: str, instance: Any, 
                       metadata: Optional[Dict[str, Any]] = None) -> Extension:
    """Convenience function to register an extension globally."""
    return get_extension_point_manager().register_extension(
        extension_point_name, plugin_name, extension_id, instance, metadata
    )


def get_extensions(extension_point_name: str) -> List[Extension]:
    """Convenience function to get extensions from a global extension point."""
    ep = get_extension_point_manager().get_extension_point(extension_point_name)
    if ep:
        return ep.get_extensions()
    return []


def create_extension_point(name: str, description: str = "") -> ExtensionPoint:
    """Convenience function to create a global extension point."""
    return get_extension_point_manager().create_extension_point(name, description)


