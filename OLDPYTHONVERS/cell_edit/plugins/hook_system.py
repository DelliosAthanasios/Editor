"""
Implements a robust hook system for plugins to interact with the core application.
Plugins can register functions to be called at specific points (hooks) in the application lifecycle.
"""

import threading
from typing import Any, Callable, Dict, List, Optional, Tuple


class HookSystem:
    """
    A centralized system for managing and calling hooks.
    Hooks allow plugins to inject custom logic at predefined points in the application.
    """
    
    def __init__(self):
        self._hooks: Dict[str, List[Tuple[Callable, int]]] = {}
        self._lock = threading.RLock()
        
    def register(self, hook_name: str, callback: Callable, priority: int = 10) -> None:
        """Register a callback function to a specific hook.
        
        Args:
            hook_name (str): The name of the hook.
            callback (Callable): The function to be called when the hook is triggered.
            priority (int): The execution priority of the callback. Lower numbers run first.
        """
        with self._lock:
            if hook_name not in self._hooks:
                self._hooks[hook_name] = []
            
            # Add callback with its priority
            self._hooks[hook_name].append((callback, priority))
            # Sort by priority (lower number = higher priority)
            self._hooks[hook_name].sort(key=lambda x: x[1])
            
    def unregister(self, hook_name: str, callback: Callable) -> bool:
        """Unregister a callback function from a hook.
        
        Args:
            hook_name (str): The name of the hook.
            callback (Callable): The function to unregister.
            
        Returns:
            bool: True if the callback was unregistered, False otherwise.
        """
        with self._lock:
            if hook_name not in self._hooks:
                return False
            
            original_len = len(self._hooks[hook_name])
            self._hooks[hook_name] = [item for item in self._hooks[hook_name] if item[0] != callback]
            return len(self._hooks[hook_name]) < original_len
            
    def call(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Call all registered callbacks for a given hook.
        
        Args:
            hook_name (str): The name of the hook to call.
            *args: Positional arguments to pass to the callbacks.
            **kwargs: Keyword arguments to pass to the callbacks.
            
        Returns:
            List[Any]: A list of results from each callback function.
        """
        results = []
        with self._lock:
            callbacks = self._hooks.get(hook_name, [])
            
            for callback, _ in callbacks:
                try:
                    result = callback(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    # Log the error, but don't stop other hooks from running
                    print(f"Error calling hook \'{hook_name}\' callback {callback.__name__}: {e}")
                    results.append(None) # Or raise a specific exception, depending on desired behavior
        return results
    
    def has_hook(self, hook_name: str) -> bool:
        """Check if a hook has any registered callbacks."""
        with self._lock:
            return hook_name in self._hooks and len(self._hooks[hook_name]) > 0
            
    def get_registered_callbacks(self, hook_name: str) -> List[Callable]:
        """Get a list of all registered callback functions for a hook (without priority)."""
        with self._lock:
            return [item[0] for item in self._hooks.get(hook_name, [])]
            
    def clear_hook(self, hook_name: str) -> None:
        """Clear all callbacks from a specific hook."""
        with self._lock:
            if hook_name in self._hooks:
                del self._hooks[hook_name]
                
    def clear_all_hooks(self) -> None:
        """Clear all hooks and their callbacks."""
        with self._lock:
            self._hooks.clear()


# Global instance of HookSystem
_global_hook_system: Optional[HookSystem] = None

def get_hook_system() -> HookSystem:
    """Get the global hook system instance."""
    global _global_hook_system
    if _global_hook_system is None:
        _global_hook_system = HookSystem()
    return _global_hook_system


def register_hook(hook_name: str, callback: Callable, priority: int = 10) -> None:
    """Convenience function to register a hook globally."""
    get_hook_system().register(hook_name, callback, priority)


def call_hook(hook_name: str, *args, **kwargs) -> List[Any]:
    """Convenience function to call a hook globally."""
    return get_hook_system().call(hook_name, *args, **kwargs)


