"""
Command Dictionary - lists all vim and emacs commands available in the editor.
"""

from typing import List, Dict
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QTabWidget, QLabel

from .viman import VIM_MODE
from .eman import EMACS_MODE


def get_vim_commands() -> List[Dict[str, str]]:
    """Get list of all vim commands."""
    return [
        {"key": "h", "description": "Move left"},
        {"key": "j", "description": "Move down"},
        {"key": "k", "description": "Move up"},
        {"key": "l", "description": "Move right"},
        {"key": "w", "description": "Jump to next word"},
        {"key": "b", "description": "Jump backward to word"},
        {"key": "e", "description": "Jump to end of word"},
        {"key": "0", "description": "Beginning of line"},
        {"key": "^", "description": "First non-blank character of line"},
        {"key": "$", "description": "End of line"},
        {"key": "gg", "description": "Go to first line of file"},
        {"key": "G", "description": "Go to last line of file"},
        {"key": "Ctrl+f", "description": "Page down"},
        {"key": "Ctrl+b", "description": "Page up"},
        {"key": "i", "description": "Insert before cursor"},
        {"key": "I", "description": "Insert at beginning of line"},
        {"key": "a", "description": "Append after cursor"},
        {"key": "A", "description": "Append at end of line"},
        {"key": "o", "description": "Open new line below"},
        {"key": "O", "description": "Open new line above"},
        {"key": "r", "description": "Replace single character"},
        {"key": "R", "description": "Replace multiple characters (overwrite mode)"},
        {"key": "c", "description": "Change (delete and enter insert mode)"},
        {"key": "C", "description": "Change to end of line"},
        {"key": "s", "description": "Substitute character (delete and insert)"},
        {"key": "S", "description": "Substitute entire line"},
        {"key": "x", "description": "Delete character under cursor"},
        {"key": "X", "description": "Delete character before cursor"},
        {"key": "dd", "description": "Delete current line"},
        {"key": "dw", "description": "Delete word"},
        {"key": "d$ or D", "description": "Delete to end of line"},
        {"key": "d^", "description": "Delete to beginning of line"},
        {"key": "dt<char>", "description": "Delete until character"},
        {"key": "dG", "description": "Delete to end of file"},
        {"key": "Esc", "description": "Exit insert/replace mode, return to normal mode"},
        {"key": "Ctrl+Shift+V", "description": "Toggle Vim mode"},
    ]


def get_vim_commandline_commands() -> List[Dict[str, str]]:
    """Get list of vim command-line commands (minibar)."""
    return [
        {"key": ":w", "description": "Save file"},
        {"key": ":write", "description": "Save file"},
        {"key": ":q", "description": "Close tab"},
        {"key": ":quit", "description": "Close tab"},
        {"key": ":wq", "description": "Save and close tab"},
        {"key": ":x", "description": "Save and close tab"},
        {"key": ":exit", "description": "Save and close tab"},
        {"key": ":q!", "description": "Close tab without saving"},
        {"key": ":e [file]", "description": "Open file"},
        {"key": ":edit [file]", "description": "Open file"},
        {"key": ":split", "description": "Split editor"},
        {"key": ":sp", "description": "Split editor"},
        {"key": ":vsplit", "description": "Split editor vertically"},
        {"key": ":vs", "description": "Split editor vertically"},
        {"key": ":new", "description": "New file"},
        {"key": ":help", "description": "Show help"},
    ]


def get_emacs_commands() -> List[Dict[str, str]]:
    """Get list of all emacs commands."""
    return [
        {"key": "Ctrl+F", "description": "Move forward (right)"},
        {"key": "Ctrl+B", "description": "Move backward (left)"},
        {"key": "Ctrl+N", "description": "Move to next line (down)"},
        {"key": "Ctrl+P", "description": "Move to previous line (up)"},
        {"key": "Ctrl+K", "description": "Kill line (delete to end)"},
        {"key": "Ctrl+G", "description": "Exit Emacs mode"},
        {"key": "Esc", "description": "Exit Emacs mode"},
        {"key": "Ctrl+Alt+E", "description": "Toggle Emacs mode"},
    ]


