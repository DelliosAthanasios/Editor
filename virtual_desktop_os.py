#!/usr/bin/env python3
"""
Virtual Desktop Operating System Prototype
A simulated desktop environment for running Python GUI applications
"""

import sys
import os
import subprocess
import importlib.util
from typing import Dict, List, Optional
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class AppWindow(QMdiSubWindow):
    """Represents a window for a running application"""
    
    closed = pyqtSignal(str)  # Signal emitted when window is closed
    
    def __init__(self, app_id: str, title: str, widget: QWidget):
        super().__init__()
        self.app_id = app_id
        self.setWidget(widget)
        self.setWindowTitle(title)
        self.resize(600, 400)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        # Window controls
        self.setWindowFlags(
            Qt.SubWindow |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowMaximizeButtonHint |
            Qt.WindowCloseButtonHint
        )
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.closed.emit(self.app_id)
        event.accept()

class TaskbarButton(QPushButton):
    """Button representing a running application in the taskbar"""
    
    def __init__(self, app_id: str, title: str):
        super().__init__(title)
        self.app_id = app_id
        self.setMaximumHeight(30)
        self.setMinimumWidth(120)
        self.setMaximumWidth(200)
        self.setCheckable(True)

class StartMenu(QWidget):
    """Start menu with application launcher"""
    
    app_requested = pyqtSignal(str)  # Signal for launching apps
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Popup)
        self.setFixedSize(250, 300)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Virtual Desktop")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 14px; padding: 10px;")
        layout.addWidget(title)
        
        # Application list
        apps_layout = QVBoxLayout()
        
        # Built-in applications
        built_in_apps = [
            ("File Explorer", "file_explorer"),
            ("Terminal", "terminal"),
            ("Text Editor", "text_editor"),
            ("Calculator", "calculator")
        ]
        
        for name, app_id in built_in_apps:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, aid=app_id: self.launch_app(aid))
            apps_layout.addWidget(btn)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        apps_layout.addWidget(line)
        
        # Load Python script option
        load_script_btn = QPushButton("Load Python Script...")
        load_script_btn.clicked.connect(self.load_python_script)
        apps_layout.addWidget(load_script_btn)
        
        apps_layout.addStretch()
        layout.addLayout(apps_layout)
        
        # Exit button
        exit_btn = QPushButton("Exit Desktop")
        exit_btn.clicked.connect(QApplication.quit)
        layout.addWidget(exit_btn)
    
    def launch_app(self, app_id: str):
        """Launch a built-in application"""
        self.app_requested.emit(app_id)
        self.hide()
    
    def load_python_script(self):
        """Load and run a Python script"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Python Script", "", "Python Files (*.py)"
        )
        if file_path:
            self.app_requested.emit(f"script:{file_path}")
            self.hide()

class FileExplorerWidget(QWidget):
    """Simple file explorer"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Address bar
        addr_layout = QHBoxLayout()
        addr_layout.addWidget(QLabel("Path:"))
        self.path_edit = QLineEdit(os.getcwd())
        self.path_edit.returnPressed.connect(self.navigate_to_path)
        addr_layout.addWidget(self.path_edit)
        
        go_btn = QPushButton("Go")
        go_btn.clicked.connect(self.navigate_to_path)
        addr_layout.addWidget(go_btn)
        layout.addLayout(addr_layout)
        
        # File list
        self.file_list = QListWidget()
        self.file_list.itemDoubleClicked.connect(self.item_double_clicked)
        layout.addWidget(self.file_list)
        
        self.refresh_file_list()
    
    def navigate_to_path(self):
        path = self.path_edit.text()
        if os.path.exists(path) and os.path.isdir(path):
            os.chdir(path)
            self.refresh_file_list()
    
    def refresh_file_list(self):
        self.file_list.clear()
        self.path_edit.setText(os.getcwd())
        
        # Add parent directory
        if os.getcwd() != os.path.dirname(os.getcwd()):
            self.file_list.addItem("..")
        
        # Add directories and files
        try:
            for item in sorted(os.listdir()):
                if os.path.isdir(item):
                    self.file_list.addItem(f"📁 {item}")
                else:
                    self.file_list.addItem(f"📄 {item}")
        except PermissionError:
            self.file_list.addItem("Permission denied")
    
    def item_double_clicked(self, item):
        name = item.text()
        if name == "..":
            os.chdir(os.path.dirname(os.getcwd()))
            self.refresh_file_list()
        elif name.startswith("📁"):
            dir_name = name[2:]  # Remove folder emoji
            new_path = os.path.join(os.getcwd(), dir_name)
            if os.path.exists(new_path):
                os.chdir(new_path)
                self.refresh_file_list()

