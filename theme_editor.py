import copy
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTabWidget, QWidget, QPushButton,
    QComboBox, QDialogButtonBox, QLabel, QColorDialog, QMessageBox, QHBoxLayout
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

from default_themes import DEFAULT_THEMES

class ThemeEditorDialog(QDialog):
    def __init__(self, parent=None, theme_data=None, theme_key=None):
        super().__init__(parent)
        self.setWindowTitle("Theme Editor")
        self.resize(700, 500)
        if theme_data:
            self.theme_data = copy.deepcopy(theme_data)
            self.theme_key = theme_key
        else:
            self.theme_data = copy.deepcopy(DEFAULT_THEMES["dark"])
            self.theme_key = "custom_theme"
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        info_layout = QFormLayout()
        self.theme_key_edit = QLineEdit(self.theme_key)
        info_layout.addRow("Theme Key:", self.theme_key_edit)
        self.theme_name_edit = QLineEdit(self.theme_data["name"])
        info_layout.addRow("Theme Name:", self.theme_name_edit)
        self.theme_desc_edit = QLineEdit(self.theme_data["description"])
        info_layout.addRow("Description:", self.theme_desc_edit)
        layout.addLayout(info_layout)
        self.tab_widget = QTabWidget()
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
        base_layout = QHBoxLayout()
        base_layout.addWidget(QLabel("Base Theme:"))
        self.base_theme_combo = QComboBox()
        for key, theme in DEFAULT_THEMES.items():
            self.base_theme_combo.addItem(theme["name"], key)
        self.base_theme_combo.currentIndexChanged.connect(self.on_base_theme_changed)
        base_layout.addWidget(self.base_theme_combo)
        layout.addLayout(base_layout)
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
            name = self.theme_name_edit.text()
            desc = self.theme_desc_edit.text()
            self.theme_data = copy.deepcopy(base_theme)
            self.theme_data["name"] = name
            self.theme_data["description"] = desc
            self.theme_name_edit.setText(name)
            self.theme_desc_edit.setText(desc)
            for key, value in self.theme_data["palette"].items():
                self.ui_color_buttons[key].setStyleSheet(f"background-color: {value}; min-width: 100px;")
            for key, value in self.theme_data["editor"].items():
                self.editor_color_buttons[key].setStyleSheet(f"background-color: {value}; min-width: 100px;")
            for key, value in self.theme_data["syntax"].items():
                self.syntax_color_buttons[key].setStyleSheet(f"background-color: {value}; min-width: 100px;")

    def get_theme_data(self):
        self.theme_data["name"] = self.theme_name_edit.text()
        self.theme_data["description"] = self.theme_desc_edit.text()
        return self.theme_data

    def get_theme_key(self):
        return self.theme_key_edit.text()