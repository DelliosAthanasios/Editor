import os
from PyQt5.QtWidgets import (
    QTreeView, QFileSystemModel, QWidget, QVBoxLayout,
    QMenu, QAction, QInputDialog, QMessageBox, QLineEdit,
    QHBoxLayout, QPushButton
)
from PyQt5.QtCore import Qt, QDir, QModelIndex, pyqtSignal
from PyQt5.QtGui import QIcon
from .theme_manager import theme_manager_singleton, get_editor_styles

class FileTreeWidget(QWidget):
    # Signal to notify when a file should be opened
    file_opened = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.setup_context_menu()
        theme_data = theme_manager_singleton.get_theme()
        self.set_theme(theme_data)
        theme_manager_singleton.themeChanged.connect(self.set_theme)
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the file system model
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        
        # Create the tree view
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(QDir.rootPath()))
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(16)
        self.tree.setSortingEnabled(True)
        
        # Set up the tree view
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.doubleClicked.connect(self.handle_double_click)
        
        # Create path input widget
        path_widget = QWidget()
        path_layout = QHBoxLayout(path_widget)
        path_layout.setContentsMargins(2, 2, 2, 2)
        
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Enter path...")
        self.path_input.returnPressed.connect(self.navigate_to_path)
        
        self.go_button = QPushButton("Go")
        self.go_button.clicked.connect(self.navigate_to_path)
        
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.go_button)
        
        # Add widgets to main layout
        layout.addWidget(self.tree)
        layout.addWidget(path_widget)
        
    def navigate_to_path(self):
        path = self.path_input.text().strip()
        if not path:
            return
            
        # Handle special paths
        if path == "~":
            path = os.path.expanduser("~")
        elif path == ".":
            path = os.getcwd()
            
        # Convert to absolute path if relative
        if not os.path.isabs(path):
            current_path = self.get_current_path() or os.getcwd()
            path = os.path.abspath(os.path.join(current_path, path))
            
        if os.path.exists(path):
            if os.path.isdir(path):
                self.set_root_path(path)
                self.path_input.setText(path)
            else:
                # If it's a file, open it
                self.open_file(path)
        else:
            QMessageBox.warning(self, "Path Error", f"Path does not exist: {path}")
            
    def open_file(self, file_path):
        """Open a file in the editor"""
        if os.path.isfile(file_path):
            # Check if the file is supported
            if self.is_supported_file(file_path):
                # Emit signal to open the file
                self.file_opened.emit(file_path)
            else:
                QMessageBox.warning(self, "Unsupported File", 
                                  f"File type not supported: {os.path.splitext(file_path)[1]}")
                
    def is_supported_file(self, file_path):
        """Check if the file type is supported"""
        supported_extensions = (
            ".txt", ".py", ".md", ".json", ".ini", ".csv", ".log",
            ".html", ".css", ".js", ".xml", ".yaml", ".yml", ".toml",
            ".c", ".cpp", ".h", ".hpp", ".java", ".php", ".rb", ".sh",
            ".bat", ".cmd", ".ps1", ".sql", ".ts", ".tsx", ".jsx"
        )
        return file_path.lower().endswith(supported_extensions)
        
    def setup_context_menu(self):
        self.context_menu = QMenu(self)
        
        # Create actions
        self.new_file_action = QAction("New File", self)
        self.new_file_action.triggered.connect(self.create_new_file)
        
        self.new_folder_action = QAction("New Folder", self)
        self.new_folder_action.triggered.connect(self.create_new_folder)
        
        self.rename_action = QAction("Rename", self)
        self.rename_action.triggered.connect(self.rename_item)
        
        self.delete_action = QAction("Delete", self)
        self.delete_action.triggered.connect(self.delete_item)
        
        self.open_action = QAction("Open", self)
        self.open_action.triggered.connect(self.open_selected)
        
        # Add actions to menu
        self.context_menu.addAction(self.open_action)
        self.context_menu.addSeparator()
        self.context_menu.addAction(self.new_file_action)
        self.context_menu.addAction(self.new_folder_action)
        self.context_menu.addSeparator()
        self.context_menu.addAction(self.rename_action)
        self.context_menu.addAction(self.delete_action)
        
    def show_context_menu(self, position):
        index = self.tree.indexAt(position)
        if index.isValid():
            self.context_menu.exec_(self.tree.viewport().mapToGlobal(position))
            
    def handle_double_click(self, index):
        if not index.isValid():
            return
            
        file_path = self.model.filePath(index)
        if os.path.isfile(file_path):
            self.open_file(file_path)
        elif os.path.isdir(file_path):
            self.set_root_path(file_path)
            self.path_input.setText(file_path)
            
    def open_selected(self):
        """Open the currently selected item"""
        index = self.tree.currentIndex()
        if index.isValid():
            file_path = self.model.filePath(index)
            if os.path.isfile(file_path):
                self.open_file(file_path)
            elif os.path.isdir(file_path):
                self.set_root_path(file_path)
                self.path_input.setText(file_path)
                
    def create_new_file(self):
        index = self.tree.currentIndex()
        if not index.isValid():
            return
            
        parent_path = self.model.filePath(index)
        if not os.path.isdir(parent_path):
            parent_path = os.path.dirname(parent_path)
            
        name, ok = QInputDialog.getText(self, "New File", "Enter file name:")
        if ok and name:
            file_path = os.path.join(parent_path, name)
            try:
                with open(file_path, 'w') as f:
                    pass
                # Refresh the view
                self.model.setRootPath(self.model.rootPath())
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create file: {str(e)}")
                
    def create_new_folder(self):
        index = self.tree.currentIndex()
        if not index.isValid():
            return
            
        parent_path = self.model.filePath(index)
        if not os.path.isdir(parent_path):
            parent_path = os.path.dirname(parent_path)
            
        name, ok = QInputDialog.getText(self, "New Folder", "Enter folder name:")
        if ok and name:
            folder_path = os.path.join(parent_path, name)
            try:
                os.makedirs(folder_path, exist_ok=True)
                # Refresh the view
                self.model.setRootPath(self.model.rootPath())
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create folder: {str(e)}")
                
    def rename_item(self):
        index = self.tree.currentIndex()
        if not index.isValid():
            return
            
        old_path = self.model.filePath(index)
        old_name = os.path.basename(old_path)
        parent_path = os.path.dirname(old_path)
        
        name, ok = QInputDialog.getText(self, "Rename", "Enter new name:", text=old_name)
        if ok and name and name != old_name:
            new_path = os.path.join(parent_path, name)
            try:
                os.rename(old_path, new_path)
                # Refresh the view
                self.model.setRootPath(self.model.rootPath())
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to rename: {str(e)}")
                
    def delete_item(self):
        index = self.tree.currentIndex()
        if not index.isValid():
            return
            
        path = self.model.filePath(index)
        name = os.path.basename(path)
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    import shutil
                    shutil.rmtree(path)
                # Refresh the view
                self.model.setRootPath(self.model.rootPath())
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {str(e)}")
                
    def set_root_path(self, path):
        """Set the root path of the file tree"""
        self.tree.setRootIndex(self.model.index(path))
        
    def get_current_path(self):
        """Get the path of the currently selected item"""
        index = self.tree.currentIndex()
        if index.isValid():
            return self.model.filePath(index)
        return None

    def set_theme(self, theme_data):
        palette = theme_data["palette"]
        editor = theme_data["editor"]
        self.setStyleSheet(f"""
            QWidget {{ background: {palette['window']}; color: {palette['window_text']}; }}
            QTreeView {{ background: {editor['background']}; color: {editor['foreground']}; alternate-background-color: {palette['alternate_base']}; selection-background-color: {editor['selection_background']}; selection-color: {editor['selection_foreground']}; }}
            QLineEdit {{ background: {palette['base']}; color: {palette['text']}; border-radius: 4px; }}
            QPushButton {{ background: {palette['button']}; color: {palette['button_text']}; border-radius: 4px; }}
            QPushButton:hover {{ background: {palette['highlight']}; color: {palette['highlight_text']}; }}
        """) 