import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QSplitter
)
from PyQt5.QtCore import Qt

# Add the global folder to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
global_dir = os.path.join(current_dir, 'global')
if global_dir not in sys.path:
    sys.path.append(global_dir)

# Import the main window and set_dark_palette from main.py
from main import TextEditor, set_dark_palette

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
    from theme_manager import theme_manager_singleton
    theme_manager_singleton.apply_theme(app, theme_manager_singleton.current_theme_key)
    app.setStyle("Fusion")
    window = CanvasWindow()
    window.show()
    sys.exit(app.exec_()) 