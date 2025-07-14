from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QPushButton,
    QHBoxLayout, QLineEdit, QMessageBox, QHeaderView, QWidget, QSplitter, QListWidget, QAbstractItemView,
    QComboBox, QInputDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from .logic import load_keybinds, save_keybinds, apply_keybinds_to_editor, keybind_manager
from .config import DEFAULT_KEYBINDS
import copy

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
        "New Tab": "New Tab",
        "Open File Explorer": "Open File Explorer",
        "Create Checkpoint": "Create Checkpoint",
        "Go to Next Checkpoint": "Go to Next Checkpoint",
        "Go to Previous Checkpoint": "Go to Previous Checkpoint",
        "Manage Checkpoints...": "Manage Checkpoints...",
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

def check_keybind_coverage(main_window, keybinds):
    """Check which keybinds are not mapped to menu actions and print/report them."""
    menu_bar = main_window.menuBar()
    menu_action_names = set()
    for action in menu_bar.actions():
        if action.menu():
            for subaction in action.menu().actions():
                text = subaction.text().split(" [")[0]
                menu_action_names.add(text)
    # Map menu text to keybind action names (same as in update_menu_action_labels)
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
        "New Tab": "New Tab",
        "Open File Explorer": "Open File Explorer",
        "Create Checkpoint": "Create Checkpoint",
        "Go to Next Checkpoint": "Go to Next Checkpoint",
        "Go to Previous Checkpoint": "Go to Previous Checkpoint",
        "Manage Checkpoints...": "Manage Checkpoints...",
    }
    covered = set(menu_map.values()) & set(keybinds.keys())
    missing = set(keybinds.keys()) - covered
    if missing:
        print("Keybinds not mapped to menu actions:", missing)
    else:
        print("All keybinds are mapped to menu actions.")

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
            elif act.text().startswith("Configure Keybinds"):
                act.triggered.connect(lambda: open_keybinds_manager_tab(main_window))
    keybinds = load_keybinds()
    apply_keybinds_to_editor(main_window, keybinds)
    update_menu_action_labels(main_window, keybinds)
    check_keybind_coverage(main_window, keybinds)

def open_keybinds_manager_tab(main_window):
    # Try to reuse an existing tab if already open
    tabs = getattr(main_window, 'tabs', None)
    if not tabs:
        return
    for i in range(tabs.count()):
        if tabs.tabText(i) == 'KeybindsManager':
            tabs.setCurrentIndex(i)
            return
    tab = KeybindsManagerTab(main_window)
    tabs.addTab(tab, 'KeybindsManager')
    tabs.setCurrentWidget(tab)

class KeySequenceCapture(QLineEdit):
    def __init__(self, initial='', parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.sequences = []
        self.extend_mode = False
        if initial:
            self.setText(initial)
            self.sequences = [s.strip() for s in initial.split(',') if s.strip()]
        self._last_key = None
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape):
            event.ignore()
            return
        mods = []
        if event.modifiers() & Qt.ControlModifier:
            mods.append('Ctrl')
        if event.modifiers() & Qt.AltModifier:
            mods.append('Alt')
        if event.modifiers() & Qt.ShiftModifier:
            mods.append('Shift')
        key = event.key()
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt):
            return
        from PyQt5.QtGui import QKeySequence
        key_name = QKeySequence(key).toString()
        if not key_name:
            key_name = event.text().upper()
        if not key_name or key_name == ',':
            return
        seq = '+'.join(mods + [key_name]) if mods or key_name else ''
        if seq:
            if self.extend_mode:
                # Prevent duplicate consecutive steps
                if self.sequences and self.sequences[-1] == seq:
                    return
                self.sequences.append(seq)
                self.setText(', '.join(self.sequences))
                self.extend_mode = False
                self.setStyleSheet("")
            else:
                self.sequences = [seq]
                self.setText(seq)
    def get_sequences(self):
        return ', '.join(self.sequences)

