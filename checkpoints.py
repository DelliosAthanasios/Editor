import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QDialogButtonBox, QMenu,
    QAction, QMessageBox, QInputDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QTextCursor, QIcon, QColor, QTextCharFormat, QBrush

class Checkpoint:
    """Represents a checkpoint (flag) in the editor."""
    
    def __init__(self, name, line_number, file_path=None, description=""):
        self.name = name
        self.line_number = line_number
        self.file_path = file_path
        self.description = description
        self.creation_time = None  # Could add timestamp later
        
    def __str__(self):
        return f"{self.name} (Line {self.line_number}): {self.description}"

class CheckpointManager(QObject):
    """Manages checkpoints across the editor."""
    
    checkpoint_added = pyqtSignal(Checkpoint)
    checkpoint_removed = pyqtSignal(Checkpoint)
    checkpoint_updated = pyqtSignal(Checkpoint)
    
    def __init__(self):
        super().__init__()
        self.checkpoints = {}  # file_path -> [Checkpoint, ...]
        self.checkpoint_formats = {}  # Store text formats for highlighting
        self.setup_formats()
        
    def setup_formats(self):
        """Setup text formats for checkpoint highlighting."""
        # Default format
        default_format = QTextCharFormat()
        default_format.setBackground(QBrush(QColor("#FFD700")))  # Gold
        self.checkpoint_formats["default"] = default_format
        
        # Additional formats could be added for different types of checkpoints
        important_format = QTextCharFormat()
        important_format.setBackground(QBrush(QColor("#FF6347")))  # Tomato
        self.checkpoint_formats["important"] = important_format
        
        info_format = QTextCharFormat()
        info_format.setBackground(QBrush(QColor("#98FB98")))  # Pale Green
        self.checkpoint_formats["info"] = info_format
        
        warning_format = QTextCharFormat()
        warning_format.setBackground(QBrush(QColor("#FFA500")))  # Orange
        self.checkpoint_formats["warning"] = warning_format
        
    def add_checkpoint(self, checkpoint):
        """Add a checkpoint to the manager."""
        if checkpoint.file_path not in self.checkpoints:
            self.checkpoints[checkpoint.file_path] = []
            
        # Check if checkpoint already exists at this line
        for existing in self.checkpoints[checkpoint.file_path]:
            if existing.line_number == checkpoint.line_number:
                # Update existing checkpoint
                existing.name = checkpoint.name
                existing.description = checkpoint.description
                self.checkpoint_updated.emit(existing)
                return existing
                
        self.checkpoints[checkpoint.file_path].append(checkpoint)
        self.checkpoint_added.emit(checkpoint)
        return checkpoint
        
    def remove_checkpoint(self, checkpoint):
        """Remove a checkpoint from the manager."""
        if checkpoint.file_path in self.checkpoints:
            if checkpoint in self.checkpoints[checkpoint.file_path]:
                self.checkpoints[checkpoint.file_path].remove(checkpoint)
                self.checkpoint_removed.emit(checkpoint)
                return True
        return False
        
    def get_checkpoints(self, file_path=None):
        """Get all checkpoints or checkpoints for a specific file."""
        if file_path:
            return self.checkpoints.get(file_path, [])
        
        # Return all checkpoints
        all_checkpoints = []
        for checkpoints in self.checkpoints.values():
            all_checkpoints.extend(checkpoints)
        return all_checkpoints
        
    def get_checkpoint_at_line(self, file_path, line_number):
        """Get checkpoint at a specific line in a file."""
        if file_path in self.checkpoints:
            for checkpoint in self.checkpoints[file_path]:
                if checkpoint.line_number == line_number:
                    return checkpoint
        return None
        
    def get_next_checkpoint(self, file_path, current_line):
        """Get the next checkpoint after the current line."""
        if file_path not in self.checkpoints:
            return None
            
        next_checkpoint = None
        next_line = float('inf')
        
        for checkpoint in self.checkpoints[file_path]:
            if checkpoint.line_number > current_line and checkpoint.line_number < next_line:
                next_checkpoint = checkpoint
                next_line = checkpoint.line_number
                
        return next_checkpoint
        
    def get_prev_checkpoint(self, file_path, current_line):
        """Get the previous checkpoint before the current line."""
        if file_path not in self.checkpoints:
            return None
            
        prev_checkpoint = None
        prev_line = -1
        
        for checkpoint in self.checkpoints[file_path]:
            if checkpoint.line_number < current_line and checkpoint.line_number > prev_line:
                prev_checkpoint = checkpoint
                prev_line = checkpoint.line_number
                
        return prev_checkpoint
        
    def get_format_for_checkpoint(self, checkpoint):
        """Get the text format for a checkpoint."""
        # Could implement logic to choose format based on checkpoint properties
        return self.checkpoint_formats["default"]
        
    def clear_checkpoints(self, file_path=None):
        """Clear all checkpoints or checkpoints for a specific file."""
        if file_path:
            if file_path in self.checkpoints:
                checkpoints = self.checkpoints[file_path].copy()
                for checkpoint in checkpoints:
                    self.remove_checkpoint(checkpoint)
                del self.checkpoints[file_path]
        else:
            file_paths = list(self.checkpoints.keys())
            for path in file_paths:
                self.clear_checkpoints(path)

