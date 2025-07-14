import sys
from PyQt5.QtWidgets import (QWidget, QLineEdit, QVBoxLayout, QListWidget, QListWidgetItem, QApplication)
from PyQt5.QtCore import Qt, QSize

class Minibar(QWidget):
    def __init__(self, parent=None, command_registry=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedHeight(36)
        self.setStyleSheet("background-color: #23232a; color: #fff; border: none;")
        self.command_registry = command_registry or {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.input = QLineEdit(self)
        self.input.setPlaceholderText(": command")
        self.input.setStyleSheet("background: #23232a; color: #fff; border: none; padding: 4px 8px; font-size: 15px;")
        self.input.returnPressed.connect(self.execute_command)
        self.input.textChanged.connect(self.update_suggestions)
        layout.addWidget(self.input)
        self.suggestions = QListWidget(self)
        self.suggestions.setStyleSheet("background: #23232a; color: #fff; border: none; font-size: 13px;")
        self.suggestions.hide()
        self.suggestions.itemActivated.connect(self.select_suggestion)
        layout.addWidget(self.suggestions)
        self.setLayout(layout)

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

    def register_command(self, name, func, description=""):
        self.command_registry[name] = {"func": func, "description": description}

    def update_suggestions(self, text):
        self.suggestions.clear()
        if not text:
            self.suggestions.hide()
            return
        matches = [k for k in self.command_registry if k.startswith(text)]
        if matches:
            for cmd in matches:
                desc = self.command_registry[cmd]["description"]
                item = QListWidgetItem(f"{cmd} - {desc}")
                item.setData(Qt.UserRole, cmd)
                self.suggestions.addItem(item)
            self.suggestions.show()
        else:
            self.suggestions.hide()

    def select_suggestion(self, item):
        cmd = item.data(Qt.UserRole)
        self.input.setText(cmd)
        self.suggestions.hide()
        self.execute_command()

    def execute_command(self):
        text = self.input.text().strip()
        if text in self.command_registry:
            self.command_registry[text]["func"]()
            self.input.clear()
            self.hide()
        else:
            self.input.setText("")
            self.hide()

# Example usage for testing
if __name__ == "__main__":
    app = QApplication(sys.argv)
    from PyQt5.QtWidgets import QMainWindow
    win = QMainWindow()
    win.setGeometry(100, 100, 800, 600)
    minibar = Minibar(win)
    minibar.register_command(":open", lambda: print("Open command executed"), "Open a file")
    minibar.register_command(":save", lambda: print("Save command executed"), "Save current file")
    minibar.register_command(":theme", lambda: print("Theme command executed"), "Change theme")
    win.show()
    minibar.show()
    sys.exit(app.exec_()) 