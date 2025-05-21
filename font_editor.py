import sys
import json
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QPushButton, QCheckBox, QGroupBox,
    QColorDialog, QTextEdit, QFontComboBox, QMessageBox, QSizePolicy
)
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon
from PyQt5.QtCore import Qt, pyqtSignal

CONFIG_PATH = "font_config.json"

def save_font_to_config(font: QFont):
    config = {
        "family": font.family(),
        "size": font.pointSize(),
        "bold": font.bold(),
        "italic": font.italic(),
        "underline": font.underline()
        # If you want to save colors, you can add them here
    }
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f)

class FontEditor(QWidget):
    settings_applied = pyqtSignal(QFont)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dark_mode = True
        self.text_color = QColor(Qt.white)
        self.bg_color = QColor(Qt.transparent)  # Editor bg will be transparent (no color set)
        self.init_ui()
        self.update_ui_theme()
        self.load_config_to_ui()

    def init_ui(self):
        self.setWindowTitle("Font Editor")
        self.setWindowIcon(QIcon.fromTheme("preferences-desktop-font"))
        self.resize(540, 420)
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', 'Fira Sans', 'Arial', sans-serif;
                font-size: 14px;
            }
            QGroupBox {
                border: 1px solid #44475a;
                border-radius: 8px;
                margin-top: 12px;
                padding: 8px 8px 8px 8px;
                font-weight: bold;
                color: #44475a;
                background: rgba(40,40,40,0.9);
            }
            QCheckBox, QLabel {
                font-size: 13px;
            }
            QPushButton {
                min-width: 90px;
                border-radius: 5px;
                padding: 4px 16px;
                background-color: #232323;
                color: #fff;
                font-weight: bold;
                border: 1px solid #888;
            }
            QPushButton:hover {
                background-color: #333438;
            }
            QFontComboBox, QSpinBox {
                min-width: 130px;
            }
            QTextEdit {
                border-radius: 6px;
                border: 1px solid #222;
                background: transparent;
                color: #fff;
            }
        """)

        main_layout = QVBoxLayout(self)

        # Preview Group
        self.preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        self.preview_text = QTextEdit()
        self.preview_text.setPlainText("The quick brown fox jumps over the lazy dog\n1234567890\n!@#$%^&*()")
        self.preview_text.setAlignment(Qt.AlignCenter)
        self.preview_text.setMinimumHeight(120)
        self.preview_text.setMaximumHeight(140)
        self.preview_text.setReadOnly(True)
        self.preview_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        preview_layout.addWidget(self.preview_text)
        self.preview_group.setLayout(preview_layout)

        # Font Settings Group
        font_group = QGroupBox("Font Settings")
        font_layout = QVBoxLayout()

        font_family_layout = QHBoxLayout()
        font_family_layout.addWidget(QLabel("Font Family:"))
        self.font_family_cb = QFontComboBox()
        self.font_family_cb.setEditable(False)
        self.font_family_cb.setMinimumWidth(180)
        self.font_family_cb.currentFontChanged.connect(self.update_font)
        font_family_layout.addWidget(self.font_family_cb)
        font_layout.addLayout(font_family_layout)

        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("Font Size:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 48)
        self.font_size_spin.setValue(12)
        self.font_size_spin.valueChanged.connect(self.update_font)
        font_size_layout.addWidget(self.font_size_spin)
        font_layout.addLayout(font_size_layout)

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
        font_layout.addLayout(font_style_layout)

        color_layout = QHBoxLayout()
        self.text_color_btn = QPushButton("Text Color")
        self.text_color_btn.clicked.connect(self.choose_text_color)
        self.bg_color_btn = QPushButton("Background Color")
        self.bg_color_btn.clicked.connect(self.choose_bg_color)
        color_layout.addWidget(self.text_color_btn)
        color_layout.addWidget(self.bg_color_btn)
        font_layout.addLayout(color_layout)

        font_group.setLayout(font_layout)

        # Action Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self.apply_settings)
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.ok_and_close)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.close)
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)

        # Theme Toggle
        self.theme_toggle = QPushButton("Switch to Light Mode")
        self.theme_toggle.clicked.connect(self.toggle_theme)
        self.theme_toggle.setStyleSheet("background-color: #232632; color: #fff; min-width: 170px; border: 1px solid #44475a;")

        main_layout.addWidget(self.preview_group)
        main_layout.addWidget(font_group)
        main_layout.addWidget(self.theme_toggle)
        main_layout.addLayout(button_layout)

    def load_config_to_ui(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    config = json.load(f)
                font = QFont(config.get("family", "Fira Code"), config.get("size", 12))
                font.setBold(config.get("bold", False))
                font.setItalic(config.get("italic", False))
                font.setUnderline(config.get("underline", False))
                self.font_family_cb.setCurrentFont(font)
                self.font_size_spin.setValue(font.pointSize())
                self.bold_check.setChecked(font.bold())
                self.italic_check.setChecked(font.italic())
                self.underline_check.setChecked(font.underline())
                self.preview_text.setFont(font)
            except Exception as e:
                print("Failed to load config:", e)
        self.update_font()

    def update_font(self):
        font = self.font_family_cb.currentFont()
        font.setPointSize(self.font_size_spin.value())
        font.setBold(self.bold_check.isChecked())
        font.setItalic(self.italic_check.isChecked())
        font.setUnderline(self.underline_check.isChecked())
        self.preview_text.setFont(font)
        self.preview_text.setTextColor(self.text_color)
        palette = self.preview_text.palette()
        palette.setColor(QPalette.Base, self.bg_color)
        self.preview_text.setPalette(palette)

    def choose_text_color(self):
        color = QColorDialog.getColor(self.text_color, self, "Select Text Color")
        if color.isValid():
            self.text_color = color
            self.preview_text.setTextColor(self.text_color)

    def choose_bg_color(self):
        color = QColorDialog.getColor(self.bg_color, self, "Select Background Color")
        if color.isValid():
            self.bg_color = color
            palette = self.preview_text.palette()
            palette.setColor(QPalette.Base, self.bg_color)
            self.preview_text.setPalette(palette)

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.update_ui_theme()

    def update_ui_theme(self):
        palette = QPalette()
        if self.dark_mode:
            palette.setColor(QPalette.Window, QColor(45, 48, 60))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(35, 38, 50))
            palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(24, 25, 26))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(80, 250, 123))
            palette.setColor(QPalette.Highlight, QColor(80, 250, 123))
            palette.setColor(QPalette.HighlightedText, Qt.black)
            self.theme_toggle.setText("Switch to Light Mode")
        else:
            palette.setColor(QPalette.Window, QColor(245, 245, 245))
            palette.setColor(QPalette.WindowText, Qt.black)
            palette.setColor(QPalette.Base, Qt.white)
            palette.setColor(QPalette.AlternateBase, QColor(240, 240, 240))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.black)
            palette.setColor(QPalette.Text, Qt.black)
            palette.setColor(QPalette.Button, QColor(220, 220, 220))
            palette.setColor(QPalette.ButtonText, Qt.black)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(0, 0, 255))
            palette.setColor(QPalette.Highlight, QColor(0, 120, 215))
            palette.setColor(QPalette.HighlightedText, Qt.white)
            self.theme_toggle.setText("Switch to Dark Mode")
        self.setPalette(palette)
        self.preview_text.setPalette(palette)

        btn_style = "background-color: #18191a; color: #fff; border: 1px solid #44475a;" if self.dark_mode else \
                    "background-color: #f8f8f8; color: #222; border: 1px solid #bbb;"
        self.apply_btn.setStyleSheet(btn_style)
        self.ok_btn.setStyleSheet(btn_style)
        self.cancel_btn.setStyleSheet(btn_style)

    def get_current_font(self):
        font = self.font_family_cb.currentFont()
        font.setPointSize(self.font_size_spin.value())
        font.setBold(self.bold_check.isChecked())
        font.setItalic(self.italic_check.isChecked())
        font.setUnderline(self.underline_check.isChecked())
        return font

    def apply_settings(self):
        font = self.get_current_font()
        save_font_to_config(font)
        self.settings_applied.emit(font)
        QMessageBox.information(self, "Font Editor", "Settings have been applied! They should take effect immediately.")

    def ok_and_close(self):
        self.apply_settings()
        self.close()

    def closeEvent(self, event):
        save_font_to_config(self.get_current_font())
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = FontEditor()
    editor.show()
    sys.exit(app.exec_())