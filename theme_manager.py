import json
import os
from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QColorDialog, QFormLayout,
    QLineEdit, QMessageBox, QComboBox, QDialogButtonBox
)
from PyQt5.QtCore import Qt

THEME_CONFIG_PATH = "theme_config.json"

# Default themes
DEFAULT_THEMES = {
    "dark": {
        "name": "Dark Theme",
        "description": "Default dark theme with blue accents",
        "palette": {
            "window": "#2b2b2b",
            "window_text": "#ffffff",
            "base": "#222226",
            "alternate_base": "#323232",
            "text": "#ffffff",
            "button": "#353535",
            "button_text": "#ffffff",
            "bright_text": "#00b4ff",
            "highlight": "#2a82da",
            "highlight_text": "#ffffff",
            "link": "#2a82da",
            "dark": "#1e1e1e",
            "mid": "#3c3c3c",
            "midlight": "#494949",
            "light": "#5c5c5c"
        },
        "editor": {
            "background": "#222226",
            "foreground": "#ffffff",
            "selection_background": "#264f78",
            "selection_foreground": "#ffffff",
            "line_number_background": "#222226",
            "line_number_foreground": "#909090",
            "current_line": "#2a2a2a",
            "search_result": "#613214"
        },
        "syntax": {
            "keyword": "#569cd6",
            "operator": "#d4d4d4",
            "brace": "#d4d4d4",
            "defclass": "#4ec9b0",
            "string": "#ce9178",
            "string2": "#ce9178",
            "comment": "#6a9955",
            "self": "#569cd6",
            "numbers": "#b5cea8",
            "background": "#222226",
            "foreground": "#d4d4d4",
            "functioncall": "#dcdcaa"
        }
    },
    "light": {
        "name": "Light Theme",
        "description": "Default light theme with blue accents",
        "palette": {
            "window": "#f0f0f0",
            "window_text": "#000000",
            "base": "#ffffff",
            "alternate_base": "#f7f7f7",
            "text": "#000000",
            "button": "#e0e0e0",
            "button_text": "#000000",
            "bright_text": "#0000ff",
            "highlight": "#308cc6",
            "highlight_text": "#ffffff",
            "link": "#0000ff",
            "dark": "#a0a0a0",
            "mid": "#b0b0b0",
            "midlight": "#c0c0c0",
            "light": "#d0d0d0"
        },
        "editor": {
            "background": "#ffffff",
            "foreground": "#000000",
            "selection_background": "#add6ff",
            "selection_foreground": "#000000",
            "line_number_background": "#f0f0f0",
            "line_number_foreground": "#707070",
            "current_line": "#f5f5f5",
            "search_result": "#f8e8a0"
        },
        "syntax": {
            "keyword": "#0000ff",
            "operator": "#000000",
            "brace": "#000000",
            "defclass": "#008080",
            "string": "#a31515",
            "string2": "#a31515",
            "comment": "#008000",
            "self": "#0000ff",
            "numbers": "#098658",
            "background": "#ffffff",
            "foreground": "#000000",
            "functioncall": "#795e26"
        }
    },
    "monokai": {
        "name": "Monokai",
        "description": "Dark theme inspired by Monokai",
        "palette": {
            "window": "#272822",
            "window_text": "#f8f8f2",
            "base": "#272822",
            "alternate_base": "#2d2e27",
            "text": "#f8f8f2",
            "button": "#32332b",
            "button_text": "#f8f8f2",
            "bright_text": "#f92672",
            "highlight": "#49483e",
            "highlight_text": "#f8f8f2",
            "link": "#66d9ef",
            "dark": "#1e1f1c",
            "mid": "#3b3c35",
            "midlight": "#474842",
            "light": "#5e5f58"
        },
        "editor": {
            "background": "#272822",
            "foreground": "#f8f8f2",
            "selection_background": "#49483e",
            "selection_foreground": "#f8f8f2",
            "line_number_background": "#272822",
            "line_number_foreground": "#90908a",
            "current_line": "#3e3d32",
            "search_result": "#4a410d"
        },
        "syntax": {
            "keyword": "#f92672",
            "operator": "#f8f8f2",
            "brace": "#f8f8f2",
            "defclass": "#a6e22e",
            "string": "#e6db74",
            "string2": "#e6db74",
            "comment": "#75715e",
            "self": "#fd971f",
            "numbers": "#ae81ff",
            "background": "#272822",
            "foreground": "#f8f8f2",
            "functioncall": "#66d9ef"
        }
    },
    "solarized_dark": {
        "name": "Solarized Dark",
        "description": "Dark theme based on Solarized color scheme",
        "palette": {
            "window": "#002b36",
            "window_text": "#839496",
            "base": "#073642",
            "alternate_base": "#073642",
            "text": "#839496",
            "button": "#073642",
            "button_text": "#839496",
            "bright_text": "#cb4b16",
            "highlight": "#268bd2",
            "highlight_text": "#fdf6e3",
            "link": "#268bd2",
            "dark": "#002b36",
            "mid": "#073642",
            "midlight": "#586e75",
            "light": "#657b83"
        },
        "editor": {
            "background": "#002b36",
            "foreground": "#839496",
            "selection_background": "#073642",
            "selection_foreground": "#93a1a1",
            "line_number_background": "#002b36",
            "line_number_foreground": "#586e75",
            "current_line": "#073642",
            "search_result": "#657b83"
        },
        "syntax": {
            "keyword": "#cb4b16",
            "operator": "#839496",
            "brace": "#839496",
            "defclass": "#b58900",
            "string": "#2aa198",
            "string2": "#2aa198",
            "comment": "#586e75",
            "self": "#d33682",
            "numbers": "#d33682",
            "background": "#002b36",
            "foreground": "#839496",
            "functioncall": "#268bd2"
        }
    },
    "solarized_light": {
        "name": "Solarized Light",
        "description": "Light theme based on Solarized color scheme",
        "palette": {
            "window": "#fdf6e3",
            "window_text": "#657b83",
            "base": "#eee8d5",
            "alternate_base": "#eee8d5",
            "text": "#657b83",
            "button": "#eee8d5",
            "button_text": "#657b83",
            "bright_text": "#cb4b16",
            "highlight": "#268bd2",
            "highlight_text": "#fdf6e3",
            "link": "#268bd2",
            "dark": "#93a1a1",
            "mid": "#839496",
            "midlight": "#93a1a1",
            "light": "#eee8d5"
        },
        "editor": {
            "background": "#fdf6e3",
            "foreground": "#657b83",
            "selection_background": "#eee8d5",
            "selection_foreground": "#586e75",
            "line_number_background": "#fdf6e3",
            "line_number_foreground": "#93a1a1",
            "current_line": "#eee8d5",
            "search_result": "#93a1a1"
        },
        "syntax": {
            "keyword": "#cb4b16",
            "operator": "#657b83",
            "brace": "#657b83",
            "defclass": "#b58900",
            "string": "#2aa198",
            "string2": "#2aa198",
            "comment": "#93a1a1",
            "self": "#d33682",
            "numbers": "#d33682",
            "background": "#fdf6e3",
            "foreground": "#657b83",
            "functioncall": "#268bd2"
        }
    },
    "dracula": {
        "name": "Dracula",
        "description": "Dark theme based on Dracula color scheme",
        "palette": {
            "window": "#282a36",
            "window_text": "#f8f8f2",
            "base": "#282a36",
            "alternate_base": "#282a36",
            "text": "#f8f8f2",
            "button": "#44475a",
            "button_text": "#f8f8f2",
            "bright_text": "#ff79c6",
            "highlight": "#44475a",
            "highlight_text": "#f8f8f2",
            "link": "#8be9fd",
            "dark": "#21222c",
            "mid": "#44475a",
            "midlight": "#6272a4",
            "light": "#6272a4"
        },
        "editor": {
            "background": "#282a36",
            "foreground": "#f8f8f2",
            "selection_background": "#44475a",
            "selection_foreground": "#f8f8f2",
            "line_number_background": "#282a36",
            "line_number_foreground": "#6272a4",
            "current_line": "#44475a",
            "search_result": "#6272a4"
        },
        "syntax": {
            "keyword": "#ff79c6",
            "operator": "#f8f8f2",
            "brace": "#f8f8f2",
            "defclass": "#50fa7b",
            "string": "#f1fa8c",
            "string2": "#f1fa8c",
            "comment": "#6272a4",
            "self": "#bd93f9",
            "numbers": "#bd93f9",
            "background": "#282a36",
            "foreground": "#f8f8f2",
            "functioncall": "#8be9fd"
        }
    },
    "nord": {
        "name": "Nord",
        "description": "Dark theme based on Nord color scheme",
        "palette": {
            "window": "#2e3440",
            "window_text": "#d8dee9",
            "base": "#3b4252",
            "alternate_base": "#434c5e",
            "text": "#d8dee9",
            "button": "#434c5e",
            "button_text": "#d8dee9",
            "bright_text": "#88c0d0",
            "highlight": "#5e81ac",
            "highlight_text": "#eceff4",
            "link": "#88c0d0",
            "dark": "#2e3440",
            "mid": "#3b4252",
            "midlight": "#434c5e",
            "light": "#4c566a"
        },
        "editor": {
            "background": "#2e3440",
            "foreground": "#d8dee9",
            "selection_background": "#4c566a",
            "selection_foreground": "#eceff4",
            "line_number_background": "#2e3440",
            "line_number_foreground": "#4c566a",
            "current_line": "#3b4252",
            "search_result": "#5e81ac"
        },
        "syntax": {
            "keyword": "#81a1c1",
            "operator": "#d8dee9",
            "brace": "#d8dee9",
            "defclass": "#8fbcbb",
            "string": "#a3be8c",
            "string2": "#a3be8c",
            "comment": "#4c566a",
            "self": "#b48ead",
            "numbers": "#b48ead",
            "background": "#2e3440",
            "foreground": "#d8dee9",
            "functioncall": "#88c0d0"
        }
    }
}