def get_emacs_keybind_commands() -> List[Dict[str, str]]:
    """Get list of emacs keybind commands (minibar)."""
    return [
        {"key": "C-x C-f", "description": "Open file"},
        {"key": "C-x C-s", "description": "Save file"},
        {"key": "C-x C-n", "description": "New tab"},
        {"key": "C-x C-b", "description": "Toggle file tree"},
        {"key": "C-x b", "description": "Toggle file tree"},
        {"key": "C-x k", "description": "Close current tab"},
        {"key": "C-x 1", "description": "Toggle tab bar visibility"},
        {"key": "C-x 2", "description": "Split editor"},
        {"key": "C-x 3", "description": "Split editor"},
        {"key": "C-x 0", "description": "Close current tab"},
        {"key": "C-x C-g", "description": "Enable code explorer"},
        {"key": "C-x m", "description": "Toggle console panel"},
        {"key": "C-x C-m", "description": "Toggle console panel"},
        {"key": "C-x C-d", "description": "Open diagram sketch"},
        {"key": "C-x C-l", "description": "Open LaTeX editor"},
        {"key": "C-x C-p", "description": "Open process manager"},
        {"key": "C-x C-t", "description": "Toggle tab bar"},
        {"key": "C-x C-e", "description": "Open code explorer"},
        {"key": "C-x C-r", "description": "Toggle number line"},
        {"key": "C-x C-m m", "description": "Toggle minimap"},
        {"key": "C-x C-space", "description": "Show minibar"},
    ]


class CommandDictionaryWidget(QWidget):
    """Widget showing all available vim and emacs commands as a tab."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        tabs = QTabWidget(self)
        
        # Vim commands tab
        vim_widget = QWidget()
        vim_layout = QVBoxLayout(vim_widget)
        vim_label = QLabel("Vim Navigation & Editing Commands:")
        vim_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
        vim_layout.addWidget(vim_label)
        vim_text = QTextEdit()
        vim_text.setReadOnly(True)
        vim_text.setFontFamily("Consolas")
        vim_text.setPlainText(self._format_commands(get_vim_commands()))
        vim_layout.addWidget(vim_text)
        tabs.addTab(vim_widget, "Vim Commands")
        
        # Vim command-line tab
        vim_cmd_widget = QWidget()
        vim_cmd_layout = QVBoxLayout(vim_cmd_widget)
        vim_cmd_label = QLabel("Vim Command-Line (Minibar) Commands:")
        vim_cmd_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
        vim_cmd_layout.addWidget(vim_cmd_label)
        vim_cmd_text = QTextEdit()
        vim_cmd_text.setReadOnly(True)
        vim_cmd_text.setFontFamily("Consolas")
        vim_cmd_text.setPlainText(self._format_commands(get_vim_commandline_commands()))
        vim_cmd_layout.addWidget(vim_cmd_text)
        tabs.addTab(vim_cmd_widget, "Vim Command-Line")
        
        # Emacs commands tab
        emacs_widget = QWidget()
        emacs_layout = QVBoxLayout(emacs_widget)
        emacs_label = QLabel("Emacs Navigation Commands:")
        emacs_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
        emacs_layout.addWidget(emacs_label)
        emacs_text = QTextEdit()
        emacs_text.setReadOnly(True)
        emacs_text.setFontFamily("Consolas")
        emacs_text.setPlainText(self._format_commands(get_emacs_commands()))
        emacs_layout.addWidget(emacs_text)
        tabs.addTab(emacs_widget, "Emacs Commands")
        
        # Emacs keybind commands tab
        emacs_kb_widget = QWidget()
        emacs_kb_layout = QVBoxLayout(emacs_kb_widget)
        emacs_kb_label = QLabel("Emacs Keybind (Minibar) Commands:")
        emacs_kb_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
        emacs_kb_layout.addWidget(emacs_kb_label)
        emacs_kb_text = QTextEdit()
        emacs_kb_text.setReadOnly(True)
        emacs_kb_text.setFontFamily("Consolas")
        emacs_kb_text.setPlainText(self._format_commands(get_emacs_keybind_commands()))
        emacs_kb_layout.addWidget(emacs_kb_text)
        tabs.addTab(emacs_kb_widget, "Emacs Keybinds")
        
        layout.addWidget(tabs)
    
    def _format_commands(self, commands: List[Dict[str, str]]) -> str:
        """Format command list for display."""
        lines = []
        max_key_len = max(len(cmd["key"]) for cmd in commands) if commands else 0
        for cmd in commands:
            key = cmd["key"].ljust(max_key_len + 2)
            desc = cmd["description"]
            lines.append(f"{key}  {desc}")
        return "\n".join(lines)


def show_command_dictionary(window):
    """Show the command dictionary as a tab."""
    from .keybind_editor import KeybindEditorWidget
    tab_widget = window.get_active_tabwidget()
    if tab_widget is None:
        return
    
    # Check if already open
    for idx in range(tab_widget.count()):
        widget = tab_widget.widget(idx)
        if isinstance(widget, CommandDictionaryWidget):
            tab_widget.setCurrentIndex(idx)
            return
    
    # Create and add new tab
    dict_widget = CommandDictionaryWidget(tab_widget)
    index = tab_widget.addTab(dict_widget, "Command Dictionary")
    tab_widget.setCurrentIndex(index)

