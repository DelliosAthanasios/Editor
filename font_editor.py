import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QSpinBox, QPushButton, QCheckBox, QGroupBox,
                             QColorDialog, QTextEdit, QFontComboBox)
from PyQt5.QtGui import QFont, QColor, QPalette, QFontDatabase
from PyQt5.QtCore import Qt


class FontEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dark_mode = False
        self.init_ui()
        self.update_ui_theme()
        
    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout()
        
        # Preview area
        self.preview_group = QGroupBox("Preview")
        self.preview_text = QTextEdit()
        self.preview_text.setPlainText("The quick brown fox jumps over the lazy dog\n1234567890\n!@#$%^&*()")
        self.preview_text.setAlignment(Qt.AlignCenter)
        self.preview_text.setMinimumHeight(150)
        
        preview_layout = QVBoxLayout()
        preview_layout.addWidget(self.preview_text)
        self.preview_group.setLayout(preview_layout)
        
        # Font controls
        font_group = QGroupBox("Font Settings")
        
        # Font family
        font_family_layout = QHBoxLayout()
        font_family_layout.addWidget(QLabel("Font Family:"))
        self.font_family_cb = QFontComboBox()
        self.font_family_cb.currentFontChanged.connect(self.update_font)
        font_family_layout.addWidget(self.font_family_cb)
        
        # Font size
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("Font Size:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(6, 72)
        self.font_size_spin.setValue(12)
        self.font_size_spin.valueChanged.connect(self.update_font)
        font_size_layout.addWidget(self.font_size_spin)
        
        # Font styles
        font_style_layout = QHBoxLayout()
        self.bold_check = QCheckBox("Bold")
        self.bold_check.toggled.connect(self.update_font)
        self.italic_check = QCheckBox("Italic")
        self.italic_check.toggled.connect(self.update_font)
        self.underline_check = QCheckBox("Underline")
        self.underline_check.toggled.connect(self.update_font)
        font_style_layout.addWidget(self.bold_check)
        font_style_layout.addWidget(self.italic_check)
        font_style_layout.addWidget(self.underline_check)
        
        # Color selection
        color_layout = QHBoxLayout()
        self.text_color_btn = QPushButton("Text Color")
        self.text_color_btn.clicked.connect(self.choose_text_color)
        self.bg_color_btn = QPushButton("Background Color")
        self.bg_color_btn.clicked.connect(self.choose_bg_color)
        color_layout.addWidget(self.text_color_btn)
        color_layout.addWidget(self.bg_color_btn)
        
        # Assemble font group
        font_layout = QVBoxLayout()
        font_layout.addLayout(font_family_layout)
        font_layout.addLayout(font_size_layout)
        font_layout.addLayout(font_style_layout)
        font_layout.addLayout(color_layout)
        font_group.setLayout(font_layout)
        
        # Theme toggle
        self.theme_toggle = QPushButton("Switch to Dark Mode")
        self.theme_toggle.clicked.connect(self.toggle_theme)
        
        # Add widgets to main layout
        main_layout.addWidget(self.preview_group)
        main_layout.addWidget(font_group)
        main_layout.addWidget(self.theme_toggle)
        
        self.setLayout(main_layout)
        self.setWindowTitle("Font Editor")
        self.resize(500, 400)
        
    def update_font(self):
        font = self.font_family_cb.currentFont()
        font.setPointSize(self.font_size_spin.value())
        font.setBold(self.bold_check.isChecked())
        font.setItalic(self.italic_check.isChecked())
        font.setUnderline(self.underline_check.isChecked())
        self.preview_text.setFont(font)
        
    def choose_text_color(self):
        color = QColorDialog.getColor(self.preview_text.textColor(), self, "Select Text Color")
        if color.isValid():
            self.preview_text.setTextColor(color)
            
    def choose_bg_color(self):
        color = QColorDialog.getColor(self.preview_text.palette().color(QPalette.Base), self, "Select Background Color")
        if color.isValid():
            palette = self.preview_text.palette()
            palette.setColor(QPalette.Base, color)
            self.preview_text.setPalette(palette)
            
    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.update_ui_theme()
        
    def update_ui_theme(self):
        palette = QPalette()
        
        if self.dark_mode:
            palette.setColor(QPalette.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, Qt.black)
            self.theme_toggle.setText("Switch to Light Mode")
        else:
            palette.setColor(QPalette.Window, QColor(240, 240, 240))
            palette.setColor(QPalette.WindowText, Qt.black)
            palette.setColor(QPalette.Base, Qt.white)
            palette.setColor(QPalette.AlternateBase, QColor(240, 240, 240))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.black)
            palette.setColor(QPalette.Text, Qt.black)
            palette.setColor(QPalette.Button, QColor(240, 240, 240))
            palette.setColor(QPalette.ButtonText, Qt.black)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(0, 0, 255))
            palette.setColor(QPalette.Highlight, QColor(0, 120, 215))
            palette.setColor(QPalette.HighlightedText, Qt.white)
            self.theme_toggle.setText("Switch to Dark Mode")
            
        self.setPalette(palette)
        
    def get_current_font(self):
        """Returns the current QFont settings"""
        font = self.font_family_cb.currentFont()
        font.setPointSize(self.font_size_spin.value())
        font.setBold(self.bold_check.isChecked())
        font.setItalic(self.italic_check.isChecked())
        font.setUnderline(self.underline_check.isChecked())
        return font
        
    def get_current_colors(self):
        """Returns a tuple of (text_color, bg_color)"""
        text_color = self.preview_text.textColor()
        bg_color = self.preview_text.palette().color(QPalette.Base)
        return (text_color, bg_color)
        
    def set_font(self, font):
        """Set all controls from a QFont object"""
        self.font_family_cb.setCurrentFont(font)
        self.font_size_spin.setValue(font.pointSize())
        self.bold_check.setChecked(font.bold())
        self.italic_check.setChecked(font.italic())
        self.underline_check.setChecked(font.underline())
        self.preview_text.setFont(font)
        
    def set_colors(self, text_color, bg_color):
        """Set text and background colors"""
        self.preview_text.setTextColor(text_color)
        palette = self.preview_text.palette()
        palette.setColor(QPalette.Base, bg_color)
        self.preview_text.setPalette(palette)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = FontEditor()
    editor.show()
    sys.exit(app.exec_())
    

    