class CheckpointDialog(QDialog):
    """Dialog for creating or editing a checkpoint."""
    
    def __init__(self, parent=None, checkpoint=None, line_number=None, file_path=None):
        super().__init__(parent)
        self.setWindowTitle("Checkpoint" if checkpoint else "Create Checkpoint")
        self.checkpoint = checkpoint
        self.line_number = line_number if checkpoint is None else checkpoint.line_number
        self.file_path = file_path if checkpoint is None else checkpoint.file_path
        self.name_edit = None
        self.desc_edit = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Checkpoint information
        form_layout = QVBoxLayout()
        
        # Name input
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        # Get name input with error handling
        name_default = self.checkpoint.name if self.checkpoint else f"Checkpoint {self.line_number + 1 if self.line_number is not None else ''}"
        name_input_tuple = QInputDialog.getText(
            self, "Checkpoint Name", "Enter checkpoint name:",
            text=name_default
        )
        if name_input_tuple and len(name_input_tuple) > 0:
            self.name_edit = name_input_tuple[0]
        else:
            self.name_edit = ""
        form_layout.addLayout(name_layout)
        
        # Description input
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        desc_default = self.checkpoint.description if self.checkpoint else ""
        desc_input_tuple = QInputDialog.getText(
            self, "Checkpoint Description", "Enter checkpoint description:",
            text=desc_default
        )
        if desc_input_tuple and len(desc_input_tuple) > 0:
            self.desc_edit = desc_input_tuple[0]
        else:
            self.desc_edit = ""
        form_layout.addLayout(desc_layout)
        
        layout.addLayout(form_layout)
        
        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_checkpoint(self):
        """Get the checkpoint from the dialog."""
        if not self.name_edit:
            return None
            
        if self.checkpoint:
            # Update existing checkpoint
            self.checkpoint.name = self.name_edit
            self.checkpoint.description = self.desc_edit
            return self.checkpoint
        else:
            # Create new checkpoint
            return Checkpoint(
                name=self.name_edit,
                line_number=self.line_number,
                file_path=self.file_path,
                description=self.desc_edit
            )

