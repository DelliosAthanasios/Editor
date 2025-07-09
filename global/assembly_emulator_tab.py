import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QComboBox, QMessageBox, QSizePolicy, QFileDialog, QSplitter, QSpacerItem
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'future'))
from future.assemblyEmuv1 import EnhancedAssemblySimulator

class AssemblyEmulatorTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.simulator = EnhancedAssemblySimulator()
        self._file_path = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Top bar: Architecture chooser, Show/Hide Output, Run button
        top_bar = QHBoxLayout()
        arch_label = QLabel("Architecture:")
        self.arch_combo = QComboBox()
        self.arch_combo.addItems(self.simulator.list_architectures())
        self.arch_combo.setFont(QFont("Fira Mono", 14, QFont.Bold))
        self.arch_combo.setMinimumHeight(36)
        top_bar.addWidget(arch_label)
        top_bar.addWidget(self.arch_combo)

        # Show/Hide Output button (clearer, with text and icon)
        self.toggle_output_btn = QPushButton()
        self.toggle_output_btn.setCheckable(True)
        self.toggle_output_btn.setChecked(True)
        self.toggle_output_btn.setFixedSize(100, 28)
        self.toggle_output_btn.setToolTip("Show/Hide Output")
        self.toggle_output_btn.setText("Hide Output")
        self.toggle_output_btn.clicked.connect(self.toggle_output)
        top_bar.addWidget(self.toggle_output_btn)

        top_bar.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Run button (small, green, play symbol, top right)
        self.run_btn = QPushButton()
        self.run_btn.setFixedSize(36, 36)
        self.run_btn.setStyleSheet("QPushButton { background-color: #27ae60; color: white; border-radius: 18px; font-size: 18px; } QPushButton:hover { background-color: #219150; }")
        self.run_btn.setToolTip("Run (Ctrl+Enter)")
        self.run_btn.setText("▶")
        self.run_btn.clicked.connect(self.run_assembly)
        top_bar.addWidget(self.run_btn)

        layout.addLayout(top_bar)

        # File name label
        self.file_label = QLabel("[Untitled]")
        self.file_label.setStyleSheet("font-weight: bold; color: #4a90e2; font-size: 13pt;")
        layout.addWidget(self.file_label)

        # Splitter for code and output
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)

        # Assembly code input
        code_widget = QWidget()
        code_layout = QVBoxLayout(code_widget)
        code_layout.setContentsMargins(0, 0, 0, 0)
        code_label = QLabel("Assembly Code:")
        self.code_edit = QTextEdit()
        self.code_edit.setPlaceholderText("Type your assembly code here...")
        self.code_edit.setFont(QFont("Fira Mono", 12))
        code_layout.addWidget(code_label)
        code_layout.addWidget(self.code_edit)
        self.splitter.addWidget(code_widget)

        # Results area
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_label = QLabel("Results:")
        self.result_edit = QTextEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setFont(QFont("Fira Mono", 11))
        self.result_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        result_layout.addWidget(result_label)
        result_layout.addWidget(self.result_edit)
        self.splitter.addWidget(result_widget)

        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        layout.addWidget(self.splitter)

    def toggle_output(self):
        if self.toggle_output_btn.isChecked():
            self.toggle_output_btn.setText("Hide Output")
            self.splitter.widget(1).show()
        else:
            self.toggle_output_btn.setText("Show Output")
            self.splitter.widget(1).hide()

    def run_assembly(self):
        arch = self.arch_combo.currentText()
        code = self.code_edit.toPlainText().strip()
        if not code:
            QMessageBox.warning(self, "No Code", "Please enter assembly code to run.")
            return
        if not self.simulator.select_architecture(arch):
            QMessageBox.critical(self, "Error", f"Failed to select architecture: {arch}")
            return
        result = self.simulator.execute_assembly(code)
        self.display_result(result)

    def display_result(self, result):
        if not result.success:
            self.result_edit.setPlainText(f"✗ Execution failed: {result.error_message}")
            return
        lines = []
        lines.append(f"✓ Execution successful!")
        lines.append(f"Instructions executed: {result.instructions_executed}")
        lines.append(f"Execution time: {result.execution_time_ns/1000:.2f} μs")
        lines.append(f"Machine code: {result.machine_code.hex()}")
        if result.disassembly:
            lines.append("\nDisassembly:")
            for line in result.disassembly[:10]:
                lines.append(f"  {line}")
            if len(result.disassembly) > 10:
                lines.append(f"  ... and {len(result.disassembly) - 10} more instructions")
        # Register changes
        before = result.registers_before
        after = result.registers_after
        changes = []
        for reg in sorted(set(before.keys()) | set(after.keys())):
            before_val = before.get(reg, 0)
            after_val = after.get(reg, 0)
            if before_val != after_val:
                changes.append(f"  {reg:6s}: 0x{before_val:016x} -> 0x{after_val:016x}")
        if changes:
            lines.append("\nRegister Changes:")
            lines.extend(changes)
        else:
            lines.append("\nNo register changes.")
        self.result_edit.setPlainText("\n".join(lines))

    def new_file(self):
        self._file_path = None
        self.code_edit.clear()
        self.file_label.setText("[Untitled]")

    def open_file(self, file_path=None):
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(self, "Open Assembly File", "", "Assembly Files (*.s *.asm);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                self.code_edit.setPlainText(code)
                self._file_path = file_path
                self.file_label.setText(os.path.basename(file_path))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")

    def save_file(self, file_path=None):
        if not file_path:
            if self._file_path:
                file_path = self._file_path
            else:
                file_path, _ = QFileDialog.getSaveFileName(self, "Save Assembly File", "", "Assembly Files (*.s *.asm);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.code_edit.toPlainText())
                self._file_path = file_path
                self.file_label.setText(os.path.basename(file_path))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Save failed: {str(e)}") 