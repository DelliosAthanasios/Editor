"""
Container Executor
Handles code execution and terminal access within Docker containers
"""

import subprocess
import os
from typing import Tuple, Optional, Callable
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QPlainTextEdit, QComboBox, QLabel
from PyQt5.QtCore import QThread, pyqtSignal, QProcess
from PyQt5.QtGui import QFont, QColor
import logging

logger = logging.getLogger(__name__)


class ContainerExecutor:
    """Executes code within containers"""
    
    def __init__(self, docker_manager):
        self.docker_manager = docker_manager
    
    def execute_command(self, env_name: str, command: str, working_dir: str = "/workspace") -> Tuple[int, str, str]:
        """
        Execute a command in a container
        Returns: (return_code, stdout, stderr)
        """
        return self.docker_manager.execute_in_container(env_name, command, working_dir)
    
    def execute_file(self, env_name: str, file_path: str, language: str = None) -> Tuple[int, str, str]:
        """
        Execute a file in a container
        Automatically determines the command based on file type
        """
        if not os.path.exists(file_path):
            return 1, "", f"File not found: {file_path}"
        
        _, ext = os.path.splitext(file_path)
        filename = os.path.basename(file_path)
        
        # Map file extensions to execution commands
        commands = {
            '.py': f"python {filename}",
            '.js': f"node {filename}",
            '.ts': f"ts-node {filename}",
            '.go': f"go run {filename}",
            '.rs': f"rustc {filename} && ./{filename[:-3]}",
            '.c': f"gcc {filename} -o {filename[:-2]} && ./{filename[:-2]}",
            '.cpp': f"g++ {filename} -o {filename[:-4]} && ./{filename[:-4]}",
            '.java': f"javac {filename} && java {filename[:-5]}",
            '.rb': f"ruby {filename}",
            '.hs': f"ghc {filename} && ./{filename[:-3]}",
            '.lisp': f"sbcl --load {filename}",
        }
        
        command = commands.get(ext.lower(), f"./{filename}")
        return self.execute_command(env_name, command, os.path.dirname(file_path) or "/workspace")
    
    def run_interactive_terminal(self, env_name: str) -> Optional[QProcess]:
        """
        Start an interactive terminal session in a container
        Returns a QProcess that can be used for interactive I/O
        """
        if env_name not in self.docker_manager.containers:
            logger.error(f"Container not found for environment: {env_name}")
            return None
        
        container_id = self.docker_manager.containers[env_name]["container_id"]
        
        process = QProcess()
        # Start docker exec with -it flags for interactive terminal
        process.start("docker", ["exec", "-it", container_id, "/bin/bash"])
        
        if not process.waitForStarted():
            logger.error("Failed to start terminal process")
            return None
        
        return process
    
    def run_build_command(self, env_name: str, language: str) -> Tuple[int, str, str]:
        """
        Run language-specific build commands
        """
        commands = {
            "Python": "python -m py_compile *.py",
            "JavaScript": "npm run build 2>/dev/null || echo 'No build script'",
            "TypeScript": "tsc",
            "Go": "go build ./...",
            "Rust": "cargo build",
            "C": "make",
            "C++": "make",
            "Java": "mvn clean compile",
            "Ruby": "bundle install",
            "Haskell": "stack build",
            "Lisp": "sbcl --eval '(asdf:make :mysystem)'",
        }
        
        command = commands.get(language, "echo 'No build command for this language'")
        return self.execute_command(env_name, command)
    
    def run_test_command(self, env_name: str, language: str) -> Tuple[int, str, str]:
        """
        Run language-specific test commands
        """
        commands = {
            "Python": "python -m pytest",
            "JavaScript": "npm test",
            "Go": "go test ./...",
            "Rust": "cargo test",
            "Java": "mvn test",
            "Ruby": "bundle exec rspec",
            "Haskell": "stack test",
        }
        
        command = commands.get(language, "echo 'No test command for this language'")
        return self.execute_command(env_name, command)


