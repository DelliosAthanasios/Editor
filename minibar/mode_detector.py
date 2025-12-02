"""
Mode detection for determining which editing mode is currently active.
"""

from typing import Optional, Tuple
from PyQt5.QtWidgets import QTextEdit


def get_editor_mode(editor: Optional[QTextEdit]) -> str:
    """
    Detect the current editing mode for an editor.
    Returns: 'vim', 'emacs', or 'normal'
    """
    if editor is None:
        return "normal"
    
    # Check vim mode first (takes precedence)
    try:
        from keysandfuncs.viman import is_vim_mode_active
        if is_vim_mode_active(editor):
            return "vim"
    except Exception:
        pass
    
    # Check emacs mode
    try:
        from keysandfuncs.eman import is_emacs_mode_active
        if is_emacs_mode_active(editor):
            return "emacs"
    except Exception:
        pass
    
    return "normal"


def get_vim_submode(editor: Optional[QTextEdit]) -> Optional[str]:
    """
    Get the vim submode (normal, insert, replace) if vim mode is active.
    Returns: 'normal', 'insert', 'replace', or None
    """
    if editor is None:
        return None
    
    try:
        from keysandfuncs.viman import get_vim_mode
        return get_vim_mode(editor)
    except Exception:
        pass
    
    return None


def get_current_editor(window) -> Optional[QTextEdit]:
    """
    Get the currently active QTextEdit from the main window.
    """
    try:
        tab_widget = window.get_active_tabwidget()
        if not tab_widget:
            return None
        current_tab = tab_widget.currentWidget()
        if not current_tab:
            return None
        if hasattr(current_tab, "editor"):
            return current_tab.editor
    except Exception:
        pass
    return None

