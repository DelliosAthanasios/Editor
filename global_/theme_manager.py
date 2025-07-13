import json
import os
import copy
from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QFormLayout, QDialogButtonBox, QGroupBox, QWidget, QSizePolicy, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject

from .default_themes import DEFAULT_THEMES

from .theme_editor import ThemeEditorDialog, load_custom_themes, save_custom_themes

THEME_CONFIG_PATH = "theme_config.json"
USER_PREFS_PATH = "user_prefs.json"

def load_themes():
    themes = copy.deepcopy(DEFAULT_THEMES)
    custom_themes = load_custom_themes()
    themes.update(custom_themes)
    return themes

def save_themes(themes):
    custom_themes = {k: v for k, v in themes.items() if k not in DEFAULT_THEMES}
    return save_custom_themes(custom_themes)

def load_user_prefs():
    """Load user preferences, including 'visual_style' (classic/modern) if present."""
    if os.path.exists(USER_PREFS_PATH):
        try:
            with open(USER_PREFS_PATH, "r") as f:
                prefs = json.load(f)
                return prefs
        except Exception as e:
            print(f"Error loading user preferences: {e}")
    return {}

def save_user_prefs(prefs):
    """Save user preferences, including 'visual_style' (classic/modern) if present."""
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

def get_menu_bar_styles(theme_data):
    """Get menu bar styling based on theme data"""
    palette_data = theme_data.get("palette", {})
    
    bg_color = palette_data.get("window", "#2b2b2b")
    text_color = palette_data.get("window_text", "#ffffff")
    button_bg = palette_data.get("button", "#353535")
    button_text = palette_data.get("button_text", "#ffffff")
    highlight_bg = palette_data.get("highlight", "#2a82da")
    highlight_text = palette_data.get("highlight_text", "#ffffff")
    
    menu_style = f"""
    QMenuBar {{
        background-color: {bg_color};
        color: {text_color};
        border-bottom: 1px solid {button_bg};
    }}
    QMenuBar::item {{
        background-color: transparent;
        color: {text_color};
        padding: 4px 8px;
    }}
    QMenuBar::item:selected {{
        background-color: {highlight_bg};
        color: {highlight_text};
    }}
    QMenuBar::item:pressed {{
        background-color: {highlight_bg};
        color: {highlight_text};
    }}
    QMenu {{
        background-color: {bg_color};
        color: {text_color};
        border: 1px solid {button_bg};
    }}
    QMenu::item {{
        background-color: transparent;
        color: {text_color};
        padding: 4px 20px;
    }}
    QMenu::item:selected {{
        background-color: {highlight_bg};
        color: {highlight_text};
    }}
    QMenu::separator {{
        height: 1px;
        background-color: {button_bg};
        margin: 2px 4px;
    }}
    """
    return menu_style

def get_separator_styles(theme_data):
    """Get separator styling based on theme data"""
    palette_data = theme_data.get("palette", {})
    editor_data = theme_data.get("editor", {})
    separator_color = palette_data.get("mid", "#3c3c3c")
    bg_color = editor_data.get("background", palette_data.get("window", "#23232a"))
    # Explicitly remove borders and set background
    separator_style = f"""
    QSplitter::handle {{
        background-color: {separator_color};
        border: none;
    }}
    QSplitter {{
        background: {bg_color};
        border: none;
    }}
    QWidget {{
        background: {bg_color};
    }}
    """
    return separator_style

def get_tab_bar_styles(theme_data):
    palette = theme_data.get("palette", {})
    editor = theme_data.get("editor", {})
    bg = palette.get("window", "#2b2b2b")
    fg = palette.get("window_text", "#ffffff")
    border = palette.get("mid", "#3c3c3c")
    selected_bg = palette.get("highlight", "#2a82da")
    selected_fg = palette.get("highlight_text", "#ffffff")
    tab_bg = editor.get("background", bg)
    tab_fg = editor.get("foreground", fg)
    # Explicitly remove pane border and set background
    return f'''
    QTabBar, QTabWidget::pane {{
        background: {bg};
        color: {fg};
        border: none;
    }}
    QTabWidget::pane {{
        background: {tab_bg};
        border: none;
    }}
    QTabBar::tab {{
        background: {tab_bg};
        color: {tab_fg};
        border: 1px solid {border};
        border-bottom: none;
        padding: 6px 18px 6px 18px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        margin-right: 2px;
        min-width: 80px;
    }}
    QTabBar::tab:selected, QTabBar::tab:hover {{
        background: {selected_bg};
        color: {selected_fg};
        border: 1.5px solid {selected_bg};
    }}
    QTabBar::tab:!selected {{
        margin-top: 2px;
    }}
    '''