class ExecutionWorker(QThread):
    """Worker thread for executing commands in containers"""
    
    output = pyqtSignal(str)
    finished = pyqtSignal(int, str, str)
    error = pyqtSignal(str)
    
    def __init__(self, executor, env_name, command, working_dir="/workspace"):
        super().__init__()
        self.executor = executor
        self.env_name = env_name
        self.command = command
        self.working_dir = working_dir
    
    def run(self):
        try:
            self.output.emit(f"Executing: {self.command}\n")
            return_code, stdout, stderr = self.executor.execute_command(
                self.env_name,
                self.command,
                self.working_dir
            )
            self.output.emit(stdout)
            if stderr:
                self.output.emit(f"STDERR:\n{stderr}")
            self.finished.emit(return_code, stdout, stderr)
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(1, "", str(e))


class ContainerTerminalWidget(QWidget):
    """Widget for interactive container terminal"""
    
    def __init__(self, env_name: str, executor: ContainerExecutor, parent=None):
        super().__init__(parent)
        self.env_name = env_name
        self.executor = executor
        self.process = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header with environment info
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel(f"Terminal: {self.env_name}"))
        header_layout.addStretch()
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_output)
        header_layout.addWidget(clear_button)
        layout.addLayout(header_layout)
        
        # Terminal output
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        font = QFont("Courier New", 10)
        self.output.setFont(font)
        layout.addWidget(self.output)
        
        self.setLayout(layout)
    
    def append_output(self, text: str):
        """Append text to terminal output"""
        self.output.appendPlainText(text)
    
    def clear_output(self):
        """Clear terminal output"""
        self.output.clear()
    
    def close_terminal(self):
        """Close the terminal process"""
        if self.process:
            self.process.terminate()
            self.process.waitForFinished(3000)


class ContainerExecutionPanel(QWidget):
    """Panel for executing code in containers"""
    
    def __init__(self, executor: ContainerExecutor, parent=None):
        super().__init__(parent)
        self.executor = executor
        self.current_worker = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Command execution section
        cmd_layout = QHBoxLayout()
        cmd_layout.addWidget(QLabel("Execute in:"))
        
        self.env_combo = QComboBox()
        cmd_layout.addWidget(self.env_combo)
        
        run_button = QPushButton("Run File")
        run_button.clicked.connect(self.run_current_file)
        cmd_layout.addWidget(run_button)
        
        build_button = QPushButton("Build")
        build_button.clicked.connect(self.run_build)
        cmd_layout.addWidget(build_button)
        
        test_button = QPushButton("Test")
        test_button.clicked.connect(self.run_tests)
        cmd_layout.addWidget(test_button)
        
        layout.addLayout(cmd_layout)
        
        # Output area
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        font = QFont("Courier New", 9)
        self.output.setFont(font)
        layout.addWidget(self.output)
        
        self.setLayout(layout)
    
    def update_environments(self, environments: list):
        """Update the list of available environments"""
        self.env_combo.clear()
        self.env_combo.addItems(environments)
    
    def run_current_file(self):
        """Run the currently open file"""
        # This would be called from the main editor
        # Implementation depends on getting current file from editor
        pass
    
    def run_build(self):
        """Run build command"""
        env_name = self.env_combo.currentText()
        if not env_name:
            self.append_output("No environment selected")
            return
        
        self.append_output(f"Building in {env_name}...")
        self.worker = ExecutionWorker(self.executor, env_name, "make")
        self.worker.output.connect(self.append_output)
        self.worker.finished.connect(self.on_execution_finished)
        self.worker.start()
    
    def run_tests(self):
        """Run test command"""
        env_name = self.env_combo.currentText()
        if not env_name:
            self.append_output("No environment selected")
            return
        
        self.append_output(f"Running tests in {env_name}...")
        self.worker = ExecutionWorker(self.executor, env_name, "make test")
        self.worker.output.connect(self.append_output)
        self.worker.finished.connect(self.on_execution_finished)
        self.worker.start()
    
    def append_output(self, text: str):
        """Append text to output"""
        self.output.appendPlainText(text)
    
    def on_execution_finished(self, return_code: int, stdout: str, stderr: str):
        """Handle execution completion"""
        if return_code == 0:
            self.append_output("\n✓ Command completed successfully")
        else:
            self.append_output(f"\n✗ Command failed with exit code {return_code}")
