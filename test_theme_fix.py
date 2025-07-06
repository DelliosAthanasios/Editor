#!/usr/bin/env python3
"""
Test script to verify theme changes work properly for menu bar and separators.
"""

import sys
import os

# Add the global folder to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
global_dir = os.path.join(current_dir, 'global')
if global_dir not in sys.path:
    sys.path.append(global_dir)

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QMenuBar
from PyQt5.QtCore import Qt
from theme_manager import theme_manager_singleton, get_menu_bar_styles, get_separator_styles

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Theme Test")
        self.setGeometry(100, 100, 600, 400)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create central widget
        central = QWidget()
        layout = QVBoxLayout(central)
        
        # Add buttons to test theme changes
        self.dark_btn = QPushButton("Dark Theme")
        self.dark_btn.clicked.connect(lambda: self.change_theme("dark"))
        layout.addWidget(self.dark_btn)
        
        self.light_btn = QPushButton("Light Theme")
        self.light_btn.clicked.connect(lambda: self.change_theme("light"))
        layout.addWidget(self.light_btn)
        
        self.monokai_btn = QPushButton("Monokai Theme")
        self.monokai_btn.clicked.connect(lambda: self.change_theme("monokai"))
        layout.addWidget(self.monokai_btn)
        
        self.setCentralWidget(central)
        
        # Apply initial theme
        self.apply_current_theme()
        
        # Connect to theme changes
        theme_manager_singleton.themeChanged.connect(self.on_theme_changed)
    
    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        file_menu.addAction("Test Action")
        
        edit_menu = menu_bar.addMenu("Edit")
        edit_menu.addAction("Another Action")
    
    def change_theme(self, theme_key):
        app = QApplication.instance()
        theme_manager_singleton.apply_theme(app, theme_key)
    
    def apply_current_theme(self):
        theme_data = theme_manager_singleton.get_theme()
        self.update_menu_bar_theme(theme_data)
    
    def update_menu_bar_theme(self, theme_data):
        menu_style = get_menu_bar_styles(theme_data)
        self.menuBar().setStyleSheet(menu_style)
    
    def on_theme_changed(self, theme_data):
        self.update_menu_bar_theme(theme_data)

def main():
    app = QApplication(sys.argv)
    
    # Apply initial theme
    theme_manager_singleton.apply_theme(app, theme_manager_singleton.current_theme_key)
    app.setStyle("Fusion")
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 