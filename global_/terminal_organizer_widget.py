"""
Terminal Organizer Rich - Professional Console Tab
Integration of terminal_organizer_rich as a PyQt5 widget for the editor
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QTabWidget,
    QTextEdit, QSplitter, QProgressBar, QMessageBox, QDialog,
    QScrollArea, QFrame, QGroupBox, QFormLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QProcess
from PyQt5.QtGui import QFont, QColor, QIcon, QTextCursor
from PyQt5.QtCore import QIODevice

import subprocess
import platform
import os
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TerminalEnvironment:
    """Represents a terminal environment"""
    name: str
    path: str
    env_type: str
    version: str = ""
    description: str = ""
    is_available: bool = True
    launch_command: str = ""


class TerminalScannerThread(QThread):
    """Background thread for scanning terminal environments"""
    
    progress = pyqtSignal(str)
    environments_found = pyqtSignal(list)
    finished = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self.system_type = platform.system()
    
    def run(self):
        try:
            environments = self._scan_terminals()
            self.environments_found.emit(environments)
            self.finished.emit(True)
        except Exception as e:
            logger.error(f"Terminal scanning failed: {e}")
            self.finished.emit(False)
    
    def _scan_terminals(self) -> List[TerminalEnvironment]:
        """Scan for available terminal environments"""
        environments = []
        
        if self.system_type == "Windows":
            environments.extend(self._scan_windows_terminals())
        else:
            environments.extend(self._scan_unix_terminals())
        
        return environments
    
    def _scan_windows_terminals(self) -> List[TerminalEnvironment]:
        """Scan Windows terminals"""
        terminals = []
        
        # PowerShell
        ps_paths = [
            (r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe", "Windows PowerShell"),
            (r"C:\Program Files\PowerShell\7\pwsh.exe", "PowerShell 7 Core"),
        ]
        
        for path, name in ps_paths:
            if os.path.exists(path):
                try:
                    result = subprocess.run([path, "-Version"], capture_output=True, text=True, timeout=2)
                    version = "Available" if result.returncode == 0 else "Unknown"
                    terminals.append(TerminalEnvironment(
                        name=name,
                        path=path,
                        env_type="PowerShell",
                        version=version,
                        description="Windows PowerShell Terminal"
                    ))
                except:
                    pass
        
        # Command Prompt
        terminals.append(TerminalEnvironment(
            name="Command Prompt",
            path="cmd.exe",
            env_type="System Shell",
            version="Available",
            description="Windows Command Prompt"
        ))
        
        # Git Bash
        git_bash_paths = [
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files (x86)\Git\bin\bash.exe"
        ]
        for path in git_bash_paths:
            if os.path.exists(path):
                terminals.append(TerminalEnvironment(
                    name="Git Bash",
                    path=path,
                    env_type="Unix Shell",
                    version="Available",
                    description="Git Bash Shell"
                ))
                break
        
        # Windows Terminal
        wt_path = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe")
        if os.path.exists(wt_path):
            terminals.append(TerminalEnvironment(
                name="Windows Terminal",
                path=wt_path,
                env_type="Terminal Emulator",
                version="Available",
                description="Modern Windows Terminal"
            ))
        
        return terminals
    
    def _scan_unix_terminals(self) -> List[TerminalEnvironment]:
        """Scan Unix/Linux terminals"""
        terminals = []
        
        shells = [
            ("bash", "Bash Shell"),
            ("zsh", "Zsh Shell"),
            ("fish", "Fish Shell"),
            ("ksh", "Korn Shell"),
        ]
        
        for cmd, name in shells:
            try:
                result = subprocess.run(["which", cmd], capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    path = result.stdout.strip()
                    version_result = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=2)
                    version = version_result.stdout.split('\n')[0] if version_result.returncode == 0 else "Available"
                    terminals.append(TerminalEnvironment(
                        name=name,
                        path=path,
                        env_type="Unix Shell",
                        version=version,
                        description=f"{name} Shell Environment"
                    ))
            except:
                pass
        
        return terminals


class TerminalOrganizerWidget(QWidget):
    """Professional Terminal Organizer Tab Widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.system_type = platform.system()
        self.found_terminals = []
        self.current_process = None
        self.init_ui()
        self.scan_terminals()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("Terminal Environment Organizer")
        header_font = QFont()
        header_font.setPointSize(12)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)
        
        # Main tabs
        tabs = QTabWidget()
        
        # Available Terminals Tab
        terminals_widget = self.create_terminals_tab()
        tabs.addTab(terminals_widget, "Available Terminals")
        
        # Terminal Console Tab
        console_widget = self.create_console_tab()
        tabs.addTab(console_widget, "Console")
        
        # System Info Tab
        info_widget = self.create_info_tab()
        tabs.addTab(info_widget, "System Information")
        
        layout.addWidget(tabs)
        
        self.setLayout(layout)
    
    def create_terminals_tab(self) -> QWidget:
        """Create available terminals tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        refresh_button = QPushButton("🔄 Scan Again")
        refresh_button.clicked.connect(self.scan_terminals)
        toolbar_layout.addWidget(refresh_button)
        
        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)
        
        # Progress
        self.scan_progress = QProgressBar()
        self.scan_progress.setVisible(False)
        layout.addWidget(self.scan_progress)
        
        # Terminals list
        self.terminals_list = QListWidget()
        self.terminals_list.itemDoubleClicked.connect(self.launch_selected_terminal)
        layout.addWidget(self.terminals_list)
        
        # Launch button
        launch_button = QPushButton("▶ Launch Selected Terminal")
        launch_button.setMinimumHeight(40)
        launch_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        launch_button.clicked.connect(self.launch_selected_terminal)
        layout.addWidget(launch_button)
        
        return widget
    
    def create_console_tab(self) -> QWidget:
        """Create console/terminal emulator tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Select terminal
        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel("Select Terminal:"))
        
        self.terminal_combo = QComboBox()
        self.terminal_combo.currentIndexChanged.connect(self.on_terminal_selected)
        select_layout.addWidget(self.terminal_combo)
        
        layout.addLayout(select_layout)
        
        # Console display
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(False)
        self.console_output.setFont(QFont("Consolas" if self.system_type == "Windows" else "Courier New", 9))
        self.console_output.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                border: 1px solid #333;
                padding: 5px;
                font-family: monospace;
            }
        """)
        layout.addWidget(self.console_output)
        
        # Command input
        input_layout = QHBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command and press Enter...")
        self.command_input.returnPressed.connect(self.execute_command)
        self.command_input.setFont(QFont("Consolas" if self.system_type == "Windows" else "Courier New", 9))
        input_layout.addWidget(self.command_input)
        
        exec_button = QPushButton("Execute")
        exec_button.setMaximumWidth(80)
        exec_button.clicked.connect(self.execute_command)
        input_layout.addWidget(exec_button)
        
        layout.addLayout(input_layout)
        
        # Clear button
        clear_button = QPushButton("Clear Console")
        clear_button.clicked.connect(lambda: self.console_output.clear())
        layout.addWidget(clear_button)
        
        return widget
    
    def create_info_tab(self) -> QWidget:
        """Create system information tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # System info
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setFont(QFont("Courier New", 9))
        
        info_content = f"""
System Information
{'='*50}

System: {platform.system()}
Release: {platform.release()}
Version: {platform.version()}
Machine: {platform.machine()}
Processor: {platform.processor()}

Python Information
{'='*50}

Python Version: {platform.python_version()}
Python Implementation: {platform.python_implementation()}
Python Compiler: {platform.python_compiler()}

Environment Paths
{'='*50}

Current Directory: {os.getcwd()}
Home Directory: {os.path.expanduser('~')}

Environment Variables (Selected)
{'='*50}

PATH: {os.environ.get('PATH', 'Not set')}
PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}
"""
        
        info_text.setPlainText(info_content)
        layout.addWidget(info_text)
        
        return widget
    
    def scan_terminals(self):
        """Scan for available terminals"""
        self.scan_progress.setVisible(True)
        self.scan_progress.setRange(0, 0)  # Indeterminate
        
        self.scanner_thread = TerminalScannerThread()
        self.scanner_thread.environments_found.connect(self.on_terminals_found)
        self.scanner_thread.finished.connect(self.on_scan_finished)
        self.scanner_thread.start()
    
    def on_terminals_found(self, terminals: List[TerminalEnvironment]):
        """Handle found terminals"""
        self.found_terminals = terminals
        
        # Update list
        self.terminals_list.clear()
        for terminal in terminals:
            item_text = f"{terminal.name}\n  Type: {terminal.env_type} | Version: {terminal.version}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, terminal)
            self.terminals_list.addItem(item)
        
        # Update combo
        self.terminal_combo.clear()
        for terminal in terminals:
            self.terminal_combo.addItem(terminal.name, terminal)
    
    def on_scan_finished(self, success):
        """Handle scan completion"""
        self.scan_progress.setVisible(False)
        
        if success:
            count = len(self.found_terminals)
            self.console_output.append(f"[✓] Found {count} terminal environment(s)\n")
        else:
            self.console_output.append("[✗] Terminal scan failed\n")
    
    def launch_selected_terminal(self):
        """Launch selected terminal"""
        current_item = self.terminals_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a terminal first")
            return
        
        terminal: TerminalEnvironment = current_item.data(Qt.UserRole)
        
        try:
            if self.system_type == "Windows":
                os.startfile(terminal.path) if os.path.exists(terminal.path) else subprocess.Popen(terminal.path)
            else:
                subprocess.Popen([terminal.path])
            
            self.console_output.append(f"[✓] Launched: {terminal.name}\n")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch terminal: {str(e)}")
    
    def on_terminal_selected(self):
        """Handle terminal selection in combo"""
        pass
    
    def execute_command(self):
        """Execute command in selected terminal"""
        command = self.command_input.text().strip()
        if not command:
            return
        
        self.console_output.append(f"$ {command}\n")
        self.command_input.clear()
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.stdout:
                self.console_output.append(result.stdout)
            if result.stderr:
                self.console_output.append(f"[ERROR] {result.stderr}")
            
            if result.returncode != 0:
                self.console_output.append(f"\n[Exit code: {result.returncode}]\n")
            
            self.console_output.append("\n")
        
        except subprocess.TimeoutExpired:
            self.console_output.append("[✗] Command timeout\n\n")
        except Exception as e:
            self.console_output.append(f"[✗] Error: {str(e)}\n\n")
