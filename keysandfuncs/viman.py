"""
Vim-style modal editing helpers for QTextEdit widgets.
"""

from PyQt5.QtCore import QObject, QEvent, Qt
from PyQt5.QtGui import QTextCursor


class VimModeController(QObject):
    def __init__(self):
        super().__init__()
        self._active_editor = None
        self._mode = "normal"  # normal | insert | replace
        self._pending_command = None

    def activate(self, editor):
        if editor is None:
            return
        if self._active_editor is editor:
            self.deactivate()
            return
        self.deactivate()
        self._active_editor = editor
        self._mode = "normal"
        self._pending_command = None
        editor.installEventFilter(self)
        editor.setFocus()
        self._notify_mode_change()

    def deactivate(self):
        was_active = self._active_editor is not None
        if self._active_editor:
            try:
                self._active_editor.removeEventFilter(self)
            except Exception:
                pass
            self._active_editor.setOverwriteMode(False)
        self._active_editor = None
        self._mode = "normal"
        self._pending_command = None
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

    # ------------------------------------------------------------------ Qt hooks
    def eventFilter(self, obj, event):
        if obj is self._active_editor and event.type() == QEvent.KeyPress:
            # Always in normal mode - handle vim commands or allow typing
            key = event.key()
            mods = event.modifiers()
            text = event.text()
            
            # Handle vim commands first
            if self._handle_normal_mode(event):
                return True
            
            # Check if this is a printable character that should allow typing
            # Allow typing if it's a normal character and not a vim command
            if text and text.isprintable() and not mods & (Qt.ControlModifier | Qt.AltModifier):
                # Allow normal text input - don't consume it
                return False
            
            # Consume all other keys
            return True
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------ modes
    def _enter_normal_mode(self):
        self._mode = "normal"
        self._pending_command = None
        if self._active_editor:
            self._active_editor.setOverwriteMode(False)

    def _enter_insert_mode(self):
        self._mode = "insert"
        if self._active_editor:
            self._active_editor.setOverwriteMode(False)

    def _enter_replace_mode(self):
        self._mode = "replace"
        if self._active_editor:
            self._active_editor.setOverwriteMode(True)

    # ------------------------------------------------------------------ helpers
    def _cursor(self):
        return QTextCursor(self._active_editor.textCursor())

    def _set_cursor(self, cursor):
        self._active_editor.setTextCursor(cursor)

    def _page_step(self):
        editor = self._active_editor
        if not editor:
            return 20
        metrics = editor.fontMetrics()
        spacing = metrics.lineSpacing() or 18
        return max(1, int(editor.viewport().height() / spacing) - 1)

    def _first_non_blank_offset(self, block_text):
        return len(block_text) - len(block_text.lstrip())

    # movement helpers -------------------------------------------------
    def _move_cursor(self, move_type, repeat=1):
        cursor = self._cursor()
        for _ in range(max(1, repeat)):
            cursor.movePosition(move_type)
        self._set_cursor(cursor)

    def _move_to_line_start(self, non_blank=False):
        cursor = self._cursor()
        cursor.movePosition(QTextCursor.StartOfLine)
        if non_blank:
            text = cursor.block().text()
            offset = self._first_non_blank_offset(text)
            cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, offset)
        self._set_cursor(cursor)

    def _move_to_line_end(self):
        cursor = self._cursor()
        cursor.movePosition(QTextCursor.EndOfLine)
        self._set_cursor(cursor)

    def _move_word(self, direction="next"):
        cursor = self._cursor()
        move = {
            "next": QTextCursor.NextWord,
            "prev": QTextCursor.PreviousWord,
            "end": QTextCursor.EndOfWord,
        }[direction]
        cursor.movePosition(move)
        self._set_cursor(cursor)

    def _page_move(self, direction=1):
        cursor = self._cursor()
        cursor.movePosition(
            QTextCursor.Down if direction > 0 else QTextCursor.Up,
            QTextCursor.MoveAnchor,
            self._page_step(),
        )
        self._set_cursor(cursor)

    def _move_to_document_start(self):
        cursor = self._cursor()
        cursor.movePosition(QTextCursor.Start)
        self._set_cursor(cursor)

    def _move_to_document_end(self):
        cursor = self._cursor()
        cursor.movePosition(QTextCursor.End)
        self._set_cursor(cursor)

    # deletion helpers -------------------------------------------------
    def _delete_cursor(self, cursor, enter_insert=False):
        if cursor and cursor.hasSelection():
            cursor.removeSelectedText()
            self._set_cursor(cursor)
            if enter_insert:
                self._enter_insert_mode()
            return True
        return False

    def _delete_line(self, enter_insert=False):
        cursor = self._cursor()
        cursor.select(QTextCursor.LineUnderCursor)
        return self._delete_cursor(cursor, enter_insert)

    def _delete_word(self, enter_insert=False):
        cursor = self._cursor()
        cursor.movePosition(QTextCursor.NextWord, QTextCursor.KeepAnchor)
        return self._delete_cursor(cursor, enter_insert)

    def _delete_to_line_end(self, enter_insert=False):
        cursor = self._cursor()
        cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
        return self._delete_cursor(cursor, enter_insert)

    def _delete_to_line_start(self, non_blank=False, enter_insert=False):
        cursor = self._cursor()
        original = cursor.position()
        cursor.setPosition(original)
        cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.MoveAnchor)
        start = cursor.position()
        if non_blank:
            start += self._first_non_blank_offset(cursor.block().text())
        cursor.setPosition(original)
        cursor.setPosition(start, QTextCursor.KeepAnchor)
        return self._delete_cursor(cursor, enter_insert)

    def _delete_to_document_end(self, enter_insert=False):
        cursor = self._cursor()
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        return self._delete_cursor(cursor, enter_insert)

    def _delete_until_char(self, ch, enter_insert=False):
        cursor = self._cursor()
        start = cursor.position()
        target = self._active_editor.document().find(ch, cursor)
        if target.isNull():
            return False
        cursor.setPosition(start)
        cursor.setPosition(target.position(), QTextCursor.KeepAnchor)
        return self._delete_cursor(cursor, enter_insert)

    def _delete_char_under(self, enter_insert=False):
        cursor = self._cursor()
        if cursor.atEnd():
            return False
        cursor.deleteChar()
        self._set_cursor(cursor)
        if enter_insert:
            self._enter_insert_mode()
        return True

    def _delete_char_before(self):
        cursor = self._cursor()
        cursor.deletePreviousChar()
        self._set_cursor(cursor)

    def _open_line(self, below=True):
        cursor = self._cursor()
        if below:
            cursor.movePosition(QTextCursor.EndOfBlock)
            cursor.insertBlock()
        else:
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.insertBlock()
            cursor.movePosition(QTextCursor.PreviousBlock)
        self._set_cursor(cursor)
        self._enter_insert_mode()

    def _replace_char(self, ch):
        if not ch:
            return
        cursor = self._cursor()
        cursor.deleteChar()
        cursor.insertText(ch)
        self._set_cursor(cursor)

    # ------------------------------------------------------------------ main handler
    def _handle_normal_mode(self, event):
        key = event.key()
        mods = event.modifiers()
        text = event.text()

        # Pending sequences ------------------------------------------------
        if self._pending_command == "g":
            if key == Qt.Key_G:
                self._move_to_document_start()
                self._pending_command = None
                return True
            self._pending_command = None
        elif self._pending_command == "d":
            handled = self._handle_operator_sequence("delete", key, text)
            self._pending_command = None
            if handled:
                return True
        elif self._pending_command == "c":
            handled = self._handle_operator_sequence("change", key, text)
            self._pending_command = None
            if handled:
                return True
        elif self._pending_command == "dt":
            self._pending_command = None
            if text:
                return self._delete_until_char(text, enter_insert=False)
            return True
        elif self._pending_command == "ct":
            self._pending_command = None
            if text:
                handled = self._delete_until_char(text, enter_insert=True)
                if handled:
                    self._enter_insert_mode()
                return handled
            return True
        elif self._pending_command == "r":
            self._pending_command = None
            if text:
                self._replace_char(text)
            return True

        # Ctrl paging ------------------------------------------------------
        if mods & Qt.ControlModifier:
            if key == Qt.Key_F:
                self._page_move(direction=1)
                return True
            if key == Qt.Key_B:
                self._page_move(direction=-1)
                return True

        # Movement ---------------------------------------------------------
        if text == "h":
            self._move_cursor(QTextCursor.Left)
            return True
        if text == "j":
            self._move_cursor(QTextCursor.Down)
            return True
        if text == "k":
            self._move_cursor(QTextCursor.Up)
            return True
        if text == "l":
            self._move_cursor(QTextCursor.Right)
            return True
        if text == "w":
            self._move_word("next")
            return True
        if text == "b":
            self._move_word("prev")
            return True
        if text == "e":
            self._move_word("end")
            return True
        if text == "0":
            self._move_to_line_start(False)
            return True
        if text == "^":
            self._move_to_line_start(True)
            return True
        if text == "$":
            self._move_to_line_end()
            return True
        if text == "g":
            self._pending_command = "g"
            return True
        if text == "G":
            self._move_to_document_end()
            return True
        if text == "i":
            # Allow typing - don't block it
            return False
        if text == "I":
            self._move_to_line_start(True)
            # Allow typing after moving
            return False
        if text == "a":
            self._move_cursor(QTextCursor.Right)
            # Allow typing after moving
            return False
        if text == "A":
            self._move_to_line_end()
            # Allow typing after moving
            return False
        if text == "o":
            self._open_line(below=True)
            # Allow typing after opening line
            return False
        if text == "O":
            self._open_line(below=False)
            # Allow typing after opening line
            return False
        if text == "r":
            self._pending_command = "r"
            return True
        if text == "R":
            # Enter overwrite mode but don't track as special mode
            if self._active_editor:
                self._active_editor.setOverwriteMode(True)
            return False
        if text == "s":
            self._delete_char_under(enter_insert=False)
            # Allow typing after deleting
            return False
        if text == "S":
            self._delete_line(enter_insert=False)
            # Allow typing after deleting
            return False
        if text == "x":
            self._delete_char_under()
            return True
        if text == "X":
            self._delete_char_before()
            return True
        if text == "d":
            self._pending_command = "d"
            return True
        if text == "c":
            self._pending_command = "c"
            return True
        if text == "C":
            self._delete_to_line_end(enter_insert=True)
            self._enter_insert_mode()
            return True
        if text == "D":
            self._delete_to_line_end()
            return True

        if key == Qt.Key_Escape:
            self.deactivate()
            return True
        
        # Handle : to open minibar in vim mode
        if key == Qt.Key_Colon and not (mods & (Qt.ControlModifier | Qt.AltModifier)):
            self._open_minibar()
            return True

        return False
    
    def _open_minibar(self):
        """Open minibar and focus it with : prefilled."""
        try:
            # Find the main window
            editor = self._active_editor
            if not editor:
                return
            window = editor.window()
            if not window or not hasattr(window, 'show_minibar'):
                return
            # Show minibar
            window.show_minibar()
            # Prefill with :
            if hasattr(window, '_minibar') and window._minibar:
                window._minibar.input.setText(":")
                window._minibar.input.setCursorPosition(1)
                window._minibar.input.setFocus()
        except Exception:
            pass

    # ------------------------------------------------------------------ operators
    def _handle_operator_sequence(self, operator, key, text):
        enter_insert = operator == "change"
        lower = text.lower()
        if lower == "d":
            handled = self._delete_line(enter_insert)
        elif lower == "w":
            handled = self._delete_word(enter_insert)
        elif lower == "b":
            cursor = self._cursor()
            cursor.movePosition(QTextCursor.PreviousWord, QTextCursor.KeepAnchor)
            handled = self._delete_cursor(cursor, enter_insert)
        elif lower == "e":
            cursor = self._cursor()
            cursor.movePosition(QTextCursor.EndOfWord, QTextCursor.KeepAnchor)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
            handled = self._delete_cursor(cursor, enter_insert)
        elif text == "$" or text == "D":
            handled = self._delete_to_line_end(enter_insert)
        elif text == "^":
            handled = self._delete_to_line_start(True, enter_insert)
        elif text == "0":
            handled = self._delete_to_line_start(False, enter_insert)
        elif text == "G":
            handled = self._delete_to_document_end(enter_insert)
        elif lower == "t":
            self._pending_command = "ct" if operator == "change" else "dt"
            return True
        else:
            handled = False

        if handled and enter_insert:
            self._enter_insert_mode()
        return handled


VIM_MODE = VimModeController()


def activate_vim_mode(editor):
    VIM_MODE.activate(editor)


def is_vim_mode_active(editor):
    """Check if vim mode is active for the given editor."""
    return VIM_MODE._active_editor is editor if editor else False


def get_vim_mode(editor):
    """Get the vim submode (normal/insert/replace) for the given editor."""
    if is_vim_mode_active(editor):
        return VIM_MODE._mode
    return None

