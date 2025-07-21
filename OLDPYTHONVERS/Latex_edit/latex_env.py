import os
import shutil
import sys
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel,
    QSplitter, QLineEdit, QComboBox, QFileDialog, QFrame
)
from PyQt5.QtCore import Qt, QProcess, pyqtSignal
from PyQt5.QtGui import QFont
try:
    from PyQt5.QtPdf import QPdfDocument  # type: ignore
    from PyQt5.QtPdfWidgets import QPdfView  # type: ignore
    PDF_VIEW_AVAILABLE = True
except ImportError:
    PDF_VIEW_AVAILABLE = False
import subprocess
from global_.editor_widget import EditorTabWidget, load_font_config
from global_.theme_manager import theme_manager_singleton

class LatexEditorEnv(QWidget):
    file_saved = pyqtSignal(str)
    file_opened = pyqtSignal(str)
    content_changed = pyqtSignal()

    def __init__(self, parent=None, file_path=None):
        super().__init__(parent)
        self.compiler = self.find_latex_compiler()
        self.process = None
        self.file_path = file_path or "untitled.tex"
        self.pdf_path = os.path.splitext(self.file_path)[0] + ".pdf"
        self.show_output = True
        self.show_pdf = False
        self.init_ui()
        self.apply_theme()

    def find_latex_compiler(self):
        for exe in ["pdflatex", "xelatex", "lualatex"]:
            if shutil.which(exe):
                return exe
        return None

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Control bar
        control_bar = QHBoxLayout()
        control_bar.setSpacing(6)
        # Compiler selection
        control_bar.addWidget(QLabel("Compiler:"))
        self.compiler_combo = QComboBox()
        self.compiler_combo.addItems(["pdflatex", "xelatex", "lualatex"])
        if self.compiler:
            idx = self.compiler_combo.findText(self.compiler)
            if idx >= 0:
                self.compiler_combo.setCurrentIndex(idx)
        self.compiler_combo.currentTextChanged.connect(self.set_compiler)
        control_bar.addWidget(self.compiler_combo)
        # .tex file path
        control_bar.addWidget(QLabel(".tex:"))
        self.tex_path_edit = QLineEdit(self.file_path)
        self.tex_path_edit.setMinimumWidth(180)
        control_bar.addWidget(self.tex_path_edit)
        tex_browse = QPushButton("...")
        tex_browse.setMaximumWidth(28)
        tex_browse.clicked.connect(self.browse_tex_file)
        control_bar.addWidget(tex_browse)
        # .pdf file path
        control_bar.addWidget(QLabel(".pdf:"))
        self.pdf_path_edit = QLineEdit(self.pdf_path)
        self.pdf_path_edit.setMinimumWidth(180)
        control_bar.addWidget(self.pdf_path_edit)
        pdf_browse = QPushButton("...")
        pdf_browse.setMaximumWidth(28)
        pdf_browse.clicked.connect(self.browse_pdf_file)
        control_bar.addWidget(pdf_browse)
        # Run/Stop
        self.run_btn = QPushButton("Run")
        self.run_btn.clicked.connect(self.run_latex)
        control_bar.addWidget(self.run_btn)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_latex)
        control_bar.addWidget(self.stop_btn)
        # Output toggle
        self.output_toggle_btn = QPushButton("Output")
        self.output_toggle_btn.setCheckable(True)
        self.output_toggle_btn.setChecked(self.show_output)
        self.output_toggle_btn.clicked.connect(self.toggle_output)
        control_bar.addWidget(self.output_toggle_btn)
        # PDF toggle
        self.pdf_toggle_btn = QPushButton("PDF Preview")
        self.pdf_toggle_btn.setCheckable(True)
        self.pdf_toggle_btn.setChecked(self.show_pdf)
        self.pdf_toggle_btn.clicked.connect(self.toggle_pdf)
        control_bar.addWidget(self.pdf_toggle_btn)
        control_bar.addStretch()
        layout.addLayout(control_bar)

        # Splitter: Editor | Output | PDF
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)
        # Editor area (main code editor tab)
        font = load_font_config()
        self.editor_tab = EditorTabWidget(parent=self, font=font, numberline_on_left=True, language="latex", file_path=self.file_path)
        self.editor = self.editor_tab.editor
        self.editor.textChanged.connect(self.content_changed.emit)
        self.splitter.addWidget(self.editor_tab)
        # Output panel
        self.output_panel = QTextEdit()
        self.output_panel.setReadOnly(True)
        self.output_panel.setFont(QFont("Consolas", 10))
        self.output_panel.setMaximumHeight(180)
        self.output_panel.setVisible(self.show_output)
        self.splitter.addWidget(self.output_panel)
        # PDF preview panel
        self.pdf_panel = QFrame()
        pdf_layout = QVBoxLayout(self.pdf_panel)
        pdf_layout.setContentsMargins(0, 0, 0, 0)
        if PDF_VIEW_AVAILABLE:
            self.pdf_doc = QPdfDocument(self)
            self.pdf_view = QPdfView(self.pdf_panel)
            self.pdf_view.setDocument(self.pdf_doc)
            pdf_layout.addWidget(self.pdf_view)
        else:
            self.pdf_view = None
            self.open_pdf_btn = QPushButton("Open PDF in System Viewer")
            self.open_pdf_btn.clicked.connect(self.open_pdf_external)
            pdf_layout.addWidget(self.open_pdf_btn)
        self.pdf_panel.setVisible(self.show_pdf)
        self.splitter.addWidget(self.pdf_panel)
        layout.addWidget(self.splitter)

    def set_compiler(self, compiler):
        self.compiler = compiler

    def browse_tex_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save LaTeX File", self.tex_path_edit.text(), "LaTeX Files (*.tex);;All Files (*)")
        if file_path:
            self.tex_path_edit.setText(file_path)
            self.file_path = file_path
            self.pdf_path_edit.setText(os.path.splitext(file_path)[0] + ".pdf")

    def browse_pdf_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save PDF File", self.pdf_path_edit.text(), "PDF Files (*.pdf);;All Files (*)")
        if file_path:
            self.pdf_path_edit.setText(file_path)
            self.pdf_path = file_path

    def run_latex(self):
        if not self.compiler:
            self.output_panel.append("No LaTeX compiler found.")
            return
        # Save .tex file
        file_path = self.tex_path_edit.text()
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            self.file_saved.emit(file_path)
        except Exception as e:
            self.output_panel.append(f"Failed to save file: {e}")
            return
        self.output_panel.clear()
        self.output_panel.append(f"Running {self.compiler} on {file_path}...\n")
        self.process = QProcess(self)
        self.process.setProgram(self.compiler)
        self.process.setArguments([file_path])
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)
        self.process.start()

    def stop_latex(self):
        if self.process and self.process.state() == QProcess.Running:
            self.process.kill()
            self.output_panel.append("\nProcess stopped by user.")

    def handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode()
        self.output_panel.append(data)

    def handle_stderr(self):
        data = self.process.readAllStandardError().data().decode()
        self.output_panel.append(data)

    def process_finished(self, exit_code, exit_status):
        if exit_code == 0:
            self.output_panel.append("\n✓ Compilation successful!")
            self.update_pdf_preview()
        else:
            self.output_panel.append(f"\n✗ Compilation failed (exit code: {exit_code})")

    def update_pdf_preview(self):
        pdf_path = self.pdf_path_edit.text()
        if os.path.exists(pdf_path):
            if PDF_VIEW_AVAILABLE:
                self.pdf_doc.load(pdf_path)
                self.pdf_view.setPageMode(self.pdf_view.SinglePage)
                self.pdf_view.setZoomMode(self.pdf_view.FitInView)
                self.pdf_panel.setVisible(True)
                self.pdf_toggle_btn.setChecked(True)
            else:
                self.pdf_panel.setVisible(True)
                self.open_pdf_btn.setEnabled(True)
                self.pdf_toggle_btn.setChecked(True)
        else:
            if PDF_VIEW_AVAILABLE:
                self.pdf_doc.load('')
            if hasattr(self, 'open_pdf_btn'):
                self.open_pdf_btn.setEnabled(False)

    def open_pdf_external(self):
        pdf_path = self.pdf_path_edit.text()
        if os.path.exists(pdf_path):
            if sys.platform.startswith('win'):
                os.startfile(pdf_path)
            elif sys.platform.startswith('darwin'):
                subprocess.call(['open', pdf_path])
            else:
                subprocess.call(['xdg-open', pdf_path])
        else:
            self.output_panel.append("No PDF file found to open.")

    def toggle_output(self):
        self.show_output = not self.show_output
        self.output_panel.setVisible(self.show_output)
        self.output_toggle_btn.setChecked(self.show_output)

    def toggle_pdf(self):
        self.show_pdf = not self.show_pdf
        self.pdf_panel.setVisible(self.show_pdf)
        self.pdf_toggle_btn.setChecked(self.show_pdf)
        if self.show_pdf:
            self.update_pdf_preview()

    def apply_theme(self):
        theme_data = theme_manager_singleton.get_theme()
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme_data.get('editor', {}).get('background', '#1e1e1e')};
                color: {theme_data.get('editor', {}).get('foreground', '#ffffff')};
                border: 1px solid {theme_data.get('editor', {}).get('border', '#404040')};
            }}
        """)
        self.output_panel.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme_data.get('console', {}).get('background', '#2d2d2d')};
                color: {theme_data.get('console', {}).get('foreground', '#cccccc')};
                border: 1px solid {theme_data.get('console', {}).get('border', '#404040')};
            }}
        """)

    # Integration methods for main editor
    def get_editor(self):
        return self.editor
    def get_file_path(self):
        return self.tex_path_edit.text()
    def set_file_path(self, path):
        self.tex_path_edit.setText(path)
        self.file_path = path
        self.pdf_path_edit.setText(os.path.splitext(path)[0] + ".pdf")
    def get_content(self):
        return self.editor.toPlainText()
    def set_content(self, content):
        self.editor.setPlainText(content) 