def load_themes():
    """Load themes from the config file or use defaults if file doesn't exist."""
    if os.path.exists(THEME_CONFIG_PATH):
        try:
            with open(THEME_CONFIG_PATH, "r") as f:
                themes = json.load(f)
                # Ensure default themes are always available
                for key, theme in DEFAULT_THEMES.items():
                    if key not in themes:
                        themes[key] = theme
                return themes
        except Exception as e:
            print(f"Error loading theme config: {e}")
    return DEFAULT_THEMES.copy()

def save_themes(themes):
    """Save themes to the config file."""
    try:
        with open(THEME_CONFIG_PATH, "w") as f:
            json.dump(themes, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving theme config: {e}")
        return False

def apply_theme(app, theme_data):
    """Apply the theme to the application."""
    palette = QPalette()
    
    # Set palette colors
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
    
    # Set additional palette colors
    palette.setColor(QPalette.Dark, QColor(palette_data["dark"]))
    palette.setColor(QPalette.Mid, QColor(palette_data["mid"]))
    palette.setColor(QPalette.Midlight, QColor(palette_data["midlight"]))
    palette.setColor(QPalette.Light, QColor(palette_data["light"]))
    
    # Apply palette to application
    app.setPalette(palette)
    
    return theme_data

def get_editor_styles(theme_data):
    """Get CSS styles for the editor based on the theme."""
    editor_data = theme_data["editor"]
    syntax_data = theme_data["syntax"]
    
    # Basic editor style
    style = f"""
    QTextEdit {{
        background-color: {editor_data["background"]};
        color: {editor_data["foreground"]};
        selection-background-color: {editor_data["selection_background"]};
        selection-color: {editor_data["selection_foreground"]};
    }}
    """
    
    return style

class ThemeManagerDialog(QDialog):
    def __init__(self, parent=None, current_theme_key="dark"):
        super().__init__(parent)
        self.setWindowTitle("Theme Manager")
        self.resize(600, 400)
        self.themes = load_themes()
        self.current_theme_key = current_theme_key
        self.selected_theme_key = current_theme_key
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Theme selection list
        self.theme_list = QListWidget()
        self.update_theme_list()
        self.theme_list.currentRowChanged.connect(self.on_theme_selected)
        layout.addWidget(self.theme_list)
        
        # Theme details
        details_layout = QFormLayout()
        self.theme_name_label = QLabel()
        self.theme_desc_label = QLabel()
        details_layout.addRow("Name:", self.theme_name_label)
        details_layout.addRow("Description:", self.theme_desc_label)
        layout.addLayout(details_layout)
        
        # Buttons
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
        
        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Select current theme
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
        
        # Disable edit/delete for default themes
        is_default = theme_key in DEFAULT_THEMES
        self.delete_btn.setEnabled(not is_default)
    
    def create_new_theme(self):
        dialog = ThemeEditorDialog(self)
        if dialog.exec_():
            new_theme = dialog.get_theme_data()
            new_key = dialog.get_theme_key()
            
            # Ensure key is unique
            if new_key in self.themes:
                i = 1
                while f"{new_key}_{i}" in self.themes:
                    i += 1
                new_key = f"{new_key}_{i}"
            
            self.themes[new_key] = new_theme
            save_themes(self.themes)
            self.update_theme_list()
            
            # Select the new theme
            for i in range(self.theme_list.count()):
                item = self.theme_list.item(i)
                if item.data(Qt.UserRole) == new_key:
                    self.theme_list.setCurrentItem(item)
                    break
    
    def edit_theme(self):
        if not self.selected_theme_key:
            return
        
        # Don't allow editing default themes
        if self.selected_theme_key in DEFAULT_THEMES:
            QMessageBox.information(
                self, 
                "Cannot Edit Default Theme",
                "Default themes cannot be edited. Please create a new theme based on this one."
            )
            return
        
        dialog = ThemeEditorDialog(self, self.themes[self.selected_theme_key], self.selected_theme_key)
        if dialog.exec_():
            updated_theme = dialog.get_theme_data()
            updated_key = dialog.get_theme_key()
            
            # If key changed, remove old key
            if updated_key != self.selected_theme_key:
                del self.themes[self.selected_theme_key]
            
            self.themes[updated_key] = updated_theme
            save_themes(self.themes)
            self.update_theme_list()
            
            # Select the updated theme
            for i in range(self.theme_list.count()):
                item = self.theme_list.item(i)
                if item.data(Qt.UserRole) == updated_key:
                    self.theme_list.setCurrentItem(item)
                    break
    
    def delete_theme(self):
        if not self.selected_theme_key:
            return
        
        # Don't allow deleting default themes
        if self.selected_theme_key in DEFAULT_THEMES:
            QMessageBox.information(
                self, 
                "Cannot Delete Default Theme",
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
            
            # Select the first theme
            if self.theme_list.count() > 0:
                self.theme_list.setCurrentRow(0)
    
    def apply_theme(self):
        if not self.selected_theme_key:
            return
        
        self.current_theme_key = self.selected_theme_key
    
    def get_selected_theme_key(self):
        return self.current_theme_key

class ThemeEditorDialog(QDialog):
    def __init__(self, parent=None, theme_data=None, theme_key=None):
        super().__init__(parent)
        self.setWindowTitle("Theme Editor")
        self.resize(700, 500)
        
        # If editing existing theme, use its data
        if theme_data:
            self.theme_data = theme_data.copy()
            self.theme_key = theme_key
        else:
            # Start with a copy of the dark theme for new themes
            self.theme_data = DEFAULT_THEMES["dark"].copy()
            self.theme_key = "custom_theme"
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Basic theme info
        info_layout = QFormLayout()
        
        self.theme_key_edit = QLineEdit(self.theme_key)
        info_layout.addRow("Theme Key:", self.theme_key_edit)
        
        self.theme_name_edit = QLineEdit(self.theme_data["name"])
        info_layout.addRow("Theme Name:", self.theme_name_edit)
        
        self.theme_desc_edit = QLineEdit(self.theme_data["description"])
        info_layout.addRow("Description:", self.theme_desc_edit)
        
        layout.addLayout(info_layout)
        
        # Color categories
        self.tab_widget = QTabWidget()
        
        # UI Colors tab
        ui_tab = QWidget()
        ui_layout = QFormLayout(ui_tab)
        self.ui_color_buttons = {}
        
        for key, value in self.theme_data["palette"].items():
            btn = QPushButton()
            btn.setStyleSheet(f"background-color: {value}; min-width: 100px;")
            btn.clicked.connect(lambda _, k=key: self.choose_color("palette", k))
            self.ui_color_buttons[key] = btn
            ui_layout.addRow(key.replace("_", " ").title() + ":", btn)
        
        self.tab_widget.addTab(ui_tab, "UI Colors")
        
        # Editor Colors tab
        editor_tab = QWidget()
        editor_layout = QFormLayout(editor_tab)
        self.editor_color_buttons = {}
        
        for key, value in self.theme_data["editor"].items():
            btn = QPushButton()
            btn.setStyleSheet(f"background-color: {value}; min-width: 100px;")
            btn.clicked.connect(lambda _, k=key: self.choose_color("editor", k))
            self.editor_color_buttons[key] = btn
            editor_layout.addRow(key.replace("_", " ").title() + ":", btn)
        
        self.tab_widget.addTab(editor_tab, "Editor Colors")
        
        # Syntax Colors tab
        syntax_tab = QWidget()
        syntax_layout = QFormLayout(syntax_tab)
        self.syntax_color_buttons = {}
        
        for key, value in self.theme_data["syntax"].items():
            btn = QPushButton()
            btn.setStyleSheet(f"background-color: {value}; min-width: 100px;")
            btn.clicked.connect(lambda _, k=key: self.choose_color("syntax", k))
            self.syntax_color_buttons[key] = btn
            syntax_layout.addRow(key.replace("_", " ").title() + ":", btn)
        
        self.tab_widget.addTab(syntax_tab, "Syntax Colors")
        
        layout.addWidget(self.tab_widget)
        
        # Base theme selection for quick start
        base_layout = QHBoxLayout()
        base_layout.addWidget(QLabel("Base Theme:"))
        
        self.base_theme_combo = QComboBox()
        for key, theme in DEFAULT_THEMES.items():
            self.base_theme_combo.addItem(theme["name"], key)
        self.base_theme_combo.currentIndexChanged.connect(self.on_base_theme_changed)
        base_layout.addWidget(self.base_theme_combo)
        
        layout.addLayout(base_layout)
        
        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def choose_color(self, category, key):
        current_color = QColor(self.theme_data[category][key])
        color = QColorDialog.getColor(current_color, self, f"Choose {key.replace('_', ' ').title()} Color")
        
        if color.isValid():
            hex_color = color.name()
            self.theme_data[category][key] = hex_color
            
            # Update button color
            if category == "palette":
                self.ui_color_buttons[key].setStyleSheet(f"background-color: {hex_color}; min-width: 100px;")
            elif category == "editor":
                self.editor_color_buttons[key].setStyleSheet(f"background-color: {hex_color}; min-width: 100px;")
            elif category == "syntax":
                self.syntax_color_buttons[key].setStyleSheet(f"background-color: {hex_color}; min-width: 100px;")
    
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
            # Keep current name and description
            name = self.theme_name_edit.text()
            desc = self.theme_desc_edit.text()
            
            # Copy base theme
            self.theme_data = base_theme.copy()
            
            # Restore name and description
            self.theme_data["name"] = name
            self.theme_data["description"] = desc
            
            # Update UI
            self.theme_name_edit.setText(name)
            self.theme_desc_edit.setText(desc)
            
            # Update color buttons
            for key, value in self.theme_data["palette"].items():
                self.ui_color_buttons[key].setStyleSheet(f"background-color: {value}; min-width: 100px;")
            
            for key, value in self.theme_data["editor"].items():
                self.editor_color_buttons[key].setStyleSheet(f"background-color: {value}; min-width: 100px;")
            
            for key, value in self.theme_data["syntax"].items():
                self.syntax_color_buttons[key].setStyleSheet(f"background-color: {value}; min-width: 100px;")
    
    def get_theme_data(self):
        # Update theme data with edited values
        self.theme_data["name"] = self.theme_name_edit.text()
        self.theme_data["description"] = self.theme_desc_edit.text()
        return self.theme_data
    
    def get_theme_key(self):
        return self.theme_key_edit.text()
