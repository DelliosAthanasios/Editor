"""
Emacs-style command handler for minibar when emacs mode is active.
Handles emacs key sequences like C-x C-f, C-x C-s, etc.
"""

from typing import Callable, Dict
from keysandfuncs.keybinds import ACTION_BLUEPRINTS


def _action_lookup() -> Dict[str, Callable]:
    """Create a lookup table from action IDs to handlers."""
    lookup = {}
    for blueprint in ACTION_BLUEPRINTS:
        lookup[blueprint["id"]] = blueprint["handler"]
    return lookup


_HANDLERS = _action_lookup()


def _cmd(action_id: str, description: str):
    """Create a command wrapper for an action."""
    handler = _HANDLERS.get(action_id)

    def _runner(window):
        if handler and window is not None:
            handler(window)

    return {"description": description, "func": _runner}


# Emacs command registry - integrated from emacscommsbar
EMACS_COMMANDS = {
    "C-x C-f": _cmd("open_file", "Open file"),
    "C-x C-s": _cmd("save_file", "Save file"),
    "C-x C-n": _cmd("new_tab", "New tab"),
    "C-x C-b": _cmd("toggle_file_tree", "Toggle file tree"),
    "C-x b": _cmd("toggle_file_tree", "Toggle file tree"),
    "C-x k": _cmd("close_current_tab", "Close current tab"),
    "C-x 1": _cmd("toggle_tab_bar", "Toggle tab bar visibility"),
    "C-x 2": _cmd("split_editor", "Split editor"),
    "C-x 3": _cmd("split_editor", "Split editor"),
    "C-x 0": _cmd("close_current_tab", "Close current tab"),
    "C-x C-g": _cmd("open_code_explorer", "Enable code explorer"),
    "C-x m": _cmd("toggle_console", "Toggle console panel"),
    "C-x C-m": _cmd("toggle_console", "Toggle console panel"),
    "C-x C-d": _cmd("open_diagram", "Open diagram sketch"),
    "C-x C-l": _cmd("open_latex", "Open LaTeX editor"),
    "C-x C-p": _cmd("open_process_manager", "Open process manager"),
    "C-x C-t": _cmd("toggle_tab_bar", "Toggle tab bar"),
    "C-x C-e": _cmd("open_code_explorer", "Open code explorer"),
    "C-x C-r": _cmd("toggle_numberline", "Toggle number line"),
    "C-x C-m m": _cmd("toggle_minimap", "Toggle minimap"),
    "C-x C-space": _cmd("open_minibar", "Show minibar"),
}


def execute_emacs_command(window, command_text: str) -> bool:
    """
    Execute an emacs-style command sequence.
    Returns True if command was handled, False otherwise.
    """
    if not command_text:
        return False
    
    cmd = command_text.strip()
    
    # Check if command exists
    if cmd in EMACS_COMMANDS:
        try:
            EMACS_COMMANDS[cmd]["func"](window)
            return True
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(window, "Command Error", f"Error executing '{cmd}': {e}")
            return True
    
    return False


def get_emacs_help() -> str:
    """Return help text for emacs commands."""
    help_lines = ["Emacs Commands:"]
    for cmd, info in sorted(EMACS_COMMANDS.items()):
        help_lines.append(f"  {cmd:<15} {info['description']}")
    return "\n".join(help_lines)

