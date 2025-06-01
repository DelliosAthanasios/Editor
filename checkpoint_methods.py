    def create_checkpoint(self):
        """Create a checkpoint at the current cursor position."""
        current_tab = self.tabs.currentWidget()
        if not current_tab or not hasattr(current_tab, "editor"):
            QMessageBox.warning(self, "Warning", "No editor tab active.")
            return
            
        editor = current_tab.editor
        cursor = editor.textCursor()
        line_number = cursor.blockNumber()
        file_path = getattr(current_tab, "_file_path", None)
        
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
                self.highlight_checkpoint(current_tab, checkpoint)
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
        cursor = QTextCursor(editor.document().findBlockByNumber(checkpoint.line_number))
        
        # Select the entire line
        cursor.select(QTextCursor.LineUnderCursor)
        
        # Apply the format
        cursor.setCharFormat(format)
    
    def goto_next_checkpoint(self):
        """Go to the next checkpoint in the current file."""
        current_tab = self.tabs.currentWidget()
        if not current_tab or not hasattr(current_tab, "editor"):
            QMessageBox.warning(self, "Warning", "No editor tab active.")
            return
            
        editor = current_tab.editor
        cursor = editor.textCursor()
        current_line = cursor.blockNumber()
        file_path = getattr(current_tab, "_file_path", None)
        
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
        current_tab = self.tabs.currentWidget()
        if not current_tab or not hasattr(current_tab, "editor"):
            QMessageBox.warning(self, "Warning", "No editor tab active.")
            return
            
        editor = current_tab.editor
        cursor = editor.textCursor()
        current_line = cursor.blockNumber()
        file_path = getattr(current_tab, "_file_path", None)
        
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
        cursor = QTextCursor(editor.document().findBlockByNumber(line_number))
        editor.setTextCursor(cursor)
        editor.centerCursor()
    
    def open_checkpoint_manager(self):
        """Open the checkpoint manager dialog."""
        dialog = CheckpointManagerDialog(self, self.checkpoint_manager)
        if dialog.exec_() and dialog.selected_checkpoint:
            checkpoint = dialog.get_selected_checkpoint()
            if checkpoint and checkpoint.file_path:
                # Open the file if not already open
                self.open_file_in_editor_tab(checkpoint.file_path)
                
                # Find the tab with this file
                for i in range(self.tabs.count()):
                    tab = self.tabs.widget(i)
                    if hasattr(tab, "_file_path") and tab._file_path == checkpoint.file_path:
                        self.tabs.setCurrentIndex(i)
                        if hasattr(tab, "editor"):
                            self.goto_checkpoint_line(tab.editor, checkpoint.line_number)
                        break