class CheckpointManagerDialog(QDialog):
    """Dialog for managing checkpoints."""
    
    def __init__(self, parent=None, checkpoint_manager=None):
        super().__init__(parent)
        self.setWindowTitle("Checkpoint Manager")
        self.checkpoint_manager = checkpoint_manager
        self.selected_checkpoint = None
        self.init_ui()
        self.resize(500, 400)
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Checkpoint list
        self.checkpoint_list = QListWidget()
        self.checkpoint_list.setSelectionMode(QListWidget.SingleSelection)
        self.checkpoint_list.itemClicked.connect(self.on_checkpoint_selected)
        self.checkpoint_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.checkpoint_list.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.checkpoint_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.goto_btn = QPushButton("Go to Checkpoint")
        self.goto_btn.clicked.connect(self.goto_checkpoint)
        self.goto_btn.setEnabled(False)
        button_layout.addWidget(self.goto_btn)
        
        self.remove_btn = QPushButton("Remove Checkpoint")
        self.remove_btn.clicked.connect(self.remove_checkpoint)
        self.remove_btn.setEnabled(False)
        button_layout.addWidget(self.remove_btn)
        
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.clear_checkpoints)
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        
        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Populate list
        self.refresh_checkpoint_list()
        
    def refresh_checkpoint_list(self):
        """Refresh the checkpoint list."""
        self.checkpoint_list.clear()
        
        checkpoints = self.checkpoint_manager.get_checkpoints()
        for checkpoint in checkpoints:
            item = QListWidgetItem(str(checkpoint))
            item.setData(Qt.UserRole, checkpoint)
            self.checkpoint_list.addItem(item)
            
    def on_checkpoint_selected(self, item):
        """Handle checkpoint selection."""
        self.selected_checkpoint = item.data(Qt.UserRole)
        self.goto_btn.setEnabled(True)
        self.remove_btn.setEnabled(True)
        
    def goto_checkpoint(self):
        """Go to the selected checkpoint."""
        if self.selected_checkpoint:
            self.accept()
            
    def remove_checkpoint(self):
        """Remove the selected checkpoint."""
        if self.selected_checkpoint:
            self.checkpoint_manager.remove_checkpoint(self.selected_checkpoint)
            self.refresh_checkpoint_list()
            self.selected_checkpoint = None
            self.goto_btn.setEnabled(False)
            self.remove_btn.setEnabled(False)
            
    def clear_checkpoints(self):
        """Clear all checkpoints."""
        confirm = QMessageBox.question(
            self,
            "Confirm Clear",
            "Are you sure you want to clear all checkpoints?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            self.checkpoint_manager.clear_checkpoints()
            self.refresh_checkpoint_list()
            self.selected_checkpoint = None
            self.goto_btn.setEnabled(False)
            self.remove_btn.setEnabled(False)
            
    def show_context_menu(self, pos):
        """Show context menu for checkpoint list."""
        item = self.checkpoint_list.itemAt(pos)
        if item:
            checkpoint = item.data(Qt.UserRole)
            
            menu = QMenu(self)
            goto_action = menu.addAction("Go to Checkpoint")
            remove_action = menu.addAction("Remove Checkpoint")
            
            action = menu.exec_(self.checkpoint_list.mapToGlobal(pos))
            
            if action == goto_action:
                self.selected_checkpoint = checkpoint
                self.goto_checkpoint()
            elif action == remove_action:
                self.selected_checkpoint = checkpoint
                self.remove_checkpoint()
                
    def get_selected_checkpoint(self):
        """Get the selected checkpoint."""
        return self.selected_checkpoint

# --------- Methods originally from checkpoint_methods.py, now integrated ---------

class CheckpointEditorMixin:
    """Mixin providing checkpoint-related editor methods."""
    
    def create_checkpoint(self):
        """Create a checkpoint at the current cursor position."""
        current_tab = getattr(self, 'tabs', None)
        if current_tab is None or not hasattr(current_tab, 'currentWidget'):
            QMessageBox.warning(self, "Warning", "No tab system found.")
            return
        
        active_tab = current_tab.currentWidget()
        if not active_tab or not hasattr(active_tab, "editor"):
            QMessageBox.warning(self, "Warning", "No editor tab active.")
            return
            
        editor = active_tab.editor
        cursor = editor.textCursor()
        line_number = cursor.blockNumber()
        file_path = getattr(active_tab, "_file_path", None)
        
        # Create checkpoint dialog
        dialog = CheckpointDialog(
            self, 
            line_number=line_number,
            file_path=file_path
        )
        
        if dialog.exec_():
            checkpoint = dialog.get_checkpoint()
            if checkpoint:
                self.checkpoint_manager.add_checkpoint(checkpoint)
                self.highlight_checkpoint(active_tab, checkpoint)
                QMessageBox.information(
                    self, 
                    "Checkpoint Created", 
                    f"Checkpoint '{checkpoint.name}' created at line {line_number + 1}."
                )
    
    def highlight_checkpoint(self, tab, checkpoint):
        """Highlight a checkpoint in the editor."""
        if not hasattr(tab, "editor"):
            return
            
        editor = tab.editor
        format = self.checkpoint_manager.get_format_for_checkpoint(checkpoint)
        
        # Create a cursor at the checkpoint line
        try:
            block = editor.document().findBlockByNumber(checkpoint.line_number)
            if not block or not block.isValid():
                return
            cursor = QTextCursor(block)
            cursor.select(QTextCursor.LineUnderCursor)
            cursor.setCharFormat(format)
        except Exception as e:
            print(f"Highlighting checkpoint failed: {e}")
    
    def goto_next_checkpoint(self):
        """Go to the next checkpoint in the current file."""
        current_tab = getattr(self, 'tabs', None)
        if current_tab is None or not hasattr(current_tab, 'currentWidget'):
            QMessageBox.warning(self, "Warning", "No tab system found.")
            return
        
        active_tab = current_tab.currentWidget()
        if not active_tab or not hasattr(active_tab, "editor"):
            QMessageBox.warning(self, "Warning", "No editor tab active.")
            return
            
        editor = active_tab.editor
        cursor = editor.textCursor()
        current_line = cursor.blockNumber()
        file_path = getattr(active_tab, "_file_path", None)
        
        if not file_path:
            QMessageBox.warning(self, "Warning", "Please save the file first.")
            return
            
        next_checkpoint = self.checkpoint_manager.get_next_checkpoint(file_path, current_line)
        if next_checkpoint:
            self.goto_checkpoint_line(editor, next_checkpoint.line_number)
        else:
            QMessageBox.information(self, "No Checkpoint", "No next checkpoint found.")
    
    def goto_prev_checkpoint(self):
        """Go to the previous checkpoint in the current file."""
        current_tab = getattr(self, 'tabs', None)
        if current_tab is None or not hasattr(current_tab, 'currentWidget'):
            QMessageBox.warning(self, "Warning", "No tab system found.")
            return
        
        active_tab = current_tab.currentWidget()
        if not active_tab or not hasattr(active_tab, "editor"):
            QMessageBox.warning(self, "Warning", "No editor tab active.")
            return
            
        editor = active_tab.editor
        cursor = editor.textCursor()
        current_line = cursor.blockNumber()
        file_path = getattr(active_tab, "_file_path", None)
        
        if not file_path:
            QMessageBox.warning(self, "Warning", "Please save the file first.")
            return
            
        prev_checkpoint = self.checkpoint_manager.get_prev_checkpoint(file_path, current_line)
        if prev_checkpoint:
            self.goto_checkpoint_line(editor, prev_checkpoint.line_number)
        else:
            QMessageBox.information(self, "No Checkpoint", "No previous checkpoint found.")
    
    def goto_checkpoint_line(self, editor, line_number):
        """Go to a specific line in the editor."""
        try:
            block = editor.document().findBlockByNumber(line_number)
            if not block or not block.isValid():
                QMessageBox.warning(self, "Warning", "Line number out of range.")
                return
            cursor = QTextCursor(block)
            editor.setTextCursor(cursor)
            editor.centerCursor()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not go to checkpoint line: {e}")
    
    def open_checkpoint_manager(self):
        """Open the checkpoint manager dialog."""
        dialog = CheckpointManagerDialog(self, self.checkpoint_manager)
        if dialog.exec_() and dialog.selected_checkpoint:
            checkpoint = dialog.get_selected_checkpoint()
            if checkpoint and checkpoint.file_path:
                # Open the file if not already open
                self.open_file_in_editor_tab(checkpoint.file_path)
                
                # Find the tab with this file
                found_tab = False
                for i in range(self.tabs.count()):
                    tab = self.tabs.widget(i)
                    if hasattr(tab, "_file_path") and tab._file_path == checkpoint.file_path:
                        self.tabs.setCurrentIndex(i)
                        if hasattr(tab, "editor"):
                            self.goto_checkpoint_line(tab.editor, checkpoint.line_number)
                        found_tab = True
                        break
                if not found_tab:
                    QMessageBox.warning(self, "Warning", f"Could not find tab for file: {checkpoint.file_path}")

# END OF MERGED MODULE
