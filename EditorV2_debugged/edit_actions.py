import re
from PyQt5.QtWidgets import (
    QInputDialog, QLineEdit, QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit, QWidget, QHBoxLayout
)
from PyQt5.QtCore import Qt

def connect_edit_menu(main_window):
    """
    Connects the Edit menu actions in main.py's TextEditor to the appropriate functions.
    Call this function from your main.py after creating the main window.
    """

    menu_bar = main_window.menuBar()
    edit_menu = menu_bar.findChild(type(menu_bar), "Edit")
    if edit_menu is None:
        # Fallback: find by text
        for i in range(menu_bar.actions().__len__()):
            if menu_bar.actions()[i].text() == "Edit":
                edit_menu = menu_bar.actions()[i].menu()
                break

    if edit_menu is None:
        print("Edit menu not found.")
        return

    # Helper to get current QTextEdit
    def get_editor():
        widget = main_window.tabs.currentWidget()
        return getattr(widget, "editor", None) if widget else None

    # --- Undo ---
    undo_action = edit_menu.actions()[0]
    undo_action.triggered.connect(lambda: get_editor().undo() if get_editor() else None)

    # --- Redo ---
    redo_action = edit_menu.actions()[1]
    redo_action.triggered.connect(lambda: get_editor().redo() if get_editor() else None)

    # --- Select All ---
    select_all_action = edit_menu.actions()[2]
    select_all_action.triggered.connect(lambda: get_editor().selectAll() if get_editor() else None)

    # --- Search/Replace ---
    search_menu = None
    for action in edit_menu.actions():
        if action.menu() and action.text() == "Search":
            search_menu = action.menu()
            break

    if search_menu:
        search_replace_action = search_menu.actions()[0]
        search_replace_action.triggered.connect(lambda: open_search_replace_dialog(main_window, get_editor()))

    # --- Go To ---
    goto_menu = None
    for action in edit_menu.actions():
        if action.menu() and action.text() == "Go To":
            goto_menu = action.menu()
            break

    if goto_menu:
        line_action = goto_menu.actions()[0]
        word_action = goto_menu.actions()[1]
        line_action.triggered.connect(lambda: goto_line_dialog(main_window, get_editor()))
        word_action.triggered.connect(lambda: goto_word_dialog(main_window, get_editor()))

def open_search_replace_dialog(parent, editor: QTextEdit):
    if not editor:
        return

    class SearchReplaceDialog(QDialog):
        def __init__(self):
            super().__init__(parent)
            self.setWindowTitle("Search and Replace")
            self.setModal(True)
            layout = QVBoxLayout()
            self.search_input = QLineEdit(self)
            self.search_input.setPlaceholderText("Search for...")
            self.replace_input = QLineEdit(self)
            self.replace_input.setPlaceholderText("Replace with...")
            self.case_checkbox = QPushButton("Case Sensitive", self)
            self.case_checkbox.setCheckable(True)
            self.replace_btn = QPushButton("Replace All", self)
            self.find_btn = QPushButton("Find Next", self)
            btns = QHBoxLayout()
            btns.addWidget(self.find_btn)
            btns.addWidget(self.replace_btn)
            layout.addWidget(QLabel("Find:"))
            layout.addWidget(self.search_input)
            layout.addWidget(QLabel("Replace:"))
            layout.addWidget(self.replace_input)
            layout.addWidget(self.case_checkbox)
            layout.addLayout(btns)
            self.setLayout(layout)
            self.resize(350, 150)

            self.find_btn.clicked.connect(self.find_next)
            self.replace_btn.clicked.connect(self.replace_all)

            self.editor = editor

        def find_next(self):
            text = self.search_input.text()
            if not text:
                return
            flags = Qt.MatchFlags()
            options = QTextEdit.FindFlags()
            if self.case_checkbox.isChecked():
                options |= QTextEdit.FindCaseSensitively

            cursor = self.editor.textCursor()
            # Move cursor to after the last match
            pos = cursor.position()
            if not self.editor.find(text, options):
                # If not found, start from top
                cursor.setPosition(0)
                self.editor.setTextCursor(cursor)
                if not self.editor.find(text, options):
                    QMessageBox.information(self, "Find", "No matches found.")

        def replace_all(self):
            search = self.search_input.text()
            replace = self.replace_input.text()
            if not search:
                return
            options = QTextEdit.FindFlags()
            if self.case_checkbox.isChecked():
                options |= QTextEdit.FindCaseSensitively
            cursor = self.editor.textCursor()
            cursor.setPosition(0)
            self.editor.setTextCursor(cursor)
            count = 0
            while self.editor.find(search, options):
                cursor = self.editor.textCursor()
                cursor.beginEditBlock()
                cursor.removeSelectedText()
                cursor.insertText(replace)
                cursor.endEditBlock()
                count += 1
            QMessageBox.information(self, "Replace", f"Replaced {count} occurrence(s).")

    dialog = SearchReplaceDialog()
    dialog.exec_()

def goto_line_dialog(parent, editor: QTextEdit):
    if not editor:
        return
    max_line = editor.document().blockCount()
    num, ok = QInputDialog.getInt(parent, "Go to Line", f"Enter line number (1 - {max_line}):", 1, 1, max_line)
    if ok:
        block = editor.document().findBlockByNumber(num - 1)
        if block.isValid():
            cursor = editor.textCursor()
            cursor.setPosition(block.position())
            editor.setTextCursor(cursor)
            editor.setFocus()

def goto_word_dialog(parent, editor: QTextEdit):
    if not editor:
        return
    word, ok = QInputDialog.getText(parent, "Go to Word", "Enter word to find:")
    if ok and word:
        document = editor.document()
        block = document.firstBlock()
        found = False
        while block.isValid() and not found:
            text = block.text()
            index = text.find(word)
            if index != -1:
                cursor = editor.textCursor()
                cursor.setPosition(block.position() + index)
                editor.setTextCursor(cursor)
                editor.setFocus()
                found = True
                break
            block = block.next()
        if not found:
            QMessageBox.information(parent, "Go to Word", f"Word '{word}' not found.")

# Usage:
# In main.py, after creating the TextEditor window, do:
# import edit_actions
# edit_actions.connect_edit_menu(window)