import sys
import os
import platform
import tempfile
import subprocess
import json
from collections import deque
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTreeView, QFileSystemModel, QVBoxLayout, QWidget,
    QStatusBar, QPushButton, QLineEdit, QLabel, QHBoxLayout, QFileDialog,
    QTabWidget, QListWidget, QListWidgetItem, QSplitter, QMessageBox, QMenu, QAction,
    QInputDialog, QDialog, QFormLayout, QComboBox, QCheckBox, QDialogButtonBox, QSpinBox,
    QKeySequenceEdit, QShortcut, QAbstractItemView, QStyleFactory, QSizePolicy, QTextEdit, QPlainTextEdit,
    QGroupBox, QFrame, QGridLayout
)
from PyQt5.QtCore import QDir, Qt, QSettings, QSortFilterProxyModel, QFileSystemWatcher, QModelIndex, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QKeySequence, QColor, QPalette, QPixmap

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

# -------- Plugin API --------
class PluginManager:
    def __init__(self, plugin_folder="plugins"):
        self.plugin_folder = plugin_folder
        self.plugins = []
        if not os.path.exists(plugin_folder):
            os.makedirs(plugin_folder)
        self.load_plugins()

    def load_plugins(self):
        self.plugins = []
        sys.path.insert(0, self.plugin_folder)
        for fname in os.listdir(self.plugin_folder):
            if fname.endswith(".py") and not fname.startswith("_"):
                try:
                    name = fname[:-3]
                    mod = __import__(name)
                    if hasattr(mod, "register"):
                        self.plugins.append(mod)
                except Exception as e:
                    print(f"Failed to load plugin {fname}: {e}")
        sys.path.pop(0)

    def get_plugin_actions(self, context):
        actions = []
        for plugin in self.plugins:
            try:
                plugin_actions = plugin.register(context)
                if isinstance(plugin_actions, list):
                    actions.extend(plugin_actions)
            except Exception as e:
                print(f"Plugin error: {e}")
        return actions

# -------- File Preview Pane --------

class PreviewPane(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMinimumWidth(180)
        self.setMaximumWidth(220)

    def show_preview(self, path):
        self.clear()
        if not path or not os.path.exists(path):
            return
        ext = os.path.splitext(path)[1].lower()
        if ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
            self.setPlainText("[Image preview not supported in text pane. Use file preview dialog.]")
        elif ext in [".txt", ".py", ".md", ".log", ".ini", ".json", ".xml", ".csv"]:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    data = f.read()
            except Exception:
                data = "[Error reading file]"
            self.setPlainText(data)
        else:
            self.setPlainText("Preview not available for this file type.")

# -------- Recent Files/Folders --------

class RecentList(QListWidget):
    def __init__(self, max_items=20, parent=None):
        super().__init__(parent)
        self.max_items = max_items
        self.setMaximumWidth(180)
        self.setWindowTitle("Recent Files/Folders")
        self.setAlternatingRowColors(True)
        self.recent = deque(maxlen=max_items)

    def add_recent(self, path):
        if path in self.recent:
            self.recent.remove(path)
        self.recent.appendleft(path)
        self.update_list()

    def update_list(self):
        self.clear()
        for path in self.recent:
            self.addItem(path)

# -------- Quick Access Bar --------

class QuickAccessBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setMaximumHeight(32)
        self.buttons = {}
        self.paths = []
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def add_quick_access(self, path, callback):
        if path in self.paths:
            return
        btn = QPushButton(os.path.basename(path) or path)
        btn.setToolTip(path)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: callback(path))
        self.layout.addWidget(btn)
        self.buttons[path] = btn
        self.paths.append(path)

    def clear_quick_access(self):
        for path, btn in self.buttons.items():
            btn.setParent(None)
        self.buttons.clear()
        self.paths.clear()

# -------- File Preview Dialog --------

