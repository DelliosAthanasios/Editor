from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QPushButton,
    QHBoxLayout, QLineEdit, QMessageBox, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal
from .logic import load_keybinds, save_keybinds, apply_keybinds_to_editor
from .config import DEFAULT_KEYBINDS

class KeybindsWindow(QDialog):
    def __init__(self, keybinds, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Default Keybinds")
        self.keybinds = keybinds
        self.layout = QVBoxLayout(self)
        desc = QLabel("Default Keybinds and their uses")
        self.layout.addWidget(desc)
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Action", "Key Combination", "Description"])
        self.table.setRowCount(len(self.keybinds))
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for row, (action, info) in enumerate(self.keybinds.items()):
            self.table.setItem(row, 0, QTableWidgetItem(action))
            self.table.setItem(row, 1, QTableWidgetItem(info["keys"]))
            self.table.setItem(row, 2, QTableWidgetItem(info["description"]))
            for col in range(3):
                self.table.item(row, col).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.layout.addWidget(self.table)
        btn = QPushButton("Close")
        btn.clicked.connect(self.accept)
        self.layout.addWidget(btn)

class KeySequenceEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setReadOnly(True)
        self.key_seq = ""
    def keyPressEvent(self, event):
        mods = []
        if event.modifiers() & Qt.ControlModifier:
            mods.append("Ctrl")
        if event.modifiers() & Qt.AltModifier:
            mods.append("Alt")
        if event.modifiers() & Qt.ShiftModifier:
            mods.append("Shift")
        key = event.key()
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt):
            return
        from PyQt5.QtGui import QKeySequence
        key_name = QKeySequence(key).toString()
        if not key_name:
            key_name = event.text().upper()
        if key_name:
            mods.append(key_name)
        seq = "+".join(mods)
        self.setText(seq)
        self.key_seq = seq
    def get_key_seq(self):
        return self.key_seq

class ConfigureKeybindsWindow(QDialog):
    keybinds_changed = pyqtSignal(dict)
    def __init__(self, keybinds, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Keybinds")
        self.setMinimumWidth(550)
        self.keybinds = keybinds.copy()
        self.layout = QVBoxLayout(self)
        info = QLabel("Double click a key combination to change it. Press Reset to restore defaults.")
        self.layout.addWidget(info)
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Action", "Key Combination", "Description"])
        self.table.setRowCount(len(self.keybinds))
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.table)
        self.populate_table()
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save)
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset_defaults)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addWidget(self.close_btn)
        self.layout.addLayout(btn_layout)
        self.table.cellDoubleClicked.connect(self.edit_keybind)
    def populate_table(self):
        self.table.setRowCount(len(self.keybinds))
        for row, (action, info) in enumerate(self.keybinds.items()):
            self.table.setItem(row, 0, QTableWidgetItem(action))
            kitem = QTableWidgetItem(info["keys"])
            kitem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
            self.table.setItem(row, 1, kitem)
            ditem = QTableWidgetItem(info["description"])
            ditem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, 2, ditem)
    def edit_keybind(self, row, col):
        if col != 1:
            return
        action = self.table.item(row, 0).text()
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Set keybind for '{action}'")
        vbox = QVBoxLayout(dialog)
        label = QLabel(f"Press the new key combination for '{action}'")
        vbox.addWidget(label)
        key_edit = KeySequenceEdit()
        vbox.addWidget(key_edit)
        btns = QHBoxLayout()
        okbtn = QPushButton("OK")
        cancelbtn = QPushButton("Cancel")
        btns.addWidget(okbtn)
        btns.addWidget(cancelbtn)
        vbox.addLayout(btns)
        okbtn.clicked.connect(dialog.accept)
        cancelbtn.clicked.connect(dialog.reject)
        key_edit.setFocus()
        if dialog.exec_() == QDialog.Accepted:
            new_seq = key_edit.get_key_seq()
            if not new_seq:
                QMessageBox.warning(self, "Invalid", "Please enter a valid key sequence.")
                return
            for i in range(self.table.rowCount()):
                if i != row and self.table.item(i, 1).text() == new_seq:
                    QMessageBox.warning(self, "Conflict", f"{new_seq} is already assigned to another action.")
                    return
            self.keybinds[action]["keys"] = new_seq
            self.table.setItem(row, 1, QTableWidgetItem(new_seq))
    def save(self):
        for row in range(self.table.rowCount()):
            action = self.table.item(row, 0).text()
            keys = self.table.item(row, 1).text()
            self.keybinds[action]["keys"] = keys
        save_keybinds(self.keybinds)
        self.keybinds_changed.emit(self.keybinds)
        QMessageBox.information(self, "Saved", "Keybinds saved successfully.")
        self.accept()
    def reset_defaults(self):
        self.keybinds = DEFAULT_KEYBINDS.copy()
        self.populate_table()

def show_default_keybinds(main_window):
    keybinds = load_keybinds()
    dlg = KeybindsWindow(keybinds, main_window)
    dlg.exec_()

def update_menu_action_labels(main_window, keybinds):
    """Update all menu action labels to show their current keybinds."""
    menu_bar = main_window.menuBar()
    action_to_keybind = {k: v["keys"] for k, v in keybinds.items()}
    # Map menu text to keybind action names
    menu_map = {
        "Undo": "Undo",
        "Redo": "Redo",
        "Select All": "Select All",
        "Find": "Search",
        "Find and Replace": "Replace",
        "Line": "Go to Line",
        "Word": "Go to Word",
        "Save File": "Save File",
        "Open File": "Open File",
        "New File": "New File",
        "Close Tab": "Close Tab",
        "Duplicate File": "Duplicate File",
        "Toggle Minimap": "Toggle Minimap",
        "Toggle Number Line": "Toggle Number Line",
        "Toggle File Tree": "Toggle File Tree",
    }
    for menu in menu_bar.findChildren(type(menu_bar)):
        for action in menu.actions():
            text = action.text().split(" [")[0]
            if text in menu_map:
                keybind_action = menu_map[text]
                key = action_to_keybind.get(keybind_action, "")
                if key:
                    action.setText(f"{text} [{key}]")
                else:
                    action.setText(text)
    # Also update top-level actions
    for action in menu_bar.actions():
        if action.menu():
            for subaction in action.menu().actions():
                text = subaction.text().split(" [")[0]
                if text in menu_map:
                    keybind_action = menu_map[text]
                    key = action_to_keybind.get(keybind_action, "")
                    if key:
                        subaction.setText(f"{text} [{key}]")
                    else:
                        subaction.setText(text)

def configure_keybinds(main_window):
    keybinds = load_keybinds()
    dlg = ConfigureKeybindsWindow(keybinds, main_window)
    def on_keybinds_changed(new_keybinds):
        apply_keybinds_to_editor(main_window, new_keybinds)
        update_menu_action_labels(main_window, new_keybinds)
    dlg.keybinds_changed.connect(on_keybinds_changed)
    dlg.exec_()

def integrate_keybinds_menu(main_window):
    menu_bar = main_window.menuBar()
    keybind_menu = None
    for action in menu_bar.actions():
        if action.menu() and action.text() == "Keybinds":
            keybind_menu = action.menu()
            break
    if keybind_menu:
        for act in keybind_menu.actions():
            if act.text() == "Default Keybinds":
                act.triggered.connect(lambda: show_default_keybinds(main_window))
            elif act.text() == "Configure Keybinds":
                act.triggered.connect(lambda: configure_keybinds(main_window))
    keybinds = load_keybinds()
    apply_keybinds_to_editor(main_window, keybinds)
    update_menu_action_labels(main_window, keybinds) 