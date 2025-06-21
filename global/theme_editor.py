import os
import json
import copy
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTabWidget, QWidget, QPushButton,
    QComboBox, QDialogButtonBox, QLabel, QColorDialog, QMessageBox, QHBoxLayout,
    QGroupBox, QFileDialog, QScrollArea
)
from PyQt5.QtGui import QColor
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
    def __init__(self, initial_color, label_text, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFixedSize(32, 32)
        self.set_color(initial_color)
        self.setToolTip(label_text)
    
    def set_color(self, color):
        self._color = QColor(color)
        self.setStyleSheet(
            f"background-color: {self._color.name()}; border: 1.5px solid #888; border-radius: 8px;"
        )
    
    def get_color(self):
        return self._color.name()

class ThemeEditorDialog(QDialog):
    def __init__(self, parent=None, theme_data=None, theme_key=None):
        super().__init__(parent)
        self.setWindowTitle("Theme Editor")
        self.setMinimumSize(660, 540)
        self.setStyleSheet("""
            QDialog { background: #262b32; color: #eee; }
            QLabel { font-size: 14px; }
            QLineEdit, QComboBox { background: #23262c; color: #eee; border: 1px solid #444; border-radius: 6px; padding: 5px;}
            QPushButton { padding: 4px 10px; font-size: 13px; border-radius: 6px; }
            QPushButton:focus { outline: 2px solid #4c8aff; }
            QGroupBox { border: 1.5px solid #555; border-radius: 10px; padding: 8px; margin-top: 8px; }
            QTabWidget::pane { border: 1.5px solid #444; border-radius: 8px; }
            QTabBar::tab { min-width: 120px; min-height: 28px; margin: 2px 8px 2px 0; padding: 4px 0; }
            QTabBar::tab:selected { background: #4c8aff; color: #fff; }
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
        layout.setSpacing(12)

        # Info
        info_box = QGroupBox("Theme Info")
        info_layout = QFormLayout(info_box)
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

        # Tab for UI, Editor, Syntax colors
        self.tab_widget = QTabWidget()
        self.make_color_tab("palette", "UI Colors")
        self.make_color_tab("editor", "Editor Colors")
        self.make_color_tab("syntax", "Syntax Colors")
        layout.addWidget(self.tab_widget)

        # Base theme selector
        base_group = QGroupBox("Base Theme")
        base_layout = QHBoxLayout(base_group)
        self.base_theme_combo = QComboBox()
        for key, theme in DEFAULT_THEMES.items():
            self.base_theme_combo.addItem(theme["name"], key)
        base_layout.addWidget(QLabel("Start from:"))
        base_layout.addWidget(self.base_theme_combo)
        self.base_theme_combo.currentIndexChanged.connect(self.on_base_theme_changed)

        # Import/Export buttons, spaced apart to avoid clashing
        import_btn = QPushButton("Import Theme...")
        import_btn.clicked.connect(self.import_theme)
        export_btn = QPushButton("Export Theme...")
        export_btn.clicked.connect(self.export_theme)
        base_layout.addStretch()
        base_layout.addWidget(import_btn)
        base_layout.addWidget(export_btn)
        layout.addWidget(base_group)

        # Save/cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Save Theme")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        layout.addStretch(1)

    def make_color_tab(self, category, label):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        area_widget = QWidget()
        area_layout = QVBoxLayout(area_widget)
        self._color_buttons[category] = {}

        for key, value in self.theme_data[category].items():
            row = QHBoxLayout()
            color_btn = ColorButton(value, key.replace('_', ' ').title())
            color_btn.clicked.connect(lambda _, k=key, c=category: self.choose_color(c, k))
            self._color_buttons[category][key] = color_btn
            row.addWidget(color_btn)
            row.addWidget(QLabel(key.replace("_", " ").title()))
            row.addStretch()
            area_layout.addLayout(row)
        area_layout.addStretch()
        scroll_area.setWidget(area_widget)
        self.tab_widget.addTab(scroll_area, label)

    def choose_color(self, category, key):
        current_color = QColor(self.theme_data[category][key])
        color = QColorDialog.getColor(current_color, self, f"Choose {key.replace('_', ' ').title()} Color")
        if color.isValid():
            hex_color = color.name()
            self.theme_data[category][key] = hex_color
            self._color_buttons[category][key].set_color(hex_color)

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
            for cat in ["palette", "editor", "syntax"]:
                for key, btn in self._color_buttons[cat].items():
                    btn.set_color(self.theme_data[cat][key])

    def accept(self):
        key = self.theme_key_edit.text().strip()
        name = self.theme_name_edit.text().strip()
        desc = self.theme_desc_edit.text().strip()
        if not key or " " in key or not name:
            QMessageBox.warning(self, "Invalid Input", "Theme key must be unique and contain no spaces. Name is required.")
            return
        if key in DEFAULT_THEMES and not self.is_editing_existing:
            QMessageBox.warning(self, "Invalid Key", "Theme key collides with a built-in theme.")
            return
        self.theme_key = key
        self.theme_data["name"] = name
        self.theme_data["description"] = desc
        self._custom_themes = load_custom_themes()
        self._custom_themes[key] = copy.deepcopy(self.theme_data)
        if not save_custom_themes(self._custom_themes):
            QMessageBox.warning(self, "Error", "Could not save custom theme!")
            return
        super().accept()

    def import_theme(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Theme", "", "JSON Files (*.json)")
        if path:
            try:
                with open(path, "r") as f:
                    theme_obj = json.load(f)
                if isinstance(theme_obj, dict) and "palette" in theme_obj and "editor" in theme_obj and "syntax" in theme_obj:
                    imported = theme_obj
                    key = theme_obj.get("key", None) or theme_obj.get("name", "imported_theme").replace(" ", "_").lower()
                    self.theme_data = imported
                    self.theme_key = key
                    self.theme_key_edit.setText(key)
                    self.theme_name_edit.setText(imported.get("name", "Imported"))
                    self.theme_desc_edit.setText(imported.get("description", "Imported theme"))
                    for cat in ["palette", "editor", "syntax"]:
                        for key2, btn in self._color_buttons[cat].items():
                            btn.set_color(self.theme_data[cat][key2])
                elif isinstance(theme_obj, dict):
                    QMessageBox.information(self, "Imported", "Multiple themes found, using the first one.")
                    theme_list = list(theme_obj.values())
                    imported = theme_list[0]
                    key = imported.get("key", None) or imported.get("name", "imported_theme").replace(" ", "_").lower()
                    self.theme_data = imported
                    self.theme_key = key
                    self.theme_key_edit.setText(key)
                    self.theme_name_edit.setText(imported.get("name", "Imported"))
                    self.theme_desc_edit.setText(imported.get("description", "Imported theme"))
                    for cat in ["palette", "editor", "syntax"]:
                        for key2, btn in self._color_buttons[cat].items():
                            btn.set_color(self.theme_data[cat][key2])
                else:
                    QMessageBox.warning(self, "Import Failed", "File does not contain a valid theme object.")
            except Exception as e:
                QMessageBox.warning(self, "Import Failed", f"Could not import theme: {e}")

    def export_theme(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Theme", f"{self.theme_key_edit.text() or 'my_theme'}.json", "JSON Files (*.json)")
        if path:
            export_obj = copy.deepcopy(self.theme_data)
            export_obj["key"] = self.theme_key_edit.text()
            try:
                with open(path, "w") as f:
                    json.dump(export_obj, f, indent=2)
                QMessageBox.information(self, "Exported", f"Theme exported to {os.path.basename(path)}")
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", f"Could not export theme: {e}")

    def get_theme_data(self):
        return copy.deepcopy(self.theme_data)

    def get_theme_key(self):
        return self.theme_key