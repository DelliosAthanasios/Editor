import os
import shutil
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel, QSplitter, QMessageBox, QLineEdit, QToolBar, QAction, QFrame)
from PyQt5.QtCore import Qt, QProcess
from PyQt5.QtGui import QFont, QIcon
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
    def __init__(self, parent=None, file_path=None):
        super().__init__(parent)
        self.setWindowTitle("LaTeX Editor")
        self.setMinimumSize(1000, 700)
        self.compiler = self.find_latex_compiler()
        self.process = None
        self.file_path = file_path
        self.init_ui()
        # Dynamic saving
        self._file_path = file_path or "untitled.tex"
        enable_dynamic_saving_for_qt(self)

    def find_latex_compiler(self):
        for exe in ["pdflatex", "xelatex", "lualatex"]:
            if shutil.which(exe):
                return exe
        return None

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        # Toolbar
        toolbar = QToolBar()
        run_action = QAction(QIcon.fromTheme("media-playback-start"), "Run", self)
        run_action.triggered.connect(self.run_latex)
        stop_action = QAction(QIcon.fromTheme("media-playback-stop"), "Stop", self)
        stop_action.triggered.connect(self.stop_latex)
        toolbar.addAction(run_action)
        toolbar.addAction(stop_action)
        toolbar.addSeparator()
        # Add common LaTeX actions (bold, italic, section, etc.)
        bold_action = QAction(QIcon.fromTheme("format-text-bold"), "Bold", self)
        bold_action.triggered.connect(lambda: self.insert_latex_command("\\textbf{}"))
        italic_action = QAction(QIcon.fromTheme("format-text-italic"), "Italic", self)
        italic_action.triggered.connect(lambda: self.insert_latex_command("\\textit{}"))
        section_action = QAction(QIcon.fromTheme("format-header-1"), "Section", self)
        section_action.triggered.connect(lambda: self.insert_latex_command("\\section{}"))
        toolbar.addAction(bold_action)
        toolbar.addAction(italic_action)
        toolbar.addAction(section_action)
        main_layout.addWidget(toolbar)
        # Status
        self.status_label = QLabel()
        if self.compiler:
            self.status_label.setText(f"Compiler found: {self.compiler}")
        else:
            self.status_label.setText("No LaTeX compiler found!")
        main_layout.addWidget(self.status_label)
        # Splitter for editor/output
        self.splitter = QSplitter(Qt.Vertical)
        # Editor area
        editor_container = QWidget()
        editor_layout = QHBoxLayout(editor_container)
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Fira Code", 13))
        self.editor.setPlaceholderText("Write your LaTeX code here...")
        self.highlighter = LatexHighlighter(self.editor.document())
        self.minimap = Minimap(self, self.editor, None, theme_manager_singleton.get_theme())
        self.numberline = NumberLine(self.editor, theme_manager_singleton.get_theme())
        self.numberline.setFont(self.editor.font())
        editor_layout.addWidget(self.numberline)
        editor_layout.addWidget(self.editor)
        editor_layout.addWidget(self.minimap)
        editor_container.setLayout(editor_layout)
        self.splitter.addWidget(editor_container)
        # Output area with frame
        output_frame = QFrame()
        output_frame.setFrameShape(QFrame.StyledPanel)
        output_layout = QVBoxLayout(output_frame)
        output_label = QLabel("Output:")
        output_label.setStyleSheet("font-weight: bold; margin-bottom: 2px;")
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Fira Code", 11))
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output)
        self.splitter.addWidget(output_frame)
        main_layout.addWidget(self.splitter)
        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search in LaTeX...")
        self.search_bar.textChanged.connect(self.search_in_editor)
        main_layout.addWidget(self.search_bar)
        # Word suggestions
        self.completer = QCompleter()
        self.completer.setModel(QStringListModel([]))
        self.completer.setWidget(self.editor)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(False)
        self.editor.textChanged.connect(self.update_suggestions)
        self.editor.cursorPositionChanged.connect(self.show_suggestion_popup)

    def insert_latex_command(self, command):
        cursor = self.editor.textCursor()
        if command.endswith("{}"):  # Place cursor inside braces
            command = command[:-1]
            cursor.insertText(command)
        else:
            cursor.insertText(command)
        self.editor.setTextCursor(cursor)

    def run_latex(self):
        if not self.compiler:
            QMessageBox.critical(self, "Error", "No LaTeX compiler found on system.")
            return
        code = self.editor.toPlainText()
        with open(self._file_path, "w", encoding="utf-8") as f:
            f.write(code)
        self.output.clear()
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
            self.output.append("\nProcess stopped.")

    def handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode()
        self.output.append(data)

    def handle_stderr(self):
        data = self.process.readAllStandardError().data().decode()
        self.output.append(data)

    def process_finished(self):
        self.output.append("\nProcess finished.")

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

    def search_in_editor(self, text):
        # Simple search: highlight all occurrences
        cursor = self.editor.textCursor()
        fmt = self.editor.currentCharFormat()
        fmt.setBackground(Qt.yellow)
        self.editor.moveCursor(cursor.Start)
        while True:
            cursor = self.editor.document().find(text, cursor)
            if cursor.isNull():
                break
            cursor.mergeCharFormat(fmt) 