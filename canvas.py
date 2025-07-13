import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QSplitter
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

# Import the main window and set_dark_palette from main.py
from main import TextEditor, set_dark_palette
from global_.dynamic_saving import enable_dynamic_saving_for_qt

class CanvasWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Canvas - Host for main.py')
        self.setGeometry(100, 100, 1400, 900)
        self.editors = []
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        vlayout = QVBoxLayout(central)
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.setSpacing(0)
        # Splitter to hold TextEditor instances
        self.splitter = QSplitter(Qt.Orientation(1))
        self.splitter.setStyleSheet("background-color: #23232a; border: none;")
        vlayout.addWidget(self.splitter)
        self.setCentralWidget(central)
        # Start with one editor
        self.split_window()

    def split_window(self, orientation=None):
        editor = TextEditor(canvas_parent=self)
        self.splitter.addWidget(editor)
        self.editors.append(editor)
        enable_dynamic_saving_for_qt(editor)

    def add_split_editor(self):
        self.split_window()

    def unsplit_window(self):
        if len(self.editors) > 1:
            editor = self.editors.pop()
            editor.setParent(None)
            editor.deleteLater()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Apply the current theme from theme manager instead of hardcoded dark palette
    try:
        from global_.theme_manager import theme_manager_singleton
        theme_manager_singleton.apply_theme(app, theme_manager_singleton.current_theme_key)
        app.setStyle("Fusion")
    except Exception as e:
        print(f"Warning: Could not apply theme: {e}")
        # Fallback to basic dark theme
        app.setStyle("Fusion")
        palette = app.palette()
        palette.setColor(palette.Window, QColor(30, 30, 30))
        palette.setColor(palette.WindowText, QColor(255, 255, 255))
        palette.setColor(palette.Base, QColor(40, 40, 40))
        palette.setColor(palette.Text, QColor(255, 255, 255))
        app.setPalette(palette)
    
    window = CanvasWindow()
    window.show()
    sys.exit(app.exec_()) 