"""
Plugin system and extensibility framework for the Cell Editor.
Enables dynamic loading of extensions, custom functions, and UI components.
"""

from plugins.plugin_manager import PluginManager, PluginInfo
from plugins.extension_points import ExtensionPoint, register_extension, get_extensions
from plugins.hook_system import HookSystem, register_hook, call_hook

__all__ = [
    'PluginManager', 'PluginInfo',
    'ExtensionPoint', 'register_extension', 'get_extensions',
    'HookSystem', 'register_hook', 'call_hook'
]

