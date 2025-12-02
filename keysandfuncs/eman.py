"""
Simple Emacs-inspired text manipulation helpers activated on demand.
"""

from PyQt5.QtCore import QObject, QEvent, Qt
from PyQt5.QtGui import QTextCursor


class EmacsModeController(QObject):
    def __init__(self):
        super().__init__()
        self._active_editor = None

    def activate(self, editor):
        if editor is None:
            return
        if self._active_editor is editor:
            self.deactivate()
            return
        self.deactivate()
        self._active_editor = editor
        editor.installEventFilter(self)
        self._notify_mode_change()

    def deactivate(self):
        was_active = self._active_editor is not None
        if self._active_editor:
            try:
                self._active_editor.removeEventFilter(self)
            except Exception:
                pass
        self._active_editor = None
        if was_active:
            self._notify_mode_change()
    
    def _notify_mode_change(self):
        """Notify keybind manager to update shortcut states."""
        try:
            from .keybinds import _WINDOW_MANAGERS
            for window, manager in _WINDOW_MANAGERS.items():
                if hasattr(manager, 'update_shortcut_state'):
                    manager.update_shortcut_state()
        except Exception:
            pass

    def eventFilter(self, obj, event):
        if obj is self._active_editor and event.type() == QEvent.KeyPress:
            # Handle Emacs commands or escape
            if self._handle_key(event):
                return True
            # All other keys are consumed/ignored in Emacs mode
            return True
        return super().eventFilter(obj, event)

    def _handle_key(self, event):
        key = event.key()
        mods = event.modifiers()
        if mods & Qt.ControlModifier:
            if key == Qt.Key_F:
                self._move(QTextCursor.Right)
                return True
            if key == Qt.Key_B:
                self._move(QTextCursor.Left)
                return True
            if key == Qt.Key_N:
                self._move(QTextCursor.Down)
                return True
            if key == Qt.Key_P:
                self._move(QTextCursor.Up)
                return True
            if key == Qt.Key_K:
                self._kill_line()
                return True
            if key == Qt.Key_G:
                self.deactivate()
                return True
        elif key == Qt.Key_Escape:
            self.deactivate()
            return True
        # Key not handled - will be consumed by eventFilter
        return False

    def _move(self, move_type):
        if not self._active_editor:
            return
        cursor = self._active_editor.textCursor()
        cursor.movePosition(move_type)
        self._active_editor.setTextCursor(cursor)

    def _kill_line(self):
        if not self._active_editor:
            return
        cursor = self._active_editor.textCursor()
        cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        self._active_editor.setTextCursor(cursor)


EMACS_MODE = EmacsModeController()


def activate_emacs_mode(editor):
    EMACS_MODE.activate(editor)


def is_emacs_mode_active(editor):
    """Check if emacs mode is active for the given editor."""
    return EMACS_MODE._active_editor is editor if editor else False

