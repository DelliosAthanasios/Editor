import sys
import json
import os
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QListWidget, QFileDialog, QMessageBox, QComboBox,
                            QListWidgetItem, QInputDialog)
from PyQt5.QtCore import Qt

class ConfigWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_file = "coderunner_config.json"
        self.extensions = {}
        self.load_config()
        self.init_ui()
    
    def init_ui(self):
        """Create the UI with PyQt5"""
        self.setWindowTitle("CodeRunner Configuration")
        self.setGeometry(100, 100, 600, 400)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("CodeRunner Configuration")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Extension input section
        input_layout = QHBoxLayout()
        
        # File extension input
        input_layout.addWidget(QLabel("File Extension:"))
        self.ext_input = QLineEdit()
        self.ext_input.setPlaceholderText("e.g., .py, .js, .cpp")
        input_layout.addWidget(self.ext_input)
        
        # App path input
        input_layout.addWidget(QLabel("App Path:"))
        self.app_input = QLineEdit()
        self.app_input.setPlaceholderText("Path to application")
        input_layout.addWidget(self.app_input)
        
        # Browse button
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_app)
        input_layout.addWidget(self.browse_btn)
        
        layout.addLayout(input_layout)
        
        # Buttons section
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Add New")
        self.add_btn.clicked.connect(self.add_extension)
        button_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self.edit_extension)
        button_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_extension)
        button_layout.addWidget(self.delete_btn)
        
        layout.addLayout(button_layout)
        
        # List of current saved paths
        layout.addWidget(QLabel("Current File Associations:"))
        self.extension_list = QListWidget()
        self.extension_list.itemClicked.connect(self.on_item_selected)
        layout.addWidget(self.extension_list)
        
        # Run section
        run_layout = QHBoxLayout()
        run_layout.addWidget(QLabel("Script Address:"))
        self.script_input = QLineEdit()
        self.script_input.setPlaceholderText("Path to script file")
        run_layout.addWidget(self.script_input)
        
        self.browse_script_btn = QPushButton("Browse Script")
        self.browse_script_btn.clicked.connect(self.browse_script)
        run_layout.addWidget(self.browse_script_btn)
        
        self.run_btn = QPushButton("Run Script")
        self.run_btn.clicked.connect(self.run_script)
        self.run_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        run_layout.addWidget(self.run_btn)
        
        layout.addLayout(run_layout)
        
        # Populate the list
        self.populate_list()
    
    def load_config(self):
        """Load configuration from JSON file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.extensions = json.load(f)
            except json.JSONDecodeError:
                self.extensions = {}
        else:
            # Default configurations
            self.extensions = {
                ".py": "python",
                ".js": "node",
                ".cpp": "g++",
                ".java": "java"
            }
            self.save_config()
    
    def save_config(self):
        """Save everything in a JSON file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.extensions, f, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")
    
    def populate_list(self):
        """Make a list with all the current saved paths"""
        self.extension_list.clear()
        for ext, app in self.extensions.items():
            item_text = f"{ext} → {app}"
            self.extension_list.addItem(item_text)
    
    def browse_app(self):
        """Browse for application executable"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Application", "", "Executable Files (*.exe);;All Files (*)"
        )
        if file_path:
            self.app_input.setText(file_path)
    
    def browse_script(self):
        """Browse for script file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Script", "", "All Files (*)"
        )
        if file_path:
            self.script_input.setText(file_path)
    
    def add_extension(self):
        """Add New button functionality"""
        ext = self.ext_input.text().strip()
        app = self.app_input.text().strip()
        
        if not ext or not app:
            QMessageBox.warning(self, "Warning", "Please fill in both extension and app path!")
            return
        
        if not ext.startswith('.'):
            ext = '.' + ext
        
        self.extensions[ext] = app
        self.save_config()
        self.populate_list()
        
        # Clear inputs
        self.ext_input.clear()
        self.app_input.clear()
        
        QMessageBox.information(self, "Success", f"Added {ext} → {app}")
    
    def edit_extension(self):
        """Edit button functionality"""
        current_item = self.extension_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select an item to edit!")
            return
        
        # Parse current selection
        item_text = current_item.text()
        ext = item_text.split(' → ')[0]
        current_app = self.extensions[ext]
        
        # Get new app path
        new_app, ok = QInputDialog.getText(
            self, "Edit Association", 
            f"Enter new app path for {ext}:", 
            text=current_app
        )
        
        if ok and new_app.strip():
            self.extensions[ext] = new_app.strip()
            self.save_config()
            self.populate_list()
            QMessageBox.information(self, "Success", f"Updated {ext} → {new_app}")
    
    def delete_extension(self):
        """Delete button functionality"""
        current_item = self.extension_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select an item to delete!")
            return
        
        # Parse current selection
        item_text = current_item.text()
        ext = item_text.split(' → ')[0]
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to delete the association for {ext}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            del self.extensions[ext]
            self.save_config()
            self.populate_list()
            QMessageBox.information(self, "Success", f"Deleted association for {ext}")
    
    def on_item_selected(self, item):
        """Handle item selection in the list"""
        item_text = item.text()
        ext = item_text.split(' → ')[0]
        app = item_text.split(' → ')[1]
        
        # Populate input fields for editing
        self.ext_input.setText(ext)
        self.app_input.setText(app)
    
    def run_script(self):
        """Run script functionality"""
        script_path = self.script_input.text().strip()
        
        if not script_path:
            QMessageBox.warning(self, "Warning", "Please provide a script address!")
            return
        
        if not os.path.exists(script_path):
            QMessageBox.critical(self, "Error", "Script file does not exist!")
            return
        
        # Get file extension
        _, ext = os.path.splitext(script_path)
        ext = ext.lower()
        
        # Check if extension exists and is connected with an app
        if ext in self.extensions:
            app = self.extensions[ext]
            try:
                # Run the script
                if ext == '.py':
                    subprocess.run([app, script_path], check=True)
                elif ext == '.js':
                    subprocess.run([app, script_path], check=True)
                elif ext == '.cpp':
                    # For C++, we need to compile first
                    exe_path = script_path.replace('.cpp', '.exe')
                    subprocess.run([app, script_path, '-o', exe_path], check=True)
                    subprocess.run([exe_path], check=True)
                elif ext == '.java':
                    # For Java, compile and run
                    subprocess.run(['javac', script_path], check=True)
                    class_name = os.path.basename(script_path).replace('.java', '')
                    subprocess.run([app, class_name], check=True)
                else:
                    # Generic execution
                    subprocess.run([app, script_path], check=True)
                
                QMessageBox.information(self, "Success", f"Script executed successfully!")
                
            except subprocess.CalledProcessError as e:
                QMessageBox.critical(self, "Execution Error", f"Script execution failed: {str(e)}")
            except FileNotFoundError:
                QMessageBox.critical(self, "Error", f"Application '{app}' not found!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
        else:
            # Print an error message
            QMessageBox.critical(
                self, "Error", 
                f"No application associated with '{ext}' extension!\n"
                f"Please add an association for this file type."
            )


def main():
    """Create UI and run the application"""
    app = QApplication(sys.argv)
    window = ConfigWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
