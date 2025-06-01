import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QListWidget, QListWidgetItem, QLabel, QPushButton,
    QComboBox, QFileDialog, QFrame, QMessageBox, QCheckBox
)
from PyQt5.QtGui import QFont, QColor, QIcon, QPixmap
from PyQt5.QtCore import Qt, QSize, QSettings, pyqtSignal

class LanguageSelector(QMainWindow):
    favorites_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.settings = QSettings("CodeMaster", "LangSelector")
        self.setWindowTitle("Code Language Manager")
        self.setGeometry(100, 100, 1000, 800)
        self.setWindowIcon(QIcon(self.resource_path("icon.png")))
        self.extensions = {}
        self.compilers = {}
        self.favorites = set()
        self.init_ui()
        self.load_data()
        self.set_styles()
        self.favorites_changed.connect(self.apply_filters)

    def resource_path(self, relative_path):
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

    def init_ui(self):
        main_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Header
        header = QLabel("Programming Language Manager")
        header.setAlignment(Qt.AlignCenter)
        
        # Controls
        control_layout = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Languages", "Common Languages", "My Favorites"])
        self.filter_combo.currentIndexChanged.connect(self.apply_filters)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search languages, extensions or compilers...")
        self.search_box.textChanged.connect(self.apply_filters)
        
        control_layout.addWidget(self.filter_combo)
        control_layout.addWidget(self.search_box)

        # Language List
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(32, 32))
        self.list_widget.itemDoubleClicked.connect(self.show_details)

        # Details Panel
        details_frame = QFrame()
        details_layout = QVBoxLayout()
        details_layout.setContentsMargins(15, 15, 15, 15)
        
        self.lang_label = QLabel("Selected Language: None")
        self.ext_label = QLabel("Extension: None")
        self.compiler_label = QLabel("Compiler: Not configured")
        
        compiler_control = QHBoxLayout()
        self.set_compiler_btn = QPushButton("Set Compiler")
        self.clear_compiler_btn = QPushButton("Clear")
        self.set_compiler_btn.clicked.connect(self.set_compiler)
        self.clear_compiler_btn.clicked.connect(self.clear_compiler)
        
        compiler_control.addWidget(self.set_compiler_btn)
        compiler_control.addWidget(self.clear_compiler_btn)
        
        details_layout.addWidget(self.lang_label)
        details_layout.addWidget(self.ext_label)
        details_layout.addWidget(self.compiler_label)
        details_layout.addLayout(compiler_control)
        details_frame.setLayout(details_layout)

        # Favorites toggle
        self.favorite_check = QCheckBox("Add to Favorites")
        self.favorite_check.stateChanged.connect(self.toggle_favorite)

        layout.addWidget(header)
        layout.addLayout(control_layout)
        layout.addWidget(self.list_widget)
        layout.addWidget(details_frame)
        layout.addWidget(self.favorite_check)
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

    def set_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
            }
            QLabel {
                color: #ffffff;
                font-size: 14px;
            }
            QLineEdit, QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 2px solid #3d3d3d;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
            }
            QListWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #404040;
                color: #ffffff;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QFrame {
                background-color: #252525;
                border-radius: 5px;
            }
            QCheckBox {
                color: #ffffff;
                font-size: 14px;
            }
        """)

    def load_data(self):
        try:
            # Load languages and extensions
            with open("programming_languages.txt", "r") as f:
                for line in f:
                    if '-' in line:
                        parts = line.split('-')
                        lang = parts[0].strip()
                        ext = parts[-1].split('#')[0].strip()
                        self.extensions[lang] = ext
            
            # Load common languages
            self.common_languages = ["Python", "Java", "C++", "JavaScript", "C#",
                                   "Ruby", "PHP", "Swift", "Go", "Rust", "TypeScript"]
            
            # Load saved compilers and favorites
            self.compilers = self.settings.value("compilers", {})
            self.favorites = set(self.settings.value("favorites", []))
            
            self.populate_list()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")

    def populate_list(self, filter_text="", filter_mode=0):
        self.list_widget.clear()
        languages = []
        
        if filter_mode == 1:  # Common
            languages = self.common_languages
        elif filter_mode == 2:  # Favorites
            languages = list(self.favorites)
        else:  # All
            languages = self.extensions.keys()
        
        for lang in sorted(languages):
            if filter_text.lower() not in f"{lang.lower()} {self.extensions.get(lang, '').lower()}":
                continue
                
            item = QListWidgetItem()
            item.setData(Qt.UserRole, lang)
            item.setSizeHint(QSize(0, 50))
            
            # Load icon if exists
            icon_path = self.resource_path(f"icons/{lang.lower()}.png")
            if os.path.exists(icon_path):
                item.setIcon(QIcon(icon_path))
            else:
                item.setIcon(QIcon(self.resource_path("icons/default.png")))
            
            # Format item text
            ext = self.extensions.get(lang, "Unknown")
            compiler = self.compilers.get(lang, "")
            favorite = "★" if lang in self.favorites else ""
            
            item.setText(f"{favorite} {lang}\nExtension: {ext}" + 
                        (f"\nCompiler: {compiler}" if compiler else ""))
            
            self.list_widget.addItem(item)

    def apply_filters(self):
        filter_text = self.search_box.text()
        filter_mode = self.filter_combo.currentIndex()
        self.populate_list(filter_text, filter_mode)

    def show_details(self, item):
        self.current_lang = item.data(Qt.UserRole)
        self.lang_label.setText(f"Language: {self.current_lang}")
        self.ext_label.setText(f"Extension: {self.extensions.get(self.current_lang, 'Unknown')}")
        self.compiler_label.setText(f"Compiler: {self.compilers.get(self.current_lang, 'Not configured')}")
        self.favorite_check.setChecked(self.current_lang in self.favorites)

    def set_compiler(self):
        if not hasattr(self, 'current_lang'):
            return
            
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Compiler", "", "Executable Files (*.exe);;All Files (*)"
        )
        if path:
            self.compilers[self.current_lang] = path
            self.settings.setValue("compilers", self.compilers)
            self.apply_filters()
            self.show_details(self.list_widget.currentItem())

    def clear_compiler(self):
        if hasattr(self, 'current_lang') and self.current_lang in self.compilers:
            del self.compilers[self.current_lang]
            self.settings.setValue("compilers", self.compilers)
            self.apply_filters()
            self.show_details(self.list_widget.currentItem())

    def toggle_favorite(self, state):
        if not hasattr(self, 'current_lang'):
            return
            
        if state == Qt.Checked:
            self.favorites.add(self.current_lang)
        else:
            self.favorites.discard(self.current_lang)
            
        self.settings.setValue("favorites", list(self.favorites))
        self.favorites_changed.emit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 12))
    window = LanguageSelector()
    window.show()
    sys.exit(app.exec_())