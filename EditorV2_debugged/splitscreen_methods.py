    def split_horizontally(self):
        self._split_tab(Qt.Horizontal)

    def split_vertically(self):
        self._split_tab(Qt.Vertical)

    def _split_tab(self, orientation):
        tab_count = self.tabs.count()
        tab_names = []
        possible_indexes = []
        for i in range(tab_count):
            widget = self.tabs.widget(i)
            if hasattr(widget, "editor") or isinstance(widget, QSplitter):
                tab_names.append(self.tabs.tabText(i))
                possible_indexes.append(i)
        if not tab_names:
            QMessageBox.warning(self, "Warning", "No editor tab to split.")
            return
        if len(tab_names) == 1:
            index = possible_indexes[0]
            splitscreen.split_tab(self.tabs, index, orientation)
        else:
            # Show a themed popup to select which tab to split
            dialog = splitscreen.SplitChoiceDialog(tab_names, theme=self.theme, parent=self)
            if dialog.exec_() == QDialog.Accepted:
                idx = dialog.selected_tab_index()
                index = possible_indexes[idx]
                # Use the orientation from the dialog
                orientation = dialog.get_orientation()
                splitscreen.split_tab(self.tabs, index, orientation)
                
    def open_custom_split_dialog(self):
        """Open the custom split configuration dialog."""
        tab_count = self.tabs.count()
        tab_names = []
        possible_indexes = []
        for i in range(tab_count):
            widget = self.tabs.widget(i)
            if hasattr(widget, "editor") or isinstance(widget, QSplitter):
                tab_names.append(self.tabs.tabText(i))
                possible_indexes.append(i)
                
        if not tab_names:
            QMessageBox.warning(self, "Warning", "No editor tabs available for splitting.")
            return
            
        dialog = splitscreen.CustomSplitDialog(tab_names, theme=self.theme, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            selected_indices = dialog.get_selected_tabs()
            cols, rows = dialog.get_layout_config()
            
            # Map selected indices to actual tab indices
            actual_indices = [possible_indexes[i] for i in selected_indices if i < len(possible_indexes)]
            
            if actual_indices:
                splitscreen.create_custom_split(self.tabs, actual_indices, cols, rows)
            else:
                QMessageBox.warning(self, "Warning", "No tabs selected for custom split.")
