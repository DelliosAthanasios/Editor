import sys
import os
import re
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QFileDialog, QPushButton, QSplitter, QHeaderView,
    QLabel, QHBoxLayout, QMenu, QAction, QMessageBox
)
from PyQt5.QtCore import QFileSystemWatcher, Qt, QPoint
from PyQt5.QtGui import QFont, QColor, QIcon

# --- Code Parsing with types and details ---
class CodeStructureParser:
    def __init__(self, language):
        self.language = language.lower()

    def parse(self, code):
        if self.language == "python":
            return self._parse_python(code)
        elif self.language in ("c", "cpp", "c++"):
            return self._parse_c_cpp(code)
        elif self.language == "java":
            return self._parse_java(code)
        else:
            return []

    def _parse_python(self, code):
        tree = []
        class_pattern = re.compile(r"^\s*class\s+(\w+)(\(.*\))?:")
        func_pattern = re.compile(r"^\s*def\s+(\w+)\s*\((.*?)\)")
        variable_pattern = re.compile(r"^\s*(\w+)\s*[:=]\s*([^=]*)")
        type_hint_pattern = re.compile(r"^\s*(\w+)\s*:\s*([\w\[\], ]+)")
        lines = code.splitlines()
        parents = []
        for idx, line in enumerate(lines):
            class_match = class_pattern.match(line)
            func_match = func_pattern.match(line)
            var_match = variable_pattern.match(line)
            type_hint_match = type_hint_pattern.match(line)
            indent = len(line) - len(line.lstrip())
            if class_match:
                class_name = class_match.group(1)
                node = {'type': 'class', 'name': class_name, 'children': [], 'line': idx+1}
                parents = [node]
                tree.append(node)
            elif func_match:
                func_name = func_match.group(1)
                params = func_match.group(2)
                param_str = params.replace("self,", "").replace("self", "")
                param_str = param_str.strip()
                node = {
                    'type': 'function',
                    'name': func_name,
                    'params': param_str,
                    'children': [],
                    'line': idx+1
                }
                if parents and indent > 0:
                    parents[-1]['children'].append(node)
                else:
                    tree.append(node)
            elif var_match:
                var_name = var_match.group(1)
                var_type = ""
                if type_hint_match:
                    var_type = type_hint_match.group(2).strip()
                node = {
                    'type': 'variable',
                    'name': var_name,
                    'vtype': var_type,
                    'line': idx+1
                }
                if parents and indent > 0:
                    parents[-1]['children'].append(node)
                else:
                    tree.append(node)
        return tree

    def _parse_c_cpp(self, code):
        tree = []
        class_pattern = re.compile(r"^\s*(class|struct)\s+(\w+)")
        func_pattern = re.compile(r"^\s*([\w\<\>\*\&\s]+)\s+(\w+)\s*\(([^)]*)\)\s*\{?")
        var_pattern = re.compile(r"^\s*([\w\<\>\*\&]+)\s+(\w+)\s*(=\s*[^;]+)?;")
        lines = code.splitlines()
        current_class = None
        inside_class = False
        for idx, line in enumerate(lines):
            class_match = class_pattern.match(line)
            func_match = func_pattern.match(line)
            var_match = var_pattern.match(line)
            if class_match:
                class_name = class_match.group(2)
                node = {'type': 'class', 'name': class_name, 'children': [], 'line': idx+1}
                tree.append(node)
                current_class = node
                inside_class = True
            elif func_match:
                ret_type = func_match.group(1).strip()
                func_name = func_match.group(2)
                params = func_match.group(3).strip()
                node = {
                    'type': 'function',
                    'name': func_name,
                    'ret_type': ret_type,
                    'params': params,
                    'children': [],
                    'line': idx+1
                }
                if inside_class and current_class:
                    current_class['children'].append(node)
                else:
                    tree.append(node)
            elif var_match:
                var_type = var_match.group(1).strip()
                var_name = var_match.group(2)
                node = {
                    'type': 'variable',
                    'name': var_name,
                    'vtype': var_type,
                    'line': idx+1
                }
                if inside_class and current_class:
                    current_class['children'].append(node)
                else:
                    tree.append(node)
            if "};" in line:
                inside_class = False
                current_class = None
        return tree

    def _parse_java(self, code):
        tree = []
        class_pattern = re.compile(r"^\s*(public\s+)?(class|interface)\s+(\w+)")
        func_pattern = re.compile(r"^\s*(public|protected|private|static|\s)+([\w\<\>\[\]]+)\s+(\w+)\s*\(([^)]*)\)\s*\{?")
        var_pattern = re.compile(r"^\s*(public|protected|private|static|\s)+([\w\<\>\[\]]+)\s+(\w+)\s*(=\s*[^;]+)?;")
        lines = code.splitlines()
        current_class = None
        inside_class = False
        for idx, line in enumerate(lines):
            class_match = class_pattern.match(line)
            func_match = func_pattern.match(line)
            var_match = var_pattern.match(line)
            if class_match:
                class_name = class_match.group(3)
                node = {'type': 'class', 'name': class_name, 'children': [], 'line': idx+1}
                tree.append(node)
                current_class = node
                inside_class = True
            elif func_match:
                ret_type = func_match.group(2).strip()
                func_name = func_match.group(3)
                params = func_match.group(4).strip()
                node = {
                    'type': 'function',
                    'name': func_name,
                    'ret_type': ret_type,
                    'params': params,
                    'children': [],
                    'line': idx+1
                }
                if inside_class and current_class:
                    current_class['children'].append(node)
                else:
                    tree.append(node)
            elif var_match:
                var_type = var_match.group(2)
                var_name = var_match.group(3)
                node = {
                    'type': 'variable',
                    'name': var_name,
                    'vtype': var_type,
                    'line': idx+1
                }
                if inside_class and current_class:
                    current_class['children'].append(node)
                else:
                    tree.append(node)
            if "}" in line and inside_class:
                inside_class = False
                current_class = None
        return tree

