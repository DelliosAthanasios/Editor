"""
Provides mechanisms for plugins to register custom themes and styling options.
This allows for a highly customizable visual appearance of the Cell Editor.
"""

from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass, field
from enum import Enum

from .extension_points import register_extension, get_extensions, create_extension_point


class ThemeType(Enum):
    """Types of themes."""
    LIGHT = "light"
    DARK = "dark"
    HIGH_CONTRAST = "high_contrast"
    CUSTOM = "custom"


# Define an extension point for custom themes
CUSTOM_THEME_EXTENSION_POINT = create_extension_point(
    "custom_themes",
    "Allows plugins to register custom themes and styling options."
)


@dataclass
class ThemeInfo:
    """
    Represents information about a custom theme provided by a plugin.
    """
    theme_id: str
    display_name: str
    theme_type: ThemeType
    # A dictionary defining the color palette, fonts, etc.
    styles: Dict[str, Any]
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class ThemeExtensionManager:
    """
    Manages the registration and retrieval of custom themes from plugins.
    """
    
    def __init__(self):
        self._registered_themes: Dict[str, ThemeInfo] = {}

    def register_theme(self, plugin_name: str, theme_info: ThemeInfo) -> None:
        """
        Registers a custom theme from a plugin.
        """
        if not isinstance(theme_info, ThemeInfo):
            raise TypeError("theme_info must be an instance of ThemeInfo")
            
        if theme_info.theme_id in self._registered_themes:
            raise ValueError(f"Theme with ID \'{theme_info.theme_id}\' already registered.")
            
        self._registered_themes[theme_info.theme_id] = theme_info
        
        # Register with the extension point for discovery
        register_extension(
            CUSTOM_THEME_EXTENSION_POINT.name,
            plugin_name,
            theme_info.theme_id,
            theme_info
        )
        print(f"Custom theme \'{theme_info.theme_id}\' registered by plugin \'{plugin_name}\'")

    def unregister_theme(self, theme_id: str) -> None:
        """
        Unregisters a custom theme.
        """
        if theme_id not in self._registered_themes:
            print(f"Theme \'{theme_id}\' not found.")
            return
            
        CUSTOM_THEME_EXTENSION_POINT.unregister(theme_id)
        del self._registered_themes[theme_id]
        print(f"Theme \'{theme_id}\' unregistered.")

    def get_theme(self, theme_id: str) -> Optional[ThemeInfo]:
        """
        Retrieves a registered theme by its ID.
        """
        return self._registered_themes.get(theme_id)

    def get_all_themes(self) -> List[ThemeInfo]:
        """
        Returns a list of all registered themes.
        """
        return list(self._registered_themes.values())


# Global instance for ThemeExtensionManager
_global_theme_extension_manager: Optional[ThemeExtensionManager] = None

def get_theme_extension_manager() -> ThemeExtensionManager:
    """
    Returns the global ThemeExtensionManager instance.
    """
    global _global_theme_extension_manager
    if _global_theme_extension_manager is None:
        _global_theme_extension_manager = ThemeExtensionManager()
    return _global_theme_extension_manager