class PreviewDialog(QDialog):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preview: " + os.path.basename(path))
        self.setMinimumSize(400, 300)
        layout = QVBoxLayout(self)
        ext = os.path.splitext(path)[1].lower()
        if ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
            label = QLabel()
            pix = QPixmap(path)
            label.setPixmap(pix.scaled(350, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            layout.addWidget(label)
        elif ext in [".txt", ".py", ".md", ".log", ".ini", ".json", ".xml", ".csv"]:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    data = f.read()
            except Exception:
                data = "[Error reading file]"
            edit = QPlainTextEdit(data)
            edit.setReadOnly(True)
            layout.addWidget(edit)
        elif ext in [".pdf"]:
            label = QLabel("PDF preview not implemented. (TODO)")
            layout.addWidget(label)
        else:
            label = QLabel("Preview not available for this file type.")
            layout.addWidget(label)
        btn = QPushButton("Close")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

# -------- Custom Actions --------

class CustomActionDialog(QDialog):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Run Custom Action")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("e.g. echo {file} or python3 {file}")
        layout.addWidget(QLabel("Shell command:"))
        layout.addWidget(self.cmd_input)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self.setLayout(layout)
    def get_command(self):
        return self.cmd_input.text()

# -------- Settings Dialog --------

class SettingsDialog(QDialog):
    settings_changed = pyqtSignal()

    def __init__(self, parent=None, shortcuts=None, show_previews=True, show_bookmarks=True, show_history=True):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setWindowIcon(QIcon.fromTheme("preferences-system"))
        self.settings = QSettings("ModernFileExplorer", "Settings")
        self.resize(550, 520)
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

        self.tabs_persistence = QCheckBox("Restore Tabs on Startup")
        self.tabs_persistence.setChecked(self.settings.value("tabs_persistence", "false") == "true")
        form.addRow(self.tabs_persistence)

        # Window controls
        self.show_preview = QCheckBox("Show File Preview Panel")
        self.show_preview.setChecked(show_previews)
        form.addRow(self.show_preview)
        self.show_bookmarks = QCheckBox("Show Bookmarks Panel")
        self.show_bookmarks.setChecked(show_bookmarks)
        form.addRow(self.show_bookmarks)
        self.show_history = QCheckBox("Show History Panel")
        self.show_history.setChecked(show_history)
        form.addRow(self.show_history)

        # Only English available
        self.language = QLabel("English (only)")
        form.addRow("Language", self.language)

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
            "Zoom Out": "Ctrl+-",
            "Preview File": "Space"
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
        self.settings.setValue("tabs_persistence", "true" if self.tabs_persistence.isChecked() else "false")
        self.settings.setValue("language", "English")
        self.settings.setValue("sort_col", self.sort_col.currentIndex())
        self.settings.setValue("sort_order", self.sort_order.currentIndex())
        for name, edit in self.shortcuts_edits.items():
            self.settings.setValue(f"shortcut_{name}", edit.keySequence().toString())
        self.settings_changed.emit()
        QDialog.accept(self)

    def restore_defaults(self):
        self.theme.setCurrentText("Dark")
        self.fontsize.setValue(12)
        self.show_hidden.setChecked(False)
        self.show_details.setChecked(True)
        self.auto_refresh.setChecked(True)
        self.tabs_persistence.setChecked(False)
        self.show_preview.setChecked(True)
        self.show_bookmarks.setChecked(True)
        self.show_history.setChecked(True)
        self.sort_col.setCurrentIndex(0)
        self.sort_order.setCurrentIndex(0)
        for name, edit in self.shortcuts_edits.items():
            edit.setKeySequence(QKeySequence(self.default_shortcuts[name]))

# -------- Cloud Storage Dialog --------

class CloudStorageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cloud Storage Integration")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        self.info = QLabel(
            "Here you could integrate your Google Drive, Dropbox, or OneDrive.\n"
            "For demo: Will just show a placeholder.\n"
            "Production: Add OAuth/SDK integrations and list/download files."
        )
        layout.addWidget(self.info)
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        layout.addWidget(btn_ok)

# -------- File Explorer Tab --------

class FileTab(QWidget):
    def __init__(self, parent, path, settings, watcher, preview_callback=None, recent_callback=None, plugin_manager=None):
        super().__init__(parent)
        self.parent_window = parent
        self.settings = settings
        self.watcher = watcher
        self.preview_callback = preview_callback
        self.recent_callback = recent_callback
        self.plugin_manager = plugin_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.proxy = FilterProxyModel()
        self.proxy.setSourceModel(self.model)

        # File tree
        self.tree = QTreeView()
        self.tree.setModel(self.proxy)
        self.tree.setRootIndex(self.proxy.mapFromSource(self.model.index(path)))
        self.tree.setFont(QFont("Fira Code", int(self.settings.value("fontsize", 12))))
        self.tree.setSortingEnabled(True)
        col = int(self.settings.value("sort_col", 0))
        order = Qt.AscendingOrder if int(self.settings.value("sort_order", 0)) == 0 else Qt.DescendingOrder
        self.tree.sortByColumn(col, order)
        self.tree.setAlternatingRowColors(True)
        palette = self.tree.palette()
        dark = self.settings.value("theme", "Dark") == "Dark"
        palette.setColor(QPalette.Base, QColor("#252526" if dark else "#fff"))
        palette.setColor(QPalette.AlternateBase, QColor("#2a2d2e" if dark else "#f5f5f5"))
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
        self.setLayout(layout)
        self.update_columns()
        self.update_hidden()
        self.install_file_watcher(path)

    def install_file_watcher(self, path):
        if self.settings.value("auto_refresh", "true") == "true":
            try:
                self.watcher.addPath(path)
                self.watcher.directoryChanged.connect(self.on_directory_changed)
                self.watcher.fileChanged.connect(self.on_directory_changed)
            except Exception:
                pass

    def on_directory_changed(self, path):
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
        preview_action = QAction("Preview")
        preview_action.triggered.connect(lambda: self.preview_callback(path))
        menu.addAction(preview_action)
        custom_action = QAction("Custom Command...")
        custom_action.triggered.connect(lambda: self.parent_window.run_custom_action(path))
        menu.addAction(custom_action)
        # Plugin actions
        if self.plugin_manager:
            plugin_actions = self.plugin_manager.get_plugin_actions({"path": path})
            for act in plugin_actions:
                if isinstance(act, QAction):
                    menu.addAction(act)
                elif isinstance(act, dict):
                    a = QAction(act.get("text", "Plugin Action"))
                    if "callback" in act:
                        a.triggered.connect(lambda checked, p=path, cb=act["callback"]: cb(p, self))
                    menu.addAction(a)
        menu.addSeparator()
        rename_action = QAction("Rename")
        rename_action.triggered.connect(lambda: self.parent_window.rename_item(path))
        menu.addAction(rename_action)
        delete_action = QAction("Delete")
        delete_action.triggered.connect(lambda: self.parent_window.delete_item(path))
        menu.addAction(delete_action)
        menu.addSeparator()
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
        if self.recent_callback:
            self.recent_callback(path)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
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
        self.setGeometry(100, 100, 1400, 800)
        self.theme = self.settings.value("theme", "Dark")
        self.fontsize = int(self.settings.value("fontsize", 12))
        self.show_hidden = self.settings.value("show_hidden", "false") == "true"
        self.show_details = self.settings.value("show_details", "true") == "true"
        self.auto_refresh = self.settings.value("auto_refresh", "true") == "true"
        self.bookmarks = []
        self.shortcuts = self.load_shortcuts()
        self.watcher = QFileSystemWatcher(self)
        self.plugin_manager = PluginManager("plugins")

        self.show_previews = True
        self.show_bookmarks = True
        self.show_history = True

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # Quick Access
        self.quick_access = QuickAccessBar()
        self.quick_access.add_quick_access(os.path.expanduser("~"), self.navigate_to_path)
        if platform.system() == "Windows":
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            if os.path.isdir(desktop):
                self.quick_access.add_quick_access(desktop, self.navigate_to_path)
        else:
            self.quick_access.add_quick_access("/tmp", self.navigate_to_path)

        # ----------- Organize controls by groupboxes -----------
        controls_grid = QGridLayout()
        controls_grid.setContentsMargins(2, 2, 2, 2)
        controls_grid.setSpacing(8)

        # View Group
        view_box = QGroupBox("View")
        vb_layout = QHBoxLayout()
        vb_layout.setContentsMargins(3, 3, 3, 3)

        zoom_in_btn = QPushButton("A+")
        zoom_in_btn.setToolTip("Zoom In")
        zoom_in_btn.clicked.connect(self.zoom_in)
        zoom_in_btn.setFixedWidth(30)
        zoom_in_btn.setCursor(Qt.PointingHandCursor)
        vb_layout.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("A-")
        zoom_out_btn.setToolTip("Zoom Out")
        zoom_out_btn.clicked.connect(self.zoom_out)
        zoom_out_btn.setFixedWidth(30)
        zoom_out_btn.setCursor(Qt.PointingHandCursor)
        vb_layout.addWidget(zoom_out_btn)

        self.toggle_hidden_btn = QPushButton(f"Show Hidden: {'ON' if self.show_hidden else 'OFF'}")
        self.toggle_hidden_btn.setCheckable(True)
        self.toggle_hidden_btn.setChecked(self.show_hidden)
        self.toggle_hidden_btn.clicked.connect(self.toggle_hidden_files)
        self.toggle_hidden_btn.setCursor(Qt.PointingHandCursor)
        vb_layout.addWidget(self.toggle_hidden_btn)

        self.toggle_details_btn = QPushButton(f"Details: {'ON' if self.show_details else 'OFF'}")
        self.toggle_details_btn.setCheckable(True)
        self.toggle_details_btn.setChecked(self.show_details)
        self.toggle_details_btn.clicked.connect(self.toggle_details_columns)
        self.toggle_details_btn.setCursor(Qt.PointingHandCursor)
        vb_layout.addWidget(self.toggle_details_btn)

        view_box.setLayout(vb_layout)
        controls_grid.addWidget(view_box, 0, 0)

        # Settings Group
        settings_box = QGroupBox("Settings")
        sb_layout = QHBoxLayout()
        sb_layout.setContentsMargins(3, 3, 3, 3)
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.open_settings)
        sb_layout.addWidget(settings_btn)
        close_btn = QPushButton("X")
        close_btn.setToolTip("Close")
        close_btn.clicked.connect(self.close)
        close_btn.setFixedWidth(30)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("color: red; font-weight: bold;")
        sb_layout.addWidget(close_btn)
        settings_box.setLayout(sb_layout)
        controls_grid.addWidget(settings_box, 0, 1)

        # Files Group
        files_box = QGroupBox("Files")
        fb_layout = QHBoxLayout()
        fb_layout.setContentsMargins(3, 3, 3, 3)
        new_tab_btn = QPushButton("New Tab")
        new_tab_btn.clicked.connect(lambda: self.add_new_tab(QDir.rootPath()))
        fb_layout.addWidget(new_tab_btn)
        prev_tab_btn = QPushButton("Previous Tab")
        prev_tab_btn.clicked.connect(self.previous_tab)
        fb_layout.addWidget(prev_tab_btn)
        bookmark_btn = QPushButton("+ Bookmark")
        bookmark_btn.setToolTip("Add current path to bookmarks")
        bookmark_btn.clicked.connect(self.add_bookmark)
        bookmark_btn.setCursor(Qt.PointingHandCursor)
        fb_layout.addWidget(bookmark_btn)
        export_bookmarks_btn = QPushButton("Export Bookmarks")
        export_bookmarks_btn.clicked.connect(self.export_bookmarks)
        fb_layout.addWidget(export_bookmarks_btn)
        import_bookmarks_btn = QPushButton("Import Bookmarks")
        import_bookmarks_btn.clicked.connect(self.import_bookmarks)
        fb_layout.addWidget(import_bookmarks_btn)
        files_box.setLayout(fb_layout)
        controls_grid.addWidget(files_box, 0, 2)

        # Github & Cloud Group
        github_box = QGroupBox("GitHub")
        gb_layout = QHBoxLayout()
        gb_layout.setContentsMargins(3, 3, 3, 3)
        github_label = QLabel("Repo URL:")
        github_label.setStyleSheet("font-weight: bold;")
        self.github_input = QLineEdit()
        self.github_input.setPlaceholderText("https://github.com/user/repo.git")
        github_clone_btn = QPushButton("Clone Repo")
        github_clone_btn.setIcon(QIcon.fromTheme("git"))
        github_clone_btn.setToolTip("Clone GitHub repository and open")
        github_clone_btn.clicked.connect(self.clone_github_repo)
        github_clone_btn.setCursor(Qt.PointingHandCursor)
        cloud_btn = QPushButton("Cloud Storage")
        cloud_btn.clicked.connect(self.open_cloud_storage)
        gb_layout.addWidget(github_label)
        gb_layout.addWidget(self.github_input)
        gb_layout.addWidget(github_clone_btn)
        gb_layout.addWidget(cloud_btn)
        github_box.setLayout(gb_layout)
        controls_grid.addWidget(github_box, 1, 0, 1, 2)

        # Path/Search
        nav_box = QGroupBox("Navigation")
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(3, 3, 3, 3)
        browse_label = QLabel("Path:")
        browse_label.setStyleSheet("font-weight: bold;")
        self.browse_input = QLineEdit(QDir.rootPath())
        self.browse_input.setPlaceholderText("Enter path or click Browse")
        self.browse_input.returnPressed.connect(self.change_root_path)
        browse_btn = QPushButton("Browse")
        browse_btn.setIcon(QIcon.fromTheme("folder-open"))
        browse_btn.clicked.connect(self.open_folder_dialog)
        browse_btn.setCursor(Qt.PointingHandCursor)
        nav_layout.addWidget(browse_label)
        nav_layout.addWidget(self.browse_input)
        nav_layout.addWidget(browse_btn)
        search_label = QLabel("Search:")
        search_label.setStyleSheet("font-weight: bold;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter files/folders...")
        self.search_input.textChanged.connect(self.filter_changed)
        nav_layout.addSpacing(10)
        nav_layout.addWidget(search_label)
        nav_layout.addWidget(self.search_input)
        nav_box.setLayout(nav_layout)
        controls_grid.addWidget(nav_box, 1, 2)

        controls_widget = QWidget()
        controls_widget.setLayout(controls_grid)
        controls_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Bookmarks
        self.bookmark_list = QListWidget()
        self.bookmark_list.setMaximumWidth(180)
        self.bookmark_list.itemClicked.connect(self.on_bookmark_clicked)

        # Recent
        self.recent_list = RecentList(max_items=30)
        self.recent_list.setMaximumWidth(180)
        self.recent_list.itemClicked.connect(lambda item: self.navigate_to_path(item.text()))

        # File Preview Pane
        self.preview_pane = PreviewPane()

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_status)
        self.add_new_tab(QDir.rootPath())

        # Splitter (Organized order: bookmarks | history | tabs | file preview)
        self.left_splitter = QSplitter(Qt.Vertical)
        self.left_splitter.addWidget(self.bookmark_list)
        self.left_splitter.addWidget(self.recent_list)
        self.left_splitter.setStretchFactor(0, 1)
        self.left_splitter.setStretchFactor(1, 1)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.addWidget(self.left_splitter)
        self.main_splitter.addWidget(self.tabs)
        self.main_splitter.addWidget(self.preview_pane)
        self.main_splitter.setSizes([120, 850, 160])

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.quick_access)
        main_layout.addWidget(controls_widget)
        main_layout.addWidget(self.main_splitter)
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        self.apply_theme()
        self.setup_shortcuts()
        self.update_status()

        # Tabs persistence
        if self.settings.value("tabs_persistence", "false") == "true":
            QTimer.singleShot(100, self.restore_tabs)

        self.apply_panel_visibility()

    # -------- Tabs Persistence --------
    def closeEvent(self, event):
        if self.settings.value("tabs_persistence", "false") == "true":
            self.save_tabs()
        super().closeEvent(event)

    def save_tabs(self):
        paths = []
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            idx = tab.tree.rootIndex()
            src_idx = tab.proxy.mapToSource(idx)
            paths.append(tab.model.filePath(src_idx))
        self.settings.setValue("last_tabs", "|".join(paths))

    def restore_tabs(self):
        last = self.settings.value("last_tabs", "")
        paths = [p for p in last.split("|") if p]
        if paths:
            self.tabs.clear()
            for path in paths:
                self.add_new_tab(path)

    # -------- Bookmarks Export/Import --------
    def export_bookmarks(self):
        export_data = {
            "bookmarks": self.bookmarks,
            "quick_access": self.quick_access.paths,
            "settings": {k: self.settings.value(k) for k in self.settings.allKeys()}
        }
        path, _ = QFileDialog.getSaveFileName(self, "Export Bookmarks/Settings", "bookmarks.json", "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2)
            QMessageBox.information(self, "Export Bookmarks", f"Bookmarks/settings exported to {path}.")
        except Exception as e:
            QMessageBox.warning(self, "Export Failed", str(e))

    def import_bookmarks(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Bookmarks/Settings", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "bookmarks" in data:
                self.bookmarks = list(data["bookmarks"])
                self.bookmark_list.clear()
                for b in self.bookmarks:
                    self.bookmark_list.addItem(b)
            if "quick_access" in data:
                self.quick_access.clear_quick_access()
                for p in data["quick_access"]:
                    self.quick_access.add_quick_access(p, self.navigate_to_path)
            if "settings" in data:
                for k, v in data["settings"].items():
                    self.settings.setValue(k, v)
            QMessageBox.information(self, "Import Bookmarks", f"Bookmarks/settings imported from {path}.")
        except Exception as e:
            QMessageBox.warning(self, "Import Failed", str(e))

    # -------- Recent/Quick Access --------
    def add_recent(self, path):
        self.recent_list.add_recent(path)

    def navigate_to_path(self, path):
        self.browse_input.setText(path)
        self.change_root_path()

    def add_quick_access(self, path):
        self.quick_access.add_quick_access(path, self.navigate_to_path)

    # -------- Tab and Navigation --------
    def add_new_tab(self, path):
        tab = FileTab(self, path, self.settings, self.watcher, preview_callback=self.file_preview, recent_callback=self.add_recent, plugin_manager=self.plugin_manager)
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
            self.add_recent(path)
            self.preview_pane.show_preview("")
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
            p.setColor(QPalette.Window, QColor(30,30,30))
            p.setColor(QPalette.WindowText, QColor(204,204,204))
            p.setColor(QPalette.Base, QColor(37, 37, 38))
            p.setColor(QPalette.AlternateBase, QColor(42, 45, 46))
            p.setColor(QPalette.ToolTipBase, Qt.white)
            p.setColor(QPalette.ToolTipText, Qt.white)
            p.setColor(QPalette.Text, QColor(204,204,204))
            p.setColor(QPalette.Button, QColor(60,60,60))
            p.setColor(QPalette.ButtonText, QColor(204,204,204))
            p.setColor(QPalette.BrightText, Qt.red)
            p.setColor(QPalette.Highlight, QColor(9, 71, 113))
            p.setColor(QPalette.HighlightedText, Qt.white)
            QApplication.setPalette(p)
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
            """)
        else:
            QApplication.setStyle(QStyleFactory.create("Fusion"))
            QApplication.setPalette(QApplication.style().standardPalette())
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
            """)

    def apply_panel_visibility(self):
        self.bookmark_list.setVisible(self.show_bookmarks)
        self.recent_list.setVisible(self.show_history)
        self.preview_pane.setVisible(self.show_previews)
        # Adjust splitter sizes for a clean look
        if not self.show_bookmarks and not self.show_history:
            self.left_splitter.setSizes([0, 0])
            self.main_splitter.setSizes([0, 8, 2])
        elif not self.show_bookmarks or not self.show_history:
            self.left_splitter.setSizes([1, 0] if self.show_bookmarks else [0, 1])
            self.main_splitter.setSizes([1, 8, 2])
        else:
            self.left_splitter.setSizes([1, 1])
            self.main_splitter.setSizes([2, 8, 2])
        if not self.show_previews:
            self.main_splitter.setSizes([2, 8, 0])

    def open_settings(self):
        dlg = SettingsDialog(self, self.shortcuts, self.show_previews, self.show_bookmarks, self.show_history)
        dlg.settings_changed.connect(self.reload_settings)
        if dlg.exec_():
            self.show_previews = dlg.show_preview.isChecked()
            self.show_bookmarks = dlg.show_bookmarks.isChecked()
            self.show_history = dlg.show_history.isChecked()
            self.apply_panel_visibility()

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

    def open_cloud_storage(self):
        dlg = CloudStorageDialog(self)
        dlg.exec_()

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
        self.add_quick_access(path)

    # -------- File Actions & Preview --------
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

    def file_preview(self, path=None):
        if not path:
            tab = self.get_current_tab()
            if tab:
                idx = tab.tree.currentIndex()
                if idx.isValid():
                    src_idx = tab.proxy.mapToSource(idx)
                    path = tab.model.filePath(src_idx)
        if path and os.path.isfile(path):
            dlg = PreviewDialog(path, self)
            dlg.exec_()
            self.preview_pane.show_preview(path)

    def run_custom_action(self, path=None):
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "No file/folder", "No file/folder selected.")
            return
        dlg = CustomActionDialog(path, self)
        if dlg.exec_():
            cmd = dlg.get_command()
            if not cmd:
                return
            cmd_str = cmd.replace("{file}", f'"{path}"')
            try:
                output = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
                QMessageBox.information(self, "Custom Action Output", output)
            except Exception as e:
                QMessageBox.warning(self, "Command Failed", str(e))

    def clone_github_repo(self):
        url = self.github_input.text().strip()
        if not url.startswith("https://github.com/") and not url.startswith("git@github.com:"):
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid GitHub repository URL.")
            return
        target_dir = QFileDialog.getExistingDirectory(self, "Select directory to clone the repo into", QDir.homePath())
        if not target_dir:
            return
        repo_name = url.rstrip('/').split('/')[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        dest_path = os.path.join(target_dir, repo_name)
        if os.path.exists(dest_path):
            QMessageBox.warning(self, "Directory Exists", f"The directory '{dest_path}' already exists.")
            return
        self.status.showMessage("Cloning repository, please wait...")
        QApplication.processEvents()
        try:
            subprocess.check_call(["git", "clone", url, dest_path])
            self.add_new_tab(dest_path)
            self.status.showMessage(f"Cloned {url} into {dest_path}")
            QMessageBox.information(self, "Repository Cloned", f"Cloned {url} into {dest_path}")
        except Exception as e:
            QMessageBox.warning(self, "Clone Failed", str(e))
            self.status.showMessage("Clone failed.")

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
            "Zoom Out": "Ctrl+-",
            "Preview File": "Space"
        }
        s = {}
        for k, v in default.items():
            s[k] = self.settings.value(f"shortcut_{k}", v)
        return s

    def setup_shortcuts(self):
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
        QShortcut(QKeySequence(sc["Preview File"]), self, self.file_preview)

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
    win = FileExplorer()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()