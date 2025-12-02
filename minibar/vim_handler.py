"""
Vim-style command handler for minibar when vim mode is active.
Handles vim command-line commands like :w, :q, :e, etc.
"""

from typing import Dict, Callable, Optional
from PyQt5.QtWidgets import QMessageBox


def _save_file(window):
    """Execute :w command"""
    try:
        window.save_file()
    except Exception as e:
        QMessageBox.warning(window, "Error", f"Failed to save: {e}")


def _quit(window):
    """Execute :q command - close current tab"""
    try:
        tab_widget = window.get_active_tabwidget()
        if tab_widget:
            index = tab_widget.currentIndex()
            if index >= 0:
                window.close_tab(index)
    except Exception:
        pass


def _edit_file(window, file_path: str = None):
    """Execute :e command"""
    if file_path:
        window.open_file_in_editor_tab(file_path)
    else:
        window.open_file()


def _write_quit(window):
    """Execute :wq command - save and close current tab"""
    _save_file(window)
    _quit(window)


def _force_quit(window):
    """Execute :q! command - close current tab without saving"""
    _quit(window)


def _split(window):
    """Execute :split command"""
    window.handle_split_action()


def _vsplit(window):
    """Execute :vsplit command"""
    window.handle_split_action()


def _new_file(window):
    """Execute :new command"""
    window.new_file()


# Vim command registry
VIM_COMMANDS: Dict[str, Callable] = {
    "w": _save_file,
    "write": _save_file,
    "q": _quit,
    "quit": _quit,
    "wq": _write_quit,
    "x": _write_quit,
    "exit": _write_quit,
    "q!": _force_quit,
    "quit!": _force_quit,
    "e": _edit_file,
    "edit": _edit_file,
    "split": _split,
    "sp": _split,
    "vsplit": _vsplit,
    "vs": _vsplit,
    "new": _new_file,
}


def execute_vim_command(window, command_text: str) -> bool:
    """
    Execute a vim-style command.
    Returns True if command was handled, False otherwise.
    """
    if not command_text or not command_text.strip():
        return False
    
    # Remove leading colon if present
    cmd = command_text.strip().lstrip(":")
    
    # Split command and arguments
    parts = cmd.split(None, 1)
    cmd_name = parts[0].lower() if parts else ""
    args = parts[1] if len(parts) > 1 else None
    
    # Handle special commands with arguments
    if cmd_name == "e" or cmd_name == "edit":
        _edit_file(window, args)
        return True
    
    # Handle regular commands
    handler = VIM_COMMANDS.get(cmd_name)
    if handler:
        try:
            handler(window)
            return True
        except Exception as e:
            QMessageBox.warning(window, "Command Error", f"Error executing '{cmd}': {e}")
            return True
    
    return False


def get_vim_help() -> str:
    """Return help text for vim commands."""
    return """Vim Commands:
  :w, :write          Save file
  :q, :quit           Close window
  :wq, :x, :exit      Save and quit
  :q!                 Quit without saving
  :e [file], :edit    Open file
  :split, :sp         Split editor
  :vsplit, :vs        Split editor vertically
  :new                New file
"""

