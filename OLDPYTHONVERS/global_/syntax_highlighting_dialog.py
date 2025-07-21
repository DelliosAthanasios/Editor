import os
import json
import shutil
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QColorDialog, QComboBox,
    QLineEdit, QMessageBox, QHeaderView, QWidget, QInputDialog
)
from PyQt5.QtGui import QColor, QBrush, QFont
from PyQt5.QtCore import Qt

# Update paths to use the global folder
LANGC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'langc')
LANGC_STOCK_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'langc_stock')

def pretty_color(color):
    if not color: return "#000000"
    return QColor(color).name()

class SyntaxHighlightingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Syntax Highlighting Editor")
        self.setMinimumSize(600, 420)
        self.setStyleSheet("""
            QDialog { background: #272c36; }
            QPushButton { padding: 6px 16px; font-size: 14px; border-radius: 6px; background:#39424f; color:#f5f5f5; }
            QPushButton:hover { background:#505b6c; }
            QComboBox, QLineEdit, QLabel { color: #f3f6fa; font-size: 14px;}
            QLineEdit { background: #23272e; border: 1px solid #394957; border-radius: 6px; padding: 3px; }
            QComboBox { background: #23272e; border: 1px solid #394957; border-radius: 6px; }
            QTableWidget { background: #23272e; color: #dde3eb; font-size: 14px; border-radius: 6px; }
        """)
        self.language_combo = QComboBox()
        self.language_combo.addItems(self.get_language_files())
        self.language_combo.currentTextChanged.connect(self.load_language)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Pattern", "Color"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)

        add_btn = QPushButton("Add Rule")
        edit_btn = QPushButton("Edit Rule")
        delete_btn = QPushButton("Delete Rule")
        reset_btn = QPushButton("Reset to Default")
        save_btn = QPushButton("Save Changes")
        new_lang_btn = QPushButton("New Language")

        desc = QLabel(
            "<b>Instructions:</b> Add or edit rules for syntax highlighting.<br>"
            "Patterns use <b>regular expressions</b> (e.g., <code>\\bdef\\b</code>)."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#a8b5c7; font-size:13px;")

        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel("Language:"))
        hlayout.addWidget(self.language_combo)
        hlayout.addStretch()
        hlayout.addWidget(new_lang_btn)

        blayout = QHBoxLayout()
        blayout.addWidget(add_btn)
        blayout.addWidget(edit_btn)
        blayout.addWidget(delete_btn)
        blayout.addStretch()
        blayout.addWidget(reset_btn)
        blayout.addWidget(save_btn)

        main = QVBoxLayout(self)
        main.addLayout(hlayout)
        main.addWidget(self.table)
        main.addLayout(blayout)
        main.addWidget(desc)
        self.setLayout(main)

        self.lang_file = None
        self.config = {"rules": [], "multiline": []}
        self.current_row = None

        add_btn.clicked.connect(self.add_rule_dialog)
        edit_btn.clicked.connect(self.edit_rule_dialog)
        delete_btn.clicked.connect(self.delete_rule)
        save_btn.clicked.connect(self.save)
        reset_btn.clicked.connect(self.reset_to_default)
        new_lang_btn.clicked.connect(self.create_new_language)
        self.table.cellDoubleClicked.connect(self.edit_rule_dialog)

        self.load_language(self.language_combo.currentText())

    def get_language_files(self):
        return [f[:-5] for f in os.listdir(LANGC_DIR) if f.endswith('.json')]

    def load_language(self, lang):
        self.lang_file = os.path.join(LANGC_DIR, f"{lang}.json")
        if not os.path.exists(self.lang_file):
            self.config = {"rules": [], "multiline": []}
        else:
            with open(self.lang_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        self.populate_table()

    def populate_table(self):
        self.table.setRowCount(0)
        for rule in self.config.get("rules", []):
            pat = rule["patterns"][0] if rule["patterns"] else ""
            color = rule["format"].get("color", "#000")
            row = self.table.rowCount()
            self.table.insertRow(row)
            item_pattern = QTableWidgetItem(pat)
            item_pattern.setToolTip("Regex pattern")
            item_color = QTableWidgetItem(color)
            item_color.setToolTip("Highlight color")
            item_color.setBackground(QBrush(QColor(color)))
            self.table.setItem(row, 0, item_pattern)
            self.table.setItem(row, 1, item_color)

    def add_rule_dialog(self):
        pattern, ok = QInputDialog.getText(self, "Add Rule", "Regex pattern for highlighting:")
        if not ok or not pattern.strip():
            return
        color = QColorDialog.getColor(QColor("#569CD6"), self, "Choose Highlight Color")
        if not color.isValid():
            return
        rule = {"patterns": [pattern.strip()], "format": {"color": color.name()}}
        self.config.setdefault("rules", []).append(rule)
        self.populate_table()

    def edit_rule_dialog(self):
        row = self.table.currentRow()
        if row == -1:
            QMessageBox.information(self, "Select Rule", "Please select a rule to edit.")
            return
        rule = self.config["rules"][row]
        pattern, ok = QInputDialog.getText(self, "Edit Rule", "Regex pattern:", text=rule["patterns"][0])
        if not ok or not pattern.strip():
            return
        color = QColorDialog.getColor(QColor(rule["format"].get("color", "#569CD6")), self, "Choose Highlight Color")
        if not color.isValid():
            return
        rule["patterns"][0] = pattern.strip()
        rule["format"]["color"] = color.name()
        self.populate_table()

    def delete_rule(self):
        row = self.table.currentRow()
        if row == -1:
            QMessageBox.information(self, "No Selection", "Select a rule to delete.")
            return
        r = QMessageBox.question(self, "Delete Rule", "Are you sure you want to delete this rule?")
        if r != QMessageBox.Yes:
            return
        del self.config["rules"][row]
        self.populate_table()

    def save(self):
        with open(self.lang_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2)
        QMessageBox.information(self, "Saved", "Highlighting rules saved.")

    def reset_to_default(self):
        lang = self.language_combo.currentText()
        stock = os.path.join(LANGC_STOCK_DIR, f"{lang}.json")
        if not os.path.exists(stock):
            QMessageBox.warning(self, "No Default", "No stock default for this language.")
            return
        shutil.copy(stock, self.lang_file)
        self.load_language(lang)
        QMessageBox.information(self, "Reset", f"{lang} highlighting was reset to default.")

    def create_new_language(self):
        text, ok = QInputDialog.getText(self, "New Language", "Enter new language name (e.g. rust):")
        if not ok or not text.strip():
            return
        lang_name = text.lower().strip()
        fn = os.path.join(LANGC_DIR, f"{lang_name}.json")
        if os.path.exists(fn):
            QMessageBox.warning(self, "Exists", "That language already exists.")
            return
        with open(fn, "w", encoding="utf-8") as f:
            json.dump({"rules": [], "multiline": []}, f, indent=2)
        self.language_combo.addItem(lang_name)
        self.language_combo.setCurrentText(lang_name)
