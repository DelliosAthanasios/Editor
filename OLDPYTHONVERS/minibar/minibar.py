import sys
from PyQt5.QtWidgets import (QWidget, QLineEdit, QVBoxLayout, QLabel, QApplication)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QKeySequence
from keysandfuncs.emacscommsbar import emacs_commands
from PyQt5.QtWidgets import QMessageBox

class Minibar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedHeight(48)
        self.setStyleSheet("background-color: #23232a; color: #fff; border: none;")
        self.init_ui()
        self.key_sequence = []  # Track pressed keys for Emacs-style sequences

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # Status/info line (Emacs style)
        self.status = QLabel(r"C-x-  (C-h for help)", self)
        self.status.setFont(QFont("Consolas", 11))
        self.status.setStyleSheet("background: #23232a; color: #fff; border: none; padding-left: 4px;")
        layout.addWidget(self.status)
        # Minibuffer input
        self.input = QLineEdit(self)
        self.input.setFont(QFont("Consolas", 12))
        self.input.setPlaceholderText("")
        self.input.setStyleSheet("background: #23232a; color: #fff; border: none; padding: 0 4px; font-size: 15px;")
        self.input.returnPressed.connect(self.execute_command)
        layout.addWidget(self.input)
        self.setLayout(layout)

    def execute_command(self):
        text = self.input.text().strip()
        if text in emacs_commands:
            try:
                main_window = self.parent()
                emacs_commands[text]["func"](main_window)
            except Exception as e:
                QMessageBox.critical(self, "Command Error", f"Error executing command '{text}': {e}")
            self.input.clear()
            # Do not hide the minibar; return focus to main window/editor
            if main_window:
                main_window.setFocus()
        else:
            QMessageBox.warning(self, "Unknown Command", f"Unknown command: {text}")
            self.input.clear()
            if self.parent():
                self.parent().setFocus()

    def keyPressEvent(self, event):
        # Emacs-style key sequence support
        key = event.key()
        mods = event.modifiers()
        seq_str = None
        # Map Qt key/modifier to Emacs-style string
        def key_to_emacs(key, mods):
            if mods & Qt.ControlModifier:
                if key == Qt.Key_Space:
                    return "C-SPC"
                elif key == Qt.Key_Slash:
                    return "C-/"
                elif key == Qt.Key_ParenLeft:
                    return "C-x ("
                elif key == Qt.Key_ParenRight:
                    return "C-x )"
                elif key == Qt.Key_U:
                    return "C-x u"
                elif key == Qt.Key_E:
                    return "C-x e"
                elif key == Qt.Key_F:
                    return "C-x C-f" if self.key_sequence == ["C-x"] else "C-f"
                elif key == Qt.Key_S:
                    return "C-x C-s" if self.key_sequence == ["C-x"] else "C-s"
                elif key == Qt.Key_W:
                    return "C-x C-w" if self.key_sequence == ["C-x"] else "C-w"
                elif key == Qt.Key_B:
                    return "C-x b" if self.key_sequence == ["C-x"] else "C-b"
                elif key == Qt.Key_V:
                    return "C-x C-v" if self.key_sequence == ["C-x"] else "C-v"
                elif key == Qt.Key_C:
                    return "C-x C-c" if self.key_sequence == ["C-x"] else "C-c"
                elif key == Qt.Key_K:
                    return "C-x k" if self.key_sequence == ["C-x"] else "C-k"
                elif key == Qt.Key_BracketLeft:
                    return "C-x ["
                elif key == Qt.Key_BracketRight:
                    return "C-x ]"
                elif key == Qt.Key_0:
                    return "C-x 0"
                elif key == Qt.Key_1:
                    return "C-x 1"
                elif key == Qt.Key_2:
                    return "C-x 2"
                elif key == Qt.Key_3:
                    return "C-x 3"
                elif key == Qt.Key_O:
                    return "C-x o" if self.key_sequence == ["C-x"] else "C-o"
                else:
                    # Only use chr(key) for valid ASCII letters
                    if (Qt.Key_A <= key <= Qt.Key_Z):
                        return f"C-{chr(key + 32)}"  # Qt.Key_A is uppercase, +32 to get lowercase
                    else:
                        seq = QKeySequence(key).toString().lower()
                        if seq:
                            return f"C-{seq}"
                        else:
                            return None
            elif mods & Qt.AltModifier:
                if key == Qt.Key_Less:
                    return "M-<"
                elif key == Qt.Key_Greater:
                    return "M->"
                elif key == Qt.Key_D:
                    return "M-d"
                elif key == Qt.Key_B:
                    return "M-b"
                elif key == Qt.Key_F:
                    return "M-f"
                elif key == Qt.Key_W:
                    return "M-w"
                elif key == Qt.Key_Y:
                    return "M-y"
                elif key == Qt.Key_Percent:
                    return "M-%"
                elif key == Qt.Key_Delete:
                    return "M-DEL"
                else:
                    if (Qt.Key_A <= key <= Qt.Key_Z):
                        return f"M-{chr(key + 32)}"
                    else:
                        seq = QKeySequence(key).toString().lower()
                        if seq:
                            return f"M-{seq}"
                        else:
                            return None
            elif mods & Qt.ControlModifier and mods & Qt.AltModifier:
                if key == Qt.Key_Percent:
                    return "C-M-%"
            elif mods & Qt.MetaModifier:
                if (Qt.Key_A <= key <= Qt.Key_Z):
                    return f"M-{chr(key + 32)}"
                else:
                    seq = QKeySequence(key).toString().lower()
                    if seq:
                        return f"M-{seq}"
                    else:
                        return None
            else:
                # Plain keys
                if key == Qt.Key_Return or key == Qt.Key_Enter:
                    return None
                elif key == Qt.Key_Space:
                    return "SPC"
                else:
                    return QKeySequence(key).toString().lower()
        # Build up sequence
        if mods & Qt.ControlModifier or mods & Qt.AltModifier or mods & Qt.MetaModifier:
            seq_str = key_to_emacs(key, mods)
            # Only append valid, printable Emacs-style strings
            if seq_str and all(ord(c) >= 32 and ord(c) < 127 for c in seq_str):
                self.key_sequence.append(seq_str)
                display_seq = " ".join(self.key_sequence)
                # Try full sequence
                if display_seq in emacs_commands:
                    self.input.setText(display_seq)
                    self.execute_command()
                    self.key_sequence = []
                    return
                # Try last key only (for single-key commands)
                elif seq_str in emacs_commands:
                    self.input.setText(seq_str)
                    self.execute_command()
                    self.key_sequence = []
                    return
                else:
                    self.input.setText(display_seq)
                    return
            else:
                # Invalid key, reset sequence
                self.key_sequence = []
                self.input.clear()
                return
        else:
            # Reset sequence if normal key pressed
            self.key_sequence = []
        # Fallback to normal QLineEdit behavior
        super().keyPressEvent(event)

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