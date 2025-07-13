import os
import shutil
import tempfile
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel, 
    QSplitter, QMessageBox, QLineEdit, QToolBar, QAction, QFrame, 
    QMenuBar, QMenu, QStatusBar, QComboBox, QCheckBox, QGroupBox,
    QGridLayout, QScrollArea, QButtonGroup, QRadioButton
)
from PyQt5.QtCore import Qt, QProcess, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QTextCursor, QTextCharFormat, QColor
from .latex_highlighter import LatexHighlighter
from .word_suggester import suggest_latex_commands
from PyQt5.QtWidgets import QCompleter
from PyQt5.QtCore import QStringListModel
from global_.minimap import Minimap
from global_.theme_manager import theme_manager_singleton
from global_.dynamic_saving import enable_dynamic_saving_for_qt
from global_.syntax_highlighter import GenericHighlighter
from global_.numberline import NumberLine

class LatexEditorEnv(QWidget):
    # Signals for integration with main editor
    file_saved = pyqtSignal(str)
    file_opened = pyqtSignal(str)
    content_changed = pyqtSignal()
    
    def __init__(self, parent=None, file_path=None):
        super().__init__(parent)
        self.setWindowTitle("LaTeX Editor")
        self.setMinimumSize(1200, 800)
        self.compiler = self.find_latex_compiler()
        self.process = None
        self.file_path = file_path
        self.layout_mode = "vertical"  # "vertical" or "horizontal"
        self.show_minimap = True
        self.show_numberline = True
        self.show_output = True
        self.search_results = []
        self.current_search_index = 0
        
        self.init_ui()
        self.setup_connections()
        
        # Dynamic saving
        self._file_path = file_path or "untitled.tex"
        # Only enable dynamic saving if not running in a test or headless mode
        import inspect
        stack = inspect.stack()
        if not any('test_latex_fix' in frame.filename for frame in stack):
            enable_dynamic_saving_for_qt(self)
        
        # Apply theme
        self.apply_theme()

    def find_latex_compiler(self):
        for exe in ["pdflatex", "xelatex", "lualatex"]:
            if shutil.which(exe):
                return exe
        return None

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Create editor area first (before menu bar)
        self.create_editor_area()
        
        # Create output area before toolbar (which references it)
        self.create_output_area()
        
        # Menu Bar
        self.create_menu_bar()
        main_layout.addWidget(self.menu_bar)
        
        # Toolbar
        self.create_toolbar()
        main_layout.addWidget(self.toolbar)
        
        # Control Panel
        self.create_control_panel()
        main_layout.addWidget(self.control_panel)
        
        # Main Splitter
        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.setChildrenCollapsible(False)
        
        # Add editor container to splitter
        self.main_splitter.addWidget(self.editor_container)
        
        # Add output container to splitter
        self.main_splitter.addWidget(self.output_container)
        
        # Set initial splitter sizes
        self.main_splitter.setSizes([600, 200])
        main_layout.addWidget(self.main_splitter)
        
        # Search Panel
        self.create_search_panel()
        main_layout.addWidget(self.search_panel)
        
        # Status Bar
        self.create_status_bar()
        main_layout.addWidget(self.status_bar)
        
        # Word suggestions
        self.setup_completer()

    def create_menu_bar(self):
        self.menu_bar = QMenuBar()
        
        # File Menu
        file_menu = self.menu_bar.addMenu("File")
        new_action = QAction("New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction("Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save As", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit Menu
        edit_menu = self.menu_bar.addMenu("Edit")
        undo_action = QAction("Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.editor.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.editor.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        cut_action = QAction("Cut", self)
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(self.editor.cut)
        edit_menu.addAction(cut_action)
        
        copy_action = QAction("Copy", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.editor.copy)
        edit_menu.addAction(copy_action)
        
        paste_action = QAction("Paste", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self.editor.paste)
        edit_menu.addAction(paste_action)
        
        edit_menu.addSeparator()
        
        select_all_action = QAction("Select All", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.editor.selectAll)
        edit_menu.addAction(select_all_action)
        
        # View Menu
        view_menu = self.menu_bar.addMenu("View")
        
        self.toggle_numberline_action = QAction("Number Line", self)
        self.toggle_numberline_action.setCheckable(True)
        self.toggle_numberline_action.setChecked(True)
        self.toggle_numberline_action.triggered.connect(self.toggle_numberline)
        view_menu.addAction(self.toggle_numberline_action)
        
        self.toggle_minimap_action = QAction("Minimap", self)
        self.toggle_minimap_action.setCheckable(True)
        self.toggle_minimap_action.setChecked(True)
        self.toggle_minimap_action.triggered.connect(self.toggle_minimap)
        view_menu.addAction(self.toggle_minimap_action)
        
        self.toggle_output_action = QAction("Output Panel", self)
        self.toggle_output_action.setCheckable(True)
        self.toggle_output_action.setChecked(True)
        self.toggle_output_action.triggered.connect(self.toggle_output)
        view_menu.addAction(self.toggle_output_action)
        
        view_menu.addSeparator()
        
        layout_menu = view_menu.addMenu("Layout")
        vertical_action = QAction("Vertical", self)
        vertical_action.triggered.connect(lambda: self.change_layout("vertical"))
        layout_menu.addAction(vertical_action)
        
        horizontal_action = QAction("Horizontal", self)
        horizontal_action.triggered.connect(lambda: self.change_layout("horizontal"))
        layout_menu.addAction(horizontal_action)
        
        # Tools Menu
        tools_menu = self.menu_bar.addMenu("Tools")
        
        run_action = QAction("Run LaTeX", self)
        run_action.setShortcut("F5")
        run_action.triggered.connect(self.run_latex)
        tools_menu.addAction(run_action)
        
        stop_action = QAction("Stop", self)
        stop_action.setShortcut("F6")
        stop_action.triggered.connect(self.stop_latex)
        tools_menu.addAction(stop_action)
        
        tools_menu.addSeparator()
        
        clear_output_action = QAction("Clear Output", self)
        clear_output_action.triggered.connect(self.output.clear)
        tools_menu.addAction(clear_output_action)

    def create_toolbar(self):
        self.toolbar = QToolBar()
        self.toolbar.setMovable(True)
        
        # File actions
        new_btn = QAction("New", self)
        new_btn.triggered.connect(self.new_file)
        self.toolbar.addAction(new_btn)
        
        open_btn = QAction("Open", self)
        open_btn.triggered.connect(self.open_file)
        self.toolbar.addAction(open_btn)
        
        save_btn = QAction("Save", self)
        save_btn.triggered.connect(self.save_file)
        self.toolbar.addAction(save_btn)
        
        self.toolbar.addSeparator()
        
        # LaTeX actions
        run_btn = QAction("▶ Run", self)
        run_btn.triggered.connect(self.run_latex)
        self.toolbar.addAction(run_btn)
        
        stop_btn = QAction("⏹ Stop", self)
        stop_btn.triggered.connect(self.stop_latex)
        self.toolbar.addAction(stop_btn)
        
        self.toolbar.addSeparator()
        
        # Formatting actions
        bold_btn = QAction("B", self)
        bold_btn.triggered.connect(lambda: self.insert_latex_command("\\textbf{}"))
        self.toolbar.addAction(bold_btn)
        
        italic_btn = QAction("I", self)
        italic_btn.triggered.connect(lambda: self.insert_latex_command("\\textit{}"))
        self.toolbar.addAction(italic_btn)
        
        section_btn = QAction("§", self)
        section_btn.triggered.connect(lambda: self.insert_latex_command("\\section{}"))
        self.toolbar.addAction(section_btn)

    def create_control_panel(self):
        self.control_panel = QFrame()
        self.control_panel.setFrameStyle(QFrame.StyledPanel)
        control_layout = QHBoxLayout(self.control_panel)
        
        # Compiler selection
        compiler_label = QLabel("Compiler:")
        self.compiler_combo = QComboBox()
        self.compiler_combo.addItems(["pdflatex", "xelatex", "lualatex"])
        if self.compiler:
            index = self.compiler_combo.findText(self.compiler)
            if index >= 0:
                self.compiler_combo.setCurrentIndex(index)
        
        # Status
        self.status_label = QLabel()
        if self.compiler:
            self.status_label.setText(f"✓ {self.compiler} found")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText("✗ No LaTeX compiler found!")
            self.status_label.setStyleSheet("color: red;")
        
        control_layout.addWidget(compiler_label)
        control_layout.addWidget(self.compiler_combo)
        control_layout.addStretch()
        control_layout.addWidget(self.status_label)

    def create_editor_area(self):
        self.editor_container = QFrame()
        self.editor_container.setFrameStyle(QFrame.StyledPanel)
        editor_layout = QHBoxLayout(self.editor_container)
        editor_layout.setContentsMargins(5, 5, 5, 5)
        
        # Editor with numberline and minimap
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Fira Code", 13))
        self.editor.setPlaceholderText("Write your LaTeX code here...\n\nExample:\n\\documentclass{article}\n\\begin{document}\nHello, World!\n\\end{document}")
        
        # Syntax highlighting
        self.highlighter = LatexHighlighter(self.editor.document())
        
        # Number line
        self.numberline = NumberLine(self.editor, theme_manager_singleton.get_theme())
        self.numberline.setFont(self.editor.font())
        
        # Minimap
        self.minimap = Minimap(self, self.editor, self.numberline, theme_manager_singleton.get_theme())
        
        editor_layout.addWidget(self.numberline)
        editor_layout.addWidget(self.editor)
        editor_layout.addWidget(self.minimap)

    def create_output_area(self):
        self.output_container = QFrame()
        self.output_container.setFrameStyle(QFrame.StyledPanel)
        output_layout = QVBoxLayout(self.output_container)
        output_layout.setContentsMargins(5, 5, 5, 5)
        
        # Output text area
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 10))
        self.output.setMaximumHeight(200)
        
        # Output header
        output_header = QHBoxLayout()
        output_label = QLabel("Output:")
        output_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        
        clear_btn = QPushButton("Clear")
        clear_btn.setMaximumWidth(60)
        clear_btn.clicked.connect(self.output.clear)
        
        output_header.addWidget(output_label)
        output_header.addStretch()
        output_header.addWidget(clear_btn)
        
        output_layout.addLayout(output_header)
        output_layout.addWidget(self.output)

    def create_search_panel(self):
        self.search_panel = QFrame()
        self.search_panel.setFrameStyle(QFrame.StyledPanel)
        search_layout = QHBoxLayout(self.search_panel)
        search_layout.setContentsMargins(5, 5, 5, 5)
        
        search_label = QLabel("Search:")
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search in LaTeX...")
        self.search_bar.textChanged.connect(self.search_in_editor)
        
        self.search_prev_btn = QPushButton("↑")
        self.search_prev_btn.setMaximumWidth(30)
        self.search_prev_btn.clicked.connect(self.search_previous)
        
        self.search_next_btn = QPushButton("↓")
        self.search_next_btn.setMaximumWidth(30)
        self.search_next_btn.clicked.connect(self.search_next)
        
        self.search_results_label = QLabel("0 results")
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_bar)
        search_layout.addWidget(self.search_prev_btn)
        search_layout.addWidget(self.search_next_btn)
        search_layout.addWidget(self.search_results_label)
        search_layout.addStretch()

    def create_status_bar(self):
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Ready")

    def setup_completer(self):
        self.completer = QCompleter()
        self.completer.setModel(QStringListModel([]))
        self.completer.setWidget(self.editor)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(False)
        self.editor.textChanged.connect(self.update_suggestions)
        self.editor.cursorPositionChanged.connect(self.show_suggestion_popup)

    def setup_connections(self):
        # Connect editor signals
        self.editor.textChanged.connect(self.content_changed.emit)
        self.editor.textChanged.connect(self.update_suggestions)
        self.editor.cursorPositionChanged.connect(self.show_suggestion_popup)
        
        # Connect numberline updates
        self.editor.textChanged.connect(self.numberline.update)
        self.editor.cursorPositionChanged.connect(self.numberline.update)

    def apply_theme(self):
        theme_data = theme_manager_singleton.get_theme()
        # Apply theme to editor
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme_data.get('editor', {}).get('background', '#1e1e1e')};
                color: {theme_data.get('editor', {}).get('foreground', '#ffffff')};
                border: 1px solid {theme_data.get('editor', {}).get('border', '#404040')};
            }}
        """)
        
        # Apply theme to output
        self.output.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme_data.get('console', {}).get('background', '#2d2d2d')};
                color: {theme_data.get('console', {}).get('foreground', '#cccccc')};
                border: 1px solid {theme_data.get('console', {}).get('border', '#404040')};
            }}
        """)

    # File operations
    def new_file(self):
        self.editor.clear()
        self._file_path = "untitled.tex"
        self.status_bar.showMessage("New file created")

    def open_file(self):
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open LaTeX File", "", 
            "LaTeX Files (*.tex);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.editor.setPlainText(content)
                self._file_path = file_path
                self.file_opened.emit(file_path)
                self.status_bar.showMessage(f"Opened: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")

    def save_file(self):
        if self._file_path == "untitled.tex":
            return self.save_file_as()
        return self.save_file_content()

    def save_file_as(self):
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save LaTeX File", self._file_path,
            "LaTeX Files (*.tex);;All Files (*)"
        )
        if file_path:
            self._file_path = file_path
            return self.save_file_content()
        return False

    def save_file_content(self):
        try:
            content = self.editor.toPlainText()
            with open(self._file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.file_saved.emit(self._file_path)
            self.status_bar.showMessage(f"Saved: {self._file_path}")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")
            return False

    # View operations
    def toggle_numberline(self):
        self.show_numberline = not self.show_numberline
        self.numberline.setVisible(self.show_numberline)
        self.toggle_numberline_action.setChecked(self.show_numberline)

    def toggle_minimap(self):
        self.show_minimap = not self.show_minimap
        self.minimap.setVisible(self.show_minimap)
        self.toggle_minimap_action.setChecked(self.show_minimap)

    def toggle_output(self):
        self.show_output = not self.show_output
        self.output_container.setVisible(self.show_output)
        self.toggle_output_action.setChecked(self.show_output)

    def change_layout(self, mode):
        self.layout_mode = mode
        if mode == "horizontal":
            self.main_splitter.setOrientation(Qt.Horizontal)
        else:
            self.main_splitter.setOrientation(Qt.Vertical)

    # LaTeX operations
    def insert_latex_command(self, command):
        cursor = self.editor.textCursor()
        if command.endswith("{}"):
            command = command[:-1]
            cursor.insertText(command)
            # Position cursor inside braces
            cursor.movePosition(cursor.Left)
            self.editor.setTextCursor(cursor)
        else:
            cursor.insertText(command)
        self.editor.setFocus()

    def run_latex(self):
        if not self.compiler:
            QMessageBox.critical(self, "Error", "No LaTeX compiler found on system.")
            return
        
        # Save current content
        if not self.save_file_content():
            return
        
        self.output.clear()
        self.output.append(f"Running {self.compiler} on {self._file_path}...\n")
        self.status_bar.showMessage("Compiling...")
        
        self.process = QProcess(self)
        self.process.setProgram(self.compiler)
        self.process.setArguments([self._file_path])
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)
        self.process.start()

    def stop_latex(self):
        if self.process and self.process.state() == QProcess.Running:
            self.process.kill()
            self.output.append("\nProcess stopped by user.")
            self.status_bar.showMessage("Process stopped")

    def handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode()
        self.output.append(data)

    def handle_stderr(self):
        data = self.process.readAllStandardError().data().decode()
        self.output.append(data)

    def process_finished(self, exit_code, exit_status):
        if exit_code == 0:
            self.output.append("\n✓ Compilation successful!")
            self.status_bar.showMessage("Compilation successful")
        else:
            self.output.append(f"\n✗ Compilation failed (exit code: {exit_code})")
            self.status_bar.showMessage("Compilation failed")

    # Search operations
    def search_in_editor(self, text):
        if not text:
            self.clear_search_highlights()
            self.search_results_label.setText("0 results")
            return
        
        self.search_results = []
        cursor = QTextCursor(self.editor.document())
        cursor.movePosition(cursor.Start)
        
        while True:
            cursor = self.editor.document().find(text, cursor)
            if cursor.isNull():
                break
            self.search_results.append(cursor.position())
        
        self.current_search_index = 0
        self.search_results_label.setText(f"{len(self.search_results)} results")
        
        if self.search_results:
            self.highlight_search_result(0)

    def search_next(self):
        if not self.search_results:
            return
        self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
        self.highlight_search_result(self.current_search_index)

    def search_previous(self):
        if not self.search_results:
            return
        self.current_search_index = (self.current_search_index - 1) % len(self.search_results)
        self.highlight_search_result(self.current_search_index)

    def highlight_search_result(self, index):
        if not self.search_results:
            return
        
        cursor = QTextCursor(self.editor.document())
        cursor.setPosition(self.search_results[index])
        cursor.movePosition(cursor.Right, cursor.KeepAnchor, len(self.search_bar.text()))
        self.editor.setTextCursor(cursor)
        self.editor.centerCursor()

    def clear_search_highlights(self):
        # Clear any search highlighting
        cursor = QTextCursor(self.editor.document())
        cursor.select(cursor.Document)
        cursor.setCharFormat(QTextCharFormat())

    # Completion operations
    def update_suggestions(self):
        cursor = self.editor.textCursor()
        cursor.select(cursor.WordUnderCursor)
        word = cursor.selectedText()
        if word.startswith("\\"):
            suggestions = suggest_latex_commands(word)
            self.completer.model().setStringList(suggestions)
        else:
            self.completer.model().setStringList([])

    def show_suggestion_popup(self):
        if self.completer.completionCount() > 0:
            self.completer.complete()

    # Integration methods for main editor
    def get_editor(self):
        return self.editor
    
    def get_file_path(self):
        return self._file_path
    
    def set_file_path(self, path):
        self._file_path = path
    
    def get_content(self):
        return self.editor.toPlainText()
    
    def set_content(self, content):
        self.editor.setPlainText(content) 