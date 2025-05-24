import sys
import os
import platform
import tempfile
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTreeView, QFileSystemModel, QVBoxLayout, QWidget,
    QStatusBar, QPushButton, QLineEdit, QLabel, QHBoxLayout, QFileDialog,
    QTabWidget, QListWidget, QListWidgetItem, QSplitter, QMessageBox, QMenu, QAction,
    QInputDialog, QDialog, QFormLayout, QComboBox, QCheckBox, QDialogButtonBox, QSpinBox,
    QKeySequenceEdit, QShortcut, QAbstractItemView, QStyleFactory
)
from PyQt5.QtCore import QDir, Qt, QSettings, QSortFilterProxyModel, QFileSystemWatcher, QModelIndex, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QKeySequence, QColor, QPalette

# -------- Helper Models --------

class FilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filter_text = ""
        self.sort_column = 0
        self.sort_order = Qt.AscendingOrder

    def setFilterText(self, text):
        self.filter_text = text.lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if not self.filter_text:
            return True
        index = self.sourceModel().index(source_row, 0, source_parent)
        filename = self.sourceModel().fileName(index).lower()
        if self.filter_text in filename:
            return True
        if self.sourceModel().isDir(index):
            for i in range(self.sourceModel().rowCount(index)):
                if self.filterAcceptsRow(i, index):
                    return True
        return False

    def lessThan(self, left, right):
        ldata = self.sourceModel().fileName(left)
        rdata = self.sourceModel().fileName(right)
        return ldata.lower() < rdata.lower()

# -------- Settings Dialog --------

class SettingsDialog(QDialog):
    settings_changed = pyqtSignal()

    def __init__(self, parent=None, shortcuts=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setWindowIcon(QIcon.fromTheme("preferences-system"))
        self.settings = QSettings("ModernFileExplorer", "Settings")
        self.resize(500, 400)
        layout = QVBoxLayout(self)

        # Theme & Font
        form = QFormLayout()

        self.theme = QComboBox()
        self.theme.addItems(["Dark", "Light"])
        self.theme.setCurrentText(self.settings.value("theme", "Dark"))
        form.addRow("Theme", self.theme)

        self.fontsize = QSpinBox()
        self.fontsize.setRange(8, 32)
        self.fontsize.setValue(int(self.settings.value("fontsize", 12)))
        form.addRow("Font Size", self.fontsize)

        self.show_hidden = QCheckBox("Show Hidden Files")
        self.show_hidden.setChecked(self.settings.value("show_hidden", "false") == "true")
        form.addRow(self.show_hidden)

        self.show_details = QCheckBox("Show Details Columns")
        self.show_details.setChecked(self.settings.value("show_details", "true") == "true")
        form.addRow(self.show_details)

        self.auto_refresh = QCheckBox("Auto Refresh (File Watching)")
        self.auto_refresh.setChecked(self.settings.value("auto_refresh", "true") == "true")
        form.addRow(self.auto_refresh)

        # Shortcuts Tab
        shortcuts_group = QWidget()
        shortcuts_layout = QFormLayout()
        self.shortcuts_edits = {}
        self.default_shortcuts = {
            "New Tab": "Ctrl+T",
            "Close Tab": "Ctrl+W",
            "Next Tab": "Ctrl+Tab",
            "Previous Tab": "Ctrl+Shift+Tab",
            "Refresh": "F5",
            "Go Home": "Ctrl+Home",
            "Go Up": "Alt+Up",
            "Rename": "F2",
            "Delete": "Del",
            "New Folder": "Ctrl+N",
            "Toggle Hidden": "Ctrl+H",
            "Toggle Details": "Ctrl+D",
            "Zoom In": "Ctrl+=",
            "Zoom Out": "Ctrl+-"
        }
        if shortcuts:
            self.default_shortcuts.update(shortcuts)
        for name, seq in self.default_shortcuts.items():
            edit = QKeySequenceEdit(QKeySequence(self.settings.value(f"shortcut_{name}", seq)))
            shortcuts_layout.addRow(name, edit)
            self.shortcuts_edits[name] = edit
        shortcuts_group.setLayout(shortcuts_layout)

        # Sorting
        self.sort_col = QComboBox()
        self.sort_col.addItems(["Name", "Type", "Size", "Modified"])
        self.sort_col.setCurrentIndex(int(self.settings.value("sort_col", 0)))
        form.addRow("Sort Column", self.sort_col)
        self.sort_order = QComboBox()
        self.sort_order.addItems(["Ascending", "Descending"])
        self.sort_order.setCurrentIndex(int(self.settings.value("sort_order", 0)))
        form.addRow("Sort Order", self.sort_order)

        # Tabs
        tabs = QTabWidget()
        main_tab = QWidget()
        main_tab.setLayout(form)
        tabs.addTab(main_tab, "General / Appearance")
        tabs.addTab(shortcuts_group, "Keyboard Shortcuts")

        layout.addWidget(tabs)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        btns.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.restore_defaults)
        layout.addWidget(btns)

    def accept(self):
        self.settings.setValue("theme", self.theme.currentText())
        self.settings.setValue("fontsize", self.fontsize.value())
        self.settings.setValue("show_hidden", "true" if self.show_hidden.isChecked() else "false")
        self.settings.setValue("show_details", "true" if self.show_details.isChecked() else "false")
        self.settings.setValue("auto_refresh", "true" if self.auto_refresh.isChecked() else "false")
        self.settings.setValue("sort_col", self.sort_col.currentIndex())
        self.settings.setValue("sort_order", self.sort_order.currentIndex())
        for name, edit in self.shortcuts_edits.items():
            self.settings.setValue(f"shortcut_{name}", edit.keySequence().toString())
        self.settings_changed.emit()
        super().accept()

    def restore_defaults(self):
        self.theme.setCurrentText("Dark")
        self.fontsize.setValue(12)
        self.show_hidden.setChecked(False)
        self.show_details.setChecked(True)
        self.auto_refresh.setChecked(True)
        self.sort_col.setCurrentIndex(0)
        self.sort_order.setCurrentIndex(0)
        for name, edit in self.shortcuts_edits.items():
            edit.setKeySequence(QKeySequence(self.default_shortcuts[name]))

