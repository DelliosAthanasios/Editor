import json
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QPushButton,
    QHBoxLayout, QLineEdit, QMessageBox, QHeaderView, QShortcut, QWidget, QApplication, QInputDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence, QTextCursor

KEYBINDS_CONFIG_PATH = "keybinds_config.json"

# Extended default keybinds (Emacs-like text traversal included)
DEFAULT_KEYBINDS = {
    "Undo": {"keys": "Ctrl+Z", "description": "Undo last change"},
    "Redo": {"keys": "Ctrl+Y", "description": "Redo last undone change"},
    "Select All": {"keys": "Ctrl+A", "description": "Select all text"},
    "Search": {"keys": "Ctrl+F", "description": "Find text/search"},
    "Replace": {"keys": "Ctrl+H", "description": "Search and replace"},
    "Go to Line": {"keys": "Ctrl+G", "description": "Go to a specific line"},
    "Go to Word": {"keys": "Ctrl+Shift+W", "description": "Go to a word"},
    "Save File": {"keys": "Ctrl+S", "description": "Save current file"},
    "Open File": {"keys": "Ctrl+O", "description": "Open file"},
    "New File": {"keys": "Ctrl+N", "description": "Create new file"},
    "Close Tab": {"keys": "Ctrl+W", "description": "Close current tab"},
    "Duplicate File": {"keys": "Ctrl+D", "description": "Duplicate file"},
    "Toggle Minimap": {"keys": "Alt+M", "description": "Show/hide minimap"},
    "Toggle Number Line": {"keys": "Alt+L", "description": "Show/hide number line"},
    "Toggle File Tree": {"keys": "Alt+F", "description": "Show/hide file tree"},
    # --- Emacs-like text traversal ---
    "Go to Start of Line": {"keys": "Ctrl+A", "description": "Move cursor to start of line"},
    "Go to End of Line": {"keys": "Ctrl+E", "description": "Move cursor to end of line"},
    "Go to Next Word": {"keys": "Alt+F", "description": "Move cursor to next word"},
    "Go to Previous Word": {"keys": "Alt+B", "description": "Move cursor to previous word"},
    "Go Up One Line": {"keys": "Ctrl+P", "description": "Move cursor up one line"},
    "Go Down One Line": {"keys": "Ctrl+N", "description": "Move cursor down one line"},
    "Go Forward One Char": {"keys": "Ctrl+F", "description": "Move cursor forward one character"},
    "Go Backward One Char": {"keys": "Ctrl+B", "description": "Move cursor backward one character"},
    "Go to Start of Document": {"keys": "Alt+<", "description": "Move cursor to start of document"},
    "Go to End of Document": {"keys": "Alt+>", "description": "Move cursor to end of document"},
    "Delete Current Line": {"keys": "Ctrl+K", "description": "Delete from cursor to end of line"},
    "Transpose Characters": {"keys": "Ctrl+T", "description": "Transpose (swap) characters at cursor"},
    "Set Mark": {"keys": "Ctrl+Space", "description": "Set selection mark (begin selection)"},
    "Select to End of Line": {"keys": "Shift+End", "description": "Select text to end of line"},
    "Select to Start of Line": {"keys": "Shift+Home", "description": "Select text to start of line"},
}

def load_keybinds():
    if os.path.exists(KEYBINDS_CONFIG_PATH):
        try:
            with open(KEYBINDS_CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_KEYBINDS.copy()

def save_keybinds(keybinds):
    try:
        with open(KEYBINDS_CONFIG_PATH, "w") as f:
            json.dump(keybinds, f, indent=2)
    except Exception as e:
        print("Failed to save keybinds:", e)

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
    """
    A QLineEdit that only accepts key sequences (like Ctrl+S).
    """
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
        # Ignore modifiers themselves
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt):
            return
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
            # Check for conflicts
            for i in range(self.table.rowCount()):
                if i != row and self.table.item(i, 1).text() == new_seq:
                    QMessageBox.warning(self, "Conflict", f"{new_seq} is already assigned to another action.")
                    return
            self.keybinds[action]["keys"] = new_seq
            self.table.setItem(row, 1, QTableWidgetItem(new_seq))

    def save(self):
        # Save table to keybinds dict
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

# --- Editor Action Helpers for Emacs-like navigation ---

def get_current_editor(main_window):
    tabs = getattr(main_window, "tabs", None)
    if not tabs:
        return None
    widget = tabs.currentWidget()
    if widget and hasattr(widget, "editor"):
        return widget.editor
    return None

def emacs_go_start_of_line(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.StartOfLine)
        editor.setTextCursor(cursor)

def emacs_go_end_of_line(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.EndOfLine)
        editor.setTextCursor(cursor)

def emacs_go_next_word(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.NextWord)
        editor.setTextCursor(cursor)

def emacs_go_prev_word(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.PreviousWord)
        editor.setTextCursor(cursor)

def emacs_go_up_one_line(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Up)
        editor.setTextCursor(cursor)

def emacs_go_down_one_line(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Down)
        editor.setTextCursor(cursor)

def emacs_forward_char(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Right)
        editor.setTextCursor(cursor)

def emacs_backward_char(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Left)
        editor.setTextCursor(cursor)

