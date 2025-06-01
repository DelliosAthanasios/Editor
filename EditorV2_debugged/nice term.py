# -*- coding: utf-8 -*-
import os
import sys
import json
from functools import partial
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QSplitter,
    QTextEdit, QTreeView, QFileSystemModel, QDialog,
    QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton, QMessageBox,
    QFileDialog, QStyleFactory, QToolBar, QDialogButtonBox, 
    QTabBar, QComboBox, QLabel, QLineEdit, QFormLayout
)
from PyQt5.QtCore import Qt, QProcess, QEvent, QPoint, QSize
from PyQt5.QtGui import QFont, QColor, QTextCursor, QTextCharFormat, QSyntaxHighlighter, QMouseEvent

# Configuration
SETTINGS = {
    "bg": "#2d2d2d",
    "fg": "#cccccc",
    "prompt_color": "#1e90ff",
    "stderr_color": "#ff4444",
    "font": QFont("Cascadia Mono", 10),
    "session_file": ".terminal_session.json",
}

class Workspace:
    def __init__(self, path):
        self.path = path
        self.session_file = str(Path(path) / SETTINGS["session_file"])

class TerminalHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.prompt_format = QTextCharFormat()
        self.prompt_format.setForeground(QColor(SETTINGS["prompt_color"]))
        self.error_format = QTextCharFormat()
        self.error_format.setForeground(QColor(SETTINGS["stderr_color"]))
        
    def highlightBlock(self, text):
        if text.startswith(("$ ", "> ", "PS ")):
            self.setFormat(0, len(text), self.prompt_format)
        elif any(e in text.lower() for e in ["error", "fail"]):
            self.setFormat(0, len(text), self.error_format)

class ClosableWidget(QWidget):
    def __init__(self, content_widget, parent=None):
        super().__init__(parent)
        self.content = content_widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.close_btn = QPushButton("×")
        self.close_btn.setStyleSheet("""
            QPushButton {
                color: #ff4444;
                font-weight: bold;
                border: none;
                padding: 0px 3px;
            }
            QPushButton:hover { background-color: #3a3a3a; }
        """)
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.clicked.connect(self.deleteLater)
        
        layout.addWidget(self.close_btn, alignment=Qt.AlignRight)
        layout.addWidget(self.content)

