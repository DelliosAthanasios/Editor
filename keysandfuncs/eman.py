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

    def deactivate(self):
        if self._active_editor:
            try:
                self._active_editor.removeEventFilter(self)
            except Exception:
                pass
        self._active_editor = None

    def eventFilter(self, obj, event):
        if obj is self._active_editor and event.type() == QEvent.KeyPress:
            if self._handle_key(event):
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