# --- UI ---
class CodeExplorerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QWidget {
                background: #23272e;
                color: #d4d4d4;
                font-size: 12px;
            }
            QTreeWidget {
                border-radius: 6px;
                border: 1px solid #333;
                background: #23272e;
                alternate-background-color: #2d323a;
                font-size: 13px;
                show-decoration-selected: 1;
            }
            QHeaderView::section {
                background: #23272e;
                color: #a0a0a0;
                border: none;
            }
            QTreeWidget::item:selected {
                background: #3874f2;
                color: #fff;
            }
            QPushButton {
                background: #3874f2;
                color: #fff;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover { background: #1e90ff; }
            QLabel { color: #fff; font-size: 14px; }
        """)
        layout = QVBoxLayout(self)
        # Info Bar
        infoLayout = QHBoxLayout()
        self.fileLabel = QLabel("No file loaded")
        infoLayout.addWidget(self.fileLabel)
        self.openBtn = QPushButton("Open File")
        self.openBtn.setMaximumWidth(100)
        self.openBtn.clicked.connect(self.open_file)
        infoLayout.addWidget(self.openBtn)
        infoLayout.addStretch()
        layout.addLayout(infoLayout)
        # File Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['Code Explorer'])
        self.tree.setAlternatingRowColors(True)
        self.tree.setMinimumWidth(220)
        self.tree.setMaximumWidth(420)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        self.tree.setFont(QFont("Consolas", 11))
        self.tree.header().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.tree)
        self.setLayout(layout)
        self.file_watcher = QFileSystemWatcher()
        self.file_watcher.fileChanged.connect(self.reload_file)
        self.current_file = None
        self.current_language = "python"
        self.structure = []

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
                if item['type'] == 'class':
                    icon = "📦"
                    text = f"{icon} class {item['name']} (Ln {item['line']})"
                elif item['type'] == 'function':
                    icon = "ƒ"
                    params = item.get('params', "")
                    ret_type = item.get('ret_type', "")
                    if ret_type:
                        text = f"{icon} {item['name']}({params}) : {ret_type} (Ln {item['line']})"
                    else:
                        text = f"{icon} {item['name']}({params}) (Ln {item['line']})"
                elif item['type'] == 'variable':
                    icon = "𝑥"
                    vtype = item.get('vtype', "")
                    if vtype:
                        text = f"{icon} {item['name']}: {vtype} (Ln {item['line']})"
                    else:
                        text = f"{icon} {item['name']} (Ln {item['line']})"
                else:
                    text = item['name']
                node = QTreeWidgetItem([text])
                node.setData(0, Qt.UserRole, item.get('line', 1))
                node.setData(0, Qt.UserRole+1, item)
                parent.addChild(node)
                if 'children' in item and item['children']:
                    add_items(node, item['children'])
        for item in structure:
            if item['type'] == 'class':
                icon = "📦"
                text = f"{icon} class {item['name']} (Ln {item['line']})"
            elif item['type'] == 'function':
                icon = "ƒ"
                params = item.get('params', "")
                ret_type = item.get('ret_type', "")
                if ret_type:
                    text = f"{icon} {item['name']}({params}) : {ret_type} (Ln {item['line']})"
                else:
                    text = f"{icon} {item['name']}({params}) (Ln {item['line']})"
            elif item['type'] == 'variable':
                icon = "𝑥"
                vtype = item.get('vtype', "")
                if vtype:
                    text = f"{icon} {item['name']}: {vtype} (Ln {item['line']})"
                else:
                    text = f"{icon} {item['name']} (Ln {item['line']})"
            else:
                text = item['name']
            root = QTreeWidgetItem([text])
            root.setData(0, Qt.UserRole, item.get('line', 1))
            root.setData(0, Qt.UserRole+1, item)
            self.tree.addTopLevelItem(root)
            if 'children' in item and item['children']:
                add_items(root, item['children'])
        self.tree.expandAll()

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

class CodeExplorer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Code Explorer")
        self.setGeometry(100, 100, 420, 640)
        self.setCentralWidget(CodeExplorerWidget())
        self.setWindowIconVisible = False
        self.setStyleSheet("QMainWindow{border-radius:12px;}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CodeExplorer()
    window.show()
    sys.exit(app.exec_())