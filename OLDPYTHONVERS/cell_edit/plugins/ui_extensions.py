"""
Provides mechanisms for plugins to register custom UI components.
This allows plugins to add new toolbars, sidebars, dialogs, and other UI elements.
"""

from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass, field
from enum import Enum

from .extension_points import register_extension, get_extensions, create_extension_point


class UIComponentType(Enum):
    """Types of UI components that can be extended."""
    TOOLBAR_BUTTON = "toolbar_button"
    SIDEBAR_PANEL = "sidebar_panel"
    MENU_ITEM = "menu_item"
    STATUS_BAR_ITEM = "status_bar_item"
    CUSTOM_DIALOG = "custom_dialog"
    CELL_RENDERER = "cell_renderer"
    CELL_EDITOR = "cell_editor"


# Define an extension point for custom UI components
CUSTOM_UI_COMPONENT_EXTENSION_POINT = create_extension_point(
    "custom_ui_components",
    "Allows plugins to register custom UI components."
)


@dataclass
class UIComponentInfo:
    """
    Represents information about a custom UI component provided by a plugin.
    """
    component_id: str
    component_type: UIComponentType
    # The actual UI component class or factory function
    component_factory: Callable[..., Any]
    # Metadata for the component (e.g., icon, label, tooltip)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Optional: Callback to be executed when the component is activated (e.g., button click)
    action_callback: Optional[Callable] = None
    # Optional: Condition to determine if the component should be enabled/visible
    condition_callback: Optional[Callable[[], bool]] = None
    
    def __post_init__(self):
        if not callable(self.component_factory):
            raise ValueError("UI component factory must be a callable.")


class UIExtensionManager:
    """
    Manages the registration and retrieval of custom UI components from plugins.
    """
    
    def __init__(self):
        self._registered_components: Dict[str, UIComponentInfo] = {}

    def register_ui_component(self, plugin_name: str, component_info: UIComponentInfo) -> None:
        """
        Registers a custom UI component from a plugin.
        """
        if not isinstance(component_info, UIComponentInfo):
            raise TypeError("component_info must be an instance of UIComponentInfo")
            
        if component_info.component_id in self._registered_components:
            raise ValueError(f"UI component with ID \'{component_info.component_id}\' already registered.")
            
        self._registered_components[component_info.component_id] = component_info
        
        # Register with the extension point for discovery
        register_extension(
            CUSTOM_UI_COMPONENT_EXTENSION_POINT.name,
            plugin_name,
            component_info.component_id,
            component_info
        )
        print(f"Custom UI component \'{component_info.component_id}\' registered by plugin \'{plugin_name}\".")

    def unregister_ui_component(self, component_id: str) -> None:
        """
        Unregisters a custom UI component.
        """
        if component_id not in self._registered_components:
            print(f"UI component \'{component_id}\' not found.")
            return
            
        CUSTOM_UI_COMPONENT_EXTENSION_POINT.unregister(component_id)
        del self._registered_components[component_id]
        print(f"UI component \'{component_id}\' unregistered.")

    def get_ui_component(self, component_id: str) -> Optional[UIComponentInfo]:
        """
        Retrieves a registered UI component.
        """
        return self._registered_components.get(component_id)

    def get_components_by_type(self, component_type: UIComponentType) -> List[UIComponentInfo]:
        """
        Returns a list of all registered components of a specific type.
        """
        return [
            comp for comp in self._registered_components.values() 
            if comp.component_type == component_type
        ]


# Global instance for UIExtensionManager
_global_ui_extension_manager: Optional[UIExtensionManager] = None

def get_ui_extension_manager() -> UIExtensionManager:
    """
    Returns the global UIExtensionManager instance.
    """
    global _global_ui_extension_manager
    if _global_ui_extension_manager is None:
        _global_ui_extension_manager = UIExtensionManager()
    return _global_ui_extension_manager