class TerminalPane(QWidget):
    def __init__(self, workspace, parent=None):
        super().__init__(parent)
        self.workspace = workspace
        self.history = []
        self.history_index = 0
        self.active_processes = {}
        self.current_prompt = ""
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        control_bar = QHBoxLayout()
        self.term_type = QComboBox()
        self.term_type.addItems(["cmd", "powershell", "bash"])
        control_bar.addWidget(self.term_type)
        layout.addLayout(control_bar)
        
        self.output = QTextEdit()
        self.output.setReadOnly(False)
        self.output.setStyleSheet(f"""
            background-color: {SETTINGS['bg']};
            color: {SETTINGS['fg']};
            border: none;
            padding: 5px;
        """)
        self.output.setFont(SETTINGS["font"])
        self.output.installEventFilter(self)
        TerminalHighlighter(self.output.document())
        layout.addWidget(self.output)
        
        self.load_session()
        self.show_prompt()

    def eventFilter(self, obj, event):
        if obj == self.output and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.execute_command()
                return True
            elif event.key() == Qt.Key_Up:
                self.navigate_history(-1)
                return True
            elif event.key() == Qt.Key_Down:
                self.navigate_history(1)
                return True
            elif event.key() == Qt.Key_Backspace:
                cursor = self.output.textCursor()
                pos = cursor.position()
                if pos > self.output.document().lastBlock().position() + len(self.current_prompt):
                    return False
                else:
                    return True
        return super().eventFilter(obj, event)
        
    def navigate_history(self, delta):
        if self.history:
            self.history_index = max(0, min(self.history_index + delta, len(self.history)-1))
            self.replace_input(self.history[self.history_index])
            
    def replace_input(self, text):
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.insertText(self.current_prompt + text)
        self.output.setTextCursor(cursor)
    
    def show_prompt(self):
        mode = self.term_type.currentText()
        prompts = {
            "cmd": f"{os.path.basename(self.workspace.path)}> ",
            "powershell": f"PS {os.path.basename(self.workspace.path)}> ",
            "bash": f"{os.path.basename(self.workspace.path)}$ "
        }
        self.current_prompt = prompts[mode]
        self.output.setTextColor(QColor(SETTINGS["prompt_color"]))
        self.output.append(self.current_prompt)
        self.move_cursor_to_end()
    
    def move_cursor_to_end(self):
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.output.setTextCursor(cursor)
    
    def get_current_input(self):
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.LineUnderCursor)
        line = cursor.selectedText().replace(self.current_prompt, "", 1)
        return line.strip()
    
    def execute_command(self):
        cmd = self.get_current_input()
        if not cmd:
            self.show_prompt()
            return
            
        self.history.append(cmd)
        self.history_index = len(self.history)
        mode = self.term_type.currentText()
        
        proc = QProcess()
        proc.setWorkingDirectory(self.workspace.path)
        
        if mode == "cmd":
            proc.start("cmd", ["/c", cmd])
        elif mode == "powershell":
            proc.start("powershell", ["-Command", cmd])
        elif mode == "bash":
            proc.start("bash", ["-c", cmd])
        
        proc.readyReadStandardOutput.connect(lambda: self.handle_stdout(proc))
        proc.readyReadStandardError.connect(lambda: self.handle_stderr(proc))
        proc.finished.connect(lambda: self.process_finished(proc))
        self.active_processes[proc.processId()] = proc
    
    def handle_stdout(self, proc):
        data = proc.readAllStandardOutput().data().decode()
        self.output.setTextColor(QColor(SETTINGS["fg"]))
        self.output.insertPlainText(data)
        self.move_cursor_to_end()
    
    def handle_stderr(self, proc):
        data = proc.readAllStandardError().data().decode()
        self.output.setTextColor(QColor(SETTINGS["stderr_color"]))
        self.output.insertPlainText(data)
        self.move_cursor_to_end()
    
    def process_finished(self, proc):
        self.active_processes.pop(proc.processId(), None)
        self.show_prompt()
    
    def save_session(self):
        full_text = self.output.toPlainText()
        if full_text.endswith(self.current_prompt):
            full_text = full_text[:-len(self.current_prompt)]
        session = {
            "history": self.history,
            "output": full_text,
        }
        with open(self.workspace.session_file, "w") as f:
            json.dump(session, f)
    
    def load_session(self):
        try:
            with open(self.workspace.session_file, "r") as f:
                session = json.load(f)
                self.history = session.get("history", [])
                self.output.setPlainText(session.get("output", ""))
        except FileNotFoundError:
            pass
    
    def closeEvent(self, event):
        self.save_session()
        super().closeEvent(event)

class SplitPreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.split_rect = None
        self.split_direction = Qt.Horizontal
        self.click_pos = None

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.split_rect:
            painter.setPen(QColor("#1e90ff"))
            painter.drawRect(self.split_rect)

    def mousePressEvent(self, event):
        self.click_pos = event.pos()
        self.update()

class TerminalApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modern Terminal")
        self.setGeometry(100, 100, 1138, 624)
        self.setup_ui()
        self.create_toolbar()
        self.add_tab()

    def setup_ui(self):
        self.setStyleSheet(f"""
            background-color: {SETTINGS['bg']};
            color: {SETTINGS['fg']};
            QTabBar::close-button {{ image: url(close.svg); }}
            QTabBar::tab {{ 
                background: #3a3a3a; 
                color: {SETTINGS['fg']}; 
                padding: 8px;
            }}
        """)
        
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)
        self.panels = {"file": True, "term": True}

    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setStyleSheet("QToolBar { background-color: #2d2d2d; }")
        
        actions = [
            ("➕ New Tab", self.add_tab),
            ("✂ Split", self.show_split_dialog),
            ("⚙ Settings", self.show_settings),
        ]
        
        for text, callback in actions:
            btn = QPushButton(text)
            btn.clicked.connect(callback)
            toolbar.addWidget(btn)
        
        self.addToolBar(toolbar)

    def show_split_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Split Configuration")
        layout = QVBoxLayout(dialog)
        
        # Split direction selection
        self.split_dir = QComboBox()
        self.split_dir.addItems(["Horizontal", "Vertical"])
        
        # Size input
        self.size_input = QLineEdit()
        self.size_input.setPlaceholderText("Optional size in pixels")
        
        form = QFormLayout()
        form.addRow("Direction:", self.split_dir)
        form.addRow("Size:", self.size_input)
        layout.addLayout(form)
        
        # Preview area
        self.preview = QLabel("Click on the tab area where you want to split")
        self.preview.setFixedSize(400, 300)
        self.preview.setStyleSheet("background-color: #3a3a3a;")
        layout.addWidget(self.preview)
        
        # Confirmation buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: self.apply_split(dialog))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.exec_()

    def apply_split(self, dialog):
        direction = Qt.Horizontal if self.split_dir.currentText() == "Horizontal" else Qt.Vertical
        size_text = self.size_input.text()
        
        try:
            split_size = int(size_text) if size_text else None
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid size value")
            return
        
        current_tab = self.tabs.currentWidget()
        if not current_tab:
            return
        
        # Find the deepest splitter
        splitter = self.find_deepest_splitter(current_tab)
        if not splitter:
            splitter = QSplitter(direction)
            current_tab.layout().addWidget(splitter)
            splitter.addWidget(self.create_pane(splitter))
        
        new_pane = self.create_pane(splitter)
        
        if direction == Qt.Horizontal:
            splitter.setOrientation(Qt.Horizontal)
            splitter.addWidget(new_pane)
        else:
            splitter.setOrientation(Qt.Vertical)
            splitter.addWidget(new_pane)
        
        if split_size:
            total = splitter.orientation() == Qt.Horizontal and splitter.width() or splitter.height()
            sizes = [total - split_size, split_size]
            splitter.setSizes(sizes)
        
        dialog.accept()

    def find_deepest_splitter(self, widget):
        if isinstance(widget, QSplitter):
            for i in range(widget.count()):
                child = widget.widget(i)
                result = self.find_deepest_splitter(child)
                if result: return result
            return widget
        return None

    def create_pane(self, parent):
        path = getattr(parent, 'workspace_path', QFileDialog.getExistingDirectory(self, "Select Workspace"))
        splitter = QSplitter(Qt.Horizontal)
        
        if self.panels["file"]:
            file_tree = QTreeView()
            model = QFileSystemModel()
            model.setRootPath(path)
            file_tree.setModel(model)
            file_tree.setRootIndex(model.index(path))
            file_tree.clicked.connect(lambda idx: self.on_file_selected(idx, splitter))
            closable_file = ClosableWidget(file_tree)
            splitter.addWidget(closable_file)
        
        terminal = TerminalPane(Workspace(path))
        closable_terminal = ClosableWidget(terminal)
        splitter.addWidget(closable_terminal)
        splitter.workspace_path = path
        
        return splitter

    def add_tab(self):
        path = QFileDialog.getExistingDirectory(self, "Select Workspace")
        if not path:
            return
        
        pane = self.create_pane(None)
        self.tabs.addTab(pane, os.path.basename(path))
        self.tabs.setCurrentIndex(self.tabs.count()-1)

    def close_tab(self, index):
        if widget := self.tabs.widget(index):
            widget.deleteLater()
        self.tabs.removeTab(index)

    def on_file_selected(self, index, pane):
        path = self.sender().model().filePath(index)
        if os.path.isfile(path) and hasattr(pane, 'terminal'):
            with open(path, 'r', encoding='utf-8') as f:
                pane.terminal.output.setText(f.read())

    def show_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        layout = QVBoxLayout(dialog)
        
        checkboxes = {}
        for name, label in [("file", "File Tree"), ("term", "Terminal")]:
            cb = QCheckBox(label)
            cb.setChecked(self.panels[name])
            cb.toggled.connect(partial(self.update_panel, name))
            layout.addWidget(cb)
            checkboxes[name] = cb
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            for name in self.panels:
                self.panels[name] = checkboxes[name].isChecked()
            self.update_ui()

    def update_panel(self, name, state):
        self.panels[name] = state
        self.update_ui()

    def update_ui(self):
        for i in range(self.tabs.count()):
            pane = self.tabs.widget(i)
            if pane:
                for file_tree in pane.findChildren(QTreeView):
                    file_tree.setVisible(self.panels["file"])
                for terminal in pane.findChildren(TerminalPane):
                    terminal.setVisible(self.panels["term"])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    window = TerminalApp()
    window.show()
    sys.exit(app.exec_())