class TerminalWidget(QWidget):
    """Simple terminal emulator"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Output area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("background-color: black; color: green; font-family: monospace;")
        layout.addWidget(self.output_text)
        
        # Input area
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("$"))
        self.command_input = QLineEdit()
        self.command_input.returnPressed.connect(self.execute_command)
        input_layout.addWidget(self.command_input)
        layout.addLayout(input_layout)
        
        self.output_text.append("Virtual Terminal v1.0")
        self.output_text.append(f"Current directory: {os.getcwd()}")
        self.output_text.append("Type 'help' for available commands\n")
    
    def execute_command(self):
        command = self.command_input.text().strip()
        if not command:
            return
        
        self.output_text.append(f"$ {command}")
        self.command_input.clear()
        
        # Handle basic commands
        if command == "help":
            self.output_text.append("Available commands: ls, pwd, cd, clear, help")
        elif command == "ls":
            try:
                files = os.listdir()
                self.output_text.append("\n".join(files) if files else "Directory is empty")
            except Exception as e:
                self.output_text.append(f"Error: {e}")
        elif command == "pwd":
            self.output_text.append(os.getcwd())
        elif command.startswith("cd "):
            path = command[3:]
            try:
                os.chdir(path)
                self.output_text.append(f"Changed to: {os.getcwd()}")
            except Exception as e:
                self.output_text.append(f"Error: {e}")
        elif command == "clear":
            self.output_text.clear()
        else:
            # Try to execute as system command
            try:
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True, timeout=10
                )
                if result.stdout:
                    self.output_text.append(result.stdout)
                if result.stderr:
                    self.output_text.append(f"Error: {result.stderr}")
            except subprocess.TimeoutExpired:
                self.output_text.append("Command timed out")
            except Exception as e:
                self.output_text.append(f"Command not found: {command}")
        
        self.output_text.append("")  # Add blank line

class TextEditorWidget(QWidget):
    """Simple text editor"""
    
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        new_btn = QPushButton("New")
        new_btn.clicked.connect(self.new_file)
        toolbar.addWidget(new_btn)
        
        open_btn = QPushButton("Open")
        open_btn.clicked.connect(self.open_file)
        toolbar.addWidget(open_btn)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_file)
        toolbar.addWidget(save_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Text area
        self.text_edit = QTextEdit()
        self.text_edit.setStyleSheet("font-family: monospace;")
        layout.addWidget(self.text_edit)
    
    def new_file(self):
        self.text_edit.clear()
        self.current_file = None
    
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "All Files (*.*)"
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    self.text_edit.setPlainText(f.read())
                self.current_file = file_path
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not open file: {e}")
    
    def save_file(self):
        if self.current_file:
            try:
                with open(self.current_file, 'w') as f:
                    f.write(self.text_edit.toPlainText())
                QMessageBox.information(self, "Success", "File saved successfully")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not save file: {e}")
        else:
            self.save_file_as()
    
    def save_file_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save File", "", "All Files (*.*)"
        )
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(self.text_edit.toPlainText())
                self.current_file = file_path
                QMessageBox.information(self, "Success", "File saved successfully")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not save file: {e}")

class CalculatorWidget(QWidget):
    """Simple calculator"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Display
        self.display = QLineEdit("0")
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignRight)
        self.display.setStyleSheet("font-size: 18px; padding: 10px;")
        layout.addWidget(self.display)
        
        # Buttons
        buttons_layout = QGridLayout()
        
        buttons = [
            ('C', 0, 0), ('±', 0, 1), ('%', 0, 2), ('÷', 0, 3),
            ('7', 1, 0), ('8', 1, 1), ('9', 1, 2), ('×', 1, 3),
            ('4', 2, 0), ('5', 2, 1), ('6', 2, 2), ('−', 2, 3),
            ('1', 3, 0), ('2', 3, 1), ('3', 3, 2), ('+', 3, 3),
            ('0', 4, 0, 1, 2), ('.', 4, 2), ('=', 4, 3)
        ]
        
        for button in buttons:
            btn_text = button[0]
            row = button[1]
            col = button[2]
            row_span = button[3] if len(button) > 3 else 1
            col_span = button[4] if len(button) > 4 else 1
            
            btn = QPushButton(btn_text)
            btn.clicked.connect(lambda checked, text=btn_text: self.button_clicked(text))
            btn.setMinimumHeight(40)
            buttons_layout.addWidget(btn, row, col, row_span, col_span)
        
        layout.addLayout(buttons_layout)
        
        self.current_value = "0"
        self.pending_operation = None
        self.pending_value = None
    
    def button_clicked(self, text):
        if text.isdigit():
            if self.current_value == "0":
                self.current_value = text
            else:
                self.current_value += text
        elif text == ".":
            if "." not in self.current_value:
                self.current_value += "."
        elif text == "C":
            self.current_value = "0"
            self.pending_operation = None
            self.pending_value = None
        elif text in ["+", "−", "×", "÷"]:
            if self.pending_operation and self.pending_value is not None:
                self.calculate()
            self.pending_value = float(self.current_value)
            self.pending_operation = text
            self.current_value = "0"
        elif text == "=":
            if self.pending_operation and self.pending_value is not None:
                self.calculate()
        
        self.display.setText(self.current_value)
    
    def calculate(self):
        try:
            current = float(self.current_value)
            if self.pending_operation == "+":
                result = self.pending_value + current
            elif self.pending_operation == "−":
                result = self.pending_value - current
            elif self.pending_operation == "×":
                result = self.pending_value * current
            elif self.pending_operation == "÷":
                result = self.pending_value / current if current != 0 else 0
            
            self.current_value = str(result)
            self.pending_operation = None
            self.pending_value = None
        except:
            self.current_value = "Error"

