import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QFileDialog, QPushButton, QSplitter, QHeaderView,
    QLabel, QHBoxLayout, QMenu, QAction, QMessageBox, QLineEdit
)
from PyQt5.QtCore import QFileSystemWatcher, Qt, QPoint
from PyQt5.QtGui import QFont, QColor, QIcon

from .parsing import CodeStructureParser  # Import moved logic here
from .theme_manager import theme_manager_singleton, get_editor_styles

class CodeExplorerWidget(QWidget):
    """
    A widget for exploring code structure (classes, functions, variables) in a file.
    Can be embedded in layouts like FileTreeWidget.
    """
    def __init__(self, file_path=None, parent=None):
        super().__init__(parent)
        self.current_file = None
        self.current_language = "python"
        self.structure = []
        self.full_source = ""
        self.icons = {
            'class': QIcon.fromTheme('class', QIcon()),
            'function': QIcon.fromTheme('function', QIcon()),
            'variable': QIcon.fromTheme('variable', QIcon()),
        }
        self.init_ui()
        # Theme integration
        theme_data = theme_manager_singleton.get_theme()
        self.set_theme(theme_data)
        theme_manager_singleton.themeChanged.connect(self.set_theme)
        if file_path:
            self.set_file(file_path)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header bar
        header_layout = QHBoxLayout()
        self.fileLabel = QLabel("No file loaded")
        self.fileLabel.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.pathLabel = QLabel("")
        self.pathLabel.setStyleSheet("color: #888; font-size: 11px;")
        self.refreshBtn = QPushButton("⟳")
        self.refreshBtn.setFixedWidth(28)
        self.refreshBtn.setToolTip("Refresh file structure")
        self.refreshBtn.clicked.connect(self.reload_file)
        header_layout.addWidget(self.fileLabel)
        header_layout.addWidget(self.pathLabel)
        header_layout.addStretch()
        header_layout.addWidget(self.refreshBtn)
        layout.addLayout(header_layout)

        # Search bar
        search_layout = QHBoxLayout()
        self.searchEdit = QLineEdit()
        self.searchEdit.setPlaceholderText("Search in code structure...")
        self.searchEdit.textChanged.connect(self.advanced_search)
        self.searchEdit.setStyleSheet("padding: 4px; border-radius: 4px; background: #222; color: #fff; font-size: 12px;")
        search_layout.addWidget(QLabel("🔍"))
        search_layout.addWidget(self.searchEdit)
        layout.addLayout(search_layout)

        # Tree view
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setMinimumWidth(200)
        self.tree.setColumnCount(1)
        self.tree.setRootIsDecorated(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        self.tree.setFont(QFont("Consolas", 10))
        self.tree.setIndentation(16)
        self.tree.setStyleSheet("QTreeWidget { background: #181a1b; color: #d4d4d4; border-radius: 3px; } QTreeWidget::item { min-height: 20px; } QTreeWidget::item:selected { background: #3874f2; color: #fff; }")
        layout.addWidget(self.tree)
        self.setLayout(layout)

    def set_file(self, file_path):
        """Load and display the structure of the given file."""
        self.current_file = file_path
        self.load_file(file_path)
        self.fileLabel.setText(os.path.basename(file_path))
        self.pathLabel.setText(file_path)

    def reload_file(self):
        if self.current_file:
            self.set_file(self.current_file)

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
        except Exception as e:
            self.tree.clear()
            self.fileLabel.setText("No file loaded")
            self.pathLabel.setText("")
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
                icon = self.icons.get(item['type'], QIcon())
                node.setIcon(0, icon)
                node.setData(0, Qt.UserRole, item.get('line', 1))
                node.setData(0, Qt.UserRole+1, item)
                parent.addChild(node)
                if 'children' in item and item['children']:
                    add_items(node, item['children'])
        for item in structure:
            text = self.node_text(item)
            root = QTreeWidgetItem([text])
            icon = self.icons.get(item['type'], QIcon())
            root.setIcon(0, icon)
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

    def set_theme(self, theme_data):
        palette = theme_data["palette"]
        editor = theme_data["editor"]
        self.setStyleSheet(f"""
            QWidget {{ background: {palette['window']}; color: {palette['window_text']}; }}
            QLabel {{ color: {palette['window_text']}; }}
            QPushButton {{ background: {palette['button']}; color: {palette['button_text']}; border-radius: 4px; }}
            QPushButton:hover {{ background: {palette['highlight']}; color: {palette['highlight_text']}; }}
            QLineEdit {{ background: {palette['base']}; color: {palette['text']}; border-radius: 4px; }}
            QTreeWidget {{ background: {editor['background']}; color: {editor['foreground']}; alternate-background-color: {palette['alternate_base']}; selection-background-color: {editor['selection_background']}; selection-color: {editor['selection_foreground']}; }}
            QTreeWidget::item:selected {{ background: {palette['highlight']}; color: {palette['highlight_text']}; }}
        """)
        self.tree.setStyleSheet(f"QTreeWidget {{ background: {editor['background']}; color: {editor['foreground']}; alternate-background-color: {palette['alternate_base']}; selection-background-color: {editor['selection_background']}; selection-color: {editor['selection_foreground']}; }}")
        self.searchEdit.setStyleSheet(f"padding: 4px; border-radius: 4px; background: {palette['base']}; color: {palette['text']}; font-size: 12px;")
        self.fileLabel.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {palette['window_text']};")
        self.pathLabel.setStyleSheet(f"color: {palette['text']}; font-size: 11px;")
        self.refreshBtn.setStyleSheet(f"background: {palette['button']}; color: {palette['button_text']}; border-radius: 4px;")

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
