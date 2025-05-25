import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QFileDialog, QPushButton, QSplitter, QHeaderView,
    QLabel, QHBoxLayout, QMenu, QAction, QMessageBox, QLineEdit
)
from PyQt5.QtCore import QFileSystemWatcher, Qt, QPoint
from PyQt5.QtGui import QFont, QColor

from parsing import CodeStructureParser  # Import moved logic here

class CodeExplorerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QWidget {
                background: #181a1b;
                color: #d4d4d4;
                font-size: 12px;
            }
            QTreeWidget, QTreeWidget::item {
                border-radius: 3px;
                border: 1px solid #222;
                background: #181a1b;
                alternate-background-color: #202325;
                font-size: 12px;
                show-decoration-selected: 1;
                min-height: 18px;
            }
            QHeaderView::section {
                background: #181a1b;
                color: #888;
                border: none;
            }
            QTreeWidget::item:selected {
                background: #3874f2;
                color: #fff;
            }
            QPushButton {
                background: #3874f2;
                color: #fff;
                border-radius: 2px;
                padding: 4px 10px;
                font-size: 12px;
            }
            QPushButton:hover { background: #1e90ff; }
            QLabel { color: #fff; font-size: 13px; }
            QLineEdit {
                background: #222;
                border: 1px solid #333;
                border-radius: 2px;
                color: #fff;
                padding: 3px;
                font-size: 12px;
            }
        """)
        layout = QVBoxLayout(self)

        # Info Bar
        infoLayout = QHBoxLayout()
        self.fileLabel = QLabel("No file loaded")
        infoLayout.addWidget(self.fileLabel)
        self.openBtn = QPushButton("Open File")
        self.openBtn.setMaximumWidth(90)
        self.openBtn.clicked.connect(self.open_file)
        infoLayout.addWidget(self.openBtn)
        self.printSrcBtn = QPushButton("Print Source")
        self.printSrcBtn.setMaximumWidth(110)
        self.printSrcBtn.clicked.connect(self.print_source)
        infoLayout.addWidget(self.printSrcBtn)
        infoLayout.addStretch()
        layout.addLayout(infoLayout)

        # Search Bar
        searchLayout = QHBoxLayout()
        self.searchEdit = QLineEdit()
        self.searchEdit.setPlaceholderText("Search in code structure...")
        self.searchEdit.textChanged.connect(self.advanced_search)
        searchLayout.addWidget(QLabel("Search:"))
        searchLayout.addWidget(self.searchEdit)
        layout.addLayout(searchLayout)

        # File Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['Code Structure'])
        self.tree.setAlternatingRowColors(True)
        self.tree.setMinimumWidth(180)
        self.tree.setColumnCount(1)
        self.tree.setRootIsDecorated(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        self.tree.setFont(QFont("Consolas", 10))
        self.tree.header().setSectionResizeMode(QHeaderView.Stretch)
        self.tree.setIndentation(14)
        layout.addWidget(self.tree)
        self.setLayout(layout)

        self.file_watcher = QFileSystemWatcher()
        self.file_watcher.fileChanged.connect(self.reload_file)
        self.current_file = None
        self.current_language = "python"
        self.structure = []
        self.full_source = ""

    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Code File", "", 
            "Code Files (*.py *.c *.cpp *.h *.hpp *.java);;All Files (*)")
        if filename:
            self.load_file(filename)
            self.file_watcher.removePaths(self.file_watcher.files())
            self.file_watcher.addPath(filename)
            self.current_file = filename

    def reload_file(self):
        if self.current_file:
            self.load_file(self.current_file)

    def load_file(self, filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                code = f.read()
            self.full_source = code
            language = self.detect_language(filename)
            self.current_language = language
            parser = CodeStructureParser(language)
            self.structure = parser.parse(code)
            self.populate_tree(self.structure)
            self.fileLabel.setText(os.path.basename(filename))
        except Exception as e:
            self.tree.clear()
            self.fileLabel.setText("No file loaded")
            QMessageBox.critical(self, "Error", "Error loading file: " + str(e))

    def detect_language(self, filename):
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".py":
            return "python"
        elif ext in (".c", ".h"):
            return "c"
        elif ext in (".cpp", ".hpp", ".cc", ".cxx"):
            return "cpp"
        elif ext == ".java":
            return "java"
        else:
            return "python"  # fallback

    def populate_tree(self, structure):
        self.tree.clear()
        def add_items(parent, items):
            for item in items:
                text = self.node_text(item)
                node = QTreeWidgetItem([text])
                node.setData(0, Qt.UserRole, item.get('line', 1))
                node.setData(0, Qt.UserRole+1, item)
                parent.addChild(node)
                if 'children' in item and item['children']:
                    add_items(node, item['children'])
        for item in structure:
            text = self.node_text(item)
            root = QTreeWidgetItem([text])
            root.setData(0, Qt.UserRole, item.get('line', 1))
            root.setData(0, Qt.UserRole+1, item)
            self.tree.addTopLevelItem(root)
            if 'children' in item and item['children']:
                add_items(root, item['children'])
        self.tree.expandAll()

    def node_text(self, item):
        if item['type'] == 'class':
            inh = f" : {item['inherits']}" if item.get('inherits') else ""
            members = f"  (members: {', '.join(item['members'])})" if item.get('members') else ""
            return f"class {item['name']}{inh} (Ln {item['line']}){members}"
        elif item['type'] == 'function':
            params = item.get('params', "")
            ret_type = item.get('ret_type', "")
            return f"{item['name']}({params}) : {ret_type} (Ln {item['line']})" if ret_type else f"{item['name']}({params}) (Ln {item['line']})"
        elif item['type'] == 'variable':
            vtype = item.get('vtype', "")
            return f"{item['name']}: {vtype} (Ln {item['line']})" if vtype else f"{item['name']} (Ln {item['line']})"
        else:
            return item['name']

    def open_context_menu(self, position: QPoint):
        item = self.tree.itemAt(position)
        if not item:
            return
        node_data = item.data(0, Qt.UserRole+1)
        menu = QMenu()
        if node_data:
            goto_action = QAction("Copy Name", self)
            goto_action.triggered.connect(lambda: QApplication.clipboard().setText(node_data['name']))
            menu.addAction(goto_action)
            if node_data['type'] == 'function':
                copy_sig = QAction("Copy Function Signature", self)
                def copy_sig_func():
                    ret_type = node_data.get('ret_type', '')
                    params = node_data.get('params', '')
                    sig = f"{node_data['name']}({params}) : {ret_type}" if ret_type else f"{node_data['name']}({params})"
                    QApplication.clipboard().setText(sig)
                copy_sig.triggered.connect(copy_sig_func)
                menu.addAction(copy_sig)
            if node_data['type'] == 'variable':
                copy_type = QAction("Copy Variable Type", self)
                def copy_type_func():
                    QApplication.clipboard().setText(node_data.get('vtype', ''))
                copy_type.triggered.connect(copy_type_func)
                menu.addAction(copy_type)
            show_info = QAction("Show Details", self)
            def show_info_func():
                details = f"Type: {node_data['type']}\nName: {node_data['name']}\nLine: {node_data['line']}"
                if 'params' in node_data:
                    details += f"\nParameters: {node_data['params']}"
                if 'ret_type' in node_data:
                    details += f"\nReturn Type: {node_data['ret_type']}"
                if 'vtype' in node_data:
                    details += f"\nVariable Type: {node_data['vtype']}"
                if 'inherits' in node_data and node_data['inherits']:
                    details += f"\nInherits: {node_data['inherits']}"
                if 'members' in node_data and node_data['members']:
                    details += f"\nMembers: {', '.join(node_data['members'])}"
                QMessageBox.information(self, "Node Details", details)
            show_info.triggered.connect(show_info_func)
            menu.addAction(show_info)
        menu.addSeparator()
        expand_action = QAction("Expand All", self)
        collapse_action = QAction("Collapse All", self)
        expand_action.triggered.connect(lambda: self.tree.expandAll())
        collapse_action.triggered.connect(lambda: self.tree.collapseAll())
        menu.addAction(expand_action)
        menu.addAction(collapse_action)
        menu.exec_(self.tree.viewport().mapToGlobal(position))

    def advanced_search(self, text):
        text = text.strip().lower()
        self.tree.expandAll()
        def search_tree(item):
            match = False
            for i in range(item.childCount()):
                if search_tree(item.child(i)):
                    match = True
            item_text = item.text(0).lower()
            if text in item_text:
                match = True
            item.setHidden(not match)
            if match:
                parent = item.parent()
                while parent:
                    parent.setHidden(False)
                    parent = parent.parent()
            return match
        for i in range(self.tree.topLevelItemCount()):
            search_tree(self.tree.topLevelItem(i))

    def print_source(self):
        if self.full_source:
            print(self.full_source)
            QMessageBox.information(self, "Print Source", "Full source code printed to standard output.")
        else:
            QMessageBox.warning(self, "Print Source", "No source code loaded.")

class CodeExplorer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Code Explorer")
        self.setGeometry(100, 100, 400, 580)
        self.setCentralWidget(CodeExplorerWidget())
        self.setWindowIconVisible = False
        self.setStyleSheet("""
            QMainWindow {
                background: #181a1b;
                color: #d4d4d4;
                border-radius: 8px;
            }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CodeExplorer()
    window.show()
    sys.exit(app.exec_())
