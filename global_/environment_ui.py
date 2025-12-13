"""
Environment UI Components
Provides PyQt5 UI dialogs and widgets for Docker environment management
"""

from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QCheckBox, QListWidget,
    QListWidgetItem, QMessageBox, QProgressBar, QProgressDialog,
    QTabWidget, QFileDialog, QTableWidget, QTableWidgetItem
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QColor
import logging
import os

logger = logging.getLogger(__name__)


class EnvironmentWorker(QThread):
    """Worker thread for Docker operations"""
    
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    error = pyqtSignal(str)
    
    def __init__(self, operation, docker_manager, config=None, env_name=None):
        super().__init__()
        self.operation = operation
        self.docker_manager = docker_manager
        self.config = config
        self.env_name = env_name
    
    def run(self):
        """Execute the operation in background"""
        try:
            if self.operation == "build":
                self.progress.emit(f"Building image: {self.config.image_name}")
                success = self.docker_manager.build_image(self.config, self.progress.emit)
                if success:
                    self.finished.emit(True, f"Successfully built {self.config.image_name}")
                else:
                    self.finished.emit(False, "Build failed")
            
            elif self.operation == "run":
                self.progress.emit(f"Starting container: {self.config.container_name}")
                container_id = self.docker_manager.run_container(self.config, self.progress.emit)
                if container_id:
                    self.finished.emit(True, f"Container started: {container_id[:12]}")
                else:
                    self.finished.emit(False, "Failed to start container")
            
            elif self.operation == "stop":
                self.progress.emit(f"Stopping container: {self.env_name}")
                success = self.docker_manager.stop_container(self.env_name)
                if success:
                    self.finished.emit(True, f"Container stopped")
                else:
                    self.finished.emit(False, "Failed to stop container")
            
            elif self.operation == "remove":
                self.progress.emit(f"Removing container: {self.env_name}")
                success = self.docker_manager.remove_container(self.env_name)
                if success:
                    self.finished.emit(True, f"Container removed")
                else:
                    self.finished.emit(False, "Failed to remove container")
        
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(False, str(e))


class EnvironmentStatusWidget(QWidget):
    """Status indicator widget for display in status bar"""
    
    def __init__(self, docker_manager, parent=None):
        super().__init__(parent)
        self.docker_manager = docker_manager
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        
        # Docker status indicator
        self.status_label = QLabel()
        self.update_status()
        layout.addWidget(self.status_label)
        
        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.setMaximumWidth(80)
        refresh_button.clicked.connect(self.update_status)
        layout.addWidget(refresh_button)
        
        self.setLayout(layout)
    
    def update_status(self):
        """Update Docker status display"""
        if self.docker_manager.is_docker_available():
            daemon_running = self.docker_manager.check_docker_daemon_running()
            if daemon_running:
                num_containers = len(self.docker_manager.containers)
                self.status_label.setText(f"🐳 Docker Ready ({num_containers} environments)")
                self.status_label.setStyleSheet("color: green;")
            else:
                self.status_label.setText("🐳 Docker Installed (daemon not running)")
                self.status_label.setStyleSheet("color: orange;")
        else:
            self.status_label.setText("🐳 Docker Not Installed")
            self.status_label.setStyleSheet("color: red;")


