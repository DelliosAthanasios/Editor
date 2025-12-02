"""
Enhanced Minibar with mode-aware vim/emacs command support.

Features:
- Mode indicator showing current editing mode (normal/vim/emacs)
- Vim command-line interface when vim mode is active
- Emacs command interface when emacs mode is active
- Session history and auto-clear on quit
"""

import sys
import os
import json
from PyQt5.QtWidgets import QWidget, QLineEdit, QVBoxLayout, QHBoxLayout, QLabel, QApplication, QMessageBox
from PyQt5.QtCore import Qt, QEvent, QTimer
from PyQt5.QtGui import QFont, QKeySequence

from .mode_detector import get_editor_mode, get_vim_submode, get_current_editor
from .mode_indicator import ModeIndicator
from .vim_handler import execute_vim_command, get_vim_help
from .emacs_handler import execute_emacs_command, get_emacs_help, EMACS_COMMANDS


class Minibar(QWidget):
    """
    Enhanced minibuffer with mode-aware command handling:
    - Shows current editing mode (normal/vim/emacs)
    - Vim command-line mode when vim is active
    - Emacs command sequences when emacs is active
    - Docks to bottom of parent window
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedHeight(48)
        self.setStyleSheet("background-color: #23232a; color: #fff; border: none;")
        
        # Command state
        self.key_sequence = []
        self.history = []
        self.history_index = -1
        self.current_mode = "normal"
        self.current_submode = None
        
        # mibdata.json path
        self.mibdata_path = os.path.join(os.path.dirname(__file__), "mibdata.json")
        self._write_mibdata([])

        self.init_ui()
        
        # Update mode indicator periodically
        self.mode_timer = QTimer(self)
        self.mode_timer.timeout.connect(self.update_mode_indicator)
        self.mode_timer.start(100)  # Update every 100ms

        # Connect to application quit to clear mibdata.json
        app = QApplication.instance()
        if app:
            try:
                app.aboutToQuit.connect(self.clear_mibdata)
            except Exception:
                pass

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top row: mode indicator + status
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(0)
        
        # Mode indicator
        self.mode_indicator = ModeIndicator(self)
        top_row.addWidget(self.mode_indicator)
        
        # Status label
        self.status = QLabel("Ready", self)
        self.status.setFont(QFont("Consolas", 11))
        self.status.setStyleSheet("background: #23232a; color: #fff; border: none; padding-left: 6px;")
        top_row.addWidget(self.status, 1)
        
        layout.addLayout(top_row)

        # Input line
        self.input = QLineEdit(self)
        self.input.setFont(QFont("Consolas", 12))
        self.input.setPlaceholderText("")
        self.input.setStyleSheet("background: #23232a; color: #fff; border: none; padding: 0 6px; font-size: 15px;")
        self.input.returnPressed.connect(self.execute_command)
        layout.addWidget(self.input)

        self.setLayout(layout)
        self.input.installEventFilter(self)

    def update_mode_indicator(self):
        """Update the mode indicator based on current editor state."""
        window = self.parent()
        if not window:
            return
        
        editor = get_current_editor(window)
        mode = get_editor_mode(editor)
        submode = get_vim_submode(editor) if mode == "vim" else None
        
        if mode != self.current_mode or submode != self.current_submode:
            self.current_mode = mode
            self.current_submode = submode
            self.mode_indicator.set_mode(mode, submode)
            
            # Update status message based on mode
            if mode == "vim":
                self.status.setText("Vim command mode (type :command)")
            elif mode == "emacs":
                self.status.setText("Emacs mode (type C-x commands)")
            else:
                self.status.setText("Normal mode")

    def execute_command(self):
        """Execute the command entered in the minibar."""
        text = self.input.text().strip()
        if not text:
            return
        
        # Save to history
        if text:
            self.history.append(text)
            self.history_index = len(self.history)
            self._append_mibdata(text)

        window = self.parent()
        if not window:
            return

        # Route command based on current mode
        editor = get_current_editor(window)
        mode = get_editor_mode(editor)
        handled = False

        if mode == "vim":
            # Vim command-line mode
            if text == ":help" or text == ":h":
                QMessageBox.information(self, "Vim Help", get_vim_help())
                handled = True
            else:
                handled = execute_vim_command(window, text)
        elif mode == "emacs":
            # Emacs command mode - text should already be a sequence like "C-x C-f"
            handled = execute_emacs_command(window, text)
        else:
            # Normal mode - try both vim and emacs formats
            if text.startswith(":"):
                handled = execute_vim_command(window, text)
            else:
                handled = execute_emacs_command(window, text)

        if not handled:
            QMessageBox.warning(self, "Unknown Command", f"Unknown command: {text}\n\nUse :help for vim commands or C-x C-h for emacs help")

        # Clear input and reset
        self.input.clear()
        self.key_sequence = []
        self.update_status_for_mode()

        # Return focus
        if window:
            window.setFocus()

    def update_status_for_mode(self):
        """Update status message based on current mode."""
        window = self.parent()
        if not window:
            return
        
        editor = get_current_editor(window)
        mode = get_editor_mode(editor)
        
        if mode == "vim":
            self.status.setText("Vim command mode (type :command)")
        elif mode == "emacs":
            self.status.setText("Emacs mode (type C-x commands)")
        else:
            self.status.setText("Normal mode")

    def eventFilter(self, obj, event):
        """Handle key events for command input and mode-specific behavior."""
        if obj is self.input and event.type() == QEvent.KeyPress:
            key = event.key()
            mods = event.modifiers()

            # History navigation
            if key == Qt.Key_Up:
                if self.history:
                    self.history_index = max(0, self.history_index - 1)
                    self.input.setText(self.history[self.history_index])
                    self.input.setCursorPosition(len(self.input.text()))
                return True
            elif key == Qt.Key_Down:
                if self.history:
                    self.history_index = min(len(self.history), self.history_index + 1)
                    if self.history_index < len(self.history):
                        self.input.setText(self.history[self.history_index])
                    else:
                        self.input.clear()
                    self.input.setCursorPosition(len(self.input.text()))
                return True

            # Cancel on Ctrl+G (emacs style)
            if mods & Qt.ControlModifier and key == Qt.Key_G:
                self.key_sequence = []
                self.update_status_for_mode()
                self.input.clear()
                return True

            # Mode-specific handling
            window = self.parent()
            if window:
                editor = get_current_editor(window)
                mode = get_editor_mode(editor)

                if mode == "emacs":
                    # Emacs mode: handle C-x prefix and key sequences
                    if mods & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier):
                        seq_str = self._make_seq_str(key, mods)
                        if not seq_str:
                            return False

                        # Handle C-x prefix
                        if seq_str == "C-x":
                            self.key_sequence = ["C-x"]
                            self.status.setText("C-x")
                            return True

                        # Complete C-x sequence
                        if self.key_sequence == ["C-x"]:
                            full = " ".join(self.key_sequence + [seq_str])
                            self.input.setText(full)
                            if full in EMACS_COMMANDS:
                                self.execute_command()
                            else:
                                self.status.setText(full)
                            self.key_sequence = []
                            return True
                        else:
                            # Single command
                            if seq_str in EMACS_COMMANDS:
                                self.input.setText(seq_str)
                                self.execute_command()
                                return True
                            else:
                                self.status.setText(seq_str)
                                self.key_sequence = [seq_str]
                                return True

                elif mode == "vim":
                    # Vim mode: allow typing : for command-line
                    if key == Qt.Key_Colon and not (mods & (Qt.ControlModifier | Qt.AltModifier)):
                        self.input.setText(":")
                        self.input.setCursorPosition(1)
                        return True

            # Default: allow normal typing
            self.key_sequence = []
            return False

        return super().eventFilter(obj, event)

    def _make_seq_str(self, key, mods):
        """Convert key+modifiers to Emacs-style string like 'C-f', 'M-x'."""
        if Qt.Key_A <= key <= Qt.Key_Z:
            char = chr(key).lower()
            if mods & Qt.ControlModifier:
                return f"C-{char}"
            if mods & (Qt.AltModifier | Qt.MetaModifier):
                return f"M-{char}"

        if mods & Qt.ControlModifier:
            if key == Qt.Key_Space:
                return "C-SPC"
            seq = QKeySequence(key).toString().lower()
            if seq:
                return f"C-{seq}"
            return None

        if mods & (Qt.AltModifier | Qt.MetaModifier):
            seq = QKeySequence(key).toString().lower()
            if seq:
                if seq.lower() == "delete":
                    return "M-DEL"
                return f"M-{seq}"
            return None

        return None

    def showEvent(self, event):
        """Dock to bottom when shown."""
        if self.parent():
            parent_geom = self.parent().geometry()
            width = parent_geom.width()
            height = self.height()
            x = 0
            y = parent_geom.height() - height
            self.setFixedWidth(width)
            self.move(x, y)
            self.input.setFocus()
            self.update_mode_indicator()
        super().showEvent(event)

    def resizeEvent(self, event):
        """Keep docked at bottom on resize."""
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
        """Clear mibdata.json on app exit."""
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
