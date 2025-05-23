import sys
import platform
import os
import tempfile
import subprocess
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTreeView, QFileSystemModel,
    QVBoxLayout, QWidget, QMessageBox, QPushButton, QLineEdit,
    QLabel, QHBoxLayout, QFileDialog, QStatusBar, QListWidget,
    QListWidgetItem, QSplitter, QMenu, QAction, QInputDialog, 
    QSizePolicy, QTabWidget, QDialog, QFormLayout, QComboBox,
    QCheckBox, QDialogButtonBox, QSpinBox, QShortcut, QKeySequenceEdit
)
from PyQt5.QtCore import QDir, Qt, QSortFilterProxyModel, QFileSystemWatcher, QSettings
from PyQt5.QtGui import QFont, QIcon, QKeySequence


class FilterProxyModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self._filter_text = ""
        self._sort_column = 0
        self._sort_order = Qt.AscendingOrder

    def setFilterText(self, text):
        self._filter_text = text.lower()
        self.invalidateFilter()

    def sort(self, column, order):
        self._sort_column = column
        self._sort_order = order
        super().sort(column, order)

    def filterAcceptsRow(self, source_row, source_parent):
        if not self._filter_text:
            return True

        index = self.sourceModel().index(source_row, 0, source_parent)
        data = self.sourceModel().fileName(index).lower()
        if self._filter_text in data:
            return True

        # Check children recursively for folders
        if self.sourceModel().isDir(index):
            for i in range(self.sourceModel().rowCount(index)):
                if self.filterAcceptsRow(i, index):
                    return True
        return False


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setWindowIcon(QIcon.fromTheme("preferences-system"))
        self.resize(500, 400)

        self.settings = QSettings("ModernFileExplorer", "Settings")
        self.shortcuts = {
            "New Tab": "Ctrl+T",
            "Close Tab": "Ctrl+W",
            "Next Tab": "Ctrl+Tab",
            "Previous Tab": "Ctrl+Shift+Tab",
            "Zoom In": "Ctrl+=",
            "Zoom Out": "Ctrl+-",
            "Toggle Hidden": "Ctrl+H",
            "Toggle Details": "Ctrl+D",
            "Refresh": "F5",
            "Go Home": "Ctrl+Home",
            "Go Up": "Alt+Up",
            "Rename": "F2",
            "Delete": "Del",
            "New Folder": "Ctrl+N",
        }

        self.tab_widget = QTabWidget()
        
        # Shortcuts Tab
        self.shortcuts_tab = QWidget()
        self.shortcuts_layout = QFormLayout()
        
        self.shortcut_widgets = {}
        for name, default in self.shortcuts.items():
            label = QLabel(name)
            edit = QKeySequenceEdit(QKeySequence(default))
            self.shortcuts_layout.addRow(label, edit)
            self.shortcut_widgets[name] = edit
        
        self.shortcuts_tab.setLayout(self.shortcuts_layout)
        self.tab_widget.addTab(self.shortcuts_tab, "Keyboard Shortcuts")

        # Appearance Tab
        self.appearance_tab = QWidget()
        appearance_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        appearance_layout.addRow(QLabel("Theme:"), self.theme_combo)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 20)
        appearance_layout.addRow(QLabel("Font Size:"), self.font_size_spin)
        
        self.show_hidden_check = QCheckBox()
        appearance_layout.addRow(QLabel("Show Hidden Files:"), self.show_hidden_check)
        
        self.show_details_check = QCheckBox()
        appearance_layout.addRow(QLabel("Show Details Columns:"), self.show_details_check)
        
        self.appearance_tab.setLayout(appearance_layout)
        self.tab_widget.addTab(self.appearance_tab, "Appearance")

        # Behavior Tab
        self.behavior_tab = QWidget()
        behavior_layout = QFormLayout()
        
        self.auto_refresh_check = QCheckBox()
        behavior_layout.addRow(QLabel("Auto Refresh on Changes:"), self.auto_refresh_check)
        
        self.single_click_check = QCheckBox()
        behavior_layout.addRow(QLabel("Single Click Navigation:"), self.single_click_check)
        
        self.confirm_delete_check = QCheckBox()
        behavior_layout.addRow(QLabel("Confirm File Deletion:"), self.confirm_delete_check)
        
        self.behavior_tab.setLayout(behavior_layout)
        self.tab_widget.addTab(self.behavior_tab, "Behavior")

        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply | QDialogButtonBox.RestoreDefaults)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply_settings)
        self.button_box.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.restore_defaults)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tab_widget)
        main_layout.addWidget(self.button_box)
        self.setLayout(main_layout)

        self.load_settings()

    def load_settings(self):
        # Load shortcuts
        for name, edit in self.shortcut_widgets.items():
            shortcut = self.settings.value(f"shortcuts/{name}", self.shortcuts[name])
            edit.setKeySequence(QKeySequence(shortcut))
        
        # Load appearance
        theme = self.settings.value("appearance/theme", "Dark")
        self.theme_combo.setCurrentText(theme)
        
        font_size = int(self.settings.value("appearance/font_size", 10))
        self.font_size_spin.setValue(font_size)
        
        show_hidden = self.settings.value("appearance/show_hidden", "false") == "true"
        self.show_hidden_check.setChecked(show_hidden)
        
        show_details = self.settings.value("appearance/show_details", "true") == "true"
        self.show_details_check.setChecked(show_details)
        
        # Load behavior
        auto_refresh = self.settings.value("behavior/auto_refresh", "true") == "true"
        self.auto_refresh_check.setChecked(auto_refresh)
        
        single_click = self.settings.value("behavior/single_click", "false") == "true"
        self.single_click_check.setChecked(single_click)
        
        confirm_delete = self.settings.value("behavior/confirm_delete", "true") == "true"
        self.confirm_delete_check.setChecked(confirm_delete)

    def save_settings(self):
        # Save shortcuts
        for name, edit in self.shortcut_widgets.items():
            self.settings.setValue(f"shortcuts/{name}", edit.keySequence().toString())
        
        # Save appearance
        self.settings.setValue("appearance/theme", self.theme_combo.currentText())
        self.settings.setValue("appearance/font_size", self.font_size_spin.value())
        self.settings.setValue("appearance/show_hidden", self.show_hidden_check.isChecked())
        self.settings.setValue("appearance/show_details", self.show_details_check.isChecked())
        
        # Save behavior
        self.settings.setValue("behavior/auto_refresh", self.auto_refresh_check.isChecked())
        self.settings.setValue("behavior/single_click", self.single_click_check.isChecked())
        self.settings.setValue("behavior/confirm_delete", self.confirm_delete_check.isChecked())

    def apply_settings(self):
        self.save_settings()
        self.parent().apply_settings()

    def restore_defaults(self):
        # Restore default shortcuts
        for name, default in self.shortcuts.items():
            self.shortcut_widgets[name].setKeySequence(QKeySequence(default))
        
        # Restore default appearance
        self.theme_combo.setCurrentText("Dark")
        self.font_size_spin.setValue(10)
        self.show_hidden_check.setChecked(False)
        self.show_details_check.setChecked(True)
        
        # Restore default behavior
        self.auto_refresh_check.setChecked(True)
        self.single_click_check.setChecked(False)
        self.confirm_delete_check.setChecked(True)


class FileTreeTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setAcceptDrops(True)
        
        # File system model
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.update_hidden_filter()
        
        self.proxy_model = FilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        
        # Tree view setup
        self.tree = QTreeView()
        self.tree.setModel(self.proxy_model)
        self.tree.setAlternatingRowColors(True)
        self.tree.setIndentation(20)
        self.tree.setFont(QFont("Fira Code", self.parent_window.font_size))
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, Qt.AscendingOrder)
        self.tree.selectionModel().selectionChanged.connect(self.parent_window.update_status)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        self.tree.doubleClicked.connect(self.on_double_click)
        
        # Enable drag and drop
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDragDropMode(QTreeView.DragDrop)
        
        self.update_columns_visibility()
        
        # File system watcher
        self.watcher = QFileSystemWatcher()
        self.watcher.directoryChanged.connect(self.handle_directory_changed)
        
        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.tree)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        # Set initial path
        self.set_root_path(QDir.rootPath())

    def update_columns_visibility(self):
        if self.parent_window.show_details:
            for i in range(3):
                self.tree.showColumn(i)
        else:
            for i in range(1, 3):
                self.tree.hideColumn(i)

    def update_hidden_filter(self):
        filters = QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot
        if not self.parent_window.show_hidden:
            filters &= ~QDir.Hidden
        else:
            filters |= QDir.Hidden
        self.model.setFilter(filters)

    def set_root_path(self, path):
        idx = self.model.index(path)
        if idx.isValid():
            proxy_idx = self.proxy_model.mapFromSource(idx)
            self.tree.setRootIndex(proxy_idx)
            self.parent_window.update_status()
            
            # Update watcher
            if self.watcher.directories():
                self.watcher.removePaths(self.watcher.directories())
            self.watcher.addPath(path)
            
            # Watch all subdirectories recursively
            for root, dirs, _ in os.walk(path):
                for dir in dirs:
                    dir_path = os.path.join(root, dir)
                    try:
                        self.watcher.addPath(dir_path)
                    except:
                        continue

    def handle_directory_changed(self, path):
        if self.parent_window.auto_refresh:
            self.model.refresh()

    def open_context_menu(self, pos):
        index = self.tree.indexAt(pos)
        if not index.isValid():
            return
            
        source_idx = self.proxy_model.mapToSource(index)
        path = self.model.filePath(source_idx)
        
        menu = QMenu()
        
        # Standard actions
        open_action = QAction("Open")
        rename_action = QAction("Rename")
        delete_action = QAction("Delete")
        new_folder_action = QAction("New Folder")
        refresh_action = QAction("Refresh")
        
        # Add shortcuts
        rename_action.setShortcut(QKeySequence("F2"))
        delete_action.setShortcut(QKeySequence("Del"))
        
        open_action.triggered.connect(lambda: self.on_double_click(index))
        rename_action.triggered.connect(lambda: self.parent_window.rename_item(path))
        delete_action.triggered.connect(lambda: self.parent_window.delete_item(path))
        new_folder_action.triggered.connect(lambda: self.create_new_folder(path if os.path.isdir(path) else os.path.dirname(path)))
        refresh_action.triggered.connect(lambda: self.model.refresh(source_idx))
        
        menu.addAction(open_action)
        menu.addAction(rename_action)
        menu.addAction(delete_action)
        menu.addSeparator()
        menu.addAction(new_folder_action)
        menu.addSeparator()
        menu.addAction(refresh_action)
        
        menu.exec_(self.tree.viewport().mapToGlobal(pos))

    def on_double_click(self, index):
        source_idx = self.proxy_model.mapToSource(index)
        path = self.model.filePath(source_idx)
        
        if os.path.isdir(path):
            self.set_root_path(path)
            self.parent_window.browse_input.setText(path)
        else:
            self.parent_window.open_file(path)

    def create_new_folder(self, parent_path):
        new_name, ok = QInputDialog.getText(self, "New Folder", "Enter folder name:")
        if ok and new_name:
            new_path = os.path.join(parent_path, new_name)
            try:
                os.mkdir(new_path)
                self.model.refresh()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create folder:\n{e}")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                print(f"File dropped: {file_path}")
            event.acceptProposedAction()


class FileTreeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modern File Explorer")
        self.setGeometry(100, 100, 1200, 700)
        self.setWindowIcon(QIcon.fromTheme("folder"))
        
        # Settings
        self.settings = QSettings("ModernFileExplorer", "Settings")
        self.load_settings()
        
        # Initialize state
        self.bookmarks = []
        self.auto_refresh = True
        
        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        
        # Create initial tab
        self.add_new_tab(QDir.rootPath())
        
        # Controls widgets
        browse_label = QLabel("Path:")
        browse_label.setStyleSheet("font-weight: bold;")
        
        self.browse_input = QLineEdit(QDir.rootPath())
        self.browse_input.setPlaceholderText("Enter path or click Browse")
        self.browse_input.returnPressed.connect(self.change_root_path)
        
        browse_button = QPushButton("Browse")
        browse_button.setIcon(QIcon.fromTheme("folder-open"))
        browse_button.clicked.connect(self.open_folder_dialog)
        browse_button.setCursor(Qt.PointingHandCursor)
        browse_button.setToolTip("Browse filesystem")
        
        search_label = QLabel("Search:")
        search_label.setStyleSheet("font-weight: bold;")
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter files/folders...")
        self.search_input.textChanged.connect(self.filter_changed)
        
        # Navigation buttons
        home_btn = QPushButton("Home")
        home_btn.setIcon(QIcon.fromTheme("go-home"))
        home_btn.clicked.connect(self.go_home)
        home_btn.setToolTip("Go to home directory")
        
        up_btn = QPushButton("Up")
        up_btn.setIcon(QIcon.fromTheme("go-up"))
        up_btn.clicked.connect(self.go_up)
        up_btn.setToolTip("Go up one directory")
        
        # Action buttons
        new_tab_btn = QPushButton("New Tab")
        new_tab_btn.setIcon(QIcon.fromTheme("tab-new"))
        new_tab_btn.clicked.connect(lambda: self.add_new_tab(QDir.rootPath()))
        new_tab_btn.setToolTip("Open new tab")
        
        zoom_in_btn = QPushButton("A+")
        zoom_in_btn.setToolTip("Zoom In")
        zoom_in_btn.clicked.connect(self.zoom_in)
        zoom_in_btn.setFixedWidth(30)
        
        zoom_out_btn = QPushButton("A-")
        zoom_out_btn.setToolTip("Zoom Out")
        zoom_out_btn.clicked.connect(self.zoom_out)
        zoom_out_btn.setFixedWidth(30)
        
        close_btn = QPushButton("X")
        close_btn.setToolTip("Close")
        close_btn.clicked.connect(self.close)
        close_btn.setFixedWidth(30)
        close_btn.setStyleSheet("color: red; font-weight: bold;")
        
        # Toggle buttons
        self.toggle_hidden_btn = QPushButton(f"Show Hidden: {'ON' if self.show_hidden else 'OFF'}")
        self.toggle_hidden_btn.setCheckable(True)
        self.toggle_hidden_btn.setChecked(self.show_hidden)
        self.toggle_hidden_btn.clicked.connect(self.toggle_hidden_files)
        
        self.toggle_details_btn = QPushButton(f"Details: {'ON' if self.show_details else 'OFF'}")
        self.toggle_details_btn.setCheckable(True)
        self.toggle_details_btn.setChecked(self.show_details)
        self.toggle_details_btn.clicked.connect(self.toggle_details_columns)
        
        # Bookmark buttons
        self.add_bookmark_btn = QPushButton("+ Bookmark")
        self.add_bookmark_btn.setToolTip("Add current path to bookmarks")
        self.add_bookmark_btn.clicked.connect(self.add_bookmark)
        
        # GitHub repo clone widgets
        github_label = QLabel("GitHub Repo URL:")
        github_label.setStyleSheet("font-weight: bold;")
        
        self.github_input = QLineEdit()
        self.github_input.setPlaceholderText("https://github.com/user/repo.git")
        self.github_input.returnPressed.connect(self.clone_github_repo)
        
        github_clone_btn = QPushButton("Clone Repo")
        github_clone_btn.setIcon(QIcon.fromTheme("git"))
        github_clone_btn.setToolTip("Clone GitHub repository and open")
        github_clone_btn.clicked.connect(self.clone_github_repo)
        
        # Settings button
        settings_btn = QPushButton("Settings")
        settings_btn.setIcon(QIcon.fromTheme("preferences-system"))
        settings_btn.clicked.connect(self.open_settings)
        
        # Controls layout
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(browse_label)
        controls_layout.addWidget(self.browse_input)
        controls_layout.addWidget(browse_button)
        controls_layout.addWidget(home_btn)
        controls_layout.addWidget(up_btn)
        controls_layout.addSpacing(10)
        controls_layout.addWidget(search_label)
        controls_layout.addWidget(self.search_input)
        controls_layout.addSpacing(10)
        controls_layout.addWidget(new_tab_btn)
        controls_layout.addWidget(zoom_in_btn)
        controls_layout.addWidget(zoom_out_btn)
        controls_layout.addWidget(self.toggle_hidden_btn)
        controls_layout.addWidget(self.toggle_details_btn)
        controls_layout.addWidget(self.add_bookmark_btn)
        controls_layout.addSpacing(10)
        controls_layout.addWidget(github_label)
        controls_layout.addWidget(self.github_input)
        controls_layout.addWidget(github_clone_btn)
        controls_layout.addSpacing(10)
        controls_layout.addWidget(settings_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(close_btn)
        
        controls_container = QWidget()
        controls_container.setLayout(controls_layout)
        controls_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Bookmarks list widget
        self.bookmark_list = QListWidget()
        self.bookmark_list.setMaximumWidth(200)
        self.bookmark_list.itemClicked.connect(self.on_bookmark_clicked)
        
        # Main splitter
        main_splitter = QSplitter()
        main_splitter.addWidget(self.bookmark_list)
        main_splitter.addWidget(self.tab_widget)
        main_splitter.setStretchFactor(1, 4)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(controls_container)
        main_layout.addWidget(main_splitter)
        
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        
        # Apply initial settings
        self.apply_settings()
        
        # Setup shortcuts
        self.setup_shortcuts()

    def load_settings(self):
        self.is_dark = self.settings.value("appearance/theme", "Dark") == "Dark"
        self.font_size = int(self.settings.value("appearance/font_size", 10))
        self.min_font_size = 7
        self.max_font_size = 20
        self.show_hidden = self.settings.value("appearance/show_hidden", "false") == "true"
        self.show_details = self.settings.value("appearance/show_details", "true") == "true"
        self.auto_refresh = self.settings.value("behavior/auto_refresh", "true") == "true"
        self.confirm_delete = self.settings.value("behavior/confirm_delete", "true") == "true"

    def setup_shortcuts(self):
        # Navigation shortcuts
        QShortcut(QKeySequence("Ctrl+T"), self, lambda: self.add_new_tab(QDir.rootPath()))
        QShortcut(QKeySequence("Ctrl+W"), self, self.close_current_tab)
        QShortcut(QKeySequence("Ctrl+Tab"), self, self.next_tab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self, self.previous_tab)
        QShortcut(QKeySequence("Ctrl+="), self, self.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self.zoom_out)
        QShortcut(QKeySequence("Ctrl+H"), self, self.toggle_hidden_files)
        QShortcut(QKeySequence("Ctrl+D"), self, self.toggle_details_columns)
        QShortcut(QKeySequence("F5"), self, self.refresh_current_tab)
        QShortcut(QKeySequence("Ctrl+Home"), self, self.go_home)
        QShortcut(QKeySequence("Alt+Up"), self, self.go_up)
        QShortcut(QKeySequence("F2"), self, self.rename_selected)
        QShortcut(QKeySequence("Del"), self, self.delete_selected)
        QShortcut(QKeySequence("Ctrl+N"), self, self.create_new_folder)

    def add_new_tab(self, path):
        tab = FileTreeTab(self)
        tab.set_root_path(path)
        tab_name = os.path.basename(path) if path != QDir.rootPath() else "Home"
        self.tab_widget.addTab(tab, tab_name)
        self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)
        self.browse_input.setText(path)

    def close_current_tab(self):
        if self.tab_widget.count() > 1:
            self.tab_widget.removeTab(self.tab_widget.currentIndex())
        else:
            QMessageBox.information(self, "Cannot Close", "You cannot close the last tab.")

    def close_tab(self, index):
        if self.tab_widget.count() > 1:
            self.tab_widget.removeTab(index)
        else:
            QMessageBox.information(self, "Cannot Close", "You cannot close the last tab.")

    def next_tab(self):
        current = self.tab_widget.currentIndex()
        if current < self.tab_widget.count() - 1:
            self.tab_widget.setCurrentIndex(current + 1)
        else:
            self.tab_widget.setCurrentIndex(0)

    def previous_tab(self):
        current = self.tab_widget.currentIndex()
        if current > 0:
            self.tab_widget.setCurrentIndex(current - 1)
        else:
            self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)

    def refresh_current_tab(self):
        current_tab = self.tab_widget.currentWidget()
        if current_tab:
            current_tab.model.refresh()

    def get_current_tab(self):
        return self.tab_widget.currentWidget()

    def update_hidden_filter(self):
        current_tab = self.get_current_tab()
        if current_tab:
            current_tab.update_hidden_filter()

    def toggle_hidden_files(self):
        self.show_hidden = not self.show_hidden
        self.toggle_hidden_btn.setText(f"Show Hidden: {'ON' if self.show_hidden else 'OFF'}")
        self.toggle_hidden_btn.setChecked(self.show_hidden)
        self.update_hidden_filter()

    def toggle_details_columns(self):
        self.show_details = not self.show_details
        self.toggle_details_btn.setText(f"Details: {'ON' if self.show_details else 'OFF'}")
        self.toggle_details_btn.setChecked(self.show_details)
        current_tab = self.get_current_tab()
        if current_tab:
            current_tab.update_columns_visibility()

    def add_bookmark(self):
        path = self.browse_input.text().strip()
        if not os.path.exists(path):
            QMessageBox.warning(self, "Invalid Path", "Cannot bookmark invalid path.")
            return
        if path not in self.bookmarks:
            self.bookmarks.append(path)
            self.bookmark_list.addItem(path)

    def on_bookmark_clicked(self, item: QListWidgetItem):
        path = item.text()
        self.browse_input.setText(path)
        self.change_root_path()

    def change_root_path(self):
        path = self.browse_input.text().strip()
        if not os.path.exists(path):
            QMessageBox.warning(self, "Invalid Path", "The specified path does not exist.")
            return
        
        current_tab = self.get_current_tab()
        if current_tab:
            current_tab.set_root_path(path)
            tab_name = os.path.basename(path) if path != QDir.rootPath() else "Home"
            self.tab_widget.setTabText(self.tab_widget.currentIndex(), tab_name)

    def open_folder_dialog(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder", QDir.rootPath())
        if path:
            self.browse_input.setText(path)
            self.change_root_path()

    def filter_changed(self, text):
        current_tab = self.get_current_tab()
        if current_tab:
            current_tab.proxy_model.setFilterText(text)

    def zoom_in(self):
        if self.font_size < self.max_font_size:
            self.font_size += 1
            self.update_font_size()

    def zoom_out(self):
        if self.font_size > self.min_font_size:
            self.font_size -= 1
            self.update_font_size()

    def update_font_size(self):
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            tab.tree.setFont(QFont("Fira Code", self.font_size))

    def update_status(self):
        current_tab = self.get_current_tab()
        if not current_tab:
            self.status.showMessage("No active tab")
            return
            
        idx = current_tab.tree.rootIndex()
        if not idx.isValid():
            self.status.showMessage("No valid root selected")
            return
            
        source_idx = current_tab.proxy_model.mapToSource(idx)
        path = current_tab.model.filePath(source_idx)
        count = current_tab.model.rowCount(source_idx)
        self.status.showMessage(f"Root: {path} | Items: {count}")

    def rename_item(self, old_path):
        base_path = os.path.dirname(old_path)
        old_name = os.path.basename(old_path)
        new_name, ok = QInputDialog.getText(self, "Rename", "Enter new name:", text=old_name)
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(base_path, new_name)
            try:
                os.rename(old_path, new_path)
                self.refresh_current_tab()
                self.update_status()
            except Exception as e:
                QMessageBox.warning(self, "Rename Failed", f"Could not rename:\n{e}")

    def delete_item(self, path):
        if self.confirm_delete:
            confirm = QMessageBox.question(
                self,
                "Delete Confirmation",
                f"Are you sure you want to delete:\n{path}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if confirm != QMessageBox.Yes:
                return

        try:
            if os.path.isdir(path):
                import shutil
                shutil.rmtree(path)
            else:
                os.remove(path)
            self.refresh_current_tab()
            self.update_status()
        except Exception as e:
            QMessageBox.warning(self, "Delete Failed", f"Failed to delete:\n{e}")

    def clone_github_repo(self):
        url = self.github_input.text().strip()
        if not url.startswith("https://github.com/") and not url.startswith("git@github.com:"):
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid GitHub repository URL.")
            return

        temp_dir = tempfile.mkdtemp(prefix="gh_repo_")
        self.status.showMessage("Cloning repository, please wait...")
        QApplication.processEvents()

        try:
            subprocess.check_call(["git", "clone", url, temp_dir])
            self.add_new_tab(temp_dir)
            self.status.showMessage(f"Cloned {url} into {temp_dir}")
        except Exception as e:
            QMessageBox.warning(self, "Clone Failed", f"Failed to clone repository:\n{e}")
            self.status.showMessage("Clone failed.")

    def go_home(self):
        home_path = os.path.expanduser("~")
        self.browse_input.setText(home_path)
        self.change_root_path()

    def go_up(self):
        current_tab = self.get_current_tab()
        if current_tab:
            current_path = current_tab.model.filePath(current_tab.proxy_model.mapToSource(current_tab.tree.rootIndex()))
            parent_path = os.path.dirname(current_path)
            if os.path.exists(parent_path):
                self.browse_input.setText(parent_path)
                self.change_root_path()

    def rename_selected(self):
        current_tab = self.get_current_tab()
        if current_tab:
            index = current_tab.tree.currentIndex()
            if index.isValid():
                source_idx = current_tab.proxy_model.mapToSource(index)
                path = current_tab.model.filePath(source_idx)
                self.rename_item(path)

    def delete_selected(self):
        current_tab = self.get_current_tab()
        if current_tab:
            index = current_tab.tree.currentIndex()
            if index.isValid():
                source_idx = current_tab.proxy_model.mapToSource(index)
                path = current_tab.model.filePath(source_idx)
                self.delete_item(path)

    def create_new_folder(self):
        current_tab = self.get_current_tab()
        if current_tab:
            index = current_tab.tree.currentIndex()
            if index.isValid():
                source_idx = current_tab.proxy_model.mapToSource(index)
                path = current_tab.model.filePath(source_idx)
                if os.path.isdir(path):
                    parent_path = path
                else:
                    parent_path = os.path.dirname(path)
                current_tab.create_new_folder(parent_path)

    def open_file(self, path):
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", path])
            else:  # Linux
                subprocess.run(["xdg-open", path])
        except Exception as e:
            QMessageBox.warning(self, "Open Failed", f"Could not open file:\n{e}")

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec_()

    def apply_settings(self):
        self.load_settings()
        self.apply_theme()
        
        # Update all tabs
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            tab.tree.setFont(QFont("Fira Code", self.font_size))
            tab.update_hidden_filter()
            tab.update_columns_visibility()

    def apply_theme(self):
        if self.is_dark:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #1e1e1e;
                    color: #cccccc;
                }
                QTreeView {
                    background-color: #252526;
                    alternate-background-color: #2a2d2e;
                    color: #cccccc;
                    selection-background-color: #094771;
                    selection-color: white;
                }
                QLineEdit, QPushButton, QListWidget {
                    background-color: #3c3c3c;
                    color: #cccccc;
                    border: 1px solid #555;
                    border-radius: 4px;
                    padding: 3px;
                }
                QPushButton:hover {
                    background-color: #444;
                }
                QPushButton:checked {
                    background-color: #007acc;
                    color: white;
                }
                QStatusBar {
                    background-color: #1e1e1e;
                    color: #888;
                    border-top: 1px solid #333;
                }
                QLabel {
                    color: #cccccc;
                }
                QMenu {
                    background-color: #252526;
                    color: #ccc;
                }
                QMenu::item:selected {
                    background-color: #094771;
                    color: white;
                }
                QTabWidget::pane {
                    border: 1px solid #444;
                }
                QTabBar::tab {
                    background: #333;
                    color: #ccc;
                    padding: 5px;
                    border: 1px solid #444;
                    border-bottom: none;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QTabBar::tab:selected {
                    background: #1e1e1e;
                    color: white;
                }
                QTabBar::tab:hover {
                    background: #444;
                }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #fff;
                    color: #000;
                }
                QTreeView {
                    background-color: #fff;
                    alternate-background-color: #f5f5f5;
                    color: #000;
                    selection-background-color: #3399ff;
                    selection-color: white;
                }
                QLineEdit, QPushButton, QListWidget {
                    background-color: #fff;
                    color: #000;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    padding: 3px;
                }
                QPushButton:hover {
                    background-color: #ddd;
                }
                QPushButton:checked {
                    background-color: #3399ff;
                    color: white;
                }
                QStatusBar {
                    background-color: #eee;
                    color: #333;
                    border-top: 1px solid #ccc;
                }
                QLabel {
                    color: #000;
                }
                QMenu {
                    background-color: #fff;
                    color: #000;
                }
                QMenu::item:selected {
                    background-color: #3399ff;
                    color: white;
                }
                QTabWidget::pane {
                    border: 1px solid #ccc;
                }
                QTabBar::tab {
                    background: #eee;
                    color: #333;
                    padding: 5px;
                    border: 1px solid #ccc;
                      border-bottom: none;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QTabBar::tab:selected {
                    background: #fff;
                    color: #000;
                }
                QTabBar::tab:hover {
                    background: #ddd;
                }
            """)


def check_os():
    os_name = platform.system()
    if os_name not in ("Windows", "Linux", "Darwin"):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Unsupported OS")
        msg.setText(f"Your OS ({os_name}) is not supported.")
        msg.exec_()
        sys.exit(1)


def main():
    check_os()
    app = QApplication(sys.argv)
    window = FileTreeWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
