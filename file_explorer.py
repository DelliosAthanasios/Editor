import sys
import platform
import os
import tempfile
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTreeView, QFileSystemModel,
    QVBoxLayout, QWidget, QMessageBox, QPushButton, QLineEdit,
    QLabel, QHBoxLayout, QFileDialog, QStatusBar, QListWidget,
    QListWidgetItem, QSplitter, QMenu, QAction, QInputDialog, QSizePolicy
)
from PyQt5.QtCore import QDir, Qt, QSortFilterProxyModel
from PyQt5.QtGui import QFont, QIcon


class FilterProxyModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self._filter_text = ""

    def setFilterText(self, text):
        self._filter_text = text.lower()
        self.invalidateFilter()

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


class FileTreeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modern File Explorer")
        self.setGeometry(100, 100, 1200, 700)
        self.setWindowIcon(QIcon.fromTheme("folder"))

        self.is_dark = True
        self.font_size = 10
        self.min_font_size = 7
        self.max_font_size = 20

        self.show_hidden = False
        self.show_details = True

        self.bookmarks = []

        self.status = QStatusBar()
        self.setStatusBar(self.status)

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
        self.tree.setFont(QFont("Fira Code", self.font_size))
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, Qt.AscendingOrder)
        self.tree.selectionModel().selectionChanged.connect(self.update_status)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)

        self.update_columns_visibility()

        # Bookmarks list widget
        self.bookmark_list = QListWidget()
        self.bookmark_list.setMaximumWidth(200)
        self.bookmark_list.itemClicked.connect(self.on_bookmark_clicked)

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

        zoom_in_btn = QPushButton("A+")
        zoom_in_btn.setToolTip("Zoom In")
        zoom_in_btn.clicked.connect(self.zoom_in)
        zoom_in_btn.setFixedWidth(30)
        zoom_in_btn.setCursor(Qt.PointingHandCursor)

        zoom_out_btn = QPushButton("A-")
        zoom_out_btn.setToolTip("Zoom Out")
        zoom_out_btn.clicked.connect(self.zoom_out)
        zoom_out_btn.setFixedWidth(30)
        zoom_out_btn.setCursor(Qt.PointingHandCursor)

        close_btn = QPushButton("X")
        close_btn.setToolTip("Close")
        close_btn.clicked.connect(self.close)
        close_btn.setFixedWidth(30)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("color: red; font-weight: bold;")

        # Toggle hidden files checkbox
        self.toggle_hidden_btn = QPushButton("Show Hidden: OFF")
        self.toggle_hidden_btn.setCheckable(True)
        self.toggle_hidden_btn.clicked.connect(self.toggle_hidden_files)
        self.toggle_hidden_btn.setCursor(Qt.PointingHandCursor)

        # Toggle details columns button
        self.toggle_details_btn = QPushButton("Details: ON")
        self.toggle_details_btn.setCheckable(True)
        self.toggle_details_btn.setChecked(True)
        self.toggle_details_btn.clicked.connect(self.toggle_details_columns)
        self.toggle_details_btn.setCursor(Qt.PointingHandCursor)

        # Bookmark add button
        self.add_bookmark_btn = QPushButton("+ Bookmark")
        self.add_bookmark_btn.setToolTip("Add current path to bookmarks")
        self.add_bookmark_btn.clicked.connect(self.add_bookmark)
        self.add_bookmark_btn.setCursor(Qt.PointingHandCursor)

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
        github_clone_btn.setCursor(Qt.PointingHandCursor)

        # Controls layout
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(browse_label)
        controls_layout.addWidget(self.browse_input)
        controls_layout.addWidget(browse_button)
        controls_layout.addSpacing(10)
        controls_layout.addWidget(search_label)
        controls_layout.addWidget(self.search_input)
        controls_layout.addSpacing(10)
        controls_layout.addWidget(github_label)
        controls_layout.addWidget(self.github_input)
        controls_layout.addWidget(github_clone_btn)
        controls_layout.addSpacing(10)
        controls_layout.addWidget(zoom_in_btn)
        controls_layout.addWidget(zoom_out_btn)
        controls_layout.addWidget(self.toggle_hidden_btn)
        controls_layout.addWidget(self.toggle_details_btn)
        controls_layout.addWidget(self.add_bookmark_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(close_btn)

        controls_container = QWidget()
        controls_container.setLayout(controls_layout)
        controls_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Set initial root path after controls initialized
        self.set_root_path(QDir.rootPath())

        # Main layout: Splitter for bookmarks and file tree
        splitter = QSplitter()
        splitter.addWidget(self.bookmark_list)
        splitter.addWidget(self.tree)
        splitter.setStretchFactor(1, 4)

        main_layout = QVBoxLayout()
        main_layout.addWidget(controls_container)
        main_layout.addWidget(splitter)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.apply_theme()

    def update_columns_visibility(self):
        if self.show_details:
            for i in range(3):
                self.tree.showColumn(i)
        else:
            for i in range(1, 3):
                self.tree.hideColumn(i)

    def update_hidden_filter(self):
        filters = QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot
        if not self.show_hidden:
            filters &= ~QDir.Hidden
        else:
            filters |= QDir.Hidden
        self.model.setFilter(filters)

    def toggle_hidden_files(self):
        self.show_hidden = not self.show_hidden
        self.toggle_hidden_btn.setText(f"Show Hidden: {'ON' if self.show_hidden else 'OFF'}")
        self.update_hidden_filter()
        self.change_root_path()

    def toggle_details_columns(self):
        self.show_details = not self.show_details
        self.toggle_details_btn.setText(f"Details: {'ON' if self.show_details else 'OFF'}")
        self.update_columns_visibility()

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

    def set_root_path(self, path):
        idx = self.model.index(path)
        if idx.isValid():
            proxy_idx = self.proxy_model.mapFromSource(idx)
            self.tree.setRootIndex(proxy_idx)
            self.browse_input.setText(path)
            self.update_status()
        else:
            QMessageBox.warning(self, "Invalid Path", "Could not set the specified path as root.")

    def change_root_path(self):
        path = self.browse_input.text().strip()
        if not os.path.exists(path):
            QMessageBox.warning(self, "Invalid Path", "The specified path does not exist.")
            return
        self.set_root_path(path)

    def open_folder_dialog(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder", QDir.rootPath())
        if path:
            self.browse_input.setText(path)
            self.change_root_path()

    def filter_changed(self, text):
        self.proxy_model.setFilterText(text)

    def zoom_in(self):
        if self.font_size < self.max_font_size:
            self.font_size += 1
            self.tree.setFont(QFont("Fira Code", self.font_size))

    def zoom_out(self):
        if self.font_size > self.min_font_size:
            self.font_size -= 1
            self.tree.setFont(QFont("Fira Code", self.font_size))

    def update_status(self):
        idx = self.tree.rootIndex()
        if not idx.isValid():
            self.status.showMessage("No valid root selected")
            return
        source_idx = self.proxy_model.mapToSource(idx)
        path = self.model.filePath(source_idx)
        count = self.model.rowCount(source_idx)
        self.status.showMessage(f"Root: {path} | Items: {count}")

    def open_context_menu(self, pos):
        index = self.tree.indexAt(pos)
        if not index.isValid():
            return
        source_idx = self.proxy_model.mapToSource(index)
        path = self.model.filePath(source_idx)

        menu = QMenu()
        rename_action = QAction("Rename")
        delete_action = QAction("Delete")
        refresh_action = QAction("Refresh")

        rename_action.triggered.connect(lambda: self.rename_item(path))
        delete_action.triggered.connect(lambda: self.delete_item(path))
        refresh_action.triggered.connect(lambda: self.model.refresh(source_idx))

        menu.addAction(rename_action)
        menu.addAction(delete_action)
        menu.addSeparator()
        menu.addAction(refresh_action)
        menu.exec_(self.tree.viewport().mapToGlobal(pos))

    def rename_item(self, old_path):
        base_path = os.path.dirname(old_path)
        old_name = os.path.basename(old_path)
        new_name, ok = QInputDialog.getText(self, "Rename", "Enter new name:", text=old_name)
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(base_path, new_name)
            try:
                os.rename(old_path, new_path)
                self.model.refresh()  # Force refresh
                self.update_status()
            except Exception as e:
                QMessageBox.warning(self, "Rename Failed", f"Could not rename:\n{e}")

    def delete_item(self, path):
        confirm = QMessageBox.question(
            self,
            "Delete Confirmation",
            f"Are you sure you want to delete:\n{path}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            try:
                if os.path.isdir(path):
                    import shutil

                    shutil.rmtree(path)
                else:
                    os.remove(path)
                self.model.refresh()
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
            # Use 'git clone' command - assumes git is installed and in PATH
            subprocess.check_call(["git", "clone", url, temp_dir])
            self.browse_input.setText(temp_dir)
            self.change_root_path()
            self.status.showMessage(f"Cloned {url} into {temp_dir}")
        except Exception as e:
            QMessageBox.warning(self, "Clone Failed", f"Failed to clone repository:\n{e}")
            self.status.showMessage("Clone failed.")

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