class KeybindsManagerTab(QWidget):
    def update_table_for_category(self, row):
        category = self.categories[row]
        cat_map = {
            "Editing": ["Undo", "Redo", "Select All", "Search", "Replace"],
            "Navigation": [
                "Go to Line", "Go to Word", "Go to Start of Line", "Go to End of Line", "Go to Next Word", "Go to Previous Word", "Go Up One Line", "Go Down One Line", "Go Forward One Char", "Go Backward One Char", "Go to Start of Document", "Go to End of Document", "Set Mark", "Select to End of Line", "Select to Start of Line", "Transpose Characters"
            ],
            "File": ["Save File", "Open File", "New File", "Close Tab", "Duplicate File", "New Tab", "Open File Explorer"],
            "View": ["Toggle Minimap", "Toggle Number Line", "Toggle File Tree"],
            "Checkpoints": ["Create Checkpoint", "Go to Next Checkpoint", "Go to Previous Checkpoint", "Manage Checkpoints..."],
            "Other": []
        }
        actions = cat_map.get(category, [])
        if category == "Other":
            all_actions = set(self.keybinds.keys())
            categorized = set(sum(cat_map.values(), []))
            actions = list(all_actions - categorized)
        self.table.setRowCount(len(actions))
        for row, action in enumerate(actions):
            info = self.keybinds.get(action, {"keys": "", "description": ""})
            self.table.setItem(row, 0, QTableWidgetItem(action))
            kitem = QTableWidgetItem(info["keys"])
            kitem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, 1, kitem)
            ditem = QTableWidgetItem(info["description"])
            ditem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, 2, ditem)
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.keybinds = keybind_manager.get_keybinds()
        self.current_profile = keybind_manager.current_profile
        self.init_ui()
        keybind_manager.keybinds_changed.connect(self.on_keybinds_changed)
        keybind_manager.profile_changed.connect(self.on_profile_changed)
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 8, 16, 8)
        main_layout.setSpacing(8)
        # Remove the big header, just add a small margin above the profile bar
        main_layout.addSpacing(4)
        # Profile dropdown and management
        profile_layout = QHBoxLayout()
        profile_label = QLabel("Profile:")
        self.profile_dropdown = QComboBox()
        self.profile_dropdown.addItems(list(keybind_manager.profiles.keys()))
        self.profile_dropdown.setCurrentText(self.current_profile)
        self.profile_dropdown.currentTextChanged.connect(self.on_profile_selected)
        add_profile_btn = QPushButton("Add Profile")
        add_profile_btn.clicked.connect(self.add_profile)
        del_profile_btn = QPushButton("Delete Profile")
        del_profile_btn.clicked.connect(self.delete_profile)
        profile_layout.addWidget(profile_label)
        profile_layout.addWidget(self.profile_dropdown)
        profile_layout.addWidget(add_profile_btn)
        profile_layout.addWidget(del_profile_btn)
        profile_layout.addStretch()
        main_layout.addLayout(profile_layout)
        splitter = QSplitter(Qt.Horizontal)
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(180)
        self.sidebar.setSelectionMode(QAbstractItemView.SingleSelection)
        self.categories = [
            "Editing", "Navigation", "File", "View", "Checkpoints", "Other"
        ]
        self.sidebar.addItems(self.categories)
        self.sidebar.setCurrentRow(0)
        self.sidebar.currentRowChanged.connect(self.update_table_for_category)
        splitter.addWidget(self.sidebar)
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(8)
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Action", "Key Combination", "Description"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("font-size: 14px;")
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self.edit_keybind_dialog)
        table_layout.addWidget(self.table)
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.setStyleSheet("padding: 6px 18px; font-weight: bold; background:#444; color:#fff; border-radius:4px;")
        self.save_btn.clicked.connect(self.save_keybinds)
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.setStyleSheet("padding: 6px 18px; background:#444; color:#fff; border-radius:4px;")
        self.reset_btn.clicked.connect(self.reset_defaults)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addStretch()
        table_layout.addLayout(btn_layout)
        splitter.addWidget(table_container)
        splitter.setStretchFactor(1, 2)
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
        self.update_table_for_category(0)
    def edit_keybind_dialog(self, row, col):
        if col != 1:
            return
        action = self.table.item(row, 0).text()
        current_keys = self.table.item(row, 1).text()
        # Ensure action exists in keybinds
        if action not in self.keybinds:
            self.keybinds[action] = {"keys": "", "description": ""}
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Set keybind for '{action}'")
        vbox = QVBoxLayout(dlg)
        label = QLabel(f"Press the new key combination(s) for '{action}':<br><span style='font-size:11px;'>(Press each sequence, separated by comma for multi-step, e.g. Ctrl+Y, Ctrl+X)</span>")
        vbox.addWidget(label)
        key_input = KeySequenceCapture(current_keys)
        vbox.addWidget(key_input)
        # Add Extend button
        extend_btn = QPushButton("Extend Sequence")
        vbox.addWidget(extend_btn)
        def on_extend():
            key_input.extend_mode = True
            key_input.setStyleSheet("background:#e0e0ff;")
        extend_btn.clicked.connect(on_extend)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec_() == QDialog.Accepted:
            new_seq = key_input.get_sequences().strip()
            if not new_seq:
                QMessageBox.warning(self, "Invalid", "Key sequence cannot be empty.")
                return
            temp_keybinds = copy.deepcopy(self.keybinds)
            temp_keybinds[action]["keys"] = new_seq
            valid, msg = keybind_manager.validate_keybinds(temp_keybinds)
            if not valid:
                QMessageBox.warning(self, "Invalid", msg)
                return
            keybind_manager.set_keybind(action, new_seq)
    def save_keybinds(self):
        # All changes are live, so just show a message
        QMessageBox.information(self, "Saved", "Keybinds saved successfully.")
    def reset_defaults(self):
        keybind_manager.reset_profile(self.current_profile)
    def add_profile(self):
        name, ok = QInputDialog.getText(self, "Add Profile", "Profile name:")
        if ok and name:
            keybind_manager.add_profile(name)
            self.profile_dropdown.addItem(name)
            self.profile_dropdown.setCurrentText(name)
    def delete_profile(self):
        name = self.profile_dropdown.currentText()
        if name == "default":
            QMessageBox.warning(self, "Cannot Delete", "Cannot delete the default profile.")
            return
        keybind_manager.delete_profile(name)
        idx = self.profile_dropdown.findText(name)
        if idx >= 0:
            self.profile_dropdown.removeItem(idx)
        self.profile_dropdown.setCurrentText(keybind_manager.current_profile)
    def on_profile_selected(self, profile):
        keybind_manager.set_profile(profile)
    def on_keybinds_changed(self, keybinds):
        self.keybinds = keybinds
        self.update_table_for_category(self.sidebar.currentRow())
    def on_profile_changed(self, profile):
        self.current_profile = profile
        self.profile_dropdown.setCurrentText(profile) 