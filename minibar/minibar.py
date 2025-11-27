import sys
import os
import json
from PyQt5.QtWidgets import (QWidget, QLineEdit, QVBoxLayout, QLabel, QApplication, QMessageBox)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QFont, QKeySequence
from keysandfuncs.emacscommsbar import emacs_commands

class Minibar(QWidget):
    """
    Emacs-like minibuffer:
    - docks to bottom of parent
    - accepts Emacs-style key sequences (C-x prefix supported)
    - saves every submitted minibuffer string to mibdata.json during the session
    - clears mibdata.json on application quit
    - supports Up/Down history navigation for entered commands during the session
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedHeight(48)
        self.setStyleSheet("background-color: #23232a; color: #fff; border: none;")
        self.key_sequence = []  # list of tokens like ["C-x", "C-f"]
        self.history = []
        self.history_index = -1
        # mibdata.json path inside the minibar package folder
        self.mibdata_path = os.path.join(os.path.dirname(__file__), "mibdata.json")
        # ensure file exists and start a fresh session file
        self._write_mibdata([])

        self.init_ui()

        # Connect to application quit to clear mibdata.json
        app = QApplication.instance()
        if app:
            try:
                app.aboutToQuit.connect(self.clear_mibdata)
            except Exception:
                # if connection fails, ignore; clearing will still happen if explicitly called
                pass

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Status/info line (Emacs style)
        self.status = QLabel("C-x  (C-h for help)", self)
        self.status.setFont(QFont("Consolas", 11))
        self.status.setStyleSheet("background: #23232a; color: #fff; border: none; padding-left: 6px;")
        layout.addWidget(self.status)

        # Minibuffer input
        self.input = QLineEdit(self)
        self.input.setFont(QFont("Consolas", 12))
        self.input.setPlaceholderText("")
        self.input.setStyleSheet("background: #23232a; color: #fff; border: none; padding: 0 6px; font-size: 15px;")
        self.input.returnPressed.connect(self.execute_command)
        layout.addWidget(self.input)

        self.setLayout(layout)

        # Install event filter on QLineEdit to intercept key sequences and history navigation
        self.input.installEventFilter(self)

    def execute_command(self):
        text = self.input.text().strip()
        # Save command to in-session history and to mibdata.json (save everything typed)
        if text:
            self.history.append(text)
            self.history_index = len(self.history)
            self._append_mibdata(text)

        # If the command matches a registered emacs command, execute it; otherwise warn
        if text in emacs_commands:
            try:
                main_window = self.parent()
                emacs_commands[text]["func"](main_window)
            except Exception as e:
                QMessageBox.critical(self, "Command Error", f"Error executing command '{text}': {e}")
        else:
            QMessageBox.warning(self, "Unknown Command", f"Unknown command: {text}")

        # Clear input after executing/attempting
        self.input.clear()
        # Reset sequence and status
        self.key_sequence = []
        self.status.setText("C-x  (C-h for help)")
        # Return focus to main window/editor if possible
        if self.parent():
            self.parent().setFocus()

    def eventFilter(self, obj, event):
        # Only handle key events for our input QLineEdit
        if obj is self.input and event.type() == QEvent.KeyPress:
            key = event.key()
            mods = event.modifiers()

            # History navigation
            if key == Qt.Key_Up:
                if self.history:
                    # move back in history
                    self.history_index = max(0, self.history_index - 1)
                    self.input.setText(self.history[self.history_index])
                    self.input.setCursorPosition(len(self.input.text()))
                return True
            elif key == Qt.Key_Down:
                if self.history:
                    # move forward in history
                    self.history_index = min(len(self.history), self.history_index + 1)
                    if self.history_index < len(self.history):
                        self.input.setText(self.history[self.history_index])
                    else:
                        self.input.clear()
                    self.input.setCursorPosition(len(self.input.text()))
                return True

            # Cancel sequence on Ctrl+G
            if mods & Qt.ControlModifier and (key == Qt.Key_G):
                self.key_sequence = []
                self.status.setText("C-x  (C-h for help)")
                self.input.clear()
                return True

            # If any modifier that we care about is pressed, try to build an Emacs-style token
            if mods & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier):
                seq_str = self._make_seq_str(key, mods)
                if not seq_str:
                    # not a printable sequence we can handle
                    # fall back to default
                    return False

                # Handle C-x prefix specially (Emacs-style)
                if seq_str == "C-x":
                    # If already have C-x as prefix, reset it (double C-x is treated as prefix restart)
                    self.key_sequence = ["C-x"]
                    self.status.setText("C-x")
                    return True

                # If current sequence is a C-x prefix, form full sequence like "C-x C-f"
                if self.key_sequence == ["C-x"]:
                    full = " ".join(self.key_sequence + [seq_str])
                    # show the sequence in input and try to execute
                    self.input.setText(full)
                    # If command exists, execute immediately
                    if full in emacs_commands:
                        self.execute_command()
                    else:
                        # Not an exact command; leave sequence displayed awaiting further input or manual enter
                        self.status.setText(full)
                    # Reset prefix state after attempting
                    self.key_sequence = []
                    return True
                else:
                    # No prefix: check single-token commands like "C-f", "M-x", etc.
                    if seq_str in emacs_commands:
                        self.input.setText(seq_str)
                        self.execute_command()
                        return True
                    else:
                        # Display the single token in the status so user sees it (but don't put into QLineEdit)
                        self.status.setText(seq_str)
                        # store it as a key_sequence in case the emacs_commands contains space-separated variants (rare)
                        self.key_sequence = [seq_str]
                        return True

            # If no modifiers: let QLineEdit handle normal typing, but also reset any held key_sequence
            self.key_sequence = []
            self.status.setText("C-x  (C-h for help)")
            return False

        return super().eventFilter(obj, event)

    def _make_seq_str(self, key, mods):
        """
        Convert a key + mods to an Emacs-style token string like "C-f", "M-x", "C-SPC", etc.
        Returns None for keys we don't handle.
        """
        # Prefer direct letter keys when possible
        if Qt.Key_A <= key <= Qt.Key_Z:
            char = chr(key).lower()
            if mods & Qt.ControlModifier:
                return f"C-{char}"
            if mods & Qt.AltModifier or mods & Qt.MetaModifier:
                return f"M-{char}"

        # Special keys handling
        if mods & Qt.ControlModifier:
            if key == Qt.Key_Space:
                return "C-SPC"
            # numeric and punctuation fallback via QKeySequence
            seq = QKeySequence(key).toString().lower()
            if seq:
                return f"C-{seq}"
            return None
        if mods & (Qt.AltModifier | Qt.MetaModifier):
            seq = QKeySequence(key).toString().lower()
            if seq:
                # map 'delete' to 'DEL' for compatibility with some emacs notation
                if seq.lower() == "delete":
                    return "M-DEL"
                return f"M-{seq}"
            return None

        return None

    def showEvent(self, event):
        # Dock to bottom of parent, flush with edge
        if self.parent():
            parent_geom = self.parent().geometry()
            width = parent_geom.width()
            height = self.height()
            x = 0
            y = parent_geom.height() - height
            self.setFixedWidth(width)
            self.move(x, y)
            # Focus the input when minibar is shown
            self.input.setFocus()
        super().showEvent(event)

    def resizeEvent(self, event):
        # Keep minibar docked at bottom on parent resize, flush with edge
        if self.parent():
            parent_geom = self.parent().geometry()
            width = parent_geom.width()
            height = self.height()
            x = 0
            y = parent_geom.height() - height
            self.setFixedWidth(width)
            self.move(x, y)
        super().resizeEvent(event)

    # mibdata.json helpers
    def _read_mibdata(self):
        try:
            if os.path.exists(self.mibdata_path):
                with open(self.mibdata_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _write_mibdata(self, data_list):
        try:
            with open(self.mibdata_path, "w", encoding="utf-8") as f:
                json.dump(list(data_list), f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _append_mibdata(self, item):
        try:
            data = self._read_mibdata()
            data.append(item)
            self._write_mibdata(data)
        except Exception:
            pass

    def clear_mibdata(self):
        """Clear contents of mibdata.json (write empty list). Called on app exit."""
        try:
            self._write_mibdata([])
        except Exception:
            pass

# Example usage for testing
if __name__ == "__main__":
    app = QApplication(sys.argv)
    from PyQt5.QtWidgets import QMainWindow
    win = QMainWindow()
    win.setGeometry(100, 100, 800, 600)
    minibar = Minibar(win)
    win.show()
    minibar.show()
    sys.exit(app.exec_())