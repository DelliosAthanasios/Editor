import sys
import json
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QPushButton, QCheckBox, QGroupBox,
    QColorDialog, QTextEdit, QFontComboBox, QMessageBox, QSizePolicy,
    QTabWidget, QComboBox, QSlider
)
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QTextCursor, QTextCharFormat
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

CONFIG_PATH = "font_config.json"

def safe_write_json(path, data):
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(data, f)
        os.replace(tmp_path, path)
    except Exception as e:
        print("Failed to write config:", e)

def save_font_to_config(font: QFont, text_color, line_spacing, letter_spacing):
    config = {
        "family": font.family(),
        "size": font.pointSize(),
        "bold": font.bold(),
        "italic": font.italic(),
        "underline": font.underline(),
        "text_color": text_color.name(),
        "line_spacing": line_spacing,
        "letter_spacing": letter_spacing
    }
    safe_write_json(CONFIG_PATH, config)

class FontEditor(QWidget):
    settings_applied = pyqtSignal(QFont)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.text_color = QColor("#ffffff")
        self.line_spacing = 1.0
        self.letter_spacing = 0
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._delayed_update)
        self.init_ui()
        self.force_dark_theme()
        self.load_config_to_ui()
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint)

    def init_ui(self):
        self.setWindowTitle("Font Editor")
        self.setWindowIcon(QIcon.fromTheme("preferences-desktop-font"))
        self.resize(640, 520)
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', 'Fira Sans', 'Arial', sans-serif;
                font-size: 14px;
                background: #18191a;
                color: #f5f6fa;
            }
            QTabWidget::pane {
                border: 1.5px solid #232323;
                border-radius: 7px;
                background: #232323;
            }
            QTabBar::tab {
                background: #232323;
                color: #bbb;
                padding: 8px 22px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                min-width: 100px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #18191a;
                color: #fff;
            }
            QGroupBox {
                border: 1.5px solid #282a36;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px 10px 6px 10px;
                font-weight: bold;
                color: #bbbbbb;
                background: transparent;
            }
            QLabel {
                font-size: 13px;
                color: #ddd;
            }
            QPushButton {
                min-width: 90px;
                border-radius: 6px;
                padding: 7px 16px;
                background-color: #232323;
                color: #fff;
                font-weight: bold;
                border: 1.5px solid #44475a;
            }
            QPushButton:disabled {
                background: #2a2a2a;
                color: #888;
            }
            QPushButton:hover {
                background-color: #333438;
            }
            QFontComboBox, QSpinBox, QComboBox {
                min-width: 110px;
                border-radius: 5px;
                border: 1.5px solid #333;
                background: #1a1a1a;
                color: #fff;
                padding: 4px 8px;
                selection-background-color: #44475a;
                selection-color: #fff;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background: #222;
                border: none;
            }
            QTextEdit {
                border-radius: 8px;
                border: 2px solid #292929;
                background: transparent;
                color: #fff;
                padding: 11px;
                font-size: 16px;
            }
            QCheckBox {
                font-size: 13px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #222;
                height: 8px;
                background: #292929;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #44475a;
                border: 1px solid #888;
                width: 18px;
                margin: -4px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #3b3b3b;
                border-radius: 4px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)

        # ----------- Tabs -----------
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # ----------- Main Tab -----------
        main_tab = QWidget()
        main_tab_layout = QVBoxLayout(main_tab)
        main_tab_layout.setContentsMargins(6, 12, 6, 6)

        # ----------- Preview Group -----------
        self.preview_group = QGroupBox("Preview (Edit text below)")
        preview_layout = QVBoxLayout()
        self.preview_text = QTextEdit()
        self.preview_text.setPlainText("The quick brown fox jumps over the lazy dog\n1234567890\n!@#$%^&*()")
        self.preview_text.setAlignment(Qt.AlignLeft)
        self.preview_text.setMinimumHeight(130)
        self.preview_text.setMaximumHeight(260)
        self.preview_text.setReadOnly(False)
        self.preview_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview_text.setToolTip("Live preview. You can edit text directly here.")
        self.preview_text.textChanged.connect(self._schedule_update)
        preview_layout.addWidget(self.preview_text)
        self.preview_group.setLayout(preview_layout)
        main_tab_layout.addWidget(self.preview_group)

        # ----------- Font Settings Group ----------
        font_group = QGroupBox("Font Settings")
        font_layout = QVBoxLayout()
        font_layout.setSpacing(8)

        # Row: Font Family
        font_family_layout = QHBoxLayout()
        family_icon = QLabel()
        family_icon.setPixmap(QIcon.fromTheme("font").pixmap(18, 18))
        font_family_layout.addWidget(family_icon)
        font_family_layout.addWidget(QLabel("Font Family:"))
        self.font_family_cb = QFontComboBox()
        self.font_family_cb.setEditable(False)
        self.font_family_cb.setToolTip("Select font family")
        self.font_family_cb.setMinimumWidth(180)
        self.font_family_cb.currentFontChanged.connect(self.update_font)
        font_family_layout.addWidget(self.font_family_cb)
        font_family_layout.addStretch(1)
        font_layout.addLayout(font_family_layout)

        # Row: Font Size
        font_size_layout = QHBoxLayout()
        size_icon = QLabel()
        size_icon.setPixmap(QIcon.fromTheme("format-text-size").pixmap(18, 18))
        font_size_layout.addWidget(size_icon)
        font_size_layout.addWidget(QLabel("Font Size:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 96)
        self.font_size_spin.setValue(12)
        self.font_size_spin.setSingleStep(1)
        self.font_size_spin.setToolTip("Adjust font size")
        self.font_size_spin.valueChanged.connect(self.update_font)
        font_size_layout.addWidget(self.font_size_spin)
        font_size_layout.addStretch(1)
        font_layout.addLayout(font_size_layout)

        # Row: Styles
        font_style_layout = QHBoxLayout()
        self.bold_check = QCheckBox("Bold")
        self.bold_check.setToolTip("Toggle bold style")
        self.bold_check.toggled.connect(self.update_font)
        self.italic_check = QCheckBox("Italic")
        self.italic_check.setToolTip("Toggle italic style")
        self.italic_check.toggled.connect(self.update_font)
        self.underline_check = QCheckBox("Underline")
        self.underline_check.setToolTip("Toggle underline style")
        self.underline_check.toggled.connect(self.update_font)
        font_style_layout.addWidget(self.bold_check)
        font_style_layout.addWidget(self.italic_check)
        font_style_layout.addWidget(self.underline_check)
        font_style_layout.addStretch(1)
        font_layout.addLayout(font_style_layout)

        # Row: Letter Spacing
        letter_spacing_layout = QHBoxLayout()
        letter_spacing_layout.addWidget(QLabel("Letter Spacing:"))
        self.letter_spacing_spin = QSpinBox()
        self.letter_spacing_spin.setRange(-5, 35)
        self.letter_spacing_spin.setValue(0)
        self.letter_spacing_spin.setToolTip("Space between letters (px)")
        self.letter_spacing_spin.valueChanged.connect(self.update_font)
        letter_spacing_layout.addWidget(self.letter_spacing_spin)
        letter_spacing_layout.addStretch(1)
        font_layout.addLayout(letter_spacing_layout)

        # Row: Text Color
        color_layout = QHBoxLayout()
        self.text_color_btn = QPushButton("Text Color")
        self.text_color_btn.setToolTip("Pick text color")
        self.text_color_btn.clicked.connect(self.choose_text_color)
        color_layout.addWidget(self.text_color_btn)
        color_layout.addStretch(1)
        font_layout.addLayout(color_layout)

        font_group.setLayout(font_layout)
        main_tab_layout.addWidget(font_group)

        # ----------- Action Buttons Row -----------
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch(1)
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setToolTip("Apply settings (Ctrl+S)")
        self.apply_btn.clicked.connect(self.apply_settings)
        self.ok_btn = QPushButton("OK")
        self.ok_btn.setToolTip("Apply and close (Enter)")
        self.ok_btn.clicked.connect(self.ok_and_close)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setToolTip("Cancel and close (Ctrl+Q)")
        self.cancel_btn.clicked.connect(self.close)
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch(1)
        main_tab_layout.addLayout(button_layout)

        # ----------- Line Spacing Tab -----------
        spacing_tab = QWidget()
        spacing_tab_layout = QVBoxLayout(spacing_tab)
        spacing_tab_layout.setContentsMargins(18, 24, 16, 8)

        spacing_group = QGroupBox("Line Spacing Options")
        spacing_group_layout = QVBoxLayout(spacing_group)

        self.line_spacing_combo = QComboBox()
        self.line_spacing_combo.addItems([
            "Default (1.0)", "1.05", "1.10", "1.15", "1.20", "1.30", "1.40", "1.50", "1.70", "2.00", "2.50", "3.00", "Custom"
        ])
        self.line_spacing_combo.setCurrentIndex(0)
        self.line_spacing_combo.setToolTip("Adjust line spacing")
        self.line_spacing_combo.currentIndexChanged.connect(self.on_line_spacing_combo_changed)
        spacing_group_layout.addWidget(QLabel("Choose line spacing:"))
        spacing_group_layout.addWidget(self.line_spacing_combo)

        self.custom_line_spacing_slider = QSlider(Qt.Horizontal)
        self.custom_line_spacing_slider.setRange(100, 400)
        self.custom_line_spacing_slider.setSingleStep(5)
        self.custom_line_spacing_slider.setValue(100)
        self.custom_line_spacing_slider.setToolTip("Custom line spacing (percent)")
        self.custom_line_spacing_slider.valueChanged.connect(self.on_custom_line_spacing_slider_changed)
        spacing_group_layout.addWidget(QLabel("Custom (percent):"))
        spacing_group_layout.addWidget(self.custom_line_spacing_slider)

        spacing_tab_layout.addWidget(spacing_group)
        spacing_tab_layout.addStretch(1)

        # Hide custom slider unless 'Custom' is chosen
        self.custom_line_spacing_slider.setVisible(False)

        # Add tabs
        self.tabs.addTab(main_tab, "Font & Preview")
        self.tabs.addTab(spacing_tab, "Line Spacing")

        # Keyboard shortcuts
        self.apply_btn.setShortcut('Ctrl+S')
        self.ok_btn.setShortcut('Return')
        self.cancel_btn.setShortcut('Ctrl+Q')

    def _schedule_update(self):
        """Schedule a delayed update to prevent rapid consecutive updates"""
        self._update_timer.start(100)  # 100ms delay

    def _delayed_update(self):
        """Perform the actual update after the delay"""
        self.update_font()

    def update_font(self):
        """Update the font and formatting of the preview text"""
        font = self.font_family_cb.currentFont()
        font.setPointSize(self.font_size_spin.value())
        font.setBold(self.bold_check.isChecked())
        font.setItalic(self.italic_check.isChecked())
        font.setUnderline(self.underline_check.isChecked())
        font.setLetterSpacing(QFont.AbsoluteSpacing, self.letter_spacing_spin.value())

        # Store cursor position and selection
        cursor = self.preview_text.textCursor()
        has_selection = cursor.hasSelection()
        selection_start = cursor.selectionStart()
        selection_end = cursor.selectionEnd()
        cursor_position = cursor.position()

        # Apply formatting to the entire document
        self.preview_text.selectAll()
        self.preview_text.setCurrentFont(font)
        self.preview_text.setTextColor(self.text_color)
        
        # Apply line spacing
        doc = self.preview_text.document()
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        
        # Create format with line spacing
        fmt = QTextCharFormat()
        fmt.setFont(font)
        fmt.setForeground(self.text_color)
        
        # Apply format to all blocks
        block = doc.firstBlock()
        while block.isValid():
            cursor = QTextCursor(block)
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.mergeCharFormat(fmt)
            
            # Set line spacing
            block_fmt = block.blockFormat()
            block_fmt.setLineHeight(int(self.line_spacing * 100), block_fmt.ProportionalHeight)
            cursor.setBlockFormat(block_fmt)
            
            block = block.next()
        
        cursor.endEditBlock()

        # Restore cursor position and selection
        cursor = self.preview_text.textCursor()
        if has_selection:
            cursor.setPosition(selection_start)
            cursor.setPosition(selection_end, QTextCursor.KeepAnchor)
        else:
            cursor.setPosition(cursor_position)
        self.preview_text.setTextCursor(cursor)

    def choose_text_color(self):
        color = QColorDialog.getColor(self.text_color, self, "Select Text Color")
        if color.isValid():
            self.text_color = color
            self.update_font()

    def on_line_spacing_combo_changed(self, idx):
        """Handle line spacing combo box changes"""
        combo_values = [
            1.0, 1.05, 1.10, 1.15, 1.20, 1.30, 1.40, 1.50, 1.70, 2.00, 2.50, 3.00
        ]
        if idx < len(combo_values):
            self.line_spacing = combo_values[idx]
            self.custom_line_spacing_slider.setVisible(False)
        else:
            # Custom option selected
            self.custom_line_spacing_slider.setVisible(True)
            self.line_spacing = self.custom_line_spacing_slider.value() / 100.0
        self._schedule_update()

    def on_custom_line_spacing_slider_changed(self, value):
        """Handle custom line spacing slider changes"""
        if self.line_spacing_combo.currentText() == "Custom":
            self.line_spacing = value / 100.0
            self._schedule_update()

    def load_config_to_ui(self):
        """Load configuration into UI elements"""
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    config = json.load(f)
                
                # Set font properties
                font = QFont(config.get("family", "Fira Code"), config.get("size", 12))
                font.setBold(config.get("bold", False))
                font.setItalic(config.get("italic", False))
                font.setUnderline(config.get("underline", False))
                
                # Update UI elements
                self.font_family_cb.setCurrentFont(font)
                self.font_size_spin.setValue(font.pointSize())
                self.bold_check.setChecked(font.bold())
                self.italic_check.setChecked(font.italic())
                self.underline_check.setChecked(font.underline())
                
                # Set colors and spacing
                self.text_color = QColor(config.get("text_color", "#ffffff"))
                self.line_spacing = config.get("line_spacing", 1.0)
                self.letter_spacing = config.get("letter_spacing", 0)
                self.letter_spacing_spin.setValue(self.letter_spacing)
                
                # Set line spacing UI
                combo_values = [1.0, 1.05, 1.10, 1.15, 1.20, 1.30, 1.40, 1.50, 1.70, 2.00, 2.50, 3.00]
                idx = 0
                for i, v in enumerate(combo_values):
                    if abs(self.line_spacing - v) < 0.001:
                        idx = i
                        break
                else:
                    idx = len(combo_values)  # Custom
                    self.custom_line_spacing_slider.setValue(int(self.line_spacing * 100))
                
                self.line_spacing_combo.setCurrentIndex(idx)
                self.custom_line_spacing_slider.setVisible(idx == len(combo_values))
                
            except Exception as e:
                print("Failed to load config:", e)
                QMessageBox.warning(self, "Configuration Error", 
                                  "Failed to load font configuration. Using default settings.")
        
        self._schedule_update()

    def apply_settings(self):
        """Apply the current font settings"""
        try:
            font = self.get_current_font()
            save_font_to_config(
                font,
                self.text_color,
                self.line_spacing,
                self.letter_spacing_spin.value()
            )
            self.settings_applied.emit(font)
            QMessageBox.information(self, "Font Editor", 
                                  "Settings have been applied successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                               f"Failed to apply settings: {str(e)}")

    def ok_and_close(self):
        """Apply settings and close the editor"""
        self.apply_settings()
        self.close()

    def closeEvent(self, event):
        """Handle window close event"""
        try:
            save_font_to_config(
                self.get_current_font(),
                self.text_color,
                self.line_spacing,
                self.letter_spacing_spin.value()
            )
        except Exception as e:
            print("Failed to save config on close:", e)
        super().closeEvent(event)

    def get_current_font(self):
        font = self.font_family_cb.currentFont()
        font.setPointSize(self.font_size_spin.value())
        font.setBold(self.bold_check.isChecked())
        font.setItalic(self.italic_check.isChecked())
        font.setUnderline(self.underline_check.isChecked())
        font.setLetterSpacing(QFont.AbsoluteSpacing, self.letter_spacing_spin.value())
        return font

    def force_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(24, 25, 26))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(35, 38, 50))
        palette.setColor(QPalette.AlternateBase, QColor(40, 40, 40))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(24, 25, 26))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(80, 250, 123))
        palette.setColor(QPalette.Highlight, QColor(80, 250, 123))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(palette)
        self.preview_text.setPalette(palette)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = FontEditor()
    editor.show()
    sys.exit(app.exec_())