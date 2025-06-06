import os
import json
import copy
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTabWidget, QWidget, QPushButton,
    QComboBox, QDialogButtonBox, QLabel, QColorDialog, QMessageBox, QHBoxLayout,
    QScrollArea, QGroupBox, QFrame, QSizePolicy
)
from PyQt5.QtGui import QColor, QFont, QPalette
from PyQt5.QtCore import Qt

from default_themes import DEFAULT_THEMES

USER_CUSTOM_THEMES_PATH = "user_custom_themes.json"

def load_custom_themes():
    if os.path.exists(USER_CUSTOM_THEMES_PATH):
        try:
            with open(USER_CUSTOM_THEMES_PATH, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading custom themes: {e}")
    return {}

def save_custom_themes(themes):
    try:
        with open(USER_CUSTOM_THEMES_PATH, "w") as f:
            json.dump(themes, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving custom themes: {e}")
        return False

class ColorButton(QPushButton):
    def __init__(self, initial_color, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFixedSize(40, 40)
        self.set_color(initial_color)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(self.styleSheet() + "border: 2px solid #888; border-radius: 8px;")
    
    def set_color(self, color):
        self._color = QColor(color)
        self.setStyleSheet(
            f"background-color: {self._color.name()}; border: 2px solid #888; border-radius: 8px;"
        )
    
    def get_color(self):
        return self._color.name()

class ThemeEditorDialog(QDialog):
    def __init__(self, parent=None, theme_data=None, theme_key=None):
        super().__init__(parent)
        self.setWindowTitle("Theme Editor")
        self.setMinimumSize(600, 640)
        self.setStyleSheet("""
            QDialog { background: #23272e; color: #eee; }
            QLabel  { font-size: 15px; }
            QLineEdit, QComboBox { background: #262b32; color: #eee; border: 1px solid #444; border-radius: 6px; padding: 5px; font-size: 15px;}
            QPushButton { padding: 5px 14px; font-size: 15px; border-radius: 7px; }
            QPushButton:focus { outline: 2px solid #4c8aff; }
            QTabWidget::pane { border: 1px solid #444; border-radius: 7px; padding: 3px;}
            QTabBar::tab { background: #262b32; border: 1px solid #444; border-radius: 7px; min-width: 120px; min-height: 28px; margin: 1px;}
            QTabBar::tab:selected { background: #4c8aff; color: #fff; }
            QGroupBox { border: 1.5px solid #555; border-radius: 10px; padding: 8px; margin-top: 8px; }
            QScrollArea { border: none; }
        """)
        self._custom_themes = load_custom_themes()
        if theme_data:
            self.theme_data = copy.deepcopy(theme_data)
            self.theme_key = theme_key
            self.is_editing_existing = theme_key in self._custom_themes
        else:
            self.theme_data = copy.deepcopy(DEFAULT_THEMES["dark"])
            self.theme_key = "custom_theme"
            self.is_editing_existing = False
        self._color_buttons = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(18)

        # Modern title header
        header = QLabel("🎨 <b>Edit or Create Theme</b>")
        header.setFont(QFont("Segoe UI", 22, QFont.Bold))
        header.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        layout.addWidget(header)

        # Info
        info_box = QGroupBox()
        info_layout = QFormLayout(info_box)
        info_box.setStyleSheet("QGroupBox { background: #262b32; }")
        self.theme_key_edit = QLineEdit(self.theme_key)
        self.theme_key_edit.setPlaceholderText("Unique theme key (no spaces)")
        info_layout.addRow(QLabel("Theme Key:"), self.theme_key_edit)
        self.theme_name_edit = QLineEdit(self.theme_data["name"])
        self.theme_name_edit.setPlaceholderText("Display name")
        info_layout.addRow(QLabel("Theme Name:"), self.theme_name_edit)
        self.theme_desc_edit = QLineEdit(self.theme_data["description"])
        self.theme_desc_edit.setPlaceholderText("Short description")
        info_layout.addRow(QLabel("Description:"), self.theme_desc_edit)
        layout.addWidget(info_box)

        # Tabs for color editing, with scrollable area for many colors
        self.tab_widget = QTabWidget()
        self.make_color_tab("palette", "UI Colors")
        self.make_color_tab("editor", "Editor Colors")
        self.make_color_tab("syntax", "Syntax Colors")
        layout.addWidget(self.tab_widget)

        # Base theme selector with preview
        base_group = QGroupBox("Base Theme")
        base_layout = QHBoxLayout(base_group)
        self.base_theme_combo = QComboBox()
        for key, theme in DEFAULT_THEMES.items():
            self.base_theme_combo.addItem(theme["name"], key)
        base_layout.addWidget(QLabel("Start from:"))
        base_layout.addWidget(self.base_theme_combo)
        preview_btn = QPushButton("Preview Base Theme Colors")
        preview_btn.clicked.connect(self.preview_base_theme)
        base_layout.addWidget(preview_btn)
        self.base_theme_combo.currentIndexChanged.connect(self.on_base_theme_changed)
        layout.addWidget(base_group)

        # Save/cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Save Theme")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        layout.addStretch(1)

    def make_color_tab(self, category, label):
        group = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(group)
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(10)
        self._color_buttons[category] = {}
        for key, value in self.theme_data[category].items():
            row = QHBoxLayout()
            color_btn = ColorButton(value)
            color_btn.clicked.connect(lambda _, k=key, c=category: self.choose_color(c, k))
            self._color_buttons[category][key] = color_btn
            row.addWidget(QLabel(f"{key.replace('_',' ').title()}:"))
            row.addWidget(color_btn)
            row.addStretch(1)
            group_layout.addLayout(row)
        group_layout.addStretch(1)
        self.tab_widget.addTab(scroll, label)

    def choose_color(self, category, key):
        current_color = QColor(self.theme_data[category][key])
        color = QColorDialog.getColor(current_color, self, f"Choose {key.replace('_', ' ').title()} Color")
        if color.isValid():
            hex_color = color.name()
            self.theme_data[category][key] = hex_color
            self._color_buttons[category][key].set_color(hex_color)

    def preview_base_theme(self):
        key = self.base_theme_combo.currentData()
        theme = DEFAULT_THEMES[key]
        preview = ""
        preview += f"<b>Name:</b> {theme['name']}<br><b>Description:</b> {theme['description']}<br><br>"
        preview += "<b>UI Colors:</b><br>"
        for k, v in theme["palette"].items():
            preview += f"<span style='display:inline-block; width:18px; height:18px; background:{v}; border:1px solid #888; margin:2px;'></span> {k}: {v}<br>"
        preview += "<br><b>Editor Colors:</b><br>"
        for k, v in theme["editor"].items():
            preview += f"<span style='display:inline-block; width:18px; height:18px; background:{v}; border:1px solid #888; margin:2px;'></span> {k}: {v}<br>"
        preview += "<br><b>Syntax Colors:</b><br>"
        for k, v in theme["syntax"].items():
            preview += f"<span style='display:inline-block; width:18px; height:18px; background:{v}; border:1px solid #888; margin:2px;'></span> {k}: {v}<br>"
        QMessageBox.information(self, "Base Theme Preview", preview)

    def on_base_theme_changed(self, index):
        base_key = self.base_theme_combo.itemData(index)
        base_theme = DEFAULT_THEMES[base_key]
        confirm = QMessageBox.question(
            self,
            "Confirm Theme Change",
            f"This will replace all current colors with those from '{base_theme['name']}'. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            name = self.theme_name_edit.text()
            desc = self.theme_desc_edit.text()
            self.theme_data = copy.deepcopy(base_theme)
            self.theme_data["name"] = name
            self.theme_data["description"] = desc
            # Update color buttons
            for cat in ["palette", "editor", "syntax"]:
                for key, btn in self._color_buttons[cat].items():
                    btn.set_color(self.theme_data[cat][key])

    def accept(self):
        # Validation
        key = self.theme_key_edit.text().strip()
        name = self.theme_name_edit.text().strip()
        desc = self.theme_desc_edit.text().strip()
        if not key or " " in key or not name:
            QMessageBox.warning(self, "Invalid Input", "Theme key must be unique and contain no spaces. Name is required.")
            return
        if key in DEFAULT_THEMES and not self.is_editing_existing:
            QMessageBox.warning(self, "Invalid Key", "Theme key collides with a built-in theme.")
            return
        # Update theme data
        self.theme_key = key
        self.theme_data["name"] = name
        self.theme_data["description"] = desc
        # Store in custom themes file
        self._custom_themes = load_custom_themes()
        self._custom_themes[key] = copy.deepcopy(self.theme_data)
        if not save_custom_themes(self._custom_themes):
            QMessageBox.warning(self, "Error", "Could not save custom theme!")
            return
        super().accept()

    def get_theme_data(self):
        return copy.deepcopy(self.theme_data)

    def get_theme_key(self):
        return self.theme_key