class EnvironmentBuildDialog(QDialog):
    """Dialog for building and running Docker environments"""
    
    def __init__(self, parent, config, docker_manager):
        super().__init__(parent)
        self.config = config
        self.docker_manager = docker_manager
        self.worker = None
        self.container_id = None
        
        self.setWindowTitle(f"Build Environment: {config.name}")
        self.setGeometry(100, 100, 600, 400)
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel(f"Building: {self.config.name}")
        header_font = QFont()
        header_font.setPointSize(12)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)
        
        # Info
        info_text = f"""
Environment: {self.config.name}
Language: {self.config.language}
Image: {self.config.image_name}
Description: {self.config.description}
        """
        info_label = QLabel(info_text.strip())
        layout.addWidget(info_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress_bar)
        
        # Output text
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Courier New", 9))
        layout.addWidget(self.output_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.build_button = QPushButton("Build Image")
        self.build_button.clicked.connect(self.build_image)
        button_layout.addWidget(self.build_button)
        
        self.run_button = QPushButton("Run Container")
        self.run_button.clicked.connect(self.run_container)
        self.run_button.setEnabled(False)
        button_layout.addWidget(self.run_button)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def build_image(self):
        """Build the Docker image"""
        self.build_button.setEnabled(False)
        self.output_text.clear()
        self.output_text.append(f"Starting build of {self.config.image_name}...\n")
        
        self.worker = EnvironmentWorker("build", self.docker_manager, config=self.config)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_build_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def run_container(self):
        """Run the Docker container"""
        self.run_button.setEnabled(False)
        self.output_text.append(f"\nStarting container {self.config.container_name}...\n")
        
        self.worker = EnvironmentWorker("run", self.docker_manager, config=self.config)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_run_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def on_progress(self, message: str):
        """Handle progress updates"""
        self.output_text.append(message)
    
    def on_build_finished(self, success: bool, message: str):
        """Handle build completion"""
        self.output_text.append(f"\n{message}")
        self.build_button.setEnabled(True)
        if success:
            self.run_button.setEnabled(True)
            self.output_text.append("\n✓ Build complete. Ready to run container.")
        else:
            self.output_text.append("\n✗ Build failed.")
    
    def on_run_finished(self, success: bool, message: str):
        """Handle run completion"""
        self.output_text.append(f"\n{message}")
        self.run_button.setEnabled(True)
        if success:
            self.output_text.append("\n✓ Container is now running!")
    
    def on_error(self, error_msg: str):
        """Handle errors"""
        self.output_text.append(f"\n✗ Error: {error_msg}")
        self.build_button.setEnabled(True)
        self.run_button.setEnabled(True)


class EnvironmentSelectionDialog(QDialog):
    """Dialog to select or create environments"""
    
    def __init__(self, parent, docker_manager=None):
        super().__init__(parent)
        if docker_manager is None:
            from global_.environment_manager import get_docker_manager
            docker_manager = get_docker_manager()
        
        self.docker_manager = docker_manager
        
        self.setWindowTitle("Select Environment")
        self.setGeometry(100, 100, 700, 500)
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Choose an Environment to Create")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Tabs
        self.tabs = QTabWidget()
        
        # Tab 1: Pre-configured environments
        self.preconfigured_tab = QWidget()
        self.init_preconfigured_tab()
        self.tabs.addTab(self.preconfigured_tab, "Pre-configured")
        
        # Tab 2: Custom environment
        self.custom_tab = QWidget()
        self.init_custom_tab()
        self.tabs.addTab(self.custom_tab, "Custom")
        
        layout.addWidget(self.tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        create_button = QPushButton("Create")
        create_button.clicked.connect(self.create_environment)
        button_layout.addWidget(create_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def init_preconfigured_tab(self):
        """Initialize pre-configured environments tab"""
        layout = QVBoxLayout(self.preconfigured_tab)
        
        # Check Docker
        if not self.docker_manager.is_docker_available():
            docker_status = QLabel("⚠️ Docker not found. Please install Docker Desktop.")
            docker_status.setStyleSheet("color: red;")
            layout.addWidget(docker_status)
        else:
            daemon_running = self.docker_manager.check_docker_daemon_running()
            if daemon_running:
                status_label = QLabel("✓ Docker is ready")
                status_label.setStyleSheet("color: green;")
            else:
                status_label = QLabel("⚠️ Docker daemon not running")
                status_label.setStyleSheet("color: orange;")
            layout.addWidget(status_label)
        
        # List of environments
        self.env_list = QListWidget()
        
        try:
            from global_.predefined_environments import list_environments, get_environment_by_name
            
            for env_name in list_environments():
                env_config = get_environment_by_name(env_name)
                item_text = f"{env_name}\n  {env_config.description}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, env_name)
                self.env_list.addItem(item)
        except ImportError as e:
            logger.error(f"Failed to load environments: {e}")
            error_item = QListWidgetItem("Error loading environments")
            self.env_list.addItem(error_item)
        
        self.env_list.itemDoubleClicked.connect(self.create_environment)
        layout.addWidget(self.env_list)
        
        self.preconfigured_tab.setLayout(layout)
    
    def init_custom_tab(self):
        """Initialize custom environment tab"""
        layout = QVBoxLayout(self.custom_tab)
        
        # Name
        layout.addWidget(QLabel("Environment Name:"))
        self.custom_name = QLineEdit()
        self.custom_name.setPlaceholderText("e.g., My Custom Env")
        layout.addWidget(self.custom_name)
        
        # Language
        layout.addWidget(QLabel("Language:"))
        self.custom_language = QLineEdit()
        self.custom_language.setPlaceholderText("e.g., Python")
        layout.addWidget(self.custom_language)
        
        # Description
        layout.addWidget(QLabel("Description:"))
        self.custom_description = QLineEdit()
        self.custom_description.setPlaceholderText("Brief description")
        layout.addWidget(self.custom_description)
        
        # Dockerfile
        layout.addWidget(QLabel("Dockerfile:"))
        self.custom_dockerfile = QTextEdit()
        self.custom_dockerfile.setPlaceholderText("FROM ubuntu:22.04\n# Add your commands here")
        self.custom_dockerfile.setFont(QFont("Courier New", 10))
        layout.addWidget(self.custom_dockerfile)
        
        layout.addStretch()
        self.custom_tab.setLayout(layout)
    
    def create_environment(self):
        """Create the selected environment"""
        if self.tabs.currentIndex() == 0:
            # Pre-configured
            current_item = self.env_list.currentItem()
            if not current_item:
                QMessageBox.warning(self, "Warning", "Please select an environment")
                return
            
            env_name = current_item.data(Qt.UserRole)
            
            try:
                from global_.predefined_environments import get_environment_by_name
                config = get_environment_by_name(env_name)
                
                dialog = EnvironmentBuildDialog(self, config, self.docker_manager)
                dialog.exec_()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create environment: {str(e)}")
        
        else:
            # Custom
            name = self.custom_name.text().strip()
            language = self.custom_language.text().strip()
            description = self.custom_description.text().strip()
            dockerfile = self.custom_dockerfile.toPlainText().strip()
            
            if not name or not language or not dockerfile:
                QMessageBox.warning(self, "Incomplete", "Please fill in all fields")
                return
            
            try:
                from global_.environment_manager import EnvironmentConfig
                
                config = EnvironmentConfig(
                    name=name,
                    language=language,
                    description=description,
                    dockerfile=dockerfile,
                    image_name=f"editor-{language.lower()}:latest",
                    container_name=f"editor-{language.lower()}-container"
                )
                
                dialog = EnvironmentBuildDialog(self, config, self.docker_manager)
                dialog.exec_()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create environment: {str(e)}")


class EnvironmentManagerDialog(QDialog):
    """Dialog to manage existing environments"""
    
    def __init__(self, parent, docker_manager=None):
        super().__init__(parent)
        if docker_manager is None:
            from global_.environment_manager import get_docker_manager
            docker_manager = get_docker_manager()
        
        self.docker_manager = docker_manager
        
        self.setWindowTitle("Manage Environments")
        self.setGeometry(100, 100, 800, 500)
        self.init_ui()
        self.refresh_environment_list()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Manage Docker Environments")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Environment list table
        self.table = QTableWidget(0, 5)  # 5 columns
        self.table.setHorizontalHeaderLabels(["Name", "Language", "Status", "Container ID", "Actions"])
        layout.addWidget(self.table)
        
        # Info area
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(100)
        layout.addWidget(self.info_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_environment_list)
        button_layout.addWidget(refresh_button)
        
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_container)
        self.start_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_container)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self.remove_container)
        self.remove_button.setEnabled(False)
        button_layout.addWidget(self.remove_button)
        
        button_layout.addStretch()
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def refresh_environment_list(self):
        """Refresh the list of environments"""
        self.table.setRowCount(0)
        
        for env_name, env_info in self.docker_manager.containers.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Name
            name_item = QTableWidgetItem(env_name)
            self.table.setItem(row, 0, name_item)
            
            # Language
            config = env_info.get("config", {})
            language = config.get("language", "Unknown")
            lang_item = QTableWidgetItem(language)
            self.table.setItem(row, 1, lang_item)
            
            # Status
            status = env_info.get("status", "unknown")
            status_item = QTableWidgetItem(str(status.value if hasattr(status, 'value') else status))
            self.table.setItem(row, 2, status_item)
            
            # Container ID
            container_id = env_info.get("container_id", "N/A")[:12]
            id_item = QTableWidgetItem(container_id)
            self.table.setItem(row, 3, id_item)
            
            # Store full env name for later use
            name_item.setData(Qt.UserRole, env_name)
        
        self.table.resizeColumnsToContents()
    
    def start_container(self):
        """Start selected container"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select an environment")
            return
        
        env_name = self.table.item(current_row, 0).data(Qt.UserRole)
        
        self.worker = EnvironmentWorker("run", self.docker_manager, env_name=env_name)
        self.worker.finished.connect(self.on_operation_finished)
        self.worker.start()
    
    def stop_container(self):
        """Stop selected container"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select an environment")
            return
        
        env_name = self.table.item(current_row, 0).data(Qt.UserRole)
        
        reply = QMessageBox.question(
            self,
            "Confirm",
            f"Stop container for {env_name}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.worker = EnvironmentWorker("stop", self.docker_manager, env_name=env_name)
            self.worker.finished.connect(self.on_operation_finished)
            self.worker.start()
    
    def remove_container(self):
        """Remove selected container"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select an environment")
            return
        
        env_name = self.table.item(current_row, 0).data(Qt.UserRole)
        
        reply = QMessageBox.question(
            self,
            "Confirm",
            f"Remove container for {env_name}? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.worker = EnvironmentWorker("remove", self.docker_manager, env_name=env_name)
            self.worker.finished.connect(self.on_operation_finished)
            self.worker.start()
    
    def on_operation_finished(self, success: bool, message: str):
        """Handle operation completion"""
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)
        
        self.refresh_environment_list()
    
    def on_table_selection_changed(self):
        """Handle table selection changes"""
        current_row = self.table.currentRow()
        has_selection = current_row >= 0
        
        self.start_button.setEnabled(has_selection)
        self.stop_button.setEnabled(has_selection)
        self.remove_button.setEnabled(has_selection)
        
        if has_selection:
            env_name = self.table.item(current_row, 0).data(Qt.UserRole)
            env_info = self.docker_manager.containers.get(env_name, {})
            config = env_info.get("config", {})
            
            info = f"""
Environment: {env_name}
Language: {config.get('language', 'N/A')}
Container ID: {env_info.get('container_id', 'N/A')}
Status: {env_info.get('status', 'unknown')}
            """
            self.info_text.setText(info.strip())