class VirtualDesktop(QMainWindow):
    """Main virtual desktop environment"""
    
    def __init__(self):
        super().__init__()
        self.running_apps: Dict[str, AppWindow] = {}
        self.app_counter = 0
        self.setup_ui()
        self.setup_desktop()
    
    def setup_ui(self):
        """Setup the main desktop interface"""
        self.setWindowTitle("Virtual Desktop OS")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget with MDI area
        self.mdi_area = QMdiArea()
        self.mdi_area.setStyleSheet("""
            QMdiArea {
                background-color: #2E86AB;
                background-image: url();
            }
        """)
        self.setCentralWidget(self.mdi_area)
        
        # Setup taskbar
        self.setup_taskbar()
        
        # Setup start menu
        self.start_menu = StartMenu()
        self.start_menu.app_requested.connect(self.launch_application)
    
    def setup_taskbar(self):
        """Setup the taskbar at the bottom"""
        # Taskbar widget
        taskbar = QWidget()
        taskbar.setFixedHeight(40)
        taskbar.setStyleSheet("""
            QWidget {
                background-color: #1f1f1f;
                border-top: 1px solid #444;
            }
        """)
        
        taskbar_layout = QHBoxLayout(taskbar)
        taskbar_layout.setContentsMargins(5, 5, 5, 5)
        
        # Start button
        self.start_button = QPushButton("🏠 Start")
        self.start_button.setFixedSize(80, 30)
        self.start_button.clicked.connect(self.toggle_start_menu)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        taskbar_layout.addWidget(self.start_button)
        
        # Running apps area
        self.taskbar_apps_layout = QHBoxLayout()
        taskbar_layout.addLayout(self.taskbar_apps_layout)
        
        taskbar_layout.addStretch()
        
        # System tray / time
        time_label = QLabel(QTime.currentTime().toString("hh:mm"))
        time_label.setStyleSheet("color: white; padding: 5px;")
        taskbar_layout.addWidget(time_label)
        
        # Add taskbar to bottom
        self.statusBar().addPermanentWidget(taskbar, 1)
        self.statusBar().setFixedHeight(40)
    
    def setup_desktop(self):
        """Setup desktop icons and background"""
        # You could add desktop icons here
        pass
    
    def toggle_start_menu(self):
        """Show/hide start menu"""
        if self.start_menu.isVisible():
            self.start_menu.hide()
        else:
            # Position start menu above start button
            button_pos = self.start_button.mapToGlobal(QPoint(0, 0))
            menu_pos = QPoint(button_pos.x(), button_pos.y() - self.start_menu.height())
            self.start_menu.move(menu_pos)
            self.start_menu.show()
    
    def launch_application(self, app_identifier: str):
        """Launch an application"""
        app_id = f"app_{self.app_counter}"
        self.app_counter += 1
        
        try:
            if app_identifier == "file_explorer":
                widget = FileExplorerWidget()
                title = "File Explorer"
            elif app_identifier == "terminal":
                widget = TerminalWidget()
                title = "Terminal"
            elif app_identifier == "text_editor":
                widget = TextEditorWidget()
                title = "Text Editor"
            elif app_identifier == "calculator":
                widget = CalculatorWidget()
                title = "Calculator"
            elif app_identifier.startswith("script:"):
                # Load Python script
                script_path = app_identifier[7:]  # Remove "script:" prefix
                widget = self.load_python_script(script_path)
                if widget is None:
                    return
                title = f"Script: {os.path.basename(script_path)}"
            else:
                QMessageBox.warning(self, "Error", f"Unknown application: {app_identifier}")
                return
            
            # Create window
            window = AppWindow(app_id, title, widget)
            window.closed.connect(self.close_application)
            
            # Add to MDI area
            self.mdi_area.addSubWindow(window)
            window.show()
            
            # Add to running apps
            self.running_apps[app_id] = window
            
            # Add taskbar button
            self.add_taskbar_button(app_id, title, window)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch application: {e}")
    
    def load_python_script(self, script_path: str) -> Optional[QWidget]:
        """Load and execute a Python script"""
        try:
            # Create a container widget for the script
            container = QWidget()
            container.setLayout(QVBoxLayout())
            
            # Add info label
            info_label = QLabel(f"Running: {os.path.basename(script_path)}")
            container.layout().addWidget(info_label)
            
            # Execute the script in a separate namespace
            script_globals = {'__name__': '__main__', 'container': container}
            
            with open(script_path, 'r') as f:
                script_content = f.read()
            
            exec(script_content, script_globals)
            
            return container
            
        except Exception as e:
            QMessageBox.critical(self, "Script Error", f"Failed to load script: {e}")
            return None
    
    def add_taskbar_button(self, app_id: str, title: str, window: AppWindow):
        """Add a button to the taskbar for the running app"""
        button = TaskbarButton(app_id, title)
        button.clicked.connect(lambda: self.focus_application(app_id))
        button.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                text-align: left;
                padding: 5px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:checked {
                background-color: #0078d4;
            }
        """)
        
        self.taskbar_apps_layout.addWidget(button)
        
        # Store reference to button in window
        window.taskbar_button = button
    
    def focus_application(self, app_id: str):
        """Focus on a running application"""
        if app_id in self.running_apps:
            window = self.running_apps[app_id]
            if window.isMinimized():
                window.showNormal()
            window.setFocus()
            self.mdi_area.setActiveSubWindow(window)
    
    def close_application(self, app_id: str):
        """Close a running application"""
        if app_id in self.running_apps:
            window = self.running_apps[app_id]
            
            # Remove taskbar button
            if hasattr(window, 'taskbar_button'):
                self.taskbar_apps_layout.removeWidget(window.taskbar_button)
                window.taskbar_button.deleteLater()
            
            # Remove from running apps
            del self.running_apps[app_id]

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    
    # Set application properties
    app.setApplicationName("Virtual Desktop OS")
    app.setApplicationVersion("1.0")
    
    # Create and show desktop
    desktop = VirtualDesktop()
    desktop.show()
    
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())