def emacs_go_start_of_doc(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        editor.setTextCursor(cursor)

def emacs_go_end_of_doc(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        editor.setTextCursor(cursor)

def emacs_delete_to_end_of_line(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        editor.setTextCursor(cursor)

def emacs_transpose_chars(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        pos = cursor.position()
        if pos == 0:
            return
        cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor)
        left_char = cursor.selectedText()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
        right_char = cursor.selectedText()
        if left_char and right_char:
            cursor.insertText(right_char + left_char)
            cursor.movePosition(QTextCursor.Left)
            editor.setTextCursor(cursor)

def emacs_set_mark(main_window):
    # In PyQt, the selection is set by moving with KeepAnchor
    # We can remember the position, and next movement with shift will use it
    # Here, just clear selection (simulate "set mark" as "start selection")
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.clearSelection()
        editor.setTextCursor(cursor)

def emacs_select_to_end_of_line(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
        editor.setTextCursor(cursor)

def emacs_select_to_start_of_line(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)
        editor.setTextCursor(cursor)

# -- Integration Helper Functions --

def apply_keybinds_to_editor(main_window, keybinds):
    """
    Binds all editor actions to user-configured keybinds.
    Call after loading or changing keybinds.
    """
    tabwidget = main_window.tabs
    # Remove all old shortcuts (optional: not necessary unless you want to clean up)
    # Iterate actions and set new shortcuts
    action_map = {
        "Undo": main_window.trigger_undo,
        "Redo": main_window.trigger_redo,
        "Select All": main_window.trigger_select_all,
        "Search": lambda: main_window.trigger_search() if hasattr(main_window, "trigger_search") else None,
        "Replace": lambda: main_window.trigger_replace() if hasattr(main_window, "trigger_replace") else None,
        "Go to Line": lambda: main_window.trigger_goto_line() if hasattr(main_window, "trigger_goto_line") else None,
        "Go to Word": lambda: main_window.trigger_goto_word() if hasattr(main_window, "trigger_goto_word") else None,
        "Save File": main_window.save_file,
        "Open File": main_window.open_file,
        "New File": main_window.new_file,
        "Close Tab": lambda: main_window.close_tab(tabwidget.currentIndex()),
        "Duplicate File": main_window.duplicate_file,
        "Toggle Minimap": main_window.toggle_minimap,
        "Toggle Number Line": main_window.view_toggle_numberline,
        "Toggle File Tree": main_window.toggle_file_tree,
        # --- Emacs-like navigation ---
        "Go to Start of Line": lambda: emacs_go_start_of_line(main_window),
        "Go to End of Line": lambda: emacs_go_end_of_line(main_window),
        "Go to Next Word": lambda: emacs_go_next_word(main_window),
        "Go to Previous Word": lambda: emacs_go_prev_word(main_window),
        "Go Up One Line": lambda: emacs_go_up_one_line(main_window),
        "Go Down One Line": lambda: emacs_go_down_one_line(main_window),
        "Go Forward One Char": lambda: emacs_forward_char(main_window),
        "Go Backward One Char": lambda: emacs_backward_char(main_window),
        "Go to Start of Document": lambda: emacs_go_start_of_doc(main_window),
        "Go to End of Document": lambda: emacs_go_end_of_doc(main_window),
        "Delete Current Line": lambda: emacs_delete_to_end_of_line(main_window),
        "Transpose Characters": lambda: emacs_transpose_chars(main_window),
        "Set Mark": lambda: emacs_set_mark(main_window),
        "Select to End of Line": lambda: emacs_select_to_end_of_line(main_window),
        "Select to Start of Line": lambda: emacs_select_to_start_of_line(main_window),
    }

    # Remove previous shortcuts if any
    if not hasattr(main_window, "_keybind_shortcuts"):
        main_window._keybind_shortcuts = []
    for sc in main_window._keybind_shortcuts:
        sc.setParent(None)
    main_window._keybind_shortcuts = []

    for action, info in keybinds.items():
        keys = info["keys"]
        func = action_map.get(action)
        if not keys or not func:
            continue
        try:
            shortcut = QShortcut(QKeySequence(keys), main_window)
            shortcut.activated.connect(func)
            main_window._keybind_shortcuts.append(shortcut)
        except Exception as e:
            print(f"Error binding shortcut for {action}: {e}")

def show_default_keybinds(main_window):
    keybinds = load_keybinds()
    dlg = KeybindsWindow(keybinds, main_window)
    dlg.exec_()

def configure_keybinds(main_window):
    keybinds = load_keybinds()
    dlg = ConfigureKeybindsWindow(keybinds, main_window)
    def on_keybinds_changed(new_keybinds):
        apply_keybinds_to_editor(main_window, new_keybinds)
    dlg.keybinds_changed.connect(on_keybinds_changed)
    dlg.exec_()

def integrate_keybinds_menu(main_window):
    """
    Call this after main_window is created, in __main__.
    Wires the keybinds functionality to the keybinds menu.
    """
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
    # Apply keybinds to editor on startup
    apply_keybinds_to_editor(main_window, load_keybinds())

# --- Example usage in your main.py:
# import keybinds
# keybinds.integrate_keybinds_menu(window)
# Place after you create window = TextEditor(), and before window.show()