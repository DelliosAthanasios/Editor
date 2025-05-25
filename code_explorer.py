import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QFileDialog, QPushButton, QHeaderView,
    QLabel, QHBoxLayout, QMenu, QAction, QMessageBox, QLineEdit
)
from PyQt5.QtCore import QFileSystemWatcher, Qt, QPoint
from PyQt5.QtGui import QFont
from parsing import CodeStructureParser

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
            "All Code Files (*.py *.c *.cpp *.h *.hpp *.java *.js *.ts *.go *.rb *.php *.cs *.kt *.swift *.rs *.scala *.pl *.lua *.hs *.dart *.m *.sh *.r *.m *.groovy *.ex *.f90 *.f95 *.f *.for *.f77 *.html *.htm *.xml *.json *.yaml *.yml *.ml *.fs *.erl *.scm *.ss *.lisp *.lsp *.ps1 *.bat *.cmd *.tcl *.css *.sass *.scss *.sql *.graphql *.gql *.cob *.cbl *.pas *.dpr *.ada *.vhd *.vhdl *.v *.sv *.jl *.cr *.nim *.asm *.s *.pro);;All Files (*)"
        )
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
        extmap = {
            # Existing
            ".py": "python",
            ".c": "c",
            ".h": "c",
            ".cpp": "cpp",
            ".hpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".java": "java",
            ".js": "javascript",
            ".ts": "typescript",
            ".go": "go",
            ".rb": "ruby",
            ".php": "php",
            ".cs": "csharp",
            ".kt": "kotlin",
            ".swift": "swift",
            ".rs": "rust",
            ".scala": "scala",
            ".pl": "perl",
            ".lua": "lua",
            ".hs": "haskell",
            ".dart": "dart",
            ".m": "matlab",  # Could also be objective-c, but prioritize matlab for now
            ".groovy": "groovy",
            ".ex": "elixir",
            ".f90": "fortran",
            ".f95": "fortran",
            ".f": "fortran",
            ".for": "fortran",
            ".f77": "fortran",
            # Markup & Data
            ".html": "html",
            ".htm": "html",
            ".xml": "xml",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            # Functional & Academic
            ".ml": "ocaml",
            ".fs": "fsharp",
            ".erl": "erlang",
            ".scm": "scheme",
            ".ss": "scheme",
            ".lisp": "commonlisp",
            ".lsp": "commonlisp",
            # Scripting & Automation
            ".ps1": "powershell",
            ".bat": "batch",
            ".cmd": "batch",
            ".tcl": "tcl",
            # Web & Domain-Specific
            ".css": "css",
            ".sass": "sass",
            ".scss": "scss",
            ".sql": "sql",
            ".graphql": "graphql",
            ".gql": "graphql",
            # Legacy & Industry
            ".cob": "cobol",
            ".cbl": "cobol",
            ".pas": "pascal",
            ".dpr": "pascal",
            ".ada": "ada",
            ".vhd": "vhdl",
            ".vhdl": "vhdl",
            ".v": "verilog",
            ".sv": "verilog",
            # Others
            ".jl": "julia",
            ".cr": "crystal",
            ".nim": "nim",
            ".asm": "assembly",
            ".s": "assembly",
            ".pro": "prolog",
        }
        return extmap.get(ext, "python")

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
        # Compact, no icons, show inheritance/membership
        if item['type'] == 'class':
            inh = f" : {item.get('inherits','')}" if item.get('inherits') else ""
            members = ""
            if item.get('members'):
                members = f"  (members: {', '.join(item['members'])})"
            return f"class {item['name']}{inh} (Ln {item['line']}){members}"
        elif item['type'] == 'function':
            params = item.get('params', "")
            ret_type = item.get('ret_type', "")
            if ret_type:
                return f"{item['name']}({params}) : {ret_type} (Ln {item['line']})"
            else:
                return f"{item['name']}({params}) (Ln {item['line']})"
        elif item['type'] == 'variable':
            vtype = item.get('vtype', "")
            if vtype:
                return f"{item['name']}: {vtype} (Ln {item['line']})"
            else:
                return f"{item['name']} (Ln {item['line']})"
        else:
            return f"{item['type']} {item['name']} (Ln {item['line']})"

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
                    if ret_type:
                        sig = f"{node_data['name']}({params}) : {ret_type}"
                    else:
                        sig = f"{node_data['name']}({params})"
                    QApplication.clipboard().setText(sig)
                copy_sig.triggered.connect(copy_sig_func)
                menu.addAction(copy_sig)
            if node_data['type'] == 'variable':
                copy_type = QAction("Copy Variable Type", self)
                def copy_type_func():
                    vtype = node_data.get('vtype', '')
                    QApplication.clipboard().setText(vtype)
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
        expand_action = QAction("Expand All", self)
        expand_action.triggered.connect(lambda: self.tree.expandAll())
        collapse_action = QAction("Collapse All", self)
        collapse_action.triggered.connect(lambda: self.tree.collapseAll())
        menu.addSeparator()
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