def get_classic_styles(theme_data):
    palette = theme_data["palette"]
    editor = theme_data["editor"]
    return f'''
    QMainWindow {{
        background: {palette['base']};
    }}
    QMenuBar {{
        background: #e4e4e4;
        color: #222;
        border-bottom: 1px solid #b0b0b0;
    }}
    QMenuBar::item {{
        background: transparent;
        color: #222;
        padding: 4px 12px;
    }}
    QMenuBar::item:selected {{
        background: #cce6ff;
        color: #000;
    }}
    QMenu {{
        background: #e4e4e4;
        color: #222;
        border: 1px solid #b0b0b0;
    }}
    QMenu::item:selected {{
        background: #cce6ff;
        color: #000;
    }}
    QTabBar::tab {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f6f6f6, stop:1 #d0d0d0);
        color: #222;
        border: 1px solid #b0b0b0;
        border-bottom: none;
        border-top-left-radius: 0px;
        border-top-right-radius: 0px;
        min-width: 48px;
        padding: 3px 10px;
    }}
    QTabBar::tab:selected {{
        background: #cce6ff;
        color: #000;
        border: 1.5px solid #3399ff;
    }}
    QPushButton {{
        background: #e4e4e4;
        border: 1px solid #b0b0b0;
        border-radius: 2px;
        padding: 4px 12px;
        color: #222;
    }}
    QPushButton:hover {{
        background: #cce6ff;
    }}
    QScrollBar:vertical, QScrollBar:horizontal {{
        background: #e4e4e4;
        width: 18px;
        margin: 0px;
        border: 1px solid #b0b0b0;
    }}
    QTextEdit {{
        background: {editor['background']};
        color: {editor['foreground']};
        selection-background-color: {editor['selection_background']};
        selection-color: {editor['selection_foreground']};
    }}
    '''

def get_modern_styles(theme_data):
    palette = theme_data["palette"]
    editor = theme_data["editor"]
    return f'''
    QMainWindow {{
        background: {palette['base']};
    }}
    QMenuBar {{
        background: {palette['window']};
        color: {palette['window_text']};
        border-bottom: 1px solid {palette['mid']};
    }}
    QMenuBar::item {{
        background: transparent;
        color: {palette['window_text']};
        padding: 4px 12px;
    }}
    QMenuBar::item:selected {{
        background: {palette['highlight']};
        color: {palette['highlight_text']};
    }}
    QMenu {{
        background: {palette['window']};
        color: {palette['window_text']};
        border: 1px solid {palette['mid']};
    }}
    QMenu::item:selected {{
        background: {palette['highlight']};
        color: {palette['highlight_text']};
    }}
    QTabBar::tab {{
        background: {editor['background']};
        color: {editor['foreground']};
        border: 1px solid {palette['mid']};
        border-bottom: none;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        min-width: 80px;
        padding: 6px 18px;
    }}
    QTabBar::tab:selected {{
        background: {palette['highlight']};
        color: {palette['highlight_text']};
        border: 1.5px solid {palette['highlight']};
    }}
    QPushButton {{
        background: {palette['button']};
        color: {palette['button_text']};
        border-radius: 8px;
        padding: 7px 18px;
        border: 1px solid {palette['mid']};
    }}
    QPushButton:hover {{
        background: {palette['highlight']};
        color: {palette['highlight_text']};
    }}
    QScrollBar:vertical, QScrollBar:horizontal {{
        background: {palette['mid']};
        width: 8px;
        margin: 0px;
        border: none;
    }}
    QTextEdit {{
        background: {editor['background']};
        color: {editor['foreground']};
        selection-background-color: {editor['selection_background']};
        selection-color: {editor['selection_foreground']};
    }}
    '''

