import sys
from PyQt5.QtWidgets import (QWidget, QLineEdit, QVBoxLayout, QLabel, QApplication)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
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
                # Pass the main window as context if needed
                main_window = self.parent()
                emacs_commands[text]["func"](main_window)
            except Exception as e:
                QMessageBox.critical(self, "Command Error", f"Error executing command '{text}': {e}")
            self.input.clear()
            self.hide()
        else:
            QMessageBox.warning(self, "Unknown Command", f"Unknown command: {text}")
            self.input.clear()
            self.hide()

    def showEvent(self, event):
        # Dock to bottom of parent
        if self.parent():
            parent_geom = self.parent().geometry()
            width = parent_geom.width()
            height = self.height()
            x = parent_geom.x()
            y = parent_geom.y() + parent_geom.height() - height
            self.setFixedWidth(width)
            self.move(x, y)
        super().showEvent(event)

    def resizeEvent(self, event):
        # Keep minibar docked at bottom on parent resize
        if self.parent():
            parent_geom = self.parent().geometry()
            width = parent_geom.width()
            height = self.height()
            x = parent_geom.x()
            y = parent_geom.y() + parent_geom.height() - height
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