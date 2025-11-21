import os
from PyQt5.QtWidgets import (
    QTreeView, QFileSystemModel, QWidget, QVBoxLayout,
    QMenu, QAction, QInputDialog, QMessageBox, QLineEdit,
    QHBoxLayout, QPushButton, QToolButton, QFileDialog, QLabel, QStyle,
    QFrame
)
from PyQt5.QtCore import Qt, QDir, QModelIndex, pyqtSignal
from PyQt5.QtGui import QIcon
from .theme_manager import theme_manager_singleton, get_editor_styles

class FileTreeWidget(QWidget):
    # Signal to notify when a file should be opened
    file_opened = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FileTreeWidget")
        self.init_ui()
        self.setup_context_menu()
        theme_data = theme_manager_singleton.get_theme()
        self.set_theme(theme_data)
        theme_manager_singleton.themeChanged.connect(self.set_theme)
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.navigation_history = []
        self.history_index = -1
        
        # Create the file system model
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())

        # Navigation bar
        self.nav_widget = QFrame()
        self.nav_widget.setObjectName("FileTreeNav")
        nav_layout = QHBoxLayout(self.nav_widget)
        nav_layout.setContentsMargins(8, 6, 8, 6)
        nav_layout.setSpacing(6)

        self.back_button = QToolButton()
        self.back_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        self.back_button.setAutoRaise(True)
        self.back_button.setToolTip("Back")
        self.back_button.clicked.connect(self.go_back)

        self.forward_button = QToolButton()
        self.forward_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowForward))
        self.forward_button.setAutoRaise(True)
        self.forward_button.setToolTip("Forward")
        self.forward_button.clicked.connect(self.go_forward)

        self.up_button = QToolButton()
        self.up_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        self.up_button.setAutoRaise(True)
        self.up_button.setToolTip("Up one folder")
        self.up_button.clicked.connect(self.go_up)

        self.browse_button = QToolButton()
        self.browse_button.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.browse_button.setAutoRaise(True)
        self.browse_button.clicked.connect(self.browse_for_folder)
        self.browse_button.setToolTip("Browse for folder")

        self.location_label = QLabel("Current location:")
        self.location_label.setObjectName("LocationLabel")
        self.location_display = QLineEdit()
        self.location_display.setObjectName("LocationDisplay")
        self.location_display.setReadOnly(True)
        self.location_display.setFocusPolicy(Qt.ClickFocus)
        self.location_display.setClearButtonEnabled(True)

        nav_layout.addWidget(self.back_button)
        nav_layout.addWidget(self.forward_button)
        nav_layout.addWidget(self.up_button)
        nav_layout.addWidget(self.browse_button)
        nav_layout.addWidget(self.location_label)
        nav_layout.addWidget(self.location_display, 1)

        layout.addWidget(self.nav_widget)

        # Create the tree view
        self.tree = QTreeView()
        self.tree.setObjectName("FileTreeView")
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(QDir.rootPath()))
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(16)
        self.tree.setSortingEnabled(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        
        # Set up the tree view
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.doubleClicked.connect(self.handle_double_click)
        
        # Create path input widget
        self.path_widget = QFrame()
        self.path_widget.setObjectName("PathInputBar")
        path_layout = QHBoxLayout(self.path_widget)
        path_layout.setContentsMargins(8, 6, 8, 6)
        path_layout.setSpacing(6)
        
        self.path_input = QLineEdit()
        self.path_input.setObjectName("PathInput")
        self.path_input.setPlaceholderText("Enter path...")
        self.path_input.setClearButtonEnabled(True)
        self.path_input.returnPressed.connect(self.navigate_to_path)
        
        self.go_button = QPushButton("Go")
        self.go_button.setObjectName("PathGo")
        self.go_button.setCursor(Qt.PointingHandCursor)
        self.go_button.clicked.connect(self.navigate_to_path)
        
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.go_button)
        
        # Add widgets to main layout
        layout.addWidget(self.tree)
        layout.addWidget(self.path_widget)

        # Initialize navigation display
        initial_path = QDir.rootPath()
        self.record_history(initial_path)
        self.update_path_display(initial_path)
        self.update_navigation_buttons()
        
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
            current_path = self.get_root_path() or os.getcwd()
            path = os.path.abspath(os.path.join(current_path, path))
            
        if os.path.exists(path):
            if os.path.isdir(path):
                self.set_root_path(path)
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

        self.windows_dialog_action = QAction("Create via Windows dialog", self)
        self.windows_dialog_action.triggered.connect(self.open_windows_file_dialog)
        
        # Add actions to menu
        self.context_menu.addAction(self.open_action)
        self.context_menu.addSeparator()
        self.context_menu.addAction(self.windows_dialog_action)
        self.context_menu.addSeparator()
        self.context_menu.addAction(self.new_file_action)
        self.context_menu.addAction(self.new_folder_action)
        self.context_menu.addSeparator()
        self.context_menu.addAction(self.rename_action)
        self.context_menu.addAction(self.delete_action)
        
    def show_context_menu(self, position):
        index = self.tree.indexAt(position)
        if index.isValid():
            self.tree.setCurrentIndex(index)
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
                
    def set_root_path(self, path, add_history=True):
        """Set the root path of the file tree"""
        root_index = self.model.index(path)
        if not root_index.isValid():
            return
        self.tree.setRootIndex(root_index)
        if add_history:
            self.record_history(path)
        self.update_path_display(path)
        self.path_input.setText(path)

    def get_root_path(self):
        """Return current root path of the tree"""
        root_index = self.tree.rootIndex()
        if root_index.isValid():
            return self.model.filePath(root_index)
        return QDir.rootPath()

    def record_history(self, path):
        if self.navigation_history and self.navigation_history[self.history_index] == path:
            return
        # Trim forward history
        if self.history_index < len(self.navigation_history) - 1:
            self.navigation_history = self.navigation_history[:self.history_index + 1]
        self.navigation_history.append(path)
        self.history_index = len(self.navigation_history) - 1
        self.update_navigation_buttons()

    def go_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            path = self.navigation_history[self.history_index]
            self.set_root_path(path, add_history=False)
            self.update_navigation_buttons()

    def go_forward(self):
        if self.history_index < len(self.navigation_history) - 1:
            self.history_index += 1
            path = self.navigation_history[self.history_index]
            self.set_root_path(path, add_history=False)
            self.update_navigation_buttons()

    def go_up(self):
        current_path = self.get_root_path()
        parent_path = os.path.dirname(os.path.normpath(current_path))
        if parent_path and os.path.exists(parent_path) and parent_path != current_path:
            self.set_root_path(parent_path)

    def browse_for_folder(self):
        start_path = self.get_root_path()
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", start_path, QFileDialog.ShowDirsOnly)
        if folder:
            self.set_root_path(folder)

    def open_windows_file_dialog(self):
        current_path = self.get_root_path()
        file_path, _ = QFileDialog.getSaveFileName(self, "Create File", current_path)
        if file_path:
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "a", encoding="utf-8"):
                    pass
                self.model.setRootPath(self.model.rootPath())
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create file: {str(e)}")

    def update_navigation_buttons(self):
        self.back_button.setEnabled(self.history_index > 0)
        self.forward_button.setEnabled(self.history_index < len(self.navigation_history) - 1)
        self.up_button.setEnabled(self.get_root_path() not in ("", QDir.rootPath()))

    def update_path_display(self, path):
        self.location_display.setText(path)
        
    def get_current_path(self):
        """Get the path of the currently selected item"""
        index = self.tree.currentIndex()
        if index.isValid():
            return self.model.filePath(index)
        return None

    def set_theme(self, theme_data):
        palette = theme_data["palette"]
        editor = theme_data["editor"]
        border = palette.get("alternate_base", editor["background"])
        accent = palette.get("highlight", editor["selection_background"])
        accent_text = palette.get("highlight_text", editor["selection_foreground"])
        button_bg = palette.get("button", accent)
        button_text = palette.get("button_text", palette["window_text"])
        self.setStyleSheet(f"""
            QWidget#FileTreeWidget {{
                background: {palette['window']};
                color: {palette['window_text']};
            }}
            QWidget#FileTreeNav {{
                background: {palette['base']};
                border-bottom: 1px solid {border};
            }}
            QWidget#FileTreeNav QLabel {{
                color: {palette['window_text']};
                font-weight: 600;
            }}
            QWidget#PathInputBar {{
                background: {palette['base']};
                border-top: 1px solid {border};
            }}
            QLineEdit#PathInput, QLineEdit#LocationDisplay {{
                background: {editor['background']};
                color: {editor['foreground']};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 8px;
            }}
            QLineEdit#LocationDisplay {{
                font-weight: 500;
            }}
            QPushButton#PathGo {{
                background: {button_bg};
                color: {button_text};
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
            }}
            QPushButton#PathGo:hover {{
                background: {accent};
                color: {accent_text};
            }}
            QToolButton {{
                border: none;
                padding: 6px;
                border-radius: 4px;
            }}
            QToolButton:hover {{
                background: {border};
            }}
            QTreeView#FileTreeView {{
                background: {editor['background']};
                color: {editor['foreground']};
                border: none;
                alternate-background-color: {palette['alternate_base']};
                selection-background-color: {editor['selection_background']};
                selection-color: {editor['selection_foreground']};
            }}
            QTreeView#FileTreeView::item:selected {{
                border: none;
            }}
        """) 