def get_user_styles():
    # Try to load user styles from user_styles.qss in the root directory
    user_qss_path = os.path.join(os.path.dirname(__file__), '..', 'user_styles.qss')
    if os.path.exists(user_qss_path):
        with open(user_qss_path, 'r', encoding='utf-8') as f:
            return f.read()
    # Fallback: return empty string
    return ''

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
        self.themes = load_themes()
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
        self.setMinimumSize(560, 480)
        self.setStyleSheet("""
            QDialog { background: #22242a; color: #f3f6fa; }
            QLabel { font-size: 15px; }
            QListWidget { font-size: 15px; border-radius: 8px; background: #23262c; color: #f3f6fa; }
            QListWidget::item:selected { background: #4c8aff; color: #fff; border-radius: 6px; }
            QPushButton { padding: 7px 18px; font-size: 15px; border-radius: 8px; background: #2d2f37; color: #d0e1ff; border: 1px solid #444; }
            QPushButton:hover { background: #4c8aff; color: #fff; }
            QDialogButtonBox QPushButton { min-width: 100px; }
            QGroupBox { border: 1.5px solid #555; border-radius: 10px; padding: 10px; margin-top: 10px; background: #23272e; }
            QFrame#line { background: #444; max-height: 2px; min-height: 2px; border: none; }
        """)
        self.themes = load_themes()
        self.current_theme_key = current_theme_key
        self.selected_theme_key = current_theme_key
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        # Title
        title = QLabel("Theme Manager")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Split for list and details
        main_row = QHBoxLayout()
        # Theme List
        list_box = QGroupBox("Available Themes")
        list_layout = QVBoxLayout(list_box)
        self.theme_list = QListWidget()
        self.theme_list.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.theme_list.setMinimumWidth(220)
        self.update_theme_list()
        self.theme_list.currentRowChanged.connect(self.on_theme_selected)
        list_layout.addWidget(self.theme_list)
        main_row.addWidget(list_box, 2)

        # Details and actions
        details_box = QGroupBox("Theme Details")
        details_layout = QFormLayout(details_box)
        details_box.setMinimumWidth(250)
        self.theme_name_label = QLabel()
        self.theme_desc_label = QLabel()
        self.theme_type_label = QLabel()
        details_layout.addRow("Name:", self.theme_name_label)
        details_layout.addRow("Description:", self.theme_desc_label)
        details_layout.addRow("Type:", self.theme_type_label)
        main_row.addWidget(details_box, 3)

        layout.addLayout(main_row)

        # Separator
        line = QFrame()
        line.setObjectName("line")
        layout.addWidget(line)

        # Modern action bar
        btn_bar = QHBoxLayout()
        btn_bar.addStretch(1)
        self.new_btn = QPushButton("New Theme")
        self.new_btn.setToolTip("Create a new custom theme")
        self.new_btn.clicked.connect(self.create_new_theme)
        btn_bar.addWidget(self.new_btn)

        self.edit_btn = QPushButton("Edit Theme")
        self.edit_btn.setToolTip("Edit the selected custom theme")
        self.edit_btn.clicked.connect(self.edit_theme)
        btn_bar.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete Theme")
        self.delete_btn.setToolTip("Delete the selected custom theme")
        self.delete_btn.clicked.connect(self.delete_theme)
        btn_bar.addWidget(self.delete_btn)

        self.apply_btn = QPushButton("Apply Theme")
        self.apply_btn.setToolTip("Apply the selected theme")
        self.apply_btn.clicked.connect(self.apply_theme)
        btn_bar.addWidget(self.apply_btn)
        btn_bar.addStretch(1)
        layout.addLayout(btn_bar)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Close")
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
            is_custom = key not in DEFAULT_THEMES
            item.setData(Qt.UserRole, key)
            if is_custom:
                item.setText(f"{theme['name']} (Custom)")
            else:
                item.setText(f"{theme['name']} (Built-in)")
            self.theme_list.addItem(item)

    def on_theme_selected(self, row):
        if row < 0:
            self.theme_name_label.setText("")
            self.theme_desc_label.setText("")
            self.theme_type_label.setText("")
            return
        item = self.theme_list.item(row)
        theme_key = item.data(Qt.UserRole)
        self.selected_theme_key = theme_key
        theme = self.themes[theme_key]
        self.theme_name_label.setText(theme["name"])
        self.theme_desc_label.setText(theme["description"])
        if theme_key in DEFAULT_THEMES:
            self.theme_type_label.setText("Built-in")
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
        else:
            self.theme_type_label.setText("Custom")
            self.edit_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)

    def create_new_theme(self):
        dialog = ThemeEditorDialog(self)
        if dialog.exec_():
            new_theme = dialog.get_theme_data()
            new_key = dialog.get_theme_key()
            if new_key in self.themes:
                i = 1
                while f"{new_key}_{i}" in self.themes:
                    i += 1
                new_key = f"{new_key}_{i}"
                new_theme["name"] += f" ({i})"
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
                "Built-in themes cannot be edited. Create a new custom theme instead."
            )
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
                "Built-in themes cannot be deleted."
            )
            return
        confirm = QMessageBox.question(
            self,
            "Delete Theme?",
            f"Delete the theme '{self.themes[self.selected_theme_key]['name']}'? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            del self.themes[self.selected_theme_key]
            save_themes(self.themes)
            self.update_theme_list()
            if self.theme_list.count() > 0:
                self.theme_list.setCurrentRow(0)
            else:
                self.theme_name_label.setText("")
                self.theme_desc_label.setText("")
                self.theme_type_label.setText("")

    def apply_theme(self):
        if not self.selected_theme_key:
            return
        self.current_theme_key = self.selected_theme_key
        prefs = load_user_prefs()
        prefs["theme"] = self.current_theme_key
        save_user_prefs(prefs)

    def get_selected_theme_key(self):
        return self.current_theme_key