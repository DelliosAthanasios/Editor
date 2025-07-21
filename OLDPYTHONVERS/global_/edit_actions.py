import re
from functools import partial
from PyQt5.QtWidgets import (
    QInputDialog, QLineEdit, QMessageBox, QDialog, QVBoxLayout, QLabel, 
    QPushButton, QTextEdit, QWidget, QHBoxLayout, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QTextCharFormat, QColor, QTextCursor, QTextDocument

class SearchReplaceDialog(QDialog):
    def __init__(self, parent=None, editor=None, mode="find"):
        super().__init__(parent)
        self.setWindowTitle("Find" if mode == "find" else "Find and Replace")
        self.setModal(True)
        self.mode = mode
        
        # Initialize all instance variables FIRST
        self.editor = editor
        self.matches = []
        self.current_match_index = -1
        self.extra_selections = []
        
        # Initialize formats
        self.highlight_format = QTextCharFormat()
        self.highlight_format.setBackground(QColor("#FFEB3B"))  # Light yellow
        self.active_format = QTextCharFormat()
        self.active_format.setBackground(QColor("#FFC107"))  # Orange for current
        
        # Create layout
        layout = QVBoxLayout()

        # Search input
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search for...")

        # Replace input (only visible in replace mode)
        self.replace_input = QLineEdit(self)
        self.replace_input.setPlaceholderText("Replace with...")
        self.replace_input.setVisible(mode == "replace")

        # Options - Use QCheckBox instead of QPushButton for better reliability
        self.case_checkbox = QCheckBox("Case Sensitive", self)
        self.case_checkbox.setChecked(False)

        # Buttons
        btn_layout = QHBoxLayout()
        self.find_btn = QPushButton("Find", self)
        self.replace_btn = QPushButton("Replace All", self)
        self.replace_btn.setVisible(mode == "replace")
        
        # Add Replace Selected button
        self.replace_selected_btn = QPushButton("Replace Selected", self)
        self.replace_selected_btn.setVisible(mode == "replace")
        self.replace_selected_btn.setEnabled(False)  # Disabled until there's a current match

        # Navigation buttons
        self.prev_btn = QPushButton("◀", self)  # Better arrow symbols
        self.next_btn = QPushButton("▶", self)
        self.prev_btn.setFixedWidth(30)
        self.next_btn.setFixedWidth(30)
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        
        # Match counter
        self.match_counter_label = QLabel("0/0", self)
        self.match_counter_label.setFixedWidth(60)
        self.match_counter_label.setAlignment(Qt.AlignCenter)
        self.match_counter_label.setStyleSheet("border: 1px solid gray; padding: 2px;")

        btn_layout.addWidget(self.find_btn)
        btn_layout.addWidget(self.prev_btn)
        btn_layout.addWidget(self.match_counter_label)
        btn_layout.addWidget(self.next_btn)
        if mode == "replace":
            btn_layout.addWidget(self.replace_selected_btn)
            btn_layout.addWidget(self.replace_btn)

        # Status label
        self.status_label = QLabel("", self)
        self.status_label.setStyleSheet("color: blue;")

        # Add to layout
        layout.addWidget(QLabel("Find:"))
        layout.addWidget(self.search_input)
        if mode == "replace":
            layout.addWidget(QLabel("Replace:"))
            layout.addWidget(self.replace_input)
        layout.addWidget(self.case_checkbox)
        layout.addLayout(btn_layout)
        layout.addWidget(self.status_label)

        self.setLayout(layout)
        self.resize(400, 200 if mode == "find" else 280)

        # Connect signals AFTER everything is initialized
        self.setup_connections()
        
        # Focus on search input
        self.search_input.setFocus()

    def setup_connections(self):
        """Setup all signal connections safely"""
        try:
            self.find_btn.clicked.connect(self.highlight_all_matches)
            self.next_btn.clicked.connect(lambda: self.goto_match(1))
            self.prev_btn.clicked.connect(lambda: self.goto_match(-1))
            self.replace_btn.clicked.connect(self.replace_all)
            self.replace_selected_btn.clicked.connect(self.replace_selected)
            self.search_input.returnPressed.connect(self.highlight_all_matches)
            self.search_input.textChanged.connect(self.on_search_text_changed)
            self.case_checkbox.toggled.connect(self.on_search_text_changed)
        except Exception as e:
            print(f"Error setting up connections: {e}")

    def closeEvent(self, event):
        """Clean up when dialog closes"""
        self.clear_highlights()
        super().closeEvent(event)

    def highlight_all_matches(self):
        """Find and highlight all matches in the document"""
        if not self.editor:
            self.status_label.setText("No editor available")
            return
            
        search_text = self.search_input.text().strip()
        if not search_text:
            self.status_label.setText("Please enter text to search")
            self.clear_all()
            return

        try:
            self.clear_highlights()
            doc = self.editor.document()
            
            # Escape special regex characters for literal search
            pattern = re.escape(search_text)
            flags = 0 if self.case_checkbox.isChecked() else re.IGNORECASE

            self.matches = []
            
            # Search through all blocks
            block = doc.firstBlock()
            while block.isValid():
                text = block.text()
                block_position = block.position()
                
                # Find all matches in this block
                for match in re.finditer(pattern, text, flags):
                    start_pos = block_position + match.start()
                    end_pos = block_position + match.end()
                    self.matches.append((start_pos, end_pos))
                
                block = block.next()

            if not self.matches:
                self.status_label.setText("No matches found")
                self.clear_all()
                return

            # Set first match as current
            self.current_match_index = 0
            self.update_ui_state()
            self.apply_highlights()
            self.center_on_current_match()
            
            self.status_label.setText(f"Found {len(self.matches)} match(es)")
            
        except Exception as e:
            self.status_label.setText(f"Search error: {str(e)}")
            self.clear_all()

    def clear_highlights(self):
        """Clear all highlights from the editor"""
        if self.editor:
            try:
                self.editor.setExtraSelections([])
            except Exception as e:
                print(f"Error clearing highlights: {e}")

    def clear_all(self):
        """Clear all search state"""
        self.matches = []
        self.current_match_index = -1
        self.update_ui_state()
        self.clear_highlights()

    def on_search_text_changed(self):
        """Handle search text changes"""
        self.status_label.setText("")
        self.clear_all()

    def update_ui_state(self):
        """Update UI buttons and counter"""
        has_matches = bool(self.matches)
        has_current_match = has_matches and self.current_match_index >= 0
        
        self.prev_btn.setEnabled(has_matches)
        self.next_btn.setEnabled(has_matches)
        self.replace_selected_btn.setEnabled(has_current_match)
        
        if not has_matches:
            self.match_counter_label.setText("0/0")
        else:
            current = self.current_match_index + 1 if self.current_match_index >= 0 else 0
            self.match_counter_label.setText(f"{current}/{len(self.matches)}")

    def apply_highlights(self):
        """Apply highlights to all matches"""
        if not self.editor or not self.matches:
            self.clear_highlights()
            return

        try:
            selections = []
            for i, (start, end) in enumerate(self.matches):
                selection = QTextEdit.ExtraSelection()
                cursor = QTextCursor(self.editor.document())
                cursor.setPosition(start)
                cursor.setPosition(end, QTextCursor.KeepAnchor)
                selection.cursor = cursor
                
                # Use different format for current match
                if i == self.current_match_index:
                    selection.format = self.active_format
                else:
                    selection.format = self.highlight_format
                    
                selections.append(selection)
            
            self.editor.setExtraSelections(selections)
            
        except Exception as e:
            print(f"Error applying highlights: {e}")

    def goto_match(self, direction):
        """Navigate to next/previous match"""
        if not self.matches:
            return

        # Calculate new index with wrapping
        if direction > 0:  # Next
            self.current_match_index = (self.current_match_index + 1) % len(self.matches)
        else:  # Previous
            self.current_match_index = (self.current_match_index - 1) % len(self.matches)

        self.update_ui_state()
        self.apply_highlights()
        self.center_on_current_match()

    def center_on_current_match(self):
        """Center the editor view on the current match"""
        if not self.matches or self.current_match_index < 0:
            return
            
        try:
            start, end = self.matches[self.current_match_index]
            cursor = self.editor.textCursor()
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            self.editor.setTextCursor(cursor)
            # Use ensureCursorVisible() instead of centerCursor()
            self.editor.ensureCursorVisible()
        except Exception as e:
            print(f"Error centering on match: {e}")

    def replace_selected(self):
        """Replace only the currently selected/highlighted match"""
        if not self.editor or not self.matches or self.current_match_index < 0:
            self.status_label.setText("No current match to replace")
            return
            
        replace_text = self.replace_input.text()
        
        try:
            start, end = self.matches[self.current_match_index]
            cursor = QTextCursor(self.editor.document())
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            cursor.insertText(replace_text)
            
            self.status_label.setText("Replaced current match")
            
            # After replacement, we need to refresh the search to update positions
            # Store the search parameters to re-run the search
            search_text = self.search_input.text().strip()
            if search_text:
                # Small delay to allow the document to update, then refresh
                self.highlight_all_matches()
            else:
                self.clear_all()
                
        except Exception as e:
            self.status_label.setText(f"Replace error: {str(e)}")

    def replace_all(self):
        """Replace all occurrences"""
        if not self.editor:
            self.status_label.setText("No editor available")
            return
            
        search_text = self.search_input.text().strip()
        replace_text = self.replace_input.text()
        
        if not search_text:
            self.status_label.setText("Please enter text to search")
            return

        try:
            # Find all matches first
            doc = self.editor.document()
            pattern = re.escape(search_text)
            flags = 0 if self.case_checkbox.isChecked() else re.IGNORECASE

            matches = []
            block = doc.firstBlock()
            while block.isValid():
                text = block.text()
                block_position = block.position()
                
                for match in re.finditer(pattern, text, flags):
                    start_pos = block_position + match.start()
                    end_pos = block_position + match.end()
                    matches.append((start_pos, end_pos))
                
                block = block.next()

            if not matches:
                QMessageBox.information(self, "Replace All", "No matches found to replace.")
                self.status_label.setText("No matches found")
                return

            # Replace from end to start to maintain position validity
            cursor = QTextCursor(doc)
            cursor.beginEditBlock()
            
            for start, end in reversed(matches):
                cursor.setPosition(start)
                cursor.setPosition(end, QTextCursor.KeepAnchor)
                cursor.insertText(replace_text)
            
            cursor.endEditBlock()
            
            self.status_label.setText(f"Replaced {len(matches)} occurrence(s)")
            self.clear_all()
            
        except Exception as e:
            self.status_label.setText(f"Replace error: {str(e)}")


def connect_edit_menu(main_window):
    """Connect Edit menu actions to functions"""
    if not main_window:
        return
        
    try:
        menu_bar = main_window.menuBar()
        if not menu_bar:
            return
            
        # Find Edit menu
        edit_menu = None
        for action in menu_bar.actions():
            if action.text() == "Edit" and action.menu():
                edit_menu = action.menu()
                break

        if not edit_menu:
            print("Edit menu not found")
            return

        def safe_get_editor():
            """Safely get the current editor"""
            try:
                if hasattr(main_window, 'tabs') and main_window.tabs:
                    widget = main_window.tabs.currentWidget()
                    if widget and hasattr(widget, 'editor'):
                        return widget.editor
                return None
            except Exception:
                return None

        # Connect basic edit actions
        actions = edit_menu.actions()
        
        if len(actions) > 0:  # Undo
            actions[0].triggered.connect(
                lambda: safe_get_editor().undo() if safe_get_editor() else None
            )
        
        if len(actions) > 1:  # Redo
            actions[1].triggered.connect(
                lambda: safe_get_editor().redo() if safe_get_editor() else None
            )
        
        if len(actions) > 2:  # Select All
            actions[2].triggered.connect(
                lambda: safe_get_editor().selectAll() if safe_get_editor() else None
            )

        # Connect Search submenu
        for action in edit_menu.actions():
            if action.menu() and action.text() == "Search":
                search_menu = action.menu()
                search_actions = search_menu.actions()
                if search_actions:
                    search_actions[0].triggered.connect(
                        lambda: open_search_replace_dialog(main_window, safe_get_editor(), "find")
                    )
                break

        # Connect GoTo submenu
        for action in edit_menu.actions():
            if action.menu() and action.text() == "Go To":
                goto_menu = action.menu()
                goto_actions = goto_menu.actions()
                if len(goto_actions) > 0:
                    goto_actions[0].triggered.connect(
                        lambda: goto_line_dialog(main_window, safe_get_editor())
                    )
                if len(goto_actions) > 1:
                    goto_actions[1].triggered.connect(
                        lambda: goto_word_dialog(main_window, safe_get_editor())
                    )
                break
                
    except Exception as e:
        print(f"Error connecting edit menu: {e}")


def open_search_replace_dialog(parent, editor, mode="find"):
    """Open search/replace dialog"""
    if not editor:
        QMessageBox.information(parent, "Search", "No active editor found.")
        return
        
    try:
        dialog = SearchReplaceDialog(parent, editor, mode)
        dialog.exec_()
    except Exception as e:
        print(f"Error opening search dialog: {e}")
        QMessageBox.critical(parent, "Error", f"Failed to open search dialog: {e}")


def goto_line_dialog(parent, editor):
    """Go to specific line"""
    if not editor:
        return
        
    try:
        max_line = editor.document().blockCount()
        line_num, ok = QInputDialog.getInt(
            parent, "Go to Line", 
            f"Enter line number (1 - {max_line}):", 
            1, 1, max_line
        )
        
        if ok:
            block = editor.document().findBlockByNumber(line_num - 1)
            if block.isValid():
                cursor = editor.textCursor()
                cursor.setPosition(block.position())
                editor.setTextCursor(cursor)
                # Use ensureCursorVisible() instead of centerCursor()
                editor.ensureCursorVisible()
                editor.setFocus()
                
    except Exception as e:
        print(f"Error in goto line: {e}")


def goto_word_dialog(parent, editor):
    """Go to specific word"""
    if not editor:
        return
        
    try:
        word, ok = QInputDialog.getText(parent, "Go to Word", "Enter word to find:")
        if not ok or not word.strip():
            return
            
        word = word.strip()
        document = editor.document()
        
        # Start search from current cursor position
        cursor = editor.textCursor()
        found_cursor = document.find(word, cursor)
        
        if found_cursor.isNull():
            # Search from beginning if not found after cursor
            found_cursor = document.find(word)
            
        if not found_cursor.isNull():
            editor.setTextCursor(found_cursor)
            # Use ensureCursorVisible() instead of centerCursor()
            editor.ensureCursorVisible()
            editor.setFocus()
        else:
            QMessageBox.information(parent, "Go to Word", f"Word '{word}' not found.")
            
    except Exception as e:
        print(f"Error in goto word: {e}")


# Usage:
# In main.py, after creating the TextEditor window, do:
# import edit_actions
# edit_actions.connect_edit_menu(window)
