import json
import os
import copy
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QFormLayout, QDialogButtonBox, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject

from default_themes import DEFAULT_THEMES  # <- You must have default_themes.py in the same folder

THEME_CONFIG_PATH = "theme_config.json"
USER_PREFS_PATH = "user_prefs.json"

def load_themes():
    if os.path.exists(THEME_CONFIG_PATH):
        try:
            with open(THEME_CONFIG_PATH, "r") as f:
                themes = json.load(f)
                for key, theme in DEFAULT_THEMES.items():
                    if key not in themes:
                        themes[key] = theme
                return themes
        except Exception as e:
            print(f"Error loading theme config: {e}")
    return copy.deepcopy(DEFAULT_THEMES)

def save_themes(themes):
    try:
        with open(THEME_CONFIG_PATH, "w") as f:
            json.dump(themes, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving theme config: {e}")
        return False

def load_user_prefs():
    if os.path.exists(USER_PREFS_PATH):
        try:
            with open(USER_PREFS_PATH, "r") as f:
                prefs = json.load(f)
                return prefs
        except Exception as e:
            print(f"Error loading user preferences: {e}")
    return {}

def save_user_prefs(prefs):
    try:
        with open(USER_PREFS_PATH, "w") as f:
            json.dump(prefs, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving user preferences: {e}")
        return False

def apply_theme_palette(app, theme_data):
    palette = QPalette()
    palette_data = theme_data["palette"]
    palette.setColor(QPalette.Window, QColor(palette_data["window"]))
    palette.setColor(QPalette.WindowText, QColor(palette_data["window_text"]))
    palette.setColor(QPalette.Base, QColor(palette_data["base"]))
    palette.setColor(QPalette.AlternateBase, QColor(palette_data["alternate_base"]))
    palette.setColor(QPalette.Text, QColor(palette_data["text"]))
    palette.setColor(QPalette.Button, QColor(palette_data["button"]))
    palette.setColor(QPalette.ButtonText, QColor(palette_data["button_text"]))
    palette.setColor(QPalette.BrightText, QColor(palette_data["bright_text"]))
    palette.setColor(QPalette.Highlight, QColor(palette_data["highlight"]))
    palette.setColor(QPalette.HighlightedText, QColor(palette_data["highlight_text"]))
    palette.setColor(QPalette.Link, QColor(palette_data["link"]))
    palette.setColor(QPalette.Dark, QColor(palette_data["dark"]))
    palette.setColor(QPalette.Mid, QColor(palette_data["mid"]))
    palette.setColor(QPalette.Midlight, QColor(palette_data["midlight"]))
    palette.setColor(QPalette.Light, QColor(palette_data["light"]))
    app.setPalette(palette)
    return theme_data

def get_editor_styles(theme_data):
    editor_data = theme_data["editor"]
    style = f"""
    QTextEdit {{
        background-color: {editor_data["background"]};
        color: {editor_data["foreground"]};
        selection-background-color: {editor_data["selection_background"]};
        selection-color: {editor_data["selection_foreground"]};
    }}
    """
    return style

class ThemeManager(QObject):
    themeChanged = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.themes = load_themes()
        self.current_theme_key = self._load_last_theme_key()
        self.current_theme_data = self.themes.get(self.current_theme_key, self.themes["dark"])

    def _load_last_theme_key(self):
        prefs = load_user_prefs()
        key = prefs.get("theme", None)
        if key in self.themes:
            return key
        return "dark"

    def _save_last_theme_key(self, theme_key):
        prefs = load_user_prefs()
        prefs["theme"] = theme_key
        save_user_prefs(prefs)

    def apply_theme(self, app, theme_key):
        if theme_key not in self.themes:
            theme_key = "dark"
        theme_data = self.themes[theme_key]
        self.current_theme_key = theme_key
        self.current_theme_data = theme_data
        apply_theme_palette(app, theme_data)
        self.themeChanged.emit(theme_data)
        self._save_last_theme_key(theme_key)
        return theme_data

    def get_theme(self, key=None):
        if key is None:
            key = self.current_theme_key
        return self.themes.get(key, self.themes["dark"])

theme_manager_singleton = ThemeManager()

class ThemeManagerDialog(QDialog):
    def __init__(self, parent=None, current_theme_key="dark"):
        super().__init__(parent)
        self.setWindowTitle("Theme Manager")
        self.resize(600, 400)
        self.themes = copy.deepcopy(theme_manager_singleton.themes)
        self.current_theme_key = current_theme_key
        self.selected_theme_key = current_theme_key
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.theme_list = QListWidget()
        self.update_theme_list()
        self.theme_list.currentRowChanged.connect(self.on_theme_selected)
        layout.addWidget(self.theme_list)

        details_layout = QFormLayout()
        self.theme_name_label = QLabel()
        self.theme_desc_label = QLabel()
        details_layout.addRow("Name:", self.theme_name_label)
        details_layout.addRow("Description:", self.theme_desc_label)
        layout.addLayout(details_layout)

        button_layout = QHBoxLayout()
        self.new_btn = QPushButton("New Theme")
        self.new_btn.clicked.connect(self.create_new_theme)
        button_layout.addWidget(self.new_btn)

        self.edit_btn = QPushButton("Edit Theme")
        self.edit_btn.clicked.connect(self.edit_theme)
        button_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete Theme")
        self.delete_btn.clicked.connect(self.delete_theme)
        button_layout.addWidget(self.delete_btn)

        self.apply_btn = QPushButton("Apply Theme")
        self.apply_btn.clicked.connect(self.apply_theme)
        button_layout.addWidget(self.apply_btn)

        layout.addLayout(button_layout)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        for i in range(self.theme_list.count()):
            item = self.theme_list.item(i)
            if item.data(Qt.UserRole) == self.current_theme_key:
                self.theme_list.setCurrentItem(item)
                break

    def update_theme_list(self):
        self.theme_list.clear()
        for key, theme in self.themes.items():
            item = QListWidgetItem(theme["name"])
            item.setData(Qt.UserRole, key)
            self.theme_list.addItem(item)

    def on_theme_selected(self, row):
        if row < 0:
            return
        item = self.theme_list.item(row)
        theme_key = item.data(Qt.UserRole)
        self.selected_theme_key = theme_key
        theme = self.themes[theme_key]
        self.theme_name_label.setText(theme["name"])
        self.theme_desc_label.setText(theme["description"])
        is_default = theme_key in DEFAULT_THEMES
        self.delete_btn.setEnabled(not is_default)

    def create_new_theme(self):
        # Use the ThemeEditorDialog from theme_editor.py
        try:
            from theme_editor import ThemeEditorDialog
        except ImportError:
            QMessageBox.warning(self, "Error", "theme_editor.py not found or import failed.")
            return
        dialog = ThemeEditorDialog(self)
        if dialog.exec_():
            new_theme = dialog.get_theme_data()
            new_key = dialog.get_theme_key()
            if new_key in self.themes:
                i = 1
                while f"{new_key}_{i}" in self.themes:
                    i += 1
                new_key = f"{new_key}_{i}"
            self.themes[new_key] = copy.deepcopy(new_theme)
            save_themes(self.themes)
            self.update_theme_list()
            for i in range(self.theme_list.count()):
                item = self.theme_list.item(i)
                if item.data(Qt.UserRole) == new_key:
                    self.theme_list.setCurrentItem(item)
                    break

    def edit_theme(self):
        if not self.selected_theme_key:
            return
        if self.selected_theme_key in DEFAULT_THEMES:
            QMessageBox.information(
                self, "Cannot Edit Default Theme",
                "Default themes cannot be edited. Please create a new theme based on this one."
            )
            return
        try:
            from theme_editor import ThemeEditorDialog
        except ImportError:
            QMessageBox.warning(self, "Error", "theme_editor.py not found or import failed.")
            return
        dialog = ThemeEditorDialog(self, self.themes[self.selected_theme_key], self.selected_theme_key)
        if dialog.exec_():
            updated_theme = dialog.get_theme_data()
            updated_key = dialog.get_theme_key()
            if updated_key != self.selected_theme_key:
                del self.themes[self.selected_theme_key]
            self.themes[updated_key] = copy.deepcopy(updated_theme)
            save_themes(self.themes)
            self.update_theme_list()
            for i in range(self.theme_list.count()):
                item = self.theme_list.item(i)
                if item.data(Qt.UserRole) == updated_key:
                    self.theme_list.setCurrentItem(item)
                    break

    def delete_theme(self):
        if not self.selected_theme_key:
            return
        if self.selected_theme_key in DEFAULT_THEMES:
            QMessageBox.information(
                self, "Cannot Delete Default Theme",
                "Default themes cannot be deleted."
            )
            return
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the theme '{self.themes[self.selected_theme_key]['name']}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            del self.themes[self.selected_theme_key]
            save_themes(self.themes)
            self.update_theme_list()
            if self.theme_list.count() > 0:
                self.theme_list.setCurrentRow(0)

    def apply_theme(self):
        if not self.selected_theme_key:
            return
        self.current_theme_key = self.selected_theme_key
        prefs = load_user_prefs()
        prefs["theme"] = self.current_theme_key
        save_user_prefs(prefs)

    def get_selected_theme_key(self):
        return self.current_theme_key