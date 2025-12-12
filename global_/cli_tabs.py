"""
CLI Tools Tab Widget
Integrates Rich CLI tools as editor tabs
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QTextEdit, QPushButton
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont
import subprocess
import os
import sys


class CLIToolWorker(QThread):
    """Background worker for running CLI tools"""
    
    output = pyqtSignal(str)
    finished = pyqtSignal(bool)
    
    def __init__(self, tool_path: str):
        super().__init__()
        self.tool_path = tool_path
    
    def run(self):
        try:
            result = subprocess.run(
                [sys.executable, self.tool_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            self.output.emit(result.stdout)
            if result.stderr:
                self.output.emit(f"\n[STDERR]\n{result.stderr}")
            self.finished.emit(result.returncode == 0)
        except subprocess.TimeoutExpired:
            self.output.emit("[Timeout] Tool execution exceeded 60 seconds")
            self.finished.emit(False)
        except Exception as e:
            self.output.emit(f"[Error] {str(e)}")
            self.finished.emit(False)


class LanguageDetectorTab(QWidget):
    """Language Detector CLI as editor tab"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_path = None
        self.init_ui()
        self.run_detector()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header
        header = QLabel("Programming Language Detector")
        header.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(header)
        
        # Output
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Courier New", 9))
        self.output.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #00aa00;
                border: 1px solid #333;
                padding: 5px;
            }
        """)
        layout.addWidget(self.output)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.run_detector)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def run_detector(self):
        """Run language detector"""
        self.output.clear()
        self.output.setText("Scanning languages...\n")
        
        tool_path = os.path.join(
            os.path.dirname(__file__),
            "cli_tools",
            "language_detector_cli.py"
        )
        
        self.worker = CLIToolWorker(tool_path)
        self.worker.output.connect(self.append_output)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
    
    def append_output(self, text: str):
        """Append output"""
        self.output.append(text)
    
    def on_finished(self, success: bool):
        """Tool finished"""
        self.output.append(f"\n[Scan {'completed' if success else 'failed'}]")


class SystemMonitorTab(QWidget):
    """System Monitor CLI as editor tab"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_path = None
        self.init_ui()
        self.run_monitor()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header
        header = QLabel("System Resources Monitor")
        header.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(header)
        
        # Output
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Courier New", 9))
        self.output.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                border: 1px solid #333;
                padding: 5px;
            }
        """)
        layout.addWidget(self.output)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.run_monitor)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def run_monitor(self):
        """Run system monitor"""
        self.output.clear()
        self.output.setText("Gathering system information...\n")
        
        tool_path = os.path.join(
            os.path.dirname(__file__),
            "cli_tools",
            "system_monitor_cli.py"
        )
        
        self.worker = CLIToolWorker(tool_path)
        self.worker.output.connect(self.append_output)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
    
    def append_output(self, text: str):
        """Append output"""
        self.output.append(text)
    
    def on_finished(self, success: bool):
        """Tool finished"""
        self.output.append(f"\n[Monitor {'completed' if success else 'failed'}]")


class TerminalOrganizerTab(QWidget):
    """Terminal Organizer CLI as editor tab"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_path = None
        self.init_ui()
        self.run_organizer()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header
        header = QLabel("Terminal Environment Organizer")
        header.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(header)
        
        # Output
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Courier New", 9))
        self.output.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #00aabb;
                border: 1px solid #333;
                padding: 5px;
            }
        """)
        layout.addWidget(self.output)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.run_organizer)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def run_organizer(self):
        """Run terminal organizer"""
        self.output.clear()
        self.output.setText("Scanning terminal environments...\n")
        
        tool_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "terminal_organizer_rich.py"
        )
        
        # Set UTF-8 encoding for Windows compatibility
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        self.worker = CLIToolWorker(tool_path)
        self.worker.output.connect(self.append_output)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
    
    def append_output(self, text: str):
        """Append output"""
        # Decode any encoding issues
        try:
            # Try to clean up garbled characters
            if isinstance(text, str):
                self.output.append(text)
            else:
                self.output.append(str(text))
        except Exception as e:
            self.output.append(f"[Display Error] {str(e)}\n{repr(text)}")
    
    def on_finished(self, success: bool):
        """Tool finished"""
        self.output.append(f"\n[Scan {'completed' if success else 'failed'}]")