# -------- File Explorer Tab --------

class FileTab(QWidget):
    def __init__(self, parent, path, settings, watcher):
        super().__init__(parent)
        self.parent_window = parent
        self.settings = settings
        self.watcher = watcher
        self.file_dropped = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.proxy = FilterProxyModel()
        self.proxy.setSourceModel(self.model)

        self.tree = QTreeView()
        self.tree.setModel(self.proxy)
        self.tree.setRootIndex(self.proxy.mapFromSource(self.model.index(path)))
        self.tree.setFont(QFont("Fira Code", int(self.settings.value("fontsize", 12))))
        self.tree.setSortingEnabled(True)
        col = int(self.settings.value("sort_col", 0))
        order = Qt.AscendingOrder if int(self.settings.value("sort_order", 0)) == 0 else Qt.DescendingOrder
        self.tree.sortByColumn(col, order)
        # Custom alternating colors to fix visual bug
        self.tree.setAlternatingRowColors(True)
        palette = self.tree.palette()
        palette.setColor(QPalette.Base, QColor("#222" if self.settings.value("theme", "Dark") == "Dark" else "#fff"))
        palette.setColor(QPalette.AlternateBase, QColor("#333" if self.settings.value("theme", "Dark") == "Dark" else "#f2f2f2"))
        self.tree.setPalette(palette)
        self.tree.doubleClicked.connect(self.on_double_click)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.setDragDropMode(QAbstractItemView.DragDrop)
        self.tree.setAcceptDrops(True)
        self.tree.setDragEnabled(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.viewport().setAcceptDrops(True)
        self.tree.setEditTriggers(QAbstractItemView.EditKeyPressed | QAbstractItemView.SelectedClicked)
        layout.addWidget(self.tree)
        self.update_columns()
        self.update_hidden()
        self.install_file_watcher(path)

    def install_file_watcher(self, path):
        if self.settings.value("auto_refresh", "true") == "true":
            try:
                self.watcher.addPath(path)
                # QFileSystemModel does not have a refresh() method.
                # Use layoutChanged to force a refresh after directory change.
                self.watcher.directoryChanged.connect(self.on_directory_changed)
                self.watcher.fileChanged.connect(self.on_directory_changed)
            except Exception:
                pass

    def on_directory_changed(self, path):
        # This will emit dataChanged and cause the view/model to update
        self.model.setRootPath('')
        self.model.setRootPath(path)

    def update_columns(self):
        for i in range(1, 4):
            if self.settings.value("show_details", "true") == "true":
                self.tree.showColumn(i)
            else:
                self.tree.hideColumn(i)

    def update_hidden(self):
        filters = QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot
        if self.settings.value("show_hidden", "false") == "true":
            filters |= QDir.Hidden
        else:
            filters &= ~QDir.Hidden
        self.model.setFilter(filters)

    def open_context_menu(self, pos):
        index = self.tree.indexAt(pos)
        if not index.isValid():
            return
        src_idx = self.proxy.mapToSource(index)
        path = self.model.filePath(src_idx)
        menu = QMenu(self)
        open_action = QAction("Open")
        open_action.triggered.connect(lambda: self.on_double_click(index))
        menu.addAction(open_action)

        rename_action = QAction("Rename")
        rename_action.triggered.connect(lambda: self.parent_window.rename_item(path))
        menu.addAction(rename_action)

        delete_action = QAction("Delete")
        delete_action.triggered.connect(lambda: self.parent_window.delete_item(path))
        menu.addAction(delete_action)

        new_folder_action = QAction("New Folder")
        new_folder_action.triggered.connect(lambda: self.parent_window.create_new_folder(os.path.dirname(path) if not os.path.isdir(path) else path))
        menu.addAction(new_folder_action)

        refresh_action = QAction("Refresh")
        refresh_action.triggered.connect(lambda: self.model.setRootPath(self.model.rootPath()))
        menu.addAction(refresh_action)
        menu.exec_(self.tree.viewport().mapToGlobal(pos))

    def on_double_click(self, index):
        src_idx = self.proxy.mapToSource(index)
        path = self.model.filePath(src_idx)
        if os.path.isdir(path):
            self.tree.setRootIndex(self.proxy.mapFromSource(self.model.index(path)))
            self.parent_window.browse_input.setText(path)
            self.install_file_watcher(path)
        else:
            self.parent_window.open_file(path)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        # Drag and Drop to Copy Files
        if event.mimeData().hasUrls():
            dest_idx = self.tree.indexAt(event.pos())
            dest_path = self.model.filePath(self.proxy.mapToSource(dest_idx)) if dest_idx.isValid() else self.parent_window.browse_input.text()
            for url in event.mimeData().urls():
                src_path = url.toLocalFile()
                if os.path.isfile(src_path):
                    try:
                        import shutil
                        shutil.copy(src_path, dest_path)
                        self.model.setRootPath('')
                        self.model.setRootPath(dest_path)
                    except Exception as e:
                        QMessageBox.warning(self, "Copy Failed", str(e))
            event.acceptProposedAction()

# -------- Main Window --------

class FileExplorer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("ModernFileExplorer", "Settings")
        self.setWindowTitle("Modern File Explorer")
        self.setWindowIcon(QIcon.fromTheme("folder"))
        self.setGeometry(100, 100, 1200, 700)
        self.theme = self.settings.value("theme", "Dark")
        self.fontsize = int(self.settings.value("fontsize", 12))
        self.show_hidden = self.settings.value("show_hidden", "false") == "true"
        self.show_details = self.settings.value("show_details", "true") == "true"
        self.auto_refresh = self.settings.value("auto_refresh", "true") == "true"
        self.bookmarks = []
        self.shortcuts = self.load_shortcuts()
        self.watcher = QFileSystemWatcher(self)

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # Controls
        controls_layout = QHBoxLayout()
        self.browse_input = QLineEdit(QDir.rootPath())
        self.browse_input.returnPressed.connect(self.change_root_path)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.open_folder_dialog)
        controls_layout.addWidget(QLabel("Path:"))
        controls_layout.addWidget(self.browse_input)
        controls_layout.addWidget(browse_btn)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter...")
        self.search_input.textChanged.connect(self.filter_changed)
        controls_layout.addWidget(QLabel("Search:"))
        controls_layout.addWidget(self.search_input)

        new_tab_btn = QPushButton("New Room Tab")
        new_tab_btn.clicked.connect(lambda: self.add_new_tab(QDir.rootPath()))
        controls_layout.addWidget(new_tab_btn)

        prev_tab_btn = QPushButton("Previous Tab")
        prev_tab_btn.clicked.connect(self.previous_tab)
        controls_layout.addWidget(prev_tab_btn)

        zoom_in_btn = QPushButton("A+")
        zoom_in_btn.clicked.connect(self.zoom_in)
        controls_layout.addWidget(zoom_in_btn)
        zoom_out_btn = QPushButton("A-")
        zoom_out_btn.clicked.connect(self.zoom_out)
        controls_layout.addWidget(zoom_out_btn)

        self.toggle_hidden_btn = QPushButton(f"Show Hidden: {'ON' if self.show_hidden else 'OFF'}")
        self.toggle_hidden_btn.setCheckable(True)
        self.toggle_hidden_btn.setChecked(self.show_hidden)
        self.toggle_hidden_btn.clicked.connect(self.toggle_hidden_files)
        controls_layout.addWidget(self.toggle_hidden_btn)

        self.toggle_details_btn = QPushButton(f"Details: {'ON' if self.show_details else 'OFF'}")
        self.toggle_details_btn.setCheckable(True)
        self.toggle_details_btn.setChecked(self.show_details)
        self.toggle_details_btn.clicked.connect(self.toggle_details_columns)
        controls_layout.addWidget(self.toggle_details_btn)

        bookmark_btn = QPushButton("+ Bookmark")
        bookmark_btn.clicked.connect(self.add_bookmark)
        controls_layout.addWidget(bookmark_btn)

        github_label = QLabel("GitHub Repo URL:")
        self.github_input = QLineEdit()
        github_clone_btn = QPushButton("Clone Repo")
        github_clone_btn.clicked.connect(self.clone_github_repo)
        controls_layout.addWidget(github_label)
        controls_layout.addWidget(self.github_input)
        controls_layout.addWidget(github_clone_btn)

        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.open_settings)
        controls_layout.addWidget(settings_btn)

        controls_widget = QWidget()
        controls_widget.setLayout(controls_layout)

        # Bookmarks
        self.bookmark_list = QListWidget()
        self.bookmark_list.setMaximumWidth(200)
        self.bookmark_list.itemClicked.connect(self.on_bookmark_clicked)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_status)
        self.add_new_tab(QDir.rootPath())

        # Splitter (Resizable)
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.bookmark_list)
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(1, 4)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(controls_widget)
        main_layout.addWidget(splitter)
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        self.apply_theme()
        self.setup_shortcuts()
        self.update_status()

    # -------- Tab and Navigation --------
    def add_new_tab(self, path):
        tab = FileTab(self, path, self.settings, self.watcher)
        tab_index = self.tabs.addTab(tab, os.path.basename(path) if path != QDir.rootPath() else "Home")
        self.tabs.setCurrentIndex(tab_index)
        self.browse_input.setText(path)
        self.update_status()

    def close_tab(self, idx):
        if self.tabs.count() > 1:
            self.tabs.removeTab(idx)
        else:
            QMessageBox.information(self, "Cannot Close", "Cannot close the last tab.")

    def previous_tab(self):
        if self.tabs.count() <= 1:
            return
        idx = self.tabs.currentIndex()
        self.tabs.setCurrentIndex((idx - 1) % self.tabs.count())

    def get_current_tab(self):
        return self.tabs.currentWidget()

    def change_root_path(self):
        path = self.browse_input.text().strip()
        if not os.path.exists(path):
            QMessageBox.warning(self, "Invalid Path", "The specified path does not exist.")
            return
        tab = self.get_current_tab()
        if tab:
            tab.tree.setRootIndex(tab.proxy.mapFromSource(tab.model.index(path)))
            self.tabs.setTabText(self.tabs.currentIndex(), os.path.basename(path) if path != QDir.rootPath() else "Home")
            tab.install_file_watcher(path)
        self.update_status()

    def open_folder_dialog(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder", QDir.rootPath())
        if path:
            self.browse_input.setText(path)
            self.change_root_path()

    def filter_changed(self, text):
        tab = self.get_current_tab()
        if tab:
            tab.proxy.setFilterText(text)

    # -------- Appearance --------
    def zoom_in(self):
        self.fontsize = min(self.fontsize + 1, 32)
        self.settings.setValue("fontsize", self.fontsize)
        self.update_fonts()

    def zoom_out(self):
        self.fontsize = max(self.fontsize - 1, 8)
        self.settings.setValue("fontsize", self.fontsize)
        self.update_fonts()

    def update_fonts(self):
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            tab.tree.setFont(QFont("Fira Code", self.fontsize))

    def toggle_hidden_files(self):
        self.show_hidden = not self.show_hidden
        self.settings.setValue("show_hidden", "true" if self.show_hidden else "false")
        self.toggle_hidden_btn.setText(f"Show Hidden: {'ON' if self.show_hidden else 'OFF'}")
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            tab.update_hidden()
        self.update_status()

    def toggle_details_columns(self):
        self.show_details = not self.show_details
        self.settings.setValue("show_details", "true" if self.show_details else "false")
        self.toggle_details_btn.setText(f"Details: {'ON' if self.show_details else 'OFF'}")
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            tab.update_columns()
        self.update_status()

    def apply_theme(self):
        if self.theme == "Dark":
            QApplication.setStyle(QStyleFactory.create("Fusion"))
            p = QPalette()
            p.setColor(QPalette.Window, QColor(34,34,34))
            p.setColor(QPalette.WindowText, Qt.white)
            p.setColor(QPalette.Base, QColor(34, 34, 34))
            p.setColor(QPalette.AlternateBase, QColor(51, 51, 51))
            p.setColor(QPalette.ToolTipBase, Qt.white)
            p.setColor(QPalette.ToolTipText, Qt.white)
            p.setColor(QPalette.Text, Qt.white)
            p.setColor(QPalette.Button, QColor(51,51,51))
            p.setColor(QPalette.ButtonText, Qt.white)
            p.setColor(QPalette.BrightText, Qt.red)
            p.setColor(QPalette.Highlight, QColor(42,130,218))
            p.setColor(QPalette.HighlightedText, Qt.black)
            QApplication.setPalette(p)
        else:
            QApplication.setStyle(QStyleFactory.create("Fusion"))
            QApplication.setPalette(QApplication.style().standardPalette())

    def open_settings(self):
        dlg = SettingsDialog(self, self.shortcuts)
        dlg.settings_changed.connect(self.reload_settings)
        dlg.exec_()

    def reload_settings(self):
        self.theme = self.settings.value("theme", "Dark")
        self.fontsize = int(self.settings.value("fontsize", 12))
        self.show_hidden = self.settings.value("show_hidden", "false") == "true"
        self.show_details = self.settings.value("show_details", "true") == "true"
        self.auto_refresh = self.settings.value("auto_refresh", "true") == "true"
        self.shortcuts = self.load_shortcuts()
        self.apply_theme()
        self.update_fonts()
        self.toggle_hidden_btn.setChecked(self.show_hidden)
        self.toggle_details_btn.setChecked(self.show_details)
        self.toggle_hidden_btn.setText(f"Show Hidden: {'ON' if self.show_hidden else 'OFF'}")
        self.toggle_details_btn.setText(f"Details: {'ON' if self.show_details else 'OFF'}")
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            tab.update_hidden()
            tab.update_columns()
        self.setup_shortcuts()
        self.update_status()

    # -------- Bookmarks --------
    def add_bookmark(self):
        path = self.browse_input.text().strip()
        if not os.path.exists(path):
            QMessageBox.warning(self, "Invalid Path", "Cannot bookmark invalid path.")
            return
        if path not in self.bookmarks:
            self.bookmarks.append(path)
            self.bookmark_list.addItem(path)

    def on_bookmark_clicked(self, item):
        path = item.text()
        self.browse_input.setText(path)
        self.change_root_path()

    # -------- File Actions --------
    def open_file(self, path):
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", path], check=True)
            else:
                subprocess.run(["xdg-open", path], check=True)
        except Exception as e:
            QMessageBox.warning(self, "Open Failed", str(e))

    def rename_item(self, path):
        base = os.path.dirname(path)
        old = os.path.basename(path)
        new, ok = QInputDialog.getText(self, "Rename", "New name:", text=old)
        if ok and new and new != old:
            try:
                os.rename(path, os.path.join(base, new))
                self.get_current_tab().model.setRootPath('')
                self.get_current_tab().model.setRootPath(base)
            except Exception as e:
                QMessageBox.warning(self, "Rename Failed", str(e))

    def delete_item(self, path):
        confirm = QMessageBox.question(self, "Delete", f"Delete {path}?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm == QMessageBox.Yes:
            try:
                if os.path.isdir(path):
                    import shutil
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                dirname = os.path.dirname(path)
                self.get_current_tab().model.setRootPath('')
                self.get_current_tab().model.setRootPath(dirname)
            except Exception as e:
                QMessageBox.warning(self, "Delete Failed", str(e))

    def create_new_folder(self, parent_path):
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name:
            try:
                os.mkdir(os.path.join(parent_path, name))
                self.get_current_tab().model.setRootPath('')
                self.get_current_tab().model.setRootPath(parent_path)
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

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
            QMessageBox.warning(self, "Clone Failed", str(e))
            self.status.showMessage("Clone failed.")

    # -------- Shortcuts --------
    def load_shortcuts(self):
        default = {
            "New Tab": "Ctrl+T",
            "Close Tab": "Ctrl+W",
            "Next Tab": "Ctrl+Tab",
            "Previous Tab": "Ctrl+Shift+Tab",
            "Refresh": "F5",
            "Go Home": "Ctrl+Home",
            "Go Up": "Alt+Up",
            "Rename": "F2",
            "Delete": "Del",
            "New Folder": "Ctrl+N",
            "Toggle Hidden": "Ctrl+H",
            "Toggle Details": "Ctrl+D",
            "Zoom In": "Ctrl+=",
            "Zoom Out": "Ctrl+-"
        }
        s = {}
        for k, v in default.items():
            s[k] = self.settings.value(f"shortcut_{k}", v)
        return s

    def setup_shortcuts(self):
        # Remove all QShortcuts from self
        for c in self.findChildren(QShortcut):
            c.setParent(None)
        sc = self.shortcuts
        QShortcut(QKeySequence(sc["New Tab"]), self, lambda: self.add_new_tab(QDir.rootPath()))
        QShortcut(QKeySequence(sc["Close Tab"]), self, lambda: self.close_tab(self.tabs.currentIndex()))
        QShortcut(QKeySequence(sc["Next Tab"]), self, lambda: self.tabs.setCurrentIndex((self.tabs.currentIndex() + 1) % self.tabs.count()))
        QShortcut(QKeySequence(sc["Previous Tab"]), self, self.previous_tab)
        QShortcut(QKeySequence(sc["Refresh"]), self, lambda: self.get_current_tab().model.setRootPath(self.get_current_tab().model.rootPath()))
        QShortcut(QKeySequence(sc["Go Home"]), self, lambda: self.browse_input.setText(os.path.expanduser("~")) or self.change_root_path())
        QShortcut(QKeySequence(sc["Go Up"]), self, self.go_up)
        QShortcut(QKeySequence(sc["Rename"]), self, self.rename_selected)
        QShortcut(QKeySequence(sc["Delete"]), self, self.delete_selected)
        QShortcut(QKeySequence(sc["New Folder"]), self, lambda: self.create_new_folder(self.browse_input.text().strip()))
        QShortcut(QKeySequence(sc["Toggle Hidden"]), self, self.toggle_hidden_files)
        QShortcut(QKeySequence(sc["Toggle Details"]), self, self.toggle_details_columns)
        QShortcut(QKeySequence(sc["Zoom In"]), self, self.zoom_in)
        QShortcut(QKeySequence(sc["Zoom Out"]), self, self.zoom_out)

    def go_up(self):
        tab = self.get_current_tab()
        if tab:
            idx = tab.tree.rootIndex()
            src_idx = tab.proxy.mapToSource(idx)
            path = tab.model.filePath(src_idx)
            parent_path = os.path.dirname(path)
            if os.path.exists(parent_path):
                self.browse_input.setText(parent_path)
                self.change_root_path()

    def rename_selected(self):
        tab = self.get_current_tab()
        if tab:
            index = tab.tree.currentIndex()
            if index.isValid():
                src_idx = tab.proxy.mapToSource(index)
                path = tab.model.filePath(src_idx)
                self.rename_item(path)

    def delete_selected(self):
        tab = self.get_current_tab()
        if tab:
            index = tab.tree.currentIndex()
            if index.isValid():
                src_idx = tab.proxy.mapToSource(index)
                path = tab.model.filePath(src_idx)
                self.delete_item(path)

    # -------- Status --------
    def update_status(self):
        tab = self.get_current_tab()
        if not tab:
            self.status.showMessage("No active tab")
            return
        idx = tab.tree.rootIndex()
        src_idx = tab.proxy.mapToSource(idx)
        path = tab.model.filePath(src_idx)
        count = tab.model.rowCount(src_idx)
        self.status.showMessage(f"Root: {path} | Items: {count}")

def main():
    app = QApplication(sys.argv)
    win = FileExplorer()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()